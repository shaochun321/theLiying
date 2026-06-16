"""nexus_v1.circuit.motor_decision — Middle decision layer (placeholder).

Architecture:

    Vestibular → Met → HC → Aff → Enc → Col
                                         │
                              MotionState extraction
                              (运动势, 时间测度, 空间测度)
                                         │
                              MotorDecisionLayer
                              ┌────────────────────┐
                              │  MotorRhythm (CPG)  │  ← 运动节奏
                              │  DirectionSelect    │  ← 方向选择
                              │  SpatialNavigator   │  ← 空间导航
                              └────────────────────┘
                                         │
                                      Motor → Muscle → Body

Currently: all three sub-layers are PASSTHROUGH (placeholder).
The Col→Motor STDP bundles still drive the motors directly.
These stubs receive MotionState but do not yet modify motor output.

BIO references:
  - MotorRhythm: spinal CPG (Grillner 2006), cerebellum (Ito 1984)
  - DirectionSelect: basal ganglia (Mink 1996), action selection
  - SpatialNavigator: hippocampus (O'Keefe 1978), path integration
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MotionState:
    """Extracted motion state from vestibular processing chain.

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

    # ── 步骤2: VitalOscillator output (宏观传出轨) ──
    # BIO: hemodynamic pulsation → postural sway (Collins & De Luca 1993)
    vital_pulse: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    vital_amplitude: float = 0.0

    # ── B.06: Thermal potential ν_th = dT_skin/dt ──
    # ν_th > 0: skin warming (moving toward heat)
    # ν_th < 0: skin cooling (moving away from heat)
    # BIO: klinokinesis — bacteria-style chemotaxis via temporal comparison.
    # REF: AI编程自足文档 步骤1 B.06
    thermal_potential: float = 0.0      # ν_th = mean dT/dt across patches
    thermal_gradient: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    # dot(∇T, v): positive = moving toward heat source
    thermal_gradient_dot_velocity: float = 0.0


class MotorRhythmGenerator:
    """Central Pattern Generator (CPG) — coupled oscillator model.

    Three phase oscillators (x, y, z), one per motor axis.
    Each generates an intrinsic rhythm that modulates motor output.

    Architecture (per axis i):
      dφ_i/dt = ω_i + Σ_j κ sin(φ_j - φ_i - Δφ_ij)  + ε · temporal_i
                 ↑       ↑                                  ↑
           intrinsic  phase coupling              entrainment by vestibular
           frequency  between axes

    Output: motor_out = motor_in × (0.5 + 0.5 · sin(φ_i))
    When sin(φ)=+1: full power. When sin(φ)=-1: zero.
    This creates rhythmic pulsing instead of constant drive.

    BIO: spinal CPG (Grillner 2006), lamprey swimming circuits.
    Ijspeert 2008: "Central pattern generators for locomotion control
    in animals and robots: A review."

    The CPG is AUTONOMOUS — it generates rhythm even without input.
    But it is ENTRAINED by vestibular temporal_measure (AC component),
    so the rhythm locks onto the body's actual motion pattern.
    """

    # ── Oscillator parameters ──
    INTRINSIC_FREQ: float = 1.0     # Hz (matched to yaw input ~1Hz)
    COUPLING_K: float = 0.5         # phase coupling strength
    ENTRAINMENT_EPS: float = 2.0    # entrainment sensitivity
    # Phase offsets: swim-like pattern (120° between axes)
    PHASE_OFFSETS = [0.0, 2.094, 4.189]  # 0, 2π/3, 4π/3

    def __init__(self):
        self._active = True

        # Phase of each oscillator [x, y, z] — starts offset
        self._phases = [0.0, 2.094, 4.189]  # 120° apart

        # Per-axis intrinsic frequency (can adapt)
        self._freqs = [self.INTRINSIC_FREQ] * 3

        # EMA of temporal input for smooth entrainment
        self._temporal_ema = [0.0, 0.0, 0.0]

    def modulate(self, motor_acts: List[float],
                 state: MotionState, dt: float = 0.001) -> List[float]:
        """Apply CPG rhythmic modulation to motor activations.

        Pipeline:
          1. Update oscillator phases (intrinsic + coupling + entrainment)
          2. Compute rhythmic envelope from phases
          3. Multiply motor activations by envelope

        Args:
            motor_acts: [x, y, z] raw motor activation totals
            state: current motion state (for entrainment)
            dt: time step (seconds)

        Returns:
            Rhythmically modulated motor activations.
        """
        TWO_PI = 2.0 * math.pi
        axes = ['x', 'y', 'z']
        oto_keys = ['oto_x', 'oto_y', 'oto_z']

        # 1. Entrainment signal: use otolith acceleration (most direct motion signal)
        for i, key in enumerate(oto_keys):
            # Try otolith first, fall back to temporal_measure
            temporal_val = abs(state.otolith_acc.get(axes[i], 0.0))
            if temporal_val < 1e-6:
                # Fall back to vestibular temporal measure
                for tax in state.temporal_measure:
                    temporal_val = max(temporal_val, state.temporal_measure.get(tax, 0.0))
            self._temporal_ema[i] += 0.01 * (temporal_val - self._temporal_ema[i])

        # 2. Update phases: dφ/dt = ω + coupling + entrainment
        new_phases = list(self._phases)
        for i in range(3):
            # Intrinsic frequency
            dphi = TWO_PI * self._freqs[i]

            # Phase coupling with neighbors (nearest-neighbor ring)
            for j in range(3):
                if i == j:
                    continue
                # Kuramoto coupling: κ sin(φ_j - φ_i - Δφ_ij)
                target_offset = self.PHASE_OFFSETS[j] - self.PHASE_OFFSETS[i]
                dphi += self.COUPLING_K * math.sin(
                    self._phases[j] - self._phases[i] - target_offset
                )

            # Entrainment: temporal signal pushes phase forward
            # BIO: sensory feedback accelerates the CPG cycle
            dphi += self.ENTRAINMENT_EPS * self._temporal_ema[i]

            new_phases[i] = (self._phases[i] + dphi * dt) % TWO_PI

        self._phases = new_phases

        # 3. Compute rhythmic envelope and modulate
        #    envelope = 0.5 + 0.5 * sin(φ) → range [0, 1]
        #    When sin(φ)=+1 → envelope=1.0 (full power)
        #    When sin(φ)=-1 → envelope=0.0 (rest phase)
        #    BIO: alternating contraction/relaxation in swim cycle
        result = []
        for i in range(3):
            envelope = 0.5 + 0.5 * math.sin(self._phases[i])
            result.append(motor_acts[i] * envelope)

        return result

    def summary(self) -> dict:
        return {
            'active': self._active,
            'phases': [round(p, 3) for p in self._phases],
            'freqs': [round(f, 3) for f in self._freqs],
            'temporal_ema': [round(t, 6) for t in self._temporal_ema],
        }


class DirectionSelector:
    """Placeholder: Action selection / direction decision.

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
    """Placeholder: Path integration / spatial memory.

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
    """Winner-take-all competition within same-axis motor pool.

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
    """Middle decision layer between Col and Motor.

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
