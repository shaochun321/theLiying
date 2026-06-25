"""nexus_v1.components.ndr — Negative Differential Resistance Element.

TYPE:HYBRID — Maps to both tunnel diode (electronics) and
Na⁺ channel inactivation (biology).

===========================================================
ZERO DEPENDENCY ON EXISTING NEXUS CODE.
===========================================================

Electronic Equivalent:
    Esaki (tunnel) diode / Chua diode / Gunn diode

    I-V characteristic (N-type NDR):

    I ↑     /‾‾‾‾‾‾‾‾‾‾
      │    / ╲
      │   /   ╲         ←  NDR region (dI/dV < 0)
      │  /     ╲________/
      │ /
      └──────────────────→ V

    Three regions:
      Region 1 (V < V_peak): I = g₁V         (positive conductance)
      Region 2 (V_peak < V < V_valley): NDR   (negative conductance)
      Region 3 (V > V_valley): I = I_v + g₃V  (positive, saturated)

Biological Equivalent:
    Na⁺ channel activation + inactivation (Hodgkin-Huxley):

    g_Na(V) = ḡ_Na × m³(V) × h(V)

    - m(V) activates fast with V ↑ → conductance rises
    - h(V) inactivates slowly with V ↑ → conductance falls
    - Net: g rises then falls → NDR in g-V curve
    - This is THE mechanism for action potential generation

    REF: Hodgkin & Huxley 1952 — Nobel Prize
    REF: Chua 1971 — nonlinear circuit theory
    REF: Pickett et al. 2013 — NbO₂ memristive NDR

Parametric Derivation:
    Na⁺ channel (normalized to nexus_v1 coordinates):
        V_peak = 0.15  (half-activation ≈ -40 mV → normalized)
        V_valley = 0.35 (inactivation ≈ -20 mV → normalized)
        g_peak = 1.0   (peak conductance, normalized)
        g_valley = 0.1 (residual conductance after inactivation)
"""

import math
from dataclasses import dataclass, field


