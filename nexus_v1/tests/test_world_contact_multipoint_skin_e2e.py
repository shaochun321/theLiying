"""T-WQR2E-1/2：世界→接触→多点皮肤端到端可区分性（审查点2①，2026-07-28）。

方案依据：`cell-cell/交叉比对/document - 2026-07-28T170247.680.md`「审查点2应
集中收口四项」①"世界→接触→多点皮肤的端到端可区分性，补上审查点1遗留债务"。

背景（审查点1的原始裁定，`test_world_physical_qualification_review.py`
T-WQR-2/3）：两个世界节点各自独立通过 `ThermalContact` 连到**同一个共享**
`SkinThermalState`（`skin_patch_id=1`）——皮肤侧只感受两条接触边通量之和，
是纯标量求和，实测坐实"同总量不同分布"（Γ1 vs Γ2）与"同总量不同接触次序"
两类物理上不同的世界过程被压平成不可区分的皮肤轨迹（`relative_diff`
分别为 1.6e-16 / 0.0）。这被登记为"多点皮肤债务"：单点皮肤把多源组合
压平，若 P2-A 需要区分多源组合，必须升级到多点结构。

本轮缺口核实（Explore agent 侦察）：P2-A2/P2-A1b 已经证明"三点皮肤"
（`skin_three_point.py:build_three_point_skin()`，`ThermalFieldGraph` 的
`s1-s2-s3` 线性带）本身对位置/次序/单点-共同作用三类反例可区分
（T-STP-6/7/8），但这些测试**直接向皮肤图节点注入**，绕过了 World 和
`ThermalContact`——从未验证"World 的真实物理差异，经过 `ThermalContact`
的真实通量计算，能否传到多点皮肤侧仍保持可区分"这条完整链路。

结构选择（不修改任何母本代码，不新建物理机制）：`ThermalContact.flux()`
签名要求 `skin: SkinThermalState`（单点对象），与 `build_three_point_skin()`
返回的 `ThermalFieldGraph`（`ThermalCell` 集合）接口不兼容，桥接两者需要
修改 `ThermalContact` 本身或新增适配层——都不是"补债务"应有的最小改动。
`joint_thermal_step_plan.prepare_joint_thermal_step`/`apply_joint_thermal_step`
本身已经原生支持 `contacts: Sequence[ThermalContact]` + `skins_by_patch_id:
Dict[int, SkinThermalState]`（一对多的多接触/多皮肤路由，见该模块 Q2）——
债务的真正根源不是"皮肤只有一个点"，而是"两条接触边路由到了同一个
patch_id"。因此本轮的最小修复：**把 T-WQR-2/3 的路由从"多对一"（两条
contact 共享一个 skin patch）改为"一对一"（每条 contact 各自一个独立
patch）**，其余电路/机制完全复用不变，验证"给每个世界源各自一个独立
接收点"是否足以消解压平问题——这正是"多点皮肤"字面含义的最小结构实现，
且是对既有 `joint_thermal_step_plan`/`ThermalContact`/`SkinThermalState`
的直接复用（RULES.md"不修改母本代码添加功能"）。

RULES.md 强制三问：
  Q1 生物对应物：与 T-WQR-2/3 同一机制（Newton冷却接触，见
     `skin_thermal_contact.py` 模块文档），本文件不引入新机制，只改变
     既有接触边的路由拓扑（多对一→一对一），这是"感受野空间分辨率"这一
     熟知生理概念的直接结构对应——多点感受野优于单点感受野正是因为前者
     不把空间上不同的信号汇聚到同一个换能单元。
  Q2 物理结构：Sources=`ThermalFieldGraph`（世界，不改）+`ThermalContact`
     （不改，只是每条边分配不同的`skin_patch_id`）+`SkinThermalState`
     （不改，只是实例化N个而非1个）→Targets=`JointThermalStepPlan`（不改）。
     不新建任何 Neuron/SynapticBundle/物理机制类。
  Q3 参数依据：h/area/capacitance/世界初始charge 全部直接复用
     `test_world_physical_qualification_review.py` 已验证的数值（0.05/1.0/
     1.0/4.0,0.0/2.0,2.0 等），不新造任何参数。
"""

from __future__ import annotations

