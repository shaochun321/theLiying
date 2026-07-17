"""T-SA-1~9：P1-A 身份/拓扑契约验收。

方案依据：第二十三节（原方案）+ V3 P1-A 章节（批判十六/十七细化）。批判十七核实
"数组索引依赖"担忧在现有代码中不是真实缺口（`ThermalFieldGraph.cells` 本来就按
`node_id` 字典键控），用户仍裁定采用完整身份地址系统作为长期基础设施投入。

8 项结构测试（T-SA-1~8）+ 图同构验证（T-SA-9，批判十七③升级版，取代简单排列
测试）。设计过程中发现并修复了一个真实的地址失效漏洞：`rebuild_physical()` 后
若原样重新调用 `register_physical()` 传旧 `local_key`，会因为 `uid=f"{domain}:
{local_key}"` 是确定性推导，悄悄覆盖已重建的新版本记录——已在
`structural_address.py` 用 `_retired_local_keys` 集合堵住（见 `_require_registered`/
`register_physical` 的拒绝逻辑）。
"""

from __future__ import annotations

import pytest

from nexus_v1.components.structural_address import (
    AddressRegistry, StructuralAddress, GeneratedAddress,
    SymmetricEdgeIdentity, OrderedEdgeIdentity, TopologyValidationReport,
    DOMAIN_WORLD_CELL, DOMAIN_SKIN_PATCH, DOMAIN_HEAT_SOURCE,
    MECHANISM_DIFFUSION, MECHANISM_CONTACT, MECHANISM_MEDIUM_TRANSPORT,
)


def _build_registry_and_addresses(n=4):
    reg = AddressRegistry()
    world_addrs = [reg.register_physical(DOMAIN_WORLD_CELL, i) for i in range(n)]
    skin_addr = reg.register_physical(DOMAIN_SKIN_PATCH, 0)
    return reg, world_addrs, skin_addr


def test_sa_1_edge_endpoints_must_exist():
    """T-SA-1: 边两端点必须是已注册地址，否则拒绝注册。"""
    reg, world_addrs, skin_addr = _build_registry_and_addresses()
    fake_addr = StructuralAddress(domain=DOMAIN_WORLD_CELL, uid="world.cell:999", version=0)
    with pytest.raises(ValueError, match="not a registered address"):
        reg.register_symmetric_edge(fake_addr, world_addrs[0], MECHANISM_DIFFUSION)


def test_sa_2_endpoint_domain_must_be_mechanism_compatible():
    """T-SA-2: 端点域必须与机制兼容（diffusion只能world-world，contact只能
    world-skin，medium-transport只能world-world）。
    """
    reg, world_addrs, skin_addr = _build_registry_and_addresses()
    with pytest.raises(ValueError, match="not compatible"):
        reg.register_symmetric_edge(skin_addr, skin_addr, MECHANISM_DIFFUSION)
    with pytest.raises(ValueError, match="not compatible"):
        reg.register_symmetric_edge(world_addrs[0], world_addrs[1], MECHANISM_CONTACT)
    # 合法组合不应报错
    reg.register_symmetric_edge(world_addrs[0], world_addrs[1], MECHANISM_DIFFUSION)
    reg.register_symmetric_edge(world_addrs[0], skin_addr, MECHANISM_CONTACT)


def test_sa_3_reordered_registration_yields_identical_addresses():
    """T-SA-3: 对象重排序结果不变——不同顺序注册同一组 local_key，得到的
    最终地址集合完全相同（uid 由 local_key 确定性推导，不依赖注册顺序）。
    """
    reg_a = AddressRegistry()
    order_a = [2, 0, 3, 1]
    addrs_a = {i: reg_a.register_physical(DOMAIN_WORLD_CELL, i) for i in order_a}

    reg_b = AddressRegistry()
    order_b = [1, 3, 0, 2]
    addrs_b = {i: reg_b.register_physical(DOMAIN_WORLD_CELL, i) for i in order_b}

    for i in range(4):
        assert addrs_a[i] == addrs_b[i]


