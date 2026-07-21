"""nexus_v1.somatosensory.transducer_neurons — Thermal transducer bridge neurons.

TYPE:BIO — Skin thermal/nociceptive transducer layer.

These neurons bridge the physical SkinPatch (thermal physics object) to
SynapticBundle-based signal propagation.  They are the first cellular stage
of sensory transduction.

Signal paths replaced (HC-009 fix):

  BEFORE (HC-009 direct injection — STDP blind):
    T_skin ──[Python × 0.1]──► thermoreceptor.step(T×0.1, dt)

  AFTER (bundle-mediated transduction):
    T_skin → ThermalInputNeuron.step(T, dt)
           → bundles_transducer_thermo_{pid}.propagate()   [plasticity=False]
           → thermoreceptor.step(current_from_bundle, dt)

  Similarly for nociceptors (TRPV1/TRPA1 dT + damage path).

BIO basis:
  - ThermalInputNeuron: TRPV3/TRPM8 channels at epidermis-dermis junction.
    REF: Brauchi et al. 2004 J Physiol — TRPV3 thermal threshold 33-39°C.
    REF: McKemy et al. 2002 Nature — TRPM8 cool-detector, threshold ~25°C.
  - NociInputNeuron: TRPV1/TRPA1 channels responding to dT/dt and damage.
    REF: Caterina et al. 1997 Nature — TRPV1 heat threshold ~43°C, dT/dt.
    REF: Bautista et al. 2006 Cell — TRPA1 injury/chemical detector.

Design constraints (from 2026-07-03 design lock):
  - These neurons override step() to bypass RC membrane dynamics.
    Justification: SkinPatch already applies τ=5s RC thermal integration;
    adding a second RC stage would double-filter the signal.
  - Transducer bundles MUST have learning_rule="frozen" (plasticity=False).
    Justification: TRPV channel transduction coefficients are evolution-fixed
    physical constants, not individually learned parameters.
    REF: Part 2 feedback report 2026-07-03, §1.4 — three-layer argument.
"""

from __future__ import annotations

from ..components.neuron import Neuron, NeuronConfig, ChannelConfig
from ..circuit.bundle import SynapticBundle, BundleConfig


# ─────────────────────────────────────────────────────────────────────────────
# Transduction gain constants (mirrors SomatosensoryChain class constants)
# ─────────────────────────────────────────────────────────────────────────────

# BIO: TRPV3/TRPM8 transduction efficiency ~10% (Brauchi et al. 2004)
# Maps raw T_skin [0-5 sim units] to thermoreceptor current [0-0.5].
# Synchronized with SomatosensoryChain.THERMAL_TRANSDUCTION_GAIN = 0.1.
_THERMAL_TRANSDUCTION_GAIN: float = 0.1

# No additional gain for noci (noci_total is already scaled by NOCI_DT_GAIN=200
# in SomatosensoryChain.step() before being passed to NociInputNeuron.step()).
_NOCI_TRANSDUCER_GAIN: float = 1.0


# ─────────────────────────────────────────────────────────────────────────────
# ThermalInputNeuron — TRPV3/TRPM8 warm/cool detector bridge
# ─────────────────────────────────────────────────────────────────────────────

class ThermalInputNeuron(Neuron):
    """TYPE:BIO — Cutaneous thermoreceptor transduction layer.

    BIO: TRPV3/TRPM8 ion channels at the epidermis-dermis junction.
         Temperature → ionic current is a fixed physical property of the
         channel protein complex; not individually learned.
    REF: Brauchi et al. 2004 J Physiol 558:647 — TRPV3 Q10 ≈ 14.
    REF: Hensel 1973 Physiol Rev 53:551 — cutaneous thermoreceptor physiology.
    PHYS: step() bypasses RC membrane dynamics (SkinPatch τ=5s handles
          thermal integration); only traces updated for bundle compatibility.
    """

    # BIO: TRPV3 warm threshold ~33°C.
    # Ambient T_skin ≈ 0.1 sim units; 0.05 fires above ambient.
    # REF: Moqrich et al. 2005 Science 307:1468 — TRPV3 expressed in keratinocytes.
    T_THRESHOLD: float = 0.05

    # Trace decay: τ ≈ 100 steps = 0.1s (for Census/Noether visibility).
    _TRACE_DECAY: float = 0.99

    def __init__(self, patch_id: str,
                 position: tuple = (0.0, 0.0, 0.0)) -> None:
        # Minimal NeuronConfig: non-spiking passthrough.
        # capacitance=0.001 → τ≈1ms (near-instantaneous; SkinPatch handles τ=5s).
        # BIO: TRPV3 channel at epidermis-dermis junction, r=2mm from body center.
        config = NeuronConfig(
            neuron_id=f"thermo_input_{patch_id}",
            position=position,
            capacitance=0.001,
            r_leak=1.0,
            inertia=0.0,
            vdd=2.0,
            r_supply=0.01,
        )
        super().__init__(config)

    def step(self, T_raw: float, dt: float = 1.0) -> float:
        """Update transducer state from raw skin temperature.

        Bypasses RC + MOSFET dynamics (SkinPatch already applies τ=5s).

        Args:
            T_raw: SkinPatch.current_temperature (sim units)
            dt:    timestep (seconds; used for trace decay)

        Returns:
            activation (= max(0, T_raw - T_THRESHOLD))
        """
        # Linear transduction above warm threshold (TRPV3 open-channel regime)
        self.activation = max(0.0, T_raw - self.T_THRESHOLD)

        # Traces for Bundle propagation and Census/Noether audit.
        self.pre_trace = (self.pre_trace * self._TRACE_DECAY
                          + abs(self.activation))
        self.pre_trace = min(self.pre_trace, 10.0)
        self._activation_ema += 0.01 * (abs(self.activation) - self._activation_ema)
        self._prev_activation = self.activation
        return self.activation


