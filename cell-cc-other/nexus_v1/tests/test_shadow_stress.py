"""Stress test: Shadow metric contraction with higher eta."""
import sys
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit

circuit = VariantCircuit()

# Initialize shadow first, then increase contraction rate
circuit.shadow_sandbox.initialize(circuit)
circuit.shadow_sandbox.metric.eta = 0.1  # 20x default

# Run 10000 ticks
for t in range(10000):
    inputs = {
        'yaw': 0.3 if t % 50 < 25 else -0.1,
        'pitch': 0.2 if t % 40 < 20 else 0.0,
        'roll': 0.1,
    }
    circuit.step(inputs, dt=0.001)

shadow = circuit.get_variant_state()['shadow']

print("=== STRESS TEST: eta=0.1, 10000 steps ===")
m = shadow['metric']
print(f"  Mean main:    {m['mean_main_dist']}")
print(f"  Mean shadow:  {m['mean_shadow_dist']}")
print(f"  Contraction:  {m['contraction_ratio']}")
print(f"  Variance:     {m['shadow_variance']}")

c = shadow['clusters']
print(f"  N clusters:   {c['n_clusters']}")
print(f"  Max fraction: {c['max_cluster_fraction']}")
print(f"  Sizes:        {c['cluster_sizes']}")

col = shadow['collapse']
print(f"  Collapse:     {col['score']} {'COLLAPSING!' if col['is_collapsing'] else 'OK'}")
for w in col['warnings']:
    print(f"    WARNING: {w}")

fe = shadow['free_energy']
print(f"  K={fe['K']:.6f}, nu={fe['nu']:.8f}, trend={fe['trend']}")

print("\n[DONE]")
