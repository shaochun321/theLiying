"""EXP-Phase4: Directional Cold-Start — 500k step verification.

Adds directional temperature gradient on top of Phase3 patches:
  - Body at [75, 20, 25]: left patch closer to heat source [75, 25, 25]
  - Langevin τ: 0.5→3.0s (macroscopic displacement)
  - YolkSac: 200→500, lambda 0.002→0.001 (500k-step window)
  - lateral_gain: 0.05→0.3 (amplify patch contrast)
  - Column v_peak: 0.25→0.10 (restore firing)
  - DA = max(RPE, Hunger) (non-zero DA floor)

Expected: left patch warmer (y+=left direction) → col_therm_left LTP →
body drifts y+ toward heat source. Directional weight divergence > 0.02.

Acceptance criteria (Phase4):
  DR1: max(Δw_left, Δw_right) > 0.02  — y-axis directional divergence
  DR2: Δy(200k) > 1.0                  — net y displacement toward source
  DR3: min(fill) > 0 @500k             — metabolic survival
  DR4: first divergence before 200k    — within YolkSac window

Run from cell-cc-other/:
    cd /j/cell-cc/cell-cc-other
    PYTHONIOENCODING=utf-8 python nexus_v1/tests/exp_phase4_directional.py
"""
from __future__ import annotations

import os
import sys
import io
import math
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if hasattr(sys.stdout, 'buffer') and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── Configuration ────────────────────────────────────────────────────────────
TOTAL_STEPS    =  500_000
DT             =    0.001
LOG_INTERVAL   =   10_000
SNAPSHOT_EVERY =  100_000

# Body offset puts left patch 3.71 units from heat source vs right at 6.29.
# ΔT ≈ 0.43 (confirmed by tech review): left≈4.38, right≈3.95.
BODY_INIT_POS  = [75.0, 20.0, 25.0]

# Therm bundle IDs (from thermal_differential_map in hebbian.py)
THERM_BUNDLE_IDS = [
    "therm_therm_front_to_move_x",
    "therm_therm_back_to_move_x",
    "therm_therm_left_to_move_y",
    "therm_therm_right_to_move_y",
]

ACCEPTANCE = {
    'DR1': ('max(Δw_left, Δw_right) > 0.02', lambda r: r['dw_y_spread'] > 0.02),
    'DR2': ('Δy(200k) > 1.0',                 lambda r: r['dy_200k'] > 1.0),
    'DR3': ('min(fill) > 0 @500k',            lambda r: r['fill_min'] > 0),
    'DR4': ('divergence before 200k steps',   lambda r: r['diverge_step'] < 200_000),
}


