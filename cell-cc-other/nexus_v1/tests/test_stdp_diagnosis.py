"""DEG-007 诊断: STDP 权重不演化的根因。"""
import sys
sys.path.insert(0, '.')
from nexus_v1.circuit.hebbian import HebbianCircuit

c = HebbianCircuit()

# Run 2000 steps
for i in range(2000):
    c.step({'yaw': 0.8}, 0.001)

print("=== STDP TRACE DIAGNOSIS ===\n")

# Check traces on key neurons
aff = c.vestibular.afferent_regular['yaw']
hc = c.vestibular.haircell_neurons['yaw']
enc = c.encoding_neurons['reg_yaw']

print(f"HairCell pre_trace:  {hc.pre_trace:.6f}")
print(f"HairCell post_trace: {hc.post_trace:.6f}  ← THIS IS THE BUG")
print(f"Aff_reg pre_trace:   {aff.pre_trace:.6f}")
print(f"Aff_reg post_trace:  {aff.post_trace:.6f}  ← THIS IS THE BUG")
print(f"Enc pre_trace:       {enc.pre_trace:.6f}")
print(f"Enc post_trace:      {enc.post_trace:.6f}  ← THIS IS THE BUG")

# Check weights
print(f"\n=== WEIGHT EVOLUTION ===")
for axis in ['yaw']:
    b1 = c.vestibular.bundles_met_to_hc[axis]
    b2 = c.vestibular.bundles_hc_to_aff[axis]
    print(f"\n{axis}:")
    print(f"  MET→HC weight: {b1.mean_weight():.6f}  (init: {b1.config.initial_weight})")
    print(f"  HC→Aff weight: {b2.mean_weight():.6f}  (init: {b2.config.initial_weight})")

# Encoding bundles  
for name, b in c.encoding_bundles.items():
    if 'yaw' in name:
        print(f"  {name} weight: {b.mean_weight():.6f}  (init: {b.config.initial_weight})")

print(f"\n=== ROOT CAUSE ===")
print(f"post_trace is NEVER incremented in neuron.py L344:")
print(f"  self.post_trace = self.post_trace * decay_post")
print(f"  → Missing: + abs(self.activation)")
print(f"  → post_trace always = 0 → dw always = 0")
