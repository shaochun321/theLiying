"""nexus_v1.vestibular.chain — 5-Layer Vestibular Transduction Chain.

Built entirely from extended MetaNeurons (same semiconductor components
as the Hebbian circuit). Each layer is a group of Neurons with specific
configurations that replicate the biological transduction chain:

  Layer 1: MET (mechanotransduction)
    - Low threshold MOSFET → sensitive to small mechanical deflections
    - Large capacitance → slow integration, rejects fast noise

  Layer 2: HairCell (multi-channel membrane)
    - 3 MOSFETs: MET-current channel + K-channel + Ca-channel
    - K and Ca have different tau_gate → resonance + gain compression
    - Ca current feeds the Ca²⁺ subsystem

  Layer 3: Release (Ca²⁺ → vesicle release)
    - Ca²⁺ Capacitor accumulates inward Ca current (rectified)
    - Release MOSFET acts as sigmoid noise gate
    - PowerRail IR-drop provides self-limiting

  Layer 4: Afferent (spike generation)
    - AdEx model: spike detection + reset + adaptation
    - Regular afferents: small b_adapt → DC encoding (gravity)
    - Irregular afferents: large b_adapt → AC encoding (motion)

  Layer 5: Output statistics
    - firing_rate, regularity, timing_precision
    - These feed into the Hebbian circuit

The chain processes 6 axes: yaw, pitch, roll (canals) + x, y, z (otoliths).
Each axis has its own parallel chain of Neurons.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Dict, List, Tuple

from ..components.neuron import Neuron, NeuronConfig, ChannelConfig
from ..circuit.bundle import SynapticBundle, BundleConfig
from ..circuit.bundle_v2 import DelayedBundle, V_COND_AALPHA            # T-012
from ..components.calcium_channel import CalciumChannel, CalciumDynamics  # T-010


# ─────────────────────────────────────────────────────────────────────
# Axis definitions
# ─────────────────────────────────────────────────────────────────────

CANAL_AXES = ["yaw", "pitch", "roll"]
OTOLITH_AXES = ["oto_x", "oto_y", "oto_z"]
ALL_AXES = CANAL_AXES + OTOLITH_AXES

# ─────────────────────────────────────────────────────────────────────
# Spatial positions (mm, vestibule-centered, +x=anterior +y=lateral +z=superior)
# REF: Goldberg et al. 2012 "The Vestibular System: A Sixth Sense" — Ch.2
# REF: Gray's Anatomy (2020) — inner ear, labyrinthine anatomy
#
# Semicircular canals: radius of curvature ~3 mm; ampullae contain cristae.
# Otolith organs: utricle (horizontal, gravity/translation) + saccule (vertical).
# Scarpa's ganglion: soma of primary afferents, ~2 mm medial to ampullae.
# ─────────────────────────────────────────────────────────────────────

# Ampulla / macula positions (mm): location of MET + HairCell sensory epithelium
_SENSORY_POS: dict = {
    # Semicircular canal ampullae
    'yaw':   ( 1.5,  2.5,  0.0),   # horizontal canal anterior ampulla
    'pitch': ( 2.5,  0.0,  2.0),   # anterior (superior) canal anterior ampulla
    'roll':  ( 0.0,  1.5,  2.5),   # posterior canal posterior ampulla
    # Otolith maculae (utricle + saccule)
    'oto_x': ( 0.5,  0.0, -1.0),   # utricular macula, x-axis hair cell orientation
    'oto_y': ( 0.0,  0.5, -1.0),   # utricular macula, y-axis orientation
    'oto_z': ( 0.0,  0.0, -2.0),   # saccular macula (vertical gravity)
}

def _afferent_pos(axis: str) -> Tuple[float, float, float] | None:
    """Scarpa's ganglion position: ~2 mm medial (−x) from sensory epithelium."""
    base = _SENSORY_POS.get(axis)
    if base is None:
        return None
    return (base[0] - 2.0, base[1], base[2])


# ─────────────────────────────────────────────────────────────────────
# Layer configurations (parameter recipes from the 5-layer chain)
# ─────────────────────────────────────────────────────────────────────

