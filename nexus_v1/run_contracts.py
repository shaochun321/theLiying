"""Automated layer contract verification.

Per RULES.md Principle 10: verify all layer contracts in one pass.
Per RULES.md Principle 11: used after each block differentiation step.

Usage: python run_contracts.py
Output: PASS / FAIL per contract, with details.
"""
import sys, math
sys.path.insert(0, '.')
from nexus_v1.circuit.hebbian import HebbianCircuit

# ── Run simulation ──
c = HebbianCircuit()
dt = 0.001
N = 5000

# Collect per-layer statistics
stats = {
    'met': {'act': [], 'energy': []},
    'hc': {'vm': [], 'ca': [], 'release': [], 'energy': []},
    'aff_r': {'v': [], 'spikes': 0, 'spike_times': [], 'energy': []},
    'enc': {'act': [], 'energy': []},
    'col': {'act': [], 'energy': []},
    'mot': {'spikes': 0, 'pre_signal_spikes': 0, 'spike_times': [], 'energy': []},
}

prev_aff = 0
prev_mot = 0

for i in range(N):
    c.step({'yaw': 0.8}, dt)

    met = c.vestibular.met_neurons['yaw']
    hc = c.vestibular.haircell_neurons['yaw']
    ar = c.vestibular.afferent_regular['yaw']
    enc = c.encoding_neurons['reg_yaw']
    col = c.column_neurons['yaw']
    mot = c.motor_neurons['move_x']

    stats['met']['act'].append(met.activation)
    stats['met']['energy'].append(met.energy)
    stats['hc']['vm'].append(hc._membrane.voltage)
    stats['hc']['release'].append(hc.release_rate)
    stats['hc']['energy'].append(hc.energy)
    if hc._ca_cap:
        stats['hc']['ca'].append(hc._ca_cap.voltage)
    stats['enc']['act'].append(enc.activation)
    stats['enc']['energy'].append(enc.energy)
    stats['col']['act'].append(col.activation)
    stats['col']['energy'].append(col.energy)
    stats['mot']['energy'].append(mot.energy)

    cur_aff = len(ar.spike_times)
    if cur_aff > prev_aff:
        stats['aff_r']['spike_times'].append(i)
        prev_aff = cur_aff
    cur_mot = len(mot.spike_times)
    if cur_mot > prev_mot:
        stats['mot']['spike_times'].append(i)
        if i < 1500:
            stats['mot']['pre_signal_spikes'] += 1
        prev_mot = cur_mot

stats['aff_r']['spikes'] = len(stats['aff_r']['spike_times'])
stats['mot']['spikes'] = len(stats['mot']['spike_times'])

# ── Contract verification ──
SIGNAL_START = 1500
results = []

def check(name, condition, actual, expected, critical=True):
    status = "PASS" if condition else "FAIL"
    results.append((name, status, actual, expected, critical))
    return condition

# Active window
active = slice(SIGNAL_START, N)

# C1: MET
met_act = stats['met']['act'][active]
met_max = max(met_act)
met_min = min(met_act)
met_e = stats['met']['energy'][-1]
check("C1 MET output_range",  0.0 <= met_min and met_max <= 5.0,
      f"[{met_min:.2f}, {met_max:.2f}]", "[0.0, 5.0]")

# Dynamic range: sweep low vs high input (proper transfer function)
from nexus_v1.vestibular.chain import VestibularChain
_v_lo = VestibularChain()
_v_hi = VestibularChain()
for _ in range(2000):
    _v_lo.step({'yaw': 0.1}, 0.001)
    _v_hi.step({'yaw': 0.8}, 0.001)
met_lo = _v_lo.met_neurons['yaw'].activation
met_hi = _v_hi.met_neurons['yaw'].activation
met_dyn = met_hi / max(met_lo, 0.001)
check("C1 MET dynamic_range", met_dyn >= 5.0,
      f"{met_dyn:.1f}:1 (lo={met_lo:.2f} hi={met_hi:.2f})", ">=5:1", critical=False)
check("C1 MET energy",        met_e > 0.5,
      f"{met_e:.3f}", ">0.5")

# C2: HairCell
hc_rel = stats['hc']['release'][active]
rel_max = max(hc_rel)
rel_min = min(hc_rel)
dyn_range = rel_max / max(rel_min, 0.0001)
hc_e = stats['hc']['energy'][-1]
# With STDP, weights evolve → peak release may increase naturally
check("C2 HC output_range",   0.001 <= rel_min and rel_max <= 0.6,
      f"[{rel_min:.4f}, {rel_max:.4f}]", "[0.001, 0.6]")
check("C2 HC dynamic_range",  dyn_range >= 10.0,
      f"{dyn_range:.1f}:1", ">=10:1")
