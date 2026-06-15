"""governance.modeler — Independent Mathematical Simulation.

Provides pre-modification prediction capabilities:
    M1. Parameter sweep: predict behavior over parameter ranges
    M2. Stability analysis: linearized eigenvalue check
    M3. Gain chain trace: signal amplification from input to output
    M4. Baseline prediction: given (bc_current, R, C, V_th) → V_ss
    M5. Coupling gain validation: safe range estimation

Usage:
    modeler = Modeler()
    result = modeler.predict_baseline(bc_current=0.06, r_leak=5.0, v_th=0.3)
    result = modeler.predict_gain_chain(gains=[0.5, 0.8, 10, 10, 10],
                                         thresholds=[0, 0, 0.3, 0.3, 0.3])
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class PredictionResult:
    """Result of a modeling prediction."""
    name: str
    inputs: Dict
    outputs: Dict
    verdict: str  # "SAFE", "WARNING", "DANGEROUS"
    message: str


class Modeler:
    """Independent mathematical simulator for pre-modification validation."""

    def predict_baseline(self, bc_current: float, r_leak: float,
                         v_th: float, capacitance: float = 1.0,
                         gm: float = 1.0, n_slope: float = 1.5,
                         v_thermal: float = 0.026,
                         ) -> PredictionResult:
        """M4: Predict steady-state baseline activity.

        Given neuron parameters, compute:
        - V_ss = bc_current × R_leak (steady-state voltage)
        - activation_superthreshold = gm × (V_ss - V_th) if V_ss > V_th
        - activation_subthreshold = gm × nVT × (exp((V_ss-V_th)/(nVT)) - 1)
        - tau = R × C (time constant)
        """
        v_ss = bc_current * r_leak
        tau = r_leak * capacitance
        nVT = n_slope * v_thermal

        if v_ss > v_th:
            activation = gm * (v_ss - v_th)
            regime = "superthreshold"
        else:
            exponent = (v_ss - v_th) / nVT
            exponent = max(exponent, -50.0)
            activation = gm * nVT * (math.exp(exponent) - 1.0)
            activation = max(activation, 0.0)  # subthreshold leakage >= 0
            regime = "subthreshold"

        verdict = "SAFE"
        if activation < 1e-6:
            verdict = "WARNING"
            msg = (f"Baseline activation ~= 0 ({activation:.2e}). "
                   f"V_ss={v_ss:.3f} << V_th={v_th:.3f}. "
                   f"Need bc_current >= {v_th/r_leak:.4f} for threshold.")
        elif activation > 1.0:
            verdict = "WARNING"
            msg = f"Baseline activation very high ({activation:.3f})."
        else:
            msg = (f"Baseline OK: V_ss={v_ss:.3f}, "
                   f"activation={activation:.4f} ({regime})")

        return PredictionResult(
            name="baseline_prediction",
            inputs={
                'bc_current': bc_current, 'r_leak': r_leak,
                'v_th': v_th, 'C': capacitance,
            },
            outputs={
                'v_ss': v_ss, 'activation': activation,
                'tau': tau, 'regime': regime,
            },
            verdict=verdict,
            message=msg,
        )

    def predict_gain_chain(self, gains: List[float],
                           thresholds: List[float],
                           input_amplitude: float = 1.0,
                           ) -> PredictionResult:
        """M3: Predict signal amplification through a chain of layers.

        Args:
            gains: gain at each layer
            thresholds: activation threshold at each layer
            input_amplitude: initial signal strength

        Returns:
            PredictionResult with per-layer signal values
        """
        signal = input_amplitude
        chain = []
        for i, (g, th) in enumerate(zip(gains, thresholds)):
            pre = signal
            if signal > th:
                signal = g * (signal - th)
            else:
                # Subthreshold (exponential, but approximate as zero for chain)
                nVT = 1.5 * 0.026
                exp_arg = (signal - th) / nVT
                exp_arg = max(exp_arg, -50.0)
                signal = g * nVT * (math.exp(exp_arg) - 1.0)
                signal = max(signal, 0.0)
            chain.append({
                'layer': i, 'gain': g, 'threshold': th,
                'input': pre, 'output': signal,
            })

        total_gain = signal / max(input_amplitude, 1e-10)

        if signal < 1e-6:
            verdict = "DANGEROUS"
            msg = f"Signal dies at layer {len(chain)}. Total gain={total_gain:.2e}"
        elif signal > 100:
            verdict = "DANGEROUS"
            msg = f"Signal explodes. Output={signal:.1f}, gain={total_gain:.1f}×"
        else:
            verdict = "SAFE"
            msg = f"Signal preserved. Output={signal:.4f}, gain={total_gain:.2f}×"

        return PredictionResult(
            name="gain_chain",
            inputs={
                'gains': gains, 'thresholds': thresholds,
                'input': input_amplitude,
            },
            outputs={
                'chain': chain, 'final_signal': signal,
                'total_gain': total_gain,
            },
            verdict=verdict,
            message=msg,
        )

    def predict_penetration(self, m: float, k: float, gamma: float,
                            d: float = 2.0) -> PredictionResult:
        """M5: Predict thermal penetration depth from medium parameters.

        Paper 3: L_pen = sqrt(kappa/gamma), kappa = k/(m*d²)
        """
        kappa = k / (m * d * d)
        if gamma > 1e-10:
            l_pen = math.sqrt(kappa / gamma)
        else:
            l_pen = float('inf')

        v_prop = d * math.sqrt(k / m)
        z = math.sqrt(k * m) / (d * d)

        verdict = "SAFE"
        if l_pen < 0.1:
            verdict = "WARNING"
            msg = f"Very short penetration L_pen={l_pen:.3f}"
        elif l_pen > 1000:
            verdict = "WARNING"
            msg = f"Very long penetration L_pen={l_pen:.1f} (near-infinite)"
        else:
            msg = f"L_pen={l_pen:.2f}, v={v_prop:.3f}, Z={z:.4f}"

        return PredictionResult(
            name="penetration_depth",
            inputs={'m': m, 'k': k, 'gamma': gamma, 'd': d},
            outputs={
                'L_pen': l_pen, 'v_propagation': v_prop,
                'impedance': z, 'kappa': kappa,
            },
            verdict=verdict,
            message=msg,
        )

    def print_prediction(self, result: PredictionResult):
        """Pretty-print a prediction result."""
        icon = {"SAFE": "[OK]", "WARNING": "[!!]", "DANGEROUS": "[XX]"}
        print(f"  {icon.get(result.verdict, '?')} [{result.name}] "
              f"{result.verdict}: {result.message}")
        if result.outputs:
            for k, v in result.outputs.items():
                if k == 'chain':
                    for step in v:
                        print(f"      L{step['layer']}: "
                              f"{step['input']:.4f} →(g={step['gain']}, "
                              f"θ={step['threshold']})→ {step['output']:.4f}")
                else:
                    print(f"      {k}: {v}")
