"""nexus_v1.components.oscillator — ResonantOscillator.

TYPE:HYBRID — Van der Pol oscillator mapped to both LC resonance
and biological central pattern generators (CPG).

===========================================================
ZERO DEPENDENCY ON EXISTING NEXUS CODE.
This file is completely standalone for safety.
===========================================================

Electronic Equivalent:
    LC tank + negative resistance (tunnel diode / Chua diode)

    ┌──[L]──┬──[C]──┐
    │       │       │
    └──[NDR]┘       GND

    f₀ = 1 / (2π√(LC))
    Q  = 2πf₀L / R_loss

    NDR compensates R_loss → self-sustained oscillation.

Biological Equivalent:
    - Vestibular nuclei tonic oscillation (~50-100 Hz)
    - Inferior olive coupled oscillators (Llinas 1988)
    - CPG half-center mutual inhibition (Marder & Bucher 2001)
    - Theta-gamma cross-frequency coupling (Buzsáki 2006)

Mathematical Model:
    Van der Pol oscillator (canonical form for relaxation oscillations):

        dx/dt = y
        dy/dt = -ω₀²x - μ(x² - 1)y + I_ext / L_eff

    Where:
        x     = normalized voltage (∝ capacitor voltage)
        y     = normalized current (∝ inductor current)
        ω₀    = 2πf₀ = natural frequency
        μ     = nonlinear damping coefficient
                μ > 0: limit cycle oscillation
                μ = 0: pure harmonic (LC)
                μ >> 1: relaxation oscillation
        I_ext = external forcing current

    Steady state: stable limit cycle with amplitude ≈ 2 and period ≈ 2π/ω₀.

    REF: Van der Pol 1926, "On relaxation oscillations"
    REF: FitzHugh 1961 — Van der Pol ↔ neural excitability equivalence

Parametric Derivation:
    For vestibular nucleus oscillation at f₀ = 50 Hz:
        ω₀ = 2π × 50 = 314.16 rad/s
        μ = 0.5 (mild nonlinearity → near-sinusoidal)
        amplitude ≈ 0.1 (small compared to Aff threshold 0.23)

    For CPG rhythm at f₀ = 5 Hz (theta):
        ω₀ = 2π × 5 = 31.42 rad/s
        μ = 2.0 (strong nonlinearity → square-wave-like)
"""

import math
from dataclasses import dataclass, field


