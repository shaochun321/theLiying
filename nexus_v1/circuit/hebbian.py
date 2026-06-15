"""nexus_v1.circuit.hebbian — Minimal Hebbian Circuit.

A complete but minimal Hebbian circuit that receives input from
the vestibular chain's afferent neurons and learns motion patterns.

Architecture:
  vestibular_input (from VestibularChain afferents)
       ↓ [bundle: vest_to_enc]
  encoding (pattern recognition)
       ↓ [bundle: enc_to_col]
  column (integration / working memory)
       ↓ [bundle: col_to_motor]
  motor (output to body)

All neurons use the same extended MetaNeuron model.
All bundles use STDP learning (Memristor-based).
"""

from __future__ import annotations

from typing import Dict, List

from ..components.neuron import Neuron, NeuronConfig, ChannelConfig
from ..circuit.bundle import SynapticBundle, BundleConfig
from ..vestibular.chain import VestibularChain, ALL_AXES


# ─────────────────────────────────────────────────────────────────────
# Neuron configurations for circuit layers
# ─────────────────────────────────────────────────────────────────────

def _encoding_config(name: str) -> NeuronConfig:
    """TYPE:SEMI — Encoding layer: pattern detection with temporal integration.

    dt=0.001: τ_RC = C×R = 1×5 = 5 ms. Retention between ISI(24ms):
    exp(-24/5000) = 0.995 (per step) → exp(-24×0.001/0.005) = 0.0079 over ISI.
    Actually need τ > ISI: τ = 5ms < ISI = 24ms → some loss, but bias compensates.
    Reduced from τ=200ms (which took 200s to reach steady state).

    Compensation A/C enabled (no B/D).
    """
    return NeuronConfig(
        neuron_id=f"enc_{name}",
        # Global τ calibration: C=0.15, R=5 → τ=0.75 (fast sensory).
        # dt/τ=1.33 — within O(dt). V_ss(bias)=0.12 < v_peak=0.35.
        # Previous C=0.1 → τ=0.5 → dt/τ=2.0 (marginal).
        capacitance=0.15,
        r_leak=5.0,
        inertia=0.5,
        vdd=1.0,
        r_supply=0.1,
        # GainChain: spiking=True — each Enc regenerates signal digitally.
        # Non-spiking Enc caused 87% signal attenuation (analog decay).
        # BIO: cortical neurons are spiking (rate coding).
        spiking=True,
        v_peak=0.35,    # V_ss ≈ 1.1 → v_peak < V_ss → sustained firing
        v_reset=0.05,   # clean reset
        b_adapt=0.01,   # moderate adaptation to prevent runaway
        tau_w=1.0,
        channels=[
            ChannelConfig(
                name="default",
                v_threshold=0.01,
                gm=1.0,
                tau_gate=0.0,
                reversal=0.0,
                sign=1.0,
            ),
        ],
        # A. VoltageRegulator — metabolic recovery (NOT excitation).
        # Rule: V_ss(VR) < v_peak/3 = 0.117. vr_max = 0.049.
        use_voltage_regulator=True,
        vr_base_rate=0.04,
        vr_activity_coeff=0.5,
        vr_max_rate=0.2,
        # C. BiasCurrentSource — baseline firing (BIO: tonic 20-40 Hz)
        # V_ss = bc × R = 0.02 × 5 = 0.10 << v_peak=0.35
        # Low bias: encoding is silent without afferent drive.
        # Previous 0.05 → V_ss=0.25 → even unstimulated axes fired 100%.
        use_bias_current=True,
        bc_current=0.02,
    )


def _column_config(name: str) -> NeuronConfig:
    """TYPE:SEMI — Column layer: integration / working memory.

    τ_RC = 2 × 5 = 10 ms (longer than Enc for temporal integration).
    Compensation A/C enabled (no B/D).
    """
    return NeuronConfig(
        neuron_id=f"col_{name}",
        # Global τ calibration: C=0.2, R=5 → τ=1.0 (integration).
        # dt/τ=1.0 — perfect match. V_ss(bias)=0.087 < v_peak=0.15.
        # Previous C=0.05 → τ=0.25 → dt/τ=4.0 (coupler was sole lifeline).
        capacitance=0.2,
        r_leak=5.0,
        inertia=1.0,
        vdd=1.0,
        r_supply=0.1,
        # GainChain: spiking=True — Col regenerates signal digitally.
        # Non-spiking Col caused massive attenuation (act=0.04 from Vm=0.24).
        # BIO: cortical column neurons fire spikes.
        spiking=True,
        v_peak=0.25,    # EXP-012: raised from 0.15 for DA modulation headroom
        v_reset=0.02,   # clean reset
        b_adapt=0.01,
        tau_w=1.0,
        channels=[
            ChannelConfig(
                name="default",
                v_threshold=0.08,   # C2: raised from 0.01 — requires encoding drive
                gm=0.8,
                tau_gate=0.0,
                reversal=0.0,
                sign=1.0,
            ),
        ],
        # A. VoltageRegulator — metabolic recovery.
        # Rule: V_ss(VR) < v_peak/3 = 0.05. vr_max = 0.017.
        use_voltage_regulator=True,
        vr_base_rate=0.015,
        vr_activity_coeff=0.5,
        vr_max_rate=0.1,
        # C. BiasCurrentSource — baseline firing
        # C2 fix: V_ss = 0.01 × 5 = 0.05 << v_peak=0.15 (was 0.03→0.15!)
        # Column MUST receive encoding input to spike.
        use_bias_current=True,
        bc_current=0.01,
    )


