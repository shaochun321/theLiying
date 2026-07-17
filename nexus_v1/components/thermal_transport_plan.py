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

**本轮范围**：只做 `prepare()`（计划生成，纯只读）。`apply_thermal_transport_
plan()`（P1-B3，提交与故障语义）留待独立后续轮次——批判二十明确要求 B3 的
故障语义需要单独设计"证明提交区不抛异常"或"快照回滚"，不应预先假设，本轮
不做。

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
    registry_revision: int             # AddressRegistry.revision 的快照，供未来 apply() 判断 staleness
    edge_transfers: Tuple[EdgeTransfer, ...]
    node_outgoing_totals: Dict[str, float]   # tail uid -> Σ power（本计划范围内）
    node_net_deltas: Dict[str, float]        # uid -> 本计划导致的净能量变化（tail为负，head为正）
    stability_report: Dict[str, float]       # tail uid -> η_i^transport（诊断用，全部应 <=1，否则prepare已拒绝）


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

    # 5. 一次性拍摄所有 tail 的 charge 快照（同一时刻，先于任何计算）。
    tail_snapshots: Dict[str, float] = {}
    for link in links:
        tail_uid = link.identity.tail.uid
        if tail_uid not in tail_snapshots:
            tail_snapshots[tail_uid] = cells_by_uid[tail_uid].capacitor.charge

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
    )