# ─────────────────────────────────────────────────────────────────────────────
# NociInputNeuron — TRPV1/TRPA1 nociceptive transduction bridge
# ─────────────────────────────────────────────────────────────────────────────

class NociInputNeuron(Neuron):
    """TYPE:BIO — Cutaneous nociceptive transduction layer.

    BIO: TRPV1/TRPA1 ion channels at C-fiber free nerve endings.
         |dT/dt| × gain + damage × 10 → ionic current; evolution-fixed gain.
    REF: Caterina et al. 1997 Nature 389:816 — TRPV1 heat + capsaicin.
    REF: Bautista et al. 2006 Cell 124:1269 — TRPA1 injury/chemical pain.
    PHYS: step() receives pre-scaled noci_total (NOCI_DT_GAIN already applied).
    """

    _TRACE_DECAY: float = 0.99

    def __init__(self, patch_id: str,
                 position: tuple = (0.0, 0.0, 0.0)) -> None:
        # BIO: TRPV1 C-fiber terminal at epidermis-dermis junction, r=2mm.
        config = NeuronConfig(
            neuron_id=f"noci_input_{patch_id}",
            position=position,
            capacitance=0.001,
            r_leak=1.0,
            inertia=0.0,
            vdd=2.0,
            r_supply=0.01,
        )
        super().__init__(config)

    def step(self, noci_total: float, dt: float = 1.0) -> float:
        """Update transducer state from nociceptive signal.

        Args:
            noci_total: abs(dT) × NOCI_DT_GAIN + damage × 10.0
            dt:         timestep (seconds)

        Returns:
            activation (= max(0, noci_total))
        """
        # Rectified passthrough: TRPV1/TRPA1 respond only to positive stimuli
        self.activation = max(0.0, noci_total)
        self.pre_trace = (self.pre_trace * self._TRACE_DECAY
                          + abs(self.activation))
        self.pre_trace = min(self.pre_trace, 10.0)
        self._activation_ema += 0.01 * (abs(self.activation) - self._activation_ema)
        self._prev_activation = self.activation
        return self.activation


# ─────────────────────────────────────────────────────────────────────────────
# Transducer bundle factories — frozen bundles (plasticity=False)
# ─────────────────────────────────────────────────────────────────────────────

def make_transducer_bundle_thermo(patch_id: str,
                                   thermo_input: ThermalInputNeuron,
                                   thermoreceptor: Neuron) -> SynapticBundle:
    """Create frozen transducer bundle: ThermalInputNeuron → Thermoreceptor.

    plasticity=False (learning_rule="frozen"):
        TRPV3/TRPM8 transduction coefficient is evolution-fixed.
    synapse_gain=0.1:
        Maps T_skin [0-5 sim units] to current [0-0.5], preserving old
        HC-009 signal magnitude (T × 0.1 → thermoreceptor input).

    BIO: transduction efficiency ~10% (Brauchi et al. 2004).
    """
    return SynapticBundle(
        config=BundleConfig(
            bundle_id=f"transducer_thermo_{patch_id}",
            # BIO: TRPV3/TRPM8 transduction gain is species-conserved.
            # REF: Desai et al. 2005 Neuron 48:977 — thermoreceptor channel
            #      properties are genetically fixed, not plastic.
            learning_rule="frozen",
            initial_weight=1.0,
            # CROSS-MODAL [A/°C → sim current]: TRPV3 transduction efficiency ≈ 0.1
            synapse_gain=_THERMAL_TRANSDUCTION_GAIN,
            bundle_role="feedforward",
        ),
        sources=[thermo_input],
        targets=[thermoreceptor],
    )


