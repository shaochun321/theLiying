"""nexus_v1.components.thermal_membrane — Scalar thermal sensor.

Biological basis: bacterial MCP (Methyl-accepting Chemotaxis Protein).

Design principle (C-004: autogenous spacetime):
  Temperature is a SCALAR field. A sensor at one point can only measure
  one number: T(x,y,z). It CANNOT measure gradient direction.

  Direction information emerges from cross-modal learning:
    "When I was moving in direction X (vestibular), I got warmer (thermal)"
    → Hebbian: w(oto_x, therm) increases
    → The organism learns "heat source is in +x direction"
    → WITHOUT directional thermal sensors!

  This is exactly how C. elegans achieves thermotaxis (Mori & Ohshima 1995):
    - AFD neuron: single temperature sensor with adaptation
    - Temporal comparison: dT/dt during locomotion
    - Klinokinesis: modulate turning rate based on dT/dt sign

Structure:
  - 1 temperature sensor at body center
  - Methylation adaptation: auto-zeros to background (τ=200 steps)
  - Output: dT/dt only (phasic, change rate)
  - NOT: absolute temperature (the organism doesn't need it)
  - NOT: directional gradient (physically impossible at one point)

BIO references:
  - Mori & Ohshima 1995: C. elegans thermotaxis
  - Paster & Bhatt (eLife 2021): bacterial MCP temporal sensing
  - Key insight: "bacteria detect dT/dt, not spatial ∇T directly"

§ corresponds to G-001 (global math formulas)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .world import World, Body


@dataclass
class ThermalMembrane:
    """Scalar thermal sensor with methylation adaptation.

    ONE sensor. ONE number. Direction comes from cross-modal learning.

    Output signals for the neural circuit:
      therm:   adapted temperature relative to baseline (how different from normal)
      dtherm:  rate of temperature change (getting hotter/colder)

    The 'therm' signal feeds into Encoding as the 7th axis.
    'dtherm' is used by the irregular pathway encoder.

    Methylation adaptation (τ=200):
      M(t+dt) = M(t) + (T - M(t)) × dt/τ
      adapted = T - M
      → Constant temperature → adapted → 0 (silent)
      → Temperature change → adapted ≠ 0 (signal)
    """

    methylation_tau: float = 200.0   # adaptation time constant (slow)

    # Internal state
    _methylation: float = 0.0        # adapted baseline
    _prev_T: float = 0.0             # previous temperature (for dT/dt)
    _initialized: bool = False

    def sense(self, world: World, body: Body, dt: float = 0.001) -> dict:
        """Sample temperature at body position, return adapted signals.

        Returns:
            dict with keys:
                'therm':  adapted temperature (T - M), relative to baseline
                'dtherm': temperature change rate dT/dt
        """
        # 1. Sample temperature at body center (ONE point, ONE number)
        T_raw = world.temperature_at(body.position)

        # 2. Initialize on first call
        if not self._initialized:
            self._methylation = T_raw
            self._prev_T = T_raw
            self._initialized = True

        # 3. Methylation adaptation
        # dM/dt = (T - M) / τ
        alpha = min(dt / self.methylation_tau, 1.0)
        self._methylation += (T_raw - self._methylation) * alpha

        # Adapted signal: deviation from adapted baseline
        adapted = T_raw - self._methylation

        # 4. Temporal derivative: dT/dt
        dT = (T_raw - self._prev_T) / max(dt, 1e-6)
        self._prev_T = T_raw

        # 5. Clamp to reasonable range
        adapted = max(-5.0, min(10.0, adapted))
        dT = max(-10.0, min(10.0, dT))

        return {
            'therm': adapted,    # tonic: how different from normal
            'dtherm': dT,        # phasic: rate of change
        }

    def get_state(self) -> dict:
        """Get sensor state for debugging."""
        return {
            'methylation': self._methylation,
            'prev_T': self._prev_T,
            'adapted': self._prev_T - self._methylation,
        }
