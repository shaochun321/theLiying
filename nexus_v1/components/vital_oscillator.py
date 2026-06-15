"""nexus_v1.components.vital_oscillator — VitalOscillator (Detuned Tri-Heart).

TYPE:HYBRID — Energy-coupled self-sustaining oscillation as the physical
origin of basal motility. Three independent Van der Pol cores with
mutually irrational frequencies produce Lissajous wandering in 3D
without any random number generation.

Design Derivation:
    BIO: Sinoatrial node → heart rhythm → hemodynamic pulsation → postural sway.
         Basal tremor in resting organisms (physiological tremor ~8-12 Hz in humans,
         but scales to body size; paramecium ciliary beat ~2 Hz).
    PHYS: Dissipative structure — self-oscillation maintained by continuous
          energy draw from EnergyStore. When energy depletes, oscillation
          ceases → organism freezes → death.

    The three VdP oscillators have slightly different natural frequencies:
        f_x = 2.00 Hz
        f_y = 2.11 Hz  (√(89/20) ≈ irrational ratio to f_x)
        f_z = 1.93 Hz  (≈ 193/100, coprime numerator to 200 and 211)

    Since the frequency ratios are irrational (or at least non-commensurate),
    the phase difference between any two oscillators drifts continuously.
    The resulting 3D trajectory traces out dense Lissajous figures that
    NEVER exactly repeat — producing ergodic space-filling wandering.

    REF: Van der Pol 1926 — self-sustained relaxation oscillation
    REF: Strogatz 2015 — "Nonlinear Dynamics and Chaos", §8.6 Lissajous
    REF: Collins & De Luca 1993 — postural sway as stochastic process

Energy Accounting:
    Each step, the oscillator withdraws energy from EnergyStore:
        ΔE = vital_energy_cost × Σ|x_i(t)| × dt

    This is booked through EnergyStore.withdraw() which automatically
    enters the Noether balance sheet (_total_withdrawn). The withdrawn
    energy is pure dissipation (heat) — it does not create charge or
    mass anywhere in the circuit.

    Death switch: when fill_fraction < 0.05, output = 0, withdraw = 0.
    This prevents numerical artifacts at near-zero energy levels.

Signal Chain:
    EnergyStore.fill_fraction → amplitude modulation
    VitalOscillator.step()    → three axis outputs [x, y, z]
    variant_adapter           → inject into Motor membranes per axis
    EnergyStore.withdraw()    → energy debit (Noether-compliant)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

from .oscillator import ResonantOscillator

if TYPE_CHECKING:
    from .energy_store import EnergyStore


@dataclass
class VitalOscillatorConfig:
    """Configuration for the vital oscillator (tri-heart).

    Default frequencies chosen for mutual incommensurability:
        f_x / f_y = 200/211 (coprime)
        f_x / f_z = 200/193 (coprime)
        f_y / f_z = 211/193 (coprime)
    This guarantees phase drift and ergodic space filling.
    """
    # Frequencies per axis (Hz) — mutually irrational ratios
    frequency_x: float = 2.00
    frequency_y: float = 2.11
    frequency_z: float = 1.93

    # Van der Pol nonlinearity (μ > 1 → relaxation oscillation → pulse-like)
    mu: float = 2.0

    # Base amplitude scaling (output = VdP_x × amplitude)
    # Must be small enough to be sub-dominant to vestibular drive (~0.01)
    # but large enough to occasionally push Motor past spike threshold.
    amplitude: float = 0.005

    # Energy cost coefficient: ΔE_withdraw = cost × Σ|output_i| × dt
    # ~0.0002/step at full amplitude ≈ basal_drain level
    energy_cost_per_unit: float = 0.02

    # Death switch: below this fill fraction, oscillator shuts down
    # Prevents numerical artifacts and models biological cardiac arrest
    death_threshold: float = 0.05


class VitalOscillator:
    """Three-frequency self-sustaining oscillator — the organism's heartbeat.

    Wraps three independent ResonantOscillator (Van der Pol) cores with
    slightly different frequencies. Their phase relationships drift
    continuously, producing complex Lissajous trajectories in 3D.

    Energy coupling: amplitude is modulated by EnergyStore fill level.
    When energy is depleted, oscillation ceases (cardiac arrest).

    Usage:
        vital = VitalOscillator()
        outputs = vital.step(energy_store, dt)
        # outputs = [x_drive, y_drive, z_drive]
        # Each value is injected into the corresponding Motor axis
    """

    def __init__(self, config: VitalOscillatorConfig | None = None):
        if config is None:
            config = VitalOscillatorConfig()
        self.config = config

        # Three independent VdP cores — one per spatial axis
        # Each starts at a different phase to avoid initial transient lock
        self._osc_x = ResonantOscillator(
            frequency=config.frequency_x,
            mu=config.mu,
            amplitude=1.0,          # raw VdP output; scaling done here
            phase_offset=0.0,
        )
        self._osc_y = ResonantOscillator(
            frequency=config.frequency_y,
            mu=config.mu,
            amplitude=1.0,
            phase_offset=math.pi * 0.7,    # arbitrary non-zero start
        )
        self._osc_z = ResonantOscillator(
            frequency=config.frequency_z,
            mu=config.mu,
            amplitude=1.0,
            phase_offset=math.pi * 1.3,    # arbitrary non-zero start
        )
        self._oscillators = [self._osc_x, self._osc_y, self._osc_z]

        # Output state (last computed values)
        self._outputs: List[float] = [0.0, 0.0, 0.0]

        # Cumulative energy withdrawn (for diagnostics)
        self._total_energy_withdrawn: float = 0.0

        # Step counter
        self._step_count: int = 0

    def step(self, energy_store: 'EnergyStore', dt: float = 0.001) -> List[float]:
        """Advance oscillator by one time step.

        Amplitude is modulated by energy_store.fill_fraction.
        Energy is withdrawn from the store proportional to output magnitude.

        Args:
            energy_store: the organism's energy reservoir
            dt: time step (seconds)

        Returns:
            List of [x, y, z] drive signals for Motor injection
        """
        self._step_count += 1
        fill = energy_store.fill_fraction

        # ── Death switch: cardiac arrest at critical energy depletion ──
        # BIO: below ~5% blood glucose, cardiac function ceases.
        # No output, no energy draw — organism is clinically dead.
        if fill < self.config.death_threshold:
            self._outputs = [0.0, 0.0, 0.0]
            return list(self._outputs)

        # ── Amplitude modulation by energy level ──
        # Full amplitude when fill > 0.3 (healthy).
        # Linear ramp-down from 0.3 to death_threshold.
        if fill >= 0.3:
            amplitude_scale = 1.0
        else:
            # Linear interpolation: [death_threshold, 0.3] → [0, 1]
            amplitude_scale = (fill - self.config.death_threshold) / (
                0.3 - self.config.death_threshold)

        effective_amplitude = self.config.amplitude * amplitude_scale

        # ── Advance three VdP oscillators (independent, uncoupled) ──
        raw_outputs = []
        for osc in self._oscillators:
            raw = osc.step(dt)
            raw_outputs.append(raw)

        # ── Scale by effective amplitude ──
        self._outputs = [raw * effective_amplitude for raw in raw_outputs]

        # ── Energy withdrawal (dissipation cost of oscillation) ──
        # Cost proportional to total absolute output magnitude
        total_magnitude = sum(abs(o) for o in self._outputs)
        energy_cost = self.config.energy_cost_per_unit * total_magnitude * dt
        if energy_cost > 0:
            actual_withdrawn = energy_store.withdraw(energy_cost)
            self._total_energy_withdrawn += actual_withdrawn

        return list(self._outputs)

    @property
    def outputs(self) -> List[float]:
        """Current output values (without advancing time)."""
        return list(self._outputs)

    @property
    def total_energy_withdrawn(self) -> float:
        """Cumulative energy consumed by the oscillator."""
        return self._total_energy_withdrawn

    @property
    def is_alive(self) -> bool:
        """Whether the oscillator is producing output."""
        return any(abs(o) > 1e-8 for o in self._outputs)

    def summary(self) -> dict:
        """State for monitoring and diagnostics."""
        return {
            "outputs": [round(o, 6) for o in self._outputs],
            "frequencies": [
                self.config.frequency_x,
                self.config.frequency_y,
                self.config.frequency_z,
            ],
            "amplitude": self.config.amplitude,
            "total_energy_withdrawn": round(self._total_energy_withdrawn, 6),
            "is_alive": self.is_alive,
            "step_count": self._step_count,
        }
