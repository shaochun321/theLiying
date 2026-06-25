"""EXP-023: Long-Term Evolutionary Verification — 500k steps.

Pre-run fixes applied (all 12/12 regression PASS):
  1. FIX-AGC-COLDSTART  (64dc0dd): warmup_steps=2000, energy_thr=0.3,
     da_thr=0.05.  Prevents AGC saturation from DA cold-start false signal.
  2. FIX-METABOLIC-COVERAGE (23585a3): heat source radius 20→30.
     8-source spatial coverage 27%→85%.
  3. FIX-TOROIDAL-DISTANCE (97b3bed): _distance() now uses minimum-image
     convention for toroidal world. Eliminates ~45% feeding opportunity loss.
  4. FIX-DRIFT-SPEED (97b3bed): S.13 source drift 0.01→0.001/step.
     Preserves octant coverage during critical early learning period.

Verification criteria:
  C1: fill > 0 throughout (metabolic wall not hit)
  C2: fill @500k > 0.30  (long-term sustainability)
  C3: DA ∈ [0.05, 0.80]  (neuromodulation healthy)
  C4: max(Δw_bundle) > 0.05  (STDP weight differentiation)
  C5: AGC_peak > 1.0  (homeostatic intervention active)
  C6: motor_ema_mean > 0.01  (organism is moving)
  C7: P_net_mean > 0  (positive energy balance)

Run from project root:
    python -X utf8 nexus_v1/tests/exp_023_500k.py
"""
from __future__ import annotations

import sys
import io
import math
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── Configuration ──────────────────────────────────────────────────────────────
TOTAL_STEPS    = 500_000
LOG_INTERVAL   =  10_000   # lightweight log every 10k
SNAPSHOT_EVERY =  50_000   # full snapshot every 50k
DT             = 1.0       # world step dt (matches existing experiments)

PASS_CRITERIA = {
    'C1': ('fill never zero',              lambda r: r['fill_min'] > 0),
    'C2': ('fill @500k > 0.30',            lambda r: r['fill_final'] > 0.30),
    'C3': ('DA_mean ∈ [0.05, 0.80]',       lambda r: 0.05 <= r['da_mean'] <= 0.80),
    'C4': ('max Δw_bundle > 0.05',         lambda r: r['dw_max'] > 0.05),
    'C5': ('AGC_peak > 1.0',               lambda r: r['agc_peak'] > 1.0),
    'C6': ('motor_ema_mean > 0.01',        lambda r: r['motor_mean'] > 0.01),
    'C7': ('P_net_mean > 0',               lambda r: r['p_net_mean'] > 0),
}


# ── Helpers ────────────────────────────────────────────────────────────────────
def dist3(a, b, size=100.0):
    """Toroidal minimum-image distance (matches world._distance fix)."""
    total = 0.0
    for x, y in zip(a, b):
        d = abs(x - y)
        if d > size * 0.5:
            d = size - d
        total += d * d
    return math.sqrt(total)


def bundle_w_mean(bundle):
    """Mean memristor weight across all (source, target) pairs."""
    weights = [bundle._memristors[r][ci].w
               for r in range(bundle.n_sources)
               for ci in range(bundle.n_targets)]
    return sum(weights) / max(len(weights), 1) if weights else float('nan')


def find_bundles_col_motor(circuit):
    """Return {bundle_id: bundle} for col→motor bundles."""
    return {b.id: b for b in circuit.bundles_col_to_motor}


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


