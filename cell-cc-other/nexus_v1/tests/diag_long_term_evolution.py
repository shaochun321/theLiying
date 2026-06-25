"""EXP-021: Long-Term Evolution Verification — Phase 4 AGC.

Validates four-phase system over 100k steps against EXP-020 baseline:
  EXP-020 Phase 3 结果: Δx=-41.9, Δw=+0.070, fill~0.121
  EXP-021 Phase 4 目标: Δx>0,   Δw>0,    fill>0.1

Scenario (与 EXP-020 保持一致):
  - 热源: x=70, 半径=20
  - 起始: x=50 (by default VariantCircuit)
  - 仅 oto_x 机械输入 (单轴趋热)
  - 步数: 100k

Metrics (每 10k 步记录):
  x_position, fill_fraction, Δw = w_front - w_back,
  AGC_gain, DA_concentration

Usage:
    python -m nexus_v1.tests.diag_long_term_evolution
"""

from __future__ import annotations

import sys
import io
import math
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TOTAL_STEPS = 100_000
LOG_INTERVAL = 10_000
INPUT_FREQ   = 0.5       # Hz — same as EXP-020


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
    print("  EXP-021: Long-Term Evolution Verification — Phase 4 AGC")
    print("=" * 70)

    c = VariantCircuit()

    # ── Bundle pair for Δw ──
    b_front = find_bundle(c, "therm_front_to_move_x")
    b_back  = find_bundle(c, "therm_back_to_move_x")
    if b_front is None or b_back is None:
        print("WARNING: therm differential bundles not found — Δw will be nan")
        print("  Available bundles:")
        for b in c.bundles_col_to_motor:
            print(f"    {b.id}")

    x_start = c.world.body.position[0]

    print(f"\n  Start x={x_start:.2f}")
    print(f"  Steps={TOTAL_STEPS//1000}k, log_interval={LOG_INTERVAL//1000}k")
    heat_info = [(round(s.position[0], 1), round(s.effective_temperature(), 1))
                 for s in c.world.heat_sources[:3]]
    print(f"  Heat sources (x, T): {heat_info}")
    print(f"  AGC τ={c.agc.config.tau_agc:.0f}, g_max={c.agc.config.g_max}")
    print()

    # ── Header ──
    print(f"{'Step':>7} | "
          f"{'x_pos':>7} {'Δx':>7} | "
          f"{'w_front':>8} {'w_back':>8} {'Δw':>8} | "
          f"{'fill':>6} {'DA':>6} {'AGC':>6} |"
          f" {'s_drive':>8}")
    print("-" * 95)

    # ── Tracking ──
    checkpoints = []
    t_total = time.time()

    for step in range(TOTAL_STEPS):
        t = step * 0.001
        oto_x = 200 * math.sin(2 * math.pi * INPUT_FREQ * t)
        c.step({'oto_x': oto_x}, 1.0)

        if (step + 1) % LOG_INTERVAL == 0:
            w_f  = get_weight(b_front)
            w_b  = get_weight(b_back)
            dw   = w_f - w_b if (b_front and b_back) else float('nan')
            x    = c.world.body.position[0]
            dx   = x - x_start
            fill = c.energy_store.fill_fraction
            da   = c.dopamine.concentration
            agc  = c.agc.gain
            sd   = c.agc.s_drive

            checkpoints.append({
                'step': step + 1,
                'x': x, 'dx': dx,
                'w_f': w_f, 'w_b': w_b, 'dw': dw,
                'fill': fill, 'da': da, 'agc': agc, 'sd': sd,
            })

            print(f"{step+1:>7} | "
                  f"{x:>7.2f} {dx:>+7.2f} | "
                  f"{w_f:>8.4f} {w_b:>8.4f} {dw:>+8.4f} | "
                  f"{fill:>6.4f} {da:>6.4f} {agc:>6.3f} |"
                  f" {sd:>8.5f}")

    elapsed = time.time() - t_total

    # ── Final analysis ──
    final = checkpoints[-1]
    print(f"\n{'=' * 70}")
    print(f"  FINAL RESULTS — {TOTAL_STEPS//1000}k steps, {elapsed:.1f}s")
    print(f"{'=' * 70}")

    print(f"\n  Displacement:")
    print(f"    x_start = {x_start:.4f}")
    print(f"    x_final = {final['x']:.4f}")
    print(f"    Δx      = {final['dx']:+.4f}")

    print(f"\n  Weight differential:")
    print(f"    w_front = {final['w_f']:.6f}")
    print(f"    w_back  = {final['w_b']:.6f}")
    print(f"    Δw      = {final['dw']:+.6f}")

    print(f"\n  Metabolic state:")
    print(f"    fill    = {final['fill']:.4f}")
    print(f"    DA      = {final['da']:.4f}")
    print(f"    AGC     = {final['agc']:.4f}")

    # AGC intervention: did AGC ever exceed 1.5?
    agc_peaks = [cp['agc'] for cp in checkpoints]
    agc_intervention = max(agc_peaks)
    agc_intervened = agc_intervention > 1.5
    print(f"\n  AGC peak gain: {agc_intervention:.4f} "
          f"({'intervened' if agc_intervened else 'no intervention'})")

    # Fill floor: did fill stay above 0 throughout?
    fill_vals = [cp['fill'] for cp in checkpoints]
    fill_min  = min(fill_vals)
    fill_ok   = fill_min > 0
    print(f"  Fill min: {fill_min:.4f} ({'ok' if fill_ok else 'hit zero!'})")

    # ── Pass criteria ──
    print(f"\n{'=' * 70}")
    print(f"  PASS CRITERIA (vs EXP-020 baseline: Δx=-41.9, Δw=+0.070)")
    print(f"{'=' * 70}")

    tests = [
        ("P1: Δx > 0 (向热源移动)",      final['dx'] > 0,
         f"Δx={final['dx']:+.4f}  [EXP-020: -41.9]"),
        ("P2: Δw > 0 (剪刀差正向)",       final['dw'] > 0,
         f"Δw={final['dw']:+.6f}  [EXP-020: +0.070]"),
        ("P3: fill > 0.1 at 100k",        final['fill'] > 0.1,
         f"fill={final['fill']:.4f}  [EXP-020: ~0.121]"),
        ("P4: fill never hit zero",        fill_ok,
         f"fill_min={fill_min:.4f}"),
        ("P5: AGC intervened (gain>1.5)", agc_intervened,
         f"peak_gain={agc_intervention:.4f}"),
    ]

    n_pass = 0
    for name, ok, val in tests:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {val}")
        if ok:
            n_pass += 1

    n_total = len(tests)
    print(f"\n  {n_pass}/{n_total} criteria passed, {elapsed:.1f}s total")

    if n_pass == n_total:
        print("  VERDICT: ✅ LONG-TERM EVOLUTION VERIFIED")
    elif n_pass >= 3:
        print("  VERDICT: ⚠️  PARTIAL — system active, some criteria unmet")
    else:
        print("  VERDICT: ❌ FAIL — behavioral regression detected")

    print("=" * 70)
    return n_pass, n_total, checkpoints


if __name__ == "__main__":
    n_pass, n_total, _ = run()
    sys.exit(0 if n_pass == n_total else 1)
