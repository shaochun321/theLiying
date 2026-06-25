"""nexus_v1.components.ecm — Extracellular Matrix.

TYPE:HYBRID — Ion buffer + thermal mass + plasticity gate mapped to both
heat sink / bypass capacitor (electronics) and PNN/CSPG (biology).

===========================================================
ZERO DEPENDENCY ON EXISTING NEXUS CODE.
===========================================================

Electronic Equivalent:
    1. Bypass Capacitor (C_bypass):
       - Absorbs high-frequency voltage transients on power rail
       - Provides local charge reservoir for fast switching
       → ECM ion buffering absorbs ionic transients

    2. Heat Sink (passive thermal mass):
       - Absorbs heat from active components
       - Conducts heat to neighboring elements
       - Raises thermal inertia (slows temperature changes)
       → ECM water content provides thermal buffering

    3. Ground Plane (reference stabilization):
       - Provides stable voltage reference for all circuits
       - Absorbs return currents
       → ECM stabilizes resting potential reference

Biological Equivalent:
    Perineuronal Net (PNN) + extracellular CSPG matrix:

    1. Ion Buffering (Härtig 1999):
       - CSPG/hyaluronan are highly negatively charged
       - They attract and buffer cations: Na⁺, K⁺, Ca²⁺
       - Maintains stable ionic microenvironment
       - Prevents post-spike K⁺ accumulation from depolarizing neighbors

    2. Thermal Mass (indirect):
       - Brain tissue is ~80% water (c_p = 4.18 J/g·K)
       - ECM constitutes ~20% of brain volume
       - Provides passive thermal buffering

    3. Plasticity Gating (Pizzorusso 2002):
       - PNN maturation closes critical period
       - Enzymatic degradation (ChABC) reopens plasticity
       - Dynamic: activity-dependent MMP remodeling

    4. Diffusion Barrier (Syková 2008):
       - ECM tortuosity limits extracellular diffusion
       - Constrains neurotransmitter spillover
       - Shapes signal reach and spatial precision

    REF: Härtig et al. 1999 — "Cortical neurons immunoreactive for the
         potassium channel Kv3.1b subunit are predominantly surrounded
         by perineuronal nets"
    REF: Tewari et al. 2018 — "Perineuronal nets decrease membrane
         capacitance of perineuronal neurons"

Mathematical Model:
    Ion buffer:
        dB/dt = absorption_rate × K_excess - B / τ_buffer
        K_excess = Σ(neuron.heat_output) / R_thermal  (proxy for ionic flux)

    Temperature:
        dT/dt = (Q_in - Q_out) / C_thermal
        Q_in = Σ(neuron.heat_output)  (heat from local neurons)
        Q_out = G_conduction × (T - T_ref) + Q_vascular

    DESIGN NOTE — Normalized Temperature:
        T_ref = 0.0 (not 37°C or any physical temperature).
        All dynamics depend on ΔT = T - T_ref, never on absolute T.
        This system is scale-invariant: the same equations work for
        biological (ΔT ~ 0.5°C) or semiconductor (ΔT ~ 50°C) regimes.
        The actual thermal scale is set by:
          - heat_inputs magnitude (from neuron.heat_output)
          - thermal_capacity (determines thermal inertia)
          - thermal_conductance (determines cooling rate)

    Effective capacitance increase:
        C_eff = C_membrane × (1 + k_ecm × maturity)
        where maturity ∈ [0, 1] represents PNN development
"""

import math
from dataclasses import dataclass, field


