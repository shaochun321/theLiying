"""v41.3 Ablation Study — Is it a number game?

5 ablation conditions × 3 seeds × 1000 ticks.
Baseline vs. each ablation, measuring:
  - grad_aco_w: did STDP learn gradient→motor?
  - Q4/Q1: did behavior improve?
  - STDP topology: which z_t→sig connections survived?
  - sed resting_potential: did sediment accumulate?
"""
import sys, os, random, math
base = r'D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp'
sys.path.insert(0, os.path.join(base, 'engines'))
sys.path.insert(0, base)
sys.path.insert(0, r'D:\cell-cc\experiments')

from _phase5_pipeline import build_full_circuit, inject_sensory, read_motor
from engines.practice_engine import PracticeEngine
from engines.hebbian_circuit import MetaNeuron

TICKS = 1000
SEEDS = [42, 123, 999]

def run_experiment(seed, ablation="none"):
    """Run one experiment. Returns metrics dict."""
    engine = PracticeEngine(n_particles=30, seed=seed)
    circuit = build_full_circuit()
    
    # === Apply ablation ===
    if ablation == "no_stdp":
        # Freeze ALL learning: no STDP, no BCM, no weight changes
        for layer in circuit.layers.values():
            for b in layer.bundles:
                b.learning_rule = "none"
        for b in circuit.inter_layer_bundles:
            b.learning_rule = "none"
    
    elif ablation == "no_gate":
        # CPG gate always open → gate=1.0
        # We do this by setting CPG neurons to fixed equal values
        # so gate = (a - b)*5 + 0.5 = 0.5 always ≈ half-gate
        # Actually, to make gate=1.0, we need a >> b
        cpg = circuit.layers.get("cpg")
        if cpg:
            for nid, n in cpg.neurons.items():
                if nid.endswith("_a"):
                    n.activation = 1.0
                    n.resting_potential = 1.0
                elif nid.endswith("_b"):
                    n.activation = 0.0
                    n.resting_potential = 0.0
    
    elif ablation == "no_sediment":
        # Remove sediment layer entirely
        if "sediment" in circuit.layers:
            del circuit.layers["sediment"]
        circuit.inter_layer_bundles = [
            b for b in circuit.inter_layer_bundles
            if b.bundle_id not in ("sed_to_enc", "sed_novelty_to_col")
        ]
    
    elif ablation == "no_feedback":
        # Motor output doesn't affect environment
        pass  # handled in the loop below
    
    prev = None
    intake_q = [[], [], [], []]
    
    for k in range(TICKS):
        if ablation == "no_feedback":
            cm = {'move_x': 0, 'move_y': 0, 'move_z': 0}  # motor disconnected
        else:
            cm = read_motor(circuit) if k > 0 else {'move_x':0,'move_y':0,'move_z':0}
        
        s = engine.step(cm)
        
        if ablation == "white_noise":
            # Replace ALL sensory signals with white noise
            rng = random.Random(seed * 10000 + k)
            for key in list(s.keys()):
                if isinstance(s[key], (int, float)):
                    s[key] = rng.random() * 2 - 1  # uniform [-1, 1]
        
        inject_sensory(circuit, s, engine.box_size)
        
        if ablation == "no_gate":
            # Force CPG to maintain gate=1.0 every tick
            cpg = circuit.layers.get("cpg")
            if cpg:
                for nid, n in cpg.neurons.items():
                    if nid.endswith("_a"):
                        n.activation = 1.0
                    elif nid.endswith("_b"):
                        n.activation = 0.0
        
        total_recv = sum(s.get('received_%s' % t, 0) for t in ['acoustic','thermal','luminous'])
        circuit.feed(total_recv * 0.01)
        se = {c: s.get(c, 0.5) for c in ['spectral_H','fano_H','synchrony_H','gradient_H',
              'sparseness_H','autocorrelation_H','energy_H']}
        circuit.transport(se, 'signal_entropy')
        
        for bun in circuit.inter_layer_bundles:
            sl = None
            for lid, l in circuit.layers.items():
                if bun.source_neuron_ids[0] in l.neurons:
                    sl = l; break
            if not sl:
                continue
            sa = [sl.neurons.get(sid, MetaNeuron('_','_')).activation 
                  for sid in bun.source_neuron_ids]
            pa = []
            for tid in bun.target_neuron_ids:
                for lid, l in circuit.layers.items():
                    if tid in l.neurons:
                        pa.append(l.neurons[tid].activation); break
                else:
                    pa.append(0.0)
            ta = bun.propagate(sa, post_activations=pa)
            for lid, l in circuit.layers.items():
                for j, tid in enumerate(bun.target_neuron_ids):
                    if tid in l.neurons and j < len(ta):
                        l.neurons[tid].activation = max(-1.0, min(1.0,
                            l.neurons[tid].activation + ta[j]))
        
        circuit.observe()
        circuit.detect_circulations()
        if prev is not None:
            circuit.compute_xin(prev)
        prev = circuit.layers['encoding'].get_activations()
        circuit.learn()
        circuit.maintain()
        circuit._detect_practice_convergence(getattr(circuit, '_circulation_measure', 0.0))
        
        q = min(k // 250, 3)
        intake_q[q].append(total_recv * 0.01)
    
    # === Collect metrics ===
    # grad_aco_w
    gb = None
    for bun in circuit.inter_layer_bundles:
        if bun.bundle_id.startswith('grad_to_motor'):
            gb = bun; break
    w_aco = 0.0
    if gb:
        w_aco = sum(gb.weights[0][j] for j in range(len(gb.weights[0]))) / len(gb.weights[0])
    
    # Q4/Q1
    q1 = sum(intake_q[0]) / max(len(intake_q[0]), 1)
    q4 = sum(intake_q[3]) / max(len(intake_q[3]), 1)
    q_ratio = q4 / max(q1, 0.0001)
    
    # STDP topology: z_t→sig feedback bundle weights
    fb_topo = {}
    enc = circuit.layers.get("encoding")
    if enc:
        for b in enc.bundles:
            z_dims = ["transition", "drift", "gamma_desync", "xin_residual",
                      "potential_disp", "churn", "magnitude"]
            if any(s in b.source_neuron_ids for s in z_dims):
                for i, sid in enumerate(b.source_neuron_ids):
                    if sid in z_dims:
                        w_sum = sum(b.weights[i]) / max(len(b.weights[i]), 1)
                        fb_topo[sid] = round(w_sum, 4)
    
    # Sediment resting_potential
    sed_rp = {}
    sed = circuit.layers.get("sediment")
    if sed:
        for nid, n in sed.neurons.items():
            if nid.startswith("sed_") and "novel" not in nid and "recur" not in nid:
                sed_rp[nid] = n.resting_potential
    
    # Anomaly
    anom = getattr(circuit, '_noether_anomaly', 0)
    
    return {
        "w_aco": round(w_aco, 4),
        "q_ratio": round(q_ratio, 2),
        "fb_topo": fb_topo,
        "sed_rp": sed_rp,
        "anom": round(anom, 4),
    }


# === Run all experiments ===
conditions = ["none", "no_stdp", "no_gate", "no_sediment", "white_noise", "no_feedback"]
labels = {
    "none": "Baseline",
    "no_stdp": "No STDP",
    "no_gate": "No CPG Gate",
    "no_sediment": "No Sediment",
    "white_noise": "White Noise",
    "no_feedback": "No Motor Feedback",
}

results = {}
for cond in conditions:
    results[cond] = {}
    for seed in SEEDS:
        print(f"Running: {labels[cond]:20s} seed={seed}...", end=" ", flush=True)
        r = run_experiment(seed, cond)
        results[cond][seed] = r
        print(f"w={r['w_aco']:.3f} Q={r['q_ratio']:.1f} anom={r['anom']:.4f}")

# === Summary table ===
print("\n" + "=" * 100)
print(f"{'Condition':22s} | {'w_aco (avg)':>12s} | {'Q4/Q1 (avg)':>12s} | {'Anomaly (avg)':>14s} | {'Conclusion':20s}")
print("-" * 100)
for cond in conditions:
    ws = [results[cond][s]["w_aco"] for s in SEEDS]
    qs = [results[cond][s]["q_ratio"] for s in SEEDS]
    ans = [results[cond][s]["anom"] for s in SEEDS]
    w_avg = sum(ws)/3
    q_avg = sum(qs)/3
    a_avg = sum(ans)/3
    
    if cond == "none":
        base_w, base_q = w_avg, q_avg
        conclusion = "REFERENCE"
    else:
        w_drop = (base_w - w_avg) / max(base_w, 0.001) * 100
        q_drop = (base_q - q_avg) / max(base_q, 0.001) * 100
        if abs(w_drop) < 5 and abs(q_drop) < 10:
            conclusion = "NO EFFECT (decorative)"
        elif w_drop > 20 or q_drop > 30:
            conclusion = "CRITICAL (essential)"
        else:
            conclusion = f"MODERATE (w-{w_drop:.0f}% q-{q_drop:.0f}%)"
    
    print(f"{labels[cond]:22s} | {w_avg:12.4f} | {q_avg:12.2f} | {a_avg:14.4f} | {conclusion:20s}")

# === STDP topology comparison ===
print("\n" + "=" * 100)
print("STDP Feedback Topology (z_t → sig weights, seed=42)")
print("-" * 80)
z_dims = ["transition", "drift", "gamma_desync", "xin_residual", "potential_disp", "churn", "magnitude"]
print(f"{'Dimension':20s}", end="")
for cond in conditions:
    print(f" | {labels[cond]:12s}", end="")
print()
for dim in z_dims:
    print(f"{dim:20s}", end="")
    for cond in conditions:
        v = results[cond][42].get("fb_topo", {}).get(dim, 0.0)
        print(f" | {v:12.4f}", end="")
    print()
