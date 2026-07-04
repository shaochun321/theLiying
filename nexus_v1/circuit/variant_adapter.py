"""nexus_v1.circuit.variant_adapter — VariantCircuit.

Inherits HebbianCircuit and overlays variant components.
DOES NOT MODIFY any existing code — pure extension via inheritance.

Rollback: replace VariantCircuit() with HebbianCircuit() anywhere.

Variant components added:
    1. ResonantOscillator: ISI synchronization for afferents
    2. MagnetofluidDamper: adaptive impedance on Enc/Col leak
    3. ExtracellularMatrix: ion buffering + thermal field + PNN
    4. VascularCooling: NVC heat removal + energy delivery
    5. NDRElement: refractory gating on afferents
    6. InhibitorySynapse: lateral inhibition between columns
    7. LiquidMetalRouter: dynamic Enc→Col topology
    8. Neuromodulator: DA three-factor learning
    9. Motor→Column feedback: efference copy (corollary discharge)
   10. World + Body: 3D environment with consumable heat sources
   11. ThermalMembrane: cell surface thermosensing (MCP receptor arrays)
   12. MuscleSystem: Motor neuron → physical force → body movement
"""

from typing import Dict, List

from ..components.neuron import Neuron, NeuronConfig, ChannelConfig

import math

from .hebbian import HebbianCircuit
from ..components.oscillator import ResonantOscillator
from ..components.damper import MagnetofluidDamper
from ..components.ecm import ExtracellularMatrix, create_vestibular_ecm
from ..components.vascular import VascularCooling, create_brainstem_vascular
from ..components.ndr import NDRElement, InhibitorySynapse
from ..components.router import LiquidMetalRouter
from ..components.modulator import Neuromodulator, create_dopamine
from ..components.binding_temporal import TemporalBindingLayer
from ..components.yolk_sac import YolkSac
from ..components.da_differential_gate import DADifferentialGate
from ..components.shadow_sandbox import ShadowSandbox
from ..components.world import World, Body, HeatSource
from ..components.heat_source import CylindricalHeatSource
from ..components.thermal_mouth import ThermalMouth
from ..components.digestive_interface import DigestiveInterface
from ..components.thermal_membrane import ThermalMembrane
from ..components.muscle import MuscleSystem
from ..somatosensory.chain import SomatosensoryChain
from ..somatosensory.transducer_neurons import (
    ThermalDeltaNeuron, make_thermo_delta_to_da_bundle)
from ..components.energy_store import EnergyStore
from ..components.vital_oscillator import VitalOscillator
from ..components.cpg_neuron import CPGNeuron
from ..components.circulation_proportion import CirculationProportionCircuit
from ..components.spinal_reflex import SpinalReflexArc
from ..components.agc import AutomaticGainControl
from ..components.langevin_noise import LangevinNoise
from .bundle import SynapticBundle, BundleConfig
from .circulation import CirculationMeter
from .motor_decision import MotorDecisionLayer, MotionState
from ..ledger import (WeightEntropyProbe, TOPRXinLedger, RecursionTracker,
                      UltrametricSpace, StructuralEntropy, StructuralBridge,
                      EntropyLedger, NoetherProbe, ComponentRegistry)
from .region_topology import (
    REGION_SPINAL, REGION_BRAINSTEM, REGION_MAIN,
    REGION_HYPOTHALAMUS, REGION_SHADOW,
)
from ..components.semiconductor import Capacitor

# Governance: parallel system, co-equal with nexus_v1
import sys as _sys
import os as _os
_governance_path = _os.path.dirname(_os.path.dirname(_os.path.dirname(
    _os.path.abspath(__file__))))
if _governance_path not in _sys.path:
    _sys.path.insert(0, _governance_path)
try:
    from governance import GovernanceSystem, GovernanceConfig
    _GOVERNANCE_AVAILABLE = True
except ImportError:
    _GOVERNANCE_AVAILABLE = False


# ── A3: Thermal delay buffer for finite heat propagation ──

class _ThermalDelayBuffer:
    """TYPE:INFRA — FIFO delay line for inter-layer heat propagation (A3 fix).

    Heat entering the buffer takes `delay_steps` ticks to emerge.
    Models finite thermal propagation speed in tissue.

    BIO: thermal diffusivity α ≈ 0.14 mm²/s in brain (Elwassif 2006).
    For distance d between layers: delay ≈ d²/(2α).

    Electronic analog: transmission line delay (LC ladder network).
    """

    def __init__(self, delay_steps: int = 100):
        self._delay = max(1, delay_steps)
        self._buffer = [0.0] * self._delay
        self._head = 0  # write position

    def push(self, heat_flow: float) -> float:
        """Push new heat flow in, return delayed heat flow out.

        Args:
            heat_flow: signed heat flow (positive = A→B, negative = B→A)

        Returns:
            Heat flow that was pushed delay_steps ago.
        """
        # Read the oldest value (output)
        output = self._buffer[self._head]
        # Write new value
        self._buffer[self._head] = heat_flow
        # Advance head (circular buffer)
        self._head = (self._head + 1) % self._delay
        return output


