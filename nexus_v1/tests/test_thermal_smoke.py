"""Smoke test: 7-axis circuit with thermal + body movement."""
import sys
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import math
from nexus_v1.circuit.variant_adapter import VariantCircuit

c = VariantCircuit()

print("=" * 60)
print("Structure Summary")
print("=" * 60)
print(f"All axes: {c.all_axes}")
print(f"Encoding neurons: {len(c.encoding_neurons)} (7×2=14)")
print(f"Column neurons: {len(c.column_neurons)} (7)")
print(f"Motor neurons: {len(c.motor_neurons)} (3)")
print(f"Binding cells: {c.binding_layer.n_cells} (C(7,2)=21)")
print(f"Heat sources: {len(c.world.heat_sources)}")
print(f"  pos={c.world.heat_sources[0].position}, T={c.world.heat_sources[0].temperature}")
print(f"Body start: {c.world.body.position}")

# List cross-modal bindings
bind_ids = list(c.binding_layer.cells.keys())
cross_modal = [b for b in bind_ids if 'therm' in b]
intra_vest = [b for b in bind_ids if 'therm' not in b]
print(f"\nIntra-vestibular bindings: {len(intra_vest)}")
print(f"Cross-modal bindings: {len(cross_modal)}")
for b in cross_modal:
    print(f"  {b}")

print("\n" + "=" * 60)
print("Running 5000 steps")
print("=" * 60)

signal = {}
for step in range(5000):
    # Vary vestibular input (simulate gentle motion)
    t = step * 0.001
    signal = {
        'yaw': 0.5 * math.sin(2.0 * t),
        'pitch': 0.3 * math.sin(1.5 * t + 0.5),
        'roll': 0.2 * math.sin(1.0 * t + 1.0),
        'oto_x': 0.4 * math.sin(3.0 * t),
        'oto_y': 0.3 * math.sin(2.5 * t + 0.3),
        'oto_z': 0.5 * math.sin(2.0 * t + 0.7),
    }
    c.step(signal, dt=0.001)

    if step % 1000 == 0 and step > 0:
        pos = c.world.body.position
        vel = c.world.body.velocity
        T_body = c.world.temperature_at(pos)
        enc_reg = c.encoding_neurons['reg_therm'].activation
        enc_irr = c.encoding_neurons['irr_therm'].activation
        col_therm = c.column_neurons['therm'].activation

        print(f"\n--- Step {step} ---")
        print(f"  Body pos: [{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}]")
        print(f"  Body vel: [{vel[0]:.6f}, {vel[1]:.6f}, {vel[2]:.6f}]")
        print(f"  T at body: {T_body:.4f}")
        print(f"  Enc therm reg: {enc_reg:.6f}")
        print(f"  Enc therm irr: {enc_irr:.6f}")
        print(f"  Col therm: {col_therm:.6f}")
        
        # Motor output
        motor = {k: round(n.activation, 4) for k, n in c.motor_neurons.items()}
        print(f"  Motor: {motor}")
        
        # Binding: compare intra vs cross
        col_act_dict = {ax: c.column_neurons[ax].activation for ax in c.all_axes}
        binding_act = c.binding_layer.compute_all(col_act_dict)
        
        active_intra = sum(1 for b in intra_vest if binding_act.get(b, 0) > 0.001)
        active_cross = sum(1 for b in cross_modal if binding_act.get(b, 0) > 0.001)
        print(f"  Active bindings: intra={active_intra}/{len(intra_vest)}, cross={active_cross}/{len(cross_modal)}")

print("\n" + "=" * 60)
print("Final state")
print("=" * 60)
print(f"Body pos: {[round(p,3) for p in c.world.body.position]}")
print(f"Heat source energy: {c.world.heat_sources[0].energy:.1f}")
print(f"Muscle energy spent: {c.muscle_system.total_energy_spent():.4f}")

# All column activations
print("\nColumn activations:")
for ax in c.all_axes:
    act = c.column_neurons[ax].activation
    print(f"  col_{ax}: {act:.6f}")
