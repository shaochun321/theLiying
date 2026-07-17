"""T-C1-1~6：P1-C1 一步联合不变量验收（批判二十四给出的四项范围，2026-07-17）。

方案依据：`基础生成元执行总纲_V3_2026-07-17.md` P1-C1 小节 + 批判二十四"直接
进入P1-C1，只需完成四项"：夹具A/B真实运行/边-节点-全局三级账本/完整联合图
同构/退化和组合失稳验证。复用P1-C0已实现的`joint_thermal_step_plan.py`
（`JointThermalRuntime`/`prepare_joint_thermal_step`/`apply_joint_thermal_step`），
不新增生产代码之外的机制——本轮只扩展了`JointThermalStepPlan`/
`JointThermalStepReceipt`的分解字段（`node_source_injection`等）供账本核实用。
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


def _build_fixture_a(node_ids=(0, 1, 2, 3, 4), skin_patch_id=1):
    """夹具A（V3已冻结定义）：5世界节点+1热源+2扩散边+2条共享tail的有序出边+
    1接触边+1皮肤+环境泄漏。参数选取使全部η值明显<1（安全区），供"退化一致性/
    三级账本/图同构"三项复用。`node_ids`可传入重命名后的id序列供同构测试用。
    """
    n0, n1, n2, n3, n4 = node_ids
    cells = [ThermalCell(node_id=nid, position=(float(i), 0, 0),
                          capacitor=Capacitor(capacitance=1.0))
             for i, nid in enumerate(node_ids)]
    links = [ThermalLink(i=n0, j=n1, kappa=0.01), ThermalLink(i=n1, j=n2, kappa=0.01)]
    graph = ThermalFieldGraph(cells=cells, links=links, r_leak_ambient=100.0)
    graph.cells[n3].capacitor.charge = 5.0  # 给传输边tail一些可搬运的过剩热量

    skin = SkinThermalState(patch_id=skin_patch_id, capacitor=Capacitor(capacitance=1.0))
    contact = ThermalContact(world_node_id=n0, skin_patch_id=skin_patch_id, h=0.02, area=1.0)
    source = DynamicHeatSource(position=(float(0), 0, 0), energy_remaining=1000.0,
                                power=1.0, efficiency=1.0)
    locator = ThermalFieldLocator(k=1)

    reg = AddressRegistry()
    for nid in node_ids:
        reg.register_physical(DOMAIN_WORLD_CELL, nid)
    addr3 = reg.address_of(DOMAIN_WORLD_CELL, n3)
    addr2 = reg.address_of(DOMAIN_WORLD_CELL, n2)
    addr4 = reg.address_of(DOMAIN_WORLD_CELL, n4)
    edge_32 = reg.register_ordered_edge(addr3, addr2, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    edge_34 = reg.register_ordered_edge(addr3, addr4, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    link_32 = OrderedExcessThermalEnergyLink(identity=edge_32, rate_per_time=0.05)
    link_34 = OrderedExcessThermalEnergyLink(identity=edge_34, rate_per_time=0.05)

    runtime = JointThermalRuntime(world_graph=graph, registry=reg)
    return {
        "runtime": runtime, "graph": graph, "skin": skin, "contact": contact,
        "source": source, "locator": locator, "transport_links": [link_32, link_34],
        "reg": reg, "skin_patch_id": skin_patch_id,
    }


def _build_fixture_b():
    """夹具B（V3已冻结定义）：1世界节点+2皮肤点+2条接触边，专测世界侧
    Σ_s H_is（一个世界节点同时连接两个不同皮肤，而非同一皮肤的冗余边——
    T-JTS-8测的是"同一世界节点+同一皮肤+两条边"，本夹具测"同一世界节点+
    两个不同皮肤"，是Σ_s H_is聚合的另一半覆盖）。
    """
    cells = [ThermalCell(node_id=0, position=(0.0, 0, 0), capacitor=Capacitor(capacitance=1.0))]
    graph = ThermalFieldGraph(cells=cells, links=[], r_leak_ambient=None)
    skin_1 = SkinThermalState(patch_id=1, capacitor=Capacitor(capacitance=1.0))
    skin_2 = SkinThermalState(patch_id=2, capacitor=Capacitor(capacitance=1.0))
    contact_1 = ThermalContact(world_node_id=0, skin_patch_id=1, h=0.02, area=1.0)
    contact_2 = ThermalContact(world_node_id=0, skin_patch_id=2, h=0.03, area=1.0)
    source = DynamicHeatSource(position=(0.0, 0, 0), energy_remaining=1000.0,
                                power=0.0, efficiency=1.0)
    locator = ThermalFieldLocator(k=1)
    reg = AddressRegistry()
    reg.register_physical(DOMAIN_WORLD_CELL, 0)
    runtime = JointThermalRuntime(world_graph=graph, registry=reg)
    return {
        "runtime": runtime, "graph": graph, "skins": {1: skin_1, 2: skin_2},
        "contacts": [contact_1, contact_2], "source": source, "locator": locator,
    }


def test_c1_1_fixture_a_real_run_succeeds():
    """T-C1-1: 夹具A完整真实运行（prepare+apply），不是独立构造矩阵。"""
    fx = _build_fixture_a()
    plan = prepare_joint_thermal_step(
        fx["runtime"], [fx["contact"]], {fx["skin_patch_id"]: fx["skin"]},
        fx["transport_links"], fx["source"], fx["locator"], dt=0.5)
    receipt = apply_joint_thermal_step(fx["runtime"], plan, {fx["skin_patch_id"]: fx["skin"]},
                                        fx["source"])
    assert receipt.residual < 1e-9
    assert all(eta < 1.0 for eta in plan.stability_report.values())


def test_c1_2_fixture_b_skin_side_sigma_h_multiple_skins():
    """T-C1-2: 夹具B——一个世界节点连接两个不同皮肤时，世界侧
    η_world = dt*(H_1+H_2+...)/C_world 正确对两个皮肤的H求和（不是只算
    最后一条接触边）。
    """
    fx = _build_fixture_b()
    plan = prepare_joint_thermal_step(
        fx["runtime"], fx["contacts"], fx["skins"], [], fx["source"], fx["locator"], dt=0.5)

    expected_eta_world = 0.5 * (0.02 + 0.03) / 1.0
    assert plan.stability_report["world:0"] == pytest.approx(expected_eta_world, abs=1e-9)
    # 两个皮肤各自独立核算，互不污染。
    assert plan.stability_report["skin:1"] == pytest.approx(0.5 * 0.02 / 1.0, abs=1e-9)
    assert plan.stability_report["skin:2"] == pytest.approx(0.5 * 0.03 / 1.0, abs=1e-9)

    receipt = apply_joint_thermal_step(fx["runtime"], plan, fx["skins"], fx["source"])
    assert receipt.residual < 1e-9


def test_c1_3_three_level_ledger_closes_on_fixture_a():
    """T-C1-3: 夹具A规模下边级/节点级/全局三级账本全部闭合（扩散+泄漏+
    接触+传输+热源同时激活的真实场景，不是简化玩具电路）。
    """
    fx = _build_fixture_a()
    plan = prepare_joint_thermal_step(
        fx["runtime"], [fx["contact"]], {fx["skin_patch_id"]: fx["skin"]},
        fx["transport_links"], fx["source"], fx["locator"], dt=0.5)
    receipt = apply_joint_thermal_step(fx["runtime"], plan, {fx["skin_patch_id"]: fx["skin"]},
                                        fx["source"])

    for key, r_i in receipt.node_ledger_residuals.items():
        assert r_i < 1e-9, f"节点级账本未闭合: {key}={r_i}"
    for key, r_e in receipt.edge_ledger_residuals.items():
        assert r_e < 1e-9, f"边级账本未闭合: {key}={r_e}"
    assert receipt.residual < 1e-9
    # 三级账本齐全覆盖夹具A的全部5个世界节点+1个皮肤+1接触边+2条共享tail的传输边。
    assert len(receipt.node_ledger_residuals) == 6  # 5 world + 1 skin
    assert len(receipt.edge_ledger_residuals) == 3  # 1 contact + 2 transport（共享tail）


def test_c1_4_full_joint_graph_isomorphism():
    """T-C1-4: 完整联合图同构——地址重命名双射φ覆盖source/skin/contact/
    transport/回执，不能只复用P1-A的世界图同构测试（T-SA-9只测了纯扩散
    通量）。构造原图与"重新编号"后的同构图（拓扑/参数/初始状态对应，仅
    world node_id 与 skin_patch_id 按φ重命名），验证：
    - 计划的世界侧/皮肤侧注入值在φ映射下逐一对应；
    - 联合稳定性 η 值集合相同（只是key的编号不同）；
    - 三级账本残差集合相同；
    - 回执的全局总量（delta_e_world/delta_e_skin/e_source_drawn/residual）
      完全相同（这些是标量总量，天然与具体编号无关）。
    """
    fx_orig = _build_fixture_a(node_ids=(0, 1, 2, 3, 4), skin_patch_id=1)
    # phi: world node_id 平移+10，skin_patch_id 平移+100（重命名双射）。
    phi_world = {0: 10, 1: 11, 2: 12, 3: 13, 4: 14}
    phi_skin = {1: 101}
    fx_relab = _build_fixture_a(node_ids=(10, 11, 12, 13, 14), skin_patch_id=101)

    plan_orig = prepare_joint_thermal_step(
        fx_orig["runtime"], [fx_orig["contact"]], {1: fx_orig["skin"]},
        fx_orig["transport_links"], fx_orig["source"], fx_orig["locator"], dt=0.5)
    plan_relab = prepare_joint_thermal_step(
        fx_relab["runtime"], [fx_relab["contact"]], {101: fx_relab["skin"]},
        fx_relab["transport_links"], fx_relab["source"], fx_relab["locator"], dt=0.5)

    # world_injections: phi(plan_orig) 应逐键对应 plan_relab。
    for nid, current in plan_orig.world_injections.items():
        assert plan_relab.world_injections[phi_world[nid]] == pytest.approx(current, abs=1e-12)

    # skin_injections 同理。
    for pid, current in plan_orig.skin_injections.items():
        assert plan_relab.skin_injections[phi_skin[pid]] == pytest.approx(current, abs=1e-12)

    # 联合稳定性 η 值集合（不看key的具体编号，只看数值集合是否对应）。
    eta_orig_world = sorted(v for k, v in plan_orig.stability_report.items() if k.startswith("world:"))
    eta_relab_world = sorted(v for k, v in plan_relab.stability_report.items() if k.startswith("world:"))
    assert eta_orig_world == pytest.approx(eta_relab_world, abs=1e-12)

    receipt_orig = apply_joint_thermal_step(fx_orig["runtime"], plan_orig, {1: fx_orig["skin"]},
                                             fx_orig["source"])
    receipt_relab = apply_joint_thermal_step(fx_relab["runtime"], plan_relab, {101: fx_relab["skin"]},
                                              fx_relab["source"])

    # 回执的全局总量与具体节点编号无关，必须逐字段相等。
    assert receipt_orig.delta_e_world == pytest.approx(receipt_relab.delta_e_world, abs=1e-12)
    assert receipt_orig.delta_e_skin == pytest.approx(receipt_relab.delta_e_skin, abs=1e-12)
    assert receipt_orig.e_source_drawn == pytest.approx(receipt_relab.e_source_drawn, abs=1e-12)
    assert receipt_orig.residual == pytest.approx(receipt_relab.residual, abs=1e-9)

    # 三级账本残差集合（数值本身，不看key）在φ下也应完全对应。
    node_residuals_orig = sorted(receipt_orig.node_ledger_residuals.values())
    node_residuals_relab = sorted(receipt_relab.node_ledger_residuals.values())
    assert node_residuals_orig == pytest.approx(node_residuals_relab, abs=1e-9)


def test_c1_5_degenerate_consistency_at_fixture_scale():
    """T-C1-5: 退化一致性在夹具A规模下重跑（T-JTS-1已用2节点玩具电路验证
    过同一结论，本测试确认更大拓扑下仍成立）——移除全部传输边后，联合
    结果应与直接调用现有`couple_world_skin_step()`（P0/P1-0已验证）在
    相同扩散拓扑+接触+热源配置下的真实运行数值精确一致。
    """
    fx_joint = _build_fixture_a()
    plan = prepare_joint_thermal_step(
        fx_joint["runtime"], [fx_joint["contact"]], {fx_joint["skin_patch_id"]: fx_joint["skin"]},
        [], fx_joint["source"], fx_joint["locator"], dt=0.5)  # 空传输边列表
    apply_joint_thermal_step(fx_joint["runtime"], plan, {fx_joint["skin_patch_id"]: fx_joint["skin"]},
                              fx_joint["source"])

    fx_p0 = _build_fixture_a()
    couple_world_skin_step(fx_p0["source"], fx_p0["locator"], fx_p0["graph"], fx_p0["contact"],
                            fx_p0["skin"], dt=0.5)

    for nid in fx_joint["graph"].cells:
        assert fx_joint["graph"].cells[nid].capacitor.charge == pytest.approx(
            fx_p0["graph"].cells[nid].capacitor.charge, abs=1e-9)
    assert fx_joint["skin"].capacitor.charge == pytest.approx(fx_p0["skin"].capacitor.charge, abs=1e-9)
    assert fx_joint["source"].energy_remaining == pytest.approx(
        fx_p0["source"].energy_remaining, abs=1e-9)


def test_c1_6_combined_instability_at_fixture_scale():
    """T-C1-6: 组合失稳在夹具A规模下验证——扩散/接触/传输各自单独看都在
    安全区，但把dt调大到联合η超限时，必须在source.release()/任何状态
    写入前拒绝，全部状态（5世界节点+1皮肤+1热源）不变。
    """
    fx = _build_fixture_a()
    world_before = {nid: cell.capacitor.charge for nid, cell in fx["graph"].cells.items()}
    skin_before = fx["skin"].capacitor.charge
    source_before = fx["source"].energy_remaining

    # dt 放大到让 node3（传输tail，a_sum=0.1）的 eta_joint 超过 eta=1.0：
    # eta_3 = dt*((0+0+0.01)/1 + 0.1) —— dt=9 时 eta_3=9*0.11=0.99<1，
    # dt=10 时 eta_3=1.1>1，选 dt=10 触发拒绝。
    with pytest.raises(JointThermalStepError, match="joint instability"):
        prepare_joint_thermal_step(
            fx["runtime"], [fx["contact"]], {fx["skin_patch_id"]: fx["skin"]},
            fx["transport_links"], fx["source"], fx["locator"], dt=10.0, eta=1.0)

    for nid, charge in world_before.items():
        assert fx["graph"].cells[nid].capacitor.charge == charge
    assert fx["skin"].capacitor.charge == skin_before
    assert fx["source"].energy_remaining == source_before


if __name__ == "__main__":
    test_c1_1_fixture_a_real_run_succeeds()
    test_c1_2_fixture_b_skin_side_sigma_h_multiple_skins()
    test_c1_3_three_level_ledger_closes_on_fixture_a()
    test_c1_4_full_joint_graph_isomorphism()
    test_c1_5_degenerate_consistency_at_fixture_scale()
    test_c1_6_combined_instability_at_fixture_scale()
    print("T-C1-1~6 ALL PASS")
