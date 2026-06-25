"""Trace binding->motor injection to find heat=1000 root cause."""
import sys; sys.path.insert(0, '.')
from nexus_v1.circuit.variant_adapter import VariantCircuit

c = VariantCircuit()
for t in range(5000):
    c.step({'yaw': 0.3, 'pitch': 0.3, 'roll': 0.02}, dt=0.001)

# Check binding activations
col_act_dict = {ax: c.column_neurons[ax].activation for ax in c.vestibular.axes}
binding_acts = c.binding_layer.compute_all(col_act_dict)
print("Binding activations:")
for bid, b_act in sorted(binding_acts.items()):
    if b_act > 1e-6:
        print(f"  {bid}: act={b_act:.4f}")

# Check what's being injected
total_inject = 0
for bid, b_act in binding_acts.items():
    if b_act < 1e-6:
        continue
    for mid in c.motor_neurons:
        w = c._binding_motor_weights[bid][mid]
        inj = b_act * w * 10.0
        total_inject += inj
        if inj > 0.001:
            print(f"  {bid}->{mid}: inject={inj:.6f} (b_act={b_act:.4f}, w={w:.6f})")
print(f"Total motor inject per step from binding: {total_inject:.6f}")

# Normal col->mot propagation
for b in c.bundles_col_to_motor:
    curr = b.propagate()
    print(f"Normal col->mot propagated: {[f'{x:.4f}' for x in curr]}")

# Motor state
for k, m in c.motor_neurons.items():
    print(f"Motor {k}: V_mem={m._membrane.voltage:.4f}, charge={m._membrane.charge:.4f}, heat={m.heat_output:.2f}, E={m.energy:.4f}")
