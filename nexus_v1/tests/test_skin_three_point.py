"""T-STP-1~8：P2-A2 三点动态皮肤独立物理资格 + 过程可区分资格验收。

方案依据：`cell-cell/交叉比对/评判_P2A1顺序倒置修正_2026-07-21.md`——
P2-A2 只建立 `s1-s2-s3` 并测量真实 `q_i^skin(t)`，不涉及生成元/κ/皮肤
映射。验收方法论复刻 `test_dynamic_thermal_field.py` 的 T-DTF-2/3/4/5
（真实锚定验稳定性/守恒，测试尺度验扩散机制方向性），双轨分工同理不
重复推导。

T-STP-3 是"结构与传播资格"的核心判据：持续向 s1 注热，验证 s3（最远端）
以延迟且衰减的方式响应，s2 响应介于两者之间——这正是最初方案（`document
- 2026-07-20T203329.284.md`）对三点皮肤提出的最低要求："刺激一个位置时，
另外两个位置能以不同延迟和幅度受到影响"。

T-STP-6~8 是评判（`document - 2026-07-21T133444.403.md`）指出的**唯一
阻塞**补件——"过程可区分资格"：T-STP-3 只证明了传播/延迟/衰减，从未
证明三点皮肤真正解决了 P2-A2 建设的原始理由（审查点1 T-WQR-2/3 反例
坐实"不同世界过程被单点皮肤压平成不可区分轨迹"这一债务）。T-STP-6/7/8
分别验证位置反例、次序反例、单点vs共同作用反例——比较对象是完整向量
`[q0,q1,q2]`，不汇总成单一总量。
"""

from __future__ import annotations

from nexus_v1.components.dynamic_thermal_field import diffusion_number, is_stable
from nexus_v1.components.skin_three_point import (
    TEST_KAPPA_THREE_POINT, TEST_R_LEAK_AMBIENT_THREE_POINT,
    build_three_point_skin, register_skin_cells,
)
from nexus_v1.components.structural_address import AddressRegistry, DOMAIN_SKIN_PATCH

DT = 1.0


# ─────────────────────────────────────────────────────────────
# T-STP-1：数值稳定——真实锚定 kappa 下长程运行无 NaN/无发散
# ─────────────────────────────────────────────────────────────
def test_numerical_stability_real_anchored():
    graph = build_three_point_skin()  # 默认真实锚定 NORMALIZED_KAPPA_DEFAULT
    for step in range(2000):
        injections = {0: 1.0} if step < 500 else {}
        graph.step(dt=DT, external_injections=injections)

    for cell in graph.cells.values():
        t = cell.temperature
        assert t == t, "T-STP-1 FAIL: 温度出现 NaN"
        assert abs(t) < 1e6, f"T-STP-1 FAIL: 温度发散 T={t}"


# ─────────────────────────────────────────────────────────────
# T-STP-2：能量守恒——真实锚定下 conservation_residual ≈ 0
# ─────────────────────────────────────────────────────────────
def test_energy_conservation_real_anchored():
    graph = build_three_point_skin()
    for step in range(500):
        injections = {0: 2.0, 2: -0.3} if step % 3 == 0 else {}
        graph.step(dt=DT, external_injections=injections)

    residual = graph.conservation_residual()
    assert residual < 1e-6, f"T-STP-2 FAIL: 能量守恒残差过大 residual={residual}"

    max_kcl = max(c.kcl_imbalance for c in graph.cells.values())
    assert max_kcl < 1e-6, f"T-STP-2 FAIL: 单节点 KCL 不闭合 max={max_kcl}"


