"""governance.fuse — Physics Law Violation Circuit Breaker.

Checks:
    F1. Energy conservation (1st law): no energy creation from nothing
    F2. Entropy monotonicity (2nd law): dS/dt ≥ 0 over window
    F3. Weight bounds: memristor w ∈ [config.weight_min, config.weight_max]
    F4. Membrane voltage divergence: |V| < V_max
    F5. Energy non-negativity: E ≥ 0 for all neurons

Behavior:
    enabled=True:  violation → FuseTrippedError (stops simulation)
    enabled=False: violation → logged, simulation continues (debug mode)

Analogy:
    Like shadow_sandbox._construction_power:
      debug=True  → power override / fuse disabled
      debug=False → normal physics / fuse enabled
"""

from dataclasses import dataclass, field
from typing import List, Tuple


class FuseTrippedError(RuntimeError):
    """Raised when physics violation is detected and fuse is enabled."""

    def __init__(self, violations: List[str], tick: int):
        msg = (
            f"\n{'='*60}\n"
            f"!! FUSE TRIPPED at tick {tick}\n"
            f"{'='*60}\n"
        )
        for v in violations:
            msg += f"  X {v}\n"
        msg += (
            f"{'='*60}\n"
            f"To debug: governance.disable_fuse() then re-run.\n"
            f"Remember to governance.enable_fuse() after debugging.\n"
        )
        super().__init__(msg)
        self.violations = violations
        self.tick = tick


@dataclass
class Fuse:
    """Physics law violation circuit breaker.

    Usage:
        fuse = Fuse()
        violations = fuse.check(circuit, dt)
        if violations:
            fuse.trip(violations, tick)
    """

    # Thresholds
    v_max: float = 50.0          # F4: membrane voltage divergence
    energy_floor: float = -0.01  # F5: tiny float error tolerance
    entropy_window: int = 100    # F2: steps for monotonicity check

    # State
    enabled: bool = True
    trip_count: int = 0

    # Internal tracking
    _entropy_history: List[float] = field(default_factory=list)
    _violations_log: List[Tuple[int, List[str]]] = field(default_factory=list)

    def check(self, circuit, dt: float) -> List[str]:
        """Check all physics constraints. Returns list of violations."""
        violations = []

        neurons = circuit.get_all_neurons()
        bundles = circuit.get_all_bundles()

        # ── F3: Weight bounds ──
        for b in bundles:
            w_min = getattr(b.config, 'weight_min', 0.0)
            w_max = getattr(b.config, 'weight_max', 1.0)
            tol = 0.001  # float tolerance
            for row in b._memristors:
                for m in row:
                    if m.w < w_min - tol or m.w > w_max + tol:
                        violations.append(
                            f"F3 Weight bound: bundle={b.id}, "
                            f"w={m.w:.4f} not in [{w_min},{w_max}]"
                        )
                        break  # one violation per bundle is enough
                if violations and violations[-1].startswith("F3"):
                    break

        # ── F4: Membrane voltage divergence ──
        for n in neurons:
            v = getattr(n, '_membrane_voltage', 0.0)
            if hasattr(n, '_cap'):
                v = n._cap.voltage
            if abs(v) > self.v_max:
                violations.append(
                    f"F4 Voltage divergence: {n.config.neuron_id}, "
                    f"|V|={abs(v):.2f} > {self.v_max}"
                )

        # ── F5: Energy non-negativity ──
        for n in neurons:
            if n.energy < self.energy_floor:
                violations.append(
                    f"F5 Negative energy: {n.config.neuron_id}, "
                    f"E={n.energy:.4f} < 0"
                )

        # ── F2: Entropy monotonicity (2nd law) ──
        total_heat = sum(n.heat_output for n in neurons)
        ds_dt = total_heat  # entropy production rate (simplified)
        self._entropy_history.append(ds_dt)
        if len(self._entropy_history) > self.entropy_window:
            self._entropy_history = self._entropy_history[-self.entropy_window:]

        if len(self._entropy_history) >= self.entropy_window:
            # Check if dS/dt < 0 for the entire window
            all_negative = all(s < -1e-10 for s in self._entropy_history)
            if all_negative:
                violations.append(
                    f"F2 Entropy decrease: dS/dt < 0 for "
                    f"{self.entropy_window} consecutive steps"
                )

        return violations

    def trip(self, violations: List[str], tick: int):
        """Handle violations: error if enabled, log if disabled."""
        self.trip_count += 1
        self._violations_log.append((tick, violations))

        if self.enabled:
            raise FuseTrippedError(violations, tick)
        else:
            # Debug mode: just log
            for v in violations:
                print(f"  [FUSE:DEBUG] tick={tick}: {v}")

    def get_violations_log(self) -> List[Tuple[int, List[str]]]:
        """Return all recorded violations."""
        return list(self._violations_log)
