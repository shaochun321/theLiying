"""T-DTFR-1~6：L2 关系微分只读接口验收（ThermalCell/ThermalLink）。

方案依据：第二十一节 21.7。第十二/十三份交叉比对批判提议给
`ThermalCell`/`ThermalLink` 加只读关系微分接口（温度差/通量/散度/守恒
残差），经代码核实这些量本来就是 `ThermalFieldGraph.step()` 内部已经
在计算的中间量，只是此前未对外暴露——本文件验证新增的只读方法/函数
数值正确、不改变 `step()` 既有行为、与已有的图级/细胞级守恒检查一致。
"""

from __future__ import annotations

from nexus_v1.components.dynamic_thermal_field import (
    ThermalCell, ThermalLink, ThermalFieldGraph,
    node_divergence, incoming_flux, outgoing_flux,
    diffusion_number, is_stable,
)
from nexus_v1.components.semiconductor import Capacitor


def _build_star_graph(kappa=0.1, capacitance=1.0, r_leak_ambient=None):
    """中心节点0 + 两个邻居1,2，两条边：0-1, 0-2。"""
    cells = [
        ThermalCell(node_id=0, position=(0, 0, 0), capacitor=Capacitor(capacitance=capacitance)),
        ThermalCell(node_id=1, position=(1, 0, 0), capacitor=Capacitor(capacitance=capacitance)),
        ThermalCell(node_id=2, position=(-1, 0, 0), capacitor=Capacitor(capacitance=capacitance)),
    ]
    links = [
        ThermalLink(i=0, j=1, kappa=kappa),
        ThermalLink(i=0, j=2, kappa=kappa),
    ]
    return ThermalFieldGraph(cells=cells, links=links, r_leak_ambient=r_leak_ambient)


def test_dtfr_1_temperature_difference_and_heat_flux_alias():
    """T-DTFR-1: temperature_difference() = T_i - T_j；heat_flux 是 flux() 的
    精确别名（同一函数对象，不是重新计算）。
    """
    graph = _build_star_graph()
    graph.cells[0].capacitor.charge = 5.0  # T_0 抬高
    link01 = graph.links[0]

    dt_val = link01.temperature_difference(graph.cells)
    expected = graph.cells[0].temperature - graph.cells[1].temperature
    assert dt_val == expected

    # bound method 对象每次访问都新建，比较底层 __func__ 才是判定"同一实现"的正确方式
    assert link01.heat_flux.__func__ is link01.flux.__func__
    assert link01.heat_flux(graph.cells) == link01.flux(graph.cells)
    assert link01.flux(graph.cells) == link01.kappa * dt_val


def test_dtfr_2_node_divergence_matches_manual_sum():
    """T-DTFR-2: node_divergence() 与手工按边求和结果精确一致（3节点星形图）。"""
    graph = _build_star_graph()
    graph.cells[0].capacitor.charge = 5.0
    graph.cells[1].capacitor.charge = 1.0
    graph.cells[2].capacitor.charge = 2.0

    div = node_divergence(graph)

    j01 = graph.links[0].flux(graph.cells)  # 0->1
    j02 = graph.links[1].flux(graph.cells)  # 0->2
    assert div[0] == j01 + j02
    assert div[1] == -j01
    assert div[2] == -j02
    # 全图散度之和应为0（内部输运守恒，无外部源/漏时）
    assert abs(sum(div.values())) < 1e-12


def test_dtfr_3_incoming_outgoing_flux_consistent_with_divergence():
    """T-DTFR-3: outgoing_flux(i) - incoming_flux(i) == node_divergence(i)。"""
    graph = _build_star_graph()
    graph.cells[0].capacitor.charge = 5.0
    graph.cells[1].capacitor.charge = 1.0
    graph.cells[2].capacitor.charge = 2.0

    div = node_divergence(graph)
    for nid in graph.cells:
        net = outgoing_flux(graph, nid) - incoming_flux(graph, nid)
        assert abs(net - div[nid]) < 1e-12


def test_dtfr_4_closure_residual_zero_after_step_no_source():
    """T-DTFR-4: 无外部注入、有环境泄漏时，每个节点的 closure_residual
    在浮点精度内为 0（step() 内部记账与新增只读账本完全一致）。
    """
    graph = _build_star_graph(r_leak_ambient=50.0)
    graph.cells[0].capacitor.charge = 5.0
    dt = 0.5
    for _ in range(20):
        graph.step(dt)
        for nid in graph.cells:
            r = graph.closure_residual(nid)
            assert r < 1e-9, f"node={nid} closure_residual={r}"


def test_dtfr_5_closure_residual_zero_with_external_injection():
    """T-DTFR-5: 有外部注入时，closure_residual 依然精确为0（S_i项被正确
    记账并纳入残差）。
    """
    graph = _build_star_graph(r_leak_ambient=50.0)
    dt = 0.3
    for step_i in range(20):
        graph.step(dt, external_injections={0: 2.0, 2: 0.5})
        for nid in graph.cells:
            r = graph.closure_residual(nid)
            assert r < 1e-9, f"step={step_i} node={nid} closure_residual={r}"


def test_dtfr_6_existing_diagnostics_unaffected():
    """T-DTFR-6: 新增只读接口不影响既有 diffusion_number()/is_stable()/
    conservation_residual() 的行为（回归确认，同源不冲突）。
    """
    graph = _build_star_graph(kappa=0.05, r_leak_ambient=100.0)
    dt = 0.2
    dn_before = diffusion_number(graph, dt)
    stable_before = is_stable(graph, dt)

    for _ in range(10):
        graph.step(dt, external_injections={0: 1.0})

    assert abs(graph.conservation_residual()) < 1e-9
    dn_after = diffusion_number(graph, dt)
    stable_after = is_stable(graph, dt)
    # 结构本身（拓扑/kappa/capacitance未变）应给出相同的 diffusion_number 值
    assert dn_before == dn_after
    assert stable_before == stable_after


if __name__ == "__main__":
    test_dtfr_1_temperature_difference_and_heat_flux_alias()
    test_dtfr_2_node_divergence_matches_manual_sum()
    test_dtfr_3_incoming_outgoing_flux_consistent_with_divergence()
    test_dtfr_4_closure_residual_zero_after_step_no_source()
    test_dtfr_5_closure_residual_zero_with_external_injection()
    test_dtfr_6_existing_diagnostics_unaffected()
    print("T-DTFR-1~6 ALL PASS")
