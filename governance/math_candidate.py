"""governance.math_candidate — Mathematical Formula Lifecycle Manager.

Tracks formulas from proposal → testing → adoption/rejection.

Lifecycle:
    PROPOSED  → formula submitted with source and expected effect
    TESTING   → being validated (modeler or experiment)
    ADOPTED   → integrated into G-001 and code
    REJECTED  → failed validation (preserved for record)
    WITHDRAWN → proposer withdrew (preserved for record)

Usage:
    mc = MathCandidateRegistry()
    cid = mc.propose(
        formula="ds² = Σ g_ij δa_i δa_j",
        source="G-001 v2.0 §2.2",
        expected_effect="Direction-aware spatial metric",
        replaces="ds² = Σ w_cross |a_i| |a_j|",
    )
    mc.advance(cid, "TESTING")
    mc.advance(cid, "ADOPTED")
    mc.print_registry()
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class MathCandidate:
    """A mathematical formula candidate."""
    id: str
    formula: str
    source: str
    expected_effect: str
    replaces: str = ""
    status: str = "PROPOSED"  # PROPOSED/TESTING/ADOPTED/REJECTED/WITHDRAWN
    history: List[str] = field(default_factory=list)
    rejection_reason: str = ""

    def __post_init__(self):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.history.append(f"{ts}: PROPOSED")


class MathCandidateRegistry:
    """Registry for mathematical formula lifecycle management."""

    def __init__(self):
        self._candidates: Dict[str, MathCandidate] = {}
        self._next_id: int = 1

    def propose(self, formula: str, source: str,
                expected_effect: str, replaces: str = "",
                ) -> str:
        """Submit a new formula candidate.

        Returns: candidate ID (e.g., "MC-001")
        """
        # Check for duplicates
        for c in self._candidates.values():
            if c.formula == formula and c.status not in (
                    "REJECTED", "WITHDRAWN"):
                return c.id  # already proposed

        cid = f"MC-{self._next_id:03d}"
        self._next_id += 1

        self._candidates[cid] = MathCandidate(
            id=cid,
            formula=formula,
            source=source,
            expected_effect=expected_effect,
            replaces=replaces,
        )
        return cid

    def advance(self, cid: str, new_status: str,
                reason: str = ""):
        """Advance a candidate to a new lifecycle stage."""
        if cid not in self._candidates:
            raise KeyError(f"Unknown candidate: {cid}")

        c = self._candidates[cid]
        valid_transitions = {
            "PROPOSED": ["TESTING", "REJECTED", "WITHDRAWN"],
            "TESTING": ["ADOPTED", "REJECTED", "WITHDRAWN"],
            "ADOPTED": ["WITHDRAWN"],  # can be un-adopted
            "REJECTED": [],  # terminal
            "WITHDRAWN": [],  # terminal
        }

        if new_status not in valid_transitions.get(c.status, []):
            raise ValueError(
                f"Invalid transition: {c.status} → {new_status}. "
                f"Valid: {valid_transitions.get(c.status, [])}"
            )

        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        c.history.append(f"{ts}: {c.status} → {new_status}")
        if reason:
            c.history.append(f"  reason: {reason}")
        if new_status == "REJECTED":
            c.rejection_reason = reason
        c.status = new_status

    def get_active(self) -> List[MathCandidate]:
        """Return all non-terminal candidates."""
        return [c for c in self._candidates.values()
                if c.status in ("PROPOSED", "TESTING")]

    def get_adopted(self) -> List[MathCandidate]:
        """Return all adopted candidates."""
        return [c for c in self._candidates.values()
                if c.status == "ADOPTED"]

    def get_rejected(self) -> List[MathCandidate]:
        """Return all rejected candidates (for record)."""
        return [c for c in self._candidates.values()
                if c.status == "REJECTED"]

    def print_registry(self):
        """Print full registry."""
        print("=" * 70)
        print("数 理 候 选 登 记 (Math Candidate Registry)")
        print("=" * 70)

        for status in ["ADOPTED", "TESTING", "PROPOSED",
                        "REJECTED", "WITHDRAWN"]:
            candidates = [c for c in self._candidates.values()
                          if c.status == status]
            if not candidates:
                continue

            icon = {"ADOPTED": "[OK]", "TESTING": "[..]", "PROPOSED": "[??]",
                    "REJECTED": "[XX]", "WITHDRAWN": "[--]"}
            print(f"\n  {icon.get(status, '?')} {status} "
                  f"({len(candidates)} formulas)")
            for c in candidates:
                print(f"    [{c.id}] {c.formula}")
                print(f"           source: {c.source}")
                if c.replaces:
                    print(f"           replaces: {c.replaces}")
                if c.rejection_reason:
                    print(f"           rejection: {c.rejection_reason}")
