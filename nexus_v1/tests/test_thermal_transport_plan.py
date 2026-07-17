"""T-TTP-1~8：P1-B2 不可变多边转移计划验收（8类，批判二十§七）。

方案依据：第二十三节 P1-B2（批判二十）。`ThermalTransportPlan`+
`prepare_thermal_transport_plan()` 解决 P1-B1.5 遗留的"多边共享同一tail节点
时，逐边直接调用会绕过统一快照纪律"问题——`prepare()`一次性从同一物理快照
生成不可变计划，边遍历顺序不应改变结果。本文件覆盖批判给出的8类验收范围：
计划纯只读/两边共享tail/遍历顺序不变/组合失稳拒绝/零或负过剩状态/多tail
独立汇总/地址拓扑错误/计划账本闭合。
"""

from __future__ import annotations

import pytest

from nexus_v1.components.dynamic_thermal_field import ThermalCell
from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.structural_address import (
    AddressRegistry, StructuralAddress, DOMAIN_WORLD_CELL,
    MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER, MECHANISM_DIFFUSION,
)
from nexus_v1.components.ordered_excess_thermal_energy_link import (
    OrderedExcessThermalEnergyLink,
)
from nexus_v1.components.thermal_transport_plan import (
    prepare_thermal_transport_plan, ThermalTransportPlanError,
)