@dataclass
class ExtracellularMatrix:
    """Extracellular Matrix: ion buffer + thermal mass + plasticity gate.

    Models the interstitial space between neurons as a dynamic
    medium that buffers ions, absorbs heat, and gates plasticity.

    Args:
        thermal_capacity: heat capacity (J/K equivalent units)
        thermal_conductance: conduction to ambient (W/K equiv)
        ion_buffer_tau: time constant for ion clearance (seconds)
        ion_buffer_capacity: max buffering capacity
        pnn_maturity: PNN development state [0=immature, 1=mature]
        pnn_tau: time constant for PNN maturation
        ambient_temperature: environmental reference temperature
    """
    # Thermal properties
    thermal_capacity: float = 5.0       # thermal inertia (normalized)
    thermal_conductance: float = 0.5    # cooling rate (normalized)
    ambient_temperature: float = 0.0    # reference point (normalized, NOT °C)
    # NOTE: 0.0 is just a reference. ΔT is all that matters.

    # Ion buffer properties
    ion_buffer_tau: float = 0.1         # 100 ms buffer clearance
    ion_buffer_capacity: float = 1.0    # max K⁺ buffering
    ion_absorption_rate: float = 0.8    # how fast ions are absorbed

    # PNN / plasticity gate
    pnn_maturity: float = 0.0           # starts immature
    pnn_tau: float = 100.0              # slow maturation (seconds)
    pnn_target: float = 0.8            # target maturity (< 1.0)

    # Capacitance modulation
    capacitance_boost: float = 0.3      # 30% boost at full PNN maturity
    # REF: Tewari 2018 — PNN decreases membrane capacitance
    # NOTE: in real bio, PNN DECREASES capacitance (increases precision).
    # We model the EFFECTIVE result: better ion buffering → smoother V

    # Internal state
    _temperature: float = field(default=0.0, repr=False)
    _ion_buffer_level: float = field(default=0.0, repr=False)
    _heat_absorbed: float = field(default=0.0, repr=False)
    _t: float = field(default=0.0, repr=False)

    def __post_init__(self):
        self._temperature = self.ambient_temperature

    @property
    def temperature(self) -> float:
        """Current local temperature (°C)."""
        return self._temperature

    @property
    def delta_t(self) -> float:
        """Temperature deviation from ambient."""
        return self._temperature - self.ambient_temperature

    @property
    def ion_buffer(self) -> float:
        """Current ion buffer level (0 = empty, capacity = full)."""
        return self._ion_buffer_level

    @property
    def plasticity_gate(self) -> float:
        """Plasticity gate: 1.0 = fully open (no PNN), 0.0 = closed.

        Inverse of PNN maturity: mature PNN blocks new plasticity.
        """
        return 1.0 - self.pnn_maturity

    def effective_capacitance_factor(self) -> float:
        """Multiplicative factor for membrane capacitance.

        Models how ECM ion buffering effectively increases the
        membrane's ability to resist voltage fluctuations.

        Returns:
            Factor >= 1.0. At full PNN maturity → 1.0 + boost
        """
        return 1.0 + self.capacitance_boost * self.pnn_maturity

    def step(self, heat_inputs: float, dt: float) -> float:
        """Update ECM state for one time step.

        Args:
            heat_inputs: total heat from local neurons (W equiv)
            dt: time step (seconds)

        Returns:
            Temperature after update
        """
        self._t += dt

        # ── 1. Thermal dynamics ──
        # dT/dt = (Q_in - Q_out) / C_thermal
        q_in = heat_inputs
        q_out = self.thermal_conductance * (self._temperature -
                                             self.ambient_temperature)
        dT = (q_in - q_out) / max(self.thermal_capacity, 0.01)
        self._temperature += dT * dt
        self._heat_absorbed += q_in * dt

        # ── 2. Ion buffer dynamics ──
        # Ions flow in proportional to neural activity (proxied by heat)
        # Ions clear at rate 1/tau
        ion_influx = self.ion_absorption_rate * heat_inputs
        ion_clearance = self._ion_buffer_level / max(self.ion_buffer_tau,
                                                      0.001)
        d_buffer = ion_influx - ion_clearance
        self._ion_buffer_level += d_buffer * dt
        self._ion_buffer_level = max(0.0, min(self.ion_buffer_capacity,
                                               self._ion_buffer_level))

        # ── 3. PNN maturation ──
        # Slow approach to target maturity
        d_pnn = (self.pnn_target - self.pnn_maturity) / max(self.pnn_tau,
                                                             0.001)
        self.pnn_maturity += d_pnn * dt
        self.pnn_maturity = max(0.0, min(1.0, self.pnn_maturity))

        return self._temperature

    def degrade_pnn(self, da_concentration: float, dt: float):
        """T2: DA-driven PNN degradation (reopens plasticity).

        Elevated dopamine triggers MMP-9 release → enzymatic
        digestion of PNN components → reduced maturity.

        This creates two opposing forces on PNN:
          Maturation:   pnn → pnn_target  (closing)
          Degradation:  pnn → 0            (opening)

        Equilibrium: pnn_eq = pnn_target × τ_deg / (τ_deg + τ_mat × DA × k)
        At baseline DA (0.1): negligible degradation.
        At elevated DA (0.5): significant reopening.

        Args:
            da_concentration: current DA level (0 to 1)
            dt: time step (seconds)

        BIO: MMP-9 is released by active neurons and degrades CSPG
             in perineuronal nets. DA potentiates MMP-9 in striatum.
             REF: Bhatt et al. 2009 — "Experience-dependent regulation
                  of MMP-9 expression"
        """
        # Degradation rate: proportional to DA above baseline
        DA_BASELINE = 0.1
        K_DEGRADE = 0.02  # degradation rate constant
        # Only degrade when DA is above baseline (novelty/prediction error)
        da_excess = max(0.0, da_concentration - DA_BASELINE)
        d_degrade = K_DEGRADE * da_excess * self.pnn_maturity
        self.pnn_maturity -= d_degrade * dt
        self.pnn_maturity = max(0.0, min(1.0, self.pnn_maturity))

    def temperature_effect_on_tau(self, tau_base: float) -> float:
        """Q10 temperature correction for time constants.

        REF: Hodgkin & Huxley 1952 — Q10 ≈ 3 for ion channels
        At +10°C, rate triples → tau divides by 3.

        Args:
            tau_base: time constant at ambient temperature

        Returns:
            Temperature-corrected time constant
        """
        q10 = 3.0
        delta = self._temperature - self.ambient_temperature
        factor = q10 ** (delta / 10.0)
        return tau_base / max(factor, 0.01)

    def temperature_effect_on_gm(self, gm_base: float) -> float:
        """Q10 temperature correction for conductance.

        Higher temperature → faster gating → higher effective gm.

        Args:
            gm_base: conductance at ambient temperature

        Returns:
            Temperature-corrected conductance
        """
        q10 = 1.5  # weaker Q10 for conductance (channels open wider)
        delta = self._temperature - self.ambient_temperature
        factor = q10 ** (delta / 10.0)
        return gm_base * factor

    def reset(self):
        """Reset to initial state."""
        self._temperature = self.ambient_temperature
        self._ion_buffer_level = 0.0
        self._heat_absorbed = 0.0
        self.pnn_maturity = 0.0
        self._t = 0.0


