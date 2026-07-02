"""nexus_v1.circuit.bundle_v2 — DelayedBundle with τ_ij axonal conduction delay.

Extends SynapticBundle with per-connection delay derived from inter-neuron distance
and fiber conduction velocity. Implements a per-(source, target) ring buffer.

Units convention (must match the simulation):
  - dt: seconds  (0.001 s = 1 ms per step, the simulation's dt convention)
  - v_cond: mm / ms  (e.g. Aα = 50 mm/ms)
  - distance (from NeuronConfig.position): mm

Delay formula:
  τ_ms    = d_ij_mm / v_cond_mm_per_ms
  τ_steps = round(τ_ms / (dt_s × 1000))   # dt_s × 1000 converts seconds → ms

Fiber type presets (REF: Bear, Connors & Paradiso 2016 Ch.3;
                        Waxman & Ritchie 1993 Ann Neurol 33:121-137;
                        Bessou & Perl 1969 J Neurophysiol 32:1025-1043):
  Aα  — large myelinated (vestibular, proprioceptive): 50   mm/ms
  Aδ  — thin myelinated (fast pain, temperature):       5   mm/ms
  C   — unmyelinated (slow pain, warmth, C-tactile):    0.5 mm/ms

If either source or target has position=None, delay falls back to 0.

Usage:
    b = make_delayed(
        config=BundleConfig(bundle_id="hc_to_aff_yaw", ...),
        sources=[hc_yaw],
        targets=[aff_reg_yaw, aff_irr_yaw],
        v_cond_mm_per_ms=50.0,
        dt=0.001,    # seconds per simulation step
    )
"""

from __future__ import annotations

import math
from collections import deque
from typing import List, Optional

from .bundle import SynapticBundle, BundleConfig
from ..components.neuron import Neuron


# ─────────────────────────────────────────────────────────────────────
# Fiber type presets
# ─────────────────────────────────────────────────────────────────────
V_COND_AALPHA = 50.0   # BIO: Aα myelinated (vestibular, proprioceptive) mm/ms
V_COND_ADELTA = 5.0    # BIO: Aδ myelinated (fast pain, temperature)  mm/ms
V_COND_C      = 0.5    # BIO: C-fiber unmyelinated (noci, warmth)      mm/ms


