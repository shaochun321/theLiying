"""EXP-L2.09: Parameter Sweep — The Boundaries of Death.

Three torture tests, each sweeping one L2 parameter to find the
exact point where the organism transitions from survival to death.

Test 1: The Flinch Test (REFLEX_GAIN)
    Sweep REFLEX_GAIN downward from 0.5 (baseline) toward 0.
    Hypothesis: below some threshold, the spinal reflex cannot overcome
    viscous friction, and the organism burns to death in place.

Test 2: The Hemorrhage Test (REPAIR_ENERGY_RATE)
    Sweep REPAIR_ENERGY_RATE upward from 0.005 (baseline) × 10-50x.
    Hypothesis: metabolic repair cost drains energy faster than feeding
    can replenish → organism escapes fire but dies of ATP exhaustion.

Test 3: The Fever Test (K_BARRIER)
    Sweep K_BARRIER downward from 2.0 (baseline) toward 0.
    Hypothesis: low K_BARRIER → massive ECM heat breach → febrile seizure
    → synaptic chaos → permanent cognitive damage / oscillatory collapse.

Usage:
  python -m nexus_v1.exp_L2_09_sweep [--test flinch|hemorrhage|fever|all]
                                     [--steps N] [--trials N]
"""

import sys
import os
import math
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.spinal_reflex import SpinalReflexConfig


# ═══════════════════════════════════════════════════════════════════════
# Core trial runner
# ═══════════════════════════════════════════════════════════════════════

def run_trial(reflex_gain=0.5, repair_rate=0.005, k_barrier=2.0,
              breach_conductance=0.1, vital_damage_k=0.5,
              total_steps=50_000, dt=0.001, label="trial"):
    """Run a single gauntlet trial with specified L2 parameters.

    Returns dict with outcome metrics. Lightweight — no time series,
    only final state and behavioral markers.
    """
    # Build circuit with specified parameters
    config = SpinalReflexConfig(reflex_gain=reflex_gain)
    circuit = VariantCircuit()
    circuit.spinal_reflex = __import__(
        'nexus_v1.components.spinal_reflex', fromlist=['SpinalReflexArc']
    ).SpinalReflexArc(config)
    circuit.vital_damage_k = vital_damage_k
    circuit.repair_energy_rate = repair_rate
    circuit.k_barrier = k_barrier
    circuit.breach_conductance = breach_conductance

    # Gauntlet: place organism at d=5 from strongest heat source
    circuit.world.body.position = [65.0, 50.0, 50.0]

    # Thermal pre-equilibration
    body = circuit.world.body
    for p in body.skin_patches:
        pos = p.world_position(body)
        T_env = circuit.world.temperature_at(pos)
        p.current_temperature = T_env
        p._prev_temperature = T_env

    INPUT = {'yaw': 0.3}

    # ── Tracking ──
    first_damage_step = None
    first_avoidance_step = None
    peak_damage = 0.0
    peak_ecm_enc = 0.0
    min_fill = 1.0
    min_vital = 1.0
    initial_distance = 5.0
    death_step = None          # step where fill < 0.05 or vital < 0.0001
    death_cause = None

    # ── Sampling (every 1000 steps for efficiency) ──
    sample_fill = []
    sample_damage = []
    sample_distance = []
    sample_ecm_enc = []
    sample_speed = []

    t0 = time.time()

    for step in range(total_steps):
        circuit.step(INPUT, dt)

        if step % 1000 == 0:
            fill = circuit.energy_store.fill_fraction
            vital_amp = sum(abs(v) for v in circuit.vital_oscillator.outputs)
            patch_data = {p.patch_id: p.damage_integral for p in body.skin_patches}
            max_dmg = max(patch_data.values()) if patch_data else 0.0
            total_dmg = sum(patch_data.values())

            nearest = circuit.world.get_nearest_heat_source(body.position)
            dist = math.sqrt(sum((a - b) ** 2
                for a, b in zip(body.position, nearest.position))) if nearest else 999.0

            ecm_enc = circuit.ecm_encoding.temperature

            # Track extremes
            if max_dmg > 0.01 and first_damage_step is None:
                first_damage_step = step
            if (first_damage_step is not None and first_avoidance_step is None
                    and step > first_damage_step + 3000
                    and dist > initial_distance * 1.5):
                first_avoidance_step = step

            peak_damage = max(peak_damage, max_dmg)
            peak_ecm_enc = max(peak_ecm_enc, ecm_enc)
            min_fill = min(min_fill, fill)
            min_vital = min(min_vital, vital_amp)

            # Death detection
            if death_step is None:
                if fill < 0.05:
                    death_step = step
                    death_cause = "METABOLIC_EXHAUSTION"
                elif vital_amp < 0.00001 and step > 5000:
                    death_step = step
                    death_cause = "CARDIAC_ARREST"

            sample_fill.append(fill)
            sample_damage.append(max_dmg)
            sample_distance.append(dist)
            sample_ecm_enc.append(ecm_enc)
            sample_speed.append(body.speed())

    elapsed = time.time() - t0

    # Final state
    final_fill = circuit.energy_store.fill_fraction
    final_vital = sum(abs(v) for v in circuit.vital_oscillator.outputs)
    final_speed = body.speed()
    nearest = circuit.world.get_nearest_heat_source(body.position)
    final_dist = math.sqrt(sum((a - b) ** 2
        for a, b in zip(body.position, nearest.position))) if nearest else 999.0

    # DA state
    da_vals = [n.activation for n in circuit.da_neurons.values()]
    final_da = sum(da_vals) / len(da_vals) if da_vals else 0.0

    # ECM final
    ecm_final = [
        circuit.ecm_vestibular.temperature,
        circuit.ecm_encoding.temperature,
        circuit.ecm_column.temperature,
    ]

    survived = final_fill > 0.05 and final_vital > 0.0001
    avoided = first_avoidance_step is not None

    return {
        'label': label,
        'params': {
            'reflex_gain': reflex_gain,
            'repair_rate': repair_rate,
            'k_barrier': k_barrier,
            'vital_damage_k': vital_damage_k,
            'breach_conductance': breach_conductance,
        },
        'outcome': {
            'survived': survived,
            'avoided': avoided,
            'death_step': death_step,
            'death_cause': death_cause,
        },
        'markers': {
            'first_damage_step': first_damage_step,
            'first_avoidance_step': first_avoidance_step,
            'peak_damage': round(peak_damage, 4),
            'peak_ecm_enc': round(peak_ecm_enc, 4),
            'min_fill': round(min_fill, 4),
            'min_vital': round(min_vital, 6),
        },
        'final': {
            'fill': round(final_fill, 4),
            'vital': round(final_vital, 6),
            'speed': round(final_speed, 5),
            'distance': round(final_dist, 1),
            'da': round(final_da, 4),
            'ecm': [round(t, 4) for t in ecm_final],
        },
        'elapsed_s': round(elapsed, 1),
    }


