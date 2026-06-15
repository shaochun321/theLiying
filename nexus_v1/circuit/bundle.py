"""nexus_v1.circuit.bundle — MetaSynapticBundle with STDP.

Connects source neurons to target neurons via Memristors.
STDP learning rule operates on pre/post traces from the Neurons.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

from ..components.semiconductor import Memristor
from ..components.neuron import Neuron
from ..components.temporal_coupler import TemporalCoupler


@dataclass
class BundleConfig:
    """Configuration for a synaptic bundle."""
    bundle_id: str = ""
    learning_rule: str = "stdp"   # "stdp", "bcm", "frozen"
    bundle_inertia: float = 1.0
    initial_weight: float = 0.1
    stdp_lr: float = 0.01
    weight_min: float = 0.0
    weight_max: float = 1.0
    # REF: Synaptic gain = V_drive / V_norm
    # In biology, synaptic driving force ~60 mV out of 130 mV range = 0.46
    # But the dt=0.001 scales inject() by dt, so we need to compensate
    # Effective gain = V_drive_norm / dt_scale
    synapse_gain: float = 1.0     # default 1.0, increase for stronger coupling

    # ── Circulation role differentiation (concept C-001.3) ──
    # Propagation delay in steps (models axon conduction time)
    # REF: myelinated axon ~100m/s, unmyelinated ~1m/s
    # feedforward=0, feedback=5, cross_axis=2, shadow=10
    delay_steps: int = 0
    # Bundle role tag for circulation analysis
    bundle_role: str = "feedforward"  # feedforward|feedback|cross_axis|shadow

    # ── Xin tension & fruit (§7 of math spec) ──
    # Accumulated prediction residual (§7.2)
    xin_tension: float = 0.0
    # Fruit lifecycle: None=∅, "dormant", "active" (§7.3)
    fruit_state: str = ""         # "" = no fruit
    fruit_tension_at_birth: float = 0.0
    fruit_threshold: float = 0.5  # |ξ| > ξ* to create dormant fruit

    # ── Maturation-linked plasticity (§3.2) ──
    # Plasticity rates indexed by maturation stage [spine, column, area]
    plasticity_by_stage: tuple = (0.18, 0.01, 0.001)
    decay_rate_by_stage: tuple = (0.025, 0.005, 0.001)

    # ── Remodeling energy cost (shadow layer §2.2) ──
    remodel_cost_kappa: float = 0.0  # 0 = no cost (main system); >0 for shadow

    # ── Temporal coupler (dendritic integration) ──
    # When coupler_capacitance > 0, a TemporalCoupler is created per target.
    # BIO: dendritic membrane capacitance bridges fast synaptic τ and slow somatic τ.
    # τ_couple = coupler_capacitance × coupler_r_leak should be ≈ dt.
    coupler_capacitance: float = 0.0    # 0 = no coupler (bypass)
    coupler_r_leak: float = 2.0         # leak resistance
    coupler_v_clamp: float = 2.0        # saturation voltage
    # C-layer: adaptive feedback (retrograde messenger).
    # MOSFET gate = downstream ema. When ema > adapt_vth → extra leak.
    coupler_adapt_vth: float = 0.0      # 0 = no adaptation
    coupler_adapt_gm: float = 0.0       # transconductance
    # B-layer: slow circulation feedback (synaptic scaling).
    # Differential comparator: ema_up vs ema_down → modulate τ_base.
    # Attractor: ema_up ≈ ema_down (impedance matched).
    # Set c_slow > 0 to enable. τ_slow = c_slow × r_slow.
    coupler_blayer_c_slow: float = 0.0  # 0 = B-layer disabled
    coupler_blayer_r_slow: float = 10.0 # slow leak resistance
    coupler_blayer_gm: float = 0.01     # MOSFET transconductance
    coupler_blayer_k: float = 2.0       # R_leak modulation gain

    # ── Silent synapse (shadow layer §3) ──
    is_silent: bool = False
    silent_snapshot: dict = field(default_factory=dict)  # {w, xin, tick}
    silence_threshold: float = 0.005  # w < this → go silent
    reactivation_threshold: float = 0.8  # cos_sim > this → reactivate

    # ── C4: Standing wave detection (垫支 / 驻波) ──
    # O(1) online zero-crossing rate of dξ/dt.
    # ZCR ∈ [0.05, 0.3] → periodic oscillation → standing wave candidate.
    # Updated every 1000 steps.
    _sw_xin_prev: float = 0.0
    _sw_dxi_sign: int = 1
    _sw_zero_crossings: int = 0
    _sw_step_count: int = 0
    standing_wave_score: float = 0.0


class SynapticBundle:
    """A bundle of synaptic connections from sources to targets.

    Each (source, target) pair has a Memristor whose conductance
    determines the connection strength.

    STDP: pre-before-post → potentiate, post-before-pre → depress.
    """

    def __init__(self, config: BundleConfig,
                 sources: List[Neuron], targets: List[Neuron]):
        self.id = config.bundle_id
        self.config = config
        self.sources = sources
        self.targets = targets

        # Create memristor matrix: sources × targets
        # Symmetry breaking: each weight gets deterministic variation
        # based on (bundle_id, source_idx, target_idx) hash.
        # This breaks the self-locking cycle where uniform weights
        # → uniform activity → uniform STDP → unchanged weights.
        # BIO: synaptic strengths are never perfectly uniform in vivo.
        self._memristors: List[List[Memristor]] = []
        for i_s, _s in enumerate(sources):
            row = []
            for i_t, _t in enumerate(targets):
                # Deterministic variation: ±25% of initial_weight
                seed = hash((config.bundle_id, i_s, i_t)) % 10000
                variation = (seed / 10000.0 - 0.5) * 0.5  # [-0.25, +0.25]
                w0 = config.initial_weight * (1.0 + variation)
                w0 = max(config.weight_min, min(config.weight_max, w0))
                m = Memristor(w=w0)
                row.append(m)
            self._memristors.append(row)

        self.transport_cost: float = 0.0

        # ── Temporal couplers (dendritic integration) ──
        # One coupler per target. Bridges fast→slow timescales.
        self._couplers: List[TemporalCoupler] = []
        if config.coupler_capacitance > 0:
            for _ in targets:
                self._couplers.append(TemporalCoupler(
                    capacitance=config.coupler_capacitance,
                    r_leak=config.coupler_r_leak,
                    v_clamp=config.coupler_v_clamp,
                    adapt_vth=config.coupler_adapt_vth,
                    adapt_gm=config.coupler_adapt_gm,
                    blayer_c_slow=config.coupler_blayer_c_slow,
                    blayer_r_slow=config.coupler_blayer_r_slow,
                    blayer_gm=config.coupler_blayer_gm,
                    blayer_k=config.coupler_blayer_k,
                ))

        # ── Delay buffer (C-001.3: axon conduction delay) ──
        self._delay_buffer: list = []  # FIFO queue of target_currents

        # ── Xin state (§7 of math spec) ──
        # Previous source activations for predict-compare
        self._prev_source_acts: List[float] = [0.0] * len(sources)
        # Accumulated Xin consumed (for conservation audit)
        self._xin_consumed: float = 0.0

    @property
    def n_sources(self) -> int:
        return len(self.sources)

    @property
    def n_targets(self) -> int:
        return len(self.targets)

    def propagate(self) -> List[float]:
        """T-phase: propagate source signals through memristors to targets.

        For spiking neurons: uses pre_trace (exponentially decaying history)
        to model EPSP time course (REF: biological EPSP lasts 5-10 ms).

        For non-spiking neurons: uses instantaneous activation directly
        (their output is continuous and doesn't need temporal spread).

        Returns list of target input currents.
        """
        target_currents = [0.0] * self.n_targets
        self.transport_cost = 0.0

        for i, src in enumerate(self.sources):
            if not src.is_alive():
                continue
            # Source signal selection:
            #   1. Spiking + CRI: use calcium_rate (continuous, bounded by Zener)
            #      BIO: downstream reads CaMKII concentration, not spikes
            #   2. Spiking (no CRI): use pre_trace (EPSP-like temporal spread)
            #   3. Non-spiking: use instantaneous activation
            if src.config.spiking and hasattr(src, '_calcium_integrator') and src._calcium_integrator is not None:
                a_src = src.calcium_rate
            elif src.config.spiking:
                a_src = src.pre_trace
            else:
                a_src = src.activation
            if abs(a_src) < 1e-12:
                continue

            for j in range(self.n_targets):
                current = self._memristors[i][j].conduct(a_src)
                current *= self.config.synapse_gain
                target_currents[j] += current
                self.transport_cost += abs(current) * 0.001

        # ── Apply propagation delay if configured ──
        if self.config.delay_steps > 0:
            self._delay_buffer.append(target_currents)
            if len(self._delay_buffer) > self.config.delay_steps:
                return self._delay_buffer.pop(0)
            return [0.0] * self.n_targets  # buffer filling, output zeros

        return target_currents

    def apply_to_targets(self, target_currents: List[float], dt: float = 0.001):
        """Inject propagated currents into target neurons.

        If temporal couplers are present, current passes through them first.
        The coupler integrates sparse fast pulses into smooth slow current,
        bridging the timescale gap between source and target layers.
        """
        for j, tgt in enumerate(self.targets):
            if j < len(target_currents):
                current = target_currents[j]
                # Temporal coupler: bridge timescale gap
                # Passes downstream ema for C-layer and upstream ema for B-layer.
                # BIO: retrograde messenger (C) + synaptic scaling (B).
                if self._couplers and j < len(self._couplers):
                    act_down = tgt._activation_ema  # [0, 1]
                    # B-layer: mean upstream (source) ema
                    ema_up = (sum(s._activation_ema for s in self.sources)
                              / max(len(self.sources), 1))
                    current = self._couplers[j].step(
                        current, dt,
                        vm_downstream=act_down,
                        ema_upstream=ema_up)
                tgt.step(current, dt)

    def learn(self, dt: float = 1.0, plasticity_gate: float = 1.0):
        """Apply unified learning rule (§4.4 of math spec).

        Learning rule is determined by target neuron maturation stage:
          - spine (M=0): STDP with soft bounds
          - column (M=1): BCM with sliding threshold
          - area (M=2): frozen

        Args:
            dt: Time step.
            plasticity_gate: PNN-derived gate g_ℓ ∈ [0,1]. Multiplicative.
        """
        if self.config.learning_rule == "frozen":
            return

        # Determine effective learning rule from target maturation
        # Use max maturation of targets (§3.3: max_{j∈T_k} M_j)
        max_maturation = 0
        for tgt in self.targets:
            m = getattr(tgt.config, 'maturation_stage', 0)
            if m > max_maturation:
                max_maturation = m

        # Override learning rule from maturation
        if max_maturation == 2:
            return  # frozen: area stage

        # Cross-axis bundles use Hebbian+decay instead of BCM (FIX-018).
        # WHY: BCM theta tracks target neuron's TOTAL activity (dominated
        # by intra-axis enc→col input). For cross-modal bundles, this means
        # (a_tgt - θ) is determined by vestibular, not thermal correlation.
        # → BCM kills the strongest cross-modal weights first (competitive
        #   elimination of exactly the signal we want to learn).
        # BIO: Association fibers (connecting different cortical areas)
        # have different plasticity rules than local circuits.
        # REF: Abbott & Nelson 2000 — correlation-based vs competition-based.
        if self.config.bundle_role == "cross_axis":
            effective_rule = "hebbian_decay"
        else:
            effective_rule = "stdp" if max_maturation == 0 else "bcm"

        # Get maturation-dependent plasticity rate
        plasticity = self.config.plasticity_by_stage[
            min(max_maturation, len(self.config.plasticity_by_stage) - 1)
        ]

        for i, src in enumerate(self.sources):
            for j, tgt in enumerate(self.targets):
                m = self._memristors[i][j]

                if effective_rule == "stdp":
                    # §4.1: STDP with multiplicative soft bounds
                    ltp = src.pre_trace * tgt.post_trace
                    decay = self.config.decay_rate_by_stage[0] * m.w
                    dw_raw = self.config.stdp_lr * dt * (ltp - decay)

                    # Multiplicative bounds (§4.1)
                    if dw_raw > 0:
                        dw = dw_raw * (self.config.weight_max - m.w)
                    else:
                        dw = dw_raw * (m.w - self.config.weight_min)

                    # Apply plasticity gate (PNN) and maturation rate
                    dw *= plasticity_gate * plasticity
                    m.apply_dw(dw, self.config.weight_min, self.config.weight_max)

                elif effective_rule == "bcm":
                    # §4.2: BCM with sliding threshold
                    # FIX-2: Use calcium_rate for spiking+CRI neurons.
                    # _activation_ema ≈ 0 for spiking neurons (0 between spikes).
                    # calcium_rate is the continuous signal (CaMKII concentration)
                    # that downstream reads — BCM must use the same signal.
                    # BIO: BCM's activity variable = postsynaptic [Ca²⁺].
                    post = self._get_activity_signal(tgt)
                    pre = self._get_activity_signal(src)
                    theta = getattr(tgt.config, 'theta_m', post)
                    dw = (self.config.stdp_lr * dt * pre
                          * post * (post - theta)
                          * plasticity_gate * plasticity)
                    m.apply_dw(dw, self.config.weight_min, self.config.weight_max)

                    # Update sliding threshold: dθ/dt = (a²_j - θ) / τ_θ
                    tau_theta = getattr(tgt.config, 'theta_m_tau', 100.0)
                    if tau_theta > 0:
                        alpha_theta = min(dt / tau_theta, 1.0)
                        tgt.config.theta_m = (
                            tgt.config.theta_m * (1.0 - alpha_theta)
                            + post ** 2 * alpha_theta
                        )

                elif effective_rule == "hebbian_decay":
                    # §4.3 FIX-018: Pure Hebbian with weight decay.
                    # dw = η × |a_src| × |a_tgt| - λ × w
                    # No competitive theta → directional correlations survive.
                    # Decay term prevents unbounded growth (replaces BCM's role).
                    # BIO: association fiber plasticity (Abbott & Nelson 2000).
                    # FIX-2: use calcium_rate for spiking+CRI neurons.
                    pre = self._get_activity_signal(src)
                    post = self._get_activity_signal(tgt)
                    decay_rate = self.config.decay_rate_by_stage[
                        min(max_maturation, len(self.config.decay_rate_by_stage) - 1)
                    ]
                    growth = self.config.stdp_lr * dt * pre * post
                    decay = decay_rate * dt * m.w
                    dw = (growth - decay) * plasticity_gate * plasticity
                    m.apply_dw(dw, self.config.weight_min, self.config.weight_max)

        # ── E_remodel: STDP weight changes consume energy (§2.2) ──
        if self.config.remodel_cost_kappa > 0:
            for i, src in enumerate(self.sources):
                total_dw = 0.0
                for j in range(self.n_targets):
                    # Approximate |dw| from weight change since last step
                    total_dw += abs(self._memristors[i][j].w
                                    - getattr(self, '_prev_weights', [[0.0]*self.n_targets]*self.n_sources)[i][j])
                e_cost = self.config.remodel_cost_kappa * total_dw
                src.energy = max(0.0, src.energy - e_cost)
            # Store current weights for next step comparison
            self._prev_weights = [
                [m.w for m in row] for row in self._memristors
            ]

    @staticmethod
    def _get_activity_signal(neuron: Neuron) -> float:
        """Get the continuous activity signal for a neuron.

        Matches propagate()'s signal selection logic:
          1. Spiking + CRI: calcium_rate (CaMKII concentration)
          2. Spiking (no CRI): pre_trace (EPSP temporal spread)
          3. Non-spiking: _activation_ema (continuous output)

        FIX-2: BCM and Hebbian learning must read the SAME signal
        that propagate() sends downstream. Otherwise learning and
        transmission are decoupled — BCM sees post≈0 while the
        actual transmitted signal is calcium_rate≈0.8.
        """
        if (neuron.config.spiking
                and hasattr(neuron, '_calcium_integrator')
                and neuron._calcium_integrator is not None):
            return neuron.calcium_rate
        elif neuron.config.spiking:
            return neuron.pre_trace
        else:
            return neuron._activation_ema

    def weight_matrix(self) -> List[List[float]]:
        """Get current weight matrix."""
        return [[m.w for m in row] for row in self._memristors]

    def mean_weight(self) -> float:
        total = sum(m.w for row in self._memristors for m in row)
        count = sum(len(row) for row in self._memristors)
        return total / max(count, 1)

    def summary(self) -> dict:
        return {
            "id": self.id,
            "n_sources": self.n_sources,
            "n_targets": self.n_targets,
            "mean_weight": self.mean_weight(),
            "learning_rule": self.config.learning_rule,
            "transport_cost": self.transport_cost,
            "xin_tension": self.config.xin_tension,
            "fruit_state": self.config.fruit_state,
        }

    # ── Xin tension (§7.2 of math spec) ────────────────────────

    def compute_xin(self, dt: float = 1.0):
        """Predict-compare: accumulate Xin tension (§7.2).

        Prediction: ŷ_j = Σ_i W_ij × a_i(t-dt)
        Residual: ξ += mean_j(ŷ_j - a_j(t)) × dt

        NOTE: Residual is normalized by N_targets to prevent fan-in bias.
        Without normalization, a 7×3 cross bundle accumulates 21× faster
        than a 1×1 axis bundle, causing false expand requests.
        BIO: per-synapse prediction error, not aggregate.
        """
        total_residual = 0.0
        for j, tgt in enumerate(self.targets):
            # Predict: use previous source activations + current weights
            predicted = 0.0
            for i in range(self.n_sources):
                predicted += self._memristors[i][j].w * self._prev_source_acts[i]
            # Actual
            actual = tgt._activation_ema  # M4: continuous prediction target
            total_residual += (predicted - actual)

        # Normalize by number of targets (fan-in correction)
        # This makes Xin accumulation rate independent of bundle topology.
        n_targets = max(len(self.targets), 1)
        total_residual /= n_targets

        # Accumulate tension with leak (prevents unbounded growth)
        # BIO: prediction error habituates — sustained mismatches gradually
        # accepted. Without leak, Xin diverges over long runs (>200k steps).
        # τ_leak = 1000s → very slow decay, preserves structural dynamics.
        XIN_LEAK_TAU = 1000.0  # seconds
        leak_factor = math.exp(-dt / XIN_LEAK_TAU)
        xin_leaked = self.config.xin_tension * (1.0 - leak_factor)
        self.config.xin_tension = self.config.xin_tension * leak_factor + total_residual * dt
        # Noether Xin conservation: SIGNED tracking with rolling ledger.
        # Exact: xin(t) = xin(0) + Σ_injected - Σ_leaked
        # Rolling checkpoint every 10000 steps prevents catastrophic
        # cancellation when accumulators grow to millions (float64 loses
        # ~6 digits precision at 10^6 base, making micro-increments vanish).
        self._xin_produced = getattr(self, '_xin_produced', 0.0) + total_residual * dt
        self._xin_consumed = getattr(self, '_xin_consumed', 0.0) + xin_leaked
        self._xin_ledger_steps = getattr(self, '_xin_ledger_steps', 0) + 1
        if self._xin_ledger_steps >= 10000:
            # Checkpoint: fold accumulators into a checkpoint offset
            self._xin_checkpoint_produced = (
                getattr(self, '_xin_checkpoint_produced', 0.0) + self._xin_produced)
            self._xin_checkpoint_consumed = (
                getattr(self, '_xin_checkpoint_consumed', 0.0) + self._xin_consumed)
            self._xin_produced = 0.0
            self._xin_consumed = 0.0
            self._xin_ledger_steps = 0

        # ── C4: Standing wave detection (O(1) online) ──
        dxi = self.config.xin_tension - self.config._sw_xin_prev
        self.config._sw_xin_prev = self.config.xin_tension
        cur_sign = 1 if dxi >= 0 else -1
        if cur_sign != self.config._sw_dxi_sign:
            self.config._sw_zero_crossings += 1
        self.config._sw_dxi_sign = cur_sign
        self.config._sw_step_count += 1
        # Update ZCR every 1000 steps
        if self.config._sw_step_count >= 1000:
            self.config.standing_wave_score = (
                self.config._sw_zero_crossings / 1000.0)
            self.config._sw_zero_crossings = 0
            self.config._sw_step_count = 0

        # Store current source activations for next step
        for i, src in enumerate(self.sources):
            self._prev_source_acts[i] = src._activation_ema  # M4: continuous

    def update_fruit(self, dt: float = 1.0,
                     da_concentration: float = 0.0) -> str:
        """T3: Update fruit lifecycle — structural event trigger (§7.3).

        Fruit converts SUSTAINED Xin tension into structural decisions.
        No weight modifications — fruit triggers sprout/prune candidates.

        State machine:
          ∅ → dormant:  |ξ| > threshold (persistent prediction error)
          dormant → mature: tension sustained for maturation period
          mature → trigger: structural event dispatched
          trigger → ∅: cleanup

        Returns:
            Event string: '', 'dormant_created', 'matured',
            'trigger_expand', 'trigger_contract'
        """
        xi = self.config.xin_tension
        state = self.config.fruit_state

        if state == "":
            # ∅ → dormant: when |ξ| exceeds threshold
            if abs(xi) > self.config.fruit_threshold:
                self.config.fruit_state = "dormant"
                self.config.fruit_tension_at_birth = xi
                self._fruit_age = 0
                return "dormant_created"

        elif state == "dormant":
            self._fruit_age = getattr(self, '_fruit_age', 0) + 1
            birth = self.config.fruit_tension_at_birth

            # Maturation: tension must stay same-sign for 500 ticks (0.5s)
            # This filters transient fluctuations — only sustained errors trigger
            MATURATION_TICKS = 500

            # C5 gate: maturation requires low DA (homeostatic balance).
            # DA low = body not in active exploration → safe to commit structure.
            # BIO: critical period closure requires stable activity patterns
            # (Hensch 2005 — experience-dependent plasticity).
            # NOTE: Standing wave gate REMOVED — empirically, ZCR is bimodal
            # (0.000 = monotonic or 1.000 = noise), never in any usable range.
            # ZCR is still tracked as a diagnostic but doesn't gate maturation.
            DA_MATURE_THRESHOLD = 0.15  # DA must be below this
            da_ok = da_concentration < DA_MATURE_THRESHOLD

            if (xi * birth > 0 and self._fruit_age >= MATURATION_TICKS
                    and da_ok):
                # Sustained tension + homeostatic balance → mature
                self.config.fruit_state = "mature"
                return "matured"

            # Decay: tension reversal kills the fruit
            if xi * birth < 0 and abs(xi) > self.config.fruit_threshold * 0.5:
                # Fruit consumed: tension reversal kills it. No tension change.
                self.config.fruit_state = ""
                self.config.fruit_tension_at_birth = 0.0
                self._fruit_age = 0
                return "consumed"

            # Timeout: if tension drops below threshold for too long
            if self._fruit_age > MATURATION_TICKS * 3 and abs(xi) < self.config.fruit_threshold * 0.3:
                self.config.fruit_state = ""
                self.config.fruit_tension_at_birth = 0.0
                self._fruit_age = 0
                return ""

        elif state == "mature":
            birth = self.config.fruit_tension_at_birth

            # Dispatch structural event based on tension sign:
            #   Positive ξ (underprediction) → expand (need more capacity)
            #   Negative ξ (overprediction) → contract (excess capacity)
            # BIO: prediction error drives cortical map expansion/contraction
            # REF: Merzenich 1984 — use-dependent cortical reorganization
            # Track tension release for Noether Xin conservation:
            # xin_tension *= 0.5 removes half the tension.
            xin_released = self.config.xin_tension * 0.5
            self._xin_consumed = getattr(self, '_xin_consumed', 0.0) + xin_released
            self.config.fruit_state = ""
            self.config.xin_tension *= 0.5  # partial tension release
            self.config.fruit_tension_at_birth = 0.0
            self._fruit_age = 0

            if birth > 0:
                # Underprediction → expand: this bundle needs more connections
                # Sets a flag that hebbian._structural_growth can read
                self._expand_request = True
                # E1: Snapshot Xin for post-expansion self-check.
                # After EVAL_DELAY steps, we check if |Xin| decreased.
                # If not, expansion was ineffective.
                # E1: Record expand event for system-level evaluation.
                # Individual bundle Xin always returns to steady state
                # (ratio=2.0, leaky integrator math). Instead, the expand
                # is evaluated by hebbian._structural_growth which can
                # measure system-level Xin redistribution.
                self._expand_eval_step = None  # set by hebbian when sprout happens
                return "trigger_expand"
            else:
                # Overprediction → contract: this bundle has excess capacity
                self._contract_request = True
                return "trigger_contract"

        return ""

    # ── Structural growth (RULE S2: 递归分化沉积) ─────────────

    # Birth tick for grace period tracking (0 = original bundle, never pruned)
    _sprout_tick: int = 0
    _prune_counter: int = 0

    # ── Mitosis rewiring (Phase 3) ────────────────────────────────

    def replace_source(self, old, new) -> bool:
        """Replace a source neuron reference (for mitosis rewiring).

        After a neuron splits, some bundles that used the parent as source
        need to point to the child instead.
        """
        for i, src in enumerate(self.sources):
            if src is old:
                self.sources[i] = new
                return True
        return False

    def replace_target(self, old, new) -> bool:
        """Replace a target neuron reference (for mitosis rewiring).

        After a neuron splits, some bundles that used the parent as target
        need to point to the child instead.
        """
        for i, tgt in enumerate(self.targets):
            if tgt is old:
                self.targets[i] = new
                return True
        return False

    def sprout(self, tick: int, peer_targets=None,
               expand_boost: bool = False) -> 'SynapticBundle':
        """母本分化: create a child bundle from this parent.

        RULE S2 Phase 1: Blind sprouting.
        - Child inherits parent's sources and targets (same topology)
        - Child starts with minimal Memristor conductance (1e-4)
          UNLESS expand_boost=True → 30% of parent's mean weight
        - Child is at maturation_stage=0 (maximum plasticity)
        - STDP will decide if child survives; pruning removes failures
        - Parent's ξ tension is halved (tension release)
        - If peer_targets provided, each target has CROSS_PROB chance
          of being replaced by a random peer (cross-target mutation)

        BIO: axon overshoot → synaptic competition → pruning.
        Cross-target: axonal growth cones exploring adjacent territory.
        The structure is NOT optimally guided; selection happens POST-HOC.

        expand_boost: When True (from Fruit expand), child inherits
        30% of parent weight. BIO: branching axons carry existing
        receptor density (Bhatt et al. 2009 — branch-specific AMPA).
        E1 finding: without boost, sprouts are 0.025% of parent weight
        and have zero effect on prediction error (ratio=2.0).

        Args:
            tick: Current step count (for unique ID generation).
            peer_targets: Optional list of same-layer neurons for cross-target
                mutation. If None, child copies parent's targets exactly.
            expand_boost: If True, initialize with 30% of parent weight.

        Returns:
            New SynapticBundle (the sprout).
        """
        import random
        from copy import copy

        CROSS_PROB = 0.3  # probability each target is replaced by a peer
        EXPAND_WEIGHT_FRACTION = 0.3  # fraction of parent weight for expand sprouts

        child_config = copy(self.config)
        child_config.bundle_id = f"{self.id}_s{tick}"

        # E1: expand-triggered sprouts inherit partial parent weight.
        # Standard sprouts still start minimal (STDP decides survival).
        if expand_boost:
            child_config.initial_weight = self.mean_weight() * EXPAND_WEIGHT_FRACTION
        else:
            child_config.initial_weight = 1e-4

        child_config.xin_tension = 0.0
        child_config.fruit_state = ""
        child_config.fruit_tension_at_birth = 0.0

        # Cross-target mutation: replace some targets with same-layer peers
        child_targets = list(self.targets)
        if peer_targets and len(peer_targets) > 1:
            for i in range(len(child_targets)):
                if random.random() < CROSS_PROB:
                    # Pick a random peer that ISN'T the current target
                    candidates = [p for p in peer_targets if p is not child_targets[i]]
                    if candidates:
                        child_targets[i] = random.choice(candidates)

        child = SynapticBundle(child_config, self.sources, child_targets)
        child._sprout_tick = tick
        # Phase 7: track sprout generation depth for ultrametric ancestry
        child._sprout_depth = getattr(self, '_sprout_depth', 0) + 1

        # Parent tension release
        self.config.xin_tension *= 0.5

        return child

    # ── Pruning (RULE S2 Phase 2) ──

    def should_prune(self, current_tick: int,
                     w_threshold: float = 0.005,
                     grace_period: int = 5000,
                     sustain_steps: int = 2) -> bool:
        """Check if this bundle should be pruned.

        Weight-based pruning with grace period:
        1. Grace period: new sprouts are immune for grace_period steps
           (gives STDP time to decide)
        2. Weight condition: mean_weight < w_threshold after grace period
           means STDP + metabolic tax have judged this pathway useless

        NOTE: ξ condition was removed because sprouts inherit the same
        signal flow as their parent and always accumulate high ξ. The
        weight condition is sufficient — metabolic tax continuously
        decays weights of energy-starved connections, so weak weight
        after grace period = genuinely unused pathway.

        Original bundles (_sprout_tick=0) are NEVER pruned — only sprouts.

        BIO: synaptic elimination during development. Weak synapses
        that aren't strengthened by activity-dependent mechanisms are
        removed by microglia.

        Args:
            current_tick: Current simulation step.
            w_threshold: Weight below which bundle is considered inactive.
            grace_period: Steps after sprouting during which pruning is blocked.
            sustain_steps: Consecutive checks weight must stay below threshold.

        Returns:
            True if bundle should be removed.
        """
        # Original bundles never pruned
        if self._sprout_tick == 0:
            return False

        # Grace period: too young to judge
        age = current_tick - self._sprout_tick
        if age < grace_period:
            return False

        # Weight condition: STDP + metabolic tax have spoken
        if self.mean_weight() < w_threshold:
            self._prune_counter += 1
        else:
            self._prune_counter = 0

        return self._prune_counter >= sustain_steps



