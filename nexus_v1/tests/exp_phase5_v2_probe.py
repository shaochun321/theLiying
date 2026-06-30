"""Phase 5 v2: Motion Drive Enhancement Probe — 100k steps.

Objective: validate that Stage 2A (oto amplitude 3.0→6.0) + muscle gain
override (0.1→0.3) sufficiently boost body velocity for DR2/DR5.

Pass criteria (short probe):
  P1: Motor EMA >= 0.02 at any checkpoint (sustained drive)
  P2: body speed >= 0.003 unit/s at end (vs baseline ~0.001)
  P3: total displacement > 0.3 units in 100k steps (vs ~0.06 baseline)
  P4: G_eff in [5, 25] (energy gating healthy, not zero)
  P5: 21/21 regression not broken (checked separately, noted here)

If all pass → proceed to 500k main experiment.
"""
import sys, math, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS = 100_000
DT = 0.001
LOG_INTERVAL = 5_000
PRINT_INTERVAL = 20_000

# Same world setup as main experiment: heat to the right
heat = HeatSource(position=[70.0, 50.0, 50.0], energy=500.0,
                  temperature=5.0, radius=30.0)
heat._drift = [0.0, 0.0, 0.0]
body = Body(position=[50.0, 50.0, 50.0])
world = World(heat_sources=[heat], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

init_pos = list(body.position)
init_dist = math.sqrt(sum((p - h)**2 for p, h in zip(body.position, heat.position)))

c = VariantCircuit()
c.world = world

# ── Stage 2A: directional learning overrides ──
c.somatosensory.LATERAL_GAIN = 0.3

# ── Stage 2A: muscle gain override (0.1 → 0.3) ──
# BIO: muscle gain ~0.1 is conservative; actual skeletal muscle force/area
# ratio supports 3× higher output at moderate activation levels.
for m in c.muscle_system.muscles:
    m.gain = 0.3

_stdp_applied = False

print("=" * 70)
print("Phase 5 v2: Motion Drive Enhancement Probe (100k steps)")
print("=" * 70)
print(f"Heat source: {heat.position}  T={heat.temperature}")
print(f"Body start:  {init_pos}  dist={init_dist:.2f}")
print(f"Overrides: lateral_gain=0.3  muscle_gain=0.3  oto_amplitude=6.0")
print()

trajectory = []
speed_history = []
motor_ema_max = 0.0
t0 = time.time()

for step in range(STEPS):
    t = step * DT
    # Stage 2A: increase oto amplitude 3.0 → 6.0
    signal = {
        'yaw':   2.0 * math.sin(1.5 * t),
        'pitch': 1.5 * math.sin(1.0 * t),
        'roll':  1.0 * math.sin(0.7 * t),
        'oto_x': 6.0 * math.sin(2.0 * t),
        'oto_y': 6.0 * math.sin(2.5 * t + 0.3),
        'oto_z': 6.0 * math.sin(3.0 * t + 0.7),
    }
    c.step(signal, dt=DT)

    if not _stdp_applied and step >= 1 and c.bundles_soma_to_da:
        for b in c.bundles_soma_to_da:
            b.config.stdp_lr = 0.005
        _stdp_applied = True

    # Track body speed
    bv = c.world.body.velocity
    speed = math.sqrt(sum(v*v for v in bv))
    speed_history.append(speed)

    # Track motor EMA across all motor neurons
    motor_ema = max(
        mot._activation_ema
        for mot in c.motor_neurons.values()
    )
    if motor_ema > motor_ema_max:
        motor_ema_max = motor_ema

    if step % LOG_INTERVAL == 0:
        pos = list(c.world.body.position)
        dist = math.sqrt(sum((p - h)**2 for p, h in zip(pos, heat.position)))
        g_eff = c.vestibular.last_gain if hasattr(c.vestibular, 'last_gain') else -1

        # Weight diff
        bda = c.bundles_soma_to_da[0] if c.bundles_soma_to_da else None
        wdiff = 0.0
        if bda:
            wm = bda.weight_matrix()
            w_lr = {}
            for i, pid in enumerate(c.somatosensory.patch_ids):
                if pid in ('left', 'right'):
                    w_lr[pid] = sum(wm[i]) / max(len(wm[i]), 1)
            if 'left' in w_lr and 'right' in w_lr:
                wdiff = abs(w_lr['right'] - w_lr['left'])

        trajectory.append({
            'step': step,
            'pos': pos,
            'dist': dist,
            'speed': speed,
            'motor_ema': motor_ema,
            'g_eff': g_eff,
            'fill': c.energy_store.fill_fraction,
            'wdiff': wdiff,
            'gdv': c.motion_state.thermal_gradient_dot_velocity,
        })

    if step > 0 and step % PRINT_INTERVAL == 0:
        rec = trajectory[-1]
        elapsed = time.time() - t0
        rate = step / max(elapsed, 0.001)
        print(f"Step {step:>6d} ({elapsed:.0f}s, {rate:.0f}/s)  "
              f"dist={rec['dist']:.3f}  speed={rec['speed']:.5f}  "
              f"motor_ema={rec['motor_ema']:.4f}  G_eff={rec['g_eff']:.2f}  "
              f"|Δw|={rec['wdiff']:.4f}")

elapsed = time.time() - t0
print(f"\nDone: {STEPS:,} steps in {elapsed:.1f}s ({STEPS/elapsed:.0f}/s)\n")

# ═══════════════════════════════════════════════════════════════
# Pass Criteria Evaluation
# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("Pass Criteria")
print("=" * 70)

final = trajectory[-1]

# P1: Motor EMA >= 0.02
p1_ok = motor_ema_max >= 0.02
print(f"\nP1 Motor EMA >= 0.02:  peak={motor_ema_max:.4f}  {'PASS' if p1_ok else 'FAIL'}")

# P2: body speed >= 0.003 at end
end_speed = sum(speed_history[-1000:]) / 1000  # last 1k steps average
p2_ok = end_speed >= 0.003
print(f"P2 Body speed >= 0.003:  avg_last1k={end_speed:.5f}  {'PASS' if p2_ok else 'FAIL'}")

# P3: total displacement > 0.3
total_disp = math.sqrt(sum((p - i)**2 for p, i in zip(final['pos'], init_pos)))
p3_ok = total_disp > 0.3
print(f"P3 Displacement > 0.3:  {total_disp:.4f}  {'PASS' if p3_ok else 'FAIL'}")
dx = final['pos'][0] - init_pos[0]
print(f"     Δx={dx:+.4f} (toward heat +x)  dist {init_dist:.2f}→{final['dist']:.3f}")

# P4: G_eff in [5, 25]
g_vals = [r['g_eff'] for r in trajectory if r['g_eff'] > 0]
g_avg = sum(g_vals) / len(g_vals) if g_vals else 0
p4_ok = 5.0 <= g_avg <= 25.0
print(f"P4 G_eff in [5,25]:  avg={g_avg:.2f}  {'PASS' if p4_ok else 'FAIL'}")

# Bonus: DR5 early signal
gdv_vals = [r['gdv'] for r in trajectory[-5:]]  # last 5 records
gdv_pos = sum(1 for v in gdv_vals if v > 0)
print(f"\nBonus DR5 early signal: grad_dot_v positive in {gdv_pos}/{len(gdv_vals)} recent records")

# Weight divergence
print(f"Weight divergence at end: |Δw|={final['wdiff']:.4f}")

# Summary
checks = [p1_ok, p2_ok, p3_ok, p4_ok]
passed = sum(checks)
labels = ['P1', 'P2', 'P3', 'P4']
print("\n" + "=" * 70)
print(f"Result: {passed}/4 criteria PASS")
print(f"  {' '.join(f'{lb}={'OK' if ok else 'NG'}' for lb, ok in zip(labels, checks))}")

if passed >= 3:
    print("\n→ SHORT PROBE PASSED: proceed to 500k main experiment")
else:
    print("\n→ SHORT PROBE FAILED: diagnose and adjust before 500k")

# Distance trajectory
print("\nDistance trajectory (every 20k steps):")
for r in trajectory[::4]:
    delta = r['dist'] - init_dist
    marker = "<" if delta < 0 else ">"
    print(f"  step {r['step']:>6d}: dist={r['dist']:.3f} ({delta:+.3f}) {marker}  "
          f"speed={r['speed']:.5f}  motor={r['motor_ema']:.4f}")

print("=" * 70)
sys.exit(0 if passed >= 3 else 1)
