"""nexus_v1.components.digestive_interface — Chemical energy transducer.

TYPE:BIO — Converts raw thermal intake (ThermalMouth output) to ATP stored in EnergyStore.

Biological analogue: mitochondrial ATP synthase. The ThermalMouth extracts heat flux
from the environment (analogous to chemiosomotic proton gradient); the DigestiveInterface
converts that flux into stored chemical energy (ATP ≡ EnergyStore Capacitor charge).

BIO: REF: Mitchell 1961 chemiosmotic theory (Nature 191:144-148)
     REF: Boyer 1997 Nobel Lecture — rotary mechanism of ATP synthesis.
     The g_digest parameter models the ATP yield per unit substrate flux.

PHYS: Transducer with transconductance g_digest [dimensionless].
  I_charge = g_digest × P_raw   [energy units / step]
  where P_raw = thermal_mouth.energy_intake (already scaled by ThermalMouth.eta).
  EnergyStore.deposit() applies deposit_efficiency in addition.

Design: Independent of ThermalMouth internals — only reads energy_intake output.
This enforces physical boundary: ThermalMouth ≡ thermal domain, DigestiveInterface ≡
electrochemical domain. ThermalMouth.step() no longer writes to EnergyStore directly.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DigestiveInterface:
    """TYPE:BIO — ATP synthase analogue: thermal flux → EnergyStore charge.

    Sits between ThermalMouth (thermal domain) and EnergyStore (chemical domain).
    Replaces the direct energy_store.deposit() call inside ThermalMouth.step(),
    making the transduction pathway explicit and auditable.

    PHYS: g_digest = 1.0 [dimensionless] — full pass-through of thermal intake.
    (ThermalMouth.eta already models thermodynamic efficiency; g_digest models
    downstream digestive/metabolic efficiency, set to 1.0 = ideal digestion.)
    """

    # ATP yield per unit raw thermal intake [dimensionless]
    # EXP: g_digest=1.0 reproduces original ThermalMouth.deposit() behavior.
    # BIO: actual mitochondrial efficiency ≈ 0.40 (P/O ratio × thermodynamic ceiling),
    #      but here ThermalMouth.eta=0.02 already accounts for total conversion loss,
    #      so g_digest=1.0 avoids double-penalizing.
    g_digest: float = 1.0

    def tick(self, thermal_mouth, energy_store, dt: float = 0.001) -> float:
        """Transduce raw thermal intake into EnergyStore charge.

        Args:
            thermal_mouth: ThermalMouth instance (reads .energy_intake).
            energy_store: EnergyStore instance (writes via .deposit()).
            dt: timestep (passed through for future current-mode variants).

        Returns:
            Energy actually stored this step (after EnergyStore.deposit() caps).
        """
        raw = thermal_mouth.energy_intake
        if raw <= 0.0:
            return 0.0
        charge = self.g_digest * raw
        return energy_store.deposit(charge)
