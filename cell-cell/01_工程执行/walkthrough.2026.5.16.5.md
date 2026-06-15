# v40.9 Walkthrough — CPG Bio-Substrate + 3D Physics Pipeline

## Summary

v40.9 delivers two major capabilities:
1. **CPG Bio-Substrate**: Prevents thermal death via endogenous oscillation
2. **3D Physics Engine**: Real spring-repulsion particle simulation as data source

---

## Part A: CPG Bio-Substrate (Thermal Death Fix)

### Problem
v40.8 suffered structural thermal death: after tick ~211, PRP=0, convergence→0, inter-layer bundles frozen.

### Solution: Three-Layer Fix

1. **CPG Half-Center Oscillator** (`_cpg_step()`): 4-neuron reciprocal inhibition
2. **Ghost Resurrection**: CPG-gated revival of dormant inter-layer bundles
3. **Convergence Decay Modulation**: CPG activity slows memory trace decay (0.99→0.997)

### v40.8 → v40.9 Results @2000 ticks

| Metric | v40.8 (dead) | v40.9 (alive) |
|--------|:-:|:-:|
| PRP | **0** | **0.0073** ✅ |
| Convergence | **0** | **9** ✅ |
| IL bundles | 9 (frozen) | **12-17** (cycling) ✅ |

---

## Part B: 3D Spring-Repulsion Particle System

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│  ParticleSystem3D (50 particles in 10³ bounding box)    │
│  ├── Spring force:    F = -k_s * (r - r_0) * r̂         │
│  ├── Repulsion force: F = k_r / r² * r̂                 │
│  ├── Damping:         F = -γ * v                        │
│  ├── Boundary:        elastic wall reflection           │
│  └── LIF neuron per particle:                           │
│       τ_m dV/dt = -(V - V_rest) + R_m * I_ext          │
│       I_ext = α|stress| + β|displacement| + I_synaptic │
└─────────────────────────────────────────────────────────┘
           ↓ per stimulus epoch
┌─────────────────────────────────────────────────────────┐
│  PhysicsSourceAdapter (CellRecord/EnvelopeRecord)       │
│  ├── natural_movie_one: coherent global oscillation     │
│  │   LIF: V_thresh≈-57, V_rest≈-62, τ≈18 (tight)      │
│  ├── natural_scenes: localized impulse bursts           │
│  │   LIF: V_thresh≈-55±4, V_rest≈-62±4, τ≈15±6 (wide) │
│  └── static_gratings: multi-frequency compression       │
│      LIF: V_rest bimodal (-58/-68), τ≈12 (fast)        │
└─────────────────────────────────────────────────────────┘
           ↓ identical interface
┌─────────────────────────────────────────────────────────┐
│  Pipeline: signal entropy → circuit → discrimination    │
└─────────────────────────────────────────────────────────┘
```

### New Files

#### [NEW] [physics_particle_system.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/physics_particle_system.py)
- `Particle3D` dataclass (position, velocity, LIF state)
- `ParticleSystem3D` (force computation, Verlet integration, LIF dynamics)
- Three perturbation functions: `perturbation_movie`, `_scenes`, `_gratings`
- Self-test validates energy conservation, spike rates, boundary containment

#### [NEW] [physics_source_adapter.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/physics_source_adapter.py)
- `PhysicsSourceAdapter` class (drop-in replacement for `AllenBrainAdapter`)
- Pre-simulates all windows, caches per-particle statistics
- LIF parameter modulation per stimulus epoch
- Self-test validates stimulus diversity and signal variation

### Modified Files

#### [MODIFY] [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py)
- `DATA_SOURCE=physics` environment variable switches to physics adapter
- NWB/HDF5 loading skipped for physics mode
- Stimulus classification uses adapter's built-in schedule

```diff:run_v40_integrated.py
#!/usr/bin/env python3
"""v40 Integrated Circuit — Full Pipeline + Signal Entropy + STDP + R-chain.

Holistic integration:
  1. Run full pipeline → writes ALL ledgers (entropy, anomaly, masking, transport)
  2. Write NEW v40_signal_entropy_ledger (spectral_H, fano, synchrony, gradient)
     — these actually vary across stimulus types unlike pipeline-structural entropy
  3. Read signal entropy + masking counterevidence from DB
  4. Feed into circuit: signal entropy as structural input neurons,
     masking survival rate as modulatory gain on z_t neurons
  5. STDP + homeostasis adapts structure based on measured quantities
  6. Compare discrimination with R-chain validation

The whole loop mirrors T/O/P/R/Xin:
  T = pipeline transport → DB
  O = observe signal entropy variation
  P = primary discrimination path (STDP circuit)
  R = counter-evidence from masking layer → refute weak dimensions
  Xin = residual tension → structural adjustment
"""
import sys, os, math, json, sqlite3
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "src"))
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "engines"))

from allen_brain_adapter import AllenBrainAdapter
from motion_recognition_engine import FeatureExtractor, BayesianMotionRecognizer
from hebbian_circuit import (HebbianCircuit, CircuitLayer, MetaNeuron,
                             MetaSynapticBundle, build_circuit_from_signal_transform)
import pipeline_engine as pe
import h5py

DB_PATH = str(BASE / "db" / "v40_integrated.db")


def build_signal_entropy_circuit(signal_transform) -> HebbianCircuit:
    """Build circuit with sensitivity zone differentiation.

    Architecture — differentiated sensitivity zones:
    ────────────────────────────────────────────────────────────────
    Each entropy channel gets its OWN receptive field (zone).
    All zones are simultaneously activated as the circulation baseline.
    This prevents any single dominant dimension from killing
    signal-source information from other channels.

    signal_entropy_layer: 4 neurons (spectral_H, fano_H, synchrony_H, gradient_H)
          │
          ├─→ zone_spectral (2 intermediate neurons) ─→ z_t targets
          ├─→ zone_fano (2 intermediate neurons) ─→ z_t targets
          ├─→ zone_synchrony (2 intermediate neurons) ─→ z_t targets
          └─→ zone_gradient (2 intermediate neurons) ─→ z_t targets
          │
    encoding_layer: 6 signal features → 7 z_t costs
          │
    column_layer: consolidation

    Within each zone:
      - Dedicated intermediate neurons transform entropy into
        zone-specific activation patterns
      - Each zone has its OWN feedback loop (closed circulation per zone)
      - STDP operates per-zone, allowing independent weight adaptation

    Cross-zone integration:
      - All zones project to shared z_t targets
      - Divisive normalization operates across z_t, not within zones
      - This creates proportional contribution, not winner-take-all

    The resulting μ(G) contains:
      - Per-zone circulations (local, always active at baseline)
      - Cross-zone circulations (global, emerge from STDP convergence)
      - The genuine P is the circulation that persists when any
        single zone is masked (validated by R-chain counterevidence)
    ────────────────────────────────────────────────────────────────
    """
    circuit = build_circuit_from_signal_transform(signal_transform)

    # Signal entropy input layer
    entropy_layer = CircuitLayer(layer_id="signal_entropy")
    entropy_names = ["spectral_H", "fano_H", "synchrony_H", "gradient_H",
                     "sparseness_H", "autocorrelation_H", "energy_H"]
    for name in entropy_names:
        n = entropy_layer.add_neuron(name)
        n.target_rate = 0.2
        n.threshold = 0.001
        n.energy = 1000.0  # input neurons: externally driven, should never die
    circuit.layers["signal_entropy"] = entropy_layer

    z_t_names = ["transition", "drift", "gamma_desync",
                 "xin_residual", "potential_disp", "churn", "magnitude"]

    # ── Create sensitivity zones ──
    # Each zone: entropy channel → 2 intermediate neurons → z_t targets
    # The intermediates allow per-zone STDP to learn independent patterns

    zone_specs = {
        "spectral": {
            "source": ["spectral_H"],
            "intermediates": ["zone_spec_mag", "zone_spec_pot"],
            "targets": ["magnitude", "potential_disp"],
        },
        "fano": {
            "source": ["fano_H"],
            "intermediates": ["zone_fano_churn", "zone_fano_drift"],
            "targets": ["churn", "drift"],
        },
        "synchrony": {
            "source": ["synchrony_H"],
            "intermediates": ["zone_sync_gamma", "zone_sync_trans"],
            "targets": ["gamma_desync", "transition"],
        },
        "gradient": {
            "source": ["gradient_H"],
            "intermediates": ["zone_grad_xin", "zone_grad_trans"],
            "targets": ["xin_residual", "transition"],
        },
    }

    # Higher-order features: parallel bundles to existing zone intermediates
    # These AUGMENT the existing zones without adding neurons or zones
    higher_order_pairs = [
        # (source_H, target_zone_intermediates, name)
        ("energy_H",          ["zone_spec_mag", "zone_spec_pot"], "energy_to_spectral"),
        ("sparseness_H",      ["zone_fano_churn", "zone_fano_drift"], "sparseness_to_fano"),
        ("autocorrelation_H", ["zone_grad_xin", "zone_grad_trans"], "autocorr_to_gradient"),
    ]

    for zone_name, spec in zone_specs.items():
        # Add intermediate neurons to encoding layer
        enc = circuit.layers["encoding"]
        for iname in spec["intermediates"]:
            n = enc.add_neuron(iname)
            n.target_rate = 0.1     # lower target: zone neurons are modulatory
            n.threshold = 0.0001    # very low: always respond to entropy
            n.energy = 1000.0       # modulatory neurons should never die

        sources = spec["source"]  # list of entropy channel names

        # Bundle 1: entropy sources → intermediate neurons
        b_in = MetaSynapticBundle(
            bundle_id=f"sigH_{zone_name}_to_zone",
            source_neuron_ids=sources,
            target_neuron_ids=spec["intermediates"],
            bundle_inertia=0.5, learning_rule="stdp")
        b_in.init_weights()
        # Higher initial weights for zone input — entropy should pass through
        for i in range(len(b_in.weights)):
            for j in range(len(b_in.weights[i])):
                b_in.weights[i][j] = 0.3
        circuit.inter_layer_bundles.append(b_in)

        # Bundle 2: intermediate neurons → z_t targets (within encoding)
        b_out = enc.add_bundle(
            source_ids=spec["intermediates"],
            target_ids=spec["targets"])
        b_out.bundle_id = f"zone_{zone_name}_to_zt"
        b_out.learning_rule = "stdp"
        # Initial weights: moderate, to be shaped by STDP
        for i in range(len(b_out.weights)):
            for j in range(len(b_out.weights[i])):
                b_out.weights[i][j] = 0.2

        # Bundle 3: z_t targets → entropy sources (feedback loop)
        # This closes the per-zone circulation, making each zone
        # a self-contained T/O/P/R/Xin mini-loop
        b_fb = MetaSynapticBundle(
            bundle_id=f"zone_{zone_name}_feedback",
            source_neuron_ids=spec["targets"],
            target_neuron_ids=sources,
            bundle_inertia=0.8, learning_rule="oja")
        b_fb.init_weights()
        for i in range(len(b_fb.weights)):
            for j in range(len(b_fb.weights[i])):
                b_fb.weights[i][j] = 0.05  # weak feedback initially
        circuit.inter_layer_bundles.append(b_fb)

    # Higher-order features (sparseness, autocorrelation, energy) are applied
    # as contrastive gain modulation in Step 3.5 of the circuit loop, not as
    # parallel bundles. This prevents range-mismatch flooding.

    return circuit


def cosine_sim(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) + 1e-12
    nb = math.sqrt(sum(x * x for x in b)) + 1e-12
    return dot / (na * nb)


