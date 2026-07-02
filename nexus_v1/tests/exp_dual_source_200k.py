"""EXP-018: Dual-Source Driving Validation — 200k steps.

Validates the three-phase modification:
  Phase 0: Memristor w_safe clamp + conductance ceiling
  Phase 3: Thermal Col → Motor axis-specific bundles (gain=10.0)
  Phase 1: Hunger reflex gain ×2 + DA modulation

Key metrics:
  1. Δx displacement toward heat source (target: > 1.0, prior baseline: 0.27)
  2. Thermal bundle weight growth (STDP maturation via scaffolding effect)
  3. Reflex drive contribution vs STDP drive contribution
  4. DA concentration dynamics

Setup: same as EXP-015 (single heat source at x=70, body at x=50, Δ=20).
"""
import os, sys, math, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

# ── Setup ──
heat_src = HeatSource(position=[70.0, 50.0, 50.0], energy=500.0,
                      temperature=5.0, radius=30.0)
heat_src._drift = [0.0, 0.0, 0.0]

body = Body(position=[50.0, 50.0, 50.0])
world = World(heat_sources=[heat_src], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

c = VariantCircuit()
c.world = world

STEPS = 200_000
DT = 0.001
REPORT_INTERVAL = 10_000

# ── Identify thermal bundles ──
therm_bundles = [b for b in c.bundles_col_to_motor
                 if 'therm' in b.id and 'cross' not in b.id]
cross_bundle = [b for b in c.bundles_col_to_motor if 'cross' in b.id]

print("=" * 70)
print("EXP-018: Dual-Source Driving Validation — 200k steps")
print("=" * 70)
print(f"Body start:      {body.position}")
print(f"Heat source:     pos={heat_src.position}, T={heat_src.temperature}")
init_dist = math.sqrt(sum((body.position[i]-heat_src.position[i])**2 for i in range(3)))
print(f"Distance:        {init_dist:.1f}")
print(f"Steps:           {STEPS}")
print(f"Thermal bundles: {[b.id for b in therm_bundles]}")
print(f"Phase 0: Memristor safety clamp — ACTIVE")
print(f"Phase 3: Thermal axis-specific bundles (gain=10.0) — ACTIVE")
print(f"Phase 1: Hunger gain=0.6, DA gating — ACTIVE")
print()

# ── Tracking ──
trajectory = []
t_start = time.time()

for step in range(STEPS):
    c.step({}, dt=DT)

    if step % REPORT_INTERVAL == 0 or step == STEPS - 1:
        pos = list(c.world.body.position)
        vel = list(c.world.body.velocity)
        spd = math.sqrt(sum(v*v for v in vel))
        dist = math.sqrt(sum((pos[i]-heat_src.position[i])**2 for i in range(3)))
        da = c.dopamine.concentration
        es = c.energy_store.fill_fraction

        # Thermal bundle weights (avg memristor w per bundle)
        therm_w = {}
        for b in therm_bundles:
            weights = [b._memristors[r][ci].w
                       for r in range(b.n_sources) for ci in range(b.n_targets)]
            therm_w[b.id] = sum(weights) / max(len(weights), 1)

        # Motor EMAs
        mot = {k: round(n._activation_ema, 4) for k, n in c.motor_neurons.items()}

        # Hunger reflex output (check if any drive exists)
        skin_T = {}
        for p in c.world.body.skin_patches:
            skin_T[p.patch_id] = round(p.current_temperature, 4)

        elapsed = time.time() - t_start
        steps_per_sec = (step + 1) / max(elapsed, 0.01)

        trajectory.append({
            'step': step, 'pos': pos, 'dist': dist,
            'speed': spd, 'da': da, 'es': es,
            'therm_w': therm_w, 'motor': mot, 'skin_T': skin_T,
        })

        dx = pos[0] - 50.0  # displacement from start (heat at x=70)
        print(f"[{step:>7d}] x={pos[0]:.3f} Δx={dx:+.3f} dist={dist:.2f} "
              f"spd={spd:.5f} DA={da:.4f} ES={es:.2f} "
              f"| therm_w=" + " ".join(f"{k.split('_to_')[1]}={v:.3f}" for k, v in therm_w.items())
              + f" | {steps_per_sec:.0f} steps/s")

# ── Final Analysis ──
print()
print("=" * 70)
print("FINAL ANALYSIS")
print("=" * 70)

# 1. Displacement
final_pos = trajectory[-1]['pos']
dx_total = final_pos[0] - 50.0
dy_total = final_pos[1] - 50.0
dz_total = final_pos[2] - 50.0
final_dist = trajectory[-1]['dist']
print(f"\n[1] DISPLACEMENT:")
print(f"  Δx = {dx_total:+.4f} (toward heat at x=70)")
print(f"  Δy = {dy_total:+.4f}")
print(f"  Δz = {dz_total:+.4f}")
print(f"  Final dist = {final_dist:.2f} (init: {init_dist:.1f})")
print(f"  Δdist = {final_dist - init_dist:+.2f}")

# 2. Thermal bundle weight evolution
print(f"\n[2] THERMAL BUNDLE WEIGHT EVOLUTION:")
for b in therm_bundles:
    w_init = trajectory[0]['therm_w'].get(b.id, 0)
    w_50k = trajectory[min(5, len(trajectory)-1)]['therm_w'].get(b.id, 0)
    w_100k = trajectory[min(10, len(trajectory)-1)]['therm_w'].get(b.id, 0)
    w_final = trajectory[-1]['therm_w'].get(b.id, 0)
    print(f"  {b.id}:")
    print(f"    0k={w_init:.4f}  50k={w_50k:.4f}  100k={w_100k:.4f}  200k={w_final:.4f}")
    print(f"    Growth: {w_final - w_init:+.4f} ({(w_final/max(w_init,0.001)-1)*100:+.1f}%)")

# 3. DA dynamics
print(f"\n[3] DA CONCENTRATION:")
da_vals = [t['da'] for t in trajectory]
print(f"  Mean: {sum(da_vals)/len(da_vals):.4f}")
print(f"  Range: [{min(da_vals):.4f}, {max(da_vals):.4f}]")

# 4. Speed profile
print(f"\n[4] SPEED PROFILE:")
speeds = [t['speed'] for t in trajectory]
print(f"  Mean: {sum(speeds)/len(speeds):.6f}")
print(f"  Max:  {max(speeds):.6f}")

# 5. Energy store
print(f"\n[5] ENERGY STORE:")
es_vals = [t['es'] for t in trajectory]
print(f"  Mean fill: {sum(es_vals)/len(es_vals):.3f}")
print(f"  Final fill: {es_vals[-1]:.3f}")

# 6. Skin temperature asymmetry (final)
print(f"\n[6] SKIN TEMPERATURE (final):")
final_skin = trajectory[-1]['skin_T']
for pid in ['front', 'back', 'left', 'right']:
    print(f"  {pid}: {final_skin.get(pid, 'N/A')}")
front_T = final_skin.get('front', 0)
back_T = final_skin.get('back', 0)
print(f"  Front-Back diff: {front_T - back_T:+.6f}")

# 7. Distance trajectory
print(f"\n[7] DISTANCE TRAJECTORY:")
for t in trajectory:
    marker = "→" if t['dist'] < init_dist else "←"
    print(f"  step {t['step']:>7d}: dist={t['dist']:.2f} {marker}")

# 8. Verdict
print()
print("=" * 70)
print("VERDICT:")
if dx_total > 5.0:
    print("  ✅✅ STRONG THERMOTAXIS — Δx > 5.0, organism reached heat source")
elif dx_total > 1.0:
    print("  ✅ THERMOTAXIS DETECTED — Δx > 1.0, significant approach")
elif dx_total > 0.3:
    print("  ⚠️ WEAK THERMOTAXIS — Δx > 0.3, marginal improvement over baseline")
elif dx_total > 0.0:
    print("  ⚠️ INCONCLUSIVE — Δx > 0 but < 0.3 (baseline was 0.27)")
else:
    print("  ❌ NO THERMOTAXIS — organism did not approach heat source")

# Compare to baseline
print(f"\n  Baseline (V8 200k): Δx ≈ 0.27")
print(f"  This run (200k):    Δx = {dx_total:+.4f}")
if dx_total > 0.27:
    print(f"  Improvement:        {dx_total/0.27:.1f}× over baseline")
else:
    print(f"  No improvement over baseline")

elapsed_total = time.time() - t_start
print(f"\n  Total time: {elapsed_total:.0f}s ({elapsed_total/60:.1f}min)")
print("=" * 70)

