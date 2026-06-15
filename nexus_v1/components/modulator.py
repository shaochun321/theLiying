"""nexus_v1.components.modulator — Neuromodulator.

TYPE:HYBRID — Diffusive modulatory signal mapped to both
DAC/PGA (electronics) and monoamine neurotransmitters (biology).

===========================================================
ZERO DEPENDENCY ON EXISTING NEXUS CODE.
===========================================================

Electronic Equivalent:
    Digital-to-Analog Converter (DAC) + Programmable Gain Amplifier (PGA):
    - Global bias voltage applied to multiple circuits
    - Slow-changing control signal that scales gain

    Also: substrate bias in CMOS (body effect):
    - Vbs shifts threshold voltage of all transistors on chip
    - Global modulation of circuit behavior

Biological Equivalent:
    Monoamine neurotransmitter systems:

    1. Dopamine (DA):
       - Source: VTA, substantia nigra
       - Target: striatum, prefrontal cortex
       - Effect: reward signal, STDP modulation
       - Timescale: seconds to minutes
       - REF: Schultz 1998 — reward prediction error

    2. Serotonin (5-HT):
       - Source: dorsal raphe nucleus
       - Target: widespread cortical/limbic
       - Effect: mood, arousal, excitability
       - Timescale: minutes to hours
       - REF: Azmitia 1999

    3. Acetylcholine (ACh):
       - Source: basal forebrain, pedunculopontine
       - Target: cortex, hippocampus
       - Effect: attention, signal-to-noise
       - Timescale: 100ms to seconds
       - REF: Hasselmo 2006 — ACh and cortical function

    4. Norepinephrine (NE):
       - Source: locus coeruleus
       - Target: widespread
       - Effect: alertness, gain control
       - REF: Aston-Jones & Cohen 2005

    Key biological principle:
    Neuromodulators are NOT point-to-point like synapses.
    They are VOLUME TRANSMISSION — released diffusely,
    affecting entire regions over slow timescales.

    REF: Marder & Thirumalai 2002 — "Cellular, synaptic and
    network effects of neuromodulation"

Mathematical Model:
    Concentration dynamics:
        dc/dt = release(t) - c/τ_decay

    Effects on target neurons:
        synapse_gain *= (1 + α_gain × c)
        bias_current += α_bias × c
        stdp_lr *= (1 + α_lr × c)
        threshold += α_thresh × c
"""

