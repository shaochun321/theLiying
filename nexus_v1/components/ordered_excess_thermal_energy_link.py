"""nexus_v1.components.ordered_excess_thermal_energy_link — Ordered EXCESS
heat-energy transfer edge (P1-B1.5).

TYPE:HYBRID — an ordered energy-transport edge between two `ThermalCell`
nodes, transferring only the portion of stored energy ABOVE each node's
own local ambient baseline.

Context (方案第二十三节, P1-B1.5, 批判十九, 2026-07-17): 第十九份批判用代码
复现验证了两处 P1-B0/B1 遗留的真实缺陷：

  ①`ThermalCell.capacitor.charge` 不是绝对热能，是相对该节点自身
    `ambient_temperature`（逐节点字段，`dynamic_thermal_field.py:175`）的
    偏差量——`temperature = ambient_temperature + capacitor.voltage`。
    两个 `ambient_temperature` 不同的节点，`charge=0` 代表的实际温度可以
    完全不同（已实测：`ambient=100`/`ambient=0` 两节点`charge=0`时温度
    分别是100.0/0.0）。直接用 `charge` 做转移隐含"两端共享同一参考系"的
    假设。且 `charge` 可以为负（节点低于自身基线时），此时若不处理，
    `p_e=a_e·charge<0` 会让"实际转移方向"翻转但边身份仍是原tail/head，
    破坏 P2-C 已依赖的"非负有序通量"前提。
  ②`a_e·Δt>1` 时递推 `u^{n+1}=(1-a_eΔt)u^n` 会让 tail 翻负号（已实测：
    `a_e=2.0,dt=1.0` 时 `u_i` 从 10 变成 -10），P1-B1 完全没有防护。

**本模块正式改名 `OrderedExcessThermalEnergyLink`**（与批判十八把
`AdvectiveThermalLink`改名`OrderedThermalEnergyLink`同一理由——语义确实
变了：从"搬运全部能量"收紧为"只搬运统一环境基线以上的过剩部分"，命名应
反映真实语义，不应 overclaim）。

Physical mechanism — Q1/Q2/Q3 (RULES.md 强制三问，本轮为既有组件的定义修正，
非全新组件，沿用原 Q1/Q2 并订正 Q3):

  Q1 生物/物理对应物: 同前版本——外部驱动的定向热能转移过程，不声称模拟
    介质质量（未来 physical-anchor 模式才升格真正 advection）。

  Q2 物理结构:
    Sources = `tail` 端"过剩能量" `u_tail^+=max(tail.capacitor.charge, 0)`
    （**不是**原始 `charge`，见 Q3①）-> `power()`（只读） -> Targets =
    `tail`/`head` 对称 `Capacitor.inject()`。**新增前提校验**：`tail.
    ambient_temperature == head.ambient_temperature`（Q3①，两端必须共享
    同一参考基线，否则转移物理上不对等，拒绝执行）。**新增稳定性门**：
    `rate_per_time * dt <= 1.0`（Q3②，单边非负性保证，fail-fast——不用
    `min()` 静默钳制转移量，那会把线性模型悄悄变成分段模型并掩盖不稳定
    配置）。

  Q3 参数依据:
    - **过剩能量钳位**（批判十九①，采纳）：`u_i^+=max(q_i,0)`，`q_i`=
      `ThermalCell.capacitor.charge`。语义订正为"统一环境基线以上的规范化
      过剩热状态"，不是节点的完整热力学内能——`energy ledger 闭合不代表
      完整热力学账本闭合`：驱动该有序转移的外部机械功/压力差未建模（见
      下方 `transport_drive_mode` 字段）。
    - **单边稳定性门**（批判十九④，采纳）：`rate_per_time*dt<=1.0` 时
      `u_i^{n+1}=(1-a_eΔt)u_i^n>=0` 恒成立；超出时在任何状态修改前
      `raise ValueError`。
    - `rate_per_time`（`a_e=1/τ_e`）：**`τ_e=2.0` 是 EXP 机制测试起点，
      尚未物理标定**（批判十九③加强措辞）——未来标定路径：若已知参考
      时间 `t_r` 内应保留比例 `r`，则 `a_e=-ln(r)/t_r`；或用半衰时间
      `a_e=ln(2)/t_half`。当前数值不声称有物理来源，只用于机制正确性
      验证。
    - `transport_drive_mode="exogenous_normalized"`（批判十九⑦，采纳）：
      非能量数值标志字段，声明当前不对驱动该转移的外部机械功/熵增/
      热力学第二定律做任何资格宣称——P1-C 只验证热量转移守恒/稳定性/
      结构可追溯性，进入 physical-anchor/advection 阶段后才加入质量流
      与驱动功账本。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.dynamic_thermal_field import ThermalCell
from nexus_v1.components.structural_address import OrderedEdgeIdentity

# EXP: P1-B0 冻结值，见模块 docstring Q3。τ_e=2.0（同 GradedPotentialRelay 量级，
# 非物理标定起点）。
DEFAULT_TAU_E: float = 2.0
DEFAULT_RATE_PER_TIME: float = 1.0 / DEFAULT_TAU_E  # a_e = 1/τ_e = 0.5

DRIVE_MODE_EXOGENOUS_NORMALIZED = "exogenous_normalized"


@dataclass(frozen=True)
class OrderedExcessThermalEnergyLink:
    """TYPE:HYBRID — 有序**过剩**热能转移边。`rate_per_time`（a_e）∈[0,∞)
    且必须有限。`transport_drive_mode` 是非能量标志字段，声明驱动机制的
    建模范围（见模块 docstring Q3）。

    首版不允许：隐藏 callback / 按坐标自动计算 / 按"朝向"选择端点 / 在
    `power()` 中直接修改节点 / 边自身偷偷保存上一步剩余能量。
    """
    identity: OrderedEdgeIdentity
    rate_per_time: float = DEFAULT_RATE_PER_TIME
    transport_drive_mode: str = DRIVE_MODE_EXOGENOUS_NORMALIZED

    def __post_init__(self):
        if not math.isfinite(self.rate_per_time):
            raise ValueError(
                f"OrderedExcessThermalEnergyLink: rate_per_time must be finite, "
                f"got {self.rate_per_time}")
        if self.rate_per_time < 0.0:
            raise ValueError(
                f"OrderedExcessThermalEnergyLink: rate_per_time must be >= 0, "
                f"got {self.rate_per_time}")

    def power(self, tail_energy: float) -> float:
        """p_e = a_e * u_tail^+，u_tail^+ = max(tail_energy, 0)（批判十九①：
        只搬运统一环境基线以上的过剩部分，节点低于自身基线时不提供过剩
        热量，p_e 恒 >= 0，tail/head 身份不会因符号翻转而颠倒）。只读，
        不产生副作用。
        """
        excess = max(tail_energy, 0.0)
        return self.rate_per_time * excess


def is_single_edge_stable(link: OrderedExcessThermalEnergyLink, dt: float) -> bool:
    """单边非负性稳定门（批判十九④）：`rate_per_time*dt<=1.0` 时递推
    `u^{n+1}=(1-a_eΔt)u^n>=0` 恒成立（当 `u^n>=0`）。这是本条边**独立于**
    其他通道的最基本正确性条件，与 P1-C 才处理的"多通道联合稳定性预算"
    是不同层次的检查（P1-C 的 η_i^joint 是本门通过之后、多条边共享同一
    节点时的进一步约束）。
    """
    return link.rate_per_time * dt <= 1.0


def step_ordered_transport(
    link: OrderedExcessThermalEnergyLink,
    tail_cell: ThermalCell,
    head_cell: ThermalCell,
    dt: float,
) -> float:
    """单边驱动（P1-B1.5 范围：单边+稳定性门+基线一致性校验；仍不处理多边
    竞争——那是 P1-B2/B3 才需要的 `ThermalTransportPlan`）。

    SINGLE-EDGE DIAGNOSTIC ONLY（批判十九⑥）：本函数在 P1-B2 引入
    `ThermalTransportPlan` 后不应继续作为生产联合调度接口——多条边共享
    同一 tail 节点时，逐边直接调用本函数会绕过"先全部快照再统一提交"的
    纪律。P1-B2 落地前，本函数仍是唯一的单边验证入口。

    Raises:
        ValueError: 若 `tail_cell.ambient_temperature != head_cell.
            ambient_temperature`（批判十九①，两端必须共享同一参考基线，
            否则转移物理上不对等）；或 `is_single_edge_stable()` 为
            False（批判十九④，fail-fast，不做静默钳制）。两种情况下都
            在触碰任一节点状态之前拒绝，`tail_cell`/`head_cell` 均不变。
    """
    if tail_cell.ambient_temperature != head_cell.ambient_temperature:
        raise ValueError(
            f"step_ordered_transport: tail/head must share the same "
            f"ambient_temperature reference baseline "
            f"(tail={tail_cell.ambient_temperature}, "
            f"head={head_cell.ambient_temperature}) — transferring "
            f"capacitor.charge between cells with different local ambient "
            f"baselines is not physically equivalent (批判十九①).")
    if not is_single_edge_stable(link, dt):
        raise ValueError(
            f"step_ordered_transport: single-edge stability violated "
            f"(rate_per_time={link.rate_per_time} * dt={dt} = "
            f"{link.rate_per_time * dt} > 1.0) — would overdraw tail below "
            f"zero excess energy (批判十九④, fail-fast per project "
            f"discipline, no silent clamping).")

    tail_energy = tail_cell.capacitor.charge  # 快照，Q3①：只读原始charge值
    p_e = link.power(tail_energy)             # power() 内部已做 max(.,0) 钳位
    tail_cell.capacitor.inject(-p_e, dt)
    head_cell.capacitor.inject(p_e, dt)
    return p_e * dt
