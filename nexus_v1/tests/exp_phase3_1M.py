"""EXP-Phase3: STDP Cold-Start — 1M step long-run verification.

Validates that STDP can learn thermotaxis from zero (no hardcoded reflexes)
using the five-patch system: A(AGC-Langevin) + B(TemporalBinding) +
C(YolkSac) + D(DADifferentialGate) + E(Efference monitoring) + Phase1
(process_hunger disabled).

Acceptance criteria (裁定文档 §六):
  CR1: max(Δw_ij) > 0.02    — meaningful weight differentiation
  CR2: Δx(200k) > 0         — net displacement by step 200k
  CR3: min(fill) @1M > 0    — yolk/metabolic survival
  CR4: R_supp < 0.9         — efference not over-suppressing

DT = 0.001s matches η_da=7.5 calibration:
    DA_peak = η_da × Δfill_feeding / dt = 7.5 × 1.08e-4 / 0.001 ≈ 0.81

Run from cell-cc-other/:
    cd /j/cell-cc/cell-cc-other
    PYTHONIOENCODING=utf-8 python nexus_v1/tests/exp_phase3_1M.py
"""
from __future__ import annotations

import os
import sys
import io
import math
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# Reconfigure stdout for UTF-8 only when it has a buffer (interactive/pipe).
# When redirected to a file via >, PYTHONIOENCODING=utf-8 already handles encoding.
if hasattr(sys.stdout, 'buffer') and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── Configuration ───────────────────────────────────────────────────────────
TOTAL_STEPS    = 1_000_000
DT             = 0.001         # matches η_da calibration math
LOG_INTERVAL   =    10_000     # lightweight log every 10k
SNAPSHOT_EVERY =   100_000     # full snapshot every 100k

ACCEPTANCE = {
    'CR1': ('max(Δw_ij) > 0.02',    lambda r: r['dw_max'] > 0.02),
    'CR2': ('Δx(200k) > 0',          lambda r: r['dx_200k'] > 0),
    'CR3': ('min(fill) > 0 @1M',     lambda r: r['fill_min'] > 0),
    'CR4': ('R_supp < 0.9',          lambda r: r['r_supp_max'] < 0.9),
}


# ── Helpers ─────────────────────────────────────────────────────────────────
def dist3(a, b, size=100.0):
    total = 0.0
    for x, y in zip(a, b):
        d = abs(x - y)
        if d > size * 0.5:
            d = size - d
        total += d * d
    return math.sqrt(total)


def bundle_w_mean(bundle):
    weights = [bundle._memristors[r][ci].w
               for r in range(bundle.n_sources)
               for ci in range(bundle.n_targets)]
    return sum(weights) / max(len(weights), 1) if weights else float('nan')


def motor_ema_mean(circuit):
    try:
        emas = [n._activation_ema for n in circuit.motor_neurons.values()]
        return sum(emas) / len(emas) if emas else 0.0
    except Exception:
        return 0.0


def nearest_src_dist(circuit):
    pos = circuit.world.body.position
    dists = [dist3(pos, s.position) for s in circuit.world.heat_sources if s.alive]
    return min(dists) if dists else float('inf')


