"""P2-A1b-3 阶段四：验证过程差异未被接口压平（接线验收）。

TYPE:INFRA — 验证`skin_transduction.transduce()`+`BaseGenerator.
tick_from_skin()`这条完整链路（皮肤→转导→生成元）是否仍然保留了
T-STP-6/7/8 已验证的"三点皮肤内部过程可区分"这一资格——评判
(`document - 2026-07-21T161711.318.md`「P2-A1b-3只做四件事」④)明确
最低判据：比较的是转导后**生成元轨迹或发生边界**（`closure.events`），
不是只确认转导函数输出了不同浮点数。

生成元固定挂在 node0（s1）位置（与`REFERENCE_TRANSDUCTION_CONFIG`的
标定数据来源一致），驱动方式复用T-STP-6/7/8同款场景定义，观测预算复用
P2-A1b-3阶段三标定实验(`exp_P2A1b_3_closure_calibration.py`)已验证的
代表性规模（900驱动+3000撤去观测，见该脚本"标定策略"）——不重新猜一个
新窗口，两个实验窗口长度保持一致以便互相印证。

三对场景（评判"不必穷尽"，只要求至少验证位置/次序/单点-共同作用各一对）：
  Γ_A(直接刺激s1) vs Γ_B(刺激s3，经传播间接到达s1) —— 位置
  Γ_C(先s1后s3) vs Γ_D(先s3后s1) —— 次序
  Γ_E(仅刺激s2中心) vs Γ_F(同时刺激s1+s3两端) —— 单点与共同作用
"""
import sys

sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.structural_address import AddressRegistry
from nexus_v1.components.skin_three_point import (
    TEST_KAPPA_THREE_POINT, TEST_R_LEAK_AMBIENT_THREE_POINT,
    build_three_point_skin,
)
from tss.generators import wrap_base_generator, REFERENCE_TRANSDUCTION_CONFIG
from tss.relations import FROZEN_THERMAL_SITES

DT = 0.001
SITE_INDEX = FROZEN_THERMAL_SITES["t1_pair"]["a"]
CONFIG = REFERENCE_TRANSDUCTION_CONFIG

# 与 exp_P2A1b_3_closure_calibration.py 的代表性预算一致（见该脚本
# "标定策略"），两处窗口长度刻意保持相同以便互相印证。
DRIVE_STEPS = 900
DECAY_STEPS = 3000
OBSERVE_NODE = 0  # 生成元固定挂在node0（s1），与REFERENCE_TRANSDUCTION_CONFIG标定来源一致


def _fresh_pair():
    circuit = VariantCircuit()
    registry = AddressRegistry()
    handle = wrap_base_generator(circuit, SITE_INDEX, registry, polarity="warm")
    graph = build_three_point_skin(
        kappa=TEST_KAPPA_THREE_POINT, r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)
    return handle, graph


def _run_scenario(injection_schedule):
    """injection_schedule: 长度为 DRIVE_STEPS 的列表，每步一个
    external_injections 字典（如 {0: 1.0}），驱动完 DRIVE_STEPS 步后
    撤去注入观测 DECAY_STEPS 步。返回驱动后的 handle（供读取
    closure.events）。"""
    handle, graph = _fresh_pair()
    t = 0
    for injections in injection_schedule:
        graph.step(dt=1.0, external_injections=injections)
        q = graph.cells[OBSERVE_NODE].temperature
        handle.tick_from_skin(q, CONFIG, DT, t)
        t += 1
    for _ in range(DECAY_STEPS):
        graph.step(dt=1.0, external_injections={})
        q = graph.cells[OBSERVE_NODE].temperature
        handle.tick_from_skin(q, CONFIG, DT, t)
        t += 1
    return handle


def _occurrence_summary(handle):
    events = handle.closure.events
    return {
        "occurrence_count": len(events),
        "l_first": events[0].t_up if events else None,
        "durations": tuple(e.t_down - e.t_up for e in events),
    }


