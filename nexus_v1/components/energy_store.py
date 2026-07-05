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
  Capacitor parameters derived from metabolic budget:
    C = capacity = 1000.0  [F equiv, charge = energy unit]
    R_leak: τ = R×C; basal_drain = Q×dt/τ at Q=Q_init
      → R = Q_init × dt / (basal_drain × C)
      → R = (500 × 0.001) / (0.0001 × 1000) = 5.0 [Ω equiv]
  REF: Bergman 1989 Am J Physiol (hepatic glycogen kinetics)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class EnergyStoreConfig:
    """TYPE:SEMI — Configuration for the energy reservoir."""
    # Capacity: maximum stored energy
    # Must survive learning period (~50k steps) without feeding.
    # DA neurons draw ~0.01/step, vascular ~0.001/step, basal ~0.0001/step.
    # Budget: 50k × 0.012 ≈ 600. Capacity 1000, start at 50% = 500.
    capacity: float = 1000.0

    # Initial fill level (fraction of capacity)
    # DESIGN NOTE: 0.5 is deliberately chosen, not 0.7.
    # With init_fill=0.7, the organism has enough energy to accumulate DA≈0.12
    # before the AGC cold-start ramp (step 2k-4k). When AGC jumps to 5.0,
    # DA overshoots to 1.0 (saturated) → motor runaway → P_out≈0.335/step >>
    # P_in_max≈0.047/step → catastrophic 8k-step starvation spiral.
    # With init_fill=0.5, the crash happens at step 2k-4k before DA accumulates
    # (DA≈0.13 only), so recovery with max_deposit=0.08 is smooth and fast.
    initial_fill: float = 0.5

    # Passive drain rate: basal metabolic cost per step
    # BIO: basal metabolic rate ≈ 80W (resting human)
    # Scaled to be small relative to capacity.
    basal_drain: float = 0.0001

    # Maximum energy deposited per step (fixed power supply)
    # BIO: blood-brain barrier limits glucose delivery rate.
    # PHYS: constant current source — universe's power budget.
    # P2.1: This + constant per-bundle drain = thermodynamic ceiling.
    #
    # FIX-DEPOSIT-RATE: 0.05 → 0.08 → 0.12.
    # EXP-023 run1 (0.05): P_net=-6.9e-4/step → fill 0.50→0.155 over 500k.
    # EXP-023 run2 (0.08): P_out_max≈0.108/step during neural full-load,
    #   exceeding 0.08 cap → feast-famine oscillations → fill=0 at step 350k.
    #   Root: delivery_factor=1.0 at full fill → all neurons fire at max →
    #   aggregate draw = 0.108 > 0.08 → structural deficit → collapse.
    # At 0.12: P_in_max(0.12) > P_out_max(0.108) → positive margin even at
    #   full neural load. Fill should stabilize without hitting zero.
    # BIO: r=30 thermal field → larger skin contact area → higher heat flux.
    # PHYS: Stefan-Boltzmann P ∝ A·T⁴; larger A (radius) → higher P_absorb.
    max_deposit_per_step: float = 0.12

    # Efficiency of deposit (not all consumed energy is stored)
    # BIO: digestive efficiency ≈ 85-95%
    deposit_efficiency: float = 0.9

    # Starvation threshold: below this, vascular delivery degrades
    # BIO: hypoglycemia impairs brain function
    starvation_threshold: float = 0.1

    # Capacitor leak resistance [Ω equiv]
    # PHYS: derived from basal_drain at Q_init=capacity×initial_fill
    #   dQ/step(linear) = basal_drain × dt = 0.0001 × 0.001 = 1e-7
    #   dQ/step(RC)     = Q × dt / (R × C)
    #   → R = Q_init × dt / (dQ_target × C)
    #   → R = 500 × 0.001 / (1e-7 × 1000) = 5000 [Ω equiv]
    # BIO: hepatic glucose output rate ≈ 10 μmol/kg/min at rest (Bergman 1989)
    r_leak: float = 5000.0


