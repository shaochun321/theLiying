"""nexus_v1.components.muscle — Motor neuron → physical force.

Simple muscle groups that convert motor neuron activation to forces
acting on the Body. Three groups for xyz movement.

Structure:
  - Each muscle has a force buffer (FIFO) for conduction delay
  - Force is proportional to motor activation
  - Contraction costs energy (from future Gut, currently free)
  - Volume: 1 unit per muscle group

BIO: simplified skeletal muscle — no sarcomere dynamics,
     just activation → force with delay.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import List


@dataclass
class Muscle:
    """Single muscle group converting neural activation to force.

    Output force follows motor activation with a conduction delay.
    """

    muscle_id: str = ""
    gain: float = 0.1              # activation → force conversion
    max_force: float = 1.0         # maximum force output
    delay_steps: int = 2           # neuromuscular conduction delay
    energy_cost_per_force: float = 0.01  # energy consumed per unit force

    # Internal FIFO buffer for delay
    _buffer: deque = field(default_factory=lambda: deque())
    _total_energy_spent: float = 0.0

    def contract(self, motor_activation: float) -> float:
        """Convert motor activation to delayed force output.

        Args:
            motor_activation: Motor neuron activation (can be negative).

        Returns:
            Delayed force value.
        """
        # Raw force (signed: positive activation = positive force)
        raw_force = motor_activation * self.gain
        # Clamp
        raw_force = max(-self.max_force, min(self.max_force, raw_force))

        # Energy cost (proportional to |force|)
        cost = abs(raw_force) * self.energy_cost_per_force
        self._total_energy_spent += cost

        # Delay buffer
        self._buffer.append(raw_force)
        if len(self._buffer) > self.delay_steps:
            return self._buffer.popleft()
        return 0.0

    def reset(self):
        """Reset buffer and energy counter."""
        self._buffer.clear()
        self._total_energy_spent = 0.0


class MuscleSystem:
    """Three muscle groups for 3D movement (xyz).

    Connects motor neurons (move_x, move_y, move_z) to Body forces.
    """

    def __init__(self, gain: float = 0.1, delay: int = 2):
        self.muscles: List[Muscle] = [
            Muscle(muscle_id="muscle_x", gain=gain, delay_steps=delay),
            Muscle(muscle_id="muscle_y", gain=gain, delay_steps=delay),
            Muscle(muscle_id="muscle_z", gain=gain, delay_steps=delay),
        ]

    def contract_all(self, motor_activations: List[float]) -> List[float]:
        """Convert 3 motor activations to 3 forces.

        Args:
            motor_activations: [act_x, act_y, act_z] from motor neurons.

        Returns:
            [force_x, force_y, force_z] for Body.step().
        """
        forces = []
        for i, muscle in enumerate(self.muscles):
            act = motor_activations[i] if i < len(motor_activations) else 0.0
            forces.append(muscle.contract(act))
        return forces

    def total_energy_spent(self) -> float:
        return sum(m._total_energy_spent for m in self.muscles)
