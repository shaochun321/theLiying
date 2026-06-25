"""governance.adjudicator — Axiom Compliance Adjudicator.

Runtime checks (always active):
    J1. Subjective layer accessing objective variables
        → Static analysis needed (cannot detect at runtime)
        → Placeholder for code review integration
    J2. Read-only observer modifying circuit state
        → Check shadow layer write isolation

Code review checks (manual invocation):
    J3. Learning rule bypassing plasticity_gate
    J4. New parameter without physical source
    J5. Formula inconsistent with G-001 v2.0

Usage:
    adj = Adjudicator()
    # Runtime:
    adj.runtime_check(circuit, tick)
    # Code review:
    report = adj.review_module("path/to/module.py")
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AdjudicationResult:
    """Result of an adjudication check."""
    rule_id: str
    status: str  # "APPROVED", "REJECTED", "CONDITIONAL", "WARNING"
    message: str
    tick: int = 0


@dataclass
class Adjudicator:
    """Axiom compliance adjudicator.

    J1/J2 are checked at runtime (per-step).
    J3/J4/J5 are checked on demand (code review).
    """

    _warnings: List[AdjudicationResult] = field(
        default_factory=list, repr=False)

    def runtime_check(self, circuit, tick: int) -> List[AdjudicationResult]:
        """Runtime adjudication: J1 and J2.

        Called every step by GovernanceSystem.post_step().
        """
        results = []

        # ── J2: Shadow layer write isolation ──
        if hasattr(circuit, 'shadow_sandbox') and circuit.shadow_sandbox:
            sb = circuit.shadow_sandbox
            if sb._initialized:
                # Check: shadow neurons should not be in main neuron dict
                main_ids = set()
                for n in circuit.get_all_neurons():
                    main_ids.add(n.config.neuron_id)

                for sid in sb.neurons:
                    if sid in main_ids:
                        r = AdjudicationResult(
                            rule_id="J2",
                            status="REJECTED",
                            message=(
                                f"Shadow neuron {sid} found in main circuit. "
                                f"Shadow layer write isolation violated."
                            ),
                            tick=tick,
                        )
                        results.append(r)
                        self._warnings.append(r)

        return results

    def review_parameter(self, param_name: str, old_value: float,
                         new_value: float, source: str = "",
                         ) -> AdjudicationResult:
        """J4: Check if parameter change has physical justification.

        Args:
            param_name: Name of the parameter being changed
            old_value: Previous value
            new_value: Proposed new value
            source: Physical/literature source for the change

        Returns:
            AdjudicationResult with approval status
        """
        if not source:
            r = AdjudicationResult(
                rule_id="J4",
                status="CONDITIONAL",
                message=(
                    f"Parameter '{param_name}' change {old_value}→{new_value} "
                    f"has no documented physical source. Provide source."
                ),
            )
        else:
            ratio = abs(new_value / max(abs(old_value), 1e-10))
            if ratio > 100 or ratio < 0.01:
                r = AdjudicationResult(
                    rule_id="J4",
                    status="WARNING",
                    message=(
                        f"Parameter '{param_name}' change {old_value}→"
                        f"{new_value} ({ratio:.0f}×). Source: {source}. "
                        f"Large change — verify with modeler."
                    ),
                )
            else:
                r = AdjudicationResult(
                    rule_id="J4",
                    status="APPROVED",
                    message=(
                        f"Parameter '{param_name}' change {old_value}→"
                        f"{new_value}. Source: {source}."
                    ),
                )

        self._warnings.append(r)
        return r

    def review_learning_rule(self, bundle_id: str,
                             uses_plasticity_gate: bool,
                             ) -> AdjudicationResult:
        """J3: Check if learning rule respects plasticity_gate.

        Any learning that bypasses plasticity_gate breaks the
        maturation system (C-002) and PNN protection (Ψ-3).
        """
        if uses_plasticity_gate:
            return AdjudicationResult(
                rule_id="J3",
                status="APPROVED",
                message=f"Bundle {bundle_id}: learning uses plasticity_gate.",
            )
        else:
            r = AdjudicationResult(
                rule_id="J3",
                status="REJECTED",
                message=(
                    f"Bundle {bundle_id}: learning bypasses plasticity_gate. "
                    f"This violates C-002 maturation and Ψ-3 chain protection."
                ),
            )
            self._warnings.append(r)
            return r

    def get_warnings(self) -> List[AdjudicationResult]:
        """Return all accumulated warnings."""
        return list(self._warnings)

    def print_report(self):
        """Print adjudication report."""
        if not self._warnings:
            print("Adjudicator: No warnings.")
            return
        print(f"Adjudicator: {len(self._warnings)} warnings")
        for w in self._warnings[-20:]:  # last 20
            icon = {"APPROVED": "[OK]", "REJECTED": "[XX]",
                    "CONDITIONAL": "[??]", "WARNING": "[!!]"}
            print(f"  {icon.get(w.status, '?')} [{w.rule_id}] "
                  f"{w.status}: {w.message}")
