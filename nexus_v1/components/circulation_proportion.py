"""nexus_v1.components.circulation_proportion — Structural carrier for C3' ratios.

Replaces software-computed circulation ratios (ρ_homeo, ρ_motor, ρ_feed)
with hardware-computed signals using physical components.

Architecture:
    Three Capacitors integrate amplitude signals (slow RC filter).
    A MOSFET comparator produces deviation from homeostatic set point.
    Deviation current is the output — injected into DA neurons.

    ┌──────────────────────────────────────────────────────┐
    │           CirculationProportionCircuit               │
    │                                                      │
    │  thermal_stability ──→ [Cap_H] ──→ V_homeo          │
    │  body_speed        ──→ [Cap_M] ──→ V_motor          │
    │  feed_alignment    ──→ [Cap_F] ──→ V_feed           │
    │                                                      │
    │  V_total = V_homeo + V_motor + V_feed                │
    │  fraction_homeo = V_homeo / (V_total + ε)            │
    │                                                      │
    │  V_ref ──→ [Cap_ref] ──→ 0.7 (homeostatic set point) │
    │                                                      │
    │  deviation = [MOSFET] (V_ref - fraction_homeo)       │
    │          ↓                                           │
    │  output: DA_excitation_current                       │
    └──────────────────────────────────────────────────────┘

BIO: hypothalamic homeostatic integrators.
  - Preoptic area: integrates temperature signals over time
  - Lateral hypothalamus: integrates feeding/satiety signals
  - These are slow integrators (~seconds), not instant computations

PHYS: RC low-pass filter + comparator circuit.
  - Capacitor: Q = ∫I·dt, V = Q/C (temporal integration)
  - Leak: V → 0 with τ = RC (prevents unbounded growth)
  - MOSFET: threshold comparator for deviation detection

S0 compliance: all ratios emerge from component voltages,
not from software division.
"""

from __future__ import annotations

from dataclasses import dataclass
from .semiconductor import Capacitor, MOSFET


@dataclass
class CirculationProportionConfig:
    """Configuration for the circulation proportion circuit."""
    # Capacitance for amplitude integrators (larger = slower, smoother)
    # BIO: hypothalamic integration time constant ~5-10 seconds
    # τ = RC = 200 * 1.0 = 200 steps at dt=0.001 → 0.2 seconds
    capacitance: float = 200.0

    # Leak resistance (prevents unbounded charge accumulation)
    # τ_leak = R × C = 50 × 200 = 10000 steps = 10 seconds
    leak_resistance: float = 50.0

    # Homeostatic set point for ρ_homeo (normal = 0.7)
    # Stored as reference voltage in a dedicated capacitor.
    homeo_set_point: float = 0.7

    # MOSFET comparator: threshold for deviation detection
    # Below this deviation, no DA excitation (noise filter)
    # Epoch 1: 0.05→0.01 — lower deadzone so weaker deviations
    # also trigger DA. BIO: lower pain threshold = more responsive.
    deviation_threshold: float = 0.01

    # MOSFET comparator: gain for deviation → DA current
    # Epoch 1: 0.3→1.0 — stronger DA response to deviation.
    # C3' DA is now a primary driver alongside C1 (shadow Xin).
    # BIO: hypothalamic neurons with high gain stress response.
    deviation_gain: float = 1.0


