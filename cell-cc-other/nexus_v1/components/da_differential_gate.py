"""nexus_v1.components.da_differential_gate — VTA dopamine RPE gate.

TYPE:BIO|SEMI
DA fires on positive rate-of-change of energy (reward), not absolute level.
Physical primitives: Capacitor (one-step delay) + MOSFET (half-wave rectifier).

BIO: VTA dopamine neurons encode reward prediction error (RPE): they burst on
unexpected reward and are silent on expected or absent reward.
REF: Schultz W, Dayan P, Montague PR (1997) "A neural substrate of prediction
     and reward." Science 275:1593-1599.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DADifferentialConfig:
    # BIO: RPE gain — scales fill_fraction rate-of-change to DA current.
    # DERIVED: target DA_peak=0.8 / (typical Δfill_fraction/dt ≈ 0.108) ≈ 7.4
    # EXP-CAL-DA: η_da=7.5 chosen as nearest clean value. clip_max=5.0 provides
    # protection against sudden large energy deposits (burst feeding).
    eta_da: float = 7.5
    # MOSFET cutoff: only positive Δfill triggers DA (RPE = improvement only)
    threshold: float = 0.0
    # Saturation cap: prevents runaway on sudden large energy deposits
    clip_max: float = 5.0


class DADifferentialGate:
    """TYPE:BIO|SEMI — Reward prediction error gate for dopamine drive.

    Computes DA signal as positive rate-of-change in energy fill:
        DA(t) = clip(max(0, eta_da × Δfill / dt), clip_max)
    where Δfill = fill_fraction(t) - fill_fraction(t-1).

    Replaces absolute-deviation DA trigger in circulation_proportion.py.
    MOSFET half-wave rectification: gate closed on zero/negative Δfill.

    BIO: VTA RPE signal — burst on unexpected reward, silent on steady state.
    REF: Schultz et al. 1997, Science 275:1593-1599.
    """

    def __init__(self, config: DADifferentialConfig | None = None,
                 initial_fill: float = 0.5):
        self.config = config or DADifferentialConfig()
        # Capacitor: holds fill_fraction from previous step
        self._fill_prev: float = initial_fill
        self._da_output: float = 0.0

    def step(self, fill_fraction: float, dt: float = 0.001) -> float:
        """Compute DA drive from energy rate-of-change.

        Args:
            fill_fraction: EnergyStore.fill_fraction at current step [0, 1].
            dt: timestep in seconds (for rate-of-change normalization).

        Returns:
            Non-negative DA current proportional to energy improvement.
        """
        delta_fill = fill_fraction - self._fill_prev
        self._fill_prev = fill_fraction

        # Rate-of-change: Δfill / dt
        raw = self.config.eta_da * delta_fill / max(dt, 1e-9)
        # MOSFET half-wave rectification: zero/negative delta → gate closed
        self._da_output = min(max(0.0, raw - self.config.threshold),
                              self.config.clip_max)
        return self._da_output

    @property
    def da_output(self) -> float:
        return self._da_output