def _met_config(axis: str) -> NeuronConfig:
    """TYPE:BIO — Layer 1: MET neuron — mechanically sensitive.

    REF: Fettiplace & Kim 2014; Eatock & Songer 2011
    BIO: C_m ~ 5 pF, tau_m ~ 5 ms, g_MET ~ 30 nS, tau_MET < 0.1 ms
    NOTE: MET channels are MECHANICALLY gated (not voltage-gated).
    """
    return NeuronConfig(
        neuron_id=f"met_{axis}",
        position=_SENSORY_POS.get(axis),   # BIO: MET channels at ampulla / macula
        capacitance=1.0,         # NORM: 5 pF / 5 pF
        r_leak=5.0,              # NORM: tau_m = 5 ms
        inertia=1.0,
        vdd=1.0,
        r_supply=0.05,
        channels=[
            ChannelConfig(
                name="default",
                v_threshold=0.001,   # BIO: mechanically-gated, NO voltage barrier
                gm=2.0,              # BIO: high sensitivity
                tau_gate=0.0,        # BIO: < 0.1 ms = instantaneous
                reversal=0.615,      # NORM: E_MET = 0 mV
                sign=1.0,
            ),
        ],
        # A. VoltageRegulator (DEG-011: MET energy depletion)
        use_voltage_regulator=True,
        vr_base_rate=0.001,
        vr_activity_coeff=0.3,
        vr_max_rate=3.0,
    )



# ─────────────────────────────────────────────────────────────────────
# N-HC Phase B differentiation parameters
# REF: Goldberg 2000 Annu Rev Physiol 62:121-155; Eatock & Songer 2011
# τ = C × R_leak; R_leak=5.0 fixed; C × factor gives frequency separation.
# HC_0 (Type I-like): fast τ, high-gain — encodes phasic/high-freq stimuli.
# HC_1 (mixed):       τ×2,  normal gain — mid-range encoding.
# HC_2 (Type II-like): τ×4, low-gain — encodes slow/tonic stimuli, saturation-resistant.
# ─────────────────────────────────────────────────────────────────────
_HC_CAP_FACTORS: tuple = (1.0, 2.0, 4.0)   # capacitance multiplier per HC index

# MET→HC synapse_gain per HC index (KCL T-024 audit correction, baseline=5.0)
# HC_0/1: 5.0 (baseline); HC_2: 4.0 (−20%, saturation-resistant)
_HC_MET_GAINS: tuple = (5.0, 5.0, 4.0)

# HC→Aff synapse_gain = 20.0 / N_hair_cells (KCL current conservation)
# Original single-HC synapse_gain=20.0; N=3 → 20.0/3 ≈ 6.67 each
_HC_AFF_GAIN_TOTAL: float = 20.0

# T-010: Vestibular HC Ca²⁺ calibration (external CalciumChannel + CalciumDynamics)
# BIO: Faster PMCA extrusion and more Ca²⁺ buffer proteins in vestibular vs auditory IHCs.
# REF: Holt et al. 1999 J Neurophysiol 82:1756 — vestibular HC Ca²⁺ clearance τ ≈ 10-50 ms
# NORM: Target release≈0.40 at V_m=0.341 (typical active HC), τ=50ms maintained.
# Derivation at V_m=0.341: I_Ca = g_max × m∞ × (E_Ca−V_m) = 2.0×0.750×1.159 = 1.738
#   V_ca_ss = I_Ca × R_ca → R_ca = 0.642 / 1.738 = 0.37 (target V_ca_ss=0.642 for release≈0.40)
#   C_ca = τ / R_ca = 0.050 / 0.37 = 0.135 (τ = R×C = 50 ms, Burrone & Lagnado 2000)
_VEST_CA_R: float = 0.37     # vestibular PMCA clearance resistance
_VEST_CA_C: float = 0.135    # vestibular buffer capacitance; τ = R×C = 50 ms
_VEST_CA_THRESHOLD: float = 0.01  # release dead-band (same as CalciumDynamics default)


