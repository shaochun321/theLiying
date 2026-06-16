"""EXP-015: Thermal Taxis v2 — Post-B.04 Behavioral Verification.

Symmetry test: zero vestibular bias, only world heat source gradient.
Does the organism move toward the heat source over 100k steps?

Changes from EXP-009 (test_thermotaxis.py):
  - Per-patch thermal axes (therm_front/back/left/right)
  - Shadow col calcium_rate tracking (not activation)
  - DA and energy diagnostics
  - Longer run (100k steps)
  - No vestibular input bias — pure thermal gradient drive

Signal chain under test:
  SkinPatch(Fourier) → Thermo/Noci → SomatoRelay → Enc → Col
       ↓ Xin tension
  Shadow Enc → Shadow Col (CRI) → DA → STDP modulation
       ↓ DA × pre × post
  Bundle weight changes → Motor direction emergence?
"""
import sys, math, os
sys.path.insert(0, "d:\\cell-cc")

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

# ── Setup: Single strong heat source, body at distance ──
heat_src = HeatSource(position=[70.0, 50.0, 50.0], energy=500.0,
                      temperature=5.0, radius=30.0)
# Disable drift for clean experiment
heat_src._drift = [0.0, 0.0, 0.0]

body = Body(position=[50.0, 50.0, 50.0])
world = World(heat_sources=[heat_src], body=body)
# Disable source regeneration for clean single-source experiment
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

c = VariantCircuit()
c.world = world

STEPS = 100_000
DT = 0.001

# ── Tracking ──
trajectory = []
da_history = []
shadow_history = []
thermal_enc_history = []

# thermal axes
THERM_AXES = [ax for ax in c.all_axes if ax.startswith('therm_')]
THERM_PATCHES = ['front', 'back', 'left', 'right']

print("=" * 70)
print("EXP-015: Thermal Taxis v2 — Post-B.04 Behavioral Verification")
print("=" * 70)
print(f"Body start:   {body.position}")
print(f"Heat source:  pos={heat_src.position}, T={heat_src.temperature}, r={heat_src.radius}")
init_dist = math.sqrt(sum((body.position[i]-heat_src.position[i])**2 for i in range(3)))
print(f"Distance:     {init_dist:.1f}")
print(f"Steps:        {STEPS}")
print(f"Thermal axes: {THERM_AXES}")
print(f"Input:        ZERO vestibular (pure thermal gradient)")
print()

for step in range(STEPS):
    # NO vestibular input — pure thermal gradient drive
    signal = {}
    c.step(signal, dt=DT)

    # Record every 2000 steps
    if step % 2000 == 0:
        pos = list(c.world.body.position)
        vel = list(c.world.body.velocity)
        spd = math.sqrt(sum(v*v for v in vel))
        dist = math.sqrt(sum((pos[i]-heat_src.position[i])**2 for i in range(3)))
        T_body = c.world.temperature_at(pos)

        # DA concentration
        da_conc = c.dopamine.concentration

        # Skin temperatures (from SomatosensoryChain patch_temps)
        skin_T = {}
        if hasattr(c, '_patch_temps'):
            for pid, vals in c._patch_temps.items():
                skin_T[pid] = round(vals[0], 4)

        # Thermal column activations (per-patch)
        col_act = {}
        for ax in THERM_AXES:
            if ax in c.column_neurons:
                col_act[ax] = round(c.column_neurons[ax]._activation_ema, 4)

        # Shadow col calcium_rate
        shadow_cr = {}
        for ax in THERM_AXES:
            s_key = f"s_col_{ax}"
            for n in c.shadow_sandbox.neurons.values():
                if n.id == s_key:
                    shadow_cr[s_key] = round(n.calcium_rate, 6)
                    break

        # Motor EMAs
        mot = {k: round(n._activation_ema, 4) for k, n in c.motor_neurons.items()}

        # Energy store
        es_fill = c.energy_store.level if hasattr(c, 'energy_store') else -1

        trajectory.append({
            'step': step, 'pos': pos, 'vel': vel, 'speed': spd,
            'dist': dist, 'T': T_body, 'da': da_conc,
            'skin_T': skin_T, 'col_act': col_act,
            'shadow_cr': shadow_cr, 'motor': mot, 'es': es_fill,
        })

    # Print progress
    if step % 10000 == 0:
        t = trajectory[-1] if trajectory else None
        if t:
            pos = t['pos']
            print(f"--- Step {step:>6d} ---")
            print(f"  Pos:  [{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}]"
                  f"  dist={t['dist']:.2f}  T={t['T']:.4f}")
            print(f"  Speed: {t['speed']:.6f}  DA: {t['da']:.6f}")
            print(f"  Skin T: {t['skin_T']}")
            print(f"  Motor: {t['motor']}")
            if t['shadow_cr']:
                print(f"  Shadow CR: {t['shadow_cr']}")
            print(f"  Energy: {t['es']:.2f}" if t['es'] >= 0 else "")
            print()