# ─────────────────────────────────────────────────────────────
# T-STP-3：独立物理资格核心判据——刺激 s1，s3 延迟且衰减响应，s2 居中
# ─────────────────────────────────────────────────────────────
def test_stimulate_s1_propagates_with_delay_and_attenuation_to_s3():
    graph = build_three_point_skin(
        kappa=TEST_KAPPA_THREE_POINT,
        r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT,
    )

    early_window = 20   # 早期：热量刚开始扩散，s3 应尚未显著响应
    late_window = 300   # 晚期：s1/s2/s3 应已按距离形成衰减梯度

    for step in range(early_window):
        graph.step(dt=DT, external_injections={0: 1.0})
    t_s1_early = graph.cells[0].temperature
    t_s3_early = graph.cells[2].temperature

    for step in range(late_window - early_window):
        graph.step(dt=DT, external_injections={0: 1.0})
    t_s1_late = graph.cells[0].temperature
    t_s2_late = graph.cells[1].temperature
    t_s3_late = graph.cells[2].temperature

    # 延迟：早期 s3 响应应远小于 s1（尚未传导过去）。
    assert t_s3_early < t_s1_early * 0.5, (
        f"T-STP-3 FAIL: s3 早期响应({t_s3_early:.4g})未明显滞后于 "
        f"s1({t_s1_early:.4g})，说明扩散延迟未体现"
    )
    # 衰减：晚期梯度 s1 > s2 > s3（持续注入下，最近端仍应最高）。
    assert t_s1_late > t_s2_late > t_s3_late, (
        f"T-STP-3 FAIL: 晚期梯度应满足 s1>s2>s3，实际="
        f"{t_s1_late:.4g}/{t_s2_late:.4g}/{t_s3_late:.4g}"
    )
    # s3 确实随时间产生了非零响应（不是完全隔绝）。
    assert t_s3_late > t_s3_early, (
        f"T-STP-3 FAIL: s3 温度未随时间上升，说明皮肤内部没有实际耦合"
    )


# ─────────────────────────────────────────────────────────────
# T-STP-4：稳定性诊断——测试尺度 kappa 下 is_stable()/diffusion_number()
# ─────────────────────────────────────────────────────────────
def test_stability_diagnostics_report_correctly():
    graph = build_three_point_skin(
        kappa=TEST_KAPPA_THREE_POINT,
        r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT,
    )
    assert is_stable(graph, dt=DT), "T-STP-4 FAIL: 测试尺度参数下应报告稳定"
    numbers = diffusion_number(graph, dt=DT)
    assert all(v <= 1.0 for v in numbers.values()), (
        f"T-STP-4 FAIL: diffusion_number 应全部 <=1（稳定），实际={numbers}"
    )

    # 明显不稳定的参数（kappa 远超合理范围）应能被诊断正确识别（不隐式兜底）。
    unstable_graph = build_three_point_skin(kappa=1000.0, r_leak_ambient=None)
    assert not is_stable(unstable_graph, dt=DT), (
        "T-STP-4 FAIL: 极端 kappa 下 is_stable() 应报告不稳定"
    )


# ─────────────────────────────────────────────────────────────
# T-STP-5：地址挂载——3 个 node_id 挂 DOMAIN_SKIN_PATCH，幂等，互不相同
# ─────────────────────────────────────────────────────────────
def test_address_registration_stable_and_distinct():
    graph = build_three_point_skin()
    registry = AddressRegistry()

    addresses = register_skin_cells(registry, graph)
    assert len(addresses) == 3
    for node_id, addr in addresses.items():
        assert addr.domain == DOMAIN_SKIN_PATCH
        assert addr.uid == f"{DOMAIN_SKIN_PATCH}:{node_id}"

    uids = {addr.uid for addr in addresses.values()}
    assert len(uids) == 3, "T-STP-5 FAIL: 三个节点的地址 uid 应互不相同"

    # 幂等：重复注册返回同一地址。
    addresses_again = register_skin_cells(registry, graph)
    for node_id in addresses:
        assert addresses_again[node_id].uid == addresses[node_id].uid
        assert addresses_again[node_id].version == addresses[node_id].version


def _q_vector(graph):
    """完整状态向量 [T(s1),T(s2),T(s3)]——比较对象必须是这个，不能汇总
    成单一总量（否则无法区分"传播了多少"与"过程本身是否可区分"）。"""
    return [graph.cells[i].temperature for i in range(3)]


def _vectors_distinguishable(q_x, q_y, tol=1e-6):
    return any(abs(a - b) >= tol for a, b in zip(q_x, q_y))


