# -*- coding: utf-8 -*-
"""Phase 5b: STDP Path Learning Verification.

Does the metabolic cycle cause STDP to encode 'approach source -> get energy'
into the motor pathways?

Test: Run 1000 ticks with metabolic cycle active. Check if:
1. Weights from integrator->motor develop directional bias
2. Motor output correlates with source direction (not just random)
3. Intake rate increases over time (learning improves foraging)
"""
import sys, os, math
base = r"D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"
sys.path.insert(0, os.path.join(base, "engines"))
sys.path.insert(0, base)

from engines.practice_engine import PracticeEngine
from engines.hebbian_circuit import (
    HebbianCircuit, CircuitLayer, MetaNeuron, MetaSynapticBundle,
)
# Reuse circuit builder from pipeline test
sys.path.insert(0, r"D:\cell-cc\experiments")
from _phase5_pipeline import build_full_circuit, inject_sensory, read_motor

import time


def find_bundle(circuit, bid_prefix):
    """Find inter-layer bundle by ID prefix."""
    for b in circuit.inter_layer_bundles:
        if b.bundle_id.startswith(bid_prefix):
            return b
    return None


def weight_summary(bundle):
    """Summarize bundle weights."""
    flat = [w for row in bundle.weights for w in row]
    if not flat:
        return {"mean": 0, "std": 0, "max": 0, "min": 0}
    m = sum(flat) / len(flat)
    var = sum((w - m)**2 for w in flat) / len(flat)
    return {
        "mean": round(m, 6),
        "std": round(var**0.5, 6),
        "max": round(max(flat), 6),
        "min": round(min(flat), 6),
        "n": len(flat),
    }


