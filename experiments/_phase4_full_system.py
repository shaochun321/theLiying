"""Phase 4 全系统验证: Medium + HH + Vestibular + Proprioception"""
import sys, os, math, time
base = r"D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"
sys.path.insert(0, os.path.join(base, "engines"))
sys.path.insert(0, base)
from engines.practice_engine import PracticeEngine
from collections import Counter

print("=" * 70)
print("  FULL SYSTEM TEST — All Subsystems")
print("=" * 70)

# ═══════════════════════════════════════════════
# 1. System initialization
# ═══════════════════════════════════════════════
print("\n=== 1. System Initialization ===")
eng = PracticeEngine(n_particles=30, seed=42)
print(f"  medium_enabled:     {eng.medium_enabled}")
print(f"  vestibular_enabled: {eng._vestibular_enabled}")
print(f"  proprio_enabled:    {eng._proprio_enabled}")
print(f"  HH active:          {eng.system._use_hh}")

# ═══════════════════════════════════════════════
# 2. Single tick + channel count
# ═══════════════════════════════════════════════
print("\n=== 2. Single Tick ===")
s = eng.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
s = eng.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})  # 2nd for vestibular init
all_keys = sorted(s.keys())
print(f"  Total sensory channels: {len(all_keys)}")

# Group by prefix
groups = {}
for k in all_keys:
    prefix = k.split('_')[0]
    groups[prefix] = groups.get(prefix, 0) + 1
for g in sorted(groups, key=groups.get, reverse=True):
    print(f"    {g:15s}: {groups[g]} channels")

# ═══════════════════════════════════════════════
# 3. Proprioception check
# ═══════════════════════════════════════════════
print("\n=== 3. Proprioceptive Signals ===")
proprio_keys = [k for k in all_keys if k.startswith('proprio_')]
for k in proprio_keys:
    print(f"    {k}: {s[k]:.4f}")

# ═══════════════════════════════════════════════
# 4. 10-tick stress test
# ═══════════════════════════════════════════════
print("\n=== 4. Stress Test (100 ticks with motor) ===")
eng = PracticeEngine(n_particles=30, seed=42)
t0 = time.time()
for i in range(100):
    motor = {"move_x": math.sin(i*0.1)*0.5,
             "move_y": math.cos(i*0.1)*0.3,
             "move_z": 0.1}
    s = eng.step(motor)
elapsed = time.time() - t0
print(f"  100 ticks in {elapsed:.2f}s ({elapsed/100*1000:.1f}ms/tick)")
print(f"  spindle_Ia: {s.get('proprio_spindle_Ia',0):.4f}")
print(f"  golgi:      {s.get('proprio_golgi_mean',0):.4f}")
print(f"  n_joints:   {s.get('proprio_n_joints',0):.0f}")
print(f"  canal_yaw:  {s.get('vest_canal_yaw',0):.4f}")
print(f"  oto_x:      {s.get('vest_oto_x',0):.4f}")

# ═══════════════════════════════════════════════
# 5. Preference regression
# ═══════════════════════════════════════════════
print("\n=== 5. Preference (N=10, T=200) ===")
L_sums = {"acoustic": 0, "thermal": 0, "luminous": 0}
counts = Counter()
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

# ═══════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════
print("\n" + "=" * 70)
print("  SUBSYSTEM SUMMARY")
print("=" * 70)
print(f"  Medium3D:      {'✅' if eng.medium_enabled else '❌'} (acoustic + thermal lattice)")
print(f"  HH Neurons:    {'✅' if eng.system._use_hh else '❌'} (Na⁺/K⁺ gating + RK4)")
print(f"  Vestibular:    {'✅' if eng._vestibular_enabled else '❌'} (3 canals + 3 otoliths)")
print(f"  Proprioception:{'✅' if eng._proprio_enabled else '❌'} (spindles + Golgi + joints)")
print(f"  Total Channels: {len(all_keys)}")
print("=" * 70)