# ═══════════════════════════════════════════════════════════════════════
# Test 1: The Flinch Test
# ═══════════════════════════════════════════════════════════════════════

def run_flinch_test(steps=50_000):
    """Sweep REFLEX_GAIN downward to find the escape threshold."""
    print("=" * 70)
    print("TEST 1: THE FLINCH TEST — Reflex Gain Sweep")
    print("=" * 70)
    print("  Question: Below what reflex gain does the organism burn to death?")
    print()

    # Sweep values: from baseline (0.5) down to near-zero
    gains = [0.5, 0.3, 0.2, 0.1, 0.05, 0.02, 0.01, 0.005, 0.0]
    results = []

    for g in gains:
        label = f"reflex={g:.3f}"
        print(f"  ► {label} ... ", end="", flush=True)
        r = run_trial(reflex_gain=g, total_steps=steps, label=label)
        status = "ALIVE" if r['outcome']['survived'] else f"DEAD ({r['outcome']['death_cause']})"
        avoided = "ESCAPED" if r['outcome']['avoided'] else "TRAPPED"
        print(f"{status:30s} {avoided:10s}  fill={r['final']['fill']:.3f}  "
              f"dmg={r['markers']['peak_damage']:.2f}  dist={r['final']['distance']:.0f}  "
              f"({r['elapsed_s']:.0f}s)")
        results.append(r)

    return results


# ═══════════════════════════════════════════════════════════════════════
# Test 2: The Hemorrhage Test
# ═══════════════════════════════════════════════════════════════════════

def run_hemorrhage_test(steps=50_000):
    """Sweep REPAIR_ENERGY_RATE upward to find metabolic death threshold."""
    print("=" * 70)
    print("TEST 2: THE HEMORRHAGE TEST — Metabolic Repair Tax Sweep")
    print("=" * 70)
    print("  Question: At what repair rate does post-escape ATP exhaustion kill?")
    print()

    # Sweep: baseline × 1, 5, 10, 20, 50, 100, 200
    multipliers = [1, 5, 10, 20, 50, 100, 200]
    baseline = 0.005
    results = []

    for m in multipliers:
        rate = baseline * m
        label = f"repair={rate:.4f} ({m}x)"
        print(f"  ► {label:30s} ... ", end="", flush=True)
        r = run_trial(repair_rate=rate, total_steps=steps, label=label)
        status = "ALIVE" if r['outcome']['survived'] else f"DEAD ({r['outcome']['death_cause']})"
        print(f"{status:30s}  fill={r['final']['fill']:.3f}  "
              f"dmg={r['markers']['peak_damage']:.2f}  min_fill={r['markers']['min_fill']:.3f}  "
              f"({r['elapsed_s']:.0f}s)")
        results.append(r)

    return results


# ═══════════════════════════════════════════════════════════════════════
# Test 3: The Fever Test
# ═══════════════════════════════════════════════════════════════════════

