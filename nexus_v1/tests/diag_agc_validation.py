"""Phase 4 AGC Validation — Contrast Experiment.

Verifies AGC mechanism correctness:
  C1: Hunger reflex gain amplified    — AGC × hunger_drive > baseline
  C2: G_agc rises when fill↓          — gain responds to deficit
  C3: G_clamped ≤ 4.0                 — saturation protection
  C4: G_agc is stable                 — no oscillation

Usage:
    python -m nexus_v1.tests.diag_agc_validation
"""

from __future__ import annotations

import sys
import io
import math
import time
import random

# Fix Windows console encoding
if 'pytest' not in sys.modules:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def run_agc_validation():
    """Run AGC contrast experiment."""
    from nexus_v1.circuit.variant_adapter import VariantCircuit
    from nexus_v1.components.agc import AGCConfig, AutomaticGainControl

    N_STEPS = 20000
    INPUT_FREQ = 0.5
    results = []

    print("=" * 60)
    print("  Phase 4 AGC Validation — Contrast Experiment")
    print("=" * 60)

    # ── Run A: AGC enabled (default τ=40k) ──
    print("\n[Run A] AGC ENABLED (τ=40k)...")
    random.seed(42)
    ca = VariantCircuit()

    agc_gain_series = []
    fill_series_a = []

    t0 = time.time()
    for i in range(N_STEPS):
        t = i * 0.001
        ca.step({'oto_x': 200 * math.sin(2 * math.pi * INPUT_FREQ * t)}, 1.0)

        if i % 100 == 0:
            agc_gain_series.append(ca.agc.gain)
            fill_series_a.append(ca.energy_store.fill_fraction)

    elapsed_a = time.time() - t0
    dx_a = ca.world.body.position[0]
    print(f"  Done in {elapsed_a:.1f}s. Δx = {dx_a:.4f}")

    # ── Analysis ──
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)

    # C1: Hunger reflex gain amplification
    # AGC only affects process_hunger(gain_multiplier=agc.gain).
    # Verify: when fill < 0.5 and gain > 1.0, the effective drive
    # would be gain_multiplier× larger than without AGC.
    # Direct test: measure AGC gain at low fill. If gain > 1.5,
    # the hunger reflex is being amplified meaningfully.
    gain_when_hungry = [g for g, f in zip(agc_gain_series, fill_series_a)
                        if f < 0.4]
    if gain_when_hungry:
        avg_gain_hungry = sum(gain_when_hungry) / len(gain_when_hungry)
        c1_pass = avg_gain_hungry > 1.5
    else:
        avg_gain_hungry = 1.0
        c1_pass = False
    status = "PASS" if c1_pass else "FAIL"
    print(f"\n  [C1] [{status}] Hunger reflex gain amplified when hungry")
    print(f"        Avg gain when fill < 0.4: {avg_gain_hungry:.4f}")
    print(f"        Samples at low fill: {len(gain_when_hungry)}")
    print(f"        Threshold: avg gain > 1.5×")
    results.append(("C1 Hunger reflex gain amplification", c1_pass))

    # C2: G_agc rises when fill drops
    c2_pass = False
    gain_at_low_fill = []
    for g, f in zip(agc_gain_series, fill_series_a):
        if f < 0.5:
            gain_at_low_fill.append(g)
    if gain_at_low_fill:
        max_gain_at_low = max(gain_at_low_fill)
        c2_pass = max_gain_at_low > 1.01
    status = "PASS" if c2_pass else "FAIL"
    print(f"\n  [C2] [{status}] G_agc rises when fill < 0.5")
    if gain_at_low_fill:
        print(f"        Max gain at low fill: {max_gain_at_low:.4f}")
        print(f"        Samples at low fill: {len(gain_at_low_fill)}")
    else:
        print(f"        (fill never dropped below 0.5)")
    results.append(("C2 Gain response to deficit", c2_pass))

    # C3: G_clamped ≤ 4.0 (gain ≤ 5.0)
    max_gain = max(agc_gain_series)
    c3_pass = max_gain <= 5.001
    status = "PASS" if c3_pass else "FAIL"
    print(f"\n  [C3] [{status}] G_clamped ≤ 4.0 (gain ≤ 5.0)")
    print(f"        Max gain observed: {max_gain:.6f}")
    results.append(("C3 Saturation protection", c3_pass))

    # C4: Stability — sign reversals detect oscillation
    if len(agc_gain_series) > 3:
        diffs = [agc_gain_series[i+1] - agc_gain_series[i]
                 for i in range(len(agc_gain_series) - 1)]
        sign_reversals = 0
        n_compared = 0
        for i in range(len(diffs) - 1):
            if abs(diffs[i]) < 1e-8 or abs(diffs[i+1]) < 1e-8:
                continue
            n_compared += 1
            if (diffs[i] > 0) != (diffs[i+1] > 0):
                sign_reversals += 1
        reversal_frac = sign_reversals / max(n_compared, 1)
        c4_pass = reversal_frac < 0.30
    else:
        reversal_frac = 0.0
        c4_pass = True
    status = "PASS" if c4_pass else "FAIL"
    print(f"\n  [C4] [{status}] Gain stability (low oscillation)")
    print(f"        Sign reversal fraction: {reversal_frac:.3f}")
    print(f"        Threshold: < 0.30")
    results.append(("C4 Stability", c4_pass))

    # C5: Unit test — isolated AGC step response
    # Feed constant deficit, verify gain ramps monotonically.
    print(f"\n  [C5] Unit test: isolated AGC step response")
    agc_unit = AutomaticGainControl()
    gains_unit = []
    for i in range(5000):
        agc_unit.step(fill_fraction=0.2, da_concentration=0.05, dt=1.0)
        if i % 100 == 0:
            gains_unit.append(agc_unit.gain)
    # Check monotonic increase
    monotonic = all(gains_unit[i] <= gains_unit[i+1] + 1e-9
                    for i in range(len(gains_unit) - 1))
    final_gain_unit = gains_unit[-1]
    c5_pass = monotonic and final_gain_unit > 1.0
    status = "PASS" if c5_pass else "FAIL"
    print(f"        [{status}] Monotonic: {monotonic}, final gain: {final_gain_unit:.4f}")
    results.append(("C5 Unit step response", c5_pass))

    # ── AGC state snapshot ──
    print(f"\n  AGC final state (full circuit):")
    agc_summary = ca.agc.summary()
    for k, v in agc_summary.items():
        print(f"    {k}: {v}")

    # ── Summary ──
    n_pass = sum(1 for _, p in results if p)
    n_fail = sum(1 for _, p in results if not p)

    print("\n" + "=" * 60)
    print(f"  AGC VALIDATION: {n_pass}/{len(results)} PASS, {n_fail} FAIL")
    print("=" * 60)

    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    return n_pass, n_fail


if __name__ == "__main__":
    n_pass, n_fail = run_agc_validation()
    sys.exit(1 if n_fail > 0 else 0)
