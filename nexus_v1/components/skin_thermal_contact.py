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

Joint scheduling order (per critique's own chain, plan §二十二 22.5):
    热源释放(release) → 世界传播(world diffusion, via graph.step()) →
    世界-皮肤交换(contact exchange, folded into the SAME graph.step() call
    via external_injections + a matching skin-side inject) → 皮肤状态更新
    (already applied as part of the above).
Stability check + locator query + contact-flux snapshot all happen BEFORE
the one side-effecting `source.release()` call, mirroring
`couple_and_step()`'s atomicity fix (plan §十八.3) — if any check fails,
neither source, world, nor skin state has been touched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

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
    """Joint scheduling: heat-source release -> world diffusion -> world-skin
    exchange, all in one atomic step with a three-way conservation ledger.

    Raises ValueError (state untouched) if the world graph configuration
    is unstable — same fail-fast contract as `guarded_step()`/
    `couple_and_step()` (plan §十八.3), extended to also guard the skin
    side by simply not being reached if the check fails.
    """
    if not is_stable(world_graph, dt, eta):
        max_dn = max(diffusion_number(world_graph, dt).values())
        raise ValueError(
            f"Unstable thermal diffusion configuration: "
            f"max diffusion_number={max_dn:.4g} > eta={eta}"
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