from nexus_v1.components.dynamic_thermal_field import ThermalCell, ThermalFieldGraph
from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.skin_thermal_contact import SkinThermalState, ThermalContact
from nexus_v1.components.thermal_source_coupling import DynamicHeatSource, ThermalFieldLocator
from nexus_v1.components.structural_address import AddressRegistry, DOMAIN_WORLD_CELL
from nexus_v1.components.joint_thermal_step_plan import (
    JointThermalRuntime, prepare_joint_thermal_step, apply_joint_thermal_step,
)


def _run_two_source_scenario_multipoint(pattern_a_power, pattern_b_power,
                                          total_time=2.0, dt=0.1):
    """T-WQR-2 场景的一对一路由版本：两个世界节点(0,1)各自通过独立接触边
    连到**各自独立**的皮肤补丁（skin_patch_id=0→patch0, 1→patch1），而不是
    共享同一个补丁。其余电路/参数与 `test_world_physical_qualification_
    review.py::_run_two_source_scenario` 完全一致（h=0.05, area=1.0,
    capacitance=1.0），只改路由拓扑。返回 `(skin_traj, world_traj)`，
    `skin_traj` 每步是 `(q_patch0, q_patch1)` 二元组（完整向量，不求和）。
    """
    cells = [ThermalCell(node_id=i, position=(float(i), 0, 0),
                          capacitor=Capacitor(capacitance=1.0)) for i in range(2)]
    graph = ThermalFieldGraph(cells=cells, links=[], r_leak_ambient=None)
    graph.cells[0].capacitor.charge = pattern_a_power
    graph.cells[1].capacitor.charge = pattern_b_power

    skin_0 = SkinThermalState(patch_id=0, capacitor=Capacitor(capacitance=1.0))
    skin_1 = SkinThermalState(patch_id=1, capacitor=Capacitor(capacitance=1.0))
    contact_0 = ThermalContact(world_node_id=0, skin_patch_id=0, h=0.05, area=1.0)
    contact_1 = ThermalContact(world_node_id=1, skin_patch_id=1, h=0.05, area=1.0)
    source = DynamicHeatSource(position=(0.0, 0, 0), energy_remaining=0.0, power=0.0)
    locator = ThermalFieldLocator(k=1)

    reg = AddressRegistry()
    reg.register_physical(DOMAIN_WORLD_CELL, 0)
    reg.register_physical(DOMAIN_WORLD_CELL, 1)
    runtime = JointThermalRuntime(world_graph=graph, registry=reg)

    skins_by_patch_id = {0: skin_0, 1: skin_1}
    skin_trajectory = []
    world_trajectory = []
    n_steps = round(total_time / dt)
    for _ in range(n_steps):
        plan = prepare_joint_thermal_step(
            runtime, [contact_0, contact_1], skins_by_patch_id, [], source, locator, dt=dt)
        apply_joint_thermal_step(runtime, plan, skins_by_patch_id, source)
        skin_trajectory.append((skin_0.capacitor.charge, skin_1.capacitor.charge))
        world_trajectory.append((graph.cells[0].capacitor.charge, graph.cells[1].capacitor.charge))
    return skin_trajectory, world_trajectory


def _vector_relative_diff(traj_1, traj_2):
    """两条向量轨迹的逐步逐分量最大相对差——复用 T-WQR-2/3 判据形式，
    只是把标量差换成向量分量的最大差。"""
    max_diff = max(
        max(abs(a_k - b_k) for a_k, b_k in zip(a, b))
        for a, b in zip(traj_1, traj_2)
    )
    max_signal = max(
        max(max(step) for step in traj_1), max(max(step) for step in traj_2), 1e-9)
    return max_diff / max_signal


