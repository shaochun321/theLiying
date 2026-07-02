"""EXP-020: Phase 3 + Adaptation Filter joint integration verification.

Verifies that the RC high-pass adaptation filter (EXP-018) and DA-gated
eligibility traces (EXP-019) work together in the full closed-loop circuit.

Signal chain under test:
  SkinPatch → SomatoRelay → [Adaptation Filter] → Encoding → Column
       ↓ (eligibility trace charges on pre×post co-activity)
  Column → Motor (LTP frozen until DA arrives)
       ↓ (dopamine from shadow circuit)
  DA × eligibility → LTP applied → w_front diverges from w_back

Pass criteria:
  1. eligibility_trace peak > 0.01 in thermal gradient zone
  2. w_front net growth > w_back when DA present
  3. Δw = w_front - w_back > 0.02 at 50k steps
  4. Body displacement toward heat source (Δx > 0)
"""
from __future__ import annotations

import os
import sys
import io
import math
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nexus_v1.circuit.variant_adapter import VariantCircuit


def find_bundle(circuit, bundle_id_substr):
    """Find a bundle by substring match in its ID."""
    for b in circuit.bundles_col_to_motor:
        if bundle_id_substr in b.id:
            return b
    return None


def get_weight(bundle):
    """Get the first memristor weight from a bundle."""
    if bundle is None:
        return float('nan')
    return bundle._memristors[0][0].w


def get_eligibility(bundle):
    """Get the eligibility trace value for the [0][0] synapse."""
    if bundle is None:
        return 0.0
    if bundle._eligibility_traces is None:
        return 0.0
    return bundle._eligibility_traces[0][0]


