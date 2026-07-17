"""nexus_v1.components.joint_thermal_step_plan — Joint world+skin+source
thermal step: unified plan/commit contract (P1-C0).

TYPE:INFRA — a scheduling/audit layer composing already-tested physical
mechanisms, not a new physical mechanism itself (same classification as
`structural_address.py`/`thermal_transport_plan.py`).

Context (方案 P1-C0, 批判二十二, 2026-07-17): P1-B's `ThermalTransportPlan`
only covers ordered-excess-thermal-transfer edges. It does not guarantee
that transport is computed from the SAME instant as world diffusion+leak
(`ThermalFieldGraph.step()`), world-skin contact
(`skin_thermal_contact.couple_world_skin_step()`), or the dynamic heat
source's release (`thermal_source_coupling.DynamicHeatSource.release()`).
Calling these four mechanisms sequentially (`graph.step() -> transport.
apply() -> skin.step() -> source.release()`) would let later mechanisms
read state already mutated by earlier ones — the exact class of bug P0/
P1-0 already fixed once for source+diffusion+contact (see
`skin_thermal_contact.py`'s "Joint scheduling order" docstring section).

This module folds ALL FOUR channels into ONE snapshot -> compute -> joint-
validate -> single-commit cycle, reusing `ThermalFieldGraph.step()`'s own
internal diffusion+leak handling as an already-tested black box (this
module does NOT reimplement diffusion math — it only computes the combined
`external_injections` dict that `step()` already accepts, extending the
pattern `couple_world_skin_step()` established for source+contact to also
include ordered-transport edges as world-to-world injections).

批判二十二 also verified three real structural gaps in P1-B3's
`apply_thermal_transport_plan()` (state-staleness detection only compares
`charge`, not the full Capacitor triple; `AppliedPlanRegistry` lifecycle
not bound to a physical graph — a fresh empty registry bypasses the
double-submit check; a plan is not bound to the specific runtime instance
that generated it — an isomorphic mirror graph can accept a foreign plan).
All three are dormant today (no production call site mutates state between
`prepare()`/`apply()`, no long-lived joint scheduler exists yet) but
become live risks once P1-C0 introduces exactly such a long-lived runtime.
This module closes all three BY CONSTRUCTION rather than patching
`ThermalTransportPlan` itself:
  - full-triple state fingerprints (charge/_q_in/_q_out) for every
    participating world node AND skin patch, not just charge;
  - `JointThermalRuntime` persistently owns its `AppliedJointPlanRegistry`
    — callers cannot pass a fresh one per call the way a bare function
    argument would allow;
  - `runtime_uid` derived from `id(world_graph)` (the actual living object
    identity, not its content) is recorded on every plan and checked at
    apply time — an isomorphic mirror graph with identical addresses/
    revision/charges has a DIFFERENT `id()` and is rejected.

Physical mechanism — Q1/Q2/Q3 (RULES.md 强制三问):

  Q1 生物/物理对应物:
    No new BIO object — this composes four already-justified mechanisms
    (`ThermalFieldGraph`'s hydrothermal-vent diffusion, `ThermalContact`'s
    Newton's-law convection, `OrderedExcessThermalEnergyLink`'s driven
    transfer, `DynamicHeatSource`'s vent power output) into one atomic
    scheduling unit. TYPE:INFRA, same as `structural_address.py`.

  Q2 物理结构:
    Sources = `ThermalFieldGraph` (world diffusion+leak, unmodified) +
    `ThermalContact`/`SkinThermalState` (world-skin convection, unmodified)
    + `OrderedExcessThermalEnergyLink` (ordered transport, unmodified) +
    `DynamicHeatSource`/`ThermalFieldLocator` (source release, unmodified)
    -> `prepare_joint_thermal_step()` (pure function: reads all four,
    combines source+contact+transport into ONE `external_injections` dict
    for the world graph, computes skin-side injections, computes the joint
    stability report; peeks `DynamicHeatSource.release()`'s exact output
    via the same formula WITHOUT calling it, so `energy_remaining` is not
    mutated until `apply()`) -> Targets = immutable `JointThermalStepPlan`.
    `apply_joint_thermal_step()` performs the ONLY mutating calls: one
    `world_graph.step(dt, world_injections)` (world diffusion+leak+source+
    contact+transport, atomically, via the already-tested `step()`), skin
    `Capacitor.inject()`/`leak()` calls, and a direct debit of
    `source.energy_remaining` by the frozen `source_actual_energy` (never
    re-derived — same "apply doesn't recompute physics" discipline as
    P1-B3).

  Q3 参数依据:
    No new physical parameters — reuses every already-calibrated constant
    (`ThermalLink.kappa`, `ThermalContact.h`/`area`,
    `OrderedExcessThermalEnergyLink.rate_per_time`,
    `DynamicHeatSource.power`/`efficiency`). The joint stability formula
    `η_i^joint = Δt·[(Σκ_ij + ΣH_is + G_i^env)/C_i + Σ_{tail=i} a_e] ≤ 1`
    is V3's already-frozen P1-B0 definition (批判十九②订正量纲), applied
    here for the first time to a REAL multi-channel node instead of being
    checked as separate per-channel numbers.

Integration note — address/node-id correlation: `ThermalFieldGraph.cells`
is keyed by integer `node_id`; `structural_address.py`'s `AddressRegistry`
tracks physical identity by `StructuralAddress.uid` (string). P1-B's own
tests never combined the two (they operated on a bare `Dict[str,
ThermalCell]`, never a `ThermalFieldGraph`). This module requires every
world node referenced by a transport edge to have been registered via
`registry.register_physical(DOMAIN_WORLD_CELL, node_id)` beforehand (the
convention every P1-A/B test already follows) and uses
`registry.resolve(uid)` to recover the `node_id` — nodes with NO transport
edges do not need to be registered (diffusion/leak/contact do not consult
the registry at all).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.dynamic_thermal_field import ThermalFieldGraph
from nexus_v1.components.skin_thermal_contact import SkinThermalState, ThermalContact
from nexus_v1.components.thermal_source_coupling import (
    DynamicHeatSource, ThermalFieldLocator,
)
from nexus_v1.components.structural_address import (
    AddressRegistry, OrderedEdgeIdentity, DOMAIN_WORLD_CELL,
    MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER,
)
from nexus_v1.components.ordered_excess_thermal_energy_link import (
    OrderedExcessThermalEnergyLink,
)


class JointThermalStepError(ValueError):
    """P1-C0 联合计划生成/提交失败。所有失败路径（prepare 全程只读；apply
    的校验阶段在唯一写入区之前）都不修改任何传入对象。
    """


CapacitorTriple = Tuple[float, float, float]  # (charge, _q_in, _q_out)


def _capacitor_triple(cap: Capacitor) -> CapacitorTriple:
    return (cap.charge, cap._q_in, cap._q_out)


def _restore_capacitor_triple(cap: Capacitor, snapshot: CapacitorTriple) -> None:
    cap.charge, cap._q_in, cap._q_out = snapshot


def _graph_diagnostic_snapshot(graph: ThermalFieldGraph) -> dict:
    """批判二十三②: `ThermalFieldGraph.step()` 除了节点 Capacitor 状态外，
    还会更新图级的本步诊断快照（`_last_injection`/`_last_leak`/
    `_last_divergence_dt`/`_last_charge_before`/`_last_dt`，`closure_residual()`
    依赖它们）与累计账本（`_total_injected`/`_total_leaked_ambient`，
    `conservation_residual()`依赖它们）。世界侧`step()`成功、皮肤侧随后失败
    时，若只回滚Capacitor三元组，这些图级字段仍停留在"已发生"状态——回滚后
    `closure_residual()`/`conservation_residual()`会读到与实际物理状态不符
    的幽灵记录。必须与Capacitor三元组同一次备份/恢复。
    """
    return {
        "_last_injection": dict(graph._last_injection),
        "_last_leak": dict(graph._last_leak),
        "_last_divergence_dt": dict(graph._last_divergence_dt),
        "_last_charge_before": dict(graph._last_charge_before),
        "_last_dt": graph._last_dt,
        "_total_injected": graph._total_injected,
        "_total_leaked_ambient": graph._total_leaked_ambient,
    }


def _restore_graph_diagnostic_snapshot(graph: ThermalFieldGraph, snapshot: dict) -> None:
    graph._last_injection = snapshot["_last_injection"]
    graph._last_leak = snapshot["_last_leak"]
    graph._last_divergence_dt = snapshot["_last_divergence_dt"]
    graph._last_charge_before = snapshot["_last_charge_before"]
    graph._last_dt = snapshot["_last_dt"]
    graph._total_injected = snapshot["_total_injected"]
    graph._total_leaked_ambient = snapshot["_total_leaked_ambient"]


@dataclass(frozen=True)
class JointThermalStepPlan:
    """不可变联合计划——一次性从同一物理快照生成。`world_injections`/
    `skin_injections`/`source_actual_energy` 是已冻结的最终结果，
    `apply_joint_thermal_step()` 不重新计算，只做一致性校验后写入。
    """
    plan_id: str
    dt: float
    runtime_uid: str
    registry_revision: int
    world_state_snapshots: Dict[int, CapacitorTriple]   # ALL world node_ids in the graph
    skin_state_snapshots: Dict[int, CapacitorTriple]     # ALL skin patch_ids passed in
    source_energy_snapshot: float
    world_injections: Dict[int, float]     # combined current (NOT energy) for world_graph.step()
    skin_injections: Dict[int, float]      # patch_id -> current (world->skin positive convention)
    source_actual_energy: float            # frozen energy to debit at apply time (== power*dt)
    transport_edge_identities: Tuple[OrderedEdgeIdentity, ...]  # for apply-time staleness re-check
    stability_report: Dict[str, float]     # "world:<node_id>" / "skin:<patch_id>" -> eta_joint


class AppliedJointPlanRegistry:
    """P1-C0: 已提交联合计划ID记录。与`ThermalTransportPlan`的
    `AppliedPlanRegistry`同构，但本对象只应由`JointThermalRuntime`持有
    （不由调用者临时创建）——闭合批判二十二点2。
    """

    def __init__(self):
        self._applied: set = set()

    def is_applied(self, plan_id: str) -> bool:
        return plan_id in self._applied

    def mark_applied(self, plan_id: str) -> None:
        self._applied.add(plan_id)


class JointThermalRuntime:
    """P1-C0: 持久化联合调度运行时——长期持有`world_graph`/`registry`/
    `applied_plan_registry`/`runtime_uid`，不由单步调用者临时创建（闭合
    批判二十二点2/3）。`runtime_uid`取自`id(self)`（批判二十三修复：不是
    `id(world_graph)`）——绑定到具体的 runtime 实例本身，不是它包装的图。
    两个独立构造的`JointThermalRuntime`即使包装同一个`world_graph`，也会
    有不同的`runtime_uid`和各自独立的`applied_plan_registry`：若仍用
    `id(world_graph)`，两个runtime的`runtime_uid`会相同，一个plan可以在
    runtime_A提交后，把状态精确复原，再通过runtime_B（独立registry，从未
    见过这个plan_id）二次提交——已用代码实测复现验证（批判二十三①）。
    """

    def __init__(self, world_graph: ThermalFieldGraph, registry: AddressRegistry):
        self.world_graph = world_graph
        self.registry = registry
        self.applied_plan_registry = AppliedJointPlanRegistry()
        self.runtime_uid = f"joint-runtime:{id(self)}"


def prepare_joint_thermal_step(
    runtime: JointThermalRuntime,
    contacts: Sequence[ThermalContact],
    skins_by_patch_id: Dict[int, SkinThermalState],
    transport_links: Sequence[OrderedExcessThermalEnergyLink],
    source: DynamicHeatSource,
    locator: ThermalFieldLocator,
    dt: float,
    eta: float = 1.0,
) -> JointThermalStepPlan:
    """统一快照 X^n=(world, skin, source) -> 计算全部流量 -> 联合稳定性
    校验 -> 返回不可变计划。全程只读，不修改 `runtime`/`contacts`/
    `skins_by_patch_id`/`transport_links`/`source` 中的任何对象。
    """
    world_graph = runtime.world_graph
    registry = runtime.registry

    # 1. 传输边身份/机制/重复校验（同 prepare_thermal_transport_plan 步骤1-3）。
    seen_edge_uids = set()
    for link in transport_links:
        edge = link.identity
        if edge.uid in seen_edge_uids:
            raise JointThermalStepError(
                f"prepare_joint_thermal_step: duplicate transport edge {edge.uid!r}")
        seen_edge_uids.add(edge.uid)
        if not registry.is_current_ordered_edge(edge):
            raise JointThermalStepError(
                f"prepare_joint_thermal_step: transport edge {edge.uid!r} is stale")
        if not registry.is_current_address(edge.tail):
            raise JointThermalStepError(
                f"prepare_joint_thermal_step: tail address {edge.tail!r} is stale")
        if not registry.is_current_address(edge.head):
            raise JointThermalStepError(
                f"prepare_joint_thermal_step: head address {edge.head!r} is stale")
        if edge.mechanism != MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER:
            raise JointThermalStepError(
                f"prepare_joint_thermal_step: edge {edge.uid!r} has mechanism "
                f"{edge.mechanism!r}, expected {MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER!r}")
        if edge.tail.domain != DOMAIN_WORLD_CELL or edge.head.domain != DOMAIN_WORLD_CELL:
            raise JointThermalStepError(
                f"prepare_joint_thermal_step: edge {edge.uid!r} must connect two "
                f"{DOMAIN_WORLD_CELL!r} nodes (world-to-skin transport is not yet "
                f"a supported mechanism)")

    # 2. 解析传输边端点 uid -> world_graph node_id（约定：node_id 即
    #    register_physical(DOMAIN_WORLD_CELL, node_id) 的 local_key）。
    def _resolve_node_id(uid: str) -> int:
        try:
            node_id = registry.resolve(uid)
        except KeyError:
            raise JointThermalStepError(
                f"prepare_joint_thermal_step: address uid={uid!r} not registered")
        if node_id not in world_graph.cells:
            raise JointThermalStepError(
                f"prepare_joint_thermal_step: resolved node_id={node_id!r} (from "
                f"uid={uid!r}) is not in this runtime's world_graph")
        return node_id

    transport_endpoints: List[Tuple[OrderedExcessThermalEnergyLink, int, int]] = []
    for link in transport_links:
        tail_nid = _resolve_node_id(link.identity.tail.uid)
        head_nid = _resolve_node_id(link.identity.head.uid)
        transport_endpoints.append((link, tail_nid, head_nid))

    # 3. 传输边两端 ambient_temperature 一致性（同 OrderedExcessThermalEnergyLink
    #    已有的单边校验，这里对联合范围内全部传输边涉及的节点统一核实）。
    if transport_endpoints:
        touched_nids = set()
        for _, tail_nid, head_nid in transport_endpoints:
            touched_nids.add(tail_nid)
            touched_nids.add(head_nid)
        ambient_values = {world_graph.cells[nid].ambient_temperature for nid in touched_nids}
        if len(ambient_values) > 1:
            raise JointThermalStepError(
                f"prepare_joint_thermal_step: transport-touched world nodes do not "
                f"share a common ambient_temperature: {sorted(ambient_values)}")

    # 4. 一次性拍摄 ALL 世界节点 + ALL 传入的皮肤 + 热源 的完整状态（三元组，
    #    不只是 charge —— 闭合批判二十二点1）。ThermalFieldGraph.step() 会
    #    通过 leak() 触碰每一个节点，不只是本轮有接触/传输的节点，所以快照
    #    范围必须是图里的全部节点。
    world_state_snapshots: Dict[int, CapacitorTriple] = {
        nid: _capacitor_triple(cell.capacitor) for nid, cell in world_graph.cells.items()
    }
    skin_state_snapshots: Dict[int, CapacitorTriple] = {
        pid: _capacitor_triple(skin.capacitor) for pid, skin in skins_by_patch_id.items()
    }
    source_energy_snapshot = source.energy_remaining

    # 5. 只读计算：定位权重 + 热源拟释放功率（`preview_release()`只读预览，
    #    与`release()`共用同一份公式，不调用`release()`本身——批判二十三④）。
    weights = locator.locate(source.position, world_graph)
    source_actual_power, source_actual_energy = source.preview_release(dt)

    # 6. 只读计算：接触通量（复用 ThermalContact.flux()，从预步快照读取）。
    contact_flux_by_index: List[float] = []
    for contact in contacts:
        if contact.skin_patch_id not in skins_by_patch_id:
            raise JointThermalStepError(
                f"prepare_joint_thermal_step: contact references skin_patch_id="
                f"{contact.skin_patch_id!r} not present in skins_by_patch_id")
        skin = skins_by_patch_id[contact.skin_patch_id]
        contact_flux_by_index.append(contact.flux(world_graph, skin))

    # 7. 只读计算：传输边功率（复用 OrderedExcessThermalEnergyLink.power()，
    #    从预步快照读取 tail charge，power() 内部已做 max(.,0) 钳位）。
    transport_power_by_index: List[float] = []
    for link, tail_nid, _head_nid in transport_endpoints:
        tail_energy = world_state_snapshots[tail_nid][0]  # charge component
        transport_power_by_index.append(link.power(tail_energy))

    # 8. 组合世界侧注入（source + contact + transport，全部是 CURRENT，不是
    #    预乘 dt 的能量 —— ThermalFieldGraph.step() 内部统一乘一次 dt，
    #    同 skin_thermal_contact.py 已确立的量纲契约）。
    world_injections: Dict[int, float] = {}
    for nid, w in weights.items():
        world_injections[nid] = world_injections.get(nid, 0.0) + source_actual_power * w
    for contact, j_ws in zip(contacts, contact_flux_by_index):
        world_injections[contact.world_node_id] = (
            world_injections.get(contact.world_node_id, 0.0) - j_ws)
    for (link, tail_nid, head_nid), power in zip(transport_endpoints, transport_power_by_index):
        world_injections[tail_nid] = world_injections.get(tail_nid, 0.0) - power
        world_injections[head_nid] = world_injections.get(head_nid, 0.0) + power

    # 9. 组合皮肤侧注入（同一皮肤可能被多条接触边命中，求和）。
    skin_injections: Dict[int, float] = {}
    for contact, j_ws in zip(contacts, contact_flux_by_index):
        skin_injections[contact.skin_patch_id] = (
            skin_injections.get(contact.skin_patch_id, 0.0) + j_ws)

    # 10. 联合稳定性 η_i^joint（世界节点）/ η_s^joint（皮肤），V3已冻结公式：
    #     η_i^joint = Δt·[(Σκ_ij + ΣH_is + G_i^env)/C_i + Σ_{tail=i} a_e] <= eta
    kappa_sum: Dict[int, float] = {nid: 0.0 for nid in world_graph.cells}
    for link_ in world_graph.links:
        kappa_sum[link_.i] += link_.kappa
        kappa_sum[link_.j] += link_.kappa

    h_sum_world: Dict[int, float] = {nid: 0.0 for nid in world_graph.cells}
    h_sum_skin: Dict[int, float] = {pid: 0.0 for pid in skins_by_patch_id}
    for contact in contacts:
        h_total = contact.h * contact.area
        h_sum_world[contact.world_node_id] = h_sum_world.get(contact.world_node_id, 0.0) + h_total
        h_sum_skin[contact.skin_patch_id] = h_sum_skin.get(contact.skin_patch_id, 0.0) + h_total

    a_sum_world: Dict[int, float] = {nid: 0.0 for nid in world_graph.cells}
    for link, tail_nid, _head_nid in transport_endpoints:
        a_sum_world[tail_nid] = a_sum_world.get(tail_nid, 0.0) + link.rate_per_time

    g_env_world = (1.0 / world_graph.r_leak_ambient) if world_graph.r_leak_ambient else 0.0

    stability_report: Dict[str, float] = {}
    for nid, cell in world_graph.cells.items():
        c_i = max(cell.capacitor.capacitance, 1e-9)
        eta_i = dt * ((kappa_sum[nid] + h_sum_world.get(nid, 0.0) + g_env_world) / c_i
                      + a_sum_world.get(nid, 0.0))
        stability_report[f"world:{nid}"] = eta_i
        if eta_i > eta:
            raise JointThermalStepError(
                f"prepare_joint_thermal_step: joint instability at world node {nid}: "
                f"eta_joint={eta_i:.4g} > eta={eta}")

    for pid, skin in skins_by_patch_id.items():
        c_s = max(skin.capacitor.capacitance, 1e-9)
        g_env_skin = (1.0 / skin.r_leak_ambient) if skin.r_leak_ambient else 0.0
        eta_s = dt * (h_sum_skin.get(pid, 0.0) + g_env_skin) / c_s
        stability_report[f"skin:{pid}"] = eta_s
        if eta_s > eta:
            raise JointThermalStepError(
                f"prepare_joint_thermal_step: joint instability at skin patch {pid}: "
                f"eta_joint={eta_s:.4g} > eta={eta}")

    # 11. 返回不可变计划。
    plan_id = (f"joint-plan:{runtime.runtime_uid}:{registry.revision}:{dt}:"
               f"{len(transport_links)}:{len(contacts)}")
    return JointThermalStepPlan(
        plan_id=plan_id,
        dt=dt,
        runtime_uid=runtime.runtime_uid,
        registry_revision=registry.revision,
        world_state_snapshots=world_state_snapshots,
        skin_state_snapshots=skin_state_snapshots,
        source_energy_snapshot=source_energy_snapshot,
        world_injections=world_injections,
        skin_injections=skin_injections,
        source_actual_energy=source_actual_energy,
        transport_edge_identities=tuple(link.identity for link in transport_links),
        stability_report=stability_report,
    )


@dataclass(frozen=True)
class JointThermalStepReceipt:
    """成功提交的联合回执。"""
    plan_id: str
    dt: float
    delta_e_world: float
    delta_e_skin: float
    e_loss_world: float
    e_loss_skin: float
    e_source_drawn: float
    residual: float             # |e_source_drawn - delta_e_world - delta_e_skin - e_loss_world - e_loss_skin|
    registry_revision: int


def apply_joint_thermal_step(
    runtime: JointThermalRuntime,
    plan: JointThermalStepPlan,
    skins_by_patch_id: Dict[int, SkinThermalState],
    source: DynamicHeatSource,
) -> JointThermalStepReceipt:
    """提交已冻结的联合计划——不重新计算任何物理量，只做一致性校验后
    在唯一写入区应用冻结好的 `world_injections`/`skin_injections`/
    `source_actual_energy`。故障语义：提交前完整快照 + 异常时全部回滚
    （同 P1-B3 已验证模式，范围扩大到世界+皮肤+热源三方）。

    校验顺序（全部通过后才进入写入区）：
    1. 计划未被提交过；
    2. `plan.runtime_uid` 与本 `runtime` 一致（闭合批判二十二点3——绑定到
       生成计划的那个具体图对象，不是内容相同的镜像图）；
    3. `registry.revision` 未变化；
    4. 传输边身份/地址仍是当前版本；
    5. 全部世界节点 + 全部皮肤 的完整状态三元组与计划快照一致（闭合批判
       二十二点1——不只比较 charge）；
    6. 热源 `energy_remaining` 与快照一致。
    """
    world_graph = runtime.world_graph
    registry = runtime.registry

    if runtime.applied_plan_registry.is_applied(plan.plan_id):
        raise JointThermalStepError(
            f"apply_joint_thermal_step: plan {plan.plan_id!r} was already applied")

    if plan.runtime_uid != runtime.runtime_uid:
        raise JointThermalStepError(
            f"apply_joint_thermal_step: plan was generated by a different runtime "
            f"instance (plan runtime_uid={plan.runtime_uid!r}, "
            f"this runtime_uid={runtime.runtime_uid!r})")

    if registry.revision != plan.registry_revision:
        raise JointThermalStepError(
            f"apply_joint_thermal_step: registry has changed since plan was prepared "
            f"(plan revision={plan.registry_revision}, current={registry.revision})")

    for edge in plan.transport_edge_identities:
        if not registry.is_current_ordered_edge(edge):
            raise JointThermalStepError(
                f"apply_joint_thermal_step: transport edge {edge.uid!r} is stale")
        if not registry.is_current_address(edge.tail):
            raise JointThermalStepError(
                f"apply_joint_thermal_step: tail address {edge.tail!r} is stale")
        if not registry.is_current_address(edge.head):
            raise JointThermalStepError(
                f"apply_joint_thermal_step: head address {edge.head!r} is stale")

    for nid, snapshot in plan.world_state_snapshots.items():
        if nid not in world_graph.cells:
            raise JointThermalStepError(
                f"apply_joint_thermal_step: world node {nid!r} missing (plan applied "
                f"to a different graph?)")
        current = _capacitor_triple(world_graph.cells[nid].capacitor)
        if current != snapshot:
            raise JointThermalStepError(
                f"apply_joint_thermal_step: world node {nid!r} state changed since "
                f"plan was prepared (snapshot={snapshot}, current={current})")

    for pid, snapshot in plan.skin_state_snapshots.items():
        if pid not in skins_by_patch_id:
            raise JointThermalStepError(
                f"apply_joint_thermal_step: skin patch {pid!r} missing")
        current = _capacitor_triple(skins_by_patch_id[pid].capacitor)
        if current != snapshot:
            raise JointThermalStepError(
                f"apply_joint_thermal_step: skin patch {pid!r} state changed since "
                f"plan was prepared (snapshot={snapshot}, current={current})")

    if source.energy_remaining != plan.source_energy_snapshot:
        raise JointThermalStepError(
            f"apply_joint_thermal_step: source energy_remaining changed since plan "
            f"was prepared (snapshot={plan.source_energy_snapshot}, "
            f"current={source.energy_remaining})")

    # ── 唯一写入区：先备份世界+皮肤全部参与容器 + 热源能量 ──
    world_backup: Dict[int, CapacitorTriple] = {
        nid: _capacitor_triple(world_graph.cells[nid].capacitor)
        for nid in plan.world_state_snapshots
    }
    skin_backup: Dict[int, CapacitorTriple] = {
        pid: _capacitor_triple(skins_by_patch_id[pid].capacitor)
        for pid in plan.skin_state_snapshots
    }
    source_backup = source.energy_remaining
    graph_diag_backup = _graph_diagnostic_snapshot(world_graph)

    e_world_before = world_graph.total_energy()
    e_skin_before = sum(skins_by_patch_id[pid].capacitor.charge for pid in plan.skin_state_snapshots)
    total_leaked_before = world_graph._total_leaked_ambient

    try:
        world_graph.step(plan.dt, plan.world_injections)

        e_loss_skin = 0.0
        for pid, j_ws in plan.skin_injections.items():
            skin = skins_by_patch_id[pid]
            if skin.r_leak_ambient is not None:
                q_before = skin.capacitor.charge
                skin.capacitor.inject(j_ws, plan.dt)
                skin.capacitor.leak(skin.r_leak_ambient, plan.dt)
                e_loss_skin += max(0.0, (q_before + j_ws * plan.dt) - skin.capacitor.charge)
            else:
                skin.capacitor.inject(j_ws, plan.dt)

        source.energy_remaining -= plan.source_actual_energy
    except Exception:
        for nid, snapshot in world_backup.items():
            _restore_capacitor_triple(world_graph.cells[nid].capacitor, snapshot)
        for pid, snapshot in skin_backup.items():
            _restore_capacitor_triple(skins_by_patch_id[pid].capacitor, snapshot)
        source.energy_remaining = source_backup
        _restore_graph_diagnostic_snapshot(world_graph, graph_diag_backup)
        raise

    runtime.applied_plan_registry.mark_applied(plan.plan_id)

    e_world_after = world_graph.total_energy()
    e_skin_after = sum(skins_by_patch_id[pid].capacitor.charge for pid in plan.skin_state_snapshots)
    e_loss_world = world_graph._total_leaked_ambient - total_leaked_before

    delta_e_world = e_world_after - e_world_before
    delta_e_skin = e_skin_after - e_skin_before
    residual = abs(
        plan.source_actual_energy - delta_e_world - delta_e_skin - e_loss_world - e_loss_skin
    )

    return JointThermalStepReceipt(
        plan_id=plan.plan_id,
        dt=plan.dt,
        delta_e_world=delta_e_world,
        delta_e_skin=delta_e_skin,
        e_loss_world=e_loss_world,
        e_loss_skin=e_loss_skin,
        e_source_drawn=plan.source_actual_energy,
        residual=residual,
        registry_revision=registry.revision,
    )
