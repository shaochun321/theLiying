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

    P1-C1（批判二十四）新增字段：`node_source_injection`/
    `node_contact_injection`/`node_transport_net` 是折叠进`world_injections`
    之前的分项（源/接触/传输各自对每个世界节点的贡献，同样是current非energy）
    ——`world_injections[nid] == node_source_injection.get(nid,0)+
    node_contact_injection.get(nid,0)+node_transport_net.get(nid,0)`恒成立，
    供节点级账本核实"分别计算的物理通道之和"与"实际观测到的状态变化"是否
    闭合，而不只是重新读回同一个已经合并的数。`edge_contact_transfers`/
    `edge_transport_transfers`是逐边快照（(world_node_id,skin_patch_id,j_ws)/
    (tail_nid,head_nid,power)），供边级账本`R_e=ΔE_donor+ΔE_receiver`逐条
    验证，而不是只验证聚合后的总账本。
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
    node_source_injection: Dict[int, float]    # P1-C1: world node_id -> source contribution (current)
    node_contact_injection: Dict[int, float]   # P1-C1: world node_id -> Σ contact contribution (current)
    node_transport_net: Dict[int, float]       # P1-C1: world node_id -> net transport contribution (current)
    edge_contact_transfers: Tuple[Tuple[int, int, float], ...]     # (world_node_id, skin_patch_id, j_ws)
    edge_transport_transfers: Tuple[Tuple[int, int, float], ...]   # (tail_nid, head_nid, power)


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
        # P1-C2（批判二十五长程浸泡测试暴露的真实bug）：plan_id 此前只由
        # registry.revision/dt/边数量拼接，冻结拓扑下连续多步 prepare() 会
        # 生成完全相同的 plan_id，第二次 apply() 立即被"重复提交"检测拒绝
        # ——不是真的重复提交，是两次不同时刻的合法新步骤恰好产生了同一个
        # 字符串。用一个纯粹的单调序号消除歧义，不代表任何物理量，只保证
        # 每次 prepare() 调用的 plan_id 唯一。
        self._prepare_sequence: int = 0


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
    #    同 skin_thermal_contact.py 已确立的量纲契约）。P1-C1：分项各自记录
    #    （不只是合并后的world_injections），供节点级账本核实分解一致性。
    node_source_injection: Dict[int, float] = {}
    for nid, w in weights.items():
        node_source_injection[nid] = node_source_injection.get(nid, 0.0) + source_actual_power * w

    node_contact_injection: Dict[int, float] = {}
    edge_contact_transfers: List[Tuple[int, int, float]] = []
    for contact, j_ws in zip(contacts, contact_flux_by_index):
        node_contact_injection[contact.world_node_id] = (
            node_contact_injection.get(contact.world_node_id, 0.0) - j_ws)
        edge_contact_transfers.append((contact.world_node_id, contact.skin_patch_id, j_ws))

    node_transport_net: Dict[int, float] = {}
    edge_transport_transfers: List[Tuple[int, int, float]] = []
    for (link, tail_nid, head_nid), power in zip(transport_endpoints, transport_power_by_index):
        node_transport_net[tail_nid] = node_transport_net.get(tail_nid, 0.0) - power
        node_transport_net[head_nid] = node_transport_net.get(head_nid, 0.0) + power
        edge_transport_transfers.append((tail_nid, head_nid, power))

    world_injections: Dict[int, float] = {}
    for nid in set(node_source_injection) | set(node_contact_injection) | set(node_transport_net):
        world_injections[nid] = (node_source_injection.get(nid, 0.0)
                                  + node_contact_injection.get(nid, 0.0)
                                  + node_transport_net.get(nid, 0.0))

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

    # 11. 返回不可变计划。plan_id 纳入单调序号（P1-C2修复：仅
    #     registry.revision/dt/边数量拼接在冻结拓扑连续多步场景下会重复，
    #     见 JointThermalRuntime.__init__ 的 `_prepare_sequence` 注释）。
    sequence = runtime._prepare_sequence
    runtime._prepare_sequence += 1
    plan_id = (f"joint-plan:{runtime.runtime_uid}:{registry.revision}:{dt}:"
               f"{len(transport_links)}:{len(contacts)}:{sequence}")
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
        node_source_injection=node_source_injection,
        node_contact_injection=node_contact_injection,
        node_transport_net=node_transport_net,
        edge_contact_transfers=tuple(edge_contact_transfers),
        edge_transport_transfers=tuple(edge_transport_transfers),
    )