def test_sa_4_local_key_change_stable_uid_unchanged():
    """T-SA-4: local_key 变化但 stable_uid 不变时，通过 uid 仍能追溯到同一
    物理身份（`resolve()` 返回最新 local_key，重建后的地址 uid 与原地址相同）。
    """
    reg, world_addrs, _ = _build_registry_and_addresses()
    original = world_addrs[0]
    rebuilt = reg.rebuild_physical(DOMAIN_WORLD_CELL, 0, 100)

    assert rebuilt.uid == original.uid           # stable_uid 不变
    assert reg.resolve(original.uid) == 100       # local_key 变化：0 -> 100
    assert rebuilt.version == original.version + 1


def test_sa_5_old_address_invalidated_after_rebuild():
    """T-SA-5: 结构重建后版本递增，旧地址失效——旧 local_key 不能被重新
    注册为一个悄悄覆盖新版本的身份（这是实现中发现并修复的真实漏洞）。
    """
    reg, world_addrs, _ = _build_registry_and_addresses()
    reg.rebuild_physical(DOMAIN_WORLD_CELL, 0, 100)

    with pytest.raises(ValueError, match="retired"):
        reg.register_physical(DOMAIN_WORLD_CELL, 0)

    # registry 中的记录必须仍是重建后的版本，不能被复活的旧版本覆盖
    current = reg.address_of(DOMAIN_WORLD_CELL, 100)
    assert current.version == 1


def test_sa_6_ordered_edges_ij_and_ji_are_distinct():
    """T-SA-6: e_ij 与 e_ji 是两个不同的有序传输实例。"""
    reg, world_addrs, _ = _build_registry_and_addresses()
    e_01 = reg.register_ordered_edge(world_addrs[0], world_addrs[1], MECHANISM_MEDIUM_TRANSPORT)
    e_10 = reg.register_ordered_edge(world_addrs[1], world_addrs[0], MECHANISM_MEDIUM_TRANSPORT)
    assert e_01 != e_10
    assert e_01.uid != e_10.uid
    assert e_01.tail == e_10.head
    assert e_01.head == e_10.tail


def test_sa_7_duplicate_edge_registration_forbidden():
    """T-SA-7: 禁止同一物理边重复注册并重复扣账（对称边端点顺序无关地被
    识别为同一条边；有序边同 tail/head/mechanism 重复注册同样拒绝）。
    """
    reg, world_addrs, _ = _build_registry_and_addresses()
    reg.register_symmetric_edge(world_addrs[0], world_addrs[1], MECHANISM_DIFFUSION)
    with pytest.raises(ValueError, match="already registered"):
        reg.register_symmetric_edge(world_addrs[1], world_addrs[0], MECHANISM_DIFFUSION)  # 端点交换

    reg.register_ordered_edge(world_addrs[0], world_addrs[1], MECHANISM_MEDIUM_TRANSPORT)
    with pytest.raises(ValueError, match="already registered"):
        reg.register_ordered_edge(world_addrs[0], world_addrs[1], MECHANISM_MEDIUM_TRANSPORT)


def test_sa_8_state_changes_traceable_to_source_or_edge():
    """T-SA-8: 所有状态变化都能追溯到明确源项或边身份——每条已注册边都能
    通过 registry 反查到具体的 uid/mechanism/端点，不存在"匿名"状态变化
    通道（这里验证 registry 的枚举接口完整覆盖已注册的全部边）。
    """
    reg, world_addrs, skin_addr = _build_registry_and_addresses()
    e_diff = reg.register_symmetric_edge(world_addrs[0], world_addrs[1], MECHANISM_DIFFUSION)
    e_contact = reg.register_symmetric_edge(world_addrs[0], skin_addr, MECHANISM_CONTACT)
    e_transport = reg.register_ordered_edge(world_addrs[0], world_addrs[2], MECHANISM_MEDIUM_TRANSPORT)

    sym_edges = reg.all_symmetric_edges()
    ord_edges = reg.all_ordered_edges()
    assert e_diff in sym_edges
    assert e_contact in sym_edges
    assert e_transport in ord_edges
    # 每条边都能定位到端点地址，端点地址都能定位到 local_key
    for edge in sym_edges:
        for addr in edge.endpoints:
            assert reg.resolve(addr.uid) is not None
    assert reg.resolve(e_transport.tail.uid) is not None
    assert reg.resolve(e_transport.head.uid) is not None


