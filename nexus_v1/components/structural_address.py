"""nexus_v1.components.structural_address — Stable identity/topology audit layer (P1-A).

TYPE:INFRA — this is NOT a physical mechanism (no BIO/SEMI correlate).
It is audit/identity infrastructure, analogous to how real distributed
systems keep a stable instance identifier independent of in-memory/storage
position (standard software-engineering practice, not a biology REF).

Context (方案第二十一~二十三节 P1 立项；批判十六/十七细化，2026-07-17):
批判十六提出 P1-A（身份/拓扑契约），批判十七做编码前的类型化订正——地址拆
`StructuralAddress`（物理支撑）/`GeneratedAddress`（关系生成物）两类，边身份拆
`SymmetricEdgeIdentity`（扩散/接触，互易对称）/`OrderedEdgeIdentity`（介质传输，
真正有序）两类。**核查结论**：现有 `ThermalFieldGraph.cells` 已是
`Dict[int, ThermalCell]` 按 `node_id` 键控，全仓库无一处按数组位置寻址——本模块
要修的不是当前代码里的真实bug，是用户裁定采纳的长期基础设施投入（批判十六①的
"数组索引依赖"担忧本身已核实不成立，见方案第二十三节 23.1）。

Physical mechanism — Q1/Q2/Q3 (RULES.md 强制三问):

  Q1 生物/物理对应物:
    本模块无 BIO 对应物——它是纯粹的审计/身份基础设施（TYPE:INFRA），类比真实
    分布式系统"稳定实例标识符独立于内存/存储位置"的标准工程实践。RULES.md 的
    "每个组件映射真实生物/物理对象"要求对 INFRA 类型组件不适用（同 `nexus_v1/
    ledger/` 下的只读观测器一样，是观测/审计工具而非物理机制本身）。

  Q2 物理结构:
    `AddressRegistry` 只读查询现有 `ThermalFieldGraph.cells`（`node_id`字段）/
    `SkinThermalState`（`patch_id`字段）/`ThermalContact`（`world_node_id`/
    `skin_patch_id`字段）建立 `(domain, local_key) -> StructuralAddress` 映射，
    不修改这些类本身，也不改变它们的既有行为契约。地址/边身份对象本身是不可变
    （frozen dataclass）的纯数据结构，不持有物理状态。

  Q3 参数依据:
    无新物理参数——纯身份管理，不涉及标定。

Naming discipline (批判十七②)：`ε_e^sym` 的 `endpoints` 用 `FrozenSet` 存储，
这就是"端点无序"这个数学性质的直接结构化体现（构造 `{a,b}` 或 `{b,a}` 得到相等的
对象），不是靠约定注释维持。`ε_e^ord` 的 `tail`/`head` 是有序字段，交换后得到
不同的对象——`e_ij` 与 `e_ji` 是两个不同的有序传输实例。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Tuple, Union

# ── 域常量（批判十七①：物理支撑域 vs 生成物域）──
DOMAIN_WORLD_CELL = "world.cell"
DOMAIN_SKIN_PATCH = "skin.patch"
DOMAIN_HEAT_SOURCE = "heat_source"
DOMAIN_OCC_THERMAL = "occ.thermal"          # 生成物域（P2 使用，本轮仅占位）
DOMAIN_RELATION_PREC = "relation.r_prec"    # 生成物域（P2 使用，本轮仅占位）
DOMAIN_RELATION_RHO = "relation.r_rho"      # 生成物域（P2 使用，本轮仅占位）
DOMAIN_EVENT_KERNEL = "event.kernel"        # 生成物域（P2-B1K0）
DOMAIN_EVENT_CANDIDATE = "event.candidate"  # 生成物域（P2-B1K0）

_PHYSICAL_DOMAINS = frozenset({DOMAIN_WORLD_CELL, DOMAIN_SKIN_PATCH, DOMAIN_HEAT_SOURCE})
_GENERATED_DOMAINS = frozenset({
    DOMAIN_OCC_THERMAL, DOMAIN_RELATION_PREC, DOMAIN_RELATION_RHO,
    DOMAIN_EVENT_KERNEL, DOMAIN_EVENT_CANDIDATE
})

# 机制类型（批判十七②；批判二十②：介质传输改名为"有序过剩热能转移"，机制标识
# 同步收紧，不再用"medium-transport"——地址/拓扑账本的机制标签不是普通注释，
# 会进入域兼容性检查/边身份/账本追踪/未来 GeneratedAddress.parent_addresses，
# 现在改成本低，等 P2 回接后再改会造成地址谱系迁移）
MECHANISM_DIFFUSION = "diffusion"
MECHANISM_CONTACT = "contact"
MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER = "ordered-excess-thermal-transfer"
_SYMMETRIC_MECHANISMS = frozenset({MECHANISM_DIFFUSION, MECHANISM_CONTACT})
_ORDERED_MECHANISMS = frozenset({MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER})

# 端点域—机制兼容表（批判十七"端点域必须与机制兼容"结构测试用）
_MECHANISM_DOMAIN_COMPAT = {
    MECHANISM_DIFFUSION: frozenset({(DOMAIN_WORLD_CELL, DOMAIN_WORLD_CELL)}),
    MECHANISM_CONTACT: frozenset({
        (DOMAIN_WORLD_CELL, DOMAIN_SKIN_PATCH), (DOMAIN_SKIN_PATCH, DOMAIN_WORLD_CELL),
    }),
    MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER: frozenset({(DOMAIN_WORLD_CELL, DOMAIN_WORLD_CELL)}),
}


@dataclass(frozen=True)
class StructuralAddress:
    """TYPE:INFRA — α_phys(x) = (domain, uid, version)，用于物理支撑
    （世界节点/皮肤支撑/热源/物理边界）。**地址不是坐标**——`uid` 是稳定身份
    字符串，不编码空间位置；`version` 只在身份连续性被破坏时递增（见
    `AddressRegistry.rebuild_physical()`），不因温度/能量等普通状态变化改变。
    """
    domain: str
    uid: str
    version: int = 0


@dataclass(frozen=True)
class GeneratedAddress:
    """TYPE:INFRA — α_gen(x) = (domain, uid, parent_addresses, generation_depth,
    version)，用于关系生成物（ξ^occ/r≺^τ/r_ρ^τ/未来关系-关系生成物）。
    `parent_addresses` 是父支撑或父关系地址的元组（不用 list，保持可哈希/不可变）。
    本轮（P1-A）只定义数据结构，不接真实实体——P2 阶段才会用它包装
    ξ^occ/r≺^τ/r_ρ^τ 的真实地址。
    """
    domain: str
    uid: str
    parent_addresses: Tuple[Union[StructuralAddress, "GeneratedAddress"], ...]
    generation_depth: int
    version: int = 0

    def __post_init__(self):
        if self.generation_depth < 0:
            raise ValueError(f"GeneratedAddress: generation_depth must be >= 0, got {self.generation_depth}")


@dataclass(frozen=True)
class SymmetricEdgeIdentity:
    """TYPE:INFRA — ε_e^sym = (uid, {addr_i, addr_j}, mechanism, version)。
    扩散边/接触边用这个类型——J=κ(T_i-T_j) / J=H(T_w-T_s) 本质是两端点间互易
    耦合，source/target 只是某次计算的符号约定，不是边永久属性。`endpoints`
    用 `FrozenSet` 存储，构造 `{a,b}` 与 `{b,a}` 得到相等对象——"端点无序"这个
    性质由数据结构本身保证，不依赖注释约定。
    """
    uid: str
    endpoints: FrozenSet[StructuralAddress]
    mechanism: str
    version: int = 0

    def __post_init__(self):
        if self.mechanism not in _SYMMETRIC_MECHANISMS:
            raise ValueError(
                f"SymmetricEdgeIdentity: mechanism must be one of "
                f"{sorted(_SYMMETRIC_MECHANISMS)}, got {self.mechanism!r}")
        if len(self.endpoints) != 2:
            raise ValueError(
                f"SymmetricEdgeIdentity: must have exactly 2 distinct endpoints, "
                f"got {len(self.endpoints)}")


@dataclass(frozen=True)
class OrderedEdgeIdentity:
    """TYPE:INFRA — ε_e^ord = (uid, tail, head, mechanism, version)。只有 P1-B
    的介质传输边（`mechanism="ordered-excess-thermal-transfer"`）用这个类型——
    `J_tail→head^tr = a·E_tail` 的公式本身依赖哪端是 `tail`，是真正有序的。
    `e_ij`（tail=i,head=j）与 `e_ji`（tail=j,head=i）是两个不同的对象。
    """
    uid: str
    tail: StructuralAddress
    head: StructuralAddress
    mechanism: str = MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER
    version: int = 0

    def __post_init__(self):
        if self.mechanism not in _ORDERED_MECHANISMS:
            raise ValueError(
                f"OrderedEdgeIdentity: mechanism must be one of "
                f"{sorted(_ORDERED_MECHANISMS)}, got {self.mechanism!r}")
        if self.tail == self.head:
            raise ValueError("OrderedEdgeIdentity: tail and head must differ (no self-loop)")


@dataclass
class TopologyValidationReport:
    """P1-A 拓扑审计结果容器。每个字段是一项结构测试的结果，`passed` 是全部
    通过的汇总。不是新的物理机制，纯粹的检查结果聚合。
    """
    checks: Dict[str, bool] = field(default_factory=dict)
    messages: Dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(self.checks.values()) if self.checks else False

    def record(self, name: str, ok: bool, message: str = "") -> None:
        self.checks[name] = ok
        self.messages[name] = message


class AddressRegistry:
    """TYPE:INFRA — `local_key ↔ stable_uid` 双向映射 + 边身份注册表。

    Q2: 只读查询已有组件的 `node_id`/`patch_id`/`world_node_id` 字段建立映射，
    不修改这些组件本身。`local_key` 是调用方传入的、组件当前使用的查表键
    （如 `ThermalFieldGraph.cells` 的整数 `node_id`）；`stable_uid` 是跨重建
    保持的物理身份字符串（`domain:local_key` 复合，首次注册时确定，重建后
    的 `stable_uid` 不变但 `version` 递增）——两者是不同字段，这样"local_key
    变化但 stable_uid 不变"这条测试才能被真正构造（批判十七③）。
    """

    def __init__(self):
        self._addresses: Dict[str, StructuralAddress] = {}          # uid -> address
        self._local_to_uid: Dict[Tuple[str, Any], str] = {}         # (domain, local_key) -> uid
        self._uid_to_local: Dict[str, Any] = {}                     # uid -> current local_key
        self._generated: Dict[str, GeneratedAddress] = {}                  # uid -> generated address (P2)
        self._generated_local_to_uid: Dict[Tuple[str, Any], str] = {}      # (domain, local_key) -> uid (P2)
        self._sym_edges: Dict[str, SymmetricEdgeIdentity] = {}
        self._ord_edges: Dict[str, OrderedEdgeIdentity] = {}
        self._sym_edge_keys: Dict[Tuple[FrozenSet[str], str], str] = {}   # (endpoint uids, mechanism) -> edge uid
        self._ord_edge_keys: Dict[Tuple[str, str, str], str] = {}         # (tail uid, head uid, mechanism) -> edge uid
        self._retired_local_keys: set = set()   # (domain, local_key) freed by rebuild_physical(); must not silently resurrect
        self._revision: int = 0   # P1-B2: monotonic counter, bumped on every successful mutation
                                   # (new address/edge registration, rebuild). Lets ThermalTransportPlan
                                   # (P1-B2) snapshot "registry state at prepare-time" for later staleness
                                   # checks (P1-B3's apply()) without needing per-object revision fields.

    @property
    def revision(self) -> int:
        """当前注册表版本号——每次成功的注册/重建操作后递增一次。供
        `ThermalTransportPlan`（P1-B2）快照，P1-B3 的 `apply()` 用它判断
        提交时注册表是否已经变化（stale plan 检测）。"""
        return self._revision

    # ── 节点地址 ──

    def register_physical(self, domain: str, local_key: Any) -> StructuralAddress:
        """幂等注册：同一 (domain, local_key) 重复调用返回同一地址（uid/version
        不变）。首次注册 uid = f"{domain}:{local_key}"，version=0。
        """
        if domain not in _PHYSICAL_DOMAINS:
            raise ValueError(f"register_physical: unknown physical domain {domain!r}, "
                              f"expected one of {sorted(_PHYSICAL_DOMAINS)}")
        key = (domain, local_key)
        if key in self._retired_local_keys:
            raise ValueError(
                f"register_physical: (domain={domain!r}, local_key={local_key!r}) was "
                f"retired by a prior rebuild_physical() call — the uid string "
                f"f'{{domain}}:{{local_key}}' would silently collide with the now-stale "
                f"pre-rebuild identity. Old address is invalidated by design (批判十七④); "
                f"use the address returned by rebuild_physical(), or resolve(uid) to find "
                f"the current local_key.")
        if key in self._local_to_uid:
            uid = self._local_to_uid[key]
            return self._addresses[uid]
        uid = f"{domain}:{local_key}"
        addr = StructuralAddress(domain=domain, uid=uid, version=0)
        self._addresses[uid] = addr
        self._local_to_uid[key] = uid
        self._uid_to_local[uid] = local_key
        self._revision += 1
        return addr

    def register_generated(
        self,
        domain: str,
        local_key: Any,
        parent_addresses: Tuple[Union[StructuralAddress, "GeneratedAddress"], ...],
        generation_depth: int,
    ) -> GeneratedAddress:
        """P2 首次接线：为关系生成物（ξ^occ/r≺^τ/r_ρ^τ）分配 `GeneratedAddress`。
        对称于 `register_physical`：幂等（同一 `(domain, local_key)` 重复调用
        返回同一地址，忽略后续调用传入的 `parent_addresses`/`generation_depth`），
        `uid = f"{domain}:{local_key}"`，version=0。

        与 `register_physical` 的区别只在于域集合（`_GENERATED_DOMAINS` 而非
        `_PHYSICAL_DOMAINS`）和多出的谱系字段（`parent_addresses`/
        `generation_depth`，由 `GeneratedAddress.__post_init__` 校验非负）。
        `parent_addresses` 必须非空——生成物地址不允许悬空谱系（禁止"猜回"
        物理上已丢失的信息，等价于强制每个生成物可追溯至少一个真实支撑）。
        """
        if domain not in _GENERATED_DOMAINS:
            raise ValueError(f"register_generated: unknown generated domain {domain!r}, "
                              f"expected one of {sorted(_GENERATED_DOMAINS)}")
        if not parent_addresses:
            raise ValueError("register_generated: parent_addresses must be non-empty "
                              "(a generated address must trace back to at least one "
                              "physical or generated parent)")
        for p in parent_addresses:
            if not isinstance(p, (StructuralAddress, GeneratedAddress)):
                raise TypeError(f"register_generated: parent_addresses entries must be "
                                 f"StructuralAddress or GeneratedAddress, got {type(p)!r}")
        key = (domain, local_key)
        if key in self._generated_local_to_uid:
            uid = self._generated_local_to_uid[key]
            return self._generated[uid]
        uid = f"{domain}:{local_key}"
        addr = GeneratedAddress(
            domain=domain, uid=uid, parent_addresses=tuple(parent_addresses),
            generation_depth=generation_depth, version=0)
        self._generated[uid] = addr
        self._generated_local_to_uid[key] = uid
        self._revision += 1
        return addr

    def rebuild_physical(self, domain: str, old_local_key: Any, new_local_key: Any) -> StructuralAddress:
        """身份连续性受控破坏事件：对象销毁后用同一 UID 重建到新的
        local_key。version 递增，uid 不变——旧 (domain, old_local_key) 的
        local_key 映射失效（不能再通过旧 local_key 查到这个地址），但通过
        uid 仍能追溯到同一物理身份。
        """
        old_key = (domain, old_local_key)
        if old_key not in self._local_to_uid:
            raise KeyError(f"rebuild_physical: {old_key} not registered")
        uid = self._local_to_uid.pop(old_key)
        self._retired_local_keys.add(old_key)
        old_addr = self._addresses[uid]
        new_addr = StructuralAddress(domain=domain, uid=uid, version=old_addr.version + 1)
        self._addresses[uid] = new_addr
        self._local_to_uid[(domain, new_local_key)] = uid
        self._uid_to_local[uid] = new_local_key
        self._revision += 1
        return new_addr

    def resolve(self, uid: str) -> Any:
        """uid -> 当前 local_key（跨重建后的最新值）。"""
        if uid not in self._uid_to_local:
            raise KeyError(f"resolve: unknown uid {uid!r}")
        return self._uid_to_local[uid]

    def address_of(self, domain: str, local_key: Any) -> Optional[StructuralAddress]:
        """只读查询，不注册。未注册返回 None（用于"边端点必须存在"检查）。"""
        return self._addresses.get(self._local_to_uid.get((domain, local_key)))

    # ── 边身份 ──

    def register_symmetric_edge(
        self, addr_i: StructuralAddress, addr_j: StructuralAddress, mechanism: str,
    ) -> SymmetricEdgeIdentity:
        """扩散/接触边注册。禁止同一物理边（相同端点对+机制）重复注册——
        重复调用会 raise，防止重复扣账（批判十七①"禁止同一物理边被重复注册
        并重复扣账"）。端点顺序无关：`register_symmetric_edge(a,b,m)` 与
        `register_symmetric_edge(b,a,m)` 命中同一条已注册边。
        """
        self._require_registered(addr_i)
        self._require_registered(addr_j)
        self._check_mechanism_domain_compat(addr_i.domain, addr_j.domain, mechanism)
        endpoint_uids = frozenset({addr_i.uid, addr_j.uid})
        edge_key = (endpoint_uids, mechanism)
        if edge_key in self._sym_edge_keys:
            raise ValueError(
                f"register_symmetric_edge: edge already registered for "
                f"endpoints={sorted(endpoint_uids)} mechanism={mechanism!r} "
                f"(duplicate registration would double-debit energy)")
        uid = f"edge.sym:{mechanism}:{':'.join(sorted(endpoint_uids))}"
        edge = SymmetricEdgeIdentity(
            uid=uid, endpoints=frozenset({addr_i, addr_j}), mechanism=mechanism)
        self._sym_edges[uid] = edge
        self._sym_edge_keys[edge_key] = uid
        self._revision += 1
        return edge

    def register_ordered_edge(
        self, tail: StructuralAddress, head: StructuralAddress, mechanism: str = MECHANISM_ORDERED_EXCESS_THERMAL_TRANSFER,
    ) -> OrderedEdgeIdentity:
        """介质传输边注册。`e_ij`（tail=i,head=j）与 `e_ji`（tail=j,head=i）
        是两个不同的有序传输实例——分别注册，互不冲突；但同一 (tail,head,
        mechanism) 重复注册仍会 raise（同上，禁止重复扣账）。
        """
        self._require_registered(tail)
        self._require_registered(head)
        self._check_mechanism_domain_compat(tail.domain, head.domain, mechanism)
        edge_key = (tail.uid, head.uid, mechanism)
        if edge_key in self._ord_edge_keys:
            raise ValueError(
                f"register_ordered_edge: edge already registered for "
                f"tail={tail.uid!r} head={head.uid!r} mechanism={mechanism!r} "
                f"(duplicate registration would double-debit energy)")
        uid = f"edge.ord:{mechanism}:{tail.uid}->{head.uid}"
        edge = OrderedEdgeIdentity(uid=uid, tail=tail, head=head, mechanism=mechanism)
        self._ord_edges[uid] = edge
        self._ord_edge_keys[edge_key] = uid
        self._revision += 1
        return edge

    def _require_registered(self, addr: StructuralAddress) -> None:
        """边两端点必须存在（批判十七 8 项结构测试之一），且必须是该 uid 当前
        有效的地址版本——引用一个已被 `rebuild_physical()` 淘汰的旧版本地址
        对象同样拒绝（旧地址失效不只对 local_key 查找生效，对边注册也生效）。
        """
        current = self._addresses.get(addr.uid)
        if current is None:
            raise ValueError(f"edge endpoint {addr!r} is not a registered address")
        if current != addr:
            raise ValueError(
                f"edge endpoint {addr!r} is a stale address (current registered "
                f"version is {current!r}) — re-fetch the address before building edges")

    @staticmethod
    def _check_mechanism_domain_compat(domain_a: str, domain_b: str, mechanism: str) -> None:
        compat = _MECHANISM_DOMAIN_COMPAT.get(mechanism)
        if compat is None:
            raise ValueError(f"_check_mechanism_domain_compat: unknown mechanism {mechanism!r}")
        if (domain_a, domain_b) not in compat and (domain_b, domain_a) not in compat:
            raise ValueError(
                f"mechanism {mechanism!r} is not compatible with domain pair "
                f"({domain_a!r}, {domain_b!r})")

    # ── 拓扑审计 ──

    def all_symmetric_edges(self) -> List[SymmetricEdgeIdentity]:
        return list(self._sym_edges.values())

    def all_ordered_edges(self) -> List[OrderedEdgeIdentity]:
        return list(self._ord_edges.values())

    def all_addresses(self) -> List[StructuralAddress]:
        return list(self._addresses.values())

    def all_generated(self) -> List[GeneratedAddress]:
        return list(self._generated.values())

    def is_current_address(self, addr: StructuralAddress) -> bool:
        """P1-B2: 只读判断——`addr` 是否仍是该 uid 当前有效的地址版本（不
        raise，供 `ThermalTransportPlan.prepare()` 批量校验时使用，同
        `_require_registered()` 的判定逻辑，只是不抛异常改为返回布尔值）。
        """
        return self._addresses.get(addr.uid) == addr

    def is_current_ordered_edge(self, edge: OrderedEdgeIdentity) -> bool:
        """P1-B2: 只读判断——`edge` 是否仍是该 uid 当前注册的有序边身份。"""
        return self._ord_edges.get(edge.uid) == edge