@dataclass
class NDRElement:
    """N-type Negative Differential Resistance element.

    Provides a non-monotonic I-V characteristic where increasing
    voltage DECREASES current in the NDR region. This enables:

    1. Self-sustained oscillations (with LC tank)
    2. Bistability (two stable states)
    3. Excitability (threshold + refractory period)
    4. Inherent inhibition (current falls at high V)

    Args:
        v_peak: voltage at peak current (start of NDR)
        v_valley: voltage at valley current (end of NDR)
        g_positive: conductance in region 1 (V < v_peak)
        g_negative: effective conductance in NDR region (< 0)
        g_saturation: conductance in region 3 (V > v_valley)
        i_valley: minimum current at valley point
    """

    v_peak: float = 0.15          # BIO: Na⁺ half-activation
    v_valley: float = 0.35        # BIO: Na⁺ inactivation onset
    g_positive: float = 2.0       # Region 1 conductance
    g_saturation: float = 0.5     # Region 3 conductance
    i_valley: float = 0.1         # Minimum current at valley

    # Internal state for dynamic NDR (inactivation gate h)
    _h_gate: float = field(default=1.0, repr=False)  # inactivation [0,1]
    tau_h: float = 5.0            # inactivation time constant (ms)

    @property
    def i_peak(self) -> float:
        """Current at peak point."""
        return self.g_positive * self.v_peak

    def conduct_static(self, voltage: float) -> float:
        """Static (instantaneous) I-V characteristic.

        Piecewise linear NDR:
          Region 1: I = g₁ × V                        (V ≤ V_peak)
          Region 2: I = I_peak - g_neg × (V - V_peak)  (V_peak < V < V_valley)
          Region 3: I = I_valley + g₃ × (V - V_valley) (V ≥ V_valley)

        Returns:
            Current through the element
        """
        if voltage <= self.v_peak:
            return self.g_positive * voltage
        elif voltage <= self.v_valley:
            # NDR region: current decreases
            dv = voltage - self.v_peak
            span = self.v_valley - self.v_peak
            if span < 0.001:
                span = 0.001
            g_neg = (self.i_peak - self.i_valley) / span
            return self.i_peak - g_neg * dv
        else:
            # Saturation region
            return self.i_valley + self.g_saturation * (voltage - self.v_valley)

    def conduct_dynamic(self, voltage: float, dt: float) -> float:
        """Dynamic I-V with inactivation gate (HH-like).

        Models the time-dependent behavior:
            I = g_max × m_inf(V) × h(t) × V

        Where:
            m_inf(V) = 1/(1 + exp(-(V - V_peak)/(V_peak/4)))
            dh/dt = (h_inf(V) - h) / τ_h
            h_inf(V) = 1/(1 + exp((V - V_valley)/(V_valley/4)))

        This gives true HH-like dynamics: fast activation, slow
        inactivation → action potential shape.

        Args:
            voltage: membrane voltage
            dt: time step

        Returns:
            Current through the element
        """
        # Fast activation (instantaneous)
        slope_m = self.v_peak / 4.0
        m_inf = 1.0 / (1.0 + math.exp(-(voltage - self.v_peak) /
                                       max(slope_m, 0.01)))

        # Slow inactivation (time-dependent)
        slope_h = self.v_valley / 4.0
        h_inf = 1.0 / (1.0 + math.exp((voltage - self.v_valley) /
                                       max(slope_h, 0.01)))

        # Update h gate
        if self.tau_h > 0:
            alpha = min(dt / max(self.tau_h * 0.001, 0.0001), 1.0)
            self._h_gate += alpha * (h_inf - self._h_gate)
        else:
            self._h_gate = h_inf

        # Current: I = g_max × m × h × V
        g_eff = self.g_positive * m_inf * self._h_gate
        return g_eff * voltage

    def differential_resistance(self, voltage: float) -> float:
        """Compute dI/dV at a given voltage.

        Returns:
            Differential resistance. Negative in NDR region.
        """
        epsilon = 0.001
        i1 = self.conduct_static(voltage - epsilon)
        i2 = self.conduct_static(voltage + epsilon)
        dIdV = (i2 - i1) / (2 * epsilon)
        if abs(dIdV) < 1e-10:
            return float('inf')
        return 1.0 / dIdV

    def is_in_ndr_region(self, voltage: float) -> bool:
        """Check if voltage is in the NDR region."""
        return self.v_peak < voltage < self.v_valley

    def reset(self):
        """Reset inactivation gate to fully available."""
        self._h_gate = 1.0


@dataclass
class InhibitorySynapse:
    """NDR-based lateral inhibition.

    Uses the NDR characteristic to implement winner-take-all:
    when one neuron's activation is high, it REDUCES current to
    neighboring neurons via the NDR I-V curve.

    BIO: Lateral inhibition in retina, cortical surround suppression
    REF: Hartline & Ratliff 1957 — lateral inhibition in Limulus

    Implementation:
        I_inhibit = -gain × NDR.conduct(V_source)
        The negative sign means: higher source V → less current
        in the NDR region → inhibition of target.
    """

    ndr: NDRElement = field(default_factory=NDRElement)
    gain: float = 1.0             # inhibition strength
    connections: list = field(default_factory=list)  # (source_idx, target_idx)

    def compute_inhibition(self, activations: list) -> list:
        """Compute inhibitory currents for all targets.

        Args:
            activations: list of neuron activations

        Returns:
            list of inhibitory currents (negative values)
        """
        n = len(activations)
        inhibition = [0.0] * n

        for src, tgt in self.connections:
            if src < n and tgt < n:
                # NDR response to source activation
                i_ndr = self.ndr.conduct_static(activations[src])
                # In NDR region, current drops → less inhibition
                # Outside NDR, current is high → strong inhibition
                inhibition[tgt] -= self.gain * i_ndr

        return inhibition
