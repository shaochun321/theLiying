"""Diagnostic: measure somatosensory relay output magnitude.

Confirms that thermal encoding neurons are driven by
real environmental heat, not just bias current.
"""
import math
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from nexus_v1.circuit.variant_adapter import VariantCircuit

c = VariantCircuit()

print("Step 0: Initial relay activations:")
soma_out = c.somatosensory.get_mechanical_inputs()
for k, v in sorted(soma_out.items()):
    print(f"  {k}: {v:.6f}")

print(f"\nBody position: {c.world.body.position}")
print(f"Heat sources: {[(s.position, s.effective_temperature(), s.radius) for s in c.world.heat_sources]}")

# Run 100 steps with oto_x only (no explicit thermal)
for i in range(100):
    t = i * 0.001
    c.step({'oto_x': 200 * math.sin(2 * math.pi * 0.5 * t)}, 1.0)

print("\nAfter 100 steps:")
soma_out = c.somatosensory.get_mechanical_inputs()
for k, v in sorted(soma_out.items()):
    print(f"  {k}: {v:.6f}")

# Check skin patch temperatures
for patch in c.world.body.skin_patches:
    pos = patch.world_position(c.world.body)
    T_env = c.world.temperature_at(pos)
    print(f"  Patch {patch.patch_id}: T_skin={patch.current_temperature:.6f}, T_env={T_env:.6f}, damage={patch.damage_integral:.6f}")

# Check encoding neuron activations
for key in ['reg_therm_front', 'reg_therm_back', 'reg_oto_x']:
    enc = c.encoding_neurons[key]
    print(f"  Enc {key}: act_ema={enc._activation_ema:.6f}, V_m={enc._membrane.voltage:.6f}")

# Run 1000 more steps 
for i in range(1000):
    t = (100 + i) * 0.001
    c.step({'oto_x': 200 * math.sin(2 * math.pi * 0.5 * t)}, 1.0)

print("\nAfter 1100 steps:")
soma_out = c.somatosensory.get_mechanical_inputs()
for k, v in sorted(soma_out.items()):
    print(f"  {k}: {v:.6f}")

for key in ['reg_therm_front', 'reg_therm_back', 'reg_oto_x']:
    enc = c.encoding_neurons[key]
    print(f"  Enc {key}: act_ema={enc._activation_ema:.6f}, V_m={enc._membrane.voltage:.6f}")

# The key question: how much current does tonic_val inject?
# Encoding neuron: V_ss = I_input * R_leak = tonic_val * 5.0
# v_peak = 0.35
# If tonic_val * 5.0 > 0.35 => guaranteed spiking => activation → 1.0
print(f"\n=== Analysis ===")
for k, v in sorted(soma_out.items()):
    if k.startswith('therm_'):
        V_ss = v * 5.0  # r_leak = 5.0 in _encoding_config
        print(f"  {k}: tonic_val={v:.4f}, V_ss={V_ss:.4f}, v_peak=0.35, will_spike={'YES' if V_ss > 0.35 else 'no'}")
