"""P3: Long-run stability test — 30s simulation."""
import sys
sys.path.insert(0, '.')
from nexus_v1.circuit.hebbian import HebbianCircuit

c = HebbianCircuit()

print("=== 30s Long-Run Stability Test ===\n")
print(f"{'Time(s)':>8s}  {'MET→HC':>8s}  {'HC→Aff':>8s}  {'Aff→Enc':>8s}  {'Enc→Col':>8s}  {'Col→Mot':>8s}  {'Aff_spk':>8s}  {'Aff_Hz':>7s}  {'HC_E':>6s}  {'Mot_E':>6s}")

last_spk = 0
for step in range(30000):
    c.step({'yaw': 0.8}, 0.001)
    t = (step + 1) * 0.001
    
    if (step + 1) % 5000 == 0:
        aff = c.vestibular.afferent_regular['yaw']
        spk = len(aff.spike_times)
        new_spk = spk - last_spk
        hz = new_spk / 5.0
        last_spk = spk
        
        hc = c.vestibular.haircell_neurons['yaw']
        mot = c.motor_neurons['move_x']
        
        w_met = c.vestibular.bundles_met_to_hc['yaw'].mean_weight()
        w_hc = c.vestibular.bundles_hc_to_aff['yaw'].mean_weight()
        
        # Find other bundles
        w_aff = w_enc = w_col = 0
        for b in c.get_all_bundles():
            if b.config.bundle_id == 'aff_reg_to_enc_yaw':
                w_aff = b.mean_weight()
            elif b.config.bundle_id == 'enc_to_col_yaw':
                w_enc = b.mean_weight()
            elif b.config.bundle_id == 'col_to_motor':
                w_col = b.mean_weight()
        
        print(f"{t:>8.1f}  {w_met:>8.4f}  {w_hc:>8.4f}  {w_aff:>8.4f}  {w_enc:>8.4f}  {w_col:>8.4f}  {spk:>8d}  {hz:>7.1f}  {hc.energy:>6.3f}  {mot.energy:>6.3f}")

print(f"\n=== Stability Verdict ===")
# Check final state
aff = c.vestibular.afferent_regular['yaw']
hc = c.vestibular.haircell_neurons['yaw']
mot = c.motor_neurons['move_x']
print(f"  Aff total spikes: {len(aff.spike_times)}")
print(f"  HC energy: {hc.energy:.3f}")
print(f"  Motor energy: {mot.energy:.3f}")

# Check weights bounded
all_ok = True
for b in c.get_all_bundles():
    w = b.mean_weight()
    if w < 0 or w > 1:
        print(f"  ✗ {b.config.bundle_id} weight out of range: {w}")
        all_ok = False
if all_ok:
    print(f"  ✓ All weights in [0, 1]")

# Check no energy depletion
for n in c.get_all_neurons():
    if n.energy < 0.001:
        print(f"  ✗ {n.config.neuron_id} energy depleted: {n.energy}")
        all_ok = False
if all_ok:
    print(f"  ✓ No energy depletion")
    print(f"  ★ 30s LONG-RUN STABLE")
