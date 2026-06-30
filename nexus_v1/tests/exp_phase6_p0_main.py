"""Phase 6 P0 Main — DR3 Fix Full Validation (500k steps).

CONSUME_RATE=9.75 (variant_adapter.py recalibrated).
heat.energy=10000 (sufficient for 500k steps at new consumption rate).

DR criteria:
  DR1: |w_right - w_left| > 0.02  (directional weight encoding)
  DR2: Δx(200k) > 1.0             (macroscopic displacement)
  DR3: fill > 0 at 200k            (metabolic sustainability — THIS IS THE FIX)
  DR4: weight divergence before 200k, sustained 50k
  DR5: grad_dot_v > 50%            (thermotaxis alignment)
  DR6: DA saturation < 20%
"""
import sys, math, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS = 500_000
DT = 0.001
LOG_INTERVAL = 50_000
PRINT_INTERVAL = 50_000
DR2_STEP = 200_000

heat = HeatSource(position=[70.0, 50.0, 50.0], energy=10_000.0,
                  temperature=5.0, radius=30.0)
heat._drift = [0.0, 0.0, 0.0]
body = Body(position=[50.0, 50.0, 50.0])
world = World(heat_sources=[heat], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

init_pos = list(body.position)
init_dist = math.sqrt(sum((p - h)**2 for p, h in zip(body.position, heat.position)))

c = VariantCircuit()
c.world = world
c.somatosensory.LATERAL_GAIN = 0.3
for m in c.muscle_system.muscles:
    m.gain = 0.3

_stdp_applied = False

print("=" * 70)
print("Phase 6 P0 Main: DR3 Fix (CONSUME_RATE=9.75), 500k steps")
print("=" * 70)
print(f"muscle_gain=0.3  oto_amp=6.0  lateral_gain=0.3  heat.energy=10000")
print(f"Body start: {init_pos}  dist={init_dist:.2f}")
print()

trajectory = []
weight_log = []
grad_dot_v_pos = 0
grad_dot_v_total = 0
da_sat_count = 0
t0 = time.time()

dr4_first_step = None
dr4_sustained_start = None
dr2_snapshot = None
fill_zero_step = None

for step in range(STEPS):
    t = step * DT
    signal = {
        'yaw':   2.0 * math.sin(1.5 * t),
        'pitch': 1.5 * math.sin(1.0 * t),
        'roll':  1.0 * math.sin(0.7 * t),
        'oto_x': 6.0 * math.sin(2.0 * t),
        'oto_y': 6.0 * math.sin(2.5 * t + 0.3),
        'oto_z': 6.0 * math.sin(3.0 * t + 0.7),
    }
    c.step(signal, dt=DT)

    if not _stdp_applied and step >= 1 and c.bundles_soma_to_da:
        for b in c.bundles_soma_to_da:
            b.config.stdp_lr = 0.005
        _stdp_applied = True

    # DR5: gradient alignment
    bv = c.world.body.velocity
    pos = list(c.world.body.position)
    nearest = c.world.get_nearest_heat_source(pos)
    if nearest and nearest.alive:
        grad = [h - p for p, h in zip(pos, nearest.position)]
        dot = sum(g * v for g, v in zip(grad, bv))
        grad_dot_v_total += 1
        if dot > 0:
            grad_dot_v_pos += 1

    # DR6: DA saturation
    da_v = c.da_neuron._membrane if hasattr(c, 'da_neuron') else 0.0
    if abs(da_v) > 0.9:
        da_sat_count += 1

    # fill zero tracking
    if fill_zero_step is None and c.energy_store.fill_fraction <= 0.0:
        fill_zero_step = step

    # weight diff tracking for DR4
    if c.bundles_soma_to_da:
        bda = c.bundles_soma_to_da[0]
        wm = bda.weight_matrix()
        w_lr = {}
        for i, pid in enumerate(c.somatosensory.patch_ids):
            if pid in ('left', 'right'):
                w_lr[pid] = sum(wm[i]) / max(len(wm[i]), 1)
        wdiff = abs(w_lr.get('right', 0) - w_lr.get('left', 0))
        if wdiff > 0.005 and dr4_first_step is None:
            dr4_first_step = step
        if wdiff > 0.005:
            if dr4_sustained_start is None:
                dr4_sustained_start = step
        else:
            dr4_sustained_start = None
    else:
        wdiff = 0.0

    # DR2 snapshot at step 200k
    if step == DR2_STEP - 1:
        pos200 = list(c.world.body.position)
        dx200 = pos200[0] - init_pos[0]
        dist200 = math.sqrt(sum((p - h)**2 for p, h in zip(pos200, heat.position)))
        fill200 = c.energy_store.fill_fraction
        dr2_snapshot = {'pos': pos200, 'dx': dx200, 'dist': dist200,
                        'wdiff': wdiff, 'fill': fill200}

    if step % LOG_INTERVAL == 0:
        dist = math.sqrt(sum((p - h)**2 for p, h in zip(pos, heat.position)))
        bv_speed = math.sqrt(sum(v*v for v in bv))
        src_energy = heat.energy if heat.alive else 0.0
        trajectory.append({
            'step': step, 'pos': pos, 'dist': dist,
            'speed': bv_speed, 'wdiff': wdiff,
            'fill': c.energy_store.fill_fraction,
            'src_energy': src_energy,
        })

    if step > 0 and step % PRINT_INTERVAL == 0:
        rec = trajectory[-1]
        elapsed = time.time() - t0
        print(f"Step {step:>6d} ({elapsed:.0f}s)  dist={rec['dist']:.3f}  "
              f"speed={rec['speed']:.5f}  fill={rec['fill']:.3f}  "
              f"|Δw|={rec['wdiff']:.4f}  src_E={rec['src_energy']:.0f}")

elapsed = time.time() - t0
print(f"\nDone: {STEPS:,} steps in {elapsed:.1f}s ({STEPS/elapsed:.0f}/s)\n")

# ─── DR evaluation ───────────────────────────────────────────────────────────
print("=" * 70)
print("DR Criteria Evaluation")
print("=" * 70)

final = trajectory[-1]

# DR1
bda = c.bundles_soma_to_da[0] if c.bundles_soma_to_da else None
w_lr_final = {}
if bda:
    wm = bda.weight_matrix()
    for i, pid in enumerate(c.somatosensory.patch_ids):
        if pid in ('left', 'right'):
            w_lr_final[pid] = sum(wm[i]) / max(len(wm[i]), 1)
wdiff_final = abs(w_lr_final.get('right', 0) - w_lr_final.get('left', 0))
dr1_ok = wdiff_final > 0.02
print(f"\nDR1 |Δw| > 0.02:  {wdiff_final:.4f}  {'PASS' if dr1_ok else 'FAIL'}")

# DR2
if dr2_snapshot:
    dr2_ok = dr2_snapshot['dx'] > 1.0
    print(f"DR2 Δx(200k) > 1.0:  Δx={dr2_snapshot['dx']:+.4f}  dist={dr2_snapshot['dist']:.3f}  "
          f"{'PASS' if dr2_ok else 'FAIL'}")
else:
    dr2_ok = False
    print("DR2: snapshot missing")

# DR3
dr3_fill = dr2_snapshot['fill'] if dr2_snapshot else 0.0
dr3_ok = dr3_fill > 0.0
fill_at_end = final['fill']
if fill_zero_step:
    print(f"DR3 fill>0 at 200k:  fill@200k={dr3_fill:.4f}  fill@500k={fill_at_end:.4f}  "
          f"(zero reached @step {fill_zero_step})  {'PASS' if dr3_ok else 'FAIL'}")
else:
    print(f"DR3 fill>0 at 200k:  fill@200k={dr3_fill:.4f}  fill@500k={fill_at_end:.4f}  "
          f"(never zeroed)  {'PASS' if dr3_ok else 'FAIL'}")

# DR4
dr4_ok = (dr4_first_step is not None and dr4_first_step < DR2_STEP and
          dr4_sustained_start is not None and
          (STEPS - dr4_sustained_start) >= 50_000)
print(f"DR4 diverge<200k+sustain50k:  first@{dr4_first_step}  "
      f"sustained_from@{dr4_sustained_start}  {'PASS' if dr4_ok else 'FAIL'}")

# DR5
dr5_pct = grad_dot_v_pos / max(grad_dot_v_total, 1) * 100
dr5_ok = dr5_pct > 50.0
print(f"DR5 grad·v>50%:  {dr5_pct:.2f}%  {'PASS' if dr5_ok else 'FAIL'}")

# DR6
dr6_pct = da_sat_count / max(STEPS, 1) * 100
dr6_ok = dr6_pct < 20.0
print(f"DR6 DA sat<20%:  {dr6_pct:.2f}%  {'PASS' if dr6_ok else 'FAIL'}")

checks = [dr1_ok, dr2_ok, dr3_ok, dr4_ok, dr5_ok, dr6_ok]
passed = sum(checks)
labels = ['DR1', 'DR2', 'DR3', 'DR4', 'DR5', 'DR6']
status_str = ' '.join(l + '=' + ('OK' if ok else 'NG') for l, ok in zip(labels, checks))
print(f"\n{'='*70}")
print(f"Result: {passed}/6 DR PASS  {status_str}")
print('='*70)

print("\nDistance + fill trajectory:")
for r in trajectory:
    ddist = r['dist'] - init_dist
    print(f"  step {r['step']:>6d}: dist={r['dist']:.3f} ({ddist:+.3f})  "
          f"fill={r['fill']:.4f}  speed={r['speed']:.5f}  |Δw|={r['wdiff']:.4f}")

sys.exit(0 if passed >= 5 else 1)
