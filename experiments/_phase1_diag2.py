"""诊断: DERC 中 n 的信息是否丢失"""
import sys, os, math
base = r"D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"
sys.path.insert(0, os.path.join(base, "engines"))
sys.path.insert(0, base)
from engines.practice_engine import PracticeEngine

# 对比: medium ON vs OFF, n=1 vs n=3
for n_val in [1.0, 3.0]:
    for med_on in [True, False]:
        eng = PracticeEngine(n_particles=30, seed=42)
        eng.medium_enabled = med_on
        eng.sources = [eng.sources[0]]
        eng.sources[0]._decay_exp = n_val
        eng.sources[0].amplitude = 5.0
        for _ in range(200):
            eng.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
        obs = eng._observer_position()
        _, _, _, r = eng.sources[0].compute_lever(obs)
        
        # Check what the agent actually "senses"
        if med_on and "acoustic" in eng._media:
            e_med = eng._media["acoustic"].read_at(obs)
            g_med = eng._media["acoustic"].read_gradient_at(obs)
            g_mag = math.sqrt(sum(x*x for x in g_med))
        else:
            e_med = eng.sources[0].received_at(obs, 200*20*0.1)
            gx,gy,gz = eng.sources[0].gradient_at(obs)
            g_mag = math.sqrt(gx*gx+gy*gy+gz*gz)
            
        label = "MED ON " if med_on else "MED OFF"
        print(f"  n={n_val:.1f} {label}: L={r:.2f}  sensed_E={e_med:.6f}  |∇|={g_mag:.6f}")

print("\n  Problem: with medium ON, the agent senses medium energy")
print("  which does NOT depend on n. The n only affects analytic 1/r^n.")
print("  Solution: medium stiffness should scale with n.")