def _haircell_config(axis: str) -> NeuronConfig:
    """TYPE:BIO — Layer 2: Hair cell — multi-channel HH equivalent.

    REF: Eatock & Songer 2011; Hodgkin & Huxley 1952; Roberts et al. 1990
    BIO: g_MET~30nS, g_K(BK)~20nS, g_Ca(CaV1.3)~5nS, g_leak~0.5nS
    BIO: tau_MET<0.1ms, tau_Ca=0.5-2ms, tau_K=1-10ms
    BIO: E_MET=0mV, E_K=-80mV, E_Ca=+50mV, E_leak=-60mV
    BIO: Ca decay tau=50-200ms, Ca release 3rd-5th power dependence
    """
    return NeuronConfig(
        neuron_id=f"hc_{axis}",
        position=_SENSORY_POS.get(axis),   # BIO: hair cells co-located with MET in cristae
        capacitance=1.0,             # NORM: 5 pF / 5 pF
        r_leak=5.0,                  # NORM: tau_m = 5 ms
        inertia=1.0,
        vdd=1.0,
        r_supply=0.05,
        v_rest=0.115,                # NORM: V_rest = -65 mV
        channels=[
            # MET current channel (excitatory, fast)
            ChannelConfig(
                name="met",
                v_threshold=0.05,
                gm=1.0,
                tau_gate=0.0,
                reversal=0.615,
                sign=1.0,
            ),
            # K channel (inhibitory, slow)
            ChannelConfig(
                name="k",
                v_threshold=0.385,
                gm=0.67,
                tau_gate=0.005,
                reversal=0.0,
                sign=-1.0,
            ),
            # Ca channel (excitatory, medium)
            ChannelConfig(
                name="ca",
                v_threshold=0.308,
                gm=0.17,
                tau_gate=0.001,
                reversal=1.0,
                sign=1.0,
            ),
        ],
        leak_conductance=0.017,
        leak_reversal=0.154,
        # Ca2+ subsystem — REF: Roberts et al. 1990
        ca_capacitance=0.2,
        # FIX-AVF: ca_r_leak 6→20. Slower Ca clearance → higher Ca_ss.
        # Old: tau_Ca=1.2ms, Ca_ss≈0.06, release≈0.01 (too weak for Aff)
        # New: tau_Ca=4.0ms, Ca_ss≈0.3+, release≈0.06+
        # BIO: active zone Ca clearance 1-5 ms (Bhatt 2005)
        # Governance modeler: aff_I goes from 0.67 to 2.29
        ca_r_leak=20.0,
        ca_release_threshold=0.01,
        # FIX-AVF: ca_release_gm 0.20→0.30 for stronger release coupling.
        # release_max = gm × (Ca_ss - threshold)
        # At Ca_ss=0.3: release = 0.30 × 0.29 = 0.087
        ca_release_gm=0.30,
        # A. VoltageRegulator (DEG-012: HC energy depletion)
        use_voltage_regulator=True,
        vr_base_rate=0.001,
        vr_activity_coeff=0.3,
        vr_max_rate=3.0,
    )


def _haircell_config_n(axis: str, hc_idx: int) -> NeuronConfig:
    """TYPE:BIO — Differentiated HC config for N-HC Phase B expansion.

    HC_0 is identical to the single-HC baseline (backward compatible).
    HC_1/2 share the same channels + Ca²⁺ subsystem but have larger capacitance
    for τ differentiation — implementing Type I / Type II parallel frequency encoding.

    BIO: Type I HCs (small C, fast τ) → high-freq phasic; Type II (large C, slow τ) → DC tonic.
    REF: Goldberg 2000 Annu Rev Physiol 62:121-155; Eatock & Songer 2011.
    """
    base = _haircell_config(axis)
    if hc_idx == 0:
        return base  # HC_0: identical to original (preserves Ca²⁺ calibration)
    c_factor = _HC_CAP_FACTORS[min(hc_idx, len(_HC_CAP_FACTORS) - 1)]
    return dataclasses.replace(
        base,
        neuron_id=f"hc_{axis}_{hc_idx}",
        capacitance=base.capacitance * c_factor,
    )


