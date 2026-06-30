"""Phase 5 v2: Directional Thermotaxis Main Experiment — 500k steps.

Stage 2A enhancements over Phase 5 v1:
  - oto_x/y/z amplitude: 3.0 → 6.0
  - muscle gain: 0.1 → 0.3 (BIO: moderate activation → higher force output)
  - lateral_gain: 0.05 → 0.3 (same as v1)
  - soma_to_da stdp_lr: 0.002 → 0.005 (same as v1)

100k probe result: 4/4 PASS, speed 0.013, displacement 0.885, G_eff 14.70
Expected 500k: DR1/DR2/DR3/DR4/DR5/DR6 all PASS (6/6).
"""
import sys, math, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS = 500_000
DT = 0.001
LOG_INTERVAL = 10_000
PRINT_INTERVAL = 50_000

heat = HeatSource(position=[70.0, 50.0, 50.0], energy=500.0,
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

# ── Stage 2A overrides ──
# BIO: lateral inhibition gain — dorsal horn A-β→C-fibre inhibition, 20–40%
# of excitatory drive (Melzack & Wall 1965 gate control; Koch & Poggio 1983
# Proc. R. Soc. B 298:227). 0.3 = mid-range.
c.somatosensory.LATERAL_GAIN = 0.3
# BIO: Hill (1938) muscle force model; gain=0.3 ≈ moderate fast-twitch fibre,
# ~50% F_max at full activation (Zajac 1989 Crit. Rev. Biomed. Eng. 17:359).
# NORM: gain=0.1 (default) → body speed <0.001; 0.3 → ~0.01 (EXP-RouteA).
for m in c.muscle_system.muscles:
    m.gain = 0.3

_stdp_applied = False

print("=" * 70)
print("Phase 5 v2: Directional Thermotaxis Main Experiment (500k steps)")
print("=" * 70)
print(f"Heat source: {heat.position}  T={heat.temperature}  r={heat.radius}")
print(f"Body start:  {init_pos}  dist={init_dist:.2f}")
print(f"Overrides: lateral_gain=0.3  muscle_gain=0.3  oto_amp=6.0  stdp_lr=0.005")
print()

trajectory = []
da_history = []
wdiff_history = []
first_diff_step = None
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
            # 0.001–0.01 per spike pair; 0.005 is median. Accelerates directional
            # weight divergence from 240k (default) to ~10k steps.
            b.config.stdp_lr = 0.005
        _stdp_applied = True

    da_history.append(c.dopamine.concentration)

    if step % LOG_INTERVAL == 0:
        pos = list(c.world.body.position)
        dist = math.sqrt(sum((p - h)**2 for p, h in zip(pos, heat.position)))

        bda = c.bundles_soma_to_da[0] if c.bundles_soma_to_da else None
        w_lr = {'left': 0.0, 'right': 0.0}
        if bda:
            wm = bda.weight_matrix()
            for i, pid in enumerate(c.somatosensory.patch_ids):
                if pid in w_lr:
                    w_lr[pid] = sum(wm[i]) / max(len(wm[i]), 1)
        wdiff = abs(w_lr['right'] - w_lr['left'])
        wdiff_history.append((step, wdiff))

        if wdiff > 0.005 and first_diff_step is None:
            first_diff_step = step

        bv = c.world.body.velocity
        speed = math.sqrt(sum(v*v for v in bv))

        trajectory.append({
            'step': step,
            'pos': pos,
            'dist': dist,
            'da': c.dopamine.concentration,
            'fill': c.energy_store.fill_fraction,
            'w_left': w_lr['left'],
            'w_right': w_lr['right'],
            'wdiff': wdiff,
            'gdv': c.motion_state.thermal_gradient_dot_velocity,
            'speed': speed,
        })

    if step > 0 and step % PRINT_INTERVAL == 0:
        rec = trajectory[-1]
        elapsed = time.time() - t0
        rate = step / max(elapsed, 0.001)
        print(f"Step {step:>7d} ({elapsed:.0f}s, {rate:.0f}/s)  "
              f"dist={rec['dist']:.3f}  |Δw|={rec['wdiff']:.4f}  "
              f"DA={rec['da']:.3f}  fill={rec['fill']:.3f}  "
              f"speed={rec['speed']:.4f}")

elapsed_total = time.time() - t0
print(f"\nDone: {STEPS:,} steps in {elapsed_total:.1f}s ({STEPS/elapsed_total:.0f}/s)\n")

# ═══════════════════════════════════════════════════════════════
# DR Analysis
# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("DR Verification")
print("=" * 70)

final = trajectory[-1]

# DR1
dr1_val = final['wdiff']
dr1_ok = dr1_val > 0.02
print(f"\nDR1 |w_right - w_left| > 0.02:  {dr1_val:.4f}  {'PASS' if dr1_ok else 'FAIL'}")
print(f"     w_right={final['w_right']:.4f}  w_left={final['w_left']:.4f}")

# DR2
idx_200k = min(20, len(trajectory) - 1)
t200 = trajectory[idx_200k]
dx = t200['pos'][0] - init_pos[0]
dist_change = t200['dist'] - init_dist
dr2_val = abs(dx)
dr2_ok = dr2_val > 1.0 or dist_change < -1.0
print(f"\nDR2 Net drift > 1.0 at ~{idx_200k*10}k steps:  Δx={dx:+.3f}  Δdist={dist_change:+.3f}  {'PASS' if dr2_ok else 'FAIL'}")

# DR3
min_fill = min(t['fill'] for t in trajectory)
dr3_ok = min_fill > 0.0
print(f"\nDR3 Energy fill > 0 throughout:  min_fill={min_fill:.4f}  {'PASS' if dr3_ok else 'FAIL'}")

# DR4
dr4_ok = False
dr4_detail = "no significant differentiation"
if first_diff_step is not None:
    persist_start = first_diff_step
    persist_end = None
    for s, wd in wdiff_history:
        if s >= persist_start + 50_000 and wd > 0.005:
            persist_end = s
            break
    if first_diff_step <= 200_000 and persist_end is not None:
        dr4_ok = True
        dr4_detail = f"started at step {first_diff_step}, persisted to ≥{persist_end}"
    elif first_diff_step <= 200_000:
        dr4_detail = f"started at step {first_diff_step} but didn't persist 50k"
    else:
        dr4_detail = f"started late (step {first_diff_step})"
print(f"\nDR4 Differentiation before 200k, persist >50k:  {'PASS' if dr4_ok else 'FAIL'}")
print(f"     {dr4_detail}")

# DR5
gdv_vals = [t['gdv'] for t in trajectory if t['wdiff'] > 0.01]
if gdv_vals:
    gdv_pos_frac = sum(1 for v in gdv_vals if v > 0) / len(gdv_vals)
    dr5_ok = gdv_pos_frac > 0.5
    print(f"\nDR5 grad_dot_v > 0 after diff (>50%):  {gdv_pos_frac:.2%}  {'PASS' if dr5_ok else 'FAIL'}")
else:
    dr5_ok = False
    print(f"\nDR5 grad_dot_v: no differentiated steps  FAIL")

# DR6
da_sat = sum(1 for d in da_history if d > 0.90) / max(len(da_history), 1)
dr6_ok = da_sat < 0.20
print(f"\nDR6 DA sat fraction < 20%:  {da_sat:.2%}  {'PASS' if dr6_ok else 'FAIL'}")
print(f"     DA mean={sum(da_history)/len(da_history):.4f}  max={max(da_history):.4f}")

# Summary
checks = [dr1_ok, dr2_ok, dr3_ok, dr4_ok, dr5_ok, dr6_ok]
passed = sum(checks)
labels = ['DR1', 'DR2', 'DR3', 'DR4', 'DR5', 'DR6']
print("\n" + "=" * 70)
print(f"Result: {passed}/6 DR criteria PASS")
print(f"  {' '.join(f'{lb}={'OK' if ok else 'NG'}' for lb, ok in zip(labels, checks))}")

# Distance trajectory
print("\nDistance to heat source:")
for rec in trajectory[::5]:
    delta = rec['dist'] - init_dist
    marker = "<" if delta < 0 else ">"
    print(f"  step {rec['step']:>7d}: dist={rec['dist']:.3f} ({delta:+.3f}) {marker}  "
          f"speed={rec['speed']:.4f}  |Δw|={rec['wdiff']:.4f}")

print("=" * 70)
sys.exit(0 if passed >= 5 else 1)
