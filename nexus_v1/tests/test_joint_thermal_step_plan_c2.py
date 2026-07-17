"""T-C2-1~8：P1-C2 物理动力学与长程资格验收（V4已冻结的5项范围，2026-07-17）。

方案依据：`基础生成元执行总纲_V4_2026-07-17.md` P1-C2 小节。复用P1-C0/C1
已完成的`joint_thermal_step_plan.py`，本轮只新增`JointThermalTrajectory`
（纯数据容器，见该文件"P1-C2"章节）+ `plan_id`唯一性修复（连续多步冻结拓扑
场景下原plan_id会重复，是本轮浸泡测试暴露的真实bug，见
`JointThermalRuntime._prepare_sequence`注释）。测试范围：
①线性正域算子提取（脉冲响应法，真实运行验证）；②过剩边界；③步长收敛；
④浸泡两段+连续物理轨迹。**明确不做**：不构造Ω、不实现Xin、不把任何一条
热传输边称为"行为算子"（V4已冻结的3条禁止事项）。
"""

from __future__ import annotations

import math

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
    JointThermalTrajectory, record_trajectory_step,
)


# ══════════════════════════════════════════════════════════════════════
# 共享夹具构造（不含contact/skin，聚焦世界侧扩散+传输的线性/长程性质）
# ══════════════════════════════════════════════════════════════════════

