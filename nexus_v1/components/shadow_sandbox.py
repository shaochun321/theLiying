"""nexus_v1.components.shadow_sandbox — Shadow Layer (Introspective Layer).

A structural copy of the sensorimotor layer's Enc→Col→Mot subgraph,
built from real Neuron + SynapticBundle + ECM + Vascular components.

The shadow layer receives Xin tension from the main system as input.
Contraction = Xin-driven STDP causing activity migration + link rewiring.
Energy-limited: E_remodel cost + weight saturation + PNN freezing.

STATUS: Read-only observer. Computes contraction, clustering, free energy,
motion potential, but does NOT feed back into the main system.

See: modeling_shadow_layer.md §1-§6
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from ..components.neuron import Neuron, NeuronConfig, ChannelConfig
from ..components.ecm import ExtracellularMatrix
from ..components.vascular import VascularCooling
from ..circuit.bundle import SynapticBundle, BundleConfig


# ─────────────────────────────────────────────────────────────
# Shadow NeuronConfig factory (A.3)
# ─────────────────────────────────────────────────────────────

def create_shadow_config(neuron_id: str, layer: str = "encoding") -> NeuronConfig:
    """Create a shadow neuron config: moderate slow τ, balanced energy.

    Shadow neurons have 3× slower RC time constant (τ=15 vs main τ=5).
    VR rate tuned to balance E_remodel drain.

    Design note (from silence diagnosis):
      C=10 gave τ=50 → 50000 steps to reach steady state (too slow).
      C=3  gives τ=15 → 15000 steps to reach steady state (3× slower than main).
    """
    base = {
        "encoding": {
            "capacitance": 3.0,    # 3x main (1.0) -> tau=15
            "r_leak": 5.0,
            "vr_base_rate": 0.05,   # 影子归一：除法归一化分母×5 → 稳态V_ss压制饱和
            # ── DIFFERENTIATION: DivisiveNormalizationReceptor (I) ──
            # Shadow enc receives Xin from vestibular chain (magnitude 0.2~20).
            # DN receptor provides per-neuron input adaptation instead of
            # global Xin normalization (which was a global-patch anti-pattern).
            # BIO: V1 divisive normalization (Carandini & Heeger 2012)
            "use_divisive_norm": True,
            "dn_sigma": 1.0,        # half-saturation: moderate normalization
        },
        "column": {
            "capacitance": 3.0,
            "r_leak": 5.0,
            "vr_base_rate": 0.05,  # 影子归一：同 encoding 层
            # ── DIFFERENTIATION: Spiking + CalciumRateIntegrator (H) ──
            # Shadow col IS spiking (hard upper bound on activation).
            # BUT downstream reads calcium_rate (continuous), not activation.
            # This solves the spike-gap problem: activation=0/1 (discrete)
            # → CRI integrates into calcium_rate ∈ [0, 1.0] (continuous).
            # BCM on enc→col bundle sees col.calcium_rate (continuous) ✓
            # shadow→DA bundle reads col.calcium_rate (continuous) ✓
            # BIO: CaMKII integrates spike rate for downstream signaling
            "spiking": True,
            "v_peak": 1.5,           # spike threshold
            "v_reset": 0.3,          # post-spike reset
            "use_calcium_rate_integrator": True,
            "cri_capacitance": 1.0,
            "cri_r_leak": 50.0,      # τ_CRI = 50 → integrates ~50 shadow steps
            "cri_q_spike": 0.2,      # charge per spike
            "cri_v_clamp": 1.0,      # max calcium_rate = 1.0
        },
        "motor": {
            "capacitance": 3.0,
            "r_leak": 5.0,
            "vr_base_rate": 0.01,
        },
    }
    params = base.get(layer, base["encoding"])
    return NeuronConfig(
        neuron_id=neuron_id,
        capacitance=params["capacitance"],
        r_leak=params["r_leak"],
        v_rest=0.0,
        # FIX-M1: explicit low-threshold channel (default is v_th=0.3,
        # too high for weak Xin-driven currents ~0.15)
        channels=[ChannelConfig(name="default", v_threshold=0.01, gm=1.0)],
        # FIX-M1: small bc_current for baseline activity
        bc_current=0.005,
        energy=5.0,  # high: I^2R heat with gain=10 is ~0.05/step
        # Per-layer spiking (col=True, enc/mot=False)
        spiking=params.get("spiking", False),
        v_peak=params.get("v_peak", 0.0),
        v_reset=params.get("v_reset", 0.0),
        use_voltage_regulator=True,
        vr_base_rate=params["vr_base_rate"],
        vr_activity_coeff=0.5,
        vr_max_rate=5.0,
        # ── Differentiated components (per-layer) ──
        # H. CRI: only col neurons
        use_calcium_rate_integrator=params.get("use_calcium_rate_integrator", False),
        cri_capacitance=params.get("cri_capacitance", 1.0),
        cri_r_leak=params.get("cri_r_leak", 50.0),
        cri_q_spike=params.get("cri_q_spike", 0.2),
        cri_v_clamp=params.get("cri_v_clamp", 1.0),
        # I. DN: only enc neurons
        use_divisive_norm=params.get("use_divisive_norm", False),
        dn_sigma=params.get("dn_sigma", 1.0),
        # maturation_stage=1 triggers BCM in bundle.learn() (S4.2).
        maturation_stage=1,
        # Epoch 1: θ_m_tau 100→10000. Frequency domain separation:
        # θ becomes an extremely sluggish baseline, so even weak
        # transient deviations (after DN compression) can exceed θ
        # and trigger LTP. Without this, θ shadows the signal so
        # closely that (post - θ) ≈ 0 → BCM weight frozen.
        # BIO: homeostatic synaptic scaling operates on hours-days,
        # not seconds (Turrigiano 2008).
        theta_m_tau=10000.0,
        trace_tau_pre=20.0,
        trace_tau_post=20.0,
    )


# ─────────────────────────────────────────────────────────────
# Shadow Sandbox (main class)
# ─────────────────────────────────────────────────────────────

class ShadowSandbox:
    """Shadow Layer built from real Neuron + Bundle + ECM components.

    Usage:
        sandbox = ShadowSandbox()
        sandbox.initialize(circuit)  # creates 21 neurons + ~30 bundles
        sandbox.observe(circuit, tick)  # Xin-driven step (pure observer)
        state = sandbox.get_state()
    """

    # Shadow operates every k steps (slow timescale)
    SHADOW_K = 10
    # Xin input gain: 1:1 物理映射，废除人工放大器。
    # 源头降维：前庭链自然|Ξ|已达15~30，3.0倍放大等于三倍轰炸影子层→积分饱和。
    # REF: 大一统方案 §4.4; 1:1真实非平衡态热力学映射
    XIN_GAIN = 1.0

    def __init__(self):
        self._initialized = False
        self._tick = 0

        # Components (created in initialize)
        self.neurons: Dict[str, Neuron] = {}
        self.bundles: Dict[str, SynapticBundle] = {}
        self.ecm_enc: Optional[ExtracellularMatrix] = None
        self.ecm_col: Optional[ExtracellularMatrix] = None
        self.ecm_mot: Optional[ExtracellularMatrix] = None
        self.vascular: Optional[VascularCooling] = None

        # Mapping: main bundle id → shadow neuron ids (for Xin routing)
        self._xin_routing: Dict[str, List[str]] = {}

        # Axes list (set during init)
        self._axes: List[str] = []

        # ── Monitoring state ──
        self._k_history: List[float] = []
        self._k_ema: float = 0.0
        self._nu: float = 0.0

        # ── M1: δa baseline tracking ──
        # ā_i = EMA(a_i, τ), δa_i = a_i - ā_i
        # §2.1: only deviations carry information
        self._baseline_ema: Dict[str, float] = {}
        self._baseline_tau: float = 200.0  # EMA window (shadow steps)

        # ── M3: κ (contraction) history ──
        self._kappa_history: List[float] = []
        self._kappa_ema: float = 0.0

        # ── Weight change rate (DA novelty signal) ──
        # Weights ARE memory. Weight change rate IS adaptation speed.
        # Converged → Δw≈0 → DA baseline. Novel input → Δw>0 → DA rises.
        self._prev_weight_snapshot: Dict[str, List[float]] = {}
        self._weight_change_rate: float = 0.0
        self._weight_change_ema: float = 0.0

        # ── Construction-phase power supply ──
        # When True, neurons get infinite energy (no I²R drain shutdown).
        # Set to False once shadow dynamics are validated.
        # VALIDATED: 100k step experiment confirmed weight convergence.
        # With construction_power=False, I²R drain self-limits activation.
        self._construction_power: bool = False

    def initialize(self, circuit):
        """Create shadow neurons and bundles mirroring circuit topology.

        Uses circuit.all_axes to include extra modalities (e.g. 'therm').
        This enables deep cross-modal coupling in the shadow layer.
        """
        # Use ALL axes (vestibular + extra) for cross-modal shadow coupling
        axes = list(getattr(circuit, 'all_axes', circuit.vestibular.axes))
        self._axes = axes
        vest_axes = list(circuit.vestibular.axes)

        # ── §1.1: Create shadow neurons ──
        # Encoding: 2 per axis (reg + irr) — ALL axes
        for axis in axes:
            for kind in ["reg", "irr"]:
                nid = f"s_enc_{kind}_{axis}"
                self.neurons[nid] = Neuron(create_shadow_config(nid, "encoding"))

        # Column: 1 per axis — ALL axes
        for axis in axes:
            nid = f"s_col_{axis}"
            self.neurons[nid] = Neuron(create_shadow_config(nid, "column"))

        # Motor: 3 (x, y, z)
        motor_map = {"move_x": "x", "move_y": "y", "move_z": "z"}
        for mk, mv in motor_map.items():
            nid = f"s_mot_{mv}"
            self.neurons[nid] = Neuron(create_shadow_config(nid, "motor"))

        # ── §1.2: Create shadow bundles ──
        # Axis-internal: s_enc → s_col (6 bundles, 2 sources each)
        for axis in axes:
            srcs = [self.neurons[f"s_enc_reg_{axis}"],
                    self.neurons[f"s_enc_irr_{axis}"]]
            tgts = [self.neurons[f"s_col_{axis}"]]
            bid = f"s_enc_to_col_{axis}"
            cfg = BundleConfig(
                bundle_id=bid,
                initial_weight=0.1,  # copy from main system
                stdp_lr=0.01,
                remodel_cost_kappa=0.001,
                synapse_gain=10.0,  # compensate for multi-stage MOSFET threshold
                bundle_role="shadow",  # C-001.3: shadow layer intra-axis
            )
            self.bundles[bid] = SynapticBundle(cfg, srcs, tgts)

        # Col → Mot (each col axis → assigned motor)
        mot_assignment = {}
        for axis in axes:
            if "yaw" in axis or "oto_x" in axis:
                mot_key = "x"
            elif "pitch" in axis or "oto_y" in axis:
                mot_key = "y"
            elif "roll" in axis or "oto_z" in axis:
                mot_key = "z"
            elif "therm" in axis:
                # Thermal column → all 3 motors equally (no spatial bias)
                mot_key = "x"  # primary, cross-axis handles the rest
            else:
                mot_key = "z"
            mot_assignment[axis] = mot_key

        for axis in axes:
            src = [self.neurons[f"s_col_{axis}"]]
            tgt = [self.neurons[f"s_mot_{mot_assignment[axis]}"]]
            bid = f"s_col_to_mot_{axis}"
            cfg = BundleConfig(
                bundle_id=bid,
                initial_weight=0.05,
                stdp_lr=0.01,
                remodel_cost_kappa=0.001,
                synapse_gain=10.0,
                bundle_role="shadow",  # C-001.3: shadow layer col→mot
            )
            self.bundles[bid] = SynapticBundle(cfg, src, tgt)

        # Cross-axis col↔col (C(n,2) dormant bundles, §1.2)
        # With 7 axes: C(7,2)=21 (was 15 for vestibular-only)
        # Cross-modal bundles (involving 'therm') encode world-body relations
        # Intra-vestibular bundles encode self-body geometry
        for i in range(len(axes)):
            for j in range(i + 1, len(axes)):
                src = [self.neurons[f"s_col_{axes[i]}"]]
                tgt = [self.neurons[f"s_col_{axes[j]}"]]
                bid = f"s_cross_{axes[i]}_{axes[j]}"
                # Cross-modal bundles start with same weight but will
                # develop differently due to activation pattern differences
                cfg = BundleConfig(
                    bundle_id=bid,
                    initial_weight=0.001,  # dormant
                    stdp_lr=0.01,
                    remodel_cost_kappa=0.001,
                    silence_threshold=0.0005,
                    synapse_gain=10.0,
                    bundle_role="cross_axis",  # C-001.3: association fibers
                    delay_steps=2,  # unmyelinated, slower conduction
                )
                self.bundles[bid] = SynapticBundle(cfg, src, tgt)

        # ── §4: Shadow ECM (independent, slow PNN) ──
        self.ecm_enc = ExtracellularMatrix(
            thermal_capacity=5.0,  # 5× main
            thermal_conductance=0.3,
            ion_buffer_tau=0.2,
            pnn_target=0.5,
            capacitance_boost=0.1,
        )
        self.ecm_col = ExtracellularMatrix(
            thermal_capacity=5.0,
            thermal_conductance=0.3,
            ion_buffer_tau=0.2,
            pnn_target=0.7,
            capacitance_boost=0.1,
        )
        self.ecm_mot = ExtracellularMatrix(
            thermal_capacity=5.0,
            thermal_conductance=0.3,
            ion_buffer_tau=0.2,
            pnn_target=0.3,
            capacitance_boost=0.1,
        )

        # ── §4: Shadow Vascular (low flow) ──
        self.vascular = VascularCooling(
            base_flow=0.2,          # 1/5 of main system
            nvc_gain=0.3,
            c_blood=1.0,
            atp_efficiency=0.05,    # less efficient supply
            max_flow=0.8,
        )

        # ── Build Xin routing map ──
        # Maps main bundle → shadow encoding neurons that receive its Xin
        for axis in axes:
            # Main enc→col bundle's Xin → shadow_enc_{axis} neurons
            main_bid = f"enc_to_col_{axis}"
            self._xin_routing[main_bid] = [
                f"s_enc_reg_{axis}", f"s_enc_irr_{axis}",
            ]
            # Vestibular axes also get upstream Xin from met→hc
            if axis in vest_axes:
                main_bid_met = f"met_to_hc_{axis}"
                self._xin_routing[main_bid_met] = [
                    f"s_enc_reg_{axis}",
                ]
            # Extra axes (therm) have no vestibular chain → no met→hc Xin
            # Their Xin comes only from enc→col bundle tension

        self._initialized = True

    def observe(self, circuit, tick: int):
        """Observe circuit and run one shadow step.

        PURE OBSERVER — does NOT modify the main circuit.
        Called every step; shadow only updates every SHADOW_K steps.
        """
        if not self._initialized:
            self.initialize(circuit)

        self._tick = tick

        # Only update every K steps (slow timescale, §6)
        if tick % self.SHADOW_K != 0:
            return

        dt = 0.001 * self.SHADOW_K  # effective dt for shadow step

        # ── 1. Accumulate input currents for all shadow neurons ──
        # Each neuron gets stepped EXACTLY ONCE to avoid double-update.
        accumulated_currents: Dict[str, float] = {
            nid: 0.0 for nid in self.neurons
        }

        # 1a. Xin from main system -> encoding neurons (§1.3)
        # NOTE: abs(xi) because shadow cares about prediction error MAGNITUDE,
        # not sign. Negative Xin would push V below MOSFET threshold (0.3)
        # and produce zero activation — defeating contraction dynamics.
        #
        # MOTHER-DIFFERENTIATION: No global Xin normalization.
        # Each shadow enc neuron has its OWN DivisiveNormalizationReceptor
        # (component I) inside neuron.step() that adapts to its input range.
        # This replaces the global max(|xi|) normalization (anti-pattern).
        # BIO: each cortical neuron normalizes independently via local
        # GABAergic interneuron pool, not a global signal.
        xin_abs_all = []
        for b in circuit.get_all_bundles():
            xi = b.config.xin_tension
            targets = self._xin_routing.get(b.id, [])
            for nid in targets:
                if nid in accumulated_currents:
                    # Raw abs(xi) × XIN_GAIN — DN receptor handles normalization
                    accumulated_currents[nid] += abs(xi) * self.XIN_GAIN
            xin_abs_all.append(abs(xi))

        # 1b. Bundle propagation → target neurons
        for bid, bundle in self.bundles.items():
            if bundle.config.is_silent:
                continue
            currents = bundle.propagate()
            for j, tgt in enumerate(bundle.targets):
                if j < len(currents):
                    accumulated_currents[tgt.id] += currents[j]

        # ── 2. Step ALL neurons exactly once with accumulated currents ──
        # CONSTRUCTION POWER: refill energy before stepping (§construction)
        if self._construction_power:
            for n in self.neurons.values():
                n.energy = max(n.energy, 5.0)

        for nid, neuron in self.neurons.items():
            neuron.step(input_current=accumulated_currents[nid], dt=dt)

        # NOTE: No global Zener clamp. Shadow col neurons now use spiking
        # (hard upper bound) + CalciumRateIntegrator (continuous output).
        # Shadow enc neurons use DivisiveNormalizationReceptor (bounded input).
        # Both are per-neuron differentiated components, not global patches.

        # ── 4. Learn: STDP on shadow bundles (§2.1) ──
        for bid, bundle in self.bundles.items():
            if bundle.config.is_silent:
                continue
            # PNN gate from shadow ECM
            if "enc_to_col" in bid:
                pnn_gate = self.ecm_enc.plasticity_gate if self.ecm_enc else 1.0
            elif "col_to_mot" in bid or "cross" in bid:
                pnn_gate = self.ecm_col.plasticity_gate if self.ecm_col else 1.0
            else:
                pnn_gate = 1.0
            bundle.learn(dt=dt, plasticity_gate=max(0.0, pnn_gate))

        # ── 4b. Xin tension for shadow bundles (§7.2) ──
        # Without this, shadow Xin stays 0 forever.
        for bid, bundle in self.bundles.items():
            if not bundle.config.is_silent:
                bundle.compute_xin(dt)

        # ── 5. Silent synapse management (§3) ──
        self._manage_silent_synapses(tick)

        # ── 6. ECM thermal update ──
        if tick % (self.SHADOW_K * 100) == 0:
            self._update_ecm(dt * 100)

        # ── 7. Vascular cooling ──
        if tick % (self.SHADOW_K * 10) == 0:
            total_heat = sum(n.heat_output for n in self.neurons.values())
            total_activity = sum(abs(n.activation) for n in self.neurons.values())
            max_temp = max(
                self.ecm_enc.temperature if self.ecm_enc else 0.1,
                self.ecm_col.temperature if self.ecm_col else 0.1,
                self.ecm_mot.temperature if self.ecm_mot else 0.1,
            )
            vasc_result = self.vascular.step(
                tissue_temperature=max_temp,
                local_activity=total_activity,
                dt=dt * 10,
            )
            # Distribute cooling
            cool = vasc_result['heat_removed'] * dt * 10 / 3.0
            for ecm in [self.ecm_enc, self.ecm_col, self.ecm_mot]:
                if ecm:
                    ecm._temperature -= cool / max(ecm.thermal_capacity, 0.01)

        # ── 8. Update free energy K and motion potential ν ──
        self._update_free_energy(xin_abs_all)

        # ── 9. M1: Update δa baselines ──
        self._update_baselines()

        # ── 10. M3: Update κ (contraction degree) ──
        self._update_kappa()

        # ── 11. Weight change rate (novelty signal for DA) ──
        self._update_weight_change_rate()

    def _manage_silent_synapses(self, tick: int):
        """Check for bundles entering/exiting silent state (§3)."""
        for bid, bundle in self.bundles.items():
            if not bid.startswith("s_cross_"):
                continue  # only cross-axis bundles can go silent

            mean_w = bundle.mean_weight()

            if not bundle.config.is_silent:
                # Check for silencing
                if mean_w < bundle.config.silence_threshold:
                    bundle.config.is_silent = True
                    bundle.config.silent_snapshot = {
                        'w': mean_w,
                        'xin': bundle.config.xin_tension,
                        'tick': tick,
                        'bundle_id': bid,
                    }
            else:
                # Check for reactivation (§3.3)
                current_xin = bundle.config.xin_tension
                stored_xin = bundle.config.silent_snapshot.get('xin', 0)
                # Simple similarity: both non-zero and same sign
                if (abs(current_xin) > 0.01 and abs(stored_xin) > 0.01
                        and current_xin * stored_xin > 0):
                    # Reactivate
                    old_w = bundle.config.silent_snapshot.get('w', 0.001)
                    for row in bundle._memristors:
                        for m in row:
                            m.w = max(m.w, old_w)
                    bundle.config.is_silent = False
                    bundle.config.silent_snapshot = {}

    def _update_ecm(self, dt: float):
        """Update shadow ECM (temperature + PNN). §4."""
        # Gather heat from each layer
        enc_heat = sum(n.heat_output for nid, n in self.neurons.items()
                       if nid.startswith("s_enc_"))
        col_heat = sum(n.heat_output for nid, n in self.neurons.items()
                       if nid.startswith("s_col_"))
        mot_heat = sum(n.heat_output for nid, n in self.neurons.items()
                       if nid.startswith("s_mot_"))
        if self.ecm_enc:
            self.ecm_enc.step(enc_heat, dt)
        if self.ecm_col:
            self.ecm_col.step(col_heat, dt)
        if self.ecm_mot:
            self.ecm_mot.step(mot_heat, dt)

    def _update_free_energy(self, xin_values: List[float]):
        """Update free energy kernel K and motion potential ν. §5."""
        K_raw = sum(xi ** 2 for xi in xin_values)
        # Michaelis-Menten saturation: K is bounded by physical state space.
        # BIO: calmodulin/CaMKII activation saturates at finite Ca2+ concentration
        #      (Bhaskara 2011). No free-energy variable can grow unboundedly.
        # Normal K_raw (|xi|~0.1-1.0, ~35 bundles) ≈ 0.35-35 → linear region.
        # Pathological K_raw (xi diverges) → bounded near K_MM_LIMIT.
        # CALIBRATE: K_MM_LIMIT=1000 keeps normal range fully linear (<3% sat).
        # Pending EXP validation of exact saturation point.
        K_MM_LIMIT = 1000.0
        K = K_raw * K_MM_LIMIT / (K_raw + K_MM_LIMIT)
        self._k_ema = self._k_ema * 0.99 + K * 0.01

        if self._k_history:
            self._nu = self._k_ema - self._k_history[-1]
        else:
            self._nu = 0.0

        self._k_history.append(self._k_ema)
        if len(self._k_history) > 500:
            self._k_history.pop(0)

    # ─────────────────────────────────────────────────────────
    # State output
    # ─────────────────────────────────────────────────────────

    def get_state(self) -> dict:
        """Get complete shadow layer state for monitoring."""
        if not self._initialized:
            return {"status": "not_initialized"}

        # ── Cluster detection: based on cross-axis bundle weights ──
        active_cross = {}
        silent_cross = []
        for bid, bundle in self.bundles.items():
            if not bid.startswith("s_cross_"):
                continue
            w = bundle.mean_weight()
            if bundle.config.is_silent:
                silent_cross.append(bid)
            elif w > 0.01:
                active_cross[bid] = round(w, 4)

        # ── Energy state ──
        total_energy = sum(n.energy for n in self.neurons.values())
        min_energy = min(n.energy for n in self.neurons.values())
        total_heat = sum(n.heat_output for n in self.neurons.values())

        # ── Neural spacetime interval ds² audit (§5) ──
        # Compute for a sample pair: yaw-enc vs pitch-enc
        ds2_sample = self._compute_ds2("s_col_yaw", "s_col_pitch")

        # ── K trend ──
        if len(self._k_history) >= 20:
            recent = sum(self._k_history[-10:]) / 10
            early = sum(self._k_history[:10]) / 10
            if recent < early * 0.9:
                trend = "decreasing"
            elif recent > early * 1.1:
                trend = "increasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "status": "active",
            "n_neurons": len(self.neurons),
            "n_bundles": len(self.bundles),
            "contraction": {
                "active_cross_links": active_cross,
                "n_active_cross": len(active_cross),
                "n_silent": len(silent_cross),
                "silent_bundles": silent_cross[:5],  # first 5
            },
            "energy": {
                "total": round(total_energy, 4),
                "min": round(min_energy, 4),
                "total_heat": round(total_heat, 6),
            },
            "free_energy": {
                "K": round(sum(xi ** 2 for xi in [
                    b.config.xin_tension for b in self.bundles.values()
                ]), 8),
                "K_ema": round(self._k_ema, 8),
                "nu": round(self._nu, 10),
                "trend": trend,
            },
            "ecm": {
                "enc_temp": round(self.ecm_enc.temperature, 4) if self.ecm_enc else 0,
                "col_temp": round(self.ecm_col.temperature, 4) if self.ecm_col else 0,
                "mot_temp": round(self.ecm_mot.temperature, 4) if self.ecm_mot else 0,
                "enc_pnn": round(self.ecm_enc.pnn_maturity, 4) if self.ecm_enc else 0,
            },
            "ds2_sample": {
                "pair": "s_col_yaw <-> s_col_pitch",
                "ds2": round(ds2_sample, 6) if ds2_sample is not None else None,
                "causal": "timelike" if (ds2_sample is not None and ds2_sample < 0) else "spacelike",
            },
            "kappa": {
                "current": round(self._kappa_ema, 6),
                "interpretation": (
                    "expanding" if self._kappa_ema > 1.0 else
                    "contracting" if self._kappa_ema > 0.01 else
                    "collapsed"
                ),
            },
            "delta_a_sample": {
                nid: round(self._get_delta_a(nid), 6)
                for nid in list(self.neurons.keys())[:4]
            },
        }

    def _compute_ds2(self, nid_a: str, nid_b: str) -> Optional[float]:
        """Compute neural spacetime interval ds² between two shadow neurons.

        M1 upgrade: uses δa (deviation from baseline) instead of raw activation.
        §2.2: ds² = Σ g_ij · δa_i · δa_j
        where g_ij = w_cross(i,j) is the cross-bundle weight.

        For a pair (a,b): ds² = g_ab · δa_a · δa_b
        Positive ds² with both δa same sign = spacelike (correlated)
        Negative = timelike (anti-correlated)
        """
        # Get δa for both neurons
        da_a = self._get_delta_a(nid_a)
        da_b = self._get_delta_a(nid_b)

        # Find cross-bundle weight g_ij
        for bid, bundle in self.bundles.items():
            src_ids = {s.id for s in bundle.sources}
            tgt_ids = {t.id for t in bundle.targets}
            if nid_a in src_ids and nid_b in tgt_ids:
                w = bundle.mean_weight()
                if w > 1e-6 and not bundle.config.is_silent:
                    # ds² = g_ij × δa_i × δa_j (§2.2)
                    ds2 = w * da_a * da_b
                    return ds2
        # No direct connection: undefined (spacelike by convention)
        return 1.0

    # ─────────────────────────────────────────────────────────
    # M1: δa infrastructure
    # ─────────────────────────────────────────────────────────

    def _get_delta_a(self, nid: str) -> float:
        """Get δa_i = a_i - ā_i for a shadow neuron."""
        n = self.neurons.get(nid)
        if n is None:
            return 0.0
        baseline = self._baseline_ema.get(nid, 0.0)
        return n.activation - baseline

    def _update_baselines(self):
        """Update EMA baselines for all shadow neurons (M1: §2.1)."""
        alpha = 1.0 / max(self._baseline_tau, 1.0)
        for nid, n in self.neurons.items():
            # M1 fix: track raw activation (not abs) so δa = a - ā works correctly.
            # abs() would bias ā upward, making δa always negative near zero.
            act = n.activation
            if nid not in self._baseline_ema:
                self._baseline_ema[nid] = act
            else:
                self._baseline_ema[nid] += alpha * (
                    act - self._baseline_ema[nid])

    # ─────────────────────────────────────────────────────────
    # M3: κ (contraction degree)
    # ─────────────────────────────────────────────────────────

    def _update_kappa(self):
        """Compute contraction degree κ (M3: §2.4).

        κ = Σ g_ij · δa_i · δa_j / Σ (δa_i)²

        g_ij = cross-bundle weight (metric tensor).
        κ > 1: expanding (cross-correlations dominate self-variance)
        κ < 1: contracting (self-variance dominates)
        κ → 0: full contraction (collapsed to point)
        """
        numerator = 0.0  # Σ g_ij · δa_i · δa_j
        denominator = 0.0  # Σ (δa_i)²

        # Collect δa for all column neurons
        col_da = {}
        for nid in self.neurons:
            if nid.startswith('s_col_'):
                col_da[nid] = self._get_delta_a(nid)
                denominator += col_da[nid] ** 2

        # Sum over cross-axis bundles (g_ij = weight)
        for bid, bundle in self.bundles.items():
            if not bid.startswith('s_cross_'):
                continue
            if bundle.config.is_silent:
                continue
            w = bundle.mean_weight()  # g_ij
            src_id = bundle.sources[0].id if bundle.sources else None
            tgt_id = bundle.targets[0].id if bundle.targets else None
            if src_id in col_da and tgt_id in col_da:
                numerator += w * col_da[src_id] * col_da[tgt_id]

        if denominator > 1e-12:
            kappa = numerator / denominator
        else:
            kappa = 0.0

        self._kappa_ema = self._kappa_ema * 0.99 + kappa * 0.01
        self._kappa_history.append(self._kappa_ema)
        if len(self._kappa_history) > 500:
            self._kappa_history.pop(0)

    def _update_weight_change_rate(self):
        """Track weight change rate across shadow bundles.

        Weights ARE memory. Weight change rate = adaptation speed = novelty.
        Converged weights → Δw ≈ 0 → DA stays at baseline.
        Novel input → STDP adjusts weights → Δw > 0 → DA rises.
        Adaptation complete → weights settle → Δw → 0 → DA falls.

        Self-normalizing: divides |Δw| by total weight mass.
        This means the signal is independent of input magnitude.
        """
        total_dw = 0.0
        total_w = 0.0
        current_snapshot = {}

        for bid, bundle in self.bundles.items():
            if bundle.config.is_silent:
                continue
            weights = [m.w for row in bundle._memristors for m in row]
            current_snapshot[bid] = weights
            total_w += sum(abs(w) for w in weights)

            if bid in self._prev_weight_snapshot:
                prev = self._prev_weight_snapshot[bid]
                for w_prev, w_curr in zip(prev, weights):
                    total_dw += abs(w_curr - w_prev)

        self._prev_weight_snapshot = current_snapshot

        # Normalize by total weight mass (self-normalizing)
        if total_w > 1e-8:
            self._weight_change_rate = total_dw / total_w
        else:
            self._weight_change_rate = 0.0

        # EMA smoothing (τ ≈ 50 shadow steps = 500 real steps = 0.5s)
        self._weight_change_ema = (
            self._weight_change_ema * 0.98
            + self._weight_change_rate * 0.02
        )
