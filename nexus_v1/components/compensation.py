"""nexus_v1.components.compensation — Semiconductor Compensation Components.

TYPE:SEMI — Four semiconductor-style compensation mechanisms:

    A. VoltageRegulator (LDO)    — activity-dependent metabolic recovery
    B. DecouplingCapacitor       — energy buffer / membrane voltage smoothing
    C. BiasCurrentSource         — tonic spontaneous baseline activity
    D. AutomaticGainControl      — homeostatic plasticity (negative feedback)

Design Derivation:
    See docs/modeling_003_compensation_fourier.md

    A. dE/dt = base + coeff × |activation|
       Matches metabolic recovery to dissipation rate.
       REF: Attwell & Laughlin 2001 — neural energy budget

    B. τ_buffer = C_buffer × R_buffer >> ISI
       Smooths bursty input into sustained drive.
       REF: Koch 1999 — cable theory, dendritic filtering

    C. I_bias = V_target / R_leak
       Keeps membrane near threshold even without input.
       REF: Goldberg 2000 — vestibular afferent tonic discharge ~70 Hz

    D. gain(t) = K / (1 + ā(t) / a_target)
       Negative feedback: high activity → low gain, low activity → high gain.
       REF: Turrigiano 2008 — homeostatic synaptic plasticity
"""

import math
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────
# A. VoltageRegulator — activity-dependent metabolic recovery
# ─────────────────────────────────────────────────────────────────────

@dataclass
class VoltageRegulator:
    """TYPE:SEMI — LDO-style metabolic recovery.

    Models mitochondrial ATP production that scales with neural activity.
    In biology: active neurons consume more ATP, and mitochondria upregulate
    production to match demand (within limits).

    Output: recovery_rate = base_rate + activity_coeff × |activity|
    Clamped to [0, max_rate] to model metabolic ceiling.

    REF: Attwell & Laughlin 2001 — ~75% of cortical energy goes to
         restoring ion gradients after synaptic activity.
    """
    base_rate: float = 0.001       # basal metabolic rate (resting)
    activity_coeff: float = 0.5    # recovery per unit activity
    max_rate: float = 5.0          # metabolic ceiling (max ATP production)

    def compute_recovery(self, activity: float) -> float:
        """Compute metabolic recovery rate given current activity level.

        Args:
            activity: absolute value of neuron activation

        Returns:
            recovery rate to add to neuron energy per step
        """
        rate = self.base_rate + self.activity_coeff * abs(activity)
        return min(rate, self.max_rate)


# ─────────────────────────────────────────────────────────────────────
# B. DecouplingCapacitor — energy buffer / temporal smoothing
# ─────────────────────────────────────────────────────────────────────

@dataclass
class DecouplingCapacitor:
    """TYPE:SEMI — Parallel capacitor for temporal smoothing.

    Models dendritic cable capacitance that smooths bursty synaptic input
    into a more sustained membrane depolarization.

    In circuit terms: a large capacitor in parallel with the membrane
    that charges slowly and discharges slowly, acting as a low-pass filter.

    Transfer function: H(s) = 1 / (1 + s × τ_buffer)
    τ_buffer = C_buffer × R_buffer

    The buffer voltage tracks the instantaneous input through exponential
    smoothing, then adds to the membrane as a sustained bias.

    REF: Koch 1999 — dendritic cable τ = 20-100 ms
    """
    capacitance: float = 40.0      # large buffer capacitor
    resistance: float = 5.0        # discharge path resistance
    voltage: float = 0.0           # current buffer voltage

    @property
    def tau(self) -> float:
        """Time constant τ = RC."""
        return self.capacitance * self.resistance

    def step(self, input_signal: float, dt: float) -> float:
        """Update buffer and return smoothed output.

        Exponential moving average:
            V_buf(t+dt) = V_buf(t) × decay + input × (1 - decay)
            decay = exp(-dt / τ)

        Args:
            input_signal: instantaneous input (e.g., activation)
            dt: time step

        Returns:
            smoothed voltage to inject into membrane
        """
        tau = max(self.tau, 0.01)
        decay = math.exp(-dt / tau)
        self.voltage = self.voltage * decay + input_signal * (1.0 - decay)
        return self.voltage


# ─────────────────────────────────────────────────────────────────────
# C. BiasCurrentSource — tonic spontaneous activity
# ─────────────────────────────────────────────────────────────────────

