"""nexus_v1.ledger.toprxin — T/O/P/R/Xin phase intensity mapping.

Maps circuit state to T/O/P/R/Xin phase intensities per bundle.
Ψ-1: T/O/P/R/Xin is organizational grammar, not runtime rule.

REF: v2.0 §0.2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class BundlePhaseIntensity:
    """T/O/P/R/Xin intensity for one bundle at one measurement."""
    bundle_id: str = ""
    t_intensity: float = 0.0    # Transmission: transport_cost
    o_intensity: float = 0.0    # Observation: |δa| of targets
    p_intensity: float = 0.0    # Prediction accuracy: 1/(1+|ξ|)
    r_intensity: float = 0.0    # Response: weight change rate
    xin_intensity: float = 0.0  # Mismatch: |ξ|


@dataclass
class TOPRXinSnapshot:
    """System-wide T/O/P/R/Xin state at one measurement."""
    tick: int = 0
    # Per-bundle phase intensities
    bundles: Dict[str, BundlePhaseIntensity] = field(default_factory=dict)
    # System-level aggregates
    total_t: float = 0.0
    total_o: float = 0.0
    total_p: float = 0.0
    total_r: float = 0.0
    total_xin: float = 0.0
    # DA state (links Xin → R)
    da_gain: float = 1.0
    da_xin_v: float = 0.0


class TOPRXinLedger:
    """Maps circuit state to T/O/P/R/Xin phase intensities.

    Ψ-1: T/O/P/R/Xin is organizational grammar, not runtime rule.
    The system doesn't "know" it's in phase T or R.
    This ledger observes and labels from outside.

    Every bundle simultaneously has all five phase intensities.
    The dominant phase tells us what's happening at that connection.
    """

    def __init__(self):
        self._history: List[TOPRXinSnapshot] = []
        self._prev_weights: Dict[str, float] = {}

    def measure(self, circuit, tick: int) -> TOPRXinSnapshot:
        """Measure T/O/P/R/Xin intensity for all bundles."""
        snap = TOPRXinSnapshot(tick=tick)

        all_bundles = circuit.get_all_bundles()
        for b in all_bundles:
            bpi = BundlePhaseIntensity(bundle_id=b.id)

            # T: Transmission intensity = transport cost
            bpi.t_intensity = b.transport_cost

            # O: Observation = mean |δa| of target neurons
            # δa = activation - baseline (EMA)
            delta_a_sum = 0.0
            for tgt in b.targets:
                if tgt.is_alive():
                    delta_a_sum += abs(tgt.activation - tgt._activation_ema)
            bpi.o_intensity = delta_a_sum / max(len(b.targets), 1)

            # P: Prediction accuracy = 1 / (1 + |ξ|)
            # High P = good prediction, low ξ
            xi = abs(b.config.xin_tension)
            bpi.p_intensity = 1.0 / (1.0 + xi)

            # R: Response = weight change rate since last measurement
            current_w = b.mean_weight()
            prev_w = self._prev_weights.get(b.id, current_w)
            bpi.r_intensity = abs(current_w - prev_w)
            self._prev_weights[b.id] = current_w

            # Xin: Mismatch intensity = |ξ|
            bpi.xin_intensity = xi

            snap.bundles[b.id] = bpi
            snap.total_t += bpi.t_intensity
            snap.total_o += bpi.o_intensity
            snap.total_p += bpi.p_intensity
            snap.total_r += bpi.r_intensity
            snap.total_xin += bpi.xin_intensity

        # DA state
        if hasattr(circuit, 'dopamine'):
            snap.da_gain = circuit.dopamine.gain_factor()
        if hasattr(circuit, '_xin_integrator'):
            snap.da_xin_v = circuit._xin_integrator.voltage

        self._history.append(snap)
        if len(self._history) > 500:
            self._history.pop(0)

        return snap

    @property
    def latest(self) -> Optional[TOPRXinSnapshot]:
        return self._history[-1] if self._history else None

    def summary(self) -> dict:
        """Return summary for monitoring."""
        if not self._history:
            return {}
        s = self._history[-1]
        return {
            "tick": s.tick,
            "T": round(s.total_t, 4),
            "O": round(s.total_o, 4),
            "P": round(s.total_p, 4),
            "R": round(s.total_r, 6),
            "Xin": round(s.total_xin, 4),
            "DA_gain": round(s.da_gain, 3),
            "n_bundles": len(s.bundles),
        }
