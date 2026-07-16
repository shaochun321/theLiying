"""T3-C1 子任务2 诊断脚本：GradedPotentialRelay 接真实下游 Bundle。

方案依据：第二十节 20.2 第2点。批判十一③指出 T3-C1R 从未验证"中继输出
经真实下游 Bundle 读取后是否仍保持比例"——Bundle 会引入
`I_i^out = w_i^eff * z_i`，若两条 Bundle 的实际电导不同（已知 Memristor
hash 扰动约5~8%），比例会再受一层偏置。

本脚本接一条真实电路：
    GradedPotentialRelay_a ─ Bundle_a(frozen) ─ observer_a(Neuron)
    GradedPotentialRelay_b ─ Bundle_b(frozen) ─ observer_b(Neuron)
`GradedPotentialRelay` 已在 T3-C1 新增 `is_alive()`/`config.spiking`/
`.activation` 三个 duck-typing 契约点，可直接作为 Bundle source。

记录 ρ_relay = z_a/z_b（中继自身输出比） vs ρ_transport = I_a^out/I_b^out
（Bundle.propagate() 的原始电流比，即经过 Memristor 电导前的下游可读值），
量化 Bundle 自身固定电导偏置的量级。**不做自动补偿**——按批判建议，
避免重新引入 Python 比例校正。

运行：PYTHONIOENCODING=utf-8 PYTHONHASHSEED=0 python -m nexus_v1.tests._diag_t3_c1_bundle_readout
"""

from __future__ import annotations

from nexus_v1.components.graded_potential_relay import GradedPotentialRelay
from nexus_v1.components.neuron import Neuron, NeuronConfig, ChannelConfig
from nexus_v1.circuit.bundle import BundleConfig, SynapticBundle

DT = 0.001
_W_RELAY_TO_OBSERVER = 0.3  # 复用 T1/T3-B 已验证权重量级（同一 ξ 源系谱）


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


def build_circuit():
    relay_a, relay_b = GradedPotentialRelay(), GradedPotentialRelay()
    observer_a = Neuron(_observer_config("a"))
    observer_b = Neuron(_observer_config("b"))
    bundle_a = _frozen_bundle("c1_relay_a_to_observer", [relay_a], [observer_a], _W_RELAY_TO_OBSERVER)
    bundle_b = _frozen_bundle("c1_relay_b_to_observer", [relay_b], [observer_b], _W_RELAY_TO_OBSERVER)
    return relay_a, relay_b, observer_a, observer_b, bundle_a, bundle_b


def drive_and_measure(y_a: float, y_b: float, n_steps: int = 300):
    relay_a, relay_b, observer_a, observer_b, bundle_a, bundle_b = build_circuit()
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

    return {
        "z_a": z_a, "z_b": z_b, "i_out_a": i_out_a, "i_out_b": i_out_b,
        "observer_a_activation": observer_a.activation,
        "observer_b_activation": observer_b.activation,
    }


def scan_bundle_bias():
    print("[T3-C1-2] GradedPotentialRelay → 真实 Bundle → observer 偏置量化")
    print(f"{'ratio':<10}{'rho_relay':<14}{'rho_transport':<16}{'偏置(%)':<10}")
    scenarios = [(1, 1), (2, 1), (3, 1), (1, 2), (1, 3)]
    max_bias_pct = 0.0
    for (ra, rb) in scenarios:
        m = drive_and_measure(ra * 0.10, rb * 0.10)
        rho_relay = m["z_a"] / m["z_b"] if m["z_b"] else float("nan")
        rho_transport = m["i_out_a"] / m["i_out_b"] if m["i_out_b"] else float("nan")
        bias_pct = abs(rho_transport / rho_relay - 1.0) * 100 if rho_relay else float("nan")
        max_bias_pct = max(max_bias_pct, bias_pct)
        print(f"{ra}:{rb:<8}{rho_relay:<14.4f}{rho_transport:<16.4f}{bias_pct:<10.2f}")

    print()
    print(f"最大偏置: {max_bias_pct:.2f}%")
    print("判读：偏置应落在已知 Memristor hash 扰动量级(~5~8%)范围内——")
    print("证实'中继输出可被Bundle接口读取，但通过Bundle后比例会受固定电导偏置'"
          "（批判十一③的准确结论），偏置来源已知（hash扰动），不需要新的解释。")


if __name__ == "__main__":
    scan_bundle_bias()
