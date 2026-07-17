"""T-OTEL-1~6：P1-B1 单边机制解析比对验收。

方案依据：第二十三节 P1-B0/B1（批判十八）。`OrderedThermalEnergyLink` 只做单边
机制，验证离散解析解 `u_i^{n+1}=(1-aΔt)u_i^n` 精确匹配 + 多步收敛到连续参考解
`u_i(t)=u_i(0)e^{-at}` + 参数边界校验 + 守恒。
"""

from __future__ import annotations

import math

import pytest

from nexus_v1.components.dynamic_thermal_field import ThermalCell
from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.structural_address import (
    AddressRegistry, DOMAIN_WORLD_CELL, MECHANISM_MEDIUM_TRANSPORT,
)
from nexus_v1.components.ordered_thermal_energy_link import (
    OrderedThermalEnergyLink, step_ordered_transport, DEFAULT_RATE_PER_TIME,
)


def _build_link_and_cells(rate=DEFAULT_RATE_PER_TIME, u0=10.0):
    reg = AddressRegistry()
    addr_i = reg.register_physical(DOMAIN_WORLD_CELL, 0)
    addr_j = reg.register_physical(DOMAIN_WORLD_CELL, 1)
    identity = reg.register_ordered_edge(addr_i, addr_j, MECHANISM_MEDIUM_TRANSPORT)
    link = OrderedThermalEnergyLink(identity=identity, rate_per_time=rate)
    cell_i = ThermalCell(node_id=0, position=(0, 0, 0), capacitor=Capacitor(capacitance=1.0))
    cell_j = ThermalCell(node_id=1, position=(1, 0, 0), capacitor=Capacitor(capacitance=1.0))
    cell_i.capacitor.charge = u0
    return link, cell_i, cell_j


def test_otel_1_single_step_matches_analytical_recursion():
    """T-OTEL-1: 单步结果精确匹配 u_i^{n+1}=(1-aΔt)u_i^n，
    u_j^{n+1}=u_j^n+aΔt·u_i^n。
    """
    a, dt, u0 = 0.5, 0.1, 10.0
    link, cell_i, cell_j = _build_link_and_cells(rate=a, u0=u0)
    step_ordered_transport(link, cell_i, cell_j, dt)

    assert cell_i.capacitor.charge == pytest.approx((1 - a * dt) * u0)
    assert cell_j.capacitor.charge == pytest.approx(a * dt * u0)


def test_otel_2_multistep_converges_to_continuous_solution():
    """T-OTEL-2: 多步驱动应收敛到连续参考解 u_i(t)=u_i(0)·e^{-at}，且误差
    应随步长减小而下降（不只是"不发散"）。
    """
    a, u0, total_time = 0.5, 10.0, 2.0

    def run(dt):
        link, cell_i, cell_j = _build_link_and_cells(rate=a, u0=u0)
        n_steps = round(total_time / dt)
        for _ in range(n_steps):
            step_ordered_transport(link, cell_i, cell_j, dt)
        return cell_i.capacitor.charge

    exact = u0 * math.exp(-a * total_time)

    err_coarse = abs(run(0.1) - exact)
    err_fine = abs(run(0.01) - exact)
    err_finer = abs(run(0.001) - exact)

    assert err_coarse > 0.0  # 显式Euler对指数衰减确有离散化误差
    assert err_fine < err_coarse
    assert err_finer < err_fine
    assert err_finer < 1e-3  # 细步长下应充分逼近解析解


def test_otel_3_negative_rate_rejected():
    """T-OTEL-3: rate_per_time < 0 在构造时拒绝。"""
    reg = AddressRegistry()
    addr_i = reg.register_physical(DOMAIN_WORLD_CELL, 0)
    addr_j = reg.register_physical(DOMAIN_WORLD_CELL, 1)
    identity = reg.register_ordered_edge(addr_i, addr_j, MECHANISM_MEDIUM_TRANSPORT)
    with pytest.raises(ValueError, match=">= 0"):
        OrderedThermalEnergyLink(identity=identity, rate_per_time=-0.1)


def test_otel_4_nan_and_inf_rate_rejected():
    """T-OTEL-4: rate_per_time 为 NaN/inf 在构造时拒绝。"""
    reg = AddressRegistry()
    addr_i = reg.register_physical(DOMAIN_WORLD_CELL, 0)
    addr_j = reg.register_physical(DOMAIN_WORLD_CELL, 1)
    identity = reg.register_ordered_edge(addr_i, addr_j, MECHANISM_MEDIUM_TRANSPORT)
    for bad_rate in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="finite"):
            OrderedThermalEnergyLink(identity=identity, rate_per_time=bad_rate)


def test_otel_5_edge_conservation_holds_over_multiple_steps():
    """T-OTEL-5: 边级守恒 R_e=Δu_tail+Δu_head=0，在多步驱动下持续成立。"""
    link, cell_i, cell_j = _build_link_and_cells()
    total_before = cell_i.capacitor.charge + cell_j.capacitor.charge
    for _ in range(50):
        step_ordered_transport(link, cell_i, cell_j, dt=0.05)
        total_after = cell_i.capacitor.charge + cell_j.capacitor.charge
        assert total_after == pytest.approx(total_before, abs=1e-9)


def test_otel_6_power_is_pure_readonly():
    """T-OTEL-6: power() 是纯只读函数——不改变边自身状态，相同输入多次
    调用给出相同输出（无隐藏 callback/无边自身状态漂移）。
    """
    link, _, _ = _build_link_and_cells(rate=0.3)
    p1 = link.power(10.0)
    p2 = link.power(10.0)
    p3 = link.power(10.0)
    assert p1 == p2 == p3 == pytest.approx(3.0)


if __name__ == "__main__":
    test_otel_1_single_step_matches_analytical_recursion()
    test_otel_2_multistep_converges_to_continuous_solution()
    test_otel_3_negative_rate_rejected()
    test_otel_4_nan_and_inf_rate_rejected()
    test_otel_5_edge_conservation_holds_over_multiple_steps()
    test_otel_6_power_is_pure_readonly()
    print("T-OTEL-1~6 ALL PASS")
