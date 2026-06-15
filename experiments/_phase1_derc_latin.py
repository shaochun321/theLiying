"""Phase 1 Step 6: DERC + 拉丁方验证 (Medium3D 激活)"""
import sys, os, math, json, time
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
    r"..\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp\engines"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
    r"..\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"))
from engines.practice_engine import PracticeEngine

N_SEEDS = 20
TICKS = 250

# ═══════════════════════════════════════════════
# Part A: DERC — Phase 0 vs Phase 1
# ═══════════════════════════════════════════════
print("=" * 70)
print(f"  DERC Scan (N={N_SEEDS}, T={TICKS}) — Medium3D ON")
print("=" * 70)

N_VALUES = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
A = 5.0
results_medium = {}
t0 = time.time()

for n_val in N_VALUES:
    L_list = []
    for i in range(N_SEEDS):
        eng = PracticeEngine(n_particles=30, seed=i*37+1)
        # Single source config
        eng.sources = [eng.sources[0]]
        eng.sources[0]._decay_exp = n_val
        eng.sources[0].amplitude = A
        for _ in range(TICKS):
            eng.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
        obs = eng._observer_position()
        _, _, _, r = eng.sources[0].compute_lever(obs)
        L_list.append(r)
    mean_L = sum(L_list) / len(L_list)
    std_L = (sum((x - mean_L)**2 for x in L_list) / len(L_list)) ** 0.5
    L_pred = (n_val * A * math.sqrt(30) / 0.3) ** (1.0 / (n_val + 1))
    ratio = mean_L / L_pred
    results_medium[n_val] = {"mean": mean_L, "std": std_L, "pred": L_pred, "ratio": ratio}
    elapsed = time.time() - t0
    print(f"  n={n_val:.2f}: E[L]={mean_L:.2f}±{std_L:.2f}  "
          f"L*={L_pred:.2f}  ratio={ratio:.3f}  [{elapsed:.0f}s]")

# Save
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "paper", "data_derc_medium.json")
save_data = {str(k): {"mean": v["mean"], "std": v["std"]} for k, v in results_medium.items()}
with open(out_path, 'w') as f:
    json.dump(save_data, f, indent=2)
print(f"\n  Saved to {out_path}")

# ═══════════════════════════════════════════════
# Part B: 拉丁方 (Medium3D ON)
# ═══════════════════════════════════════════════
print()
print("=" * 70)
print(f"  Latin Square (N={N_SEEDS}, T={TICKS}) — Medium3D ON")
print("=" * 70)

positions_list = [
    [(7.5,0,0), (0,7.5,0), (0,0,7.5)],
    [(0,7.5,0), (0,0,7.5), (7.5,0,0)],
    [(0,0,7.5), (7.5,0,0), (0,7.5,0)],
]
pos_labels = ["x,y,z", "y,z,x", "z,x,y"]
n1_rank_all = []

for n_config_label, decay_exps in [("B: aco=1", [1,2,2]), ("C: the=1", [2,1,2])]:
    n1_source = "acoustic" if decay_exps[0]==1 else "thermal"
    print(f"\n  --- {n_config_label} (n=1 → {n1_source}) ---")
    for pi, positions in enumerate(positions_list):
        L_means = {"acoustic": 0, "thermal": 0, "luminous": 0}
        counts = Counter()
        for i in range(N_SEEDS):
            eng = PracticeEngine(n_particles=30, seed=i*37+1)
            for idx, src in enumerate(eng.sources):
                src.pos = positions[idx]
                src._decay_exp = decay_exps[idx]
                src.amplitude = 5.0
            for _ in range(TICKS):
                eng.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
            obs = eng._observer_position()
            levers = {}
            for src in eng.sources:
                _, _, _, r = src.compute_lever(obs)
                levers[src.source_type] = r
                L_means[src.source_type] += r
            counts[min(levers, key=levers.get)] += 1
        for s in L_means:
            L_means[s] /= N_SEEDS
        order = sorted(L_means, key=L_means.get, reverse=True)
        n1_rank = order.index(n1_source) + 1
        n1_rank_all.append(n1_rank)
        print(f"  {pos_labels[pi]}: E[L] aco={L_means['acoustic']:.2f} "
              f"the={L_means['thermal']:.2f} lum={L_means['luminous']:.2f}  "
              f"  n=1 rank: #{n1_rank}  closest: {dict(counts)}")

print(f"\n  n=1 ranks across all 6 conditions: {n1_rank_all}")
print(f"  All rank #1? {'YES' if all(r==1 for r in n1_rank_all) else 'NO'}")
