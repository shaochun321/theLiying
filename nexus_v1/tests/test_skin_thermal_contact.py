"""T-STC-1~8：P0 世界-身体边界与联合守恒闭合验收。

方案依据：第二十二节 22.5/22.6。第十四份交叉比对批判建议恢复已暂停的
W2B 支线（重命名+范围收紧为 P0），验收范围严格限定：单接触点/3~5个
`ThermalCell`/单动态热源/失败路径测试，不接 ξ^occ/Neuron/Bundle/L3/
坐标组件。
"""

from __future__ import annotations

import pytest

from nexus_v1.components.dynamic_thermal_field import ThermalCell, ThermalLink, ThermalFieldGraph
from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.thermal_source_coupling import DynamicHeatSource, ThermalFieldLocator
from nexus_v1.components.skin_thermal_contact import (
    SkinThermalState, ThermalContact, couple_world_skin_step,
)

_RESIDUAL_TOL = 1e-9


def _build_world(n=4, kappa=0.05, r_leak_ambient=100.0):
    cells = [ThermalCell(node_id=i, position=(float(i), 0, 0),
                          capacitor=Capacitor(capacitance=1.0)) for i in range(n)]
    links = [ThermalLink(i=i, j=i + 1, kappa=kappa) for i in range(n - 1)]
    return ThermalFieldGraph(cells=cells, links=links, r_leak_ambient=r_leak_ambient)


def _build_rig(n=4, power=5.0, energy=1000.0, h=0.1, area=1.0, contact_node=1,
               kappa=0.05, r_leak_ambient=100.0):
    world = _build_world(n=n, kappa=kappa, r_leak_ambient=r_leak_ambient)
    source = DynamicHeatSource(position=(0.0, 0, 0), energy_remaining=energy, power=power)
    locator = ThermalFieldLocator(k=2)
    skin = SkinThermalState(patch_id=0, capacitor=Capacitor(capacitance=1.0))
    contact = ThermalContact(world_node_id=contact_node, skin_patch_id=0, h=h, area=area)
    return world, source, locator, skin, contact


def test_stc_1_joint_conservation_holds_over_time():
    """T-STC-1: 三方能量账本 residual 在浮点精度内持续为0（20步验证）。"""
    world, source, locator, skin, contact = _build_rig()
    for _ in range(20):
        ledger = couple_world_skin_step(source, locator, world, contact, skin, dt=0.2)
        assert ledger.residual < _RESIDUAL_TOL, f"residual={ledger.residual}"


def test_stc_2_skin_temperature_rises_from_world_heat():
    """T-STC-2: 世界节点持续升温后，皮肤温度确实通过接触边升高（真实物理
    交换，非人工赋值）。
    """
    world, source, locator, skin, contact = _build_rig()
    t0 = skin.temperature
    for _ in range(50):
        couple_world_skin_step(source, locator, world, contact, skin, dt=0.2)
    assert skin.temperature > t0


def test_stc_3_disconnected_contact_zero_exchange():
    """T-STC-3: 接触面积为0（"接触断开"）时，皮肤温度不受世界影响
    （world仍正常升温，但ΔE_skin恒为0）。
    """
    world, source, locator, skin, contact = _build_rig(area=0.0)
    for _ in range(20):
        ledger = couple_world_skin_step(source, locator, world, contact, skin, dt=0.2)
        assert ledger.delta_e_skin == 0.0
        assert ledger.residual < _RESIDUAL_TOL
    assert skin.temperature == 0.0
    assert world.cells[1].temperature > 0.0  # 世界侧仍正常被驱动


def test_stc_4_heat_source_exhausted_no_further_injection():
    """T-STC-4: 热源耗尽后 e_source_drawn=0，世界/皮肤状态不再因源注入
    变化（扩散/泄漏仍可继续，但不再有新能量注入）。
    """
    world, source, locator, skin, contact = _build_rig(energy=0.5, power=5.0)
    ledger1 = couple_world_skin_step(source, locator, world, contact, skin, dt=0.2)
    assert ledger1.e_source_drawn > 0.0
    assert source.energy_remaining == 0.0

    ledger2 = couple_world_skin_step(source, locator, world, contact, skin, dt=0.2)
    assert ledger2.e_source_drawn == 0.0
    assert ledger2.residual < _RESIDUAL_TOL


def test_stc_5_instability_rejected_state_untouched():
    """T-STC-5: 不稳定配置在执行前被拒绝，source/world/skin 状态均未被
    触碰（同 T-TSC-7 的"状态未被触碰"验证方法论）。
    """
    world, source, locator, skin, contact = _build_rig(kappa=50.0, r_leak_ambient=None)
    energy_before = source.energy_remaining
    world_energy_before = world.total_energy()
    skin_charge_before = skin.capacitor.charge

    with pytest.raises(ValueError):
        couple_world_skin_step(source, locator, world, contact, skin, dt=1.0)

    assert source.energy_remaining == energy_before
    assert world.total_energy() == world_energy_before
    assert skin.capacitor.charge == skin_charge_before


def test_stc_6_scope_no_xi_occ_neuron_bundle_dependency():
    """T-STC-6: 范围声明——本模块不导入/不依赖 ξ^occ、Neuron、Bundle
    （静态核查 import 表，确认 P0 严格不接这些组件）。
    """
    import nexus_v1.components.skin_thermal_contact as mod
    src = open(mod.__file__, encoding="utf-8").read()
    assert "from nexus_v1.components.neuron" not in src
    assert "from ..components.neuron" not in src
    assert "SynapticBundle" not in src
    assert "thermal_quantum_collectors" not in src


def test_stc_7_multi_cell_world_still_conserves():
    """T-STC-7: 5节点世界（P0范围上限）下联合守恒依然成立。"""
    world, source, locator, skin, contact = _build_rig(n=5, contact_node=2)
    for _ in range(15):
        ledger = couple_world_skin_step(source, locator, world, contact, skin, dt=0.15)
        assert ledger.residual < _RESIDUAL_TOL


def test_stc_8_no_skin_leak_by_default():
    """T-STC-8: 默认不给皮肤加环境泄漏（r_leak_ambient=None），
    e_loss_skin 恒为0（P0 最小默认配置）。
    """
    world, source, locator, skin, contact = _build_rig()
    assert skin.r_leak_ambient is None
    for _ in range(10):
        ledger = couple_world_skin_step(source, locator, world, contact, skin, dt=0.2)
        assert ledger.e_loss_skin == 0.0


if __name__ == "__main__":
    test_stc_1_joint_conservation_holds_over_time()
    test_stc_2_skin_temperature_rises_from_world_heat()
    test_stc_3_disconnected_contact_zero_exchange()
    test_stc_4_heat_source_exhausted_no_further_injection()
    test_stc_5_instability_rejected_state_untouched()
    test_stc_6_scope_no_xi_occ_neuron_bundle_dependency()
    test_stc_7_multi_cell_world_still_conserves()
    test_stc_8_no_skin_leak_by_default()
    print("T-STC-1~8 ALL PASS")
