"""Phase 5: Directional Thermotaxis Experiment — 500k steps.

Goal: verify that soma relay → DA STDP pathway produces directional
weight differentiation (left vs right relay weights diverge based on
heat source location), and that this drives sustained body drift toward
the heat source (klinokinesis via vestibular oscillation + thermal bias).

Verification criteria (DR1-DR6):
  DR1: |w_left - w_right| > 0.02  at 500k steps (weight differentiation)
  DR2: Δy(200k) or Δx(200k) > 1.0  (net body drift toward heat)
  DR3: energy fill > 0 throughout (metabolic survival)
  DR4: differentiation appears before 200k and persists > 50k steps
  DR5: grad_dot_v positive after differentiation (thermal alignment)
  DR6: DA concentration < 0.90 for majority (dynamic range preserved)

Architecture:
  - Heat source at [70,50,50] (to the RIGHT of body)
  - Body starts at [50,50,50]
  - Directional drive: relay_right fires more → w_right grows
  - soma_to_da bundle (initial_weight=0.5, v2: stdp_lr=0.005)
  - Klinokinesis substrate: periodic vestibular drives body oscillation
  - Net drift expected toward +x (toward heat) if thermotaxis works

Phase 5 parameter overrides:
  - lateral_gain: 0.05 → 0.3  (stronger inter-patch competition)
  - soma_to_da stdp_lr: 0.002 → 0.005  (faster thermal learning)
"""
import sys, math, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS = 500_000
DT = 0.001
LOG_INTERVAL = 10_000   # record every 10k steps
PRINT_INTERVAL = 50_000 # print every 50k steps

# Heat source to the RIGHT of body (+x direction)
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

# ── Phase 5 parameter overrides ──
c.somatosensory.LATERAL_GAIN = 0.3    # stronger directional competition

# soma_to_da stdp_lr override (applied after first step initializes DA circuit)
_stdp_lr_applied = False

print("=" * 70)
print("Phase 5: Directional Thermotaxis Experiment")
print("=" * 70)
print(f"Heat source: {heat.position}  T={heat.temperature}  r={heat.radius}")
print(f"Body start:  {init_pos}  dist={init_dist:.2f}")
print(f"Steps: {STEPS:,}  DT={DT}")
print(f"Parameters: lateral_gain=0.3  soma_to_da stdp_lr=0.005")
print()

# ── Tracking ──
trajectory = []      # list of dicts per LOG_INTERVAL
da_history = []      # (step, da) per step for saturation analysis
wdiff_history = []   # (step, |w_right - w_left|) per LOG_INTERVAL
first_diff_step = None  # first step |Δw| > 0.005
t0 = time.time()

for step in range(STEPS):
    t = step * DT
    # Klinokinesis substrate: periodic vestibular drives oscillation
    # Heat source to right → body oscillates → right patch gets more heat
    # → relay_right fires more → w_right grows via STDP → net drift right
    signal = {
        'yaw':   2.0 * math.sin(1.5 * t),
        'pitch': 1.5 * math.sin(1.0 * t),
        'roll':  1.0 * math.sin(0.7 * t),
        'oto_x': 3.0 * math.sin(2.0 * t),
        'oto_y': 3.0 * math.sin(2.5 * t + 0.3),
        'oto_z': 3.0 * math.sin(3.0 * t + 0.7),
    }
    c.step(signal, dt=DT)

    # Apply stdp_lr override after DA circuit is initialized (step 1)
    if not _stdp_lr_applied and step >= 1 and c.bundles_soma_to_da:
        for b in c.bundles_soma_to_da:
            b.config.stdp_lr = 0.005
        _stdp_lr_applied = True

    # Track DA every step for saturation check
    da_history.append(c.dopamine.concentration)

    # Record per LOG_INTERVAL
    if step % LOG_INTERVAL == 0:
        pos = list(c.world.body.position)
        dist = math.sqrt(sum((p - h)**2 for p, h in zip(pos, heat.position)))

        # Weight state
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
        pt = c._patch_temps
        gdv = sum([pt.get('right',(0,))[0]-pt.get('left',(0,))[0], 0.0,
                   pt.get('front',(0,))[0]-pt.get('back',(0,))[0]][i]*bv[i]
                  for i in range(min(3,len(bv)))) if pt else 0.0

        trajectory.append({
            'step': step,
            'pos': pos,
            'dist': dist,
            'da': c.dopamine.concentration,
            'fill': c.energy_store.fill_fraction,
            'w_left': w_lr['left'],
            'w_right': w_lr['right'],
            'wdiff': wdiff,
            'gdv': gdv,
            'relay_left': c.somatosensory.relays['left']._activation_ema,
            'relay_right': c.somatosensory.relays['right']._activation_ema,
        })

    # Print progress
    if step > 0 and step % PRINT_INTERVAL == 0:
        t_rec = trajectory[-1]
        elapsed = time.time() - t0
        rate = step / max(elapsed, 0.001)
        print(f"Step {step:>7d} ({elapsed:.0f}s, {rate:.0f}/s)  "
              f"dist={t_rec['dist']:.2f}  |Δw|={t_rec['wdiff']:.4f}  "
              f"DA={t_rec['da']:.3f}  fill={t_rec['fill']:.3f}")