def _distinguishable(summary_a, summary_b):
    """至少一项（occurrence_count/l_first/durations）不同即视为可区分
    ——评判明确的最低判据，比较发生记录而非转导函数的浮点数输出。"""
    return (
        summary_a["occurrence_count"] != summary_b["occurrence_count"]
        or summary_a["l_first"] != summary_b["l_first"]
        or summary_a["durations"] != summary_b["durations"]
    )


def test_position_difference_preserved_through_interface():
    """Γ_A(直接刺激s1=观测节点) vs Γ_B(刺激s3，须经传播间接到达观测节点)
    ——转导+生成元接线后，观测节点(s1)的发生记录应仍能区分"我被直接
    刺激"与"远端被刺激、信号传播过来"这两种不同的世界过程。"""
    schedule_a = [{0: 1.0}] * DRIVE_STEPS  # Γ_A：直接刺激观测节点本身
    schedule_b = [{2: 1.0}] * DRIVE_STEPS  # Γ_B：刺激远端节点

    handle_a = _run_scenario(schedule_a)
    handle_b = _run_scenario(schedule_b)
    sum_a = _occurrence_summary(handle_a)
    sum_b = _occurrence_summary(handle_b)

    print(f"Gamma_A(位置-直接): {sum_a}")
    print(f"Gamma_B(位置-间接): {sum_b}")
    assert _distinguishable(sum_a, sum_b), (
        f"位置差异应在生成元发生记录中保留可区分性，实际 A={sum_a} B={sum_b}")


def test_temporal_order_difference_preserved_through_interface():
    """Γ_C(前半程刺激s1观测节点本身、后半程刺激s3) vs
    Γ_D(前半程刺激s3、后半程刺激s1观测节点本身)——次序差异应在观测节点
    的发生记录里保留可区分性。"""
    m = DRIVE_STEPS // 2
    schedule_c = [{0: 1.0}] * m + [{2: 1.0}] * (DRIVE_STEPS - m)
    schedule_d = [{2: 1.0}] * m + [{0: 1.0}] * (DRIVE_STEPS - m)

    handle_c = _run_scenario(schedule_c)
    handle_d = _run_scenario(schedule_d)
    sum_c = _occurrence_summary(handle_c)
    sum_d = _occurrence_summary(handle_d)

    print(f"Gamma_C(次序-先直接后间接): {sum_c}")
    print(f"Gamma_D(次序-先间接后直接): {sum_d}")
    assert _distinguishable(sum_c, sum_d), (
        f"次序差异应在生成元发生记录中保留可区分性，实际 C={sum_c} D={sum_d}")


def test_single_vs_combined_difference_preserved_through_interface():
    """Γ_E(仅刺激s2中心，观测节点s1为间接) vs
    Γ_F(同时刺激s1观测节点本身+s3两端，各半强度)——单点中心刺激与
    双端共同作用刺激应在观测节点的发生记录里保留可区分性。"""
    schedule_e = [{1: 1.0}] * DRIVE_STEPS
    schedule_f = [{0: 0.5, 2: 0.5}] * DRIVE_STEPS

    handle_e = _run_scenario(schedule_e)
    handle_f = _run_scenario(schedule_f)
    sum_e = _occurrence_summary(handle_e)
    sum_f = _occurrence_summary(handle_f)

    print(f"Gamma_E(单点中心): {sum_e}")
    print(f"Gamma_F(共同两端): {sum_f}")
    assert _distinguishable(sum_e, sum_f), (
        f"单点与共同作用差异应在生成元发生记录中保留可区分性，"
        f"实际 E={sum_e} F={sum_f}")


if __name__ == "__main__":
    test_position_difference_preserved_through_interface()
    test_temporal_order_difference_preserved_through_interface()
    test_single_vs_combined_difference_preserved_through_interface()
    print("All P2-A1b-3 integration tests passed.")
