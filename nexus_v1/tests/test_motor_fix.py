"""FIX-017 verification: does Motor fire now?"""
import sys, math
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

heat_src = HeatSource(position=[60.0, 50.0, 50.0], energy=200.0,
                      temperature=5.0, radius=25.0)
body = Body(position=[55.0, 50.0, 50.0])
body.velocity = [0.05, 0.0, 0.0]
world = World(heat_sources=[heat_src], body=body)
c = VariantCircuit()
c.world = world

# Track motor spikes
motor_spike_count = {"move_x": 0, "move_y": 0, "move_z": 0}
body_positions = []

STEPS = 20000
for step in range(STEPS):
    t = step * 0.001
    signal = {
        'yaw': 5.0 * math.sin(3.0 * t),
        'pitch': 3.0 * math.sin(2.0 * t + 0.5),
        'roll': 2.0 * math.sin(1.5 * t + 1.0),
        'oto_x': 4.0 * math.sin(4.0 * t),
        'oto_y': 3.0 * math.sin(2.5 * t + 0.3),
        'oto_z': 5.0 * math.sin(3.0 * t + 0.7),
    }
    c.step(signal, dt=0.001)

    # Count motor spikes
    for k, mot in c.motor_neurons.items():
        if mot.activation > 0.01:
            motor_spike_count[k] += 1

    # Record body position periodically
    if step % 1000 == 0:
        body_positions.append(list(c.world.body.position))

    # Print progress
    if step % 5000 == 0:
        pos = c.world.body.position
        print(f"Step {step:>6d}:")

        # Motor state
        for k, mot in c.motor_neurons.items():
            ch = mot._channels.get("default")
            v_th = ch.v_threshold if ch else "?"
            print(f"  {k}: V={mot._membrane.voltage:.6f}"
                  f"  act={mot.activation:.4f}"
                  f"  E={mot.energy:.4f}"
                  f"  threshold={v_th:.4f}"
                  f"  spikes={motor_spike_count[k]}")

        # Col->Motor
        b = c.bundles_col_to_motor[0]
        currents = b.propagate()
        print(f"  Col->Motor: gain={b.config.synapse_gain:.4f}"
              f"  w={b.mean_weight():.4f}"
              f"  I={currents[0]:.4f}")

        # PowerRail check
        mot = c.motor_neurons["move_x"]
        I = currents[0]
        V_supply = mot.config.vdd * mot.energy / (1 + abs(I) * mot.config.r_supply)
        print(f"  V_supply={V_supply:.4f}  (need > threshold)")

        # Body
        print(f"  Body: [{pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f}]")

        # Afferent energy
        r = c.vestibular.afferent_regular["yaw"]
        print(f"  Aff_yaw_reg: E={r.energy:.4f}")
        print()

# Final summary
print("=" * 60)
print("FINAL SUMMARY")
print("=" * 60)
print(f"Motor spikes: {motor_spike_count}")
print(f"Total motor spikes: {sum(motor_spike_count.values())}")
print(f"Body start: {body_positions[0]}")
print(f"Body end:   {body_positions[-1]}")
dx = body_positions[-1][0] - body_positions[0][0]
dy = body_positions[-1][1] - body_positions[0][1]
dz = body_positions[-1][2] - body_positions[0][2]
dist = math.sqrt(dx**2 + dy**2 + dz**2)
print(f"Distance moved: {dist:.4f}")
print(f"Muscle energy spent: {c.muscle_system.total_energy_spent():.6f}")
if sum(motor_spike_count.values()) > 0:
    print(">>> MOTOR IS FIRING! Closed loop is active! <<<")
else:
    print(">>> Motor still silent <<<")
