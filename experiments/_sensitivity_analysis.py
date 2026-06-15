"""降级敏感性分析: 哪些降级回升会破坏论文结论？"""
import os, sys, math
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
    r"Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp\engines"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
    r"Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"))
from engines.practice_engine import PracticeEngine

N_SEEDS = 20
TICKS = 300

def run_experiment(label, modifier_fn):
    """Run N trials with a modification and return stats."""
    counts = Counter()
    L_means = {"acoustic": 0, "thermal": 0, "luminous": 0}
    for i in range(N_SEEDS):
        seed = i * 37 + 1
        engine = PracticeEngine(n_particles=30, seed=seed)
        modifier_fn(engine)
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
    order = sorted(L_means, key=L_means.get, reverse=True)
    return counts, L_means, order

print("=" * 70)
print("  降级敏感性分析: 回升是否破坏结论？")
print("=" * 70)

# Baseline
print("\n--- BASELINE (current system) ---")
c, m, o = run_experiment("baseline", lambda e: None)
baseline_order = o
print(f"  E[L]: aco={m['acoustic']:.1f} the={m['thermal']:.1f} lum={m['luminous']:.1f}")
print(f"  Order: {' > '.join(o)}")
print(f"  Closest: {dict(c)}")

# Test 1: Equal decay exponents (all 1/r^2)
print("\n--- TEST 1: All sources 1/r^2 (remove decay law asymmetry) ---")
def make_all_1r2(engine):
    for src in engine.sources:
        src._decay_exp = 2
c, m, o = run_experiment("all_1r2", make_all_1r2)
print(f"  E[L]: aco={m['acoustic']:.1f} the={m['thermal']:.1f} lum={m['luminous']:.1f}")
print(f"  Order: {' > '.join(o)}")
print(f"  Closest: {dict(c)}")
print(f"  -> Ordering preserved? {'YES' if o == baseline_order else 'NO - ORDER CHANGED!'}")

# Test 2: Equal decay exponents (all 1/r)
print("\n--- TEST 2: All sources 1/r (remove decay law asymmetry) ---")
def make_all_1r(engine):
    for src in engine.sources:
        src._decay_exp = 1
c, m, o = run_experiment("all_1r", make_all_1r)
print(f"  E[L]: aco={m['acoustic']:.1f} the={m['thermal']:.1f} lum={m['luminous']:.1f}")
print(f"  Order: {' > '.join(o)}")
print(f"  Closest: {dict(c)}")

# Test 3: Equal amplitudes + equal decay (pure symmetry)
print("\n--- TEST 3: Equal A=5, equal n=2 (pure symmetry) ---")
def make_symmetric(engine):
    for src in engine.sources:
        src.amplitude = 5.0
        src._decay_exp = 2
c, m, o = run_experiment("symmetric", make_symmetric)
print(f"  E[L]: aco={m['acoustic']:.1f} the={m['thermal']:.1f} lum={m['luminous']:.1f}")
print(f"  Order: {' > '.join(o)}")
print(f"  Closest: {dict(c)}")
print(f"  -> With full symmetry, closest should be ~33% each")

# Test 4: Equal A, equal n, equal leak (remove ALL asymmetry)
print("\n--- TEST 4: A=5, n=2, lambda=0.04 (ALL equal) ---")
def make_fully_symmetric(engine):
    for src in engine.sources:
        src.amplitude = 5.0
        src._decay_exp = 2
    for integ in engine.integrators.values():
        integ.leak_base = 0.04
c, m, o = run_experiment("fully_symmetric", make_fully_symmetric)
print(f"  E[L]: aco={m['acoustic']:.1f} the={m['thermal']:.1f} lum={m['luminous']:.1f}")
print(f"  Order: {' > '.join(o)}")
print(f"  Closest: {dict(c)}")

# Test 5: Add exponential absorption (simulate medium)
print("\n--- TEST 5: Add absorption alpha=0.05 (medium upgrade) ---")
import types
def make_absorbing(engine):
    alpha = 0.05
    for src in engine.sources:
        orig_received = src.received_at
        src_self = src
        def new_received(obs, t, _orig=orig_received, _a=alpha, _s=src_self):
            val = _orig(obs, t)
            _, _, _, r = _s.compute_lever(obs)
            return val * math.exp(-_a * r)
        src.received_at = new_received
c, m, o = run_experiment("absorbing", make_absorbing)
print(f"  E[L]: aco={m['acoustic']:.1f} the={m['thermal']:.1f} lum={m['luminous']:.1f}")
print(f"  Order: {' > '.join(o)}")
print(f"  Closest: {dict(c)}")
print(f"  -> Ordering preserved? {'YES' if o == baseline_order else 'NO - ABSORPTION CHANGES ORDER!'}")

# Test 6: Swap decay laws (acoustic=1/r^2, thermal=1/r)
print("\n--- TEST 6: SWAP decay laws (acoustic=1/r^2, thermal=1/r) ---")
def swap_decay(engine):
    for src in engine.sources:
        if src.source_type == "acoustic":
            src._decay_exp = 2
        elif src.source_type == "thermal":
            src._decay_exp = 1
c, m, o = run_experiment("swap", swap_decay)
print(f"  E[L]: aco={m['acoustic']:.1f} the={m['thermal']:.1f} lum={m['luminous']:.1f}")
print(f"  Order: {' > '.join(o)}")
print(f"  Closest: {dict(c)}")
print(f"  -> If n determines order, thermal should now be farthest")