def make_transducer_bundle_noci(patch_id: str,
                                 noci_input: NociInputNeuron,
                                 nociceptor: Neuron) -> SynapticBundle:
    """Create frozen transducer bundle: NociInputNeuron → Nociceptor.

    plasticity=False (learning_rule="frozen"):
        TRPV1/TRPA1 transduction coefficient is evolution-fixed.
    synapse_gain=1.0:
        noci_total is already scaled by NOCI_DT_GAIN (200×) before
        passing to NociInputNeuron — no additional gain needed here.

    BIO: TRPV1/TRPA1 dT/dt sensitivity is species-conserved.
    REF: Caterina et al. 1997 — TRPV1 threshold invariant across rodents.
    """
    return SynapticBundle(
        config=BundleConfig(
            bundle_id=f"transducer_noci_{patch_id}",
            # BIO: TRPV1/TRPA1 transduction constants are not plastic.
            # REF: Caterina et al. 1997; Bautista et al. 2006.
            learning_rule="frozen",
            initial_weight=1.0,
            synapse_gain=_NOCI_TRANSDUCER_GAIN,
            bundle_role="feedforward",
        ),
        sources=[noci_input],
        targets=[nociceptor],
    )


# ─────────────────────────────────────────────────────────────────────────────
# ThermalDeltaNeuron — warm-onset (dT/dt > 0) transducer for VTA reward
# ─────────────────────────────────────────────────────────────────────────────

# BIO: Type II AMH (A-δ fibers) respond specifically to warming (dT/dt > 0).
# Project: dorsal horn Lamina I → parabrachial nucleus (LPB) → VTA DA neurons.
# REF: Norris et al. 2021 Nat Neurosci — LPB→VTA pathway for thermal reward.
# REF: LaMotte & Campbell 1978 J Neurophysiol — Type II AMH warm-onset firing.
# SEMI: MOSFET half-wave rectification — only positive dT conducts (warming).
#       Cooling (dT < 0) is blocked; handled separately by TRPA1/NociInputNeuron.
#
# Gain calibrated from SomatosensoryChain.NOCI_DT_GAIN = 200 (chain.py L377-382):
#   I_warmth = dT × WARM_ONSET_GAIN = 5e-5 × 200 = 0.01 at baseline approach rate.
_WARM_ONSET_GAIN: float = 200.0


class ThermalDeltaNeuron(Neuron):
    """TYPE:BIO|SEMI — Warm-onset thermoreceptor transducer for VTA reward signal.

    BIO: Type II AMH (A-δ) fibers at skin surface detect dT/dt > 0 (approach
         to warm stimulus). Project via Lamina I → lateral parabrachial nucleus
         (LPB) → VTA dopaminergic neurons, driving DA burst on warm-field entry.
    REF: Norris et al. 2021 Nat Neurosci 24:1407 — LPB→VTA thermal reward.
    REF: LaMotte & Campbell 1978 J Neurophysiol 41:924 — Type II AMH warm-onset.
    SEMI: MOSFET half-wave: activation = max(0, dT × WARM_ONSET_GAIN).
    PHYS: step() bypasses RC (SkinPatch already applies τ=5s integration).

    FIX-019 (2026-07-21, DEG-015): `activation` now clamped to
    `_ACTIVATION_MAX=10.0` (matching the base `Neuron.step()` ±10.0
    activation clamp convention already used everywhere else — see
    `neuron.py:438/466`). Root cause: this class fully overrides
    `Neuron.step()` (PHYS note above) and therefore never went through
    that base-class clamp, so its output was genuinely unbounded
    (`dT_raw × 200`, linear, no ceiling). P2-A generator-core root-cause
    diagnosis (`exp_P2A_highinput_root_cause.py`, u=0.1/0.2/0.5 fine
    sweep) empirically confirmed: downstream ensemble neurons' `PowerRail`
    IR-drop (`semiconductor.py:290-294`, `v_actual=max(0,vdd-I·r_internal)`)
    saturates smoothly-but-fully to 0 once L1's unbounded output drives
    injected current past `vdd/r_internal`; at `activation=20` (u=0.1)
    ensemble `PowerRail.v_actual` was already down to ~0.03-0.04 (nearly
    fully collapsed), and by `activation=30` (u=0.15) it was exactly 0 for
    every ensemble neuron — silencing the entire downstream pathway. This
    is the same collapse family already logged as
    `project_memristor_saturation_edge_bug`/DEG-014 (PowerRail draws current
    beyond its rail capacity → v_avail clamps to 0), recurring here because
    the 2026-07-11 fix for that bug only capped the L1→HC bundle weight
    (assuming "dT≤0.1 stays safe"), not L1's own output — an assumption
    silently violated once P2-A1a scanned dT beyond 0.1.
    `_ACTIVATION_MAX=10.0` keeps ensemble `PowerRail.v_actual` at ≈0.46-0.48
    (meaningfully alive, not collapsed) at the cap, verified empirically
    by the same diagnostic script.
    """

    _TRACE_DECAY: float = 0.99
    _ACTIVATION_MAX: float = 10.0

    def __init__(self, patch_id: str,
                 position: tuple = (0.0, 0.0, 0.0)) -> None:
        config = NeuronConfig(
            neuron_id=f"thermo_delta_{patch_id}",
            position=position,
            capacitance=0.001,
            r_leak=1.0,
            inertia=0.0,
            vdd=2.0,
            r_supply=0.01,
        )
        super().__init__(config)

    def step(self, dT_raw: float, dt: float = 1.0) -> float:
        """Update from raw skin temperature derivative (signed dT per step).

        Args:
            dT_raw: patch_temps[pid][1] — raw dT per timestep (signed).
            dt:     timestep (seconds; used for trace decay).

        Returns:
            activation = clip(max(0, dT_raw × WARM_ONSET_GAIN), 0, _ACTIVATION_MAX)
                         (MOSFET half-wave: zero output on cooling; upper
                         clamp added by FIX-019, see class docstring)
        """
        self.activation = min(
            max(0.0, dT_raw * _WARM_ONSET_GAIN), self._ACTIVATION_MAX)
        self.pre_trace = (self.pre_trace * self._TRACE_DECAY
                          + abs(self.activation))
        self.pre_trace = min(self.pre_trace, 10.0)
        self._activation_ema += 0.01 * (abs(self.activation) - self._activation_ema)
        self._prev_activation = self.activation
        return self.activation