def _afferent_regular_config(axis: str) -> NeuronConfig:
    """TYPE:BIO — Layer 4: Regular afferent — DC encoding (gravity, tonic).

    REF: Goldberg 2000; Destexhe et al. 1994
    BIO: firing rate 50-100 Hz, CV = 0.05-0.1
    FIX-017: Added tonic discharge (bc_current=0.05) per Goldberg 2000.
      Real vestibular afferents fire at 50-100 Hz even at rest.
      VR rate increased 0.001→0.05 to prevent energy depletion.
    """
    return NeuronConfig(
        neuron_id=f"aff_reg_{axis}",
        position=_afferent_pos(axis),   # BIO: soma at Scarpa's ganglion (~2 mm medial)
        capacitance=0.5,
        r_leak=10.0,
        inertia=0.5,
        vdd=1.0,
        r_supply=0.05,
        spiking=True,
        v_peak=0.23,
        v_reset=0.077,
        b_adapt=0.005,
        tau_w=2.0,
        # A. VoltageRegulator — FIX-017: faster recovery to prevent depletion
        use_voltage_regulator=True,
        vr_base_rate=0.05,            # FIX-017: 0.001→0.05
        vr_activity_coeff=0.3,
        vr_max_rate=3.0,
        # B. Tonic discharge — FIX-017
        # BIO: Regular afferents fire at ~80 Hz at rest (Goldberg 2000)
        use_bias_current=True,
        bc_current=0.05,
    )


def _afferent_irregular_config(axis: str) -> NeuronConfig:
    """TYPE:BIO — Layer 4: Irregular afferent — AC encoding (motion, phasic).

    REF: Goldberg 2000
    FIX-017: Added tonic discharge (bc_current=0.03) and faster VR.
      Irregular afferents have lower baseline (~30-50 Hz) than regular.
    """
    return NeuronConfig(
        neuron_id=f"aff_irr_{axis}",
        position=_afferent_pos(axis),   # BIO: soma at Scarpa's ganglion (~2 mm medial)
        capacitance=0.3,
        r_leak=8.0,
        inertia=0.3,
        vdd=1.0,
        r_supply=0.05,
        spiking=True,
        v_peak=0.23,
        v_reset=0.077,
        b_adapt=0.05,
        tau_w=10.0,
        # A. VoltageRegulator — FIX-017: faster recovery
        use_voltage_regulator=True,
        vr_base_rate=0.05,            # FIX-017: 0.001→0.05
        vr_activity_coeff=0.3,
        vr_max_rate=3.0,
        # B. Tonic discharge — FIX-017
        # BIO: Irregular afferents fire at ~40 Hz at rest (Goldberg 2000)
        # FIX-A2: bc 0.03->0.045. V_ss=0.045*8=0.36 > V_th=0.3
        # Governance: modeler SAFE (activation=0.06), adjudicator APPROVED
        use_bias_current=True,
        bc_current=0.045,
    )


# ─────────────────────────────────────────────────────────────────────
# VestibularChain
# ─────────────────────────────────────────────────────────────────────

