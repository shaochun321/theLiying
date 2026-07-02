"""EXP-022: V8 Post-Merge 200k Long-Term Evolution.

Validates system behavior after LangevinNoise injection:
  - Δx > 0 sustained across 100k-200k range
  - fill maintains viable levels (> 0) throughout
  - Langevin noise statistics (σ, autocorrelation)
  - AGC behavior under extended metabolic pressure

Inputs: oto_x = Langevin-injected (via variant_adapter, no manual sine wave)

Usage:
    python -m nexus_v1.tests.diag_v8_200k
"""

from __future__ import annotations

import sys
import io
import math
import time
import statistics

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TOTAL_STEPS  = 200_000
LOG_INTERVAL = 10_000


def find_bundle(circuit, substr):
    for b in circuit.bundles_col_to_motor:
        if substr in b.id:
            return b
    return None


def get_weight(bundle):
    if bundle is None:
        return float('nan')
    return bundle._memristors[0][0].w


def run():
    from nexus_v1.circuit.variant_adapter import VariantCircuit

    print("=" * 70)
    print("  EXP-022: V8 Post-Merge 200k Long-Term Evolution")
    print("  Langevin OU noise replaces mechanical sine wave")
    print("=" * 70)

    c = VariantCircuit()

    b_front = find_bundle(c, "therm_front_to_move_x")
    b_back  = find_bundle(c, "therm_back_to_move_x")
    if b_front is None or b_back is None:
        print("WARNING: therm differential bundles not found — Dw will be nan")

    x_start = c.world.body.position[0]
    heat_info = [(round(s.position[0], 1), round(s.effective_temperature(), 1))
                 for s in c.world.heat_sources[:3]]

    print(f"\n  Start x={x_start:.2f}")
    print(f"  Steps={TOTAL_STEPS//1000}k, log_interval={LOG_INTERVAL//1000}k")
    print(f"  Heat sources (x, T): {heat_info}")
    print(f"  AGC tau={c.agc.config.tau_agc:.0f}, g_max={c.agc.config.g_max}")
    print(f"  Input: empty dict (Langevin injected internally by VariantCircuit)")
    print()

    print(f"{'Step':>7} | "
          f"{'x_pos':>7} {'Dx':>7} | "
          f"{'w_front':>8} {'w_back':>8} {'Dw':>8} | "
          f"{'fill':>6} {'DA':>6} {'AGC':>6} |"
          f" {'eta_rms':>8}")
    print("-" * 95)

    checkpoints = []
    eta_samples  = []   # track Langevin noise amplitude
    fill_history = []
    t_total = time.time()

    for step in range(TOTAL_STEPS):
        # V8: no external sine wave — Langevin noise is injected inside step()
        c.step({}, 1.0)

        # Sample Langevin state (OU process internal state)
        eta_rms_now = math.sqrt(sum(e*e for e in c._langevin._eta) / 3.0)
        eta_samples.append(eta_rms_now)
        fill_history.append(c.energy_store.fill_fraction)

        if (step + 1) % LOG_INTERVAL == 0:
            w_f  = get_weight(b_front)
            w_b  = get_weight(b_back)
            dw   = w_f - w_b if (b_front and b_back) else float('nan')
            x    = c.world.body.position[0]
            dx   = x - x_start
            fill = c.energy_store.fill_fraction
            da   = c.dopamine.concentration
            agc  = c.agc.gain

            # RMS of Langevin noise over this window
            window_eta = eta_samples[-LOG_INTERVAL:]
            eta_rms = math.sqrt(sum(e*e for e in window_eta) / len(window_eta))

            checkpoints.append({
                'step': step + 1,
                'x': x, 'dx': dx,
                'w_f': w_f, 'w_b': w_b, 'dw': dw,
                'fill': fill, 'da': da, 'agc': agc,
                'eta_rms': eta_rms,
            })

            print(f"{step+1:>7} | "
                  f"{x:>7.2f} {dx:>+7.2f} | "
                  f"{w_f:>8.4f} {w_b:>8.4f} {dw:>+8.4f} | "
                  f"{fill:>6.4f} {da:>6.4f} {agc:>6.3f} |"
                  f" {eta_rms:>8.5f}")

    elapsed = time.time() - t_total

    # ── Final analysis ──
    final   = checkpoints[-1]
    cp_100k = next((cp for cp in checkpoints if cp['step'] == 100_000), None)
    cp_200k = checkpoints[-1]

    print(f"\n{'=' * 70}")
    print(f"  FINAL RESULTS — {TOTAL_STEPS//1000}k steps, {elapsed:.1f}s")
    print(f"{'=' * 70}")

    print(f"\n  Displacement:")
    print(f"    x_start  = {x_start:.4f}")
    if cp_100k:
        print(f"    x@100k   = {cp_100k['x']:.4f}  (Dx={cp_100k['dx']:+.4f})")
    print(f"    x_final  = {final['x']:.4f}  (Dx={final['dx']:+.4f})")

    # Check Dx monotonicity 100k→200k
    dx_series = [cp['dx'] for cp in checkpoints]
    dx_100k_vals = [cp['dx'] for cp in checkpoints if cp['step'] >= 100_000]
    dx_increasing_in_second_half = (
        dx_100k_vals[-1] > dx_100k_vals[0] if len(dx_100k_vals) >= 2 else True
    )

    print(f"\n  Weight differential:")
    print(f"    w_front = {final['w_f']:.6f}")
    print(f"    w_back  = {final['w_b']:.6f}")
    print(f"    Dw      = {final['dw']:+.6f}")

    print(f"\n  Metabolic state:")
    fill_vals = [cp['fill'] for cp in checkpoints]
    fill_min  = min(fill_history)
    fill_mean_2nd = statistics.mean([cp['fill'] for cp in checkpoints
                                     if cp['step'] >= 100_000])
    print(f"    fill_min     = {fill_min:.4f}")
    print(f"    fill_mean@100k-200k = {fill_mean_2nd:.4f}")
    print(f"    fill@200k    = {final['fill']:.4f}")
    print(f"    DA@200k      = {final['da']:.4f}")
    print(f"    AGC@200k     = {final['agc']:.4f}")

    print(f"\n  Langevin noise statistics:")
    eta_all = eta_samples
    eta_mean = sum(eta_all) / len(eta_all)
    eta_rms_global = math.sqrt(sum(e*e for e in eta_all) / len(eta_all))
    print(f"    eta_mean (should ~0) = {eta_mean:.6f}")
    print(f"    eta_rms  (OU σ)      = {eta_rms_global:.6f}")
    # Compare eta_rms vs acceleration RMS
    body_acc = c.world.body.acceleration
    acc_mag = math.sqrt(sum(a*a for a in body_acc))
    print(f"    body_acc_mag@end     = {acc_mag:.6f}")

    agc_peaks = [cp['agc'] for cp in checkpoints]
    agc_max   = max(agc_peaks)
    agc_intervened = agc_max > 1.5

    # ── Pass criteria ──
    fill_ok     = fill_min > 0
    fill_viable = fill_mean_2nd > 0.05
    dx_positive = final['dx'] > 0
    dx_100k_pos = (cp_100k['dx'] > 0) if cp_100k else True
    dx_200k_pos = dx_100k_vals[-1] > 0 if dx_100k_vals else True

    print(f"\n{'=' * 70}")
    print(f"  PASS CRITERIA (EXP-022 — V8 Langevin 200k)")
    print(f"{'=' * 70}")

    tests = [
        ("P1: Dx > 0 at 100k",
         dx_100k_pos,
         f"Dx={cp_100k['dx']:+.4f}" if cp_100k else "n/a"),
        ("P2: Dx > 0 at 200k",
         dx_positive,
         f"Dx={final['dx']:+.4f}"),
        ("P3: Dx still growing 100k->200k",
         dx_increasing_in_second_half,
         f"Dx@100k={dx_100k_vals[0]:+.2f} -> Dx@200k={dx_100k_vals[-1]:+.2f}"
         if dx_100k_vals else "n/a"),
        ("P4: fill never hit zero",
         fill_ok,
         f"fill_min={fill_min:.4f}"),
        ("P5: fill mean > 0.05 in 100k-200k",
         fill_viable,
         f"fill_mean={fill_mean_2nd:.4f}"),
        ("P6: AGC intervened (gain>1.5)",
         agc_intervened,
         f"peak_gain={agc_max:.4f}"),
        ("P7: Langevin eta mean ~ 0 (unbiased)",
         abs(eta_mean) < 0.05,
         f"eta_mean={eta_mean:.6f}"),
    ]

    n_pass = 0
    for name, ok, val in tests:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {val}")
        if ok:
            n_pass += 1

    n_total = len(tests)
    print(f"\n  {n_pass}/{n_total} criteria passed, {elapsed:.1f}s total")

    if n_pass >= 6:
        print("  VERDICT: PASS — V8 Langevin system stable at 200k")
    elif n_pass >= 4:
        print("  VERDICT: PARTIAL — system active, metabolic pressure observed")
    else:
        print("  VERDICT: FAIL — behavioral regression detected")

    print("=" * 70)
    return n_pass, n_total, checkpoints


if __name__ == "__main__":
    n_pass, n_total, _ = run()
    sys.exit(0 if n_pass >= 6 else 1)
