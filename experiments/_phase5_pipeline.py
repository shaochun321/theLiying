# -*- coding: utf-8 -*-
"""Phase 5: Pipeline + Metabolic Cycle (59ch -> HebbianCircuit -> Motor)."""
import sys, os, math
base = r"D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"
sys.path.insert(0, os.path.join(base, "engines"))
sys.path.insert(0, base)

from engines.practice_engine import PracticeEngine
from engines.hebbian_circuit import (
    HebbianCircuit, CircuitLayer, MetaNeuron, MetaSynapticBundle,
)


def build_full_circuit():
    circuit = HebbianCircuit()

    # encoding layer
    enc = circuit.add_layer("encoding")
    sig_names = ["sig_mean", "sig_std", "sig_peak_rate",
                 "sig_temporal_d", "sig_sync", "sig_range"]
    for f in sig_names:
        n = enc.add_neuron(f); n.target_rate = 0.05; n.threshold = 0.003; n.energy = 1000.0
    z_t = ["transition", "drift", "gamma_desync", "xin_residual",
           "potential_disp", "churn", "magnitude"]
    for c in z_t:
        n = enc.add_neuron(c); n.target_rate = 0.03; n.threshold = 0.003
    for f in sig_names:
        enc.add_bundle(source_ids=[f], target_ids=z_t)
    # v41.1 RECOVERED: emergent feedback topology
    # Previously: hand-designed groups (transition,drift→sig_mean,sig_std etc.)
    # Now: ALL z_t → ALL sig, with small random init weights.
    # STDP selectively strengthens causal pathways; irrelevant ones decay.
    # previously: degraded_from = "emergent_feedback_topology"
    import random as _rng
    _rng.seed(42)  # reproducible init
    fb = enc.add_bundle(source_ids=z_t, target_ids=sig_names)
    fb.init_weights()
    # Set small random initial weights (not uniform)
    for i in range(len(fb.weights)):
        for j in range(len(fb.weights[i])):
            fb.weights[i][j] = 0.01 + _rng.random() * 0.04  # [0.01, 0.05]
    for v in ["visc_rhythm", "visc_baseline"]:
        n = enc.add_neuron(v); n.target_rate = 0.01; n.threshold = 0.001; n.energy = 1000.0

    # signal_entropy layer
    se = CircuitLayer(layer_id="signal_entropy")
    se_names = ["spectral_H", "fano_H", "synchrony_H", "gradient_H",
                "sparseness_H", "autocorrelation_H", "energy_H"]
    for nm in se_names:
        n = se.add_neuron(nm); n.target_rate = 0.2; n.threshold = 0.001; n.energy = 1000.0
    circuit.layers["signal_entropy"] = se
    for nm in se_names[:4]:
        b = MetaSynapticBundle(bundle_id=f"se_{nm}", source_neuron_ids=[nm],
                               target_neuron_ids=z_t[:3]); b.init_weights()
        circuit.inter_layer_bundles.append(b)

    # column layer (v41.1: BCM learning, previously simple EMA)
    col = circuit.add_layer("column")
    for c in z_t:
        n = col.add_neuron(f"col_{c}", maturation="column")
        n.lateral_suppression_radius = 3; n.stdp_ltp_boost = 2.0; n.inertia = 2.0
        # v41.1: BCM sliding threshold
        n.bcm_theta = n.target_rate * n.target_rate
        n.bcm_theta_tau = 100.0
    enc_to_col = circuit.add_inter_layer_bundle("encoding", z_t, "column", [f"col_{c}" for c in z_t])
    enc_to_col.learning_rule = "bcm"

    # cpg layer
    cpg = circuit.add_layer("cpg")
    for cid in ["cpg_fast_a", "cpg_fast_b", "cpg_slow_a", "cpg_slow_b"]:
        n = cpg.add_neuron(cid); n.target_rate = 0.1; n.threshold = 0.001; n.energy = 1000.0
        n.activation = 0.1 if cid.endswith("_a") else 0.01
    def _ilb(bid, src, tgt, w=0.1):
        b = MetaSynapticBundle(bundle_id=bid, source_neuron_ids=src,
                               target_neuron_ids=tgt, bundle_inertia=1.0, learning_rule="stdp")
        b.init_weights()
        for i in range(len(b.weights)):
            for j in range(len(b.weights[i])): b.weights[i][j] = w
        circuit.inter_layer_bundles.append(b)
    _ilb("cpg_to_rhythm", ["cpg_fast_a", "cpg_fast_b"], ["visc_rhythm"])
    _ilb("cpg_to_baseline", ["cpg_slow_a", "cpg_slow_b"], ["visc_baseline"])

    # motor layer
    # v41.3: target_rate=0.01 — motor neurons have spontaneous firing rates
    # (motor readiness potential, Kornhuber 1965). Without this, HSS has no
    # drive to scale up incoming weights from weak signal sources (gradients).
    mot = CircuitLayer(layer_id="motor")
    for m in ["move_x", "move_y", "move_z"]:
        mn = mot.add_neuron(m); mn.target_rate = 0.01; mn.threshold = 0.01; mn.energy = 1000.0
    circuit.layers["motor"] = mot
    _ilb("enc_to_motor", z_t, ["move_x", "move_y", "move_z"], 0.01)
    _ilb("motor_to_enc", ["move_x", "move_y", "move_z"], ["transition", "magnitude"], 0.1)

    # origin layer
    orig = CircuitLayer(layer_id="origin")
    for o in ["origin_x", "origin_y", "origin_z", "origin_confidence", "origin_bandwidth"]:
        on = orig.add_neuron(o); on.target_rate = 0.0; on.threshold = 0.001; on.energy = 1000.0
    circuit.layers["origin"] = orig
    _ilb("motor_to_origin", ["move_x", "move_y", "move_z"],
         ["origin_x", "origin_y", "origin_z"])

    # vestibular layer
    vest = CircuitLayer(layer_id="vestibular")
    for v in ["lever_acoustic", "dlever_acoustic", "lever_thermal", "dlever_thermal",
              "lever_luminous", "dlever_luminous",
              "integ_acoustic", "integ_thermal", "integ_luminous",
              # v41.1: Gradient neurons — "chemoreceptors" for food direction
              "grad_acoustic", "grad_thermal", "grad_luminous",
              "vest_canal_yaw", "vest_canal_pitch", "vest_canal_roll",
              "vest_oto_x", "vest_oto_y", "vest_oto_z",
              "vest_omega_mag", "vest_accel_mag"]:
        vn = vest.add_neuron(v); vn.target_rate = 0.0; vn.threshold = 0.001; vn.energy = 1000.0
    # Gradient neurons: non-zero target_rate so homeostatic adaptation
    # finds the right threshold for their weak-but-persistent signals.
    # Biological basis: chemoreceptors have spontaneous firing rates
    # that maintain baseline sensitivity (Firestein 2001).
    for gn in ["grad_acoustic", "grad_thermal", "grad_luminous"]:
        vest.neurons[gn].target_rate = 0.01
    circuit.layers["vestibular"] = vest
    _ilb("imu_to_enc", ["vest_canal_yaw", "vest_canal_pitch", "vest_canal_roll",
                         "vest_oto_x", "vest_oto_y", "vest_oto_z"],
         ["transition", "drift", "magnitude"], 0.03)
    _ilb("integ_to_motor", ["integ_acoustic", "integ_thermal", "integ_luminous"],
         ["move_x", "move_y", "move_z"], 0.08)
    # v41.1: Gradient → motor pathway — THE KEY TRAINING TARGET
    # STDP must learn: "when gradient is active AND agent moves toward source → LTP"
    # Initial weights are low; must be built by experience
    _ilb("grad_to_motor", ["grad_acoustic", "grad_thermal", "grad_luminous"],
         ["move_x", "move_y", "move_z"], 0.05)
    # Gradient → encoding: let the circuit associate gradient with sensory patterns
    _ilb("grad_to_enc", ["grad_acoustic", "grad_thermal", "grad_luminous"],
         ["sig_mean", "sig_range", "magnitude"], 0.03)
    # v41.1: CPG → motor "babbling" pathway
    # CPG provides RANDOM motor exploration (like infant babbling).
    # This is a STRUCTURAL connection (like spinal cord), NOT learnable.
    # learning_rule='none' prevents STDP from degrading it.
    #
    # First: create the CPG layer with symmetry-breaking initial conditions
    cpg_layer = CircuitLayer(layer_id="cpg")
    cpg_neurons = {
        "cpg_fast_a": {"target_rate": 0.1, "threshold": 0.005, "init_act": 0.08},
        "cpg_fast_b": {"target_rate": 0.1, "threshold": 0.005, "init_act": 0.02},
        "cpg_slow_a": {"target_rate": 0.04, "threshold": 0.003, "init_act": 0.06},
        "cpg_slow_b": {"target_rate": 0.04, "threshold": 0.003, "init_act": 0.01},
    }
    for nid, params in cpg_neurons.items():
        n = cpg_layer.add_neuron(nid)
        n.target_rate = params["target_rate"]
        n.threshold = params["threshold"]
        n.energy = 1000.0
        n.activation = params["init_act"]  # symmetry-breaking!
    circuit.layers["cpg"] = cpg_layer

    b_cpg_m = MetaSynapticBundle(
        bundle_id="cpg_to_motor",
        source_neuron_ids=["cpg_fast_a", "cpg_fast_b"],
        target_neuron_ids=["move_x", "move_y", "move_z"],
        bundle_inertia=1.0, learning_rule="none")  # FIXED, no STDP
    b_cpg_m.init_weights()
    for i in range(len(b_cpg_m.weights)):
        for j in range(len(b_cpg_m.weights[i])):
            b_cpg_m.weights[i][j] = 0.15
    circuit.inter_layer_bundles.append(b_cpg_m)
    # Visceral → encoding z_t: let CPG rhythm modulate encoding sensitivity
    _ilb("visc_to_enc", ["visc_rhythm", "visc_baseline"],
         ["transition", "drift", "churn"], 0.05)

    # proprioception layer
    prop = CircuitLayer(layer_id="proprioception")
    pn = ["proprio_spindle_Ia", "proprio_spindle_II",
          "proprio_golgi_mean", "proprio_angle_mean", "proprio_energy"]
    for p in pn:
        n = prop.add_neuron(p); n.target_rate = 0.0; n.threshold = 0.001; n.energy = 1000.0
    circuit.layers["proprioception"] = prop
    _ilb("proprio_to_enc", pn, ["churn", "potential_disp", "drift"], 0.03)
    _ilb("proprio_to_motor", ["proprio_spindle_Ia", "proprio_golgi_mean"],
         ["move_x", "move_y", "move_z"], 0.02)

    # practice_cortex (empty, dynamic)
    circuit.layers["practice_cortex"] = CircuitLayer(layer_id="practice_cortex")

    # v41.3: sediment layer — deep memory substrate
    # A real hypergraph region with time-dilated neurons (update every 20 ticks).
    # Sedimentation modifies resting_potential, not activation.
    # Three input channels: expired fruits, ghost_bundles, encoding calcium.
    # Two output signals: sed_novelty, sed_recurrence.
    sed = circuit.add_layer("sediment")
    for c in z_t:
        n = sed.add_neuron(f"sed_{c}", maturation="sediment")
        n.inertia = 10.0
        n.threshold = 0.3
        n.target_rate = 0.001
        n.update_interval = 20
        n.energy = 1000.0
    # Special detection nodes
    for special in ["sed_novelty", "sed_recurrence"]:
        n = sed.add_neuron(special, maturation="sediment")
        n.inertia = 5.0
        n.threshold = 0.1
        n.target_rate = 0.005
        n.update_interval = 20
        n.energy = 1000.0

    # Weak feedback: sediment → encoding (frozen, w=0.001)
    b_sed_enc = MetaSynapticBundle(
        bundle_id="sed_to_enc",
        source_neuron_ids=[f"sed_{c}" for c in z_t],
        target_neuron_ids=z_t[:3],  # only transition, drift, gamma_desync
        bundle_inertia=10.0, learning_rule="none")
    b_sed_enc.init_weights()
    for i in range(len(b_sed_enc.weights)):
        for j in range(len(b_sed_enc.weights[i])):
            b_sed_enc.weights[i][j] = 0.001
    circuit.inter_layer_bundles.append(b_sed_enc)

    # Novelty → Column misalignment (frozen, w=0.01)
    b_nov_col = MetaSynapticBundle(
        bundle_id="sed_novelty_to_col",
        source_neuron_ids=["sed_novelty"],
        target_neuron_ids=["col_misalign_acc"],
        bundle_inertia=10.0, learning_rule="none")
    b_nov_col.init_weights()
    for i in range(len(b_nov_col.weights)):
        for j in range(len(b_nov_col.weights[i])):
            b_nov_col.weights[i][j] = 0.01
    circuit.inter_layer_bundles.append(b_nov_col)

    return circuit


