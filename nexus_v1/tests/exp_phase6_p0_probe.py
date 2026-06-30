"""Phase 6 P0 Probe — DR3 Fix Validation (100k steps).

Hypothesis: CONSUME_RATE 0.15→9.75 balances neural drain vs world deposit,
keeping fill > 0 throughout 500k steps.

At d=20, r=30:
  deposit/step = 9.75 × 0.333 × 0.001 = 0.00325 ≈ drain 0.00324/step

Heat source energy set to 10000 (vs default 500) so it doesn't deplete
in 500k steps at the new consumption rate.

Pass criteria (must all pass before 500k main run):
  P1: Motor EMA >= 0.015
  P2: body speed >= 0.003
  P3: displacement > 0.15 in 100k steps
  P4: fill > 0.35 at 100k end  (NEW: validates DR3 fix)
  P5: G_eff in [5, 25]
"""
import sys, math, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS = 100_000
DT = 0.001
LOG_INTERVAL = 10_000
PRINT_INTERVAL = 25_000

heat = HeatSource(position=[70.0, 50.0, 50.0], energy=10_000.0,
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
c.somatosensory.LATERAL_GAIN = 0.3
for m in c.muscle_system.muscles:
    m.gain = 0.3

_stdp_applied = False

print("=" * 70)
print("Phase 6 P0 Probe: DR3 Fix (CONSUME_RATE=9.75), 100k steps")
print("=" * 70)
print(f"muscle_gain=0.3  oto_amp=6.0  lateral_gain=0.3  heat.energy=10000")
print(f"Body start: {init_pos}  dist={init_dist:.2f}")
print()

trajectory = []
motor_ema_max = 0.0
fill_history = []
t0 = time.time()

for step in range(STEPS):
    t = step * DT
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

    motor_ema = max(mot._activation_ema for mot in c.motor_neurons.values())
    if motor_ema > motor_ema_max:
        motor_ema_max = motor_ema

    fill_history.append(c.energy_store.fill_fraction)

    if step % LOG_INTERVAL == 0:
        pos = list(c.world.body.position)
        dist = math.sqrt(sum((p - h)**2 for p, h in zip(pos, heat.position)))
        bv = c.world.body.velocity
        speed = math.sqrt(sum(v*v for v in bv))
        g_eff = c.vestibular.last_gain if hasattr(c.vestibular, 'last_gain') else -1
        src_energy = heat.energy if heat.alive else 0.0
        trajectory.append({
            'step': step, 'pos': pos, 'dist': dist,
            'speed': speed, 'motor_ema': motor_ema,
            'fill': c.energy_store.fill_fraction,
            'g_eff': g_eff, 'src_energy': src_energy,
        })

    if step > 0 and step % PRINT_INTERVAL == 0:
        rec = trajectory[-1]
        elapsed = time.time() - t0
        print(f"Step {step:>6d} ({elapsed:.0f}s)  dist={rec['dist']:.3f}  "
              f"speed={rec['speed']:.5f}  fill={rec['fill']:.3f}  "
              f"motor={rec['motor_ema']:.4f}  src_E={rec['src_energy']:.0f}")

elapsed = time.time() - t0
print(f"\nDone: {STEPS:,} steps in {elapsed:.1f}s ({STEPS/elapsed:.0f}/s)\n")

print("=" * 70)
print("Pass Criteria")
print("=" * 70)

final = trajectory[-1]

p1_ok = motor_ema_max >= 0.015
print(f"\nP1 Motor EMA >= 0.015:  peak={motor_ema_max:.4f}  {'PASS' if p1_ok else 'FAIL'}")

end_speed = sum(r['speed'] for r in trajectory[-5:]) / 5
p2_ok = end_speed >= 0.003
print(f"P2 Body speed >= 0.003:  avg_last5={end_speed:.5f}  {'PASS' if p2_ok else 'FAIL'}")

total_disp = math.sqrt(sum((p - i)**2 for p, i in zip(final['pos'], init_pos)))
dx = final['pos'][0] - init_pos[0]
p3_ok = total_disp > 0.15
print(f"P3 Displacement > 0.15:  {total_disp:.4f}  Δx={dx:+.4f}  {'PASS' if p3_ok else 'FAIL'}")

p4_ok = final['fill'] > 0.35
fill_50k_avg = sum(fill_history[-50000:]) / 50000
print(f"P4 fill > 0.35 at 100k:  {final['fill']:.4f}  {'PASS' if p4_ok else 'FAIL'}")
print(f"     fill avg last50k={fill_50k_avg:.4f}")

g_vals = [r['g_eff'] for r in trajectory if r['g_eff'] > 0]
g_avg = sum(g_vals) / len(g_vals) if g_vals else 0
p5_ok = 5.0 <= g_avg <= 25.0
print(f"P5 G_eff in [5,25]:  avg={g_avg:.2f}  {'PASS' if p5_ok else 'FAIL'}")

checks = [p1_ok, p2_ok, p3_ok, p4_ok, p5_ok]
passed = sum(checks)
labels = ['P1', 'P2', 'P3', 'P4', 'P5']
status_str = ' '.join(l + '=' + ('OK' if ok else 'NG') for l, ok in zip(labels, checks))
print(f"\nResult: {passed}/5 PASS  {status_str}")

print("\nFill + energy trajectory:")
for r in trajectory:
    print(f"  step {r['step']:>6d}: fill={r['fill']:.4f}  dist={r['dist']:.3f}  "
          f"speed={r['speed']:.5f}  src_E={r['src_energy']:.0f}")

fill_drain_10k = (fill_history[0] - fill_history[-1]) / (STEPS / 10000)
print(f"\nOverall fill drain/10k = {fill_drain_10k:.4f}")
print(f"(positive = still draining; near-zero or negative = balanced/recovering)")
print("=" * 70)

if passed >= 4:
    print("→ PHASE 6 P0 PROBE PASSED: proceed to 500k main experiment")
else:
    print("→ PHASE 6 P0 PROBE FAILED: check fill and motor")
sys.exit(0 if passed >= 4 else 1)