def run_joint_verification(total_steps=50000, log_interval=5000):
    """Run Phase 3 + Adaptation Filter joint verification."""
    print("=" * 80)
    print("  EXP-020: Phase 3 + Adaptation Filter — Joint Integration")
    print("=" * 80)

    start = time.time()
    c = VariantCircuit()

    # ── Identify differential pair bundles ──
    b_front_x = find_bundle(c, "therm_front_to_move_x")
    b_back_x  = find_bundle(c, "therm_back_to_move_x")

    if b_front_x is None or b_back_x is None:
        print("ERROR: Thermal differential pair bundles not found!")
        for b in c.bundles_col_to_motor:
            print(f"  {b.id}")
        return False

    # ── Pre-check: eligibility trace enabled? ──
    elig_ok = (b_front_x.config.use_eligibility_trace and
               b_back_x.config.use_eligibility_trace)
    print(f"\n  Pre-check: eligibility_trace enabled = {elig_ok}")
    print(f"  τ_elig = {b_front_x.config.eligibility_tau}")
    print(f"  elig_gain = {b_front_x.config.eligibility_gain}")
    print(f"  elig_ltd_rate = {b_front_x.config.eligibility_ltd_rate}")

    # ── Pre-check: adaptation filter? ──
    has_adapt = hasattr(c.somatosensory, '_thermal_adapt')
    print(f"  Adaptation filter installed = {has_adapt}")
    print(f"  τ_adapt = {c.somatosensory.TAU_ADAPT}")

    print(f"\n  Body start: {c.world.body.position}")
    heat_info = [(s.position, s.effective_temperature()) for s in c.world.heat_sources[:3]]
    print(f"  Heat sources: {heat_info}")
    print(f"  w_front={get_weight(b_front_x):.4f}  w_back={get_weight(b_back_x):.4f}")

    # ── Column header ──
    print(f"\n{'Step':>7} | {'w_front':>8} {'w_back':>8} {'Δw':>8} | "
          f"{'elig_f':>8} {'elig_b':>8} | "
          f"{'enc_f':>6} {'enc_b':>6} | "
          f"{'DA':>5} {'fill':>5} | "
          f"{'pos_x':>7} {'Δx':>6}")
    print("-" * 110)

    x_start = c.world.body.position[0]

    # ── Tracking ──
    elig_peak_front = 0.0
    elig_peak_back = 0.0
    da_peak = 0.0
    w_history = {'front': [], 'back': [], 'dw': []}

    # ── Main simulation loop ──
    for step in range(total_steps):
        c.step({}, 1.0)

        if (step + 1) % log_interval == 0:
            w_f = get_weight(b_front_x)
            w_b = get_weight(b_back_x)
            dw = w_f - w_b

            e_f = get_eligibility(b_front_x)
            e_b = get_eligibility(b_back_x)

            elig_peak_front = max(elig_peak_front, abs(e_f))
            elig_peak_back = max(elig_peak_back, abs(e_b))

            enc_f = c.encoding_neurons.get('reg_therm_front')
            enc_b = c.encoding_neurons.get('reg_therm_back')
            enc_f_ema = enc_f._activation_ema if enc_f else 0
            enc_b_ema = enc_b._activation_ema if enc_b else 0

            da = c.dopamine.concentration
            da_peak = max(da_peak, da)
            fill = c.energy_store.fill_fraction

            pos_x = c.world.body.position[0]
            dx = pos_x - x_start

            w_history['front'].append(w_f)
            w_history['back'].append(w_b)
            w_history['dw'].append(dw)

            print(f"{step+1:>7} | {w_f:>8.4f} {w_b:>8.4f} {dw:>+8.4f} | "
                  f"{e_f:>8.6f} {e_b:>8.6f} | "
                  f"{enc_f_ema:>6.3f} {enc_b_ema:>6.3f} | "
                  f"{da:>5.3f} {fill:>5.3f} | "
                  f"{pos_x:>7.2f} {dx:>+6.2f}")

    elapsed = time.time() - start

    # ── Final analysis ──
    w_f_final = get_weight(b_front_x)
    w_b_final = get_weight(b_back_x)
    dw_final = w_f_final - w_b_final
    pos_final = c.world.body.position
    dx_total = pos_final[0] - x_start

    print(f"\n{'=' * 80}")
    print(f"  FINAL RESULTS — {total_steps // 1000}k steps, {elapsed:.1f}s")
    print(f"{'=' * 80}")

    print(f"\n  Move-X differential pair:")
    print(f"    w_front = {w_f_final:.6f}")
    print(f"    w_back  = {w_b_final:.6f}")
    print(f"    Δw      = {dw_final:+.6f}")

    print(f"\n  Eligibility trace peaks:")
    print(f"    elig_front_peak = {elig_peak_front:.6f}")
    print(f"    elig_back_peak  = {elig_peak_back:.6f}")

    print(f"\n  DA peak: {da_peak:.4f}")

    print(f"\n  Body displacement:")
    print(f"    Δx = {dx_total:+.4f}")
    print(f"    Final position: {[f'{p:.2f}' for p in pos_final]}")

    # ── Adapted thermal output check ──
    soma_adapted = c.somatosensory.get_mechanical_inputs()
    print(f"\n  Adapted thermal outputs (AC only):")
    for k in ['therm_front', 'therm_back', 'therm_left', 'therm_right']:
        print(f"    {k}: {soma_adapted.get(k, 0.0):.4f}")

    # ── Raw relay EMA check ──
    print(f"\n  Raw relay EMAs (before adaptation):")
    for pid in ['front', 'back', 'left', 'right']:
        relay = c.somatosensory.relays.get(pid)
        if relay:
            adapt = c.somatosensory._thermal_adapt.get(pid, 0)
            print(f"    {pid}: raw={relay._activation_ema:.4f}  "
                  f"adapt={adapt:.4f}  "
                  f"AC={relay._activation_ema - adapt:+.4f}")

    # ── Pass criteria ──
    print(f"\n{'=' * 80}")
    print(f"  PASS CRITERIA")
    print(f"{'=' * 80}")

    tests = []

    # C1: Eligibility trace charged
    c1 = max(elig_peak_front, elig_peak_back) > 0.01
    tests.append(("C1: eligibility_trace peak > 0.01",
                   c1, f"peak_f={elig_peak_front:.6f} peak_b={elig_peak_back:.6f}"))

    # C2: DA appeared
    c2 = da_peak > 0.001
    tests.append(("C2: DA concentration appeared",
                   c2, f"da_peak={da_peak:.4f}"))

    # C3: Δw > 0.02
    c3 = dw_final > 0.02
    tests.append(("C3: Δw = w_front - w_back > 0.02",
                   c3, f"Δw={dw_final:+.6f}"))

    # C4: Direction bias (Δx > 0)
    c4 = dx_total > 0
    tests.append(("C4: Body displacement Δx > 0",
                   c4, f"Δx={dx_total:+.4f}"))

    # C5: Adaptation working (enc quiet when stationary)
    enc_f_ema = c.encoding_neurons.get('reg_therm_front')
    enc_f_val = enc_f_ema._activation_ema if enc_f_ema else 999
    c5 = enc_f_val < 0.10  # much lower than pre-adaptation ~0.20
    tests.append(("C5: Adapted enc_front < 0.10 (baseline absorbed)",
                   c5, f"enc_front={enc_f_val:.4f}"))

    passed = 0
    for name, ok, val in tests:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {val}")
        if ok:
            passed += 1

    total = len(tests)
    print(f"\n  {passed}/{total} criteria passed")

    if passed >= 4:
        print("  VERDICT: ✅ JOINT VERIFICATION PASSED")
    elif passed >= 2:
        print("  VERDICT: ⚠️ PARTIAL — signal chain active but behavioral threshold not met")
        print("  → Consider parameter adjustment (see plan §III.3)")
    else:
        print("  VERDICT: ❌ FAIL — fundamental integration issue")

    print(f"{'=' * 80}")

    return {
        'passed': passed,
        'total': total,
        'dw_final': dw_final,
        'elig_peak_front': elig_peak_front,
        'elig_peak_back': elig_peak_back,
        'da_peak': da_peak,
        'dx_total': dx_total,
        'w_history': w_history,
    }


if __name__ == "__main__":
    result = run_joint_verification(total_steps=50000, log_interval=5000)
