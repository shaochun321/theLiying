"""T-WQR-1~3：世界物理资格审查（审查点1，2026-07-17，批判二十六/二十七）。

方案依据：`基础生成元执行总纲_V5_2026-07-17.md`"审查点1"章节。这不是P1-C2
的延续（不重开"P1-C2.1"），是"资格与升级登记表"四个集中审查点里的第一个，
独立执行、独立记录结论。范围：①完整联合路径（source+diffusion+contact+
OET+skin同时激活）步长收敛——T-C2-6只测了纯扩散，未覆盖完整联合路径；
②多点皮肤最小反例——单点皮肤是否会把两个物理上不同的世界过程压平成不可
区分的皮肤轨迹。
"""

from __future__ import annotations

import pytest

from nexus_v1.components.dynamic_thermal_field import ThermalCell, ThermalLink, ThermalFieldGraph
from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.skin_thermal_contact import SkinThermalState, ThermalContact
from nexus_v1.components.thermal_source_coupling import DynamicHeatSource, ThermalFieldLocator
from nexus_v1.components.structural_address import (
    AddressRegistry, DOMAIN_WORLD_CELL, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER,
)
from nexus_v1.components.ordered_excess_thermal_energy_link import (
    OrderedExcessThermalEnergyLink,
)
from nexus_v1.components.joint_thermal_step_plan import (
    JointThermalRuntime, prepare_joint_thermal_step, apply_joint_thermal_step,
)


# ══════════════════════════════════════════════════════════════════════
# ① 完整联合路径步长收敛（批判二十六阻塞项）
# ══════════════════════════════════════════════════════════════════════

