"""T-C1B-1~3：T3-C1 子任务2 下游 Bundle 实际接入正式验收。

方案依据：第二十节 20.2 第2点。诊断脚本 `_diag_t3_c1_bundle_readout.py`
（多个固定 `PYTHONHASHSEED` 对照：0/1/42/7）已确认：`GradedPotentialRelay`
可直接作为 `SynapticBundle` source（新增 `is_alive()`/`config.spiking`/
`.activation` 三个 duck-typing 契约点，不重新触发二次门控）；
`ρ_transport` 相对 `ρ_relay` 的偏置量级为 0.00%~4.52%（依赖具体
`PYTHONHASHSEED`，`seed=0`下两条Bundle的hash扰动恰好都落在"正向偏移→
被weight_max硬clamp抹平"区间，`seed=1/7/42`下稳定复现~3.5%~4.5%偏置），
与 T3-B 已记录的 Memristor hash 扰动量级(~5~8%)同一数量级。本文件把
"中继输出可被Bundle接口读取，但通过Bundle后比例会受固定电导偏置"这一
批判十一③的准确结论转为正式回归测试，容差**容忍**观测到的全部偏置范围
（同T3-B 17.5"测试应适应扰动而非绕过它"的既定方针，不依赖固定seed）。
"""

from __future__ import annotations

from nexus_v1.components.graded_potential_relay import GradedPotentialRelay
from nexus_v1.components.neuron import Neuron, NeuronConfig, ChannelConfig
from nexus_v1.circuit.bundle import BundleConfig, SynapticBundle

DT = 0.001
_W_RELAY_TO_OBSERVER = 0.3
# 多seed实测(0/1/7/42)偏置范围 0.00%~4.52%，同 T3-B 已知Memristor hash扰动
# 量级(~5~8%)。容差取 2x 观测上界的余量，同T3-C0容差标定方法论。
_BUNDLE_BIAS_TOL_PCT = 10.0


def _observer_config(label: str) -> NeuronConfig:
    return NeuronConfig(
        neuron_id=f"c1_observer_{label}",
        region=0x01,
        spiking=False,
        capacitance=0.05,
        r_leak=5.0,
        inertia=1.0,
        channels=[ChannelConfig(name="default", v_threshold=0.0, gm=20.0)],
    )


def _frozen_bundle(bundle_id: str, sources, targets, weight: float) -> SynapticBundle:
    cfg = BundleConfig(
        bundle_id=bundle_id,
        learning_rule="frozen",
        initial_weight=weight,
        weight_max=weight,
        synapse_gain=1.0,
        bundle_role="feedforward",
        remodel_cost_kappa=0.0,
    )
    return SynapticBundle(cfg, sources, targets)


def _build_circuit():
    relay_a, relay_b = GradedPotentialRelay(), GradedPotentialRelay()
    observer_a = Neuron(_observer_config("a"))
    observer_b = Neuron(_observer_config("b"))
    bundle_a = _frozen_bundle("c1_relay_a_to_observer", [relay_a], [observer_a], _W_RELAY_TO_OBSERVER)
    bundle_b = _frozen_bundle("c1_relay_b_to_observer", [relay_b], [observer_b], _W_RELAY_TO_OBSERVER)
    return relay_a, relay_b, observer_a, observer_b, bundle_a, bundle_b


def _drive_and_measure(y_a: float, y_b: float, n_steps: int = 300):
    relay_a, relay_b, observer_a, observer_b, bundle_a, bundle_b = _build_circuit()
    z_a = z_b = 0.0
    i_out_a = i_out_b = 0.0
    for _ in range(n_steps):
        z_a = relay_a.step(y_a, DT)
        z_b = relay_b.step(y_b, DT)
        currents_a = bundle_a.propagate()
        currents_b = bundle_b.propagate()
        i_out_a = currents_a[0] if currents_a else 0.0
        i_out_b = currents_b[0] if currents_b else 0.0
        bundle_a.apply_to_targets(currents_a, DT)
        bundle_b.apply_to_targets(currents_b, DT)
    return {"z_a": z_a, "z_b": z_b, "i_out_a": i_out_a, "i_out_b": i_out_b}


def test_c1b_1_relay_satisfies_bundle_source_contract():
    """T-C1B-1: GradedPotentialRelay 满足 Bundle source 契约，propagate()
    不抛异常，返回非空电流列表。"""
    relay_a, relay_b, _, _, bundle_a, bundle_b = _build_circuit()
    relay_a.step(0.2, DT)
    relay_b.step(0.1, DT)
    currents_a = bundle_a.propagate()
    currents_b = bundle_b.propagate()
    assert len(currents_a) == 1
    assert len(currents_b) == 1
    assert currents_a[0] >= 0.0
    assert currents_b[0] >= 0.0


def test_c1b_2_bundle_output_ratio_tracks_relay_ratio_within_known_bias():
    """T-C1B-2: 经真实下游 Bundle 后，ρ_transport 相对 ρ_relay 的偏置落在
    已知 Memristor hash 扰动量级范围内（不要求零偏置，也不做自动补偿）。
    """
    scenarios = [(1, 1), (2, 1), (3, 1), (1, 2), (1, 3)]
    for (ra, rb) in scenarios:
        m = _drive_and_measure(ra * 0.10, rb * 0.10)
        rho_relay = m["z_a"] / m["z_b"]
        rho_transport = m["i_out_a"] / m["i_out_b"]
        bias_pct = abs(rho_transport / rho_relay - 1.0) * 100
        assert bias_pct <= _BUNDLE_BIAS_TOL_PCT, (
            f"ratio={ra}:{rb} 偏置{bias_pct:.2f}% 超出已知hash扰动容差")


def test_c1b_3_relay_activation_matches_step_return_no_recompute():
    """T-C1B-3: relay.activation 精确等于最近一次 step() 的返回值（不重新
    计算，不引入二次门控——这是 Bundle-source 契约点的核心正确性要求）。
    """
    relay = GradedPotentialRelay()
    for _ in range(50):
        returned = relay.step(0.15, DT)
    assert relay.activation == returned
    assert relay.is_alive() is True
    assert relay.config.spiking is False


if __name__ == "__main__":
    test_c1b_1_relay_satisfies_bundle_source_contract()
    test_c1b_2_bundle_output_ratio_tracks_relay_ratio_within_known_bias()
    test_c1b_3_relay_activation_matches_step_return_no_recompute()
    print("T-C1B-1~3 ALL PASS")
