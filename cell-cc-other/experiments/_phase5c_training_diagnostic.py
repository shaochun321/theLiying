# -*- coding: utf-8 -*-
"""v41.1 Training Diagnostic: Why can't STDP learn gradient→motor?

Traces the exact causal chain tick-by-tick:
  gradient active? → motor active? → coincidence? → LTP or LTD?
  dlever < 0 (approaching)? → intake > 0? → Xin feeding bonus?
"""
import sys, os, math
base = r"D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"
sys.path.insert(0, os.path.join(base, "engines"))
sys.path.insert(0, base)
sys.path.insert(0, r"D:\cell-cc\experiments")

from _phase5_pipeline import build_full_circuit, inject_sensory, read_motor
from engines.practice_engine import PracticeEngine
from engines.hebbian_circuit import MetaNeuron


def find_bundle(circuit, bid_prefix):
    for b in circuit.inter_layer_bundles:
        if b.bundle_id.startswith(bid_prefix):
            return b
    return None


if __name__ == "__main__":
    engine = PracticeEngine(n_particles=30, seed=42)
    circuit = build_full_circuit()

    gb = find_bundle(circuit, "grad_to_motor")
    cpgb = find_bundle(circuit, "cpg_to_motor")

    print("=" * 80)
    print("  v41.1 STDP Training Diagnostic")
    print("=" * 80)

    # Track co-activation events
    ltp_events = 0
    ltd_events = 0
    coincidence_events = 0
    gradient_active_ticks = 0
    motor_active_ticks = 0
    approaching_ticks = 0

    TICKS = 3000
    prev = None
    quarter = TICKS // 4
    intake_q = [[] for _ in range(4)]
    motor_q = [[] for _ in range(4)]

    for k in range(TICKS):
        cm = read_motor(circuit) if k > 0 else {"move_x": 0, "move_y": 0, "move_z": 0}
        s = engine.step(cm)
        inject_sensory(circuit, s, engine.box_size)

        total_recv = sum(s.get("received_%s" % t, 0) for t in ["acoustic", "thermal", "luminous"])
        intake = total_recv * 0.01
        circuit.feed(intake)

        se = {c: s.get(c, 0.5) for c in ["spectral_H", "fano_H", "synchrony_H",
              "gradient_H", "sparseness_H", "autocorrelation_H", "energy_H"]}
        circuit.transport(se, "signal_entropy")

        # Propagate inter-layer
        for b in circuit.inter_layer_bundles:
            sl = None
            for lid, l in circuit.layers.items():
                if b.source_neuron_ids[0] in l.neurons:
                    sl = l; break
            if sl is None: continue
            sa = [sl.neurons.get(sid, MetaNeuron("_", "_")).activation
                  for sid in b.source_neuron_ids]
            pa = []
            for tid in b.target_neuron_ids:
                for lid, l in circuit.layers.items():
                    if tid in l.neurons:
                        pa.append(l.neurons[tid].activation); break
                else:
                    pa.append(0.0)
            ta = b.propagate(sa, post_activations=pa)
            for lid, l in circuit.layers.items():
                for j, tid in enumerate(b.target_neuron_ids):
                    if tid in l.neurons and j < len(ta):
                        l.neurons[tid].activation = max(-1.0, min(1.0,
                            l.neurons[tid].activation + ta[j]))

        circuit.observe()
        circuit.detect_circulations()
        if prev is not None:
            circuit.compute_xin(prev)
        prev = circuit.layers["encoding"].get_activations()

        # DIAGNOSE: Check pre/post activations for grad_to_motor
        vest = circuit.layers["vestibular"]
        mot = circuit.layers["motor"]
        grad_act = [vest.neurons[g].activation for g in
                    ["grad_acoustic", "grad_thermal", "grad_luminous"]]
        motor_act = [mot.neurons[m].activation for m in
                     ["move_x", "move_y", "move_z"]]
        grad_mag = max(abs(a) for a in grad_act)
        motor_mag = math.sqrt(sum(a**2 for a in motor_act))

        # Check approaching
        dlever_sum = sum(s.get("dlever_%s" % t, 0) for t in ["acoustic", "thermal", "luminous"])
        approaching = dlever_sum < 0  # negative = getting closer

        if grad_mag > 0.01:
            gradient_active_ticks += 1
        if motor_mag > 0.01:
            motor_active_ticks += 1
        if approaching:
            approaching_ticks += 1
        if grad_mag > 0.01 and motor_mag > 0.01:
            coincidence_events += 1

        # Check pre/post traces for STDP timing
        pre_traces = [getattr(vest.neurons[g], 'pre_trace', 0)
                      for g in ["grad_acoustic", "grad_thermal", "grad_luminous"]]
        post_traces = [getattr(mot.neurons[m], 'post_trace', 0)
                       for m in ["move_x", "move_y", "move_z"]]
        pre_max = max(pre_traces)
        post_max = max(post_traces)

        dw = circuit.learn()
        circuit.maintain()
        mu = getattr(circuit, '_circulation_measure', 0.0)
        circuit._detect_practice_convergence(mu)

        q = min(k // quarter, 3)
        intake_q[q].append(intake)
        motor_q[q].append(motor_mag)

        if k < 20 or k % 500 == 0:
            ms = circuit.get_metabolic_state()
            gw = [gb.weights[i][j] for i in range(len(gb.weights))
                  for j in range(len(gb.weights[i]))]
            gw_mean = sum(gw) / len(gw) if gw else 0
            gw_max = max(gw) if gw else 0
            print("t=%4d  grad=%.4f  motor=%.4f  approach=%s  "
                  "intake=%.4f  pool=%.3f  hunger=%.3f  "
                  "pre_tr=%.3f  post_tr=%.3f  gw_mean=%.5f  gw_max=%.5f" % (
                k, grad_mag, motor_mag, "Y" if approaching else "N",
                intake, ms["energy_pool"], ms["hunger"],
                pre_max, post_max, gw_mean, gw_max))

    print()
    print("=" * 80)
    print("  SUMMARY (%d ticks)" % TICKS)
    print("=" * 80)
    print("  Gradient active (>0.01): %d/%d (%.1f%%)" % (
        gradient_active_ticks, TICKS, 100*gradient_active_ticks/TICKS))
    print("  Motor active (>0.01):    %d/%d (%.1f%%)" % (
        motor_active_ticks, TICKS, 100*motor_active_ticks/TICKS))
    print("  Coincidence (both):      %d/%d (%.1f%%)" % (
        coincidence_events, TICKS, 100*coincidence_events/TICKS))
    print("  Approaching source:      %d/%d (%.1f%%)" % (
        approaching_ticks, TICKS, 100*approaching_ticks/TICKS))
    print()

    print("  Intake trend:")
    for q in range(4):
        avg_i = sum(intake_q[q]) / max(len(intake_q[q]), 1)
        avg_m = sum(motor_q[q]) / max(len(motor_q[q]), 1)
        print("    Q%d: intake=%.5f  motor=%.4f" % (q+1, avg_i, avg_m))

    print()
    print("  grad_to_motor final weights:")
    for i, src in enumerate(gb.source_neuron_ids):
        for j, tgt in enumerate(gb.target_neuron_ids):
            w = gb.weights[i][j]
            print("    %s -> %s: %.6f (d=%+.6f)" % (src, tgt, w, w - 0.05))

    # Key question
    print()
    if coincidence_events < TICKS * 0.05:
        print("  >> DIAGNOSIS: Too few coincidence events (%.1f%%)" %
              (100*coincidence_events/TICKS))
        print("     gradient and motor rarely active at the same time")
        print("     STDP cannot form LTP without pre+post coincidence")
        if motor_active_ticks < TICKS * 0.1:
            print("     ROOT CAUSE: Motor activity too low (%.1f%%)" %
                  (100*motor_active_ticks/TICKS))
            print("     CPG babbling not reaching motor neurons effectively")
        if gradient_active_ticks < TICKS * 0.1:
            print("     ROOT CAUSE: Gradient signals too weak (%.1f%%)" %
                  (100*gradient_active_ticks/TICKS))
    elif coincidence_events > TICKS * 0.1:
        gw = [gb.weights[i][j] for i in range(len(gb.weights))
              for j in range(len(gb.weights[i]))]
        if max(gw) > 0.06:
            print("  >> LTP DETECTED: grad_to_motor weights growing!")
        else:
            print("  >> Coincidence present (%.1f%%) but no weight growth" %
                  (100*coincidence_events/TICKS))
            print("     Possible cause: LTP and LTD balancing out")