class EnergyStore:
    """TYPE:SEMI — External energy reservoir — the organism's 'battery'.

    Sits between World (food acquisition) and internal metabolism.
    Can be replaced/upgraded without changing internal wiring.

    Physical basis: Capacitor (semiconductor.py) stores charge Q = energy.
    V = Q/C = fill_fraction; deposit/withdraw map to inject/drain.
    External API (fill_fraction, deposit, withdraw, tick) unchanged.

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

        # Physical storage: Capacitor primitive
        # charge [Q] ≡ energy_level; voltage [V] = Q/C = fill_fraction
        # C = capacity (so that V_max = Q_max/C = 1.0 = full)
        from nexus_v1.components.semiconductor import Capacitor
        self._cap = Capacitor()
        self._cap.capacitance = config.capacity
        self._cap.charge = config.capacity * config.initial_fill

        # Noether tracking — preserved from original for audit compatibility
        self._total_deposited: float = 0.0
        self._total_withdrawn: float = 0.0
        self._total_basal_drain: float = 0.0

    @property
    def level(self) -> float:
        """Current energy stored (= capacitor charge Q)."""
        return self._cap.charge

    @property
    def fill_fraction(self) -> float:
        """Fill level as fraction [0, 1] (= capacitor voltage V = Q/C)."""
        return self._cap.voltage

    @property
    def is_starving(self) -> bool:
        """Below starvation threshold?"""
        return self.fill_fraction < self.config.starvation_threshold

    def deposit(self, amount: float) -> float:
        """Store energy from external source (feeding).

        PHYS: inject charge into capacitor (dQ = amount after efficiency & cap).
        Maps to Capacitor.inject(current=stored, dt=1.0) with dt=1 so dQ=stored.

        Args:
            amount: raw energy absorbed from heat source.

        Returns:
            Actual amount stored (after efficiency loss, capped at capacity).
        """
        if amount <= 0:
            return 0.0
        effective = amount * self.config.deposit_efficiency
        space = self.config.capacity - self._cap.charge
        cap = self.config.max_deposit_per_step
        stored = min(effective, space, cap)
        if stored > 0:
            # PHYS: inject charge; dt=1 so dQ = current × 1 = stored
            self._cap.inject(stored, dt=1.0)
            self._total_deposited += stored
        return stored

    def withdraw(self, requested: float) -> float:
        """Draw energy for internal use (vascular delivery, neuron refill).

        PHYS: extract charge from capacitor (negative inject).

        Args:
            requested: amount of energy needed.

        Returns:
            Actual amount delivered (may be less if store is low).
        """
        if requested <= 0:
            return 0.0
        delivered = min(requested, self._cap.charge)
        if delivered > 0:
            self._cap.inject(-delivered, dt=1.0)
            self._total_withdrawn += delivered
        return delivered

    def tick(self, dt: float = 0.001):
        """Basal metabolic drain — organism costs energy just to exist.

        PHYS: RC leak of capacitor (exponential decay with τ = R_leak × C).
        BIO: resting metabolic rate consumes glucose continuously.
        """
        q_before = self._cap.charge
        self._cap.leak(self.config.r_leak, dt)
        drained = q_before - self._cap.charge
        self._total_basal_drain += drained

        # P0-3: Mandatory basal metabolic rate — thermodynamic second law.
        # BIO: ATP synthase idling + Na+/K+ pump maintenance; unavoidable in any dissipative structure.
        # Q3: BMR=0.002/step (DT-independent, same convention as YolkSac λ=0.001/step).
        #     Net cold-zone: YolkSac(+0.001) - RC_leak(~0.0001) - BMR(-0.002) ≈ -0.0011/step → hunger.
        # REF: 最终架构裁决 P0-3, 2026-07-05; PHYS: 热力学第二定律
        BMR = 0.002
        bmr_drain = min(BMR, self._cap.charge)
        if bmr_drain > 0:
            self._cap.inject(-bmr_drain, 1.0)
            self._total_basal_drain += bmr_drain

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
        return max(0.0, frac / 0.3)

    def summary(self) -> dict:
        """State for monitoring and Noether audit."""
        return {
            "level": round(self._cap.charge, 4),
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
                - self._cap.charge
                + self.config.capacity * self.config.initial_fill,
                6),
            # KCL imbalance on Capacitor itself (semiconductor-level audit)
            "cap_kcl_imbalance": round(self._cap.kcl_imbalance, 8),
        }
