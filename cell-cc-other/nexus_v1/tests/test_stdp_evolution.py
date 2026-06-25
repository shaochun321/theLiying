"""STDP 权重演化分析。"""
import sys
sys.path.insert(0, '.')
from nexus_v1.circuit.hebbian import HebbianCircuit

c = HebbianCircuit()

print("=== STDP WEIGHT EVOLUTION (post-fix) ===\n")
print(f"{'Step':>6s}  {'MET→HC':>8s}  {'HC→Aff':>8s}  {'HC_rel':>8s}  {'Aff_spk':>8s}  {'HC_E':>6s}")

prev_spk = 0
for i in range(5000):
    c.step({'yaw': 0.8}, 0.001)
    
    if i % 500 == 0 or i < 50:
        b1 = c.vestibular.bundles_met_to_hc['yaw']
        b2 = c.vestibular.bundles_hc_to_aff['yaw']
        hc = c.vestibular.haircell_neurons['yaw']
        aff = c.vestibular.afferent_regular['yaw']
        spk = len(aff.spike_times)
        print(f"{i:>6d}  {b1.mean_weight():>8.4f}  {b2.mean_weight():>8.4f}  "
              f"{hc.release_rate:>8.4f}  {spk:>8d}  {hc.energy:>6.3f}")