def _motor_config(name: str) -> NeuronConfig:
    """TYPE:SEMI — Motor layer: spiking output for motor commands.

    Motor neurons are spiking (clear discrete commands).
    FIX-017: Added bc_current for tonic baseline (like real motor pool).
      BIO: Motor neurons have low tonic activity that increases with drive.
      Threshold lowered 0.3→0.2 to match reduced col→motor gain (0.1).
    """
    return NeuronConfig(
        neuron_id=f"motor_{name}",
        # Global τ calibration: C=0.3, R=5 → τ=1.5 (slow motor output).
        # dt/τ=0.67. V_ss(bias)=0.11 < v_peak=0.2.
        # BIO: motor neurons are large cells (soma ~50μm) with high C_m.
        capacitance=0.3,
        r_leak=5.0,
        inertia=0.5,
        vdd=1.0,
        r_supply=0.1,
        spiking=True,
        v_peak=0.2,
        v_reset=0.0,  # Clean reset (previous 0.077 = 51% of threshold)
        b_adapt=0.005,
        tau_w=1.0,
        # FIX-S3: Explicit channel with v_threshold < v_peak.
        # CHECK 2: v_th=0.15 < v_peak=0.2 → spike possible.
        # Previous: default MOSFET v_th=0.3 > v_peak=0.2 → NEVER spikes.
        channels=[
            ChannelConfig(
                name="default",
                v_threshold=0.15,
                gm=1.0,
                tau_gate=0.0,
                reversal=0.0,
                sign=1.0,
            ),
        ],
        # A. VoltageRegulator — metabolic recovery.
        # Rule: V_ss(VR) < v_peak/3 = 0.067. vr_max = 0.019.
        # Previous vr_base=0.5 → V_ss=1.76 >> v_peak (Motor self-sustained).
        use_voltage_regulator=True,
        vr_base_rate=0.015,
        vr_activity_coeff=0.5,
        vr_max_rate=0.1,
        # Phase 5: V_ss = bc*R = 0.01*5 = 0.05. V_ss(bias)=0.035 << v_peak=0.2.
        # Motor must be driven by Column to spike — not self-sustain.
        # headroom = v_peak - V_ss(bias) = 0.165 → coupler has regulation range.
        # BIO: spinal motor neurons have low spontaneous rate (~2Hz).\n        use_bias_current=True,\n        bc_current=0.01,
        # E. FatigueCapacitor: spike-rate-dependent threshold adaptation
        # Replaces external rate homeostasis (which had section conflicts).
        # τ_fatigue = C*R = 1.0*3.0 = 3s.
        # Equilibrium: I_excite = k * Q * f * τ * dt/C
        #   0.005 = 0.1 * 0.05 * f * 3 * 0.1 → f ≈ 3.3 Hz
        # k=0.5 was too strong (0.2 Hz, STDP dead); k=0.1 → ~3 Hz target.
        # BIO: Ca²⁺-dependent K⁺ channel conductance.
        use_fatigue=True,
        fatigue_capacitance=1.0,
        fatigue_r_leak=3.0,
        fatigue_q_spike=0.05,
        fatigue_k=0.1,
        # F. Mitosis: split when sustained moderate load
        # V_fat > 0.4 for 30k steps (30s) → eligible to split.
        # At 3 Hz: V_fat = 0.05*3*3 = 0.45 > 0.4 → triggers
        # Fatigue prevents catastrophic overload; mitosis handles moderate load.
        # Max 4 splits per lineage (3 originals → max 48 motors).
        enable_mitosis=True,
        mitosis_v_fat_threshold=0.4,
        mitosis_confirm_steps=30000,
        mitosis_max_splits=4,
        # G. Apoptosis: die when energy-starved too long
        # BIO: ATP depletion → caspase cascade → programmed cell death.
        # energy < 0.05 for 30k steps (30s) → neuron removed.
        enable_apoptosis=True,
        apoptosis_energy_threshold=0.05,
        apoptosis_confirm_steps=30000,
        # Motor basal cost higher: 80% of recovery → any shared PowerRail
        # load makes zombies drain. BIO: motor neurons have high metabolic
        # demands (large soma, many ion channels, NMJ maintenance).
        basal_metabolic_cost=0.0008,
    )



# ─────────────────────────────────────────────────────────────────────
# HebbianCircuit
# ─────────────────────────────────────────────────────────────────────

