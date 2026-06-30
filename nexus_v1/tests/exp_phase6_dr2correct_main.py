"""Phase 6 DR2-corrected Main Experiment (500k steps).

DR2 definition correction: Δx (x-axis only) → 3D distance reduction.

Rationale: the organism has a 6-axis vestibular drive (yaw/pitch/roll +
oto_x/y/z), so body motion is inherently 3-dimensional. Using only the
x-axis displacement overstates directional progress when the body also
drifts laterally (y/z), while understating it when the heat source is not
purely in the x-direction. 3D distance reduction directly measures how much
closer the body has come to the heat source — the thermotaxis objective.

Phase 6 P0 retrospective: Δx@200k was +0.9636 but 3D dist reduction was
only 0.880 (body drifted ~1.87 units laterally in y/z, partially offsetting
the x-approach). The 3D metric is the canonical DR2 going forward.

Parameters: identical to Phase 6 P0 (CONSUME_RATE=9.75 already in circuit).
"""
import sys, math, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS = 500_000
DT = 0.001
LOG_INTERVAL = 50_000
DR2_STEP = 200_000   # checkpoint for DR2

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
# BIO: lateral inhibition gain — dorsal horn A-β→C-fibre inhibition, 20–40%
# of excitatory drive (Melzack & Wall 1965 gate control; Koch & Poggio 1983
# Proc. R. Soc. B 298:227). 0.3 = mid-range.
c.somatosensory.LATERAL_GAIN = 0.3
# BIO: Hill (1938) muscle force model; gain=0.3 ≈ moderate fast-twitch fibre,
# ~50% F_max at full activation (Zajac 1989 Crit. Rev. Biomed. Eng. 17:359).
for m in c.muscle_system.muscles:
    m.gain = 0.3

_stdp_applied = False

print("=" * 70)
print("Phase 6 DR2-corrected: 3D distance reduction metric, 500k steps")
print("=" * 70)
print(f"DR2 metric: 3D dist reduction at step {DR2_STEP} > 1.0  (was: Δx > 1.0)")
print(f"muscle_gain=0.3  oto_amp=6.0  lateral_gain=0.3  heat.energy=10000")
print(f"Body start: {init_pos}  heat: {heat.position}  init_dist={init_dist:.2f}")
print()

trajectory = []
dr2_snapshot = None
fill_zero_step = None
grad_dot_v_pos = 0
grad_dot_v_total = 0
da_sat_count = 0
dr4_first_step = None
dr4_sustained_start = None
t0 = time.time()

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
            # BIO: STDP lr=0.005 — Bi & Poo (1998 J. Neurosci.; 2001 ARN) report
            # 0.001–0.01 per spike pair; 0.005 is median.
            b.config.stdp_lr = 0.005
        _stdp_applied = True

    pos = list(c.world.body.position)
    dist = math.sqrt(sum((p - h)**2 for p, h in zip(pos, heat.position)))
    bv = c.world.body.velocity

    # DR5: gradient·velocity alignment
    if heat.alive:
        grad = [h - p for p, h in zip(pos, heat.position)]
        dot = sum(g * v for g, v in zip(grad, bv))
        grad_dot_v_total += 1
        if dot > 0:
            grad_dot_v_pos += 1

    # DR6: DA saturation
    da_v = c.da_neuron._membrane if hasattr(c, 'da_neuron') else 0.0
    if abs(da_v) > 0.9:
        da_sat_count += 1

    # fill zero
    if fill_zero_step is None and c.energy_store.fill_fraction <= 0.0:
        fill_zero_step = step

    # DR4: weight divergence
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

    # DR2 snapshot at 200k  — 3D distance reduction
    if step == DR2_STEP - 1:
        dist_reduction_200k = init_dist - dist
        dr2_snapshot = {
            'pos': pos, 'dist': dist,
            'dist_reduction': dist_reduction_200k,
            'dx': pos[0] - init_pos[0],
            'fill': c.energy_store.fill_fraction,
            'wdiff': wdiff,
        }

    if step % LOG_INTERVAL == 0:
        speed = math.sqrt(sum(v*v for v in bv))
        src_energy = heat.energy if heat.alive else 0.0
        trajectory.append({
            'step': step, 'pos': pos, 'dist': dist,
            'dist_reduction': init_dist - dist,
            'speed': speed, 'wdiff': wdiff,
            'fill': c.energy_store.fill_fraction,
            'src_energy': src_energy,
        })
        if step > 0:
            elapsed = time.time() - t0
            print(f"Step {step:>6d} ({elapsed:.0f}s)  dist={dist:.3f} (-{init_dist-dist:.3f})  "
                  f"fill={c.energy_store.fill_fraction:.3f}  |Δw|={wdiff:.4f}")

elapsed = time.time() - t0
print(f"\nDone: {STEPS:,} steps in {elapsed:.1f}s ({STEPS/elapsed:.0f}/s)\n")

# ─── DR evaluation ────────────────────────────────────────────────────────────
print("=" * 70)
print("DR Criteria (DR2 = 3D distance reduction > 1.0 at 200k)")
print("=" * 70)

final = trajectory[-1]

# DR1
bda = c.bundles_soma_to_da[0] if c.bundles_soma_to_da else None
w_lr_f = {}
if bda:
    wm = bda.weight_matrix()
    for i, pid in enumerate(c.somatosensory.patch_ids):
        if pid in ('left', 'right'):
            w_lr_f[pid] = sum(wm[i]) / max(len(wm[i]), 1)
wdiff_f = abs(w_lr_f.get('right', 0) - w_lr_f.get('left', 0))
dr1_ok = wdiff_f > 0.02
print(f"\nDR1 |Δw| > 0.02:  {wdiff_f:.4f}  {'PASS' if dr1_ok else 'FAIL'}")

# DR2 — 3D distance reduction
if dr2_snapshot:
    dr2_reduction = dr2_snapshot['dist_reduction']
    dr2_ok = dr2_reduction > 1.0
    print(f"DR2 3D-dist-reduction(200k) > 1.0:  {dr2_reduction:.4f}  "
          f"(Δx_only={dr2_snapshot['dx']:+.4f})  {'PASS' if dr2_ok else 'FAIL'}")
    # also report when 1.0 threshold is crossed
    crossed_step = None
    for rec in trajectory:
        if rec['dist_reduction'] > 1.0:
            crossed_step = rec['step']
            break
    if crossed_step is not None:
        print(f"     → 1.0 threshold crossed at step ~{crossed_step}")
    else:
        print(f"     → 1.0 threshold NOT crossed in 500k steps")
else:
    dr2_ok = False

# DR3
dr3_fill = dr2_snapshot['fill'] if dr2_snapshot else 0.0
dr3_ok = dr3_fill > 0.0
if fill_zero_step:
    print(f"DR3 fill>0@200k:  {dr3_fill:.4f}  (zero at step {fill_zero_step})  "
          f"{'PASS' if dr3_ok else 'FAIL'}")
else:
    print(f"DR3 fill>0@200k:  {dr3_fill:.4f}  (never zeroed, final={final['fill']:.4f})  "
          f"{'PASS' if dr3_ok else 'FAIL'}")

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
    print(f"  step {r['step']:>6d}: dist={r['dist']:.3f} (-{r['dist_reduction']:.3f})  "
          f"fill={r['fill']:.4f}  speed={r['speed']:.5f}  |Δw|={r['wdiff']:.4f}")

sys.exit(0 if passed >= 5 else 1)
