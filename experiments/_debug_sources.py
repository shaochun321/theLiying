"""紧急调查: 为什么修改源参数没有效果？"""
import os, sys, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
    r"Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp\engines"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
    r"Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"))
from engines.practice_engine import PracticeEngine

# Hypothesis: the modifier is not taking effect because
# PracticeEngine uses something else to determine behavior

engine = PracticeEngine(n_particles=30, seed=1)

# Check: what are the source positions?
print("Source positions:")
for src in engine.sources:
    print(f"  {src.source_type}: pos={src.pos}, A={src.amplitude}, n={src._decay_exp}")

# Check: where does the observer start?
obs = engine._observer_position()
print(f"\nInitial observer: ({obs[0]:.2f}, {obs[1]:.2f}, {obs[2]:.2f})")

# Check distances
for src in engine.sources:
    _, _, _, r = src.compute_lever(obs)
    print(f"  Distance to {src.source_type}: {r:.2f}")

# KEY TEST: does the source even MATTER?
# Remove ALL sources and run
print("\n--- No sources test ---")
engine2 = PracticeEngine(n_particles=30, seed=1)
engine2.sources = []  # remove all sources
for k in range(300):
    try:
        engine2.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
    except Exception as e:
        print(f"  Error at tick {k}: {e}")
        break
obs2 = engine2._observer_position()
print(f"  Final position (no sources): ({obs2[0]:.2f}, {obs2[1]:.2f}, {obs2[2]:.2f})")

# Compare with normal run
engine3 = PracticeEngine(n_particles=30, seed=1)
for k in range(300):
    engine3.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
obs3 = engine3._observer_position()
print(f"  Final position (with sources): ({obs3[0]:.2f}, {obs3[1]:.2f}, {obs3[2]:.2f})")

# Are they the same?
diff = math.sqrt(sum((a-b)**2 for a,b in zip(obs2, obs3)))
print(f"  Position difference: {diff:.4f}")
if diff < 0.01:
    print(f"  -> SOURCES HAVE NO EFFECT ON TRAJECTORY!")
    print(f"  -> The 'preference' is entirely from particle initial positions + CPG!")
else:
    print(f"  -> Sources do affect trajectory (diff={diff:.2f})")

# What determines the observer position? It's the mean of particles.
# Particles are initialized by the physics system with seed.
# The SEED determines the initial particle positions!
print(f"\nParticle positions at t=0:")
for i, p in enumerate(engine.physics.particles[:5]):
    print(f"  p[{i}]: ({p.x:.2f}, {p.y:.2f}, {p.z:.2f})")
