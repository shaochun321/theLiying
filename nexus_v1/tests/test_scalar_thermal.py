"""Quick smoke test: scalar thermal sensor + motor firing."""
import sys, math
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

heat_src = HeatSource(position=[65.0, 50.0, 50.0], energy=200.0,
                      temperature=5.0, radius=25.0)
body = Body(position=[50.0, 50.0, 50.0])
world = World(heat_sources=[heat_src], body=body)

c = VariantCircuit()
c.world = world

spikes = 0
for step in range(10000):
    t = step * 0.001
    signal = {
        'yaw': 3.0 * math.sin(3.0 * t),
        'pitch': 2.0 * math.sin(2.0 * t + 0.5),
        'roll': 1.5 * math.sin(1.5 * t + 1.0),
        'oto_x': 3.0 * math.sin(4.0 * t),
        'oto_y': 2.0 * math.sin(2.5 * t + 0.3),
        'oto_z': 3.0 * math.sin(3.0 * t + 0.7),
    }
    c.step(signal, dt=0.001)
    for m in c.motor_neurons.values():
        if m.activation > 0.01:
            spikes += 1

    if step == 5000:
        state = c.thermal_membrane.get_state()
        pos = c.world.body.position
        T = c.world.temperature_at(pos)
        print(f"Step 5000:")
        print(f"  Body: [{pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f}]")
        print(f"  T_raw: {T:.4f}")
        print(f"  Sensor state: {state}")
        print(f"  Col therm: {c.column_neurons['therm'].activation:.6f}")
        print(f"  Motor spikes so far: {spikes}")

pos = c.world.body.position
dist = math.sqrt(sum((pos[i]-heat_src.position[i])**2 for i in range(3)))
print(f"\nFinal (10k steps):")
print(f"  Body: [{pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f}]")
print(f"  Distance to heat: {dist:.2f}")
print(f"  Total motor spikes: {spikes}")
print(f"  Axes: {c.all_axes}")
print(f"  Encoding neurons: {len(c.encoding_neurons)}")
print(f"  Column neurons: {len(c.column_neurons)}")
print(f"  Binding cells: {c.binding_layer.n_cells}")
print(f"  Shadow neurons: {len(c.shadow_sandbox.neurons)}")
if spikes > 0:
    print(">>> PASS: Motor firing, closed loop active <<<")
else:
    print(">>> FAIL: Motor silent <<<")