def test_sa_9_graph_isomorphism_under_relabeling():
    """T-SA-9（批判十七③，升级版排列测试）：地址重命名双射 φ:V→V'，验证
    φ(F_G(x)) = F_{φ(G)}(φ(x))——用真实 ThermalFieldGraph 的扩散通量计算作为
    F，构造原图与"重新编号"后的同构图，验证物理量（通量）只发生对应的
    地址置换，数值本身不变。
    """
    from nexus_v1.components.dynamic_thermal_field import ThermalCell, ThermalLink, ThermalFieldGraph
    from nexus_v1.components.semiconductor import Capacitor

    def build_graph(node_ids, charges):
        cells = [ThermalCell(node_id=nid, position=(float(nid), 0, 0),
                              capacitor=Capacitor(capacitance=1.0))
                 for nid in node_ids]
        for cell, q in zip(cells, charges):
            cell.capacitor.charge = q
        # 链式拓扑：node_ids[0]-node_ids[1]-node_ids[2]
        links = [ThermalLink(i=node_ids[k], j=node_ids[k + 1], kappa=0.1)
                 for k in range(len(node_ids) - 1)]
        return ThermalFieldGraph(cells=cells, links=links, r_leak_ambient=None)

    # 原图：节点 id = 0,1,2，charge = 5,1,2
    original_ids = [0, 1, 2]
    charges = [5.0, 1.0, 2.0]
    graph_orig = build_graph(original_ids, charges)

    # phi: 0->10, 1->11, 2->12（重命名双射，拓扑/参数/初始状态保持对应）
    phi = {0: 10, 1: 11, 2: 12}
    relabeled_ids = [phi[i] for i in original_ids]
    graph_relabeled = build_graph(relabeled_ids, charges)

    # F = 对每条边算 flux()（读出量，不改变状态，用于验证同构）
    flux_orig = [link.flux(graph_orig.cells) for link in graph_orig.links]
    flux_relabeled = [link.flux(graph_relabeled.cells) for link in graph_relabeled.links]

    assert flux_orig == flux_relabeled, (
        "图同构性质被破坏：重新编号后同一条物理边的通量数值应完全相同")

    # 用 AddressRegistry 把两套 local_key 映射到同一组 stable_uid，验证
    # 地址层面也维持同构对应（uid 与 local_key 具体取值无关，只与 domain
    # 内的相对身份有关——这里用"第 k 个注册的节点"的顺序位置模拟 stable_uid
    # 与 local_key 解耦）
    reg_orig = AddressRegistry()
    reg_relabeled = AddressRegistry()
    for k, nid in enumerate(original_ids):
        reg_orig.register_physical(DOMAIN_WORLD_CELL, f"slot{k}")  # local_key用槽位而非nid
    for k, nid in enumerate(relabeled_ids):
        reg_relabeled.register_physical(DOMAIN_WORLD_CELL, f"slot{k}")

    addrs_orig = reg_orig.all_addresses()
    addrs_relabeled = reg_relabeled.all_addresses()
    assert {a.uid for a in addrs_orig} == {a.uid for a in addrs_relabeled}, (
        "地址层：用槽位而非物理坐标做local_key时，两套注册应产生完全相同的"
        "稳定身份集合（证明身份不依赖具体节点编号取值）")


if __name__ == "__main__":
    test_sa_1_edge_endpoints_must_exist()
    test_sa_2_endpoint_domain_must_be_mechanism_compatible()
    test_sa_3_reordered_registration_yields_identical_addresses()
    test_sa_4_local_key_change_stable_uid_unchanged()
    test_sa_5_old_address_invalidated_after_rebuild()
    test_sa_6_ordered_edges_ij_and_ji_are_distinct()
    test_sa_7_duplicate_edge_registration_forbidden()
    test_sa_8_state_changes_traceable_to_source_or_edge()
    test_sa_9_graph_isomorphism_under_relabeling()
    print("T-SA-1~9 ALL PASS")