def make_thermo_delta_to_da_bundle(patch_id: str,
                                    delta_neuron: 'ThermalDeltaNeuron',
                                    da_neurons: list) -> SynapticBundle:
    """Create frozen bundle: ThermalDeltaNeuron → all DA neurons.

    Frozen (innate): LPB→VTA thermal projection is anatomically hardwired.
    REF: Norris et al. 2021 — LPB→VTA exists in naive (unlearned) animals.

    Q3 Parameter derivation:
      initial_weight=0.1: G(0.1)≈0.111; I_peak=0.05×0.111×1.0≈0.0056A.
        Matches CPG bundle amplitude (cpg_bundle w=0.1, sg=0.1→after cut: 0.00056A).
        Target: warm-onset DA burst ~5× stronger than residual CPG → phasic drive.
      synapse_gain=1.0: unit; calibrated against relay_to_da sg=0.2 but 3× relays.
      weight_max=0.1: frozen at initial (innate anatomy, not plastic).
      EXP-BASE-200K: warm approach dT≈0.00025/step → activation=0.05 → I=0.0056A ✓
    """
    return SynapticBundle(
        config=BundleConfig(
            bundle_id=f"thermo_delta_to_da_{patch_id}",
            learning_rule="frozen",
            initial_weight=0.1,
            weight_max=0.1,
            synapse_gain=1.0,
            bundle_role="feedforward",
            remodel_cost_kappa=0.0,
        ),
        sources=[delta_neuron],
        targets=da_neurons,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Thermal hair-cell analog (Level 2 of quantum-thermal reconstruction)
# ─────────────────────────────────────────────────────────────────────────────

def _thermo_haircell_config(patch_id: str, position: tuple = (0.0, 0.0, 0.0),
                             region: int = 0x00) -> NeuronConfig:
    """TYPE:BIO — Thermal hair-cell analog: multi-channel graded transducer.

    BIO: Free nerve ending thermoreceptor with genuine membrane dynamics,
         replacing the single-formula ThermalDeltaNeuron shortcut with a
         multi-channel HH-equivalent — same structural pattern as the
         vestibular hair cell (_haircell_config, vestibular/chain.py:152).
    REF: Vriens et al. 2014 Neuron 82:730 — TRP channel thermosensation.
    REF: Cesare & McNaughton 1996 J Physiol 495:517 — thermoreceptor
         adaptation/desensitization to sustained stimuli (the behavior
         ThermalDeltaNeuron's memoryless max(0, dT*gain) formula lacks).
    REF: Roberts et al. 1990 J Neurosci — Ca²⁺ release subsystem (same
         structural form as the vestibular hair cell, retuned below for
         thermal (second-scale) rather than mechanical (ms-scale) kinetics).

    Q1. BIO: TRP channel (fast excitatory) + K+ adaptation channel (slow
        inhibitory, provides desensitization) + Ca2+ channel (graded release).
    Q2. Level1(ThermalDeltaNeuron, ±dT) → [frozen bundle] → this hair-cell
        analog → [frozen bundle] → quantum ensemble(10).
    Q3. Structure copied verbatim from _haircell_config's 3-channel +
        Ca2+-subsystem form (vestibular/chain.py:161-198). Numeric values
        are placeholders pending calibration against synthetic thermal
        scenarios (thermal adaptation time constants are ~1-10s, vs
        vestibular's ms-scale — NOT the same numbers, only the same
        equation structure is reused). Flagged TODO-CALIBRATE below.
    """
    return NeuronConfig(
        neuron_id=f"thermo_hc_{patch_id}",
        position=position,
        region=region,
        capacitance=1.0,
        r_leak=5.0,
        inertia=1.0,
        vdd=1.0,
        r_supply=0.05,
        v_rest=0.115,
        channels=[
            # TRP current channel (excitatory, fast) — analog of MET channel.
            ChannelConfig(
                name="trp",
                v_threshold=0.05,
                gm=1.0,
                tau_gate=0.0,
                reversal=0.615,
                sign=1.0,
            ),
            # K+ adaptation channel (inhibitory, slow) — TODO-CALIBRATE:
            # tau_gate here sets desensitization speed; placeholder value
            # copied from vestibular (ms-scale) pending thermal-scale
            # (second-scale, Cesare & McNaughton 1996) recalibration.
            ChannelConfig(
                name="k",
                v_threshold=0.385,
                gm=0.67,
                tau_gate=0.005,
                reversal=0.0,
                sign=-1.0,
            ),
            # Ca channel (excitatory, medium) — feeds Ca2+ release subsystem.
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
        # Ca2+ subsystem — TODO-CALIBRATE: structure copied from
        # _haircell_config verbatim; thermal receptor clearance/release
        # kinetics need their own measurement (not the same numbers as
        # vestibular's Ca2+ clearance, which is tuned to ms-scale synaptic
        # release, not second-scale thermal adaptation).
        ca_capacitance=0.2,
        ca_r_leak=20.0,
        ca_release_threshold=0.01,
        ca_release_gm=0.30,
        use_voltage_regulator=True,
        vr_base_rate=0.001,
        vr_activity_coeff=0.3,
        vr_max_rate=3.0,
    )


def make_thermo_l1_to_hc_bundle(patch_id: str, delta_neuron: 'ThermalDeltaNeuron',
                                 hc_neuron: 'Neuron') -> SynapticBundle:
    """Create frozen bundle: ThermalDeltaNeuron (Level1) → thermal hair-cell (Level2).

    Frozen (innate): TRP channel transduction coefficients are evolution-fixed
    physical constants, not individually learned (same justification as the
    other transducer bundles in this module — see module docstring).

    Q3: initial_weight=0.3（非 1.0）—— 实测发现的边缘案例：Memristor 电导
        G=1/(r_min+ΔR(1-w))，w=1.0 时 G=10.0（=1/r_min，物理上限）。
        SynapticBundle 构造时对每条 bundle 施加 ±25%"对称性打破"随机扰动
        （bundle.py:170-173，基于 bundle_id 哈希），若 initial_weight 卡在
        weight_max=1.0 附近，扰动可能把某些实例推到 w≈1.0（G=10），使注入
        电流 4.0(dT=0.02时L1峰值)×10=40 远超 PowerRail 饱和点
        vdd/r_supply=1.0/0.05=20，导致电流被 IR-drop 完全钳死为 0——而另一
        些实例扰动推低了 w，电导降到安全区间，正常工作。这曾在 warm/cool
        对称构造中制造出一侧沉默一侧正常的假性"整流失败"（2026-07-11 调试
        记录）。initial_weight=0.3 → G(0.3)≈0.14，即使在扰动+dT=0.1 上限下
        注入电流仍 <4，远离饱和点，两个极性对称工作。
    """
    return SynapticBundle(
        config=BundleConfig(
            bundle_id=f"thermo_l1_to_hc_{patch_id}",
            learning_rule="frozen",
            initial_weight=0.3,
            weight_max=0.3,
            synapse_gain=1.0,
            bundle_role="feedforward",
            remodel_cost_kappa=0.0,
        ),
        sources=[delta_neuron],
        targets=[hc_neuron],
    )
