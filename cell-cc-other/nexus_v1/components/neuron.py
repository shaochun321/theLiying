"""nexus_v1.components.neuron — Extended MetaNeuron.

A single neuron model that can express both:
  - Simple threshold neurons (default: 1 MOSFET, no spikes)
  - HH-equivalent neurons (multi-MOSFET, Ca²⁺ gate, AdEx spikes)

Same model, different configurations. The vestibular transduction chain
and the Hebbian circuit both use this same neuron — no second model.

Configuration via NeuronConfig:
  - mode="simple":     1 MOSFET, continuous output (current default)
  - mode="hair_cell":  3 MOSFETs (MET + K + Ca), Ca²⁺ gate, no spikes
  - mode="afferent":   1 MOSFET, AdEx spike generation, adaptation
  - mode="multi":      3 MOSFETs + spikes (full HH-equivalent)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .semiconductor import Capacitor, MOSFET, Memristor, PowerRail
from .compensation import (
    VoltageRegulator, DecouplingCapacitor,
    BiasCurrentSource, AutomaticGainControl,
    CalciumRateIntegrator, DivisiveNormalizationReceptor,
    D2Autoreceptor,
)


@dataclass
class ChannelConfig:
    """Configuration for one ion channel (= one MOSFET)."""
    name: str                    # e.g. "met", "k", "ca", "leak"
    v_threshold: float = 0.3    # activation voltage
    gm: float = 1.0             # max conductance
    tau_gate: float = 0.0       # gating time constant (0=instantaneous)
    reversal: float = 0.0       # reversal potential E_x
    sign: float = 1.0           # +1 = excitatory, -1 = inhibitory


@dataclass
class NeuronConfig:
    """Complete neuron configuration."""
    neuron_id: str = ""

    # Base parameters
    capacitance: float = 1.0
    r_leak: float = 5.0
    v_rest: float = 0.0
    inertia: float = 1.0

    # PowerRail
    vdd: float = 1.0
    r_supply: float = 0.1

    # Multi-channel (empty = single default MOSFET)
    channels: List[ChannelConfig] = field(default_factory=list)
    leak_conductance: float = 0.01
    leak_reversal: float = 0.0      # E_leak

    # Ca²⁺ subsystem (None = disabled)
    ca_capacitance: float = 0.0     # 0 = no Ca²⁺ system
    ca_r_leak: float = 50.0         # τ_Ca = ca_capacitance × ca_r_leak
    ca_release_threshold: float = 0.3
    ca_release_gm: float = 1.0

    # Spike generation (False = continuous output)
    spiking: bool = False
    v_peak: float = 1.0
    v_reset: float = -0.3
    b_adapt: float = 0.01
    tau_w: float = 0.1

    # Initial resting voltage
    v_rest: float = 0.0          # set to 0.115 for biological V_rest = -65mV

    # Traces
    trace_tau_pre: float = 20.0
    trace_tau_post: float = 20.0
    # NOTE: pre_trace and post_trace use DIFFERENT input signals
    # (see step() L338) to break STDP symmetry.
    # pre_trace ← |activation| (level)
    # post_trace ← |d(activation)/dt| (change rate)

    # Metabolism
    energy: float = 1.0
    metabolic_recovery: float = 0.001  # legacy: used if no VoltageRegulator
    basal_metabolic_cost: float = 0.0002  # cost of existing per step (ion gradient maintenance)

    # ── Compensation components (原则 7: TYPE:SEMI) ──
    # A. VoltageRegulator: activity-dependent metabolic recovery
    use_voltage_regulator: bool = False
    vr_base_rate: float = 0.001
    vr_activity_coeff: float = 0.5
    vr_max_rate: float = 5.0

    # B. DecouplingCapacitor: temporal smoothing of synaptic input
    use_decoupling_cap: bool = False
    dc_capacitance: float = 40.0
    dc_resistance: float = 5.0

    # C. BiasCurrentSource: tonic spontaneous drive
    use_bias_current: bool = False
    bc_current: float = 0.025

    # D. AutomaticGainControl: homeostatic gain adaptation
    use_agc: bool = False
    agc_base_gain: float = 20.0
    agc_target_activity: float = 1.0
    agc_tau: float = 0.1

    # E. FatigueCapacitor: spike-rate-dependent threshold adaptation
    # BIO: Na+ channel slow inactivation + Ca2+-dependent K+ channels.
    # Each spike injects Q_spike charge into a capacitor C_fatigue.
    # Fatigue voltage V_fat raises effective threshold: v_th_eff += k_fat * V_fat.
    # Capacitor leaks through R_fatigue → τ_fatigue = C_fat * R_fat.
    # This is a per-neuron, per-step RC filter — no software polling needed.
    use_fatigue: bool = False
    fatigue_capacitance: float = 1.0    # C_fatigue
    fatigue_r_leak: float = 3.0         # R_fatigue → τ=3s
    fatigue_q_spike: float = 0.05       # charge per spike
    fatigue_k: float = 0.5              # threshold gain from fatigue voltage

    # F. Mitosis (Phase 3: neuron splitting)
    # When fatigue voltage V_fat stays above mitosis_v_fat_threshold for
    # mitosis_confirm_steps consecutive steps, neuron is eligible to split.
    # BIO: sustained cellular stress (p53, HSP70) → mitotic entry.
    # S0: reads Capacitor voltage (component state), no software stats.
    enable_mitosis: bool = False
    mitosis_v_fat_threshold: float = 0.8   # V_fat > this to count
    mitosis_confirm_steps: int = 50000     # 50s sustained overload
    mitosis_max_splits: int = 4            # max splits per lineage

    # G. Apoptosis (Phase 3b: programmed cell death)
    # When energy stays below apoptosis_energy_threshold for
    # apoptosis_confirm_steps, neuron is eligible for removal.
    # S0: reads energy (PowerRail voltage × duty cycle), no software stats.
    # BIO: ATP depletion → caspase cascade → programmed cell death.
    enable_apoptosis: bool = False
    apoptosis_energy_threshold: float = 0.05   # energy < this to count
    apoptosis_confirm_steps: int = 30000       # 30s sustained starvation

    # H. CalciumRateIntegrator: spike rate → continuous signal
    # DIFFERENTIATION: only for spiking projection neurons (e.g., shadow col)
    use_calcium_rate_integrator: bool = False
    cri_capacitance: float = 1.0     # Ca²⁺ pool capacitance
    cri_r_leak: float = 50.0         # leak R → τ_CRI = 50 ms
    cri_q_spike: float = 0.2         # charge per spike
    cri_v_clamp: float = 1.0         # Zener clamp voltage

    # I. DivisiveNormalizationReceptor: input range adaptation
    # DIFFERENTIATION: only for sensory-input neurons (e.g., shadow enc)
    use_divisive_norm: bool = False
    dn_sigma: float = 1.0            # half-saturation constant
    dn_pool_capacitance: float = 5.0
    dn_pool_r_leak: float = 5.0      # → τ_pool = 25 ms

    # J. D2Autoreceptor: DA-specific negative feedback
    # DIFFERENTIATION: only for dopaminergic neurons
    use_d2_autoreceptor: bool = False
    d2_conductance: float = 0.5      # max GIRK conductance
    d2_ec50: float = 0.3             # D2R half-activation threshold
    d2_da_capacitance: float = 1.0   # local [DA] integrator
    d2_da_r_leak: float = 100.0      # → τ_D2 = 100 ms >> τ_membrane

    # DA concentration input (set externally for D2R neurons)
    da_concentration_input: float = 0.0

    # ── Maturation lifecycle (§3 of math spec) ──
    # Stages: 0=spine (fast learning), 1=column (BCM refinement), 2=area (frozen)
    maturation_stage: int = 0
    # Accumulated potential: incremented by |activation| × ε each step
    # Used for maturation transition threshold (Φ₁=50, Φ₂=500)
    potential_phi: float = 0.0
    potential_phi_epsilon: float = 0.001  # accumulation rate
    # BCM sliding threshold θ_M (only used when maturation=1/column)
    theta_m: float = 0.0
    theta_m_tau: float = 100.0  # τ_θ in BCM update


class Neuron:
    """Extended MetaNeuron — unified model for all layers.

    Same semiconductor components throughout. Configuration determines
    whether it behaves as a simple threshold, a hair cell, or a spiking
    afferent.
    """

    def __init__(self, config: NeuronConfig):
        self.id = config.neuron_id
        self.config = config

        # Core circuit: Capacitor (membrane) + PowerRail (metabolism)
        self._membrane = Capacitor(config.capacitance)
        # Initialize membrane to resting potential
        if config.v_rest != 0.0:
            self._membrane.discharge_to(config.v_rest)
        # PowerRail: can be shared (Phase 3b: axis-group competition)
        self._power = PowerRail(config.vdd, config.r_supply)
        self._shared_power_rail: Optional[PowerRail] = None  # set externally

        # Channels: if none specified, create one default MOSFET
        if config.channels:
            self._channels = {
                ch.name: MOSFET(
                    v_threshold=ch.v_threshold,
                    gm=ch.gm,
                    tau_gate=ch.tau_gate,
                )
                for ch in config.channels
            }
            self._channel_configs = {ch.name: ch for ch in config.channels}
        else:
            self._channels = {
                "default": MOSFET(v_threshold=0.3, gm=1.0)
            }
            self._channel_configs = {
                "default": ChannelConfig(
                    name="default", v_threshold=0.3, gm=1.0, reversal=0.0
                )
            }

        # Ca²⁺ subsystem (optional)
        self._ca_enabled = config.ca_capacitance > 0
        if self._ca_enabled:
            self._ca_cap = Capacitor(capacitance=config.ca_capacitance)
            self._ca_gate = MOSFET(
                v_threshold=config.ca_release_threshold,
                gm=config.ca_release_gm,
            )
            # RULE S0: Voltage clamp via MOSFET (Zener diode analog).
            # When Ca_v > 1.0, this MOSFET conducts strongly and drains
            # excess charge. gm=10 ensures hard clamp.
            # BIO: Ca²⁺ buffering proteins + active pumps (PMCA, NCX)
            self._ca_clamp = MOSFET(v_threshold=1.0, gm=10.0)
            # RULE S0: Vesicle pool as Capacitor (finite charge reservoir).
            # Release draws from this pool; pool replenishes slowly.
            # BIO: readily-releasable pool (RRP) ~50-200 vesicles
            self._vesicle_pool = Capacitor(capacitance=1.0)
            self._vesicle_pool.discharge_to(0.5)  # start half-full
            # CHECK 2: HC release≈0.28, replenish must keep up.
            # rate=0.3 → pool sustainable at steady state.
            self._vesicle_replenish_rate = 0.3
        else:
            self._ca_cap = None
            self._ca_gate = None
            self._ca_clamp = None
            self._vesicle_pool = None

        # State
        self.activation: float = 0.0
        self.release_rate: float = 0.0  # output of Ca²⁺ gate (if enabled)
        self.energy: float = config.energy
        self.heat_output: float = 0.0

        # Spike state
        self.spike_times: List[float] = []
        self._spike_heat: float = 0.0    # energy released per spike reset
        self._vr_energy_delivered: float = 0.0  # VR recovery for Noether tracking
        self._cumulative_heat_out: float = 0.0  # total energy dissipated (cumulative)
        self._cumulative_energy_in: float = 0.0 # total energy received (cumulative)
        self._w_adapt: float = 0.0      # adaptation current
        self._spiked_this_step: bool = False

        # STDP traces
        self.pre_trace: float = 0.0
        self.post_trace: float = 0.0
        self._prev_activation: float = 0.0  # for change-rate post_trace

        # Statistics
        self._current_time: float = 0.0
        self._activation_ema: float = 0.0

        # ── Compensation components ──
        # A. VoltageRegulator
        self._voltage_regulator: Optional[VoltageRegulator] = None
        if config.use_voltage_regulator:
            self._voltage_regulator = VoltageRegulator(
                base_rate=config.vr_base_rate,
                activity_coeff=config.vr_activity_coeff,
                max_rate=config.vr_max_rate,
            )

        # B. DecouplingCapacitor
        self._decoupling_cap: Optional[DecouplingCapacitor] = None
        if config.use_decoupling_cap:
            self._decoupling_cap = DecouplingCapacitor(
                capacitance=config.dc_capacitance,
                resistance=config.dc_resistance,
            )

        # C. BiasCurrentSource
        self._bias_source: Optional[BiasCurrentSource] = None
        if config.use_bias_current:
            self._bias_source = BiasCurrentSource(
                i_bias=config.bc_current,
            )

        # D. AutomaticGainControl
        self._agc: Optional[AutomaticGainControl] = None
        if config.use_agc:
            self._agc = AutomaticGainControl(
                base_gain=config.agc_base_gain,
                target_activity=config.agc_target_activity,
                tau_agc=config.agc_tau,
            )

        # E. FatigueCapacitor (RULE S0: RC filter for spike-rate adaptation)
        self._fatigue_cap: Optional[Capacitor] = None
        self._fatigue_v_th_base: float = 0.0  # original threshold to restore toward
        if config.use_fatigue:
            self._fatigue_cap = Capacitor(config.fatigue_capacitance)
            # Remember the base threshold for fatigue modulation
            if config.channels:
                self._fatigue_v_th_base = config.channels[0].v_threshold
            else:
                self._fatigue_v_th_base = 0.3

        # F. Mitosis state
        self._mitosis_counter: int = 0
        self._split_count: int = 0  # how many times this neuron has split

        # G. Apoptosis state
        self._apoptosis_counter: int = 0

        # H. CalciumRateIntegrator (DIFFERENTIATED: spiking projection only)
        self._calcium_integrator: Optional[CalciumRateIntegrator] = None
        if config.use_calcium_rate_integrator:
            self._calcium_integrator = CalciumRateIntegrator(
                capacitance=config.cri_capacitance,
                r_leak=config.cri_r_leak,
                q_spike=config.cri_q_spike,
                v_clamp=config.cri_v_clamp,
            )

        # I. DivisiveNormalizationReceptor (DIFFERENTIATED: sensory input only)
        self._dn_receptor: Optional[DivisiveNormalizationReceptor] = None
        if config.use_divisive_norm:
            self._dn_receptor = DivisiveNormalizationReceptor(
                sigma=config.dn_sigma,
                pool_capacitance=config.dn_pool_capacitance,
                pool_r_leak=config.dn_pool_r_leak,
            )

        # J. D2Autoreceptor (DIFFERENTIATED: DA neurons only)
        self._d2_receptor: Optional[D2Autoreceptor] = None
        if config.use_d2_autoreceptor:
            self._d2_receptor = D2Autoreceptor(
                conductance=config.d2_conductance,
                ec50=config.d2_ec50,
                da_capacitance=config.d2_da_capacitance,
                da_r_leak=config.d2_da_r_leak,
            )

    # ── Main computation ──────────────────────────────────────────

    def step(self, input_current: float, dt: float = 1.0) -> float:
        """Advance neuron by one time step.

        This is the unified computation path for all neuron types:
          1. Input current → PowerRail → Capacitor
          2. Membrane voltage → channel currents (multi-MOSFET)
          3. Channel currents → update membrane
          4. (Optional) Ca²⁺ accumulation → release gate
          5. (Optional) Spike detection → reset + adaptation
          6. Output: activation (continuous) or spike event

        Args:
            input_current: Total synaptic input current
            dt: Time step size

        Returns:
            activation: output signal
        """
        self._current_time += dt
        self._spiked_this_step = False

        # ── 1. Power-limited input ──
        # C. Bias current: add tonic drive
        total_input = input_current
        if self._bias_source is not None:
            total_input += self._bias_source.current()

        # I. Divisive normalization: adapt input range (BEFORE scaling)
        # Only exists in sensory-input neurons (e.g., shadow encoding)
        if self._dn_receptor is not None:
            total_input = self._dn_receptor.normalize(total_input, dt)

        # J. D2 autoreceptor: hyperpolarizing GIRK current (DA neurons only)
        # Uses da_concentration_input set externally before step()
        if self._d2_receptor is not None:
            i_girk = self._d2_receptor.compute_girk(
                self.config.da_concentration_input, dt)
            total_input += i_girk  # negative = hyperpolarizing

        scaled_current = total_input / max(self.config.inertia, 0.1)

        # D. AGC: modulate effective gain
        if self._agc is not None:
            scaled_current *= self._agc.gain()

        v_avail = self._power.draw(abs(scaled_current))
        v_ratio = v_avail / max(self._power.vdd, 0.01)
        injected = scaled_current * v_ratio

        # B. DecouplingCapacitor: smooth the input before injection
        if self._decoupling_cap is not None:
            injected = self._decoupling_cap.step(injected, dt)

        self._membrane.inject(injected, dt)

        # ── 2. Multi-channel currents ──
        vm = self._membrane.voltage
        i_total = 0.0
        i_ca = 0.0  # track Ca current separately

        if len(self._channels) == 1 and "default" in self._channels:
            # Simple mode: single MOSFET, direct output
            gate = self._channels["default"]
            gate.update_gate(vm, dt)
            # Clamp: biological saturation — neurons can't produce ∞ output
            self.activation = max(-10.0, min(10.0, gate.gated_conduct(vm)))
        else:
            # Multi-channel mode: sum ionic currents
            for name, gate in self._channels.items():
                cfg = self._channel_configs[name]
                gate.update_gate(vm, dt)
                g = gate.gated_conduct(vm)
                i_channel = cfg.sign * g * (vm - cfg.reversal)
                i_total += i_channel

                # Track Ca²⁺ current for release subsystem
                if name == "ca":
                    # FIX: In biology, E_Ca = +130 mV >> V_m always.
                    # Ca²⁺ influx depends on channel OPEN state, not
                    # driving force (which reverses in our normalized coords
                    # because vm > E_Ca_norm=1.0).
                    # Use gate activation × g_Ca as Ca influx proxy.
                    # REF: Roberts et al. 1990 — Ca influx ∝ I_Ca ∝ g_Ca × (V-E_Ca)
                    # but in real mV, (V-E_Ca) is ALWAYS negative and large.
                    i_ca = g  # gate_activation × gm = amount of Ca entering

            # Add leak current
            i_leak = self.config.leak_conductance * (vm - self.config.leak_reversal)
            i_total += i_leak

            # Inject net ionic current into membrane (negative = hyperpolarizing)
            self._membrane.inject(-i_total, dt)
            # Clamp: same saturation limit
            self.activation = max(-10.0, min(10.0, vm))

        # ── 3. Spike detection (AdEx) ──
        # MUST occur BEFORE membrane leak: in biology, Na⁺ channel
        # activation (spike) is faster (~0.5ms) than passive K⁺ leak
        # (~1-2ms). If leak runs first, Vm is destroyed before the
        # spike threshold can be tested (critical when dt >> τ_RC).
        if self.config.spiking:
            # Adaptation current reduces membrane voltage
            self._membrane.inject(-self._w_adapt, dt)

            # E. Fatigue: inject hyperpolarizing current BEFORE spike check
            # BIO: Ca²⁺-dependent K⁺ channels — sustained firing accumulates
            # Ca²⁺ → opens K⁺ channels → outward current → hyperpolarizes → slows firing.
            # This directly prevents V_m from reaching v_peak.
            if self._fatigue_cap is not None:
                self._fatigue_cap.leak(self.config.fatigue_r_leak, dt)
                v_fat = self._fatigue_cap.voltage
                # Inject hyperpolarizing current proportional to fatigue voltage
                self._membrane.inject(-self.config.fatigue_k * v_fat, dt)

            if self._membrane.voltage > self.config.v_peak:
                # ── Absolute Energy Interlock ──────────────────────
                # RULE S0: No ATP → no Na⁺/K⁺ pump → no spike.
                # BIO: depolarization block — membrane stays depolarized
                # but ion channels cannot cycle. Motor becomes paralyzed.
                # PHYS: 0.005 ≈ minimum cost of one Na⁺/K⁺ pump cycle
                # per spike (Harris et al. 2012).
                SPIKE_ENERGY_COST = 0.005
                if self.energy >= SPIKE_ENERGY_COST:
                    # Spike approved: debit energy, fire action potential
                    v_pre = self._membrane.voltage
                    self._membrane.discharge_to(self.config.v_reset)
                    v_post = self.config.v_reset
                    c_m = self._membrane.capacitance
                    self._spike_heat = 0.5 * c_m * (v_pre**2 - v_post**2)
                    # Na⁺/K⁺ pump cost routed through _spike_heat →
                    # heat_output → energy drain (L594-601). Not debited
                    # directly here to avoid double-charging.
                    self._spike_heat += SPIKE_ENERGY_COST
                    self.spike_times.append(self._current_time)
                    self._w_adapt += self.config.b_adapt
                    self._spiked_this_step = True

                    # E. Fatigue: each spike adds Q_spike voltage directly to cap
                    # (bypass inject() which multiplies by dt again)
                    if self._fatigue_cap is not None:
                        self._fatigue_cap.charge += (
                            self.config.fatigue_q_spike
                            * self._fatigue_cap.capacitance
                        )
                else:
                    # Depolarization block: V_m reached threshold but
                    # no energy to drive ion channels. Membrane leaks
                    # passively — 50% voltage decay per blocked attempt.
                    # BIO: sustained depolarization → Na⁺ channel inactivation.
                    self._membrane.discharge_to(
                        self._membrane.voltage * 0.5)

            # Adaptation decay: dw/dt = -w/τ_w
            if self.config.tau_w > 0:
                self._w_adapt *= math.exp(-dt / self.config.tau_w)

            # For spiking neurons, activation = instantaneous spike (0 or 1)
            self.activation = 1.0 if self._spiked_this_step else 0.0

        # ── 4. Membrane leak (RC discharge toward rest) ──
        # RC discharge represents passive membrane properties.
        # Occurs AFTER spike detection: spike is a fast event,
        # leak/repolarization is the slower recovery process.
        # In multi-channel mode, this works ALONGSIDE ionic leak.
        self._membrane.leak(self.config.r_leak, dt)

        # ── 5. Ca²⁺ subsystem ──
        if self._ca_enabled and self._ca_cap is not None:
            # Accumulate inward Ca current
            ca_input = max(0.0, i_ca)  # rectified (only inward)
            self._ca_cap.inject(ca_input, dt)
            self._ca_cap.leak(self.config.ca_r_leak, dt)

            # RULE S0: Ca voltage clamp via MOSFET (replaces pure-math clamp).
            # When Ca_v > 1.0, clamp MOSFET conducts and drains excess.
            # I_clamp = gm * (Ca_v - V_th) when Ca_v > V_th.
            # This charge is removed from the Ca capacitor.
            ca_v = self._ca_cap.voltage
            i_clamp = self._ca_clamp.conduct(ca_v)
            if i_clamp > 0:
                self._ca_cap.inject(-i_clamp, dt)  # drain excess

            # Release gate: MOSFET threshold on Ca²⁺ voltage
            ca_v = self._ca_cap.voltage
            raw_release = max(0.0, self._ca_gate.conduct(ca_v))

            # RULE S0: Vesicle pool limits release (replaces pure-math min()).
            # Pool replenishes at fixed rate; release draws from pool.
            # When pool is depleted, release naturally diminishes.
            self._vesicle_pool.inject(self._vesicle_replenish_rate, dt)
            pool_v = self._vesicle_pool.voltage
            # Actual release = min(gate output, pool availability)
            actual_release = min(raw_release, max(0.0, pool_v))
            # Deplete pool by the amount released
            if actual_release > 0:
                self._vesicle_pool.inject(-actual_release, dt)
            self.release_rate = actual_release
        else:
            self.release_rate = abs(self.activation)

        # H. CalciumRateIntegrator: update Ca²⁺ pool AFTER spike detection
        # Only exists in spiking projection neurons
        if self._calcium_integrator is not None:
            cri_heat = self._calcium_integrator.step(
                self._spiked_this_step, dt)
            # CRI Zener clamp heat added to neuron heat output
            self.heat_output += cri_heat

        # ── 6. Traces and metabolism ──
        # pre_trace: tracks LEVEL of activity (|activation|) — always
        # post_trace: depends on neuron type:
        #   spiking → |activation| (spikes ARE the timing signal)
        #   non-spiking → |d(act)/dt| (change rate breaks symmetry)
        # BIO: pre=AMPA (level), post=NMDA (timing for spiking, sustained for graded)
        decay_pre = math.exp(-dt / max(self.config.trace_tau_pre * 0.001, 0.001))
        decay_post = math.exp(-dt / max(self.config.trace_tau_post * 0.001, 0.001))
        self.pre_trace = self.pre_trace * decay_pre + abs(self.activation)
        if self.config.spiking:
            # Spiking: post_trace tracks spike events (natural timing)
            self.post_trace = self.post_trace * decay_post + abs(self.activation)
        else:
            # Non-spiking: post_trace tracks change rate (breaks LTP=LTD)
            act_change = abs(self.activation - self._prev_activation) / max(dt, 0.0001)
            act_change_norm = min(act_change * 0.01, 5.0)
            self.post_trace = self.post_trace * decay_post + act_change_norm
        self._prev_activation = self.activation
        # Clamp to prevent overflow in downstream propagation
        self.pre_trace = min(self.pre_trace, 10.0)
        self.post_trace = min(self.post_trace, 10.0)

        self._activation_ema += 0.01 * (abs(self.activation) - self._activation_ema)

        # Energy cost: I²R dissipation + spike reset + basal metabolic
        # ALL energy drains included in heat_output for Noether accounting.
        clamped_current = max(-100.0, min(100.0, scaled_current))
        self.heat_output = (clamped_current ** 2 * self._power.r_internal
                            + self._spike_heat
                            + self.config.basal_metabolic_cost)
        self._spike_heat = 0.0  # reset for next step
        e_before_drain = self.energy
        self.energy = max(0.0, self.energy - self.heat_output)
        actual_drain = e_before_drain - self.energy
        self.heat_output = actual_drain
        self._cumulative_heat_out += actual_drain

        # A. VoltageRegulator: activity-dependent recovery
        if self._voltage_regulator is not None:
            # Use EMA for spiking neurons (instantaneous activation is 0/1)
            activity_signal = self._activation_ema if self.config.spiking else self.activation
            recovery = self._voltage_regulator.compute_recovery(activity_signal)
        else:
            recovery = self.config.metabolic_recovery

        # Phase 3b: shared PowerRail reduces recovery.
        if self._shared_power_rail is not None:
            v_ratio = self._shared_power_rail.v_actual / max(self._shared_power_rail.vdd, 1e-6)
            recovery *= max(0.0, v_ratio)

        # Track actual recovery (clamped at 1.0 — excess is wasted)
        e_before_recovery = self.energy
        self.energy = min(1.0, self.energy + recovery)
        actual_recovery = self.energy - e_before_recovery
        self._vr_energy_delivered = actual_recovery
        self._cumulative_energy_in += actual_recovery

        # D. AGC: update activity running average
        if self._agc is not None:
            self._agc.update(self.activation, dt)

        # F. Mitosis counter: track sustained fatigue overload
        if (self.config.enable_mitosis
                and self._fatigue_cap is not None
                and self._split_count < self.config.mitosis_max_splits):
            if self._fatigue_cap.voltage > self.config.mitosis_v_fat_threshold:
                self._mitosis_counter += 1
            else:
                # Slow decay (not instant reset) — brief relief doesn't cancel
                self._mitosis_counter = max(0, self._mitosis_counter - 1)

        return self.activation

    # ── Mitosis (Phase 3: neuron splitting) ────────────────────────

    def should_split(self) -> bool:
        """Check if neuron is eligible for mitosis.

        S0-compliant: reads _mitosis_counter which is driven by
        FatigueCapacitor voltage (component state).
        """
        return (self.config.enable_mitosis
                and self._mitosis_counter >= self.config.mitosis_confirm_steps
                and self._split_count < self.config.mitosis_max_splits)

    def split(self, child_id: str) -> 'Neuron':
        """Perform mitosis: create child neuron.

        Parent (self) becomes Child_A:
          - Keeps all current state (membrane, fatigue, traces)
          - Resets mitosis counter and fatigue capacitor
          - Increments split count

        Child_B (returned):
          - Fresh state (V=0, fatigue=0)
          - Half energy of parent at split time
          - maturation_stage=0 (maximum plasticity for learning)
          - Inherits shared PowerRail (axis-group competition)
          - Negative mitosis counter (cooldown prevents cascade)

        Bundle rewiring is handled by the circuit layer (hebbian.py).

        BIO: asymmetric cell division — mother cell retains identity,
        daughter cell starts fresh with inherited genetic program.
        """
        from copy import deepcopy

        child_config = deepcopy(self.config)
        child_config.neuron_id = child_id
        # Child starts at maturation stage 0 (maximum plasticity)
        # so it can learn in even high-PNN environments
        child_config.maturation_stage = 0
        child_config.potential_phi = 0.0

        child = Neuron(child_config)
        # Daughter gets half of parent's energy at birth
        child.energy = self.energy * 0.5
        self.energy *= 0.5  # parent also loses energy (cost of division)

        # Inherit shared PowerRail (axis-group competition)
        if self._shared_power_rail is not None:
            child._shared_power_rail = self._shared_power_rail

        # Child cooldown: negative counter must reach 0 before counting
        # Total cooldown = 2 × confirm_steps before child can split
        child._mitosis_counter = -self.config.mitosis_confirm_steps

        # Reset parent's overload state
        # Parent ALSO gets cooldown (not just child) to prevent cascade.
        # Parent must wait confirm_steps before splitting again.
        self._mitosis_counter = -self.config.mitosis_confirm_steps
        if self._fatigue_cap is not None:
            self._fatigue_cap.charge = 0.0  # discharge fatigue
        self._split_count += 1

        return child

    def should_die(self) -> bool:
        """Check if neuron should undergo apoptosis.

        S0-compliant: reads energy (PowerRail voltage × duty cycle).
        BIO: sustained ATP depletion → caspase cascade → cell death.
        """
        if not self.config.enable_apoptosis:
            return False
        if self.energy < self.config.apoptosis_energy_threshold:
            self._apoptosis_counter += 1
        else:
            self._apoptosis_counter = max(0, self._apoptosis_counter - 1)
        return self._apoptosis_counter >= self.config.apoptosis_confirm_steps

    # ── Differentiated component outputs ────────────────────────────

    @property
    def calcium_rate(self) -> float:
        """Continuous rate signal from CalciumRateIntegrator.

        If CRI is enabled, returns the Ca²⁺ pool voltage (continuous,
        bounded by Zener clamp). Otherwise returns activation (fallback).

        This is the preferred pre-synaptic signal for bundles whose
        source neurons have CRI enabled.
        """
        if self._calcium_integrator is not None:
            return self._calcium_integrator.calcium_rate
        return abs(self.activation)

    # ── Output statistics ─────────────────────────────────────────

    def firing_rate(self, window: float = 0.1) -> float:
        """Compute firing rate over recent window."""
        if not self.config.spiking or not self.spike_times:
            return self._activation_ema
        t_start = self._current_time - window
        recent = [t for t in self.spike_times if t >= t_start]
        return len(recent) / max(window, 1e-6)

    def regularity(self, window: float = 0.1) -> float:
        """Compute ISI regularity (CV⁻¹) over recent window.

        Regular afferents:   CV⁻¹ > 5  → encode DC (gravity)
        Irregular afferents: CV⁻¹ < 2  → encode AC (acceleration)
        """
        if not self.config.spiking:
            return 0.0
        t_start = self._current_time - window
        recent = [t for t in self.spike_times if t >= t_start]
        if len(recent) < 3:
            return 0.0
        isis = [recent[i+1] - recent[i] for i in range(len(recent)-1)]
        mean_isi = sum(isis) / len(isis)
        if mean_isi < 1e-12:
            return 0.0
        variance = sum((x - mean_isi)**2 for x in isis) / len(isis)
        std_isi = math.sqrt(variance)
        if std_isi < 1e-12:
            return 100.0  # perfectly regular
        return mean_isi / std_isi

    def is_alive(self) -> bool:
        return self.energy > 0.0

    @property
    def spiked(self) -> bool:
        return self._spiked_this_step

    def reset_spike_history(self, keep_last: int = 1000):
        """Prune old spike times."""
        if len(self.spike_times) > keep_last:
            self.spike_times = self.spike_times[-keep_last:]

    # ── Summary ───────────────────────────────────────────────────

    def summary(self) -> dict:
        return {
            "id": self.id,
            "V_mem": self._membrane.voltage,
            "activation": self.activation,
            "release_rate": self.release_rate,
            "firing_rate": self.firing_rate(),
            "regularity": self.regularity(),
            "energy": self.energy,
            "n_spikes": len(self.spike_times),
            "n_channels": len(self._channels),
            "ca_enabled": self._ca_enabled,
            "spiking": self.config.spiking,
        }
