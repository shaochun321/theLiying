"""nexus_v1.components.vascular — Vascular Cooling System.

TYPE:HYBRID — Activity-coupled heat removal + energy delivery mapped to
liquid cooling loop (electronics) and neurovascular coupling (biology).

===========================================================
ZERO DEPENDENCY ON EXISTING NEXUS CODE.
===========================================================

Electronic Equivalent:
    Liquid Cooling Loop (data center / IC thermal management):
    1. Coolant pump: base flow rate (always on)
    2. Thermal interface material (TIM): conduction from die to coolant
    3. Dynamic flow control: throttle valve adjusts flow based on load
    4. Power delivery: VRM adjusts voltage/current to chip
    → NVC: base flow + activity-scaled flow + ATP delivery

    Also: Dynamic Voltage & Frequency Scaling (DVFS):
    - High load → boost voltage + frequency → more heat → more cooling
    - Low load → lower voltage → less heat → less cooling
    → Brain: high activity → more blood flow → more heat removal

Biological Equivalent:
    Neurovascular Unit (NVU):

    1. Cerebral Blood Flow (CBF):
       - Base flow: ~750 mL/min total, ~50 mL/100g/min locally
       - Arterial temp: 36.6°C, brain: 37.2°C, venous: 37.0°C
       - Removes ~20W of metabolic heat continuously

    2. Neurovascular Coupling (NVC):
       - Neural activity → astrocyte Ca²⁺ → vasoactive release
       - Active region: blood flow ↑ 20-60% in seconds
       - REF: Attwell et al. 2010 — "Glial and neuronal control of
         brain blood flow"

    3. Metabolic Supply:
       - Blood delivers O₂ + glucose → mitochondrial ATP
       - Astrocyte-Neuron Lactate Shuttle (ANLS)
       - REF: Pellerin & Magistretti 1994

    4. Temperature Shielding:
       - CBF prevents external temperature fluctuations from
         reaching deep brain structures
       - REF: Zhu et al. 2006

Mathematical Model:
    Heat removal:
        Q_remove = flow_rate × c_blood × (T_tissue - T_ref)

    Activity-coupled flow:
        flow_rate = base_flow × (1 + nvc_gain × activity_signal)
        activity_signal is smoothed with τ_nvc (astrocyte Ca²⁺ delay)

    Energy delivery:
        E_deliver = flow_rate × efficiency × dt
        (models O₂ + glucose → ATP conversion)

    DESIGN NOTE — Normalized Temperature:
        T_ref = 0.0 (not 36.6°C or any physical temperature).
        Heat removal = flow × c × ΔT. Only ΔT matters.
        The thermal scale is set by the ECM's heat_inputs and capacitance,
        not by any absolute temperature reference.
"""

import math
from dataclasses import dataclass, field


