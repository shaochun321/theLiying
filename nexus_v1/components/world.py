"""nexus_v1.components.world — 3D World with consumable heat sources.

Provides the environment for the thermophilic organism:
  - HeatSource: consumable energy objects at fixed positions
  - Body: physical body with position, velocity, mass, friction
  - World: 3D space containing heat sources and the body

Heat source ecology (C3'):
  Sources deplete as the organism feeds. Depleted sources are replaced
  at random positions (deep-sea hydrothermal vent model). This forces
  the organism to continuously explore, testing homeostatic coupling.

Physics: F = ma - μv (Newtonian + viscous drag in fluid medium)
Thermal: T(pos) = Σ src.temperature × max(0, 1 - d/r) + ambient
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class HeatSource:
    """A consumable thermal energy source in 3D space.
    
    S.13: Sources drift slowly, simulating vent migration on the sea floor.
    """

    position: List[float]          # [x, y, z]
    energy: float = 50.0           # remaining energy (consumed by nearby organism)
    temperature: float = 5.0       # surface temperature (decreases as energy depletes)
    radius: float = 20.0           # thermal influence radius
    # S.13: drift velocity (random direction, slow)
    _drift: List[float] = field(default=None, repr=False)

    def __post_init__(self):
        if self._drift is None:
            # Random drift direction, speed ~0.01 per step
            import random
            speed = 0.01
            self._drift = [random.gauss(0, speed) for _ in range(3)]

    @property
    def alive(self) -> bool:
        return self.energy > 0.01

    def effective_temperature(self) -> float:
        """Temperature scales with remaining energy."""
        if self.energy <= 0:
            return 0.0
        # T drops as energy depletes: T_eff = T_base × min(1, E/E_half)
        E_HALF = 10.0  # half-life energy
        return self.temperature * min(1.0, self.energy / E_HALF)

    def step(self, dt: float = 1.0):
        """S.13: Drift position. Wrap at world boundaries [0, 100]."""
        for i in range(3):
            self.position[i] += self._drift[i] * dt
            if self.position[i] < 0:
                self.position[i] += 100.0
            elif self.position[i] > 100.0:
                self.position[i] -= 100.0


@dataclass
class Body:
    """Physical body of the organism in 3D space.

    Simple Newtonian mechanics with viscous drag (fluid medium).
    """

    position: List[float] = field(default_factory=lambda: [50.0, 50.0, 50.0])
    velocity: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    acceleration: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    mass: float = 1.0
    friction: float = 0.5          # viscous drag coefficient (water)
    total_volume: int = 9          # sum of all organ volumes
    # A4: tissue stiffness (elastic modulus analogy)
    # BIO: soft tissue k ~ 1-10 kPa. Normalized to 1.0.
    stiffness: float = 1.0

    @property
    def impedance(self) -> float:
        """Mechanical impedance Z = sqrt(k * m).

        A4 (§1E.3): determines signal transmission efficiency.
        Higher mass/stiffness → better mechanical impedance matching.
        """
        return math.sqrt(self.stiffness * self.mass)

    def step(self, forces: List[float], dt: float):
        """Update velocity and position.

        F_net = F_muscle - μ·v
        a = F_net / m

        Acceleration is recorded for vestibular sensing.
        """
        for i in range(3):
            a = (forces[i] - self.friction * self.velocity[i]) / self.mass
            self.acceleration[i] = a    # record for vestibular sensing
            self.velocity[i] += a * dt
            self.position[i] += self.velocity[i] * dt

        # Boundary: toroidal wrap (periodic, no energy loss)
        # BIO: organism in open water — no walls, space wraps.
        # Prevents corner-stall observed in 2M experiment.
        for i in range(3):
            if self.position[i] < 0:
                self.position[i] += 100.0
            elif self.position[i] > 100.0:
                self.position[i] -= 100.0

    def speed(self) -> float:
        return math.sqrt(sum(v * v for v in self.velocity))

    def kinetic_damping(self) -> float:
        """A4: Speed-dependent damping factor for muscle output.

        Faster movement → harder to accelerate further (viscous regime).
        Returns factor in (0, 1]: 1.0 at rest, decreasing with speed.

        BIO: Golgi tendon organ feedback + viscous drag.
        Physics: effective gain = gain / (1 + speed/v_ref)
        """
        V_REF = 0.5  # reference speed (normalized)
        return 1.0 / (1.0 + self.speed() / V_REF)

    def mass_inertia_factor(self) -> float:
        """A4: Mass-dependent factor for learning rate modulation.

        Heavier body → slower neural adaptation (more observations needed
        to learn from each movement, because movements are smaller).

        Returns factor in (0, 1]: 1.0 at mass=1, decreasing with mass.
        BIO: larger organisms have slower motor learning rates.
        """
        return 1.0 / math.sqrt(max(self.mass, 0.01))

    def thermal_mass_factor(self) -> float:
        """A4: Volume-dependent thermal capacity scaling.

        Larger body → more thermal inertia → slower temperature changes.
        Returns multiplier for ECM thermal_capacity.

        BIO: larger organisms buffer temperature better (surface/volume ratio).
        Physics: C_thermal ~ volume × c_p × ρ
        """
        return max(0.1, self.total_volume / 9.0)  # normalized to default=9


class World:
    """3D environment with heat sources and a body.

    Temperature field: superposition of all heat sources.
    Gradient: finite-difference approximation.
    """

    # C3': heat source ecology parameters
    MAX_SOURCES = 5          # max simultaneous sources
    REGEN_PROB = 0.001       # probability per step of spawning a new source
    MIN_ALIVE = 2            # always maintain at least this many active sources

    def __init__(self, heat_sources: List[HeatSource] | None = None,
                 body: Body | None = None):
        if heat_sources is None:
            # C3': multiple heat sources at varied positions
            # Models scattered hydrothermal vents in deep-sea floor
            heat_sources = [
                HeatSource(position=[70.0, 50.0, 50.0], energy=50.0,
                           temperature=5.0, radius=20.0),
                HeatSource(position=[30.0, 70.0, 40.0], energy=35.0,
                           temperature=3.5, radius=15.0),
                HeatSource(position=[80.0, 20.0, 60.0], energy=25.0,
                           temperature=4.0, radius=18.0),
            ]
        if body is None:
            body = Body()

        self.heat_sources = heat_sources
        self.body = body
        self.ambient_temp: float = 0.1
        self.size: Tuple[float, float, float] = (100.0, 100.0, 100.0)
        # C3': tracking
        self._total_consumed: float = 0.0
        self._sources_depleted: int = 0
        self._sources_spawned: int = 0

    def temperature_at(self, pos: List[float]) -> float:
        """Calculate temperature at a point (superposition of all sources)."""
        T = self.ambient_temp
        for src in self.heat_sources:
            if not src.alive:
                continue
            d = _distance(pos, src.position)
            if d < src.radius:
                # Linear falloff: T_src × (1 - d/r)
                T += src.effective_temperature() * (1.0 - d / src.radius)
        return T

    def gradient_at(self, pos: List[float], eps: float = 0.5) -> List[float]:
        """Temperature gradient at pos (finite difference).

        Returns [∂T/∂x, ∂T/∂y, ∂T/∂z].
        """
        grad = [0.0, 0.0, 0.0]
        for i in range(3):
            pos_plus = list(pos)
            pos_minus = list(pos)
            pos_plus[i] += eps
            pos_minus[i] -= eps
            grad[i] = (self.temperature_at(pos_plus)
                        - self.temperature_at(pos_minus)) / (2 * eps)
        return grad

    def consume_nearby(self, pos: List[float], rate: float, dt: float) -> float:
        """Consume energy from nearby heat sources. Returns energy absorbed."""
        total_absorbed = 0.0
        for src in self.heat_sources:
            if not src.alive:
                continue
            d = _distance(pos, src.position)
            if d < src.radius:
                proximity = 1.0 - d / src.radius
                amount = rate * proximity * dt
                amount = min(amount, src.energy)
                src.energy -= amount
                total_absorbed += amount
        self._total_consumed += total_absorbed
        return total_absorbed

    def get_nearest_heat_source(self, pos: List[float]) -> Optional[HeatSource]:
        """Return the nearest alive heat source, or None."""
        best = None
        best_d = float('inf')
        for src in self.heat_sources:
            if not src.alive:
                continue
            d = _distance(pos, src.position)
            if d < best_d:
                best_d = d
                best = src
        return best

    def regenerate_sources(self):
        """C3': Heat source ecology — spawn new sources, remove dead ones.

        Deep-sea model: hydrothermal vents have finite lifetimes.
        When a vent dies, new ones emerge at random positions.
        Ensures the organism always has sources to seek.

        S.13: Alive sources drift each step.
        Called once per step from the main loop.
        """
        # S.13: Drift alive sources
        for s in self.heat_sources:
            if s.alive:
                s.step()

        # Count alive sources
        alive = [s for s in self.heat_sources if s.alive]
        dead = [s for s in self.heat_sources if not s.alive]

        # Remove dead sources
        for d in dead:
            self.heat_sources.remove(d)
            self._sources_depleted += 1

        # Ensure minimum alive count
        while len(self.heat_sources) < self.MIN_ALIVE:
            self._spawn_source()

        # Random chance of new source (if below max)
        if (len(self.heat_sources) < self.MAX_SOURCES
                and random.random() < self.REGEN_PROB):
            self._spawn_source()

    def _spawn_source(self):
        """Create a new heat source at a random position."""
        pos = [
            random.uniform(10.0, 90.0),
            random.uniform(10.0, 90.0),
            random.uniform(10.0, 90.0),
        ]
        # Vary energy and temperature (natural diversity)
        energy = random.uniform(20.0, 60.0)
        temp = random.uniform(2.5, 6.0)
        radius = random.uniform(12.0, 25.0)
        src = HeatSource(position=pos, energy=energy,
                         temperature=temp, radius=radius)
        self.heat_sources.append(src)
        self._sources_spawned += 1

    def ecology_summary(self) -> dict:
        """Summary of heat source ecology for monitoring."""
        alive = sum(1 for s in self.heat_sources if s.alive)
        total_energy = sum(s.energy for s in self.heat_sources)
        return {
            "alive_sources": alive,
            "total_energy": round(total_energy, 2),
            "total_consumed": round(self._total_consumed, 2),
            "sources_depleted": self._sources_depleted,
            "sources_spawned": self._sources_spawned,
        }


def _distance(a: List[float], b: List[float]) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))
