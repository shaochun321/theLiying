"""EXP-016: Vital Heartbeat Thermal Taxis — Post-VitalOscillator Verification.

Hypothesis: VitalOscillator (tri-heart) provides basal motility that:
  1. Breaks the cold-start deadlock (body moves from dead-stop)
  2. Generates spatial dT/dt at skin patches (Lissajous wandering)
  3. Keeps Shadow col from saturating (changing thermal input = prediction errors)
  4. Maintains DA activity beyond 20k steps (unlike EXP-015 DA collapse)
  5. Eventually produces directional thermal taxis

Comparison with EXP-015:
  - EXP-015: zero vestibular, zero basal motor -> body stationary -> DA collapsed
  - EXP-016: zero vestibular, VitalOscillator heartbeat -> body sways -> ???

Signal chain under test:
  VitalOscillator --> Motor.inject() --> Body moves
       |
  SkinPatch(Fourier) --> Thermo/Noci --> SomatoRelay --> Enc --> Col
       |  (Xin tension)
  Shadow Enc --> Shadow Col (CRI) --> DA --> STDP modulation
       |
  Bundle weight changes --> Motor direction emergence?

Run: python nexus_v1/tests/test_exp016_vital_thermotaxis.py
"""
import sys, math, os, time
sys.path.insert(0, "d:\\cell-cc")

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

# =====================================================================
# Setup: Single strong heat source, body at distance
# =====================================================================
heat_src = HeatSource(position=[70.0, 50.0, 50.0], energy=500.0,
                      temperature=5.0, radius=30.0)
heat_src._drift = [0.0, 0.0, 0.0]  # disable drift