def main():
    print("=" * 72)
    print("v40 INTEGRATED: Signal Entropy + STDP + R-chain Validation")
    print("=" * 72)

    # ══════════════════════════════════════════════════════════════
    # Phase 1: T — Full pipeline → all ledgers
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 1 [T]: Pipeline transport → all ledgers")
    print(f"{'─' * 72}")

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    pe.apply_migrations(conn)
    conn.commit()

    adapter = AllenBrainAdapter(split_role="all")
    run_id = "v40_integrated_001"
    pe.register_adapter(conn, run_id, adapter)

    ext = FeatureExtractor()
    rec = BayesianMotionRecognizer(prior_var=1.0)
    prev_cells = None
    WINDOWS = adapter.total_windows

    # Load stimulus epochs
    nwb_path = str(BASE / "data/allen_brain/ophys_experiment_data/500964514.nwb")
    f = h5py.File(nwb_path, "r")
    pres = f["stimulus"]["presentation"]
    epochs = []
    for sn in pres.keys():
        ds = pres[sn]
        if "timestamps" in ds:
            ts = ds["timestamps"][:]
            if len(ts) >= 2:
                clean = sn.replace("_stimulus", "")
                block_start = ts[0]
                prev_t = ts[0]
                for i in range(1, len(ts)):
                    if ts[i] - prev_t > 30:
                        epochs.append((clean, float(block_start), float(prev_t)))
                        block_start = ts[i]
                    prev_t = ts[i]
                epochs.append((clean, float(block_start), float(prev_t)))
    # Sort by DURATION ascending (narrowest first) for proper matching
    # static_gratings spans [50,3803] but movie is [2362,2662] — narrowest wins
    epochs.sort(key=lambda x: x[2] - x[1])
    fl_ts = f["processing"]["brain_observatory_pipeline"]["DfOverF"]["imaging_plane_1"]["timestamps"][:]
    sub_ts = fl_ts[::38][:3003]
    f.close()

    for k in range(WINDOWS):
        cells = adapter.generate_cells(k)
        if not cells:
            continue

        env = adapter.make_envelope(k)
        env_id = pe.write_envelope(conn, run_id, env)
        pw_id = pe.write_process_window(conn, run_id, adapter, k, env_id,
                                         len(cells), ["ingest", "transport"])
        uid_map = pe.write_cells(conn, run_id, adapter, k, cells)

        if prev_cells is not None:
            pe.write_transport(conn, run_id, adapter, k, prev_cells, cells)

        hyps = pe.write_hypotheses(conn, run_id, adapter, k, cells)
        xi_id = pe.write_xi(conn, run_id, adapter, k, hyps, cells[:5])

        if prev_cells is not None:
            disps = {}
            for i in range(min(len(prev_cells), len(cells))):
                dx = cells[i].x - prev_cells[i].x
                dy = cells[i].y - prev_cells[i].y
                disps[i] = math.sqrt(dx*dx + dy*dy)
            feats = ext.extract(
                {i: (c.x, c.y) for i, c in enumerate(prev_cells)},
                {i: (c.x, c.y) for i, c in enumerate(cells)},
                disps, signal_values=[c.V_mean for c in cells])
            pred, _, _ = rec.classify(feats)
            rec.learn(feats, pred)

        # Write ALL ledgers
        pe.write_external_ledgers(conn, run_id, adapter, k, env, cells)
        # Write v40 SIGNAL entropy (the key new ledger)
        pe.write_signal_entropy_ledger(conn, run_id, adapter, k, cells)

        prev_cells = cells
        if k % 20 == 0:
            conn.commit()

    conn.commit()
    ext._signal_transform.freeze()

    # ══════════════════════════════════════════════════════════════
    # Phase 1.5 [O]: Observe signal entropy variation
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 1.5 [O]: Observe signal entropy variation")
    print(f"{'─' * 72}")

    sig_rows = conn.execute(
        "SELECT window_id, spectral_entropy, fano_factor, synchrony_entropy, gradient_entropy, "
        "population_sparseness, temporal_autocorrelation, energy_concentration "
        "FROM v40_signal_entropy_ledger ORDER BY CAST(stage_k_id AS INTEGER)"
    ).fetchall()
    print(f"  Signal entropy rows: {len(sig_rows)} (7-channel)")
    for col, name in [(1, "spectral_H"), (2, "fano_H"), (3, "synchrony_H"), (4, "gradient_H")]:
        vals = [r[col] for r in sig_rows]
        mean_v = sum(vals)/len(vals)
        std_v = math.sqrt(sum((v-mean_v)**2 for v in vals)/len(vals))
        print(f"    {name:15s}: [{min(vals):.4f}, {max(vals):.4f}]  "
              f"mean={mean_v:.4f}  std={std_v:.4f}  cv={std_v/max(abs(mean_v),1e-10):.2%}")

    # Compare: old pipeline entropy vs new signal entropy coefficient of variation
    old_rows = conn.execute(
        "SELECT transport_entropy, candidate_fragment_entropy, origin_support_entropy, "
        "residual_accumulation_entropy FROM external_entropy_ledger"
    ).fetchall()
    print(f"\n  Pipeline entropy (old) — coefficient of variation:")
    for col, name in [(0, "transport_H"), (1, "candidate_H"), (2, "origin_H"), (3, "residual_H")]:
        vals = [r[col] for r in old_rows]
        mean_v = sum(vals)/len(vals)
        std_v = math.sqrt(sum((v-mean_v)**2 for v in vals)/len(vals))
        cv = std_v/max(abs(mean_v), 1e-10)
        print(f"    {name:15s}: cv={cv:.2%}  {'✓ varies' if cv > 0.05 else '✗ near-constant'}")

    # Masking counterevidence stats
    mask_count = conn.execute("SELECT COUNT(*) FROM masking_counterevidence_record").fetchone()[0]
    mask_support = conn.execute(
        "SELECT verdict, COUNT(*) FROM masking_counterevidence_record GROUP BY verdict"
    ).fetchall()
    print(f"\n  Masking counterevidence: {mask_count} records")
    for verdict, cnt in mask_support:
        print(f"    {verdict}: {cnt}")

    # Anomaly stats
    anom_rows = conn.execute(
        "SELECT anomaly_type, COUNT(*) FROM external_anomaly_ledger GROUP BY anomaly_type"
    ).fetchall()
    print(f"  Anomaly ledger:")
    for atype, cnt in anom_rows:
        print(f"    {atype}: {cnt}")

    # ══════════════════════════════════════════════════════════════
    # Phase 2 [P]: Build circuit + run with signal entropy
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 2 [P]: STDP circuit with signal entropy inputs")
    print(f"{'─' * 72}")

    circuit = build_signal_entropy_circuit(ext._signal_transform)
    print(f"  Circuit: {sum(len(l.neurons) for l in circuit.layers.values())} neurons, "
          f"{sum(len(l.bundles) for l in circuit.layers.values()) + len(circuit.inter_layer_bundles)} bundles")

    feature_names = ["sig_mean", "sig_std", "sig_peak_rate",
                     "sig_temporal_d", "sig_sync", "sig_range"]
    z_t_names = ["transition", "drift", "gamma_desync",
                 "xin_residual", "potential_disp", "churn", "magnitude"]

    circuit_z_t_by_stim = defaultdict(list)
    flat_z_t_by_stim = defaultdict(list)
    prev_activations = None
    prev_cells = None

    # Collect per-window signal entropy for injection
    sig_entropy_map = {}
    for row in sig_rows:
        sig_entropy_map[row[0]] = {
            "spectral_H": row[1],
            "fano_H": row[2],
            "synchrony_H": row[3],
            "gradient_H": row[4],
            "sparseness_H": row[5] if len(row) > 5 else 0.5,
            "autocorrelation_H": row[6] if len(row) > 6 else 0.5,
            "energy_H": row[7] if len(row) > 7 else 0.5,
        }

    # Also read masking survival rates per window
    mask_map = defaultdict(float)
    mask_rows = conn.execute(
        "SELECT hypothesis_id, verdict FROM masking_counterevidence_record"
    ).fetchall()
    for hyp_id, verdict in mask_rows:
        # Extract window k from hypothesis_id pattern
        mask_map[hyp_id] = 1.0 if verdict == "supports_confirmation" else -0.5

    for k in range(WINDOWS):
        cells = adapter.generate_cells(k)
        if not cells or prev_cells is None:
            prev_cells = cells
            continue

        sigs = [c.V_mean for c in cells]
        sf = ext._signal_transform.extract_signal_features(sigs)
        _, _, z_t_old = ext._signal_transform.transform(sigs)

        # Read REAL signal entropy from DB
        win_id = f"win_{adapter.adapter_name}_{k}"
        entropy_inputs = sig_entropy_map.get(win_id, {
            "spectral_H": 0.5, "fano_H": 0.5,
            "synchrony_H": 0.5, "gradient_H": 0.5,
            "sparseness_H": 0.5, "autocorrelation_H": 0.5,
            "energy_H": 0.5})

        # Compute circulation feedback amplification from DB history
        circ_gain = pe.compute_circulation_amplification(
            conn, run_id, k, win_id, lookback=5)

        # Apply gain to entropy inputs: amplify when entropy is falling
        # Cap amplified values to prevent flooding from high-range channels
        amplified_entropy = {}
        for key in entropy_inputs:
            g = circ_gain.get(key, 1.0)
            val = entropy_inputs[key] * g
            # Cap at 1.0 to prevent high-range features from flooding zones
            amplified_entropy[key] = min(1.0, val)

        # Step 1: Transport signal features → encoding
        signal_inputs = {feature_names[i]: sf[i] for i in range(len(sf))}
        circuit.transport(signal_inputs, "encoding")

        # Step 2: Transport AMPLIFIED signal entropy → signal_entropy layer
        circuit.transport(amplified_entropy, "signal_entropy")

        # Step 3: Propagate signal entropy → encoding via inter-layer bundles
        for bundle in circuit.inter_layer_bundles:
            src_layer = None
            for lid, l in circuit.layers.items():
                if bundle.source_neuron_ids[0] in l.neurons:
                    src_layer = l
                    break
            if src_layer is None:
                continue
            src_acts = [src_layer.neurons.get(sid, MetaNeuron("_","_")).activation
                        for sid in bundle.source_neuron_ids]
            tgt_acts = bundle.propagate(src_acts)
            for lid, l in circuit.layers.items():
                for j, tid in enumerate(bundle.target_neuron_ids):
                    if tid in l.neurons and j < len(tgt_acts):
                        l.neurons[tid].activation += tgt_acts[j]

        # Step 3.5: Contrastive gain modulation from higher-order features
        # Instead of directly injecting sparseness/autocorr/energy (which are
        # near-constant ~0.9 and flood zones), compute z-scores relative to
        # population mean and use as multiplicative gain on z_t neurons.
        # This extracts the DISCRIMINATIVE signal (scenes vs gratings).
        enc = circuit.layers["encoding"]
        ho_features = {
            "sparseness_H": ("churn", "drift"),      # scenes=0.85 < gratings=0.89
            "autocorrelation_H": ("transition", "drift"),  # scenes=0.43 > gratings=0.34
            "energy_H": ("magnitude", "potential_disp"),    # scenes=0.93 < gratings=0.97
        }
        # Population means from discovery diagnostic
        ho_means = {"sparseness_H": 0.88, "autocorrelation_H": 0.38, "energy_H": 0.95}
        ho_stds = {"sparseness_H": 0.05, "autocorrelation_H": 0.07, "energy_H": 0.03}
        for ho_name, (target_up, target_down) in ho_features.items():
            val = amplified_entropy.get(ho_name, ho_means.get(ho_name, 0.5))
            mean_v = ho_means[ho_name]
            std_v = max(ho_stds[ho_name], 1e-6)
            z = (val - mean_v) / std_v  # z-score: positive=above mean, negative=below
            # Clamp z to [-2, 2] to prevent extreme modulation
            z = max(-2.0, min(2.0, z))
            # Gain modulation: above-mean amplifies target_up, below amplifies target_down
            if target_up in enc.neurons:
                enc.neurons[target_up].activation *= (1.0 + 0.1 * z)
            if target_down in enc.neurons:
                enc.neurons[target_down].activation *= (1.0 - 0.1 * z)

        # Circulation gain amplification for starving neurons
        G = circ_gain.get("combined", 1.0)
        for nid in z_t_names:
            n = enc.neurons[nid]
            if n.calcium < n.target_rate * 0.5 and G > 1.01:
                n.activation *= G

        # Step 4: Lateral inhibition
        circuit._apply_lateral_inhibition(circuit.layers["encoding"])

        # Step 5: O/P/R/Xin
        circuit.observe()
        circuit.detect_circulations()
        if prev_activations:
            circuit.compute_xin(prev_activations)

        # Step 6: Learn (STDP + inter-layer)
        circuit.learn()
        for bundle in circuit.inter_layer_bundles:
            src_layer = None
            for lid, l in circuit.layers.items():
                if bundle.source_neuron_ids[0] in l.neurons:
                    src_layer = l
                    break
            if src_layer is None:
                continue
            pre_neurons = [src_layer.neurons[sid]
                           for sid in bundle.source_neuron_ids
                           if sid in src_layer.neurons]
            post_neurons = []
            for lid, l in circuit.layers.items():
                for tid in bundle.target_neuron_ids:
                    if tid in l.neurons:
                        post_neurons.append(l.neurons[tid])
            if pre_neurons and post_neurons:
                bundle.stdp_update(pre_neurons, post_neurons, 1.0)

        # Step 7: Maintain
        circuit.maintain()

        # Extract z_t
        enc = circuit.layers["encoding"]
        circuit_z_t = [enc.neurons[c].activation for c in z_t_names]

        si = k * 30
        if si < len(sub_ts):
            t_mid = sub_ts[si]
            for sn, es, ee in epochs:
                if es <= t_mid <= ee:
                    circuit_z_t_by_stim[sn].append(tuple(circuit_z_t))
                    break

        prev_activations = {nid: n.activation for nid, n in enc.neurons.items()}
        prev_cells = cells

    # ══════════════════════════════════════════════════════════════
    # Phase 3 [R]: Counter-evidence validation + discrimination
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 3 [R]: Discrimination + counter-evidence analysis")
    print(f"{'─' * 72}")

    stim_names = sorted(circuit_z_t_by_stim.keys())
    print(f"  Stimuli: {stim_names}")
    print(f"  Samples: {', '.join(f'{s}={len(circuit_z_t_by_stim[s])}' for s in stim_names)}")

    def compute_mean(z_list):
        n = len(z_list)
        dim = len(z_list[0])
        return tuple(sum(z[d] for z in z_list) / n for d in range(dim))

    circuit_means = {}
    for s in stim_names:
        if circuit_z_t_by_stim.get(s):
            circuit_means[s] = compute_mean(circuit_z_t_by_stim[s])

    print(f"\n  Circuit discrimination (signal entropy driven):")
    circuit_sims = []
    for i, s1 in enumerate(stim_names):
        for s2 in stim_names[i+1:]:
            if s1 in circuit_means and s2 in circuit_means:
                sim = cosine_sim(circuit_means[s1], circuit_means[s2])
                circuit_sims.append(sim)
                print(f"    cos({s1[:18]:18s}, {s2[:18]:18s}) = {sim:.6f}")

    avg_circuit = sum(circuit_sims) / max(len(circuit_sims), 1)

    print(f"\n  Per-dimension z_t profiles:")
    for s in stim_names:
        if s in circuit_means:
            vals = "  ".join(f"{v:.4f}" for v in circuit_means[s])
            print(f"    {s[:22]:22s}: [{vals}]")

    # Signal entropy bundle evolution
    print(f"\n  Signal entropy → z_t bundle evolution:")
    for b in circuit.inter_layer_bundles:
        if b.bundle_id.startswith("sigH_"):
            cond = getattr(b, '_conductance_history', 0.0)
            print(f"    {b.bundle_id:35s}: strength={b.bundle_strength:.4f}  "
                  f"conductance={cond:.4f}  inertia={b.bundle_inertia:.4f}")

    # Circulation amplification stats
    try:
        amp_rows = conn.execute(
            "SELECT gain_combined, entropy_slope_spectral, entropy_slope_fano "
            "FROM v40_circulation_amplification_ledger "
            "WHERE run_id=? ORDER BY CAST(stage_k_id AS INTEGER)",
            (run_id,)).fetchall()
        if amp_rows:
            gains_all = [r[0] for r in amp_rows]
            amplified = sum(1 for g in gains_all if g > 1.01)
            print(f"\n  Circulation amplification (from entropy ledger):")
            print(f"    Windows amplified: {amplified}/{len(gains_all)}")
            print(f"    Gain range: [{min(gains_all):.3f}, {max(gains_all):.3f}]  "
                  f"mean={sum(gains_all)/len(gains_all):.3f}")
    except Exception:
        pass

    # Homeostatic state: structural differentiation
    print(f"\n  Homeostatic differentiation (encoding layer):")
    for nid in z_t_names:
        n = circuit.layers["encoding"].neurons[nid]
        print(f"    {nid:18s}: threshold={n.threshold:.6f}  "
              f"calcium={n.calcium:.6f}  pre_trace={n.pre_trace:.4f}")

    # R-chain: which z_t dims have structural support?
    print(f"\n  R-chain: structural support per z_t dimension:")
    for nid in z_t_names:
        n = circuit.layers["encoding"].neurons[nid]
        # Dimension has support if: threshold adapted away from initial AND calcium > 0
        calcium_active = n.calcium > 0.001
        threshold_adapted = abs(n.threshold - 0.005) > 0.0001
        has_bundle_support = any(
            nid in b.target_neuron_ids and b.bundle_strength > 0.05
            for b in circuit.layers["encoding"].bundles + circuit.inter_layer_bundles
        )
        status = "✅" if (calcium_active or threshold_adapted) else "⚠️ weak"
        print(f"    {nid:18s}: ca={calcium_active}  thr_adapt={threshold_adapted}  "
              f"bundle={has_bundle_support}  → {status}")

    m = circuit.get_metrics()
    print(f"\n  Circuit: alive={m['alive_neurons']}/{m['total_neurons']}  "
          f"P={'✓' if m['p_circulation'] else '✗'}  "
          f"R={'✓' if m['r_circulation'] else '✗'}  "
          f"T={m['temperature']:.4f}  fruits={m['dormant_fruits']}")

    # Circulation measure (probability integral over all paths)
    circ_mu = getattr(circuit, '_circulation_measure', 0.0)
    all_cycles = getattr(circuit, '_all_cycle_measures', [])
    ghost_count = sum(len(getattr(l, '_ghost_bundles', []))
                      for l in circuit.layers.values())
    print(f"\n  Circulation measure μ(G) = {circ_mu:.6f}")
    print(f"    Active cycles: {len(all_cycles)}")
    if all_cycles:
        print(f"    P fraction: {all_cycles[0]['fraction']:.4f}")
        if len(all_cycles) > 1:
            print(f"    R fraction: {all_cycles[1]['fraction']:.4f}")
            print(f"    Secondary+: {sum(c['fraction'] for c in all_cycles[2:]):.4f}")
    print(f"    Ghost bundles: {ghost_count}")

    # ══════════════════════════════════════════════════════════════
    # Phase 4 [Xin]: Verdict + structural tension
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'=' * 72}")
    print("  Phase 4 [Xin]: VERDICT + remaining tension")
    print(f"{'=' * 72}")

    flat_avg = 0.999460  # known baseline from flat W_signal
    improved = avg_circuit < flat_avg
    print(f"  Flat baseline cosine: {flat_avg:.6f}")
    print(f"  Circuit avg cosine:   {avg_circuit:.6f}")
    print(f"  Improvement:          {flat_avg - avg_circuit:.6f}")
    print(f"  Discrimination:       {'✅ YES' if improved else '❌ NO'}")

    thresholds = [circuit.layers["encoding"].neurons[n].threshold for n in z_t_names]
    thr_std = math.sqrt(sum((t - sum(thresholds)/len(thresholds))**2 for t in thresholds)/len(thresholds))
    print(f"  Threshold diversity:  std={thr_std:.6f} {'✅' if thr_std > 0.0005 else '❌'}")

    # Count non-zero dimensions per stimulus
    active_dims = {}
    for s in stim_names:
        if s in circuit_means:
            active = sum(1 for v in circuit_means[s] if abs(v) > 0.001)
            active_dims[s] = active
    print(f"  Active dimensions:    {active_dims}")

    # Remaining Xin tension
    xin_total = sum(abs(v) for v in circuit._xin_tensions.values())
    print(f"  Xin total tension:    {xin_total:.4f}")
    print(f"  Activated fruits:     {len(circuit._activated_fruits)}")

    report = {
        "flat_avg_cosine": flat_avg,
        "circuit_avg_cosine": avg_circuit,
        "improvement": flat_avg - avg_circuit,
        "improved": improved,
        "threshold_diversity": thr_std,
        "active_dims": active_dims,
        "xin_tension": xin_total,
        "circuit_metrics": m,
        "signal_entropy_rows": len(sig_rows),
        "masking_records": mask_count,
    }
    rp = str(BASE / "db" / "v40_integrated_report.json")
    with open(rp, "w") as f_out:
        json.dump(report, f_out, indent=2, default=str)
    print(f"\n  DB:     {DB_PATH}")
    print(f"  Report: {rp}")
    print("=" * 72)

    conn.close()