@dataclass(frozen=True)
class JointThermalStepReceipt:
    """成功提交的联合回执。P1-C1（批判二十四）新增
    `node_ledger_residuals`/`edge_ledger_residuals`：三级账本中的节点级/边级
    残差（全局残差即原有`residual`字段）——`node_ledger_residuals`用真实观测
    到的`ΔE_i`（从`world_graph`/skin的实际Capacitor状态变化读出，不是重新
    计算）与计划里冻结的分项（`node_source_injection`/`node_contact_injection`/
    `node_transport_net`，加上`world_graph`自己记录的真实扩散/泄漏）对照；
    `edge_ledger_residuals`逐条验证每条接触边/传输边自身两端能量变化互相
    抵消。
    """
    plan_id: str
    dt: float
    delta_e_world: float
    delta_e_skin: float
    e_loss_world: float
    e_loss_skin: float
    e_source_drawn: float
    residual: float             # |e_source_drawn - delta_e_world - delta_e_skin - e_loss_world - e_loss_skin|
    registry_revision: int
    node_ledger_residuals: Dict[str, float]   # "world:<nid>" / "skin:<pid>" -> R_i
    edge_ledger_residuals: Dict[str, float]   # "contact:<i>" / "transport:<i>" -> R_e (index into edge tuples)


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

        e_loss_skin_by_patch: Dict[int, float] = {}
        for pid, j_ws in plan.skin_injections.items():
            skin = skins_by_patch_id[pid]
            if skin.r_leak_ambient is not None:
                q_before = skin.capacitor.charge
                skin.capacitor.inject(j_ws, plan.dt)
                skin.capacitor.leak(skin.r_leak_ambient, plan.dt)
                e_loss_skin_by_patch[pid] = max(0.0, (q_before + j_ws * plan.dt) - skin.capacitor.charge)
            else:
                skin.capacitor.inject(j_ws, plan.dt)
                e_loss_skin_by_patch[pid] = 0.0

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
    e_loss_skin = sum(e_loss_skin_by_patch.values())

    delta_e_world = e_world_after - e_world_before
    delta_e_skin = e_skin_after - e_skin_before
    residual = abs(
        plan.source_actual_energy - delta_e_world - delta_e_skin - e_loss_world - e_loss_skin
    )

    # P1-C1（批判二十四）节点级账本：真实观测 ΔE_i 与"冻结分项之和"
    # （Q_i^source+Q_i^diff+Q_i^contact+Q_i^oet-Q_i^loss）对照。扩散/泄漏
    # 项来自 world_graph 自己刚更新的图级诊断（_last_divergence_dt/
    # _last_leak，真实执行结果，非重算），source/contact/transport 三项用
    # plan 里已冻结的分解值（不重新计算物理量）。
    node_ledger_residuals: Dict[str, float] = {}
    for nid, before_triple in plan.world_state_snapshots.items():
        delta_e_i = world_graph.cells[nid].capacitor.charge - before_triple[0]
        q_diff = -world_graph._last_divergence_dt.get(nid, 0.0)
        q_loss = world_graph._last_leak.get(nid, 0.0)
        q_source = plan.node_source_injection.get(nid, 0.0) * plan.dt
        q_contact = plan.node_contact_injection.get(nid, 0.0) * plan.dt
        q_oet = plan.node_transport_net.get(nid, 0.0) * plan.dt
        node_ledger_residuals[f"world:{nid}"] = abs(
            delta_e_i - (q_source + q_diff + q_contact + q_oet - q_loss))

    for pid, before_triple in plan.skin_state_snapshots.items():
        delta_e_pid = skins_by_patch_id[pid].capacitor.charge - before_triple[0]
        q_contact_skin = plan.skin_injections.get(pid, 0.0) * plan.dt
        q_loss_skin = e_loss_skin_by_patch.get(pid, 0.0)
        node_ledger_residuals[f"skin:{pid}"] = abs(delta_e_pid - (q_contact_skin - q_loss_skin))

    # P1-C1 边级账本：每条接触边/传输边自身两端能量变化应互相抵消
    # （R_e=ΔE_donor+ΔE_receiver，用 plan 里已冻结的逐边 j_ws/power 值，
    # 不依赖能否从聚合后的真实状态里反推出单条边的贡献——多边共享同一节点
    # 时无法从观测状态里拆分出"这部分是哪条边造成的"，边级账本验证的是
    # plan 自身的逐边对称性）。
    edge_ledger_residuals: Dict[str, float] = {}
    for i, (_world_nid, _skin_pid, j_ws) in enumerate(plan.edge_contact_transfers):
        edge_ledger_residuals[f"contact:{i}"] = abs((-j_ws * plan.dt) + (j_ws * plan.dt))
    for i, (_tail_nid, _head_nid, power) in enumerate(plan.edge_transport_transfers):
        edge_ledger_residuals[f"transport:{i}"] = abs((-power * plan.dt) + (power * plan.dt))

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
        node_ledger_residuals=node_ledger_residuals,
        edge_ledger_residuals=edge_ledger_residuals,
    )