def inject_sensory(circuit, sensory, box):
    # ── v41.1: CPG Phase Gate (Thalamic Gating) ──
    # External signals must align with CPG phase to enter the circuit.
    # This is structural coupling, not artificial coupling.
    #
    # Biological basis: thalamic reticular nucleus (TRN) rhythmically
    # inhibits sensory relay. Only signals arriving during the "open
    # window" (correct CPG phase) reach cortex.
    #
    # Implementation: gate = sigmoid(cpg_fast_a * gain)
    # cpg_fast_a > 0 (A-side active): gate ≈ 1.0 → signals pass
    # cpg_fast_a < 0 (B-side active): gate ≈ 0.0 → signals blocked
    # cpg_fast_a = 0 (transition):    gate = 0.5 → partial pass
    cpg = circuit.layers.get("cpg")
    if cpg and "cpg_fast_a" in cpg.neurons:
        cpg_a = cpg.neurons["cpg_fast_a"].activation
        cpg_b = cpg.neurons["cpg_fast_b"].activation
        # Gate uses A-B difference: oscillates around 0
        # A dominant → positive → gate open
        # B dominant → negative → gate closed
        phase_gate = max(0.0, min(1.0, (cpg_a - cpg_b) * 5.0 + 0.5))
    else:
        phase_gate = 1.0  # fallback: always open

    # Internal signals: entropy channels (already inside circuit, no gate needed)
    se = circuit.layers.get("signal_entropy")
    if se:
        for nm in ["spectral_H", "fano_H", "synchrony_H", "gradient_H",
                    "sparseness_H", "autocorrelation_H", "energy_H"]:
            if nm in se.neurons and nm in sensory:
                se.neurons[nm].activate(sensory[nm])

    # External signals: vestibular (GATED by CPG phase)
    # v41.3: All externally-driven neurons mark pre_trace when active.
    # Without pre_trace, STDP cannot detect causal timing from these neurons.
    # Biological basis: sensory receptor action potentials propagate to
    # downstream synapses, generating pre-synaptic traces (Kandel Ch.10).
    vest = circuit.layers.get("vestibular")
    if vest:
        for st in ["acoustic", "thermal", "luminous"]:
            # Lever arms and rates: gated external signals
            for pf, fn in [("lever_", lambda r: r/(box+1e-6)),
                           ("dlever_", lambda r: math.tanh(r*10)),
                           ("integ_", lambda r: math.tanh(r/5))]:
                k = f"{pf}{st}"
                if k in vest.neurons:
                    raw = fn(sensory.get(k, 0))
                    vest.neurons[k].activation = raw * phase_gate
                    if abs(vest.neurons[k].activation) > 0.001:
                        vest.neurons[k].pre_trace += 1.0
        # IMU signals: less gated (vestibular is partially internal)
        imu_gate = 0.5 + 0.5 * phase_gate  # [0.5, 1.0] — always partially open
        for vk in ["vest_canal_yaw", "vest_canal_pitch", "vest_canal_roll",
                    "vest_oto_x", "vest_oto_y", "vest_oto_z",
                    "vest_omega_mag", "vest_accel_mag"]:
            if vk in vest.neurons:
                vest.neurons[vk].activation = math.tanh(sensory.get(vk, 0) * 5) * imu_gate
                if abs(vest.neurons[vk].activation) > 0.001:
                    vest.neurons[vk].pre_trace += 1.0
        # Gradient signals: FULLY gated
        # v41.4: Receptor gain modulation by hunger
        # DEGRADED: chemoreceptor_density_upregulation
        #   → proxy: gain = 1 + hunger_excess × k_gain
        # 物理: 饥饿 → 化学受体基因表达上调 → 受体密度增加
        #       → 同浓度梯度产生更强神经响应 (Bargmann 2006)
        hunger_state = circuit.get_metabolic_state() if hasattr(circuit, 'get_metabolic_state') else {}
        _hunger = hunger_state.get('hunger', 0.0)
        _hunger_excess = max(0.0, _hunger - 0.3)
        _receptor_gain = 1.0 + _hunger_excess * 5.0  # max gain = 4.5× at hunger=1.0
        for st in ["acoustic", "thermal", "luminous"]:
            gk = f"grad_{st}"
            if gk in vest.neurons:
                raw_grad = sensory.get(f"gradient_{st}", 0)
                vest.neurons[gk].activation = math.tanh(raw_grad * 5) * phase_gate * _receptor_gain
                if abs(vest.neurons[gk].activation) > 0.001:
                    vest.neurons[gk].pre_trace += 1.0

    # ── v41.1: Column Mossy Fiber Pathway (Ungated Signal) ──
    # The Column forward model needs access to RAW signal strength
    # (before thalamic gating) to detect misalignment.
    # In biology: cerebellum receives sensory input via mossy fibers
    # from pontine nuclei, bypassing the thalamic gate.
    # We use received_* (total signal at agent) rather than gradient_*
    # (directional derivative, too small) for robust detection.
    col = circuit.layers.get("column")
    if col:
        for st in ["acoustic", "thermal", "luminous"]:
            raw_key = f"col_raw_{st}"
            if raw_key not in col.neurons:
                n = col.add_neuron(raw_key)
                n.energy = 1000.0
                n.maturation = "column"
                n.lateral_suppression_radius = 0
                n.stdp_ltp_boost = 1.0
            raw_recv = sensory.get(f"received_{st}", 0)
            # UNGATED: Column sees the true signal, gate or no gate
            col.neurons[raw_key].activation = math.tanh(raw_recv * 2)
            if abs(col.neurons[raw_key].activation) > 0.001:
                col.neurons[raw_key].pre_trace += 1.0

    orig = circuit.layers.get("origin")
    if orig:
        for ax in ["x", "y", "z"]:
            orig.neurons[f"origin_{ax}"].activation = sensory.get(f"origin_{ax}", 0) / (box+1e-6)
            if abs(orig.neurons[f"origin_{ax}"].activation) > 0.001:
                orig.neurons[f"origin_{ax}"].pre_trace += 1.0
        orig.neurons["origin_confidence"].activation = sensory.get("origin_confidence", 0)
        if abs(orig.neurons["origin_confidence"].activation) > 0.001:
            orig.neurons["origin_confidence"].pre_trace += 1.0
        orig.neurons["origin_bandwidth"].activation = math.tanh(sensory.get("origin_crystallizable", 0))
        if abs(orig.neurons["origin_bandwidth"].activation) > 0.001:
            orig.neurons["origin_bandwidth"].pre_trace += 1.0
    prop = circuit.layers.get("proprioception")
    if prop:
        for pk in ["proprio_spindle_Ia", "proprio_spindle_II",
                    "proprio_golgi_mean", "proprio_angle_mean", "proprio_energy"]:
            if pk in prop.neurons:
                prop.neurons[pk].activation = math.tanh(sensory.get(pk, 0) * 2)
                if abs(prop.neurons[pk].activation) > 0.001:
                    prop.neurons[pk].pre_trace += 1.0
    enc = circuit.layers.get("encoding")
    if enc:
        mp = {"sig_mean": sensory.get("energy", 0), "sig_std": sensory.get("fano_H", 0),
              "sig_peak_rate": sensory.get("motor_magnitude", 0),
              "sig_temporal_d": sensory.get("delta_ke", 0),
              "sig_sync": sensory.get("synchrony_H", 0),
              "sig_range": sensory.get("spectral_H", 0)}
        for nid, val in mp.items():
            if nid in enc.neurons: enc.neurons[nid].activate(float(val))


