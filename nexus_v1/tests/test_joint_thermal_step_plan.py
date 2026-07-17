"""T-JTS-1~9：P1-C0 联合计划与统一提交验收（批判二十二给出的设计，2026-07-17）。

方案依据：第二十三节 P1-C0（批判二十二）。`prepare_joint_thermal_step()`/
`apply_joint_thermal_step()` 把世界扩散+泄漏/世界-皮肤接触/有序过剩热能转移/
动态热源释放折叠进一个统一快照-计算-联合校验-单次提交周期，同时闭合批判二十二
用代码实测验证的三处 P1-B3 结构性边界（状态过期检测范围/提交登记表生命周期/
运行实例绑定）。
"""

from __future__ import annotations

import pytest

from nexus_v1.components.dynamic_thermal_field import ThermalCell, ThermalLink, ThermalFieldGraph
from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.skin_thermal_contact import (
    SkinThermalState, ThermalContact, couple_world_skin_step,
)
from nexus_v1.components.thermal_source_coupling import DynamicHeatSource, ThermalFieldLocator
from nexus_v1.components.structural_address import (
    AddressRegistry, DOMAIN_WORLD_CELL, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER,
)
from nexus_v1.components.ordered_excess_thermal_energy_link import (
    OrderedExcessThermalEnergyLink,
)
from nexus_v1.components.joint_thermal_step_plan import (
    JointThermalRuntime, prepare_joint_thermal_step, apply_joint_thermal_step,
    JointThermalStepError,
)


def _build_rig(n_world=2, kappa=0.01, h=0.05, area=1.0, source_power=2.0,
                r_leak_ambient=None):
    cells = [ThermalCell(node_id=i, position=(float(i), 0, 0),
                          capacitor=Capacitor(capacitance=1.0)) for i in range(n_world)]
    links = [ThermalLink(i=0, j=1, kappa=kappa)] if n_world >= 2 else []
    graph = ThermalFieldGraph(cells=cells, links=links, r_leak_ambient=r_leak_ambient)
    skin = SkinThermalState(patch_id=1, capacitor=Capacitor(capacitance=1.0))
    contact = ThermalContact(world_node_id=0, skin_patch_id=1, h=h, area=area)
    source = DynamicHeatSource(position=(0.0, 0, 0), energy_remaining=1000.0,
                                power=source_power, efficiency=1.0)
    locator = ThermalFieldLocator(k=1)
    reg = AddressRegistry()
    for i in range(n_world):
        reg.register_physical(DOMAIN_WORLD_CELL, i)
    runtime = JointThermalRuntime(world_graph=graph, registry=reg)
    return runtime, graph, skin, contact, source, locator, reg


def test_jts_1_degenerate_consistency_matches_couple_world_skin_step():
    """T-JTS-1: 无传输边时，联合调度结果应与现有 couple_world_skin_step()
    在相同输入下数值一致（真实运行对照，不是独立构造矩阵）。
    """
    runtime_a, graph_a, skin_a, contact_a, source_a, locator_a, _ = _build_rig()
    ledger = couple_world_skin_step(source_a, locator_a, graph_a, contact_a, skin_a, dt=0.3)

    runtime_b, graph_b, skin_b, contact_b, source_b, locator_b, _ = _build_rig()
    plan = prepare_joint_thermal_step(runtime_b, [contact_b], {1: skin_b}, [], source_b,
                                       locator_b, dt=0.3)
    receipt = apply_joint_thermal_step(runtime_b, plan, {1: skin_b}, source_b)

    for nid in graph_a.cells:
        assert graph_a.cells[nid].capacitor.charge == pytest.approx(
            graph_b.cells[nid].capacitor.charge, abs=1e-9)
    assert skin_a.capacitor.charge == pytest.approx(skin_b.capacitor.charge, abs=1e-9)
    assert source_a.energy_remaining == pytest.approx(source_b.energy_remaining, abs=1e-9)
    assert ledger.residual < 1e-9
    assert receipt.residual < 1e-9


