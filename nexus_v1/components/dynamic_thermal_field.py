"""nexus_v1.components.dynamic_thermal_field — Process-based local thermal field (W1).

TYPE:HYBRID — physical diffusion process (Fourier's law, discretized) built
from the existing SEMI Capacitor primitive (energy-conservation bookkeeping
reused, not reinvented).

Context (plan §十四, W0~W5 world-model reconstruction):
  The existing `nexus_v1.components.world.World.temperature_at(pos)` /
  `nexus_v1.components.heat_source.CylindricalHeatSource.temperature_at(pos)`
  are INSTANT QUERY FUNCTIONS T=F(x) — no local state, no propagation time,
  no flux between positions ("InstantFieldWorld" paradigm, see W0 docstring
  notes added to those two files). This module is an ADDITIVE, OPT-IN
  alternative: a local process-based thermal field where temperature is a
  per-node STATE that exchanges heat with its neighbors over time, giving
  genuine physical grounding to environmental heat-flux direction relations
  (the eventual r_flux generator) that InstantFieldWorld structurally cannot
  support.

  W1 scope (current): standalone module. NOT connected to SkinPatch/Body/
  VariantCircuit. Only unit-test-level validation (numerical stability,
  energy conservation, gradient formation under external heat injection).
  Body-world exchange (W2), advective flux (W3), generator recalibration
  (W4), and relation-generator reconnection (W5) are explicitly out of
  scope for this file and will be added in later, separately-approved
  phases — see plan §十四.5 scope statement.

Physical mechanism — Q1/Q2/Q3 (RULES.md 强制三问):

  Q1 生物/物理对应物:
    BIO/REF: discretized heat conduction between adjacent water/sediment
    parcels near a hydrothermal vent (same physical setting as
    `heat_source.py`'s `CylindricalHeatSource`, REF: Kelley et al. 2002,
    Science 301). Real seawater thermal diffusivity α ≈ 1.4e-7 m²/s
    (standard physical constant for water at ambient ocean temperature)
    anchors the diffusion time scale.

  Q2 物理结构:
    Sources -> ThermalLink (Fourier-law flux) -> Targets, both ends are
    ThermalCell nodes, each wrapping an existing `Capacitor` (SEMI
    primitive, `semiconductor.py`) as its local energy reservoir —
    Q=CV, temperature is the "voltage" analog. No new state-holding
    primitive is invented; ThermalLink only computes a flux value and
    routes it through `Capacitor.inject()`, exactly like every other
    inter-node coupling in the project (compare `vascular.py` step(),
    `ecm.py` step() — both compute a flux/delta from two states and
    apply it via `Capacitor`-style accumulation, not raw attribute writes).

  Q3 参数依据:
    - `capacitance` (per ThermalCell): EXP-anchored placeholder pending W1
      unit-test calibration — see `DEFAULT_CAPACITANCE` derivation comment
      below. Not tuned "to make a test pass"; tuned against the real
      diffusivity anchor the same way `SKIN_DEPTH_M`'s τ was derived in
      `world.py` (τ = d²/(2α)).
    - `kappa` (per ThermalLink): finite-volume discretization of Fourier's
      law for two adjacent cells sharing an interface, κ_ij = κ_0 / d_ij
      (conductance falls off with the distance between cell centers, the
      standard FV-discretization form — REF: Patankar 1980, "Numerical
      Heat Transfer and Fluid Flow", ch.4, central-difference diffusion
      coefficient). κ_0 is anchored to the same real diffusivity constant.

  Independent RC constants (memory: project_omega_coupling_generator_complete
  — the Ω-layer lesson that a new aggregation layer reusing an old layer's
  RC constant goes silent under bursty upstream input): this module's
  capacitance/kappa are deliberately NOT reused from any existing thermal
  or ξ-layer constant; they are freshly derived here and will very likely
  need empirical recalibration once connected to a real dt/grid in W2+,
  exactly as T1's r≺ generator needed a 5-round calibration pass after its
  initial physically-derived starting point (see T1 report). W1's unit
  tests exist precisely to surface that need early, in isolation.

Dimensional mode (W1.5, added 2026-07-16 per critique-7 §一.1 — see plan
§十五): this module currently operates in **normalized mode**, not
**physical-anchor mode**. Concretely:
  - `capacitance` is a dimensionless numeric convention (default 1.0,
    matching the project-wide `Capacitor` default), not `C_th=ρ·c_p·V_i`
    (no per-node volume is tracked).
  - `kappa_ij = kappa_0 / d_ij` omits the interface-area factor a true
    finite-volume conductance would carry (`G_ij = k·A_ij/d_ij`); there is
    no per-edge `A_ij`.
  - `kappa_0` IS anchored to the real seawater diffusivity constant (see
    `_TAU_REF_STEPS` derivation below), so it is not an arbitrary number —
    but the anchoring is incomplete (area/volume terms missing), so the
    module as a whole cannot yet claim to be a physical-anchor model.
  `THERMAL_FIELD_MODE` below records this explicitly so future code/tests
  can check it rather than assume. A physical-anchor mode (explicit
  `A_ij`/`V_i`, real J/K/W units) is deferred until W2+ actually needs
  precise physical calibration (e.g. connecting to a real `HeatSource`
  power budget) — building it now would be premature given W1 has no
  consumer requiring that precision yet.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.skin_network import fibonacci_sphere_points

# W1.5 (critique-7 §一.1, plan §十五): explicit dimensional-mode declaration.
# "normalized" = capacitance/kappa are dimensionless numeric conventions
# (kappa_0 anchored to real diffusivity, but no area/volume factors).
# "physical-anchor" = full real units (A_ij, V_i, J, K, W) — not implemented
# in this file; deferred to whenever W2+ actually needs precise physical
# calibration. See module docstring "Dimensional mode" section.
THERMAL_FIELD_MODE: str = "normalized"

# ── Physical anchor constants ──────────────────────────────────────────
# REF: thermal diffusivity of seawater at ambient ocean temperature,
# standard physical constant, α = k/(ρ·c_p) ≈ 1.4e-7 m²/s.
SEAWATER_THERMAL_DIFFUSIVITY_M2_S: float = 1.4e-7

# Reuse the project's existing sim-unit <-> meter mapping (world.py) so
# this module's constants are commensurable with the rest of the thermal
# system rather than inventing a second, incompatible length scale.
from nexus_v1.components.world import BODY_SCALE_M  # noqa: E402

# EXP: W1 calibration placeholder. Derivation: pick a reference grid
# spacing d_ref = 1 sim_unit (= BODY_SCALE_M meters), compute the real
# diffusion time constant tau = d_ref_m^2 / (2*alpha) for that spacing,
# then set capacitance/kappa so that a two-node ThermalLink with that
# spacing reproduces tau in sim steps at dt=1.0. This mirrors exactly how
# `world.py`'s SKIN_DEPTH_M -> tau was derived (see world.py comment).
# NOT yet validated against a real dt convention — flagged in the W1 unit
# test as a first-pass value subject to recalibration (see module docstring).
_D_REF_M: float = BODY_SCALE_M  # 1 sim_unit reference spacing, in meters
_TAU_REF_S: float = (_D_REF_M ** 2) / (2.0 * SEAWATER_THERMAL_DIFFUSIVITY_M2_S)

# Real seconds -> sim steps: reuse the project's dt=0.001s (1ms) convention
# (CLAUDE.md: "dt=0.001 (1 ms) is the simulation timestep convention").
_DT_STEP_S: float = 0.001
_TAU_REF_STEPS: float = _TAU_REF_S / _DT_STEP_S

# Reference capacitance chosen as 1.0 (dimensionless energy-storage unit,
# matching the project convention of C=1.0 as the Capacitor default —
# see semiconductor.py). kappa_0 is then back-derived so that the
# two-node RC time constant tau=1/kappa_0 (for C_i=C_j=1) matches
# _TAU_REF_STEPS in simulation steps.
DEFAULT_CAPACITANCE: float = 1.0
DEFAULT_KAPPA_0: float = 1.0 / max(_TAU_REF_STEPS, 1e-6)

# Ambient dissipation: leakage of each cell to the surrounding (unmodeled,
# effectively infinite) ambient water body at baseline temperature. Chosen
# as a slow leak relative to inter-cell diffusion (10x longer time
# constant) so that the graph's internal gradient structure is visible
# before ambient dissipation erases it — same qualitative role as
# `r_leak` in other RC circuits in this project.
DEFAULT_R_LEAK_AMBIENT: float = 10.0 / max(DEFAULT_KAPPA_0, 1e-6)


@dataclass
class ThermalCell:
    """TYPE:HYBRID — local thermal reservoir node (one patch of medium).

    BIO: a small parcel of water/sediment near a hydrothermal vent, storing
    thermal energy above the ambient baseline. Q2: wraps a `Capacitor`
    (SEMI) as its energy store — Q=CV, V is the temperature-above-ambient
    analog. Does not duplicate Capacitor's charge-tracking logic.
    """
    node_id: int
    position: Tuple[float, float, float]
    ambient_temperature: float = 0.0
    capacitor: Capacitor = field(default_factory=lambda: Capacitor(capacitance=DEFAULT_CAPACITANCE))

    @property
    def temperature(self) -> float:
        """T_i = T_ambient + V_i (V_i = Q_i/C_i, from the wrapped Capacitor)."""
        return self.ambient_temperature + self.capacitor.voltage

    @property
    def kcl_imbalance(self) -> float:
        """Per-node conservation residual (delegates to Capacitor.kcl_imbalance)."""
        return self.capacitor.kcl_imbalance


@dataclass
class ThermalLink:
    """TYPE:SEMI — diffusive thermal coupling edge between two ThermalCell nodes.

    BIO/REF: discretized Fourier's law of heat conduction, finite-volume
    form J_ij = kappa_ij * (T_i - T_j) (REF: Patankar 1980, ch.4). Q2:
    Sources = the two ThermalCell endpoints' `.temperature`; the flux this
    computes is routed through each endpoint's `Capacitor.inject()` by
    `ThermalFieldGraph.step()` — this class itself holds no state and does
    not write to the cells directly (mirrors the Bundle-reads-Neuron
    read-only-then-external-apply pattern used throughout the project).
    """
    i: int
    j: int
    kappa: float = DEFAULT_KAPPA_0

    def flux(self, cells: Dict[int, "ThermalCell"]) -> float:
        """Positive value = heat currently flowing from node i to node j."""
        return self.kappa * (cells[self.i].temperature - cells[self.j].temperature)


class ThermalFieldGraph:
    """TYPE:HYBRID — a sparse graph of ThermalCell nodes coupled by ThermalLink edges.

    Q2: this is purely a container + scheduler; all physical state lives in
    the ThermalCell/Capacitor objects it holds. Update order follows the
    same discipline as the project's relation-layer 8-step scheduling
    protocol (plan §七 约束8): all flux values are computed from a single
    consistent pre-step snapshot BEFORE any node's charge is mutated, so
    edge-processing order never biases the result (a bug class T1/T3 both
    hit independently — see plan §七 约束8 history).
    """

    def __init__(
        self,
        cells: List[ThermalCell],
        links: List[ThermalLink],
        r_leak_ambient: Optional[float] = DEFAULT_R_LEAK_AMBIENT,
    ):
        self.cells: Dict[int, ThermalCell] = {c.node_id: c for c in cells}
        self.links: List[ThermalLink] = links
        self.r_leak_ambient = r_leak_ambient
        self._total_injected: float = 0.0
        self._total_leaked_ambient: float = 0.0
        self._initial_total_energy: float = self.total_energy()

    def total_energy(self) -> float:
        """Sum of all node energies (Σ Q_i, the conserved quantity)."""
        return sum(c.capacitor.charge for c in self.cells.values())

    def step(self, dt: float, external_injections: Optional[Dict[int, float]] = None) -> None:
        """Advance the graph by one step.

        external_injections: {node_id: current} — generic external heat
        source current (W1 keeps this fully synthetic/test-driven; wiring
        it to a real `HeatSource`/`CylindricalHeatSource` is explicit W2+
        scope, not part of this file).
        """
        external_injections = external_injections or {}

        # Step 1: snapshot all link fluxes from the CURRENT (pre-update)
        # state — see class docstring on why this must not interleave with
        # node updates.
        fluxes = [(link, link.flux(self.cells)) for link in self.links]

        # Step 2: accumulate net delta-energy per node. What leaves node i
        # is exactly what enters node j (same value, opposite sign) —
        # internal transfer is conservative by construction.
        deltas: Dict[int, float] = {nid: 0.0 for nid in self.cells}
        for link, j_ij in fluxes:
            d_e = j_ij * dt
            deltas[link.i] -= d_e
            deltas[link.j] += d_e

        # Step 3: external injection (only place energy enters the system).
        for nid, current in external_injections.items():
            d_e = current * dt
            deltas[nid] += d_e
            self._total_injected += d_e

        # Step 4: apply all deltas in one pass, via the wrapped Capacitor's
        # own inject() (dt=1.0 since dt is already folded into the delta).
        for nid, d_e in deltas.items():
            self.cells[nid].capacitor.inject(d_e, dt=1.0)

        # Step 5: ambient dissipation (only place energy leaves the system).
        if self.r_leak_ambient is not None:
            for cell in self.cells.values():
                q_before = cell.capacitor.charge
                cell.capacitor.leak(self.r_leak_ambient, dt)
                self._total_leaked_ambient += (q_before - cell.capacitor.charge)

    def conservation_residual(self) -> float:
        """|ΔE_total - injected + leaked|. Should be ≈0 (floating-point only).

        This is the graph-level counterpart to Capacitor.kcl_imbalance,
        aggregated across the whole network — the "进入 Noether 账本" hook
        referenced in plan §十四.3 point 5. A future integration phase can
        surface this value to `nexus_v1.ledger` directly; W1 only needs it
        to exist and be independently verifiable.
        """
        delta_e = self.total_energy() - self._initial_total_energy
        return abs(delta_e - self._total_injected + self._total_leaked_ambient)


def diffusion_number(graph: "ThermalFieldGraph", dt: float) -> Dict[int, float]:
    """Per-node explicit-diffusion stability number: Δt·(Σ_j κ_ij)/C_i.

    W1.5 addition (critique-7 §二.4/§三.2, plan §十五 point 5): numerical
    stability (no NaN/divergence) does not imply the chosen parameters are
    physically sensible — a large diffusion number means one step moves
    more energy across a link than the sending node currently holds,
    which is the explicit-Euler analogue of violating a CFL condition.

    This is a READ-ONLY diagnostic. It does not change `step()` behavior
    and does not implement automatic substepping — per critique-7's own
    guidance ("不应靠调小测试输入掩盖，应给出明确诊断"), the responsibility
    to act on a large diffusion number belongs to the caller (choose a
    smaller dt, or fewer/weaker links), not to a silent internal fix.
    Automatic substepping is deferred as a separate, larger behavioral
    change if it turns out to be needed.
    """
    result: Dict[int, float] = {nid: 0.0 for nid in graph.cells}
    for link in graph.links:
        result[link.i] += link.kappa
        result[link.j] += link.kappa
    for nid, kappa_sum in result.items():
        capacitance = max(graph.cells[nid].capacitor.capacitance, 1e-9)
        result[nid] = dt * kappa_sum / capacitance
    return result


def is_stable(graph: "ThermalFieldGraph", dt: float, eta: float = 1.0) -> bool:
    """True iff every node's diffusion_number is <= eta (default eta=1.0).

    REF: explicit finite-difference diffusion stability bound, standard
    form Δt·Σκ/C <= η with η<=1 (critique-7 §二.4). This checks the bound;
    it does not enforce it.
    """
    return all(v <= eta for v in diffusion_number(graph, dt).values())


def build_fibonacci_shell_graph(
    n_nodes: int,
    radius: float,
    k_neighbors: int = 4,
    capacitance: float = DEFAULT_CAPACITANCE,
    kappa: float = DEFAULT_KAPPA_0,
    r_leak_ambient: Optional[float] = DEFAULT_R_LEAK_AMBIENT,
) -> ThermalFieldGraph:
    """Build a minimal-viable (~10^2 node) sparse thermal graph on a sphere shell.

    TEST FIXTURE ONLY (W1.5, critique-7 §二.2, plan §十五 point 4). Do NOT
    use this directly as the production world coordinate space in W2's
    body-world coupling — skin points are ALSO placed with this same
    `fibonacci_sphere_points` generator (see `variant_adapter.py`'s thermal
    quantum pathway init), so reusing it for world-node placement risks
    silently conflating "world space" with "body surface space" (e.g. a
    world node landing exactly on a skin sample point isn't meaningful,
    it's a coincidence of sharing one geometry generator). A production
    world topology (sparse 3D grid / fixed point cloud / adaptive node
    graph, fixed in world coordinates, independent of body-frame geometry)
    is W2 `ThermalFieldLocator` design scope — not implemented here.

    Reuses `fibonacci_sphere_points` (existing pure-geometry utility, already
    used for T0's skin-point sampling — see `skin_network.py` docstring: "no
    dependency on Neuron/SynapticBundle mother classes by design") for node
    placement, then connects each node to its `k_neighbors` nearest
    neighbors — the same "sparse graph, limited neighbors" discipline as
    plan §十四.3 point 2 (minimal-support applied to the world-model scale).
    """
    if n_nodes < 2:
        raise ValueError(f"build_fibonacci_shell_graph: n_nodes must be >= 2, got {n_nodes}")
    if k_neighbors < 1:
        raise ValueError(f"build_fibonacci_shell_graph: k_neighbors must be >= 1, got {k_neighbors}")

    points = fibonacci_sphere_points(n_nodes, radius)
    cells = [ThermalCell(node_id=idx, position=p, capacitor=Capacitor(capacitance=capacitance))
             for idx, p in enumerate(points)]

    def _dist(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
        return math.sqrt(sum((a[k] - b[k]) ** 2 for k in range(3)))

    seen_edges = set()
    links: List[ThermalLink] = []
    for i, pi in enumerate(points):
        dists = sorted(
            ((j, _dist(pi, pj)) for j, pj in enumerate(points) if j != i),
            key=lambda t: t[1],
        )[:k_neighbors]
        for j, d_ij in dists:
            edge_key = (min(i, j), max(i, j))
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            # kappa_ij = kappa_0 / d_ij — finite-volume discretization, see
            # module docstring Q3. d_ij guarded against 0 (coincident points).
            kappa_ij = kappa / max(d_ij, 1e-6)
            links.append(ThermalLink(i=i, j=j, kappa=kappa_ij))

    return ThermalFieldGraph(cells=cells, links=links, r_leak_ambient=r_leak_ambient)