def test_wqr2e_1_multipoint_skin_distinguishes_distribution():
    """T-WQR2E-1：一对一路由下，"同总量不同分布"（Γ1: node0=4.0,node1=0.0；
    Γ2: node0=2.0,node1=2.0，与 T-WQR-2 完全同一世界侧场景）经真实
    World→ThermalContact 链路后，皮肤侧完整向量 `[q_patch0,q_patch1]`
    应可区分——不再是 T-WQR-2 单点共享路由下的 relative_diff≈1.6e-16。
    """
    skin_traj_1, world_traj_1 = _run_two_source_scenario_multipoint(4.0, 0.0)
    skin_traj_2, world_traj_2 = _run_two_source_scenario_multipoint(2.0, 2.0)

    assert world_traj_1[0] != world_traj_2[0], "两个场景的世界侧初始状态应不同（构造前提，同T-WQR-2）"

    relative_diff = _vector_relative_diff(skin_traj_1, skin_traj_2)
    is_distinguishable = relative_diff > 1e-6

    global WQR2E1_DIAGNOSTIC
    WQR2E1_DIAGNOSTIC = {
        "relative_diff": relative_diff,
        "is_distinguishable": is_distinguishable,
        "skin_traj_1_final": skin_traj_1[-1],
        "skin_traj_2_final": skin_traj_2[-1],
    }
    assert is_distinguishable, (
        f"一对一路由下应可区分（relative_diff={relative_diff}），"
        f"若仍不可区分说明'多点皮肤'本身不足以消解压平债务，需要进一步调查"
    )


def test_wqr2e_2_multipoint_skin_distinguishes_temporal_order():
    """T-WQR2E-2：一对一路由下的"同峰值不同接触次序"（与 T-WQR-3 完全同一
    世界侧场景：两节点初始charge都是2.0，只交换h0/h1），验证一对一路由后
    皮肤侧向量能否区分"次序"这个维度——不再是 T-WQR-3 单点共享路由下的
    relative_diff=0.0。
    """
    def run_with_h_multipoint(h0, h1, total_time=1.0, dt=0.1):
        cells = [ThermalCell(node_id=i, position=(float(i), 0, 0),
                              capacitor=Capacitor(capacitance=1.0)) for i in range(2)]
        graph = ThermalFieldGraph(cells=cells, links=[], r_leak_ambient=None)
        graph.cells[0].capacitor.charge = 2.0
        graph.cells[1].capacitor.charge = 2.0
        skin_0 = SkinThermalState(patch_id=0, capacitor=Capacitor(capacitance=1.0))
        skin_1 = SkinThermalState(patch_id=1, capacitor=Capacitor(capacitance=1.0))
        contact_0 = ThermalContact(world_node_id=0, skin_patch_id=0, h=h0, area=1.0)
        contact_1 = ThermalContact(world_node_id=1, skin_patch_id=1, h=h1, area=1.0)
        source = DynamicHeatSource(position=(0.0, 0, 0), energy_remaining=0.0, power=0.0)
        locator = ThermalFieldLocator(k=1)
        reg = AddressRegistry()
        reg.register_physical(DOMAIN_WORLD_CELL, 0)
        reg.register_physical(DOMAIN_WORLD_CELL, 1)
        runtime = JointThermalRuntime(world_graph=graph, registry=reg)
        skins_by_patch_id = {0: skin_0, 1: skin_1}
        traj = []
        for _ in range(round(total_time / dt)):
            plan = prepare_joint_thermal_step(
                runtime, [contact_0, contact_1], skins_by_patch_id, [], source, locator, dt=dt)
            apply_joint_thermal_step(runtime, plan, skins_by_patch_id, source)
            traj.append((skin_0.capacitor.charge, skin_1.capacitor.charge))
        return traj

    traj_fast_slow = run_with_h_multipoint(0.08, 0.02)  # node0快, node1慢
    traj_slow_fast = run_with_h_multipoint(0.02, 0.08)  # node0慢, node1快

    relative_diff = _vector_relative_diff(traj_fast_slow, traj_slow_fast)
    is_distinguishable = relative_diff > 1e-6

    global WQR2E2_DIAGNOSTIC
    WQR2E2_DIAGNOSTIC = {
        "relative_diff": relative_diff,
        "is_distinguishable": is_distinguishable,
    }
    assert is_distinguishable, (
        f"一对一路由下次序应可区分（relative_diff={relative_diff}），"
        f"若仍不可区分说明对称路由本身（各自独立通道）无法编码次序信息，"
        f"需要进一步调查（次序信息可能需要时间戳/延迟线等额外结构，不在本轮范围）"
    )


if __name__ == "__main__":
    test_wqr2e_1_multipoint_skin_distinguishes_distribution()
    test_wqr2e_2_multipoint_skin_distinguishes_temporal_order()
    print("T-WQR2E-1/2 ALL PASS")
    print("T-WQR2E-1 diagnostic:", WQR2E1_DIAGNOSTIC)
    print("T-WQR2E-2 diagnostic:", WQR2E2_DIAGNOSTIC)