# ══════════════════════════════════════════════════════════════════════
# P1-C2: 连续物理轨迹与谱系输出（批判二十五，2026-07-17）
# ══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class JointThermalTrajectoryStep:
    """P1-C2（批判二十五）：单步的连续物理轨迹记录——`Γ^phys` 的一个采样点
    `{X^n, Q_source^n, Q_diff^n, Q_contact^n, Q_oet^n, Q_loss^n}`。**只记录
    已经在 `JointThermalStepPlan`/`JointThermalStepReceipt` 里存在的分项
    数值**（`node_source_injection`/`node_contact_injection`/
    `node_transport_net`来自plan，扩散/泄漏来自`world_graph`自己刚更新的
    图级诊断），不新增计算、不添加事件分段标签、不添加"对象/方向/成功/
    失败"等语义——纯粹是"这一步各物理通道各贡献了多少"的原始记录，供未来
    对某个历史关系做保留/阻断对照时使用（结构/行为算子资格门，见V4）。

    P2-A0（批判二十八）新增`runtime_uid`/`plan_id`：轨迹现在承担P2-A的
    "发生元标定证据"用途（启动/峰值/burst/衰减/静息测量），`record_
    trajectory_step()`据此核对这两个字段确实对应一次真实提交，不是伪造
    组合——记录下来供事后审计复查，不只在写入时检查一次。
    """
    step_index: int
    dt: float
    runtime_uid: str                     # 本步来自哪个runtime实例
    plan_id: str                         # 本步对应哪个已提交的计划
    world_charges: Dict[int, float]      # X^n（世界侧），提交后的charge
    skin_charges: Dict[int, float]       # X^n（皮肤侧），提交后的charge
    q_source: Dict[int, float]           # 世界节点 -> 本步源注入能量（已乘dt）
    q_diff: Dict[int, float]             # 世界节点 -> 本步扩散净流入能量
    q_contact: Dict[int, float]          # 世界节点 -> 本步接触净注入能量
    q_oet: Dict[int, float]              # 世界节点 -> 本步传输净注入能量
    q_loss: Dict[int, float]             # 世界节点 -> 本步环境泄漏能量


