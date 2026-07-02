"""nexus_v1.components.yolk_sac — Embryonic energy bootstrap reserve.

TYPE:BIO
Yolk sac (vitellus): non-replenishable maternal energy reserve.
Discharges at constant rate into EnergyStore until depleted.
Physical primitive: Capacitor (fixed charge Q_yolk, one-way discharge).

BIO: Yolk sac in vertebrate embryogenesis — sole energy source before
external feeding is established. Fixed maternal endowment, not refillable.
REF: Davidson EH (2006) The Regulatory Genome, Ch.3.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class YolkSacConfig:
    """TYPE:BIO — Configuration for embryonic energy reserve (yolk sac)."""
    # Phase4: expanded from 200→500 to extend STDP learning window from 100k→500k steps
    initial_level: float = 500.0
    # Phase4: halved from 0.002→0.001/step to slow release and create mild hunger gradient.
    # 500 / 0.001 = 500k step depletion. fill slowly declines during yolk phase → Hunger signal active.
    # Units: energy/step (NOT per-second — do NOT multiply by dt).
    lambda_yolk: float = 0.001


class YolkSac:
    """TYPE:BIO — Non-replenishable embryonic energy reserve (Capacitor analogue).

    Discharges at constant rate lambda_yolk per step into EnergyStore.
    Once depleted, transfer stops. Cannot be refilled.

    Depletion timeline: initial_level / lambda_yolk = 500 / 0.001 = 500k steps.

    BIO: Vitellus provides the only available energy source during neural
    circuit bootstrapping, before the organism can acquire food by behavior.
    REF: Davidson 2006, The Regulatory Genome, Ch.3.
    """

    def __init__(self, config: YolkSacConfig | None = None):
        self.config = config or YolkSacConfig()
        self._level: float = self.config.initial_level
        self._depleted: bool = False
        self._total_transferred: float = 0.0

    def step(self, energy_store, dt: float = 0.001) -> float:
        """Transfer lambda_yolk to EnergyStore. Returns amount transferred.

        NOTE: dt is accepted for API compatibility but NOT used in the
        calculation. lambda_yolk has units of energy/step, not energy/second.
        """
        if self._depleted:
            return 0.0
        transfer = self.config.lambda_yolk  # per-step, do NOT multiply by dt
        if self._level <= transfer:
            transfer = self._level
            self._depleted = True
        self._level -= transfer
        self._total_transferred += transfer
        energy_store.deposit(transfer)
        return transfer

    @property
    def level(self) -> float:
        return self._level

    @property
    def is_depleted(self) -> bool:
        return self._depleted

    @property
    def fraction_remaining(self) -> float:
        if self.config.initial_level <= 0:
            return 0.0
        return self._level / self.config.initial_level