import math
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Neuromodulator:
    """Diffusive neuromodulatory signal.

    Models a slow, volume-transmitted chemical signal that
    globally modulates the behavior of target neurons.

    Unlike synaptic transmission (fast, point-to-point),
    neuromodulation is slow, diffuse, and affects parameters
    (gain, threshold, learning rate) rather than membrane voltage.

    Args:
        name: modulator identity (e.g., "dopamine", "serotonin")
        tau_decay: concentration decay time constant (seconds)
        tau_release: release smoothing time constant (seconds)
        baseline: tonic concentration level
        max_concentration: saturation level

    Effect coefficients (how concentration modulates targets):
        alpha_gain: multiplicative effect on synapse gain
        alpha_bias: additive effect on bias current
        alpha_lr: multiplicative effect on STDP learning rate
        alpha_threshold: additive effect on spike threshold
    """

    name: str = "modulator"
    tau_decay: float = 2.0        # seconds — slow decay
    tau_release: float = 0.5      # seconds — release smoothing
    baseline: float = 0.1         # tonic level
    max_concentration: float = 1.0

    # Effect coefficients
    alpha_gain: float = 0.5       # gain modulation
    alpha_bias: float = 0.0       # bias modulation
    alpha_lr: float = 1.0         # learning rate modulation
    alpha_threshold: float = 0.0  # threshold modulation

    # Internal state
    _concentration: float = field(default=0.1, repr=False)
    _release_input: float = field(default=0.0, repr=False)
    _t: float = field(default=0.0, repr=False)

    def __post_init__(self):
        self._concentration = self.baseline

    @property
    def concentration(self) -> float:
        """Current modulator concentration."""
        return self._concentration

    @property
    def is_elevated(self) -> bool:
        """Whether concentration is above baseline."""
        return self._concentration > self.baseline * 1.5

    def release(self, amount: float):
        """Trigger modulator release (phasic burst).

        Args:
            amount: release amount (added to release buffer)
        """
        self._release_input += amount

    def step(self, dt: float) -> float:
        """Update concentration dynamics.

        dc/dt = release_smoothed - c/τ_decay + baseline/τ_decay

        Args:
            dt: time step

        Returns:
            Current concentration
        """
        self._t += dt

        # Release rate: exponential drain from release buffer
        # release_rate has units [concentration / second]
        release_rate = self._release_input / max(self.tau_release, 0.001)
        drain = release_rate * dt
        drain = min(drain, self._release_input)  # don't drain more than available
        self._release_input -= drain

        # Concentration dynamics (proper ODE)
        # dc/dt = release_rate - (c - baseline) / τ_decay
        decay_rate = (self._concentration - self.baseline) / \
            max(self.tau_decay, 0.001)
        dc_dt = release_rate - decay_rate
        self._concentration += dc_dt * dt

        # Clamp
        self._concentration = max(0.0, min(self.max_concentration,
                                           self._concentration))

        return self._concentration

    # ── Effect computation ──────────────────────────────────

    def gain_factor(self) -> float:
        """Multiplicative gain factor for synaptic strength.

        Returns:
            Factor >= 0. Example: 1.0 at baseline, 1.5 at elevated.
        """
        return 1.0 + self.alpha_gain * (self._concentration - self.baseline)

    def bias_offset(self) -> float:
        """Additive bias current offset.

        Returns:
            Current to add to neuron's bias.
        """
        return self.alpha_bias * self._concentration

    def lr_factor(self) -> float:
        """Learning rate scaling factor.

        Models "three-factor learning rule":
            Δw = STDP_signal × DA_signal
        Only potentiate if reward signal (DA) is present.

        REF: Izhikevich 2007 — "Solving the distal reward problem"
        """
        return 1.0 + self.alpha_lr * (self._concentration - self.baseline)

    def threshold_offset(self) -> float:
        """Threshold modification.

        Returns:
            Value to add to neuron spike threshold.
        """
        return self.alpha_threshold * self._concentration

    def reset(self):
        """Reset to baseline."""
        self._concentration = self.baseline
        self._release_input = 0.0
        self._t = 0.0


# ── Preset modulators ──────────────────────────────────────

def create_dopamine() -> Neuromodulator:
    """Create a dopamine-like modulator.

    DA: reward prediction error → STDP gating.
    """
    return Neuromodulator(
        name="dopamine",
        tau_decay=2.0,        # slow (seconds)
        tau_release=0.2,      # fast burst
        baseline=0.1,
        max_concentration=1.0,
        alpha_gain=1.5,       # EXP-012: was 0.3 → ±27% too weak. 1.5 → 1.0x–2.35x range
        alpha_bias=0.0,       # no bias effect
        alpha_lr=2.0,         # strong LR boost (three-factor)
        alpha_threshold=0.0,
    )


def create_serotonin() -> Neuromodulator:
    """Create a serotonin-like modulator.

    5-HT: arousal/mood → global excitability.
    """
    return Neuromodulator(
        name="serotonin",
        tau_decay=10.0,       # very slow (tens of seconds)
        tau_release=1.0,
        baseline=0.2,
        max_concentration=0.8,
        alpha_gain=0.0,       # no gain effect
        alpha_bias=0.01,      # slight bias increase
        alpha_lr=0.0,         # no learning effect
        alpha_threshold=-0.05,  # lower threshold (more excitable)
    )


def create_acetylcholine() -> Neuromodulator:
    """Create an acetylcholine-like modulator.

    ACh: attention → signal-to-noise enhancement.
    """
    return Neuromodulator(
        name="acetylcholine",
        tau_decay=0.5,        # faster than DA
        tau_release=0.1,
        baseline=0.15,
        max_concentration=1.0,
        alpha_gain=1.0,       # strong gain boost
        alpha_bias=0.0,
        alpha_lr=0.5,         # moderate LR boost
        alpha_threshold=0.0,
    )