@dataclass
class BiasCurrentSource:
    """TYPE:SEMI — Constant current source for tonic baseline.

    Models the leak currents and ion channel noise that drive
    spontaneous tonic firing in vestibular afferents (~70 Hz at rest).

    In circuit terms: a constant current source connected to the
    neuron's input, keeping it near but below firing threshold.

    I_bias = V_target / R_leak (derived from steady-state V = I × R)

    REF: Goldberg 2000 — vestibular afferents have spontaneous
         discharge even without head movement.
    REF: Smith & Goldberg 1986 — tonic rate ~70 spikes/s
    """
    i_bias: float = 0.025          # constant bias current
    enabled: bool = True

    def current(self) -> float:
        """Return the bias current to inject each step."""
        if self.enabled:
            return self.i_bias
        return 0.0


# ─────────────────────────────────────────────────────────────────────
# D. AutomaticGainControl — homeostatic plasticity
# ─────────────────────────────────────────────────────────────────────

@dataclass
class AutomaticGainControl:
    """TYPE:SEMI — AGC via negative feedback on synaptic gain.

    Models homeostatic synaptic plasticity: neurons adjust their
    sensitivity to maintain a target activity level.

    gain(t) = K / (1 + ā(t) / a_target)

    ā(t) is an exponential moving average of |activation|:
        ā(t+1) = ā(t) × (1 - α) + |activation| × α
        α = dt / τ_agc

    When activity is high → gain decreases → prevents runaway
    When activity is low  → gain increases → amplifies weak signals

    REF: Turrigiano 2008 — homeostatic plasticity scales
         AMPA receptor density over hours.
    REF: Desai et al. 1999 — intrinsic excitability homeostasis.

    NOTE: In biology this operates over hours-days. Here we use
    a faster τ_agc (~100 ms) for computational efficiency.
    This is tagged as UNGROUNDED for the time constant.
    """
    base_gain: float = 20.0        # K: maximum gain (when silent)
    target_activity: float = 1.0   # desired steady-state |activation|
    tau_agc: float = 0.1           # UNGROUNDED: smoothing τ (100 ms)
    _activity_avg: float = field(default=0.0, repr=False)

    @property
    def activity_avg(self) -> float:
        return self._activity_avg

    def update(self, activation: float, dt: float):
        """Update the activity running average.

        Args:
            activation: current neuron activation
            dt: time step
        """
        alpha = min(dt / max(self.tau_agc, 0.001), 1.0)
        self._activity_avg += alpha * (abs(activation) - self._activity_avg)

    def gain(self) -> float:
        """Compute current gain based on activity history.

        Returns:
            multiplicative gain factor for synaptic input
        """
        return self.base_gain / (1.0 + self._activity_avg / self.target_activity)


# ─────────────────────────────────────────────────────────────────────
# H. CalciumRateIntegrator — spike rate → continuous signal
# ─────────────────────────────────────────────────────────────────────

@dataclass
class CalciumRateIntegrator:
    """TYPE:SEMI — Ca²⁺ pool integrates spike events into continuous rate.

    DIFFERENTIATION: Only exists in spiking projection neurons whose
    downstream reader requires a continuous signal (e.g., shadow col → DA).

    Problem solved: spiking neurons have activation = 0/1 (instantaneous).
    Downstream BCM learning and bundle propagation need a continuous
    pre-synaptic signal, not discrete spikes.

    In biology: CaMKII in dendritic spines integrates Ca²⁺ influx from
    NMDA receptors during spikes. CaMKII concentration reflects the
    time-averaged firing rate over a ~50-100 ms window. Downstream
    synaptic machinery reads CaMKII, not individual spikes.

    Circuit: Capacitor (Ca²⁺ pool) + MOSFET Zener clamp.
      - Each spike injects Q_spike charge into the Ca²⁺ capacitor.
      - Capacitor leaks with τ = C × R (integration window).
      - MOSFET Zener clamp at V_clamp prevents saturation.
      - Output: calcium_rate = V_Ca (continuous, bounded).

    Parameter relationships:
      V_CRI_ss = f_spike × Q_spike × R_leak    (steady-state Ca voltage)
      f_max = V_clamp / (Q_spike × R_leak)      (max representable rate)
      τ_CRI = C × R_leak                        (integration time window)

    ds²/ν contribution:
      ds² += ΔV²_Ca × C_Ca                      (stored energy in Ca pool)
      ν += I²_clamp × R_clamp                   (Zener dissipation)

    REF: Lisman et al. 2012 — CaMKII as molecular switch
    REF: Bhatt et al. 2009 — Ca²⁺ imaging of spike rate
    """
    capacitance: float = 1.0        # Ca²⁺ pool capacitance
    r_leak: float = 50.0            # leak resistance → τ = 50 ms
    q_spike: float = 0.2            # charge injected per spike [C]
    v_clamp: float = 1.0            # Zener clamp voltage (max output)
    gm_clamp: float = 10.0          # Zener MOSFET conductance (hard clamp)

    # Runtime state
    _ca_voltage: float = field(default=0.0, repr=False)

    @property
    def calcium_rate(self) -> float:
        """Continuous rate signal derived from Ca²⁺ pool voltage."""
        return self._ca_voltage

    def step(self, spiked: bool, dt: float) -> float:
        """Update Ca²⁺ pool: spike injection + leak + Zener clamp.

        Called inside neuron.step() AFTER spike detection.
        Returns calcium_rate (continuous signal for downstream).

        Energy accounting: spike injection energy = Q_spike × V_Ca
        is implicitly part of the spike reset energy (already in heat_output).
        Zener clamp energy = I_clamp × V_clamp is additional dissipation
        returned as heat for the caller to add to heat_output.
        """
        # 1. Spike injection: ΔQ = Q_spike (direct charge, not current×dt)
        if spiked:
            self._ca_voltage += self.q_spike / max(self.capacitance, 1e-6)

        # 2. RC leak: V *= exp(-dt/τ)  (exact exponential, not Euler)
        tau = max(self.r_leak * self.capacitance, 0.01)
        self._ca_voltage *= math.exp(-dt / tau)

        # 3. Zener clamp: MOSFET conducts when V > V_clamp
        heat_clamp = 0.0
        if self._ca_voltage > self.v_clamp:
            excess = self._ca_voltage - self.v_clamp
            # I_clamp = gm × excess, clamp drains excess voltage
            i_clamp = self.gm_clamp * excess
            # Energy dissipated by clamp = I × V × dt (approx)
            heat_clamp = i_clamp * excess * dt
            self._ca_voltage = self.v_clamp  # hard clamp

        return heat_clamp