class VariantCircuit(HebbianCircuit):
    """TYPE:INFRA — HebbianCircuit + variant components (oscillator + damper).

    Design principle: INHERIT, DON'T MODIFY.
    - HebbianCircuit.__init__() runs 100% unchanged
    - HebbianCircuit.step() runs 100% unchanged
    - Variant effects are applied AFTER the mother step

    This means:
    1. If variant breaks anything → use HebbianCircuit instead
    2. Mother contracts can be verified independently
    3. No risk of corrupting the mother codebase
    """

    def __init__(self):
        # ── Mother initialization with thermal patch axes ──
        # 4 skin patches → 4 extra axes in the Hebbian circuit
        _patch_axes = ["therm_front", "therm_back", "therm_left", "therm_right"]
        super().__init__(extra_axes=_patch_axes)

        # ── Variant: Oscillators for afferent ISI synchronization ──
        # REF: Vestibular nucleus tonic oscillation
        # One oscillator per axis, injected into regular afferents
        self.oscillators: Dict[str, ResonantOscillator] = {}
        for axis in self.vestibular.axes:
            self.oscillators[axis] = ResonantOscillator(
                frequency=50.0,     # match target Aff frequency
                mu=1.0,             # moderate nonlinearity
                amplitude=0.15,     # modulation depth ±15% (sweet spot)
                # Modulation strategy (not direct injection):
                # Multiply HC→Aff gain by (1 + osc_output)
                # This entrains spike timing to oscillation peaks
                # without injecting extra energy into the membrane
                # BIO: efference copy modulates synapse efficacy
            )

        # ── Variant: Dampers for Encoding/Column adaptive impedance ──
        # REF: Myelin — high activity → more insulation
        self.dampers_enc: Dict[str, MagnetofluidDamper] = {}
        self.dampers_col: Dict[str, MagnetofluidDamper] = {}
        for axis in self.vestibular.axes:
            self.dampers_enc[axis] = MagnetofluidDamper(
                r_base=1.0,
                alpha=0.3,          # mild damping
                beta=0.05,          # weak self-induction
            )
            self.dampers_col[axis] = MagnetofluidDamper(
                r_base=1.0,
                alpha=0.2,          # weaker damping (integration layer)
                beta=0.03,
            )

        # ── Variant: ECM per layer (thermal + ion buffer + PNN) ──
        # One ECM per layer to track local thermal state
        # BIO: different brain regions have different ECM density
        self.ecm_vestibular = create_vestibular_ecm()
        self.ecm_encoding = ExtracellularMatrix(
            thermal_capacity=4.0,
            thermal_conductance=0.6,
            ion_buffer_tau=0.1,
            pnn_target=0.5,
            capacitance_boost=0.2,
        )
        self.ecm_column = ExtracellularMatrix(
            thermal_capacity=5.0,
            thermal_conductance=0.5,
            ion_buffer_tau=0.15,
            pnn_target=0.7,         # higher PNN in integration layers
            capacitance_boost=0.25,
        )

        # ── Variant: Vascular cooling (NVC) ──
        # Global vascular system for the circuit
        self.vascular = create_brainstem_vascular()

        # ── Variant: NDR for afferent refractory gating ──
        # BIO: Na⁺ inactivation refines refractory period
        # EE: tunnel diode creates self-limiting current
        self.ndr_afferent: Dict[str, NDRElement] = {}
        for axis in self.vestibular.axes:
            self.ndr_afferent[axis] = NDRElement(
                v_peak=0.15,        # threshold for NDR onset
                v_valley=0.35,      # end of NDR region
                g_positive=2.0,     # standard
                tau_h=5.0,          # inactivation τ (ms)
            )

        # ── Variant: Lateral inhibition between column neurons ──
        # BIO: cortical surround suppression (Hartline 1957)
        # Each column neuron inhibits every OTHER column neuron
        axes = list(self.vestibular.axes)
        connections = []
        for i in range(len(axes)):
            for j in range(len(axes)):
                if i != j:
                    connections.append((i, j))
        self.lateral_inhibition = InhibitorySynapse(
            ndr=NDRElement(v_peak=0.1, v_valley=0.3),
            gain=0.05,          # gentle inhibition
            connections=connections,
        )

        # ── C2 fix: Cross-axis motor lateral inhibition ──
        # BIO: Vestibulospinal push-pull (Shimazu & Precht 1966).
        # When yaw drives move_x strongly, move_y and move_z should
        # be suppressed. Without this, all three motors saturate equally.
        # Structure: all-to-all inhibition between move_x, move_y, move_z.
        motor_connections = [(0,1),(0,2),(1,0),(1,2),(2,0),(2,1)]
        self.motor_lateral_inhibition = InhibitorySynapse(
            ndr=NDRElement(v_peak=0.1, v_valley=0.4),
            gain=0.15,          # stronger than column inhibition
            connections=motor_connections,
        )
        self._col_axes_order = axes  # fixed order for indexing

        # ── B1b: Renshaw interneurons (HC-023 replacement) ──
        # BIO: Renshaw cells are spinal inhibitory interneurons activated by
        #      motor axon collaterals; they recurrently inhibit the same and
        #      adjacent motor neuron pools (Eccles et al. 1961, J Physiol).
        # Q1 BIO: α-motor neuron collateral → Renshaw cell → motor pool
        #         inhibition (Eccles 1961, J Physiol 155:586–606).
        # Q2 Structure: motor_{x,y,z} (0x03) → [frozen, gain=1.0, w=0.3]
        #              → renshaw_{x,y,z} (0x01)
        #              → [frozen, gain=-0.5, w=0.3]
        #              → motor_{others} (0x03)
        # Q3 Params: excit gain=1.0 (collateral strength = soma strength),
        #            inhib gain=-0.5 (Renshaw inhibition ~50% of excit, Dale 2003),
        #            w=0.3 (matches relay lateral inh pattern in P0-B).
        _motor_key_order = ['move_x', 'move_y', 'move_z']
        self.renshaw_neurons = {}
        for axis in _motor_key_order:
            suffix = axis.split('_')[1]  # x, y, z
            self.renshaw_neurons[axis] = Neuron(NeuronConfig(
                neuron_id=f'renshaw_{suffix}',
                capacitance=1.0,
                r_leak=5.0,
                region=0x01,
                spiking=False,
            ))
        # Excitatory bundles: motor → renshaw (1:1, one per axis)
        self.bundles_renshaw_excit = []
        for mkey in _motor_key_order:
            self.bundles_renshaw_excit.append(SynapticBundle(
                config=BundleConfig(
                    bundle_id=f'motor_{mkey.split("_")[1]}_to_renshaw',
                    learning_rule='frozen',
                    initial_weight=0.3,
                    synapse_gain=1.0,
                ),
                sources=[self.motor_neurons[mkey]],
                targets=[self.renshaw_neurons[mkey]],
            ))
        # Inhibitory bundles: renshaw → other two motors (1:2, one per axis)
        self.bundles_renshaw_inhib = []
        for i, mkey in enumerate(_motor_key_order):
            other_motors = [self.motor_neurons[k]
                            for k in _motor_key_order if k != mkey]
            self.bundles_renshaw_inhib.append(SynapticBundle(
                config=BundleConfig(
                    bundle_id=f'renshaw_{mkey.split("_")[1]}_inhib',
                    learning_rule='frozen',
                    initial_weight=0.3,
                    synapse_gain=-0.5,
                ),
                sources=[self.renshaw_neurons[mkey]],
                targets=other_motors,
            ))

        # ── Variant: LiquidMetalRouter on Enc→Col connections ──
        # BIO: structural plasticity (Holtmaat 2009)
        # Start connected; correlation drives pruning/strengthening
        self.routers_enc_col: Dict[str, LiquidMetalRouter] = {}
        for axis in self.vestibular.axes:
            router = LiquidMetalRouter(
                g_metal=1.0,
                tau_reconfig=5.0,    # 5s to open/close (slow structural)
                theta_grow=0.1,      # easy to maintain
                theta_prune=0.01,    # very low to prune
                oxide_factor=0.2,
                ema_tau=2.0,         # 2s activity memory
            )
            router.force_connect()   # start with all routes open
            self.routers_enc_col[axis] = router

        # ── Variant: Neuromodulator (Dopamine) ──
        # BIO: VTA DA → reward-gated three-factor learning
        # Motor spikes = "reward signal" → DA release
        self.dopamine = create_dopamine()
        self._prev_motor_spikes: Dict[str, int] = {}
        for key in self.motor_neurons:
            self._prev_motor_spikes[key] = 0

        # ── Variant: Motor → Column inhibitory feedback ──
        # BIO: corollary discharge / efference copy
        # REF: Cullen 2004 — vestibular efference copy
        # Motor activity feeds back to suppress column activation
        # preventing sustained over-drive after motor response
        self._feedback_traces: Dict[str, float] = {}
        for key in self.motor_neurons:
            self._feedback_traces[key] = 0.0
        self._feedback_gain = 0.05   # gentle suppression
        self._feedback_tau = 0.5     # 500ms smoothing

        # ── Variant: Binding Layer (§5 of math spec) ──
        # Patch B: TemporalBindingLayer replaces BindingLayer.
        # STF convolution on vestibular axes (tau_w=30); thermal stays instantaneous.
        # co_activation_threshold=0.0: learning window fully open (calibration doc §1).
        # BIO: Presynaptic Ca2+ remnant, Zucker & Regehr 2002.
        self.binding_layer = TemporalBindingLayer(
            axes=list(self.all_axes),
            co_activation_threshold=0.0,
            tau_w=30,
            thermal_axes={'therm'},
        )

        # Binding → Motor bundle (side channel, parallel to Col→Motor)
        # Uses virtual "binding neurons" represented by their activations
        # Initial weight ≈ 0.001 (dormant per structure-constrains-dynamics)
        # We store binding→motor weights as a simple matrix
        self._binding_motor_weights: Dict[str, Dict[str, float]] = {}
        for bid in self.binding_layer.cells:
            self._binding_motor_weights[bid] = {}
            for mid in self.motor_neurons:
                self._binding_motor_weights[bid][mid] = 0.001  # dormant

        # ── Variant: Shadow Sandbox (read-only dual metric) ──
        self.shadow_sandbox = ShadowSandbox()

        # ── C1: Shadow ν → DA gate (NuThresholdNeuron) ──
        # BIO: Prediction residual ν (free energy change rate) gates VTA DA burst.
        # Q1 BIO: basal ganglia prediction error → VTA DA burst (Schultz 1997;
        #         Friston et al. 2012 "predictive coding and free energy").
        # Q2 Structure: shadow._nu [transducer] → shadow_nu_neuron (0x05)
        #              → [frozen, gain=1.0, w=0.3] → da_neurons (0x03)
        # Q3 NU_SCALE = 1/176 (calibrated: ν_90th = 176.2, 20k-step stat, 2026-07-04).
        #    shadow_nu_neuron: C=0.1 (fast τ=100 steps), R=1.0;
        #    MOSFET v_threshold=0.9 → fires at ν > 0.9×176 = 158 (≈88th percentile).
        #    w=0.3, gain=1.0 → I_DA = activation × 0.3 per DA neuron.
        # NOTE: ν is the shadow layer's macroscopic free-energy rate; NuThresholdNeuron
        #       is a boundary transducer (analogous to ThermalInputNeuron). The conversion
        #       from ν (abstract) to neural current at this boundary IS the transduction.
        #       Physical limitation noted: ν is a lagged aggregate; true phasic DA should
        #       eventually track local Xin collapses. Preserved as a refinement interface.
        self._NU_SCALE = 1.0 / 176.0  # BIO-CAL-2026-07-04: ν_90th = 176.2 (20k baseline)
        self.shadow_nu_neuron = Neuron(NeuronConfig(
            neuron_id='shadow_nu',
            capacitance=0.1,
            r_leak=1.0,
            region=0x05,
            spiking=False,
            channels=[ChannelConfig(name='nu_thresh', v_threshold=0.9, gm=1.0)],
        ))
        # Bundle created after DA neurons are instantiated (see _init_da_neurons call below)
        self.bundle_shadow_nu_to_da = None  # placeholder; initialized after DA neurons

        # ── Variant: 3D World + Body + Thermal + Muscle ──
        # Heat source at [70,50,50], body starts at [50,50,50]
        self.world = World()
        self.thermal_membrane = ThermalMembrane()
        self.muscle_system = MuscleSystem(gain=0.1, delay=2)
        self._patch_temps: dict = {}  # updated each step; exposed for DR5 metric

        # ── Variant: Somatosensory chain (4-patch thermal sensing) ──
        # Parallel to vestibular chain: Thermoreceptor + Nociceptor + SomatoRelay
        # per skin patch. Relay output feeds encoding layer via extra_axes.
        self.somatosensory = SomatosensoryChain(
            patch_ids=["front", "back", "left", "right"],
            lateral_gain=0.3,   # Phase4: 0.05→0.3, amplifies patch contrast via S0 InhibitorySynapse
        )

        # ── Variant: EnergyStore (external reservoir) ──
        # Bridges World.consume_nearby() → Vascular → neuron.energy.
        # External to neural circuit; can be replaced without rewiring.
        # BIO: liver glycogen + blood glucose buffer.
        self.energy_store = EnergyStore()

        # ── Patch C: YolkSac (embryonic bootstrap energy) ──
        # Non-replenishable maternal reserve; discharges at 0.002/step into EnergyStore.
        # Provides baseline energy for STDP during cold-start before feeding.
        # Depletes at step ~100k. BIO: Davidson 2006, The Regulatory Genome, Ch.3.
        self.yolk_sac = YolkSac()

        # ── Patch D: DADifferentialGate (VTA RPE signal) ──
        # DA fires on positive rate-of-change of energy fill, not absolute level.
        # Replaces c3_da_current from circulation_proportion (absolute deviation).
        # BIO: Schultz et al. 1997, Science 275:1593-1599.
        self.da_gate = DADifferentialGate(
            initial_fill=self.energy_store.fill_fraction
        )

        # ── Variant: VitalOscillator (basal heartbeat / tri-heart) ──
        # Three detuned VdP oscillators (2.00, 2.11, 1.93 Hz) produce
        # Lissajous wandering in 3D. Energy-coupled via EnergyStore.
        # Breaks cold-start deadlock by providing basal motor drive.
        # BIO: sinoatrial node → hemodynamic pulsation → postural sway.
        self.vital_oscillator = VitalOscillator()

        # ── B1a: CPC deviation transducer → VitalOscillator amplitude mod ──
        # BIO: LH arousal → PPTg/LDT → locomotor CPG amplitude scaling (Saper 2002).
        # Q1 BIO: LH → PPTg arousal projection (Saper 2002, Nat Rev Neurosci 3:833-843).
        # Q2 Structure: cpc_dev_neuron (hypo, 0x04) → bundle → vital_amp_neuron (brainstem, 0x02).
        # Q3 cpc_dev_neuron: C=1.0, R=3.0 → τ=3s (tonic LH signal, slow arousal);
        #    vital_amp_neuron: C=1.0, R=5.0 → τ=5s (brainstem integration);
        #    gain=0.3, w=0.5 (200k baseline: deviation≈0.05–0.2 → mod≈0.01–0.03).
        self.cpc_dev_neuron = Neuron(NeuronConfig(
            neuron_id='cpc_deviation',
            capacitance=1.0,
            r_leak=3.0,
            region=0x04,
            spiking=False,
        ))
        self.vital_amp_neuron = Neuron(NeuronConfig(
            neuron_id='vital_amp',
            capacitance=1.0,
            r_leak=5.0,
            region=0x02,
            spiking=False,
        ))
        self.bundle_cpc_to_vital = SynapticBundle(
            config=BundleConfig(
                bundle_id='cpc_to_vital',
                learning_rule='frozen',
                initial_weight=0.5,
                synapse_gain=0.3,
            ),
            sources=[self.cpc_dev_neuron],
            targets=[self.vital_amp_neuron],
        )

        # ── L2:SELECTION: Spinal Reflex Arc (nociceptive withdrawal) ──
        # BIO: Aδ-fiber → spinal interneuron → α-motor neuron (Sherrington 1906).
        # DESIGN: Hardwired directional withdrawal from nociceptor spatial contrast.
        #         MOSFET gate (default VDD=open) provides cortical override placeholder.
        # EMERGE: Withdrawal direction is L2-fixed. Cortical override is future L1.
        self.spinal_reflex = SpinalReflexArc()

        # ── Phase 4: Automatic Gain Control (AGC) ──
        # RC leaky integrator driven by physiological deficit (energy + DA).
        # τ ≈ 40k steps — slow enough to avoid interference with Phase 2/3.
        # Output scales hunger reflex drive and Col→Motor bundle currents.
        # BIO: HPA axis cortisol → locomotor drive (Sapolsky 1992).
        self.agc = AutomaticGainControl()

        # ── V8: LangevinNoise (Ornstein-Uhlenbeck thermal noise) ──
        # Provides physical thermal fluctuations to vestibular afferent path.
        # Driven by ECM temperature (endolymph thermal bath).
        # BIO: Johnson-Nyquist noise → hair cell membrane displacement.
        # DESIGN: Sensor-side injection: O_k = a_body + η_k (宏微观同构).
        #         Shadow predictor cannot predict η → persistent Xin residual.
        # REF: langevin_noise.py; 步骤2统一物理架构方案 §二 ECM热浴
        self._langevin = LangevinNoise()

        # ── L2:SELECTION: Overridable feedback loop parameters ──
        # Default values from L2.08 screening (FULL PASS baseline).
        # L2.09 parameter sweep overrides these post-construction.
        self.vital_damage_k: float = 0.5       # Loop A: cardiac depression sensitivity
        self.repair_energy_rate: float = 0.005  # Loop B: repair metabolic tax
        self.k_barrier: float = 2.0             # Loop D: ECM barrier half-saturation
        self.breach_conductance: float = 0.1    # Loop D: breach heat transfer rate

        # ── Variant: CirculationProportionCircuit (C3' structural carrier) ──
        # Three capacitors integrate amplitude signals → voltages = ratios.
        # MOSFET comparator produces deviation → DA current.
        # Replaces software-computed rho_homeo/motor/feed.
        self.circulation_proportion = CirculationProportionCircuit()

        # ── Variant: CirculationMeter ──
        self._circulation_meter = CirculationMeter()
        self.circulation_state = None

        # ── Variant: T/O/P/R/Xin Entropy Ledger (Phase 6) ──
        self._entropy_probe = WeightEntropyProbe()
        self._toprxin_ledger = TOPRXinLedger()
        self._recursion_tracker = RecursionTracker()

        # ── Variant: Candidate Math Framework (Phase 7) ──
        self._ultrametric = UltrametricSpace(self._recursion_tracker)
        self._structural_entropy = StructuralEntropy(self._recursion_tracker)
        self._structural_bridge = StructuralBridge(
            self._ultrametric, self._recursion_tracker, self._entropy_probe)

        # ── Variant: Noether Conservation Probe (T4) ──
        self._noether_probe = NoetherProbe()

        # ── Variant: Energy Ledger (global thermodynamic accounting) ──
        # Tracks energy balance, ISI entropy, layer transfer entropy.
        # Previously existed as dead code (never instantiated).
        self._energy_ledger = EntropyLedger()

        # ── Variant: Component Registry (TYPE tags + census visibility) ──
        self._component_registry = ComponentRegistry()

        # ── Governance: parallel co-equal system ──
        if _GOVERNANCE_AVAILABLE:
            self.governance = GovernanceSystem(
                GovernanceConfig(debug_mode=False))
        else:
            self.governance = None

        # ── RULE S0: Semiconductor components for signal-path computation ──
        from ..components.semiconductor import Capacitor, MOSFET

        # S0-A1: Xin integrator (Capacitor) + release gate (MOSFET)
        # Xin tension accumulates in a Capacitor; MOSFET gates DA release.
        # BIO: VTA prediction-error integration -> DA burst
        # CHECK 2: tau = C*R = 1.0*50 = 50s (matches DA burst timescale ~1-5s)
        # Previous C=10 gave tau=500s -> DA never decayed -> permanent saturation
        self._xin_integrator = Capacitor(capacitance=1.0)   # was 10.0
        self._xin_gate = MOSFET(v_threshold=0.1, gm=0.5)    # Vth=0.1: only meaningful Xin
        # Fix-2: Clamp integrator to prevent DA saturation.
        # Same Zener architecture as Ca clamp (RULE S0).
        # When V > 1.0, MOSFET drains excess charge.
        self._xin_clamp = MOSFET(v_threshold=1.0, gm=5.0)

        # S0-A5: Sync gate MOSFET (binding → Col→Motor learning gate)
        # Binding activation as gate voltage → MOSFET conducts → gate opens
        # BIO: cross-modal co-activation required for motor learning
        self._sync_gate = MOSFET(v_threshold=0.1, gm=1.0)

        # S0-A3: Thermal coupling MOSFETs (inter-layer heat conductance)
        # MOSFET with v_threshold=0: always-on conductor, I = gm * V_diff
        # gm = κ (thermal diffusivity). Radiative loss = separate leak.
        self._thermal_coupler_ve = MOSFET(v_threshold=0.0, gm=0.01)  # vest↔enc
        self._thermal_coupler_ec = MOSFET(v_threshold=0.0, gm=0.01)  # enc↔col
        self._thermal_loss = MOSFET(v_threshold=0.0, gm=0.001)  # radiative

        # A3 FIX: Finite propagation delay + penetration threshold
        # BIO: thermal diffusivity in brain ≈ 0.14 mm²/s (Elwassif 2006).
        # For 0.5mm inter-layer spacing: delay ≈ d²/(2α) ≈ 0.9s ≈ 900 ticks.
        # Use 100 ticks (100ms) as practical delay (layers are adjacent).
        # Penetration threshold: ΔT < 0.001 doesn't conduct (skin depth).
        self._thermal_delay_ve = _ThermalDelayBuffer(delay_steps=100)
        self._thermal_delay_ec = _ThermalDelayBuffer(delay_steps=100)
        self._thermal_penetration_min = 0.001  # min ΔT to conduct

        # S0-A4: Impedance matching MOSFET divider
        # Two MOSFETs: body impedance + medium impedance
        # Signal attenuation = gm_body / (gm_body + gm_medium)
        # gm tracks Z = sqrt(k*m); updated each step
        self._impedance_body = MOSFET(v_threshold=0.0, gm=1.0)
        self._impedance_medium = MOSFET(v_threshold=0.0, gm=1.0)

        # ── P0: Efference copy — predict acc from motor output ──
        # BIO: cerebellum forward model. If motor fires but body doesn't
        # respond (corner-stall, wall), suppress mitosis on that axis.
        self._efference_gain = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self._motor_efficacy = {'x': 1.0, 'y': 1.0, 'z': 1.0}

        # ── Patch E: Efference Copy suppression ratio monitoring (INFRA) ──
        # Tracks fraction of Binding events suppressed by low motor efficacy.
        # Alert threshold: R_supp >= 0.9 (critation doc §五).
        self._efference_supp_count: int = 0
        self._efference_total_count: int = 0
        self._efference_supp_ratio: float = 0.0
        self._efference_monitor_window: int = 10000  # steps per reporting window
        self._efficacy_suppress_threshold: float = 0.1  # efficacy < 0.1 = motor ineffective

        # ── Middle decision layer (placeholder) ──
        # Sits between Col (motion state) and Motor (muscle commands).
        # Currently passthrough — all three sub-systems are stubs.
        self.motor_decision = MotorDecisionLayer()
        # Exposed motion state for external inspection
        self.motion_state = MotionState()

        # ── DA neuron pool (structural VTA circuit) ──
        # Replaces hardcoded Neuromodulator.release() with real neurons.
        # DA neurons receive input via SynapticBundles (shadow→DA, xin→DA).
        # Their activation IS the DA concentration (volumetric broadcast).
        # BIO: VTA contains ~15k DA neurons; we use 3 (one per motor axis).
        self.da_neurons: Dict[str, Neuron] = {}
        for i in range(3):
            nid = f"da_vta_{i}"
            cfg = NeuronConfig(
                neuron_id=nid,
                # τ = C*R = 2.0*1.0 = 2s (matches original DA τ_decay=2.0)
                capacitance=2.0,
                r_leak=1.0,
                v_rest=0.0,
                channels=[ChannelConfig(name="default", v_threshold=0.01, gm=1.0)],
                # gm=1.0: non-spiking continuous DA neuron; unit gain maps V→activation linearly.
                # gm=8.0 caused saturation at V>0.135V (too sensitive for tonic mode).
                # With gm=1.0: concentration = max(0, V-0.01); saturates only at V>1.01.
                # BIO: VTA DA neurons fire tonically at 1-5Hz; graded output mode (Grace & Onn 1989)
                # bc_current produces baseline activation ≈ 0.1
                # V_ss = bc * R = 0.1 * 1.0 = 0.1 → concentration = 0.09 (tonic ~9%)
                use_bias_current=True,
                bc_current=0.1,
                energy=10.0,
                spiking=False,
                # maturation_stage=0 (spine): full plasticity on input bundles
                maturation_stage=0,
                trace_tau_pre=20.0,
                trace_tau_post=20.0,
                # VoltageRegulator: generic metabolic homeostasis (kept).
                use_voltage_regulator=True,
                vr_base_rate=0.5,
                vr_activity_coeff=1.0,
                vr_max_rate=5.0,
                # ── DIFFERENTIATION: D2 Autoreceptor (J) ──
                # Only DA neurons have D2R. This is the DA-specific
                # negative feedback that prevents saturation.
                # VR provides generic metabolic recovery.
                # D2R provides DA-specific activity dampening.
                # Both work together: VR sustains energy, D2R limits firing.
                # BIO: VTA DA neurons express D2R on soma/dendrites
                # → GIRK K⁺ current → hyperpolarization → reduced DA release.
                # REF: Lacey et al. 1987; Ford 2014
                use_d2_autoreceptor=True,
                d2_conductance=0.5,     # GIRK conductance
                d2_ec50=0.3,            # D2R activates at [DA] > 0.3
                d2_da_capacitance=1.0,  # local [DA] integrator
                d2_da_r_leak=1.0,       # τ_D2 = 1s (1000 steps); reaches SS within 10k probe window.
                # Original 100.0 (τ=100s) was too slow — D2R only built up 9.5% at 10k steps.
                # BIO: D2R desensitization kinetics 200-500ms (Beckstead 2004); 1.0s = 2× biological ✓
                # Stability: τ_D2=1s vs τ_membrane=2s; close ratio enables fast self-regulation.
            )
            self.da_neurons[nid] = Neuron(cfg)

        # Xin relay neuron: mirrors Xin integrator voltage into a real Neuron
        # so it can connect to DA neurons via a proper SynapticBundle.
        # BIO: pontine relay neuron → VTA (phasic prediction error)
        self._xin_relay = Neuron(NeuronConfig(
            neuron_id="xin_relay",
            capacitance=0.5,    # fast τ = 0.5*1 = 0.5s (phasic)
            r_leak=1.0,
            v_rest=0.0,
            channels=[ChannelConfig(name="default", v_threshold=0.01, gm=1.0)],
            spiking=False,
            energy=10.0,
        ))

        # DA bundles initialized lazily (shadow layer not ready yet)
        self._da_circuit_initialized = False
        self.bundles_shadow_to_da: List[SynapticBundle] = []
        self.bundles_xin_to_da: List[SynapticBundle] = []
        # BIO: spinal lamina I → parabrachial nucleus → VTA (Dayan & Abbott 2001)
        # Somatosensory relay → DA: STDP-enabled directional reinforcement path.
        # Exposed as bundles_soma_to_da for backward compat with Phase 5-8 scripts.
        # P1-DIFF: relay neurons (lamina V WDR) are NOT direct sources for DA.
        # Intermediate lamina I spinoparabrachial projection neurons (母本分化)
        # receive from relay and provide Zener-bounded calcium_rate to DA bundles.
        self._soma_proj: Dict[str, Neuron] = {}          # lamina I proj neurons (4 patches)
        self._bundles_relay_to_proj: List[SynapticBundle] = []  # relay → proj (frozen)
        self.bundles_relay_to_da: List[SynapticBundle] = []

        # P0-B: Relay-layer lateral inhibition (Winner-Take-All)
        # BIO: retinal horizontal cells / olfactory bulb granule cells antagonistic surround.
        # REF: Hartline & Ratliff 1957 J Gen Physiol — lateral inhibition in Limulus.
        # Frozen cross-inhibition: prevents simultaneous LTP on all relay_to_da pathways.
        self.bundles_relay_lateral_inh: List[SynapticBundle] = []

        # CPG → DA oscillator (lazy init alongside DA circuit)
        # BIO: VTA pacemaker interneuron → 2 Hz rhythmic drive to DA neurons
        # Keeps DA.post_trace > 0 at steady state → relay_to_da STDP stays active.
        self._da_cpg: CPGNeuron | None = None
        self.bundles_cpg_to_da: List[SynapticBundle] = []

        # Warm-onset → DA: ThermalDeltaNeuron per patch (lazy init alongside DA)
        # BIO: Type II AMH (Aδ) → LPB → VTA warm-onset DA burst.
        # REF: Norris et al. 2021 Nat Neurosci — LPB→VTA thermal reward pathway.
        self.thermo_delta_neurons: Dict[str, 'ThermalDeltaNeuron'] = {}
        self.bundles_thermo_delta_to_da: List[SynapticBundle] = []

        # HC-016 A: Yaw turn reflex via relay→yaw motor neurons (SynapticBundle)
        # BIO: crossed spinal thermotaxis reflex — left-side heat → contralateral
        #      motor interneurons → CCW turn toward heat.
        # REF: Mori & Ohshima 1995 Nature 376:344 (C. elegans AFD→AIY→SMB circuit).
        # SEMI: MOSFET threshold; two neurons compete (push-pull) via yaw_torque diff.
        # Q1. BIO: crossed thermosensory interneuron (relay → contralateral yaw motor)
        # Q2. thermo_inputs['left'] → [frozen] → yaw_ccw; thermo_inputs['right'] → [frozen] → yaw_cw
        # Q3. w=0.3: relay.act≈0.4@T=8 → G(0.3)×1.0×0.4≈0.056A → V_ss≈0.28 → act≈0.28
        self.yaw_ccw_neuron: Neuron = Neuron(NeuronConfig(
            neuron_id="yaw_ccw",
            channels=[ChannelConfig(name="default", v_threshold=0.01, gm=1.0)],
            spiking=False,
        ))
        self.yaw_cw_neuron: Neuron = Neuron(NeuronConfig(
            neuron_id="yaw_cw",
            channels=[ChannelConfig(name="default", v_threshold=0.01, gm=1.0)],
            spiking=False,
        ))
        self.bundle_left_to_yaw: SynapticBundle | None = None
        self.bundle_right_to_yaw: SynapticBundle | None = None
        self._init_yaw_bundles()

        # D1: Phasic relay → spinal_turn_toward STDP arc (thermal direction learning)
        # Q1. BIO: SA2 slow-adapting input subtraction → dorsal-horn WDR phasic output.
        #     slow_relay tracks DC baseline; phasic = relay − slow = rate-of-change.
        #     spinal_turn_toward: spinal interneuron that learns to gate yaw drive when
        #     phasic signal (approach) coincides with DA reward.
        #     REF: Collins et al. 1997 J Neurophysiol 78:88 (phasic/tonic WDR dissociation)
        #     REF: Sherrington 1910 J Physiol 40:28 (spinal reflex interneuron arc)
        # Q2. relay_left → slow_relay_left (frozen, g=1.0, w=1/R_slow)
        #     relay_left → phasic_left (frozen, g=+1.0, w=W_P) [excit]
        #     slow_relay_left → phasic_left (frozen, g=−1.0, w=W_P) [inhib → KCL subtraction]
        #     phasic_left → spinal_ccw (STDP, DA-gated, eligibility trace)
        #     spinal_ccw → yaw_ccw_neuron (frozen, w=0.5)
        #     (mirror structure for right/cw side)
        # Q3. slow_relay: R=5000 → τ=5000 steps≈5s. SA2 τ∈[2,10]s (Johansson 2004).
        #     W_RELAY_TO_SLOW=1/R_slow=0.0002: V_ss_slow=relay.act×W×R_slow=relay.act ✓
        #     W_PHASIC=0.02: at Δ=0.05 → I_net=0.001 → V_phasic=0.1 → act=10×0.1=1.0 ✓
        #     D1 STDP: init_w=0.1, w_max=0.3, stdp_lr=0.005 (Bi & Poo 1998 Neuron).
        #     spinal_out: w=0.5 (conservative; D1 grows from 0.1 to 0.3 over 200k).
        _W_RS = 1.0 / 5000.0   # relay→slow weight: V_ss_slow ≈ relay.act
        _W_P  = 0.02            # relay→phasic weight; at Δ=0.05 → phasic.act≈1.0

        self.slow_relay_left = Neuron(NeuronConfig(
            neuron_id='slow_relay_left', capacitance=1.0, r_leak=5000.0, region=0x03,
            spiking=False, channels=[ChannelConfig(name='slow_l', v_threshold=0.0001, gm=1.0)]))
        self.slow_relay_right = Neuron(NeuronConfig(
            neuron_id='slow_relay_right', capacitance=1.0, r_leak=5000.0, region=0x03,
            spiking=False, channels=[ChannelConfig(name='slow_r', v_threshold=0.0001, gm=1.0)]))
        self.phasic_left = Neuron(NeuronConfig(
            neuron_id='phasic_left', capacitance=0.5, r_leak=100.0, region=0x03,
            spiking=False, channels=[ChannelConfig(name='phasic_l', v_threshold=0.0001, gm=10.0)]))
        self.phasic_right = Neuron(NeuronConfig(
            neuron_id='phasic_right', capacitance=0.5, r_leak=100.0, region=0x03,
            spiking=False, channels=[ChannelConfig(name='phasic_r', v_threshold=0.0001, gm=10.0)]))
        self.spinal_ccw = Neuron(NeuronConfig(
            neuron_id='spinal_ccw', capacitance=1.0, r_leak=5.0, region=0x01,
            spiking=False, channels=[ChannelConfig(name='spinal_ccw', v_threshold=0.01, gm=1.0)]))
        self.spinal_cw = Neuron(NeuronConfig(
            neuron_id='spinal_cw', capacitance=1.0, r_leak=5.0, region=0x01,
            spiking=False, channels=[ChannelConfig(name='spinal_cw', v_threshold=0.01, gm=1.0)]))

        _rl = self.somatosensory.relays.get('left')
        _rr = self.somatosensory.relays.get('right')
        _frozen_cfg = lambda bid, w, sg: BundleConfig(
            bundle_id=bid, learning_rule='frozen',
            initial_weight=w, weight_max=w, synapse_gain=sg,
            bundle_role='feedforward', remodel_cost_kappa=0.0)

        self.bundle_relay_to_slow_left = (
            SynapticBundle(_frozen_cfg('relay_left_to_slow', _W_RS, 1.0), [_rl], [self.slow_relay_left])
            if _rl else None)
        self.bundle_relay_to_slow_right = (
            SynapticBundle(_frozen_cfg('relay_right_to_slow', _W_RS, 1.0), [_rr], [self.slow_relay_right])
            if _rr else None)
        self.bundle_relay_to_phasic_left = (
            SynapticBundle(_frozen_cfg('relay_left_to_phasic', _W_P, 1.0), [_rl], [self.phasic_left])
            if _rl else None)
        self.bundle_slow_to_phasic_left = SynapticBundle(
            _frozen_cfg('slow_left_to_phasic', _W_P, -1.0), [self.slow_relay_left], [self.phasic_left])
        self.bundle_relay_to_phasic_right = (
            SynapticBundle(_frozen_cfg('relay_right_to_phasic', _W_P, 1.0), [_rr], [self.phasic_right])
            if _rr else None)
        self.bundle_slow_to_phasic_right = SynapticBundle(
            _frozen_cfg('slow_right_to_phasic', _W_P, -1.0), [self.slow_relay_right], [self.phasic_right])

        _stdp_d1_cfg = lambda bid, src, tgt: SynapticBundle(BundleConfig(
            bundle_id=bid, learning_rule='stdp',
            initial_weight=0.1, weight_max=0.3, stdp_lr=0.005,
            synapse_gain=1.0, bundle_role='feedforward', remodel_cost_kappa=0.0,
            use_eligibility_trace=True), [src], [tgt])
        self.bundle_d1_phasic_left_to_spinal_ccw = _stdp_d1_cfg(
            'd1_phasic_left_to_spinal_ccw', self.phasic_left, self.spinal_ccw)
        self.bundle_d1_phasic_right_to_spinal_cw = _stdp_d1_cfg(
            'd1_phasic_right_to_spinal_cw', self.phasic_right, self.spinal_cw)

        # w=0.002: slow_relay warmup (τ=5000 steps) creates spurious phasic activation
        # 6× HC-016 torque at w=0.5, disrupting col→motor STDP. Directional learning
        # lives in phasic→spinal STDP; output relay weight set small until STDP matures.
        # EXP: T4.1 regression analysis 2026-07-04; tune upward after 200k D1 validation.
        self.bundle_spinal_ccw_to_yaw = SynapticBundle(
            _frozen_cfg('spinal_ccw_to_yaw', 0.002, 1.0), [self.spinal_ccw], [self.yaw_ccw_neuron])
        self.bundle_spinal_cw_to_yaw = SynapticBundle(
            _frozen_cfg('spinal_cw_to_yaw', 0.002, 1.0), [self.spinal_cw], [self.yaw_cw_neuron])

        # 接口三：接近→制动束（thermo_front → motor_move_x，抑制性反射弧）
        # Q1. BIO: 脊髓热防御制动反射 — TRPV1/A1 热感受器激活 → Aδ/C 热觉传入
        #     → 脊髓腹角运动神经元抑制，body 正面接近热源时自动减速防止冲过。
        #     REF: Caterina & Julius 2001 Annu Rev Neurosci 24:487; Haidarliu 2008.
        # Q2. thermo_inputs['front'] → [frozen, sg=g_brake=-0.5] → motor_neurons['move_x']
        # Q3. w=0.3: T_front≈4 → thermo_act≈0.3 → G(0.3)×(-0.5)=-0.021A 抑制电流
        #     g_brake=-0.5 [A/°C]: EXP-HC016-003 校准（不完全抑制，允许慢速接近）
        self.bundle_front_to_brake: SynapticBundle | None = None
        self._init_brake_bundle()

        # 接口二：能量感知链 — EnergyStore Capacitor → ARC → LH → DA
        # BIO: ARC nucleus K_ATP channel neurons → lateral hypothalamus → VTA
        # REF: Spanswick 1997 Nature 390:521; Wise 2004 Nat Rev Neurosci 5:483.
        # Q1: ARC K_ATP → LH整合 → VTA饥饿tonic DA（替代 _hunger_da HC）
        # Q2: EnergyStore.fill_fraction → sensor×3 → average → hunger → da_neurons
        # Q3: G_E=1.0, w_s2a=0.1, w_a2h=0.1, w_h2d=0.04（等效原_hunger_da贡献）
        self._G_ENERGY_SENSE: float = 1.0
        self.energy_sensors: List[Neuron] = []
        self.average_energy_neuron: Neuron | None = None
        self.hypothalamus_hunger: Neuron | None = None
        self.bundle_sensors_to_average: SynapticBundle | None = None
        self.bundle_average_to_hunger: SynapticBundle | None = None
        self.bundle_hunger_to_da: SynapticBundle | None = None
        self._init_energy_sensing()

        # 接口一：Motor 传出副本（efference copy）→ hypothalamus_effort
        # Q1. BIO: 脊髓前角运动神经元轴突侧枝 → 脑干 → 下丘脑 effort signal
        #     体现 corollary discharge（传出副本）原理：运动指令同时上报下丘脑。
        #     REF: Helmholtz 1867; von Holst & Mittelstaedt 1950 Naturwissenschaften 37:464;
        #          Wolpert & Kawato 1998 Trends Cogn Sci 2:338.
        # Q2. motor_neurons['move_x'] → [frozen, g_efference=0.1] → hypothalamus_effort
        # Q3. w=0.1: motor.act≈0.5（运动时）→ I_effort=0.05A → V=0.25V → act≈0.24（act阈值0.01）
        self.hypothalamus_effort: Neuron | None = None
        self.bundle_motor_to_effort: SynapticBundle | None = None
        self._init_efference_bundle()

        # P2-HC007: relay→enc STDP bundles (replace HC-007 direct injection)
        # BIO: STT → VPL thalamus → S1 cortex (thalamo-cortical thermal encoding)
        # encoding_neurons (from super().__init__) and somatosensory.relays both ready now.
        self.bundles_relay_to_enc: List[SynapticBundle] = []
        self._init_relay_to_enc()

        # ── World 2.0: Cylindrical heat source + thermal mouth ──
        # BIO: hydrothermal vent (Kelley et al. 2002) + chemosynthetic feeding.
        # DESIGN: Single cylindrical source at Z=25 (body Z-plane, Phase 1 lock).
        # Objection fix: center Z=25 (not 50) so within_height check always fires.
        self._cylindrical_source = CylindricalHeatSource(
            center=[50.0, 50.0, 25.0],  # Z=25: same plane as body (Phase 1)
            radius=6.0, height=16.0,
            T_surface=5.0, T_ambient=0.15, sigma=25.0,
            energy=1000.0, regeneration_rate=0.002,
        )
        self.world.cylindrical_sources = [self._cylindrical_source]
        self.thermal_mouth = ThermalMouth()
        # BIO: ATP synthase analogue — converts raw thermal intake to EnergyStore charge.
        # REF: Mitchell 1961 chemiosmotic theory (Nature 191:144-148).
        # PHYS: g_digest=1.0 [dimensionless]; ThermalMouth.eta already models thermodynamic loss.
        self.digestive_interface = DigestiveInterface()

        # ── FeedRateCapacitor: DigestiveInterface deposit_rate → V_feed [V] ──
        # 脆弱点3修正：将进食信号换源为 DigestiveInterface.tick() 的实际 deposit rate。
        # 原 feed_alignment = patch 温差（max-min）在热源中心归零，破坏 CPC 进食环流信号。
        # Q1. BIO: 胃肠道缓慢积分摄入功率，对应"饱腹感"tonic 信号（分钟尺度建立）。
        # Q2. DigestiveInterface.tick() → I_feed = deposit_rate/dt → Capacitor(C=1,R=5) → v_feed
        # Q3. deposit_rate≈2e-4（进食时ΔT≈5°C）→ I_feed=0.2A → V_ss=0.2×5=1.0V（tonic满载）
        #     τ=C×R/dt=1×5/0.001=5000步（5s，平滑phasic噪声）
        #     REF: 三核心脆弱点修正方案 §脆弱点3（2026-07-04）
        self._feed_rate_cap = Capacitor(capacitance=1.0)
        self._R_FEED: float = 5.0
        self._v_feed: float = 0.0   # current V_feed voltage (exposed for monitoring)

        # ── Region assignment: tag all neurons with brain region codes ──
        # Must be called AFTER all _init_* methods complete (neurons fully created).
        self._assign_regions()

    def _assign_regions(self):
        """Assign brain region codes to all neurons based on functional identity.

        TYPE:INFRA — Pure metadata, zero effect on computation.

        Region mapping (source: 《整合最终版v2.0》§1.1):
          0x01 SPINAL:       spinal reflex layer (Renshaw, brake interneurons)
          0x02 BRAINSTEM:    vestibular transducers + encoding (MET/HC/Aff/Enc-vest)
          0x03 MAIN:         column, motor, DA, somatosensory, yaw neurons
          0x04 HYPOTHALAMUS: energy sensing chain (ARC→VMH→LH)
          0x05 SHADOW:       shadow sandbox (microcircuit-attached to 0x03)
        """
        _VESTIBULAR_AXES = {'yaw', 'pitch', 'roll', 'oto_x', 'oto_y', 'oto_z'}
        _VEST_BRAINSTEM_PREFIXES = ('met_', 'hc_', 'aff_reg_', 'aff_irr_')

        _HYPOTHALAMUS_IDS = {
            'energy_sensor_0', 'energy_sensor_1', 'energy_sensor_2',
            'average_energy', 'hypothalamus_hunger', 'hypothalamus_effort',
        }

        # 0x01 SPINAL: brake/Renshaw interneurons (Phase B will add more)
        _SPINAL_IDS = {'spinal_renshaw_interneuron', 'motor_brake_interneuron'}

        for n in self.get_all_neurons():
            nid = n.id

            # 0x01 SPINAL
            if nid in _SPINAL_IDS or nid.startswith('spinal_'):
                n.config.region = REGION_SPINAL

            # 0x02 BRAINSTEM: vestibular transducers (met/hc/aff) + vestibular encoding
            elif any(nid.startswith(p) for p in _VEST_BRAINSTEM_PREFIXES):
                n.config.region = REGION_BRAINSTEM
            elif nid.startswith(('enc_reg_', 'enc_irr_')):
                # Extract axis: enc_reg_yaw → axis = yaw
                axis = '_'.join(nid.split('_')[2:])
                if axis in _VESTIBULAR_AXES:
                    n.config.region = REGION_BRAINSTEM
                else:
                    n.config.region = REGION_MAIN

            # 0x04 HYPOTHALAMUS
            elif nid in _HYPOTHALAMUS_IDS:
                n.config.region = REGION_HYPOTHALAMUS

            # 0x05 SHADOW: s_enc, s_col, s_mot prefixes
            elif nid.startswith(('s_enc_', 's_col_', 's_mot_', 'shadow_')):
                n.config.region = REGION_SHADOW

            # 0x03 MAIN: everything else (col, motor, DA, somatosensory, yaw, etc.)
            else:
                n.config.region = REGION_MAIN

    def step(self, mechanical_inputs: Dict[str, float], dt: float = 1.0):
        """Process one time step: mother + variant overlay.

        Pipeline:
          0. Motor(prev) → Muscle → Body movement → Thermal sensing
          1. Oscillator modulation
          2. Mother step (vestibular + encoding + column + motor)
          3. Post-hoc variant effects
        """
        # ── Phase 0: Entropy ledger pre-step guard ──
        # Runs BEFORE all computation. Checks conservation invariants
        # from the PREVIOUS step and gates structural modifications.
        if not hasattr(self, '_maturation_tick'):
            self._maturation_tick = 0
        self._ledger_pre_step(self._maturation_tick, dt)

        # ── 0. Body integration: Motor → Muscle → Movement → Sensing ──
        # Motor output from PREVIOUS step drives movement THIS step
        # Aggregate motor activations per axis (mitosis may add child neurons)
        # Original motors: move_x, move_y, move_z
        # Children: move_x_m230000, etc. → still contribute to their parent axis
        axis_individual = {'x': [], 'y': [], 'z': []}
        for key, mot in self.motor_neurons.items():
            # M4 fix: use firing rate (EMA), not spike binary {0,1}
            # Muscle force ∝ motor neuron firing rate (Henneman principle)
            if 'move_x' in key:
                axis_individual['x'].append(mot._activation_ema)
            elif 'move_y' in key:
                axis_individual['y'].append(mot._activation_ema)
            elif 'move_z' in key:
                axis_individual['z'].append(mot._activation_ema)

        # C2: Lateral inhibition (Renshaw cells) — break clone symmetry
        for axis_key in axis_individual:
            axis_individual[axis_key] = self.motor_decision.lateral.compete(
                axis_individual[axis_key])

        # Aggregate inhibited activations per axis
        axis_acts = [
            sum(axis_individual['x']),
            sum(axis_individual['y']),
            sum(axis_individual['z']),
        ]

        # B1b: Cross-axis motor lateral inhibition is now handled by Renshaw
        # interneurons in _propagate_bundles() (after Col→Motor propagation).
        # See bundles_renshaw_excit / bundles_renshaw_inhib.

        # ── Extract MotionState from previous step's processing ──
        # This is the OUTPUT of the motion state discrimination structure.
        # Three measures: motion_potential, temporal, spatial.
        ms = self.motion_state
        # Motion potential: overall motion intensity
        ms.motion_potential = sum(
            abs(self.column_neurons[ax].activation)
            for ax in self.vestibular.axes
        )
        # Temporal measure: irregular afferent rates (AC component)
        for ax in self.vestibular.axes:
            irr_key = f'irr_{ax}'
            if irr_key in self.encoding_neurons:
                ms.temporal_measure[ax] = self.encoding_neurons[irr_key]._activation_ema
        # Spatial measure: regular afferent rates (DC component)
        for ax in self.vestibular.axes:
            reg_key = f'reg_{ax}'
            if reg_key in self.encoding_neurons:
                ms.spatial_measure[ax] = self.encoding_neurons[reg_key]._activation_ema
        # Otolith: body acceleration
        ms.otolith_acc = {
            'x': self.world.body.acceleration[0],
            'y': self.world.body.acceleration[1],
            'z': self.world.body.acceleration[2],
        }
        ms.body_speed = self.world.body.speed()
        # Thermal
        if hasattr(self, 'thermal_membrane') and self.thermal_membrane._initialized:
            ms.thermal = self.thermal_membrane._prev_T - self.thermal_membrane._methylation

        # ── Middle decision layer: Col raw acts → decided acts ──
        # Currently passthrough; future: CPG + direction + navigation
        motor_acts = self.motor_decision.process(
            axis_acts, self.motion_state,
            da=self.dopamine.concentration, dt=dt
        )

        # A4: kinetic damping — body speed attenuates muscle force
        # BIO: Golgi tendon organ feedback + viscous drag in fluid
        kd = self.world.body.kinetic_damping()
        forces_raw = self.muscle_system.contract_all(motor_acts)
        forces_body = [f * kd for f in forces_raw]

        # HC-016 B: rotate body-frame muscle forces to world frame via current yaw.
        # PHYS: muscles contract along body axes; rigid-body orientation (yaw) maps
        # body frame to world frame. Without this, move_x always pushes world +x
        # regardless of body heading, breaking the yaw→forward locomotion coupling.
        # BIO: efference copy + proprioception implicitly encode body frame (no new
        # neurons needed — this is pure coordinate transform, not a signal path).
        _cy = math.cos(self.world.body.yaw)
        _sy = math.sin(self.world.body.yaw)
        forces_world = [
            forces_body[0] * _cy - forces_body[1] * _sy,
            forces_body[0] * _sy + forces_body[1] * _cy,
            forces_body[2],
        ]
        self.world.body.step(forces_world, dt)

        # ── A7: Motor potential ν = dK/dt ──
        # Kinetic energy after body physics step
        vel = self.world.body.velocity
        mass = self.world.body.mass
        k_new = 0.5 * mass * sum(v*v for v in vel)
        k_prev = ms.kinetic_energy  # from previous step
        ms.kinetic_energy = k_new
        nu_raw = (k_new - k_prev) / max(dt, 1e-10)
        # EMA smoothing: α=0.01 (~100-step window)
        # FFT verified: raw ν is broadband noise; EMA recovers input freq.
        NU_ALPHA = 0.01
        ms.motor_potential += NU_ALPHA * (nu_raw - ms.motor_potential)
        # Per-axis components: ν_i = m × v_i × a_i, also EMA-smoothed
        acc = self.world.body.acceleration
        for i in range(3):
            nu_i_raw = mass * vel[i] * acc[i]
            ms.motor_potential_xyz[i] += NU_ALPHA * (nu_i_raw - ms.motor_potential_xyz[i])
        # Polarization: P = max(|ν_i|) / Σ|ν_i| (from smoothed values)
        abs_nu = [abs(n) for n in ms.motor_potential_xyz]
        sum_abs = sum(abs_nu)
        if sum_abs > 1e-12:
            ms.polarization = max(abs_nu) / sum_abs
        else:
            ms.polarization = 0.333  # undefined → isotropic

        # ── P0: Efference copy update ──
        # Compare predicted acceleration (from motor acts) with actual.
        # If mismatch is low for sustained period → motor is ineffective.
        for i, axis in enumerate(['x', 'y', 'z']):
            predicted_acc = motor_acts[i] * self._efference_gain[axis]
            actual_acc = self.world.body.acceleration[i]
            error = actual_acc - predicted_acc
            # Slow learning of forward model
            self._efference_gain[axis] += 0.001 * error
            # Efficacy: does motor output produce movement?
            mismatch = abs(error)
            if motor_acts[i] > 0.01 and mismatch < 0.001:
                # Motor firing but no effect → decay efficacy
                self._motor_efficacy[axis] = max(0.0,
                    self._motor_efficacy[axis] - 0.0001)
            else:
                # Motor is effective → restore efficacy
                self._motor_efficacy[axis] = min(1.0,
                    self._motor_efficacy[axis] + 0.001)

        # Thermal membrane senses environment at new body position
        # (legacy single-point sensor kept for backward compatibility)
        therm_signal = self.thermal_membrane.sense(
            self.world, self.world.body, dt)

        # ── Somatosensory chain: 4-patch spatial temperature sensing ──
        # 1. Sample skin patches at body surface positions
        patch_temps = self.world.body.sample_skin(self.world, dt)
        self._patch_temps = patch_temps  # exposed for DR5 metric in experiment scripts

        # ── Relay lateral inhibition pre-inject (P0-B: Winner-Take-All) ──
        # Inject inhibitory currents from previous step into competing relay membranes
        # BEFORE somatosensory.step() — relay.step() then starts from suppressed voltage.
        # 1-step delay is standard in discrete-time recurrent networks; synaptic delay
        # ≈ 1ms matches DT=0.001 s (BIO: spinal interneuron conduction, Brown & Franz 1969).
        # Current path: bundle.propagate() → Capacitor.inject() (not semantic HC).
        if self.bundles_relay_lateral_inh:
            _lat_acc: dict = {}
            for _bundle in self.bundles_relay_lateral_inh:
                _currents = _bundle.propagate()
                for _j, _tgt in enumerate(_bundle.targets):
                    if _j < len(_currents):
                        _lat_acc[_tgt.id] = _lat_acc.get(_tgt.id, 0.0) + _currents[_j]
            for _pid, _I in _lat_acc.items():
                _relay = self.somatosensory.relays.get(_pid.replace('relay_', ''))
                if _relay is not None and abs(_I) > 1e-12:
                    _relay._membrane.inject(_I, dt)

        # 2. Step the somatosensory chain (Thermo + Noci + Relay)
        self.somatosensory.step(patch_temps, dt)

        # ── Warm-onset transducers: step ThermalDeltaNeurons from dT per patch ──
        # BIO: Type II AMH (Aδ) fire on positive dT/dt (body entering warm field).
        # Lazy: neurons exist only after _init_da_circuit() (first call triggers it).
        if self.thermo_delta_neurons:
            for pid, dn in self.thermo_delta_neurons.items():
                dT_raw = patch_temps.get(pid, (0.0, 0.0, 0.0))[1]
                dn.step(dT_raw, dt)

        # ── D1: Phasic relay computation ──
        # slow_relay tracks DC relay with τ≈5000 (SA2 adaptation baseline).
        # phasic = relay − slow_relay = rate-of-change (fires only when temp increasing).
        # TIMING: after somatosensory.step() (relay states current); before HC-016 A yaw.
        if self.bundle_relay_to_slow_left is not None:
            _sl = self.bundle_relay_to_slow_left.propagate()
            self.slow_relay_left.step(_sl[0] if _sl else 0.0, dt)
        if self.bundle_relay_to_slow_right is not None:
            _sr = self.bundle_relay_to_slow_right.propagate()
            self.slow_relay_right.step(_sr[0] if _sr else 0.0, dt)

        _i_pl = 0.0
        if self.bundle_relay_to_phasic_left is not None:
            _rpl = self.bundle_relay_to_phasic_left.propagate()
            _i_pl += _rpl[0] if _rpl else 0.0
        _spl = self.bundle_slow_to_phasic_left.propagate()
        _i_pl += _spl[0] if _spl else 0.0
        self.phasic_left.step(_i_pl, dt)

        _i_pr = 0.0
        if self.bundle_relay_to_phasic_right is not None:
            _rpr = self.bundle_relay_to_phasic_right.propagate()
            _i_pr += _rpr[0] if _rpr else 0.0
        _spr = self.bundle_slow_to_phasic_right.propagate()
        _i_pr += _spr[0] if _spr else 0.0
        self.phasic_right.step(_i_pr, dt)

        # Spinal turn interneurons: D1 STDP forward pass (pre_trace already updated above)
        _d1_ccw = self.bundle_d1_phasic_left_to_spinal_ccw.propagate()
        self.spinal_ccw.step(_d1_ccw[0] if _d1_ccw else 0.0, dt)
        _d1_cw = self.bundle_d1_phasic_right_to_spinal_cw.propagate()
        self.spinal_cw.step(_d1_cw[0] if _d1_cw else 0.0, dt)

        # ── P2-HC007: relay→enc STDP bundle propagation ──
        # Replaces: enc_reg.step(relay.activation * EXTRA_AXIS_GAIN, dt) (direct injection)
        # With: bundle current fed through mechanical_inputs → HebbianCircuit injects it.
        # Net injection identical to HC-007 at w=0; STDP grows w → stronger therm encoding.
        # TIMING: after somatosensory.step() (relay.pre_trace updated) and
        #         before super().step() (enc_reg.post_trace not yet updated — bundle.learn
        #         is called after super(), so traces are ordered correctly).
        _HC007_GAIN = 0.04  # must match EXTRA_AXIS_GAIN in HebbianCircuit
        _relay_enc_override: dict = {}
        for bundle in self.bundles_relay_to_enc:
            currents = bundle.propagate()
            for j, tgt in enumerate(bundle.targets):
                if j < len(currents):
                    # tgt.id = "reg_therm_{pid}"; extract pid
                    pid = tgt.id[len("reg_therm_"):]
                    # HebbianCircuit does: enc_reg.step(tonic_val * 0.04, dt)
                    # so tonic_val = bundle_current / 0.04 → injected = bundle_current ✓
                    _relay_enc_override[f"therm_{pid}"] = currents[j] / _HC007_GAIN

        # 3. Inject relay outputs into mechanical_inputs for extra_axes
        #    tonic therm axes: use bundle-driven value (HC-007 fix), others pass through
        mechanical_inputs = dict(mechanical_inputs)  # don't mutate caller's dict
        soma_out = self.somatosensory.get_mechanical_inputs(dt)
        for key, val in soma_out.items():
            mechanical_inputs[key] = _relay_enc_override.get(key, val)

        # ── 0b. Closed sensorimotor loop: body acceleration → vestibular ──
        # BIO: otolith organs measure linear acceleration (utricle, saccule).
        # This is a physical measurement, not a mathematical injection.
        # Motor → Muscle → Body.step() → acceleration → vestibular input
        # OTOLITH_GAIN scales acceleration to vestibular input range.
        OTOLITH_GAIN = 500.0
        acc = self.world.body.acceleration
        # V8: Langevin thermal noise → vestibular afferent (sensor-side)
        # OU process exact discretization, σ driven by ECM T_bath.
        # Added to body acceleration BEFORE otolith gain scaling.
        eta = self._langevin.step(self.ecm_vestibular, dt)
        # Patch A: de-mean (zero-point purity, highest priority)
        # OU samples have finite-window bias ~1e-6; AGC amplifies 5× at starvation.
        # Over 1M steps this creates deterministic directional bias → breaks emergence.
        # BIO: LC-NE increases variance, not mean (Sara 2009, NRN 10:211-223).
        _eta_mean = sum(eta) / len(eta)
        eta = [x - _eta_mean for x in eta]
        # Patch A: AGC modulates exploration amplitude (LC-NE analogue)
        # AGC.gain ∈ [1.0, 5.0]; previous step's gain used (agc.step() at L836).
        eta = [e * self.agc.gain for e in eta]
        # Patch A: RMS clamp — motor saturation protection
        # At starvation: σ_eff ≈ 0.42; peak may exceed 1.0 → Motor runaway.
        eta = [max(-1.0, min(1.0, e)) for e in eta]
        mechanical_inputs['oto_x'] = mechanical_inputs.get('oto_x', 0.0) + (acc[0] + eta[0]) * OTOLITH_GAIN
        mechanical_inputs['oto_y'] = mechanical_inputs.get('oto_y', 0.0) + (acc[1] + eta[1]) * OTOLITH_GAIN
        mechanical_inputs['oto_z'] = mechanical_inputs.get('oto_z', 0.0) + (acc[2] + eta[2]) * OTOLITH_GAIN
        # ── World 2.0: Phase 1 planar approximation — lock Z axis ──
        # TEMP: remove in Phase 2 (full 3D motion). Z=25 matches cylindrical
        # source center Z, ensuring within_height check always fires.
        # Prevents non-physical vertical ejection when body enters height range.
        self.world.body.position[2] = 25.0
        self.world.body.velocity[2] = 0.0

        # ── HC-016 A: Yaw torque via relay→yaw Bundle (replaces T_left−T_right HC) ──
        # BIO: crossed spinal thermotaxis reflex arc.
        # REF: Mori & Ohshima 1995 Nature 376:344; Fraenkel & Gunn 1940.
        # DESIGN: relay_left active → yaw_ccw fires → CCW torque (turn toward left heat).
        #         relay_right active → yaw_cw fires → CW torque (turn toward right heat).
        #         Net: (yaw_ccw − yaw_cw) × YAW_GAIN; push-pull from structural asymmetry.
        YAW_GAIN = 0.1   # EXP-W2-003 calibrated; same as prior direct formula
        _i_ccw = 0.0
        _i_cw = 0.0
        if self.bundle_left_to_yaw is not None:
            _cur = self.bundle_left_to_yaw.propagate()
            _i_ccw += _cur[0] if _cur else 0.0
        if self.bundle_right_to_yaw is not None:
            _cur = self.bundle_right_to_yaw.propagate()
            _i_cw += _cur[0] if _cur else 0.0
        # D1: add spinal_turn_toward → yaw contribution (KCL, stepped once)
        _sc = self.bundle_spinal_ccw_to_yaw.propagate()
        _i_ccw += _sc[0] if _sc else 0.0
        _sw = self.bundle_spinal_cw_to_yaw.propagate()
        _i_cw += _sw[0] if _sw else 0.0
        self.yaw_ccw_neuron.step(_i_ccw, dt=dt)
        self.yaw_cw_neuron.step(_i_cw, dt=dt)
        _yaw_torque = (self.yaw_ccw_neuron.activation - self.yaw_cw_neuron.activation) * YAW_GAIN
        self.world.body.apply_yaw_torque(_yaw_torque, dt)

        # ── World 2.0: Thermal convective drift (buoyancy advection) ──
        # PHYS: Boussinesq — heated fluid is less dense; cooler fluid flows
        # inward to replace it, creating an advective current toward the source.
        # BIO: Hydrothermal vent archaea are carried by thermal plumes (Kelley 2002).
        # F_conv = k_conv × ∇T applied as Δv; friction damps to v_t = k_conv|∇T|/μ.
        # EXP-W2-004: k_conv=0.5 → terminal v≈0.12 units/step at σ distance;
        # expected drift ~11 units toward cylinder over 100k steps.
        _CONV_K = getattr(self, '_conv_k', 0.5)  # overridable per-instance (EXP: set circuit._conv_k)
        _grad = self.world.gradient_at(self.world.body.position)
        self.world.body.velocity[0] += _CONV_K * _grad[0] * dt
        self.world.body.velocity[1] += _CONV_K * _grad[1] * dt
        # _grad[2] intentionally skipped: Z axis locked in Phase 1

        # ── World 2.0: Cylinder collision detection ──
        for _csrc in self.world.cylindrical_sources:
            if _csrc.alive:
                self.world.body._collide_with_cylinder(_csrc, dt)
        # Regenerate cylindrical sources
        for _csrc in self.world.cylindrical_sources:
            _csrc.step(dt)

        # ── C3': Thermal energy absorption (feeding) ──
        # PHYS: Organism converts environmental thermal flux into metabolic
        # energy — the same temperature field that causes skin damage also
        # provides sustenance. This is NOT a separate "feeding" channel;
        # it IS the thermal interaction, viewed from the energy-intake side.
        #
        # BIO: chemolithoautotrophy at hydrothermal vents. Organisms like
        # Riftia pachyptila harvest energy from the thermal/chemical gradient.
        # The conversion efficiency is a membrane material property.
        #
        # COUPLING: temperature_at() and consume_nearby() share the same
        # (1 - d/r) falloff. By using T_local as the rate, we derive
        # feeding power directly from the physical field:
        #   P_feed = T_local × membrane_efficiency × dt
        # No arbitrary CONSUME_RATE constant needed.
        #
        # THERMODYNAMIC BUDGET (self-calibrated):
        #   T_local at d=5 from source (T_src=5.0): ~3.75
        #   P_feed = 3.75 × 1.0 × 0.001 = 0.00375/step
        #   Metabolic expense (measured): ~0.0033/step (vascular withdraw)
        #   → At d≈5-6, income ≈ expense (equilibrium distance)
        #   → Closer: net gain (but increasing burn risk)
        #   → Further: net deficit → eventual starvation
        T_local = self.world.temperature_at(self.world.body.position)
        energy_absorbed = self.world.consume_nearby(
            self.world.body.position, T_local, dt)
        # Regenerate depleted point sources (deep-sea vent ecology)
        self.world.regenerate_sources()

        # ── Energy pipeline: World → EnergyStore ──
        # Patch C: YolkSac discharges BEFORE deposit/tick, so it primes the
        # store for Δfill detection by DADifferentialGate (DA RPE).
        self.yolk_sac.step(self.energy_store, dt)
        # Consumed energy flows into the external reservoir.
        # Store handles efficiency loss (digestive efficiency ~90%).
        self.energy_store.deposit(energy_absorbed)

        # ── World 2.0: ThermalMouth energy intake ──
        # BIO: oral thermal exchange organ — chemosynthetic feeding.
        # FIX-PHASE1-002: ECM temperature passed explicitly (objection fix).
        # ECM.temperature binds mouth cooling to body thermal state.
        _ecm_temp = getattr(self, 'ecm_vestibular', None)
        _ecm_temp_val = _ecm_temp.temperature if _ecm_temp is not None else 0.15
        self.thermal_mouth.step(
            self.world, self.world.body,
            ecm_temp=_ecm_temp_val, dt=dt)
        # DigestiveInterface: thermal → chemical transduction (ATP synthase analogue).
        # Replaces ThermalMouth.deposit() — physical boundary ThermalMouth≡thermal domain.
        # 脆弱点3修正：保存 deposit_rate 返回值用于 FeedRateCapacitor 换能（原被丢弃）。
        _deposit_rate = self.digestive_interface.tick(
            self.thermal_mouth, self.energy_store, dt=dt)

        # Basal metabolic drain: organism costs energy to exist.
        self.energy_store.tick(dt)

        # ═══════════════════════════════════════════════════════════════
        # L2:SELECTION — Operation Trauma Genesis: Damage Feedback Loops
        # BIO: Tissue damage has systemic physiological consequences.
        # DESIGN: We inject physical consequences (not behavioral rules).
        #         The avoidance behavior must EMERGE from L1 circulation
        #         coupling under these L2 constraints.
        # ═══════════════════════════════════════════════════════════════

        # ── Collect damage state from all skin patches ──
        # patch_temps format: patch_id → (T_skin, dT_skin, damage_integral)
        _damage_values = [patch_temps[pid][2] for pid in patch_temps]
        _max_damage = max(_damage_values) if _damage_values else 0.0
        _total_damage = sum(_damage_values)

        # ── Feedback Loop A: damage → VitalOscillator amplitude decay ──
        # L2:SELECTION — Tissue damage depresses cardiac output.
        # BIO: Burn injury → systemic inflammatory response → cardiac
        #      depression (Horton 2003: hypovolemic shock in burn patients).
        # DESIGN: max(damage) across patches → sigmoid suppression factor.
        #         At damage=0 → factor=1.0 (healthy heartbeat).
        #         At damage=5 → factor≈0.27 (cardiac depression).
        # EMERGE: System should learn that proximity→damage→vital_drop
        #         is costly, and self-organize avoidance behavior.
        vital_damage_factor = 1.0 / (1.0 + _max_damage * self.vital_damage_k)

        # ── Feedback Loop B: damage → EnergyStore repair metabolic cost ──
        # L2:SELECTION — Tissue repair requires ATP (thermodynamic necessity).
        # BIO: Wound healing consumes 20-50% additional metabolic energy
        #      (Arnold & Barbul 2006: "Nutrition and Wound Healing").
        # DESIGN: total_damage → additional energy drain from EnergyStore.
        #         This creates thermodynamic pressure: damage costs real energy.
        # EMERGE: System should learn to avoid states that increase drain.
        repair_cost = _total_damage * self.repair_energy_rate * dt
        if repair_cost > 0:
            self.energy_store.withdraw(repair_cost)

        # Vital oscillator is called after CPC deviation is computed (B1a).
        # See "B1a: CPC deviation → VitalOscillator" block below (~line 1247).

        # ── Feedback Loop C: Spinal nociceptive withdrawal reflex ──
        # L2:SELECTION — Hardwired directional withdrawal from noxious stimuli.
        # BIO: Aδ/C-fiber → spinal interneuron → contralateral flexor motor
        #      neuron. Reflexive withdrawal AWAY from noxious stimulus.
        #      (Sherrington 1906: "flexion reflex", hardwired at birth.)
        # DESIGN: Spatial nociceptor contrast → directional motor current.
        #         Uses existing SkinPatch spatial arrangement.
        #         MOSFET gate (default: VDD=open) → future cortical override.
        # EMERGE: None — this IS L2 hardwired. But cortical override CAN
        #         suppress it in the future ("enduring pain to eat").
        soma_output = self.somatosensory.get_output()
        noci_activations = {
            pid: soma_output[pid]["noci_activation"]
            for pid in soma_output
        }
        reflex_drives = self.spinal_reflex.process(noci_activations, dt)
        for mkey, drive in reflex_drives.items():
            if drive != 0.0 and mkey in self.motor_neurons:
                self.motor_neurons[mkey]._membrane.inject(drive, dt)

        # ── Hunger-driven thermotaxis: approach warmer side when hungry ──
        # L2:SELECTION — Same spatial contrast architecture as noci withdrawal,
        # but inverted direction (approach, not flee) and gated by hunger.
        # BIO: hypothalamic hunger → lateral hypothalamus → locomotor drive
        #      toward thermal/chemical gradient (Saper et al. 2002).
        # PHYS: uses thermoreceptor DC channel (not nociceptor AC).
        thermo_activations = {
            pid: soma_output[pid]["thermo_activation"]
            for pid in soma_output
        }
        # HC-024 removed: hunger reflex drives were all 0.0 (PHASE 1 DISABLED).
        # Motor is driven by Langevin noise (AGC-modulated); thermotaxis from STDP only.

        # ── C3': Homeostatic circulation coupling (structural carrier) ──
        # HC-014 fix: thermal_stability from somatosensory relay circuit output.
        # Old: Python sigmoid of raw physics vars (_prev_T, _methylation).
        # New: relay neuron average activation — high relay = warm skin = less stable.
        # BIO: preoptic area integrator receives spinal relay input coding thermal load;
        #      high thermal load → suppressed homeostatic channel → DA excitation.
        # REF: Nakamura & Morrison 2008 Nat Neurosci — preoptic thermosensory neurons.
        relay_vals = [soma_output[pid]["relay_activation"] for pid in soma_output]
        soma_relay_avg = sum(relay_vals) / max(len(relay_vals), 1)
        thermal_stability = max(0.0, 1.0 - soma_relay_avg)
        body_speed = self.world.body.speed()

        # FeedRateCapacitor: DigestiveInterface deposit_rate → V_feed [diagnostic]
        # 脆弱点3基础设施：保存 deposit_rate → FeedRateCapacitor 积分，供将来 ν-DA 集成。
        # V_ss ≈ 1.0V（进食时），τ ≈ 5000步。
        # NOTE: _v_feed 量级(~1V) >> circulation_proportion 期望的 feed_alignment(~0.02)，
        # 故暂不接入 CPC；仍用 patch温差(max-min) 传入 CPC，待量纲校准后再切换。
        _I_feed = _deposit_rate / max(dt, 1e-12)
        self._feed_rate_cap.inject(_I_feed, dt)
        self._feed_rate_cap.leak(self._R_FEED, dt)
        self._v_feed = self._feed_rate_cap.voltage

        # Feed alignment: thermoreceptor spatial contrast (physical, not god-view)
        # BIO: dorsal horn spatial comparison across dermatomes.
        thermo_vals = [soma_output[pid]["thermo_activation"] for pid in soma_output]
        feed_alignment = (max(thermo_vals) - min(thermo_vals) if thermo_vals else 0.0)

        # ── Structural circuit: Capacitor integration + MOSFET deviation ──
        # All ratios emerge from component voltages, not software division.
        # S0-compliant: Capacitor.inject() + leak() + MOSFET.conduct().
        circ = self.circulation_proportion.step(
            thermal_stability, body_speed, feed_alignment, dt)

        # Record in MotionState (reads from structural circuit output)
        ms.homeo_amplitude = circ['v_homeo']
        ms.motor_amplitude = circ['v_motor']
        ms.feed_amplitude = circ['v_feed']
        ms.rho_homeo = circ['rho_homeo']
        ms.rho_motor = circ['rho_motor']
        ms.rho_feed = circ['rho_feed']
        ms.homeo_deviation = circ['deviation']
        ms.energy_absorbed = energy_absorbed
        ms.fill_fraction = self.energy_store.fill_fraction

        # ── Phase 4: AGC update ──
        # Drive signal computed from energy deficit + DA deficit.
        # Slow RC integrator (τ=40k) produces gain multiplier.
        # Applied to: (1) hunger reflex, (2) Col→Motor bundle propagation.
        self.agc.step(self.energy_store.fill_fraction,
                      self.dopamine.concentration, dt)
        ms.agc_gain = self.agc.gain
        ms.yolk_level = self.yolk_sac.level
        ms.yolk_depleted = self.yolk_sac.is_depleted
        ms.efference_supp_ratio = self._efference_supp_ratio

        # ── Patch D: DA fires on energy improvement rate (VTA RPE signal) ──
        # Replaces c3_da_current (absolute deviation) with rate-of-change gate.
        # DA = max(0, eta_da × Δfill / dt), gated by MOSFET (positive only).
        # BIO: VTA burst on unexpected reward, silent on steady state.
        # REF: Schultz et al. 1997, Science 275:1593-1599.
        _rpe_da = self.da_gate.step(self.energy_store.fill_fraction, dt)
        # HC-017删除: _hunger_da = max(0, 1.0*(0.5-fill_fraction)) [原L1094]
        # 饥饿 DA 已由接口二物理路径取代（ARC K_ATP → LH → hunger → DA Bundle）
        # BIO: Spanswick 1997 / Wise 2004；路径见 _init_energy_sensing()。
        _da_drive = _rpe_da
        # Phase5-revised: RPE inject amplitude calibrated for gm=1.0 DA neurons.
        # With gm=1.0: concentration = V - 0.01. For meaningful reward signal:
        # tonic (bc only): V=0.1 → c=0.09 (9%); max RPE: V=0.6 → c=0.59 (59%).
        # Ratio 2.6× matches VTA burst rate ratio (Schultz 1997: ~3× on unexpected reward).
        # Formula: V_RPE = bc_V + I_direct×R = 0.1 + RPE×SCALE×1.0; target V_RPE≈0.6.
        # SCALE = (0.6-0.1)/RPE_peak = 0.5/5.0 = 0.1. D2R keeps max steady-state at ~58%.
        DA_INJECT_SCALE = 0.1
        # HC-017 fix: RPE/hunger drive accumulated into da_input_currents (after bundles).

        # ── B1a: CPC deviation → VitalOscillator amplitude modulation ──
        # BIO: lateral hypothalamus (LH) → PPTg/LDT arousal projection
        #      modulates locomotor stride amplitude (Saper 2002).
        # Q1 BIO: LH lesion → akinesia; LH activation → locomotion (Saper 2002).
        # Q2 Structure: cpc_dev_neuron (0x04) → [frozen bundle, gain=0.3, w=0.5]
        #               → vital_amp_neuron (0x02) → VitalOscillator.deviation_mod
        # Q3 Params: gain=0.3 (attenuates raw deviation [0,1] → mod [0,0.3]);
        #            w=0.5 initial (calibration: 200k baseline shows deviation≈0.05–0.2)
        self.cpc_dev_neuron.step(circ['deviation'], dt)
        _cpc_cur = self.bundle_cpc_to_vital.propagate()
        self.bundle_cpc_to_vital.apply_to_targets(_cpc_cur, dt)

        # ── Vital Oscillator: heartbeat → Motor membrane injection ──
        # Three detuned VdP oscillators draw energy from store and inject
        # sub-threshold current into Motor X/Y/Z membranes.
        # Signal chain: EnergyStore + deviation_mod → VitalOscillator → Motor.inject()
        vital_outputs = self.vital_oscillator.step(
            self.energy_store, dt,
            deviation_mod=self.vital_amp_neuron.activation)
        # Apply Feedback A: damage suppresses vital oscillation
        vital_outputs = [v * vital_damage_factor for v in vital_outputs]
        _VITAL_MOTOR_MAP = ['move_x', 'move_y', 'move_z']
        for i, mkey in enumerate(_VITAL_MOTOR_MAP):
            if mkey in self.motor_neurons:
                self.motor_neurons[mkey]._membrane.inject(vital_outputs[i], dt)
        # Record in MotionState
        ms.vital_pulse = list(vital_outputs)
        ms.vital_amplitude = sum(abs(v) for v in vital_outputs)

        # ── 1. Advance oscillators ──
        osc_modulations = {}
        for axis in self.vestibular.axes:
            osc = self.oscillators[axis]
            osc_out = osc.step(dt)
            osc_modulations[axis] = 1.0 + osc_out

        # ── 0c. Impedance-matched signal transmission (A4: §1E.3) ──
        # RULE S0+S1: Impedance matching via symmetric MOSFET divider pair.
        # Physics: acoustic transmission T = 2Z_b/(Z_b+Z_m).
        # The factor 2 comes from TWO symmetric paths:
        #   Path A: body→medium (forward wave)
        #   Path B: medium→body (reflected wave, adds constructively at match)
        # Each path is a MOSFET divider: ratio = Z_b/(Z_b+Z_m)
        # Two paths sum: T = 2 × Z_b/(Z_b+Z_m)
        # CHECK 3: formula matches acoustic impedance, not EE voltage divider.
        Z_body = self.world.body.impedance
        Z_MEDIUM = 1.0
        self._impedance_body.gm = Z_body
        self._impedance_medium.gm = Z_MEDIUM
        # Path A (forward): body drives into medium
        i_body = self._impedance_body.conduct(1.0)
        i_total = i_body + self._impedance_medium.conduct(1.0)
        path_a = i_body / max(i_total, 1e-8)
        # Path B (symmetric): medium drives into body → same ratio by symmetry
        path_b = path_a  # symmetric structure → same ratio
        # Transmission = sum of both paths, capped at 1.0
        T_impedance = min(1.0, path_a + path_b)
        for key in list(mechanical_inputs.keys()):
            # Skip thermal patch axes — not mechanical signals
            if key.startswith('therm') or key.startswith('dtherm'):
                continue
            mechanical_inputs[key] *= T_impedance

        # ── 2. Mother step (UNCHANGED) ──
        super().step(mechanical_inputs, dt)

        # ── 2b. Governance post-step (fuse + ledger) ──
        if self.governance is not None:
            tick = getattr(self, '_maturation_tick', 0)
            self.governance.post_step(self, tick, dt)

        # ── 3. Post-hoc modulation of Aff membrane ──
        # Apply oscillatory gain modulation to the ALREADY-computed
        # afferent membrane voltage. This effectively scales the
        # synaptic current without touching mother code.
        for axis in self.vestibular.axes:
            mod = osc_modulations[axis]
            aff_reg = self.vestibular.afferent_regular[axis]
            # Scale membrane voltage by modulation factor
            # This is equivalent to scaling synaptic current
            v = aff_reg._membrane.voltage
            v_rest = 0.0  # rest voltage
            # Only modulate the deviation from rest
            deviation = v - v_rest
            new_v = v_rest + deviation * max(mod, 0.0)
            # Set membrane charge to match new voltage (KCL-compliant: tracks delta in _q_in/_q_out)
            aff_reg._membrane.discharge_to(new_v)

        # ── 3. Damper-modified leak ──
        # Apply adaptive damping to Enc/Col based on their current
        for axis in self.vestibular.axes:
            # Encoding neurons
            for prefix in ['reg_', 'irr_']:
                key = f"{prefix}{axis}"
                enc = self.encoding_neurons[key]
                damper = self.dampers_enc[axis]
                # Adaptive leak: high activation → more damping
                df = damper.damping_factor(enc._activation_ema)  # M4: continuous rate
                # Apply additional leak based on damping factor
                # This is ADDITIVE, not replacing the mother's leak
                if df > 1.01:  # only if meaningfully damped
                    extra_leak = (df - 1.0) * 0.001  # very gentle
                    enc.energy = max(0.0, enc.energy - extra_leak)

            # Column neurons
            col = self.column_neurons[axis]
            damper_c = self.dampers_col[axis]
            df_c = damper_c.damping_factor(col._activation_ema)  # M4: continuous rate
            if df_c > 1.01:
                extra_leak_c = (df_c - 1.0) * 0.001
                col.energy = max(0.0, col.energy - extra_leak_c)

        # ── 5. NDR refractory gating on afferents ──
        # Apply dynamic NDR to modulate afferent membrane:
        # If V is in NDR region, Na⁺-like inactivation reduces current
        # This refines the refractory period beyond the basic AHP
        for axis in self.vestibular.axes:
            aff = self.vestibular.afferent_regular[axis]
            ndr = self.ndr_afferent[axis]
            v = aff._membrane.voltage
            # Get dynamic NDR current (updates h gate internally)
            i_ndr = ndr.conduct_dynamic(v, dt)
            # Use NDR as a gate: when h_gate is low (post-spike),
            # reduce membrane excitability
            gate = ndr._h_gate  # 0=inactivated, 1=available
            if gate < 0.9:  # only apply during recovery
                # Reduce membrane charge proportionally to inactivation
                reduction = (1.0 - gate) * 0.01  # gentle
                aff._membrane.charge *= (1.0 - reduction)

        # ── 6. Lateral inhibition between columns ──
        # M4 fix: use continuous rate for WTA competition, inject IPSP current
        col_activations = [self.column_neurons[ax]._activation_ema
                           for ax in self._col_axes_order]
        inhibitions = self.lateral_inhibition.compute_inhibition(col_activations)
        for idx, axis in enumerate(self._col_axes_order):
            col = self.column_neurons[axis]
            # M4 fix: inject inhibitory current instead of overwriting activation
            # BIO: IPSP via Cl⁻ channel → outward current → Vm drops naturally
            if inhibitions[idx] < 0:
                col._membrane.inject(inhibitions[idx], dt)

        # ── 6b. Binding Layer: hyperedge activation (§5.2) ──
        # Uses ALL axes (vestibular + thermal) for cross-modal binding
        col_act_dict = {ax: self.column_neurons[ax]._activation_ema  # M4: continuous
                        for ax in self.all_axes}
        binding_activations = self.binding_layer.compute_all(col_act_dict)
        # Store for _do_learning() to compute sync gate
        self._binding_activations = binding_activations

        # ── Patch E: Efference Copy suppression ratio monitoring (INFRA) ──
        # Count Binding events suppressed by low motor efficacy.
        # Alert at R_supp >= 0.9 (critation doc §五).
        _avg_efficacy = sum(self._motor_efficacy.values()) / max(len(self._motor_efficacy), 1)
        for _bid in binding_activations:
            self._efference_total_count += 1
            if _avg_efficacy < self._efficacy_suppress_threshold:
                self._efference_supp_count += 1
        # Report every _efference_monitor_window steps
        _mtick = getattr(self, '_maturation_tick', 0)
        if (_mtick > 0 and _mtick % self._efference_monitor_window == 0
                and self._efference_total_count > 0):
            import warnings as _warnings
            self._efference_supp_ratio = (self._efference_supp_count
                                          / self._efference_total_count)
            if self._efference_supp_ratio >= 0.9:
                _warnings.warn(
                    f"[EXP] Efference suppression ratio {self._efference_supp_ratio:.2f}"
                    f" >= 0.9 at step {_mtick}. Check motor efficacy.",
                    RuntimeWarning, stacklevel=2)
            self._efference_supp_count = 0
            self._efference_total_count = 0

        # Binding → Motor side channel (§5.4: I_total = direct + binding)
        for bid, b_act in binding_activations.items():
            if b_act < 1e-6:
                continue
            for mid, mot in self.motor_neurons.items():
                # Lazily add binding weights for new motor neurons (mitosis)
                if mid not in self._binding_motor_weights.get(bid, {}):
                    if bid not in self._binding_motor_weights:
                        self._binding_motor_weights[bid] = {}
                    self._binding_motor_weights[bid][mid] = 0.001
                w = self._binding_motor_weights[bid][mid]
                # Add binding contribution to motor (ADDITIVE, not replacing)
                # Binding is a DORMANT side channel — subordinate to
                # the main col→motor pathway (which has adaptive coupler).
                # Previous gain=10.0 injected dV=7.0/step >> v_peak=0.2.
                mot_inject = b_act * w
                mot._membrane.inject(mot_inject * 0.1, dt)  # dormant

        # ── 7. LiquidMetalRouter: Enc→Col dynamic topology ──
        # Update routers based on Enc-Col activity correlation
        for axis in self.vestibular.axes:
            router = self.routers_enc_col[axis]
            # Use encoding and column activations as pre/post
            enc_act = sum(self.encoding_neurons[f'{p}{axis}']._activation_ema
                          for p in ['reg_', 'irr_']) / 2.0  # M4: rate
            col_act = self.column_neurons[axis]._activation_ema  # M4: rate
            # Router updates its internal state
            g = router.step(enc_act, col_act, dt)
            # Modulate the column neuron's effective input
            # by the router conductance (< 1.0 = attenuated)
            # Use gentle additive reduction rather than multiplicative
            if g < 0.9:  # only apply if meaningfully attenuated
                attenuation = (1.0 - g) * 0.0005  # very gentle
                self.column_neurons[axis].energy = max(
                    0.001, self.column_neurons[axis].energy - attenuation)

        # ── 8. Neuromodulator (DA) update ──
        # 8a. Motor spike tracking (used for feedback, NOT for DA release)
        # BIO: DA is released by prediction error changes (VTA), not motor activity.
        # Motor activity tracking is kept for efference copy feedback (section 9).
        for key, mot in self.motor_neurons.items():
            self._prev_motor_spikes[key] = len(mot.spike_times)

        # 8b. Structural DA circuit (replaces all hardcoded DA release)
        #
        # Architecture:
        #   Shadow col neurons → [Bundle: shadow_to_da] → DA neurons
        #   Xin integrator → xin_relay neuron → [Bundle: xin_to_da] → DA neurons
        #   DA neuron activation → dopamine.concentration (volumetric broadcast)
        #
        # All pathways use real Neurons + Bundles with STDP.
        # Eligible for sprout/prune. Registered in entropy ledger.
        # DA baseline = DA neuron bc_current * R_leak = 0.1 (structural).
        # BIO: VTA receives cortical + pontine input via real synapses.

        # Lazy init: create bundles once shadow layer is ready
        if not self._da_circuit_initialized:
            self._init_da_circuit()

        # ── Xin relay: mirror integrator into a real neuron ──
        # Xin integrator (Capacitor) tracks |dξ/dt| of main layer.
        # Relay neuron converts voltage → activation for bundle input.
        total_xin = sum(abs(b.config.xin_tension)
                        for b in self.get_all_bundles())
        if not hasattr(self, '_prev_total_xin'):
            self._prev_total_xin = total_xin
        delta_xin = abs(total_xin - self._prev_total_xin)
        self._prev_total_xin = total_xin
        self._xin_integrator.inject(delta_xin, dt)
        self._xin_integrator.leak(0.5, dt)
        # Clamp (Zener)
        xin_v = self._xin_integrator.voltage
        i_xin_clamp = self._xin_clamp.conduct(xin_v)
        if i_xin_clamp > 0:
            self._xin_integrator.inject(-i_xin_clamp, dt)
        # Feed integrator voltage into relay neuron as input current
        self._xin_relay.step(self._xin_integrator.voltage * 0.5, dt)

        # ── DA input bundles: propagate ──
        da_input_currents = {nid: 0.0 for nid in self.da_neurons}

        for bundle in self.bundles_shadow_to_da:
            currents = bundle.propagate()
            for j, tgt in enumerate(bundle.targets):
                if j < len(currents) and tgt.id in da_input_currents:
                    da_input_currents[tgt.id] += currents[j]

        for bundle in self.bundles_xin_to_da:
            currents = bundle.propagate()
            for j, tgt in enumerate(bundle.targets):
                if j < len(currents) and tgt.id in da_input_currents:
                    da_input_currents[tgt.id] += currents[j]

        # ── Step lamina I proj neurons (relay → proj → DA, P1-DIFF) ──
        # Must be stepped BEFORE relay_to_da propagates, so calcium_rate is current.
        if self._soma_proj:
            proj_input_currents = {n.id: 0.0 for n in self._soma_proj.values()}
            for bundle in self._bundles_relay_to_proj:
                currents = bundle.propagate()
                for j, tgt in enumerate(bundle.targets):
                    if j < len(currents) and tgt.id in proj_input_currents:
                        proj_input_currents[tgt.id] += currents[j]
            for neuron in self._soma_proj.values():
                neuron.step(proj_input_currents.get(neuron.id, 0.0), dt)

        for bundle in self.bundles_relay_to_da:
            currents = bundle.propagate()
            for j, tgt in enumerate(bundle.targets):
                if j < len(currents) and tgt.id in da_input_currents:
                    da_input_currents[tgt.id] += currents[j]

        # ── CPG → DA: advance pacemaker and propagate rhythmic drive ──
        # Advances 2Hz VdP oscillator; injects low-amplitude AC into DA neurons.
        # Keeps DA.post_trace = |d(activation)/dt| > 0 at steady state.
        if self._da_cpg is not None:
            self._da_cpg.step(dt)
            for bundle in self.bundles_cpg_to_da:
                currents = bundle.propagate()
                for j, tgt in enumerate(bundle.targets):
                    if j < len(currents) and tgt.id in da_input_currents:
                        da_input_currents[tgt.id] += currents[j]

        # ── Warm-onset → DA: propagate ThermalDelta bundles into da_input_currents ──
        # BIO: LPB→VTA warm-onset path; innate frozen weights (see _init_da_circuit).
        # Provides phasic DA burst correlated with relay activity during warm approach:
        #   relay (pre, tonic) → warm entry → ThermalDelta → DA (post) → LTP ✓
        if self.bundles_thermo_delta_to_da:
            for bundle in self.bundles_thermo_delta_to_da:
                currents = bundle.propagate()
                for j, tgt in enumerate(bundle.targets):
                    if j < len(currents) and tgt.id in da_input_currents:
                        da_input_currents[tgt.id] += currents[j]

        # ── 接口二：ARC K_ATP → LH → hunger → DA（物理路径替代 _hunger_da HC）──
        # BIO: K_ATP通道在ATP低时开放（fill<0.5）→ ARC激活 → LH整合 → VTA tonic DA。
        # REF: Spanswick 1997 Nature 390:521; Wise 2004 Nat Rev Neurosci 5:483.
        # PHYS: hunger_signal = max(0, 0.5 - fill) 为K_ATP整流（传感器边界操作，非HC）
        if self.energy_sensors and self.bundle_hunger_to_da is not None:
            _hunger_signal = max(0.0, 0.5 - self.energy_store.fill_fraction)
            for _sensor in self.energy_sensors:
                _sensor.step(self._G_ENERGY_SENSE * _hunger_signal, dt)
            _sa_cur = self.bundle_sensors_to_average.propagate()
            self.bundle_sensors_to_average.apply_to_targets(_sa_cur, dt)
            _ah_cur = self.bundle_average_to_hunger.propagate()
            self.bundle_average_to_hunger.apply_to_targets(_ah_cur, dt)
            _hd_cur = self.bundle_hunger_to_da.propagate()
            for j, tgt in enumerate(self.bundle_hunger_to_da.targets):
                if j < len(_hd_cur) and tgt.id in da_input_currents:
                    da_input_currents[tgt.id] += _hd_cur[j]

        # ── C1: shadow_nu → DA (prediction-error phasic gate) ──
        # bundle_shadow_nu_to_da created lazily (after DA circuit init).
        if self.bundle_shadow_nu_to_da is not None:
            _nu_cur = self.bundle_shadow_nu_to_da.propagate()
            for j, tgt in enumerate(self.bundle_shadow_nu_to_da.targets):
                if j < len(_nu_cur) and tgt.id in da_input_currents:
                    da_input_currents[tgt.id] += _nu_cur[j]

        # HC-017 fix: RPE DA drive via normal step() pathway (not _membrane.inject).
        # BIO: VTA RPE → DA burst (Schultz 1997).
        # REF: Schultz 1997 J Neurophysiol 77:1060.
        # NOTE: _hunger_da 已删除（HC L1094），饥饿驱动现由接口二物理路径提供。
        if _da_drive > 0:
            rpe_current = _da_drive * DA_INJECT_SCALE
            for nid in da_input_currents:
                da_input_currents[nid] += rpe_current

        # ── Step DA neurons ──
        # DA neuron energy: withdraw from EnergyStore (not magic refill).
        # Rate-limited: max 0.01 per step per neuron (prevents store drain).
        # When store is low, DA neurons get less energy → reduced output.
        # Track refill as cumulative_energy_in for Noether conservation.
        # P2.1: Reduced from 0.01 to 0.001. Previous rate (0.03/step total)
        # dwarfed world energy production (0.002/step), causing immediate
        # store depletion. DA neurons don't need high energy for continuous mode.
        DA_REFILL_RATE = 0.001  # max energy per step per DA neuron
        for nid, neuron in self.da_neurons.items():
            needed = min(DA_REFILL_RATE, max(0.0, 5.0 - neuron.energy))
            refill = self.energy_store.withdraw(needed)
            if refill > 0:
                neuron.energy += refill
                neuron._cumulative_energy_in += refill
        # Set DA concentration input for D2 autoreceptor BEFORE step.
        # D2R reads the CURRENT DA concentration and generates GIRK current
        # inside neuron.step() (standard path → in energy accounting).
        current_da = self.dopamine.concentration
        for nid, neuron in self.da_neurons.items():
            neuron.config.da_concentration_input = current_da
            neuron.step(da_input_currents.get(nid, 0.0), dt)

        # ── DA neuron activation → dopamine concentration ──
        # Volumetric broadcast: mean DA neuron activation = concentration.
        # BIO: DA is released diffusely, affecting entire regions.
        mean_da = sum(n.activation for n in self.da_neurons.values()) / max(len(self.da_neurons), 1)
        self.dopamine._concentration = max(0.0, min(1.0, mean_da))
        # Don't call dopamine.step() — concentration is set structurally.

        # ── STDP on DA input bundles ──
        for bundle in self.bundles_shadow_to_da + self.bundles_xin_to_da + self.bundles_relay_to_da:
            bundle.learn(dt=dt, fill_fraction=self.energy_store.fill_fraction,
                         da_concentration=self.dopamine.concentration)
            bundle.compute_xin(dt)
        # relay_to_proj is frozen (no STDP) but track ν for ledger visibility
        for bundle in self._bundles_relay_to_proj:
            bundle.compute_xin(dt)
        # cpg_to_da is frozen (innate pacemaker) — only Xin tracking needed
        for bundle in self.bundles_cpg_to_da:
            bundle.compute_xin(dt)
        # thermo_delta_to_da is frozen (innate LPB→VTA) — only Xin tracking needed
        for bundle in self.bundles_thermo_delta_to_da:
            bundle.compute_xin(dt)
        # P2-HC007: STDP on relay→enc bundles (thermal thalamo-cortical learning)
        # TIMING: after super().step() so enc_reg.post_trace is updated (enc_reg stepped above).
        # relay.pre_trace updated in somatosensory.step() (earlier this frame). ✓
        for bundle in self.bundles_relay_to_enc:
            bundle.learn(dt=dt, fill_fraction=self.energy_store.fill_fraction,
                         da_concentration=self.dopamine.concentration)
            bundle.compute_xin(dt)

        # DA modulation moved to _propagate_bundles() override (multiplicative).
        # See below: DA gain_factor scales synapse currents, not injected current.

        # ── 9. Motor → Column feedback (efference copy) ──
        # RULE S1 CHECK 1: Motor activity -> Capacitor (filter) -> inhibitory current
        # Motor spike is "event" (neuroscience). Column needs "current" (circuit).
        # Capacitor acts as temporal integrator (replaces EMA, satisfies S0).
        if not hasattr(self, '_feedback_caps'):
            from ..components.semiconductor import Capacitor as FBCap
            self._feedback_caps = {
                key: FBCap(capacitance=self._feedback_tau)
                for key in self.motor_neurons
            }
        for key, mot in self.motor_neurons.items():
            # Lazily create feedback caps for new motor neurons (mitosis)
            if key not in self._feedback_caps:
                from ..components.semiconductor import Capacitor as FBCap
                self._feedback_caps[key] = FBCap(capacitance=self._feedback_tau)
            if key not in self._prev_motor_spikes:
                self._prev_motor_spikes[key] = 0
            mot_act = 1.0 if (len(mot.spike_times) > self._prev_motor_spikes.get(key, 0) - 1) and mot.activation > 0.5 else 0.0
            # Inject motor activity into feedback Capacitor
            self._feedback_caps[key].inject(mot_act, dt)
            # Capacitor leak = temporal decay (equivalent to EMA)
            self._feedback_caps[key].leak(1.0, dt)  # R=1 -> tau = C*R = feedback_tau

        # Apply feedback: Capacitor voltage = filtered motor trace -> inhibitory current
        total_fb_v = sum(cap.voltage for cap in self._feedback_caps.values())
        if total_fb_v > 0.01:
            fb_current = total_fb_v * self._feedback_gain
            for axis in self.vestibular.axes:
                col = self.column_neurons[axis]
                # Inject NEGATIVE current = inhibition (CHECK 1: current domain)
                col._membrane.inject(-fb_current, dt)

        # ── 10. Maturation potential accumulation (§3, every step) ──
        for n in self.get_all_neurons():
            cfg = n.config
            if hasattr(cfg, 'potential_phi'):
                cfg.potential_phi += n._activation_ema * cfg.potential_phi_epsilon  # M4

        # ── 11. Maturation phase transitions (§3.1, slow: every ~1000 steps) ──
        self._maturation_tick += 1
        if self._maturation_tick % 1000 == 0:
            self._check_maturation_transitions()

        # ── 12. Learning is handled by _do_learning() ──
        # Phase 4: P→R closure. All learning happens via the virtual method
        # _do_learning() called in mother's step(). No duplicate calls here.
        # See _do_learning() override below for DA + PNN + sync gating.

        # ── 13. Xin tension accumulation (§7.2) ──
        for b in self.get_all_bundles():
            b.compute_xin(dt)

        # ── 14. Fruit lifecycle (§7.3, slow: every 100 steps) ──
        if self._maturation_tick % 100 == 0:
            for b in self.get_all_bundles():
                b.update_fruit(dt, da_concentration=self.dopamine.concentration)

        # ── 15. Circulation detection (§6, slow: every 100 steps) ──
        if not hasattr(self, '_circulation_meter'):
            self._circulation_meter = CirculationMeter()
            self.circulation_state = None
        if self._maturation_tick % 100 == 0:
            self.circulation_state = self._circulation_meter.measure(
                self, self._maturation_tick
            )

        # ── 16. Shadow sandbox observation (read-only) ──
        # Match SHADOW_K=10 interval for proper τ convergence.
        # At 100-step interval, shadow needs 150k steps to reach steady state.
        # At 10-step interval, only ~15k steps needed.
        if self._maturation_tick % 10 == 0:
            self.shadow_sandbox.observe(self, self._maturation_tick)

        # ── C1: ShadowNuNeuron step (boundary transducer: ν → neural) ──
        # BIO: basal ganglia prediction error → VTA DA burst (Friston 2012).
        # _nu only updates every 10 steps; step every step to maintain τ dynamics.
        self.shadow_nu_neuron.step(self.shadow_sandbox._nu * self._NU_SCALE, dt)

        # ── Phase Z: Entropy ledger post-step (slow-scale only) ──
        self._ledger_post_step(self._maturation_tick, dt)

        # ── 5. ECM thermal field ──
        # Collect heat from each layer, update ECM temperatures
        vest_heat = sum(n.heat_output for n in [
            self.vestibular.met_neurons.get(axis),
            self.vestibular.haircell_neurons.get(axis),
            self.vestibular.afferent_regular.get(axis),
            self.vestibular.afferent_irregular.get(axis),
        ] for axis in self.vestibular.axes if self.vestibular.met_neurons.get(axis))
        enc_heat = sum(n.heat_output for n in self.encoding_neurons.values())
        col_heat = sum(n.heat_output for n in self.column_neurons.values())

        # A4: scale ECM thermal capacity by body volume (larger = more inertia)
        # This is applied each step (not cached) in case body volume changes.
        tmf = self.world.body.thermal_mass_factor()
        self.ecm_vestibular.thermal_capacity = 3.0 * tmf  # base=3.0 (vestibular preset)
        self.ecm_encoding.thermal_capacity = 4.0 * tmf   # base=4.0
        self.ecm_column.thermal_capacity = 5.0 * tmf     # base=5.0

        self.ecm_vestibular.step(vest_heat, dt)
        self.ecm_encoding.step(enc_heat, dt)
        self.ecm_column.step(col_heat, dt)

        # ── Feedback Loop D: damage → ECM thermal barrier breach ──
        # L2:SELECTION — Tissue damage destroys dermal barrier → deep heat.
        # BIO: Burns destroy dermal barrier → deep tissue thermal injury.
        #      High temperature in ECM → Q10 effect → ion channel acceleration
        #      → potential febrile seizure (high-thermal chaos in neural net).
        # PHYS: Damaged insulator → thermal resistance drops → heat flows in.
        # DESIGN: damage_integral acts as inverse thermal resistance.
        #         Michaelis-Menten saturation: breach = D/(D+K).
        #         No damage → ECM fully insulated. High damage → exposed.
        # EMERGE: ECM thermal disruption → ion channel dynamics change →
        #         prediction error (Shadow) → DA burst → STDP learning.
        #         This is the "febrile seizure" catalyst for rapid learning.
        K_BARRIER = self.k_barrier
        BREACH_CONDUCTANCE = self.breach_conductance
        if _max_damage > 0.01:
            breach_factor = _max_damage / (_max_damage + K_BARRIER)
            # Find hottest skin patch temperature
            max_skin_T = max(patch_temps[pid][0] for pid in patch_temps)
            for ecm in [self.ecm_vestibular, self.ecm_encoding, self.ecm_column]:
                # Heat flows from hot skin into cooler ECM (thermodynamically correct)
                delta_T = max_skin_T - ecm.temperature
                if delta_T > 0:
                    heat_breach = breach_factor * delta_T * BREACH_CONDUCTANCE
                    ecm._temperature += heat_breach * dt

        # ── 5b. Inter-layer heat diffusion (A3: §1E.2) ──
        # A3 FIX: heat propagates with finite delay and penetration threshold.
        # Step 1: Compute instantaneous heat flow from ΔT
        # Step 2: Push into delay buffer (FIFO queue)
        # Step 3: Pop delayed heat and apply
        # BIO: heat diffuses between adjacent tissue layers via tissue conductance
        #   but not instantaneously — thermal diffusivity limits propagation speed.
        ecm_pairs = [
            (self.ecm_vestibular, self.ecm_encoding,
             self._thermal_coupler_ve, self._thermal_delay_ve),
            (self.ecm_encoding, self.ecm_column,
             self._thermal_coupler_ec, self._thermal_delay_ec),
        ]
        for ecm_a, ecm_b, coupler, delay_buf in ecm_pairs:
            delta_t = ecm_a.temperature - ecm_b.temperature

            # A3: Penetration threshold — small ΔT doesn't propagate
            # BIO: thermal skin depth limits how far weak signals reach
            if abs(delta_t) < self._thermal_penetration_min:
                heat_flow_in = 0.0
            else:
                # MOSFET conduct: I = gm * (V - Vth) = gm * |ΔT| (Vth=0)
                heat_flow_in = coupler.conduct(abs(delta_t))

            # A3: Push into delay buffer, get delayed output
            sign = 1.0 if delta_t > 0 else -1.0
            heat_flow_out = delay_buf.push(heat_flow_in * sign)

            # Apply delayed heat flow
            if abs(heat_flow_out) > 1e-12:
                ecm_a._temperature -= heat_flow_out * dt
                ecm_b._temperature += heat_flow_out * dt

        # Radiative loss via MOSFET: I_loss = gm_loss * T
        for ecm in [self.ecm_vestibular, self.ecm_encoding, self.ecm_column]:
            loss = self._thermal_loss.conduct(max(0.0, ecm.temperature))
            ecm._temperature -= loss * dt
            ecm._temperature = max(0.0, ecm._temperature)  # physical: T >= 0

        # ── PNN Critical Period (T2: DA-driven degradation) ──
        # Phase 4: PNN gating is unified in _do_learning() via plasticity_gate.
        # T2 FIX: elevated DA now degrades PNN (reopens plasticity).
        # Loop: novelty → high Xin → DA → MMP-9 → PNN degradation → gate opens.
        # Without this, PNN only matures → plasticity monotonically decreases.
        da_conc = self.dopamine.concentration
        for ecm in [self.ecm_vestibular, self.ecm_encoding, self.ecm_column]:
            ecm.degrade_pnn(da_conc, dt)

        # ── 6. Vascular cooling ──
        # Use max ECM temperature as tissue temp
        max_temp = max(self.ecm_vestibular.temperature,
                       self.ecm_encoding.temperature,
                       self.ecm_column.temperature)
        total_activity = sum(n._activation_ema for n in self.get_all_neurons())  # M4
        vasc_result = self.vascular.step(
            tissue_temperature=max_temp,
            local_activity=total_activity,
            dt=dt
        )
        # Apply vascular cooling to ECM temperatures
        cool_per_layer = vasc_result['heat_removed'] * dt / 3.0
        for ecm in [self.ecm_vestibular, self.ecm_encoding, self.ecm_column]:
            ecm._temperature -= cool_per_layer / max(ecm.thermal_capacity, 0.01)

        # ── 7. Vascular energy delivery (gated by EnergyStore) ──
        # Vascular delivery is scaled by store level: low store → less delivery.
        # Energy withdrawn from store, not created from nothing.
        # BIO: hypoglycemia reduces cerebral metabolic supply.
        delivery_factor = self.energy_store.delivery_factor()
        raw_delivery = vasc_result['energy_delivered']
        n_neurons = max(len(self.get_all_neurons()), 1)
        requested_total = raw_delivery * delivery_factor * 0.01
        actual_total = self.energy_store.withdraw(requested_total)
        energy_per_neuron = actual_total / n_neurons
        for n in self.get_all_neurons():
            n.energy = min(1.0, n.energy + energy_per_neuron)

    # ── DA Multiplicative Gain Modulation ──────────────────────────

    def _propagate_bundles(self, dt: float):
        """Override: DA gain_factor scales synapse currents multiplicatively.

        Instead of injecting extra DC current into Column membranes
        (additive, which competes with synaptic drive and produces U-curves),
        DA scales the OUTPUT of propagate() before it enters the neuron.

        Physics: DA D1 receptor enhances NMDA/AMPA conductance → scales
        postsynaptic current (Seamans & Yang 2004). This is a PGA
        (Programmable Gain Amplifier) on the synaptic channel, not a
        bias voltage injector.

        gain_factor = 1 + alpha_gain × (conc - baseline)
        At baseline (0.1): gain = 1.0 (no change)
        At elevated DA (0.5): gain = 1.6 (60% boost)
        At max DA (1.0): gain = 2.35 (135% boost)

        Energy accounting: scaled current still enters via inject(),
        sourced from upstream neuron activity. Noether ledger tracks it.
        """
        da_gain = self.dopamine.gain_factor()

        # 接口三：制动束先于 col_to_motor 注入抑制电流
        # 先于驱动电流注入；dt=0.001 尺度下两次 step() 的累加误差 < 0.1%
        if getattr(self, 'bundle_front_to_brake', None) is not None:
            _brake_cur = self.bundle_front_to_brake.propagate()
            self.bundle_front_to_brake.apply_to_targets(_brake_cur, dt)

        # Enc → Col: DA scales encoding→column signal
        for bundle in self.bundles_enc_to_col:
            currents = bundle.propagate()
            if da_gain != 1.0:
                currents = [c * da_gain for c in currents]
            bundle.apply_to_targets(currents, dt)

        # Col → Motor: DA scales column→motor signal
        # BIO: D1 receptors present on both prefrontal and motor cortex
        # NOTE: AGC is NOT applied here — it acts only on hunger reflex.
        # Applying AGC broadly amplifies ALL motor pathways (incl. thermal),
        # which disrupts encoding selectivity (T2.2/T2.3 regression).
        for bundle in self.bundles_col_to_motor:
            currents = bundle.propagate()
            if da_gain != 1.0:
                currents = [c * da_gain for c in currents]
            bundle.apply_to_targets(currents, dt)

        # B1b: Renshaw recurrent lateral inhibition (after Col→Motor)
        # BIO: α-motor collateral → Renshaw cell → motor pool inhibition
        # (Eccles et al. 1961). Prevents co-contraction of antagonist pools.
        # Excit: motor → renshaw (reads motor activation from Col→Motor step above)
        for bundle in self.bundles_renshaw_excit:
            currents = bundle.propagate()
            bundle.apply_to_targets(currents, dt)
        # Inhib: renshaw → other motors (reads renshaw activation just set)
        for bundle in self.bundles_renshaw_inhib:
            currents = bundle.propagate()
            bundle.apply_to_targets(currents, dt)

        # 接口一：Motor 传出副本（efference copy）→ hypothalamus_effort
        # 在 Col→Motor 传播后执行（Motor 神经元已被 step，activation 已更新）
        if getattr(self, 'bundle_motor_to_effort', None) is not None:
            _eff_cur = self.bundle_motor_to_effort.propagate()
            self.bundle_motor_to_effort.apply_to_targets(_eff_cur, dt)

        # Sprouted bundles: same DA scaling
        for bundle in self._sprouted_bundles:
            currents = bundle.propagate()
            if da_gain != 1.0:
                currents = [c * da_gain for c in currents]
            bundle.apply_to_targets(currents, dt)

    # ── Ledger: Pre-step / Post-step ──────────────────────────────

    def _ledger_pre_step(self, tick: int, dt: float):
        """Phase 0: Entropy ledger guard — runs BEFORE all computation.

        Multi-scale sampling entry point:
          Every step:  heat accumulation (Landauer tracking)
          100 steps:   Noether verification + weight entropy + TOPRXIN

        If Noether finds violations, sets _structural_freeze = True
        to prevent structural modifications in this step.

        Checks state from the PREVIOUS step (before this step modifies
        anything). Violations at t-1 are caught before t executes.
        """
        # Reset freeze flag (re-evaluated each step)
        self._structural_freeze = False

        # ── Every step: heat accumulation ──
        # Accumulates heat from the PREVIOUS step's neuron outputs.
        total_heat = sum(n.heat_output for n in self.get_all_neurons())
        self._entropy_probe.accumulate_heat(total_heat)

        # ── 100-step periodic: guard-level checks ──
        if tick % 100 == 0 and tick > 0:
            # 1. Noether conservation (previous step's state)
            violations_before = len(self._noether_probe._violations)
            self._noether_probe.check(self, tick, dt)
            new_violations = len(self._noether_probe._violations) - violations_before
            if new_violations > 0:
                self._structural_freeze = True

            # 2. Weight entropy snapshot (Shannon)
            self._entropy_probe.measure(self, tick)

            # 3. TOPRXIN phase intensities + recursion cycle update
            toprxin_snap = self._toprxin_ledger.measure(self, tick)
            self._recursion_tracker.update_phases(tick, toprxin_snap)

    def _ledger_post_step(self, tick: int, dt: float):
        """Phase Z: Slow-scale structural metrics — runs AFTER computation.

        1000-step interval: structural entropy + structural bridge + energy ledger.
        These need to see the current step's structural changes
        (sprout/prune/mitosis outcomes), so they run post-step.
        """
        if tick % 1000 == 0 and tick > 0:
            self._structural_entropy.measure(tick)
            self._structural_bridge.structural_influence(tick)
            # Energy ledger: global thermodynamic accounting
            self._energy_ledger.record(self, dt)
            # Component registry: scan all live components
            self._component_registry.scan(self, tick)

    def _do_learning(self, dt: float):
        """Phase 4: P→R closure — unified three-factor learning.

        Full chain: |ξ| → c_DA → α_lr → Δw (v2.0 §1E.5)

        Three factors combined into plasticity_gate per layer:
          1. PNN gate (g_ℓ): ECM maturation → critical period closure
          2. DA modulation: Xin tension → DA release → learning rate boost
          3. Sync gate (g_sync): binding activation → col→motor gate

        Phase 2 addition: fill_fraction gates LTD decay in all bundles.
        When EnergyStore is depleted, LTD is frozen to prevent metabolic
        forgetting (EXP-016: Δw collapsed +0.289→+0.013 at fill=0).

        This replaces both the old step-12 learn() and the PNN lr cache,
        which previously conflicted (double learning + permanent lr mutation).

        BIO: Three-factor rule: pre × post × neuromodulator (Reynolds 2002)
             PNN closes critical period (Pizzorusso 2002)
             Cross-modal binding gates motor learning (Stein & Stanford 2008)
        """
        # Factor 1: PNN gates (per-layer ECM maturity)
        gate_vest = self.ecm_vestibular.plasticity_gate
        gate_enc = self.ecm_encoding.plasticity_gate
        gate_col = self.ecm_column.plasticity_gate

        # Factor 2: DA modulation (Xin → DA → gain)
        da_lr_mod = self.dopamine.gain_factor()  # 1.0=baseline, >1=boosted

        # Factor 3: Sync gate from binding layer (col→motor only)
        # RULE S0: Binding activation as MOSFET gate voltage.
        binding_acts = getattr(self, '_binding_activations', {})
        total_bind_act = sum(binding_acts.values())
        g_sync_raw = self._sync_gate.conduct(total_bind_act)
        g_sync = min(1.0, g_sync_raw)

        # Phase 2: Energy-gated LTD freeze.
        # Read fill_fraction once, pass to all bundles.
        fill = self.energy_store.fill_fraction

        # Phase 3: DA concentration for three-factor eligibility trace.
        # Read once, pass to all bundles. Bundles with use_eligibility_trace=True
        # will gate LTP by this value. Others ignore it (default da=0.0 is safe).
        da_conc = self.dopamine.concentration

        # Vestibular → Encoding: PNN × DA
        for b in self.bundles_vest_to_enc:
            b.learn(dt, plasticity_gate=gate_vest * da_lr_mod,
                    fill_fraction=fill, da_concentration=da_conc)

        # Encoding → Column: PNN × DA
        for b in self.bundles_enc_to_col:
            b.learn(dt, plasticity_gate=gate_enc * da_lr_mod,
                    fill_fraction=fill, da_concentration=da_conc)

        # A4: mass inertia factor — heavier body = slower motor learning
        # BIO: larger organisms have slower motor adaptation rates
        body_lr = self.world.body.mass_inertia_factor()

        # Column → Motor: PNN × DA × sync × body_inertia
        for b in self.bundles_col_to_motor:
            b.learn(dt, plasticity_gate=gate_col * da_lr_mod * g_sync * body_lr,
                    fill_fraction=fill, da_concentration=da_conc)

        # Sprouted bundles: use target layer's gate
        for b in self._sprouted_bundles:
            bid = b.config.bundle_id
            if 'col_to_motor' in bid:
                gate = gate_col * da_lr_mod * g_sync * body_lr
            elif 'enc_to_col' in bid or 'aff' in bid:
                gate = gate_enc * da_lr_mod
            else:
                gate = gate_vest * da_lr_mod
            b.learn(dt, plasticity_gate=gate, fill_fraction=fill,
                    da_concentration=da_conc)

        # D1: phasic→spinal STDP (DA-gated, col→motor gate; directional thermal learning)
        for _bd1 in [self.bundle_d1_phasic_left_to_spinal_ccw,
                     self.bundle_d1_phasic_right_to_spinal_cw]:
            _bd1.learn(dt, plasticity_gate=gate_col * da_lr_mod * g_sync * body_lr,
                       fill_fraction=fill, da_concentration=da_conc)
            _bd1.compute_xin(dt)

    def get_variant_state(self) -> dict:
        """Get variant component states for monitoring."""
        return {
            "oscillators": {
                axis: {
                    "output": osc.output(),
                    "phase": osc.phase,
                    "frequency": osc.frequency,
                }
                for axis, osc in self.oscillators.items()
            },
            "dampers_enc": {
                axis: {
                    "b_field": d.b_field,
                    "viscosity_ratio": d.viscosity_ratio,
                }
                for axis, d in self.dampers_enc.items()
            },
            "ecm": {
                "vestibular": {
                    "temperature": self.ecm_vestibular.temperature,
                    "ion_buffer": self.ecm_vestibular.ion_buffer,
                    "pnn_maturity": self.ecm_vestibular.pnn_maturity,
                },
                "encoding": {
                    "temperature": self.ecm_encoding.temperature,
                    "ion_buffer": self.ecm_encoding.ion_buffer,
                },
                "column": {
                    "temperature": self.ecm_column.temperature,
                    "ion_buffer": self.ecm_column.ion_buffer,
                },
            },
            "vascular": {
                "flow_rate": self.vascular.flow_rate,
                "activity_signal": self.vascular.activity_signal,
                "total_heat_removed": self.vascular.total_heat_removed,
                "total_energy_delivered": self.vascular.total_energy_delivered,
            },
            # ── New systems ──
            "binding": self.binding_layer.summary(),
            "circulation": {
                "p": self.circulation_state.p_path.path_id if (
                    self.circulation_state and self.circulation_state.p_path) else None,
                "r": self.circulation_state.r_path.path_id if (
                    self.circulation_state and self.circulation_state.r_path) else None,
                "rho": self.circulation_state.rho if self.circulation_state else {},
                "nu": self.circulation_state.nu if self.circulation_state else {},
                "total_flow": self.circulation_state.total_flow if self.circulation_state else 0,
            } if hasattr(self, 'circulation_state') else {},
            "xin": {
                b.id: {"tension": b.config.xin_tension, "fruit": b.config.fruit_state}
                for b in self.get_all_bundles()
            },
            "maturation": {
                n.id: getattr(n.config, 'maturation_stage', 0)
                for n in list(self.encoding_neurons.values()) + list(self.column_neurons.values())
            },
            "crystallization": {
                b.id: self._is_crystallized(b)
                for b in self.get_all_bundles()
            },
            "shadow": self.shadow_sandbox.get_state(),
            # Phase 6: T/O/P/R/Xin Entropy Ledger
            "entropy_probe": self._entropy_probe.summary(),
            "toprxin": self._toprxin_ledger.summary(),
            "recursion": self._recursion_tracker.summary(),
            # Phase 7: candidate math framework
            "ultrametric": self._ultrametric.summary(),
            "structural_entropy": self._structural_entropy.summary(),
            "structural_bridge": self._structural_bridge.summary(),
            # T4: Noether conservation verification
            "noether": self._noether_probe.summary(),
            # Energy ledger: global thermodynamic accounting
            "energy_ledger": self._energy_ledger.summary(),
            # Phase 4: AGC state
            "agc": self.agc.summary(),
        }

    # ── Phase 6: Structural event hooks → RecursionTracker ────

    def _on_sprout(self, tick: int, parent_id: str, child_id: str):
        """Feed sprout event to RecursionTracker."""
        self._recursion_tracker.on_sprout(tick, parent_id, child_id)

    def _on_prune(self, tick: int, bundle_id: str):
        """Feed prune event to RecursionTracker."""
        self._recursion_tracker.on_prune(tick, bundle_id)

    def _on_mitosis(self, tick: int, parent_id: str, child_id: str):
        """Feed mitosis event to RecursionTracker."""
        self._recursion_tracker.on_mitosis(tick, parent_id, child_id)

    # ── DA circuit initialization (lazy, after shadow ready) ──────

    def _init_da_circuit(self):
        """Create DA input bundles after shadow layer is initialized.

        Called lazily from _update_neuromodulation on first step.
        Shadow layer neurons don't exist at __init__ time.

        Creates three bundle pathways:
          1. Shadow col → DA neurons (tonic/baseline, frozen)
          2. Xin relay → DA neurons (phasic bursts, frozen)
          3. Soma relay → DA neurons (directional thermal, STDP-learning)
             BIO: spinal lamina I → parabrachial nucleus → VTA

        All pathways use real SynapticBundles — eligible for:
        - STDP weight adaptation (learns what signals predict "need for DA")
        - Sprout/prune (structural optimization via hebbian._structural_growth)
        - Entropy ledger tracking (Noether weight conservation)
        - 垫支 (weight crystallization = structural memory of "normal DA")
        """
        if not self.shadow_sandbox._initialized:
            # Shadow not ready yet, will try again next step
            return

        shadow_cols = [n for nid, n in self.shadow_sandbox.neurons.items()
                       if nid.startswith('s_col_')]
        da_list = list(self.da_neurons.values())

        if not shadow_cols or not da_list:
            return

        # ── 1. Shadow col → DA (single excitatory pathway) ──
        # MOTHER-DIFFERENTIATION: shadow col neurons are now spiking
        # with CalciumRateIntegrator (CRI). The bundle's propagate()
        # automatically uses col.calcium_rate (continuous, bounded ∈ [0,1])
        # instead of pre_trace or raw activation.
        # This solves: (1) spike-gap zero-signal problem
        #              (2) unbounded activation (spiking = hard limit)
        # BIO: CaMKII concentration → synaptic input to VTA DA neurons.
        #
        # gain=1.0: with calcium_rate ∈ [0,1],
        # I = 7 sources × rate(≤1.0) × w(0.05) × 1.0 = 0.35
        # V_ss = (0.35 + 0.1bc) × 1.0 = 0.45 → moderate DA ✓
        # D2R will prevent saturation if DA > 0.3 (ec50)
        cfg_shadow = BundleConfig(
            bundle_id="shadow_to_da",
            learning_rule="frozen",  # INNATE: hypothalamus→VTA phylogenetic prior
            initial_weight=0.05,     # Reverted: w=1.0 (Phase1-fix) was 20× overshoot causing DA sat.
            # w=0.05 gives I_shadow=7×rate×0.05×1.0=0.175A at rate=0.5. Correct with gm=1.0.
            # "DA sleeps" at w=0.05 was due to gm=8.0 bug (saturation at V>0.135), not weight.
            weight_max=0.5,          # reduced ceiling consistent with innate prior weight
            stdp_lr=0.005,           # retained for reference but unused (frozen)
            synapse_gain=1.0,        # col activation is now bounded by spiking
            bundle_role="feedforward",
            remodel_cost_kappa=0.002,
        )
        self.bundles_shadow_to_da.append(
            SynapticBundle(cfg_shadow, shadow_cols, da_list))

        # ── 2. Xin relay → DA (phasic pathway) ──
        # Xin relay neuron carries |dξ/dt| from main layer.
        # Sudden prediction error changes → phasic DA burst.
        # 1 source × act × w(0.1) × gain(0.5) = modest phasic addition
        cfg_xin = BundleConfig(
            bundle_id="xin_to_da",
            learning_rule="frozen",  # INNATE: prediction_error→VTA phylogenetic prior
            initial_weight=0.1,      # Reverted: w=5.0 (Phase1-fix) was 50× overshoot.
            # w=0.1 gives I_xin=relay_act×0.1×0.5=0.025A at relay_act=0.5. Correct with gm=1.0.
            weight_max=1.0,          # xin pathway is phasic; ceiling matches innate prior
            stdp_lr=0.003,           # retained for reference but unused (frozen)
            synapse_gain=0.5,        # moderate: 1 source, phasic
            bundle_role="feedforward",
            remodel_cost_kappa=0.001,
        )
        self.bundles_xin_to_da.append(
            SynapticBundle(cfg_xin, [self._xin_relay], da_list))

        # ── 3a. Lamina I spinoparabrachial projection neurons (母本分化) ──
        # BIO: Spinal lamina I projection neurons distinct from lamina V WDR relay neurons.
        # REF: Todd 2010, Nat Rev Neurosci; Craig 2003, J Comp Neurol; Dayan & Abbott 2001.
        # Lamina V WDR relay neurons (relay_neurons) output UNBOUNDED activation (~0-10).
        # Projecting them directly to DA causes saturation (DA=2.019 observed, EXP-017).
        # Fix: add intermediate lamina I proj neurons with spiking+CRI → calcium_rate ∈ [0,1].
        # Zener clamp v_clamp=1.0 guarantees bounded output regardless of relay activation.
        #
        # Q1. BIO: lamina I spinoparabrachial neurons project to PBN→VTA (Todd 2010)
        # Q2. relay → relay_to_proj (frozen) → _soma_proj (spiking+CRI) → relay_to_da (STDP)
        # Q3. initial_weight=0.3 (innate strong laminar projection);
        #     v_peak=0.05 (fires when relay.act > 0.05/G(0.3) = 0.35, i.e., d<12 from heat);
        #     PROBE: relay.act max ≈ 0.84 (d=5), V_ss_proj=0.119 V >> v_peak=0.05 ✓
        #     C=0.1, R=1.0 → τ=0.1ms (fast follower, tracks relay instantaneously)
        for pid in self.somatosensory.patch_ids:
            cfg_proj = NeuronConfig(
                neuron_id=f"soma_proj_{pid}",
                capacitance=0.1,      # τ=0.1ms: fast follower of relay
                r_leak=1.0,
                inertia=1.0,
                vdd=1.0,
                r_supply=0.05,
                spiking=True,
                v_peak=0.05,          # fires when relay.act > 0.35 (d<12 from heat source)
                v_reset=0.001,
                b_adapt=0.0,          # no adaptation: tonic projection
                use_calcium_rate_integrator=True,
                cri_r_leak=50.0,      # τ_CRI=50 time-units; smooth rate estimate
                cri_q_spike=0.2,      # standard charge per spike (matches shadow cols)
                cri_v_clamp=1.0,      # Zener: calcium_rate ∈ [0, 1] → DA saturation fixed
                use_voltage_regulator=True,
                vr_base_rate=0.01,
                vr_activity_coeff=0.3,
                vr_max_rate=3.0,
            )
            self._soma_proj[pid] = Neuron(cfg_proj)

        relay_sources = list(self.somatosensory.relays.values())
        proj_list = list(self._soma_proj.values())

        # ── 3b. relay → proj bundles (one per patch, frozen innate pathway) ──
        for i, pid in enumerate(self.somatosensory.patch_ids):
            cfg_r2p = BundleConfig(
                bundle_id=f"relay_to_proj_{pid}",
                learning_rule="frozen",   # INNATE: lamina V → lamina I anatomy
                initial_weight=0.3,       # PROBE: relay.act=0.84 → V_ss_proj=0.119>v_peak=0.05 ✓ (d<12)
                weight_max=1.0,
                synapse_gain=1.0,
                bundle_role="feedforward",
                remodel_cost_kappa=0.0,
            )
            self._bundles_relay_to_proj.append(
                SynapticBundle(cfg_r2p, [relay_sources[i]], [proj_list[i]]))

        # ── 3c. Proj → DA (directional thermal pathway, STDP) ──
        # HC-002 fix: patch-specific bundles replace all-to-all.
        # Old: 1 bundle, sources=[4 proj], targets=[3 DA] → single 4×3 weight matrix;
        #      all patches share one STDP trajectory → direction information lost.
        # New: 4 bundles, each sources=[1 proj_pid], targets=[3 DA] → 4 independent 1×3
        #      weight matrices; each patch's STDP evolves separately → direction preserved.
        #
        # BIO: VTA DA neurons receive topographically segregated spinal input
        #      via PBN (parabrachial nucleus) → spatial heat direction preserved.
        #      REF: Todd 2010 NRN; Schultz 1997 Science 275:1593; Dayan & Abbott 2001 §9.1.
        #
        # Q3. Saturation unchanged: max I_da = 4 × 1.0 × G(0.3) × 0.2 = 0.114 A (identical
        #     to old all-to-all, since total contribution from 4 patch bundles is the same).
        for pid in self.somatosensory.patch_ids:
            proj = self._soma_proj.get(pid)
            if proj is None:
                continue
            cfg_relay = BundleConfig(
                bundle_id=f"relay_to_da_{pid}",
                learning_rule="stdp",
                # BIO: three-factor eligibility-trace Hebbian learning (Izhikevich 2007
                # Cereb Cortex 17:2443; Gerstner et al. 2018 Nat Neurosci 21:555).
                # DA gates LTP via eligibility trace E(pre,post); LTD also DA-gated,
                # so weights are frozen during DA-quiet periods (prevents constitutive
                # erasure by two-factor STDP decay when body is stationary near source).
                use_eligibility_trace=True,
                eligibility_tau=300.0,           # default ~300ms trace window
                eligibility_gain=1.0,             # default
                eligibility_ltd_rate=0.01,        # DA-dep LTD, negligible when DA quiet
                decay_rate_by_stage=(0.001, 0.0005, 0.0001),  # has dt factor in elig-mode
                initial_weight=0.1,
                weight_max=0.3,       # G(0.3)=0.142; 4×G(0.3)×0.2=0.114A total ✓
                stdp_lr=0.005,        # BIO: Bi & Poo 1998 (thalamo-cortical-VTA)
                synapse_gain=0.2,     # thermal modulation ~0.1V on 0.83V baseline
                bundle_role="feedforward",
                remodel_cost_kappa=0.001,
            )
            self.bundles_relay_to_da.append(
                SynapticBundle(cfg_relay, [proj], da_list))

        # ── 4. CPG → DA (VTA pacemaker oscillation, frozen) ──
        # BIO: VTA interneurons provide 2 Hz intrinsic rhythmic drive to DA neurons
        #      (Grace & Bunney 1984). Keeps DA.post_trace = |d(act)/dt| > 0 at
        #      steady state so relay_to_da STDP continues during d<12 proximity.
        # Q1. BIO: VTA pacemaker → rhythmic excitation of DA projection neurons.
        # Q2. CPGNeuron → bundles_cpg_to_da[frozen] → all da_neurons.
        # Q3. amplitude=0.05 → activation ∈ [0, 0.10]; w=0.1 (G≈0.111); gain=1.0
        #     → I_peak ≈ 0.011A; V_DA_osc ≈ 0.011V ∈ ε∈(0.001, 0.024V) ✓
        self._da_cpg = CPGNeuron(
            frequency=2.0,     # BIO: 2Hz VTA pacemaker (Grace & Bunney 1984)
            amplitude=0.005,   # PHASE-B: 10× reduction (0.05→0.005). Retains post_trace
                               # baseline during body-away periods without dominating DA;
                               # ThermalDeltaNeuron (dT/dt>0) provides the causal burst.
            mu=2.0,            # relaxation mode (pulse-like, same as VitalOscillator)
            neuron_id="vta_cpg",
        )
        cfg_cpg = BundleConfig(
            bundle_id="cpg_to_da",
            learning_rule="frozen",    # INNATE: VTA intrinsic oscillation anatomy
            initial_weight=0.1,        # G(0.1)≈0.111; I_peak=0.10×0.111=0.011A ✓
            weight_max=0.1,            # cap at initial — innate, not plastic
            # EXP-BASE-200K: CPG 2Hz phasic DA caused 82% LTD in relay_to_da (tonic
            # relay vs phasic CPG → anti-correlated STDP). Reduce 10× to suppress LTD
            # while retaining 10% residual to keep post_trace > 0 during quiet periods.
            synapse_gain=0.1,
            bundle_role="feedforward",
            remodel_cost_kappa=0.0,    # no remodeling cost — structural innate pathway
        )
        self.bundles_cpg_to_da.append(
            SynapticBundle(cfg_cpg, [self._da_cpg], da_list))

        # ── 5. Warm-onset → DA: ThermalDeltaNeuron per skin patch (frozen) ──
        # BIO: Type II AMH (Aδ) warm-onset fibers → Lamina I → LPB → VTA DA.
        #      Fires when body enters warm field (dT/dt > 0); drives phasic DA
        #      correlated with relay activation → relay_to_da STDP → LTP.
        # REF: Norris et al. 2021 Nat Neurosci 24:1407 — LPB→VTA thermal reward.
        # REF: LaMotte & Campbell 1978 J Neurophysiol 41:924 — Type II AMH.
        # Q2. ThermalDeltaNeuron[pid] → frozen bundle → all da_neurons.
        # Q3. See make_thermo_delta_to_da_bundle() docstring for derivation.
        _SKIN_POS = {'front': (2, 0, 0), 'back': (-2, 0, 0),
                     'left': (0, -2, 0), 'right': (0, 2, 0)}
        for pid in self.somatosensory.patch_ids:
            pos = _SKIN_POS.get(pid, (0.0, 0.0, 0.0))
            dn = ThermalDeltaNeuron(patch_id=pid, position=pos)
            self.thermo_delta_neurons[pid] = dn
            self.bundles_thermo_delta_to_da.append(
                make_thermo_delta_to_da_bundle(pid, dn, da_list))

        # ── 6. Relay-layer lateral inhibition (Winner-Take-All) ──
        # P0-B Phase B structural fix: cross-inhibition between relay channels.
        # Q1. BIO: horizontal-cell / granule-cell antagonistic surround inhibition.
        #     REF: Hartline & Ratliff 1957 J Gen Physiol; Shepherd 1972 Physiol Rev.
        #     In skin: spinal interneurons mediate lateral inhibition between
        #     spatially adjacent relay (WDR) neurons (Brown & Franz 1969 J Physiol).
        # Q2. relay_{src} (non-spiking) → BundleConfig(frozen, gain=-1.0) → relay_{tgt}.
        #     Four antipodal pairs: rl, lr, fb, bf.
        # Q3. initial_weight=0.3: G(0.3)≈0.142; at relay_src.act=1.3 (hot side):
        #     I_inh = 1.3 × 0.142 × (-1.0) ≈ -0.18 A  → suppresses relay_tgt.
        #     Adjust to -2.0 if WTA not clean enough in 100k verification.
        _LATERAL_INH_PAIRS = [
            ('relay_lateral_inh_rl', 'right', 'left'),
            ('relay_lateral_inh_lr', 'left',  'right'),
            ('relay_lateral_inh_fb', 'front', 'back'),
            ('relay_lateral_inh_bf', 'back',  'front'),
        ]
        _relays = self.somatosensory.relays
        for bid, src_pid, tgt_pid in _LATERAL_INH_PAIRS:
            src_n = _relays.get(src_pid)
            tgt_n = _relays.get(tgt_pid)
            if src_n is None or tgt_n is None:
                continue
            cfg_inh = BundleConfig(
                bundle_id=bid,
                learning_rule="frozen",
                initial_weight=0.3,
                weight_max=0.3,
                synapse_gain=-1.0,      # inhibitory: suppresses competing relay channel
                bundle_role="feedforward",
                remodel_cost_kappa=0.0,
            )
            self.bundles_relay_lateral_inh.append(
                SynapticBundle(cfg_inh, [src_n], [tgt_n]))

        # ── C1: shadow_nu_neuron → DA (free energy gate, frozen) ──
        # shadow_nu_neuron is already created in __init__; create the bundle here
        # because we need da_list (not available at __init__ time in current lazy pattern).
        cfg_nu = BundleConfig(
            bundle_id='shadow_nu_to_da',
            learning_rule='frozen',
            initial_weight=0.3,
            weight_max=0.3,
            synapse_gain=1.0,
            bundle_role='feedforward',
            remodel_cost_kappa=0.0,
        )
        self.bundle_shadow_nu_to_da = SynapticBundle(
            cfg_nu, [self.shadow_nu_neuron], da_list)

        self._da_circuit_initialized = True

        # Log to growth log (same as sprout events)
        self._growth_log.append(
            f"DA_CIRCUIT_INIT step={self._step_count} "
            f"shadow_cols={len(shadow_cols)} da_neurons={len(da_list)} "
            f"proj_neurons={len(self._soma_proj)} "
            f"bundles=shadow_to_da+xin_to_da+relay_to_proj({len(self._bundles_relay_to_proj)})"
            f"+relay_to_da({len(self.bundles_relay_to_da)})+cpg_to_da({len(self.bundles_cpg_to_da)})"
            f"+relay_lateral_inh({len(self.bundles_relay_lateral_inh)})"
            f"+shadow_nu_to_da(1)"
        )

    # ── P2-HC007: relay→enc STDP initialization ──────────────────

    def _init_relay_to_enc(self):
        """Create relay→enc STDP bundles replacing HC-007 direct injection.

        HC-007 was: enc_reg.step(relay.activation * EXTRA_AXIS_GAIN, dt)
        This fix routes the signal through a SynapticBundle with STDP so
        the thalamo-cortical thermal pathway can strengthen with experience.

        Q1. BIO: Spinal relay (lamina V WDR, STT) → VPL thalamus → S1 cortex.
            REF: Willis 1985 (STT anatomy); Craig 2003 (lamina I→VPL);
                 Kandel et al. 2013, Principles of Neural Science §23.
        Q2. relay_{pid} (non-spiking) → bundle → reg_therm_{pid} (non-spiking enc).
            One 1-to-1 bundle per patch: front/back/left/right.
        Q3. initial_weight=0.0: G(0) × sg = 0.1 × 0.4 = 0.04 = EXTRA_AXIS_GAIN
                                (HC-007 parity at w=0 — no behavior change initially).
            weight_max=0.4: max I = relay.act × 0.166 × 0.4 = relay.act × 0.066
                            (64% above baseline, safe for enc_reg input range).
            stdp_lr=0.005: BIO: Bi & Poo 1998, J Neurosci 18:10464 (thalamo-cortical).
            synapse_gain=0.4: calibrated — G(w=0)=1/r_max=0.1; 0.1×0.4=0.04=EXTRA_AXIS_GAIN.
        """
        _EXTRA_AXIS_GAIN = 0.04  # must match HebbianCircuit EXTRA_AXIS_GAIN constant
        _G_w0 = 0.1              # G(w=0) = 1/r_max = 1/10.0 (Memristor default)

        for pid in self.somatosensory.patch_ids:
            enc_reg = self.encoding_neurons.get(f"reg_therm_{pid}")
            relay = self.somatosensory.relays.get(pid)
            if enc_reg is None or relay is None:
                continue
            cfg = BundleConfig(
                bundle_id=f"relay_to_enc_{pid}",
                learning_rule="stdp",
                initial_weight=0.0,                          # G(0)×sg=0.04=EXTRA_AXIS_GAIN ✓
                weight_max=0.4,                              # caps max thermal injection
                stdp_lr=0.005,                               # BIO: Bi & Poo 1998
                synapse_gain=_EXTRA_AXIS_GAIN / _G_w0,      # = 0.4: HC-007 parity at w=0
                bundle_role="feedforward",
                remodel_cost_kappa=0.001,
            )
            self.bundles_relay_to_enc.append(SynapticBundle(cfg, [relay], [enc_reg]))

        self._growth_log.append(
            f"RELAY_TO_ENC_INIT step=0 "
            f"bundles={len(self.bundles_relay_to_enc)} "
            f"patches={list(self.somatosensory.patch_ids)}"
        )

    def _init_yaw_bundles(self):
        """HC-016 A: thermo_input[left/right] → yaw_ccw/cw neurons via frozen SynapticBundles.

        Replaces direct T_left−T_right Python subtraction with structural push-pull.
        Uses ThermalInputNeuron (raw thermoreceptor), NOT relay neurons — relay neurons
        have lateral inhibition from front/back that corrupts left-right direction signal.

        Q1. BIO: thermoreceptive Aδ/C-fibers project via DIRECT spinal reflex arc to
            contralateral motor neurons (spinoreticular pathway, bypassing thalamus).
            This is the INNATE reflex; relay pathway handles associative learning separately.
            REF: Mori & Ohshima 1995 Nature 376:344 (C. elegans thermotaxis reflex);
                 Kandel et al. 2013 PoNS Ch.23 (crossed spinal reflex arcs).
        Q2. thermo_inputs['left']  → [frozen, sg=1.0] → yaw_ccw_neuron (CCW when left warm)
            thermo_inputs['right'] → [frozen, sg=1.0] → yaw_cw_neuron  (CW when right warm)
        Q3. initial_weight=0.3: thermo.act≈0.3@T=4 → G(0.3)≈0.142 → I≈0.043A
            → V_ss_yaw≈0.21 (r_leak=5). Net torque at ΔT=4: 0.21×0.1=0.021 ≈ existing
            T_diff×0.1 at ΔT=2 (≈0.2 after inertia). YAW_GAIN=0.1 preserved (EXP-W2-003).
        """
        thermo_left = self.somatosensory.thermo_inputs.get("left")
        thermo_right = self.somatosensory.thermo_inputs.get("right")
        if thermo_left is None or thermo_right is None:
            return

        cfg_left = BundleConfig(
            bundle_id="thermo_left_to_yaw_ccw",
            learning_rule="frozen",
            initial_weight=0.3,    # Q3: thermo.act×G(0.3)×1.0≈0.043A → V_ss≈0.21
            weight_max=0.3,
            synapse_gain=1.0,
            bundle_role="feedforward",
            remodel_cost_kappa=0.0,
        )
        cfg_right = BundleConfig(
            bundle_id="thermo_right_to_yaw_cw",
            learning_rule="frozen",
            initial_weight=0.3,
            weight_max=0.3,
            synapse_gain=1.0,
            bundle_role="feedforward",
            remodel_cost_kappa=0.0,
        )
        self.bundle_left_to_yaw = SynapticBundle(cfg_left, [thermo_left], [self.yaw_ccw_neuron])
        self.bundle_right_to_yaw = SynapticBundle(cfg_right, [thermo_right], [self.yaw_cw_neuron])

    def _init_brake_bundle(self):
        """接口三：接近→制动束，反射弧初始化。"""
        thermo_front = self.somatosensory.thermo_inputs.get('front')
        motor_x = self.motor_neurons.get('move_x')
        if thermo_front is None or motor_x is None:
            return
        cfg = BundleConfig(
            bundle_id="thermo_front_to_motor_brake",
            learning_rule="frozen",
            initial_weight=0.3,
            weight_max=0.3,
            # g_brake = -0.5 [A/°C]: 正权重 + 负增益 = 净抑制（weight_min=0.0 不支持负权重）
            synapse_gain=-0.5,
            bundle_role="feedforward",
            remodel_cost_kappa=0.0,
        )
        self.bundle_front_to_brake = SynapticBundle(cfg, [thermo_front], [motor_x])

    def _init_efference_bundle(self):
        """接口一：Motor 传出副本 — 脊髓前角轴突侧枝 → hypothalamus_effort。

        BIO: corollary discharge / Reafferenzprinzip (von Holst & Mittelstaedt 1950).
        REF: Wolpert & Kawato 1998 Trends Cogn Sci 2:338 (internal forward model).
        PHYS: frozen Bundle (axiom: efference copy weight is phylogenetically fixed,
              not learned — the brain knows it's sending a motor command always).

        g_efference = initial_weight × synapse_gain = 0.1 [A/activation_unit]
        EXP: motor_x.act≈0.5（body 运动时）→ I_effort=0.05A → V_ss=0.25V
             → act_effort=max(0, 0.25-0.01)=0.24（v_thresh=0.01，低阈值跟踪）
        """
        motor_x = self.motor_neurons.get('move_x')
        if motor_x is None:
            return

        # hypothalamus_effort：下丘脑运动努力感知节点
        # v_thresh=0.01（同 yaw_ccw/cw）：即使微弱 Motor 也有激活
        self.hypothalamus_effort = Neuron(NeuronConfig(
            neuron_id="hypothalamus_effort",
            channels=[ChannelConfig(name="default", v_threshold=0.01, gm=1.0)],
            spiking=False,
            position=[55, 50, 45],
        ))

        cfg = BundleConfig(
            bundle_id="motor_x_to_hypothalamus_effort",
            learning_rule="frozen",
            initial_weight=0.1,
            weight_max=0.1,
            synapse_gain=1.0,
            bundle_role="feedforward",
            remodel_cost_kappa=0.0,
        )
        self.bundle_motor_to_effort = SynapticBundle(
            cfg, [motor_x], [self.hypothalamus_effort])

    def _init_energy_sensing(self):
        """接口二：能量感知链 — ARC K_ATP → LH → VTA。

        替代 HC: _hunger_da = max(0, 1.0*(0.5 - fill_fraction))。
        BIO: ARC nucleus AgRP/NPY neurons fire when K_ATP opens (low ATP).
             Lateral hypothalamus integrates, drives VTA DA tonic under hunger.
        REF: Spanswick 1997 Nature 390:521-525 (K_ATP channels in ARC);
             Saper 2002 Nature 417:833-838 (LH integrator);
             Wise 2004 Nat Rev Neurosci 5:483-494 (LH→VTA hunger DA).

        PHYS: g_energy_sense=1.0 [A/unit] — normalized K_ATP transconductance.

          Q3 激活阈值确认（fill<0.44 vs 原HC fill<0.5，差异=0.06，约12%）：
            成因：sensor v_threshold=0.3 [V]（NeuronConfig默认），r_leak=5.0 [Ω]（Neuron默认）
            死区计算：fill_boundary = 0.5 − v_threshold/(G_E×r_leak)
                                     = 0.5 − 0.3/(1.0×5.0) = 0.5 − 0.06 = 0.44
            生物依据：K_ATP通道实际开放阈值在胞内ATP约40-45%耗竭时（非精确50%）。
                     REF: Nichols & Lederer 1991 Am J Physiol（K_ATP gate Hill coefficient~2,
                          half-activation [ATP]₀.₅ ≈ 100 µM vs 静息 ~5 mM，≈2%，但
                          功能意义上约40-50%储量时通道开始有效驱动膜电位）。
            裁决：fill<0.44 是有意接受的物理近似（MOSFET死区内生于半导体原语），
                 等效于 K_ATP 通道的亚阈偏移，不需要调整 G_E。

          w_s2a=0.1: 3传感器 → act_avg≈3.0（fill=0时，sensor饱和）
          w_a2h=0.1: act_avg=3.0 → act_hunger≈1.2
          w_h2d=0.04: act_hunger=1.2 × 0.04 ≈ 0.05 ≈ 原_hunger_da×0.1（fill=0时）
          数值推导: target da_current=0.05A（fill=0），act_hunger=1.2 → w=0.05/1.2≈0.04
        """
        # 3个弥散分布 ARC 感受器（体内部，间距≥10mm）
        # NeuronConfig 默认 = simple 模式（单 MOSFET channel，default v_threshold=0.3）
        sensor_positions = [[55, 45, 35], [55, 55, 55], [55, 45, 65]]
        for k, pos in enumerate(sensor_positions):
            cfg = NeuronConfig(
                neuron_id=f"energy_sensor_{k}",
                position=pos,
            )
            self.energy_sensors.append(Neuron(cfg))

        # AverageEnergyNeuron：LH 整合（多传感器的空间平均）
        self.average_energy_neuron = Neuron(NeuronConfig(
            neuron_id="average_energy",
            position=[55, 50, 50],
        ))

        # hypothalamus_hunger：LH output → VTA
        self.hypothalamus_hunger = Neuron(NeuronConfig(
            neuron_id="hypothalamus_hunger",
            position=[55, 50, 55],
        ))

        # Bundle: sensors → average (frozen, w=0.1/sensor)
        # 3传感器并联 → average：每sensor权重0.1，合计电流≈3×act×0.1
        cfg_sa = BundleConfig(
            bundle_id="energy_sensors_to_average",
            learning_rule="frozen",
            initial_weight=0.1,
            weight_max=0.1,
            synapse_gain=1.0,
            bundle_role="feedforward",
            remodel_cost_kappa=0.0,
        )
        self.bundle_sensors_to_average = SynapticBundle(
            cfg_sa, self.energy_sensors, [self.average_energy_neuron])

        # Bundle: average → hunger (frozen, w=0.1)
        # act_avg≈3.0 → input_hunger=0.3A → vm_hunger=1.5V → act_hunger≈1.2（fill=0）
        cfg_ah = BundleConfig(
            bundle_id="energy_average_to_hunger",
            learning_rule="frozen",
            initial_weight=0.1,
            weight_max=0.1,
            synapse_gain=1.0,
            bundle_role="feedforward",
            remodel_cost_kappa=0.0,
        )
        self.bundle_average_to_hunger = SynapticBundle(
            cfg_ah, [self.average_energy_neuron], [self.hypothalamus_hunger])

        # Bundle: hunger → DA neurons (frozen, w=0.04)
        # act_hunger=1.2 × w=0.04 ≈ 0.05 A = 等效原 _hunger_da × DA_INJECT_SCALE（fill=0时）
        cfg_hd = BundleConfig(
            bundle_id="hunger_to_da",
            learning_rule="frozen",
            initial_weight=0.04,
            weight_max=0.04,
            synapse_gain=1.0,
            bundle_role="feedforward",
            remodel_cost_kappa=0.0,
        )
        self.bundle_hunger_to_da = SynapticBundle(
            cfg_hd, [self.hypothalamus_hunger], list(self.da_neurons.values()))

    # ── Override get_all_neurons/bundles to include DA components ──

    def get_all_neurons(self):
        """Include DA neurons, Xin relay, and somatosensory in neuron census.

        Noether probe, entropy ledger, and vascular energy delivery
        all enumerate neurons via this method. Every neuron must be
        included for correct energy/weight conservation checks.

        Prior to P1-FIX: somatosensory chain (therm_, noci_, relay_)
        was excluded → invisible to ledger, no vascular energy delivery,
        Noether conservation balance incomplete. EXP-016b confirmed
        zero behavioral impact from nociceptor parameter changes.
        """
        neurons = super().get_all_neurons()
        neurons.extend(self.da_neurons.values())
        neurons.append(self._xin_relay)
        # P1-FIX: somatosensory chain neurons (therm_, noci_, relay_)
        neurons.extend(self.somatosensory.get_all_neurons())
        # P1-DIFF: lamina I spinoparabrachial projection neurons
        neurons.extend(self._soma_proj.values())
        # P2-FIX: shadow sandbox neurons (s_enc, s_col, s_mot) — visible to ledger/Noether
        if self.shadow_sandbox._initialized:
            neurons.extend(self.shadow_sandbox.neurons.values())
        # Warm-onset transducers (thermo_delta_{pid}) — LPB→VTA arm
        neurons.extend(self.thermo_delta_neurons.values())
        # HC-016 A: yaw push-pull motor neurons (crossed thermotaxis reflex)
        neurons.append(self.yaw_ccw_neuron)
        neurons.append(self.yaw_cw_neuron)
        # 接口二：能量感知链神经元（ARC传感器、LH整合、下丘脑hunger）
        neurons.extend(self.energy_sensors)
        if self.average_energy_neuron is not None:
            neurons.append(self.average_energy_neuron)
        if self.hypothalamus_hunger is not None:
            neurons.append(self.hypothalamus_hunger)
        # 接口一：Motor efference copy → hypothalamus_effort
        if self.hypothalamus_effort is not None:
            neurons.append(self.hypothalamus_effort)
        # B1a: CPC deviation transducer + vital amplitude integrator
        neurons.append(self.cpc_dev_neuron)
        neurons.append(self.vital_amp_neuron)
        # B1b: Renshaw interneurons (spinal lateral inhibition)
        neurons.extend(self.renshaw_neurons.values())
        # C1: shadow ν → DA boundary transducer
        neurons.append(self.shadow_nu_neuron)
        # D1: phasic relay arc neurons NOT included in vascular census.
        # Adding them dilutes energy_per_neuron → changes ECM gate_col → breaks
        # col→motor STDP selectivity (T4.1 regression). D1 neurons are passive
        # (non-spiking, non-energy-limited) so vascular exclusion is safe.
        # D1 bundles ARE in get_all_bundles() for Noether/Xin bookkeeping.
        return neurons

    def get_all_bundles(self):
        """Include DA input bundles and somatosensory bundles in census.

        Noether weight balance check, Xin bookkeeping, and sprout/prune
        all enumerate bundles via this method. All bundles must be
        included for correct entropy ledger accounting.

        Prior to P1-FIX: somatosensory bundles (thermo_to_relay,
        noci_to_relay, lateral) were excluded → weight entropy blind,
        Xin tension not accumulated, metabolic tax not applied.
        """
        bundles = super().get_all_bundles()
        bundles.extend(self.bundles_shadow_to_da)
        bundles.extend(self.bundles_xin_to_da)
        bundles.extend(self.bundles_relay_to_da)
        # P1-DIFF: relay → proj bundles (lamina I projection pathway)
        bundles.extend(self._bundles_relay_to_proj)
        # P1-FIX: somatosensory chain bundles
        bundles.extend(self.somatosensory.get_all_bundles())
        # P2-HC007: relay→enc STDP bundles (thalamo-cortical thermal encoding)
        bundles.extend(self.bundles_relay_to_enc)
        # CPG → DA pacemaker pathway (frozen, visible for Noether/Xin accounting)
        bundles.extend(self.bundles_cpg_to_da)
        # Warm-onset → DA (frozen, LPB→VTA innate pathway)
        bundles.extend(self.bundles_thermo_delta_to_da)
        # P0-B: Relay lateral inhibition (frozen WTA cross-inhibition)
        bundles.extend(self.bundles_relay_lateral_inh)
        # HC-016 A: relay→yaw frozen bundles (crossed thermotaxis reflex arc)
        if self.bundle_left_to_yaw is not None:
            bundles.append(self.bundle_left_to_yaw)
        if self.bundle_right_to_yaw is not None:
            bundles.append(self.bundle_right_to_yaw)
        # 接口三：接近→制动束
        if self.bundle_front_to_brake is not None:
            bundles.append(self.bundle_front_to_brake)
        # 接口二：能量感知链 Bundle（ARC→LH→hunger→DA）
        if self.bundle_sensors_to_average is not None:
            bundles.append(self.bundle_sensors_to_average)
        if self.bundle_average_to_hunger is not None:
            bundles.append(self.bundle_average_to_hunger)
        if self.bundle_hunger_to_da is not None:
            bundles.append(self.bundle_hunger_to_da)
        # 接口一：Motor efference copy Bundle
        if self.bundle_motor_to_effort is not None:
            bundles.append(self.bundle_motor_to_effort)
        # B1a: CPC deviation → VitalOscillator amplitude modulation
        bundles.append(self.bundle_cpc_to_vital)
        # B1b: Renshaw lateral inhibition bundles
        bundles.extend(self.bundles_renshaw_excit)
        bundles.extend(self.bundles_renshaw_inhib)
        # C1: shadow ν → DA gate (lazy: only after _init_da_circuit)
        if self.bundle_shadow_nu_to_da is not None:
            bundles.append(self.bundle_shadow_nu_to_da)
        # D1: phasic relay arc bundles
        for _b in [self.bundle_relay_to_slow_left, self.bundle_relay_to_slow_right,
                   self.bundle_relay_to_phasic_left, self.bundle_relay_to_phasic_right]:
            if _b is not None:
                bundles.append(_b)
        bundles.extend([self.bundle_slow_to_phasic_left, self.bundle_slow_to_phasic_right,
                        self.bundle_d1_phasic_left_to_spinal_ccw,
                        self.bundle_d1_phasic_right_to_spinal_cw,
                        self.bundle_spinal_ccw_to_yaw, self.bundle_spinal_cw_to_yaw])
        return bundles

    @property
    def bundles_soma_to_da(self):
        """Alias for bundles_relay_to_da — backward compat with Phase 5-8 scripts."""
        return self.bundles_relay_to_da

    # ── V2.0 Spatial scaffold ──────────────────────────────────────

    @property
    def neuron_positions(self):
        """Map neuron_id → (x, y, z) position in mm (or None if unpositioned).

        REF: NeuronConfig.position field added in V2.0 spatial scaffold (commit b2597b3).
        Foundation for V2.0 features:
          - Distance matrix D[i][j] = d_ij for τ_ij synaptic delay
          - P_S = η_s × (dw/dt)² × d_ij distance-penalized STDP
        None entries = neurons without assigned anatomical position.
        """
        return {n.config.neuron_id: n.config.position for n in self.get_all_neurons()}

    @property
    def distance_matrix(self):
        """Pairwise distance matrix D[nid_a][nid_b] = d_mm for positioned neurons.

        Only includes neurons where position != None (currently 24 vestibular neurons).
        O(n²) with n=24 positioned neurons → 576 pairs, computed on access.
        REF: Highstein & Holstein 2006 labyrinth geometry (positions from neuron_positions).
        Used for V2.0 τ_ij = d_ij / (v_cond × dt) conduction delay scaffold.
        """
        import math as _math
        positions = {nid: p for nid, p in self.neuron_positions.items() if p is not None}
        nids = list(positions.keys())
        matrix = {}
        for a in nids:
            pa = positions[a]
            matrix[a] = {
                b: _math.sqrt(sum((pa[k] - positions[b][k]) ** 2 for k in range(3)))
                for b in nids
            }
        return matrix

    # ── Maturation lifecycle (§3.1 of math spec) ──────────────────

    # Transition thresholds
    _MATURATION_THRESHOLDS = {
        # spine→column: PNN > 0.3 AND Φ > 50
        0: {"pnn_threshold": 0.3, "phi_threshold": 50.0},
        # column→area: PNN > 0.7 AND Φ > 500
        1: {"pnn_threshold": 0.7, "phi_threshold": 500.0},
    }

    def _check_maturation_transitions(self):
        """Check and execute maturation phase transitions (§3.1).

        Called periodically (~every 1000 steps).
        Transition condition: PNN > θ AND Φ > Φ_threshold.
        """
        # Map neurons to their layer's ECM for PNN readout
        layer_ecm = {}
        for key in self.encoding_neurons:
            layer_ecm[f"enc_{key}" if not key.startswith("enc_") else key] = self.ecm_encoding
        for key in self.column_neurons:
            layer_ecm[f"col_{key}" if not key.startswith("col_") else key] = self.ecm_column

        for n in list(self.encoding_neurons.values()) + list(self.column_neurons.values()):
            cfg = n.config
            stage = getattr(cfg, 'maturation_stage', 0)
            if stage >= 2:
                continue  # already at area (max)

            thresholds = self._MATURATION_THRESHOLDS.get(stage)
            if thresholds is None:
                continue

            # Get PNN maturity from the neuron's layer ECM
            ecm = layer_ecm.get(n.id)
            if ecm is None:
                continue
            pnn = ecm.pnn_maturity

            phi = getattr(cfg, 'potential_phi', 0.0)

            if pnn > thresholds["pnn_threshold"] and phi > thresholds["phi_threshold"]:
                cfg.maturation_stage = stage + 1

    # ── Crystallization detection (§8.1) ──────────────────────────

    @staticmethod
    def _is_crystallized(bundle) -> bool:
        """Check if a bundle is crystallized (§8.1).

        Conditions: target at area stage AND weight variance < 0.01.
        """
        max_m = 0
        for tgt in bundle.targets:
            m = getattr(tgt.config, 'maturation_stage', 0)
            if m > max_m:
                max_m = m
        if max_m < 2:
            return False

        weights = [m.w for row in bundle._memristors for m in row]
        if not weights:
            return False
        mean_w = sum(weights) / len(weights)
        var_w = sum((w - mean_w) ** 2 for w in weights) / len(weights)
        return var_w < 0.01

    # ── Shadow Layer (§9, current active definition) ────────────
    # Current: burial + decay + resonance = ACTIVE
    # degraded_target = "hierarchical_variational_sandbox"
    # See modeling_shadow_dual_metric.md for the unverified advanced theory.

    def _shadow_maintenance(self):
        """Shadow layer maintenance (§9.1-9.3, active definition)."""
        if not hasattr(self, '_shadow_store'):
            self._shadow_store = []
            self._shadow_decay = 0.999

        # §9.1: Burial
        prune_threshold = 0.02
        for b in self.get_all_bundles():
            if b.mean_weight() < prune_threshold and b.config.xin_tension < 0:
                snapshot = {
                    'weights': [m.w for row in b._memristors for m in row],
                    'xin': b.config.xin_tension,
                    'energy': 1.0,
                    'bundle_id': b.id,
                }
                self._shadow_store.append(snapshot)

        # §9.2: Decay
        expired = []
        for i, entry in enumerate(self._shadow_store):
            entry['energy'] *= self._shadow_decay
            if entry['energy'] < 0.01:
                expired.append(i)
        for i in reversed(expired):
            self._shadow_store.pop(i)

        # §9.3: Resonance (cosine similarity, record only)
        for entry in self._shadow_store:
            for b in self.get_all_bundles():
                live_w = [m.w for row in b._memristors for m in row]
                shadow_w = entry['weights']
                if len(live_w) != len(shadow_w):
                    continue
                dot = sum(a * s for a, s in zip(live_w, shadow_w))
                n_l = sum(a ** 2 for a in live_w) ** 0.5
                n_s = sum(a ** 2 for a in shadow_w) ** 0.5
                if n_l > 1e-8 and n_s > 1e-8:
                    if dot / (n_l * n_s) > 0.9:
                        entry['echo_count'] = entry.get('echo_count', 0) + 1

        # Cap size
        max_shadow = len(self.get_all_bundles()) * 3
        if len(self._shadow_store) > max_shadow:
            self._shadow_store = self._shadow_store[-max_shadow:]