# ── Presets ──────────────────────────────────────────────────

def create_cortical_ecm() -> ExtracellularMatrix:
    """ECM for cortical regions (dense PNN around PV+ interneurons)."""
    return ExtracellularMatrix(
        thermal_capacity=5.0,
        thermal_conductance=0.5,
        ion_buffer_tau=0.1,
        ion_buffer_capacity=1.0,
        pnn_target=0.8,          # mature PNN
        pnn_tau=100.0,
        capacitance_boost=0.3,
    )


def create_vestibular_ecm() -> ExtracellularMatrix:
    """ECM for vestibular nuclei (moderate PNN, high metabolic rate)."""
    return ExtracellularMatrix(
        thermal_capacity=3.0,    # smaller region
        thermal_conductance=0.8, # better perfusion → more conduction
        ion_buffer_tau=0.05,     # faster clearance (high activity)
        ion_buffer_capacity=2.0, # larger buffer (high firing rates)
        pnn_target=0.5,          # moderate PNN
        pnn_tau=200.0,
        capacitance_boost=0.2,
    )


def create_hippocampal_ecm() -> ExtracellularMatrix:
    """ECM for hippocampus (low PNN, high plasticity)."""
    return ExtracellularMatrix(
        thermal_capacity=4.0,
        thermal_conductance=0.6,
        ion_buffer_tau=0.15,     # slower clearance
        ion_buffer_capacity=0.8,
        pnn_target=0.2,          # low PNN — high plasticity region
        pnn_tau=50.0,
        capacitance_boost=0.1,   # minimal capacitance boost
    )
