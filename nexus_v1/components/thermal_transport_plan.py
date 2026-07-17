"""nexus_v1.components.thermal_transport_plan — Immutable multi-edge ordered
transport plan (P1-B2).

TYPE:INFRA — a read-only planning layer, not a physical mechanism itself
(analogous to `structural_address.py`'s TYPE:INFRA classification).

Context (方案第二十三节, P1-B2, 批判二十, 2026-07-17): 批判十九/二十指出
`step_ordered_transport()`（P1-B1.5）是"仅单边诊断接口"——多条
`OrderedExcessThermalEnergyLink` 共享同一 tail 节点时，逐边直接调用会绕过
"先全部快照再统一提交"的纪律（同一节点先被边A扣除后再算边B，边遍历顺序会
改变物理结果）。批判二十给出完整设计：**不可变** `ThermalTransportPlan`（一次
性从同一物理快照生成，不可变，不可重复应用）+ `prepare_thermal_transport_plan()`
（严格11步只读序列）。

**P1-B3（批判二十一，2026-07-17）**：`apply_thermal_transport_plan()` 已实现。
故障语义采用**快照回滚**（不是"证明提交区不抛异常"——那需要完整源码级副作用
审计，尚未完成，不应现在假设）。状态过期检测用**方案A**（计划保存所有参与
节点的 charge 快照，提交前比对，不一致拒绝）而非全局状态修订号（方案B需要
给所有物理组件维护一个全局计数器，触及"不改母本代码"边界；方案A只需要计划
自己多存一份已有可读数据，零侵入）。`apply()` 不重新计算任何物理量（`u_i^+`/
`a_e`/功率/单步能量/节点净变化全部已冻结在计划里），只做一致性检查+写入已
冻结的 delta。回滚不只恢复 `charge`，还恢复 `Capacitor` 的 KCL 相关字段
（`_q_in`/`_q_out`/`_q_initial`），否则回滚后账本自身会不一致。

Physical mechanism — Q1/Q2/Q3 (RULES.md 强制三问):

  Q1 生物/物理对应物:
    与 `structural_address.py` 同理，本模块无 BIO 对应物——它是计划/审计
    基础设施，不是物理机制。它服务的物理机制仍是 `OrderedExcessThermalEnergyLink`
    （P1-B1.5 已建立，本模块只是为"多条边共享同一物理快照"这个调度纪律提供
    正式载体）。

  Q2 物理结构:
    Sources = 多个 `OrderedExcessThermalEnergyLink` 边 + 对应的
    `ThermalCell`（只读快照，一次性拍摄全部 tail 的 `capacitor.charge`）
    -> `prepare_thermal_transport_plan()`（纯函数，不修改任何传入对象）
    -> Targets = 不可变 `ThermalTransportPlan`（本轮只生成，不应用；P1-B3
    的 `apply()` 才是真正写回 `ThermalCell` 状态的地方）。

  Q3 参数依据:
    无新物理参数——复用 P1-B1.5 已标定的 `rate_per_time`，本模块只做多边
    快照/汇总/校验的调度逻辑。**传输专属稳定性门**
    `η_i^transport=Δt·Σ_{e:tail(e)=i}a_e≤1`（批判二十⑥）是
    `η_i^joint`（P1-C 才处理，覆盖扩散+接触+泄漏+传输）在"只有传输边，B2
    尚不接扩散/接触/泄漏"这个范围下的正确子集，不是新公式，是 P1-C 公式的
    受限版本。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from nexus_v1.components.dynamic_thermal_field import ThermalCell
from nexus_v1.components.structural_address import (
    AddressRegistry, StructuralAddress, OrderedEdgeIdentity,
    MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER,
)
from nexus_v1.components.ordered_excess_thermal_energy_link import (
    OrderedExcessThermalEnergyLink,
)


@dataclass(frozen=True)
class EdgeTransfer:
    """单条边在本次计划中的快照+计算结果（批判二十给出的最小字段集）。"""
    edge_identity: OrderedEdgeIdentity
    tail_address: StructuralAddress
    head_address: StructuralAddress
    tail_energy_snapshot: float   # 快照时的原始 charge（未钳位）
    rate_per_time: float
    power: float                  # p_e = a_e * max(tail_energy_snapshot, 0)
    delta_energy: float           # q_e = power * dt


@dataclass(frozen=True)
class ThermalTransportPlan:
    """不可变多边传输计划——一次性从同一物理快照生成，`prepare()` 之后
    不再变化。`apply_thermal_transport_plan()`（P1-B3，未实现）才是真正
    写回节点状态的地方；本类本身只读、可安全传递/检查/丢弃。
    """
    plan_id: str
    dt: float
    thermal_reference: float           # 参与本计划的所有节点共享的 ambient_temperature
    registry_revision: int             # AddressRegistry.revision 的快照，供 apply() 判断 staleness
    edge_transfers: Tuple[EdgeTransfer, ...]
    node_outgoing_totals: Dict[str, float]   # tail uid -> Σ power（本计划范围内）
    node_net_deltas: Dict[str, float]        # uid -> 本计划导致的净能量变化（tail为负，head为正）
    stability_report: Dict[str, float]       # tail uid -> η_i^transport（诊断用，全部应 <=1，否则prepare已拒绝）
    participating_node_snapshots: Dict[str, float]  # P1-B3: 全部参与节点（tail+head）的charge快照，
                                                     # apply()提交前用于状态过期检测（方案A）


class ThermalTransportPlanError(ValueError):
    """P1-B2 计划生成失败——所有失败路径都不修改任何传入对象（`ThermalCell`/
    `AddressRegistry` 均保持 `prepare()` 调用前的状态，纯只读函数天然满足）。
    """


def prepare_thermal_transport_plan(
    links: Sequence[OrderedExcessThermalEnergyLink],
    cells_by_uid: Dict[str, ThermalCell],
    registry: AddressRegistry,
    dt: float,
    eta: float = 1.0,
) -> ThermalTransportPlan:
    """严格11步只读序列（批判二十§五.2）。任何一步失败都 raise
    `ThermalTransportPlanError`，不修改 `cells_by_uid`/`registry`
    ——本函数全程只读，天然满足"失败时状态不变"。

    Args:
        links: 参与本次计划的有序边列表（可能有多条边共享同一 tail）。
        cells_by_uid: `{StructuralAddress.uid: ThermalCell}`，调用方负责
            组装（本模块不关心 `ThermalCell` 存放在哪个容器/图里，只按
            uid 查表——同 `structural_address.py` 的"地址不是坐标"纪律）。
        registry: 用于校验地址/边身份仍是当前版本。
        dt: 时间步长。
        eta: 稳定性阈值（默认1.0，同项目既有 `is_stable()`/
            `is_contact_stable()` 约定）。
    """
    # 1. 验证所有边身份仍是当前版本（地址+边本身，批判二十"stale 检测"）。
    for link in links:
        edge = link.identity
        if not registry.is_current_ordered_edge(edge):
            raise ThermalTransportPlanError(
                f"prepare_thermal_transport_plan: edge {edge.uid!r} is not the "
                f"registry's current version — stale edge identity")
        if not registry.is_current_address(edge.tail):
            raise ThermalTransportPlanError(
                f"prepare_thermal_transport_plan: tail address {edge.tail!r} is stale")
        if not registry.is_current_address(edge.head):
            raise ThermalTransportPlanError(
                f"prepare_thermal_transport_plan: head address {edge.head!r} is stale")

    # 2. 验证所有边机制类型正确（本计划只处理有序过剩热能转移边）。
    for link in links:
        if link.identity.mechanism != MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER:
            raise ThermalTransportPlanError(
                f"prepare_thermal_transport_plan: edge {link.identity.uid!r} has "
                f"mechanism {link.identity.mechanism!r}, expected "
                f"{MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER!r}")

    # 3. 验证无重复边（同一 edge uid 在本次 links 列表里出现超过一次）。
    seen_edge_uids = set()
    for link in links:
        uid = link.identity.uid
        if uid in seen_edge_uids:
            raise ThermalTransportPlanError(
                f"prepare_thermal_transport_plan: duplicate edge {uid!r} in plan input "
                f"(would double-debit energy)")
        seen_edge_uids.add(uid)
    # （自环已在 OrderedEdgeIdentity.__post_init__ 层面禁止，此处无需重复校验。）

    if not links:
        raise ThermalTransportPlanError(
            "prepare_thermal_transport_plan: no edges provided")

    # 4. 验证所有参与节点共享同一 ambient_temperature（热参考基线）。
    participating_uids = set()
    for link in links:
        participating_uids.add(link.identity.tail.uid)
        participating_uids.add(link.identity.head.uid)
    for uid in participating_uids:
        if uid not in cells_by_uid:
            raise ThermalTransportPlanError(
                f"prepare_thermal_transport_plan: no ThermalCell provided for "
                f"address uid={uid!r}")
    ambient_values = {cells_by_uid[uid].ambient_temperature for uid in participating_uids}
    if len(ambient_values) > 1:
        raise ThermalTransportPlanError(
            f"prepare_thermal_transport_plan: participating nodes do not share a "
            f"common ambient_temperature reference baseline: {sorted(ambient_values)}")
    thermal_reference = next(iter(ambient_values))

    # 5. 一次性拍摄所有参与节点（tail+head）的 charge 快照（同一时刻，先于
    #    任何计算）。head 的快照本身不参与 u_tail^+/功率计算（那只依赖
    #    tail），但 P1-B3 的 apply() 用全部参与节点的快照做状态过期检测
    #    （批判二十一：Q_plan={(α_i,q_i^snapshot)} 覆盖"所有参与节点"）。
    participating_snapshots: Dict[str, float] = {
        uid: cells_by_uid[uid].capacitor.charge for uid in participating_uids
    }
    tail_snapshots: Dict[str, float] = {
        link.identity.tail.uid: participating_snapshots[link.identity.tail.uid]
        for link in links
    }

    # 6-7. 从快照计算每条边的 u_tail^+、功率、单步能量。
    edge_transfers: List[EdgeTransfer] = []
    for link in links:
        edge = link.identity
        tail_energy = tail_snapshots[edge.tail.uid]
        power = link.power(tail_energy)  # power() 内部已做 max(.,0) 钳位
        delta_energy = power * dt
        edge_transfers.append(EdgeTransfer(
            edge_identity=edge,
            tail_address=edge.tail,
            head_address=edge.head,
            tail_energy_snapshot=tail_energy,
            rate_per_time=link.rate_per_time,
            power=power,
            delta_energy=delta_energy,
        ))

    # 8. 按 tail 汇总全部出流率（Σa_e，供第9步稳定性校验）。
    outgoing_rate_by_tail: Dict[str, float] = {}
    for link in links:
        tail_uid = link.identity.tail.uid
        outgoing_rate_by_tail[tail_uid] = outgoing_rate_by_tail.get(tail_uid, 0.0) + link.rate_per_time

    # 9. 验证传输专属联合稳定性 η_i^transport = dt * Σa_e <= eta（批判二十⑥）。
    #    单条边分别稳定不代表组合稳定——这是 B2 自己的稳定性门，不是逐边检查。
    stability_report: Dict[str, float] = {}
    for tail_uid, total_rate in outgoing_rate_by_tail.items():
        eta_transport = dt * total_rate
        stability_report[tail_uid] = eta_transport
        if eta_transport > eta:
            raise ThermalTransportPlanError(
                f"prepare_thermal_transport_plan: combined transport instability at "
                f"tail={tail_uid!r}: eta_transport={eta_transport:.4g} > eta={eta} "
                f"(individual edges may each be stable, but their sum overdraws the "
                f"shared tail — 批判二十⑥)")

    # 10. 生成节点净变化 + 出流汇总账本预览。
    node_outgoing_totals: Dict[str, float] = {}
    node_net_deltas: Dict[str, float] = {}
    for et in edge_transfers:
        tail_uid, head_uid = et.tail_address.uid, et.head_address.uid
        node_outgoing_totals[tail_uid] = node_outgoing_totals.get(tail_uid, 0.0) + et.power
        node_net_deltas[tail_uid] = node_net_deltas.get(tail_uid, 0.0) - et.delta_energy
        node_net_deltas[head_uid] = node_net_deltas.get(head_uid, 0.0) + et.delta_energy

    # 11. 返回不可变计划。
    plan_id = f"plan:{registry.revision}:{dt}:{len(edge_transfers)}"
    return ThermalTransportPlan(
        plan_id=plan_id,
        dt=dt,
        thermal_reference=thermal_reference,
        registry_revision=registry.revision,
        edge_transfers=tuple(edge_transfers),
        node_outgoing_totals=node_outgoing_totals,
        node_net_deltas=node_net_deltas,
        stability_report=stability_report,
        participating_node_snapshots=participating_snapshots,
    )


# ══════════════════════════════════════════════════════════════════════
# P1-B3: 提交与故障语义（批判二十一，2026-07-17）
# ══════════════════════════════════════════════════════════════════════

class AppliedPlanRegistry:
    """P1-B3: 已提交计划ID记录，防止同一计划被提交两次（批判二十一§一.2，
    不需要建设大型事务管理器，一个最小提交登记表即可）。
    """

    def __init__(self):
        self._applied: set = set()

    def is_applied(self, plan_id: str) -> bool:
        return plan_id in self._applied

    def mark_applied(self, plan_id: str) -> None:
        self._applied.add(plan_id)


@dataclass(frozen=True)
class ThermalTransportReceipt:
    """成功提交的回执（批判二十一§一.5）。"""
    plan_id: str
    dt: float
    node_deltas_applied: Dict[str, float]   # uid -> 实际应用的净变化（应与plan.node_net_deltas一致）
    total_transport_residual: float         # |Σ实际净变化|，应≈0（账本闭合）
    registry_revision: int                  # 提交时的 registry.revision


def _snapshot_capacitor_state(cell: ThermalCell) -> Tuple[float, float, float]:
    """快照 Capacitor 的完整可变状态（不只是 charge，还有 KCL 记账字段）
    ——回滚时必须一并恢复，否则回滚后账本自身会不一致（批判二十一§一.4）。
    """
    cap = cell.capacitor
    return (cap.charge, cap._q_in, cap._q_out)


def _restore_capacitor_state(cell: ThermalCell, snapshot: Tuple[float, float, float]) -> None:
    cap = cell.capacitor
    cap.charge, cap._q_in, cap._q_out = snapshot


def apply_thermal_transport_plan(
    plan: ThermalTransportPlan,
    cells_by_uid: Dict[str, ThermalCell],
    registry: AddressRegistry,
    applied_plans: AppliedPlanRegistry,
) -> ThermalTransportReceipt:
    """提交已冻结的计划——只做一致性检查+写入已冻结的 delta，**不重新计算**
    任何物理量（批判二十一§一.3："计划审计的是一组值，实际提交的是另一组值"
    是必须避免的错误）。

    校验顺序（全部通过后才进入唯一的写入区）：
    1. 计划未被提交过（`applied_plans`）；
    2. `registry.revision` 未变化（拓扑/地址/边注册整体未变）；
    3. 计划涉及的每条边/每个端点地址仍是 registry 当前版本；
    4. 计划涉及的每个参与节点 charge 与快照时一致（方案A状态过期检测）。

    故障语义：**提交前快照+回滚**（批判二十一§一.4方案，非"证明不会异常"）。
    若写入过程中任何一步异常，恢复所有已修改节点的完整 Capacitor 状态
    （charge+KCL字段），并重新抛出原始异常——不吞异常、不部分提交。

    Raises:
        ThermalTransportPlanError: 任何一致性检查失败时，`cells_by_uid`/
            `registry`/`applied_plans` 均保持调用前状态。
    """
    # 1. 计划只能提交一次。
    if applied_plans.is_applied(plan.plan_id):
        raise ThermalTransportPlanError(
            f"apply_thermal_transport_plan: plan {plan.plan_id!r} was already applied "
            f"(double-apply would double-transfer energy)")

    # 2. registry 版本未变化（拓扑/地址/边整体层面的过期检测）。
    if registry.revision != plan.registry_revision:
        raise ThermalTransportPlanError(
            f"apply_thermal_transport_plan: registry has changed since plan was "
            f"prepared (plan revision={plan.registry_revision}, "
            f"current revision={registry.revision})")

    # 3. 每条边/每个端点地址仍是当前版本（同 prepare() 的校验，提交前再核实
    #    一次——防止 registry.revision 恰好因为一增一减而"看似"没变但实际
    #    已被替换的边界情况；也防止计划被应用到另一个 registry/图）。
    for et in plan.edge_transfers:
        if not registry.is_current_ordered_edge(et.edge_identity):
            raise ThermalTransportPlanError(
                f"apply_thermal_transport_plan: edge {et.edge_identity.uid!r} is no "
                f"longer the registry's current version")
        if not registry.is_current_address(et.tail_address):
            raise ThermalTransportPlanError(
                f"apply_thermal_transport_plan: tail address {et.tail_address!r} is stale")
        if not registry.is_current_address(et.head_address):
            raise ThermalTransportPlanError(
                f"apply_thermal_transport_plan: head address {et.head_address!r} is stale")

    # 4. 参与节点 charge 与计划快照时一致（方案A：状态过期检测）。
    for uid, snapshot_charge in plan.participating_node_snapshots.items():
        if uid not in cells_by_uid:
            raise ThermalTransportPlanError(
                f"apply_thermal_transport_plan: no ThermalCell provided for "
                f"address uid={uid!r} (plan applied to a different graph?)")
        current_charge = cells_by_uid[uid].capacitor.charge
        if current_charge != snapshot_charge:
            raise ThermalTransportPlanError(
                f"apply_thermal_transport_plan: node {uid!r} charge changed since "
                f"plan was prepared (snapshot={snapshot_charge}, current={current_charge})")

    # ── 唯一的写入区：提交前先备份全部参与节点的完整 Capacitor 状态 ──
    backup: Dict[str, Tuple[float, float, float]] = {
        uid: _snapshot_capacitor_state(cells_by_uid[uid])
        for uid in plan.participating_node_snapshots
    }
    try:
        for et in plan.edge_transfers:
            tail_cell = cells_by_uid[et.tail_address.uid]
            head_cell = cells_by_uid[et.head_address.uid]
            tail_cell.capacitor.inject(-et.power, plan.dt)
            head_cell.capacitor.inject(et.power, plan.dt)
    except Exception:
        for uid, snapshot in backup.items():
            _restore_capacitor_state(cells_by_uid[uid], snapshot)
        raise

    applied_plans.mark_applied(plan.plan_id)

    node_deltas_applied: Dict[str, float] = {
        uid: cells_by_uid[uid].capacitor.charge - plan.participating_node_snapshots[uid]
        for uid in plan.participating_node_snapshots
    }
    total_transport_residual = abs(sum(node_deltas_applied.values()))

    return ThermalTransportReceipt(
        plan_id=plan.plan_id,
        dt=plan.dt,
        node_deltas_applied=node_deltas_applied,
        total_transport_residual=total_transport_residual,
        registry_revision=registry.revision,
    )
