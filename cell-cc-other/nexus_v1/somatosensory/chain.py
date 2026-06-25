"""nexus_v1.somatosensory.chain — Thermal skin sensing chain.

Parallel to vestibular.chain, built from the same MetaNeurons.
Each skin patch has its own transduction chain:

  Layer 1: Thermoreceptor (Reg channel — DC/tonic temperature)
    - Large capacitance C=5.0 → slow integration (τ=100ms)
    - Low threshold → sensitive to small ΔT
    - BIO: TRPV/TRPM ion channels, τ_thermal >> τ_mechanical

  Layer 2: Nociceptor (Irr channel — AC/phasic dT/dt)
    - Small capacitance C=0.5 → fast response (τ=4ms)
    - High threshold → only fires on rapid temperature changes
    - BIO: TRPV1/TRPA1 nociceptors, spiking neurons

  Layer 3: SomatoRelay (lateral inhibition network)
    - One relay neuron per patch
    - Adjacent patches mutually inhibit (gain=0.05)
    - Computes discrete Laplacian ∇²T across body surface
    - BIO: dorsal horn wide-dynamic-range neurons

The chain outputs per-patch relay activity into the Hebbian
circuit's encoding layer via the extra_axes mechanism.

RC equivalence to vestibular:
  - Thermal:     τ_th  = C(5.0) × R(20.0) = 100ms
  - Mechanical:  τ_mech = C(1.0) × R(5.0)  = 5ms
  Same component, different time constants.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

from ..components.neuron import Neuron, NeuronConfig, ChannelConfig
from ..circuit.bundle import SynapticBundle, BundleConfig


# ─────────────────────────────────────────────────────────────────────
# Patch definitions
# ─────────────────────────────────────────────────────────────────────

PATCH_IDS = ["front", "back", "left", "right"]

# Adjacency graph: patches that share a body-surface border.
# front↔left, front↔right, back↔left, back↔right.
# NOT front↔back (diametrically opposite, not adjacent).
ADJACENCY = {
    "front": ["left", "right"],
    "back":  ["left", "right"],
    "left":  ["front", "back"],
    "right": ["front", "back"],
}


# ─────────────────────────────────────────────────────────────────────
# Neuron configurations
# ─────────────────────────────────────────────────────────────────────

def _thermoreceptor_config(patch_id: str) -> NeuronConfig:
    """Thermoreceptor: DC/tonic temperature sensor.

    RC time constant calibrated for dt=0.001 (1ms per step):
      τ_th = C × R = 1.0 × 5.0 = 5.0 time-units = 5000 steps = 5s biological
      V_ss = I × R = T_skin × 5.0.  For T_skin=0.2: V_ss=1.0.
      Reaches 63% in ~5000 steps (5s), 95% in ~15000 steps (15s).
    BIO: TRPV3/TRPM8 channels — thermal integration τ ≈ 1-10s for tonic response.
    Previous τ=100 was 20× too slow (never reached steady state in typical runs).

    Uses single-channel mode (activation = MOSFET(V_m)) with low threshold
    because skin temperatures are small (0.1-0.3 normalized). Default
    MOSFET v_threshold=0.3 is too high — skin T rarely exceeds 0.3.
    v_threshold=0.01 → fires at any skin T above ambient (0.1).
    """
    return NeuronConfig(
        neuron_id=f"thermo_{patch_id}",
        capacitance=1.0,        # reduced from 5.0 → 5× faster equilibration
        r_leak=5.0,             # reduced from 20.0 → τ=5.0, V_ss=T_skin×5.0
        inertia=1.0,
        vdd=1.0,
        r_supply=0.05,
        # Override default MOSFET threshold: skin T produces V_m ~ 0.5-1.0
        # Default v_th=0.3 would leave only the top of the range active.
        # v_th=0.01 ensures graded response across full skin-T range.
        channels=[
            ChannelConfig(
                name="default",    # use "default" to trigger single-channel path
                v_threshold=0.01,  # low threshold: fires at skin T > ambient
                gm=1.0,
                tau_gate=0.0,      # instantaneous (DC tonic sensor)
                reversal=0.0,
                sign=1.0,
            ),
        ],
        use_voltage_regulator=True,
        vr_base_rate=0.001,
        vr_activity_coeff=0.3,
        vr_max_rate=3.0,
    )



def _nociceptor_config(patch_id: str) -> NeuronConfig:
    """Nociceptor: AC/phasic rapid temperature change detector.

    BARE-NERVE DIFFERENTIATOR: hypersensitive to dT/dt.
    Calibrated for vital heartbeat micro-motion (speed ~0.00025):
      dT_skin/step ≈ 5e-5 at d=20 from source
      With NOCI_DT_GAIN=200: I_noci = 0.01
      V_ss = I × R = 0.01 × 50 = 0.5 >> v_peak=0.01
      τ_noci = C × R = 0.02 × 50 = 1ms (ultrafast differentiator)

    EXP-016 fix: original C=0.5, v_peak=0.5 was a damage-threshold
    detector (tissue denaturation at T>43°C). Could NEVER fire from
    thermal gradients at safe distances → DA collapse → boiling frog.

    BIO: C-fibers detect dT/dt ≥ 0.001°C/s (TRPV1 channel sensitivity).
    Thin unmyelinated axons → tiny membrane area → very small C.
    Low v_peak = high sensitivity to temperature RATE, not level.
    """
    return NeuronConfig(
        neuron_id=f"noci_{patch_id}",
        capacitance=0.02,       # bare nerve: 25× smaller → ultrafast
        r_leak=50.0,            # τ = 1ms, higher R → higher V_ss
        inertia=0.3,
        vdd=1.0,
        r_supply=0.05,
        spiking=True,
        v_peak=0.01,            # hypersensitive: 50× lower threshold
        v_reset=0.001,          # small reset gap (near-threshold)
        b_adapt=0.02,           # moderate adaptation: allows bursting
        tau_w=5.0,              # longer adaptation decay
        use_voltage_regulator=True,
        vr_base_rate=0.05,
        vr_activity_coeff=0.3,
        vr_max_rate=3.0,
    )


def _relay_config(patch_id: str) -> NeuronConfig:
    """SomatoRelay neuron: wide-dynamic-range convergence.

    Receives thermoreceptor + nociceptor input, participates in
    lateral inhibition with adjacent patch relays.
    BIO: dorsal horn WDR neuron (lamina V).
    """
    return NeuronConfig(
        neuron_id=f"relay_{patch_id}",
        capacitance=2.0,        # moderate integration
        r_leak=10.0,            # τ = 20ms
        inertia=1.0,
        vdd=1.0,
        r_supply=0.05,
        # Single default MOSFET: simple integrator
        # Receives summed thermo + noci input via bundles
        use_voltage_regulator=True,
        vr_base_rate=0.001,
        vr_activity_coeff=0.3,
        vr_max_rate=3.0,
    )


# ─────────────────────────────────────────────────────────────────────
# SomatosensoryChain
# ─────────────────────────────────────────────────────────────────────

class SomatosensoryChain:
    """Thermal skin sensing chain, parallel to VestibularChain.

    Architecture per patch:
        T_sample → [Thermoreceptor] ──┐
        dT_sample → [Nociceptor] ─────┤
                                      ↓
                              [SomatoRelay] ←→ lateral inhibition
                                      ↓
                              output → Encoding layer

    4 patches × 3 neurons = 12 neurons
    4 × 2 input bundles + 4 lateral pairs = 12 bundles

    Lateral inhibition gain is constrained to < 0.05 to prevent
    stiff ODE oscillations (dt/τ stability condition).
    """

    # Lateral inhibition gain — user-specified constraint
    LATERAL_GAIN: float = 0.05

    # Sensory adaptation time constant (steps).
    # RC high-pass filter: tracks relay baseline (DC) and subtracts it,
    # outputting only the AC component (temperature changes / gradients).
    # BIO: spike frequency adaptation in thermoreceptors — tonic response
    # decays over seconds, leaving only phasic (dT/dt) sensitivity.
    # τ_adapt = 5000 steps × dt=0.001 = 5s biological time constant.
    # At 63% of τ, baseline tracking is 63% complete.
    TAU_ADAPT: float = 5000.0

    def __init__(self, patch_ids: List[str] | None = None,
                 lateral_gain: float = 0.05,
                 tau_adapt: float = 5000.0):
        if patch_ids is None:
            patch_ids = list(PATCH_IDS)
        self.patch_ids = patch_ids
        self.LATERAL_GAIN = lateral_gain
        self.TAU_ADAPT = tau_adapt

        # Adaptation state: slow capacitor tracking relay baseline per patch
        self._thermal_adapt: Dict[str, float] = {pid: 0.0 for pid in patch_ids}

        # ── Create neurons per patch ──
        self.thermoreceptors: Dict[str, Neuron] = {}
        self.nociceptors: Dict[str, Neuron] = {}
        self.relays: Dict[str, Neuron] = {}

        for pid in patch_ids:
            self.thermoreceptors[pid] = Neuron(_thermoreceptor_config(pid))
            self.nociceptors[pid] = Neuron(_nociceptor_config(pid))
            self.relays[pid] = Neuron(_relay_config(pid))

        # ── Bundles: Thermoreceptor → Relay ──
        self.bundles_thermo_to_relay: Dict[str, SynapticBundle] = {}
        for pid in patch_ids:
            b = SynapticBundle(
                config=BundleConfig(
                    bundle_id=f"thermo_to_relay_{pid}",
                    learning_rule="stdp",
                    initial_weight=0.3,
                    stdp_lr=0.005,
                    synapse_gain=3.0,
                    bundle_role="feedforward",
                    # TemporalCoupler: bridge slow thermo (τ=100ms) to relay
                    coupler_capacitance=50.0,
                    coupler_r_leak=2.0,
                    coupler_adapt_vth=0.2,
                    coupler_adapt_gm=2.0,
                    coupler_blayer_c_slow=100.0,
                    coupler_blayer_r_slow=10.0,
                    coupler_blayer_gm=0.01,
                    coupler_blayer_k=2.0,
                ),
                sources=[self.thermoreceptors[pid]],
                targets=[self.relays[pid]],
            )
            self.bundles_thermo_to_relay[pid] = b

        # ── Bundles: Nociceptor → Relay ──
        self.bundles_noci_to_relay: Dict[str, SynapticBundle] = {}
        for pid in patch_ids:
            b = SynapticBundle(
                config=BundleConfig(
                    bundle_id=f"noci_to_relay_{pid}",
                    learning_rule="stdp",
                    initial_weight=0.2,
                    stdp_lr=0.005,
                    synapse_gain=5.0,      # noci needs higher gain (spiking)
                    bundle_role="feedforward",
                    coupler_capacitance=10.0,
                    coupler_r_leak=2.0,
                    coupler_adapt_vth=0.2,
                    coupler_adapt_gm=2.0,
                    coupler_blayer_c_slow=100.0,
                    coupler_blayer_r_slow=10.0,
                    coupler_blayer_gm=0.01,
                    coupler_blayer_k=2.0,
                ),
                sources=[self.nociceptors[pid]],
                targets=[self.relays[pid]],
            )
            self.bundles_noci_to_relay[pid] = b

        # ── Bundles: Lateral inhibition (adjacent relays) ──
        # Each adjacent pair gets a bidirectional inhibitory bundle.
        # Only create one direction per pair to avoid duplication.
        self.bundles_lateral: Dict[str, SynapticBundle] = {}
        created_pairs = set()
        for pid in patch_ids:
            for adj in ADJACENCY.get(pid, []):
                if adj not in patch_ids:
                    continue
                pair_key = tuple(sorted([pid, adj]))
                if pair_key in created_pairs:
                    continue
                created_pairs.add(pair_key)

                # Forward: pid → adj (inhibitory)
                bid_fwd = f"lateral_{pid}_to_{adj}"
                b_fwd = SynapticBundle(
                    config=BundleConfig(
                        bundle_id=bid_fwd,
                        learning_rule="stdp",
                        initial_weight=self.LATERAL_GAIN,
                        weight_max=0.1,     # hard cap prevents instability
                        stdp_lr=0.001,      # very slow lateral learning
                        synapse_gain=-1.0,  # INHIBITORY: negative gain
                        bundle_role="lateral",
                    ),
                    sources=[self.relays[pid]],
                    targets=[self.relays[adj]],
                )
                self.bundles_lateral[bid_fwd] = b_fwd

                # Reverse: adj → pid (inhibitory)
                bid_rev = f"lateral_{adj}_to_{pid}"
                b_rev = SynapticBundle(
                    config=BundleConfig(
                        bundle_id=bid_rev,
                        learning_rule="stdp",
                        initial_weight=self.LATERAL_GAIN,
                        weight_max=0.1,
                        stdp_lr=0.001,
                        synapse_gain=-1.0,  # INHIBITORY
                        bundle_role="lateral",
                    ),
                    sources=[self.relays[adj]],
                    targets=[self.relays[pid]],
                )
                self.bundles_lateral[bid_rev] = b_rev

    # Nociceptor dT/dt gain: converts skin temperature derivative into
    # input current for the bare-nerve differentiator.
    # Calibration (EXP-016 diagnosis):
    #   Vital speed 0.00025 → dT_skin/step ≈ 5e-5
    #   I_noci = |dT| × NOCI_DT_GAIN = 5e-5 × 200 = 0.01
    #   V_ss = I × R_leak = 0.01 × 50 = 0.5 >> v_peak=0.01
    #   → Nociceptor fires robustly from heartbeat micro-motion
    # BIO: TRPV1 thermosensitivity ~0.001°C/s detection threshold
    # (Caterina et al. 1997, Julius & Basbaum 2001)
    NOCI_DT_GAIN: float = 200.0

    def step(self, patch_temps: Dict[str, Tuple[float, float, float]],
             dt: float = 1.0):
        """Process one time step.

        Args:
            patch_temps: dict of patch_id → (T_skin, dT_skin, damage_integral)
                from body.sample_skin(). T_skin is the Fourier-integrated
                skin temperature, not the raw environment temperature.
            dt: time step
        """
        # ── 1. Sensory transduction ──
        for pid in self.patch_ids:
            vals = patch_temps.get(pid, (0.0, 0.0, 0.0))
            T = vals[0]
            dT = vals[1] if len(vals) > 1 else 0.0
            damage = vals[2] if len(vals) > 2 else 0.0

            # Thermoreceptor: driven by skin temperature (Fourier-integrated)
            # This is the real T_skin, NOT the environment temperature.
            self.thermoreceptors[pid].step(T, dt)

            # Nociceptor: DUAL-CHANNEL input
            #   Channel A: dT/dt → rapid thermal gradient detection
            #     BIO: TRPV1 thermosensitivity — C-fibers detect dT/dt
            #     even at safe absolute temperatures. This is how the
            #     organism senses thermal APPROACH before tissue damage.
            #   Channel B: damage_integral → tissue injury alarm
            #     BIO: TRPV1/TRPA1 activation by damage products
            #     (bradykinin, prostaglandins) at T > 43°C.
            # EXP-016 fix: original code used ONLY damage (= 0 at safe
            # distances) → nociceptor blind → DA collapse → boiling frog.
            noci_dT_input = abs(dT) * self.NOCI_DT_GAIN
            noci_damage_input = damage * 10.0
            noci_total = noci_dT_input + noci_damage_input
            self.nociceptors[pid].step(noci_total, dt)

        # ── 2. Sensory → Relay propagation ──
        for pid in self.patch_ids:
            # Thermo → Relay
            b_th = self.bundles_thermo_to_relay[pid]
            currents_th = b_th.propagate()
            # Noci → Relay
            b_nc = self.bundles_noci_to_relay[pid]
            currents_nc = b_nc.propagate()

            # Sum both inputs into relay
            total_input = 0.0
            if currents_th:
                total_input += currents_th[0]
            if currents_nc:
                total_input += currents_nc[0]

            # Apply lateral inhibition currents
            for bid, b_lat in self.bundles_lateral.items():
                if self.relays[pid] in b_lat.targets:
                    lat_currents = b_lat.propagate()
                    if lat_currents:
                        # Inhibitory: synapse_gain is negative, so this subtracts
                        idx = b_lat.targets.index(self.relays[pid])
                        if idx < len(lat_currents):
                            total_input += lat_currents[idx]

            self.relays[pid].step(total_input, dt)

        # ── 3. STDP learning ──
        for pid in self.patch_ids:
            self.bundles_thermo_to_relay[pid].learn(dt)
            self.bundles_noci_to_relay[pid].learn(dt)
        for b in self.bundles_lateral.values():
            b.learn(dt)

    def get_output(self) -> Dict[str, Dict[str, float]]:
        """Get per-patch output for circuit integration.

        Returns dict of patch_id → {
            "relay_activation": relay neuron activation (main output),
            "thermo_activation": thermoreceptor activation,
            "noci_activation": nociceptor activation,
        }
        """
        output = {}
        for pid in self.patch_ids:
            output[pid] = {
                "relay_activation": self.relays[pid].activation,
                "thermo_activation": self.thermoreceptors[pid].activation,
                "noci_activation": self.nociceptors[pid].activation,
            }
        return output

    def get_mechanical_inputs(self, dt: float = 1.0) -> Dict[str, float]:
        """Get per-patch values formatted for hebbian extra_axes input.

        Returns dict with keys like 'therm_front', 'dtherm_front' etc.
        These are injected into mechanical_inputs for the Hebbian circuit.

        Applies sensory adaptation (RC high-pass filter) to relay output:
          adapted_baseline += (raw - adapted_baseline) × (1 - e^(-dt/τ))
          output = max(0, raw - adapted_baseline)

        This absorbs constant ambient temperature (DC component) and only
        passes through temperature changes (AC component). Equivalent to
        spike frequency adaptation in biological thermoreceptors.

        BIO: TRPV3/TRPM8 channels show strong adaptation — sustained
        constant temperature → firing rate returns to near-baseline
        within seconds. Only dT/dt drives persistent output.
        """
        # Exponential decay factor for adaptation capacitor
        decay = math.exp(-dt / max(self.TAU_ADAPT, 1.0))

        result = {}
        for pid in self.patch_ids:
            raw = self.relays[pid]._activation_ema

            # Slow capacitor tracks baseline (DC component)
            self._thermal_adapt[pid] = (
                self._thermal_adapt[pid] * decay + raw * (1.0 - decay)
            )

            # High-pass output: only the AC component (gradient signal)
            result[f"therm_{pid}"] = max(0.0, raw - self._thermal_adapt[pid])

            # Noci EMA → phasic axis (irr encoding) — no adaptation needed
            # (nociceptors are already phasic/differentiating by design)
            result[f"dtherm_{pid}"] = self.nociceptors[pid]._activation_ema
        return result

    def get_all_neurons(self) -> List[Neuron]:
        """Get all neurons in the chain."""
        neurons = []
        for pid in self.patch_ids:
            neurons.extend([
                self.thermoreceptors[pid],
                self.nociceptors[pid],
                self.relays[pid],
            ])
        return neurons

    def get_all_bundles(self) -> List[SynapticBundle]:
        """Get all bundles in the chain."""
        bundles = []
        bundles.extend(self.bundles_thermo_to_relay.values())
        bundles.extend(self.bundles_noci_to_relay.values())
        bundles.extend(self.bundles_lateral.values())
        return bundles

    @property
    def axes(self) -> List[str]:
        """Axes registered in the Hebbian circuit's extra_axes."""
        return [f"therm_{pid}" for pid in self.patch_ids]

    def summary(self) -> dict:
        output = self.get_output()
        return {
            "patches": self.patch_ids,
            "n_neurons": len(self.get_all_neurons()),
            "n_bundles": len(self.get_all_bundles()),
            "lateral_gain": self.LATERAL_GAIN,
            "per_patch": output,
        }