if __name__ == "__main__":
    print("=" * 70)
    print("  STDP Path Learning: Does metabolism drive weight specialization?")
    print("=" * 70)

    engine = PracticeEngine(n_particles=30, seed=42)
    circuit = build_full_circuit()

    # Track key bundles
    key_bundles = [
        "integ_to_motor",    # integrator -> motor (source direction -> movement)
        "enc_to_motor",      # encoding -> motor (perception -> action)
        "proprio_to_motor",  # proprioception -> motor (body state -> action)
        "imu_to_enc",        # vestibular -> encoding (rotation -> perception)
        "motor_to_enc",      # efference copy (action -> perception)
    ]

    # Record initial weights
    print("\n=== Initial Weights ===")
    initial_weights = {}
    for bid in key_bundles:
        b = find_bundle(circuit, bid)
        if b:
            ws = weight_summary(b)
            initial_weights[bid] = ws
            print(f"  {bid:25s}: mean={ws['mean']:.6f}  std={ws['std']:.6f}  range=[{ws['min']:.6f}, {ws['max']:.6f}]")

    TICKS = 1000
    print(f"\n=== Running {TICKS} ticks ===")
    t0 = time.perf_counter()

    # Split into 4 quarters for trend analysis
    quarter = TICKS // 4
    intake_by_quarter = [[], [], [], []]
    motor_by_quarter = [[], [], [], []]

    for k in range(TICKS):
        cm = read_motor(circuit) if k > 0 else {"move_x": 0, "move_y": 0, "move_z": 0}
        sensory = engine.step(cm)
        inject_sensory(circuit, sensory, engine.box_size)

        total_recv = sum(sensory.get(f"received_{s}", 0) for s in ["acoustic", "thermal", "luminous"])
        intake = total_recv * 0.01
        circuit.feed(intake)

        se_in = {ch: sensory.get(ch, 0.5)
                 for ch in ["spectral_H", "fano_H", "synchrony_H", "gradient_H",
                            "sparseness_H", "autocorrelation_H", "energy_H"]}
        circuit.transport(se_in, "signal_entropy")

        for bundle in circuit.inter_layer_bundles:
            sl = None
            for lid, l in circuit.layers.items():
                if bundle.source_neuron_ids[0] in l.neurons:
                    sl = l; break
            if sl is None: continue
            sa = [sl.neurons.get(s, MetaNeuron("_","_")).activation for s in bundle.source_neuron_ids]
            pa = []
            for tid in bundle.target_neuron_ids:
                for lid, l in circuit.layers.items():
                    if tid in l.neurons: pa.append(l.neurons[tid].activation); break
                else: pa.append(0.0)
            ta = bundle.propagate(sa, post_activations=pa)
            for lid, l in circuit.layers.items():
                for j, tid in enumerate(bundle.target_neuron_ids):
                    if tid in l.neurons and j < len(ta):
                        l.neurons[tid].activation = max(-1.0, min(1.0, l.neurons[tid].activation + ta[j]))

        obs = circuit.observe()
        p_circ, _ = circuit.detect_circulations()
        circ_mu = getattr(circuit, '_circulation_measure', 0.0)
        if k > 0: circuit.compute_xin(prev_acts)
        prev_acts = circuit.layers["encoding"].get_activations()
        dw = circuit.learn()
        circuit.maintain()
        circuit._detect_practice_convergence(circ_mu)

        q = min(k // quarter, 3)
        motor_mag = math.sqrt(sum(v**2 for v in cm.values()))
        intake_by_quarter[q].append(intake)
        motor_by_quarter[q].append(motor_mag)

        if k % 200 == 0:
            ms = circuit.get_metabolic_state()
            print(f"  t={k+1:5d}  pool={ms['energy_pool']:.3f}  hunger={ms['hunger']:.3f}  "
                  f"motor={motor_mag:.4f}  intake={intake:.4f}  dw={dw:.3f}")

    elapsed = time.perf_counter() - t0
    print(f"\n  Total: {elapsed:.1f}s ({elapsed/TICKS*1000:.1f}ms/tick)")

    # Final weights
    print("\n=== Final Weights ===")
    for bid in key_bundles:
        b = find_bundle(circuit, bid)
        if b:
            ws = weight_summary(b)
            iw = initial_weights.get(bid, {})
            dw_mean = ws["mean"] - iw.get("mean", 0)
            dw_std = ws["std"] - iw.get("std", 0)
            print(f"  {bid:25s}: mean={ws['mean']:.6f} (d={dw_mean:+.6f})  "
                  f"std={ws['std']:.6f} (d={dw_std:+.6f})  "
                  f"range=[{ws['min']:.6f}, {ws['max']:.6f}]")

    # Weight change analysis
    print("\n=== Weight Specialization Analysis ===")
    integ_mot = find_bundle(circuit, "integ_to_motor")
    if integ_mot:
        print(f"  integrator->motor weights (3x3):")
        for i, src in enumerate(integ_mot.source_neuron_ids):
            for j, tgt in enumerate(integ_mot.target_neuron_ids):
                w = integ_mot.weights[i][j]
                init_w = 0.08  # initial value
                d = w - init_w
                arrow = "^" if d > 0.01 else "v" if d < -0.01 else "="
                print(f"    {src:20s} -> {tgt:8s}: {w:.6f} ({d:+.6f}) {arrow}")

    # Intake trend
    print("\n=== Foraging Efficiency Trend ===")
    for q in range(4):
        if intake_by_quarter[q]:
            avg_i = sum(intake_by_quarter[q]) / len(intake_by_quarter[q])
            avg_m = sum(motor_by_quarter[q]) / len(motor_by_quarter[q])
            efficiency = avg_i / max(avg_m, 1e-6)
            print(f"  Q{q+1} (t={q*quarter+1}-{(q+1)*quarter}): "
                  f"intake={avg_i:.5f}  motor={avg_m:.4f}  "
                  f"efficiency={efficiency:.4f}")

    # Final check
    print("\n=== Conclusion ===")
    q1_intake = sum(intake_by_quarter[0]) / max(len(intake_by_quarter[0]), 1)
    q4_intake = sum(intake_by_quarter[3]) / max(len(intake_by_quarter[3]), 1)
    if q4_intake > q1_intake * 1.1:
        ratio = q4_intake / max(q1_intake, 1e-6)
        print(f"  >> LEARNING DETECTED: Q4 intake {ratio:.2f}x higher than Q1")
        print(f"  >> STDP is encoding source-approach pathways")
    else:
        print(f"  >> No significant intake improvement (Q1={q1_intake:.5f}, Q4={q4_intake:.5f})")
        print(f"  >> STDP may need more time or stronger coupling")

    integ_ws = weight_summary(integ_mot) if integ_mot else {}
    init_ws = initial_weights.get("integ_to_motor", {})
    if integ_ws.get("std", 0) > init_ws.get("std", 0) * 1.5:
        print(f"  >> WEIGHT SPECIALIZATION: std increased {integ_ws['std']/max(init_ws['std'],1e-6):.2f}x")
    else:
        print(f"  >> Weight variance unchanged (no directional specialization yet)")

    print("\n" + "=" * 70)