@dataclass
class ResonantOscillator:
    """Self-sustained oscillator based on Van der Pol dynamics.

    Produces a periodic output signal with controllable frequency,
    amplitude, and waveform shape (sinusoidal ↔ relaxation).

    Can be used as:
      1. ISI synchronization clock (injected into afferents)
      2. CPG rhythm generator (for motor pattern generation)
      3. Phase reference (for cross-frequency coupling)

    Args:
        frequency: oscillation frequency in Hz
        mu: nonlinear damping (0=harmonic, 0.5=mild, 2+=relaxation)
        amplitude: output scaling factor
        phase_offset: initial phase in radians
    """

    frequency: float = 50.0       # Hz — vestibular nucleus tonic rate
    mu: float = 0.5               # nonlinearity (0=LC, >1=relaxation)
    amplitude: float = 0.1        # output scaling
    phase_offset: float = 0.0     # initial phase

    # Internal state (Van der Pol: x, y)
    _x: float = field(default=0.1, repr=False)
    _y: float = field(default=0.0, repr=False)
    _t: float = field(default=0.0, repr=False)

    def __post_init__(self):
        """Initialize state from phase offset."""
        self._x = self.amplitude * math.cos(self.phase_offset)
        self._y = -self.amplitude * self.omega * math.sin(self.phase_offset)

    @property
    def omega(self) -> float:
        """Natural angular frequency ω₀ = 2πf₀."""
        return 2.0 * math.pi * self.frequency

    @property
    def phase(self) -> float:
        """Current instantaneous phase (extracted from state)."""
        return math.atan2(-self._y / max(self.omega, 1e-6), self._x)

    @property
    def instant_frequency(self) -> float:
        """Instantaneous frequency (may differ from natural freq due to μ)."""
        return self.frequency  # For Van der Pol, average freq ≈ f₀

    def step(self, dt: float, i_ext: float = 0.0) -> float:
        """Advance oscillator by one time step.

        Uses 4th-order Runge-Kutta for numerical stability.

        Args:
            dt: time step (seconds)
            i_ext: external forcing current (for injection locking)

        Returns:
            Oscillator output voltage (scaled by amplitude)
        """
        w2 = self.omega ** 2
        mu = self.mu

        def dxdt(x, y):
            return y

        def dydt(x, y):
            # Van der Pol: dy/dt = -ω²x - μ(x²-1)y + I_ext
            return -w2 * x - mu * (x * x - 1.0) * y + i_ext

        # RK4 integration
        x, y = self._x, self._y

        k1x = dxdt(x, y)
        k1y = dydt(x, y)

        x2 = x + 0.5 * dt * k1x
        y2 = y + 0.5 * dt * k1y
        k2x = dxdt(x2, y2)
        k2y = dydt(x2, y2)

        x3 = x + 0.5 * dt * k2x
        y3 = y + 0.5 * dt * k2y
        k3x = dxdt(x3, y3)
        k3y = dydt(x3, y3)

        x4 = x + dt * k3x
        y4 = y + dt * k3y
        k4x = dxdt(x4, y4)
        k4y = dydt(x4, y4)

        self._x += dt / 6.0 * (k1x + 2*k2x + 2*k3x + k4x)
        self._y += dt / 6.0 * (k1y + 2*k2y + 2*k3y + k4y)
        self._t += dt

        # Clamp to prevent numerical blowup
        self._x = max(-10.0, min(10.0, self._x))
        self._y = max(-10000.0, min(10000.0, self._y))

        return self._x * self.amplitude

    def output(self) -> float:
        """Current output value (without advancing time)."""
        return self._x * self.amplitude

    def reset(self, phase: float = 0.0):
        """Reset oscillator to a given phase."""
        self._x = 2.0 * math.cos(phase)  # limit cycle amplitude ≈ 2
        self._y = -2.0 * self.omega * math.sin(phase)
        self._t = 0.0

    def inject_lock(self, reference_phase: float, coupling: float = 0.1):
        """Phase-lock to a reference oscillator (Kuramoto coupling).

        Adjusts internal phase toward reference:
            dφ/dt = ω + K × sin(φ_ref - φ)

        REF: Kuramoto 1984 — coupled oscillator synchronization
        """
        phase_error = reference_phase - self.phase
        # Wrap to [-π, π]
        phase_error = (phase_error + math.pi) % (2 * math.pi) - math.pi
        # Apply coupling as a frequency correction
        correction = coupling * math.sin(phase_error) * self.omega
        self._y += correction


@dataclass
class CoupledOscillatorArray:
    """Array of coupled oscillators for cross-frequency dynamics.

    Models theta-gamma coupling:
        Slow oscillator (theta, 5 Hz) modulates amplitude of
        fast oscillators (gamma, 40 Hz) → information routing.

    REF: Buzsáki 2006 — "Rhythms of the Brain"
    REF: Canolty & Knight 2010 — cross-frequency coupling
    """

    oscillators: list = field(default_factory=list)
    coupling_matrix: list = field(default_factory=list)  # K[i][j]

    def add(self, osc: ResonantOscillator):
        """Add an oscillator to the array."""
        n = len(self.oscillators)
        self.oscillators.append(osc)
        # Extend coupling matrix
        for row in self.coupling_matrix:
            row.append(0.0)
        self.coupling_matrix.append([0.0] * (n + 1))

    def set_coupling(self, i: int, j: int, strength: float):
        """Set coupling strength from oscillator i to j."""
        self.coupling_matrix[i][j] = strength

    def step(self, dt: float) -> list:
        """Advance all oscillators with mutual coupling.

        Returns list of output values.
        """
        n = len(self.oscillators)
        outputs = []

        # Compute coupling forces
        phases = [osc.phase for osc in self.oscillators]

        for i in range(n):
            # Sum coupling from all other oscillators
            i_ext = 0.0
            for j in range(n):
                if i != j and self.coupling_matrix[j][i] != 0:
                    K = self.coupling_matrix[j][i]
                    phase_diff = phases[j] - phases[i]
                    i_ext += K * math.sin(phase_diff)

            out = self.oscillators[i].step(dt, i_ext)
            outputs.append(out)

        return outputs
