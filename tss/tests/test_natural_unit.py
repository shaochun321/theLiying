"""T-NU-1~4：P2-B0 单 occurrence 自然化接口验证（2026-07-28）。

方案依据：`cell-cell/交叉比对/document - 2026-07-28T183325.248.md`（正式放行
P2-B0）+ `nexus_v1/generators/natural_unit.py` 模块文档。

验证 `naturalize()` 组装出的 `NaturalUnit` 满足四个必答问题：
  T-NU-1: count_measure 恒为1，duration_seconds 精确等于 (t_rearm-t_up)*dt
          （Q1/Q2：两个候选测度分别正确、不混淆）。
  T-NU-2: address 透传父物理支撑谱系，不是裸数字（Q4）。
  T-NU-3: port 正确标识生成元实例。
  T-NU-4: physical_ledger 与 trajectory.window() 直接调用结果一致；未挂载
          trajectory 时为空 tuple 而不报错（向后兼容）。
"""
import sys

sys.path.insert(0, '.')

from tss.generators import wrap_base_generator, naturalize, REFERENCE_TRANSDUCTION_CONFIG
from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.structural_address import AddressRegistry
from nexus_v1.components.skin_three_point import (
    TEST_KAPPA_THREE_POINT, TEST_R_LEAK_AMBIENT_THREE_POINT, build_three_point_skin,
)
from tss.relations import FROZEN_THERMAL_SITES

DT = 0.001
CONFIG = REFERENCE_TRANSDUCTION_CONFIG
SITE_INDEX = FROZEN_THERMAL_SITES["t1_pair"]["a"]


def _fresh_skin():
    return build_three_point_skin(
        kappa=TEST_KAPPA_THREE_POINT, r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)


def _run_to_one_occurrence(record_trajectory: bool):
    """驱动一个生成元产生恰好一次 occurrence，返回 (handle, occurrence)。"""
    circuit = VariantCircuit()
    registry = AddressRegistry()
    handle = wrap_base_generator(
        circuit, SITE_INDEX, registry, polarity="warm",
        record_trajectory=record_trajectory)
    graph = _fresh_skin()
    t = 0
    occurrence = None
    for _ in range(900):
        graph.step(dt=1.0, external_injections={0: 1.0})
        q = graph.cells[0].temperature
        ev = handle.tick_from_skin(q, CONFIG, DT, t)
        if ev is not None:
            occurrence = ev
        t += 1
    for _ in range(3500):
        graph.step(dt=1.0, external_injections={})
        q = graph.cells[0].temperature
        ev = handle.tick_from_skin(q, CONFIG, DT, t)
        if ev is not None:
            occurrence = ev
        t += 1
    assert occurrence is not None, "本次驱动预算内应产生恰好一次 occurrence"
    return handle, occurrence


def test_nu_1_count_and_duration_measures():
    handle, occ = _run_to_one_occurrence(record_trajectory=False)
    nu = naturalize(handle, occ, DT, transduction_config=CONFIG)

    assert nu.count_measure == 1
    expected_duration_steps = occ.t_rearm - occ.t_up
    assert nu.duration_raw_steps == expected_duration_steps
    assert abs(nu.duration_seconds - expected_duration_steps * DT) < 1e-12
    print(f"T-NU-1 PASS: count_measure=1, duration_raw_steps={nu.duration_raw_steps}, "
          f"duration_seconds={nu.duration_seconds}")


def test_nu_2_address_preserves_lineage():
    handle, occ = _run_to_one_occurrence(record_trajectory=False)
    nu = naturalize(handle, occ, DT, transduction_config=CONFIG)

    assert nu.address is occ.address
    assert len(nu.address.parent_addresses) > 0, "address 必须回指父物理支撑，不能是裸地址"
    print(f"T-NU-2 PASS: address={nu.address.uid}, "
          f"parent_addresses={[a.uid for a in nu.address.parent_addresses]}")


def test_nu_3_port_identifies_generator():
    handle, occ = _run_to_one_occurrence(record_trajectory=False)
    nu = naturalize(handle, occ, DT, transduction_config=CONFIG)

    assert nu.port == (handle.site_index, handle.polarity)
    assert nu.port == (SITE_INDEX, "warm")
    print(f"T-NU-3 PASS: port={nu.port}")


def test_nu_4_physical_ledger_matches_trajectory_window():
    # 挂载 trajectory 的场景：physical_ledger 应与直接调用 window() 一致。
    handle_with_traj, occ_with_traj = _run_to_one_occurrence(record_trajectory=True)
    nu_with_traj = naturalize(handle_with_traj, occ_with_traj, DT, transduction_config=CONFIG)
    expected_ledger = tuple(
        handle_with_traj.trajectory.window(occ_with_traj.t_up, occ_with_traj.t_rearm))
    assert nu_with_traj.physical_ledger == expected_ledger
    assert len(nu_with_traj.physical_ledger) > 0, "窗口内应有非空的轨迹记录"
    print(f"T-NU-4a PASS: physical_ledger 长度={len(nu_with_traj.physical_ledger)}，"
          f"与 trajectory.window() 直接调用一致")

    # 未挂载 trajectory 的场景：physical_ledger 应为空 tuple，不报错（向后兼容）。
    handle_no_traj, occ_no_traj = _run_to_one_occurrence(record_trajectory=False)
    nu_no_traj = naturalize(handle_no_traj, occ_no_traj, DT, transduction_config=CONFIG)
    assert nu_no_traj.physical_ledger == ()
    print("T-NU-4b PASS: 未挂载 trajectory 时 physical_ledger=()，不报错")


def test_nu_5_count_measure_validation_rejects_non_one():
    """NaturalUnit.__post_init__ 应拒绝 count_measure != 1（07-20 文档禁止
    冒充物理量的纪律——若上游误传非1的count，应立刻报错而不是静默接受）。"""
    from tss.generators.natural_unit import NaturalUnit
    handle, occ = _run_to_one_occurrence(record_trajectory=False)
    try:
        NaturalUnit(
            address=occ.address, port=(handle.site_index, handle.polarity),
            window=(occ.t_up, occ.t_rearm), count_measure=2,
            duration_raw_steps=occ.t_rearm - occ.t_up,
            duration_seconds=(occ.t_rearm - occ.t_up) * DT,
        )
        assert False, "count_measure=2 应该被拒绝"
    except ValueError as e:
        print(f"T-NU-5 PASS: count_measure!=1 被正确拒绝 ({e})")


def run():
    test_nu_1_count_and_duration_measures()
    test_nu_2_address_preserves_lineage()
    test_nu_3_port_identifies_generator()
    test_nu_4_physical_ledger_matches_trajectory_window()
    test_nu_5_count_measure_validation_rejects_non_one()
    print()
    print("T-NU-1~5 ALL PASS")


if __name__ == "__main__":
    run()
