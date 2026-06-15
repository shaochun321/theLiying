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

from dataclasses import dataclass
from typing import Dict, List, Tuple

from ..components.neuron import Neuron, NeuronConfig, ChannelConfig
from ..circuit.bundle import SynapticBundle, BundleConfig


# ─────────────────────────────────────────────────────────────────────
# Axis definitions
# ─────────────────────────────────────────────────────────────────────

CANAL_AXES = ["yaw", "pitch", "roll"]
OTOLITH_AXES = ["oto_x", "oto_y", "oto_z"]
ALL_AXES = CANAL_AXES + OTOLITH_AXES


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
    """5-layer vestibular transduction chain, built from MetaNeurons.

    Architecture per axis:
        mechanical_input → [MET] → [HairCell] → release → [Afferent_reg]
                                                       → [Afferent_irr]

    MET → HairCell via bundle (STDP-capable)
    HairCell.release_rate → Afferent via bundle (STDP-capable)

    Two afferents per axis: regular (DC/gravity) + irregular (AC/motion)
    Total neurons: 6 axes × 4 neurons = 24
    Total bundles: 6 axes × 2 bundles = 12
    """

    def __init__(self, axes: List[str] | None = None):
        if axes is None:
            axes = ALL_AXES
        self.axes = axes

        # Create neurons per axis
        self.met_neurons: Dict[str, Neuron] = {}
        self.haircell_neurons: Dict[str, Neuron] = {}
        self.afferent_regular: Dict[str, Neuron] = {}
        self.afferent_irregular: Dict[str, Neuron] = {}

        # Bundles
        self.bundles_met_to_hc: Dict[str, SynapticBundle] = {}
        self.bundles_hc_to_aff: Dict[str, SynapticBundle] = {}

        for axis in axes:
            # Create neurons
            met = Neuron(_met_config(axis))
            hc = Neuron(_haircell_config(axis))
            aff_r = Neuron(_afferent_regular_config(axis))
            aff_i = Neuron(_afferent_irregular_config(axis))

            self.met_neurons[axis] = met
            self.haircell_neurons[axis] = hc
            self.afferent_regular[axis] = aff_r
            self.afferent_irregular[axis] = aff_i


            # Bundle: MET → HairCell
            b_met_hc = SynapticBundle(
                config=BundleConfig(
                    bundle_id=f"met_to_hc_{axis}",
                    learning_rule="stdp",
                    initial_weight=0.5,    # moderate (standard chemical synapse)
                    stdp_lr=0.005,
                    # Gain: HC needs to reach Ca threshold (0.308) from rest (0.115)
                    # ΔV = 0.193 in ~200 steps, C=1.0
                    # I_needed = 0.193 / (0.002 * 200) = 0.48
                    # I_without = act(1.0) × G(1.0) = 1.0 → gain = 0.48/1.0 ≈ 1
                    # But MET activation rises slowly, so need more gain
                    synapse_gain=5.0,
                ),
                sources=[met],
                targets=[hc],
            )
            self.bundles_met_to_hc[axis] = b_met_hc

            # Bundle: HairCell → Afferents (regular + irregular)
            b_hc_aff = SynapticBundle(
                config=BundleConfig(
                    bundle_id=f"hc_to_aff_{axis}",
                    learning_rule="frozen",  # ribbon synapse: no STDP
                    # REF: Bao et al. 2003 — ribbon synapse = structurally stable
                    initial_weight=0.8,    # BIO: ribbon synapse (calibrated)
                    weight_max=0.95,       # cap prevents over-drive
                    # Gain derivation (after Ca fix):
                    # release_ss ≈ 0.4, G(w=0.8) = 0.48
                    # Target 50 Hz: ISI=20, ΔV=0.153, C=0.5
                    # I_needed = 0.153 × 0.5 / (20 × 0.001) = 3.83
                    # gain = 3.83 / (0.4 × 0.48) = 19.9 → 20
                    synapse_gain=20.0,
                ),
                sources=[hc],
                targets=[aff_r, aff_i],
            )
            self.bundles_hc_to_aff[axis] = b_hc_aff

    def step(self, mechanical_inputs: Dict[str, float], dt: float = 1.0):
        """Process one time step.

        Args:
            mechanical_inputs: per-axis mechanical deflection values.
                Keys: axis names (e.g. "yaw", "pitch", "oto_x")
                Values: local strain / radial velocity (float)
            dt: time step
        """
        for axis in self.axes:
            deflection = mechanical_inputs.get(axis, 0.0)

            # Layer 1: MET
            met = self.met_neurons[axis]
            met.step(deflection, dt)

            # Layer 2: HairCell (receives MET output via bundle)
            currents = self.bundles_met_to_hc[axis].propagate()
            hc = self.haircell_neurons[axis]
            if currents:
                hc.step(currents[0], dt)
            else:
                hc.step(0.0, dt)

            # Layer 3: Release is computed inside HairCell (Ca²⁺ subsystem)
            # hc.release_rate is the output of the Ca²⁺ gate

            # Layer 4: Afferents (receive release_rate via bundle)
            # We inject release_rate as the "activation" of haircell
            # so the bundle can propagate it
            hc.activation = hc.release_rate  # bridge: release → propagation
            # Also update pre_trace so bundle.propagate() uses release_rate
            # (pre_trace was computed from MOSFET output during step())
            import math as _math
            _decay = _math.exp(-dt / max(hc.config.trace_tau_pre * 0.001, 0.001))
            hc.pre_trace = hc.pre_trace * _decay + abs(hc.release_rate)
            hc.pre_trace = min(hc.pre_trace, 10.0)
            aff_currents = self.bundles_hc_to_aff[axis].propagate()
            aff_r = self.afferent_regular[axis]
            aff_i = self.afferent_irregular[axis]
            if len(aff_currents) >= 2:
                aff_r.step(aff_currents[0], dt)
                aff_i.step(aff_currents[1], dt)
            elif len(aff_currents) == 1:
                aff_r.step(aff_currents[0], dt)
                aff_i.step(aff_currents[0], dt)

        # Learning
        for axis in self.axes:
            self.bundles_met_to_hc[axis].learn(dt)
            self.bundles_hc_to_aff[axis].learn(dt)

    def get_output(self) -> Dict[str, Dict[str, float]]:
        """Get per-axis output from afferent neurons.

        Returns dict of axis → {
            "rate_regular": firing rate of regular afferent,
            "rate_irregular": firing rate of irregular afferent,
            "regularity": ISI regularity of regular afferent,
            "release_rate": Ca²⁺ release rate from hair cell,
        }
        """
        output = {}
        for axis in self.axes:
            aff_r = self.afferent_regular[axis]
            aff_i = self.afferent_irregular[axis]
            hc = self.haircell_neurons[axis]

            output[axis] = {
                "rate_regular": aff_r.firing_rate(),
                "rate_irregular": aff_i.firing_rate(),
                "regularity": aff_r.regularity(),
                "release_rate": hc.release_rate,
                "met_activation": self.met_neurons[axis].activation,
                "hc_voltage": hc._membrane.voltage,
            }
        return output

    def get_all_neurons(self) -> List[Neuron]:
        """Get all neurons in the chain (for circuit integration)."""
        neurons = []
        for axis in self.axes:
            neurons.extend([
                self.met_neurons[axis],
                self.haircell_neurons[axis],
                self.afferent_regular[axis],
                self.afferent_irregular[axis],
            ])
        return neurons

    def get_all_bundles(self) -> List[SynapticBundle]:
        """Get all bundles (for circuit integration)."""
        bundles = []
        for axis in self.axes:
            bundles.append(self.bundles_met_to_hc[axis])
            bundles.append(self.bundles_hc_to_aff[axis])
        return bundles

    def summary(self) -> dict:
        output = self.get_output()
        return {
            "axes": self.axes,
            "n_neurons": len(self.get_all_neurons()),
            "n_bundles": len(self.get_all_bundles()),
            "per_axis": output,
        }