def test_jts_2_combined_instability_rejected_state_untouched():
    """T-JTS-2: 扩散/接触各自看似安全，但联合 η_i^joint 超限时，在
    source.release()/任何状态写入前拒绝，全部状态不变。
    """
    runtime, graph, skin, contact, source, locator, _ = _build_rig(
        kappa=0.4, h=0.4, source_power=1.0)
    world0_before = graph.cells[0].capacitor.charge
    skin_before = skin.capacitor.charge
    source_before = source.energy_remaining

    with pytest.raises(JointThermalStepError, match="joint instability"):
        prepare_joint_thermal_step(runtime, [contact], {1: skin}, [], source, locator,
                                    dt=1.5, eta=1.0)

    assert graph.cells[0].capacitor.charge == world0_before
    assert skin.capacitor.charge == skin_before
    assert source.energy_remaining == source_before


def test_jts_3_full_state_fingerprint_closes_p1b3_gap1():
    """T-JTS-3（闭合批判二十二点1）: 计划生成后，节点被外部 inject(+delta)
    再 inject(-delta) —— charge 精确回到快照值，但 _q_in/_q_out 已变化。
    联合计划的完整状态三元组检测必须能察觉，P1-B3 的纯 charge 比较做不到这点。
    """
    runtime, graph, skin, contact, source, locator, _ = _build_rig()
    plan = prepare_joint_thermal_step(runtime, [contact], {1: skin}, [], source,
                                       locator, dt=0.3)

    graph.cells[0].capacitor.inject(+3.0, 1.0)
    graph.cells[0].capacitor.inject(-3.0, 1.0)
    assert graph.cells[0].capacitor.charge == plan.world_state_snapshots[0][0]  # charge回到快照值
    assert graph.cells[0].capacitor._q_in != 0.0  # 但_q_in/_q_out已变

    with pytest.raises(JointThermalStepError, match="state changed"):
        apply_joint_thermal_step(runtime, plan, {1: skin}, source)


def test_jts_4_double_submit_via_same_runtime_rejected():
    """T-JTS-4（闭合批判二十二点2）: `AppliedJointPlanRegistry` 由
    `JointThermalRuntime` 持久持有，调用方无法传入"全新的"提交登记表
    ——API本身不接受外部registry参数，双重提交结构性不可能绕过。
    """
    runtime, graph, skin, contact, source, locator, _ = _build_rig()
    plan = prepare_joint_thermal_step(runtime, [contact], {1: skin}, [], source,
                                       locator, dt=0.3)
    apply_joint_thermal_step(runtime, plan, {1: skin}, source)

    with pytest.raises(JointThermalStepError, match="already applied"):
        apply_joint_thermal_step(runtime, plan, {1: skin}, source)


def test_jts_5_mirror_runtime_rejected_by_runtime_uid():
    """T-JTS-5（闭合批判二十二点3）: 两个地址/revision/charge完全相同但
    独立构造的镜像图，用图A生成的计划不能提交到图B的runtime——因为
    `runtime_uid`取自`id(world_graph)`，绑定到实际存活的对象本身。
    """
    runtime_a, graph_a, skin_a, contact_a, source_a, locator_a, _ = _build_rig()
    plan_a = prepare_joint_thermal_step(runtime_a, [contact_a], {1: skin_a}, [], source_a,
                                         locator_a, dt=0.3)

    runtime_b, graph_b, skin_b, contact_b, source_b, locator_b, _ = _build_rig()
    assert runtime_a.runtime_uid != runtime_b.runtime_uid

    with pytest.raises(JointThermalStepError, match="different runtime instance"):
        apply_joint_thermal_step(runtime_b, plan_a, {1: skin_b}, source_b)


