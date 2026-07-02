"""Shadow layer probe: free energy, contraction, inner/outer pipelines."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import math
from nexus_v1.circuit.variant_adapter import VariantCircuit

STEPS = 15000
REPORT_EVERY = 1000

def fmt(v):
    if v is None: return "None"
    return f"{v:.4f}"

def run():
    print("Building circuit...")
    c = VariantCircuit()

    shadow = c.shadow_sandbox
    print(f"SHADOW_K={shadow.SHADOW_K}  (updates every {shadow.SHADOW_K} steps)")
    print()

    headers = ["step", "sh_init", "depth",
               "fe_mean", "fe_std", "kappa",
               "sh_enc_act", "sh_col_act", "sh_mot_act",
               "shadow_to_da_w", "xin_to_da_w",
               "da_v", "da_rate"]
    print(",".join(headers))

    for t in range(STEPS + 1):
        # sinusoidal oto_x input
        omega = 2 * math.pi * 0.5
        mech = {"oto_x": 200.0 * math.sin(omega * t * 0.001)}
        c.step(mechanical_inputs=mech, dt=0.001)

        if t % REPORT_EVERY != 0:
            continue

        # ── shadow internals ──
        sh = shadow
        initialized = sh._initialized

        fe_vals = sh._fe_history if hasattr(sh, '_fe_history') else []
        fe_mean = sum(fe_vals) / len(fe_vals) if fe_vals else None
        fe_std  = None
        if fe_vals and len(fe_vals) > 1:
            mu = fe_mean
            fe_std = math.sqrt(sum((x - mu)**2 for x in fe_vals) / len(fe_vals))

        kappa = sh._kappa_history[-1] if hasattr(sh, '_kappa_history') and sh._kappa_history else None

        # shadow neuron activations by layer
        sh_enc = sh_col = sh_mot = 0.0
        if initialized:
            for nid, n in sh.neurons.items():
                a = abs(n.activation)
                if "enc" in nid:   sh_enc = max(sh_enc, a)
                elif "col" in nid: sh_col = max(sh_col, a)
                elif "mot" in nid: sh_mot = max(sh_mot, a)

        # ── outer pipeline: shadow→DA and xin→DA ──
        s2da_w = xin2da_w = "no_bundle"
        if c.bundles_shadow_to_da:
            s2da_w = fmt(c.bundles_shadow_to_da[0].mean_weight())
        if c.bundles_xin_to_da:
            xin2da_w = fmt(c.bundles_xin_to_da[0].mean_weight())

        # DA neuron state
        da_v = da_rate = "—"
        if hasattr(c, '_da_neurons') and c._da_neurons:
            n = c._da_neurons[0]
            da_v    = fmt(n.activation)
            da_rate = fmt(getattr(n, 'release_rate', 0.0))

        row = [
            str(t),
            str(initialized),
            str(shadow._maturation_tick if hasattr(shadow, '_maturation_tick') else "?"),
            fmt(fe_mean), fmt(fe_std) if fe_std is not None else "—",
            fmt(kappa) if kappa is not None else "—",
            fmt(sh_enc), fmt(sh_col), fmt(sh_mot),
            s2da_w, xin2da_w,
            da_v, da_rate,
        ]
        print(",".join(row))

    # ── final: inner shadow bundles ──
    print()
    print("=== Inner shadow bundles ===")
    if shadow._initialized:
        for bid, b in shadow.bundles.items():
            w = b.mean_weight()
            xin = b.config.xin_tension
            print(f"  {bid:40s}  w={w:.4f}  xin={xin:.4f}")
    else:
        print("  (shadow not initialized)")

    print()
    print("=== Shadow state snapshot ===")
    state = shadow.get_state()
    for k, v in state.items():
        if not isinstance(v, (list, dict)):
            print(f"  {k}: {v}")

if __name__ == "__main__":
    run()
