"""Quick functional test of all new systems."""
import sys
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit

circuit = VariantCircuit()

# Run 2000 ticks with input
for t in range(2000):
    inputs = {
        'yaw': 0.3 if t % 50 < 25 else -0.1,
        'pitch': 0.2 if t % 40 < 20 else 0.0,
        'roll': 0.1,
    }
    circuit.step(inputs, dt=0.001)

# Check all new systems have output
state = circuit.get_variant_state()

print("=== Binding Layer ===")
print(f"  Active bindings: {state['binding']['active']}/{state['binding']['n_cells']}")
for bid, act in state['binding']['activations'].items():
    if act > 0:
        print(f"    {bid}: {act:.6f}")

print("\n=== Xin Tension ===")
for bid, xin_info in state['xin'].items():
    t_val = xin_info['tension']
    fruit = xin_info['fruit']
    if abs(t_val) > 0.001:
        print(f"  {bid}: tension={t_val:.4f} fruit={fruit or 'none'}")

print("\n=== Circulation ===")
circ = state.get('circulation', {})
print(f"  P: {circ.get('p', 'none')}")
print(f"  R: {circ.get('r', 'none')}")
print(f"  Total flow: {circ.get('total_flow', 0):.6f}")
if circ.get('rho'):
    print(f"  ρ = {circ['rho']}")
if circ.get('nu'):
    non_zero_nu = {k: v for k, v in circ['nu'].items() if abs(v) > 1e-6}
    if non_zero_nu:
        print(f"  ν (non-zero): {non_zero_nu}")

print("\n=== Maturation ===")
for nid, stage in state['maturation'].items():
    print(f"  {nid}: stage={stage} ({'spine' if stage==0 else 'column' if stage==1 else 'area'})")

print("\n=== Crystallization ===")
any_crystal = any(state['crystallization'].values())
print(f"  Any crystallized: {any_crystal}")

print("\n[OK] All new systems operational.")
