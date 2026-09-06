"""governance — Entropy Governance System.

Parallel system to nexus_v1. Co-equal, not subordinate.

Architecture:
    nexus_v1/  (the organism — runs physics + learning)
    governance/ (the auditor — monitors + adjudicates + models)

Five capabilities, two different activation modes:
    RUNTIME (called automatically every step by GovernanceSystem.post_step()):
        1. Fuse:           Physics law violation → circuit-break
        2. GovernanceLedger: Entropy/gain-chain bookkeeping
        3. Adjudicator:    Axiom compliance check (J1/J2 runtime)
    ON-DEMAND (design-time / code-review tools, invoked manually by a
    developer proposing a change — NOT wired into the per-step loop):
        4. Validator:      Parameter physical plausibility (check_stability,
                            check_boundary, etc. — call before committing
                            a parameter change)
        5. Modeler:        Independent mathematical prediction, run before
                            modifying a circuit parameter to estimate effect
        6. MathCandidate:  Formula lifecycle management (PROPOSED→ADOPTED)

    2026-09-06 audit: prior versions of this docstring implied all five/six
    capabilities run "every step" — false. Adjudicator was previously
    instantiated nowhere (see fix below); Validator/Modeler/MathCandidate
    are intentionally on-demand APIs (see their own module docstrings) and
    have simply never been invoked by a developer during code review so far
    — that is a process gap, not a wiring bug, and is not something this
    module can fix by force-calling them every step without a use case.

The runtime portion (Fuse + Ledger + Adjudicator) is ALWAYS active unless
explicitly in debug mode. Debug mode = fuse disabled (like
shadow_sandbox._construction_power). Debug ends → fuse re-enabled.
"""

from dataclasses import dataclass, field
from typing import Optional

from .fuse import Fuse, FuseTrippedError
from .ledger import GovernanceLedger
from .adjudicator import Adjudicator


@dataclass
class GovernanceConfig:
    """Configuration for the governance system."""

    # Debug mode: fuse disabled, warnings only
    debug_mode: bool = False

    # Fuse thresholds
    fuse_v_max: float = 50.0         # membrane voltage divergence
    fuse_energy_floor: float = -0.01  # allow tiny float errors
    fuse_entropy_window: int = 100    # steps for 2nd law check

    # Adjudicator: runtime checks (J1, J2)
    runtime_adjudication: bool = True

    # Ledger recording interval (every N steps)
    ledger_interval: int = 1

    # Governance overhead budget: skip expensive checks if > budget
    max_overhead_ms: float = 1.0


class GovernanceSystem:
    """Co-equal parallel system to nexus_v1.

    Usage:
        gov = GovernanceSystem()

        # In circuit.step():
        gov.pre_step(circuit, tick)
        # ... circuit logic ...
        gov.post_step(circuit, tick, dt)

        # Report:
        gov.ledger.print_report()
    """

    def __init__(self, config: Optional[GovernanceConfig] = None):
        self.config = config or GovernanceConfig()
        self.fuse = Fuse(
            v_max=self.config.fuse_v_max,
            energy_floor=self.config.fuse_energy_floor,
            entropy_window=self.config.fuse_entropy_window,
            enabled=not self.config.debug_mode,
        )
        self.ledger = GovernanceLedger(window_size=1000)
        self.adjudicator = Adjudicator()

        # Track governance overhead
        self._overhead_us: float = 0.0

    def pre_step(self, circuit, tick: int):
        """Pre-step checks. Called BEFORE circuit.step().

        Currently: no pre-step checks (reserved for future use).
        """
        pass

    def post_step(self, circuit, tick: int, dt: float):
        """Post-step checks. Called AFTER circuit.step().

        1. Ledger records state
        2. Fuse checks physics violations
        3. Runtime adjudication (J1/J2) if enabled
        """
        # ── 1. Ledger ──
        if tick % self.config.ledger_interval == 0:
            self.ledger.record(circuit, dt)

        # ── 2. Fuse (always check, trip behavior depends on enabled) ──
        violations = self.fuse.check(circuit, dt)
        if violations:
            self.fuse.trip(violations, tick)

        # ── 3. Runtime adjudication (J1/J2) ──
        # 2026-09-06 fix: this used to call a local `_check_j1_j2` stub whose
        # J2 branch was `pass` (no-op) — Adjudicator.runtime_check() already
        # implements the real J2 check (shadow neuron ID leak into main
        # circuit) but was never instantiated/called from here. Delegating
        # to it now makes the module docstring's "called every step by
        # GovernanceSystem.post_step()" claim (adjudicator.py:50) true.
        # J1 (subjective layer accessing objective variables) remains
        # undetectable at runtime per Adjudicator's own docstring — reserved
        # for a static-analysis/code-review tool, not fixable here.
        if self.config.runtime_adjudication:
            self.adjudicator.runtime_check(circuit, tick)

    def enable_fuse(self):
        """Re-enable fuse after debug session."""
        self.fuse.enabled = True
        self.config.debug_mode = False

    def disable_fuse(self):
        """Disable fuse for debug session."""
        self.fuse.enabled = False
        self.config.debug_mode = True

    def summary(self) -> dict:
        """Combined governance report."""
        return {
            'debug_mode': self.config.debug_mode,
            'fuse_enabled': self.fuse.enabled,
            'fuse_trips': self.fuse.trip_count,
            'adjudicator_warnings': len(self.adjudicator.get_warnings()),
            'ledger': self.ledger.summary(),
        }
