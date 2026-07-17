"""T-STC-1~14：P0 世界-身体边界与联合守恒闭合验收 + P1-0 前置收口。

方案依据：第二十二节 22.5/22.6（P0）+ 第二十三节 23.3（P1-0）。第十四份
交叉比对批判建议恢复已暂停的 W2B 支线（重命名+范围收紧为 P0），验收范围
严格限定：单接触点/3~5个`ThermalCell`/单动态热源/失败路径测试，不接
ξ^occ/Neuron/Bundle/L3/坐标组件。第十五份批判确认 P0 机制成立但指出真实
接触边稳定性缺口（已用代码复现验证：小kappa+大h+小皮肤热容场景下
`is_stable(world)=True`但实际发散到~1e25），T-STC-11~14 覆盖修复后的
`is_contact_stable()` 四种失稳场景；T-STC-9/10 补逆向交换与长程收敛。
"""

from __future__ import annotations

import pytest

from nexus_v1.components.dynamic_thermal_field import ThermalCell, ThermalLink, ThermalFieldGraph
from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.thermal_source_coupling import DynamicHeatSource, ThermalFieldLocator
from nexus_v1.components.skin_thermal_contact import (
    SkinThermalState, ThermalContact, couple_world_skin_step,
    contact_stability_numbers, is_contact_stable,
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


# ── P1-0 前置收口新增测试（方案第二十三节 23.3）──

def test_stc_9_reverse_exchange_skin_hotter_than_world():
    """T-STC-9: 皮肤更热时（T_s>T_w），世界获得能量、皮肤失去能量，
    联合账本仍闭合（批判十五§四：防止实现只适配"世界加热皮肤"这一方向）。
    """
    world, source, locator, skin, contact = _build_rig(power=0.0, energy=0.0)
    skin.capacitor.charge = 5.0  # 皮肤初始远高于世界(T_world=0)
    e_world_before = world.total_energy()
    e_skin_before = skin.capacitor.charge

    ledger = couple_world_skin_step(source, locator, world, contact, skin, dt=0.2)

    assert ledger.delta_e_world > 0.0  # 世界获得能量
    assert ledger.delta_e_skin < 0.0   # 皮肤失去能量
    assert ledger.residual < _RESIDUAL_TOL
    assert world.total_energy() > e_world_before
    assert skin.capacitor.charge < e_skin_before


def test_stc_10_long_run_convergence_no_overshoot():
    """T-STC-10: 长程运行覆盖接触时间常数 τ_ws 的多个倍数，ΔT=T_w-T_s
    应单调趋于0，不出现过冲或符号振荡（批判十五§四）。

    隔离场景：世界无环境泄漏、无热源、无扩散干扰（单节点世界），只让
    接触通道单独驱动，精确对照批判给出的解析递推
    ΔT^{n+1}=[1-χ_contact]ΔT^n（否则世界自身的环境泄漏/扩散会叠加进
    ΔT 的演化，破坏"只测接触通道单调性"这个验证目标）。
    """
    world = _build_world(n=1, kappa=0.0, r_leak_ambient=None)
    source = DynamicHeatSource(position=(0.0, 0, 0), energy_remaining=0.0, power=0.0)
    locator = ThermalFieldLocator(k=1)
    skin = SkinThermalState(patch_id=0, capacitor=Capacitor(capacitance=1.0))
    contact = ThermalContact(world_node_id=0, skin_patch_id=0, h=0.1, area=1.0)
    world.cells[0].capacitor.charge = 5.0  # 初始温差
    dt = 0.2
    h_total = contact.h * contact.area
    c_w = world.cells[0].capacitor.capacitance
    c_s = skin.capacitor.capacitance
    tau_ws = 1.0 / (h_total * (1.0 / c_w + 1.0 / c_s))

    n_steps = int(10 * tau_ws / dt)  # 覆盖约10个时间常数，确保充分收敛
    prev_dT = world.cells[0].temperature - skin.temperature
    sign = 1 if prev_dT > 0 else -1
    for _ in range(n_steps):
        couple_world_skin_step(source, locator, world, contact, skin, dt=dt)
        dT = world.cells[0].temperature - skin.temperature
        # 单调性：|dT|不应增大，且不应变号（无振荡）
        assert abs(dT) <= abs(prev_dT) + 1e-9
        assert (dT >= 0) == (sign >= 0) or abs(dT) < 1e-6
        prev_dT = dT
    assert abs(prev_dT) < 0.01  # 10个τ后应基本收敛到0


@pytest.mark.parametrize("h,area,skin_cap,dt", [
    (1000.0, 1.0, 1.0, 0.2),   # 大h
    (0.1, 5000.0, 1.0, 0.2),   # 大area
    (0.1, 1.0, 1e-4, 0.2),     # 小C_s
    (0.1, 1.0, 1.0, 5000.0),   # 大dt
])
def test_stc_11_14_contact_instability_rejected(h, area, skin_cap, dt):
    """T-STC-11~14: 四种接触失稳场景（大h/大area/小C_s/大dt）均在
    source.release()前被 is_contact_stable() 正确拒绝，三方状态未被触碰
    （批判十五§二，同T-STC-5方法论扩展到接触边）。
    """
    world = _build_world(n=4, kappa=0.001, r_leak_ambient=None)  # 世界侧极稳
    source = DynamicHeatSource(position=(0.0, 0, 0), energy_remaining=1000.0, power=5.0)
    locator = ThermalFieldLocator(k=2)
    skin = SkinThermalState(patch_id=0, capacitor=Capacitor(capacitance=skin_cap))
    contact = ThermalContact(world_node_id=1, skin_patch_id=0, h=h, area=area)

    assert not is_contact_stable(contact, world, skin, dt)

    energy_before = source.energy_remaining
    world_energy_before = world.total_energy()
    skin_charge_before = skin.capacitor.charge

    with pytest.raises(ValueError):
        couple_world_skin_step(source, locator, world, contact, skin, dt=dt)

    assert source.energy_remaining == energy_before
    assert world.total_energy() == world_energy_before
    assert skin.capacitor.charge == skin_charge_before


if __name__ == "__main__":
    test_stc_1_joint_conservation_holds_over_time()
    test_stc_2_skin_temperature_rises_from_world_heat()
    test_stc_3_disconnected_contact_zero_exchange()
    test_stc_4_heat_source_exhausted_no_further_injection()
    test_stc_5_instability_rejected_state_untouched()
    test_stc_6_scope_no_xi_occ_neuron_bundle_dependency()
    test_stc_7_multi_cell_world_still_conserves()
    test_stc_8_no_skin_leak_by_default()
    test_stc_9_reverse_exchange_skin_hotter_than_world()
    test_stc_10_long_run_convergence_no_overshoot()
    for _h, _area, _skin_cap, _dt in [
        (1000.0, 1.0, 1.0, 0.2),
        (0.1, 5000.0, 1.0, 0.2),
        (0.1, 1.0, 1e-4, 0.2),
        (0.1, 1.0, 1.0, 5000.0),
    ]:
        test_stc_11_14_contact_instability_rejected(_h, _area, _skin_cap, _dt)
    print("T-STC-1~14 ALL PASS")
