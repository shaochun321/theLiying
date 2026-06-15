"""nexus_v1.components.energy_store — External energy reservoir.

Bridges the gap between feeding (external acquisition) and metabolism
(internal consumption). All energy entering the organism flows through
this store; all internal energy consumption draws from it.

Design principles:
  - EXTERNAL to the neural circuit (can be swapped without rewiring)
  - Finite capacity (organism can't store infinite energy)
  - Noether-compatible: total_deposited = total_withdrawn + current_level
  - Two interfaces: deposit() from World, withdraw() to Vascular/neurons

Energy flow:
  World.consume_nearby() → EnergyStore.deposit()
                                ↓
  EnergyStore.withdraw() → Vascular → neuron.energy
                                ↓
                          neuron.step() → heat_output
                                ↓
                          Noether accounting

BIO: glycogen stores in liver/muscle + blood glucose buffer.
  - Liver glycogen ≈ 100g (≈400 kcal) — primary reserve
  - Muscle glycogen ≈ 400g (≈1600 kcal) — local reserve
  - Blood glucose ≈ 4g (≈16 kcal) — transit buffer
  This component models the aggregate reserve, not individual pools.

PHYS: Capacitor with max charge (Q_max). Deposit = charge, withdraw = discharge.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EnergyStoreConfig:
    """Configuration for the energy reservoir."""
    # Capacity: maximum stored energy
    # Must survive learning period (~50k steps) without feeding.
    # DA neurons draw ~0.01/step, vascular ~0.001/step, basal ~0.0001/step.
    # Budget: 50k × 0.012 ≈ 600. Capacity 1000, start at 50% = 500.
    capacity: float = 1000.0

    # Initial fill level (fraction of capacity)
    initial_fill: float = 0.5

    # Passive drain rate: basal metabolic cost per step
    # BIO: basal metabolic rate ≈ 80W (resting human)
    # Scaled to be small relative to capacity.
    basal_drain: float = 0.0001

    # Maximum energy deposited per step (fixed power supply)
    # BIO: blood-brain barrier limits glucose delivery rate.
    # PHYS: constant current source — universe's power budget.
    # P2.1: This + constant per-bundle drain = thermodynamic ceiling.
    max_deposit_per_step: float = 0.05

    # Efficiency of deposit (not all consumed energy is stored)
    # BIO: digestive efficiency ≈ 85-95%
    deposit_efficiency: float = 0.9

    # Starvation threshold: below this, vascular delivery degrades
    # BIO: hypoglycemia impairs brain function
    starvation_threshold: float = 0.1


class EnergyStore:
    """External energy reservoir — the organism's 'battery'.

    Sits between World (food acquisition) and internal metabolism.
    Can be replaced/upgraded without changing internal wiring.

    Usage:
        store = EnergyStore()
        store.deposit(energy_from_feeding)     # after consume_nearby
        available = store.withdraw(requested)  # for vascular/neurons
        store.tick(dt)                         # basal metabolism drain
    """

    def __init__(self, config: EnergyStoreConfig | None = None):
        if config is None:
            config = EnergyStoreConfig()
        self.config = config

        # Current energy level
        self._level: float = config.capacity * config.initial_fill
        # Noether tracking
        self._total_deposited: float = 0.0
        self._total_withdrawn: float = 0.0
        self._total_basal_drain: float = 0.0

    @property
    def level(self) -> float:
        """Current energy stored."""
        return self._level

    @property
    def fill_fraction(self) -> float:
        """Fill level as fraction [0, 1]."""
        return self._level / max(self.config.capacity, 1e-8)

    @property
    def is_starving(self) -> bool:
        """Below starvation threshold?"""
        return self.fill_fraction < self.config.starvation_threshold

    def deposit(self, amount: float) -> float:
        """Store energy from external source (feeding).

        Args:
            amount: raw energy absorbed from heat source.

        Returns:
            Actual amount stored (after efficiency loss, capped at capacity).
        """
        if amount <= 0:
            return 0.0
        effective = amount * self.config.deposit_efficiency
        space = self.config.capacity - self._level
        # P2.1: Fixed power supply cap (constant current source).
        # The universe can only deliver this much per step.
        cap = self.config.max_deposit_per_step
        stored = min(effective, space, cap)
        self._level += stored
        self._total_deposited += stored
        return stored

    def withdraw(self, requested: float) -> float:
        """Draw energy for internal use (vascular delivery, neuron refill).

        Args:
            requested: amount of energy needed.

        Returns:
            Actual amount delivered (may be less if store is low).
        """
        if requested <= 0:
            return 0.0
        delivered = min(requested, self._level)
        self._level -= delivered
        self._total_withdrawn += delivered
        return delivered

    def tick(self, dt: float = 0.001):
        """Basal metabolic drain — organism costs energy just to exist.

        Called once per step. Drains a small fixed amount.
        BIO: resting metabolic rate consumes glucose continuously.
        """
        drain = self.config.basal_drain * dt
        actual = min(drain, self._level)
        self._level -= actual
        self._total_basal_drain += actual

    def delivery_factor(self) -> float:
        """Scaling factor for vascular energy delivery.

        When store is full: factor = 1.0 (full delivery).
        When store is low:  factor < 1.0 (reduced delivery).
        When starving:      factor → 0.0 (no delivery).

        BIO: hypoglycemia reduces cerebral metabolic rate.
        """
        frac = self.fill_fraction
        if frac >= 0.3:
            return 1.0
        # Gradual degradation below 30%
        return max(0.0, frac / 0.3)

    def summary(self) -> dict:
        """State for monitoring and Noether audit."""
        return {
            "level": round(self._level, 4),
            "capacity": self.config.capacity,
            "fill_fraction": round(self.fill_fraction, 4),
            "is_starving": self.is_starving,
            "total_deposited": round(self._total_deposited, 4),
            "total_withdrawn": round(self._total_withdrawn, 4),
            "total_basal_drain": round(self._total_basal_drain, 4),
            # Noether check: deposited = withdrawn + basal + current - initial
            "noether_balance": round(
                self._total_deposited
                - self._total_withdrawn
                - self._total_basal_drain
                - self._level
                + self.config.capacity * self.config.initial_fill,
                6),
        }
