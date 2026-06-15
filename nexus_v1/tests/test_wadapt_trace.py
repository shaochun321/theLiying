"""Trace motor w_adapt to understand spike suppression."""
import sys; sys.path.insert(0, '.')
from nexus_v1.circuit.variant_adapter import VariantCircuit

c = VariantCircuit()
mot = c.motor_neurons['move_x']

print(f"{'t':>6s}  {'V_mem':>8s}  {'w_adapt':>8s}  {'act':>5s}  {'spk':>4s}  {'E':>6s}  {'heat':>8s}  {'charge':>8s}")

for t in range(15000):
    c.step({'yaw': 0.3, 'pitch': 0.3, 'roll': 0.02}, dt=0.001)
    if t % 500 == 0 or mot._spiked_this_step or (t > 4000 and t % 200 == 0):
        v = mot._membrane.voltage
        wa = mot._w_adapt
        spk = len(mot.spike_times)
        spiked = "SPK" if mot._spiked_this_step else ""
        ch = mot._membrane.charge
        print(f"{t:>6d}  {v:>+8.4f}  {wa:>8.5f}  {mot.activation:>5.2f}  {spk:>4d}  {mot.energy:>6.4f}  {mot.heat_output:>8.2f}  {ch:>+8.4f}  {spiked}")
