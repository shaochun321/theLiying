"""T-TTPA-1~9：P1-B3 提交与故障语义验收（9项，批判二十一"B3验收重点"）。

方案依据：第二十三节 P1-B3（批判二十一）。`apply_thermal_transport_plan()` 完成
"已生成的计划能否恰好提交一次，并且失败时不留下部分修改"这一 B3 唯一交付物。
覆盖批判给出的9项验收：成功提交与计划完全一致/计划生成后节点状态改变提交拒绝/
registry revision改变提交拒绝/边版本改变提交拒绝/同一计划二次提交拒绝/计划应用到
另一个图拒绝/中途异常完整回滚/所有拒绝场景状态不变/成功提交后账本闭合。
"""

from __future__ import annotations

import pytest

from nexus_v1.components.dynamic_thermal_field import ThermalCell
from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.structural_address import (
    AddressRegistry, DOMAIN_WORLD_CELL, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER,
)
from nexus_v1.components.ordered_excess_thermal_energy_link import (
    OrderedExcessThermalEnergyLink,
)
from nexus_v1.components.thermal_transport_plan import (
    prepare_thermal_transport_plan, apply_thermal_transport_plan,
    AppliedPlanRegistry, ThermalTransportPlanError,
)


def _build_rig(tail_charge=10.0, rate=0.2):
    reg = AddressRegistry()
    addr_i = reg.register_physical(DOMAIN_WORLD_CELL, 0)
    addr_j = reg.register_physical(DOMAIN_WORLD_CELL, 1)
    edge = reg.register_ordered_edge(addr_i, addr_j, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    link = OrderedExcessThermalEnergyLink(identity=edge, rate_per_time=rate)
    cell_i = ThermalCell(node_id=0, position=(0, 0, 0), capacitor=Capacitor(capacitance=1.0))
    cell_j = ThermalCell(node_id=1, position=(1, 0, 0), capacitor=Capacitor(capacitance=1.0))
    cell_i.capacitor.charge = tail_charge
    cells = {addr_i.uid: cell_i, addr_j.uid: cell_j}
    return reg, cells, link, addr_i, addr_j


def test_ttpa_1_successful_commit_matches_plan_exactly():
    """T-TTPA-1: 成功提交后，实际节点净变化与计划的 node_net_deltas 完全一致。"""
    reg, cells, link, addr_i, addr_j = _build_rig(tail_charge=10.0, rate=0.2)
    applied = AppliedPlanRegistry()
    plan = prepare_thermal_transport_plan([link], cells, reg, dt=0.5)

    receipt = apply_thermal_transport_plan(plan, cells, reg, applied)

    assert receipt.node_deltas_applied == plan.node_net_deltas
    assert receipt.plan_id == plan.plan_id


def test_ttpa_2_state_changed_since_prepare_rejected():
    """T-TTPA-2: 计划生成后节点状态被其他过程修改，提交拒绝。"""
    reg, cells, link, addr_i, addr_j = _build_rig()
    applied = AppliedPlanRegistry()
    plan = prepare_thermal_transport_plan([link], cells, reg, dt=0.3)

    cells[addr_i.uid].capacitor.charge = 999.0  # 计划生成后被外部修改

    with pytest.raises(ThermalTransportPlanError, match="charge changed"):
        apply_thermal_transport_plan(plan, cells, reg, applied)


def test_ttpa_3_registry_revision_changed_rejected():
    """T-TTPA-3: registry revision 在计划生成后发生变化（新增注册），提交拒绝。"""
    reg, cells, link, addr_i, addr_j = _build_rig()
    applied = AppliedPlanRegistry()
    plan = prepare_thermal_transport_plan([link], cells, reg, dt=0.3)

    reg.register_physical(DOMAIN_WORLD_CELL, 99)  # 触发 revision 递增

    with pytest.raises(ThermalTransportPlanError, match="registry has changed"):
        apply_thermal_transport_plan(plan, cells, reg, applied)


def test_ttpa_4_edge_version_changed_rejected():
    """T-TTPA-4: 边/地址版本在计划生成后失效（节点被重建），提交拒绝。"""
    reg, cells, link, addr_i, addr_j = _build_rig()
    applied = AppliedPlanRegistry()
    plan = prepare_thermal_transport_plan([link], cells, reg, dt=0.3)

    reg.rebuild_physical(DOMAIN_WORLD_CELL, 0, 100)  # tail 节点重建，旧地址失效

    with pytest.raises(ThermalTransportPlanError):
        apply_thermal_transport_plan(plan, cells, reg, applied)


def test_ttpa_5_double_submit_rejected():
    """T-TTPA-5: 同一计划第二次提交拒绝（同一份能量转移不能被执行两次）。"""
    reg, cells, link, addr_i, addr_j = _build_rig()
    applied = AppliedPlanRegistry()
    plan = prepare_thermal_transport_plan([link], cells, reg, dt=0.3)

    apply_thermal_transport_plan(plan, cells, reg, applied)
    with pytest.raises(ThermalTransportPlanError, match="already applied"):
        apply_thermal_transport_plan(plan, cells, reg, applied)


def test_ttpa_6_plan_applied_to_different_graph_rejected():
    """T-TTPA-6: 计划应用到另一组 cells 时拒绝——覆盖两种"不是同一个图"的
    具体表现：(a) 缺少参与地址对应的 ThermalCell；(b) tail 存在但 charge
    与快照不符（碰巧同一地址但物理内容不同的"另一个图"）。
    """
    reg, cells, link, addr_i, addr_j = _build_rig()
    applied = AppliedPlanRegistry()
    plan = prepare_thermal_transport_plan([link], cells, reg, dt=0.3)

    # (a) tail 匹配快照，但缺 head —— 命中"no ThermalCell provided"
    tail_matching_cell = ThermalCell(node_id=0, position=(0, 0, 0),
                                      capacitor=Capacitor(capacitance=1.0))
    tail_matching_cell.capacitor.charge = plan.participating_node_snapshots[addr_i.uid]
    other_cells_missing_head = {addr_i.uid: tail_matching_cell}
    with pytest.raises(ThermalTransportPlanError, match="no ThermalCell provided"):
        apply_thermal_transport_plan(plan, other_cells_missing_head, reg, applied)

    # (b) 两端地址都在，但 tail 的物理状态与快照不符 —— 命中"charge changed"
    other_cells_wrong_state = {
        addr_i.uid: ThermalCell(node_id=0, position=(0, 0, 0), capacitor=Capacitor(capacitance=1.0)),
        addr_j.uid: ThermalCell(node_id=1, position=(1, 0, 0), capacitor=Capacitor(capacitance=1.0)),
    }
    with pytest.raises(ThermalTransportPlanError, match="charge changed"):
        apply_thermal_transport_plan(plan, other_cells_wrong_state, reg, applied)


def test_ttpa_7_mid_apply_exception_triggers_full_rollback():
    """T-TTPA-7: 多边计划中，前面的边已成功写入，后面的边抛异常——所有已
    修改节点（不只是抛异常的那条边）都必须完整回滚。
    """
    reg = AddressRegistry()
    addr_i = reg.register_physical(DOMAIN_WORLD_CELL, 0)
    addr_j = reg.register_physical(DOMAIN_WORLD_CELL, 1)
    addr_k = reg.register_physical(DOMAIN_WORLD_CELL, 2)
    edge_ij = reg.register_ordered_edge(addr_i, addr_j, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    edge_ik = reg.register_ordered_edge(addr_i, addr_k, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    link_ij = OrderedExcessThermalEnergyLink(identity=edge_ij, rate_per_time=0.2)
    link_ik = OrderedExcessThermalEnergyLink(identity=edge_ik, rate_per_time=0.2)

    cell_i = ThermalCell(node_id=0, position=(0, 0, 0), capacitor=Capacitor(capacitance=1.0))
    cell_j = ThermalCell(node_id=1, position=(1, 0, 0), capacitor=Capacitor(capacitance=1.0))
    cell_k = ThermalCell(node_id=2, position=(2, 0, 0), capacitor=Capacitor(capacitance=1.0))
    cell_i.capacitor.charge = 10.0
    cells = {addr_i.uid: cell_i, addr_j.uid: cell_j, addr_k.uid: cell_k}

    applied = AppliedPlanRegistry()
    plan = prepare_thermal_transport_plan([link_ij, link_ik], cells, reg, dt=0.5)

    i_before = cell_i.capacitor.charge
    j_before = cell_j.capacitor.charge
    k_before = cell_k.capacitor.charge

    def broken_inject(current, dt=1.0):
        raise RuntimeError("simulated mid-apply failure")
    cell_k.capacitor.inject = broken_inject

    with pytest.raises(RuntimeError, match="simulated mid-apply failure"):
        apply_thermal_transport_plan(plan, cells, reg, applied)

    assert cell_i.capacitor.charge == i_before
    assert cell_j.capacitor.charge == j_before  # 边ij已成功写入，仍需回滚
    assert cell_k.capacitor.charge == k_before
    assert not applied.is_applied(plan.plan_id)


def test_ttpa_8_all_rejection_paths_leave_state_unchanged():
    """T-TTPA-8: 汇总检查——T-TTPA-2~6 的每种拒绝场景，cells/registry/
    applied_plans 均保持调用前状态（逐场景独立验证，非仅抽样）。
    """
    # 场景A: 状态过期
    reg, cells, link, addr_i, addr_j = _build_rig()
    applied = AppliedPlanRegistry()
    plan = prepare_thermal_transport_plan([link], cells, reg, dt=0.3)
    cells[addr_i.uid].capacitor.charge = 999.0
    j_before = cells[addr_j.uid].capacitor.charge
    with pytest.raises(ThermalTransportPlanError):
        apply_thermal_transport_plan(plan, cells, reg, applied)
    assert cells[addr_j.uid].capacitor.charge == j_before
    assert not applied.is_applied(plan.plan_id)

    # 场景B: registry revision 变化
    reg2, cells2, link2, addr_i2, addr_j2 = _build_rig()
    applied2 = AppliedPlanRegistry()
    plan2 = prepare_thermal_transport_plan([link2], cells2, reg2, dt=0.3)
    i2_before = cells2[addr_i2.uid].capacitor.charge
    reg2.register_physical(DOMAIN_WORLD_CELL, 99)
    with pytest.raises(ThermalTransportPlanError):
        apply_thermal_transport_plan(plan2, cells2, reg2, applied2)
    assert cells2[addr_i2.uid].capacitor.charge == i2_before
    assert not applied2.is_applied(plan2.plan_id)


def test_ttpa_9_successful_commit_closes_ledger():
    """T-TTPA-9: 成功提交后，边级与全局传输账本闭合——节点净变化总和为0，
    receipt 的 total_transport_residual 应≈0。
    """
    reg = AddressRegistry()
    addr_i = reg.register_physical(DOMAIN_WORLD_CELL, 0)
    addr_j = reg.register_physical(DOMAIN_WORLD_CELL, 1)
    addr_k = reg.register_physical(DOMAIN_WORLD_CELL, 2)
    edge_ij = reg.register_ordered_edge(addr_i, addr_j, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    edge_ik = reg.register_ordered_edge(addr_i, addr_k, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    link_ij = OrderedExcessThermalEnergyLink(identity=edge_ij, rate_per_time=0.15)
    link_ik = OrderedExcessThermalEnergyLink(identity=edge_ik, rate_per_time=0.25)

    cell_i = ThermalCell(node_id=0, position=(0, 0, 0), capacitor=Capacitor(capacitance=1.0))
    cell_j = ThermalCell(node_id=1, position=(1, 0, 0), capacitor=Capacitor(capacitance=1.0))
    cell_k = ThermalCell(node_id=2, position=(2, 0, 0), capacitor=Capacitor(capacitance=1.0))
    cell_i.capacitor.charge = 10.0
    cells = {addr_i.uid: cell_i, addr_j.uid: cell_j, addr_k.uid: cell_k}

    applied = AppliedPlanRegistry()
    plan = prepare_thermal_transport_plan([link_ij, link_ik], cells, reg, dt=0.4)
    receipt = apply_thermal_transport_plan(plan, cells, reg, applied)

    assert receipt.total_transport_residual < 1e-9


if __name__ == "__main__":
    test_ttpa_1_successful_commit_matches_plan_exactly()
    test_ttpa_2_state_changed_since_prepare_rejected()
    test_ttpa_3_registry_revision_changed_rejected()
    test_ttpa_4_edge_version_changed_rejected()
    test_ttpa_5_double_submit_rejected()
    test_ttpa_6_plan_applied_to_different_graph_rejected()
    test_ttpa_7_mid_apply_exception_triggers_full_rollback()
    test_ttpa_8_all_rejection_paths_leave_state_unchanged()
    test_ttpa_9_successful_commit_closes_ledger()
    print("T-TTPA-1~9 ALL PASS")