# ── Helpers ──────────────────────────────────────────────────────────────────
def dist3(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


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


def col_therm_ema(circuit, name):
    """EMA of thermal column neuron (e.g. 'therm_left')."""
    try:
        return circuit.column_neurons[name]._activation_ema
    except (KeyError, AttributeError):
        return float('nan')


# ── Main ─────────────────────────────────────────────────────────────────────
def run():
    from nexus_v1.circuit.variant_adapter import VariantCircuit

    print("=" * 78)
    print("  EXP-Phase4: Directional Cold-Start — 500k steps")
    print("  Patches: P0(v_peak→0.10) + τ(3.0s) + YolkSac(500/0.001)")
    print("           + lateral_gain(0.3) + DA=max(RPE,Hunger)")
    print("  Body offset: [75,20,25] — left patch closer to heat source")
    print("=" * 78)

    c = VariantCircuit()

    # Override body position (tech review §Q3: safe to set after __init__)
    c.world.body.position = list(BODY_INIT_POS)
    body_start = list(c.world.body.position)

    # ── World ecology ──
    print(f"\n  Heat sources: {len(c.world.heat_sources)}")
    for i, s in enumerate(c.world.heat_sources):
        print(f"    src[{i}] pos={[round(p,1) for p in s.position]} T={s.temperature} r={s.radius}")
    d_init = nearest_src_dist(c)
    print(f"  Body start: {[round(p,1) for p in body_start]}  dist={d_init:.2f}")

    # ── Confirm ΔT via world.temperature_at (env temp, not skin equilibrium) ──
    try:
        env_temps = {}
        for patch in c.world.body.skin_patches:
            wp = patch.world_position(c.world.body)
            env_temps[patch.patch_id] = c.world.temperature_at(wp)
        print(f"  Env temps at patches: {', '.join(f'{k}={v:.3f}' for k,v in env_temps.items())}")
        if 'left' in env_temps and 'right' in env_temps:
            print(f"  ΔT(left-right) = {env_temps['left']-env_temps['right']:+.4f}  "
                  f"(expected ≈ +0.43, left=hot)")
    except Exception as e:
        print(f"  Env temps: unavailable ({e})")

    # ── Component summary ──
    print(f"\n  YolkSac: level={c.yolk_sac.level:.0f}, "
          f"lambda={c.yolk_sac.config.lambda_yolk}/step, "
          f"depletes in ~{c.yolk_sac.level/c.yolk_sac.config.lambda_yolk/1000:.0f}k steps")
    print(f"  lateral_gain={c.somatosensory.LATERAL_GAIN:.2f}")
    print(f"  DA gate η_da={c.da_gate.config.eta_da}, clip={c.da_gate.config.clip_max}")
    print(f"  col v_peak (therm_front): {c.column_neurons['therm_front'].config.v_peak:.2f}")

    # ── Therm bundle inventory ──
    bundles_therm = {}
    for b in c.bundles_col_to_motor:
        if b.id in THERM_BUNDLE_IDS:
            bundles_therm[b.id] = b
    print(f"\n  Therm bundles ({len(bundles_therm)}):")
    for bid in THERM_BUNDLE_IDS:
        if bid in bundles_therm:
            print(f"    {bid}: w_init={bundle_w_mean(bundles_therm[bid]):.5f}")
        else:
            print(f"    {bid}: NOT FOUND")

    print(f"\n  Run: {TOTAL_STEPS//1000}k steps, DT={DT}s, "
          f"log/{LOG_INTERVAL//1000}k, snap/{SNAPSHOT_EVERY//1000}k")
    print()

    # ── Header ──
    hdr = (f"{'Step':>8} | "
           f"{'fill':>6} {'yolk%':>6} {'DA':>6} | "
           f"{'dist':>6} {'dy':>7} | "
           f"{'c_L':>6} {'c_R':>6} | "
           f"{'wL':>7} {'wR':>7} | "
           f"{'Nv':>3} {'sps':>6}")
    print(hdr)
    print("-" * len(hdr))

    # ── Tracking ──
    checkpoints = []
    snapshots   = []
    fill_vals   = []
    diverge_step = TOTAL_STEPS  # step when y-axis weight divergence first > 0.02
    dy_200k = None
    noether_prev = 0

    t_start = time.time()
    t_block = t_start
    blk_cnt = 0

    w_left_init  = bundle_w_mean(bundles_therm["therm_therm_left_to_move_y"])  if "therm_therm_left_to_move_y"  in bundles_therm else float('nan')
    w_right_init = bundle_w_mean(bundles_therm["therm_therm_right_to_move_y"]) if "therm_therm_right_to_move_y" in bundles_therm else float('nan')

    for step in range(TOTAL_STEPS):
        c.step({}, DT)
        blk_cnt += 1
        fill_vals.append(c.energy_store.fill_fraction)

        if (step + 1) % LOG_INTERVAL == 0:
            fill  = c.energy_store.fill_fraction
            yolk_f = c.yolk_sac.fraction_remaining
            da    = c.dopamine.concentration
            dist  = nearest_src_dist(c)
            dy    = c.world.body.position[1] - body_start[1]

            c_left  = col_therm_ema(c, 'therm_left')
            c_right = col_therm_ema(c, 'therm_right')

            w_left  = bundle_w_mean(bundles_therm["therm_therm_left_to_move_y"])  if "therm_therm_left_to_move_y"  in bundles_therm else float('nan')
            w_right = bundle_w_mean(bundles_therm["therm_therm_right_to_move_y"]) if "therm_therm_right_to_move_y" in bundles_therm else float('nan')

            noether_total = len(c._noether_probe._violations)
            noether_new   = noether_total - noether_prev
            noether_prev  = noether_total

            t_now   = time.time()
            sps     = blk_cnt / max(t_now - t_block, 1e-6)
            t_block = t_now
            blk_cnt = 0

            cp = {
                'step': step + 1, 'fill': fill, 'yolk_f': yolk_f,
                'da': da, 'dist': dist, 'dy': dy,
                'col_left': c_left, 'col_right': c_right,
                'w_left': w_left, 'w_right': w_right,
                'noether_new': noether_new, 'sps': sps,
            }
            checkpoints.append(cp)

            # Track first directional divergence
            if abs(w_left - w_right) > 0.02 and diverge_step == TOTAL_STEPS:
                diverge_step = step + 1

            # y-displacement at 200k
            if (step + 1) == 200_000:
                dy_200k = dy

            nv_flag = f"!{noether_new}" if noether_new > 0 else "  0"
            print(f"{step+1:>8} | "
                  f"{fill:>6.4f} {yolk_f:>6.4f} {da:>6.4f} | "
                  f"{dist:>6.2f} {dy:>+7.2f} | "
                  f"{c_left:>6.4f} {c_right:>6.4f} | "
                  f"{w_left:>7.5f} {w_right:>7.5f} | "
                  f"{nv_flag:>3} {sps:>6.0f}")

            if noether_new > 0:
                vd = c._noether_probe.summary().get('violation_counts', {})
                print(f"  [!NOETHER] +{noether_new}: {vd}")

            if (step + 1) % SNAPSHOT_EVERY == 0:
                se = c._structural_entropy.summary()
                print(f"  [SNAP @{(step+1)//1000}k] Body={[round(p,1) for p in c.world.body.position]}"
                      f"  yolk={c.yolk_sac.level:.1f}"
                      f"  H_struct={se.get('H_struct',0):.4f}")
                w_front = bundle_w_mean(bundles_therm.get("therm_therm_front_to_move_x", type('',(),{'n_sources':0,'n_targets':0,'_memristors':{}})()))
                w_back  = bundle_w_mean(bundles_therm.get("therm_therm_back_to_move_x",  type('',(),{'n_sources':0,'n_targets':0,'_memristors':{}})()))
                print(f"  [SNAP] therm weights: front={w_front:.5f} back={w_back:.5f} "
                      f"left={w_left:.5f} right={w_right:.5f}")
                snapshots.append({**cp, 'H_struct': se.get('H_struct', 0.0)})

    elapsed = time.time() - t_start

    # ── Final analysis ────────────────────────────────────────────────────────
    fill_min  = min(fill_vals)
    w_left_f  = bundle_w_mean(bundles_therm["therm_therm_left_to_move_y"])  if "therm_therm_left_to_move_y"  in bundles_therm else float('nan')
    w_right_f = bundle_w_mean(bundles_therm["therm_therm_right_to_move_y"]) if "therm_therm_right_to_move_y" in bundles_therm else float('nan')
    dw_y_spread = abs(w_left_f - w_right_f)
    if dy_200k is None:
        dy_200k = 0.0

    print(f"\n{'=' * 78}")
    print(f"  EXP-Phase4 FINAL — {TOTAL_STEPS//1000}k steps, {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"{'=' * 78}")

    print(f"\n[1] METABOLIC:")
    print(f"  fill_min   = {fill_min:.6f}  (DR3: > 0)")
    print(f"  fill_final = {checkpoints[-1]['fill']:.4f}")
    print(f"  yolk_left  = {c.yolk_sac.level:.1f}/{c.yolk_sac.config.initial_level:.0f} "
          f"({'depleted' if c.yolk_sac.is_depleted else 'remaining'})")

    print(f"\n[2] NEUROMODULATION:")
    da_vals = [cp['da'] for cp in checkpoints]
    print(f"  DA_mean = {sum(da_vals)/len(da_vals):.4f}   DA_max = {max(da_vals):.4f}")

    print(f"\n[3] BEHAVIOR / MOTOR:")
    print(f"  Δy(200k)   = {dy_200k:+.4f}  (DR2: > 1.0, toward y+ heat)")
    print(f"  Δy(final)  = {checkpoints[-1]['dy']:+.4f}")
    dist_vals = [cp['dist'] for cp in checkpoints]
    print(f"  dist_final = {dist_vals[-1]:.2f}  (init={d_init:.2f})")

    print(f"\n[4] DIRECTIONAL WEIGHT DIVERGENCE:")
    print(f"  w_left  init={w_left_init:.5f} → final={w_left_f:.5f}  Δ={w_left_f-w_left_init:+.5f}")
    print(f"  w_right init={w_right_init:.5f} → final={w_right_f:.5f}  Δ={w_right_f-w_right_init:+.5f}")
    print(f"  spread  = |w_left - w_right| = {dw_y_spread:.5f}  (DR1: > 0.02)")
    print(f"  diverge_step = {diverge_step:,}  (DR4: < 200,000)")

    print(f"\n[5] COLUMN ACTIVITY (y-axis):")
    c_left_vals  = [cp['col_left']  for cp in checkpoints]
    c_right_vals = [cp['col_right'] for cp in checkpoints]
    print(f"  col_therm_left  mean={sum(c_left_vals)/len(c_left_vals):.5f}")
    print(f"  col_therm_right mean={sum(c_right_vals)/len(c_right_vals):.5f}")

    print(f"\n[6] DISTANCE TRAJECTORY (every 100k):")
    for cp in checkpoints[::10]:
        arrow = "→" if cp['dist'] < d_init else "·"
        print(f"  step {cp['step']:>8,}: dist={cp['dist']:.2f} dy={cp['dy']:+.2f} {arrow}")

    # ── Acceptance ────────────────────────────────────────────────────────────
    results = {
        'dw_y_spread':  dw_y_spread,
        'dy_200k':      dy_200k,
        'fill_min':     fill_min,
        'diverge_step': diverge_step,
    }

    print(f"\n{'=' * 78}")
    print(f"  ACCEPTANCE CRITERIA (Phase4)")
    print(f"{'=' * 78}")
    n_pass = 0
    for cid, (name, fn) in ACCEPTANCE.items():
        ok = False
        try:
            ok = fn(results)
        except Exception:
            ok = False
        status = "PASS" if ok else "FAIL"
        if ok:
            n_pass += 1
        print(f"  [{status}] {cid}: {name}")

    print(f"\n  Result: {n_pass}/{len(ACCEPTANCE)} criteria met")
    if n_pass == len(ACCEPTANCE):
        print("  EXPERIMENT PASSED — directional thermotaxis learning confirmed")
    else:
        print("  EXPERIMENT FAILED — see failure analysis above")
    print()


if __name__ == "__main__":
    run()
