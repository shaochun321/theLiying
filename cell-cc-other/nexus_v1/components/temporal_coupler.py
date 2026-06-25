"""nexus_v1.components.temporal_coupler — Timescale impedance matching.

BIO: Dendritic integration + retrograde messenger + synaptic scaling.

     Two-layer adaptive regulation:

     B (slow, primary): Synaptic scaling / homeostatic plasticity.
       Differential MOSFET comparator reads upstream vs downstream activity.
       Slow capacitor integrates mismatch → modulates R_leak (τ_base).
       Timescale: ~1000 steps. Attractor: ema_up ≈ ema_down.
       BIO: hours-to-days scaling of synaptic strength (Turrigiano 2008).

     C (fast, secondary): Retrograde messenger feedback.
       MOSFET reads downstream ema → adds extra leak when saturated.
       Timescale: every step. Attractor: ema → adapt_vth.
       BIO: endocannabinoid/NO release (milliseconds).

STRUCTURE:
     [upstream spikes] → [C_couple : inject()]
                              ↓
                     [leak(R_base_eff)]  ← B-layer modulates R
                              ↓
                     [leak(R_adapt)]     ← C-layer adaptive drain
                              ↓
                     [clamp] → output V_couple

     B-layer internals:
       ema_up → [MOSFET_up] → I_charge ↓
                                        [C_slow] → V_slow → R_base_eff
       ema_dn → [MOSFET_dn] → I_drain  ↑

S0: Capacitor.inject() + Capacitor.leak() + MOSFET.conduct(). Only.
"""

from .semiconductor import Capacitor, MOSFET