def read_motor(circuit):
    # v41.1: Motor output is pure neural activation — no metabolic injection
    mot = circuit.layers.get("motor")
    if mot: return {n: mot.neurons[n].activation for n in mot.neurons}
    return {"move_x": 0, "move_y": 0, "move_z": 0}


if __name__ == "__main__":
    import time

    print("=" * 70)
    print("  PHASE 5: Pipeline + Metabolic Cycle")
    print("  consumption -> hunger -> exploration -> feeding -> recovery")
    print("=" * 70)

    engine = PracticeEngine(n_particles=30, seed=42)
    circuit = build_full_circuit()

    nn = sum(len(l.neurons) for l in circuit.layers.values())
    nb = sum(len(l.bundles) for l in circuit.layers.values()) + len(circuit.inter_layer_bundles)
    print(f"\n  {len(circuit.layers)} layers, {nn} neurons, {nb} bundles")

    TICKS = 500
    print(f"\n=== Running {TICKS} ticks ===")
    t0 = time.perf_counter()

    log_pool, log_hunger, log_motor, log_intake = [], [], [], []

    for k in range(TICKS):
        cm = read_motor(circuit) if k > 0 else {"move_x": 0, "move_y": 0, "move_z": 0}
        sensory = engine.step(cm)
        inject_sensory(circuit, sensory, engine.box_size)

        # Metabolic: received_* -> feed()
        total_recv = sum(sensory.get(f"received_{s}", 0) for s in ["acoustic", "thermal", "luminous"])
        intake = total_recv * 0.01
        circuit.feed(intake)

        # Transport
        se_in = {ch: sensory.get(ch, 0.5)
                 for ch in ["spectral_H", "fano_H", "synchrony_H", "gradient_H",
                            "sparseness_H", "autocorrelation_H", "energy_H"]}
        circuit.transport(se_in, "signal_entropy")

        # Inter-layer propagation
        for bundle in circuit.inter_layer_bundles:
            sl = None
            for lid, l in circuit.layers.items():
                if bundle.source_neuron_ids[0] in l.neurons: sl = l; break
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

        ms = circuit.get_metabolic_state()
        mm = math.sqrt(sum(v**2 for v in cm.values()))
        log_pool.append(ms["energy_pool"])
        log_hunger.append(ms["hunger"])
        log_motor.append(mm)
        log_intake.append(intake)

        if k % 50 == 0 or k == TICKS - 1:
            h = ms["hunger"]
            filled = int(h * 20)
            bar = "#" * filled + "." * (20 - filled)
            print(f"  t={k+1:4d}  pool={ms['energy_pool']:5.2f}  "
                  f"hunger={h:.3f} [{bar}]  motor={mm:.4f}  "
                  f"intake={intake:.4f}  dw={dw:.3f}  "
                  f"P={'Y' if p_circ else 'N'}")

    elapsed = time.perf_counter() - t0
    print(f"\n  Total: {elapsed:.1f}s ({elapsed/TICKS*1000:.1f}ms/tick)")

    # Analysis
    print(f"\n=== Metabolic Analysis ===")
    mh = max(log_hunger); mi = max(log_intake)
    print(f"  Peak hunger:  {mh:.3f} at tick {log_hunger.index(mh)}")
    print(f"  Peak intake:  {mi:.4f} at tick {log_intake.index(mi)}")
    print(f"  Pool first50: {sum(log_pool[:50])/50:.3f}")
    print(f"  Pool last50:  {sum(log_pool[-50:])/50:.3f}")

    hungry = [(h, m) for h, m in zip(log_hunger, log_motor) if h > 0.3]
    sated = [(h, m) for h, m in zip(log_hunger, log_motor) if h <= 0.3]
    if hungry and sated:
        mh_avg = sum(m for _, m in hungry) / len(hungry)
        ms_avg = sum(m for _, m in sated) / len(sated)
        ratio = mh_avg / max(ms_avg, 1e-6)
        print(f"\n  Motor when hungry:  {mh_avg:.4f} (n={len(hungry)})")
        print(f"  Motor when sated:   {ms_avg:.4f} (n={len(sated)})")
        print(f"  Ratio: {ratio:.2f}x")
        if ratio > 1.2:
            print(f"  >> HUNGER DRIVES EXPLORATION ({ratio:.1f}x motor increase)")
        else:
            print(f"  >> Hunger-exploration coupling weak")
    else:
        print(f"  >> Insufficient data for hungry/sated comparison")

    met = circuit.get_metrics()
    ms = circuit.get_metabolic_state()
    print(f"\n=== Final State ===")
    print(f"  Neurons: {met['total_neurons']}  Alive: {met['alive_neurons']}  Bundles: {met['total_bundles']}")
    print(f"  Maturation: {met['maturation']}")
    cx = sum(1 for n in circuit.layers['encoding'].neurons if n.startswith('cx_'))
    print(f"  cx_ crystals: {cx}  Dormant fruits: {met['dormant_fruits']}")
    print(f"  Energy: {ms['energy_pool']:.3f}/{ms['energy_capacity']:.1f}  Hunger: {ms['hunger']:.3f}")

    print("\n" + "=" * 70)
    print("  PHASE 5 COMPLETE")
    print("=" * 70)
