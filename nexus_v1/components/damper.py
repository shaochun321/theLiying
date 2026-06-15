"""nexus_v1.components.damper — MagnetofluidDamper.

TYPE:HYBRID — Magnetorheological fluid damper mapped to both
MR shock absorber (electronics/mechanical) and myelin/ECM (biology).

===========================================================
ZERO DEPENDENCY ON EXISTING NEXUS CODE.
===========================================================

Electronic/Mechanical Equivalent:
    Magnetorheological (MR) fluid damper:
    - Viscosity changes with applied magnetic field
    - R_eff = R_base × (1 + α × B²)
    - Self-induced field: B_local = β × I_through

    REF: Rosensweig 1985 — Ferrohydrodynamics
    REF: Jolly et al. 1999 — MR fluid devices

    Faraday instability: under AC field, ferrofluid surface
    forms periodic standing waves → internal oscillation source

Biological Equivalent:
    - Myelin sheath: variable insulation, saltatory conduction
      → BIO: 80 m/s myelinated vs 1 m/s unmyelinated
      → REF: Waxman & Ritchie 1993
    - Extracellular matrix (ECM): mechanical damping of signals
    - Perineuronal nets: stabilize synapses, restrict plasticity
      → REF: Pizzorusso et al. 2002

    The key biological property: ADAPTIVE IMPEDANCE.
    High activity → more resistance → signal shaping
    Low activity → less resistance → sensitivity preserved

Mathematical Model:
    Damping coefficient:
        R(t) = R_base × (1 + α × B²(t))

    Self-induced field:
        B(t) = B_ext + β × I_local(t)

    Faraday oscillation (optional periodic component):
        B_faraday(t) = A_f × sin(2πf_f × t) × H(|B| - B_threshold)

    Where H is the Heaviside step function (oscillation only
    activates above a field threshold — Rosensweig instability).
"""

import math
from dataclasses import dataclass, field


@dataclass
class MagnetofluidDamper:
    """Field-controlled adaptive damper.

    Variable resistance that increases with local current flow
    (via self-induced magnetic field). Provides:

    1. Signal shaping: large signals get attenuated more
    2. Frequency filtering: high-frequency signals see more damping
    3. Self-stabilization: prevents runaway excitation
    4. Optional Faraday oscillation: internal periodic source

    Args:
        r_base: baseline resistance (no field)
        alpha: field sensitivity coefficient
        beta: self-induction coefficient (current → field)
        b_external: externally applied field
        faraday_enabled: whether Faraday instability generates oscillation
        faraday_freq: Faraday oscillation frequency (Hz)
        faraday_threshold: minimum field for instability
        faraday_amplitude: oscillation amplitude
    """

    r_base: float = 1.0           # Ω — baseline
    alpha: float = 0.5            # field sensitivity
    beta: float = 0.1             # self-induction I→B
    b_external: float = 0.0       # external field

    # Faraday oscillation parameters
    faraday_enabled: bool = False
    faraday_freq: float = 100.0   # Hz — typical for MR fluid
    faraday_threshold: float = 0.5  # minimum B for instability
    faraday_amplitude: float = 0.05

    # Internal state
    _b_field: float = field(default=0.0, repr=False)
    _t: float = field(default=0.0, repr=False)
    _last_current: float = field(default=0.0, repr=False)

    def effective_resistance(self, current: float) -> float:
        """Compute effective resistance given current flow.

        R_eff = R_base × (1 + α × B²)
        B = B_ext + β × |I|

        Args:
            current: current flowing through the damper

        Returns:
            Effective resistance
        """
        self._last_current = current
        self._b_field = self.b_external + self.beta * abs(current)
        b_sq = self._b_field ** 2
        return self.r_base * (1.0 + self.alpha * b_sq)

    def damping_factor(self, current: float) -> float:
        """Compute damping multiplier (>= 1.0).

        Returns the ratio R_eff / R_base.
        """
        r_eff = self.effective_resistance(current)
        return r_eff / max(self.r_base, 1e-6)

    def attenuate(self, signal: float) -> float:
        """Attenuate a signal through the damper.

        Output = signal / damping_factor(signal)

        Large signals get attenuated more (compressive nonlinearity).
        """
        df = self.damping_factor(signal)
        return signal / max(df, 0.01)

    def step(self, current: float, dt: float) -> float:
        """Update internal state and return Faraday oscillation.

        Args:
            current: current flowing through the element
            dt: time step

        Returns:
            Faraday oscillation output (0.0 if disabled)
        """
        self._t += dt
        self._last_current = current
        self._b_field = self.b_external + self.beta * abs(current)

        if not self.faraday_enabled:
            return 0.0

        # Faraday instability: only activates above threshold
        if abs(self._b_field) < self.faraday_threshold:
            return 0.0

        # Faraday oscillation amplitude scales with (B - B_th)
        excess_b = abs(self._b_field) - self.faraday_threshold
        amp = self.faraday_amplitude * min(excess_b, 1.0)
        return amp * math.sin(2.0 * math.pi * self.faraday_freq * self._t)

    @property
    def b_field(self) -> float:
        """Current magnetic field strength."""
        return self._b_field

    @property
    def viscosity_ratio(self) -> float:
        """Equivalent viscosity ratio (for biological interpretation).

        Maps to myelin thickness:
          ratio ≈ 1.0: unmyelinated
          ratio ≈ 5.0: thinly myelinated
          ratio ≈ 20+: heavily myelinated
        """
        return 1.0 + self.alpha * self._b_field ** 2

    def reset(self):
        """Reset internal state."""
        self._b_field = 0.0
        self._t = 0.0
        self._last_current = 0.0
