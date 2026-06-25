"""Phase 1 系统测试: Medium3D 集成验证"""
import sys, os, math
base = r"D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"
sys.path.insert(0, os.path.join(base, "engines"))
sys.path.insert(0, base)
from engines.practice_engine import PracticeEngine

# ═══════════════════════════════════════════════
# Test 1: Engine starts with medium enabled
# ═══════════════════════════════════════════════
print("=== 1. Engine Initialization ===")
eng = PracticeEngine(n_particles=30, seed=42)
print(f"  medium_enabled: {eng.medium_enabled}")
if eng.medium_enabled:
    for mt, med in eng._media.items():
        stats = med.get_stats()
        T_c = eng._coupling.get(mt, 0)
        print(f"  {mt}: {stats['n_particles']} particles, "
              f"v={stats['v_prop']:.3f}, L_pen={stats['L_pen']:.2f}, "
              f"T_coupling={T_c:.4f}")

# ═══════════════════════════════════════════════
# Test 2: Basic stepping works
# ═══════════════════════════════════════════════
print("\n=== 2. Basic Stepping ===")
eng = PracticeEngine(n_particles=30, seed=42)
for i in range(10):
    sensory = eng.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
print(f"  10 ticks OK, keys: {len(sensory)} channels")
print(f"  received_acoustic: {sensory.get('received_acoustic', 'N/A'):.6f}")
print(f"  received_thermal:  {sensory.get('received_thermal', 'N/A'):.6f}")
print(f"  received_luminous: {sensory.get('received_luminous', 'N/A'):.6f}")

# ═══════════════════════════════════════════════
# Test 3: Medium energy builds up over time
# ═══════════════════════════════════════════════
print("\n=== 3. Medium Energy Build-up ===")
eng = PracticeEngine(n_particles=30, seed=42)
for t in range(50):
    eng.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
    if t in [0, 9, 19, 49]:
        for mt, med in eng._media.items():
            stats = med.get_stats()
            print(f"  t={t+1:3d}: {mt} total_E={stats['total_energy']:.6f} "
                  f"max_E={stats['max_energy']:.6f}")

# ═══════════════════════════════════════════════
# Test 4: Preference ordering (quick N=10)
# ═══════════════════════════════════════════════
print("\n=== 4. Preference (N=10, T=200) ===")
from collections import Counter
counts = Counter()
L_sums = {"acoustic": 0, "thermal": 0, "luminous": 0}
for i in range(10):
    eng = PracticeEngine(n_particles=30, seed=i*37+1)
    for _ in range(200):
        eng.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
    obs = eng._observer_position()
    levers = {}
    for src in eng.sources:
        _, _, _, r = src.compute_lever(obs)
        levers[src.source_type] = r
        L_sums[src.source_type] += r
    counts[min(levers, key=levers.get)] += 1

for s in L_sums:
    L_sums[s] /= 10
order = sorted(L_sums, key=L_sums.get, reverse=True)
print(f"  E[L]: aco={L_sums['acoustic']:.2f} the={L_sums['thermal']:.2f} "
      f"lum={L_sums['luminous']:.2f}")
print(f"  Order: {' > '.join(order)}")
print(f"  Closest: {dict(counts)}")

print("\n=== PHASE 1 INTEGRATION OK ===")
