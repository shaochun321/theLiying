"""nexus_v1.components.thermal_mouth — Oral thermal energy intake organ.

TYPE:BIO — Analogous to chemosynthetic feeding at hydrothermal vents:
organism absorbs thermal energy through mouth organ when warmer than
internal body temperature.

BIO: REF: thermosynthesis at hydrothermal vents (Muller 1995, PNAS).
     REF: Riftia pachyptila chemolithotrophy (Childress & Fisher 1992).
PHYS: Fourier heat transfer + body cooling pool (blood circulation analog).

Parameters (all require justification):
  conductance=2.0  # NORM: same as SkinPatch.conductance (world.py)
  area=1.0         # NORM: unit area, dimensionally consistent
  eta=0.02         # EXP-W2-002: heat→metabolic conversion efficiency; calibrate
  tau_heat=13      # DERIVED: T_mouth_ss≈4.0 at T_env=5.0, T_body=0.15, tau_cool=50
                   #   T_ss = (T_env/τ_h + T_body/τ_c) / (1/τ_h + 1/τ_c)
                   #        = (5.0/13 + 0.15/50) / (1/13 + 1/50) = 251.95/63 ≈ 4.0 ✓
  tau_cool=50      # DESIGN: slow drainage maintains temperature differential ΔT≈1
"""
import math
from dataclasses import dataclass, field
from typing import List


@dataclass
class ThermalMouth:
    """TYPE:BIO — Oral thermal exchange organ for chemosynthetic energy intake."""

    # Position in body frame (forward-facing tip of mouth)
    local_offset: List[float] = field(default_factory=lambda: [2.0, 0.0, 0.0])
    # 2.0 ≈ effective_radius(1.30) + 0.5 oral protrusion + 0.2 margin

    # Thermal physics parameters
    temperature: float = 0.15    # initial mouth temperature = T_ambient
    conductance: float = 2.0     # k: Fourier conductance (NORM: SkinPatch)
    area: float = 1.0            # A: heat exchange surface area
    eta: float = 0.02            # η: heat→metabolic conversion efficiency
    tau_heat: float = 13.0       # τ_heat: env→mouth time constant (DERIVED)
    tau_cool: float = 50.0       # τ_cool: mouth→body time constant (DESIGN)

    # State
    energy_intake: float = 0.0   # energy deposited this step (for monitoring)

    def world_position(self, body) -> List[float]:
        """Mouth world position, rotated with body yaw.

        Uses same yaw-rotation convention as SkinPatch.world_position().
        """
        cos_y = math.cos(body.yaw)
        sin_y = math.sin(body.yaw)
        lx, ly, lz = self.local_offset
        return [
            body.position[0] + lx * cos_y - ly * sin_y,
            body.position[1] + lx * sin_y + ly * cos_y,
            body.position[2] + lz,
        ]

    def step(self, world, body, ecm_temp: float = 0.15,
             dt: float = 0.001) -> float:
        """Update mouth temperature and compute raw thermal intake.

        PHYS: dT_mouth/dt = (T_env - T_mouth)/tau_heat - (T_mouth - T_body)/tau_cool
        FIX-PHASE1-002: T_body = ecm_temp, dynamically passed from variant_adapter.
          Enables ECM thermal state to suppress feeding (fever→appetite loss).
        FIX-PHASE1-001: deduct total_heat_flux from heat source, not just eta fraction.
          98% waste heat still extracted from vent, maintaining energy conservation.

        NOTE: EnergyStore.deposit() is NO LONGER called here.
        DigestiveInterface.tick() handles the thermal→chemical transduction step.
        ThermalMouth is now a pure thermal-domain component (no electrochemical side effects).

        Returns raw energy_intake (before DigestiveInterface conversion).
        """
        pos = self.world_position(body)
        T_env = world.temperature_at(pos)
        T_body = ecm_temp  # FIX-PHASE1-002: dynamic ECM binding

        # Thermal dynamics (Euler step)
        dT = ((T_env - self.temperature) / self.tau_heat
              - (self.temperature - T_body) / self.tau_cool)
        self.temperature += dT * dt

        # Energy intake: only when environment is warmer than mouth
        delta_T = max(0.0, T_env - self.temperature)
        total_heat_flux = self.conductance * self.area * delta_T * dt
        self.energy_intake = self.eta * total_heat_flux

        if self.energy_intake > 0:
            # FIX-PHASE1-001: absorb total heat flux from heat source.
            # eta controls ATP yield, but all extracted heat comes from source.
            # Noether: heat source loses total_heat_flux, not just eta fraction.
            for src in getattr(world, 'cylindrical_sources', []):
                if src.alive:
                    src.absorb(total_heat_flux)
                    break

        return self.energy_intake