if __name__ == "__main__":
    main()
===
#!/usr/bin/env python3
"""v40 Integrated Circuit — Full Pipeline + Signal Entropy + STDP + R-chain.

Holistic integration:
  1. Run full pipeline → writes ALL ledgers (entropy, anomaly, masking, transport)
  2. Write NEW v40_signal_entropy_ledger (spectral_H, fano, synchrony, gradient)
     — these actually vary across stimulus types unlike pipeline-structural entropy
  3. Read signal entropy + masking counterevidence from DB
  4. Feed into circuit: signal entropy as structural input neurons,
     masking survival rate as modulatory gain on z_t neurons
  5. STDP + homeostasis adapts structure based on measured quantities
  6. Compare discrimination with R-chain validation

The whole loop mirrors T/O/P/R/Xin:
  T = pipeline transport → DB
  O = observe signal entropy variation
  P = primary discrimination path (STDP circuit)
  R = counter-evidence from masking layer → refute weak dimensions
  Xin = residual tension → structural adjustment
"""
import sys, os, math, json, sqlite3
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "src"))
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "engines"))

from allen_brain_adapter import AllenBrainAdapter
from physics_source_adapter import PhysicsSourceAdapter
from motion_recognition_engine import FeatureExtractor, BayesianMotionRecognizer
from hebbian_circuit import (HebbianCircuit, CircuitLayer, MetaNeuron,
                             MetaSynapticBundle, build_circuit_from_signal_transform)
import pipeline_engine as pe

DB_PATH = str(BASE / "db" / "v40_integrated.db")