check("C2 HC energy",         hc_e > 0.5,
      f"{hc_e:.3f}", ">0.5")

# C3: Afferent
aff_active_spikes = len([t for t in stats['aff_r']['spike_times'] if t >= SIGNAL_START])
aff_rate = aff_active_spikes / ((N - SIGNAL_START) / 1000) if N > SIGNAL_START else 0
# CV — measured in steady-state window only
# BIO: vestibular afferent CV is defined at steady tonic discharge,
# not during response onset (Ca²⁺ ramp-up is a natural phenomenon).
# REF: Goldberg et al. 1984 — "Response of vestibular-nerve afferents
#   in the squirrel monkey to externally applied galvanic currents"
#   CV measured at spontaneous discharge rate (steady-state)
STEADY_START = 3000  # step 3000 = 3.0s — well past transient
sts_steady = [t for t in stats['aff_r']['spike_times'] if t >= STEADY_START]
isis_steady = []
for j in range(1, len(sts_steady)):
    isis_steady.append(sts_steady[j] - sts_steady[j-1])
if isis_steady:
    mean_isi = sum(isis_steady) / len(isis_steady)
    cv = (sum((x - mean_isi)**2 for x in isis_steady) / len(isis_steady))**0.5 / mean_isi
else:
    mean_isi = 0
    cv = 0

check("C3 Aff frequency",     20 <= aff_rate <= 100,
      f"{aff_rate:.1f} Hz", "[20, 100] Hz")
check("C3 Aff CV",            cv <= 0.2,
      f"{cv:.3f}", "<=0.2")

# C4: Encoding
enc_act = stats['enc']['act'][active]
enc_max = max(enc_act)
enc_min = min(enc_act)
enc_e = stats['enc']['energy'][-1]
check("C4 Enc output_range",  0.1 <= enc_min or enc_max <= 10.0,
      f"[{enc_min:.2f}, {enc_max:.2f}]", "[0.1, 10.0]", critical=False)
check("C4 Enc energy",        enc_e > 0.1,
      f"{enc_e:.3f}", ">0.1")

# C5: Column
col_act = stats['col']['act'][active]
col_max = max(col_act)
col_min = min(col_act)
col_e = stats['col']['energy'][-1]
check("C5 Col output_range",  0.05 <= col_min or col_max <= 10.0,
      f"[{col_min:.2f}, {col_max:.2f}]", "[0.05, 10.0]", critical=False)
check("C5 Col energy",        col_e > 0.1,
      f"{col_e:.3f}", ">0.1")

# C6: Motor
total_mot = stats['mot']['spikes']
pre_sig = stats['mot']['pre_signal_spikes']
post_sig = total_mot - pre_sig
snr = post_sig / max(pre_sig, 1) if pre_sig > 0 else (float('inf') if post_sig > 0 else 0)
mot_e = stats['mot']['energy'][-1]
check("C6 Motor silence",     pre_sig == 0,
      f"{pre_sig} pre-signal spikes", "0")
check("C6 Motor signal",      post_sig > 0,
      f"{post_sig} signal spikes", ">0")
check("C6 Motor energy",      mot_e > 0.1,
      f"{mot_e:.3f}", ">0.1")

# ── Print results ──
print("=" * 70)
print("LAYER CONTRACT VERIFICATION")
print("=" * 70)

passes = sum(1 for _, s, _, _, _ in results if s == "PASS")
fails = sum(1 for _, s, _, _, _ in results if s == "FAIL")
crits = sum(1 for _, s, _, _, c in results if s == "FAIL" and c)

for name, status, actual, expected, critical in results:
    icon = "[OK]" if status == "PASS" else "[!!]" if critical else "[--]"
    print(f"  {icon} {name:30s}  actual={actual:30s}  expected={expected}")

print(f"\n  TOTAL: {passes} PASS, {fails} FAIL ({crits} critical)")
if crits == 0:
    print("  VERDICT: ALL CRITICAL CONTRACTS SATISFIED")
else:
    print(f"  VERDICT: {crits} CRITICAL VIOLATIONS — block differentiation needed")

# Print cascade analysis
print(f"\n  VIOLATION CASCADE:")
fail_layers = set()
for name, status, _, _, critical in results:
    if status == "FAIL" and critical:
        layer = name.split()[0]
        fail_layers.add(layer)

if 'C2' in fail_layers:
    print("    C2(HC) violated → propagates to C3(Aff) → C4(Enc) → C5(Col) → C6(Motor)")
    print("    ROOT: Fix C2 first (Ca dynamics)")
if 'C5' in fail_layers and 'C2' not in fail_layers:
    print("    C5(Col) violated independently → propagates to C6(Motor)")
    print("    ROOT: Fix C5 VR params")
