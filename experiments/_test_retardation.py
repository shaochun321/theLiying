"""验证传播延迟升级"""
import sys, os, math
base = r"D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"
sys.path.insert(0, os.path.join(base, "engines"))
sys.path.insert(0, base)
from engines.practice_engine import PracticeEngine

# 1. Verify propagation speeds
print("=== 传播延迟验证 ===")
eng = PracticeEngine(n_particles=30, seed=42)
for src in eng.sources:
    delay = 7.5 / src._v_prop
    print(f"  {src.source_type}: v={src._v_prop:.1f}  "
          f"delay at r=7.5: {delay:.2f} ticks")

# 2. Verify received_at works with retardation
obs = (0.0, 0.0, 0.0)
for src in eng.sources:
    phi_t0 = src.received_at(obs, 0)
    phi_t1 = src.received_at(obs, 1)
    phi_t10 = src.received_at(obs, 10)
    print(f"  {src.source_type}: Phi(t=0)={phi_t0:.4f} "
          f"Phi(t=1)={phi_t1:.4f} Phi(t=10)={phi_t10:.4f}")

# 3. Run standard test: source effect still works?
print("\n=== 源效应验证 ===")
e1 = PracticeEngine(n_particles=30, seed=42)
e2 = PracticeEngine(n_particles=30, seed=42)
e2.sources = []
for t in range(300):
    e1.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
    e2.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
o1, o2 = e1._observer_position(), e2._observer_position()
diff = math.sqrt(sum((a-b)**2 for a, b in zip(o1, o2)))
print(f"  Diff (with vs without): {diff:.4f}  (should be > 0)")

# 4. Preference ordering still holds?
print("\n=== 偏好排序 ===")
from collections import Counter
counts = Counter()
L_sums = {"acoustic": 0, "thermal": 0, "luminous": 0}
for i in range(20):
    eng = PracticeEngine(n_particles=30, seed=i*37+1)
    for _ in range(250):
        eng.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
    obs_p = eng._observer_position()
    levers = {}
    for src in eng.sources:
        _, _, _, r = src.compute_lever(obs_p)
        levers[src.source_type] = r
        L_sums[src.source_type] += r
    counts[min(levers, key=levers.get)] += 1
for s in L_sums:
    L_sums[s] /= 20
order = sorted(L_sums, key=L_sums.get, reverse=True)
print(f"  E[L]: aco={L_sums['acoustic']:.2f} the={L_sums['thermal']:.2f} lum={L_sums['luminous']:.2f}")
print(f"  Order: {' > '.join(order)}")
print(f"  Closest: {dict(counts)}")

# 5. Retardation effect comparison
print("\n=== 传播延迟的效应 ===")
eng = PracticeEngine(n_particles=30, seed=42)
obs = (0.0, 0.0, 0.0)
t = 5.0
for src in eng.sources:
    # Without delay
    r = 7.5
    phi_instant = src.amplitude / (r ** src._decay_exp) * (1.0 + 0.3 * math.sin(2*math.pi*src.frequency*t))
    phi_retarded = src.received_at(obs, t)
    print(f"  {src.source_type}: instant={phi_instant:.4f} retarded={phi_retarded:.4f} "
          f"diff={abs(phi_instant-phi_retarded):.4f}")
print("\n=== ALL OK ===")
