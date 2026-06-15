"""对称位置实验: 隔离 n 的纯效应"""
import os, sys, math
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
    r"Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp\engines"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
    r"Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"))
from engines.practice_engine import PracticeEngine

N_SEEDS = 20
TICKS = 300

def run_with_config(label, positions, decay_exps, amplitudes):
    """Run experiment with custom source config."""
    counts = Counter()
    L_means = {"acoustic": 0, "thermal": 0, "luminous": 0}
    stypes = ["acoustic", "thermal", "luminous"]
    for i in range(N_SEEDS):
        seed = i * 37 + 1
        engine = PracticeEngine(n_particles=30, seed=seed)
        for idx, src in enumerate(engine.sources):
            src.pos = positions[idx]
            src._decay_exp = decay_exps[idx]
            src.amplitude = amplitudes[idx]
        for _ in range(TICKS):
            engine.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
        obs = engine._observer_position()
        levers = {}
        for src in engine.sources:
            _, _, _, r = src.compute_lever(obs)
            levers[src.source_type] = r
            L_means[src.source_type] += r
        counts[min(levers, key=levers.get)] += 1
    for s in L_means:
        L_means[s] /= N_SEEDS
    return counts, L_means

print("=" * 70)
print("  实验 A: 所有源在同一轴, 等距对称 (纯 n 比较)")
print("=" * 70)

# 3 sources all at distance 7.5 but along the SAME axis (x-axis)
# This eliminates CPG directional bias
# Slight offset in y/z to avoid exact overlap
print("\n  Config: all sources on x-axis at x=7.5, offset y={0, 0.01, -0.01}")
print("  n:  acoustic=1, thermal=2, luminous=2")
print("  A:  all = 5.0")

c, m = run_with_config(
    "same_axis",
    positions=[(7.5, 0.0, 0.0), (7.5, 0.01, 0.0), (7.5, -0.01, 0.0)],
    decay_exps=[1, 2, 2],
    amplitudes=[5.0, 5.0, 5.0]
)
print(f"  E[L]: aco={m['acoustic']:.2f} the={m['thermal']:.2f} lum={m['luminous']:.2f}")
print(f"  Closest: {dict(c)}")
if m['acoustic'] > m['thermal'] and m['acoustic'] > m['luminous']:
    print(f"  -> acoustic (n=1) IS farthest! n WORKS when position is controlled! ✅")
else:
    print(f"  -> n effect NOT clear with same-axis placement")

print()
print("=" * 70)
print("  实验 B: 拉丁方设计 — 旋转源位置")
print("=" * 70)
print("  每种模态分别被放在 x, y, z 三个位置")
print("  如果 n 有因果效应, acoustic 在任何位置都应该最远")

rotations = [
    {"label": "aco→x, the→y, lum→z (default)",
     "pos": [(7.5,0,0), (0,7.5,0), (0,0,7.5)]},
    {"label": "aco→y, the→z, lum→x",
     "pos": [(0,7.5,0), (0,0,7.5), (7.5,0,0)]},
    {"label": "aco→z, the→x, lum→y",
     "pos": [(0,0,7.5), (7.5,0,0), (0,7.5,0)]},
]

aco_farthest_count = 0
for rot in rotations:
    c, m = run_with_config(
        rot["label"],
        positions=rot["pos"],
        decay_exps=[1, 2, 2],  # acoustic always n=1
        amplitudes=[5.0, 5.0, 5.0]  # equal amplitudes
    )
    order = sorted(m, key=m.get, reverse=True)
    aco_rank = order.index("acoustic") + 1
    if aco_rank == 1:
        aco_farthest_count += 1
    print(f"\n  {rot['label']}:")
    print(f"    E[L]: aco={m['acoustic']:.2f} the={m['thermal']:.2f} lum={m['luminous']:.2f}")
    print(f"    Order: {' > '.join(order)}  (acoustic rank: #{aco_rank})")

print(f"\n  Summary: acoustic farthest in {aco_farthest_count}/3 rotations")
if aco_farthest_count == 3:
    print(f"  -> CONFIRMED: n=1 makes acoustic farthest regardless of position! ✅")
elif aco_farthest_count >= 2:
    print(f"  -> STRONG: n=1 effect dominant but position has some influence")
else:
    print(f"  -> WEAK: position dominates over n ⚠️")

print()
print("=" * 70)
print("  实验 C: 反转控制 — thermal 获得 n=1, acoustic 获得 n=2")
print("  如果 n 有因果效应, thermal 应该变成最远")
print("=" * 70)

for rot in rotations:
    c, m = run_with_config(
        rot["label"],
        positions=rot["pos"],
        decay_exps=[2, 1, 2],  # SWAP: acoustic=2, thermal=1
        amplitudes=[5.0, 5.0, 5.0]
    )
    order = sorted(m, key=m.get, reverse=True)
    the_rank = order.index("thermal") + 1
    print(f"\n  {rot['label']}:")
    print(f"    E[L]: aco={m['acoustic']:.2f} the={m['thermal']:.2f} lum={m['luminous']:.2f}")
    print(f"    Order: {' > '.join(order)}  (thermal[n=1] rank: #{the_rank})")
