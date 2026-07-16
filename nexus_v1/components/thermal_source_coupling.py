"""nexus_v1.components.thermal_source_coupling — World-node locator + power-based
dynamic heat source coupling (W2A).

TYPE:HYBRID — combines a TYPE:MATH geometric locator with a TYPE:HYBRID
power-budget heat source, both driving the existing `ThermalFieldGraph`
(`dynamic_thermal_field.py`) through its already-public `step()` interface.

Context (plan §十六.3, world-model reconstruction W2A): the first sub-phase
of W2 (身体-世界热交换) — world positioning + a heat source with genuine
power semantics feeding the W1 diffusion graph conservatively. Deliberately
does NOT touch skin/body coupling (that is W2B, a separate, not-yet-approved
phase) and does NOT modify `dynamic_thermal_field.py`'s `ThermalFieldGraph`
or its `step()` method — this file is purely additive, composing with the
existing public API (`ThermalFieldGraph.cells`, `.step(dt, external_injections)`,
`diffusion_number()`, `is_stable()`).

Physical mechanism — Q1/Q2/Q3 (RULES.md 强制三问):

  Q1 生物/物理对应物:
    `ThermalFieldLocator`: a pure coordinate-to-nearby-node query, the same
    kind of "coordinate generator should not know about circuits" utility
    as `skin_network.fibonacci_sphere_points` and T0's nearest-neighbor
    site selection (`relations/site_selection.py`) — not a Bundle, a
    geometry/interpolation tool.
    `DynamicHeatSource`: BIO — hydrothermal vent power output, same
    physical setting as `heat_source.py`'s `CylindricalHeatSource`
    (REF: Kelley et al. 2002, Science 301), but with genuine POWER
    semantics (dQ/dt) instead of temperature semantics — critique-7/8
    both correctly pointed out that a temperature value cannot be
    directly reused as an injected power/current without a semantic
    mismatch (plan §十五 critique point 4, §十六.1).

  Q2 物理结构:
    Sources = `DynamicHeatSource.release(dt)` (a power value) + world
    position -> `ThermalFieldLocator.locate(x, graph)` (nonnegative
    weights summing to 1) -> Targets = per-node injection currents fed
    into `ThermalFieldGraph.step(dt, external_injections=...)`. No new
    state-holding coupling primitive is invented for the routing itself
    (`couple()` below is a pure function); the only new state is the
    heat source's own energy budget, which mirrors `HeatSource`'s
    existing energy-depletion pattern in `world.py` (finite reservoir,
    not an infinite tap).

  Q3 参数依据:
    `DynamicHeatSource` defaults are EXP-flagged test-scale placeholders
    (not claimed to be precisely physically calibrated — consistent with
    `THERMAL_FIELD_MODE="normalized"` in `dynamic_thermal_field.py`).
    `k` (locator neighbor count) defaults to 4, matching
    `build_fibonacci_shell_graph`'s own `k_neighbors` default, for
    consistency across the W1/W2A test fixtures.

Numerical-stability escalation (plan §十六.1, critique-8 §四): W1's
`is_stable()`/`diffusion_number()` are read-only diagnostics — that
boundary was correct for W1's fully-controlled test harness. W2A adds
`guarded_step()`, a fail-fast WRAPPER around `ThermalFieldGraph.step()`
that raises before calling `step()` if the configuration is unstable.
`ThermalFieldGraph.step()` itself is NOT modified — it keeps its
already-tested W1/W1.5 diagnostic-only behavior; `guarded_step()` is
purely additive and only used by W2A-and-later call sites. No automatic
substepping (per critique-7/8's own recommendation: substepping changes
world/body/ξ^occ time-scale relationships and should wait for W4's
cross-scale calibration).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from nexus_v1.components.dynamic_thermal_field import (
    ThermalFieldGraph,
    diffusion_number,
    is_stable,
)


def _distance(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return math.sqrt(sum((a[k] - b[k]) ** 2 for k in range(3)))


class ThermalFieldLocator:
    """TYPE:MATH — world-position -> nearby-graph-node weight query.

    Q2: pure geometric interpolation, read-only (never mutates `graph`).
    Reuses inverse-distance weighting (standard interpolation scheme,
    REF: Shepard 1968, "A two-dimensional interpolation function for
    irregularly-spaced data" — not an invented formula).
    """

    def __init__(self, k: int = 4):
        if k < 1:
            raise ValueError(f"ThermalFieldLocator: k must be >= 1, got {k}")
        self.k = k

    def locate(
        self, x: Tuple[float, float, float], graph: ThermalFieldGraph
    ) -> Dict[int, float]:
        """Return {node_id: weight}, weight>=0, sum(weight)==1.

        If x coincides exactly with a node's position, that node gets
        weight 1.0 (avoids division by zero in inverse-distance weighting).
        """
        node_ids = list(graph.cells.keys())
        if not node_ids:
            raise ValueError("ThermalFieldLocator.locate: graph has no nodes")

        dists = [(nid, _distance(x, graph.cells[nid].position)) for nid in node_ids]
        # Exact coincidence: return that single node with weight 1.
        for nid, d in dists:
            if d < 1e-9:
                return {nid: 1.0}

        dists.sort(key=lambda t: t[1])
        nearest = dists[: min(self.k, len(dists))]
        inv_dists = [(nid, 1.0 / d) for nid, d in nearest]
        total = sum(w for _, w in inv_dists)
        return {nid: w / total for nid, w in inv_dists}


@dataclass
class DynamicHeatSource:
    """TYPE:HYBRID — finite-energy heat source with genuine power (dQ/dt) output.

    BIO: hydrothermal vent, same setting as `heat_source.py`'s
    `CylindricalHeatSource` (REF: Kelley et al. 2002, Science 301), but
    modeling output as POWER, not temperature — a legacy `HeatSource`'s
    `effective_temperature()` cannot be reused directly as an injected
    current without conflating "how hot" with "how much energy per step"
    (plan §十五/§十六, critique points on temperature-vs-power mismatch).

    Q3: EXP-flagged test-scale defaults — `THERMAL_FIELD_MODE="normalized"`
    applies here too, not claiming precise physical calibration.
    """
    position: Tuple[float, float, float]
    energy_remaining: float
    power: float
    efficiency: float = 1.0

    def release(self, dt: float) -> float:
        """Return the actual power injected this step (<= self.power),
        respecting the finite energy budget: power*dt <= energy_remaining.
        Depletes energy_remaining accordingly. Returns 0.0 once exhausted.
        """
        if self.energy_remaining <= 0.0 or self.power <= 0.0 or dt <= 0.0:
            return 0.0
        requested_energy = self.power * dt
        actual_energy = min(requested_energy, self.energy_remaining)
        self.energy_remaining -= actual_energy
        actual_power = (actual_energy / dt) * self.efficiency
        return actual_power


def couple(
    source: DynamicHeatSource,
    locator: ThermalFieldLocator,
    graph: ThermalFieldGraph,
    dt: float,
) -> Dict[int, float]:
    """Sources(DynamicHeatSource.release) -> Targets(per-node injection currents).

    Q2: `locator.locate()` gives nonnegative weights summing to 1 (or an
    empty dict is never returned — locate() raises on an empty graph), so
    `sum(couple(...).values()) == power` by construction — no separate
    renormalization step is needed. Returns a dict directly usable as
    `ThermalFieldGraph.step(dt, external_injections=couple(...))`.

    NOT ATOMIC (critique-9 §一, plan §十八): this calls `source.release(dt)`
    first, which immediately debits `source.energy_remaining` — if the
    caller subsequently fails to deliver the returned injections to a
    graph (e.g. a separate `guarded_step()` call raises because the graph
    is unstable), that energy is lost across the source-graph boundary.
    This low-level function is kept for composability/testing (T-TSC-2~5
    test `release()`/`couple()` in isolation); production call sites
    should use `couple_and_step()` below, which orders the stability
    check and locator query BEFORE the only side-effecting call
    (`release()`), achieving atomicity without a transaction object.
    """
    power = source.release(dt)
    if power == 0.0:
        return {}
    weights = locator.locate(source.position, graph)
    return {node_id: power * w for node_id, w in weights.items()}


def guarded_step(
    graph: ThermalFieldGraph,
    dt: float,
    external_injections: Optional[Dict[int, float]] = None,
    eta: float = 1.0,
) -> None:
    """Fail-fast wrapper around `ThermalFieldGraph.step()` (W2A, critique-8 §四).

    Raises ValueError BEFORE calling `graph.step()` if the configuration
    is unstable (`is_stable(graph, dt, eta)` is False) — graph state is
    left completely unmodified when this raises. Does not implement
    automatic substepping (see module docstring).

    `ThermalFieldGraph.step()` itself remains diagnostic-only (unchanged
    from W1/W1.5) — this wrapper is purely additive, for W2A-and-later
    call sites where inputs are no longer fully test-controlled.
    """
    if not is_stable(graph, dt, eta):
        max_dn = max(diffusion_number(graph, dt).values())
        raise ValueError(
            f"Unstable thermal diffusion configuration: "
            f"max diffusion_number={max_dn:.4g} > eta={eta}"
        )
    graph.step(dt, external_injections)


def couple_and_step(
    source: DynamicHeatSource,
    locator: ThermalFieldLocator,
    graph: ThermalFieldGraph,
    dt: float,
    eta: float = 1.0,
) -> None:
    """Atomic source-to-graph injection (W2A fix, critique-9 §一/十八.3).

    Fixes a real gap `couple()` + `guarded_step()` had when called as two
    separate steps: `couple()` debits `source.energy_remaining` via
    `release()` BEFORE any confirmation that `graph.step()` will actually
    run, so a subsequent `guarded_step()` rejection loses that energy
    across the source-graph boundary (verified: `release()` unconditionally
    does `self.energy_remaining -= actual_energy` — see `DynamicHeatSource
    .release()`).

    Fix is a reordering, not a transaction object: `is_stable()` depends
    only on the graph's own kappa/capacitance (not on injection amount —
    see `diffusion_number(graph, dt)` signature), and `locator.locate()`
    is read-only and independent of power too. So both checks can run
    BEFORE `release()` (the only side-effecting call in this whole
    pipeline), making `release()` the single commit point: if either
    check fails, neither `source` nor `graph` has been touched.
    """
    if not is_stable(graph, dt, eta):
        max_dn = max(diffusion_number(graph, dt).values())
        raise ValueError(
            f"Unstable thermal diffusion configuration: "
            f"max diffusion_number={max_dn:.4g} > eta={eta}"
        )
    weights = locator.locate(source.position, graph)
    power = source.release(dt)
    if power == 0.0:
        return
    injections = {node_id: power * w for node_id, w in weights.items()}
    graph.step(dt, injections)
