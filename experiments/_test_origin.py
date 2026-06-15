"""Test origin crystallization"""
import sys, os
base = r"D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"
sys.path.insert(0, os.path.join(base, "engines"))
sys.path.insert(0, base)
from engines.practice_engine import PracticeEngine

for ticks in [100, 200, 300, 500]:
    e = PracticeEngine(n_particles=30, seed=42)
    for t in range(ticks):
        e.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
    st = e.origin.get_state()
    print(f"T={ticks:3d}: conf={st['confidence']:.4f}  "
          f"crystallizable={st['crystallizable']}  age={st['age']}  "
          f"est=({st['x']:.1f},{st['y']:.1f},{st['z']:.1f})")