def build_signal_entropy_circuit(signal_transform) -> HebbianCircuit:
    """Build circuit with sensitivity zone differentiation.

    Architecture — differentiated sensitivity zones:
    ────────────────────────────────────────────────────────────────
    Each entropy channel gets its OWN receptive field (zone).
    All zones are simultaneously activated as the circulation baseline.
    This prevents any single dominant dimension from killing
    signal-source information from other channels.

    signal_entropy_layer: 4 neurons (spectral_H, fano_H, synchrony_H, gradient_H)
          │
          ├─→ zone_spectral (2 intermediate neurons) ─→ z_t targets
          ├─→ zone_fano (2 intermediate neurons) ─→ z_t targets
          ├─→ zone_synchrony (2 intermediate neurons) ─→ z_t targets
          └─→ zone_gradient (2 intermediate neurons) ─→ z_t targets
          │
    encoding_layer: 6 signal features → 7 z_t costs
          │
    column_layer: consolidation

    Within each zone:
      - Dedicated intermediate neurons transform entropy into
        zone-specific activation patterns
      - Each zone has its OWN feedback loop (closed circulation per zone)
      - STDP operates per-zone, allowing independent weight adaptation

    Cross-zone integration:
      - All zones project to shared z_t targets
      - Divisive normalization operates across z_t, not within zones
      - This creates proportional contribution, not winner-take-all

    The resulting μ(G) contains:
      - Per-zone circulations (local, always active at baseline)
      - Cross-zone circulations (global, emerge from STDP convergence)
      - The genuine P is the circulation that persists when any
        single zone is masked (validated by R-chain counterevidence)
    ────────────────────────────────────────────────────────────────
    """
    circuit = build_circuit_from_signal_transform(signal_transform)

    # Signal entropy input layer
    entropy_layer = CircuitLayer(layer_id="signal_entropy")
    entropy_names = ["spectral_H", "fano_H", "synchrony_H", "gradient_H",
                     "sparseness_H", "autocorrelation_H", "energy_H"]
    for name in entropy_names:
        n = entropy_layer.add_neuron(name)
        n.target_rate = 0.2
        n.threshold = 0.001
        n.energy = 1000.0  # input neurons: externally driven, should never die
    circuit.layers["signal_entropy"] = entropy_layer

    z_t_names = ["transition", "drift", "gamma_desync",
                 "xin_residual", "potential_disp", "churn", "magnitude"]

    # ── Create sensitivity zones ──
    # Each zone: entropy channel → 2 intermediate neurons → z_t targets
    # The intermediates allow per-zone STDP to learn independent patterns

    zone_specs = {
        "spectral": {
            "source": ["spectral_H"],
            "intermediates": ["zone_spec_mag", "zone_spec_pot"],
            "targets": ["magnitude", "potential_disp"],
        },
        "fano": {
            "source": ["fano_H"],
            "intermediates": ["zone_fano_churn", "zone_fano_drift"],
            "targets": ["churn", "drift"],
        },
        "synchrony": {
            "source": ["synchrony_H"],
            "intermediates": ["zone_sync_gamma", "zone_sync_trans"],
            "targets": ["gamma_desync", "transition"],
        },
        "gradient": {
            "source": ["gradient_H"],
            "intermediates": ["zone_grad_xin", "zone_grad_trans"],
            "targets": ["xin_residual", "transition"],
        },
    }

    # Higher-order features: parallel bundles to existing zone intermediates
    # These AUGMENT the existing zones without adding neurons or zones
    higher_order_pairs = [
        # (source_H, target_zone_intermediates, name)
        ("energy_H",          ["zone_spec_mag", "zone_spec_pot"], "energy_to_spectral"),
        ("sparseness_H",      ["zone_fano_churn", "zone_fano_drift"], "sparseness_to_fano"),
        ("autocorrelation_H", ["zone_grad_xin", "zone_grad_trans"], "autocorr_to_gradient"),
    ]

    # v40.6: Zone-differentiated target_rates based on entropy channel CV
    zone_target_rates = {
        "spectral": 0.05,    # cv=24.6% → moderate variability → moderate target
        "fano": 0.02,        # cv=56.2% → high variability → low target (sparse responder)
        "synchrony": 0.06,   # cv=29.8% → moderate → slightly higher
        "gradient": 0.08,    # cv=19.3% → low variability → high target (tonic responder)
    }

    # v40.6: Per-dimension z_t target_rates based on zone coverage frequency
    z_t_target_rates = {
        "transition": 0.04,     # covered by synchrony + gradient
        "drift": 0.03,          # covered by fano alone
        "gamma_desync": 0.04,   # covered by synchrony alone
        "xin_residual": 0.03,   # covered by gradient alone
        "potential_disp": 0.02, # covered by spectral alone
        "churn": 0.03,          # covered by fano alone
        "magnitude": 0.02,      # covered by spectral alone
    }

    # Apply z_t target_rates to z_t neurons already in encoding layer
    enc_layer = circuit.layers["encoding"]
    for zt_name, zt_rate in z_t_target_rates.items():
        if zt_name in enc_layer.neurons:
            enc_layer.neurons[zt_name].target_rate = zt_rate

    for zone_name, spec in zone_specs.items():
        # Add intermediate neurons to encoding layer
        enc = circuit.layers["encoding"]
        zt_rate = zone_target_rates.get(zone_name, 0.05)
        for iname in spec["intermediates"]:
            n = enc.add_neuron(iname)
            n.target_rate = zt_rate  # v40.6: zone-differentiated target
            n.threshold = 0.0001    # very low: always respond to entropy
            n.energy = 1000.0       # modulatory neurons should never die

        sources = spec["source"]  # list of entropy channel names

        # Bundle 1: entropy sources → intermediate neurons
        b_in = MetaSynapticBundle(
            bundle_id=f"sigH_{zone_name}_to_zone",
            source_neuron_ids=sources,
            target_neuron_ids=spec["intermediates"],
            bundle_inertia=0.5, learning_rule="stdp")
        b_in.init_weights()
        # Higher initial weights for zone input — entropy should pass through
        for i in range(len(b_in.weights)):
            for j in range(len(b_in.weights[i])):
                b_in.weights[i][j] = 0.3
        circuit.inter_layer_bundles.append(b_in)

        # Bundle 2: intermediate neurons → z_t targets (within encoding)
        b_out = enc.add_bundle(
            source_ids=spec["intermediates"],
            target_ids=spec["targets"])
        b_out.bundle_id = f"zone_{zone_name}_to_zt"
        b_out.learning_rule = "stdp"
        # Initial weights: moderate, to be shaped by STDP
        for i in range(len(b_out.weights)):
            for j in range(len(b_out.weights[i])):
                b_out.weights[i][j] = 0.2

        # Bundle 3: z_t targets → entropy sources (feedback loop)
        # This closes the per-zone circulation, making each zone
        # a self-contained T/O/P/R/Xin mini-loop
        b_fb = MetaSynapticBundle(
            bundle_id=f"zone_{zone_name}_feedback",
            source_neuron_ids=spec["targets"],
            target_neuron_ids=sources,
            bundle_inertia=0.8, learning_rule="oja")
        b_fb.init_weights()
        for i in range(len(b_fb.weights)):
            for j in range(len(b_fb.weights[i])):
                b_fb.weights[i][j] = 0.05  # weak feedback initially
        circuit.inter_layer_bundles.append(b_fb)

    # Higher-order features (sparseness, autocorrelation, energy) are applied
    # as contrastive gain modulation in Step 3.5 of the circuit loop, not as
    # parallel bundles. This prevents range-mismatch flooding.

    # ── v40.9: CPG Bio-Substrate Layer ──
    # Central Pattern Generator — self-sustaining oscillatory layer.
    # Provides baseline neural drive to prevent thermal death.
    #
    # Architecture: two half-center pairs (fast + slow)
    # DEGRADED: CPG pacemaker neuron intrinsic bursting → reciprocal inhibition
    # degraded_from = "CPG_half_center_reciprocal_inhibition"
    #
    # This layer is a bottom-level input source with the same spatiotemporal
    # measurement framework as signal_entropy. It is prepared for real signal
    # source binding (compute metrics, hardware telemetry) through the standard
    # inter-layer bundle interface. Its dynamics represent structural material
    # movement — currently proxied as reciprocal inhibition oscillation.
    cpg_layer = CircuitLayer(layer_id="cpg")
    cpg_neurons = {
        # Fast pair (theta-like, ~8 tick period)
        "cpg_fast_a": {"target_rate": 0.1, "threshold": 0.005},
        "cpg_fast_b": {"target_rate": 0.1, "threshold": 0.005},
        # Slow pair (cardio-like, ~20 tick period)
        "cpg_slow_a": {"target_rate": 0.04, "threshold": 0.003},
        "cpg_slow_b": {"target_rate": 0.04, "threshold": 0.003},
    }
    for nid, params in cpg_neurons.items():
        n = cpg_layer.add_neuron(nid)
        n.target_rate = params["target_rate"]
        n.threshold = params["threshold"]
        n.energy = 1000.0  # intrinsic oscillator: externally stable
        # Initialize with asymmetric activation to break symmetry
        # (otherwise both pairs start equal and never oscillate)
        if nid.endswith("_a"):
            n.activation = 0.03
        else:
            n.activation = 0.0
    circuit.layers["cpg"] = cpg_layer

    # Reciprocal inhibition bundles (intra-CPG)
    # fast pair: A ←→ B
    b_fast_ab = cpg_layer.add_bundle(
        source_ids=["cpg_fast_a"], target_ids=["cpg_fast_b"])
    b_fast_ab.bundle_id = "cpg_fast_a_to_b"
    for i in range(len(b_fast_ab.weights)):
        for j in range(len(b_fast_ab.weights[i])):
            b_fast_ab.weights[i][j] = -0.3  # inhibitory

    b_fast_ba = cpg_layer.add_bundle(
        source_ids=["cpg_fast_b"], target_ids=["cpg_fast_a"])
    b_fast_ba.bundle_id = "cpg_fast_b_to_a"
    for i in range(len(b_fast_ba.weights)):
        for j in range(len(b_fast_ba.weights[i])):
            b_fast_ba.weights[i][j] = -0.3

    # slow pair: A ←→ B
    b_slow_ab = cpg_layer.add_bundle(
        source_ids=["cpg_slow_a"], target_ids=["cpg_slow_b"])
    b_slow_ab.bundle_id = "cpg_slow_a_to_b"
    for i in range(len(b_slow_ab.weights)):
        for j in range(len(b_slow_ab.weights[i])):
            b_slow_ab.weights[i][j] = -0.2

    b_slow_ba = cpg_layer.add_bundle(
        source_ids=["cpg_slow_b"], target_ids=["cpg_slow_a"])
    b_slow_ba.bundle_id = "cpg_slow_b_to_a"
    for i in range(len(b_slow_ba.weights)):
        for j in range(len(b_slow_ba.weights[i])):
            b_slow_ba.weights[i][j] = -0.2

    # ── Visceral zone in encoding layer ──
    # visc_rhythm:   receives fast CPG output → PRP/calcium maintenance
    # visc_baseline: receives slow CPG output → metabolic baseline
    enc = circuit.layers["encoding"]
    for visc_id, visc_rate in [("visc_rhythm", 0.05), ("visc_baseline", 0.02)]:
        vn = enc.add_neuron(visc_id)
        vn.target_rate = visc_rate
        vn.threshold = 0.001  # low: should respond to CPG drive
        vn.energy = 1000.0    # visceral neurons are structurally stable

    # Inter-layer bundles: CPG → encoding visceral zone
    b_cpg_rhythm = MetaSynapticBundle(
        bundle_id="cpg_to_rhythm",
        source_neuron_ids=["cpg_fast_a", "cpg_fast_b"],
        target_neuron_ids=["visc_rhythm"],
        bundle_inertia=1.0, learning_rule="stdp")
    b_cpg_rhythm.init_weights()
    for i in range(len(b_cpg_rhythm.weights)):
        for j in range(len(b_cpg_rhythm.weights[i])):
            b_cpg_rhythm.weights[i][j] = 0.15
    circuit.inter_layer_bundles.append(b_cpg_rhythm)

    b_cpg_baseline = MetaSynapticBundle(
        bundle_id="cpg_to_baseline",
        source_neuron_ids=["cpg_slow_a", "cpg_slow_b"],
        target_neuron_ids=["visc_baseline"],
        bundle_inertia=1.0, learning_rule="stdp")
    b_cpg_baseline.init_weights()
    for i in range(len(b_cpg_baseline.weights)):
        for j in range(len(b_cpg_baseline.weights[i])):
            b_cpg_baseline.weights[i][j] = 0.1
    circuit.inter_layer_bundles.append(b_cpg_baseline)

    return circuit


def cosine_sim(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) + 1e-12
    nb = math.sqrt(sum(x * x for x in b)) + 1e-12
    return dot / (na * nb)


