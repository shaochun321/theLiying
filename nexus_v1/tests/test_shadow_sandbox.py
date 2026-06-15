"""Functional test: Structural Shadow Layer with real components."""
import sys
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit

circuit = VariantCircuit()

# Run 10000 ticks
for t in range(10000):
    inputs = {
        'yaw': 0.3 if t % 50 < 25 else -0.1,
        'pitch': 0.2 if t % 40 < 20 else 0.0,
        'roll': 0.1,
    }
    circuit.step(inputs, dt=0.001)

state = circuit.get_variant_state()
shadow = state['shadow']

print("=== Structural Shadow Layer (10000 steps) ===")
print(f"  Status:   {shadow['status']}")
print(f"  Neurons:  {shadow['n_neurons']}")
print(f"  Bundles:  {shadow['n_bundles']}")

print("\n--- Contraction ---")
c = shadow['contraction']
print(f"  Active cross-links:  {c['n_active_cross']}")
print(f"  Silent bundles:      {c['n_silent']}")
if c['active_cross_links']:
    for bid, w in sorted(c['active_cross_links'].items(), key=lambda x: -x[1])[:5]:
        print(f"    {bid}: w={w}")

print("\n--- Energy ---")
e = shadow['energy']
print(f"  Total energy:  {e['total']}")
print(f"  Min energy:    {e['min']}")
print(f"  Total heat:    {e['total_heat']}")

print("\n--- Free Energy ---")
fe = shadow['free_energy']
print(f"  K (raw):    {fe['K']}")
print(f"  K (EMA):    {fe['K_ema']}")
print(f"  nu (dK/dt): {fe['nu']}")
print(f"  Trend:      {fe['trend']}")

print("\n--- ECM ---")
ecm = shadow['ecm']
print(f"  Enc temp:  {ecm['enc_temp']}")
print(f"  Col temp:  {ecm['col_temp']}")
print(f"  Mot temp:  {ecm['mot_temp']}")
print(f"  Enc PNN:   {ecm['enc_pnn']}")

print("\n--- Minkowski ds^2 ---")
ds2 = shadow['ds2_sample']
print(f"  Pair:    {ds2['pair']}")
print(f"  ds^2:    {ds2['ds2']}")
print(f"  Causal:  {ds2['causal']}")

print("\n[OK] Structural shadow test complete.")
