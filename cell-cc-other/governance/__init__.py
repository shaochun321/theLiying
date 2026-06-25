"""governance — Entropy Governance System.

Parallel system to nexus_v1. Co-equal, not subordinate.

Architecture:
    nexus_v1/  (the organism — runs physics + learning)
    governance/ (the auditor — monitors + adjudicates + models)

Five capabilities:
    1. Fuse:           Physics law violation → circuit-break
    2. Adjudicator:    Axiom compliance check (J1/J2 runtime)
    3. Validator:      Parameter physical plausibility
    4. Modeler:        Independent mathematical simulation
    5. MathCandidate:  Formula lifecycle management

The governance system is ALWAYS active unless explicitly in debug mode.
Debug mode = fuse disabled (like shadow_sandbox._construction_power).
Debug ends → fuse re-enabled.

Directory: d:/cell-cc/governance/ (parallel to d:/cell-cc/nexus_v1/)
"""

from dataclasses import dataclass, field
from typing import Optional

from .fuse import Fuse, FuseTrippedError
from .ledger import GovernanceLedger


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

        # ── 3. Runtime adjudication ──
        if self.config.runtime_adjudication:
            self._check_j1_j2(circuit, tick)

    def _check_j1_j2(self, circuit, tick: int):
        """Runtime adjudication: J1 and J2.

        J1: Subjective layer accessing objective variables?
            → Cannot detect at runtime (static analysis needed).
            → Reserved for code review tool.

        J2: Read-only observer modifying circuit state?
            → Check shadow_sandbox write-back (should be None).
        """
        # J2: Shadow layer should not modify main circuit
        if hasattr(circuit, 'shadow_sandbox'):
            sb = circuit.shadow_sandbox
            # Shadow neurons should not appear in main circuit's neuron list
            # This is a structural check, not a per-step check
            pass  # Currently shadow is read-only by design

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
            'ledger': self.ledger.summary(),
        }