# ─────────────────────────────────────────────────────────────────────
# I. DivisiveNormalizationReceptor — input range adaptation
# ─────────────────────────────────────────────────────────────────────

@dataclass
class DivisiveNormalizationReceptor:
    """TYPE:SEMI — Divisive normalization via shunting inhibition pool.

    DIFFERENTIATION: Only exists in sensory-receiving neurons that face
    multi-scale input magnitudes (e.g., shadow encoding neurons receiving
    Xin from vestibular chain where magnitudes span 0.2 ~ 20).

    Problem solved: input magnitude varies 100× across different bundles.
    Without normalization, high-Xin bundles dominate and saturate neurons.
    With normalization, each neuron adapts to its own input range.

    In biology: V1 cortical neurons exhibit divisive normalization:
      R_i = L_i^n / (σ^n + Σ_j L_j^n)
    Implemented via GABAergic interneuron pool → shunting inhibition.
    The pool conductance acts as a divisor on excitatory input.

    Circuit: Capacitor (pool activity integrator).
      - Pool voltage tracks total input magnitude via exponential smoothing.
      - Output current = input × σ / (σ + V_pool)
      - σ = half-saturation constant (determines normalization strength).

    Parameter relationships:
      I_eff = I_raw × σ / (σ + V_pool)        (normalized output)
      V_pool_ss = I_total × R_pool             (pool tracks input average)
      When I_total >> σ/R_pool: I_eff → I_raw × σ/(I_total × R_pool)
      → output ∝ I_raw / I_total (relative normalization) ✓

    ds²/ν contribution:
      ds² += ΔV²_pool × C_pool                (stored energy in pool)
      ν += (I_raw - I_eff)² × R_shunt         (shunted energy)

    REF: Carandini & Heeger 2012, Nature Reviews Neuroscience
    REF: Schwartz & Simoncelli 2001 — natural image statistics
    """
    sigma: float = 1.0              # half-saturation voltage [V]
    pool_capacitance: float = 5.0   # pool integrator capacitance
    pool_r_leak: float = 5.0        # pool leak resistance → τ_pool = 25 ms

    # Runtime state
    _pool_voltage: float = field(default=0.0, repr=False)

    @property
    def pool_activity(self) -> float:
        return self._pool_voltage

    def normalize(self, input_current: float, dt: float) -> float:
        """Apply divisive normalization to input current.

        Called inside neuron.step() BEFORE membrane injection.
        Returns normalized current. No additional heat (passive divider).

        The pool tracks |input| via exponential smoothing (Capacitor analog).
        Normalization factor = σ / (σ + V_pool).
        """
        # 1. Update pool: inject |input| and leak
        # Pool voltage = EMA of |input| (Capacitor: charge += I×dt, leak)
        abs_input = abs(input_current)
        self._pool_voltage += abs_input * dt / max(self.pool_capacitance, 1e-6)
        tau_pool = max(self.pool_r_leak * self.pool_capacitance, 0.01)
        self._pool_voltage *= math.exp(-dt / tau_pool)

        # 2. Divisive normalization: I_eff = I_raw × σ / (σ + V_pool)
        # Defensive: denominator always ≥ σ × 0.01 (prevents near-zero)
        denominator = max(self.sigma + self._pool_voltage, self.sigma * 0.01)
        norm_factor = self.sigma / denominator
        return input_current * norm_factor


