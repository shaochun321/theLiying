"""Calibrate THERMAL_TRANSDUCTION_GAIN: scan relay activation vs gain at d=20.

KNOWN RESULT (2026-07-02 calibration scan, 3000-step warmup):
  gain=0.1 (default) → relay.vm=0.703V, relay.act=0.165 → relay OPEN at d=20.
  Decision: do NOT increase THERMAL_TRANSDUCTION_GAIN. Default gain=0.1 is sufficient.
  relay.vm≈0.02-0.05 seen in earlier P2 diagnostics was a cold-start artifact
  (measured at t≈200 steps; τ=C×R=2.0×10.0=20,000 steps → only 1% of V_ss reached).

Purpose of this script (historical diagnostic tool):
  - Documents the full gain→relay_act curve across scan range
  - Can be re-run if relay parameters change (v_threshold, C, R, etc.)
  - Confirms relay RC warmup behavior: use ≥1200 steps before measuring

Method:
  - Body FIXED at [60,50,25] (d=20 from S1=[80,50,25])
  - Muscles disabled (gain=0) — no body movement
  - For each gain: 3000 steps warmup + 2000 steps average
  - Measure: thermo.vm, relay.vm, relay.activation, proj.calcium_rate
"""
import sys, math, os

sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

DT = 0.001
WARMUP = 3000   # steps to reach thermal steady state
MEASURE = 2000  # steps to average

GAINS = [0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0]

src1 = HeatSource(position=[80.0, 50.0, 25.0], energy=1_000_000.0,
                  temperature=5.0, radius=30.0)
src1._drift = [0.0, 0.0, 0.0]

print("=" * 80)
print("THERMAL_TRANSDUCTION_GAIN Calibration Scan (body fixed at d=20)")
print("=" * 80)
print(f"  S1={src1.position}  r={src1.radius}  T={src1.temperature}")
print(f"  body=[60,50,25]  d=20  (proximity={1-20/30:.3f})")
print(f"  Warmup: {WARMUP} steps | Measure: {MEASURE} steps | dt={DT}")
print()

hdr = (f"{'gain':>5} | {'thF.vm':>7} {'thF.act':>8} | "
       f"{'rF.vm':>7} {'rF.act':>8} | {'prF.ca':>8} | {'relay_open':>10}")
print(hdr)
print("-" * len(hdr))

results = []

for gain in GAINS:
    body = Body(position=[60.0, 50.0, 25.0])
    world = World(heat_sources=[src1], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world

    # Override gain before any steps
    c.somatosensory.THERMAL_TRANSDUCTION_GAIN = gain

    # Disable all muscles — body stays fixed
    for m in c.muscle_system.muscles:
        m.gain = 0.0

    # Standard vestibular signal (same as Phase 3)
    import math as _m

    # Accumulate measurements over MEASURE window
    acc_thvm = 0.0
    acc_thact = 0.0
    acc_rvm = 0.0
    acc_ract = 0.0
    acc_prca = 0.0
    n_meas = 0

    total_steps = WARMUP + MEASURE
    for step in range(total_steps):
        t = step * DT
        signal = {
            'yaw':   2.0 * _m.sin(1.5 * t),
            'pitch': 1.5 * _m.sin(1.0 * t),
            'roll':  1.0 * _m.sin(0.7 * t),
            'oto_x': 6.0 * _m.sin(2.0 * t),
            'oto_y': 6.0 * _m.sin(2.5 * t + 0.3),
            'oto_z': 6.0 * _m.sin(3.0 * t + 0.7),
        }
        c.step(signal, dt=DT)

        # Force body to stay at d=20 (override physics)
        c.world.body.position = [60.0, 50.0, 25.0]
        c.world.body.velocity = [0.0, 0.0, 0.0]

        if step >= WARMUP:
            soma = c.somatosensory
            th_f = soma.thermoreceptors.get('front')
            r_f  = soma.relays.get('front')
            pr_f = c._soma_proj.get('front') if hasattr(c, '_soma_proj') else None

            if th_f and r_f:
                acc_thvm  += th_f._membrane.voltage
                acc_thact += th_f.activation
                acc_rvm   += r_f._membrane.voltage
                acc_ract  += r_f.activation
                if pr_f:
                    acc_prca += getattr(pr_f, '_cri_voltage', 0.0)
            n_meas += 1

    if n_meas > 0:
        th_vm   = acc_thvm  / n_meas
        th_act  = acc_thact / n_meas
        r_vm    = acc_rvm   / n_meas
        r_act   = acc_ract  / n_meas
        pr_ca   = acc_prca  / n_meas
    else:
        th_vm = th_act = r_vm = r_act = pr_ca = 0.0

    relay_open = r_act > 0.01
    status = "OPEN  ✓" if relay_open else "closed"

    print(f"{gain:>5.1f} | {th_vm:>7.4f} {th_act:>8.5f} | "
          f"{r_vm:>7.4f} {r_act:>8.5f} | {pr_ca:>8.5f} | {status:>10}")

    results.append((gain, th_vm, th_act, r_vm, r_act, pr_ca, relay_open))

print()
print("=" * 80)
print("Summary:")

open_gains = [g for g, *_, ok in results if ok]
if open_gains:
    print(f"  gain_min (relay opens at d=20): {min(open_gains)}")
    print(f"  Recommended: {min(open_gains) * 1.3:.2f} (30% safety margin above threshold)")
else:
    print("  No gain in scan range opens relay at d=20 — extend scan range.")

# Also show relay.vm vs v_threshold=0.3 crossing
print()
print(f"  v_threshold (relay MOSFET): 0.3")
print(f"  Relay.vm crossing 0.3:")
for gain, th_vm, th_act, r_vm, r_act, pr_ca, ok in results:
    if r_vm >= 0.3:
        print(f"    gain={gain}: relay.vm={r_vm:.4f} ✓")
        break
else:
    print("    Not reached in scan range.")