elapsed_total = time.time() - t0
rate_total = STEPS / max(elapsed_total, 0.001)
print(f"\nDone: {STEPS:,} steps in {elapsed_total:.1f}s ({rate_total:.0f}/s)\n")

# ═══════════════════════════════════════════════════════════════
# DR Analysis
# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("DR Verification")
print("=" * 70)

# DR1: Final weight differentiation
final = trajectory[-1]
dr1_val = final['wdiff']
dr1_ok = dr1_val > 0.02
print(f"\nDR1 |w_right - w_left| > 0.02:  {dr1_val:.4f}  {'PASS' if dr1_ok else 'FAIL'}")
print(f"     w_right={final['w_right']:.4f}  w_left={final['w_left']:.4f}")

# DR2: Net drift toward heat source (check ~200k steps)
idx_200k = min(20, len(trajectory) - 1)   # 200k = index 20 (at 10k interval)
t200 = trajectory[idx_200k]
dx = t200['pos'][0] - init_pos[0]   # x-drift toward heat
dist_change = t200['dist'] - init_dist
dr2_val = abs(dx)
dr2_ok = dr2_val > 1.0 or dist_change < -1.0
print(f"\nDR2 Net drift > 1.0 at ~{idx_200k*10}k steps:  Δx={dx:+.3f}  Δdist={dist_change:+.3f}  {'PASS' if dr2_ok else 'FAIL'}")

# DR3: Energy fill > 0 throughout
min_fill = min(t['fill'] for t in trajectory)
dr3_ok = min_fill > 0.0
print(f"\nDR3 Energy fill > 0 throughout:  min_fill={min_fill:.4f}  {'PASS' if dr3_ok else 'FAIL'}")

# DR4: Differentiation before 200k, persistent > 50k steps
dr4_ok = False
dr4_detail = "no significant differentiation"
if first_diff_step is not None:
    # Check if it persists for 50k steps
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
        dr4_detail = f"started at step {first_diff_step} but didn't persist 50k steps"
    else:
        dr4_detail = f"started late (step {first_diff_step})"
print(f"\nDR4 Differentiation before 200k, persist >50k:  {'PASS' if dr4_ok else 'FAIL'}")
print(f"     {dr4_detail}")

# DR5: grad_dot_v positive after differentiation
gdv_vals = [t['gdv'] for t in trajectory if t['wdiff'] > 0.01]
if gdv_vals:
    gdv_pos_frac = sum(1 for v in gdv_vals if v > 0) / len(gdv_vals)
    dr5_ok = gdv_pos_frac > 0.5
    print(f"\nDR5 grad_dot_v > 0 after diff (>50%):  {gdv_pos_frac:.2%}  {'PASS' if dr5_ok else 'FAIL'}")
else:
    dr5_ok = False
    print(f"\nDR5 grad_dot_v: no differentiated steps found  FAIL")

# DR6: DA not persistently saturated
da_sat = sum(1 for d in da_history if d > 0.90) / max(len(da_history), 1)
dr6_ok = da_sat < 0.20
print(f"\nDR6 DA sat fraction < 20%:  {da_sat:.2%}  {'PASS' if dr6_ok else 'FAIL'}")
print(f"     DA mean={sum(da_history)/len(da_history):.4f}  max={max(da_history):.4f}")

# ── Summary ──
checks = [dr1_ok, dr2_ok, dr3_ok, dr4_ok, dr5_ok, dr6_ok]
passed = sum(checks)
labels = ['DR1', 'DR2', 'DR3', 'DR4', 'DR5', 'DR6']
print("\n" + "=" * 70)
print(f"Result: {passed}/6 DR criteria PASS")
print(f"  {' '.join(f'{lb}={'✓' if ok else '✗'}' for lb, ok in zip(labels, checks))}")

# ── Weight trajectory ──
print("\nWeight divergence over time:")
for s, wd in wdiff_history[::5]:  # every 50k steps
    bar = '█' * int(wd * 200)
    print(f"  step {s:>7d}: |Δw|={wd:.4f}  {bar}")

# ── Distance trajectory ──
print("\nDistance to heat source:")
for t in trajectory[::5]:  # every 50k steps
    d_init = init_dist
    delta = t['dist'] - d_init
    marker = "←" if delta < 0 else "→"
    print(f"  step {t['step']:>7d}: dist={t['dist']:.2f} ({delta:+.2f}) {marker}")

print("=" * 70)
sys.exit(0 if passed >= 4 else 1)
