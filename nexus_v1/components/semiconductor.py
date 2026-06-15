"""nexus_v1.components.semiconductor — Extended Semiconductor Components.

Extends the Morphosphere v42 semiconductor library with:
  1. MOSFET gating dynamics (tau_gate) → HH-equivalent channel kinetics
  2. All existing components preserved (Capacitor, PowerRail, Memristor)

Equivalent Circuit per Neuron (extended):

                Vdd (PowerRail)
                 │
                 R_supply
                 │
        ┌────────┤ V_internal
        │        │
 in ──[M]──┬──[C]──┤         M = Memristor (synapse)
 (synapse) │       │         C = Capacitor (membrane)
          [R_leak] GND       FET = MOSFET (channel)
           │
          GND

 V_C → [FET_met] → MET current
 V_C → [FET_k]  → K current (repolarization)
 V_C → [FET_ca] → Ca current (depolarization)
 Sum currents → output

Each FET now has a gating variable m ∈ [0,1] with time constant tau_gate,
making it equivalent to one HH ion channel: I = g_max * m(V) * (V - E).
"""

import math
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────
# Capacitor — membrane capacitance
# ─────────────────────────────────────────────────────────────────────

@dataclass
class Capacitor:
    """Membrane capacitance: charge accumulation with RC time constant.

    Q = CV, dV/dt = I/C - V/(RC).

    KCL tracking: cumulative charge_in and charge_out for Noether audit.
    Conservation: charge_in - charge_out ≡ Δcharge = Q(t) - Q(0).
    """
    capacitance: float = 1.0
    charge: float = 0.0
    # KCL tracking (Noether) — initialized lazily on first operation
    _q_in: float = field(default=0.0, repr=False)
    _q_out: float = field(default=0.0, repr=False)
    _q_initial: float = field(default=None, repr=False, init=False)

    def _ensure_kcl_init(self):
        """Lazily capture initial charge state on first KCL-tracked operation."""
        if self._q_initial is None:
            self._q_initial = self.charge

    @property
    def voltage(self) -> float:
        """V = Q / C"""
        return self.charge / max(self.capacitance, 1e-6)

    def inject(self, current: float, dt: float = 1.0):
        """Inject current → accumulate charge. ΔQ = I·dt."""
        self._ensure_kcl_init()
        dq = current * dt
        self.charge += dq
        if dq >= 0:
            self._q_in += dq
        else:
            self._q_out += (-dq)

    def leak(self, resistance: float, dt: float = 1.0):
        """RC discharge: dV/dt = -V / (R·C)."""
        self._ensure_kcl_init()
        if resistance < 0.01:
            resistance = 0.01
        tau = resistance * self.capacitance
        decay = math.exp(-dt / max(tau, 0.01))
        q_before = self.charge
        self.charge *= decay
        # KCL: leaked charge = q_before - q_after
        dq_leaked = q_before - self.charge
        if dq_leaked >= 0:
            self._q_out += dq_leaked
        else:
            self._q_in += (-dq_leaked)

    def discharge_to(self, target_voltage: float):
        """Reset to target voltage (post-spike reset)."""
        self._ensure_kcl_init()
        q_before = self.charge
        self.charge = target_voltage * self.capacitance
        # KCL: track the reset charge transfer
        dq = self.charge - q_before
        if dq >= 0:
            self._q_in += dq
        else:
            self._q_out += (-dq)

    @property
    def kcl_imbalance(self) -> float:
        """KCL conservation check: should be ≈ 0."""
        if self._q_initial is None:
            return 0.0  # never used — no imbalance
        dq_stored = self.charge - self._q_initial
        return abs(self._q_in - self._q_out - dq_stored)


# ─────────────────────────────────────────────────────────────────────
# MOSFET — voltage-gated threshold with gating dynamics
# ─────────────────────────────────────────────────────────────────────