# ── Main ────────────────────────────────────────────────────────────────────
def run():
    from nexus_v1.circuit.variant_adapter import VariantCircuit

    print("=" * 76)
    print("  EXP-Phase3: STDP Cold-Start — 1M steps")
    print("  Five patches: A(AGC-Langevin) B(TemporalBinding) C(YolkSac)")
    print("                D(DAGate) E(Efference) + Phase1(no hunger reflex)")
    print("=" * 76)

    c = VariantCircuit()

    # ── World ecology ──
    print(f"\n  World ecology: {len(c.world.heat_sources)} heat sources")
    for i, s in enumerate(c.world.heat_sources):
        print(f"    src[{i}] pos={[round(p,1) for p in s.position]} "
              f"E={s.energy:.0f} T={s.temperature} r={s.radius}")
    body_start = list(c.world.body.position)
    d_nearest_init = nearest_src_dist(c)
    print(f"  Body start: {[round(p,1) for p in body_start]}")
    print(f"  Dist to nearest src: {d_nearest_init:.2f}")

    # ── Component summary ──
    print(f"\n  EnergyStore: cap={c.energy_store.config.capacity}, "
          f"fill={c.energy_store.fill_fraction:.3f}")
    print(f"  YolkSac:     level={c.yolk_sac.level:.1f} "
          f"(depletes in ~{c.yolk_sac.level / c.yolk_sac.config.lambda_yolk / 1000:.0f}k steps)")
    print(f"  DAGate:      η_da={c.da_gate.config.eta_da}, "
          f"clip={c.da_gate.config.clip_max}")

    # ── Bundle inventory (col→motor) ──
    bundles_cm = {b.id: b for b in c.bundles_col_to_motor}
    print(f"\n  Col→Motor bundles ({len(bundles_cm)}):")
    for bid in sorted(bundles_cm):
        print(f"    {bid}: w={bundle_w_mean(bundles_cm[bid]):.5f}")

    print(f"\n  Run: {TOTAL_STEPS//1000}k steps, DT={DT}s, "
          f"log every {LOG_INTERVAL//1000}k, snapshot every {SNAPSHOT_EVERY//1000}k")
    print()

    # ── Header ──
    hdr = (f"{'Step':>8} | "
           f"{'fill':>6} {'yolk%':>6} {'DA':>6} {'AGC':>5} | "
           f"{'dist':>6} {'motor':>7} | "
           f"{'Nv':>3} {'H_w':>5} {'R_su':>5} | "
           f"{'sps':>6}")
    print(hdr)
    print("-" * len(hdr))

    # ── Tracking ──
    checkpoints  = []
    snapshots    = []
    fill_vals    = []
    r_supp_vals  = []
    noether_violations_prev = 0
    dx_200k      = None       # displacement by step 200k

    t_start  = time.time()
    t_block  = t_start
    blk_cnt  = 0

    for step in range(TOTAL_STEPS):
        c.step({}, DT)
        blk_cnt += 1

        fill = c.energy_store.fill_fraction
        fill_vals.append(fill)

        if (step + 1) % LOG_INTERVAL == 0:
            da     = c.dopamine.concentration
            agc    = c.agc.gain
            yolk_f = c.yolk_sac.fraction_remaining
            dist   = nearest_src_dist(c)
            mm     = motor_ema_mean(c)
            rsupp  = c._efference_supp_ratio
            r_supp_vals.append(rsupp)

            # ── Entropy ledger snapshot ──
            noether_total = len(c._noether_probe._violations)
            noether_new   = noether_total - noether_violations_prev
            noether_violations_prev = noether_total
            w_ent = c._entropy_probe.summary().get('total_entropy', float('nan'))

            t_now = time.time()
            sps   = blk_cnt / max(t_now - t_block, 1e-6)
            t_block = t_now
            blk_cnt = 0

            cp = {
                'step': step + 1,
                'fill': fill, 'yolk_f': yolk_f,
                'da': da, 'agc': agc,
                'dist': dist, 'motor': mm,
                'rsupp': rsupp, 'sps': sps,
                'noether_new': noether_new,
                'weight_entropy': w_ent,
            }
            checkpoints.append(cp)

            # Displacement by 200k
            if (step + 1) == 200_000:
                body_now = list(c.world.body.position)
                dx_200k = body_now[0] - body_start[0]  # x-axis displacement

            nv_flag = f"!{noether_new}" if noether_new > 0 else f"{noether_new:>2}"
            print(f"{step+1:>8} | "
                  f"{fill:>6.4f} {yolk_f:>6.4f} {da:>6.4f} {agc:>5.3f} | "
                  f"{dist:>6.2f} {mm:>7.5f} | "
                  f"{nv_flag:>3} {w_ent:>5.2f} {rsupp:>5.3f} | "
                  f"{sps:>6.0f}")

            # Alert on Noether violations
            if noether_new > 0:
                viol_detail = c._noether_probe.summary().get('violation_counts', {})
                print(f"  [!NOETHER] +{noether_new} violations this window: {viol_detail}")

            if (step + 1) % SNAPSHOT_EVERY == 0:
                bw = {bid: bundle_w_mean(b) for bid, b in bundles_cm.items()}
                # Energy ledger per-layer
                el = c._energy_ledger.summary()
                se = c._structural_entropy.summary()
                snapshots.append({**cp, 'bundle_weights': bw,
                                  'body_pos': list(c.world.body.position),
                                  'H_struct': se.get('H_struct', 0.0)})
                print(f"  [SNAP @{(step+1)//1000}k] Bundle weights:")
                for bid, w in sorted(bw.items()):
                    print(f"    {bid}: {w:.6f}")
                alive = sum(1 for s in c.world.heat_sources if s.alive)
                print(f"  [SNAP] Living sources: {alive}, "
                      f"Body: {[round(p,1) for p in c.world.body.position]}, "
                      f"yolk={c.yolk_sac.level:.1f}")
                print(f"  [LEDGER] Noether total={noether_total}  "
                      f"H_struct={se.get('H_struct',0):.4f}  "
                      f"weight_entropy={w_ent:.3f}")
                # Layer-by-layer motor activity
                mot_act = el.get('layers', {}).get('L6_Mot', {}).get('avg_activity', 0)
                col_act = el.get('layers', {}).get('L5_Col', {}).get('avg_activity', 0)
                print(f"  [LEDGER] L5_Col_activity={col_act:.5f}  "
                      f"L6_Mot_activity={mot_act:.5f}")

    elapsed = time.time() - t_start

    # ── Final analysis ──────────────────────────────────────────────────────
    final_bw  = {bid: bundle_w_mean(b) for bid, b in bundles_cm.items()}
    fill_min  = min(fill_vals)
    fill_mean = sum(fill_vals) / len(fill_vals)
    r_supp_max = max(r_supp_vals) if r_supp_vals else 0.0

    # Weight differentiation: max pair spread in col→motor bundles
    bw_items = sorted(final_bw.items())
    dw_max = 0.0
    for i in range(len(bw_items)):
        for j in range(i + 1, len(bw_items)):
            dw = abs(bw_items[i][1] - bw_items[j][1])
            if dw > dw_max:
                dw_max = dw

    if dx_200k is None:
        # Didn't reach 200k (shouldn't happen) — compute from checkpoints
        cp_200k = next((cp for cp in checkpoints if cp['step'] == 200_000), None)
        dx_200k = 0.0  # fallback

    print(f"\n{'=' * 76}")
    print(f"  EXP-Phase3 FINAL — {TOTAL_STEPS//1000}k steps, {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"{'=' * 76}")

    print(f"\n[1] ENERGY / METABOLIC:")
    print(f"  fill_min  = {fill_min:.6f}  (CR3: > 0)")
    print(f"  fill_mean = {fill_mean:.4f}")
    print(f"  fill_final= {checkpoints[-1]['fill']:.4f}")
    print(f"  yolk_left = {c.yolk_sac.level:.1f} / {c.yolk_sac.config.initial_level:.0f}  "
          f"({'depleted' if c.yolk_sac.is_depleted else 'remaining'})")

    print(f"\n[2] NEUROMODULATION:")
    da_vals = [cp['da'] for cp in checkpoints]
    print(f"  DA_mean   = {sum(da_vals)/len(da_vals):.4f}")
    print(f"  DA_max    = {max(da_vals):.4f}")
    agc_vals = [cp['agc'] for cp in checkpoints]
    print(f"  AGC_peak  = {max(agc_vals):.4f}")

    print(f"\n[3] BEHAVIOR / MOTOR:")
    print(f"  Δx(200k)  = {dx_200k:+.4f}  (CR2: > 0)")
    motor_vals = [cp['motor'] for cp in checkpoints]
    print(f"  motor_mean= {sum(motor_vals)/len(motor_vals):.5f}")

    print(f"\n[4] STDP WEIGHT EVOLUTION:")
    if snapshots:
        init_bw = snapshots[0]['bundle_weights']
        for bid, w_f in sorted(final_bw.items()):
            w_i = init_bw.get(bid, float('nan'))
            print(f"  {bid}: {w_i:.6f} → {w_f:.6f}  Δ={w_f-w_i:+.6f}")
    print(f"  dw_max    = {dw_max:.6f}  (CR1: > 0.02)")

    print(f"\n[5] EFFERENCE SUPPRESSION:")
    print(f"  R_supp_max= {r_supp_max:.4f}  (CR4: < 0.9)")
    if r_supp_vals:
        print(f"  R_supp_mean={sum(r_supp_vals)/len(r_supp_vals):.4f}")

    print(f"\n[6] DISTANCE TRAJECTORY (sample every 100k):")
    for cp in checkpoints[::10]:
        bar = "→" if cp['dist'] < d_nearest_init else "·"
        print(f"  step {cp['step']:>8d}: dist={cp['dist']:.2f} {bar}")

    # ── Acceptance check ────────────────────────────────────────────────────
    results = {
        'dw_max':    dw_max,
        'dx_200k':   dx_200k,
        'fill_min':  fill_min,
        'r_supp_max': r_supp_max,
    }

    print(f"\n{'=' * 76}")
    print(f"  ACCEPTANCE CRITERIA (裁定文档 §六)")
    print(f"{'=' * 76}")
    n_pass = 0
    for cid, (name, fn) in ACCEPTANCE.items():
        ok = False
        try:
            ok = fn(results)
        except Exception as e:
            name = f"{name} [ERROR: {e}]"
        status = "PASS" if ok else "FAIL"
        n_pass += ok
        print(f"  [{status}] {cid}: {name}")

    n_total = len(ACCEPTANCE)
    if n_pass == n_total:
        verdict = "FULL PASS — STDP thermotaxis emergence VERIFIED"
    elif n_pass >= 3:
        verdict = "PARTIAL — Learning initiated, some criteria unmet"
    elif n_pass >= 2:
        verdict = "DEGRADED — Significant issues; review DA/weight dynamics"
    else:
        verdict = "FAIL — No thermotaxis emergence; check AGC/Binding/YolkSac"

    print(f"\n  {n_pass}/{n_total} criteria passed  ({elapsed:.0f}s total)")
    print(f"  VERDICT: {verdict}")
    print("=" * 76)

    return n_pass, n_total, results, checkpoints


if __name__ == "__main__":
    n_pass, n_total, results, _ = run()
    sys.exit(0 if n_pass == n_total else 1)
