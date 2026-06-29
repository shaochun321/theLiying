"""TYPE:HYBRID — VestibularChainV2: v2.0 chain with network layer, FIFO delays, soft saturation.

Extends VestibularChain (all neurons and bundles unchanged) with:
  1. VestibularNetworkLayer: topology registry (V-N1..V-N5)
  2. FIFODelayBuffer per connection: MET→HC (2 steps), HC→Aff (2 steps)
  3. soft_saturate() on all propagated bundle currents
  4. p_avail reference slot for future dynamic G_eff integration

Signal latency budget (same-axis, v_cond=1000, dt=0.001):
  MET→HC:  L=2 → 2 steps (2 ms)
  HC→Aff:  L=2 → 2 steps (2 ms)
  Aff→Enc: L=2.5 → 3 steps (handled by hebbian.py synapse_gain=16.0 + G_eff)
  Enc→Col: L=2 → 2 steps
  Total chain latency: 9 steps ≈ 9 ms, within VOR window (5–15 ms) ✓

BIO: VOR arc (Carey & Bhatt 2005); myelination timing (Waxman & Bennett 1972).
REF: 以前庭重构为驱动的网络层接入方案 V-N1..V-N6;
     前庭系统的空间网络化重构补充 §1-§3.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

from .chain import VestibularChain
from .fifo_buffer import FIFODelayBuffer
from .network_layer import VestibularNetworkLayer, soft_saturate


class VestibularChainV2(VestibularChain):
    """v2.0 vestibular chain with topology-aware delays and soft saturation.

    Drop-in extension of VestibularChain. Existing tests continue to use
    VestibularChain via VariantCircuit; this class is for v2.0 experiments.

    Args:
        axes: subset of axes to instantiate (default: all 6)
        p_avail_ref: mutable list [float] for energy gating.
            Set p_avail_ref[0] = EnergyStore.fill each step to enable
            dynamic G_eff. Defaults to [1.0] (constant full energy).
    """

    def __init__(self,
                 axes: Optional[List[str]] = None,
                 p_avail_ref: Optional[List[float]] = None):
        super().__init__(axes=axes)

        if p_avail_ref is None:
            p_avail_ref = [1.0]
        self.p_avail_ref: List[float] = p_avail_ref

        # V-N1..V-N5: topology registry
        self.network = VestibularNetworkLayer(p_avail_ref=p_avail_ref)

        # FIFOs: one per axis per connection type
        self.fifo_met_to_hc:  Dict[str, FIFODelayBuffer] = {}
        self.fifo_hc_to_aff:  Dict[str, FIFODelayBuffer] = {}

        for axis in self.axes:
            addr_met = self.network.register(f"met_{axis}")
            addr_hc  = self.network.register(f"hc_{axis}")
            addr_aff = self.network.register(f"aff_reg_{axis}")

            self.fifo_met_to_hc[axis]  = self.network.make_fifo(addr_met, addr_hc)
            self.fifo_hc_to_aff[axis]  = self.network.make_fifo(addr_hc, addr_aff)

    def step(self, mechanical_inputs: Dict[str, float], dt: float = 1.0):
        """One simulation step with FIFO delays and soft saturation.

        Signal flow per axis:
          deflection → MET.step()
            → bundle.propagate() → soft_saturate → FIFO(2 steps) → HC.step()
            → bridge release_rate → bundle.propagate() → soft_saturate → FIFO(2 steps)
            → Aff_reg.step() / Aff_irr.step()
        """
        _log_dt = max(dt, 1e-9)

        for axis in self.axes:
            deflection = mechanical_inputs.get(axis, 0.0)

            # ── Layer 1: MET ─────────────────────────────────────────────
            met = self.met_neurons[axis]
            met.step(deflection, dt)

            # ── MET → HC: soft saturate + FIFO delay ─────────────────────
            raw_met_currents = self.bundles_met_to_hc[axis].propagate()
            i_met_raw = raw_met_currents[0] if raw_met_currents else 0.0
            i_met_sat = soft_saturate(i_met_raw, r_supply=0.05)
            i_hc_in = self.fifo_met_to_hc[axis].push_and_pop(i_met_sat)

            # ── Layer 2: HairCell ─────────────────────────────────────────
            hc = self.haircell_neurons[axis]
            hc.step(i_hc_in, dt)

            # ── Bridge Ca²⁺ release → HC activation for bundle.propagate()
            # (same bridge as VestibularChain.step() — must be preserved)
            hc.activation = hc.release_rate
            _decay = math.exp(-_log_dt / max(hc.config.trace_tau_pre * 0.001, 0.001))
            hc.pre_trace = hc.pre_trace * _decay + abs(hc.release_rate)
            hc.pre_trace = min(hc.pre_trace, 10.0)

            # ── HC → Aff: soft saturate + FIFO delay ─────────────────────
            raw_aff_currents = self.bundles_hc_to_aff[axis].propagate()
            sat_aff = [soft_saturate(c, r_supply=0.05) for c in raw_aff_currents]

            # One FIFO per axis; both aff_reg and aff_irr share the same HC source
            # delay (same axon distance). Use primary current for FIFO; irr gets same delay.
            i_aff_primary = sat_aff[0] if sat_aff else 0.0
            i_aff_delayed = self.fifo_hc_to_aff[axis].push_and_pop(i_aff_primary)

            # ── Layer 4: Afferents ────────────────────────────────────────
            aff_r = self.afferent_regular[axis]
            aff_i = self.afferent_irregular[axis]
            if len(sat_aff) >= 2:
                aff_r.step(i_aff_delayed, dt)
                # Irregular aff: soft_saturate already applied above (sat_aff[1])
                # Apply same FIFO delay (identical source distance)
                aff_i.step(i_aff_delayed, dt)
            else:
                aff_r.step(i_aff_delayed, dt)
                aff_i.step(i_aff_delayed, dt)

        # ── STDP / learning ───────────────────────────────────────────────
        for axis in self.axes:
            self.bundles_met_to_hc[axis].learn(dt)
            self.bundles_hc_to_aff[axis].learn(dt)

    def network_summary(self) -> dict:
        """Report network layer topology (V-N6 verification helper)."""
        return self.network.summary()