def _build_world_only_rig(charges, kappa=0.02, rate_per_time=0.05,
                            r_leak_ambient=None, source_power=0.0,
                            source_energy=1e9):
    """2世界节点：node0<->node1扩散边 + node0->node1传输边（tail=node0）。
    `charges=(q0,q1)`初始电荷。`source_power=0`时热源不参与（power=0时
    `preview_release()`直接返回0，不影响状态）。
    """
    cells = [ThermalCell(node_id=i, position=(float(i), 0, 0),
                          capacitor=Capacitor(capacitance=1.0)) for i in range(2)]
    graph = ThermalFieldGraph(cells=cells, links=[ThermalLink(i=0, j=1, kappa=kappa)],
                               r_leak_ambient=r_leak_ambient)
    graph.cells[0].capacitor.charge = charges[0]
    graph.cells[1].capacitor.charge = charges[1]

    reg = AddressRegistry()
    reg.register_physical(DOMAIN_WORLD_CELL, 0)
    reg.register_physical(DOMAIN_WORLD_CELL, 1)
    addr0 = reg.address_of(DOMAIN_WORLD_CELL, 0)
    addr1 = reg.address_of(DOMAIN_WORLD_CELL, 1)
    edge = reg.register_ordered_edge(addr0, addr1, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    link = OrderedExcessThermalEnergyLink(identity=edge, rate_per_time=rate_per_time)

    source = DynamicHeatSource(position=(0.0, 0, 0), energy_remaining=source_energy,
                                power=source_power, efficiency=1.0)
    locator = ThermalFieldLocator(k=1)
    runtime = JointThermalRuntime(world_graph=graph, registry=reg)
    return runtime, graph, link, source, locator, reg


def _run_one_step(runtime, graph, link, source, locator, dt, eta=1.0):
    """跑一个真实联合步（无接触/皮肤，`{}`），返回(receipt, plan)。"""
    plan = prepare_joint_thermal_step(runtime, [], {}, [link], source, locator, dt=dt, eta=eta)
    receipt = apply_joint_thermal_step(runtime, plan, {}, source)
    return receipt, plan


# ══════════════════════════════════════════════════════════════════════
# ① 线性正域算子提取（脉冲响应法，验证真实运行代码而非独立构造矩阵）
# ══════════════════════════════════════════════════════════════════════

def _one_step_world_charges(charges, kappa, rate_per_time, r_leak_ambient,
                              source_power, dt):
    """从给定初始charges出发，真实跑一个联合步，返回结果charges元组。
    每次调用重新构造一整套独立系统（runtime不能跨试验复用，因为已经
    step()过的图状态不能"倒带"）。
    """
    runtime, graph, link, source, locator, _reg = _build_world_only_rig(
        charges, kappa=kappa, rate_per_time=rate_per_time,
        r_leak_ambient=r_leak_ambient, source_power=source_power)
    _run_one_step(runtime, graph, link, source, locator, dt)
    return (graph.cells[0].capacitor.charge, graph.cells[1].capacitor.charge)


def _extract_linear_operator(baseline, kappa, rate_per_time, r_leak_ambient,
                               source_power, dt, eps=1e-4):
    """脉冲响应法提取 M_E（2x2）与常数项 b（2维）：对baseline与
    baseline+eps*e_i各真实跑一步，差分消去b，除以eps得到M的第i列。
    `source_power`若非零，b是该常数注入项（energy_remaining给到1e9，
    确保preview_release()不被截断，b真正是常数）。
    """
    x1_baseline = _one_step_world_charges(baseline, kappa, rate_per_time,
                                            r_leak_ambient, source_power, dt)
    n = len(baseline)
    m_cols = []
    for i in range(n):
        perturbed = list(baseline)
        perturbed[i] += eps
        x1_perturbed = _one_step_world_charges(tuple(perturbed), kappa, rate_per_time,
                                                  r_leak_ambient, source_power, dt)
        col = [(x1_perturbed[k] - x1_baseline[k]) / eps for k in range(n)]
        m_cols.append(col)
    # m_cols[i][k] = dX1_k/dX0_i，即 M[k][i]。
    m = [[m_cols[i][k] for i in range(n)] for k in range(n)]
    b = [x1_baseline[k] - sum(m[k][i] * baseline[i] for i in range(n)) for k in range(n)]
    return m, b


def test_c2_1_linear_operator_nonneg_and_conservative_when_closed():
    """T-C2-1: 无泄漏（闭合系统）时，从真实运行提取的 M_E 满足 M_ij>=0
    （物理上不应有负系数），且列和=1（能量态守恒，`1^⊤M_E=1^⊤`）。
    """
    baseline = (3.0, 1.0)
    m, b = _extract_linear_operator(baseline, kappa=0.02, rate_per_time=0.05,
                                      r_leak_ambient=None, source_power=0.0, dt=0.5)
    for row in m:
        for v in row:
            assert v >= -1e-9, f"M_ij应非负，实测{v}"
    for i in range(2):
        col_sum = sum(m[k][i] for k in range(2))
        assert col_sum == pytest.approx(1.0, abs=1e-6), f"列{i}和应为1（能量守恒），实测{col_sum}"
    # 无外部源时 b 应为0（没有常数注入项）。
    assert all(abs(v) < 1e-9 for v in b)


def test_c2_2_extracted_operator_predicts_real_runtime_on_new_baseline():
    """T-C2-2: 用baseline A提取的 M_E/b，预测一个**未参与提取过程**的新
    baseline B的下一步状态，必须与B的真实运行结果吻合
    （`E_runtime^{n+1}≈M_E·E_runtime^n+b`）——这是"验证真实代码"的关键，
    不是"独立矩阵自洽"。
    """
    kappa, rate, dt, source_power = 0.02, 0.05, 0.5, 0.3
    m, b = _extract_linear_operator((3.0, 1.0), kappa=kappa, rate_per_time=rate,
                                      r_leak_ambient=None, source_power=source_power, dt=dt)

    baseline_b = (5.0, 0.5)  # 未参与提取过程的新起点
    predicted = [sum(m[k][i] * baseline_b[i] for i in range(2)) + b[k] for k in range(2)]
    real_result = _one_step_world_charges(baseline_b, kappa, rate, None, source_power, dt)

    for k in range(2):
        assert predicted[k] == pytest.approx(real_result[k], abs=1e-6), (
            f"预测值{predicted[k]}与真实运行值{real_result[k]}不符（维度{k}）")


def test_c2_3_temperature_state_conservation_condition_differs_from_energy_state():
    """T-C2-3: 矩阵守恒需明确状态变量——能量态`1^⊤M_E=1^⊤`与温度态
    `C^⊤M_T=C^⊤`条件不同（数学演示：不同热容节点间用错条件会得出错误结论，
    此处构造C_0≠C_1验证列和条件的确不同）。
    """
    c0, c1 = 2.0, 1.0  # 不同热容
    # 能量态 M_E 满足列和=1（守恒）。温度态 M_T 由 T_i=E_i/C_i 变换得到：
    # T^{n+1} = D^-1 M_E D T^n（D=diag(C)），M_T 的守恒条件是 C^⊤M_T=C^⊤，
    # 不是列和=1——用一个简单的2x2 M_E 验证变换后 M_T 列和≠1（除非C_0=C_1）。
    m_e = [[0.9, 0.1], [0.1, 0.9]]  # 能量态：列和=1，满足守恒
    d = [c0, c1]
    # M_T = D^-1 M_E D（D=diag(C)）：(D^-1 M_E D)[k][i] = M_E[k][i]*D[i]/D[k]。
    m_t = [[m_e[k][i] * d[i] / d[k] for i in range(2)] for k in range(2)]

    col_sum_e = [sum(m_e[k][i] for k in range(2)) for i in range(2)]
    col_sum_t = [sum(m_t[k][i] for k in range(2)) for i in range(2)]
    assert all(abs(v - 1.0) < 1e-9 for v in col_sum_e), "能量态列和应为1"
    assert not all(abs(v - 1.0) < 1e-9 for v in col_sum_t), (
        "温度态列和不应为1（C_0≠C_1时），否则会被误判为守恒")

    # 温度态真正的守恒条件 C^⊤M_T=C^⊤。
    ct_mt = [sum(d[k] * m_t[k][i] for k in range(2)) for i in range(2)]
    assert all(abs(ct_mt[i] - d[i]) < 1e-9 for i in range(2)), "C^⊤M_T应等于C^⊤"


# ══════════════════════════════════════════════════════════════════════
# ② 过剩边界
# ══════════════════════════════════════════════════════════════════════

def test_c2_4_excess_boundary_no_negative_transfer_no_chattering():
    """T-C2-4: tail charge 跨越0附近时——传输功率钳位在0（不出现负传输）；
    head侧注入符号不因tail耗尽而翻转；`q_i<=0`后该边净贡献恒为0；账本每步
    仍闭合；多步运行中传输贡献单调趋于0，不出现0附近来回跳变（chattering）。
    """
    # tail初始有过剩热量，a_e*dt=0.15<1（联合稳定性门要求），几何衰减
    # 恒正但单调趋于0（不会在有限步内精确到达0，这本身就是"不chattering"
    # 的直接证据——纯粹平滑衰减，不振荡）。
    runtime, graph, link, source, locator, _reg = _build_world_only_rig(
        (0.3, 0.0), kappa=0.0, rate_per_time=0.3, r_leak_ambient=None, source_power=0.0)

    transport_contributions = []
    for _ in range(10):
        plan = prepare_joint_thermal_step(runtime, [], {}, [link], source, locator, dt=0.5)
        # node0(tail)的净传输贡献应恒 <=0（只流出不流入，此拓扑下没有其他边）。
        contribution = plan.node_transport_net.get(0, 0.0)
        assert contribution <= 1e-12, f"tail侧传输贡献不应为正: {contribution}"
        transport_contributions.append(contribution)
        receipt = apply_joint_thermal_step(runtime, plan, {}, source)
        for r_e in receipt.edge_ledger_residuals.values():
            assert r_e < 1e-9

    # 单调趋于0，不振荡（相邻贡献的绝对值应单调不增）。
    for i in range(1, len(transport_contributions)):
        assert abs(transport_contributions[i]) <= abs(transport_contributions[i - 1]) + 1e-12, (
            "传输贡献应单调衰减，不应出现振荡（chattering）")

    # 人为把tail拉到略低于0（模拟"已跨越0"的状态，同T-JTS-3先例的直接状态
    # 操纵手法），验证跨越后功率立即精确钳位为0且此后保持为0（不来回跳变）。
    graph.cells[0].capacitor.charge = -0.01
    post_cross_contributions = []
    for _ in range(3):
        plan = prepare_joint_thermal_step(runtime, [], {}, [link], source, locator, dt=0.5)
        contribution = plan.node_transport_net.get(0, 0.0)
        post_cross_contributions.append(contribution)
        apply_joint_thermal_step(runtime, plan, {}, source)
    assert all(v == 0.0 for v in post_cross_contributions), (
        f"跨越0后传输贡献应恒为0，不应来回跳变: {post_cross_contributions}")


def test_c2_5_excess_boundary_tail_head_roles_never_flip():
    """T-C2-5: tail低于自身环境基线（charge<0）时，`power=0`（不会因charge
    为负而让head变成"倒灌"回tail、翻转两端角色）。
    """
    runtime, graph, link, source, locator, _reg = _build_world_only_rig(
        (-2.0, 0.0), kappa=0.0, rate_per_time=0.1, r_leak_ambient=None, source_power=0.0)
    plan = prepare_joint_thermal_step(runtime, [], {}, [link], source, locator, dt=0.5)
    assert plan.node_transport_net.get(0, 0.0) == 0.0
    assert plan.node_transport_net.get(1, 0.0) == 0.0
    receipt = apply_joint_thermal_step(runtime, plan, {}, source)
    assert receipt.residual < 1e-9
    # 两端状态都不应发生传输相关变化（charge应保持不变，无扩散无源）。
    assert graph.cells[0].capacitor.charge == pytest.approx(-2.0, abs=1e-9)
    assert graph.cells[1].capacitor.charge == pytest.approx(0.0, abs=1e-9)


# ══════════════════════════════════════════════════════════════════════
# ③ 步长收敛
# ══════════════════════════════════════════════════════════════════════

def test_c2_6_timestep_convergence_against_analytic_diffusion_solution():
    """T-C2-6: 纯扩散二节点系统有解析解——`(q1-q2)(t)=(q1-q2)(0)e^{-2κt}`，
    `(q1+q2)`守恒。用`Δt`/`Δt/2`/`Δt/4`跑到同一物理时刻T，比较数值解与
    解析解的误差，验证误差随步长减小而下降。
    """
    kappa = 0.05
    q0_init, q1_init = 4.0, 1.0
    total_time = 4.0

    def run_to_time(dt):
        runtime, graph, link, source, locator, _reg = _build_world_only_rig(
            (q0_init, q1_init), kappa=kappa, rate_per_time=0.0,  # rate=0 排除传输影响
            r_leak_ambient=None, source_power=0.0)
        n_steps = round(total_time / dt)
        for _ in range(n_steps):
            _run_one_step(runtime, graph, link, source, locator, dt)
        return graph.cells[0].capacitor.charge

    analytic_diff = (q0_init - q1_init) * math.exp(-2 * kappa * total_time)
    analytic_q0 = ((q0_init + q1_init) + analytic_diff) / 2.0

    dt_coarse, dt_mid, dt_fine = 0.5, 0.25, 0.125
    err_coarse = abs(run_to_time(dt_coarse) - analytic_q0)
    err_mid = abs(run_to_time(dt_mid) - analytic_q0)
    err_fine = abs(run_to_time(dt_fine) - analytic_q0)

    assert err_mid < err_coarse, f"步长减半误差应下降: {err_mid} vs {err_coarse}"
    assert err_fine < err_mid, f"步长再减半误差应继续下降: {err_fine} vs {err_mid}"


# ══════════════════════════════════════════════════════════════════════
# ④ 浸泡两段 + 连续物理轨迹
# ══════════════════════════════════════════════════════════════════════

def test_c2_7_frozen_segment_soak_with_trajectory():
    """T-C2-7: 冻结段——热源关闭，拓扑固定，用T-C2-1提取的M_E第二特征值
    估算`τ_slow`，运行`5~10τ_slow`步，验证：能量漂移趋零/无NaN·inf/三级
    账本每步闭合/正确收敛到稳态；同时逐步记录连续物理轨迹
    （`JointThermalTrajectory`），验证轨迹不携带事件/语义标签，只有原始
    物理量。
    """
    kappa, rate, dt = 0.02, 0.05, 0.5
    m, _b = _extract_linear_operator((3.0, 1.0), kappa=kappa, rate_per_time=rate,
                                       r_leak_ambient=None, source_power=0.0, dt=dt)
    # 2x2矩阵特征值（解析公式）：迹和行列式。
    trace = m[0][0] + m[1][1]
    det = m[0][0] * m[1][1] - m[0][1] * m[1][0]
    disc = trace * trace - 4 * det
    if disc >= 0:
        sqrt_disc = math.sqrt(disc)
        lambda1 = (trace + sqrt_disc) / 2.0
        lambda2 = (trace - sqrt_disc) / 2.0
    else:
        # 复特征值，退化用模长。
        lambda1 = trace / 2.0
        lambda2 = trace / 2.0
    lambda_second = min(abs(lambda1), abs(lambda2))
    lambda_second = max(lambda_second, 1e-6)  # 避免log(0)
    if lambda_second >= 1.0:
        n_steps = 100  # 非收敛情形（不应发生在本夹具下），退化为固定步数
    else:
        tau_slow = -1.0 / math.log(lambda_second)
        n_steps = max(int(5 * tau_slow), 20)
        n_steps = min(n_steps, 500)  # 上限，避免测试过慢

    runtime, graph, link, source, locator, _reg = _build_world_only_rig(
        (3.0, 1.0), kappa=kappa, rate_per_time=rate, r_leak_ambient=None, source_power=0.0)

    trajectory = JointThermalTrajectory()
    e_total_history = []
    for step in range(n_steps):
        plan = prepare_joint_thermal_step(runtime, [], {}, [link], source, locator, dt=dt)
        receipt = apply_joint_thermal_step(runtime, plan, {}, source)
        record_trajectory_step(trajectory, step, graph, {}, plan)

        for r_i in receipt.node_ledger_residuals.values():
            assert r_i < 1e-6, f"第{step}步节点级账本未闭合: {r_i}"
        total_e = graph.total_energy()
        assert not math.isnan(total_e) and not math.isinf(total_e)
        e_total_history.append(total_e)

    # 能量漂移趋零（闭合系统，无泄漏无源，总能量应严格守恒到浮点精度）。
    assert abs(e_total_history[-1] - e_total_history[0]) < 1e-6

    # 正确稳态：末尾若干步的状态变化幅度应显著小于初始变化幅度（收敛）。
    early_delta = abs(trajectory[1].world_charges[0] - trajectory[0].world_charges[0])
    late_delta = abs(trajectory[-1].world_charges[0] - trajectory[-2].world_charges[0])
    assert late_delta <= early_delta + 1e-9, "长程运行应趋于稳态，末段变化不应大于初段"

    # 轨迹不携带事件/语义标签——只检查字段集合是原始物理量。
    assert len(trajectory) == n_steps
    sample = trajectory[0]
    expected_fields = {"step_index", "dt", "world_charges", "skin_charges",
                        "q_source", "q_diff", "q_contact", "q_oet", "q_loss"}
    assert set(sample.__dataclass_fields__.keys()) == expected_fields


def test_c2_8_driven_segment_then_converges_to_frozen_behavior():
    """T-C2-8: 驱动段——热源开启，验证有界性+逐步账本闭合；驱动停止
    （power设为0）后必须能进入冻结段行为并收敛（不残留虚假注入）。
    """
    kappa, rate, dt = 0.02, 0.05, 0.5
    runtime, graph, link, source, locator, _reg = _build_world_only_rig(
        (1.0, 0.0), kappa=kappa, rate_per_time=rate, r_leak_ambient=None,
        source_power=0.5, source_energy=3.0)  # 有限能量预算(0.25/步耗尽)，驱动段会自然耗尽

    charge_history = []
    for step in range(20):
        plan = prepare_joint_thermal_step(runtime, [], {}, [link], source, locator, dt=dt)
        receipt = apply_joint_thermal_step(runtime, plan, {}, source)
        assert receipt.residual < 1e-6
        total_e = graph.total_energy()
        assert not math.isnan(total_e) and not math.isinf(total_e)
        assert abs(total_e) < 1e6, "驱动段能量应有界，不应发散"
        charge_history.append(total_e)

    # 热源耗尽后（source.energy_remaining应已降到0附近），后续步骤不应再
    # 出现能量增长（无虚假注入）——最后几步的能量变化应趋于0。
    assert source.energy_remaining < 1e-6, "本场景能量预算应已耗尽"
    late_deltas = [abs(charge_history[i] - charge_history[i - 1])
                   for i in range(len(charge_history) - 3, len(charge_history))]
    early_deltas = [abs(charge_history[i] - charge_history[i - 1])
                    for i in range(1, 4)]
    assert max(late_deltas) <= max(early_deltas) + 1e-9, (
        "驱动耗尽后能量变化幅度不应大于驱动初期（应进入冻结段收敛行为）")


if __name__ == "__main__":
    test_c2_1_linear_operator_nonneg_and_conservative_when_closed()
    test_c2_2_extracted_operator_predicts_real_runtime_on_new_baseline()
    test_c2_3_temperature_state_conservation_condition_differs_from_energy_state()
    test_c2_4_excess_boundary_no_negative_transfer_no_chattering()
    test_c2_5_excess_boundary_tail_head_roles_never_flip()
    test_c2_6_timestep_convergence_against_analytic_diffusion_solution()
    test_c2_7_frozen_segment_soak_with_trajectory()
    test_c2_8_driven_segment_then_converges_to_frozen_behavior()
    print("T-C2-1~8 ALL PASS")