def test_jts_6_mid_apply_exception_triggers_full_rollback():
    """T-JTS-6: world_graph.step() 成功后（世界侧已写入），皮肤侧inject
    抛异常——世界+皮肤+热源全部状态必须完整回滚，不是只回滚异常发生的那一步。
    """
    runtime, graph, skin, contact, source, locator, _ = _build_rig()
    plan = prepare_joint_thermal_step(runtime, [contact], {1: skin}, [], source,
                                       locator, dt=0.3)

    world0_before = graph.cells[0].capacitor.charge
    world1_before = graph.cells[1].capacitor.charge
    skin_before = skin.capacitor.charge
    source_before = source.energy_remaining

    def broken_inject(current, dt=1.0):
        raise RuntimeError("simulated skin inject failure")
    skin.capacitor.inject = broken_inject

    with pytest.raises(RuntimeError, match="simulated skin inject failure"):
        apply_joint_thermal_step(runtime, plan, {1: skin}, source)

    assert graph.cells[0].capacitor.charge == world0_before
    assert graph.cells[1].capacitor.charge == world1_before
    assert skin.capacitor.charge == skin_before
    assert source.energy_remaining == source_before
    assert not runtime.applied_plan_registry.is_applied(plan.plan_id)


def test_jts_7_successful_commit_ledger_closes():
    """T-JTS-7: 世界+接触+传输+热源共同参与的场景下，成功提交后三方账本
    闭合（residual≈0）。
    """
    runtime, graph, skin, contact, source, locator, reg = _build_rig(n_world=3, kappa=0.01)
    addr1 = reg.address_of(DOMAIN_WORLD_CELL, 1)
    addr2 = reg.address_of(DOMAIN_WORLD_CELL, 2)
    edge_12 = reg.register_ordered_edge(addr1, addr2, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    link_12 = OrderedExcessThermalEnergyLink(identity=edge_12, rate_per_time=0.1)
    graph.cells[1].capacitor.charge = 5.0

    plan = prepare_joint_thermal_step(runtime, [contact], {1: skin}, [link_12], source,
                                       locator, dt=0.5)
    receipt = apply_joint_thermal_step(runtime, plan, {1: skin}, source)

    assert receipt.residual < 1e-9


def test_jts_8_multiple_contacts_and_shared_tail_transport_aggregate_correctly():
    """T-JTS-8: 同一皮肤被多条接触边命中时通量求和；共享同一tail的多条
    传输边的 Σa_e 正确进入联合稳定性门（不是分别检查后拼接）。
    """
    cells = [ThermalCell(node_id=i, position=(float(i), 0, 0),
                          capacitor=Capacitor(capacitance=1.0)) for i in range(3)]
    graph = ThermalFieldGraph(cells=cells, links=[], r_leak_ambient=None)
    skin = SkinThermalState(patch_id=1, capacitor=Capacitor(capacitance=1.0))
    contact_a = ThermalContact(world_node_id=0, skin_patch_id=1, h=0.02, area=1.0)
    contact_b = ThermalContact(world_node_id=0, skin_patch_id=1, h=0.02, area=1.0)
    source = DynamicHeatSource(position=(0.0, 0, 0), energy_remaining=1000.0,
                                power=0.0, efficiency=1.0)
    locator = ThermalFieldLocator(k=1)
    reg = AddressRegistry()
    for i in range(3):
        reg.register_physical(DOMAIN_WORLD_CELL, i)
    runtime = JointThermalRuntime(world_graph=graph, registry=reg)

    addr0 = reg.address_of(DOMAIN_WORLD_CELL, 0)
    addr1 = reg.address_of(DOMAIN_WORLD_CELL, 1)
    addr2 = reg.address_of(DOMAIN_WORLD_CELL, 2)
    edge_01 = reg.register_ordered_edge(addr0, addr1, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    edge_02 = reg.register_ordered_edge(addr0, addr2, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    link_01 = OrderedExcessThermalEnergyLink(identity=edge_01, rate_per_time=0.3)
    link_02 = OrderedExcessThermalEnergyLink(identity=edge_02, rate_per_time=0.3)
    graph.cells[0].capacitor.charge = 10.0

    plan = prepare_joint_thermal_step(runtime, [contact_a, contact_b], {1: skin},
                                       [link_01, link_02], source, locator, dt=0.5)

    # 两条接触边通量求和进入 skin_injections。
    assert plan.skin_injections[1] == pytest.approx(
        contact_a.flux(graph, skin) + contact_b.flux(graph, skin), abs=1e-9)
    # 联合稳定性门里 node0 的 a_sum 是两条传输边之和 (0.3+0.3=0.6)，
    # H_sum 是两条接触边之和 (0.02+0.02=0.04)，无扩散 kappa/env泄漏。
    eta_0 = plan.stability_report["world:0"]
    expected_eta_0 = 0.5 * ((0.0 + 0.04 + 0.0) / 1.0 + 0.6)
    assert eta_0 == pytest.approx(expected_eta_0, abs=1e-9)


def test_jts_9_unregistered_transport_endpoint_rejected():
    """T-JTS-9: 传输边引用了未注册 DOMAIN_WORLD_CELL 地址的节点时，
    prepare 阶段拒绝（不是运行到一半才失败）。
    """
    runtime, graph, skin, contact, source, locator, reg = _build_rig(n_world=3)
    # 手动构造一个引用了未在 world_graph 里出现的 node_id 的边（用一个独立的
    # AddressRegistry注册，制造"该地址在本registry里合法，但local_key对应的
    # node_id不在这个graph里"的场景）。
    other_graph_reg = AddressRegistry()
    fake_addr_a = other_graph_reg.register_physical(DOMAIN_WORLD_CELL, 999)
    fake_addr_b = other_graph_reg.register_physical(DOMAIN_WORLD_CELL, 998)
    fake_edge = other_graph_reg.register_ordered_edge(
        fake_addr_a, fake_addr_b, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    fake_link = OrderedExcessThermalEnergyLink(identity=fake_edge, rate_per_time=0.1)

    with pytest.raises(JointThermalStepError):
        prepare_joint_thermal_step(runtime, [contact], {1: skin}, [fake_link], source,
                                    locator, dt=0.3)


def test_jts_10_two_runtimes_same_graph_cannot_double_apply():
    """T-JTS-10（批判二十三①，阻塞项修复回归）: 两个独立构造的
    `JointThermalRuntime`包装同一个`world_graph`，`runtime_uid`必须不同
    （取自`id(self)`而非`id(world_graph)`）——即使把三方状态完整复原到
    快照值，也不能通过另一个runtime二次提交同一计划。
    """
    runtime_a, graph, skin, contact, source, locator, _ = _build_rig()
    runtime_b = JointThermalRuntime(world_graph=graph, registry=runtime_a.registry)
    assert runtime_a.runtime_uid != runtime_b.runtime_uid
    assert runtime_a.applied_plan_registry is not runtime_b.applied_plan_registry

    plan = prepare_joint_thermal_step(runtime_a, [contact], {1: skin}, [], source,
                                       locator, dt=0.3)
    apply_joint_thermal_step(runtime_a, plan, {1: skin}, source)

    # 把三方状态（含 _q_in/_q_out）精确复原到快照值。
    def _restore(cap, triple):
        cap.charge, cap._q_in, cap._q_out = triple
    for nid, triple in plan.world_state_snapshots.items():
        _restore(graph.cells[nid].capacitor, triple)
    for pid, triple in plan.skin_state_snapshots.items():
        _restore(skin.capacitor, triple)
    source.energy_remaining = plan.source_energy_snapshot

    with pytest.raises(JointThermalStepError, match="different runtime instance"):
        apply_joint_thermal_step(runtime_b, plan, {1: skin}, source)


def test_jts_11_rollback_restores_graph_level_diagnostics():
    """T-JTS-11（批判二十三②，非阻塞项修复回归）: 世界侧`step()`成功后
    皮肤侧异常，`ThermalFieldGraph`自己的图级诊断快照
    （`_last_injection`/`_last_leak`/`_last_divergence_dt`/
    `_last_charge_before`/`_last_dt`/`_total_injected`/
    `_total_leaked_ambient`）必须与Capacitor三元组一起回滚，否则
    `closure_residual()`/`conservation_residual()`会读到与实际物理状态
    不符的幽灵记录。
    """
    runtime, graph, skin, contact, source, locator, _ = _build_rig()
    plan = prepare_joint_thermal_step(runtime, [contact], {1: skin}, [], source,
                                       locator, dt=0.3)

    last_injection_before = dict(graph._last_injection)
    last_leak_before = dict(graph._last_leak)
    last_divergence_before = dict(graph._last_divergence_dt)
    last_charge_before_before = dict(graph._last_charge_before)
    last_dt_before = graph._last_dt
    total_injected_before = graph._total_injected
    total_leaked_before = graph._total_leaked_ambient

    def broken_inject(current, dt=1.0):
        raise RuntimeError("simulated skin inject failure")
    skin.capacitor.inject = broken_inject

    with pytest.raises(RuntimeError):
        apply_joint_thermal_step(runtime, plan, {1: skin}, source)

    assert graph._last_injection == last_injection_before
    assert graph._last_leak == last_leak_before
    assert graph._last_divergence_dt == last_divergence_before
    assert graph._last_charge_before == last_charge_before_before
    assert graph._last_dt == last_dt_before
    assert graph._total_injected == total_injected_before
    assert graph._total_leaked_ambient == total_leaked_before

    # closure_residual 在回滚后应仍然闭合（不产生幽灵记录）。
    for nid in graph.cells:
        assert graph.closure_residual(nid) < 1e-9
    assert graph.conservation_residual() < 1e-9


def test_jts_12_skin_joint_stability_sums_across_distinct_world_nodes():
    """T-JTS-12（批判二十三③，测试覆盖补全）: 两个不同世界节点通过各自
    的接触边连到同一皮肤时，皮肤端联合稳定性 η_s 必须是 Σ_i H_is（跨
    world_node_id 求和），不只是同一世界节点多条边的情形（T-JTS-8 已覆盖
    后者）。
    """
    cells = [ThermalCell(node_id=i, position=(float(i), 0, 0),
                          capacitor=Capacitor(capacitance=1.0)) for i in range(2)]
    graph = ThermalFieldGraph(cells=cells, links=[], r_leak_ambient=None)
    skin = SkinThermalState(patch_id=1, capacitor=Capacitor(capacitance=1.0))
    contact_0 = ThermalContact(world_node_id=0, skin_patch_id=1, h=0.03, area=1.0)
    contact_1 = ThermalContact(world_node_id=1, skin_patch_id=1, h=0.04, area=1.0)
    source = DynamicHeatSource(position=(0.0, 0, 0), energy_remaining=1000.0,
                                power=0.0, efficiency=1.0)
    locator = ThermalFieldLocator(k=1)
    reg = AddressRegistry()
    reg.register_physical(DOMAIN_WORLD_CELL, 0)
    reg.register_physical(DOMAIN_WORLD_CELL, 1)
    runtime = JointThermalRuntime(world_graph=graph, registry=reg)

    plan = prepare_joint_thermal_step(runtime, [contact_0, contact_1], {1: skin}, [],
                                       source, locator, dt=0.5)

    expected_eta_s = 0.5 * (0.03 + 0.04) / 1.0
    assert plan.stability_report["skin:1"] == pytest.approx(expected_eta_s, abs=1e-9)
    assert plan.skin_injections[1] == pytest.approx(
        contact_0.flux(graph, skin) + contact_1.flux(graph, skin), abs=1e-9)


if __name__ == "__main__":
    test_jts_1_degenerate_consistency_matches_couple_world_skin_step()
    test_jts_2_combined_instability_rejected_state_untouched()
    test_jts_3_full_state_fingerprint_closes_p1b3_gap1()
    test_jts_4_double_submit_via_same_runtime_rejected()
    test_jts_5_mirror_runtime_rejected_by_runtime_uid()
    test_jts_6_mid_apply_exception_triggers_full_rollback()
    test_jts_7_successful_commit_ledger_closes()
    test_jts_8_multiple_contacts_and_shared_tail_transport_aggregate_correctly()
    test_jts_9_unregistered_transport_endpoint_rejected()
    test_jts_10_two_runtimes_same_graph_cannot_double_apply()
    test_jts_11_rollback_restores_graph_level_diagnostics()
    test_jts_12_skin_joint_stability_sums_across_distinct_world_nodes()
    print("T-JTS-1~12 ALL PASS")
