"""EXP-Phase5: Directional Thermotaxis — 500k step verification.

Builds on Phase 4 with thermal chain fully repaired:
  - Noci v_peak 0.01→0.25 (TRPV1 AP threshold, Julius 2001)
  - THERMAL_TRANSDUCTION_GAIN=0.1 (reg_therm in [0,1])
  - Shadow census patch (21 neurons visible to entropy ledger)
  - Thermal column v_peak=0.20 (L2/3 pyramidal threshold, Liu 2014)
  - DA_INJECT_SCALE=0.014 (RPE peak 5.0 → V_ss=0.35 < v_peak=1.0)
  - DEVIATION_MOTOR_GAIN=1/dt (dt-invariant motor drive)
  - enc→col thermal synapse_gain=4.0 (col_therm reliably crosses v_peak=0.20)

Phase 5 vs Phase 4 key differences:
  - stdp_lr: 0.05 → 0.005 (slow learning, more stable weight trajectory)
  - lambda_yolk: 0.001 → 0.0015 (extended metabolic window)
  - DA no longer saturates (DA_INJECT_SCALE applied in base circuit)
  - col_therm reliably fires (enc→col gain boosted)

Acceptance criteria (Phase5):
  DR1: |w_left - w_right| > 0.02  — directional weight divergence
  DR2: Δy(200k) > 1.0              — net y displacement toward source
  DR3: min(fill) > 0 @500k         — metabolic survival
  DR4: first divergence before 200k — within YolkSac window
  DR5: thermal_alignment > 0 sustained — moving toward heat source
  DR6: DA max_V < 0.9 × v_peak     — DA not saturated (dynamic range)

Run from j:/cell-cc:
    cd /j/cell-cc
    PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.exp_phase5_directional
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

# ── Configuration ─────────────────────────────────────────────────────────────
TOTAL_STEPS    =  500_000
DT             =    0.001
LOG_INTERVAL   =   10_000
SNAPSHOT_EVERY =  100_000

# Phase5 R4: lambda=0.002 > consumption_rate≈0.001502 → fill net-positive throughout.
# yolk_level=1000: 1000/0.002 = 500k steps lifetime. DR3 fix.
LAMBDA_YOLK_P5 = 0.002
YOLK_LEVEL_P5  = 1000.0

# Body offset: left patch 3.71u from source, right 6.29u. ΔT≈0.43.
BODY_INIT_POS  = [75.0, 20.0, 25.0]

# y-axis thermal bundle IDs
THERM_BUNDLE_IDS = [
    "therm_therm_front_to_move_x",
    "therm_therm_back_to_move_x",
    "therm_therm_left_to_move_y",
    "therm_therm_right_to_move_y",
]

ACCEPTANCE = {
    'DR1': ('|w_left - w_right| > 0.02',        lambda r: r['dw_y_spread'] > 0.02),
    'DR2': ('Δy(200k) > 1.0',                    lambda r: r['dy_200k'] > 1.0),
    'DR3': ('min(fill) > 0 @500k',               lambda r: r['fill_min'] > 0),
    'DR4': ('divergence before 200k steps',       lambda r: r['diverge_step'] < 200_000),
    'DR5': ('thermal_alignment > 0 (>50% steps)', lambda r: r['align_pos_frac'] > 0.5),
    'DR6': ('DA max_V < 0.9 × v_peak',           lambda r: r['da_max_v'] < 0.9),
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def dist3(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def bundle_w_mean(bundle):
    weights = [bundle._memristors[r][ci].w
               for r in range(bundle.n_sources)
               for ci in range(bundle.n_targets)]
    return sum(weights) / max(len(weights), 1) if weights else float('nan')


def nearest_src(circuit):
    pos = circuit.world.body.position
    alive = [s for s in circuit.world.heat_sources if s.alive]
    if not alive:
        return None, float('inf')
    best = min(alive, key=lambda s: dist3(pos, s.position))
    return best, dist3(pos, best.position)


def col_therm_ema(circuit, name):
    try:
        return circuit.column_neurons[name]._activation_ema
    except (KeyError, AttributeError):
        return float('nan')


def da_max_voltage(circuit):
    """Highest DA neuron membrane voltage, normalized by v_peak."""
    try:
        v_peak = list(circuit.da_neurons.values())[0].config.v_peak
        max_v = max(n._membrane.voltage for n in circuit.da_neurons.values())
        return max_v / v_peak
    except Exception:
        return float('nan')


def thermal_alignment(pos_now, pos_prev, src):
    """dot(velocity_direction, direction_to_source)."""
    if src is None:
        return 0.0
    v = [pos_now[i] - pos_prev[i] for i in range(3)]
    g = [src.position[i] - pos_now[i] for i in range(3)]
    v_norm = math.sqrt(sum(x**2 for x in v))
    g_norm = math.sqrt(sum(x**2 for x in g))
    if v_norm < 1e-9 or g_norm < 1e-9:
        return 0.0
    v_u = [x / v_norm for x in v]
    g_u = [x / g_norm for x in g]
    return sum(a * b for a, b in zip(v_u, g_u))


# ── Main ──────────────────────────────────────────────────────────────────────
def run():
    from nexus_v1.circuit.variant_adapter import VariantCircuit

    print("=" * 78)
    print("  EXP-Phase5: Directional Thermotaxis — 500k steps")
    print("  Thermal chain fully repaired:")
    print("    noci v_peak=0.25 | THERMAL_GAIN=0.1 | col_therm v_peak=0.20")
    print("    DA_INJECT_SCALE=0.014 | DEVIATION_GAIN=1/dt | enc→col gain=4.0")
    print(f"  lambda_yolk={LAMBDA_YOLK_P5} (override from circuit default)")
    print("=" * 78)

    c = VariantCircuit()

    # Phase5 metabolic override
    c.yolk_sac.config.lambda_yolk = LAMBDA_YOLK_P5
    c.yolk_sac.config.initial_level = YOLK_LEVEL_P5
    c.yolk_sac._level = YOLK_LEVEL_P5
    est_steps = c.yolk_sac.level / LAMBDA_YOLK_P5
    print(f"\n  YolkSac: level={c.yolk_sac.level:.0f}, "
          f"lambda={LAMBDA_YOLK_P5}/step → depletes ~{est_steps/1000:.0f}k steps")

    # Body position
    c.world.body.position = list(BODY_INIT_POS)
    body_start = list(c.world.body.position)
    src_init, d_init = nearest_src(c)

    # ── Startup summary ──
    print(f"\n  Heat sources: {len(c.world.heat_sources)}")
    for i, s in enumerate(c.world.heat_sources):
        print(f"    src[{i}] pos={[round(p,1) for p in s.position]} T={s.temperature}")
    print(f"  Body start: {[round(p,1) for p in body_start]}  dist={d_init:.2f}")

    try:
        env_temps = {}
        for patch in c.world.body.skin_patches:
            wp = patch.world_position(c.world.body)
            env_temps[patch.patch_id] = c.world.temperature_at(wp)
        dt_str = ', '.join(f'{k}={v:.3f}' for k, v in env_temps.items())
        print(f"  Env temps: {dt_str}")
        if 'left' in env_temps and 'right' in env_temps:
            print(f"  ΔT(left-right) = {env_temps['left']-env_temps['right']:+.4f}")
    except Exception as e:
        print(f"  Env temps unavailable ({e})")

    print(f"  lateral_gain={c.somatosensory.LATERAL_GAIN:.2f}")
    print(f"  DA gate η_da={c.da_gate.config.eta_da}")
    print(f"  col v_peak therm_front={c.column_neurons['therm_front'].config.v_peak:.2f}")

    # Therm bundle inventory
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

    hdr = (f"{'Step':>8} | "
           f"{'fill':>6} {'yolk%':>6} {'DA_V':>6} | "
           f"{'dist':>6} {'dy':>7} {'align':>7} | "
           f"{'c_F':>6} {'c_B':>6} {'c_L':>6} {'c_R':>6} | "
           f"{'wL':>7} {'wR':>7} | "
           f"{'Nv':>3} {'sps':>6}")
    print(hdr)
    print("-" * len(hdr))

    # ── Tracking ──
    checkpoints  = []
    fill_vals    = []
    align_vals   = []
    diverge_step = TOTAL_STEPS
    dy_200k      = None
    noether_prev = 0
    da_max_v_all = 0.0
    prev_pos     = list(body_start)

    w_left_init  = bundle_w_mean(bundles_therm.get("therm_therm_left_to_move_y",  None) or type('',(),{'n_sources':0,'n_targets':0,'_memristors':{}})())
    w_right_init = bundle_w_mean(bundles_therm.get("therm_therm_right_to_move_y", None) or type('',(),{'n_sources':0,'n_targets':0,'_memristors':{}})())

    t_start = time.time()
    t_block = t_start
    blk_cnt = 0

    for step in range(TOTAL_STEPS):
        c.step({}, DT)
        blk_cnt += 1
        fill_vals.append(c.energy_store.fill_fraction)

        if (step + 1) % LOG_INTERVAL == 0:
            pos_now = list(c.world.body.position)
            src, dist = nearest_src(c)

            fill   = c.energy_store.fill_fraction
            yolk_f = c.yolk_sac.fraction_remaining
            da_v   = da_max_voltage(c)
            da_max_v_all = max(da_max_v_all, da_v)
            dy     = pos_now[1] - body_start[1]

            align  = thermal_alignment(pos_now, prev_pos, src)
            align_vals.append(align)
            prev_pos = pos_now

            c_front = col_therm_ema(c, 'therm_front')
            c_back  = col_therm_ema(c, 'therm_back')
            c_left  = col_therm_ema(c, 'therm_left')
            c_right = col_therm_ema(c, 'therm_right')

            w_left  = bundle_w_mean(bundles_therm.get("therm_therm_left_to_move_y",  None) or type('',(),{'n_sources':0,'n_targets':0,'_memristors':{}})())
            w_right = bundle_w_mean(bundles_therm.get("therm_therm_right_to_move_y", None) or type('',(),{'n_sources':0,'n_targets':0,'_memristors':{}})())

            noether_total = len(c._noether_probe._violations)
            noether_new   = noether_total - noether_prev
            noether_prev  = noether_total

            t_now   = time.time()
            sps     = blk_cnt / max(t_now - t_block, 1e-6)
            t_block = t_now
            blk_cnt = 0

            cp = {
                'step': step + 1, 'fill': fill, 'yolk_f': yolk_f,
                'da_v': da_v, 'dist': dist, 'dy': dy, 'align': align,
                'col_front': c_front, 'col_back': c_back,
                'col_left': c_left, 'col_right': c_right,
                'w_left': w_left, 'w_right': w_right,
                'noether_new': noether_new, 'sps': sps,
            }
            checkpoints.append(cp)

            if abs(w_left - w_right) > 0.02 and diverge_step == TOTAL_STEPS:
                diverge_step = step + 1

            if (step + 1) == 200_000:
                dy_200k = dy

            nv_flag = f"!{noether_new}" if noether_new > 0 else "  0"
            align_flag = f"{align:+.3f}"
            print(f"{step+1:>8} | "
                  f"{fill:>6.4f} {yolk_f:>6.4f} {da_v:>6.3f} | "
                  f"{dist:>6.2f} {dy:>+7.2f} {align_flag:>7} | "
                  f"{c_front:>6.4f} {c_back:>6.4f} {c_left:>6.4f} {c_right:>6.4f} | "
                  f"{w_left:>7.5f} {w_right:>7.5f} | "
                  f"{nv_flag:>3} {sps:>6.0f}")

            if noether_new > 0:
                vd = c._noether_probe.summary().get('violation_counts', {})
                print(f"  [!NOETHER] +{noether_new}: {vd}")

            if (step + 1) % SNAPSHOT_EVERY == 0:
                se = c._structural_entropy.summary()
                pos_str = [round(p, 1) for p in c.world.body.position]
                print(f"  [SNAP @{(step+1)//1000}k] Body={pos_str}"
                      f"  yolk={c.yolk_sac.level:.1f}"
                      f"  H_struct={se.get('H_struct',0):.4f}"
                      f"  DA_max_V={da_max_v_all:.3f}")
                for bid in THERM_BUNDLE_IDS:
                    b = bundles_therm.get(bid)
                    w = bundle_w_mean(b) if b else float('nan')
                    print(f"  [SNAP]   {bid}: w={w:.5f}")

    elapsed = time.time() - t_start

    # ── Final analysis ─────────────────────────────────────────────────────────
    fill_min  = min(fill_vals)
    w_left_f  = bundle_w_mean(bundles_therm.get("therm_therm_left_to_move_y",  None) or type('',(),{'n_sources':0,'n_targets':0,'_memristors':{}})())
    w_right_f = bundle_w_mean(bundles_therm.get("therm_therm_right_to_move_y", None) or type('',(),{'n_sources':0,'n_targets':0,'_memristors':{}})())
    dw_y_spread     = abs(w_left_f - w_right_f)
    align_pos_frac  = sum(1 for a in align_vals if a > 0) / max(len(align_vals), 1)
    if dy_200k is None:
        dy_200k = 0.0

    print(f"\n{'=' * 78}")
    print(f"  EXP-Phase5 FINAL — {TOTAL_STEPS//1000}k steps, {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"{'=' * 78}")

    print(f"\n[1] METABOLIC:")
    print(f"  fill_min   = {fill_min:.6f}  (DR3: > 0)")
    print(f"  fill_final = {checkpoints[-1]['fill']:.4f}")
    print(f"  yolk_left  = {c.yolk_sac.level:.1f}  "
          f"({'depleted' if c.yolk_sac.is_depleted else 'remaining'})")

    print(f"\n[2] DA NEUROMODULATION:")
    da_vals = [cp['da_v'] for cp in checkpoints]
    print(f"  DA_max_V/v_peak = {da_max_v_all:.4f}  (DR6: < 0.9)")
    print(f"  DA_V mean={sum(da_vals)/len(da_vals):.4f}  max={max(da_vals):.4f}")

    print(f"\n[3] BEHAVIOR / MOTOR:")
    print(f"  Δy(200k)   = {dy_200k:+.4f}  (DR2: > 1.0)")
    print(f"  Δy(final)  = {checkpoints[-1]['dy']:+.4f}")
    dist_vals = [cp['dist'] for cp in checkpoints]
    print(f"  dist_final = {dist_vals[-1]:.2f}  (init={d_init:.2f})")

    print(f"\n[4] DIRECTIONAL WEIGHT DIVERGENCE:")
    print(f"  w_left  init={w_left_init:.5f} → final={w_left_f:.5f}  Δ={w_left_f-w_left_init:+.5f}")
    print(f"  w_right init={w_right_init:.5f} → final={w_right_f:.5f}  Δ={w_right_f-w_right_init:+.5f}")
    print(f"  spread  = |w_left - w_right| = {dw_y_spread:.5f}  (DR1: > 0.02)")
    print(f"  diverge_step = {diverge_step:,}  (DR4: < 200,000)")

    print(f"\n[5] COLUMN ACTIVITY (x+y axes):")
    c_front_vals = [cp.get('col_front', 0.0) for cp in checkpoints]
    c_back_vals  = [cp.get('col_back',  0.0) for cp in checkpoints]
    c_left_vals  = [cp['col_left']  for cp in checkpoints]
    c_right_vals = [cp['col_right'] for cp in checkpoints]
    print(f"  col_therm_front mean={sum(c_front_vals)/len(c_front_vals):.5f}  (x-axis)")
    print(f"  col_therm_back  mean={sum(c_back_vals)/len(c_back_vals):.5f}  (x-axis)")
    print(f"  col_therm_left  mean={sum(c_left_vals)/len(c_left_vals):.5f}  (y-axis)")
    print(f"  col_therm_right mean={sum(c_right_vals)/len(c_right_vals):.5f}  (y-axis)")

    print(f"\n[6] THERMAL ALIGNMENT (DR5):")
    print(f"  align_pos_frac = {align_pos_frac:.3f}  (DR5: > 0.5 → moving toward heat)")
    if align_vals:
        print(f"  align mean={sum(align_vals)/len(align_vals):+.4f}  "
              f"min={min(align_vals):+.4f}  max={max(align_vals):+.4f}")

    print(f"\n[7] DISTANCE TRAJECTORY (every 100k):")
    for cp in checkpoints[::10]:
        arrow = "->" if cp['dist'] < d_init else " ."
        print(f"  step {cp['step']:>8,}: dist={cp['dist']:.2f} dy={cp['dy']:+.2f} {arrow}")

    results = {
        'dw_y_spread':    dw_y_spread,
        'dy_200k':        dy_200k,
        'fill_min':       fill_min,
        'diverge_step':   diverge_step,
        'align_pos_frac': align_pos_frac,
        'da_max_v':       da_max_v_all,
    }

    print(f"\n{'=' * 78}")
    print(f"  ACCEPTANCE CRITERIA (Phase5)")
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
        print("  EXPERIMENT PASSED — directional thermotaxis confirmed")
    elif n_pass >= 4:
        print("  EXPERIMENT PARTIAL — see failure analysis, consider tuning DR5/DR6")
    else:
        print("  EXPERIMENT FAILED — review emergency adjustments (Section 7 of plan)")
    print()


if __name__ == "__main__":
    run()
