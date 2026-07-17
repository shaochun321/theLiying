"""nexus_v1.components.skin_thermal_contact — World-skin thermal boundary (P0).

TYPE:HYBRID — combines a local skin energy reservoir (`SkinThermalState`)
with a convective-exchange boundary (`ThermalContact`) between one
`ThermalFieldGraph` node and the skin, plus a joint scheduling function
tying heat-source release, world diffusion, and world-skin exchange into
one atomic, three-way-accounted step.

Context (plan §二十二, P0 — world-body boundary + joint conservation
closure): the fourteenth cross-comparison critique
(`交叉比对/document - 2026-07-17T113002.137.md`) confirmed the world model
has a working "local thermal process core" (`dynamic_thermal_field.py` +
L2 read-only relation accessors) but the body is not yet actually IN that
process — skin sensing still reads the old InstantFieldWorld. This module
is the minimal boundary closing that gap: **P0 scope only** — single
contact edge, 3~5 `ThermalCell` world nodes, one dynamic heat source, no
ξ^occ, no Neuron/Bundle, no L3, no mouth/self coordinates (see plan §二十二
22.6 scope statement). Does NOT modify `dynamic_thermal_field.py` or
`thermal_source_coupling.py` — purely additive, composing with their
already-public APIs (`ThermalFieldGraph.step()`, `DynamicHeatSource.
release()`, `ThermalFieldLocator.locate()`, `is_stable()`/
`diffusion_number()`), same discipline as W2A's `thermal_source_coupling.py`.

Physical mechanism — Q1/Q2/Q3 (RULES.md 强制三问):

  Q1 生物/物理对应物:
    `SkinThermalState`: a local patch of skin tissue storing thermal
    energy above ambient, structurally identical to `ThermalCell`'s role
    for a world node (real skin has measurable thermal capacitance —
    REF: standard physiological heat-transfer modeling treats skin as a
    lumped thermal mass exchanging with environment by convection).
    `ThermalContact`: world-skin convective heat exchange, REF: Newton's
    law of cooling, `J = h*A*(T_world - T_skin)` — h (convective heat
    transfer coefficient) and A (contact area) are the two standard
    parameters of this textbook relation (not an invented formula).

  Q2 物理结构:
    Sources = one `ThermalFieldGraph` contact node's `.temperature` (world
    side) + `SkinThermalState.temperature` (skin side) -> `ThermalContact`
    (read-only flux computation, mirrors `ThermalLink.flux()`'s
    "compute-only, caller applies" pattern — this class holds no state
    and does not write to either endpoint) -> Targets = symmetric
    `Capacitor.inject()` calls on the world node (via the SAME
    `external_injections` dict already passed to `ThermalFieldGraph.
    step()`, so world-diffusion and world-skin exchange are applied in
    ONE atomic step — same "multiple inputs summed before one step()"
    discipline as plan §七 约束8) and on `SkinThermalState.capacitor`
    (a standalone object, not managed by `ThermalFieldGraph`).

  Q3 参数依据:
    `h`/`A`/skin `capacitance` are EXP-flagged first-pass test-scale
    values (same `THERMAL_FIELD_MODE="normalized"` regime as
    `dynamic_thermal_field.py` — not claimed to be precisely physically
    calibrated). Chosen so the contact flux is comparable in magnitude to
    inter-cell diffusion flux under the same `kappa`, avoiding a new
    RC-timescale mismatch of the kind flagged in
    `memory: project_omega_coupling_generator_complete`.

Joint scheduling order (P1-0 correction, plan §二十三 23.1 point①, 批判十五 §一):
    the actual semantics are NOT a sequential process ("release, THEN world
    propagates, THEN exchanges with skin") — they are "snapshot all t_n
    state, compute everything, commit once":
      1. snapshot all state at t_n (world temperatures, skin temperature);
      2. compute all source/diffusion/contact terms from that ONE snapshot
         (`contact.flux()` reads pre-step world/skin temperatures, never
         post-step ones);
      3. verify stability (world diffusion AND contact channel, see below)
         and available energy;
      4. commit once to t_{n+1} (`source.release()` then a single
         `world_graph.step()` call carrying BOTH the source injection and
         the contact exchange in the same `external_injections` dict, plus
         a matching skin-side inject);
      5. update the joint ledger.
    (The previous docstring described this as "release -> world diffusion
    -> world-skin exchange", which reads as a sequential process using the
    NEW world state for the exchange — that was never what the code did,
    and the wording is corrected here to avoid ambiguity once P1 adds more
    flux types that also need "which state, old or new" answered clearly.)

Stability guard (P1-0 fix, plan §二十三 23.1 point②, 批判十五 §二 — a REAL,
verified gap, not just a wording issue): the pre-existing `is_stable()`
only checks WORLD DIFFUSION stability (Δt·Σκ/C_i). It never covered the
contact channel's own stability number. Verified by direct construction:
a graph with tiny `kappa` (world diffusion trivially stable) plus a large
`h`/tiny skin capacitance contact edge diverges to ~1e25 within 5 steps
while `is_stable(world)` reports `True` throughout. The contact channel's
explicit-Euler update gives `ΔT^{n+1} = [1 - χ_contact]·ΔT^n` where
`χ_contact = H·dt·(1/C_w + 1/C_s)`, `H = h*A` — same CFL-style bound family
as `diffusion_number()`, requiring `χ_contact <= eta` for non-oscillating
convergence. `couple_world_skin_step()` below now checks a JOINT per-node
stability budget at the contact world-node (`η_w` folds the contact's `H`
into that node's existing diffusion-kappa sum — a node draining through
BOTH diffusion AND contact in the same step must not overdraw either
channel's individually-"safe" budget) alongside a skin-side check
(`η_s = dt·H/C_s`). See `contact_stability_numbers()`/`is_contact_stable()`.

Dimensional contract (P1-0 formalization, plan §二十三 23.1 point④, 批判
十五 §三 — the dt² bug found and fixed during P0 must not be allowed to
recur once P1 adds advection flux): **every value passed via
`external_injections` to `ThermalFieldGraph.step()` is a POWER/CURRENT
(energy per unit time), NEVER a pre-multiplied-by-dt energy.**
`ThermalFieldGraph.step()` itself performs the `* dt` exactly once,
internally. Naming convention going forward in this module (and any
future P1 flux module): `*_flux`/`*_current`/`power` = current-like
(NOT yet multiplied by dt); `delta_e_*`/`e_*_drawn`/`e_loss_*` = already
energy (already multiplied by dt) — the same variable must never switch
meaning mid-function. `ThermalContact.flux()` returns a current
(`j_ws`, matching `ThermalLink.flux()`'s existing convention); it is
passed as-is into `injections`, never pre-scaled by `dt`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.dynamic_thermal_field import (
    ThermalFieldGraph,
    diffusion_number,
    is_stable,
)
from nexus_v1.components.thermal_source_coupling import (
    DynamicHeatSource,
    ThermalFieldLocator,
)

# EXP: P0 first-pass placeholder, see module docstring Q3.
DEFAULT_SKIN_CAPACITANCE: float = 1.0


@dataclass
class SkinThermalState:
    """TYPE:HYBRID — local skin thermal reservoir (one contact patch).

    Structurally identical role to `ThermalCell` on the world side — wraps
    a `Capacitor` (SEMI) as its energy store, does not duplicate charge
    tracking logic. See module docstring Q1/Q2.
    """
    patch_id: int
    ambient_temperature: float = 0.0
    capacitor: Capacitor = field(
        default_factory=lambda: Capacitor(capacitance=DEFAULT_SKIN_CAPACITANCE))
    r_leak_ambient: Optional[float] = None  # None = no leak (P0 minimal default)

    @property
    def temperature(self) -> float:
        return self.ambient_temperature + self.capacitor.voltage


@dataclass
class ThermalContact:
    """TYPE:SEMI — single convective world-skin coupling edge.

    BIO/REF: Newton's law of cooling, J = h*A*(T_world - T_skin). Holds no
    state; `flux()` only reads the two endpoints' temperatures (mirrors
    `ThermalLink.flux()`'s read-only, caller-applies pattern). Setting
    `area=0.0` models a disconnected contact (zero exchange) without
    special-casing — same "structural parameter reaching zero" idiom used
    elsewhere in the project rather than a boolean "connected" flag.
    """
    world_node_id: int
    skin_patch_id: int
    h: float
    area: float

    def flux(self, world_graph: ThermalFieldGraph, skin: SkinThermalState) -> float:
        """Positive value = heat currently flowing from world node to skin."""
        t_world = world_graph.cells[self.world_node_id].temperature
        return self.h * self.area * (t_world - skin.temperature)


def contact_stability_numbers(
    contact: "ThermalContact",
    world_graph: ThermalFieldGraph,
    skin: SkinThermalState,
    dt: float,
) -> Tuple[float, float]:
    """P1-0 fix (plan §二十三 23.1 point②): per-node stability numbers that
    JOINTLY account for the contact world-node's existing diffusion budget
    PLUS the new contact channel — not two separately-checked numbers that
    happen to individually look safe (a node draining through both
    diffusion and contact in one step must not overdraw the combined
    budget, even if each channel alone would).

    Returns (eta_w, eta_s):
        eta_w = dt * (Σ_j kappa_wj + H) / C_w   (world contact-node side)
        eta_s = dt * H / C_s                     (skin side)
    where H = h*area. READ-ONLY diagnostic, same style/contract as
    `diffusion_number()` — does not mutate state.
    """
    world_node = world_graph.cells[contact.world_node_id]
    c_w = max(world_node.capacitor.capacitance, 1e-9)
    c_s = max(skin.capacitor.capacitance, 1e-9)
    h_total = contact.h * contact.area

    kappa_sum = 0.0
    for link in world_graph.links:
        if link.i == contact.world_node_id or link.j == contact.world_node_id:
            kappa_sum += link.kappa

    eta_w = dt * (kappa_sum + h_total) / c_w
    eta_s = dt * h_total / c_s
    return eta_w, eta_s


def is_contact_stable(
    contact: "ThermalContact",
    world_graph: ThermalFieldGraph,
    skin: SkinThermalState,
    dt: float,
    eta: float = 1.0,
) -> bool:
    """P1-0 fix: True iff both `contact_stability_numbers()` values are
    <= eta (default eta=1.0, same convention as `is_stable()`). Checks
    the bound; does not enforce it — same "diagnostic, not automatic
    substepping" contract as `is_stable()`/`diffusion_number()`.
    """
    eta_w, eta_s = contact_stability_numbers(contact, world_graph, skin, dt)
    return eta_w <= eta and eta_s <= eta


@dataclass
class JointStepLedger:
    """P0 三方账本（plan §二十二 22.5）: 一次 `couple_world_skin_step()` 调用
    的能量收支快照。`residual` 应≈0（浮点精度内），是本模块的完成判据
    `R_global`。
    """
    e_source_drawn: float
    delta_e_world: float
    delta_e_skin: float
    e_loss_world: float
    e_loss_skin: float
    residual: float


def couple_world_skin_step(
    source: DynamicHeatSource,
    locator: ThermalFieldLocator,
    world_graph: ThermalFieldGraph,
    contact: ThermalContact,
    skin: SkinThermalState,
    dt: float,
    eta: float = 1.0,
) -> JointStepLedger:
    """Joint scheduling: snapshot t_n state -> compute all source/diffusion/
    contact terms -> verify stability -> commit once to t_{n+1} -> update
    ledger (see module docstring "Joint scheduling order" for the P1-0
    wording correction — this is NOT a sequential release-then-propagate-
    then-exchange process).

    Raises ValueError (state untouched) if EITHER the world graph diffusion
    is unstable OR the contact channel itself is unstable (P1-0 fix, plan
    §二十三 23.1 point②) — same fail-fast contract as `guarded_step()`/
    `couple_and_step()` (plan §十八.3), both checks happen before the one
    side-effecting call (`source.release()`).
    """
    if not is_stable(world_graph, dt, eta):
        max_dn = max(diffusion_number(world_graph, dt).values())
        raise ValueError(
            f"Unstable thermal diffusion configuration: "
            f"max diffusion_number={max_dn:.4g} > eta={eta}"
        )
    if not is_contact_stable(contact, world_graph, skin, dt, eta):
        eta_w, eta_s = contact_stability_numbers(contact, world_graph, skin, dt)
        raise ValueError(
            f"Unstable world-skin contact configuration: "
            f"eta_w={eta_w:.4g} eta_s={eta_s:.4g} > eta={eta}"
        )

    # Pre-step snapshot (read-only) — locator weights + contact flux, BOTH
    # computed from state that has not yet been touched this step, per the
    # project's 8-step relation-layer scheduling protocol (plan §七 约束8).
    weights = locator.locate(source.position, world_graph)
    j_ws = contact.flux(world_graph, skin)  # positive = world -> skin

    e_world_before = world_graph.total_energy()
    e_skin_before = skin.capacitor.charge

    # Single commit point (mirrors couple_and_step()'s atomicity fix,
    # plan §十八.3): source.release() is the only side-effecting call
    # before this point; everything above was read-only.
    power = source.release(dt)

    # NOTE: `ThermalFieldGraph.step()` treats every value in
    # `external_injections` as a CURRENT and multiplies by `dt` internally
    # (mirrors `couple()`'s existing convention) — `j_ws` must be passed
    # as-is (a current), NOT pre-multiplied by dt, or the contact term
    # would be scaled by dt twice.
    injections: Dict[int, float] = {nid: power * w for nid, w in weights.items()}
    injections[contact.world_node_id] = injections.get(contact.world_node_id, 0.0) - j_ws

    total_leaked_before = world_graph._total_leaked_ambient
    world_graph.step(dt, injections)
    e_loss_world = world_graph._total_leaked_ambient - total_leaked_before

    e_loss_skin = 0.0
    if skin.r_leak_ambient is not None:
        q_before = skin.capacitor.charge
        skin.capacitor.inject(j_ws, dt)
        skin.capacitor.leak(skin.r_leak_ambient, dt)
        e_loss_skin = max(0.0, (q_before + j_ws * dt) - skin.capacitor.charge)
    else:
        skin.capacitor.inject(j_ws, dt)

    e_world_after = world_graph.total_energy()
    e_skin_after = skin.capacitor.charge

    delta_e_world = e_world_after - e_world_before
    delta_e_skin = e_skin_after - e_skin_before

    residual = abs(
        power * dt - delta_e_world - delta_e_skin - e_loss_world - e_loss_skin
    )

    return JointStepLedger(
        e_source_drawn=power * dt,
        delta_e_world=delta_e_world,
        delta_e_skin=delta_e_skin,
        e_loss_world=e_loss_world,
        e_loss_skin=e_loss_skin,
        residual=residual,
    )
