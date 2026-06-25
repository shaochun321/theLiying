"""Experiment 4: Full closed-loop thermotaxis + shadow coupling.

Motor is firing (FIX-017). Now observe:
1. Does the body move toward the heat source? (thermotaxis)
2. Does shadow cross-modal weight encode heat source direction?
3. Does the body trajectory change as weights evolve?
"""
import sys, math
sys.path.insert(0, "d:\\cell-cc")

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

# Heat source at [65, 50, 50], body at [50, 50, 50] — needs to move +x
heat_src = HeatSource(position=[65.0, 50.0, 50.0], energy=200.0,
                      temperature=5.0, radius=25.0)
body = Body(position=[50.0, 50.0, 50.0])  # 15 units from heat source
world = World(heat_sources=[heat_src], body=body)

c = VariantCircuit()
c.world = world

STEPS = 50000
DT = 0.001

# Tracking
trajectory = []
motor_spikes = {"move_x": 0, "move_y": 0, "move_z": 0}
shadow_cross_history = []

print("=" * 70)
print("Experiment 4: Full Closed-Loop Thermotaxis")
print("=" * 70)
print(f"Body start: {body.position}")
print(f"Heat source: pos={heat_src.position}, T={heat_src.temperature}")
print(f"Distance: {math.sqrt(sum((body.position[i]-heat_src.position[i])**2 for i in range(3))):.1f}")
print(f"Steps: {STEPS}")
print()

for step in range(STEPS):
    t = step * DT

    # Moderate vestibular input (simulate natural perturbations)
    signal = {
        'yaw': 3.0 * math.sin(3.0 * t),
        'pitch': 2.0 * math.sin(2.0 * t + 0.5),
        'roll': 1.5 * math.sin(1.5 * t + 1.0),
        'oto_x': 3.0 * math.sin(4.0 * t),
        'oto_y': 2.0 * math.sin(2.5 * t + 0.3),
        'oto_z': 3.0 * math.sin(3.0 * t + 0.7),
    }
    c.step(signal, dt=DT)

    # Count motor spikes
    for k, mot in c.motor_neurons.items():
        if mot.activation > 0.01:
            motor_spikes[k] += 1

    # Record every 1000 steps
    if step % 1000 == 0:
        pos = list(c.world.body.position)
        vel = list(c.world.body.velocity)
        T = c.world.temperature_at(pos)
        dist = math.sqrt(sum((pos[i]-heat_src.position[i])**2 for i in range(3)))
        trajectory.append({
            'step': step, 'pos': pos, 'vel': vel, 'T': T, 'dist': dist,
            'col_therm': next((n.activation for k, n in c.column_neurons.items() if 'therm' in k), 0.0),
            'motor_x_V': c.motor_neurons['move_x']._membrane.voltage,
        })

    # Shadow cross-modal weights every 10k steps
    if step % 10000 == 0:
        sw = {}
        for bid, bundle in c.shadow_sandbox.bundles.items():
            if 's_cross_' in bid and 'therm' in bid:
                sw[bid] = bundle.mean_weight()
        shadow_cross_history.append({'step': step, 'weights': sw})

    # Print progress
    if step % 10000 == 0 and step > 0:
        pos = c.world.body.position
        vel = c.world.body.velocity
        dist = math.sqrt(sum((pos[i]-heat_src.position[i])**2 for i in range(3)))
        T = c.world.temperature_at(pos)

        print(f"--- Step {step:>6d} ---")
        print(f"  Body: [{pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f}]"
              f"  dist={dist:.2f}  T={T:.4f}")
        print(f"  Velocity: [{vel[0]:.6f}, {vel[1]:.6f}, {vel[2]:.6f}]")
        print(f"  Motor spikes: x={motor_spikes['move_x']}"
              f"  y={motor_spikes['move_y']}  z={motor_spikes['move_z']}")
        print(f"  Col therm: {next((n.activation for k, n in c.column_neurons.items() if 'therm' in k), 0.0):.4f}")

        # Col->Motor state
        b = c.bundles_col_to_motor[0]
        print(f"  Col->Mot: gain={b.config.synapse_gain:.4f}  w={b.mean_weight():.4f}")

        # Shadow cross-modal
        sw = shadow_cross_history[-1]['weights']
        if sw:
            vals = list(sw.values())
            print(f"  Shadow cross: avg={sum(vals)/len(vals):.6f}")
        print()

# ── Final Analysis ──
print("=" * 70)
print("THERMOTAXIS ANALYSIS")
print("=" * 70)

# 1. Trajectory: did body move toward heat source?
print("\nTrajectory (x-coordinate toward heat source at x=65):")
for i in range(0, len(trajectory), 5):
    t = trajectory[i]
    direction = "toward" if t['pos'][0] > trajectory[0]['pos'][0] else "away"
    print(f"  step {t['step']:>6d}: x={t['pos'][0]:.4f}  "
          f"dist={t['dist']:.2f}  T={t['T']:.4f}  [{direction}]")

# 2. Movement vector
start = trajectory[0]['pos']
end = trajectory[-1]['pos']
dx = end[0] - start[0]
dy = end[1] - start[1]
dz = end[2] - start[2]
total = math.sqrt(dx**2 + dy**2 + dz**2)
print(f"\nNet displacement: dx={dx:.4f} dy={dy:.4f} dz={dz:.4f} total={total:.4f}")

# Is it biased toward heat source?
# Heat source is at x=65, body starts at x=50 → +x direction
if dx > 0:
    toward_pct = dx / total * 100 if total > 0 else 0
    print(f"Toward heat source: {toward_pct:.1f}% of movement in +x direction")
else:
    print("Body moved AWAY from heat source")

# 3. Shadow weight asymmetry
print(f"\nShadow cross-modal weight evolution:")
for sh in shadow_cross_history:
    w = sh['weights']
    if w:
        sorted_w = sorted(w.items(), key=lambda x: x[1], reverse=True)
        print(f"  Step {sh['step']:>6d}:")
        for k, v in sorted_w:
            axis = k.replace('s_cross_', '').replace('_therm', '')
            print(f"    {axis}-therm: {v:.6f}")

# 4. Motor spike distribution
print(f"\nMotor spike distribution:")
total_spikes = sum(motor_spikes.values())
for k, v in motor_spikes.items():
    pct = v / total_spikes * 100 if total_spikes > 0 else 0
    print(f"  {k}: {v} ({pct:.1f}%)")

# 5. Distance to heat source over time
print(f"\nDistance to heat source:")
print(f"  Start: {trajectory[0]['dist']:.2f}")
print(f"  End:   {trajectory[-1]['dist']:.2f}")
print(f"  Change: {trajectory[-1]['dist'] - trajectory[0]['dist']:+.4f}")
if trajectory[-1]['dist'] < trajectory[0]['dist']:
    print(f"  >>> Body approached heat source <<<")
