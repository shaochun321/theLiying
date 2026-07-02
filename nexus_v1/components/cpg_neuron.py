"""nexus_v1.components.cpg_neuron — CPGNeuron (Central Pattern Generator proxy).

TYPE:HYBRID — Self-sustaining oscillator with SynapticBundle-compatible duck-type interface.

BIO: VTA dopaminergic neurons exhibit intrinsic pacemaker oscillations at 2-5 Hz
     (Grace & Bunney 1984, J Neurosci 4:2877). This CPG models the tonic rhythmic
     drive from VTA interneurons that maintains DA.post_trace non-zero at steady state,
     enabling relay_to_da STDP during sustained proximity to a heat source.

     Problem it solves: relay_to_da STDP uses post_trace = |d(activation)/dt|.
     When DA neurons reach steady state, d(activation)/dt → 0 → STDP freezes.
     CPG injects a low-amplitude 2 Hz oscillation, keeping post_trace > 0 always.

PHYS: Van der Pol relaxation oscillator (ResonantOscillator, same class as VitalOscillator
      internals) → rectified output [0, amplitude*2] → SynapticBundle (frozen weight)
      → DA neurons. Amplitude calibrated so V_DA_osc ≈ 0.011V ∈ (0.001, 0.024V) ε range.

DESIGN: Duck-typed source proxy — NOT a Neuron subclass.
        Implements only what SynapticBundle.propagate() requires for non-spiking sources:
          - is_alive() → True
          - config.spiking → False
          - activation → float ≥ 0

        For learning_rule="frozen" bundles, no trace access is needed from source.
        CPGNeuron is NOT in get_all_neurons() — it is a driver, not a circuit neuron.
        Its bundle IS in get_all_bundles() for Noether/Xin accounting.
"""
from __future__ import annotations

from types import SimpleNamespace

from .oscillator import ResonantOscillator


class CPGNeuron:
    """TYPE:HYBRID — VTA pacemaker CPG proxy for SynapticBundle source.

    BIO: VTA local interneuron providing 2 Hz rhythmic excitatory drive to
         DA projection neurons. Maintains DA.post_trace > 0 at steady state.
    REF: Grace & Bunney 1984 J Neurosci 4:2877 — VTA burst-pause oscillation.
    REF: Schultz 2007 Ann NY Acad Sci — DA phasic vs tonic signaling.
    """

    def __init__(self, frequency: float = 2.0, amplitude: float = 0.05,
                 mu: float = 2.0, neuron_id: str = "vta_cpg"):
        # Duck-type config: SynapticBundle.propagate() checks config.spiking
        self.config = SimpleNamespace(spiking=False)
        self.neuron_id = neuron_id
        self.id = neuron_id

        # Internal VdP oscillator — same class used inside VitalOscillator
        # PARAM: amplitude=0.05 → limit-cycle output ≈ ±0.10 (VdP _x ≈ ±2)
        #        Rectified: activation ∈ [0, 0.10]
        #        With bundle w=0.1 (G≈0.111), synapse_gain=1.0:
        #          I_peak = 0.10 × 0.111 = 0.011A
        #          V_DA_osc = I × r_leak(1.0) = 0.011V ∈ (0.001, 0.024V) ✓
        self._oscillator = ResonantOscillator(
            frequency=frequency,
            mu=mu,
            amplitude=amplitude,
            phase_offset=0.0,
        )

        self.activation: float = 0.0
        # Neuron-compatible attributes required by SynapticBundle helper methods:
        # compute_xin() reads _activation_ema; _apply_metabolic_tax() reads energy.
        self._activation_ema: float = 0.0
        # energy=10.0: always above ENERGY_FLOOR(0.3) → no synaptic decay triggered.
        # Not drained (EnergyStore handles bundle basal cost when available).
        self.energy: float = 10.0

    def step(self, dt: float) -> None:
        """Advance oscillator one timestep and update activation."""
        raw = self._oscillator.step(dt)
        # Rectify: only positive half-cycle (firing rate ≥ 0, no negative DA drive)
        # BIO: interneuron firing rate cannot go negative; silent during hyperpolarization
        self.activation = max(0.0, raw)
        self._activation_ema = self.activation

    def is_alive(self) -> bool:
        """Always alive — CPG is an intrinsic circuit element."""
        return True