body = Body(position=[50.0, 50.0, 50.0])
world = World(heat_sources=[heat_src], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

c = VariantCircuit()
c.world = world

STEPS = 100_000
DT = 0.001

# =====================================================================
# Tracking
# =====================================================================
trajectory = []
THERM_PATCHES = ['front', 'back', 'left', 'right']

print("=" * 70)
print("EXP-016: Vital Heartbeat Thermal Taxis")
print("=" * 70)
print(f"Body start:   {body.position}")
print(f"Heat source:  pos={heat_src.position}, T={heat_src.temperature}, r={heat_src.radius}")
init_dist = math.sqrt(sum((body.position[i]-heat_src.position[i])**2 for i in range(3)))
print(f"Distance:     {init_dist:.1f}")
print(f"Steps:        {STEPS}")
cfg = c.vital_oscillator.config
print(f"VitalOsc:     freqs=[{cfg.frequency_x}, {cfg.frequency_y}, {cfg.frequency_z}]")
print(f"Input:        ZERO vestibular (vital heartbeat only)")
print()

t0 = time.time()

for step in range(STEPS):
    signal = {}  # zero vestibular
    c.step(signal, dt=DT)

    # Record every 1000 steps (finer than EXP-015's 2000)
    if step % 1000 == 0:
        pos = list(c.world.body.position)
        vel = list(c.world.body.velocity)
        spd = math.sqrt(sum(v*v for v in vel))
        dist = math.sqrt(sum((pos[i]-heat_src.position[i])**2 for i in range(3)))

        # DA
        da_conc = c.dopamine.concentration

        # Skin temperatures
        skin_T = {}
        for p in c.world.body.skin_patches:
            skin_T[p.patch_id] = round(p.current_temperature, 4)

        # Shadow col calcium_rate
        shadow_cr = {}
        for ax in [a for a in c.all_axes if a.startswith('therm_')]:
            s_key = f"s_col_{ax}"
            for n in c.shadow_sandbox.neurons.values():
                if n.id == s_key:
                    shadow_cr[s_key] = round(n.calcium_rate, 6)
                    break

        # Motor EMAs
        mot = {k: round(n._activation_ema, 4) for k, n in c.motor_neurons.items()}

        # Vital oscillator
        vital = list(c.vital_oscillator.outputs)
        vital_amp = c.motion_state.vital_amplitude

        # Energy
        es_fill = c.energy_store.fill_fraction
        es_level = c.energy_store.level

        trajectory.append({
            'step': step, 'pos': pos, 'vel': vel, 'speed': spd,
            'dist': dist, 'da': da_conc,
            'skin_T': skin_T, 'shadow_cr': shadow_cr,
            'motor': mot, 'vital': vital, 'vital_amp': vital_amp,
            'es_fill': es_fill, 'es_level': es_level,
        })

    # Print progress every 10k steps
    if step % 10000 == 0 and step > 0:
        t = trajectory[-1]
        pos = t['pos']
        elapsed = time.time() - t0
        rate = step / max(elapsed, 0.001)
        print(f"--- Step {step:>6d} ({elapsed:.0f}s, {rate:.0f} step/s) ---")
        print(f"  Pos:  [{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}]"
              f"  dist={t['dist']:.2f}")
        print(f"  Speed: {t['speed']:.6f}  DA: {t['da']:.6f}")
        print(f"  Vital: [{t['vital'][0]:.5f}, {t['vital'][1]:.5f}, {t['vital'][2]:.5f}]"
              f"  amp={t['vital_amp']:.6f}")
        print(f"  Skin T: front={t['skin_T'].get('front',0):.4f}"
              f"  back={t['skin_T'].get('back',0):.4f}"
              f"  L={t['skin_T'].get('left',0):.4f}"
              f"  R={t['skin_T'].get('right',0):.4f}")
        print(f"  Motor: {t['motor']}")
        # Shadow CR summary
        cr_vals = list(t['shadow_cr'].values())
        if cr_vals:
            print(f"  Shadow CR: min={min(cr_vals):.4f} max={max(cr_vals):.4f}"
                  f"  spread={max(cr_vals)-min(cr_vals):.4f}")
        print(f"  Energy: fill={t['es_fill']:.4f}  level={t['es_level']:.2f}")
        print()

elapsed_total = time.time() - t0
print(f"\nSimulation complete: {STEPS} steps in {elapsed_total:.1f}s "
      f"({STEPS/max(elapsed_total,0.001):.0f} step/s)\n")

# =====================================================================
# Analysis
# =====================================================================
print("=" * 70)
print("EXP-016 ANALYSIS")
print("=" * 70)

# --- 1. Distance trajectory ---
print("\n[1] DISTANCE TO HEAT SOURCE:")
dists = [(t['step'], t['dist']) for t in trajectory]
for i in range(0, len(dists), 10):  # every 10k steps
    s, d = dists[i]
    marker = "CLOSER" if d < init_dist else "farther"
    print(f"  step {s:>6d}: dist={d:.2f}  ({marker})")

final_dist = dists[-1][1]
delta_dist = final_dist - init_dist
print(f"\n  Initial: {init_dist:.2f}")
print(f"  Final:   {final_dist:.2f}")
print(f"  Change:  {delta_dist:+.2f}")

# --- 2. Speed profile (KEY: was 0 in EXP-015) ---
print("\n[2] SPEED PROFILE (vs EXP-015 speed ~= 0):")
speeds = [t['speed'] for t in trajectory]
# Split into epochs
for epoch_start in range(0, len(trajectory), 10):
    epoch_end = min(epoch_start + 10, len(trajectory))
    epoch_speeds = speeds[epoch_start:epoch_end]
    if epoch_speeds:
        s0 = trajectory[epoch_start]['step']
        s1 = trajectory[min(epoch_end-1, len(trajectory)-1)]['step']
        avg = sum(epoch_speeds) / len(epoch_speeds)
        mx = max(epoch_speeds)
        print(f"  step {s0:>6d}-{s1:>6d}: mean={avg:.6f}  max={mx:.6f}")

print(f"\n  Overall mean: {sum(speeds)/len(speeds):.6f}")
print(f"  Overall max:  {max(speeds):.6f}")

# --- 3. DA trajectory (KEY: collapsed to 0 at 20k in EXP-015) ---
print("\n[3] DA CONCENTRATION (vs EXP-015 collapse at 20k):")
da_vals = [t['da'] for t in trajectory]
for epoch_start in range(0, len(trajectory), 10):
    epoch_end = min(epoch_start + 10, len(trajectory))
    epoch_da = da_vals[epoch_start:epoch_end]
    if epoch_da:
        s0 = trajectory[epoch_start]['step']
        avg = sum(epoch_da) / len(epoch_da)
        mx = max(epoch_da)
        mn = min(epoch_da)
        print(f"  step {s0:>6d}: mean={avg:.6f}  range=[{mn:.6f}, {mx:.6f}]")

# --- 4. Shadow col calcium_rate (KEY: saturated to 0.97+ in EXP-015) ---
print("\n[4] SHADOW COL CALCIUM_RATE EVOLUTION:")
for epoch_i, sample_step in enumerate(range(0, len(trajectory), 10)):
    if sample_step >= len(trajectory):
        break
    t = trajectory[sample_step]
    cr = t['shadow_cr']
    if cr:
        cr_vals = list(cr.values())
        step_num = t['step']
        print(f"  step {step_num:>6d}: {' '.join(f'{v:.4f}' for v in cr_vals)}"
              f"  spread={max(cr_vals)-min(cr_vals):.4f}")

# --- 5. Vital oscillator amplitude ---
print("\n[5] VITAL OSCILLATOR:")
vital_amps = [t['vital_amp'] for t in trajectory]
print(f"  Mean amplitude: {sum(vital_amps)/len(vital_amps):.6f}")
print(f"  Max amplitude:  {max(vital_amps):.6f}")
# Check outputs aren't collinear (Lissajous)
v_first = trajectory[10]['vital'] if len(trajectory) > 10 else [0,0,0]
v_last = trajectory[-1]['vital']
print(f"  Sample early: [{v_first[0]:.5f}, {v_first[1]:.5f}, {v_first[2]:.5f}]")
print(f"  Sample late:  [{v_last[0]:.5f}, {v_last[1]:.5f}, {v_last[2]:.5f}]")

# --- 6. Skin temperature asymmetry ---
print("\n[6] SKIN TEMPERATURE ASYMMETRY:")
for t in trajectory[::20]:  # every 20k steps
    st = t['skin_T']
    fb_diff = st.get('front', 0) - st.get('back', 0)
    lr_diff = st.get('left', 0) - st.get('right', 0)
    print(f"  step {t['step']:>6d}: F-B={fb_diff:+.4f}  L-R={lr_diff:+.4f}"
          f"  front={st.get('front',0):.4f}")

# --- 7. Motor bias ---
print("\n[7] MOTOR NEURON EMAs:")
final = trajectory[-1]
for k, v in sorted(final['motor'].items()):
    print(f"  {k}: {v}")

# --- 8. Energy store ---
print("\n[8] ENERGY STORE:")
print(f"  Initial: fill={trajectory[0]['es_fill']:.4f}  level={trajectory[0]['es_level']:.2f}")
print(f"  Final:   fill={final['es_fill']:.4f}  level={final['es_level']:.2f}")

# --- 9. X-displacement (heat source at x=70) ---
print("\n[9] X-COORDINATE (heat source at x=70):")
dx = trajectory[-1]['pos'][0] - trajectory[0]['pos'][0]
print(f"  Start x: {trajectory[0]['pos'][0]:.4f}")
print(f"  End   x: {trajectory[-1]['pos'][0]:.4f}")
print(f"  dx:      {dx:+.4f}  {'(TOWARD heat)' if dx > 0 else '(AWAY from heat)'}")

# =====================================================================
# Verdict
# =====================================================================
print("\n" + "=" * 70)
print("VERDICT vs EXP-015:")
print("=" * 70)

# Gate checks
mean_speed = sum(speeds) / len(speeds)
mean_da = sum(da_vals) / len(da_vals)
# DA alive at end: check last 10% of trajectory
late_da = da_vals[len(da_vals)*9//10:]
late_da_mean = sum(late_da) / max(len(late_da), 1)

gates = []

# G1: Body speed > 0 (EXP-015: ~0)
g1 = mean_speed > 0.00001
gates.append(('G1: Body moves (speed > 0)', g1, f"mean_speed={mean_speed:.6f}"))

# G2: DA alive after 50k (EXP-015: collapsed to 0 at 20k)
g2 = late_da_mean > 0.001
gates.append(('G2: DA alive after 50k', g2, f"late_da_mean={late_da_mean:.6f}"))

# G3: Shadow CR not all saturated (EXP-015: all > 0.97)
final_cr = list(final['shadow_cr'].values())
if final_cr:
    cr_spread = max(final_cr) - min(final_cr)
    cr_max = max(final_cr)
    g3 = cr_max < 0.97 or cr_spread > 0.05
    gates.append(('G3: Shadow not saturated', g3, f"max_cr={cr_max:.4f} spread={cr_spread:.4f}"))
else:
    gates.append(('G3: Shadow not saturated', False, "no shadow data"))

# G4: Skin temperature varies over time (not static)
early_front = trajectory[5]['skin_T'].get('front', 0) if len(trajectory) > 5 else 0
late_front = trajectory[-1]['skin_T'].get('front', 0)
skin_changed = abs(late_front - early_front) > 0.001
gates.append(('G4: Skin T changes over time', skin_changed,
              f"early={early_front:.4f} late={late_front:.4f}"))

# G5: Energy store not bankrupt
g5 = final['es_fill'] > 0.1
gates.append(('G5: Energy store healthy', g5, f"fill={final['es_fill']:.4f}"))

# G6: Net distance change (bonus: actual taxis)
g6 = delta_dist < -1.0
gates.append(('G6: Net approach to heat (bonus)', g6, f"delta={delta_dist:+.2f}"))

print()
passed = 0
for name, result, detail in gates:
    status = "PASS" if result else "FAIL"
    passed += int(result)
    print(f"  [{status}] {name}  ({detail})")

print(f"\n  Score: {passed}/{len(gates)} gates passed")
print()

# Comparison table
print("  EXP-015 vs EXP-016 comparison:")
print(f"  {'Metric':<30} {'EXP-015':>12} {'EXP-016':>12}")
print(f"  {'-'*30} {'-'*12} {'-'*12}")
print(f"  {'Mean speed':<30} {'~0.00025':>12} {mean_speed:>12.6f}")
print(f"  {'DA at 50k+':<30} {'0.000':>12} {late_da_mean:>12.6f}")
print(f"  {'Total displacement':<30} {'+0.014':>12} {dx:>+12.4f}")
print(f"  {'Distance change':<30} {'-0.01':>12} {delta_dist:>+12.2f}")

print("\n" + "=" * 70)
