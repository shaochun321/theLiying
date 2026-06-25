"""STDP vs Frozen comparison."""
import sys
sys.path.insert(0, '.')
from nexus_v1.circuit.hebbian import HebbianCircuit

# Test 1: With STDP
c1 = HebbianCircuit()
for i in range(5000):
    c1.step({'yaw': 0.8}, 0.001)
aff1 = c1.vestibular.afferent_regular['yaw']
w1a = c1.vestibular.bundles_met_to_hc['yaw'].mean_weight()
w1b = c1.vestibular.bundles_hc_to_aff['yaw'].mean_weight()
print(f"With STDP:   {len(aff1.spike_times)} spikes, w_met={w1a:.4f}, w_hc={w1b:.4f}")

# Test 2: Freeze weights  
c2 = HebbianCircuit()
for b in c2.get_all_bundles():
    b.config.learning_rule = 'frozen'
for i in range(5000):
    c2.step({'yaw': 0.8}, 0.001)
aff2 = c2.vestibular.afferent_regular['yaw']
w2a = c2.vestibular.bundles_met_to_hc['yaw'].mean_weight()
w2b = c2.vestibular.bundles_hc_to_aff['yaw'].mean_weight()
print(f"Frozen STDP: {len(aff2.spike_times)} spikes, w_met={w2a:.4f}, w_hc={w2b:.4f}")
