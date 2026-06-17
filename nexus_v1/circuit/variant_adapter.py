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
from ..components.binding import BindingLayer
from ..components.shadow_sandbox import ShadowSandbox
from ..components.world import World, Body, HeatSource
from ..components.thermal_membrane import ThermalMembrane
from ..components.muscle import MuscleSystem
from ..components.energy_store import EnergyStore
from ..somatosensory.chain import SomatosensoryChain
from ..components.vital_oscillator import VitalOscillator
from ..components.langevin_noise import LangevinNoise
from ..components.circulation_proportion import CirculationProportionCircuit
from .bundle import SynapticBundle, BundleConfig
from .circulation import CirculationMeter
from .motor_decision import MotorDecisionLayer, MotionState
from ..ledger import (WeightEntropyProbe, TOPRXinLedger, RecursionTracker,
                      UltrametricSpace, StructuralEntropy, StructuralBridge,
                      EntropyLedger, NoetherProbe,
                      SerialModificationLog, GuidedConstructionAuditor)

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
    """FIFO delay line for inter-layer heat propagation (A3 fix).

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
    """HebbianCircuit + variant components (oscillator + damper).

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
        # ── Mother initialization with thermal extra axis ──
        super().__init__(extra_axes=["therm"])

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
        # Uses ALL axes (vestibular + thermal) for cross-modal binding
        # C(7,2) = 21 binding cells (was C(6,2)=15 for vestibular only)
        self.binding_layer = BindingLayer(
            axes=list(self.all_axes),
            co_activation_threshold=0.05,
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

        # ── Variant: 3D World + Body + Thermal + Muscle ──
        # Heat source at [70,50,50], body starts at [50,50,50]
        self.world = World()
        self.thermal_membrane = ThermalMembrane()
        self.muscle_system = MuscleSystem(gain=0.1, delay=2)

        # ── Variant: VitalOscillator (步骤2 — 宏观传出轨) ──
        # Three-frequency detuned Van der Pol heart; injects into Motor membrane.
        # BIO: sinoatrial node → hemodynamic pulsation → postural sway (Collins 1993).
        # Energy from EnergyStore — death switch at fill < 0.05.
        self.vital_oscillator = VitalOscillator()

        # ── Variant: LangevinNoise (步骤2 — 微观传入轨) ──
        # OU process: σ₀=0.70 anchored by FDT + stochastic resonance optimum.
        # σ* ≈ θ_sys/√2 ≈ 0.07; T_bath≈0.01 → σ₀ = 0.07/√0.01 = 0.70.
        # BIO: endolymph thermal fluctuation → hair cell displacement.
        # REF: 皮层除颤与热力学大一统方案 §2.1-§2.3
        self._langevin = LangevinNoise()

        # ── Variant: SomatosensoryChain (V01) ──
        # 4 skin patches (front/back/left/right), each with:
        #   Thermoreceptor (tonic T) → Nociceptor (phasic dT/dt) → Relay (∇²T)
        # Provides 12 neurons + 12 bundles visible to all entropy ledger tools.
        # BIO: TRPV/TRPM thermoreceptors + spinal dorsal-horn relays.
        self.somatosensory = SomatosensoryChain()
        # Previous patch temperatures for dT/dt computation (one per patch)
        self._soma_prev_temps: dict = {pid: 0.0 for pid in self.somatosensory.patch_ids}

        # ── Variant: EnergyStore (external reservoir) ──
        # Bridges World.consume_nearby() → Vascular → neuron.energy.
        # External to neural circuit; can be replaced without rewiring.
        # BIO: liver glycogen + blood glucose buffer.
        self.energy_store = EnergyStore()

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

        # ── Variant: Guided Construction Auditor (V15) ──
        # Tracks serial modifications to pathways; flags 过渡自限.
        # READ-ONLY observer — never modifies circuit state.
        self._construction_auditor = GuidedConstructionAuditor()
        # Audit alert log: receives alerts from energy_ledger + weight_entropy
        self._ledger_alerts: List[str] = []

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
                channels=[ChannelConfig(name="default", v_threshold=0.01, gm=8.0)],
                # bc_current produces baseline activation ≈ 0.1
                # V_ss = bc * R = 0.1 * 1.0 = 0.1 (matches DA baseline)
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
                d2_da_r_leak=100.0,     # τ_D2 = 100 >> τ_membrane = 2 (50× ratio → stable)
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
        # B.06: Somatosensory relay → DA (structural thermal pathway)
        self.bundles_soma_to_da: List[SynapticBundle] = []

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

        # C2 fix: Cross-axis motor inhibition (push-pull)
        # Inject inhibitory current into motor neurons based on
        # other axes' activation. Strongest axis suppresses weakest.
        motor_inhib = self.motor_lateral_inhibition.compute_inhibition(axis_acts)
        motor_keys = ['move_x', 'move_y', 'move_z']
        for idx, mkey in enumerate(motor_keys):
            if motor_inhib[idx] < 0:
                mot = self.motor_neurons[mkey]
                mot._membrane.inject(motor_inhib[idx], dt)

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
        forces = [f * kd for f in forces_raw]
        self.world.body.step(forces, dt)

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
        therm_signal = self.thermal_membrane.sense(
            self.world, self.world.body, dt)

        # ── SomatosensoryChain: 4-patch skin sensing (V01) ──
        # Sample temperature at 4 body-surface offsets (body radius ≈ 1.0 world unit)
        BODY_RADIUS = 1.0
        pos = self.world.body.position
        patch_positions = {
            "front": [pos[0],            pos[1],            pos[2] + BODY_RADIUS],
            "back":  [pos[0],            pos[1],            pos[2] - BODY_RADIUS],
            "left":  [pos[0] - BODY_RADIUS, pos[1],         pos[2]],
            "right": [pos[0] + BODY_RADIUS, pos[1],         pos[2]],
        }
        patch_temps = {}
        for pid, ppos in patch_positions.items():
            T = self.world.temperature_at(ppos)
            dT = (T - self._soma_prev_temps[pid]) / max(dt, 1e-6)
            self._soma_prev_temps[pid] = T
            damage = max(0.0, T - 0.8)  # damage accumulates above 0.8 normalized T
            patch_temps[pid] = (T, dT, damage)
        self.somatosensory.step(patch_temps, dt)
        self._patch_temps = patch_temps  # expose for tests/diagnostics

        # Inject thermal signal into mechanical_inputs for mother step
        # These get routed to extra_axes encoding neurons in HebbianCircuit
        mechanical_inputs = dict(mechanical_inputs)  # don't mutate caller's dict
        mechanical_inputs['therm'] = therm_signal['therm']
        mechanical_inputs['dtherm'] = therm_signal['dtherm']

        # ── 0b. Closed sensorimotor loop: body acceleration → vestibular ──
        # BIO: otolith organs measure linear acceleration (utricle, saccule).
        # This is a physical measurement, not a mathematical injection.
        # Motor → Muscle → Body.step() → acceleration → vestibular input
        # OTOLITH_GAIN scales acceleration to vestibular input range.
        OTOLITH_GAIN = 500.0
        acc = self.world.body.acceleration

        # ── LangevinNoise → otolith afferent (步骤2 微观传入轨) ──
        # Exact OU discretization (variance-preserving), σ₀=0.70 from FDT.
        # BIO: endolymph thermal fluctuation → hair cell membrane displacement.
        # REF: langevin_noise.py; 皮层除颤与热力学大一统方案 §2.1-§2.3
        eta = self._langevin.step(self.ecm_vestibular, dt)
        # Sensor-side addition: O_k = a_body + η (宏微观绝对同构，只做加法)
        mechanical_inputs['oto_x'] = mechanical_inputs.get('oto_x', 0.0) + (acc[0] + eta[0]) * OTOLITH_GAIN
        mechanical_inputs['oto_y'] = mechanical_inputs.get('oto_y', 0.0) + (acc[1] + eta[1]) * OTOLITH_GAIN
        mechanical_inputs['oto_z'] = mechanical_inputs.get('oto_z', 0.0) + (acc[2] + eta[2]) * OTOLITH_GAIN
        # ── C3': Heat source consumption + ecology ──
        # Organism absorbs energy from nearby heat sources (metabolic feeding).
        # BIO: chemolithoautotrophy at hydrothermal vents.
        CONSUME_RATE = 0.15  # energy absorption rate (P2.1: calibrated for viable income)
        energy_absorbed = self.world.consume_nearby(
            self.world.body.position, CONSUME_RATE, dt)
        # Regenerate depleted sources (deep-sea vent ecology)
        self.world.regenerate_sources()

        # ── Energy pipeline: World → EnergyStore ──
        # Consumed energy flows into the external reservoir.
        # Store handles efficiency loss (digestive efficiency ~90%).
        self.energy_store.deposit(energy_absorbed)
        # Basal metabolic drain: organism costs energy to exist.
        self.energy_store.tick(dt)

        # ── C3': Homeostatic circulation coupling (structural carrier) ──
        # Raw signals from existing sensors (physical measurements):
        thermal_err = abs(self.thermal_membrane._prev_T
                         - self.thermal_membrane._methylation)
        thermal_stability = 1.0 / (1.0 + thermal_err * 10.0)
        body_speed = self.world.body.speed()

        # Feed alignment: direction toward nearest heat source
        nearest = self.world.get_nearest_heat_source(
            self.world.body.position)
        if nearest is not None:
            dx = [nearest.position[i] - self.world.body.position[i]
                  for i in range(3)]
            d_mag = math.sqrt(sum(x * x for x in dx) + 1e-12)
            heat_dir = [x / d_mag for x in dx]
            vel = self.world.body.velocity
            v_mag = math.sqrt(sum(v * v for v in vel) + 1e-12)
            vel_dir = [v / v_mag for v in vel]
            alignment = sum(heat_dir[i] * vel_dir[i] for i in range(3))
            feed_alignment = max(0.0, alignment) * thermal_err
        else:
            feed_alignment = 0.0

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

        # ── C3': Deviation → DA boost (structural output) ──
        # MOSFET comparator outputs DA current when deviation > threshold.
        # Current flows into DA neurons via membrane injection.
        # Goes through D2R autoregulation naturally (not a bypass).
        c3_da_current = circ['da_current']
        if c3_da_current > 0:
            for nid, neuron in self.da_neurons.items():
                neuron._membrane.inject(c3_da_current, dt)

        # ── C.04: Deviation → Motor direct activation ──
        # Spinal-level reflex: bypasses slow DA modulation.
        # BIO: hypothalamic thermoregulatory drive → locomotor CPG
        # (Satinoff 1978: thermoregulatory behavior = motor output).
        # Phase 1 calibration (EXP-012): 0.05 produced 0.0000045V/step
        # ("whispering in a hurricane"). 1.0 → 0.09V/step at deviation=0.19
        # — sufficient to push past Motor v_peak and force spike.
        DEVIATION_MOTOR_GAIN = 1.0
        deviation = circ['deviation']
        if deviation > 0.1:  # threshold: only significant deviation
            motor_drive = (deviation - 0.1) * DEVIATION_MOTOR_GAIN
            for key, mot in self.motor_neurons.items():
                mot._membrane.inject(motor_drive, dt)

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
            if key not in ('therm', 'dtherm'):
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
            # Set membrane charge to match new voltage
            # FIX(V04): record delta in _q_in/_q_out so KCL audit stays valid
            old_charge = aff_reg._membrane.charge
            new_charge = new_v * aff_reg._membrane.capacitance
            aff_reg._membrane.charge = new_charge
            delta_q = new_charge - old_charge
            if delta_q >= 0:
                aff_reg._membrane._q_in += delta_q
            else:
                aff_reg._membrane._q_out += (-delta_q)

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
                # FIX(V04): track charge reduction in _q_out for KCL audit
                old_charge = aff._membrane.charge
                aff._membrane.charge *= (1.0 - reduction)
                delta_q = aff._membrane.charge - old_charge  # negative
                aff._membrane._q_out += (-delta_q)

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

        # ── 7b. VitalOscillator → Motor membrane (步骤2 宏观传出轨) ──
        # Three-frequency VdP heart injects basal drive into Motor membranes.
        # BIO: hemodynamic pulsation → postural tremor → basal motility.
        # Energy withdrawn from EnergyStore (Noether-compliant, via withdraw()).
        # REF: vital_oscillator.py; 步骤2统一物理架构方案 §一
        _vital_out = self.vital_oscillator.step(self.energy_store, dt)
        _vital_axes = ['move_x', 'move_y', 'move_z']
        for _k, _ax in enumerate(_vital_axes):
            if _ax in self.motor_neurons:
                self.motor_neurons[_ax]._membrane.inject(_vital_out[_k], dt)
        # Record in MotionState for observability
        self.motion_state.vital_pulse = _vital_out
        self.motion_state.vital_amplitude = sum(abs(v) for v in _vital_out)

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

        # ── B.06: Record thermal state in MotionState (observability only) ──
        # Actual thermal→DA coupling is structural: soma_to_da bundle propagates
        # relay activation into DA neurons. No math hardcoding here.
        T_p = {pid: patch_temps[pid][0] for pid in self.somatosensory.patch_ids}
        grad_T = [
            T_p.get("right", 0.0) - T_p.get("left", 0.0),
            0.0,
            T_p.get("front", 0.0) - T_p.get("back", 0.0),
        ]
        vel = list(self.world.body.velocity)
        grad_dot_v = sum(grad_T[i] * vel[i] for i in range(min(3, len(vel))))
        mean_dT = sum(abs(patch_temps[pid][1])
                      for pid in self.somatosensory.patch_ids
                      ) / len(self.somatosensory.patch_ids)
        self.motion_state.thermal_potential = mean_dT
        self.motion_state.thermal_gradient = grad_T
        self.motion_state.thermal_gradient_dot_velocity = grad_dot_v

        for bundle in self.bundles_shadow_to_da:
            currents = bundle.propagate()
            for j, tgt in enumerate(bundle.targets):
                if j < len(currents) and tgt.id in da_input_currents:
                    # tanh saturation: vesicle pool + receptor conductance ceiling.
                    # BIO: max synaptic release rate bounded by vesicle replenishment
                    #      (Attwell & Laughlin 2001). Receptor conductance saturates.
                    # I_MAX = 2.0: shadow pathway is secondary modulator (< xin_relay).
                    # I_SCALE = 3.0: half-sat at I=3. With w=0.1 and Ca_rate~0.25,
                    # raw I ≈ 7×0.25×0.111≈0.19 → tanh(0.19/3)≈0.063 → effectively
                    # linear. Upper bound: I_MAX×tanh(∞)=2.0 prevents unbounded DA.
                    I_MAX, I_SCALE = 2.0, 3.0
                    import math as _math
                    da_input_currents[tgt.id] += I_MAX * _math.tanh(currents[j] / I_SCALE)

        for bundle in self.bundles_xin_to_da:
            currents = bundle.propagate()
            for j, tgt in enumerate(bundle.targets):
                if j < len(currents) and tgt.id in da_input_currents:
                    da_input_currents[tgt.id] += currents[j]

        # B.06: soma relay → DA (thermal pathway, structural)
        for bundle in self.bundles_soma_to_da:
            currents = bundle.propagate()
            for j, tgt in enumerate(bundle.targets):
                if j < len(currents) and tgt.id in da_input_currents:
                    da_input_currents[tgt.id] += currents[j]

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
        for bundle in self.bundles_shadow_to_da + self.bundles_xin_to_da + self.bundles_soma_to_da:
            bundle.learn(dt=dt)
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

        # Enc → Col: DA scales encoding→column signal
        for bundle in self.bundles_enc_to_col:
            currents = bundle.propagate()
            if da_gain != 1.0:
                currents = [c * da_gain for c in currents]
            bundle.apply_to_targets(currents, dt)

        # Col → Motor: DA also scales column→motor signal
        # BIO: D1 receptors present on both prefrontal and motor cortex
        for bundle in self.bundles_col_to_motor:
            currents = bundle.propagate()
            if da_gain != 1.0:
                currents = [c * da_gain for c in currents]
            bundle.apply_to_targets(currents, dt)

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

            # 2. Weight entropy snapshot (Shannon); V14: surface freeze alert
            w_snap = self._entropy_probe.measure(self, tick)
            if w_snap.learning_frozen:
                n_frozen = self._entropy_probe._frozen_count
                self._ledger_alerts.append(
                    f"t={tick}: DEG-FREEZE: weight entropy delta≈0 for "
                    f"{n_frozen} consecutive measurements — learning may be frozen"
                )

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
            # V05/V06/V08: check anomalies and surface any alerts
            alerts = self._energy_ledger.check_anomalies()
            if alerts:
                for alert in alerts:
                    self._ledger_alerts.append(f"t={tick}: {alert}")

    def _do_learning(self, dt: float):
        """Phase 4: P→R closure — unified three-factor learning.

        Full chain: |ξ| → c_DA → α_lr → Δw (v2.0 §1E.5)

        Three factors combined into plasticity_gate per layer:
          1. PNN gate (g_ℓ): ECM maturation → critical period closure
          2. DA modulation: Xin tension → DA release → learning rate boost
          3. Sync gate (g_sync): binding activation → col→motor gate

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

        # Vestibular → Encoding: PNN × DA
        for b in self.bundles_vest_to_enc:
            b.learn(dt, plasticity_gate=gate_vest * da_lr_mod)

        # Encoding → Column: PNN × DA
        for b in self.bundles_enc_to_col:
            b.learn(dt, plasticity_gate=gate_enc * da_lr_mod)

        # A4: mass inertia factor — heavier body = slower motor learning
        # BIO: larger organisms have slower motor adaptation rates
        body_lr = self.world.body.mass_inertia_factor()

        # Column → Motor: PNN × DA × sync × body_inertia
        for b in self.bundles_col_to_motor:
            b.learn(dt, plasticity_gate=gate_col * da_lr_mod * g_sync * body_lr)

        # Sprouted bundles: use target layer's gate
        for b in self._sprouted_bundles:
            bid = b.config.bundle_id
            if 'col_to_motor' in bid:
                gate = gate_col * da_lr_mod * g_sync * body_lr
            elif 'enc_to_col' in bid or 'aff' in bid:
                gate = gate_enc * da_lr_mod
            else:
                gate = gate_vest * da_lr_mod
            b.learn(dt, plasticity_gate=gate)

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

        Creates two bundle pathways:
          1. Shadow col → DA neurons (tonic/baseline, BCM STDP)
          2. Xin relay → DA neurons (phasic bursts, fast STDP)

        Both pathways use real SynapticBundles — eligible for:
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
        # gain=1.0: with post-defibrillation calcium_rate ∈ [0.2, 0.6],
        # I = 7 sources × rate(0.25) × w(0.1) × 1.0 = 0.175
        # V_ss = (0.175 + 0.1bc) × 1.0 = 0.275 → DA gradient available ✓
        # Peak: rate=0.58 → I=0.406 → V_ss=0.506 → D2R kicks in ✓
        # Phase 1 fix (w=1.0) was calibrated before cortical defibrillation
        # when Shadow Col had calcium_rate=0 (contributed nothing).
        # Post-defibrillation calcium_rate=0.2-0.6 → must re-calibrate.
        # D2R τ_D2=100s means at 10k steps it only provides 10% compensation;
        # w=1.0 overwhelms it. Original design w=0.05 was for rate≈1.0 full-fire.
        # New w=0.1 ≈ 0.05 × (1.0/0.25) × 0.5 (half-scale for D2R build-up slack).
        # REF: 热趋性行为分析_v2.0_2026-06-16 §三 DA再饱和诊断
        cfg_shadow = BundleConfig(
            bundle_id="shadow_to_da",
            learning_rule="frozen",  # INNATE: hypothalamus→VTA phylogenetic prior
            initial_weight=0.1,      # Post-defibrillation recalibration (was 1.0)
            weight_max=5.0,          # structural upper bound
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
            initial_weight=5.0,      # Phase 1 fix: 0.1 too thin → DA sleeps
            weight_max=10.0,         # EXP-012 fix: was default 1.0 → silently clamped 5.0→1.0
            stdp_lr=0.003,           # retained for reference but unused (frozen)
            synapse_gain=0.5,        # moderate: 1 source, phasic
            bundle_role="feedforward",
            remodel_cost_kappa=0.001,
        )
        self.bundles_xin_to_da.append(
            SynapticBundle(cfg_xin, [self._xin_relay], da_list))

        # ── B.06: Somatosensory relay → DA (thermal pathway) ──
        # Relay neurons compute ∇²T (Laplacian) via lateral inhibition.
        # Front/back/left/right asymmetry in relay activation encodes
        # temperature gradient direction relative to body orientation.
        # When approaching heat: front relay fires more → DA↑ (structural).
        # No explicit dot-product math — directionality emerges from relay
        # activation differences propagating through this bundle.
        # BIO: spinal relay → VTA pathway (thermotaxis in simple organisms).
        # REF: AI编程自足文档 步骤1 B.06; analysis_concept_evolution §5
        relay_neurons = [self.somatosensory.relays[pid]
                         for pid in self.somatosensory.patch_ids]
        cfg_soma = BundleConfig(
            bundle_id="soma_to_da",
            learning_rule="stdp",
            initial_weight=0.5,
            weight_max=2.0,
            stdp_lr=0.002,
            synapse_gain=1.0,
            bundle_role="feedforward",
            remodel_cost_kappa=0.001,
        )
        self.bundles_soma_to_da.append(
            SynapticBundle(cfg_soma, relay_neurons, da_list))

        self._da_circuit_initialized = True

        # Log to growth log (same as sprout events)
        self._growth_log.append(
            f"DA_CIRCUIT_INIT step={self._step_count} "
            f"shadow_cols={len(shadow_cols)} da_neurons={len(da_list)} "
            f"bundles=shadow_to_da+xin_to_da+soma_to_da"
        )

    # ── Override get_all_neurons/bundles to include DA components ──

    def get_all_neurons(self):
        """Include DA neurons, Xin relay, and SomatosensoryChain in neuron census.

        Noether probe, entropy ledger, and vascular energy delivery
        all enumerate neurons via this method. DA neurons must be
        included for correct energy/weight conservation checks.
        V01: SomatosensoryChain (12 neurons) now included — no more blind spot.
        """
        neurons = super().get_all_neurons()
        neurons.extend(self.da_neurons.values())
        neurons.append(self._xin_relay)
        neurons.extend(self.somatosensory.get_all_neurons())
        return neurons

    def get_all_bundles(self):
        """Include DA bundles and SomatosensoryChain bundles in bundle census.

        Noether weight balance check, Xin bookkeeping, and sprout/prune
        all enumerate bundles via this method. DA bundles must be
        included for correct entropy ledger accounting.
        V01: SomatosensoryChain bundles now included.
        """
        bundles = super().get_all_bundles()
        bundles.extend(self.bundles_shadow_to_da)
        bundles.extend(self.bundles_xin_to_da)
        bundles.extend(self.bundles_soma_to_da)
        bundles.extend(self.somatosensory.get_all_bundles())
        return bundles

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