class TemporalCoupler:
    """Adaptive impedance-matching between layers of different timescales.

    Two-layer regulation:
      B (slow): circulation mismatch → τ_base drift (dam capacity)
      C (fast): downstream ema → τ_eff adjustment (spillway opening)

    Args:
        capacitance: Integration capacitance (larger = longer memory).
        r_leak: Base leak resistance → τ_base = C × R.
        v_clamp: Maximum output voltage (Zener-like saturation).
        adapt_vth: C-layer MOSFET threshold (target ema).
        adapt_gm: C-layer MOSFET transconductance.
        blayer_c_slow: B-layer slow integrator capacitance.
        blayer_r_slow: B-layer slow integrator leak resistance.
                       τ_slow = C_slow × R_slow (≈1000 steps).
        blayer_gm: B-layer MOSFET transconductance (tiny).
        blayer_k: B-layer R_leak modulation gain.
    """

    def __init__(self, capacitance: float = 1.0,
                 r_leak: float = 2.0,
                 v_clamp: float = 2.0,
                 # C-layer params
                 adapt_vth: float = 0.0,
                 adapt_gm: float = 0.0,
                 # B-layer params
                 blayer_c_slow: float = 0.0,
                 blayer_r_slow: float = 10.0,
                 blayer_gm: float = 0.01,
                 blayer_k: float = 2.0):
        self._cap = Capacitor(capacitance)
        self._r_leak_base = r_leak
        self._r_leak = r_leak     # effective R_leak (modulated by B)
        self._v_clamp = v_clamp
        self._tau_base = capacitance * r_leak

        # ── C-layer: fast ema feedback (retrograde messenger) ──
        self._adapt_enabled = (adapt_gm > 0 and adapt_vth > 0)
        self._adapt_gate = MOSFET(v_threshold=adapt_vth, gm=adapt_gm)
        self._tau_eff = self._tau_base

        # ── B-layer: slow circulation feedback (synaptic scaling) ──
        # Differential comparator: ema_up vs ema_down.
        # V_slow > 0: upstream overproducing → increase τ (pass more)
        # V_slow < 0: downstream over-active → decrease τ (pass less)
        self._blayer_enabled = (blayer_c_slow > 0)
        if self._blayer_enabled:
            self._blayer_cap = Capacitor(blayer_c_slow)
            # Both MOSFETs are always-on (v_th=0): linear response
            self._blayer_up = MOSFET(v_threshold=0.0, gm=blayer_gm)
            self._blayer_dn = MOSFET(v_threshold=0.0, gm=blayer_gm)
            self._blayer_r_slow = blayer_r_slow
            self._blayer_k = blayer_k
            # R_leak bounds (prevent extreme τ)
            self._blayer_r_min = max(0.2, r_leak * 0.1)
            self._blayer_r_max = r_leak * 5.0
        self._v_slow = 0.0  # diagnostic

        # ── Noether energy tracking ──
        # Coupler stores energy E = 0.5 × C × V².
        # Track all energy flows for conservation audit.
        self._cumulative_energy_in = 0.0   # from upstream inject
        self._cumulative_energy_out = 0.0  # leak + drain + clamp

    def step(self, input_current: float, dt: float,
             vm_downstream: float = 0.0,
             ema_upstream: float = 0.0) -> float:
        """Integrate input, apply B+C adaptive leak, return smoothed voltage.

        Args:
            input_current: Raw synaptic current from upstream bundle.
            dt: System timestep.
            vm_downstream: Downstream neuron ema (C-layer gate signal).
            ema_upstream: Upstream neuron mean ema (B-layer signal).

        Returns:
            Smoothed voltage (used as input current to downstream neuron).
        """
        # ── 1. Charge: accumulate upstream signal ──
        e_before = self.stored_energy
        self._cap.inject(input_current, dt)
        e_after_inject = self.stored_energy
        self._cumulative_energy_in += max(0.0, e_after_inject - e_before)

        # ── 2. B-layer: slow circulation feedback ──
        # Differential MOSFET comparator integrates ema mismatch.
        # V_slow modulates R_leak → τ_base drifts toward equilibrium.
        # BIO: synaptic scaling (Turrigiano 2008)
        r_leak = self._r_leak_base
        if self._blayer_enabled:
            # Upstream MOSFET: charges C_slow proportional to ema_up
            i_up = self._blayer_up.conduct(ema_upstream)
            # Downstream MOSFET: drains C_slow proportional to ema_down
            i_dn = self._blayer_dn.conduct(vm_downstream)
            # Net current: positive when upstream > downstream
            self._blayer_cap.inject(i_up - i_dn, dt)
            # Slow leak (τ_slow = C_slow × R_slow ≈ 1000 steps)
            self._blayer_cap.leak(self._blayer_r_slow, dt)
            # Read slow voltage
            self._v_slow = self._blayer_cap.voltage
            # Modulate R_leak: V_slow > 0 → more R → more τ → pass more
            r_leak = self._r_leak_base * (1.0 + self._blayer_k * self._v_slow)
            r_leak = max(self._blayer_r_min, min(self._blayer_r_max, r_leak))
            # Update τ_base for diagnostics
            self._r_leak = r_leak
            self._tau_base = self._cap.capacitance * r_leak

        # ── 3. Base leak: τ_base decay (with B-modulated R) ──
        self._cap.leak(r_leak, dt)

        # ── 4. C-layer: fast adaptive leak (retrograde messenger) ──
        # MOSFET reads downstream ema. High ema → drain coupler charge.
        if self._adapt_enabled:
            g_adapt = self._adapt_gate.conduct(vm_downstream)
            if g_adapt > 0:
                drain = g_adapt * self._cap.voltage * dt
                self._cap.charge = max(0.0,
                                       self._cap.charge - drain)
                self._tau_eff = 1.0 / (1.0 / self._tau_base
                                       + g_adapt / self._cap.capacitance)
            else:
                self._tau_eff = self._tau_base
        else:
            self._tau_eff = self._tau_base

        # ── 5. Clamp: prevent runaway (BIO: receptor saturation) ──
        v = self._cap.voltage
        if v > self._v_clamp:
            self._cap.charge = self._v_clamp * self._cap.capacitance
        elif v < -self._v_clamp:
            self._cap.charge = -self._v_clamp * self._cap.capacitance

        # Track total energy dissipated this step
        e_final = self.stored_energy
        e_dissipated = max(0.0, e_before - e_final
                           + max(0.0, e_after_inject - e_before))
        self._cumulative_energy_out += e_dissipated

        return self._cap.voltage

    @property
    def stored_energy(self) -> float:
        """Energy stored in coupler capacitor: E = 0.5 × C × V²."""
        v = self._cap.voltage
        return 0.5 * self._cap.capacitance * v * v

    @property
    def voltage(self) -> float:
        """Current coupler voltage (for diagnostics)."""
        return self._cap.voltage

    @property
    def tau_base(self) -> float:
        """Base time constant (after B-layer modulation)."""
        return self._tau_base

    @property
    def tau_eff(self) -> float:
        """Effective time constant (after B+C adaptation)."""
        return self._tau_eff

    @property
    def v_slow(self) -> float:
        """B-layer slow integrator voltage (for diagnostics)."""
        return self._v_slow

    def summary(self) -> dict:
        return {
            'voltage': self._cap.voltage,
            'tau_base': self._tau_base,
            'tau_eff': self._tau_eff,
            'v_slow': self._v_slow,
            'r_leak': self._r_leak,
            'r_leak_base': self._r_leak_base,
            'capacitance': self._cap.capacitance,
            'v_clamp': self._v_clamp,
            'adapt_enabled': self._adapt_enabled,
            'blayer_enabled': self._blayer_enabled,
        }