@dataclass
class VascularCooling:
    """Activity-coupled vascular cooling and energy delivery.

    Models the neurovascular unit (NVU) as a closed-loop cooling
    and energy supply system. Activity increases blood flow, which
    removes heat and delivers ATP precursors.

    Args:
        base_flow: baseline blood flow rate (normalized)
        nvc_gain: neurovascular coupling gain (activity → flow)
        tau_nvc: NVC response delay (seconds, astrocyte Ca²⁺ lag)
        c_blood: blood specific heat capacity (normalized)
        t_artery: arterial reference temperature (°C)
        atp_efficiency: fraction of flow converted to energy delivery
        max_flow: maximum flow rate (autoregulation ceiling)
    """
    # Flow parameters
    base_flow: float = 1.0          # normalized baseline
    nvc_gain: float = 0.5           # 50% flow increase at max activity
    tau_nvc: float = 2.0            # 2s delay (astrocyte Ca²⁺ kinetics)
    max_flow: float = 3.0           # autoregulation ceiling (3× base)

    # Thermal parameters
    c_blood: float = 1.0            # normalized specific heat
    t_artery: float = 0.0           # reference temperature (normalized, NOT °C)
    # NOTE: 0.0 is just T_ref. Heat removal = flow × c × (T - T_ref).

    # Energy delivery
    atp_efficiency: float = 0.1     # energy delivered per unit flow
    # REF: brain metabolic rate ≈ 20W, CBF ≈ 750mL/min
    # efficiency ≈ 20 / 750 ≈ 0.027 W/(mL/min), normalized to 0.1

    # Internal state
    _flow_rate: float = field(default=1.0, repr=False)
    _activity_ema: float = field(default=0.0, repr=False)
    _heat_removed: float = field(default=0.0, repr=False)
    _energy_delivered: float = field(default=0.0, repr=False)
    _t: float = field(default=0.0, repr=False)

    def __post_init__(self):
        self._flow_rate = self.base_flow

    @property
    def flow_rate(self) -> float:
        """Current blood flow rate."""
        return self._flow_rate

    @property
    def activity_signal(self) -> float:
        """Smoothed activity signal (EMA of inputs)."""
        return self._activity_ema

    @property
    def total_heat_removed(self) -> float:
        """Cumulative heat removed."""
        return self._heat_removed

    @property
    def total_energy_delivered(self) -> float:
        """Cumulative energy delivered."""
        return self._energy_delivered

    def step(self, tissue_temperature: float, local_activity: float,
             dt: float) -> dict:
        """Update vascular system for one time step.

        Args:
            tissue_temperature: local tissue temperature (°C)
            local_activity: summed neural activity (normalized)
            dt: time step (seconds)

        Returns:
            dict with:
                heat_removed: W equivalent removed this step
                energy_delivered: energy units delivered this step
                flow_rate: current flow rate
        """
        self._t += dt

        # ── 1. Smooth activity signal (astrocyte Ca²⁺ dynamics) ──
        alpha = min(dt / max(self.tau_nvc, 0.001), 1.0)
        self._activity_ema += alpha * (local_activity - self._activity_ema)

        # ── 2. Flow rate (NVC-modulated) ──
        # flow = base × (1 + gain × activity)
        nvc_boost = self.nvc_gain * self._activity_ema
        self._flow_rate = self.base_flow * (1.0 + nvc_boost)
        self._flow_rate = min(self._flow_rate, self.max_flow)
        self._flow_rate = max(self._flow_rate, 0.0)

        # ── 3. Heat removal (convective) ──
        # Q = flow × c × (T_tissue - T_artery)
        delta_t = tissue_temperature - self.t_artery
        heat_removed = self._flow_rate * self.c_blood * max(delta_t, 0.0)
        self._heat_removed += heat_removed * dt

        # ── 4. Energy delivery ──
        # ATP delivery proportional to flow
        energy = self._flow_rate * self.atp_efficiency * dt
        self._energy_delivered += energy

        return {
            'heat_removed': heat_removed,
            'energy_delivered': energy,
            'flow_rate': self._flow_rate,
        }

    def reset(self):
        """Reset to initial state."""
        self._flow_rate = self.base_flow
        self._activity_ema = 0.0
        self._heat_removed = 0.0
        self._energy_delivered = 0.0
        self._t = 0.0


# ── Presets ──────────────────────────────────────────────────

def create_cortical_vascular() -> VascularCooling:
    """Vascular system for cortical regions."""
    return VascularCooling(
        base_flow=1.0,
        nvc_gain=0.5,           # moderate NVC
        tau_nvc=2.0,            # standard astrocyte delay
        c_blood=1.0,
        atp_efficiency=0.1,
        max_flow=2.5,
    )


def create_brainstem_vascular() -> VascularCooling:
    """Vascular system for brainstem (high tonic activity)."""
    return VascularCooling(
        base_flow=1.5,          # higher baseline (tonic nuclei)
        nvc_gain=0.3,           # weaker NVC (already high flow)
        tau_nvc=1.5,            # slightly faster response
        c_blood=1.0,
        atp_efficiency=0.12,    # efficient supply chain
        max_flow=3.0,
    )


def create_cerebellar_vascular() -> VascularCooling:
    """Vascular system for cerebellum (very high metabolic rate)."""
    return VascularCooling(
        base_flow=2.0,          # highest baseline
        nvc_gain=0.4,
        tau_nvc=1.0,            # fast coupling
        c_blood=1.0,
        atp_efficiency=0.15,    # very efficient
        max_flow=4.0,
    )
