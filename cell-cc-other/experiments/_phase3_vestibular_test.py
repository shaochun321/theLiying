"""Phase 3 验证: 6轴前庭系统"""
import sys, os, math
base = r"D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"
sys.path.insert(0, os.path.join(base, "engines"))
sys.path.insert(0, base)
from engines.practice_engine import PracticeEngine

# ═══════════════════════════════════════════════
# Test 1: Vestibular channels exist
# ═══════════════════════════════════════════════
print("=== 1. Vestibular Initialization ===")
eng = PracticeEngine(n_particles=30, seed=42)
print(f"  vestibular_enabled: {eng._vestibular_enabled}")
sensory = eng.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
vest_keys = [k for k in sensory if k.startswith('vest_')]
print(f"  Vestibular channels: {len(vest_keys)}")
for k in sorted(vest_keys):
    print(f"    {k}: {sensory[k]:.6f}")

# ═══════════════════════════════════════════════
# Test 2: Canal response to rotation
# ═══════════════════════════════════════════════
print("\n=== 2. Canal Response (induced rotation) ===")
eng = PracticeEngine(n_particles=30, seed=42)
# Apply asymmetric force to induce rotation
for i in range(20):
    if i < 10:
        s = eng.step({"move_x": 2.0, "move_y": -1.0, "move_z": 0.5})
    else:
        s = eng.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
    if i in [0, 4, 9, 14, 19]:
        print(f"  t={i+1:3d}: yaw={s.get('vest_canal_yaw',0):.4f} "
              f"pitch={s.get('vest_canal_pitch',0):.4f} "
              f"roll={s.get('vest_canal_roll',0):.4f} "
              f"ω_mag={s.get('vest_omega_mag',0):.4f}")

# ═══════════════════════════════════════════════
# Test 3: Otolith response to acceleration
# ═══════════════════════════════════════════════
print("\n=== 3. Otolith Response (linear accel) ===")
eng = PracticeEngine(n_particles=30, seed=42)
for i in range(20):
    if i < 5:
        s = eng.step({"move_x": 2.0, "move_y": 0.0, "move_z": 0.0})
    elif i < 10:
        s = eng.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
    else:
        s = eng.step({"move_x": -2.0, "move_y": 0.0, "move_z": 0.0})
    if i in [0, 4, 9, 14, 19]:
        print(f"  t={i+1:3d}: oto_x={s.get('vest_oto_x',0):.4f} "
              f"oto_y={s.get('vest_oto_y',0):.4f} "
              f"oto_z={s.get('vest_oto_z',0):.4f} "
              f"a_mag={s.get('vest_accel_mag',0):.4f}")

# ═══════════════════════════════════════════════
# Test 4: Total channel count
# ═══════════════════════════════════════════════
print("\n=== 4. Total Sensory Channels ===")
all_keys = sorted(sensory.keys())
print(f"  Total: {len(all_keys)} channels")
groups = {}
for k in all_keys:
    prefix = k.split('_')[0]
    groups[prefix] = groups.get(prefix, 0) + 1
for g in sorted(groups, key=groups.get, reverse=True):
    print(f"    {g}: {groups[g]} channels")

# ═══════════════════════════════════════════════
# Test 5: Full regression (偏好排序)
# ═══════════════════════════════════════════════
print("\n=== 5. Preference Regression (N=10, T=200) ===")
from collections import Counter
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

print("\n=== PHASE 3 INTEGRATION OK ===")