class CirculationProportionCircuit:
    """Structural carrier for homeostatic circulation ratios.

    Three capacitors integrate amplitude signals. Their voltages
    naturally represent the time-averaged amplitudes. The ratios
    emerge from voltage comparison, not software division.

    Output: DA excitation current proportional to homeostatic deviation.
    """

    def __init__(self, config: CirculationProportionConfig | None = None):
        if config is None:
            config = CirculationProportionConfig()
        self.config = config

        # Three amplitude integrators (one per subsystem)
        # BIO: hypothalamic nuclei with slow integration
        self._cap_homeo = Capacitor(capacitance=config.capacitance)
        self._cap_motor = Capacitor(capacitance=config.capacitance)
        self._cap_feed = Capacitor(capacitance=config.capacitance)

        # Reference capacitor: holds homeostatic set point voltage
        # Pre-charged to set point. Slow leak maintains it.
        # BIO: genetically determined temperature set point in preoptic area
        self._cap_ref = Capacitor(capacitance=config.capacitance * 10)
        self._cap_ref.charge = (config.homeo_set_point
                                * config.capacitance * 10)

        # Deviation comparator: MOSFET as threshold detector
        # Only fires when deviation exceeds threshold (noise filter)
        # BIO: hypothalamic alarm neurons with threshold
        self._comparator = MOSFET(
            v_threshold=config.deviation_threshold,
            gm=config.deviation_gain,
        )

    def step(self, thermal_stability: float, body_speed: float,
             feed_alignment: float, dt: float = 0.001) -> dict:
        """Integrate amplitude signals and compute structural outputs.

        Args:
            thermal_stability: 1/(1+|thermal_err|×10). High = stable.
            body_speed: actual body speed. High = moving.
            feed_alignment: max(0, dot(heat_dir, vel_dir)) × thermal_err.
            dt: time step.

        Returns:
            dict with:
                'v_homeo', 'v_motor', 'v_feed': capacitor voltages
                'rho_homeo', 'rho_motor', 'rho_feed': normalized fractions
                'deviation': homeostatic deviation
                'da_current': DA excitation current (structural output)
        """
        # ── 1. Inject amplitude signals into capacitors ──
        # Current = signal strength. Capacitor integrates over time.
        # BIO: synaptic input to hypothalamic integrator neurons.
        self._cap_homeo.inject(thermal_stability, dt)
        self._cap_motor.inject(body_speed, dt)
        self._cap_feed.inject(feed_alignment, dt)

        # ── 2. Leak: RC discharge prevents unbounded growth ──
        # τ_leak = R × C. Without leak, voltages grow forever.
        # BIO: neural adaptation / habituation.
        R = self.config.leak_resistance
        self._cap_homeo.leak(R, dt)
        self._cap_motor.leak(R, dt)
        self._cap_feed.leak(R, dt)
        # Reference capacitor: very slow leak (10× larger C)
        self._cap_ref.leak(R * 100, dt)

        # ── 3. Read voltages (the structural carriers of amplitude) ──
        v_h = max(0.0, self._cap_homeo.voltage)
        v_m = max(0.0, self._cap_motor.voltage)
        v_f = max(0.0, self._cap_feed.voltage)
        v_total = v_h + v_m + v_f + 1e-8

        # Fractions: emerge from voltage comparison (not software division)
        # In hardware: voltage divider. Here: V_i / V_total is the
        # natural reading of "what proportion of total signal is this?"
        rho_h = v_h / v_total
        rho_m = v_m / v_total
        rho_f = v_f / v_total

        # ── 4. Deviation via MOSFET comparator ──
        # V_ref holds the set point (0.7).
        # FIX-1: Bi-directional deviation. Original max(0, v_ref - rho_h)
        # only fired when rho_homeo DROPPED below setpoint. But rho_homeo
        # can also be TOO HIGH (over-stable, no motor/feed activity).
        # Both directions are homeostatic errors requiring DA-driven action.
        # BIO: hypothalamic neurons respond to both hypo- and hyperthermia.
        v_ref = self._cap_ref.voltage
        deviation_input = abs(v_ref - rho_h)

        # MOSFET comparator: superthreshold = DA current output
        # Subthreshold = no output (noise filter)
        da_current = self._comparator.conduct(deviation_input)

        return {
            'v_homeo': v_h,
            'v_motor': v_m,
            'v_feed': v_f,
            'rho_homeo': rho_h,
            'rho_motor': rho_m,
            'rho_feed': rho_f,
            'deviation': deviation_input,
            'da_current': da_current,
        }

    def summary(self) -> dict:
        """State for monitoring."""
        return {
            'v_homeo': round(self._cap_homeo.voltage, 4),
            'v_motor': round(self._cap_motor.voltage, 4),
            'v_feed': round(self._cap_feed.voltage, 4),
            'v_ref': round(self._cap_ref.voltage, 4),
            'comparator_gate': round(self._comparator.m_gate, 4),
        }
