"""论文2数据收集: 连续扫描衰减指数 n ∈ [0.5, 3.0]"""
import os, sys, math, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
    r"Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp\engines"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
    r"Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"))
from engines.practice_engine import PracticeEngine

# Place ONE source at (7.5, 0, 0) with varying n
# Measure E[L] as function of n
# Remove other sources to isolate single-source effect

N_SEEDS = 15
TICKS = 250
N_VALUES = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]

print("=" * 70)
print(f"  论文2: E[L](n) 连续扫描  (N_seeds={N_SEEDS}, T={TICKS})")
print("=" * 70)
print()

results = {}
for n_val in N_VALUES:
    L_list = []
    for i in range(N_SEEDS):
        seed = i * 37 + 1
        engine = PracticeEngine(n_particles=30, seed=seed)
        # Keep only one source, set its n
        engine.sources = [engine.sources[0]]  # keep acoustic
        engine.sources[0]._decay_exp = n_val
        engine.sources[0].amplitude = 5.0

        for _ in range(TICKS):
            engine.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
        obs = engine._observer_position()
        _, _, _, r = engine.sources[0].compute_lever(obs)
        L_list.append(r)

    mean_L = sum(L_list) / len(L_list)
    std_L = (sum((x - mean_L)**2 for x in L_list) / len(L_list)) ** 0.5
    results[n_val] = {"mean": mean_L, "std": std_L, "data": L_list}
    print(f"  n={n_val:.2f}:  E[L]={mean_L:.2f} ± {std_L:.2f}")

# Theoretical prediction: L* ~ (n*A*sqrt(N)/sigma)^(1/(n+1))
# With A=5, N=30, sigma=0.3
A, N, sigma = 5.0, 30, 0.3
print(f"\n  理论预测 L* = (n*A*sqrt(N)/sigma)^(1/(n+1)):")
for n_val in N_VALUES:
    L_pred = (n_val * A * math.sqrt(N) / sigma) ** (1.0 / (n_val + 1))
    print(f"  n={n_val:.2f}:  L*_predicted={L_pred:.2f}  "
          f"E[L]_measured={results[n_val]['mean']:.2f}  "
          f"ratio={results[n_val]['mean']/L_pred:.2f}")

# Save raw data
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper", "data_n_sweep.json")
save_data = {str(k): {"mean": v["mean"], "std": v["std"], "data": v["data"]} for k, v in results.items()}
with open(out_path, 'w') as f:
    json.dump(save_data, f, indent=2)
print(f"\n  Data saved to {out_path}")

# Check: does the curve have a clear functional form?
print(f"\n  n vs E[L] curve shape:")
means = [results[n]["mean"] for n in N_VALUES]
if all(means[i] >= means[i+1] for i in range(len(means)-1)):
    print("  Monotonically DECREASING: higher n → closer approach ✅")
elif all(means[i] <= means[i+1] for i in range(len(means)-1)):
    print("  Monotonically INCREASING: higher n → farther ⚠️")
else:
    print("  Non-monotonic: complex relationship ⚠️")
    peak_idx = means.index(max(means))
    print(f"  Peak at n={N_VALUES[peak_idx]:.2f}, E[L]={max(means):.2f}")
