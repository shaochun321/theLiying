"""governance.validator — Parameter Physical Plausibility Validator.

Checks:
    V1. Dimensional consistency (units match)
    V2. Boundary plausibility (physical range)
    V3. Numerical stability (τ > dt)
    V4. Symmetry provenance (physical vs artificial)
    V5. Baseline impact (does change break baseline activity)

Usage:
    v = Validator()
    ok = v.check_stability(tau=5.0, dt=0.001)
    ok = v.check_boundary(param="w", value=0.5, bounds=(0.0, 1.0))
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class ValidationResult:
    """Result of a validation check."""
    rule_id: str
    passed: bool
    message: str
    param_name: str = ""


class Validator:
    """Parameter physical plausibility validator."""

    _results: List[ValidationResult] = field(default_factory=list)

    def __init__(self):
        self._results = []

    def check_stability(self, tau: float, dt: float,
                        param_name: str = ""
                        ) -> ValidationResult:
        """V3: Check numerical stability.

        τ must be >> dt for stable integration.
        Rule of thumb: τ/dt > 5 for Euler, τ/dt > 2 for RK2.
        """
        ratio = tau / max(dt, 1e-15)
        if ratio < 2:
            r = ValidationResult(
                rule_id="V3", passed=False,
                message=(f"UNSTABLE: τ={tau}, dt={dt}, ratio={ratio:.1f} < 2. "
                         f"Integration will diverge."),
                param_name=param_name,
            )
        elif ratio < 5:
            r = ValidationResult(
                rule_id="V3", passed=True,
                message=(f"MARGINAL: τ={tau}, dt={dt}, ratio={ratio:.1f}. "
                         f"Stable with RK2, not with Euler."),
                param_name=param_name,
            )
        else:
            r = ValidationResult(
                rule_id="V3", passed=True,
                message=f"STABLE: τ/dt={ratio:.1f}",
                param_name=param_name,
            )
        self._results.append(r)
        return r

    def check_boundary(self, param: str, value: float,
                       bounds: Tuple[float, float]
                       ) -> ValidationResult:
        """V2: Check parameter boundary plausibility."""
        lo, hi = bounds
        if value < lo or value > hi:
            r = ValidationResult(
                rule_id="V2", passed=False,
                message=(f"OUT OF BOUNDS: {param}={value} ∉ [{lo}, {hi}]"),
                param_name=param,
            )
        elif value == lo or value == hi:
            r = ValidationResult(
                rule_id="V2", passed=True,
                message=f"AT BOUNDARY: {param}={value} (edge of [{lo}, {hi}])",
                param_name=param,
            )
        else:
            r = ValidationResult(
                rule_id="V2", passed=True,
                message=f"OK: {param}={value} ∈ [{lo}, {hi}]",
                param_name=param,
            )
        self._results.append(r)
        return r

    def check_baseline_impact(self, bc_current: float, r_leak: float,
                              v_th: float
                              ) -> ValidationResult:
        """V5: Check if parameters support baseline activity.

        From G-001 v2.0 §1E.1:
            V_ss = bc_current × R_leak
            Need V_ss ≈ V_th for meaningful baseline.
        """
        v_ss = bc_current * r_leak
        ratio = v_ss / max(v_th, 1e-10)

        if ratio < 0.1:
            r = ValidationResult(
                rule_id="V5", passed=False,
                message=(
                    f"NO BASELINE: V_ss={v_ss:.4f} << V_th={v_th}. "
                    f"Need bc_current >= {v_th/r_leak:.4f}."
                ),
                param_name="bc_current",
            )
        elif ratio < 0.8:
            r = ValidationResult(
                rule_id="V5", passed=True,
                message=(
                    f"SUBTHRESHOLD ONLY: V_ss={v_ss:.4f} < V_th={v_th}. "
                    f"Baseline from subthreshold current only."
                ),
                param_name="bc_current",
            )
        elif ratio <= 1.2:
            r = ValidationResult(
                rule_id="V5", passed=True,
                message=(
                    f"GOOD BASELINE: V_ss={v_ss:.4f} ~= V_th={v_th}. "
                    f"Near-threshold operation."
                ),
                param_name="bc_current",
            )
        else:
            r = ValidationResult(
                rule_id="V5", passed=True,
                message=(
                    f"HIGH BASELINE: V_ss={v_ss:.4f} > V_th={v_th}. "
                    f"Strong tonic firing."
                ),
                param_name="bc_current",
            )

        self._results.append(r)
        return r

    def check_symmetry_source(self, operation: str,
                              physical_reason: str = ""
                              ) -> ValidationResult:
        """V4: Check if symmetry operation has physical origin.

        From G-001 v2.0 §2.2: BCM naturally symmetric,
        don't force symmetrize.
        """
        if not physical_reason:
            r = ValidationResult(
                rule_id="V4", passed=False,
                message=(
                    f"ARTIFICIAL SYMMETRY: '{operation}' has no physical "
                    f"reason. If the physics produces asymmetry, keep it."
                ),
                param_name=operation,
            )
        else:
            r = ValidationResult(
                rule_id="V4", passed=True,
                message=(
                    f"PHYSICAL SYMMETRY: '{operation}' justified by "
                    f"'{physical_reason}'."
                ),
                param_name=operation,
            )
        self._results.append(r)
        return r

    def get_results(self) -> List[ValidationResult]:
        """Return all validation results."""
        return list(self._results)

    def all_passed(self) -> bool:
        """Check if all validations passed."""
        return all(r.passed for r in self._results)

    def print_report(self):
        """Print validation report."""
        passed = sum(1 for r in self._results if r.passed)
        total = len(self._results)
        print(f"Validator: {passed}/{total} passed")
        for r in self._results:
            icon = "[OK]" if r.passed else "[XX]"
            print(f"  {icon} [{r.rule_id}] {r.message}")
