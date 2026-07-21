"""T-STP-1~5：P2-A2 三点动态皮肤独立物理资格验收。

方案依据：`cell-cell/交叉比对/评判_P2A1顺序倒置修正_2026-07-21.md`——
P2-A2 只建立 `s1-s2-s3` 并测量真实 `q_i^skin(t)`，不涉及生成元/κ/皮肤
映射。验收方法论复刻 `test_dynamic_thermal_field.py` 的 T-DTF-2/3/4/5
（真实锚定验稳定性/守恒，测试尺度验扩散机制方向性），双轨分工同理不
重复推导。

T-STP-3 是本轮"独立物理资格"的核心判据：持续向 s1 注热，验证 s3（最远端）
以延迟且衰减的方式响应，s2 响应介于两者之间——这正是最初方案（`document
- 2026-07-20T203329.284.md`）对三点皮肤提出的最低要求："刺激一个位置时，
另外两个位置能以不同延迟和幅度受到影响"。
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
