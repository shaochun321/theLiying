"""T-OETL-1~12：P1-B1.5 有序过剩热能转移机制验收。

方案依据：第二十三节 P1-B1.5（批判十九）。第十九份批判用代码复现验证了两处
P1-B0/B1 真实缺陷：①`capacitor.charge`是相对本节点`ambient_temperature`的
偏差量，不是绝对热能，且可以为负；②`a_e·Δt>1`时递推会让tail翻负号，此前
无任何保护。本文件（原`test_ordered_thermal_energy_link.py`，随组件改名为
`OrderedExcessThermalEnergyLink`同步改名）覆盖修复后的完整验收范围。
"""

from __future__ import annotations

import math

import pytest

from nexus_v1.components.dynamic_thermal_field import ThermalCell
from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.structural_address import (
    AddressRegistry, DOMAIN_WORLD_CELL, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER,
)
from nexus_v1.components.ordered_excess_thermal_energy_link import (
    OrderedExcessThermalEnergyLink, step_ordered_transport, is_single_edge_stable,
    DEFAULT_RATE_PER_TIME, DRIVE_MODE_EXOGENOUS_NORMALIZED,
)


def _build_link_and_cells(rate=DEFAULT_RATE_PER_TIME, u0=10.0, ambient_i=0.0, ambient_j=0.0):
    reg = AddressRegistry()
    addr_i = reg.register_physical(DOMAIN_WORLD_CELL, 0)
    addr_j = reg.register_physical(DOMAIN_WORLD_CELL, 1)
    identity = reg.register_ordered_edge(addr_i, addr_j, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    link = OrderedExcessThermalEnergyLink(identity=identity, rate_per_time=rate)
    cell_i = ThermalCell(node_id=0, position=(0, 0, 0), ambient_temperature=ambient_i,
                          capacitor=Capacitor(capacitance=1.0))
    cell_j = ThermalCell(node_id=1, position=(1, 0, 0), ambient_temperature=ambient_j,
                          capacitor=Capacitor(capacitance=1.0))
    cell_i.capacitor.charge = u0
    return link, cell_i, cell_j


def test_oetl_1_single_step_matches_analytical_recursion():
    """T-OETL-1: 单步结果精确匹配 u_i^{n+1}=(1-aΔt)u_i^n（tail_energy>0区间）。"""
    a, dt, u0 = 0.5, 0.1, 10.0
    link, cell_i, cell_j = _build_link_and_cells(rate=a, u0=u0)
    step_ordered_transport(link, cell_i, cell_j, dt)
    assert cell_i.capacitor.charge == pytest.approx((1 - a * dt) * u0)
    assert cell_j.capacitor.charge == pytest.approx(a * dt * u0)


def test_oetl_2_multistep_converges_to_continuous_solution():
    """T-OETL-2: 多步驱动收敛到 u_i(t)=u_i(0)e^{-at}，误差随步长减小而下降。"""
    a, u0, total_time = 0.5, 10.0, 2.0

    def run(dt):
        link, cell_i, cell_j = _build_link_and_cells(rate=a, u0=u0)
        for _ in range(round(total_time / dt)):
            step_ordered_transport(link, cell_i, cell_j, dt)
        return cell_i.capacitor.charge

    exact = u0 * math.exp(-a * total_time)
    err_coarse = abs(run(0.1) - exact)
    err_fine = abs(run(0.01) - exact)
    err_finer = abs(run(0.001) - exact)
    assert err_coarse > 0.0
    assert err_fine < err_coarse
    assert err_finer < err_fine
    assert err_finer < 1e-3


def test_oetl_3_negative_rate_rejected():
    """T-OETL-3: rate_per_time < 0 在构造时拒绝。"""
    reg = AddressRegistry()
    addr_i = reg.register_physical(DOMAIN_WORLD_CELL, 0)
    addr_j = reg.register_physical(DOMAIN_WORLD_CELL, 1)
    identity = reg.register_ordered_edge(addr_i, addr_j, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    with pytest.raises(ValueError, match=">= 0"):
        OrderedExcessThermalEnergyLink(identity=identity, rate_per_time=-0.1)


def test_oetl_4_nan_and_inf_rate_rejected():
    """T-OETL-4: rate_per_time 为 NaN/inf 在构造时拒绝。"""
    reg = AddressRegistry()
    addr_i = reg.register_physical(DOMAIN_WORLD_CELL, 0)
    addr_j = reg.register_physical(DOMAIN_WORLD_CELL, 1)
    identity = reg.register_ordered_edge(addr_i, addr_j, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)
    for bad_rate in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="finite"):
            OrderedExcessThermalEnergyLink(identity=identity, rate_per_time=bad_rate)


def test_oetl_5_edge_conservation_holds_over_multiple_steps():
    """T-OETL-5: 边级守恒 R_e=Δu_tail+Δu_head=0，多步驱动下持续成立。"""
    link, cell_i, cell_j = _build_link_and_cells()
    total_before = cell_i.capacitor.charge + cell_j.capacitor.charge
    for _ in range(50):
        step_ordered_transport(link, cell_i, cell_j, dt=0.05)
        total_after = cell_i.capacitor.charge + cell_j.capacitor.charge
        assert total_after == pytest.approx(total_before, abs=1e-9)


def test_oetl_6_power_is_pure_readonly():
    """T-OETL-6: power() 是纯只读函数，无隐藏状态。"""
    link, _, _ = _build_link_and_cells(rate=0.3)
    p1 = link.power(10.0)
    p2 = link.power(10.0)
    assert p1 == p2 == pytest.approx(3.0)


def test_oetl_7_negative_tail_charge_clamped_to_zero_transfer():
    """T-OETL-7（批判十九①）: tail charge 为负（低于自身环境基线）时，
    过剩能量钳位为0，转移量为0，tail 保持不变（不产生负功率导致的方向
    翻转）。
    """
    link, cell_i, cell_j = _build_link_and_cells(u0=-5.0)
    q = step_ordered_transport(link, cell_i, cell_j, dt=0.1)
    assert q == 0.0
    assert cell_i.capacitor.charge == pytest.approx(-5.0)
    assert cell_j.capacitor.charge == pytest.approx(0.0)


def test_oetl_8_tail_exactly_zero_transfer_is_zero():
    """T-OETL-8: tail 过剩能量恰好为0时，转移量为0。"""
    link, cell_i, cell_j = _build_link_and_cells(u0=0.0)
    q = step_ordered_transport(link, cell_i, cell_j, dt=0.1)
    assert q == 0.0


def test_oetl_9_boundary_a_dt_equals_one_full_transfer():
    """T-OETL-9（批判十九④边界情形）: a_e·Δt=1 时应允许，且结果是恰好
    全部转移（tail归零）。
    """
    a, dt, u0 = 0.5, 2.0, 10.0  # a*dt = 1.0
    assert a * dt == 1.0
    link, cell_i, cell_j = _build_link_and_cells(rate=a, u0=u0)
    assert is_single_edge_stable(link, dt) is True
    step_ordered_transport(link, cell_i, cell_j, dt)
    assert cell_i.capacitor.charge == pytest.approx(0.0, abs=1e-9)
    assert cell_j.capacitor.charge == pytest.approx(u0, abs=1e-9)


def test_oetl_10_a_dt_over_one_rejected_state_untouched():
    """T-OETL-10（批判十九④，已验证的真实bug回归测试）: a_e·Δt>1 在
    任何状态修改前拒绝，tail/head 均不变——此前会让 tail 翻负号
    （实测 a_e=2.0,dt=1.0 时 u_i 从10变成-10）。
    """
    link, cell_i, cell_j = _build_link_and_cells(rate=2.0, u0=10.0)
    dt = 1.0
    assert is_single_edge_stable(link, dt) is False
    i_before, j_before = cell_i.capacitor.charge, cell_j.capacitor.charge

    with pytest.raises(ValueError, match="stability violated"):
        step_ordered_transport(link, cell_i, cell_j, dt)

    assert cell_i.capacitor.charge == i_before
    assert cell_j.capacitor.charge == j_before


def test_oetl_11_ambient_temperature_mismatch_rejected():
    """T-OETL-11（批判十九①）: tail/head 的 ambient_temperature 不同时
    拒绝执行，状态未被触碰——两端 charge=0 若代表不同实际温度，直接转移
    charge 物理上不对等。
    """
    link, cell_i, cell_j = _build_link_and_cells(ambient_i=100.0, ambient_j=0.0)
    i_before, j_before = cell_i.capacitor.charge, cell_j.capacitor.charge

    with pytest.raises(ValueError, match="ambient_temperature"):
        step_ordered_transport(link, cell_i, cell_j, dt=0.1)

    assert cell_i.capacitor.charge == i_before
    assert cell_j.capacitor.charge == j_before


def test_oetl_12_tail_and_head_identical_rejected_at_identity_construction():
    """T-OETL-12（批判十九§四）: tail 与 head 相同时，构造边身份阶段即拒绝
    （复用 P1-A `OrderedEdgeIdentity` 已有的自环校验，本测试确认该保护
    在 P1-B1.5 场景下仍然有效）。
    """
    reg = AddressRegistry()
    addr_i = reg.register_physical(DOMAIN_WORLD_CELL, 0)
    with pytest.raises(ValueError, match="tail and head must differ"):
        reg.register_ordered_edge(addr_i, addr_i, MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER)


def test_oetl_13_drive_mode_flag_present_and_default():
    """T-OETL-13（批判十九⑦）: `transport_drive_mode` 字段存在，默认为
    `exogenous_normalized`，声明当前不对驱动机制的外部机械功/热力学
    第二定律做资格宣称。
    """
    link, _, _ = _build_link_and_cells()
    assert link.transport_drive_mode == DRIVE_MODE_EXOGENOUS_NORMALIZED


if __name__ == "__main__":
    test_oetl_1_single_step_matches_analytical_recursion()
    test_oetl_2_multistep_converges_to_continuous_solution()
    test_oetl_3_negative_rate_rejected()
    test_oetl_4_nan_and_inf_rate_rejected()
    test_oetl_5_edge_conservation_holds_over_multiple_steps()
    test_oetl_6_power_is_pure_readonly()
    test_oetl_7_negative_tail_charge_clamped_to_zero_transfer()
    test_oetl_8_tail_exactly_zero_transfer_is_zero()
    test_oetl_9_boundary_a_dt_equals_one_full_transfer()
    test_oetl_10_a_dt_over_one_rejected_state_untouched()
    test_oetl_11_ambient_temperature_mismatch_rejected()
    test_oetl_12_tail_and_head_identical_rejected_at_identity_construction()
    test_oetl_13_drive_mode_flag_present_and_default()
    print("T-OETL-1~13 ALL PASS")