@dataclass
class MOSFET:
    """Voltage-gated threshold with optional gating dynamics.

    Base behavior (instantaneous):
      Superthreshold: I = gm × (Vgs - Vth)
      Subthreshold:   I ∝ exp((Vgs - Vth) / (n·VT))

    Extended behavior (with gating):
      m_gate tracks the steady-state with time constant tau_gate.
      I_gated = m_gate × I_instantaneous
      This is equivalent to HH's: I = g_max × m(V) × (V - E)

    When tau_gate = 0 (default), gating is instantaneous (no dynamics).
    """
    v_threshold: float = 0.3
    gm: float = 1.0

    # Subthreshold parameters
    n_slope: float = 1.5
    v_thermal: float = 0.026  # kT/q ≈ 26mV at 300K

    # Gating dynamics (HH-equivalent)
    m_gate: float = 0.0       # gating variable [0, 1]
    tau_gate: float = 0.0     # gating time constant (0 = instantaneous)

    def conduct(self, v_gate: float) -> float:
        """Instantaneous gate voltage → drain current.

        Superthreshold: linear I = gm × (Vgs - Vth)
        Subthreshold:   exponential I ∝ exp((Vgs-Vth)/(n×VT)) - 1
        Both give I = 0 at Vgs = Vth (continuous).
        """
        if v_gate >= self.v_threshold:
            return self.gm * (v_gate - self.v_threshold)
        else:
            # Subthreshold: I_sub = gm × nVT × (exp((Vgs-Vth)/(nVT)) - 1)
            # In real MOSFETs, subthreshold current is always positive
            # (drain current flows, just exponentially small).
            # The formula gives negative because exp(x)-1 < 0 for x < 0,
            # but physical drain current = |I_sub|.
            nVT = self.n_slope * max(self.v_thermal, 0.001)
            exponent = (v_gate - self.v_threshold) / nVT
            exponent = max(exponent, -50.0)
            return max(0.0, self.gm * nVT * (math.exp(exponent) - 1.0))

    def update_gate(self, v_gate: float, dt: float):
        """Update gating variable toward steady-state.

        Equivalent to HH: dm/dt = (m_inf(V) - m) / tau_m
        m_inf = instantaneous_conductance / gm, clamped to [0, 1].
        """
        if self.tau_gate <= 0:
            # Instantaneous: m_gate tracks steady-state exactly
            raw = self.conduct(v_gate)
            self.m_gate = min(1.0, max(0.0, raw / max(self.gm, 1e-6)))
        else:
            # First-order relaxation toward steady-state
            raw = self.conduct(v_gate)
            m_inf = min(1.0, max(0.0, raw / max(self.gm, 1e-6)))
            self.m_gate += (m_inf - self.m_gate) * dt / self.tau_gate

    def gated_conduct(self, v_gate: float) -> float:
        """Conductance with gating dynamics.

        I = m_gate × gm × f(Vgs)
        Equivalent to HH's I = g_max × m × (V - E).
        """
        return self.m_gate * self.conduct(v_gate)

    def adapt_threshold(self, actual_rate: float, target_rate: float,
                        rate: float = 0.01):
        """Homeostatic Vth drift (NBTI/PBTI analogy)."""
        error = actual_rate - target_rate
        self.v_threshold += rate * error
        self.v_threshold = max(0.005, min(2.0, self.v_threshold))


# ─────────────────────────────────────────────────────────────────────
# Memristor — synaptic weight
# ─────────────────────────────────────────────────────────────────────

@dataclass
class Memristor:
    """Synaptic weight: plastic resistance with STDP via charge flux.

    R = R_min + ΔR × (1 - w), where w ∈ [0, 1].
    
    Noether audit: tracks cumulative LTP, LTD, and clamp for weight balance.
    Conservation: w(t) - w(0) = Σ_ltp - Σ_ltd - Σ_clamp.
    """
    w: float = 0.5
    r_min: float = 0.1
    r_max: float = 10.0
    # Weight audit tracking
    _cum_ltp: float = field(default=0.0, repr=False)
    _cum_ltd: float = field(default=0.0, repr=False)
    _cum_clamp: float = field(default=0.0, repr=False)  # lost to min/max bounds
    _w_initial: float = field(default=0.5, repr=False)

    def __post_init__(self):
        self._w_initial = self.w

    @property
    def resistance(self) -> float:
        return self.r_min + (self.r_max - self.r_min) * (1.0 - self.w)

    @property
    def conductance(self) -> float:
        return 1.0 / max(self.resistance, 1e-6)

    def conduct(self, v_in: float) -> float:
        """Pass current through memristor. I = V × G."""
        return v_in * self.conductance

    def apply_dw(self, dw: float, w_min: float = 0.0, w_max: float = 1.0):
        """Apply weight change with tracking.
        
        Tracks LTP (dw > 0), LTD (dw < 0), and clamp loss.
        """
        w_before = self.w
        self.w += dw
        # Clamp
        if self.w > w_max:
            self._cum_clamp += self.w - w_max
            self.w = w_max
        elif self.w < w_min:
            self._cum_clamp += w_min - self.w
            self.w = w_min
        # Track effective change
        effective_dw = self.w - w_before
        if effective_dw > 0:
            self._cum_ltp += effective_dw
        else:
            self._cum_ltd += (-effective_dw)

    @property
    def weight_audit_imbalance(self) -> float:
        """Weight conservation check: should be ≈ 0.
        
        w(t) - w(0) should equal cum_ltp - cum_ltd.
        """
        dw_actual = self.w - self._w_initial
        dw_tracked = self._cum_ltp - self._cum_ltd
        return abs(dw_actual - dw_tracked)

    def update(self, current: float, pre_trace: float, post_trace: float):
        """STDP update via charge flux history."""
        dw = 0.5 * current * (pre_trace - post_trace)
        self.apply_dw(dw)


# ─────────────────────────────────────────────────────────────────────
# PowerRail — metabolic energy supply
# ─────────────────────────────────────────────────────────────────────

@dataclass
class PowerRail:
    """Metabolic energy supply: Vdd from SubstrateNetwork.

    V_actual = Vdd - I × R_internal.
    IR drop is the natural gain limiter — large currents saturate.
    """
    vdd: float = 1.0
    r_internal: float = 0.1
    _last_current: float = field(default=0.0, repr=False)

    def draw(self, current: float) -> float:
        """Draw current, return available voltage after IR drop."""
        self._last_current = current
        v_drop = current * self.r_internal
        return max(0.0, self.vdd - v_drop)

    @property
    def v_actual(self) -> float:
        return max(0.0, self.vdd - self._last_current * self.r_internal)

    @property
    def power_dissipated(self) -> float:
        """I²R internal dissipation."""
        return self._last_current ** 2 * self.r_internal
