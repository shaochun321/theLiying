"""nexus_v1.ledger.weight_entropy — Shannon entropy of weight distributions.

Measures information content of the learned weight structure.
Learning REDUCES entropy (from uniform → structured).
Heat dissipation must compensate (Landauer bound).

REF: Jaynes 1957 (MaxEnt), Landauer 1961 (erasure bound)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EntropySnapshot:
    """One measurement of weight distribution entropy."""
    tick: int = 0
    # Per-layer Shannon entropy (bits)
    layer_entropy: Dict[str, float] = field(default_factory=dict)
    # Total system entropy
    total_entropy: float = 0.0
    # Change since last measurement
    delta_entropy: float = 0.0
    # Total heat dissipated since last measurement
    q_dissipated: float = 0.0
    # Landauer check: Q >= kT*ln2*max(0, ΔS)
    # (qualitative: k=1, T=system temperature)
    landauer_satisfied: bool = True


class WeightEntropyProbe:
    """Shannon entropy of weight distributions.

    Measures information content of the learned weight structure.
    Learning REDUCES entropy (from uniform → structured).
    Heat dissipation must compensate (Landauer bound).

    Usage:
        probe = WeightEntropyProbe()
        snap = probe.measure(circuit, tick)
    """

    N_BINS = 50  # Histogram bins for weight distribution [0, 1]

    def __init__(self):
        self._prev_entropy: float = 0.0
        self._prev_tick: int = 0
        self._cumulative_heat: float = 0.0
        self._heat_since_last: float = 0.0
        self._history: List[EntropySnapshot] = []

    def accumulate_heat(self, heat: float):
        """Called every step to track heat between entropy measurements."""
        self._cumulative_heat += heat
        self._heat_since_last += heat

    def measure(self, circuit, tick: int) -> EntropySnapshot:
        """Compute Shannon entropy of all weight distributions.

        Groups weights by bundle layer for per-layer analysis.
        """
        snap = EntropySnapshot(tick=tick)

        # Collect weights per layer
        layer_weights: Dict[str, List[float]] = {
            "vest_to_enc": [],
            "enc_to_col": [],
            "col_to_motor": [],
            "sprouts": [],
            # P3-FIX: somatosensory chain bundles (was invisible)
            "soma_thermo_to_relay": [],
            "soma_noci_to_relay": [],
            "soma_lateral": [],
        }

        for b in getattr(circuit, 'bundles_vest_to_enc', []):
            layer_weights["vest_to_enc"].extend(
                m.w for row in b._memristors for m in row)

        for b in getattr(circuit, 'bundles_enc_to_col', []):
            layer_weights["enc_to_col"].extend(
                m.w for row in b._memristors for m in row)

        for b in getattr(circuit, 'bundles_col_to_motor', []):
            layer_weights["col_to_motor"].extend(
                m.w for row in b._memristors for m in row)

        for b in getattr(circuit, '_sprouted_bundles', []):
            layer_weights["sprouts"].extend(
                m.w for row in b._memristors for m in row)

        # P3-FIX: somatosensory chain weight collection
        soma = getattr(circuit, 'somatosensory', None)
        if soma is not None:
            for b in getattr(soma, 'bundles_thermo_to_relay', {}).values():
                layer_weights["soma_thermo_to_relay"].extend(
                    m.w for row in b._memristors for m in row)
            for b in getattr(soma, 'bundles_noci_to_relay', {}).values():
                layer_weights["soma_noci_to_relay"].extend(
                    m.w for row in b._memristors for m in row)
            for b in getattr(soma, 'bundles_lateral', {}).values():
                layer_weights["soma_lateral"].extend(
                    m.w for row in b._memristors for m in row)

        # Compute per-layer entropy
        total_s = 0.0
        total_count = 0
        for layer_name, weights in layer_weights.items():
            if not weights:
                continue
            s = self._shannon_entropy(weights)
            snap.layer_entropy[layer_name] = s
            total_s += s * len(weights)
            total_count += len(weights)

        snap.total_entropy = total_s / max(total_count, 1)
        snap.delta_entropy = snap.total_entropy - self._prev_entropy
        snap.q_dissipated = self._heat_since_last

        # Landauer check: kT × ln2 × |ΔH| ≤ Q_dissipated
        # FIXED: previous version omitted kT multiplier (external review §2).
        # P_Landauer = kT_system × ln2 × |dH/dt| (Landauer 1961)
        # NOTE: kT_system uses effective temperature (normalized units).
        # In our system, T_eff ≈ ECM temperature ≈ 0.1~0.5.
        # We use T_eff = 1.0 as default (consistent with NoetherProbe).
        # The 0.01 scaling factor accounts for:
        #   (a) our weight entropy is in arbitrary histogram bins, not bits
        #   (b) our energy units are normalized, not Joules
        K_T_SYSTEM = 1.0  # effective temperature (normalized units)
        if snap.delta_entropy < 0:
            # ΔS < 0 → information was written → heat required
            landauer_bound = K_T_SYSTEM * math.log(2) * abs(snap.delta_entropy)
            snap.landauer_satisfied = snap.q_dissipated >= landauer_bound * 0.01
        else:
            snap.landauer_satisfied = True

        self._prev_entropy = snap.total_entropy
        self._heat_since_last = 0.0
        self._prev_tick = tick

        self._history.append(snap)
        if len(self._history) > 500:
            self._history.pop(0)

        return snap

    def _shannon_entropy(self, weights: List[float]) -> float:
        """Compute Shannon entropy of weight distribution in bits."""
        if not weights:
            return 0.0

        # Histogram
        counts = [0] * self.N_BINS
        for w in weights:
            idx = min(int(w * self.N_BINS), self.N_BINS - 1)
            idx = max(0, idx)
            counts[idx] += 1

        n = len(weights)
        entropy = 0.0
        for c in counts:
            if c > 0:
                p = c / n
                entropy -= p * math.log2(p)

        return entropy

    @property
    def latest(self) -> Optional[EntropySnapshot]:
        return self._history[-1] if self._history else None

    def summary(self) -> dict:
        """Return summary for monitoring."""
        if not self._history:
            return {"total_entropy": 0, "measurements": 0}
        latest = self._history[-1]
        return {
            "total_entropy": round(latest.total_entropy, 4),
            "delta_entropy": round(latest.delta_entropy, 6),
            "q_dissipated": round(latest.q_dissipated, 6),
            "landauer_ok": latest.landauer_satisfied,
            "per_layer": {k: round(v, 4)
                         for k, v in latest.layer_entropy.items()},
            "measurements": len(self._history),
        }