class HebbianCircuit:
    """Minimal Hebbian circuit integrated with vestibular chain.

    The vestibular chain IS part of this circuit — not a separate system.
    VestibularChain provides the sensory layers (MET, HairCell, Afferent).
    This class adds the cognitive layers (Encoding, Column, Motor).

    Architecture:
        [VestibularChain: MET → HairCell → Afferent_reg + Afferent_irr]
             ↓
        [Encoding: 2 per axis (regular + irregular pathway)]
             ↓
        [Column: 1 per axis]
             ↓
        [Motor: 3 neurons (move_x, move_y, move_z)]

    Extra axes (e.g. 'therm') bypass the vestibular chain and feed
    directly into Encoding neurons. BIO: thermoreceptors have a shorter
    signal chain (3 stages vs 4 for mechanoreceptors).
    """

    # ── RULE S2: Structural growth constants ──
    SPROUT_INTERVAL: int = 10000    # check every 10k steps (10s)
    XI_SPROUT: float = 0.3          # |ξ| > 0.3 triggers sprouting (calibrated from 100k run)
    # P2.1: MAX_TOTAL_BUNDLES removed. Thermodynamic ceiling via
    # EnergyStore (P_inflow) + constant per-bundle basal drain.
    # N_max ≈ P_inflow / P_basal (physics, not code).
    MAX_SPROUTS_PER_INTERVAL: int = 3  # max sprouts per check (blind, no ξ ranking)
    SPROUT_ENERGY_COST: float = 0.1 # energy consumed per sprout
    MAX_MOTORS_PER_AXIS: int = 20    # P2: max motor neurons per axis (skull constraint)

    def __init__(self, vestibular: VestibularChain | None = None,
                 extra_axes: List[str] | None = None):
        # Vestibular chain (creates its own if not provided)
        if vestibular is None:
            vestibular = VestibularChain()
        self.vestibular = vestibular
        self.extra_axes: List[str] = extra_axes or []
        # All axes = vestibular + extra
        self.all_axes: List[str] = list(vestibular.axes) + self.extra_axes
        self._step_count: int = 0
        # FIX-014: store base col→motor gain for synaptic scaling
        self._base_col_mot_gain: float = 5.0  # FIX-S3b: 2.0→5.0

        # ── RULE S2: Structural growth parameters ──
        self._sprouted_bundles: List[SynapticBundle] = []
        self._growth_log: List[str] = []  # event log for governance
        # Entropy ledger gate: when True, structural ops are frozen
        self._structural_freeze: bool = False

        # ── Encoding layer: 2 neurons per axis (vestibular + extra) ──
        # One for regular pathway (DC/tonic), one for irregular (AC/phasic)
        self.encoding_neurons: Dict[str, Neuron] = {}
        for axis in self.all_axes:
            self.encoding_neurons[f"reg_{axis}"] = Neuron(
                _encoding_config(f"reg_{axis}"))
            self.encoding_neurons[f"irr_{axis}"] = Neuron(
                _encoding_config(f"irr_{axis}"))

        # ── Column layer: 1 neuron per axis ──
        self.column_neurons: Dict[str, Neuron] = {}
        for axis in self.all_axes:
            self.column_neurons[axis] = Neuron(_column_config(axis))

        # ── Motor layer: 3 neurons (x, y, z) ──
        self.motor_neurons: Dict[str, Neuron] = {}
        for m in ["move_x", "move_y", "move_z"]:
            self.motor_neurons[m] = Neuron(_motor_config(m))

        # Phase 3b: shared PowerRail per axis group
        # Same-axis neurons compete for energy; cross-axis don't.
        # BIO: vascular territory → local energy budget.
        # R_internal=0.3: at full load (3 motors × EMA 0.58 = I=1.74),
        # v_actual = 1.0 - 1.74×0.3 = 0.478 (healthy competition).
        # Previous R=2.0 → v_actual = -2.48 → clamp 0 → permanent brownout.
        from ..components.semiconductor import PowerRail
        self._motor_power_rails: Dict[str, PowerRail] = {
            'x': PowerRail(vdd=1.0, r_internal=0.3),
            'y': PowerRail(vdd=1.0, r_internal=0.3),
            'z': PowerRail(vdd=1.0, r_internal=0.3),
        }
        for key, neuron in self.motor_neurons.items():
            axis = self._motor_axis(key)
            neuron._shared_power_rail = self._motor_power_rails[axis]

        # ── Bundles: Afferent → Encoding ──
        self.bundles_vest_to_enc: List[SynapticBundle] = []
        for axis in vestibular.axes:
            # Regular afferent → regular encoding neuron
            b_reg = SynapticBundle(
                config=BundleConfig(
                    bundle_id=f"aff_reg_to_enc_{axis}",
                    learning_rule="stdp",
                    initial_weight=0.2,
                    stdp_lr=0.01,
                    # GainChain fix: gain 1→2. Aff pre_trace≈0.64, w≈0.2,
                    # gain=1 → I=0.085 → Enc Vm=0.37, act=0.12 (too weak).
                    # gain=2 → I=0.17 → Enc Vm≈0.8, act≈0.7 (healthy).
                    # Previous gain=10 caused saturation at act=7+.
                    synapse_gain=2.0,
                    bundle_role="feedforward",  # C-001.3: sensory input, fast
                    # Adaptive coupler: prevents Enc 100% saturation.
                    # Enc v_peak=0.35, adapt_vth=0.2 (target ~20% duty).
                    coupler_capacitance=1.0,
                    coupler_r_leak=2.0,
                    coupler_adapt_vth=0.2,
                    coupler_adapt_gm=2.0,
                    coupler_blayer_c_slow=100.0,
                    coupler_blayer_r_slow=10.0,
                    coupler_blayer_gm=0.01,
                    coupler_blayer_k=2.0,
                ),
                sources=[vestibular.afferent_regular[axis]],
                targets=[self.encoding_neurons[f"reg_{axis}"]],
            )
            self.bundles_vest_to_enc.append(b_reg)

            # Irregular afferent → irregular encoding neuron
            b_irr = SynapticBundle(
                config=BundleConfig(
                    bundle_id=f"aff_irr_to_enc_{axis}",
                    learning_rule="stdp",
                    initial_weight=0.2,
                    stdp_lr=0.01,
                    # GainChain fix: same as reg pathway
                    synapse_gain=2.0,
                    bundle_role="feedforward",  # C-001.3: sensory input, fast
                    # Adaptive coupler: same as reg pathway.
                    coupler_capacitance=1.0,
                    coupler_r_leak=2.0,
                    coupler_adapt_vth=0.2,
                    coupler_adapt_gm=2.0,
                    coupler_blayer_c_slow=100.0,
                    coupler_blayer_r_slow=10.0,
                    coupler_blayer_gm=0.01,
                    coupler_blayer_k=2.0,
                ),
                sources=[vestibular.afferent_irregular[axis]],
                targets=[self.encoding_neurons[f"irr_{axis}"]],
            )
            self.bundles_vest_to_enc.append(b_irr)

        # ── Bundles: Encoding → Column (all axes) ──
        self.bundles_enc_to_col: List[SynapticBundle] = []
        for axis in self.all_axes:
            b = SynapticBundle(
                config=BundleConfig(
                    bundle_id=f"enc_to_col_{axis}",
                    learning_rule="stdp",
                    initial_weight=0.15,
                    stdp_lr=0.008,
                    # GainChain fix: gain 1→3. Enc act≈0.7, w≈0.15,
                    # gain=1 → I=0.07 → Col Vm=0.03 (starved).
                    # gain=3 → I=0.21 → Col Vm≈1.0, act≈0.8 (healthy).
                    # Previous gain=5 + old high Enc caused saturation.
                    synapse_gain=3.0,
                    bundle_role="feedforward",  # C-001.3: encoding pathway
                    # Temporal coupler: bridges fast Enc spikes (τ=0.5) to
                    # slow Col membrane (τ=0.25) across dt=1.0.
                    # τ_couple = 1.0 × 2.0 = 2.0 → retains 60% per step.
                    # BIO: dendritic integration capacitance.
                    coupler_capacitance=1.0,
                    coupler_r_leak=2.0,
                    # C-layer adaptive: gate = target ema (firing rate).
                    # Attractor at ema=0.2 (20% duty). When ema>0.2 →
                    # MOSFET conducts → extra leak → coupler output drops.
                    # BIO: endocannabinoid release ∝ Ca²⁺ accumulation.
                    coupler_adapt_vth=0.2,    # target duty cycle
                    coupler_adapt_gm=2.0,     # moderate feedback
                    # B-layer: slow circulation feedback.
                    # τ_slow = 100×10 = 1000 steps. ema_up vs ema_down
                    # → V_slow → modulate R_leak → τ_base drifts.
                    # BIO: synaptic scaling (Turrigiano 2008).
                    coupler_blayer_c_slow=100.0,
                    coupler_blayer_r_slow=10.0,
                    coupler_blayer_gm=0.01,
                    coupler_blayer_k=2.0,
                ),
                sources=[
                    self.encoding_neurons[f"reg_{axis}"],
                    self.encoding_neurons[f"irr_{axis}"],
                ],
                targets=[self.column_neurons[axis]],
            )
            self.bundles_enc_to_col.append(b)

        # ── Bundles: Column → Motor (axis-specific + cross-axis) ──
        # BIO: vestibular nucleus → motor pools are topologically organized.
        # VOR: yaw→horizontal eye (move_x), pitch→vertical eye (move_y)
        # VSR: roll→trunk (move_z). Otolith axes via cross-axis.
        self.bundles_col_to_motor: List[SynapticBundle] = []

        # Axis-specific bundles (strong: topological bias)
        axis_motor_map = [
            ('yaw',   'move_x'),  # VOR horizontal
            ('pitch', 'move_y'),  # VOR vertical
            ('roll',  'move_z'),  # VSR trunk
        ]
        for col_ax, mot_name in axis_motor_map:
            b = SynapticBundle(
                config=BundleConfig(
                    bundle_id=f"col_{col_ax}_to_{mot_name}",
                    learning_rule="stdp",
                    initial_weight=0.4,   # C2: strong topological bias (VOR hardwire)
                    weight_max=0.5,
                    stdp_lr=0.005,
                    synapse_gain=5.0,
                    bundle_role="feedforward",
                    coupler_capacitance=1.0,
                    coupler_r_leak=2.0,
                    coupler_adapt_vth=0.2,
                    coupler_adapt_gm=2.0,
                    coupler_blayer_c_slow=100.0,
                    coupler_blayer_r_slow=10.0,
                    coupler_blayer_gm=0.01,
                    coupler_blayer_k=2.0,
                    decay_rate_by_stage=(0.5, 0.1, 0.01),
                ),
                sources=[self.column_neurons[col_ax]],
                targets=[self.motor_neurons[mot_name]],
            )
            self.bundles_col_to_motor.append(b)

        # Cross-axis bundle (weak: all columns → all motors)
        # Allows STDP to develop compensatory cross-axis pathways.
        # Otolith columns (oto_x/y/z) participate only via cross-axis.
        # BIO: convergent multisensory integration in vestibular nuclei.
        col_list = [self.column_neurons[ax] for ax in self.all_axes]
        motor_list = [self.motor_neurons[m] for m in ["move_x", "move_y", "move_z"]]
        b_cross = SynapticBundle(
            config=BundleConfig(
                bundle_id="col_to_motor_cross",
                learning_rule="stdp",
                initial_weight=0.05,  # weak: must be earned by correlation
                weight_max=0.15,      # C2: low ceiling prevents chase
                stdp_lr=0.0005,       # C2: very slow cross-axis learning
                synapse_gain=0.7,     # C2: fan-in normalized (5.0/7≈0.7)
                bundle_role="feedforward",
                coupler_capacitance=1.0,
                coupler_r_leak=2.0,
                coupler_adapt_vth=0.2,
                coupler_adapt_gm=2.0,
                coupler_blayer_c_slow=100.0,
                coupler_blayer_r_slow=10.0,
                coupler_blayer_gm=0.01,
                coupler_blayer_k=2.0,
                decay_rate_by_stage=(0.5, 0.1, 0.01),
            ),
            sources=col_list,
            targets=motor_list,
        )
        self.bundles_col_to_motor.append(b_cross)

    def step(self, mechanical_inputs: Dict[str, float], dt: float = 1.0):
        """Process one full time step.

        1. Vestibular chain processes mechanical inputs
        2. Extra axes feed directly into encoding (bypass vestibular)
        3. Afferent outputs propagate to encoding
        4. Encoding → Column → Motor
        5. STDP learning on all bundles

        Args:
            mechanical_inputs: per-axis values. Vestibular axes go through
                the chain. Extra axes (e.g. 'therm', 'dtherm') feed directly
                into encoding neurons.
        """
        # ── 1. Vestibular transduction ──
        self.vestibular.step(mechanical_inputs, dt)

        # ── 2. Afferent → Encoding (vestibular axes) ──
        for bundle in self.bundles_vest_to_enc:
            currents = bundle.propagate()
            bundle.apply_to_targets(currents, dt)

        # ── 2b. Direct input → Encoding (extra axes) ──
        # Extra axes bypass the vestibular chain entirely.
        # Signal naming: axis name = tonic (reg), 'd'+axis = phasic (irr)
        for axis in self.extra_axes:
            # Tonic input → reg encoding neuron
            tonic_val = mechanical_inputs.get(axis, 0.0)
            enc_reg = self.encoding_neurons.get(f"reg_{axis}")
            if enc_reg is not None:
                # Apply as input current (same as bundle would)
                enc_reg.step(tonic_val * 5.0, dt)  # gain=5 matches enc_to_col
            else:
                continue

            # Phasic input → irr encoding neuron
            phasic_val = mechanical_inputs.get(f"d{axis}", 0.0)
            enc_irr = self.encoding_neurons.get(f"irr_{axis}")
            if enc_irr is not None:
                enc_irr.step(phasic_val * 5.0, dt)

        # ── 3. Encoding → Column ──
        # ── 4. Column → Motor ──
        # ── 4b. Sprouted bundles ──
        # Delegated to overridable method for subclass modulation hooks.
        self._propagate_bundles(dt)

        # ── 4c. Shared PowerRail: draw total current per axis group ──
        # S0: PowerRail.draw(I_total) sets v_actual = Vdd - I*R.
        # More motor neurons on same axis → higher I → lower v_actual
        # → reduced energy recovery for all neurons in that group.
        # BIO: neurovascular coupling — vascular territory energy budget.
        for axis_key, rail in self._motor_power_rails.items():
            total_current = 0.0
            for key, mot in self.motor_neurons.items():
                if self._motor_axis(key) == axis_key:
                    # Use _activation_ema (smoothed), not transient activation.
                    # Spiking neurons have activation=0 most steps → useless.
                    # EMA tracks sustained activity level correctly.
                    total_current += mot._activation_ema * 1.0
            rail.draw(total_current)

        # ── 5. Learn (delegated to subclass if variant overlay active) ──
        # Base class calls learn() with default gate=1.0.
        # VariantAdapter overrides _do_learning() to add DA/PNN/sync gating.
        self._do_learning(dt)

        # ── 6. Metabolic tax (RULE S2: 代谢制动) ──
        self._step_count += 1
        if self._step_count % 100 == 0:
            self._apply_metabolic_tax(dt)

        # ── 7. Structural growth (RULE S2: 递归分化沉积) ──
        if self._step_count % self.SPROUT_INTERVAL == 0:
            if self._structural_freeze:
                self._growth_log.append(
                    f"FREEZE step={self._step_count} target=sprout "
                    f"reason=noether_pre_check")
            else:
                self._structural_growth(dt)

        # ── 8. Motor homeostasis (FIX-014, DEG-009) ──
        if self._step_count % 100 == 0:
            self._motor_homeostasis(dt)

        # ── 9. Mitosis check (Phase 3: neuron splitting) ──
        if self._step_count % self.SPROUT_INTERVAL == 0:
            if self._structural_freeze:
                self._growth_log.append(
                    f"FREEZE step={self._step_count} target=mitosis "
                    f"reason=noether_pre_check")
            else:
                self._check_mitosis()

    def _propagate_bundles(self, dt: float):
        """Propagate signals through enc→col, col→motor, and sprouted bundles.

        Subclasses override this to inject neuromodulatory gain scaling
        (e.g., DA × synapse current) without modifying the mother step.
        """
        for bundle in self.bundles_enc_to_col:
            currents = bundle.propagate()
            bundle.apply_to_targets(currents, dt)

        for bundle in self.bundles_col_to_motor:
            currents = bundle.propagate()
            bundle.apply_to_targets(currents, dt)

        for bundle in self._sprouted_bundles:
            currents = bundle.propagate()
            bundle.apply_to_targets(currents, dt)

    def _apply_metabolic_tax(self, dt: float):
        """RULE S2: Synaptic maintenance tax.

        Every bundle continuously drains source neuron energy.
        When a neuron's energy drops below ENERGY_FLOOR, its
        outgoing Memristor conductances decay — modeling the
        biological reality that synapse maintenance requires ATP
        (ion pump operation, receptor turnover, mitochondria).

        This creates natural selection pressure: neurons can only
        sustain a limited number of outgoing connections. Weak
        connections from energy-starved neurons die first.

        BIO: ~40% of brain energy goes to synaptic maintenance.
        REF: Harris et al. 2012 — synaptic energy budget.
        """
        # P2.1: Constant per-bundle basal drain from EnergyStore.
        # Each bundle costs a FIXED amount per tax-check (local, no global N).
        # PHYS: ion pump operation + receptor turnover = constant power per synapse.
        # When EnergyStore depletes, delivery_factor drops, neurons starve,
        # weights decay, bundles get pruned. Thermodynamic ceiling emerges.
        # Calibrated: 40 bundles × 0.0005 = 0.02 per tax (every 100 steps)
        # = 0.0002/step << P_inflow to allow growth room.
        BUNDLE_BASAL_COST = 0.0005  # energy per bundle per tax-check
        ENERGY_FLOOR = 0.3          # below this → conductance decay

        # Withdraw basal maintenance cost from EnergyStore
        energy_store = getattr(self, 'energy_store', None)
        for bundle in self.get_all_bundles():
            # P2.1: Each bundle drains constant energy from global store
            if energy_store is not None:
                energy_store.withdraw(BUNDLE_BASAL_COST)
            else:
                # Fallback: drain from source neurons (legacy)
                for src in bundle.sources:
                    src.energy = max(0.0, src.energy - 5e-5)

            # Energy-starved decay: Memristor conductance drops
            # when source neurons can't maintain the synapse
            avg_src_energy = sum(
                s.energy for s in bundle.sources
            ) / max(len(bundle.sources), 1)

            if avg_src_energy < ENERGY_FLOOR:
                # P.08: Decay rate coupled to energy deficit (not magic constant)
                # BIO: synapse protein turnover rate ∝ ATP deficit
                # Physics: decay_rate = (1 - E/E_floor) × base_rate
                deficit = 1.0 - (avg_src_energy / ENERGY_FLOOR)
                decay_rate = deficit * 0.002  # base rate × deficit
                for row in bundle._memristors:
                    for m in row:
                        dw = -decay_rate * m.w  # proportional decay
                        m.apply_dw(dw, bundle.config.weight_min,
                                   bundle.config.weight_max)

    def _structural_growth(self, dt: float):
        """RULE S2: Recursive differentiation and sedimentation.

        Phase 1 (Sprouting): When a bundle's |ξ| exceeds threshold,
        create a blind sprout — same topology, minimal weights.
        STDP decides if the sprout survives.
        Max MAX_SPROUTS_PER_INTERVAL sprouts per check (no ξ ranking).

        Phase 2 (Pruning): Dual-condition with grace period.
        Both weight AND ξ must be below thresholds after grace period.

        BIO: axon overshoot → competition → elimination.
        """
        # ── E1: System-level Xin evaluation ──
        # Leaky integrator means per-bundle Xin always returns to steady
        # state (ratio=2.0). Instead, track TOTAL system Xin across growth
        # intervals. If expansion is effective, total |Xin| per bundle
        # (mean) should decrease or stay flat despite growing N_bundles.
        all_bundles = self.get_all_bundles()
        current_total_xin = sum(abs(b.config.xin_tension) for b in all_bundles)
        current_n = len(all_bundles)
        current_mean_xin = current_total_xin / max(current_n, 1)

        prev_snap = getattr(self, '_e1_system_snapshot', None)
        if prev_snap is not None:
            prev_mean = prev_snap['mean_xin']
            ratio = current_mean_xin / max(prev_mean, 1e-6)
            self._e1_system_eval = {
                'step': self._step_count,
                'prev_n': prev_snap['n_bundles'],
                'curr_n': current_n,
                'prev_mean_xin': prev_mean,
                'curr_mean_xin': current_mean_xin,
                'ratio': ratio,
                'effective': ratio < 1.05,  # allow 5% noise margin
            }
            self._growth_log.append(
                f"E1_EVAL step={self._step_count} "
                f"N:{prev_snap['n_bundles']}→{current_n} "
                f"mean_xi:{prev_mean:.1f}→{current_mean_xin:.1f} "
                f"ratio={ratio:.3f} "
                f"{'OK' if ratio < 1.05 else 'WARN'}"
            )

        self._e1_system_snapshot = {
            'step': self._step_count,
            'n_bundles': current_n,
            'total_xin': current_total_xin,
            'mean_xin': current_mean_xin,
        }

        total_bundles = current_n
        sprout_count = 0

        # ── Phase 1: Sprouting (blind + cross-target, with concurrency limit) ──
        # Phase 7: include sprouted bundles as candidates (enables 2nd-gen sprouts
        # for non-trivial ultrametric ancestry). Depth limited to prevent explosion.
        # P2.1: No hard cap. EnergyStore depletion provides thermodynamic ceiling.
        MAX_SPROUT_DEPTH = 3  # max nesting: original→gen1→gen2→gen3
        energy_store = getattr(self, 'energy_store', None)
        store_can_afford = (energy_store is None or not energy_store.is_starving)
        if store_can_afford:
            candidates = (self.bundles_vest_to_enc
                          + self.bundles_enc_to_col
                          + self.bundles_col_to_motor
                          + [b for b in self._sprouted_bundles
                             if getattr(b, '_sprout_depth', 1) < MAX_SPROUT_DEPTH])
            for bundle in candidates:
                if sprout_count >= self.MAX_SPROUTS_PER_INTERVAL:
                    break
                xi = abs(bundle.config.xin_tension)

                # T3: fruit expand request lowers sprout threshold by 50%
                # Sustained prediction error (via fruit maturation) makes
                # structural expansion easier — the system "wants" more capacity
                sprout_threshold = self.XI_SPROUT
                is_expand = getattr(bundle, '_expand_request', False)
                if is_expand:
                    sprout_threshold *= 0.5
                    bundle._expand_request = False  # consume the request

                if xi > sprout_threshold:
                    can_afford = all(
                        s.energy > self.SPROUT_ENERGY_COST
                        for s in bundle.sources
                    )
                    if not can_afford:
                        continue
                    # Determine same-layer peer targets for cross-target mutation
                    peer_targets = None
                    if bundle in self.bundles_vest_to_enc:
                        peer_targets = list(self.encoding_neurons.values())
                    elif bundle in self.bundles_enc_to_col:
                        peer_targets = list(self.column_neurons.values())
                    elif bundle in self.bundles_col_to_motor:
                        peer_targets = list(self.motor_neurons.values())
                    else:
                        # Sprouted bundle: infer layer from bundle_id
                        bid = bundle.config.bundle_id
                        if 'col_to_motor' in bid:
                            peer_targets = list(self.motor_neurons.values())
                        elif 'enc_to_col' in bid:
                            peer_targets = list(self.column_neurons.values())
                        elif 'vest_to_enc' in bid or 'aff' in bid:
                            peer_targets = list(self.encoding_neurons.values())
                    # E1: expand-triggered sprouts get weight boost
                    child = bundle.sprout(self._step_count,
                                          peer_targets=peer_targets,
                                          expand_boost=is_expand)

                    # C2 fix: Sprouting selectivity — check activity correlation
                    # BIO: ephrin/Eph guidance ensures new axons reach functionally
                    # related targets. Without this, sprouting creates leaky cross-talk.
                    # Reject sprout if source-target correlation is too low.
                    src_ema = sum(s._activation_ema for s in child.sources) / max(len(child.sources), 1)
                    tgt_ema = sum(t._activation_ema for t in child.targets) / max(len(child.targets), 1)
                    # Correlation proxy: both active or both quiet = high correlation
                    # One active, one quiet = low correlation → reject
                    activity_match = 1.0 - abs(src_ema - tgt_ema)
                    if activity_match < 0.3:
                        continue  # reject: uncorrelated neurons, would cause leakage

                    self._sprouted_bundles.append(child)
                    for s in bundle.sources:
                        s.energy -= self.SPROUT_ENERGY_COST
                    self._growth_log.append(
                        f"SPROUT step={self._step_count} "
                        f"parent={bundle.id} child={child.id} "
                        f"xi={xi:.4f} bundles={total_bundles+1}"
                    )
                    self._on_sprout(self._step_count, bundle.id, child.id)
                    total_bundles += 1
                    sprout_count += 1

        # ── Phase 2: Pruning (dual-condition + grace period + ZCR guide) ──
        # Standing wave principle: prune antinodes (low ZCR), protect nodes (high ZCR).
        # Low ZCR = energy deadwater (signal amplified but stuck).
        # High ZCR = information highway (rapid energy exchange, signal throughput).
        # BIO: synapses in high-activity loops are stabilized (Bhatt 2009).
        ZCR_PROTECT_THRESHOLD = 0.15  # bundles with ZCR above this are protected
        to_remove = []
        for bundle in self._sprouted_bundles:
            should_prune = bundle.should_prune(current_tick=self._step_count)

            # T3: fruit contract request forces pruning of this bundle
            # Sustained overprediction (via fruit) → excess capacity removal
            if getattr(bundle, '_contract_request', False):
                should_prune = True
                bundle._contract_request = False  # consume the request

            # ZCR protection: high-ZCR bundles (wave nodes) resist pruning.
            # Only contract_request can override ZCR protection (explicit demand).
            sw = bundle.config.standing_wave_score
            if should_prune and sw > ZCR_PROTECT_THRESHOLD:
                if not getattr(bundle, '_contract_request', False):
                    should_prune = False  # ZCR protection overrides

            if should_prune:
                to_remove.append(bundle)
                for s in bundle.sources:
                    s.energy = min(1.0, s.energy + self.SPROUT_ENERGY_COST * 0.3)
                self._growth_log.append(
                    f"PRUNE step={self._step_count} "
                    f"bundle={bundle.id} w={bundle.mean_weight():.6f} "
                    f"xi={bundle.config.xin_tension:.4f} "
                    f"zcr={sw:.3f}"
                )
                self._on_prune(self._step_count, bundle.id)
        for bundle in to_remove:
            self._sprouted_bundles.remove(bundle)

        # ── Xin computation for sprouts ──
        for bundle in self._sprouted_bundles:
            bundle.compute_xin(dt)

    def _motor_homeostasis(self, dt: float):
        """FIX-014: Homeostatic regulation of motor layer.

        FatigueCapacitor in neuron.py now handles ALL motor homeostasis:
          - Each spike → charge C_fatigue → hyperpolarizing current
          - RC leak → threshold recovers when rate drops
          - Per-neuron, per-step, zero software polling

        Previous mechanisms removed (S0 violations):
          1. Threshold adaptation: used firing_rate() (software stats)
          2. Synaptic scaling: used cross-neuron energy average (no physical component)
          3. Rate homeostasis: used every-100-step polling (replaced by fatigue cap)
        """
        # All motor homeostasis is now handled by FatigueCapacitor
        # inside Neuron.step() — no external intervention needed.
        pass

    def _do_learning(self, dt: float):
        """Default learning: no gating.

        VariantAdapter overrides this to add DA + PNN + sync gating
        (P→R closure: §1E.5 of math spec v2.0).

        This virtual method pattern prevents the double-learn problem:
        without it, mother's ungated learn() runs first, then variant's
        gated learn() runs again → DA modulation is diluted.
        """
        for bundle in self.bundles_vest_to_enc:
            bundle.learn(dt)
        for bundle in self.bundles_enc_to_col:
            bundle.learn(dt)
        for bundle in self.bundles_col_to_motor:
            bundle.learn(dt)
        for bundle in self._sprouted_bundles:
            bundle.learn(dt)

    # ── Structural event hooks (Phase 6: entropy ledger) ──────

    def _on_sprout(self, tick: int, parent_id: str, child_id: str):
        """Hook called after a bundle sprout. Override for ledger."""
        pass

    def _on_prune(self, tick: int, bundle_id: str):
        """Hook called after a bundle prune. Override for ledger."""
        pass

    def _on_mitosis(self, tick: int, parent_id: str, child_id: str):
        """Hook called after a neuron mitosis. Override for ledger."""
        pass

    def _check_mitosis(self):
        """Phase 3b: Check for neuron splitting AND apoptosis.

        Scans motor neurons for:
          1. Sustained fatigue overload → split (mitosis)
          2. Sustained energy starvation → remove (apoptosis)

        S0-compliant: both triggers read component state
        (FatigueCapacitor voltage, PowerRail energy).
        """
        import random
        from copy import copy

        # ── Apoptosis: remove dead neurons first ──
        # Never kill original 3 motor neurons (move_x, move_y, move_z)
        to_die = [(key, neuron) for key, neuron in self.motor_neurons.items()
                   if neuron.should_die()
                   and key not in ('move_x', 'move_y', 'move_z')]

        for key, neuron in to_die:
            # Remove from motor_neurons
            del self.motor_neurons[key]
            # Remove bundles targeting or sourcing this neuron
            self._cleanup_dead_neuron_bundles(neuron)
            self._growth_log.append(
                f"APOPTOSIS step={self._step_count} "
                f"neuron={key} energy={neuron.energy:.4f} "
                f"motors={len(self.motor_neurons)}"
            )

        # ── Mitosis: split overloaded neurons ──
        # P0+P2: gated by efference copy efficacy + axis capacity
        to_split = []
        for key, neuron in self.motor_neurons.items():
            if not neuron.should_split():
                continue
            axis = self._motor_axis(key)
            # P2: capacity check — max neurons per axis
            axis_count = sum(1 for k in self.motor_neurons if axis in k)
            if axis_count >= self.MAX_MOTORS_PER_AXIS:
                neuron._mitosis_counter = 0  # cap reached, reset
                continue
            # P0: efficacy check — is motor output producing movement?
            efficacy = getattr(self, '_motor_efficacy', {}).get(axis, 1.0)
            if efficacy < 0.3:  # motor is ineffective
                neuron._mitosis_counter = 0  # don't waste energy
                continue
            to_split.append((key, neuron))

        for key, parent in to_split:
            child_id = f"{key}_m{self._step_count}"
            child = parent.split(child_id)

            # Assign shared PowerRail (axis-group competition)
            axis = self._motor_axis(child_id)
            if axis in self._motor_power_rails:
                child._shared_power_rail = self._motor_power_rails[axis]

            # Add child to motor neurons dict
            self.motor_neurons[child_id] = child

            # Rewire bundles
            self._rewire_after_split(parent, child)

            self._growth_log.append(
                f"MITOSIS step={self._step_count} "
                f"parent={key} child={child_id} "
                f"motors={len(self.motor_neurons)}"
            )
            self._on_mitosis(self._step_count, key, child_id)

    def _cleanup_dead_neuron_bundles(self, dead_neuron):
        """Remove bundles that reference a dead neuron.

        For incoming bundles (dead is target): remove dead from targets.
        For outgoing bundles (dead is source): remove from sprouted list.
        """
        # Remove from sprouted bundles if dead is source
        to_remove = []
        for bundle in self._sprouted_bundles:
            if dead_neuron in bundle.sources:
                to_remove.append(bundle)
        for b in to_remove:
            self._sprouted_bundles.remove(b)

        # For original bundles, remove dead from targets list
        for bundle in self.get_all_bundles():
            if dead_neuron in bundle.targets:
                bundle.targets = [t for t in bundle.targets if t is not dead_neuron]

    @staticmethod
    def _motor_axis(key: str) -> str:
        """Extract axis from motor neuron key.

        'move_x' → 'x', 'move_y_m200000' → 'y', etc.
        Used for PowerRail grouping (same-axis neurons share energy).
        Future: grouping by circulation topology instead of name prefix.
        """
        if 'move_x' in key:
            return 'x'
        elif 'move_y' in key:
            return 'y'
        elif 'move_z' in key:
            return 'z'
        return 'x'  # fallback

    def _rewire_after_split(self, parent: 'Neuron', child: 'Neuron'):
        """Rewire bundles after a neuron splits.

        Incoming bundles (where parent is TARGET):
          - Each bundle has a 50% chance of being redirected to child
          - This splits the input load between parent and child

        Outgoing bundles (where parent is SOURCE):
          - Parent keeps all existing outgoing bundles
          - Child gets weak copies (w=1e-4) of each outgoing bundle
          - STDP decides which copies survive

        BIO: dendritic arbor splits; axon branches to both daughters.
        """
        import random
        from copy import copy

        # Find all bundles where parent is a target (incoming)
        all_bundles = self.get_all_bundles()
        for bundle in all_bundles:
            if parent in bundle.targets:
                # 50% chance: redirect this target slot to child
                if random.random() < 0.5:
                    bundle.replace_target(parent, child)

        # Find all bundles where parent is a source (outgoing)
        # Create weak copies for child
        new_bundles = []
        for bundle in all_bundles:
            if parent in bundle.sources:
                # Create a weak copy for child
                child_config = copy(bundle.config)
                child_config.bundle_id = f"{bundle.id}_mc{self._step_count}"
                child_config.initial_weight = 1e-4
                child_config.xin_tension = 0.0
                child_config.fruit_state = ""
                child_config.fruit_tension_at_birth = 0.0

                # Replace parent with child in sources
                child_sources = list(bundle.sources)
                for i, src in enumerate(child_sources):
                    if src is parent:
                        child_sources[i] = child

                from .bundle import SynapticBundle
                child_bundle = SynapticBundle(
                    child_config, child_sources, list(bundle.targets)
                )
                child_bundle._sprout_tick = self._step_count
                new_bundles.append(child_bundle)

        # Add new bundles to sprouted list (will participate in learning/pruning)
        self._sprouted_bundles.extend(new_bundles)

    def get_motor_output(self) -> Dict[str, float]:
        """Get motor commands for PracticeEngine."""
        return {
            name: neuron.activation
            for name, neuron in self.motor_neurons.items()
        }

    def get_all_neurons(self) -> List[Neuron]:
        """Get all neurons in the entire system (vestibular + circuit)."""
        neurons = self.vestibular.get_all_neurons()
        neurons.extend(self.encoding_neurons.values())
        neurons.extend(self.column_neurons.values())
        neurons.extend(self.motor_neurons.values())
        return neurons

    def get_all_bundles(self) -> List[SynapticBundle]:
        """Get all bundles in the entire system (including sprouts)."""
        bundles = self.vestibular.get_all_bundles()
        bundles.extend(self.bundles_vest_to_enc)
        bundles.extend(self.bundles_enc_to_col)
        bundles.extend(self.bundles_col_to_motor)
        bundles.extend(self._sprouted_bundles)
        return bundles

    def summary(self) -> dict:
        all_n = self.get_all_neurons()
        all_b = self.get_all_bundles()
        vest_out = self.vestibular.get_output()
        motor_out = self.get_motor_output()

        return {
            "total_neurons": len(all_n),
            "total_bundles": len(all_b),
            "vestibular_output": vest_out,
            "motor_output": motor_out,
            "encoding": {k: n.summary() for k, n in self.encoding_neurons.items()},
            "column": {k: n.summary() for k, n in self.column_neurons.items()},
            "motor": {k: n.summary() for k, n in self.motor_neurons.items()},
            "bundle_weights": {b.id: b.mean_weight() for b in all_b},
        }