# ─────────────────────────────────────────────────────────────────────
# J. D2Autoreceptor — DA-specific negative feedback
# ─────────────────────────────────────────────────────────────────────

@dataclass
class D2Autoreceptor:
    """TYPE:SEMI — D2 autoreceptor negative feedback on DA neurons.

    DIFFERENTIATION: Only exists in dopaminergic neurons. No other
    neuron type has this component. This is the DA-specific homeostatic
    mechanism that prevents DA saturation.

    Problem solved: DA neuron receives excitatory input → activates →
    releases DA → DA concentration rises → without feedback, DA saturates.
    D2R provides the ONLY DA-specific negative feedback pathway.

    In biology: VTA DA neurons express D2 autoreceptors on soma/dendrites:
      - DA released from axon terminal diffuses to somatodendritic area
      - DA binds D2R → activates Gi/o → opens GIRK K⁺ channels
      - GIRK current hyperpolarizes → reduces firing rate → less DA
      - This creates a closed-loop negative feedback specific to DA
      - τ_D2 ≈ 100-500 ms (slower than membrane τ for stability)

    Circuit: MOSFET (D2 receptor) + Capacitor (local [DA] integrator).
      - Capacitor integrates DA concentration with τ_D2.
      - MOSFET conducts when local [DA] > ec50 (D2R activation threshold).
      - Output: hyperpolarizing current I_girk (injected into membrane).

    Parameter relationships:
      τ_D2 = C_da × R_da                       (DA integration window)
      [DA]*: gm_D2 × (V_da - ec50) = I_exc - I_base  (equilibrium DA)
      Recovery time ≈ τ_D2 after perturbation

    Stability constraint: τ_D2 >> τ_membrane (slow feedback is stable).
      With τ_membrane = C_membrane × R_leak = 2.0 × 1.0 = 2.0
      τ_D2 = 1.0 × 100.0 = 100.0 >> 2.0 ✓ (50× ratio → stable)

    ds²/ν contribution:
      ds² += ΔV²_da × C_da                     (stored energy in DA pool)
      ν += I²_girk × R_membrane                 (GIRK dissipation via membrane)

    REF: Lacey et al. 1987 — D2R → GIRK in VTA
    REF: Ford 2014, Pharmacological Reviews — DA autoreceptor physiology
    REF: Beckstead et al. 2004 — D2R desensitization kinetics
    """
    conductance: float = 0.5        # max GIRK conductance [S]
    ec50: float = 0.3               # D2R half-activation [DA] concentration
    da_capacitance: float = 1.0     # local [DA] integrator capacitance
    da_r_leak: float = 100.0        # leak resistance → τ_D2 = 100 ms

    # Runtime state
    _da_local: float = field(default=0.0, repr=False)

    @property
    def da_local_voltage(self) -> float:
        """Local DA concentration (integrated)."""
        return self._da_local

    def compute_girk(self, da_concentration: float, dt: float) -> float:
        """Compute GIRK hyperpolarizing current from DA concentration.

        Called inside neuron.step(). Returns negative current to inject
        into membrane (hyperpolarizing). The current flows through the
        membrane resistance and is automatically included in I²R heat.

        Args:
            da_concentration: current system DA level (from dopamine.concentration)
            dt: time step

        Returns:
            i_girk: hyperpolarizing current (negative = reduces V_m)
        """
        # 1. Integrate local [DA] via Capacitor analog
        self._da_local += da_concentration * dt / max(self.da_capacitance, 1e-6)
        tau_d2 = max(self.da_r_leak * self.da_capacitance, 0.01)
        self._da_local *= math.exp(-dt / tau_d2)

        # 2. D2R activation → GIRK current
        # MOSFET-style: subthreshold is smooth exponential (not hard ReLU)
        # This prevents chattering oscillation (external review concern)
        if self._da_local >= self.ec50:
            # Superthreshold: linear
            i_girk = -self.conductance * (self._da_local - self.ec50)
        else:
            # Subthreshold: smooth exponential approach to zero
            # I = -gm × nVT × (exp((V-Vth)/(nVT)) - 1), clamped to ≤ 0
            n_vt = 1.5 * 0.026  # n × V_thermal
            exponent = (self._da_local - self.ec50) / n_vt
            exponent = max(exponent, -50.0)  # prevent underflow
            i_girk = -self.conductance * n_vt * max(0.0, math.exp(exponent) - 1.0)

        return i_girk