class JointThermalTrajectory:
    """P1-C2：纯数据容器，长期累积`JointThermalTrajectoryStep`序列。不持有
    `world_graph`/`runtime`的引用，不做任何物理计算——只负责`append()`调用方
    已经算好的记录，同`AppliedJointPlanRegistry`一样是最小职责对象。

    P2-A0（批判二十八）：`append()`新增`step_index`严格递增校验——轨迹
    必须从0开始、逐步append，不允许跳步/乱序/重复，否则拒绝（同一批判
    指出"轨迹已经开始承担标定证据"，不能再只靠调用方自律）。
    """

    def __init__(self):
        self._steps: List[JointThermalTrajectoryStep] = []

    def append(self, step: JointThermalTrajectoryStep) -> None:
        expected_index = len(self._steps)
        if step.step_index != expected_index:
            raise JointThermalStepError(
                f"JointThermalTrajectory.append: step_index必须严格递增"
                f"（期望{expected_index}，实际{step.step_index}）——不允许"
                f"跳步/乱序/重复写入轨迹")
        self._steps.append(step)

    def __len__(self) -> int:
        return len(self._steps)

    def __getitem__(self, index: int) -> JointThermalTrajectoryStep:
        return self._steps[index]

    def steps(self) -> Tuple[JointThermalTrajectoryStep, ...]:
        return tuple(self._steps)


def record_trajectory_step(
    trajectory: JointThermalTrajectory,
    step_index: int,
    runtime: JointThermalRuntime,
    skins_by_patch_id: Dict[int, SkinThermalState],
    plan: JointThermalStepPlan,
    receipt: JointThermalStepReceipt,
) -> None:
    """P2-A0（批判二十八）：从一次**已核实真实提交**的
    `apply_joint_thermal_step()`结果组装一条轨迹记录并追加。此前
    （P1-C2）只接收`plan`+裸`world_graph`，纯粹依赖调用方自律保证两者
    对应同一步——现在轨迹要承担P2-A的发生元标定证据用途，改为要求传入
    `runtime`+`receipt`（提交回执，证明真的applied过，不是只prepare()
    没apply()）并三层核对：
    1. `receipt.plan_id == plan.plan_id`（回执与计划配对一致）；
    2. `runtime.applied_plan_registry.is_applied(plan.plan_id)`为真
       （这个计划确实已经提交到这个runtime，不是伪造的回执）；
    3. `JointThermalTrajectory.append()`自己核对`step_index`严格递增。
    任何一项不满足都拒绝记录，不静默接受。
    """
    if receipt.plan_id != plan.plan_id:
        raise JointThermalStepError(
            f"record_trajectory_step: receipt.plan_id({receipt.plan_id!r}) "
            f"与 plan.plan_id({plan.plan_id!r}) 不一致——回执与计划不是同一步")
    if not runtime.applied_plan_registry.is_applied(plan.plan_id):
        raise JointThermalStepError(
            f"record_trajectory_step: plan {plan.plan_id!r} 未在本runtime上"
            f"确认提交过（is_applied()为False）——不能记录未经确认提交的步骤")

    world_graph = runtime.world_graph
    world_charges = {nid: cell.capacitor.charge for nid, cell in world_graph.cells.items()}
    skin_charges = {pid: skin.capacitor.charge for pid, skin in skins_by_patch_id.items()}
    q_source = {nid: v * plan.dt for nid, v in plan.node_source_injection.items()}
    q_contact = {nid: v * plan.dt for nid, v in plan.node_contact_injection.items()}
    q_oet = {nid: v * plan.dt for nid, v in plan.node_transport_net.items()}
    q_diff = {nid: -world_graph._last_divergence_dt.get(nid, 0.0) for nid in world_graph.cells}
    q_loss = {nid: world_graph._last_leak.get(nid, 0.0) for nid in world_graph.cells}

    trajectory.append(JointThermalTrajectoryStep(
        step_index=step_index,
        dt=plan.dt,
        runtime_uid=runtime.runtime_uid,
        plan_id=plan.plan_id,
        world_charges=world_charges,
        skin_charges=skin_charges,
        q_source=q_source,
        q_diff=q_diff,
        q_contact=q_contact,
        q_oet=q_oet,
        q_loss=q_loss,
    ))