# ─────────────────────────────────────────────────────────────
# T-STP-6：位置反例——Γ_A(仅刺激s1) vs Γ_B(仅刺激s3) 应产生不同轨迹
# ─────────────────────────────────────────────────────────────
def test_position_reversal_produces_distinguishable_trajectories():
    steps = 150
    graph_a = build_three_point_skin(
        kappa=TEST_KAPPA_THREE_POINT, r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)
    graph_b = build_three_point_skin(
        kappa=TEST_KAPPA_THREE_POINT, r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)

    for _ in range(steps):
        graph_a.step(dt=DT, external_injections={0: 1.0})  # Γ_A：仅刺激 s1
    for _ in range(steps):
        graph_b.step(dt=DT, external_injections={2: 1.0})  # Γ_B：仅刺激 s3（相同电流/时长）

    q_a, q_b = _q_vector(graph_a), _q_vector(graph_b)

    assert _vectors_distinguishable(q_a, q_b), (
        f"T-STP-6 FAIL: 位置反例应产生不同轨迹，实际 q_A={q_a} q_B={q_b} 几乎相等"
    )
    # 镜像对称核实：线性链在 0↔2 节点交换下对称，q_B 应约等于 reverse(q_A)——
    # 这既确认了差异的真实来源（结构镜像对称，非数值噪声），也是对
    # ThermalFieldGraph 本身"方向从结构涌现"的间接复核。
    assert abs(q_a[0] - q_b[2]) < 1e-9 and abs(q_a[2] - q_b[0]) < 1e-9, (
        f"T-STP-6 FAIL: q_B 应是 q_A 的镜像，实际 q_A={q_a} q_B={q_b}"
    )


# ─────────────────────────────────────────────────────────────
# T-STP-7：次序反例——Γ_C(s1先s3后) vs Γ_D(s3先s1后) 应产生不同轨迹
# ─────────────────────────────────────────────────────────────
def test_temporal_order_reversal_produces_distinguishable_trajectories():
    m = 150  # 每阶段步数
    graph_c = build_three_point_skin(
        kappa=TEST_KAPPA_THREE_POINT, r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)
    graph_d = build_three_point_skin(
        kappa=TEST_KAPPA_THREE_POINT, r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)

    # Γ_C：前 m 步刺激 s1，后 m 步刺激 s3。
    for _ in range(m):
        graph_c.step(dt=DT, external_injections={0: 1.0})
    for _ in range(m):
        graph_c.step(dt=DT, external_injections={2: 1.0})

    # Γ_D：前 m 步刺激 s3，后 m 步刺激 s1（总注入能量/时长与 Γ_C 相同，仅次序相反）。
    for _ in range(m):
        graph_d.step(dt=DT, external_injections={2: 1.0})
    for _ in range(m):
        graph_d.step(dt=DT, external_injections={0: 1.0})

    # 必须在第2阶段刚结束的时刻比较（不能等弛豫到平衡态——线性时不变系统
    # 若继续弛豫到纯环境基线，注入次序造成的差异会被抹平，必须在有限
    # 时刻比较才能体现"次序依赖"这个因果结构）。
    q_c, q_d = _q_vector(graph_c), _q_vector(graph_d)

    assert _vectors_distinguishable(q_c, q_d), (
        f"T-STP-7 FAIL: 次序反例应产生不同轨迹，实际 q_C={q_c} q_D={q_d} 几乎相等"
    )


# ─────────────────────────────────────────────────────────────
# T-STP-8：单点与共同作用反例——Γ_E(仅刺激s2) vs Γ_F(同时刺激s1,s3，
# 总量相同) 应产生不同轨迹
# ─────────────────────────────────────────────────────────────
def test_single_center_vs_combined_edges_produces_distinguishable_trajectories():
    steps = 150
    graph_e = build_three_point_skin(
        kappa=TEST_KAPPA_THREE_POINT, r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)
    graph_f = build_three_point_skin(
        kappa=TEST_KAPPA_THREE_POINT, r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)

    for _ in range(steps):
        graph_e.step(dt=DT, external_injections={1: 1.0})  # Γ_E：仅刺激 s2（中心），电流1.0
    for _ in range(steps):
        # Γ_F：同时刺激 s1、s3（两端），各注入0.5——总量与 Γ_E 相同。
        graph_f.step(dt=DT, external_injections={0: 0.5, 2: 0.5})

    q_e, q_f = _q_vector(graph_e), _q_vector(graph_f)

    assert _vectors_distinguishable(q_e, q_f), (
        f"T-STP-8 FAIL: 单点(中心)与共同作用(两端)应产生不同轨迹，"
        f"实际 q_E={q_e} q_F={q_f} 几乎相等"
    )
