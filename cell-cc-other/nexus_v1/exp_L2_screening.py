"""EXP-L2.08: Biological Screening — Operation Trauma Genesis.

L2:SELECTION — Long-step validation of damage feedback loops.
BIO: Equivalent to one organism's lifetime under selection pressure.
DESIGN: Run ≥100k steps, observe whether avoidance behavior emerges
        from L1 circulation coupling under L2 constraints.
EMERGE: System should develop:
  1. Spatial avoidance (distance from heat sources increases after damage)
  2. Cardiac recovery (vital_amplitude stabilizes after transient damage)
  3. Energy viability (fill_fraction > 0.1, not starving from repair costs)
  4. DA-driven learning (STDP weights shift in response to damage signals)

Monitoring schedule:
  Every 1000 steps: vital signs snapshot
  Every 10000 steps: full diagnostic dump
  Final: behavioral analysis summary

Usage:
  python -m nexus_v1.exp_L2_screening [--steps N] [--seed S]
"""

import sys
import os
import math
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus_v1.circuit.variant_adapter import VariantCircuit


def compute_distance(pos, target_pos):
    """Euclidean distance between two 3D points."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(pos, target_pos)))


def run_screening(total_steps=100_000, seed=42, log_interval=1000,
                  diag_interval=10_000):
    """Run L2.08 biological screening experiment.

    Returns dict of time-series data for analysis.
    """
    print("=" * 70)
    print("EXP-L2.08: Biological Screening — Operation Trauma Genesis")
    print("=" * 70)
    print(f"  Steps: {total_steps:,}")
    print(f"  Log interval: {log_interval}")
    print(f"  Diagnostic interval: {diag_interval}")
    print()

    circuit = VariantCircuit()
    dt = 0.001
    INPUT = {'yaw': 0.3}  # mild vestibular input (organism is moving)

    # ── L2.08 Gauntlet: place organism INSIDE the damage zone ──
    # Thermal math:
    #   T_at(d) = T_eff × (1 - d/radius) = 5.0 × (1 - d/20)
    #   damage_threshold = 3.0 → requires d < 8.0 for damage
    # Starting at d ≈ 5 from the strongest source [70,50,50]:
    # → T_skin ≈ 5.0 × (1 - 5/20) = 3.75 → ABOVE threshold → damage begins
    # BIO equivalent: placing C. elegans directly on heated agar (33°C)
    circuit.world.body.position = [65.0, 50.0, 50.0]  # d=5 from [70,50,50]
    print("  GAUNTLET: organism placed INSIDE damage zone (d=5.0)")

    # ── Thermal pre-equilibration ──
    # DIAGNOSTIC FINDING: SkinPatch tau = C/k = 10/2 = 5s = 5000 steps.
    # T_skin needs ~10k steps to rise from 0.1 to >3.0 (damage threshold).
    # But the organism drifts away in <5k steps from vital oscillator kicks.
    # SOLUTION: Pre-equilibrate skin to local T_env (organism was already
    # in this zone before the experiment clock starts).
    # BIO: organism that wandered into a vent plume — skin already warm.
    # PHYSICS: set T_skin = T_env (instantaneous equilibration, t >> tau).
    body = circuit.world.body
    print("  PRE-EQUILIBRATING skin patches to local T_env...")
    for p in body.skin_patches:
        pos = p.world_position(body)
        T_env = circuit.world.temperature_at(pos)
        p.current_temperature = T_env  # skip transient, start at steady-state
        p._prev_temperature = T_env
        print(f"    {p.patch_id}: T_skin = T_env = {T_env:.3f} "
              f"({'ABOVE' if T_env > p.damage_threshold else 'below'} threshold {p.damage_threshold})")
    print()

    # ── Time series buffers ──
    ts_steps = []
    ts_fill = []
    ts_vital = []
    ts_max_damage = []
    ts_total_damage = []
    ts_deviation = []
    ts_distance_to_nearest = []
    ts_speed = []
    ts_da_mean = []
    ts_reflex_gate = []
    ts_ecm_temps = []

    # ── Behavioral markers ──
    first_damage_step = None
    first_avoidance_step = None    # first time speed increases after damage
    first_cardiac_depression = None
    peak_damage = 0.0
    damage_episodes = 0  # number of times max_damage crosses 0.5

    # ── Baseline capture (step 0) ──
    body = circuit.world.body
    nearest_source = circuit.world.get_nearest_heat_source(body.position)
    if nearest_source:
        initial_distance = compute_distance(body.position, nearest_source.position)
    else:
        initial_distance = float('inf')

    t0 = time.time()
    in_damage_episode = False

    print(f"  Initial position: [{body.position[0]:.1f}, {body.position[1]:.1f}, {body.position[2]:.1f}]")
    if nearest_source:
        print(f"  Nearest heat source: [{nearest_source.position[0]:.1f}, {nearest_source.position[1]:.1f}, {nearest_source.position[2]:.1f}]")
        print(f"  Initial distance: {initial_distance:.1f}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # Main simulation loop
    # ═══════════════════════════════════════════════════════════════
    for step in range(total_steps):
        circuit.step(INPUT, dt)

        # ── Snapshot every log_interval ──
        if step % log_interval == 0:
            # Vital signs
            fill = circuit.energy_store.fill_fraction
            vital_amp = sum(abs(v) for v in circuit.vital_oscillator.outputs)
            speed = body.speed()

            # Damage state
            patch_data = {p.patch_id: p.damage_integral
                          for p in body.skin_patches}
            max_dmg = max(patch_data.values()) if patch_data else 0.0
            total_dmg = sum(patch_data.values())

            # Distance to nearest source
            nearest = circuit.world.get_nearest_heat_source(body.position)
            dist = compute_distance(body.position, nearest.position) if nearest else float('inf')

            # DA concentration
            da_vals = [n.activation for n in circuit.da_neurons.values()]
            da_mean = sum(da_vals) / len(da_vals) if da_vals else 0.0

            # Circulation deviation
            # Access the last computed deviation from MotionState
            deviation = getattr(circuit, '_last_deviation', 0.0)
            # Try to get from the circulation circuit directly
            try:
                deviation = circuit.circulation_proportion._mosfet_deviation.conduct(
                    circuit.circulation_proportion._cap_homeo._voltage
                )
            except Exception:
                pass

            # ECM temperatures
            ecm_t = [
                circuit.ecm_vestibular.temperature,
                circuit.ecm_encoding.temperature,
                circuit.ecm_column.temperature,
            ]

            # Reflex gate
            gate = circuit.spinal_reflex.gate_voltage

            # Record
            ts_steps.append(step)
            ts_fill.append(fill)
            ts_vital.append(vital_amp)
            ts_max_damage.append(max_dmg)
            ts_total_damage.append(total_dmg)
            ts_deviation.append(deviation)
            ts_distance_to_nearest.append(dist)
            ts_speed.append(speed)
            ts_da_mean.append(da_mean)
            ts_reflex_gate.append(gate)
            ts_ecm_temps.append(ecm_t)

            # ── Behavioral marker detection ──
            if max_dmg > 0.01 and first_damage_step is None:
                first_damage_step = step
                print(f"  [!] FIRST DAMAGE at step {step:,}: max_damage={max_dmg:.4f}")

            if max_dmg > peak_damage:
                peak_damage = max_dmg

            # Damage episode tracking
            if max_dmg > 0.5 and not in_damage_episode:
                in_damage_episode = True
                damage_episodes += 1
            elif max_dmg < 0.1:
                in_damage_episode = False

            # Avoidance detection: after damage, does organism move away?
            if (first_damage_step is not None and
                first_avoidance_step is None and
                step > first_damage_step + 5000 and
                dist > initial_distance * 1.2):
                first_avoidance_step = step
                print(f"  [AVOID] AVOIDANCE DETECTED at step {step:,}: "
                      f"distance={dist:.1f} > initial*1.2={initial_distance*1.2:.1f}")

            # Cardiac depression
            if (first_cardiac_depression is None and
                vital_amp < 0.0005 and max_dmg > 0.5):
                first_cardiac_depression = step
                print(f"  [CARDIAC] DEPRESSION at step {step:,}: "
                      f"vital={vital_amp:.6f}, damage={max_dmg:.3f}")

        # ── Full diagnostic every diag_interval ──
        if step % diag_interval == 0:
            elapsed = time.time() - t0
            steps_per_sec = (step + 1) / elapsed if elapsed > 0 else 0

            # Get latest values from last snapshot
            idx = len(ts_steps) - 1
            if idx >= 0:
                print(f"  [{step:>7,}] fill={ts_fill[idx]:.3f} "
                      f"vital={ts_vital[idx]:.5f} "
                      f"dmg={ts_max_damage[idx]:.3f} "
                      f"dist={ts_distance_to_nearest[idx]:.1f} "
                      f"DA={ts_da_mean[idx]:.3f} "
                      f"spd={ts_speed[idx]:.4f} "
                      f"ECM=[{ts_ecm_temps[idx][0]:.2f},{ts_ecm_temps[idx][1]:.2f},{ts_ecm_temps[idx][2]:.2f}] "
                      f"({steps_per_sec:.0f} step/s)")

    elapsed_total = time.time() - t0

    # ═══════════════════════════════════════════════════════════════
    # Final Analysis
    # ═══════════════════════════════════════════════════════════════
    print()
    print("=" * 70)
    print("SCREENING RESULTS")
    print("=" * 70)

    # ── Survival check ──
    final_fill = ts_fill[-1]
    survived = final_fill > 0.05
    print(f"\n  SURVIVAL: {'[OK] YES' if survived else '[XX] NO'} "
          f"(fill_fraction={final_fill:.4f})")

    # ── Vital stability ──
    final_vital = ts_vital[-1]
    vital_healthy = final_vital > 0.0001
    print(f"  VITAL PULSE: {'[OK] ACTIVE' if vital_healthy else '[XX] FLATLINE'} "
          f"(amplitude={final_vital:.6f})")

    # ── Damage history ──
    print(f"  PEAK DAMAGE: {peak_damage:.4f}")
    print(f"  DAMAGE EPISODES (>0.5): {damage_episodes}")
    if first_damage_step is not None:
        print(f"  FIRST DAMAGE: step {first_damage_step:,}")
    else:
        print(f"  FIRST DAMAGE: none (never touched hot zone)")

    # ── Avoidance behavior ──
    if first_avoidance_step is not None:
        print(f"  AVOIDANCE BEHAVIOR: [OK] EMERGED at step {first_avoidance_step:,}")
    else:
        # Check if distance increased at all
        if len(ts_distance_to_nearest) >= 2:
            d_start = ts_distance_to_nearest[0]
            d_end = ts_distance_to_nearest[-1]
            d_max = max(ts_distance_to_nearest)
            print(f"  AVOIDANCE BEHAVIOR: [??] NOT DETECTED")
            print(f"    distance: start={d_start:.1f} → end={d_end:.1f} "
                  f"(max={d_max:.1f})")

    # ── ECM thermal breach ──
    ecm_start = ts_ecm_temps[0] if ts_ecm_temps else [0, 0, 0]
    ecm_end = ts_ecm_temps[-1] if ts_ecm_temps else [0, 0, 0]
    ecm_rise = [ecm_end[i] - ecm_start[i] for i in range(3)]
    print(f"  ECM THERMAL RISE: vest={ecm_rise[0]:+.3f} "
          f"enc={ecm_rise[1]:+.3f} col={ecm_rise[2]:+.3f}")

    # ── DA dynamics ──
    da_start_avg = sum(ts_da_mean[:5]) / max(len(ts_da_mean[:5]), 1)
    da_end_avg = sum(ts_da_mean[-5:]) / max(len(ts_da_mean[-5:]), 1)
    da_max = max(ts_da_mean) if ts_da_mean else 0
    print(f"  DA DYNAMICS: start={da_start_avg:.4f} → end={da_end_avg:.4f} "
          f"(peak={da_max:.4f})")

    # ── Speed profile ──
    speed_start = sum(ts_speed[:5]) / max(len(ts_speed[:5]), 1)
    speed_end = sum(ts_speed[-5:]) / max(len(ts_speed[-5:]), 1)
    speed_max = max(ts_speed) if ts_speed else 0
    print(f"  SPEED: start={speed_start:.5f} → end={speed_end:.5f} "
          f"(peak={speed_max:.5f})")

    # ── Overall screening verdict ──
    print(f"\n  {'='*50}")
    criteria = {
        'Survived': survived,
        'Vital pulse active': vital_healthy,
        'Experienced damage': first_damage_step is not None,
        'Avoidance emerged': first_avoidance_step is not None,
    }
    passed = sum(1 for v in criteria.values() if v)
    total = len(criteria)

    for name, ok in criteria.items():
        print(f"  {'[OK]' if ok else '[XX]'} {name}")

    print(f"\n  SCREENING: {passed}/{total} criteria met")
    if passed == total:
        print(f"  FULL PASS -- L2 parameters are in viable interval!")
    elif survived and vital_healthy:
        print(f"  PARTIAL -- organism viable but behavior not yet emerged")
        print(f"     -> May need longer run or parameter tuning")
    else:
        print(f"  FAIL -- organism not viable under current L2 constraints")
        print(f"     -> L2 pressure too strong, reduce damage consequences")

    print(f"\n  Total time: {elapsed_total:.1f}s "
          f"({total_steps/elapsed_total:.0f} steps/s)")

    # ── Save raw data for post-analysis ──
    result = {
        'total_steps': total_steps,
        'elapsed_s': elapsed_total,
        'criteria': {k: v for k, v in criteria.items()},
        'markers': {
            'first_damage_step': first_damage_step,
            'first_avoidance_step': first_avoidance_step,
            'first_cardiac_depression': first_cardiac_depression,
            'peak_damage': peak_damage,
            'damage_episodes': damage_episodes,
        },
        'final_state': {
            'fill_fraction': final_fill,
            'vital_amplitude': final_vital,
            'max_damage': ts_max_damage[-1] if ts_max_damage else 0,
            'distance': ts_distance_to_nearest[-1] if ts_distance_to_nearest else 0,
            'speed': ts_speed[-1] if ts_speed else 0,
            'da_mean': ts_da_mean[-1] if ts_da_mean else 0,
        },
        'time_series': {
            'steps': ts_steps,
            'fill': ts_fill,
            'vital': ts_vital,
            'max_damage': ts_max_damage,
            'total_damage': ts_total_damage,
            'distance': ts_distance_to_nearest,
            'speed': ts_speed,
            'da_mean': ts_da_mean,
            'ecm_temps': ts_ecm_temps,
        },
    }

    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='L2.08 Biological Screening')
    parser.add_argument('--steps', type=int, default=100_000,
                        help='Number of simulation steps (default: 100000)')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    result = run_screening(total_steps=args.steps, seed=args.seed)

    # Save results
    out_path = os.path.join(os.path.dirname(__file__),
                            'docs', 'exp_L2_screening_result.json')
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  Results saved to: {out_path}")