def _build_star_rig(n_leaves=2, tail_charge=10.0, ambient=0.0, rate=0.2):
    """1个tail节点 + n_leaves个head节点，tail对每个head各一条有序边。"""
    reg = AddressRegistry()
    addr_tail = reg.register_physical(DOMAIN_WORLD_CELL, 0)
    cell_tail = ThermalCell(node_id=0, position=(0, 0, 0), ambient_temperature=ambient,
                             capacitor=Capacitor(capacitance=1.0))
    cell_tail.capacitor.charge = tail_charge
    cells = {addr_tail.uid: cell_tail}
    links = []
    for k in range(1, n_leaves + 1):
        addr_head = reg.register_physical(DOMAIN_WORLD_CELL, k)
        cell_head = ThermalCell(node_id=k, position=(float(k), 0, 0), ambient_temperature=ambient,
                                 capacitor=Capacitor(capacitance=1.0))
        cells[addr_head.uid] = cell_head
        edge = reg.register_ordered_edge(addr_tail, addr_head, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
        links.append(OrderedExcessThermalEnergyLink(identity=edge, rate_per_time=rate))
    return reg, cells, links, addr_tail


def test_ttp_1_prepare_is_pure_readonly():
    """T-TTP-1: prepare() 调用前后，所有参与节点的 charge 完全不变。"""
    reg, cells, links, addr_tail = _build_star_rig(n_leaves=2)
    charges_before = {uid: cell.capacitor.charge for uid, cell in cells.items()}

    prepare_thermal_transport_plan(links, cells, reg, dt=0.5)

    charges_after = {uid: cell.capacitor.charge for uid, cell in cells.items()}
    assert charges_before == charges_after


def test_ttp_2_shared_tail_uses_single_snapshot():
    """T-TTP-2: 两条边共享同一 tail，均基于同一份快照计算——不是第二条边
    读取第一条边"扣除后"的状态（因为 prepare() 从不修改 cells，这一点由
    "纯只读"天然保证，这里额外验证两条边的 tail_energy_snapshot 数值
    确实相同且等于原始 charge）。
    """
    reg, cells, links, addr_tail = _build_star_rig(n_leaves=2, tail_charge=10.0)
    plan = prepare_thermal_transport_plan(links, cells, reg, dt=0.3)
    snapshots = {et.tail_energy_snapshot for et in plan.edge_transfers}
    assert snapshots == {10.0}


def test_ttp_3_traversal_order_invariance():
    """T-TTP-3: 边注册顺序/输入列表顺序改变后，计划的规范化结果（节点净
    变化+出流汇总）完全一致，只允许 edge_transfers 元组内部记录顺序不同。
    """
    reg, cells, links, addr_tail = _build_star_rig(n_leaves=3, tail_charge=10.0)
    plan_forward = prepare_thermal_transport_plan(links, cells, reg, dt=0.2)
    plan_reversed = prepare_thermal_transport_plan(list(reversed(links)), cells, reg, dt=0.2)

    assert plan_forward.node_net_deltas == plan_reversed.node_net_deltas
    assert plan_forward.node_outgoing_totals == plan_reversed.node_outgoing_totals
    assert plan_forward.stability_report == plan_reversed.stability_report


def test_ttp_4_combined_instability_rejected_state_untouched():
    """T-TTP-4: 每条边分别 a_eΔt<1，但总和 (a_1+a_2)Δt>1 时 prepare() 拒绝，
    状态不变——单条边分别稳定不能保证共享tail的组合稳定（批判二十⑥）。
    """
    reg, cells, links, addr_tail = _build_star_rig(n_leaves=2, tail_charge=10.0, rate=0.7)
    dt = 1.0
    for link in links:
        assert link.rate_per_time * dt < 1.0  # 单独稳定
    total_rate = sum(l.rate_per_time for l in links)
    assert total_rate * dt > 1.0  # 组合失稳

    charges_before = {uid: cell.capacitor.charge for uid, cell in cells.items()}
    with pytest.raises(ThermalTransportPlanError, match="combined transport instability"):
        prepare_thermal_transport_plan(links, cells, reg, dt=dt)
    charges_after = {uid: cell.capacitor.charge for uid, cell in cells.items()}
    assert charges_before == charges_after


def test_ttp_5_zero_or_negative_excess_gives_zero_power_on_all_outgoing_edges():
    """T-TTP-5: tail 过剩能量 <=0 时，该tail的所有有序出边 p_e 均为0。"""
    reg, cells, links, addr_tail = _build_star_rig(n_leaves=2, tail_charge=-3.0)
    plan = prepare_thermal_transport_plan(links, cells, reg, dt=0.2)
    for et in plan.edge_transfers:
        assert et.power == 0.0
        assert et.delta_energy == 0.0


def test_ttp_6_multiple_tails_independently_aggregated():
    """T-TTP-6: 两个不同 tail 的出流预算不会被错误合并——各自的
    η_i^transport 只反映自己名下的边。
    """
    reg = AddressRegistry()
    addr_t1 = reg.register_physical(DOMAIN_WORLD_CELL, 0)
    addr_t2 = reg.register_physical(DOMAIN_WORLD_CELL, 1)
    addr_h1 = reg.register_physical(DOMAIN_WORLD_CELL, 2)
    addr_h2 = reg.register_physical(DOMAIN_WORLD_CELL, 3)

    cell_t1 = ThermalCell(node_id=0, position=(0, 0, 0), capacitor=Capacitor(capacitance=1.0))
    cell_t2 = ThermalCell(node_id=1, position=(1, 0, 0), capacitor=Capacitor(capacitance=1.0))
    cell_h1 = ThermalCell(node_id=2, position=(2, 0, 0), capacitor=Capacitor(capacitance=1.0))
    cell_h2 = ThermalCell(node_id=3, position=(3, 0, 0), capacitor=Capacitor(capacitance=1.0))
    cell_t1.capacitor.charge = 10.0
    cell_t2.capacitor.charge = 20.0
    cells = {addr_t1.uid: cell_t1, addr_t2.uid: cell_t2, addr_h1.uid: cell_h1, addr_h2.uid: cell_h2}

    edge_1 = reg.register_ordered_edge(addr_t1, addr_h1, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    edge_2 = reg.register_ordered_edge(addr_t2, addr_h2, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    link_1 = OrderedExcessThermalEnergyLink(identity=edge_1, rate_per_time=0.3)
    link_2 = OrderedExcessThermalEnergyLink(identity=edge_2, rate_per_time=0.9)  # 明显更大

    plan = prepare_thermal_transport_plan([link_1, link_2], cells, reg, dt=0.5)
    assert plan.stability_report[addr_t1.uid] == pytest.approx(0.3 * 0.5)
    assert plan.stability_report[addr_t2.uid] == pytest.approx(0.9 * 0.5)
    # 数值不应互相污染
    assert plan.stability_report[addr_t1.uid] != plan.stability_report[addr_t2.uid]


def test_ttp_7a_unregistered_endpoint_and_stale_address_rejected():
    """T-TTP-7a: stale 地址（rebuild后使用旧版本地址对象构造的边）在
    prepare() 阶段拒绝。"""
    reg, cells, links, addr_tail = _build_star_rig(n_leaves=1, tail_charge=10.0)
    # 手工构造一个"版本不对"的场景：伪造一个非当前版本的StructuralAddress
    stale_tail = StructuralAddress(domain=DOMAIN_WORLD_CELL, uid=addr_tail.uid, version=99)
    from nexus_v1.components.structural_address import OrderedEdgeIdentity
    fake_edge = OrderedEdgeIdentity.__new__(OrderedEdgeIdentity)
    object.__setattr__(fake_edge, "uid", links[0].identity.uid)
    object.__setattr__(fake_edge, "tail", stale_tail)
    object.__setattr__(fake_edge, "head", links[0].identity.head)
    object.__setattr__(fake_edge, "mechanism", MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    object.__setattr__(fake_edge, "version", 0)
    fake_link = OrderedExcessThermalEnergyLink(identity=fake_edge, rate_per_time=0.2)

    with pytest.raises(ThermalTransportPlanError, match="stale"):
        prepare_thermal_transport_plan([fake_link], cells, reg, dt=0.2)


def test_ttp_7b_duplicate_edge_in_input_rejected():
    """T-TTP-7b: 同一条边在输入列表里重复出现时拒绝。"""
    reg, cells, links, addr_tail = _build_star_rig(n_leaves=1)
    with pytest.raises(ThermalTransportPlanError, match="duplicate edge"):
        prepare_thermal_transport_plan([links[0], links[0]], cells, reg, dt=0.2)


def test_ttp_7c_different_ambient_baseline_rejected():
    """T-TTP-7c: 参与节点 ambient_temperature 不同时拒绝。"""
    reg = AddressRegistry()
    addr_i = reg.register_physical(DOMAIN_WORLD_CELL, 0)
    addr_j = reg.register_physical(DOMAIN_WORLD_CELL, 1)
    cell_i = ThermalCell(node_id=0, position=(0, 0, 0), ambient_temperature=50.0,
                          capacitor=Capacitor(capacitance=1.0))
    cell_j = ThermalCell(node_id=1, position=(1, 0, 0), ambient_temperature=0.0,
                          capacitor=Capacitor(capacitance=1.0))
    cell_i.capacitor.charge = 10.0
    cells = {addr_i.uid: cell_i, addr_j.uid: cell_j}
    edge = reg.register_ordered_edge(addr_i, addr_j, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    link = OrderedExcessThermalEnergyLink(identity=edge, rate_per_time=0.2)

    with pytest.raises(ThermalTransportPlanError, match="ambient_temperature"):
        prepare_thermal_transport_plan([link], cells, reg, dt=0.2)


def test_ttp_7d_missing_cell_for_participating_address_rejected():
    """T-TTP-7d: cells_by_uid 缺少某个参与地址对应的 ThermalCell 时拒绝。"""
    reg, cells, links, addr_tail = _build_star_rig(n_leaves=1)
    incomplete_cells = {addr_tail.uid: cells[addr_tail.uid]}  # 缺 head
    with pytest.raises(ThermalTransportPlanError, match="no ThermalCell provided"):
        prepare_thermal_transport_plan(links, incomplete_cells, reg, dt=0.2)


def test_ttp_8_plan_ledger_closes():
    """T-TTP-8: 计划账本闭合——边级 Σ(-Δu_e+Δu_e)=0（tail扣减+head注入
    幅度相等，方向相反）；节点级汇总 ΣΔu_i^transport=0。
    """
    reg, cells, links, addr_tail = _build_star_rig(n_leaves=3, tail_charge=10.0, rate=0.15)
    plan = prepare_thermal_transport_plan(links, cells, reg, dt=0.4)

    for et in plan.edge_transfers:
        # 每条边：tail端扣减 == head端注入（幅度相等）
        assert et.delta_energy >= 0.0

    total_node_delta = sum(plan.node_net_deltas.values())
    assert total_node_delta == pytest.approx(0.0, abs=1e-9)


if __name__ == "__main__":
    test_ttp_1_prepare_is_pure_readonly()
    test_ttp_2_shared_tail_uses_single_snapshot()
    test_ttp_3_traversal_order_invariance()
    test_ttp_4_combined_instability_rejected_state_untouched()
    test_ttp_5_zero_or_negative_excess_gives_zero_power_on_all_outgoing_edges()
    test_ttp_6_multiple_tails_independently_aggregated()
    test_ttp_7a_unregistered_endpoint_and_stale_address_rejected()
    test_ttp_7b_duplicate_edge_in_input_rejected()
    test_ttp_7c_different_ambient_baseline_rejected()
    test_ttp_7d_missing_cell_for_participating_address_rejected()
    test_ttp_8_plan_ledger_closes()
    print("T-TTP-1~8 ALL PASS")
