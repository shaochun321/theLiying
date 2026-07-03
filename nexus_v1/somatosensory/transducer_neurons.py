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

from ..components.neuron import Neuron, NeuronConfig
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
