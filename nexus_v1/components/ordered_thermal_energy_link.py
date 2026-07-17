"""nexus_v1.components.ordered_thermal_energy_link — Ordered heat-energy
transfer edge (P1-B1).

TYPE:HYBRID — an ordered energy-transport edge between two `ThermalCell`
nodes, at the same layer as `ThermalLink` (diffusion) but with a directed
transfer law instead of a reciprocal one.

Context (方案第二十三节, P1-B0/B1, 批判十八, 2026-07-17): 批判十八指出
`AdvectiveThermalLink` 这个命名 overclaim 了物理——真正的介质平流需要质量转移
（`J^adv=ṁ_e·c_p·T_i`，节点热容 `C_i=m_i·c_p` 随之变化），而当前世界模型仍处于
`THERMAL_FIELD_MODE="normalized"`（`dynamic_thermal_field.py` 已声明：无
`A_ij`/`V_i`，无介质质量状态）。只搬热能、不搬质量，不是严格意义上的"平流"。
**本组件正式命名 `OrderedThermalEnergyLink`**——外部驱动的有序热能转移，明确
不声称模拟介质质量；未来项目进入 physical-anchor 模式（加入质量/比热/流量/体积）
才升格为真正的 advection。

**本轮（P1-B1）范围**：只做单边机制 + 解析解对比验证。不接多边竞争（P1-B2）、
不建 `ThermalTransportPlan`（P1-B3 处理多边争抢同一 tail 节点时才需要）。

Physical mechanism — Q1/Q2/Q3 (RULES.md 强制三问):

  Q1 生物/物理对应物:
    外部驱动的定向热能转移过程（如受控载流通道、理想化定向热流），REF 与
    `dynamic_thermal_field.py` 的 `ThermalLink`（导热网络）同一物理场景类比——
    差别只在于扩散是互易的，本组件建模的是外部维持的、有方向性的转移过程。

  Q2 物理结构:
    Sources = `tail` 端 `ThermalCell.capacitor.charge`（**已冻结的能量零点**，见
    Q3 第2点） -> `OrderedThermalEnergyLink.power()`（只读计算，不持状态、不改
    节点、无隐藏 callback、不按坐标/朝向自动计算端点） -> Targets = `tail`/`head`
    两端对称的 `Capacitor.inject()`（外部驱动函数 `step_ordered_transport()` 统一
    应用，同 `ThermalLink.flux()`→`ThermalFieldGraph.step()` 的"只读计算+外部
    统一应用"模式）。

  Q3 参数依据:
    - 能量零点：状态变量 `u_i` 直接读 `ThermalCell.capacitor.charge`（构造时
      charge=0 的绝对能量状态），不从 `.temperature` 临时倒算——因为
      `p_e=a_e·u_i` 依赖 `u_i` 的绝对零点，任意平移的温度会让转移量依赖零点
      选择这个结构性错误（批判十八②）。
    - `rate_per_time`（即 `a_e=1/τ_e`）：首轮 EXP 起点 `τ_e=2.0`（同
      `GradedPotentialRelay` 已用的 `r_leak×capacitance=2.0` 量级，项目既有 RC
      时间尺度惯例），即 `DEFAULT_RATE_PER_TIME=0.5`，不拍脑袋填 0.1（批判十八③）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.dynamic_thermal_field import ThermalCell
from nexus_v1.components.structural_address import OrderedEdgeIdentity

# EXP: P1-B0 冻结值，见模块 docstring Q3。τ_e=2.0（同 GradedPotentialRelay 量级）。
DEFAULT_TAU_E: float = 2.0
DEFAULT_RATE_PER_TIME: float = 1.0 / DEFAULT_TAU_E  # a_e = 1/τ_e = 0.5


@dataclass(frozen=True)
class OrderedThermalEnergyLink:
    """TYPE:HYBRID — 有序热能转移边。`rate_per_time`（a_e）∈[0,∞) 且必须有限。

    首版不允许（批判十八§四.1）：隐藏 callback / 按坐标自动计算 / 按"朝向"
    选择端点 / 在 `power()` 中直接修改节点 / 边自身偷偷保存上一步剩余能量。
    `power()` 只根据传入的快照值计算，不读取任何外部可变状态。
    """
    identity: OrderedEdgeIdentity
    rate_per_time: float = DEFAULT_RATE_PER_TIME

    def __post_init__(self):
        if not math.isfinite(self.rate_per_time):
            raise ValueError(
                f"OrderedThermalEnergyLink: rate_per_time must be finite, "
                f"got {self.rate_per_time}")
        if self.rate_per_time < 0.0:
            raise ValueError(
                f"OrderedThermalEnergyLink: rate_per_time must be >= 0, "
                f"got {self.rate_per_time}")

    def power(self, tail_energy: float) -> float:
        """p_e = a_e * u_tail。只读，不产生副作用。`tail_energy` 由调用方
        显式传入快照值（不在此方法内部读取任何节点状态），保证"统一快照"
        纪律不会被本方法内部悄悄绕过。
        """
        return self.rate_per_time * tail_energy


def step_ordered_transport(
    link: OrderedThermalEnergyLink,
    tail_cell: ThermalCell,
    head_cell: ThermalCell,
    dt: float,
) -> float:
    """单边驱动：读 tail 端能量快照 -> 算功率 -> 对称应用到两端。

    P1-B1 范围：只处理单条边，不涉及多边竞争同一 tail 节点的场景（那是
    P1-B2 才需要"先全部快照再统一提交"的 `ThermalTransportPlan`）。这里
    "快照"体现为：`tail_energy` 在调用 `inject()` 之前就已读出并固定，
    不会因为后续的 `inject()` 调用而改变。

    量纲契约（批判十七④/十八，方案已正式化）：`p_e` 是功率/电流，不是
    已乘 dt 的能量——`Capacitor.inject(current, dt)` 内部自己做 `*dt`，
    这里不能重复乘一次（同 P1-0 已修复的 dt² 教训）。

    Returns:
        q_e = p_e * dt（本步实际转移的能量，供调用方做账本核对）。
    """
    tail_energy = tail_cell.capacitor.charge  # 快照，能量零点=Capacitor自身charge
    p_e = link.power(tail_energy)
    tail_cell.capacitor.inject(-p_e, dt)
    head_cell.capacitor.inject(p_e, dt)
    return p_e * dt
