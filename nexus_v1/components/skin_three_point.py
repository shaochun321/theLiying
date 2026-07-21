"""nexus_v1.components.skin_three_point — P2-A2 三点动态皮肤（独立物理资格）。

TYPE:HYBRID — 复用既有 `ThermalFieldGraph`/`ThermalCell`/`ThermalLink`
（`dynamic_thermal_field.py`）构造一条线性三点皮肤带 `s1-s2-s3`，不新建
任何物理机制，只是该既有基础设施的一个具体配置实例。

方案依据：`cell-cell/交叉比对/document - 2026-07-20T203329.284.md`（最小
动态皮肤方案）+ `document - 2026-07-20T212539.832.md`（三点物理支撑应由
`ThermalFieldGraph` 的三个节点+两条热连接实现，"这三个节点是皮肤物理状态
节点，不是三个外接传感器"）+ `评判_P2A1顺序倒置修正_2026-07-21.md`
（P2-A2 只建立 `s1-s2-s3` 并测量原始 `q_i^skin(t)`，不涉及生成元/κ/皮肤
映射）。

**范围边界（严格遵守，见 `document - 2026-07-21T122445.485.md` §五）**：
本模块只负责皮肤自身的独立物理资格——刺激一点、另两点以不同延迟和幅度
受影响、能量守恒、数值稳定。**不**反推参数迎合任何生成元的观测活动带、
不预选增益让皮肤信号刚好落入某个区间、不为迁就生成元响应特性改动扩散
模型本身。与 `BaseGenerator` 的连接（`D_i^sim: q_i^skin → u_i`）是
P2-A1b 的工作，本模块不涉及。

RULES.md 强制三问：

  Q1 生物对应物：
    一小段连续导热皮肤组织，三个测量位置之间通过组织本身的热传导
    （Fourier 定律）耦合——`ThermalFieldGraph`/`ThermalLink` 已经承担
    这个物理机制的 BIO/PHYS 论证（见该模块 docstring），本文件只是
    选择三节点线性拓扑的具体实例化，不新增生物学论证。

  Q2 物理结构：
    `build_three_point_skin()` 只调用既有 `ThermalCell`/`ThermalLink`/
    `ThermalFieldGraph` 构造函数，不修改这些类本身。地址挂载复用
    `AddressRegistry.register_physical`（P2-A0 先例），不新增地址系统
    API，不给 `ThermalCell` 添加字段。

  Q3 参数依据：
    - 节点间距：复用项目既有 `world.py` 的 `BODY_SCALE_M=0.01m/sim_unit`
      换算（1 sim_unit 间距 = 1cm，符合局部皮肤支撑的真实尺度），仅作为
      位置文档字段，不参与 flux 计算（`ThermalLink.flux()` 只用 kappa
      和温度差，不用距离）。
    - kappa（热耦合系数）分两档，复用已建立的双轨纪律（同
      `test_dynamic_thermal_field.py` 的 T-DTF-1/2 vs T-DTF-3/4/5 分工）：
      **真实锚定** `NORMALIZED_KAPPA_DEFAULT`（海水/组织热扩散率量级，
      用于稳定性/守恒验收，不要求在合理步数内观测到扩散——该尺度下
      扩散确实极慢，是物理真实，不是缺陷）；
      **测试尺度** 直接复用 `test_dynamic_thermal_field.py` 已建立并
      验证过的同一个 `_TEST_KAPPA_0=0.05` 值（不新造数字），用于观测
      "刺激一点、另一点以不同延迟和幅度受影响"这条独立物理资格的核心
      判据。
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from .dynamic_thermal_field import (
    NORMALIZED_KAPPA_DEFAULT, DEFAULT_R_LEAK_AMBIENT,
    ThermalCell, ThermalFieldGraph, ThermalLink,
)
from .semiconductor import Capacitor
from .structural_address import AddressRegistry, DOMAIN_SKIN_PATCH, StructuralAddress
from .world import BODY_SCALE_M

# EXP：直接复用 `test_dynamic_thermal_field.py:49` 已验证过的测试尺度值
# （tau=1/kappa=20 步，数百步内可观测扩散），不新造数字。仅用于"独立物理
# 资格"验收（T-STP-3/4），不作为生产候选值。
TEST_KAPPA_THREE_POINT: float = 0.05

# 与 `_TEST_R_LEAK_AMBIENT`(200.0) 同一比例关系（比扩散慢 10x，保证梯度
# 先形成再被环境抹平），复用同一推导。
TEST_R_LEAK_AMBIENT_THREE_POINT: float = 200.0

# 三个节点在 sim_unit 坐标系下的间距 = 1（= BODY_SCALE_M = 0.01m 真实
# 间距），仅作为 position 文档字段，不参与 flux 计算。
_NODE_SPACING_SIM_UNITS: float = 1.0


def build_three_point_skin(
    kappa: Optional[float] = None,
    r_leak_ambient: Optional[float] = None,
) -> ThermalFieldGraph:
    """构造三点线性皮肤 `s1-s2-s3`（node_id=0,1,2，两条链式 ThermalLink）。

    `kappa`/`r_leak_ambient` 为 None 时使用真实锚定的
    `NORMALIZED_KAPPA_DEFAULT`/`DEFAULT_R_LEAK_AMBIENT`（稳定性/守恒验收
    档）；传入 `TEST_KAPPA_THREE_POINT`/`TEST_R_LEAK_AMBIENT_THREE_POINT`
    做独立物理资格验收（观测延迟/衰减响应）。
    """
    k = kappa if kappa is not None else NORMALIZED_KAPPA_DEFAULT
    r_leak = r_leak_ambient if r_leak_ambient is not None else DEFAULT_R_LEAK_AMBIENT

    cells = [
        ThermalCell(node_id=i, position=(i * _NODE_SPACING_SIM_UNITS, 0.0, 0.0),
                    capacitor=Capacitor(capacitance=1.0))
        for i in range(3)
    ]
    links = [
        ThermalLink(i=0, j=1, kappa=k),
        ThermalLink(i=1, j=2, kappa=k),
    ]
    return ThermalFieldGraph(cells=cells, links=links, r_leak_ambient=r_leak)


def register_skin_cells(
    registry: AddressRegistry, graph: ThermalFieldGraph,
) -> Dict[int, StructuralAddress]:
    """给三点皮肤的每个 node_id 挂稳定地址（`DOMAIN_SKIN_PATCH` 域）。

    复用 P2-A0 已建立的 `register_physical()`（`register_skin_patch()`
    同一模式，本函数只是把它应用到 `ThermalFieldGraph` 节点而非
    `SkinThermalState`——`ThermalCell` 本身没有 `.address` 字段，映射
    保存在调用方持有的返回字典里，不修改 `ThermalCell` 本身）。幂等：
    重复调用对同一 node_id 返回同一地址。
    """
    return {
        node_id: registry.register_physical(DOMAIN_SKIN_PATCH, node_id)
        for node_id in graph.cells.keys()
    }
