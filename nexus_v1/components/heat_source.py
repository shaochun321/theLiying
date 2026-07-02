"""nexus_v1.components.heat_source — Cylindrical heat source with Gaussian field.

TYPE:BIO — Analogous to hydrothermal vent: physical volume, finite energy,
Gaussian thermal diffusion from cylindrical surface.

BIO: REF: hydrothermal vent thermal plume (Kelley et al. 2002, Science 301).
"""
import math
from dataclasses import dataclass, field
from typing import List


def _dist_to_cylinder_surface(pos: List[float], center: List[float],
                               radius: float, half_height: float) -> float:
    """Shortest distance from pos to cylinder surface. Returns 0 if inside."""
    dx = pos[0] - center[0]
    dy = pos[1] - center[1]
    dz = pos[2] - center[2]
    radial = math.sqrt(dx * dx + dy * dy)
    within_height = abs(dz) <= half_height

    if within_height:
        return max(0.0, radial - radius)
    else:
        dz_to_rim = abs(dz) - half_height
        if radial <= radius:
            return dz_to_rim
        else:
            return math.sqrt((radial - radius) ** 2 + dz_to_rim ** 2)


@dataclass
class CylindricalHeatSource:
    """TYPE:BIO — Cylindrical heat source with Gaussian thermal field.

    BIO: Hydrothermal vent: physical volume + surface thermal diffusion.
    SEMI: Thermal energy reservoir with slow regeneration.

    Temperature field: T(r) = T_ambient + (T_surface - T_ambient) * exp(-d²/2σ²)
    where d = shortest distance to cylinder surface (0 inside).
    """

    center: List[float]           # [x, y, z] cylinder axis midpoint
    radius: float = 6.0           # cylinder radius (collision + thermal)
    height: float = 16.0          # total height (±half_height from center)
    T_surface: float = 5.0        # base surface temperature at full energy
    T_ambient: float = 0.15       # far-field ambient temperature
    sigma: float = 25.0           # Gaussian diffusion length (units)
    energy: float = 1000.0        # remaining thermal energy
    energy_initial: float = field(default=None, repr=False)
    regeneration_rate: float = 0.002  # energy replenishment per step

    def __post_init__(self):
        if self.energy_initial is None:
            self.energy_initial = self.energy

    @property
    def alive(self) -> bool:
        return self.energy > 0.01

    @property
    def effective_T_surface(self) -> float:
        """Surface temperature scales with remaining energy fraction."""
        if self.energy <= 0:
            return self.T_ambient
        frac = min(1.0, self.energy / self.energy_initial)
        return self.T_ambient + (self.T_surface - self.T_ambient) * frac

    def temperature_at(self, pos: List[float]) -> float:
        """Gaussian temperature field from cylinder surface."""
        if not self.alive:
            return self.T_ambient
        d = _dist_to_cylinder_surface(
            pos, self.center, self.radius, self.height / 2.0)
        return self.T_ambient + (self.effective_T_surface - self.T_ambient) * math.exp(
            -d * d / (2.0 * self.sigma * self.sigma)
        )

    def absorb(self, amount: float) -> float:
        """Deduct absorbed energy from reservoir. Returns actual deducted."""
        actual = min(amount, self.energy)
        self.energy -= actual
        return actual

    def step(self, dt: float = 1.0):
        """Slow regeneration: vent recharges from geothermal heat."""
        if self.energy < self.energy_initial:
            self.energy = min(self.energy_initial,
                              self.energy + self.regeneration_rate * dt)
