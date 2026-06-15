"""CV 根因分析: 暂态 vs 稳态 ISI 分布。

目标: 确定 CV=0.471 主要来自:
  A) 暂态: Ca²⁺ ramp-up 期间的不规则 ISI
  B) 稳态: 稳定放电时仍然高 CV
  
这决定了修复路径:
  A → 需要更快的初始化 (Ca²⁺ 快通道)
  B → 需要结构性修复 (NDR/ECM/振荡器)
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.hebbian import HebbianCircuit

STEPS = 5000
DT = 0.001

circuit = HebbianCircuit()

# Collect all spike times with timestamps
spike_data = {}
for axis in circuit.vestibular.axes:
    spike_data[axis] = []

for step_i in range(STEPS):
    circuit.step({'yaw': 0.8}, DT)
    
    t = step_i * DT
    for axis in circuit.vestibular.axes:
        aff = circuit.vestibular.afferent_regular[axis]
        if aff.activation == 1.0:  # spiking
            spike_data[axis].append(t)

print("=" * 70)
print("CV ROOT CAUSE ANALYSIS — Transient vs Steady State")
print("=" * 70)

for axis in circuit.vestibular.axes:
    spikes = spike_data[axis]
    if len(spikes) < 5:
        print(f"\n{axis}: insufficient spikes ({len(spikes)})")
        continue
    
    # Compute all ISIs
    isis = [spikes[i+1] - spikes[i] for i in range(len(spikes)-1)]
    
    # Split into phases
    # Phase 1: first 20% of time (ramp-up / transient)
    # Phase 2: last 60% of time (steady state)
    t_total = STEPS * DT
    t_transient_end = t_total * 0.2  # first 1 second
    t_steady_start = t_total * 0.4   # after 2 seconds
    
    isis_transient = []
    isis_steady = []
    
    for i in range(len(isis)):
        t_mid = (spikes[i] + spikes[i+1]) / 2
        if t_mid <= t_transient_end:
            isis_transient.append(isis[i])
        elif t_mid >= t_steady_start:
            isis_steady.append(isis[i])
    
    def compute_cv(isi_list):
        if len(isi_list) < 2:
            return float('nan'), 0, 0
        mean_isi = sum(isi_list) / len(isi_list)
        var = sum((x - mean_isi)**2 for x in isi_list) / len(isi_list)
        cv = var**0.5 / mean_isi if mean_isi > 0 else 999
        return cv, mean_isi, len(isi_list)
    
    cv_all, mean_all, n_all = compute_cv(isis)
    cv_trans, mean_trans, n_trans = compute_cv(isis_transient)
    cv_steady, mean_steady, n_steady = compute_cv(isis_steady)
    
    print(f"\n── {axis.upper()} ──")
    print(f"  Total spikes: {len(spikes)}")
    print(f"  {'Phase':12s} {'N_ISI':>8s} {'mean ISI':>10s} {'freq Hz':>10s} {'CV':>8s}")
    print(f"  {'All':12s} {n_all:>8d} {mean_all*1000:>8.2f} ms {1/mean_all if mean_all>0 else 0:>8.1f} Hz {cv_all:>8.3f}")
    print(f"  {'Transient':12s} {n_trans:>8d} {mean_trans*1000:>8.2f} ms {1/mean_trans if mean_trans>0 else 0:>8.1f} Hz {cv_trans:>8.3f}")
    print(f"  {'Steady':12s} {n_steady:>8d} {mean_steady*1000:>8.2f} ms {1/mean_steady if mean_steady>0 else 0:>8.1f} Hz {cv_steady:>8.3f}")
    
    # Detailed ISI distribution in 10 time bins
    print(f"\n  Time-resolved ISI (10 bins):")
    bin_size = t_total / 10
    for b in range(10):
        t_lo = b * bin_size
        t_hi = (b + 1) * bin_size
        bin_isis = [isis[i] for i in range(len(isis)) 
                    if t_lo <= (spikes[i]+spikes[i+1])/2 < t_hi]
        if len(bin_isis) >= 2:
            cv_b, mean_b, n_b = compute_cv(bin_isis)
            print(f"    [{t_lo:.1f}-{t_hi:.1f}s] N={n_b:>3d}  "
                  f"mean={mean_b*1000:.2f}ms  "
                  f"freq={1/mean_b:.1f}Hz  "
                  f"CV={cv_b:.3f}  "
                  f"{'◼' * max(1, min(20, int(cv_b * 20)))}")
        elif len(bin_isis) == 1:
            print(f"    [{t_lo:.1f}-{t_hi:.1f}s] N=  1  ISI={bin_isis[0]*1000:.2f}ms  (insufficient)")
        else:
            print(f"    [{t_lo:.1f}-{t_hi:.1f}s] N=  0  (no spikes)")

    # Root cause verdict
    print(f"\n  VERDICT:")
    if not math.isnan(cv_trans) and not math.isnan(cv_steady):
        if cv_trans > cv_steady * 2:
            print(f"    → Transient-dominated (CV_trans={cv_trans:.3f} >> CV_steady={cv_steady:.3f})")
            print(f"    → Fix: faster Ca²⁺ initialization")
        elif cv_steady > 0.3:
            print(f"    → Steady-state still high (CV_steady={cv_steady:.3f} > 0.3)")
            print(f"    → Fix: structural (NDR/ECM/oscillator)")
        else:
            print(f"    → Steady-state acceptable (CV_steady={cv_steady:.3f})")
            print(f"    → Fix: only transient needs work")
    else:
        print(f"    → Insufficient data for verdict")
