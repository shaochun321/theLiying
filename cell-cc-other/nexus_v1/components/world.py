"""nexus_v1.components.world — 3D World with consumable heat sources.

Provides the environment for the thermophilic organism:
  - SkinPatch: body-surface patch that samples local temperature
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
            # Random drift direction.
            # FIX-DRIFT-SPEED: speed 0.01 → 0.001.
            # At 0.01/step, octant-placed sources scatter 20 units in 2000
            # steps, destroying the ~85% spatial coverage before learning
            # can establish thermotaxis. Empirically this dropped zone-time
            # to ~40%, causing metabolic collapse at ~10k steps.
            # At 0.001/step:
            #   drift@2k = 2 units  → octant structure intact
            #   drift@20k = 20 units → minor disruption
            #   drift@500k = 500 units = 5 toroidal wraps → uniform
            # BIO: deep-sea hydrothermal vent migration on geological
            #      timescales corresponds to extremely slow positional drift.
            import random
            speed = 0.001
            self._drift = [random.gauss(0, speed) for _ in range(3)]

    @property
    def alive(self) -> bool:
        return self.energy > 0.01

    def effective_temperature(self) -> float:
        """Temperature scales with remaining energy."""
        if self.energy <= 0:
            return 0.0
        # T drops as energy depletes: T_eff = T_base × min(1, E/E_half)
        # FIX-METABOLIC-WALL: E_HALF 10→100 so a source with E=500 stays at
        # full temperature throughout the learning period (~10k steps).
        # Old E_HALF=10 caused T_eff to drop dramatically below E=10,
        # collapsing P_in BEFORE the source was technically 'dead' (E>0.01).
        E_HALF = 100.0
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
class SkinPatch:
    """Body-surface thermal integrator patch.

    NOT an ideal thermometer — this is a physical thermal mass that
    integrates heat flux over time via Newton's cooling law (Fourier):

        q_dot = conductance × (T_env - T_skin)
        dT_skin = q_dot / heat_capacity × dt

    A fast pass through a heat source barely raises T_skin (thermal
    inertia), while sustained exposure accumulates tissue damage.

    Heading = velocity direction (if moving) or [1,0,0] (at rest).
    Rotation uses Rodrigues' formula in the horizontal plane.

    BIO: skin receptive field with finite thermal mass.
    Physics: Newton's cooling + Arrhenius damage integral.
    """

    patch_id: str                     # "front", "back", "left", "right"
    local_offset: List[float] = field(default_factory=lambda: [1.0, 0.0, 0.0])

    # ── Thermal physics parameters ──
    heat_capacity: float = 10.0       # C_th: thermal mass (J/K analog)
    conductance: float = 2.0          # k: thermal conductance (W/K analog)
    # BIO: skin thermal time constant τ = C/k = 10/2 = 5 steps
    # This means the patch needs ~5 steps to equilibrate with environment.

    # ── State variables (physical, not semantic) ──
    current_temperature: float = field(default=0.1, repr=False)  # T_skin
    _prev_temperature: float = field(default=0.1, repr=False)    # for dT/dt
    damage_integral: float = field(default=0.0, repr=False)      # tissue damage
    damage_threshold: float = 3.0     # T_skin above this → tissue denaturation
    # BIO: 43°C in real units; normalized to 3.0 in our thermal range.
    # Damage accumulates only when skin temperature exceeds this.
    damage_heal_rate: float = 0.1     # slow self-repair rate

    def world_position(self, body: 'Body') -> List[float]:
        """Compute patch world position from body state.

        Rotates local_offset into heading frame, then translates
        by body.position. Heading from velocity (or default [1,0,0]).
        """
        # Heading direction from velocity
        spd = math.sqrt(sum(v * v for v in body.velocity) + 1e-12)
        if spd > 0.01:
            hx = body.velocity[0] / spd
            hy = body.velocity[1] / spd
            hz = body.velocity[2] / spd
        else:
            hx, hy, hz = 1.0, 0.0, 0.0  # default heading

        # Rotation: align [1,0,0] with heading via Rodrigues'
        lx, ly, lz = self.local_offset

        # Body frame: x=forward, y=left, z=up
        # Perpendicular to heading in horizontal plane
        perp_mag = math.sqrt(hx * hx + hy * hy + 1e-12)
        if perp_mag > 0.01:
            # Left perpendicular: rotate heading 90° CCW in xy-plane
            px = -hy / perp_mag
            py = hx / perp_mag
        else:
            px, py = 0.0, 1.0

        # Rotated world offset
        wx = lx * hx + ly * px
        wy = lx * hy + ly * py
        wz = lz + hz * lx  # vertical: body tilt effect

        return [
            body.position[0] + wx,
            body.position[1] + wy,
            body.position[2] + wz,
        ]

    def step_thermal(self, world: 'World', body: 'Body', dt: float = 1.0):
        """Integrate thermal dynamics for this patch.

        Fourier heat conduction (Newton's cooling law):
            q_dot = k × (T_env - T_skin)
            dT_skin = q_dot / C × dt

        Tissue damage integral:
            If T_skin > threshold: damage += (T_skin - threshold) × dt
            Else: damage -= heal_rate × dt (slow self-repair)

        Returns (T_skin, dT_skin) for downstream neuron input.
        """
        self._prev_temperature = self.current_temperature

        # Get environment temperature at patch world position
        pos = self.world_position(body)
        T_env = world.temperature_at(pos)

        # Fourier conduction: heat flows from hot to cold
        q_dot = self.conductance * (T_env - self.current_temperature)
        # Thermal capacity integration: dT = q/C × dt
        self.current_temperature += (q_dot / max(self.heat_capacity, 0.01)) * dt

        # Tissue damage integral (Arrhenius-type accumulation)
        if self.current_temperature > self.damage_threshold:
            excess = self.current_temperature - self.damage_threshold
            self.damage_integral += excess * dt
        else:
            # Slow self-repair when below threshold
            self.damage_integral = max(
                0.0, self.damage_integral - self.damage_heal_rate * dt)

        return self.current_temperature, self.dT

    # Legacy compatibility: sample() calls step_thermal()
    def sample(self, world: 'World', body: 'Body', dt: float = 1.0):
        """Sample temperature at this patch (with thermal dynamics).

        Returns (T_skin, dT_skin).
        """
        return self.step_thermal(world, body, dt)

    @property
    def temperature(self) -> float:
        return self.current_temperature

    @property
    def dT(self) -> float:
        """Temperature rate of change (discrete derivative)."""
        return self.current_temperature - self._prev_temperature


def _default_skin_patches(effective_radius: float = 2.0) -> List[SkinPatch]:
    """Create 4 default skin patches: front, back, left, right.

    Placed at body effective radius in the body frame.
    Body frame: x=forward, y=left, z=up.
    """
    r = effective_radius
    return [
        SkinPatch(patch_id="front", local_offset=[r, 0.0, 0.0]),
        SkinPatch(patch_id="back",  local_offset=[-r, 0.0, 0.0]),
        SkinPatch(patch_id="left",  local_offset=[0.0, r, 0.0]),
        SkinPatch(patch_id="right", local_offset=[0.0, -r, 0.0]),
    ]


@dataclass
class Body:
    """Physical body of the organism in 3D space.

    Simple Newtonian mechanics with viscous drag (fluid medium).
    """

    # FIX-METABOLIC-WALL: Start at dist=12 from src[4] (pos=[75,25,25], r=20).
    # T_local at d=12: 5.0*(1-12/20)=2.0 < damage_threshold=3.0 -> no burn.
    # Energy intake: (1-d/r)=40% of max -> 0.02/step -> sufficient to bootstrap.
    # dist=5 (T=3.75) caused burn damage -> massive repair withdraw -> P_out>>P_in.
    # BIO: neonate begins near nutrient source but not at its hottest core.
    position: List[float] = field(default_factory=lambda: [63.0, 25.0, 25.0])
    velocity: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    acceleration: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    mass: float = 1.0
    friction: float = 0.5          # viscous drag coefficient (water)
    total_volume: int = 9          # sum of all organ volumes
    # A4: tissue stiffness (elastic modulus analogy)
    # BIO: soft tissue k ~ 1-10 kPa. Normalized to 1.0.
    stiffness: float = 1.0
    # B.01: skin patches (body-surface temperature sensors)
    skin_patches: List[SkinPatch] = field(default=None, repr=False)

    def __post_init__(self):
        if self.skin_patches is None:
            self.skin_patches = _default_skin_patches(self.effective_radius)

    @property
    def effective_radius(self) -> float:
        """Body effective radius from volume (sphere model).

        V = (4/3)πr³ → r = (3V/4π)^(1/3)
        """
        return (3.0 * self.total_volume / (4.0 * math.pi)) ** (1.0 / 3.0)

    def sample_skin(self, world: 'World', dt: float = 1.0) -> dict:
        """Step thermal dynamics and sample all skin patches.

        Each patch integrates heat flux via Fourier conduction,
        producing physically delayed temperature responses.

        Returns dict: patch_id → (T_skin, dT_skin, damage_integral)
        """
        result = {}
        for patch in self.skin_patches:
            T, dT = patch.sample(world, self, dt)
            result[patch.patch_id] = (T, dT, patch.damage_integral)
        return result

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
    MAX_SOURCES = 12         # raised: 8 initial + headroom for regen
    REGEN_PROB = 0.001       # probability per step of spawning a new source
    MIN_ALIVE = 4            # always maintain at least 4 active sources

    def __init__(self, heat_sources: List[HeatSource] | None = None,
                 body: Body | None = None):
        if heat_sources is None:
            # C3': multiple heat sources at varied positions
            # Models scattered hydrothermal vents in deep-sea floor
            # FIX-METABOLIC-WALL: 8 uniformly distributed sources (octant
            # centers of the world cube) give ~27% spatial coverage vs the
            # previous 3-source ~10%. Random drift is 2.7× less likely to
            # strand the organism outside all feeding zones during the
            # thermotaxis learning period.
            # Each source: energy=500, E_HALF=100 → sustains ~10k steps.
            # BIO: dense hydrothermal vent field (EPR, mid-ocean ridge).
            #
            # FIX-METABOLIC-COVERAGE: radius 20 → 30.
            # Coverage = 8 × (4/3)π×30³ / 100³ ≈ 90.5% (was 26.8%).
            # At 90% coverage a ~0.09-unit/step random walk almost always
            # stays within some source's thermal field, ensuring P_in > P_out
            # and preventing starvation from dry-zone stranding.
            # BIO: EPR hydrothermal vent plumes extend 10-100 m laterally;
            #      radius=30 models the warm-water halo, not just the vent.
            heat_sources = [
                HeatSource(position=[25.0, 25.0, 25.0], energy=500.0,
                           temperature=5.0, radius=30.0),
                HeatSource(position=[25.0, 25.0, 75.0], energy=500.0,
                           temperature=4.5, radius=30.0),
                HeatSource(position=[25.0, 75.0, 25.0], energy=500.0,
                           temperature=4.0, radius=30.0),
                HeatSource(position=[25.0, 75.0, 75.0], energy=450.0,
                           temperature=3.5, radius=30.0),
                HeatSource(position=[75.0, 25.0, 25.0], energy=500.0,
                           temperature=5.0, radius=30.0),
                HeatSource(position=[75.0, 25.0, 75.0], energy=450.0,
                           temperature=4.0, radius=30.0),
                HeatSource(position=[75.0, 75.0, 25.0], energy=400.0,
                           temperature=3.5, radius=30.0),
                HeatSource(position=[75.0, 75.0, 75.0], energy=350.0,
                           temperature=3.0, radius=30.0),
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
        """Consume energy from nearby heat sources. Returns energy absorbed.

        PHYS: rate = T_local (from temperature_at), which already encodes
        distance falloff via (1 - d/r). The absorption power is:
            P = rate × dt
        The only physical constraint is source energy depletion.

        Each source contributes proportionally to its fraction of T_local.
        This ensures Noether: absorbed energy is subtracted from the source
        that provided it, proportionally.
        """
        total_absorbed = 0.0
        # Calculate each source's contribution to T_local
        contributions = []
        for src in self.heat_sources:
            if not src.alive:
                contributions.append(0.0)
                continue
            d = _distance(pos, src.position)
            if d < src.radius:
                contributions.append(
                    src.effective_temperature() * (1.0 - d / src.radius))
            else:
                contributions.append(0.0)

        total_T = sum(contributions)
        if total_T < 1e-12:
            return 0.0

        # Total absorption = rate × dt (rate IS T_local, already distance-weighted)
        total_want = rate * dt

        # Distribute across sources proportionally and enforce depletion
        for i, src in enumerate(self.heat_sources):
            if contributions[i] < 1e-12:
                continue
            frac = contributions[i] / total_T
            want_from_src = total_want * frac
            actual = min(want_from_src, src.energy)
            src.energy -= actual
            total_absorbed += actual

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
        # FIX-METABOLIC-WALL: energy 200-600 (was 20-60) to match E_HALF=100
        # scaling. Spawned sources must also sustain feeding over learning timescales.
        # FIX-METABOLIC-COVERAGE: radius 20-35 (was 12-25) to match initial
        # sources and maintain ~90% spatial coverage as sources regenerate.
        energy = random.uniform(200.0, 600.0)
        temp = random.uniform(2.5, 6.0)
        radius = random.uniform(20.0, 35.0)
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


def _distance(a: List[float], b: List[float],
              size: float = 100.0) -> float:
    """Toroidal (periodic) 3D distance.

    The world wraps at [0, size] in all three dimensions.
    Both the body (Body.step) and heat sources (HeatSource.step) use
    toroidal wrapping, so distances must also be computed toroidally.

    FIX-TOROIDAL-DISTANCE: the previous implementation used plain
    Euclidean distance, causing temperature_at() and consume_nearby()
    to return zero for a body that is close to a source *across* a
    wrap boundary (e.g. body at [99,25,25], source at [1,25,25]:
    Euclidean d=98, toroidal d=2). This silently eliminated ~40-50% of
    all valid feeding events, causing metabolic collapse.

    Physics: Periodic/Born-von Kármán boundary conditions. The minimum
    image convention gives the shortest path between two points on a
    torus. This is equivalent to how atoms interact in molecular
    dynamics simulation cells.

    BIO: The organism lives in open water — no walls, space wraps.
    All distances (thermal, feeding, spatial) must respect the torus.
    """
    total = 0.0
    for i in range(3):
        delta = abs(a[i] - b[i])
        # Minimum image convention: choose shorter of direct or wrap path
        if delta > size * 0.5:
            delta = size - delta
        total += delta * delta
    return math.sqrt(total)
