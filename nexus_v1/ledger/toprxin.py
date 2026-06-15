"""nexus_v1.ledger.toprxin — T/O/P/R/Xin phase intensity mapping.

Maps circuit state to T/O/P/R/Xin phase intensities per bundle.
Ψ-1: T/O/P/R/Xin is organizational grammar, not runtime rule.

REF: v2.0 §0.2
REF: analysis_concept_evolution.2026.5.21 §5 (ρ vector simplex)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RhoVector:
    """4-component probability simplex: ρ = (p, r, x, u), sum = 1.

    Continuous measure of a bundle's phase state.
    Replaces the former binary (has_P=True/False, has_R=True/False) encoding.

    Components:
      p  — prediction quality (stable absorption): high when ξ is small
      r  — response/learning activity: high when weights are changing
      x  — unresolved Xin residual: high when ξ is large
      u  — unaccounted (u = 1 - p - r - x): structural slack

    Constraint: p + r + x + u = 1  (probability simplex)

    REF: analysis_concept_evolution.2026.5.21 §5
         "4分量 ⊂ 7分量 ⊂ 8分量; earliest: ρ=(p,r,x,u), p+r+x+u=1"
    NORM(V12): upgrades from binary P/R flags to continuous simplex.
    """
    p: float = 0.0   # prediction quality fraction
    r: float = 0.0   # response/learning fraction
    x: float = 0.0   # Xin residual fraction
    u: float = 1.0   # unresolved fraction (default: fully unresolved)

    @property
    def dominant(self) -> str:
        """Return the dominant phase label."""
        vals = {'p': self.p, 'r': self.r, 'x': self.x, 'u': self.u}
        return max(vals, key=vals.get)

    @property
    def entropy(self) -> float:
        """Shannon entropy of the ρ distribution (bits). 0=pure, 2=uniform."""
        import math
        h = 0.0
        for v in (self.p, self.r, self.x, self.u):
            if v > 1e-10:
                h -= v * math.log2(v)
        return h


@dataclass
class BundlePhaseIntensity:
    """T/O/P/R/Xin intensity for one bundle at one measurement."""
    bundle_id: str = ""
    t_intensity: float = 0.0    # Transmission: transport_cost
    o_intensity: float = 0.0    # Observation: |δa| of targets
    p_intensity: float = 0.0    # Prediction accuracy: 1/(1+|ξ|)
    r_intensity: float = 0.0    # Response: weight change rate
    xin_intensity: float = 0.0  # Mismatch: |ξ|
    # NORM(V12): continuous simplex ρ vector (replaces binary P/R flags)
    rho: RhoVector = field(default_factory=RhoVector)


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
    # System-level ρ aggregate (mean across all bundles)
    mean_rho: RhoVector = field(default_factory=RhoVector)
    # DA state (links Xin → R)
    da_gain: float = 1.0
    da_xin_v: float = 0.0


def _compute_rho(xi: float, dw: float) -> RhoVector:
    """Compute 4-component ρ simplex for one bundle.

    Args:
        xi:  |ξ| = abs(xin_tension) — current Xin residual
        dw:  |Δmean_weight| since last measurement

    Returns:
        RhoVector with p + r + x + u = 1.
    """
    # Raw scores in [0, 1] range (scale factors tuned to typical magnitudes)
    p_raw = 1.0 / (1.0 + xi * 5.0)     # high when ξ small (good prediction)
    x_raw = min(xi * 5.0, 1.0)          # high when ξ large (unresolved residual)
    r_raw = min(abs(dw) * 50.0, 1.0)    # high when weights actively changing
    u_raw = 0.1                          # baseline unresolved slack

    total = p_raw + r_raw + x_raw + u_raw
    if total < 1e-10:
        return RhoVector(p=0.0, r=0.0, x=0.0, u=1.0)

    return RhoVector(
        p=p_raw / total,
        r=r_raw / total,
        x=x_raw / total,
        u=u_raw / total,
    )


class TOPRXinLedger:
    """Maps circuit state to T/O/P/R/Xin phase intensities.

    Ψ-1: T/O/P/R/Xin is organizational grammar, not runtime rule.
    The system doesn't "know" it's in phase T or R.
    This ledger observes and labels from outside.

    Every bundle simultaneously has all five phase intensities.
    The dominant phase tells us what's happening at that connection.

    V12: Each bundle now also carries a ρ vector (continuous simplex),
    replacing the former binary P/R presence flags.
    """

    def __init__(self):
        self._history: List[TOPRXinSnapshot] = []
        self._prev_weights: Dict[str, float] = {}

    def measure(self, circuit, tick: int) -> TOPRXinSnapshot:
        """Measure T/O/P/R/Xin intensity for all bundles."""
        snap = TOPRXinSnapshot(tick=tick)

        all_bundles = circuit.get_all_bundles()
        rho_p_sum = rho_r_sum = rho_x_sum = rho_u_sum = 0.0

        for b in all_bundles:
            bpi = BundlePhaseIntensity(bundle_id=b.id)

            # T: Transmission intensity = transport cost
            bpi.t_intensity = b.transport_cost

            # O: Observation = mean |δa| of target neurons
            delta_a_sum = 0.0
            for tgt in b.targets:
                if tgt.is_alive():
                    delta_a_sum += abs(tgt.activation - tgt._activation_ema)
            bpi.o_intensity = delta_a_sum / max(len(b.targets), 1)

            # P: Prediction accuracy = 1 / (1 + |ξ|)
            xi = abs(b.config.xin_tension)
            bpi.p_intensity = 1.0 / (1.0 + xi)

            # R: Response = weight change rate since last measurement
            current_w = b.mean_weight()
            prev_w = self._prev_weights.get(b.id, current_w)
            dw = current_w - prev_w
            bpi.r_intensity = abs(dw)
            self._prev_weights[b.id] = current_w

            # Xin: Mismatch intensity = |ξ|
            bpi.xin_intensity = xi

            # ρ vector: continuous simplex (V12)
            bpi.rho = _compute_rho(xi, dw)
            rho_p_sum += bpi.rho.p
            rho_r_sum += bpi.rho.r
            rho_x_sum += bpi.rho.x
            rho_u_sum += bpi.rho.u

            snap.bundles[b.id] = bpi
            snap.total_t += bpi.t_intensity
            snap.total_o += bpi.o_intensity
            snap.total_p += bpi.p_intensity
            snap.total_r += bpi.r_intensity
            snap.total_xin += bpi.xin_intensity

        # System-level ρ mean
        n = max(len(all_bundles), 1)
        snap.mean_rho = RhoVector(
            p=rho_p_sum / n,
            r=rho_r_sum / n,
            x=rho_x_sum / n,
            u=rho_u_sum / n,
        )

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
        rho = s.mean_rho
        return {
            "tick": s.tick,
            "T": round(s.total_t, 4),
            "O": round(s.total_o, 4),
            "P": round(s.total_p, 4),
            "R": round(s.total_r, 6),
            "Xin": round(s.total_xin, 4),
            "DA_gain": round(s.da_gain, 3),
            "n_bundles": len(s.bundles),
            # V12: ρ simplex aggregate
            "rho": {
                "p": round(rho.p, 4),
                "r": round(rho.r, 4),
                "x": round(rho.x, 4),
                "u": round(rho.u, 4),
                "dominant": rho.dominant,
                "entropy_bits": round(rho.entropy, 4),
            },
        }