# ── Main ───────────────────────────────────────────────────────────────────────
def run():
    from nexus_v1.circuit.variant_adapter import VariantCircuit

    print("=" * 72)
    print("  EXP-023: Long-Term Evolutionary Verification — 500k steps")
    print("=" * 72)

    c = VariantCircuit()

    # Print world ecology summary
    print(f"\n  World ecology:")
    print(f"    Sources: {len(c.world.heat_sources)}")
    for i, s in enumerate(c.world.heat_sources):
        print(f"      src[{i}] pos={[round(p,1) for p in s.position]} "
              f"E={s.energy:.0f} T={s.temperature} r={s.radius}")
    body_pos = list(c.world.body.position)
    print(f"    Body start: {[round(p, 1) for p in body_pos]}")
    d_nearest = nearest_src_dist(c)
    print(f"    Dist to nearest src: {d_nearest:.2f}")

    print(f"\n  EnergyStore: cap={c.energy_store.config.capacity}, "
          f"fill={c.energy_store.fill_fraction:.3f}, "
          f"max_deposit={c.energy_store.config.max_deposit_per_step}")

    # Bundle inventory
    bundles = find_bundles_col_motor(c)
    print(f"\n  Col→Motor bundles ({len(bundles)}):")
    for bid in sorted(bundles):
        print(f"    {bid}")

    print(f"\n  Run: {TOTAL_STEPS//1000}k steps, DT={DT}, "
          f"log every {LOG_INTERVAL//1000}k, snapshot every {SNAPSHOT_EVERY//1000}k")
    print()

    # ── Header ────────────────────────────────────────────────────────────────
    hdr = (f"{'Step':>7} | "
           f"{'fill':>6} {'DA':>6} {'AGC':>6} | "
           f"{'dist':>6} {'motor':>7} | "
           f"{'P_in/s':>8} {'P_out/s':>8} | "
           f"{'steps/s':>7}")
    print(hdr)
    print("-" * len(hdr))

    # ── Tracking state ────────────────────────────────────────────────────────
    checkpoints = []        # lightweight records every LOG_INTERVAL
    snapshots   = []        # full records every SNAPSHOT_EVERY

    fill_vals   = []
    da_vals     = []
    motor_vals  = []
    pin_vals    = []        # P_in per step (proxy: energy_store deposit rate)
    pout_vals   = []        # P_out per step

    prev_level  = c.energy_store.level
    t_start     = time.time()
    t_block     = t_start
    steps_block = 0

    for step in range(TOTAL_STEPS):
        c.step({}, DT)
        steps_block += 1

        # Track level change for P_in / P_out proxy
        cur_level   = c.energy_store.level
        delta       = cur_level - prev_level
        prev_level  = cur_level

        # P_in proxy: deposits always >= 0; drain makes delta negative
        p_in_step  = max(delta, 0)   # net positive component (rough)
        p_out_step = max(-delta, 0)  # net negative component (rough)
        pin_vals.append(p_in_step)
        pout_vals.append(p_out_step)

        fill = c.energy_store.fill_fraction
        da   = c.dopamine.concentration
        mm   = motor_ema_mean(c)

        fill_vals.append(fill)
        da_vals.append(da)
        motor_vals.append(mm)

        if (step + 1) % LOG_INTERVAL == 0:
            agc   = c.agc.gain
            dist  = nearest_src_dist(c)
            t_now = time.time()
            sps   = steps_block / max(t_now - t_block, 1e-6)
            t_block = t_now
            steps_block = 0

            # P_in/P_out mean over last block
            n_blk = LOG_INTERVAL
            pin_mean  = sum(pin_vals[-n_blk:]) / n_blk
            pout_mean = sum(pout_vals[-n_blk:]) / n_blk

            cp = {
                'step': step + 1,
                'fill': fill, 'da': da, 'agc': agc,
                'dist': dist, 'motor': mm,
                'pin': pin_mean, 'pout': pout_mean,
                'sps': sps,
            }
            checkpoints.append(cp)

            print(f"{step+1:>7} | "
                  f"{fill:>6.4f} {da:>6.4f} {agc:>6.3f} | "
                  f"{dist:>6.2f} {mm:>7.5f} | "
                  f"{pin_mean:>8.5f} {pout_mean:>8.5f} | "
                  f"{sps:>7.0f}")

            # Snapshot every SNAPSHOT_EVERY
            if (step + 1) % SNAPSHOT_EVERY == 0:
                bw = {bid: bundle_w_mean(b) for bid, b in bundles.items()}
                snapshots.append({**cp, 'bundle_weights': bw,
                                  'body_pos': list(c.world.body.position)})
                print(f"  [SNAP @{(step+1)//1000}k] Bundle weights:")
                for bid, w in sorted(bw.items()):
                    print(f"    {bid}: {w:.5f}")
                alive_srcs = [s for s in c.world.heat_sources if s.alive]
                print(f"  [SNAP] Living sources: {len(alive_srcs)}, "
                      f"Body: {[round(p,1) for p in c.world.body.position]}")

    elapsed = time.time() - t_start

    # ── Final analysis ─────────────────────────────────────────────────────────
    final_cp  = checkpoints[-1]
    final_bw  = {bid: bundle_w_mean(b) for bid, b in bundles.items()}
    fill_min  = min(fill_vals)
    fill_mean = sum(fill_vals) / len(fill_vals)
    da_mean   = sum(da_vals) / len(da_vals)
    motor_mean = sum(motor_vals) / len(motor_vals)
    agc_peak  = max(cp['agc'] for cp in checkpoints)
    p_net_mean = sum(pin_vals) / len(pin_vals) - sum(pout_vals) / len(pout_vals)

    # Weight differentiation: max spread within any bundle pair (front/back)
    dw_max = 0.0
    bw_items = sorted(final_bw.items())
    for i in range(len(bw_items)):
        for j in range(i+1, len(bw_items)):
            dw = abs(bw_items[i][1] - bw_items[j][1])
            if dw > dw_max:
                dw_max = dw

    # Weight evolution (first snapshot vs final)
    print(f"\n{'=' * 72}")
    print(f"  EXP-023 FINAL RESULTS — {TOTAL_STEPS//1000}k steps, {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"{'=' * 72}")

    print(f"\n[1] ENERGY / METABOLIC:")
    print(f"  fill_min  = {fill_min:.6f}  (must > 0)")
    print(f"  fill_mean = {fill_mean:.4f}")
    print(f"  fill_final= {final_cp['fill']:.4f}  (must > 0.30)")
    print(f"  P_net_mean= {p_net_mean:+.7f}/step  (must > 0)")

    print(f"\n[2] NEUROMODULATION:")
    print(f"  DA_mean   = {da_mean:.4f}  (must ∈ [0.05, 0.80])")
    print(f"  AGC_peak  = {agc_peak:.4f}  (must > 1.0)")

    print(f"\n[3] MOTOR / BEHAVIOR:")
    print(f"  motor_mean= {motor_mean:.5f}  (must > 0.01)")

    print(f"\n[4] STDP WEIGHT EVOLUTION:")
    if snapshots:
        init_bw = snapshots[0]['bundle_weights']
        for bid, w_final in sorted(final_bw.items()):
            w_init = init_bw.get(bid, float('nan'))
            print(f"  {bid}: {w_init:.5f} → {w_final:.5f}  Δ={w_final-w_init:+.5f}")
    print(f"  max_inter_bundle_Δw = {dw_max:.5f}  (must > 0.05)")

    print(f"\n[5] DISTANCE TRAJECTORY (nearest source):")
    for cp in checkpoints[::5]:   # every 50k
        bar = "→" if cp['dist'] < d_nearest else "·"
        print(f"  step {cp['step']:>7d}: dist={cp['dist']:.2f} {bar}")

    # ── Pass/Fail ──────────────────────────────────────────────────────────────
    results = {
        'fill_min':    fill_min,
        'fill_final':  final_cp['fill'],
        'da_mean':     da_mean,
        'dw_max':      dw_max,
        'agc_peak':    agc_peak,
        'motor_mean':  motor_mean,
        'p_net_mean':  p_net_mean,
    }

    print(f"\n{'=' * 72}")
    print(f"  PASS/FAIL CRITERIA")
    print(f"{'=' * 72}")
    n_pass = 0
    for cid, (name, fn) in PASS_CRITERIA.items():
        ok = False
        try:
            ok = fn(results)
        except Exception as e:
            name = f"{name} [ERROR: {e}]"
        status = "PASS" if ok else "FAIL"
        n_pass += ok
        print(f"  [{status}] {cid}: {name}")

    n_total = len(PASS_CRITERIA)
    print(f"\n  {n_pass}/{n_total} criteria passed  ({elapsed:.0f}s total)")

    if n_pass == n_total:
        verdict = "✅ FULL PASS — Long-term evolutionary verification COMPLETE"
    elif n_pass >= 5:
        verdict = "⚠️  PARTIAL — System alive, some criteria unmet"
    elif n_pass >= 3:
        verdict = "⚠️  DEGRADED — Significant issues detected"
    else:
        verdict = "❌ FAIL — Behavioral regression or metabolic collapse"

    print(f"\n  VERDICT: {verdict}")
    print("=" * 72)

    return n_pass, n_total, results, checkpoints


if __name__ == "__main__":
    n_pass, n_total, results, _ = run()
    sys.exit(0 if n_pass == n_total else 1)