class VestibularChain:
    """TYPE:BIO — 5-layer vestibular transduction chain, built from MetaNeurons.

    Architecture per axis (N=1):
        mechanical_input → [MET] → [HairCell] → release → [Afferent_reg]
                                                       → [Afferent_irr]

    Architecture per axis (N=3, Phase B):
        mechanical_input → [MET] ─┬→ [HC_0 fast τ, STDP] ─┐
                                  ├→ [HC_1 mid  τ, frozen]─┼→ KCL add → [Aff_reg]
                                  └→ [HC_2 slow τ, frozen]─┘          → [Aff_irr]

    MET → HairCell via bundle (HC_0 STDP; HC_1/2 frozen)
    HairCell.release_rate → Afferent via bundle (frozen, KCL scaled)

    Two afferents per axis: regular (DC/gravity) + irregular (AC/motion)
    N=1: 6 axes × 4 neurons = 24 neurons, 12 bundles
    N=3: 6 axes × (1 MET + 3 HC + 2 Aff) = 36 neurons, 36 bundles
    """

    def __init__(self, axes: List[str] | None = None, n_hair_cells: int = 1,
                 dt: float = 0.001):
        if axes is None:
            axes = ALL_AXES
        self.axes = axes
        self.n_hair_cells = n_hair_cells
        self._dt = dt   # T-012: stored for DelayedBundle conduction delay computation

        # Create neurons per axis
        self.met_neurons: Dict[str, Neuron] = {}
        self.afferent_regular: Dict[str, Neuron] = {}
        self.afferent_irregular: Dict[str, Neuron] = {}

        # HC_0 (primary, backward-compatible access)
        self.haircell_neurons: Dict[str, Neuron] = {}
        self.bundles_met_to_hc: Dict[str, SynapticBundle] = {}
        self.bundles_hc_to_aff: Dict[str, SynapticBundle] = {}

        # Full lists for N≥1 (includes HC_0 as index 0)
        self.haircell_neurons_all: Dict[str, List[Neuron]] = {}
        self.bundles_met_to_hc_all: Dict[str, List[SynapticBundle]] = {}
        self.bundles_hc_to_aff_all: Dict[str, List[SynapticBundle]] = {}

        # T-010: per-HC external Ca²⁺ objects (CalciumChannel + CalciumDynamics)
        # Indexed as calcium_channels_all[axis][hc_idx]
        self.calcium_channels_all: Dict[str, List[CalciumChannel]] = {}
        self.calcium_dynamics_all: Dict[str, List[CalciumDynamics]] = {}

        # KCL: total HC→Aff gain is fixed; each HC contributes 1/N share
        hc_aff_gain = round(_HC_AFF_GAIN_TOTAL / n_hair_cells, 4)

        for axis in axes:
            met = Neuron(_met_config(axis))
            aff_r = Neuron(_afferent_regular_config(axis))
            aff_i = Neuron(_afferent_irregular_config(axis))

            self.met_neurons[axis] = met
            self.afferent_regular[axis] = aff_r
            self.afferent_irregular[axis] = aff_i

            hc_list: List[Neuron] = []
            met_hc_list: List[SynapticBundle] = []
            hc_aff_list: List[SynapticBundle] = []
            ca_ch_list: List[CalciumChannel] = []    # T-010
            ca_dyn_list: List[CalciumDynamics] = []  # T-010

            for hc_idx in range(n_hair_cells):
                hc = Neuron(_haircell_config_n(axis, hc_idx))
                hc_list.append(hc)

                # T-010: per-HC external Ca²⁺ objects with vestibular calibration
                # CalciumChannel: Boltzmann gate replaces internal MOSFET Ca²⁺
                # CalciumDynamics: RC integrator with vestibular-specific clearance
                # REF: Bao et al. 2003; Holt et al. 1999; Burrone & Lagnado 2000
                ca_ch = CalciumChannel()          # uses class defaults (V_half=0.308, g_max=2.0)
                ca_dyn = CalciumDynamics()
                ca_dyn.R_ca = _VEST_CA_R          # vestibular-calibrated clearance
                ca_dyn.C_ca = _VEST_CA_C          # τ = R×C = 50 ms
                ca_ch_list.append(ca_ch)
                ca_dyn_list.append(ca_dyn)

                # Bundle: MET → HairCell_i
                # HC_0: STDP (preserves original learning dynamics)
                # HC_1/2: frozen (fixed frequency-domain filters)
                met_gain = _HC_MET_GAINS[min(hc_idx, len(_HC_MET_GAINS) - 1)]
                b_id = (f"met_to_hc_{axis}" if n_hair_cells == 1
                        else f"met_to_hc_{axis}_{hc_idx}")
                b_met_hc = SynapticBundle(
                    config=BundleConfig(
                        bundle_id=b_id,
                        learning_rule="stdp" if hc_idx == 0 else "frozen",
                        initial_weight=0.5,
                        stdp_lr=0.005,
                        # HC_0/1: gain=5.0 (baseline); HC_2: 4.0 (saturation-resistant)
                        # BIO: Type II HCs have lower gain per Goldberg 2000
                        # T-024 audit: corrected from plan baseline 1.0 → actual 5.0
                        synapse_gain=met_gain,
                    ),
                    sources=[met],
                    targets=[hc],
                )
                met_hc_list.append(b_met_hc)

                # T-012: DelayedBundle for HC→Aff (Aα myelinated vestibular fiber)
                # BIO: Scarpa's ganglion primary afferents — Aα fiber, v=50 mm/ms
                # REF: Goldberg et al. 2012 "The Vestibular System" Ch.2
                # NORM: d≈2mm HC-to-ganglion → τ_steps=round(2/50/1)=0 (no delay at current scale)
                # KCL: each HC contributes 1/N of total Aff drive; 3×6.67=20.0 preserved
                # REF: Bao et al. 2003 — ribbon synapse = structurally stable (frozen)
                b_aff_id = (f"hc_to_aff_{axis}" if n_hair_cells == 1
                            else f"hc_to_aff_{axis}_{hc_idx}")
                b_hc_aff = DelayedBundle(
                    config=BundleConfig(
                        bundle_id=b_aff_id,
                        learning_rule="frozen",
                        initial_weight=0.8,
                        weight_max=0.95,
                        synapse_gain=hc_aff_gain,
                    ),
                    sources=[hc],
                    targets=[aff_r, aff_i],
                    v_cond_mm_per_ms=V_COND_AALPHA,
                    dt=dt,
                )
                hc_aff_list.append(b_hc_aff)

            # Backward-compatible single references (HC_0)
            self.haircell_neurons[axis] = hc_list[0]
            self.bundles_met_to_hc[axis] = met_hc_list[0]
            self.bundles_hc_to_aff[axis] = hc_aff_list[0]

            # Full N-HC lists
            self.haircell_neurons_all[axis] = hc_list
            self.bundles_met_to_hc_all[axis] = met_hc_list
            self.bundles_hc_to_aff_all[axis] = hc_aff_list

            # T-010: per-HC Ca²⁺ objects
            self.calcium_channels_all[axis] = ca_ch_list
            self.calcium_dynamics_all[axis] = ca_dyn_list

    def step(self, mechanical_inputs: Dict[str, float], dt: float = 1.0):
        """Process one time step.

        Args:
            mechanical_inputs: per-axis mechanical deflection values.
                Keys: axis names (e.g. "yaw", "pitch", "oto_x")
                Values: local strain / radial velocity (float)
            dt: time step
        """
        import math as _math
        for axis in self.axes:
            deflection = mechanical_inputs.get(axis, 0.0)

            # Layer 1: MET
            met = self.met_neurons[axis]
            met.step(deflection, dt)

            # Layer 2–3: All HCs receive MET output through their individual bundles.
            # Each HC has its own RC time constant (τ = C × R_leak) for frequency separation.
            aff_r = self.afferent_regular[axis]
            aff_i = self.afferent_irregular[axis]
            total_aff_r = 0.0
            total_aff_i = 0.0

            hc_list = self.haircell_neurons_all[axis]
            met_hc_list = self.bundles_met_to_hc_all[axis]
            hc_aff_list = self.bundles_hc_to_aff_all[axis]

            ca_ch_list = self.calcium_channels_all[axis]
            ca_dyn_list = self.calcium_dynamics_all[axis]

            for _hc_idx, (hc, b_met_hc, b_hc_aff) in enumerate(
                    zip(hc_list, met_hc_list, hc_aff_list)):
                currents = b_met_hc.propagate()
                _pt_before = hc.pre_trace
                hc.step(currents[0] if currents else 0.0, dt)

                # Layer 3: T-010 Ca²⁺ Phase B — explicit CalciumChannel + CalciumDynamics
                # Replaces internal release_rate bridge (HC-008 code bridge).
                # BIO: CaV1.3 Ca²⁺ drives vesicle exocytosis at IHC ribbon synapse.
                # REF: Fuchs 2005 J Physiology 567(1):13-19; Nouvian et al. 2006
                # REF: Bao et al. 2003 J Neurophysiol 90:1195 — CaV1.3 Boltzmann gate
                # Clamp V_m to physiological range before Boltzmann gate.
                # When dt=1.0 (regression sim-step convention), HC voltage can
                # swing far below rest; below V_m≈-20 the exp() overflows.
                # Physiologically: Ca channel is CLOSED (g≈0) for V_m << V_half=0.308.
                _vm_safe = max(-0.5, min(hc._membrane.voltage, 2.0))
                _I_Ca = ca_ch_list[_hc_idx].current(_vm_safe)
                # Use stored physical dt (self._dt=0.001s), NOT the simulation-step dt.
                # CalciumDynamics τ=50ms requires dt << τ for Euler stability.
                # Regression tests pass dt=1.0 (sim-steps), not seconds.
                ca_dyn_list[_hc_idx].step(_I_Ca, self._dt)
                _ext_release = ca_dyn_list[_hc_idx].release_rate(_VEST_CA_THRESHOLD)
                hc.activation = _ext_release        # T-011: Ca²⁺ pre_trace now non-zero
                hc.release_rate = _ext_release      # sync get_output() release_rate field
                _decay = _math.exp(-dt / max(hc.config.trace_tau_pre * 0.001, 0.001))
                hc.pre_trace = min(_pt_before * _decay + abs(_ext_release), 10.0)

                # Layer 4: Accumulate Aff currents from all N HCs (KCL addition)
                aff_currents = b_hc_aff.propagate()
                if len(aff_currents) >= 2:
                    total_aff_r += aff_currents[0]
                    total_aff_i += aff_currents[1]
                elif len(aff_currents) == 1:
                    total_aff_r += aff_currents[0]
                    total_aff_i += aff_currents[0]

            # Step Afferents once with the summed KCL current
            aff_r.step(total_aff_r, dt)
            aff_i.step(total_aff_i, dt)

        # Learning (all bundles across all HCs)
        for axis in self.axes:
            for b in self.bundles_met_to_hc_all[axis]:
                b.learn(dt)
            for b in self.bundles_hc_to_aff_all[axis]:
                b.learn(dt)

    def get_output(self) -> Dict[str, Dict[str, float]]:
        """Get per-axis output from afferent neurons.

        Returns dict of axis → {
            "rate_regular": firing rate of regular afferent,
            "rate_irregular": firing rate of irregular afferent,
            "regularity": ISI regularity of regular afferent,
            "release_rate": Ca²⁺ release rate from HC_0 (primary hair cell),
            "hc_voltages": list of membrane voltages for all N HCs,
        }
        """
        output = {}
        for axis in self.axes:
            aff_r = self.afferent_regular[axis]
            aff_i = self.afferent_irregular[axis]
            hc0 = self.haircell_neurons[axis]  # HC_0 (primary)

            output[axis] = {
                "rate_regular": aff_r.firing_rate(),
                "rate_irregular": aff_i.firing_rate(),
                "regularity": aff_r.regularity(),
                "release_rate": hc0.release_rate,
                "met_activation": self.met_neurons[axis].activation,
                "hc_voltage": hc0._membrane.voltage,
                "hc_voltages": [hc._membrane.voltage
                                for hc in self.haircell_neurons_all[axis]],
            }
        return output

    def get_all_neurons(self) -> List[Neuron]:
        """Get all neurons in the chain (for circuit integration)."""
        neurons = []
        for axis in self.axes:
            neurons.append(self.met_neurons[axis])
            neurons.extend(self.haircell_neurons_all[axis])   # all N HCs
            neurons.append(self.afferent_regular[axis])
            neurons.append(self.afferent_irregular[axis])
        return neurons

    def get_all_bundles(self) -> List[SynapticBundle]:
        """Get all bundles (for circuit integration)."""
        bundles = []
        for axis in self.axes:
            bundles.extend(self.bundles_met_to_hc_all[axis])  # all N MET→HC
            bundles.extend(self.bundles_hc_to_aff_all[axis])  # all N HC→Aff
        return bundles

    def summary(self) -> dict:
        output = self.get_output()
        return {
            "axes": self.axes,
            "n_neurons": len(self.get_all_neurons()),
            "n_bundles": len(self.get_all_bundles()),
            "per_axis": output,
        }