def main():
    print("=" * 72)
    print("v40 INTEGRATED: Signal Entropy + STDP + R-chain Validation")
    print("=" * 72)

    # ══════════════════════════════════════════════════════════════
    # Phase 1: T — Full pipeline → all ledgers
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 1 [T]: Pipeline transport → all ledgers")
    print(f"{'─' * 72}")

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    pe.apply_migrations(conn)
    conn.commit()

    # v40.9: Data source selection — allen (real) or physics (3D simulation)
    data_source = os.environ.get("DATA_SOURCE", "allen")
    if data_source == "physics":
        adapter = PhysicsSourceAdapter(
            n_particles=50,
            n_windows=100,
            seed=42,
            split_role="all",
        )
        print(f"  Data source: PHYSICS (3D spring-repulsion LIF)")
    else:
        adapter = AllenBrainAdapter(split_role="all")
        print(f"  Data source: Allen Brain Observatory (real calcium imaging)")
    run_id = "v40_integrated_001"
    pe.register_adapter(conn, run_id, adapter)

    ext = FeatureExtractor()
    rec = BayesianMotionRecognizer(prior_var=1.0)
    prev_cells = None
    WINDOWS = adapter.total_windows

    # Load stimulus epochs (Allen-specific, skip for physics)
    if data_source != "physics":
        import h5py
        nwb_path = str(BASE / "data/allen_brain/ophys_experiment_data/500964514.nwb")
        f = h5py.File(nwb_path, "r")
        pres = f["stimulus"]["presentation"]
        epochs = []
        for sn in pres.keys():
            ds = pres[sn]
            if "timestamps" in ds:
                ts = ds["timestamps"][:]
                if len(ts) >= 2:
                    clean = sn.replace("_stimulus", "")
                    block_start = ts[0]
                    prev_t = ts[0]
                    for i in range(1, len(ts)):
                        if ts[i] - prev_t > 30:
                            epochs.append((clean, float(block_start), float(prev_t)))
                            block_start = ts[i]
                        prev_t = ts[i]
                    epochs.append((clean, float(block_start), float(prev_t)))
        epochs.sort(key=lambda x: x[2] - x[1])
        fl_ts = f["processing"]["brain_observatory_pipeline"]["DfOverF"]["imaging_plane_1"]["timestamps"][:]
        sub_ts = fl_ts[::38][:3003]
        f.close()

    for k in range(WINDOWS):
        cells = adapter.generate_cells(k)
        if not cells:
            continue

        env = adapter.make_envelope(k)
        env_id = pe.write_envelope(conn, run_id, env)
        pw_id = pe.write_process_window(conn, run_id, adapter, k, env_id,
                                         len(cells), ["ingest", "transport"])
        uid_map = pe.write_cells(conn, run_id, adapter, k, cells)

        if prev_cells is not None:
            pe.write_transport(conn, run_id, adapter, k, prev_cells, cells)

        hyps = pe.write_hypotheses(conn, run_id, adapter, k, cells)
        xi_id = pe.write_xi(conn, run_id, adapter, k, hyps, cells[:5])

        if prev_cells is not None:
            disps = {}
            for i in range(min(len(prev_cells), len(cells))):
                dx = cells[i].x - prev_cells[i].x
                dy = cells[i].y - prev_cells[i].y
                disps[i] = math.sqrt(dx*dx + dy*dy)
            feats = ext.extract(
                {i: (c.x, c.y) for i, c in enumerate(prev_cells)},
                {i: (c.x, c.y) for i, c in enumerate(cells)},
                disps, signal_values=[c.V_mean for c in cells])
            pred, _, _ = rec.classify(feats)
            rec.learn(feats, pred)

        # Write ALL ledgers
        pe.write_external_ledgers(conn, run_id, adapter, k, env, cells)
        # Write v40 SIGNAL entropy (the key new ledger)
        pe.write_signal_entropy_ledger(conn, run_id, adapter, k, cells)

        prev_cells = cells
        if k % 20 == 0:
            conn.commit()

    conn.commit()
    ext._signal_transform.freeze()

    # ══════════════════════════════════════════════════════════════
    # Phase 1.5 [O]: Observe signal entropy variation
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 1.5 [O]: Observe signal entropy variation")
    print(f"{'─' * 72}")

    sig_rows = conn.execute(
        "SELECT window_id, spectral_entropy, fano_factor, synchrony_entropy, gradient_entropy, "
        "population_sparseness, temporal_autocorrelation, energy_concentration "
        "FROM v40_signal_entropy_ledger ORDER BY CAST(stage_k_id AS INTEGER)"
    ).fetchall()
    print(f"  Signal entropy rows: {len(sig_rows)} (7-channel)")
    for col, name in [(1, "spectral_H"), (2, "fano_H"), (3, "synchrony_H"), (4, "gradient_H")]:
        vals = [r[col] for r in sig_rows]
        mean_v = sum(vals)/len(vals)
        std_v = math.sqrt(sum((v-mean_v)**2 for v in vals)/len(vals))
        print(f"    {name:15s}: [{min(vals):.4f}, {max(vals):.4f}]  "
              f"mean={mean_v:.4f}  std={std_v:.4f}  cv={std_v/max(abs(mean_v),1e-10):.2%}")

    # Compare: old pipeline entropy vs new signal entropy coefficient of variation
    old_rows = conn.execute(
        "SELECT transport_entropy, candidate_fragment_entropy, origin_support_entropy, "
        "residual_accumulation_entropy FROM external_entropy_ledger"
    ).fetchall()
    print(f"\n  Pipeline entropy (old) — coefficient of variation:")
    for col, name in [(0, "transport_H"), (1, "candidate_H"), (2, "origin_H"), (3, "residual_H")]:
        vals = [r[col] for r in old_rows]
        mean_v = sum(vals)/len(vals)
        std_v = math.sqrt(sum((v-mean_v)**2 for v in vals)/len(vals))
        cv = std_v/max(abs(mean_v), 1e-10)
        print(f"    {name:15s}: cv={cv:.2%}  {'✓ varies' if cv > 0.05 else '✗ near-constant'}")

    # Masking counterevidence stats
    mask_count = conn.execute("SELECT COUNT(*) FROM masking_counterevidence_record").fetchone()[0]
    mask_support = conn.execute(
        "SELECT verdict, COUNT(*) FROM masking_counterevidence_record GROUP BY verdict"
    ).fetchall()
    print(f"\n  Masking counterevidence: {mask_count} records")
    for verdict, cnt in mask_support:
        print(f"    {verdict}: {cnt}")

    # Anomaly stats
    anom_rows = conn.execute(
        "SELECT anomaly_type, COUNT(*) FROM external_anomaly_ledger GROUP BY anomaly_type"
    ).fetchall()
    print(f"  Anomaly ledger:")
    for atype, cnt in anom_rows:
        print(f"    {atype}: {cnt}")

    # ══════════════════════════════════════════════════════════════
    # Phase 1.6 [O]: Dynamic contrastive gain statistics from DB
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 1.6 [O]: Dynamic contrastive gain statistics")
    print(f"{'─' * 72}")

    ho_channels = ["population_sparseness", "temporal_autocorrelation", "energy_concentration"]
    ho_stats = {}
    for col_name in ho_channels:
        vals = conn.execute(
            f"SELECT {col_name} FROM v40_signal_entropy_ledger WHERE run_id=?",
            (run_id,)
        ).fetchall()
        vals = [v[0] for v in vals if v[0] is not None]
        if vals:
            mu = sum(vals) / len(vals)
            std = math.sqrt(sum((v - mu)**2 for v in vals) / len(vals))
        else:
            mu, std = 0.5, 0.1
        # Map column name to ho_key
        ho_key_map = {
            "population_sparseness": "sparseness_H",
            "temporal_autocorrelation": "autocorrelation_H",
            "energy_concentration": "energy_H",
        }
        ho_key = ho_key_map[col_name]
        ho_stats[ho_key] = {"mean": mu, "std": max(std, 1e-6)}
        print(f"    {ho_key:22s}: μ={mu:.6f}  σ={std:.6f}")

    # ══════════════════════════════════════════════════════════════
    # Phase 1.7 [O]: Temporal resolution audit + bootstrap augmentation
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 1.7 [O]: Temporal resolution audit")
    print(f"{'─' * 72}")

    # Identify stimulus for each window via epoch matching
    stim_window_counts = defaultdict(int)
    stim_window_ids = defaultdict(list)
    for row in sig_rows:
        win_id_check = row[0]
        # Extract k from window_id pattern: win_<adapter>_<k>
        parts = win_id_check.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            k_val = int(parts[1])
            if data_source == "physics":
                # Physics: use adapter's built-in stimulus schedule
                stim_label = adapter._get_stim_for_window(k_val)
                stim_window_counts[stim_label] += 1
                stim_window_ids[stim_label].append(win_id_check)
            else:
                # Allen: match window time to NWB epoch
                si = k_val * 30
                if si < len(sub_ts):
                    t_mid = sub_ts[si]
                    for sn, es, ee in epochs:
                        if es <= t_mid <= ee:
                            stim_window_counts[sn] += 1
                            stim_window_ids[sn].append(win_id_check)
                            break

    MIN_WINDOWS = 20
    for stim, count in sorted(stim_window_counts.items()):
        if count < MIN_WINDOWS:
            print(f"  ⚠ {stim}: {count} windows < {MIN_WINDOWS} → augmenting")
            aug_rows = pe.compute_temporal_resolution_augmentation(
                conn, run_id, stim, stim_window_ids[stim],
                target_windows=MIN_WINDOWS)
            print(f"    → generated {aug_rows} bootstrap windows")
            # Refresh sig_rows after augmentation
            sig_rows = conn.execute(
                "SELECT window_id, spectral_entropy, fano_factor, synchrony_entropy, gradient_entropy, "
                "population_sparseness, temporal_autocorrelation, energy_concentration "
                "FROM v40_signal_entropy_ledger WHERE run_id=? ORDER BY CAST(stage_k_id AS INTEGER)",
                (run_id,)
            ).fetchall()
        else:
            print(f"  ✓ {stim}: {count} windows ≥ {MIN_WINDOWS}")

    # Rebuild sig_entropy_map with augmented data
    sig_entropy_map = {}
    for row in sig_rows:
        sig_entropy_map[row[0]] = {
            "spectral_H": row[1],
            "fano_H": row[2],
            "synchrony_H": row[3],
            "gradient_H": row[4],
            "sparseness_H": row[5] if len(row) > 5 else 0.5,
            "autocorrelation_H": row[6] if len(row) > 6 else 0.5,
            "energy_H": row[7] if len(row) > 7 else 0.5,
        }

    # ══════════════════════════════════════════════════════════════
    # Phase 2 [P]: Build circuit + run with signal entropy
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 2 [P]: STDP circuit with signal entropy inputs")
    print(f"{'─' * 72}")

    circuit = build_signal_entropy_circuit(ext._signal_transform)
    print(f"  Circuit: {sum(len(l.neurons) for l in circuit.layers.values())} neurons, "
          f"{sum(len(l.bundles) for l in circuit.layers.values()) + len(circuit.inter_layer_bundles)} bundles")

    feature_names = ["sig_mean", "sig_std", "sig_peak_rate",
                     "sig_temporal_d", "sig_sync", "sig_range"]
    z_t_names = ["transition", "drift", "gamma_desync",
                 "xin_residual", "potential_disp", "churn", "magnitude"]

    circuit_z_t_by_stim = defaultdict(list)
    flat_z_t_by_stim = defaultdict(list)
    prev_activations = None
    prev_cells = None

    # Collect per-window signal entropy for injection
    sig_entropy_map = {}
    for row in sig_rows:
        sig_entropy_map[row[0]] = {
            "spectral_H": row[1],
            "fano_H": row[2],
            "synchrony_H": row[3],
            "gradient_H": row[4],
            "sparseness_H": row[5] if len(row) > 5 else 0.5,
            "autocorrelation_H": row[6] if len(row) > 6 else 0.5,
            "energy_H": row[7] if len(row) > 7 else 0.5,
        }

    # Also read masking survival rates per window
    mask_map = defaultdict(float)
    mask_rows = conn.execute(
        "SELECT hypothesis_id, verdict FROM masking_counterevidence_record"
    ).fetchall()
    for hyp_id, verdict in mask_rows:
        # Extract window k from hypothesis_id pattern
        mask_map[hyp_id] = 1.0 if verdict == "supports_confirmation" else -0.5

    for k in range(WINDOWS):
        cells = adapter.generate_cells(k)
        if not cells or prev_cells is None:
            prev_cells = cells
            continue

        sigs = [c.V_mean for c in cells]
        sf = ext._signal_transform.extract_signal_features(sigs)
        _, _, z_t_old = ext._signal_transform.transform(sigs)

        # Read REAL signal entropy from DB
        win_id = f"win_{adapter.adapter_name}_{k}"
        entropy_inputs = sig_entropy_map.get(win_id, {
            "spectral_H": 0.5, "fano_H": 0.5,
            "synchrony_H": 0.5, "gradient_H": 0.5,
            "sparseness_H": 0.5, "autocorrelation_H": 0.5,
            "energy_H": 0.5})

        # Compute circulation feedback amplification from DB history
        circ_gain = pe.compute_circulation_amplification(
            conn, run_id, k, win_id, lookback=5)

        # Apply gain to entropy inputs: amplify when entropy is falling
        # Cap amplified values to prevent flooding from high-range channels
        amplified_entropy = {}
        for key in entropy_inputs:
            g = circ_gain.get(key, 1.0)
            val = entropy_inputs[key] * g
            # Cap at 1.0 to prevent high-range features from flooding zones
            amplified_entropy[key] = min(1.0, val)

        # Step 1: Transport signal features → encoding
        signal_inputs = {feature_names[i]: sf[i] for i in range(len(sf))}
        circuit.transport(signal_inputs, "encoding")

        # Step 2: Transport AMPLIFIED signal entropy → signal_entropy layer
        circuit.transport(amplified_entropy, "signal_entropy")

        # Step 3: Propagate signal entropy → encoding via inter-layer bundles
        for bundle in circuit.inter_layer_bundles:
            src_layer = None
            for lid, l in circuit.layers.items():
                if bundle.source_neuron_ids[0] in l.neurons:
                    src_layer = l
                    break
            if src_layer is None:
                continue
            src_acts = [src_layer.neurons.get(sid, MetaNeuron("_","_")).activation
                        for sid in bundle.source_neuron_ids]
            tgt_acts = bundle.propagate(src_acts)
            for lid, l in circuit.layers.items():
                for j, tid in enumerate(bundle.target_neuron_ids):
                    if tid in l.neurons and j < len(tgt_acts):
                        l.neurons[tid].activation += tgt_acts[j]

        # Step 3.5: Contrastive gain modulation from higher-order features
        # Instead of directly injecting sparseness/autocorr/energy (which are
        # near-constant ~0.9 and flood zones), compute z-scores relative to
        # population mean and use as multiplicative gain on z_t neurons.
        # This extracts the DISCRIMINATIVE signal (scenes vs gratings).
        enc = circuit.layers["encoding"]
        ho_features = {
            "sparseness_H": ("churn", "drift"),      # scenes=0.85 < gratings=0.89
            "autocorrelation_H": ("transition", "drift"),  # scenes=0.43 > gratings=0.34
            "energy_H": ("magnitude", "potential_disp"),    # scenes=0.93 < gratings=0.97
        }
        # v40.6: Population means from DB (computed in Phase 1.6), not hardcoded
        for ho_name, (target_up, target_down) in ho_features.items():
            val = amplified_entropy.get(ho_name, 0.5)
            stats = ho_stats.get(ho_name, {"mean": 0.5, "std": 0.1})
            mean_v = stats["mean"]
            std_v = stats["std"]
            z = (val - mean_v) / std_v  # z-score: positive=above mean, negative=below
            # Clamp z to [-2, 2] to prevent extreme modulation
            z = max(-2.0, min(2.0, z))
            # Gain modulation: above-mean amplifies target_up, below amplifies target_down
            if target_up in enc.neurons:
                enc.neurons[target_up].activation *= (1.0 + 0.1 * z)
            if target_down in enc.neurons:
                enc.neurons[target_down].activation *= (1.0 - 0.1 * z)

        # Circulation gain amplification for starving neurons
        G = circ_gain.get("combined", 1.0)
        for nid in z_t_names:
            n = enc.neurons[nid]
            if n.calcium < n.target_rate * 0.5 and G > 1.01:
                n.activation *= G

        # Step 4: Lateral inhibition
        circuit._apply_lateral_inhibition(circuit.layers["encoding"])

        # Step 5: O/P/R/Xin
        circuit.observe()
        circuit.detect_circulations()
        if prev_activations:
            circuit.compute_xin(prev_activations)

        # Step 6: Learn (STDP + inter-layer)
        circuit.learn()
        for bundle in circuit.inter_layer_bundles:
            src_layer = None
            for lid, l in circuit.layers.items():
                if bundle.source_neuron_ids[0] in l.neurons:
                    src_layer = l
                    break
            if src_layer is None:
                continue
            pre_neurons = [src_layer.neurons[sid]
                           for sid in bundle.source_neuron_ids
                           if sid in src_layer.neurons]
            post_neurons = []
            for lid, l in circuit.layers.items():
                for tid in bundle.target_neuron_ids:
                    if tid in l.neurons:
                        post_neurons.append(l.neurons[tid])
            if pre_neurons and post_neurons:
                bundle.stdp_update(pre_neurons, post_neurons, 1.0)

        # Step 7: Maintain
        circuit.maintain()

        # Extract z_t
        enc = circuit.layers["encoding"]
        circuit_z_t = [enc.neurons[c].activation for c in z_t_names]

        si = k * 30
        if data_source == "physics":
            # Physics adapter: stimulus label is embedded in cell metadata
            if cells:
                stim_label = cells[0].source_signal_refs.get("stimulus", "unknown")
                circuit_z_t_by_stim[stim_label].append(tuple(circuit_z_t))
        else:
            # Allen adapter: match window time to NWB epoch
            if si < len(sub_ts):
                t_mid = sub_ts[si]
                for sn, es, ee in epochs:
                    if es <= t_mid <= ee:
                        circuit_z_t_by_stim[sn].append(tuple(circuit_z_t))
                        break

        prev_activations = {nid: n.activation for nid, n in enc.neurons.items()}
        prev_cells = cells

    # ── B.3: Inject synthetic bootstrap windows into circuit ──
    # For starved stimuli, run additional circuit ticks with synthetic entropy
    # STDP weight is attenuated: real_windows / total_windows
    syn_windows = [row for row in sig_rows
                   if row[0].startswith("syn_")]
    if syn_windows:
        print(f"\n  Injecting {len(syn_windows)} synthetic windows into circuit...")
        for syn_row in syn_windows:
            syn_win_id = syn_row[0]
            entropy_inputs = {
                "spectral_H": syn_row[1],
                "fano_H": syn_row[2],
                "synchrony_H": syn_row[3],
                "gradient_H": syn_row[4],
                "sparseness_H": syn_row[5] if len(syn_row) > 5 else 0.5,
                "autocorrelation_H": syn_row[6] if len(syn_row) > 6 else 0.5,
                "energy_H": syn_row[7] if len(syn_row) > 7 else 0.5,
            }

            # Transport synthetic entropy → signal_entropy layer → zone intermediates
            circuit.transport(entropy_inputs, "signal_entropy")

            # Forward-propagate inter-layer bundles (signal_entropy → encoding)
            for bundle in circuit.inter_layer_bundles:
                src_layer = None
                for lid, l in circuit.layers.items():
                    if bundle.source_neuron_ids[0] in l.neurons:
                        src_layer = l
                        break
                if src_layer is None:
                    continue
                src_acts = [src_layer.neurons.get(sid, MetaNeuron("_","_")).activation
                            for sid in bundle.source_neuron_ids]
                tgt_acts = bundle.propagate(src_acts)
                for lid, l in circuit.layers.items():
                    for j, tid in enumerate(bundle.target_neuron_ids):
                        if tid in l.neurons and j < len(tgt_acts):
                            l.neurons[tid].activation += tgt_acts[j]

            # v40.6: Also inject z_t from entropy directly, proportional to
            # how much each z_t dimension is informative for this stimulus.
            # Different stimuli have different entropy profiles → different z_t patterns
            enc = circuit.layers["encoding"]
            entropy_to_zt_map = {
                "transition": ("synchrony_H", "gradient_H"),   # temporal structure
                "drift": ("fano_H", "sparseness_H"),          # variability metrics
                "gamma_desync": ("synchrony_H",),              # synchronization
                "xin_residual": ("gradient_H", "energy_H"),    # spatial gradient
                "potential_disp": ("spectral_H",),             # spectral content
                "churn": ("fano_H", "autocorrelation_H"),      # temporal dynamics
                "magnitude": ("energy_H", "spectral_H"),       # signal strength
            }
            for zt_name, entropy_keys in entropy_to_zt_map.items():
                if zt_name in enc.neurons:
                    # Use z-scored entropy: how much this stimulus DEVIATES from population
                    zt_val = 0.0
                    for k in entropy_keys:
                        raw = entropy_inputs.get(k, 0.5)
                        stats = ho_stats.get(k, None)
                        if stats:
                            z = (raw - stats["mean"]) / max(stats["std"], 1e-6)
                        else:
                            z = 0.0
                        zt_val += z
                    zt_val /= len(entropy_keys)
                    # Scale: z-scored values → small activation
                    # Positive z = above population mean → more activation
                    zt_val = max(0.0, zt_val * 0.01)  # only positive deviations
                    if zt_val > 0:
                        enc.neurons[zt_name].activate(zt_val)

            # Contrastive gain modulation for synthetic windows (same as Step 3.5)
            enc = circuit.layers["encoding"]
            ho_features = {
                "sparseness_H": ("churn", "drift"),
                "autocorrelation_H": ("transition", "drift"),
                "energy_H": ("magnitude", "potential_disp"),
            }
            for ho_name, (target_up, target_down) in ho_features.items():
                val = entropy_inputs.get(ho_name, 0.5)
                stats = ho_stats.get(ho_name, {"mean": 0.5, "std": 0.1})
                mean_v = stats["mean"]
                std_v = stats["std"]
                z = (val - mean_v) / std_v
                z = max(-2.0, min(2.0, z))
                if target_up in enc.neurons:
                    enc.neurons[target_up].activation *= (1.0 + 0.1 * z)
                if target_down in enc.neurons:
                    enc.neurons[target_down].activation *= (1.0 - 0.1 * z)

            # Lateral inhibition
            circuit._apply_lateral_inhibition(circuit.layers["encoding"])

            # O/P/R/Xin
            circuit.observe()
            circuit.detect_circulations()
            if prev_activations:
                circuit.compute_xin(prev_activations)

            # Learn with ATTENUATED STDP weight
            # Parse stdp_weight from calculation_variant stored in DB
            stdp_weight = 0.4  # default fallback
            cv_row = conn.execute(
                "SELECT calculation_variant FROM v40_signal_entropy_ledger "
                "WHERE window_id=? AND run_id=?",
                (syn_win_id, run_id)).fetchone()
            if cv_row and "weight_" in cv_row[0]:
                try:
                    stdp_weight = float(cv_row[0].rsplit("_", 1)[1])
                except (ValueError, IndexError):
                    pass

            # Scale STDP learning by synthetic weight
            eta_orig = 1.0 / max(circuit._temperature, 0.1)
            eta_syn = max(0.1, min(2.0, eta_orig)) * stdp_weight
            for layer in circuit.layers.values():
                for bundle in layer.bundles:
                    pre_neurons = [layer.neurons[sid]
                                   for sid in bundle.source_neuron_ids
                                   if sid in layer.neurons]
                    post_neurons = [layer.neurons[tid]
                                    for tid in bundle.target_neuron_ids
                                    if tid in layer.neurons]
                    if pre_neurons and post_neurons:
                        bundle.stdp_update(pre_neurons, post_neurons, stdp_weight)

            for bundle in circuit.inter_layer_bundles:
                src_layer = None
                for lid, l in circuit.layers.items():
                    if bundle.source_neuron_ids[0] in l.neurons:
                        src_layer = l
                        break
                if src_layer is None:
                    continue
                pre_neurons = [src_layer.neurons[sid]
                               for sid in bundle.source_neuron_ids
                               if sid in src_layer.neurons]
                post_neurons = []
                for lid, l in circuit.layers.items():
                    for tid in bundle.target_neuron_ids:
                        if tid in l.neurons:
                            post_neurons.append(l.neurons[tid])
                if pre_neurons and post_neurons:
                    bundle.stdp_update(pre_neurons, post_neurons, stdp_weight)

            # Extract z_t for synthetic windows BEFORE maintain (decay zeroes it)
            enc = circuit.layers["encoding"]
            circuit_z_t = [enc.neurons[c].activation for c in z_t_names]

            # Map synthetic window to stimulus name for discrimination
            # syn_<stim_name>_<i> → stim_name
            stim_from_syn = syn_win_id.replace("syn_", "").rsplit("_", 1)[0]
            circuit_z_t_by_stim[stim_from_syn].append(tuple(circuit_z_t))

            circuit.maintain()

            prev_activations = {nid: n.activation for nid, n in enc.neurons.items()}

        print(f"    Synthetic injection complete. Total circuit ticks: {circuit.tick}")

    # ── v40.8: P/R Distance Matrix Evolution ──
    # Track how representational distances between stimuli changed
    # through the circuit's learning process.
    # This tests the hypothesis: pruning/crystallization → related P/R converge
    if circuit_z_t_by_stim:
        stim_keys = sorted(circuit_z_t_by_stim.keys())
        # Compute cos distance matrix from the FINAL z_t profiles
        final_profiles = {}
        for sk in stim_keys:
            profiles = circuit_z_t_by_stim[sk]
            if profiles:
                # Mean profile for this stimulus
                n_dims = len(profiles[0])
                mean_p = [sum(p[d] for p in profiles) / len(profiles)
                          for d in range(n_dims)]
                final_profiles[sk] = mean_p

        if len(final_profiles) >= 2:
            print(f"\n  v40.8 P/R Distance Matrix (representational similarity):")
            # Compute all pairwise cosine distances
            pr_distance_matrix = {}
            for i, s1 in enumerate(stim_keys):
                for s2 in stim_keys[i+1:]:
                    if s1 in final_profiles and s2 in final_profiles:
                        p1, p2 = final_profiles[s1], final_profiles[s2]
                        dot = sum(a*b for a, b in zip(p1, p2))
                        n1 = math.sqrt(sum(a*a for a in p1)) + 1e-12
                        n2 = math.sqrt(sum(b*b for b in p2)) + 1e-12
                        cos_sim = dot / (n1 * n2)
                        pr_distance_matrix[(s1, s2)] = cos_sim
                        print(f"    dist({s1:20s}, {s2:20s}) = {1-cos_sim:.6f}  "
                              f"(cos={cos_sim:.6f})")

            # Compute per-stimulus "centroid magnitude" (how distinct is this P/R?)
            print(f"\n  P/R centroid magnitudes (larger = more distinctive):")
            for sk in stim_keys:
                if sk in final_profiles:
                    mag = math.sqrt(sum(v*v for v in final_profiles[sk]))
                    active_dims = sum(1 for v in final_profiles[sk] if abs(v) > 0.001)
                    print(f"    {sk:25s}  |p|={mag:.6f}  active_dims={active_dims}/{len(final_profiles[sk])}")

    # ── v40.8 Phase 4: Stress Test Extension ──
    # Continue cycling stimuli to reach target tick count.
    # Default: 500 ticks. Set STRESS_TEST_TICKS env var to override.
    stress_target = int(os.environ.get("STRESS_TEST_TICKS", "500"))
    current_ticks = circuit.tick

    if current_ticks < stress_target and sig_rows:
        remaining = stress_target - current_ticks
        print(f"\n{'─' * 72}")
        print(f"  Phase 2.5 [P]: Stress test extension ({current_ticks}→{stress_target} ticks)")
        print(f"{'─' * 72}")

        # Snapshot storage
        snapshots = []
        def take_snapshot(tick_n):
            enc_l = circuit.layers["encoding"]
            all_e = [n.energy for l in circuit.layers.values() for n in l.neurons.values()]
            n_cx = sum(1 for nid in enc_l.neurons if nid.startswith("cx_"))
            n_alive = sum(1 for l in circuit.layers.values()
                         for n in l.neurons.values() if n.is_alive())
            n_quiescent = sum(1 for l in circuit.layers.values()
                             for n in l.neurons.values()
                             if getattr(n, '_quiescent', False))
            n_bundles = sum(len(l.bundles) for l in circuit.layers.values())
            n_il = len(circuit.inter_layer_bundles)
            n_contracting = sum(1 for l in circuit.layers.values()
                               for b in l.bundles if b.bundle_strength < 0.1)
            F = getattr(circuit, '_free_energy', 0)

            # P/R cos snapshot
            enc = circuit.layers["encoding"]
            z_t_snap = {nid: enc.neurons[nid].activation
                        for nid in z_t_names if nid in enc.neurons}

            snapshots.append({
                "tick": tick_n,
                "neurons": len([n for l in circuit.layers.values() for n in l.neurons]),
                "alive": n_alive,
                "quiescent": n_quiescent,
                "bundles": n_bundles,
                "il_bundles": n_il,
                "cx": n_cx,
                "contracting": n_contracting,
                "energy_min": min(all_e) if all_e else 0,
                "energy_mean": sum(all_e)/len(all_e) if all_e else 0,
                "F": F,
                "T": getattr(circuit, '_temperature', 0),
            })

        # Initial snapshot
        take_snapshot(current_ticks)

        # Cycle through all real windows repeatedly
        all_real_rows = [r for r in sig_rows if not r[0].startswith("syn_")]
        cycle_idx = 0
        tick_count = 0
        snapshot_interval = 50

        while tick_count < remaining:
            row = all_real_rows[cycle_idx % len(all_real_rows)]
            cycle_idx += 1

            entropy_inputs = {
                "spectral_H": row[1],
                "fano_H": row[2],
                "synchrony_H": row[3],
                "gradient_H": row[4],
                "sparseness_H": row[5] if len(row) > 5 else 0.5,
                "autocorrelation_H": row[6] if len(row) > 6 else 0.5,
                "energy_H": row[7] if len(row) > 7 else 0.5,
            }

            # Transport
            circuit.transport(entropy_inputs, "signal_entropy")
            enc = circuit.layers["encoding"]
            for zt_name in z_t_names:
                if zt_name in enc.neurons:
                    zt_val = 0.0
                    ek = {"transition": ("synchrony_H", "gradient_H"),
                          "drift": ("fano_H", "sparseness_H"),
                          "gamma_desync": ("synchrony_H",),
                          "xin_residual": ("gradient_H", "energy_H"),
                          "potential_disp": ("spectral_H",),
                          "churn": ("fano_H", "autocorrelation_H"),
                          "magnitude": ("energy_H", "spectral_H")}
                    for k in ek.get(zt_name, ()):
                        raw = entropy_inputs.get(k, 0.5)
                        stats = ho_stats.get(k, None)
                        if stats:
                            z = (raw - stats["mean"]) / max(stats["std"], 1e-6)
                        else:
                            z = 0.0
                        zt_val += z
                    zt_val /= max(len(ek.get(zt_name, (1,))), 1)
                    zt_val = max(0.0, zt_val * 0.01)
                    if zt_val > 0:
                        enc.neurons[zt_name].activate(zt_val)

            circuit._apply_lateral_inhibition(enc)
            circuit.observe()
            circuit.detect_circulations()
            prev_a = {nid: n.activation for nid, n in enc.neurons.items()}
            circuit.compute_xin(prev_a)

            # STDP learning (attenuated for stress cycling — consolidation phase)
            stress_eta = 0.3
            for layer in circuit.layers.values():
                for bundle in layer.bundles:
                    pre_n = [layer.neurons[sid]
                             for sid in bundle.source_neuron_ids
                             if sid in layer.neurons]
                    post_n = [layer.neurons[tid]
                              for tid in bundle.target_neuron_ids
                              if tid in layer.neurons]
                    if pre_n and post_n:
                        bundle.stdp_update(pre_n, post_n, stress_eta)
            for bundle in circuit.inter_layer_bundles:
                src_layer = None
                for lid2, l2 in circuit.layers.items():
                    if bundle.source_neuron_ids[0] in l2.neurons:
                        src_layer = l2
                        break
                if src_layer is None:
                    continue
                pre_n = [src_layer.neurons[sid]
                         for sid in bundle.source_neuron_ids
                         if sid in src_layer.neurons]
                post_n = []
                for lid2, l2 in circuit.layers.items():
                    for tid in bundle.target_neuron_ids:
                        if tid in l2.neurons:
                            post_n.append(l2.neurons[tid])
                if pre_n and post_n:
                    bundle.stdp_update(pre_n, post_n, stress_eta)

            circuit.maintain()
            tick_count += 1

            if tick_count % snapshot_interval == 0:
                take_snapshot(current_ticks + tick_count)

        # Final snapshot
        take_snapshot(circuit.tick)

        # Print snapshot timeline
        print(f"\n  Stress test snapshots ({len(snapshots)} points):")
        print(f"    {'tick':>6s}  {'N':>3s}  {'alive':>5s}  {'Q':>2s}  {'B':>3s}  {'IL':>3s}  "
              f"{'cx':>3s}  {'contr':>5s}  {'E_min':>6s}  {'E_avg':>6s}  {'F':>8s}  {'T':>8s}")
        for s in snapshots:
            print(f"    {s['tick']:6d}  {s['neurons']:3d}  {s['alive']:5d}  "
                  f"{s['quiescent']:2d}  {s['bundles']:3d}  {s['il_bundles']:3d}  "
                  f"{s['cx']:3d}  {s['contracting']:5d}  "
                  f"{s['energy_min']:6.4f}  {s['energy_mean']:6.4f}  "
                  f"{s['F']:8.2f}  {s['T']:8.6f}")

        # Stability verdict
        if len(snapshots) >= 3:
            e_means = [s['energy_mean'] for s in snapshots]
            F_vals = [s['F'] for s in snapshots]
            e_stable = max(e_means) - min(e_means) < 0.3
            F_positive = all(f > 0 for f in F_vals)
            n_stable = snapshots[-1]['neurons'] - snapshots[0]['neurons'] < 20
            print(f"\n  Stability verdict:")
            print(f"    Energy range:   [{min(e_means):.4f}, {max(e_means):.4f}]  "
                  f"{'✅ stable' if e_stable else '⚠️ unstable'}")
            print(f"    Free energy F:  {'✅ always positive' if F_positive else '⚠️ went negative'}")
            print(f"    Neuron growth:  {snapshots[0]['neurons']}→{snapshots[-1]['neurons']}  "
                  f"{'✅ bounded' if n_stable else '⚠️ unbounded'}")


    # ══════════════════════════════════════════════════════════════
    # Phase 3 [R]: Counter-evidence validation + discrimination
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 3 [R]: Discrimination + counter-evidence analysis")
    print(f"{'─' * 72}")

    stim_names = sorted(circuit_z_t_by_stim.keys())
    print(f"  Stimuli: {stim_names}")
    print(f"  Samples: {', '.join(f'{s}={len(circuit_z_t_by_stim[s])}' for s in stim_names)}")

    def compute_mean(z_list):
        n = len(z_list)
        dim = len(z_list[0])
        return tuple(sum(z[d] for z in z_list) / n for d in range(dim))

    circuit_means = {}
    for s in stim_names:
        if circuit_z_t_by_stim.get(s):
            circuit_means[s] = compute_mean(circuit_z_t_by_stim[s])

    print(f"\n  Circuit discrimination (signal entropy driven):")
    circuit_sims = []
    for i, s1 in enumerate(stim_names):
        for s2 in stim_names[i+1:]:
            if s1 in circuit_means and s2 in circuit_means:
                sim = cosine_sim(circuit_means[s1], circuit_means[s2])
                circuit_sims.append(sim)
                print(f"    cos({s1[:18]:18s}, {s2[:18]:18s}) = {sim:.6f}")

    avg_circuit = sum(circuit_sims) / max(len(circuit_sims), 1)

    print(f"\n  Per-dimension z_t profiles:")
    for s in stim_names:
        if s in circuit_means:
            vals = "  ".join(f"{v:.4f}" for v in circuit_means[s])
            print(f"    {s[:22]:22s}: [{vals}]")

    # Signal entropy bundle evolution
    print(f"\n  Signal entropy → z_t bundle evolution:")
    for b in circuit.inter_layer_bundles:
        if b.bundle_id.startswith("sigH_"):
            cond = getattr(b, '_conductance_history', 0.0)
            print(f"    {b.bundle_id:35s}: strength={b.bundle_strength:.4f}  "
                  f"conductance={cond:.4f}  inertia={b.bundle_inertia:.4f}")

    # Circulation amplification stats
    try:
        amp_rows = conn.execute(
            "SELECT gain_combined, entropy_slope_spectral, entropy_slope_fano "
            "FROM v40_circulation_amplification_ledger "
            "WHERE run_id=? ORDER BY CAST(stage_k_id AS INTEGER)",
            (run_id,)).fetchall()
        if amp_rows:
            gains_all = [r[0] for r in amp_rows]
            amplified = sum(1 for g in gains_all if g > 1.01)
            print(f"\n  Circulation amplification (from entropy ledger):")
            print(f"    Windows amplified: {amplified}/{len(gains_all)}")
            print(f"    Gain range: [{min(gains_all):.3f}, {max(gains_all):.3f}]  "
                  f"mean={sum(gains_all)/len(gains_all):.3f}")
    except Exception:
        pass

    # Homeostatic state: structural differentiation
    print(f"\n  Homeostatic differentiation (encoding layer):")
    for nid in z_t_names:
        n = circuit.layers["encoding"].neurons[nid]
        print(f"    {nid:18s}: threshold={n.threshold:.6f}  "
              f"calcium={n.calcium:.6f}  pre_trace={n.pre_trace:.4f}")

    # R-chain: which z_t dims have structural support?
    print(f"\n  R-chain: structural support per z_t dimension:")
    for nid in z_t_names:
        n = circuit.layers["encoding"].neurons[nid]
        # Dimension has support if: threshold adapted away from initial AND calcium > 0
        calcium_active = n.calcium > 0.001
        threshold_adapted = abs(n.threshold - 0.005) > 0.0001
        has_bundle_support = any(
            nid in b.target_neuron_ids and b.bundle_strength > 0.05
            for b in circuit.layers["encoding"].bundles + circuit.inter_layer_bundles
        )
        status = "✅" if (calcium_active or threshold_adapted) else "⚠️ weak"
        print(f"    {nid:18s}: ca={calcium_active}  thr_adapt={threshold_adapted}  "
              f"bundle={has_bundle_support}  → {status}")

    m = circuit.get_metrics()
    print(f"\n  Circuit: alive={m['alive_neurons']}/{m['total_neurons']}  "
          f"P={'✓' if m['p_circulation'] else '✗'}  "
          f"R={'✓' if m['r_circulation'] else '✗'}  "
          f"T={m['temperature']:.4f}  fruits={m['dormant_fruits']}")

    # v40.7: Column physical privilege report
    print(f"\n  v40.7 Structural privilege (Column ≠ Spine):")
    columns_found = 0
    total_prp = 0.0
    for lid, layer in circuit.layers.items():
        for nid, n in layer.neurons.items():
            if n.maturation != "spine":
                columns_found += 1
                total_prp += n.prp_emission
                print(f"    {nid:18s}: {n.maturation:6s}  "
                      f"lat_r={n.lateral_suppression_radius}  "
                      f"ltp×={n.stdp_ltp_boost:.1f}  "
                      f"prp={n.prp_emission:.4f}")
    if columns_found == 0:
        print("    (no neurons matured beyond Spine yet)")
    else:
        print(f"    → {columns_found} Column/Area neurons, total PRP={total_prp:.4f}")

    # v40.7g: Energy + free energy monitoring
    all_energies = []
    for lid, layer in circuit.layers.items():
        for n in layer.neurons.values():
            all_energies.append(n.energy)
    if all_energies:
        print(f"\n  Metabolic state:")
        print(f"    neuron energy: min={min(all_energies):.4f}  "
              f"max={max(all_energies):.4f}  mean={sum(all_energies)/len(all_energies):.4f}")
        print(f"    free energy F: {getattr(circuit, '_free_energy', 0):.4f}  "
              f"temperature T: {getattr(circuit, '_temperature', 0):.6f}")

    # v40.8: Layer dynamics + quiescence
    for lid, layer in circuit.layers.items():
        n_quiescent = sum(1 for n in layer.neurons.values()
                         if getattr(n, '_quiescent', False))
        n_contracting = sum(1 for b in layer.bundles if b.bundle_strength < 0.1)
        print(f"    {lid:20s}  T_layer={layer.layer_temperature:.6f}  "
              f"occ={layer.layer_occupancy:.4f}  "
              f"quiescent={n_quiescent}  contracting={n_contracting}")
    n_il_bundles = len(circuit.inter_layer_bundles)
    n_il_ghosts = len(getattr(circuit, '_inter_ghost_bundles', []))
    print(f"    inter_layer: {n_il_bundles} bundles, {n_il_ghosts} ghosts")

    # v40.9: CPG Bio-Substrate diagnostics
    cpg_layer = circuit.layers.get("cpg")
    if cpg_layer:
        print(f"\n  v40.9 CPG Bio-Substrate (类生体层):")
        for nid in ["cpg_fast_a", "cpg_fast_b", "cpg_slow_a", "cpg_slow_b"]:
            n = cpg_layer.neurons.get(nid)
            if n:
                adapt = getattr(n, '_cpg_adaptation', 0.0)
                print(f"    {nid:15s}  act={n.activation:+.6f}  adapt={adapt:.6f}  "
                      f"ca={n.calcium:.6f}  thr={n.threshold:.6f}")
        # Visceral zone status
        enc = circuit.layers.get("encoding")
        if enc:
            for vid in ["visc_rhythm", "visc_baseline"]:
                vn = enc.neurons.get(vid)
                if vn:
                    print(f"    {vid:15s}  act={vn.activation:+.6f}  "
                          f"ca={vn.calcium:.6f}  pre_trace={vn.pre_trace:.4f}")
        # CPG entropy audit
        cpg_bundles = [b for b in circuit.inter_layer_bundles
                       if b.bundle_id.startswith("cpg_to_")]
        cpg_heat = sum(b.transport_cost for b in cpg_bundles)
        print(f"    CPG→encoding transport heat: {cpg_heat:.6f}  "
              f"(bundles: {len(cpg_bundles)})")

    # v40.7: Dormant fruit trace decay statistics
    all_fruits = []
    for lid, layer in circuit.layers.items():
        for b in layer.bundles:
            if b.xin_dormant_fruit is not None:
                all_fruits.append(b.xin_dormant_fruit)
    for b in circuit.inter_layer_bundles:
        if b.xin_dormant_fruit is not None:
            all_fruits.append(b.xin_dormant_fruit)
    if all_fruits:
        traces = [f.get("trace_strength", 1.0) for f in all_fruits]
        print(f"\n  Dormant fruit traces: {len(all_fruits)} alive")
        print(f"    trace range: [{min(traces):.4f}, {max(traces):.4f}]  "
              f"mean={sum(traces)/len(traces):.4f}")

    # Circulation measure (probability integral over all paths)
    circ_mu = getattr(circuit, '_circulation_measure', 0.0)
    all_cycles = getattr(circuit, '_all_cycle_measures', [])
    ghost_count = sum(len(getattr(l, '_ghost_bundles', []))
                      for l in circuit.layers.values())
    print(f"\n  Circulation measure μ(G) = {circ_mu:.6f}")
    print(f"    Active cycles: {len(all_cycles)}")
    if all_cycles:
        print(f"    P fraction: {all_cycles[0]['fraction']:.4f}")
        if len(all_cycles) > 1:
            print(f"    R fraction: {all_cycles[1]['fraction']:.4f}")
            print(f"    Secondary+: {sum(c['fraction'] for c in all_cycles[2:]):.4f}")
    print(f"    Ghost bundles: {ghost_count}")

    # v40.7e: Convergence sub-manifold report
    conv_nodes = getattr(circuit, '_convergence_nodes', {})
    if conv_nodes:
        print(f"\n  v40.7e Shared sub-manifold convergence nodes: {len(conv_nodes)}")
        for node_id, node in sorted(conv_nodes.items(),
                                     key=lambda x: -x[1]["strength"]):
            dims = " × ".join(node["dims"])
            print(f"    {dims:30s}  strength={node['strength']:.6f}  "
                  f"prime={node['priming_applied']:.6f}  "
                  f"age={circuit.tick - node['created_tick']}")
    else:
        print(f"\n  v40.7e Convergence: (no sub-manifold nodes detected yet)")

    # v40.7h: Crystallized convergence neurons
    enc_layer = circuit.layers.get("encoding")
    if enc_layer:
        crystal_neurons = {nid: n for nid, n in enc_layer.neurons.items()
                          if nid.startswith("cx_")}
        if crystal_neurons:
            # Count inter-layer output bundles from cx_ neurons
            cx_out_bundles = sum(
                1 for b in circuit.inter_layer_bundles
                if any(sid.startswith("cx_") for sid in b.source_neuron_ids))
            print(f"\n  v40.7h Crystallized sub-manifold neurons: {len(crystal_neurons)}"
                  f"  (→ {cx_out_bundles} output bundles to column)")
            for nid, n in crystal_neurons.items():
                print(f"    {nid:25s}  ca={n.calcium:.6f}  "
                      f"thr={n.threshold:.6f}  act_n={n.activation_count:4d}  "
                      f"en={n.energy:.4f}")

    # ══════════════════════════════════════════════════════════════
    # Phase 4 [Xin]: Verdict + structural tension
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'=' * 72}")
    print("  Phase 4 [Xin]: VERDICT + remaining tension")
    print(f"{'=' * 72}")

    flat_avg = 0.999460  # known baseline from flat W_signal
    improved = avg_circuit < flat_avg
    print(f"  Flat baseline cosine: {flat_avg:.6f}")
    print(f"  Circuit avg cosine:   {avg_circuit:.6f}")
    print(f"  Improvement:          {flat_avg - avg_circuit:.6f}")
    print(f"  Discrimination:       {'✅ YES' if improved else '❌ NO'}")

    thresholds = [circuit.layers["encoding"].neurons[n].threshold for n in z_t_names]
    thr_std = math.sqrt(sum((t - sum(thresholds)/len(thresholds))**2 for t in thresholds)/len(thresholds))
    print(f"  Threshold diversity:  std={thr_std:.6f} {'✅' if thr_std > 0.0005 else '❌'}")

    # Count non-zero dimensions per stimulus
    active_dims = {}
    for s in stim_names:
        if s in circuit_means:
            active = sum(1 for v in circuit_means[s] if abs(v) > 0.001)
            active_dims[s] = active
    print(f"  Active dimensions:    {active_dims}")

    # Remaining Xin tension
    xin_total = sum(abs(v) for v in circuit._xin_tensions.values())
    print(f"  Xin total tension:    {xin_total:.4f}")
    print(f"  Activated fruits:     {len(circuit._activated_fruits)}")

    report = {
        "flat_avg_cosine": flat_avg,
        "circuit_avg_cosine": avg_circuit,
        "improvement": flat_avg - avg_circuit,
        "improved": improved,
        "threshold_diversity": thr_std,
        "active_dims": active_dims,
        "xin_tension": xin_total,
        "circuit_metrics": m,
        "signal_entropy_rows": len(sig_rows),
        "masking_records": mask_count,
    }

    # v40.9: CPG Bio-Substrate telemetry → report + DB write-back
    cpg_layer = circuit.layers.get("cpg")
    enc_layer = circuit.layers.get("encoding")
    if cpg_layer:
        cpg_state = {}
        for nid in ["cpg_fast_a", "cpg_fast_b", "cpg_slow_a", "cpg_slow_b"]:
            n = cpg_layer.neurons.get(nid)
            if n:
                cpg_state[nid] = {
                    "activation": n.activation,
                    "calcium": n.calcium,
                    "adaptation": getattr(n, '_cpg_adaptation', 0.0),
                    "threshold": n.threshold,
                }
        visc_state = {}
        if enc_layer:
            for vid in ["visc_rhythm", "visc_baseline"]:
                vn = enc_layer.neurons.get(vid)
                if vn:
                    visc_state[vid] = {
                        "activation": vn.activation,
                        "calcium": vn.calcium,
                        "pre_trace": vn.pre_trace,
                    }
        cpg_bundles = [b for b in circuit.inter_layer_bundles
                       if b.bundle_id.startswith("cpg_to_")]
        cpg_heat = sum(b.transport_cost for b in cpg_bundles)

        report["cpg_bio_substrate"] = {
            "neurons": cpg_state,
            "visceral_zone": visc_state,
            "transport_heat": cpg_heat,
            "il_bundles_total": len(circuit.inter_layer_bundles),
            "il_ghosts_total": len(getattr(circuit, '_inter_ghost_bundles', [])),
        }

        # Write CPG circuit state to DB for pipeline feedback loop
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS v40_circuit_state_ledger (
                state_id TEXT PRIMARY KEY,
                run_id TEXT,
                tick INTEGER,
                circuit_temperature REAL,
                free_energy REAL,
                neuron_count INTEGER,
                alive_count INTEGER,
                il_bundle_count INTEGER,
                il_ghost_count INTEGER,
                total_prp REAL,
                convergence_node_count INTEGER,
                cpg_slow_activation REAL,
                cpg_fast_activation REAL,
                visc_calcium REAL,
                cpg_transport_heat REAL,
                created_at TEXT
            )""")
            from datetime import datetime, timezone
            n_conv = len(getattr(circuit, '_convergence_nodes', {}))
            n_alive = sum(1 for l in circuit.layers.values()
                          for n in l.neurons.values() if n.is_alive())
            total_prp_val = sum(n.prp_emission
                                for l in circuit.layers.values()
                                for n in l.neurons.values())
            cpg_slow_a = cpg_layer.neurons.get("cpg_slow_a")
            cpg_fast_a = cpg_layer.neurons.get("cpg_fast_a")
            visc_r = enc_layer.neurons.get("visc_rhythm") if enc_layer else None
            conn.execute(
                "INSERT INTO v40_circuit_state_ledger VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"cs_{circuit.tick}", run_id, circuit.tick,
                 getattr(circuit, '_temperature', 0),
                 getattr(circuit, '_free_energy', 0),
                 sum(len(l.neurons) for l in circuit.layers.values()),
                 n_alive,
                 len(circuit.inter_layer_bundles),
                 len(getattr(circuit, '_inter_ghost_bundles', [])),
                 total_prp_val, n_conv,
                 cpg_slow_a.activation if cpg_slow_a else 0,
                 cpg_fast_a.activation if cpg_fast_a else 0,
                 visc_r.calcium if visc_r else 0,
                 cpg_heat,
                 datetime.now(timezone.utc).isoformat()))
            conn.commit()
        except Exception as e:
            print(f"  (circuit state DB write skipped: {e})")

    rp = str(BASE / "db" / "v40_integrated_report.json")
    with open(rp, "w") as f_out:
        json.dump(report, f_out, indent=2, default=str)
    print(f"\n  DB:     {DB_PATH}")
    print(f"  Report: {rp}")
    print("=" * 72)

    conn.close()


if __name__ == "__main__":
    main()
```

---

## Results: Allen Brain vs Physics 3D

| Metric | Allen Brain | **Physics 3D** |
|--------|:-:|:-:|
| Data source | real calcium imaging | 3D spring-repulsion LIF |
| Particles/cells | 214 | 50 |
| Signal entropy rows | 100 | 100 |
| **Circuit avg cosine** | **0.298** | **0.340** |
| **Discrimination** | ✅ YES | **✅ YES** |
| **PRP** | 0.007 | **2.658** ↑ 380× |
| **Convergence nodes** | 16 | **10** |
| Active dims | movie=3, scenes=3, grat=5 | movie=5, scenes=2, grat=0 |
| Xin tension | 11.55 | **50.20** ↑ 4.3× |
| Fruits | 0 | **8** |
| IL bundles | 13 | **10** |
| Temperature | 0.047 | **0.030** |

### Signal Entropy Separation

```
Movie:    sp=[0.60,0.97]  fa=[0.01,0.06]  sy=[0.63,0.91]  — coherent
Scenes:   sp=[0.59,0.90]  fa=[0.03,0.09]  sy=[0.58,0.87]  — bursty  
Gratings: sp=[0.57,0.99]  fa=[0.02,0.05]  sy=[0.63,0.89]  — structured
```

---

## Pipeline Feedback Loop

### DB Tables
- `v40_signal_entropy_ledger`: 100 rows × 7 channels from physics simulation
- `v40_circuit_state_ledger`: CPG state, temperature, PRP, convergence count

### JSON Report
- `cpg_bio_substrate` section with neuron states, visceral zone, transport heat
- `circuit_metrics` with temperature, free energy, alive counts

---

## Degraded Components (31 total, +4 new)

| New Proxy | Real Mechanism |
|-----------|---------------|
| `hodgkin_huxley_conductance_model` | Full ion-channel dynamics → LIF proxy |
| `experimental_calcium_imaging` | Real data acquisition → physics simulation |
| `spontaneous_reactivation_during_rest` | Sleep-dependent memory reactivation |
| `sleep_dependent_memory_trace_maintenance` | Offline memory consolidation |