class DelayedBundle(SynapticBundle):
    """TYPE:BIO — SynapticBundle with per-(source, target) axonal conduction delay.

    Each connection (source_i → target_j) carries a ring buffer of depth τ_ij steps.
    On every propagate(), current source signals are pushed into the buffer and the
    signal from τ_ij steps ago is forwarded to the targets.

    BIO: action potentials propagate at finite velocity along axons.
         τ_ij = d_ij / v_cond = propagation time in ms.
    REF: Bear, Connors & Paradiso 2016 Ch.3 — axon conduction velocity
    REF: Goldberg & Fernandez 1971 J Neurophysiol — vestibular afferent properties

    Implementation notes:
    - Inherits all STDP / Xin / ledger tracking from SynapticBundle.
    - Only propagate() is overridden; learn(), compute_xin() etc. are unchanged.
    - Currents are RETURNED (not injected) — same contract as base class.
      Caller uses apply_to_targets(currents, dt) to inject.
    """

    def __init__(
        self,
        config: BundleConfig,
        sources: List[Neuron],
        targets: List[Neuron],
        v_cond_mm_per_ms: float = V_COND_AALPHA,
        dt: float = 0.001,
    ):
        """
        Args:
            v_cond_mm_per_ms: axon conduction velocity in mm per millisecond.
            dt: simulation timestep in SECONDS (0.001 = 1 ms/step).
        """
        super().__init__(config=config, sources=sources, targets=targets)

        self._v_cond_mm_per_ms = v_cond_mm_per_ms
        self._dt_s = dt
        self._dt_ms = dt * 1000.0  # convert seconds to ms for delay computation

        n_src = len(sources)
        n_tgt = len(targets)

        # Build delay matrix (steps)
        self._delay: list[list[int]] = [
            [self._compute_delay_steps(sources[i], targets[j])
             for j in range(n_tgt)]
            for i in range(n_src)
        ]

        # Build ring buffers: buffer[i][j] holds signals for the i→j connection.
        # maxlen = delay + 1 so the oldest element is always at index -1.
        # At delay=0: maxlen=1 → buffer[i][j][-1] == the just-pushed signal.
        self._buffers: list[list[deque]] = [
            [deque([0.0] * (self._delay[i][j] + 1), maxlen=self._delay[i][j] + 1)
             for j in range(n_tgt)]
            for i in range(n_src)
        ]

        self._max_delay: int = max(
            (self._delay[i][j] for i in range(n_src) for j in range(n_tgt)),
            default=0,
        )

    def _compute_delay_steps(self, src: Neuron, tgt: Neuron) -> int:
        """Compute propagation delay in simulation steps.

        τ_ms    = d_ij_mm / v_cond_mm_per_ms
        τ_steps = round(τ_ms / dt_ms)        # dt_ms = dt_s × 1000

        Returns 0 if either neuron has position=None (instantaneous fallback).
        """
        ps = getattr(src.config, 'position', None)
        pt = getattr(tgt.config, 'position', None)
        if ps is None or pt is None:
            return 0
        if self._v_cond_mm_per_ms <= 0 or self._dt_ms <= 0:
            return 0
        d_mm = math.sqrt(sum((ps[k] - pt[k]) ** 2 for k in range(3)))
        tau_ms = d_mm / self._v_cond_mm_per_ms
        tau_steps = tau_ms / self._dt_ms
        return max(0, round(tau_steps))

    def propagate(self) -> List[float]:
        """Propagate delayed source signals to targets.

        Mirrors the base SynapticBundle.propagate() signal selection:
          - spiking + CRI → calcium_rate
          - spiking (no CRI) → pre_trace
          - non-spiking → activation

        Returns list of currents (one per target), NOT injected yet.
        """
        n_src = len(self.sources)
        n_tgt = len(self.targets)

        # 1. Read current source signals (same selection as base class)
        current_signals: list[float] = []
        for src in self.sources:
            if not src.is_alive():
                current_signals.append(0.0)
                continue
            if src.config.spiking and hasattr(src, '_calcium_integrator') and src._calcium_integrator is not None:
                a_src = src.calcium_rate
            elif src.config.spiking:
                a_src = src.pre_trace
            else:
                a_src = src.activation
            current_signals.append(a_src)

        # 2. Push signals into ring buffers (appendleft → newest at index 0)
        for i in range(n_src):
            for j in range(n_tgt):
                self._buffers[i][j].appendleft(current_signals[i])

        # 3. Compute target currents from DELAYED signals (oldest = index -1)
        target_currents = [0.0] * n_tgt
        self.transport_cost = 0.0
        for i in range(n_src):
            buf_row = self._buffers[i]
            m_row = self._memristors[i]
            for j in range(n_tgt):
                delayed_signal = buf_row[j][-1]  # oldest entry = τ steps ago
                if abs(delayed_signal) < 1e-12:
                    continue
                current = m_row[j].conduct(delayed_signal) * self.config.synapse_gain
                target_currents[j] += current
                self.transport_cost += abs(current) * 0.001

        return target_currents

    def delay_table(self) -> dict:
        """Return {(src_id, tgt_id): delay_steps} for diagnostics."""
        result = {}
        for i, src in enumerate(self.sources):
            for j, tgt in enumerate(self.targets):
                result[(src.config.neuron_id, tgt.config.neuron_id)] = self._delay[i][j]
        return result

    def summary(self) -> dict:
        base = super().summary()
        base['max_delay_steps'] = self._max_delay
        base['v_cond_mm_per_ms'] = self._v_cond_mm_per_ms
        base['delay_table'] = self.delay_table()
        return base


def make_delayed(
    config: BundleConfig,
    sources: List[Neuron],
    targets: List[Neuron],
    v_cond_mm_per_ms: float = V_COND_AALPHA,
    dt: float = 0.001,
) -> DelayedBundle:
    """Factory: create a DelayedBundle (convenience wrapper).

    Args:
        v_cond_mm_per_ms: fiber conduction velocity (see V_COND_* presets).
        dt: simulation timestep in seconds.

    Example:
        b = make_delayed(config, [hc_yaw], [aff_reg_yaw, aff_irr_yaw],
                         v_cond_mm_per_ms=V_COND_AALPHA)
    """
    return DelayedBundle(
        config=config,
        sources=sources,
        targets=targets,
        v_cond_mm_per_ms=v_cond_mm_per_ms,
        dt=dt,
    )
