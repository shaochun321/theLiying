"""Quick regression: run 1000 steps of VariantCircuit with VitalOscillator."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit

vc = VariantCircuit()
dt = 0.001
for i in range(1000):
    vc.step({}, dt)

v = vc.vital_oscillator
ms = vc.motion_state
es = vc.energy_store.summary()

print(f"After 1000 steps:")
print(f"  vital alive: {v.is_alive}")
print(f"  vital outputs: {[round(x,6) for x in v.outputs]}")
print(f"  vital energy withdrawn: {v.total_energy_withdrawn:.6f}")
print(f"  ms.vital_amplitude: {ms.vital_amplitude:.6f}")
print(f"  energy fill: {vc.energy_store.fill_fraction:.4f}")
print(f"  noether balance: {es['noether_balance']}")
print(f"  body speed: {vc.world.body.speed():.6f}")
print(f"  body pos: {[round(p,2) for p in vc.world.body.position]}")
print("1000-STEP REGRESSION OK")