def run_fever_test(steps=50_000):
    """Sweep K_BARRIER downward + BREACH_CONDUCTANCE upward for brain fire."""
    print("=" * 70)
    print("TEST 3: THE FEVER TEST — ECM Thermal Barrier Sweep")
    print("=" * 70)
    print("  Question: At what barrier level does febrile seizure destroy cognition?")
    print()

    # Sweep K_BARRIER down (lower = more heat breach) with increasing breach conductance
    configs = [
        # (k_barrier, breach_conductance, label)
        (2.0,   0.1,  "baseline K=2.0 B=0.1"),
        (1.0,   0.1,  "K=1.0 B=0.1"),
        (0.5,   0.1,  "K=0.5 B=0.1"),
        (0.2,   0.1,  "K=0.2 B=0.1"),
        (0.1,   0.1,  "K=0.1 B=0.1"),
        (0.5,   0.5,  "K=0.5 B=0.5"),
        (0.2,   0.5,  "K=0.2 B=0.5"),
        (0.1,   0.5,  "K=0.1 B=0.5"),
        (0.1,   1.0,  "K=0.1 B=1.0"),
        (0.05,  1.0,  "K=0.05 B=1.0"),
    ]
    results = []

    for kb, bc, label in configs:
        label_full = f"{label:25s}"
        print(f"  ► {label_full} ... ", end="", flush=True)
        r = run_trial(k_barrier=kb, breach_conductance=bc,
                      total_steps=steps, label=label)
        status = "ALIVE" if r['outcome']['survived'] else f"DEAD ({r['outcome']['death_cause']})"
        ecm = r['final']['ecm']
        print(f"{status:30s}  ECM=[{ecm[0]:.2f},{ecm[1]:.2f},{ecm[2]:.2f}]  "
              f"peak_ecm={r['markers']['peak_ecm_enc']:.2f}  "
              f"dmg={r['markers']['peak_damage']:.2f}  ({r['elapsed_s']:.0f}s)")
        results.append(r)

    return results


# ═══════════════════════════════════════════════════════════════════════
# Summary report
# ═══════════════════════════════════════════════════════════════════════

def print_summary(test_name, results):
    """Print a condensed death boundary summary."""
    print()
    print(f"  {'─'*60}")
    print(f"  {test_name} — DEATH BOUNDARY SUMMARY")
    print(f"  {'─'*60}")

    alive_results = [r for r in results if r['outcome']['survived']]
    dead_results = [r for r in results if not r['outcome']['survived']]

    if alive_results and dead_results:
        # Find the boundary
        last_alive = alive_results[-1]
        first_dead = dead_results[0]
        print(f"  LAST ALIVE: {last_alive['label']}")
        print(f"    fill={last_alive['final']['fill']:.4f}  "
              f"vital={last_alive['final']['vital']:.6f}")
        print(f"  FIRST DEAD: {first_dead['label']}")
        print(f"    death_cause={first_dead['outcome']['death_cause']}  "
              f"death_step={first_dead['outcome']['death_step']}")
        print(f"  ⟶ PHASE BOUNDARY between these two parameter values")
    elif not dead_results:
        print(f"  ALL SURVIVED — no death boundary found in tested range")
        weakest = min(alive_results, key=lambda r: r['final']['fill'])
        print(f"  WEAKEST: {weakest['label']} (fill={weakest['final']['fill']:.4f})")
    else:
        print(f"  ALL DIED — organism cannot survive any tested value")
        strongest = max(dead_results, key=lambda r: r['outcome'].get('death_step', 0) or 0)
        print(f"  LONGEST SURVIVOR: {strongest['label']} "
              f"(died at step {strongest['outcome']['death_step']})")
    print()


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='L2.09: Parameter Sweep — The Boundaries of Death')
    parser.add_argument('--test', choices=['flinch', 'hemorrhage', 'fever', 'all'],
                        default='all', help='Which test to run')
    parser.add_argument('--steps', type=int, default=50_000,
                        help='Steps per trial (default: 50000)')
    args = parser.parse_args()

    all_results = {}
    t_total = time.time()

    if args.test in ('flinch', 'all'):
        print()
        results = run_flinch_test(steps=args.steps)
        print_summary("FLINCH TEST (REFLEX_GAIN)", results)
        all_results['flinch'] = results

    if args.test in ('hemorrhage', 'all'):
        print()
        results = run_hemorrhage_test(steps=args.steps)
        print_summary("HEMORRHAGE TEST (REPAIR_RATE)", results)
        all_results['hemorrhage'] = results

    if args.test in ('fever', 'all'):
        print()
        results = run_fever_test(steps=args.steps)
        print_summary("FEVER TEST (K_BARRIER)", results)
        all_results['fever'] = results

    # ── Final report ──
    total_time = time.time() - t_total
    total_trials = sum(len(v) for v in all_results.values())
    print("=" * 70)
    print(f"L2.09 COMPLETE: {total_trials} trials in {total_time:.0f}s "
          f"({total_time/60:.1f} min)")
    print("=" * 70)

    # Save all results
    out_path = os.path.join(os.path.dirname(__file__),
                            'docs', 'exp_L2_09_sweep_result.json')
    with open(out_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"  Results saved to: {out_path}")
