"""nexus_v1.ledger.nu_probe — ν (nu) Xin-tension power flux probe.

TYPE:INFRA

Computes ν(t) = ξ|O−P| − ξ²/R_ξ per bundle at every timestep.

Physical interpretation:
  ν > 0  →  charging (error-injection > dissipation): exploration / plasticity open
  ν < 0  →  discharging (dissipation > error-injection): consolidation

Formula derivation (from nu_framework_stub.py):
  Xin dynamics:  C_ξ dξ/dt = −ξ/R_ξ + |O−P|
  Power (×ξ):    ν = d(½C_ξξ²)/dt = ξ|O−P| − ξ²/R_ξ

|O−P| inference (read-only, no bundle modification):
  Bundle update:  ξ_new = ξ_old × exp(−dt/τ) + |O−P| × dt
  Inverting:      |O−P| = (ξ_new − ξ_old × exp(−dt/τ)) / dt

Where τ = R_ξ = XIN_LEAK_TAU = 1000.0 (from bundle.py).

Pure observer — reads circuit state, NEVER writes.
REF: nexus_v1/ledger/nu_framework_stub.py (2026-06-30)
REF: 对架构师反馈的综合评估与最终裁决.md §1.1
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Matches XIN_LEAK_TAU in bundle.py — READ ONLY, never modify this value here.
_R_XI = 1000.0  # Xin dissipation resistance [sim time units]


@dataclass
class NuSnapshot:
    """Per-bundle ν measurement at a single timestep."""
    bundle_id: str
    step: int
    xi: float           # current Xin tension ξ[t]
    residual: float     # inferred |O−P|[t]
    nu: float           # ν = ξ|O−P| − ξ²/R_ξ
    state: str          # "charging" (ν>0) | "discharging" (ν<0) | "idle" (ξ≈0)


@dataclass
class NuReport:
    """Aggregated ν statistics over the tracking window."""
    step: int
    # Per-bundle ν mean (exponential moving average)
    bundle_nu_ema: Dict[str, float] = field(default_factory=dict)
    # Counts of charging vs discharging bundles
    n_charging: int = 0
    n_discharging: int = 0
    n_idle: int = 0
    # System-level ν (sum across all bundles)
    system_nu: float = 0.0
    # Bundle with maximum |ν| (highest plasticity signal)
    max_nu_bundle: str = ""
    max_nu_value: float = 0.0


class NuProbe:
    """Read-only ν power flux probe for all bundles in the circuit.

    Usage:
        probe = NuProbe(ema_alpha=0.01)   # α = 1/N_steps smoothing
        # In simulation loop:
        probe.update(circuit, step, dt)
        # Every K steps:
        report = probe.report(step)
        print(report)
    """

    def __init__(self, ema_alpha: float = 0.001, idle_threshold: float = 1e-6):
        """
        Args:
            ema_alpha: EMA smoothing factor for ν per bundle.
                       α = 1/1000 → ~1000-step window.
            idle_threshold: ξ below this → bundle treated as idle (ν undefined).
        """
        self._ema_alpha = ema_alpha
        self._idle_threshold = idle_threshold
        self._prev_xi: Dict[str, float] = {}       # ξ[t-1] per bundle
        self._nu_ema: Dict[str, float] = {}         # EMA of ν per bundle
        self._step_count = 0
        self._last_snapshots: List[NuSnapshot] = []

    def update(self, circuit, step: int, dt: float = 0.001) -> None:
        """Compute ν for all bundles at this timestep.

        Call once per simulation step AFTER circuit.step() has run
        (so bundle.config.xin_tension already reflects the new ξ[t]).
        """
        self._step_count = step
        bundles = circuit.get_all_bundles()
        snapshots = []

        leak_factor = math.exp(-dt / _R_XI)  # = exp(-dt/1000)

        for b in bundles:
            bid = b.config.bundle_id
            xi_new = b.config.xin_tension
            xi_old = self._prev_xi.get(bid, xi_new)  # first call: assume no change

            # Infer |O−P| from Xin dynamics (read-only)
            residual_times_dt = xi_new - xi_old * leak_factor
            residual = residual_times_dt / max(dt, 1e-12)

            # ν = ξ|O−P| − ξ²/R_ξ
            if abs(xi_new) < self._idle_threshold:
                nu_val = 0.0
                state = "idle"
            else:
                nu_val = xi_new * residual - xi_new ** 2 / _R_XI
                state = "charging" if nu_val > 0 else "discharging"

            # EMA update
            if bid not in self._nu_ema:
                self._nu_ema[bid] = nu_val
            else:
                self._nu_ema[bid] = (self._ema_alpha * nu_val
                                     + (1.0 - self._ema_alpha) * self._nu_ema[bid])

            self._prev_xi[bid] = xi_new
            snapshots.append(NuSnapshot(
                bundle_id=bid, step=step,
                xi=xi_new, residual=residual, nu=nu_val, state=state))

        self._last_snapshots = snapshots

    def report(self, step: int) -> NuReport:
        """Generate aggregated ν report from current EMA values."""
        r = NuReport(step=step)
        r.bundle_nu_ema = dict(self._nu_ema)

        total_nu = 0.0
        max_abs = 0.0

        for snap in self._last_snapshots:
            nu_ema = self._nu_ema.get(snap.bundle_id, 0.0)
            if snap.state == "idle":
                r.n_idle += 1
            elif nu_ema > 0:
                r.n_charging += 1
            else:
                r.n_discharging += 1

            total_nu += nu_ema
            if abs(nu_ema) > max_abs:
                max_abs = abs(nu_ema)
                r.max_nu_bundle = snap.bundle_id
                r.max_nu_value = nu_ema

        r.system_nu = total_nu
        return r

    def top_bundles(self, n: int = 10, by: str = "abs") -> List[NuSnapshot]:
        """Return top-N bundles sorted by |ν| or ν.

        Args:
            n: number of bundles to return.
            by: "abs" (|ν|) or "raw" (signed ν).
        """
        key = (lambda s: abs(self._nu_ema.get(s.bundle_id, 0.0))
               if by == "abs"
               else lambda s: self._nu_ema.get(s.bundle_id, 0.0))
        return sorted(self._last_snapshots, key=key, reverse=True)[:n]

    def format_report(self, report: NuReport, top_n: int = 8) -> str:
        """Human-readable ν report string."""
        lines = [
            f"ν Report (step={report.step})",
            f"  system ν = {report.system_nu:+.4f}  "
            f"[charging={report.n_charging} discharging={report.n_discharging} idle={report.n_idle}]",
            f"  peak: {report.max_nu_bundle} ν={report.max_nu_value:+.4f}",
            "  Top bundles (EMA):",
        ]
        for snap in self.top_bundles(top_n):
            nu_ema = self._nu_ema.get(snap.bundle_id, 0.0)
            bar_len = int(min(abs(nu_ema) * 500, 20))
            bar = ('▲' if nu_ema > 0 else '▽') * bar_len
            lines.append(f"    {snap.bundle_id:40s} ν={nu_ema:+.5f}  ξ={snap.xi:.4f}  {bar}")
        return "\n".join(lines)

    @property
    def system_nu_ema(self) -> float:
        """Current EMA of system-level ν (sum across all bundles)."""
        return sum(self._nu_ema.values())

    @property
    def charging_fraction(self) -> float:
        """Fraction of non-idle bundles currently charging (ν>0)."""
        non_idle = [v for v in self._nu_ema.values() if abs(v) > 1e-10]
        if not non_idle:
            return 0.0
        return sum(1 for v in non_idle if v > 0) / len(non_idle)
