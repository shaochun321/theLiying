"""全链路系统测试"""
import sys, os, math
base = r"D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"
sys.path.insert(0, os.path.join(base, "engines"))
sys.path.insert(0, base)
from engines.practice_engine import PracticeEngine
from collections import Counter

# 1. PracticeEngine 基础运行
print("=== 1. PracticeEngine (300 ticks) ===")
engine = PracticeEngine(n_particles=30, seed=42)
for t in range(300):
    s = engine.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
obs = engine._observer_position()
print(f"  Final obs: ({obs[0]:.2f}, {obs[1]:.2f}, {obs[2]:.2f})")
for src in engine.sources:
    _, _, _, r = src.compute_lever(obs)
    print(f"  L_{src.source_type}: {r:.2f} (n={src._decay_exp})")
for name, integ in engine.integrators.items():
    print(f"  I_{name}: {integ.state:.4f}")
print(f"  Origin crystallizable: {engine.origin.is_crystallizable()}")
print(f"  Origin confidence: {engine.origin.confidence:.4f}")
origin_attrs = [a for a in dir(engine.origin) if not a.startswith("_")]
print(f"  Origin public attrs: {origin_attrs}")
print()

# 2. Source Effect
print("=== 2. Source Effect ===")
e1 = PracticeEngine(n_particles=30, seed=42)
e2 = PracticeEngine(n_particles=30, seed=42)
e2.sources = []
for t in range(300):
    e1.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
    e2.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
o1, o2 = e1._observer_position(), e2._observer_position()
diff = math.sqrt(sum((a-b)**2 for a,b in zip(o1, o2)))
print(f"  With sources: ({o1[0]:.2f}, {o1[1]:.2f}, {o1[2]:.2f})")
print(f"  No sources:   ({o2[0]:.2f}, {o2[1]:.2f}, {o2[2]:.2f})")
print(f"  Diff: {diff:.4f}  (>0 = taxis works)")
print()

# 3. Physics system
print("=== 3. Physics System ===")
e3 = PracticeEngine(n_particles=30, seed=42)
for t in range(100):
    e3.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
print(f"  N particles: {len(e3.system.particles)}")
print(f"  KE: {e3.system.total_kinetic:.6f}")
print(f"  PE: {e3.system.total_potential:.6f}")
print()

# 4. N=20 preference test
print("=== 4. Preference Test (N=20) ===")
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
print(f"  Closest: {dict(counts)}")
print(f"  E[L]: aco={L_sums['acoustic']:.2f} the={L_sums['thermal']:.2f} lum={L_sums['luminous']:.2f}")
order = sorted(L_sums, key=L_sums.get, reverse=True)
print(f"  Order: {' > '.join(order)}")
print()

# 5. Gradient magnitude at various distances
print("=== 5. Gradient Field Analysis ===")
print("  Gradient at distance L from each source:")
for L_dist in [3.0, 5.0, 7.0, 10.0]:
    row = f"  L={L_dist:.0f}: "
    for src in eng.sources:
        # Place observer at distance L from the source along its axis
        if src.pos[0] > 0:
            test_pos = (src.pos[0] - L_dist, 0, 0)
        elif src.pos[1] > 0:
            test_pos = (0, src.pos[1] - L_dist, 0)
        else:
            test_pos = (0, 0, src.pos[2] - L_dist)
        gx, gy, gz = src.gradient_at(test_pos)
        mag = math.sqrt(gx**2 + gy**2 + gz**2)
        phi = src.received_at(test_pos, 0)
        row += f"  {src.source_type[:3]}(n={src._decay_exp}): |G|={mag:.3f} Phi={phi:.3f}"
    print(row)
print()

# 6. Sensory dict structure
print("=== 6. Sensory Dict Keys ===")
eng = PracticeEngine(n_particles=30, seed=1)
s = eng.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
print(f"  Keys ({len(s)}): {sorted(s.keys())}")
print()

# 7. run_v40_integrated import test
print("=== 7. Import Test ===")
try:
    from engines.hebbian_circuit import HebbianCircuit
    print(f"  HebbianCircuit: OK")
except Exception as e:
    print(f"  HebbianCircuit: FAIL - {e}")

try:
    from engines.physics_particle_system import ParticleSystem
    print(f"  ParticleSystem: OK")
except Exception as e:
    print(f"  ParticleSystem: FAIL - {e}")
print()

print("=== ALL TESTS COMPLETED ===")
