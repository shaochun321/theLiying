"""nexus_v1.circuit.motor_decision — Middle decision layer.

Architecture:

    Vestibular → Met → HC → Aff → Enc → Col
                                         │
                              MotionState extraction
                              (运动势, 时间测度, 空间测度)
                                         │
                              MotorDecisionLayer
                              ┌────────────────────┐
                              │  MotorRhythm (CPG)  │  ← 运动节奏 (VdP)
                              │  DirectionSelect    │  ← 方向选择 (PASSTHROUGH)
                              │  SpatialNavigator   │  ← 空间导航 (PASSTHROUGH)
                              └────────────────────┘
                                         │
                                      Motor → Muscle → Body

BIO references:
  - MotorRhythm: spinal CPG (Grillner 2006), lamprey interneurons
  - DirectionSelect: basal ganglia (Mink 1996), action selection
  - SpatialNavigator: hippocampus (O'Keefe 1978), path integration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..components.oscillator import ResonantOscillator


@dataclass
class MotionState:
    """TYPE:INFRA — Extracted motion state from vestibular processing chain.

    This is the OUTPUT of the motion state discrimination structure
    (Met→HC→Aff→Enc→Col) — the foundation for all higher motor functions.

    Three fundamental measures:
      motion_potential: scalar magnitude of current motion (how much moving)
      temporal_measure: dict of per-axis temporal change rates (when/how fast changing)
      spatial_measure:  dict of per-axis static orientation (where am I oriented)

    BIO: vestibular nuclei output to cerebellum, basal ganglia, cortex.
    """
    # Scalar: overall motion intensity (sum of |Col activations|)
    motion_potential: float = 0.0

    # Per-axis temporal measure: rate of change (from irregular pathway)
    # BIO: irregular afferents encode AC component (jerk, transient)
    temporal_measure: Dict[str, float] = field(default_factory=dict)

    # Per-axis spatial measure: static orientation (from regular pathway)
    # BIO: regular afferents encode DC component (gravity, tilt)
    spatial_measure: Dict[str, float] = field(default_factory=dict)

    # Per-axis otolith: linear acceleration
    # BIO: utricle + saccule
    otolith_acc: Dict[str, float] = field(default_factory=dict)

    # Body speed (proprioceptive)
    body_speed: float = 0.0

    # Thermal: adapted temperature
    thermal: float = 0.0

    # ── C3': Homeostatic circulation coupling ──
    # Three circulation amplitudes (raw)
    homeo_amplitude: float = 0.0     # homeostasis loop amplitude
    motor_amplitude: float = 0.0     # motor loop amplitude
    feed_amplitude: float = 0.0      # feeding loop amplitude
    # Normalized ratios (sum to 1.0)
    rho_homeo: float = 0.7           # homeostasis fraction (normal ~0.7)
    rho_motor: float = 0.2           # motor fraction (normal ~0.2)
    rho_feed: float = 0.1            # feeding fraction (normal ~0.1)
    # Deviation from normal homeostasis ratio
    homeo_deviation: float = 0.0     # max(0, 0.7 - rho_homeo)
    # Energy absorbed from heat sources this step
    energy_absorbed: float = 0.0
    # EnergyStore fill level [0, 1]. Bridges metabolic state → behavior.
    # BIO: blood glucose level → hypothalamic hunger signal.
    fill_fraction: float = 1.0

    # ── A7: Motor potential (ν = dK/dt) ──
    # ν > 0: accelerating (gaining kinetic energy)
    # ν < 0: decelerating (losing kinetic energy to drag)
    # ν = 0: steady state (constant speed or at rest)
    kinetic_energy: float = 0.0      # K = ½mv²
    motor_potential: float = 0.0     # ν = dK/dt
    # Per-axis components: ν_i = m × v_i × a_i
    motor_potential_xyz: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    # Polarization: P = max(|ν_i|) / Σ|ν_i|. Range [1/3, 1].
    # P→1: single-axis motion (偏振). P→1/3: uniform (非偏振).
    polarization: float = 0.333

    # ── Vital Oscillator (basal heartbeat drive) ──
    # Per-axis vital drive injected into Motor membranes
    # BIO: postural sway from cardiac/respiratory rhythm
    vital_pulse: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    # Scalar: total vital oscillation magnitude
    vital_amplitude: float = 0.0

    # ── Phase 4: AGC (automatic gain control) ──
    # Current effective gain multiplier from AGC.
    # 1.0 = no boost (energy/DA sufficient).
    # 5.0 = maximum boost (severe deficit).
    # BIO: HPA axis cortisol → locomotor drive scaling.
    agc_gain: float = 1.0


class MotorRhythmGenerator:
    """TYPE:BIO — Central Pattern Generator (CPG) — Van der Pol oscillator model.

    Three independent VdP oscillators, one per motor axis, with 120° initial
    phase offset. Each generates a rhythmic envelope that modulates motor output.

    Architecture (per axis i):
      ResonantOscillator_i.step(dt, i_ext=ε·temporal_i)
           ↓  raw ∈ [-2, +2] (VdP limit cycle)
      envelope = (raw + 2) / 4  ∈ [0, 1]
           ↓
      motor_out_i = motor_in_i × envelope

    Entrainment: vestibular otolith signal injected as i_ext into VdP.
    BIO: spinal CPG interneurons (Grillner 2006, Science 296:1532).
    PHYS: Van der Pol relaxation oscillator = LC tank + negative resistance (NDR).
    REF: Ijspeert 2008, Neural Networks — CPG for locomotion control.

    FIX: HC-025 — replaced Kuramoto math.sin with VdP ResonantOscillator.
    Kuramoto coupling (sin(φ_j-φ_i)) was semantic-math (python formula replaces
    physical oscillator dynamics). VdP produces equivalent rhythmic envelope
    without any trigonometric hardcoding.
    """

    INTRINSIC_FREQ: float = 1.0   # Hz — lamprey CPG range (Grillner 2006: 0.5-5Hz)
    ENTRAINMENT_EPS: float = 2.0  # entrainment sensitivity (vestibular → i_ext)

    def __init__(self):
        self._active = True

        # Three VdP oscillators, 120° phase offset — swim-like triphasic pattern
        # BIO: lamprey spinal CPG segments oscillate at 120° offset (Grillner 2006)
        # PHYS: ResonantOscillator = VdP, same class used inside VitalOscillator
        self._osc_x = ResonantOscillator(
            frequency=self.INTRINSIC_FREQ, mu=2.0, amplitude=1.0, phase_offset=0.0)
        self._osc_y = ResonantOscillator(
            frequency=self.INTRINSIC_FREQ, mu=2.0, amplitude=1.0, phase_offset=2.094)
        self._osc_z = ResonantOscillator(
            frequency=self.INTRINSIC_FREQ, mu=2.0, amplitude=1.0, phase_offset=4.189)
        self._oscillators = [self._osc_x, self._osc_y, self._osc_z]

        self._temporal_ema = [0.0, 0.0, 0.0]

    def modulate(self, motor_acts: List[float],
                 state: MotionState, dt: float = 0.001) -> List[float]:
        """Apply CPG rhythmic modulation to motor activations.

        Pipeline:
          1. Update entrainment EMA from vestibular otolith
          2. Step VdP oscillators (with entrainment forcing i_ext)
          3. Map raw VdP output [-2,+2] → envelope [0,1]
          4. Multiply motor activations by envelope

        Returns:
            Rhythmically modulated motor activations.
        """
        axes = ['x', 'y', 'z']
        oto_keys = ['oto_x', 'oto_y', 'oto_z']

        # Entrainment signal from otolith (AC motion component)
        for i, key in enumerate(oto_keys):
            temporal_val = abs(state.otolith_acc.get(axes[i], 0.0))
            if temporal_val < 1e-6:
                for tax in state.temporal_measure:
                    temporal_val = max(temporal_val, state.temporal_measure.get(tax, 0.0))
            self._temporal_ema[i] += 0.01 * (temporal_val - self._temporal_ema[i])

        # Step VdP oscillators with entrainment forcing; map to [0,1] envelope
        # VdP limit cycle: raw ∈ ≈ [-2, +2]; (raw+2)/4 maps to [0, 1]
        # Equivalent range to original 0.5 + 0.5*sin(φ) without math hardcoding.
        result = []
        for i, osc in enumerate(self._oscillators):
            i_ext = self.ENTRAINMENT_EPS * self._temporal_ema[i]
            raw = osc.step(dt, i_ext=i_ext)
            envelope = max(0.0, min(1.0, (raw + 2.0) / 4.0))
            result.append(motor_acts[i] * envelope)

        return result

    def summary(self) -> dict:
        return {
            'active': self._active,
            'phases': [round(osc.phase, 3) for osc in self._oscillators],
            'freqs': [self.INTRINSIC_FREQ] * 3,
            'temporal_ema': [round(t, 6) for t in self._temporal_ema],
        }


class DirectionSelector:
    """TYPE:MATH — Placeholder: Action selection / direction decision.

    Future: selects which direction to move (or whether to move at all)
    based on MotionState + reward signals (DA).

    BIO: basal ganglia direct/indirect pathways (Mink 1996).
    Striatum: integrates cortical input + DA → Go/NoGo selection.

    Current: PASSTHROUGH — does not modify motor output.
    """

    def __init__(self):
        self._active = False

    def select(self, motor_acts: List[float],
               state: MotionState, da: float = 0.1) -> List[float]:
        """Select/gate motor activations based on direction decision.

        Args:
            motor_acts: [x, y, z] motor activation totals
            state: current motion state
            da: dopamine level (reward signal)

        Returns:
            Selected motor activations (currently unchanged).
        """
        # PLACEHOLDER: passthrough
        return list(motor_acts)


class SpatialNavigator:
    """TYPE:MATH — Placeholder: Path integration / spatial memory.

    Future: integrates MotionState over time to maintain internal
    position estimate. Provides "where am I" signal.

    BIO: hippocampal place cells + entorhinal grid cells.
    O'Keefe & Nadel 1978: "The Hippocampus as a Cognitive Map."
    Hafting et al. 2005: grid cells in entorhinal cortex.

    Current: PASSTHROUGH — does not track position.
    """

    def __init__(self):
        self._active = False
        self._estimated_position = [0.0, 0.0, 0.0]  # internal estimate

    def update(self, state: MotionState, dt: float = 0.001):
        """Update internal position estimate from motion state.

        Future: dead reckoning via otolith integration.
        Currently does nothing.
        """
        # PLACEHOLDER: no integration yet
        pass

    @property
    def position_estimate(self) -> List[float]:
        return list(self._estimated_position)


class LateralInhibition:
    """TYPE:BIO — Winner-take-all competition within same-axis motor pool.

    Each motor inhibits all other same-axis motors proportionally
    to its own activation. Strongest motor suppresses weakest.

    BIO: Renshaw cells in spinal cord provide recurrent inhibition
    between motor neurons of the same pool (Renshaw 1946).
    This is essential for motor neuron differentiation — without it,
    all clone motors fire identically (N_eff = 1).

    Mechanism:
        For each motor i in axis pool:
            inhibition_i = strength × (sum_others / N)
            output_i = activation_i - inhibition_i
    """

    def __init__(self, inhibition_strength: float = 0.3):
        self._strength = inhibition_strength
        self._active = True

    def compete(self, activations: List[float]) -> List[float]:
        """Apply lateral inhibition within a motor pool.

        Args:
            activations: list of motor activations for ONE axis

        Returns:
            Inhibited activations (same length). Strongest motor
            is least affected, weakest is most suppressed.
        """
        if not self._active or len(activations) <= 1:
            return list(activations)

        total = sum(abs(a) for a in activations)
        if total < 1e-8:
            return list(activations)

        n = len(activations)
        result = []
        for i, a in enumerate(activations):
            # Inhibition from all other motors
            others_sum = total - abs(a)
            inhibition = self._strength * others_sum / n
            # Subtract inhibition, preserving sign
            if a >= 0:
                result.append(max(0.0, a - inhibition))
            else:
                result.append(min(0.0, a + inhibition))
        return result

    def summary(self) -> dict:
        return {'active': self._active, 'strength': self._strength}


class MotorDecisionLayer:
    """TYPE:HYBRID — Middle decision layer between Col and Motor.

    Receives MotionState from vestibular processing chain.
    Contains four sub-systems that modulate motor output.

    Architecture:
        MotionState ──→ MotorRhythm ──→ LateralInhibition ──→ DirectionSelect ──→ Motor
                                    └──→ SpatialNavigator (side channel)
    """

    def __init__(self):
        self.rhythm = MotorRhythmGenerator()
        self.lateral = LateralInhibition()
        self.direction = DirectionSelector()
        self.navigator = SpatialNavigator()

    def process(self, motor_acts: List[float],
                state: MotionState, da: float = 0.1,
                dt: float = 0.001) -> List[float]:
        """Full decision pipeline.

        Args:
            motor_acts: raw [x, y, z] motor activations from Col→Motor STDP
            state: extracted motion state from vestibular chain
            da: dopamine concentration
            dt: time step

        Returns:
            Final motor activations (currently = input, unchanged).
        """
        # 1. Update spatial navigator (side channel, doesn't modify output)
        self.navigator.update(state, dt)

        # 2. Apply rhythmic modulation (CPG: coupled oscillators)
        acts = self.rhythm.modulate(motor_acts, state, dt)

        # 3. Apply direction selection (future: Go/NoGo gating)
        acts = self.direction.select(acts, state, da)

        return acts

    def summary(self) -> dict:
        return {
            'rhythm': self.rhythm.summary(),
            'lateral': self.lateral.summary(),
            'direction_active': self.direction._active,
            'navigator_active': self.navigator._active,
            'nav_position': self.navigator.position_estimate,
        }