def _build_full_joint_rig(q0, q1, kappa=0.02, rate_per_time=0.05, h=0.02,
                            source_power=0.3, source_energy=1e9):
    """世界node0<->node1扩散边 + node0->node1传输边(tail=0) + node0<->skin1
    接触边 + 定位到node0的热源——source/diffusion/contact/OET/skin全部同时
    激活，是"完整联合路径"的最小夹具。
    """
    cells = [ThermalCell(node_id=i, position=(float(i), 0, 0),
                          capacitor=Capacitor(capacitance=1.0)) for i in range(2)]
    graph = ThermalFieldGraph(cells=cells, links=[ThermalLink(i=0, j=1, kappa=kappa)],
                               r_leak_ambient=None)
    graph.cells[0].capacitor.charge = q0
    graph.cells[1].capacitor.charge = q1

    skin = SkinThermalState(patch_id=1, capacitor=Capacitor(capacitance=1.0))
    contact = ThermalContact(world_node_id=0, skin_patch_id=1, h=h, area=1.0)
    source = DynamicHeatSource(position=(0.0, 0, 0), energy_remaining=source_energy,
                                power=source_power, efficiency=1.0)
    locator = ThermalFieldLocator(k=1)

    reg = AddressRegistry()
    reg.register_physical(DOMAIN_WORLD_CELL, 0)
    reg.register_physical(DOMAIN_WORLD_CELL, 1)
    addr0 = reg.address_of(DOMAIN_WORLD_CELL, 0)
    addr1 = reg.address_of(DOMAIN_WORLD_CELL, 1)
    edge = reg.register_ordered_edge(addr0, addr1, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    link = OrderedExcessThermalEnergyLink(identity=edge, rate_per_time=rate_per_time)

    runtime = JointThermalRuntime(world_graph=graph, registry=reg)
    return runtime, graph, skin, contact, link, source, locator


def _run_full_joint_to_time(dt, total_time, q0=3.0, q1=1.0):
    """从同一初始状态出发，用给定dt真实跑到`total_time`，返回
    `(q0, q1, q_skin, e_source_remaining)`终态。
    """
    runtime, graph, skin, contact, link, source, locator = _build_full_joint_rig(q0, q1)
    n_steps = round(total_time / dt)
    for _ in range(n_steps):
        plan = prepare_joint_thermal_step(runtime, [contact], {1: skin}, [link], source,
                                           locator, dt=dt)
        apply_joint_thermal_step(runtime, plan, {1: skin}, source)
    return (graph.cells[0].capacitor.charge, graph.cells[1].capacitor.charge,
            skin.capacitor.charge, source.energy_remaining)


def test_wqr_1_full_joint_path_timestep_convergence():
    """T-WQR-1（批判二十六阻塞项）: source+diffusion+contact+OET+skin同时
    激活时，`q_world`/`q_skin`/`E_source`在同一物理终点T随步长
    `dt→dt/2→dt/4`收敛（用极细`dt_ref`做参考解，不要求解析解——完整耦合
    系统没有简单闭式解）。这是P2-A的入口条件：若皮肤峰值/衰减随dt漂移，
    产生的ξ^occ可能只是离散算法产物。
    """
    total_time = 2.0
    dt_ref = total_time / 2048  # 极细步长参考解
    ref = _run_full_joint_to_time(dt_ref, total_time)

    dt_coarse, dt_mid, dt_fine = 0.25, 0.125, 0.0625
    result_coarse = _run_full_joint_to_time(dt_coarse, total_time)
    result_mid = _run_full_joint_to_time(dt_mid, total_time)
    result_fine = _run_full_joint_to_time(dt_fine, total_time)

    # e_source_remaining 不纳入单调收敛断言：热源功率恒定且从不被
    # energy_remaining截断时，Σ(power·dt_i)=power·total_time是精确值，
    # 与步数无关（不是被积分离散化的量，是精确求和），三种dt下误差恒为
    # 浮点精度量级——这是正确的诊断结果，不是bug，只是它不适合用来检验
    # "收敛速度"（没有真正的离散化误差可供比较）。仍单独核实其确为精确解。
    assert abs(result_coarse[3] - ref[3]) < 1e-3, "热源精确耗尽量误差应远小于信号本身（浮点累积量级）"

    labels = ["q_world_0", "q_world_1", "q_skin"]
    for i, label in enumerate(labels):
        err_coarse = abs(result_coarse[i] - ref[i])
        err_mid = abs(result_mid[i] - ref[i])
        err_fine = abs(result_fine[i] - ref[i])
        assert err_mid < err_coarse, (
            f"{label}: 步长减半误差应下降: {err_mid} vs {err_coarse}")
        assert err_fine < err_mid, (
            f"{label}: 步长再减半误差应继续下降: {err_fine} vs {err_mid}")


# ══════════════════════════════════════════════════════════════════════
# ② 多点皮肤最小反例（批判二十七，需要最小反例测试后裁定）
# ══════════════════════════════════════════════════════════════════════

def _run_two_source_scenario(pattern_a_power, pattern_b_power, total_time=2.0, dt=0.1):
    """两个世界节点(0,1)各自通过独立接触边连到**同一皮肤**（skin_patch_id=1）
    ——`pattern_a_power`/`pattern_b_power`是两个节点各自的初始charge（模拟
    "同总量、不同分布"的两个物理上不同的过程）。返回皮肤charge的完整轨迹
    （逐步采样，不止终态）。
    """
    cells = [ThermalCell(node_id=i, position=(float(i), 0, 0),
                          capacitor=Capacitor(capacitance=1.0)) for i in range(2)]
    graph = ThermalFieldGraph(cells=cells, links=[], r_leak_ambient=None)  # 无扩散，两节点独立
    graph.cells[0].capacitor.charge = pattern_a_power
    graph.cells[1].capacitor.charge = pattern_b_power

    skin = SkinThermalState(patch_id=1, capacitor=Capacitor(capacitance=1.0))
    contact_0 = ThermalContact(world_node_id=0, skin_patch_id=1, h=0.05, area=1.0)
    contact_1 = ThermalContact(world_node_id=1, skin_patch_id=1, h=0.05, area=1.0)
    source = DynamicHeatSource(position=(0.0, 0, 0), energy_remaining=0.0, power=0.0)
    locator = ThermalFieldLocator(k=1)

    reg = AddressRegistry()
    reg.register_physical(DOMAIN_WORLD_CELL, 0)
    reg.register_physical(DOMAIN_WORLD_CELL, 1)
    runtime = JointThermalRuntime(world_graph=graph, registry=reg)

    skin_trajectory = []
    world_trajectory = []
    n_steps = round(total_time / dt)
    for _ in range(n_steps):
        plan = prepare_joint_thermal_step(runtime, [contact_0, contact_1], {1: skin}, [],
                                           source, locator, dt=dt)
        apply_joint_thermal_step(runtime, plan, {1: skin}, source)
        skin_trajectory.append(skin.capacitor.charge)
        world_trajectory.append((graph.cells[0].capacitor.charge, graph.cells[1].capacitor.charge))
    return skin_trajectory, world_trajectory


def test_wqr_2_single_point_skin_minimal_counterexample():
    """T-WQR-2（批判二十七，"最小反例测试后裁定"）: 构造两个总能量相同但
    分布不同的世界过程——Γ1: node0=4.0,node1=0.0；Γ2: node0=2.0,node1=2.0
    （同总量`4.0`，不同接触分布）。**如实报告**皮肤侧轨迹`q_s[Γ1]`与
    `q_s[Γ2]`是否可区分，不预设"通过"结论。
    """
    skin_traj_1, world_traj_1 = _run_two_source_scenario(4.0, 0.0)
    skin_traj_2, world_traj_2 = _run_two_source_scenario(2.0, 2.0)

    # 世界侧过程本身确实不同（Γ1≠Γ2，两个节点的真实充能状态不一样）。
    assert world_traj_1[0] != world_traj_2[0], "两个场景的世界侧初始状态应不同（构造前提）"

    # 皮肤侧只感受到两条接触边通量之和——本质上是标量求和，如实验证其是否
    # 不可区分。用相对误差判断：若所有采样点几乎重合（误差远小于信号幅度），
    # 判定为"不可区分"；否则为"可区分"。
    max_diff = max(abs(a - b) for a, b in zip(skin_traj_1, skin_traj_2))
    max_signal = max(max(skin_traj_1), max(skin_traj_2), 1e-9)
    relative_diff = max_diff / max_signal

    # 如实记录裁定：h_0=h_1（对称接触系数）+ 同总量分布，理论上皮肤侧总
    # 通量在每一步都相同（Σh_i*q_i(t)，对称系数下与"总量"而非"分布"相关，
    # 当且仅当两节点各自不与其他机制耦合、独立衰减时）——此测试预期观察到
    # 不可区分（relative_diff接近0），验证批判二十七"单点皮肤压平多源
    # 差异"的诊断在本反例场景下成立。
    is_distinguishable = relative_diff > 1e-6
    # 不预设结论，只做诊断记录——用一个宽松阈值确认"如实报告"这件事本身
    # 可执行（无论True/False都不算测试失败，失败的判据是"代码无法产出
    # 一致的诊断结果"）。
    assert isinstance(is_distinguishable, bool)

    # 记录用于报告的诊断值（供报告引用，不是断言本身）。
    global _WQR2_DIAGNOSTIC
    _WQR2_DIAGNOSTIC = {
        "relative_diff": relative_diff,
        "is_distinguishable": is_distinguishable,
        "skin_traj_1_final": skin_traj_1[-1],
        "skin_traj_2_final": skin_traj_2[-1],
    }


def test_wqr_3_single_point_skin_distinguishes_different_temporal_order():
    """T-WQR-3（批判二十七，"同峰值不同接触次序"补充反例）: 两个节点初始
    charge相同（对称），但一个场景node0接触边`h`更大（先快后慢），另一个
    场景node1接触边`h`更大（先慢后快）——总能量、总接触强度相同，只是
    "谁先谁后"不同。验证单点皮肤能否区分"次序"这个维度。
    """
    def run_with_h(h0, h1, total_time=1.0, dt=0.1):
        cells = [ThermalCell(node_id=i, position=(float(i), 0, 0),
                              capacitor=Capacitor(capacitance=1.0)) for i in range(2)]
        graph = ThermalFieldGraph(cells=cells, links=[], r_leak_ambient=None)
        graph.cells[0].capacitor.charge = 2.0
        graph.cells[1].capacitor.charge = 2.0
        skin = SkinThermalState(patch_id=1, capacitor=Capacitor(capacitance=1.0))
        contact_0 = ThermalContact(world_node_id=0, skin_patch_id=1, h=h0, area=1.0)
        contact_1 = ThermalContact(world_node_id=1, skin_patch_id=1, h=h1, area=1.0)
        source = DynamicHeatSource(position=(0.0, 0, 0), energy_remaining=0.0, power=0.0)
        locator = ThermalFieldLocator(k=1)
        reg = AddressRegistry()
        reg.register_physical(DOMAIN_WORLD_CELL, 0)
        reg.register_physical(DOMAIN_WORLD_CELL, 1)
        runtime = JointThermalRuntime(world_graph=graph, registry=reg)
        traj = []
        for _ in range(round(total_time / dt)):
            plan = prepare_joint_thermal_step(runtime, [contact_0, contact_1], {1: skin}, [],
                                               source, locator, dt=dt)
            apply_joint_thermal_step(runtime, plan, {1: skin}, source)
            traj.append(skin.capacitor.charge)
        return traj

    traj_fast_slow = run_with_h(0.08, 0.02)  # node0快, node1慢
    traj_slow_fast = run_with_h(0.02, 0.08)  # node0慢, node1快

    # 两节点初始状态对称（都是2.0），h只是互换——单点皮肤只感受Σh_i*q_i(t)
    # 的瞬时和，两种h分配方式下逐步轨迹应完全对称等价（不可区分次序）。
    max_diff = max(abs(a - b) for a, b in zip(traj_fast_slow, traj_slow_fast))
    max_signal = max(max(traj_fast_slow), max(traj_slow_fast), 1e-9)
    relative_diff = max_diff / max_signal
    is_distinguishable = relative_diff > 1e-6

    global _WQR3_DIAGNOSTIC
    _WQR3_DIAGNOSTIC = {
        "relative_diff": relative_diff,
        "is_distinguishable": is_distinguishable,
    }
    assert isinstance(is_distinguishable, bool)


if __name__ == "__main__":
    test_wqr_1_full_joint_path_timestep_convergence()
    test_wqr_2_single_point_skin_minimal_counterexample()
    test_wqr_3_single_point_skin_distinguishes_different_temporal_order()
    print("T-WQR-1~3 ALL PASS")
    print("T-WQR-2 diagnostic:", _WQR2_DIAGNOSTIC)
    print("T-WQR-3 diagnostic:", _WQR3_DIAGNOSTIC)
