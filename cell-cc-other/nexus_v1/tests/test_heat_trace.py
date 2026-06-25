"""Trace motor heat over time to find heat=1000 onset."""
import sys; sys.path.insert(0, '.')
from nexus_v1.circuit.variant_adapter import VariantCircuit

c = VariantCircuit()
max_heat = 0
spike_at = None

for t in range(10000):
    c.step({'yaw': 0.3, 'pitch': 0.3, 'roll': 0.02}, dt=0.001)
    h = c.motor_neurons['move_x'].heat_output
    e = c.motor_neurons['move_x'].energy
    if h > max_heat:
        max_heat = h
    if t % 500 == 0 or h > 100:
        v = c.motor_neurons['move_x']._membrane.voltage
        ch = c.motor_neurons['move_x']._channels.get('default')
        vth = ch.v_threshold if ch else 'N/A'
        spk = len(c.motor_neurons['move_x'].spike_times)
        # binding
        col_act = {ax: c.column_neurons[ax].activation for ax in c.vestibular.axes}
        ba = c.binding_layer.compute_all(col_act)
        b_max = max(ba.values()) if ba else 0
        print(f"  t={t:>6d}  heat={h:>10.2f}  E={e:.4f}  V={v:>+8.4f}  vth={vth}  spk={spk}  b_max={b_max:.2f}")
        if h > 100 and spike_at is None:
            spike_at = t

print(f"\nMax heat seen: {max_heat:.2f}")
print(f"Heat>100 first at: {spike_at}")