# ── Final Analysis ──
print("=" * 70)
print("THERMOTAXIS ANALYSIS")
print("=" * 70)

# 1. Distance trajectory
print("\n[1] DISTANCE TO HEAT SOURCE:")
dists = [(t['step'], t['dist']) for t in trajectory]
for i in range(0, len(dists), 5):  # every 10k steps
    s, d = dists[i]
    marker = "→" if d < init_dist else "←"
    print(f"  step {s:>6d}: dist={d:.2f} {marker}")

final_dist = dists[-1][1]
delta_dist = final_dist - init_dist
print(f"\n  Initial: {init_dist:.2f}")
print(f"  Final:   {final_dist:.2f}")
print(f"  Change:  {delta_dist:+.2f} {'(CLOSER)' if delta_dist < 0 else '(FARTHER)'}")

# 2. X-coordinate (heat source is at x=70)
print("\n[2] X-COORDINATE TRAJECTORY (heat source at x=70):")
x_coords = [(t['step'], t['pos'][0]) for t in trajectory]
for i in range(0, len(x_coords), 5):
    s, x = x_coords[i]
    print(f"  step {s:>6d}: x={x:.4f}")
dx = x_coords[-1][1] - x_coords[0][1]
print(f"  Δx = {dx:+.4f} {'(TOWARD)' if dx > 0 else '(AWAY)'}")

# 3. DA modulation
print("\n[3] DA CONCENTRATION:")
da_vals = [t['da'] for t in trajectory]
print(f"  Mean:  {sum(da_vals)/len(da_vals):.6f}")
print(f"  Min:   {min(da_vals):.6f}")
print(f"  Max:   {max(da_vals):.6f}")
print(f"  Range: {max(da_vals)-min(da_vals):.6f}")

# 4. Skin temperature asymmetry
print("\n[4] SKIN TEMPERATURE (final):")
final = trajectory[-1]
for pid in THERM_PATCHES:
    print(f"  {pid}: {final['skin_T'].get(pid, 'N/A')}")

# Check front-back asymmetry (heat source is +x = front)
front_T = final['skin_T'].get('front', 0)
back_T = final['skin_T'].get('back', 0)
print(f"  Front-Back diff: {front_T - back_T:+.6f}")

# 5. Shadow differentiation
print("\n[5] SHADOW COL CALCIUM_RATE (final):")
for k, v in sorted(final['shadow_cr'].items()):
    print(f"  {k}: {v}")

# 6. Motor bias
print("\n[6] MOTOR NEURON EMAs:")
for k, v in sorted(final['motor'].items()):
    print(f"  {k}: {v}")

# 7. Speed profile
print("\n[7] SPEED PROFILE:")
speeds = [t['speed'] for t in trajectory]
print(f"  Mean: {sum(speeds)/len(speeds):.6f}")
print(f"  Max:  {max(speeds):.6f}")

# 8. Verdict
print("\n" + "=" * 70)
print("VERDICT:")
# Criteria: any systematic bias toward heat source?
# Statistical: compute mean displacement per 10k-step window
windows = []
for i in range(0, len(trajectory)-5, 5):
    d0 = trajectory[i]['dist']
    d1 = trajectory[i+5]['dist']
    windows.append(d1 - d0)

approaching = sum(1 for w in windows if w < 0)
retreating = sum(1 for w in windows if w > 0)
print(f"  Approaching windows: {approaching}/{len(windows)}")
print(f"  Retreating windows:  {retreating}/{len(windows)}")

if delta_dist < -2.0:
    print("  ✅ THERMOTAXIS DETECTED — organism moved closer to heat source")
elif abs(delta_dist) < 2.0:
    print("  ⚠️ INCONCLUSIVE — no clear directional bias")
else:
    print("  ❌ NO THERMOTAXIS — organism did not approach heat source")

print("=" * 70)
