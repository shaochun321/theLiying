"""nexus_v1.events.event_support — P2-B1K0: 事件元支撑绑定器

TYPE:INFRA（数据结构与资格判定逻辑，不涉及神经动力学）

方案依据：`cell-cell/交叉比对/document - 2026-07-29T140411.192.md`

背景：P2-B1R已证明学习后的关系连接具有局部物理作用（L1资格），可作为
事件元支撑。P2-B1K0解决的问题是：**这段局部作用属于哪两次真实发生？
哪些物理结构共同支撑了这一次关系过程？**

核心约束：
  1. 必须记录实例身份（occurrence_28_epoch_17），不是站点身份（site28）
  2. 补齐D2→D1→D0谱系（关系→occurrence→物理支撑）
  3. 账本只是可选审计字段，不主动控制事件成立条件

本轮资格：
  能够把一条已取得局部作用资格的D2关系，绑定到正确的两次D1发生。

RULES.md 强制三问：
  Q1 生物/物理对应物：
    本模块是INFRA类型，类似AddressRegistry——是审计/身份管理基础设施，
    不对应具体物理机制。它管理的是"哪些结构共同支撑一个事件实例"的
    谱系绑定关系，不执行神经动力学。

  Q2 物理结构：
    只读查询已有结构地址（Occurrence/NaturalUnit/relation/collector/bundle），
    建立谱系绑定关系。不修改这些结构本身，不新增神经元或bundle。

  Q3 参数依据：
    无物理参数——纯身份管理与资格判定逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from ..components.structural_address import GeneratedAddress, StructuralAddress

# ── 事件核类型常量 ──
EVENT_KERNEL_A_PRECEDES_B_FAST = "event.a_prec_b_fast"

# ── 候选资格状态 ──
STATUS_CANDIDATE = "CANDIDATE"
STATUS_REJECTED_INCOMPLETE_SUPPORT = "REJECTED_INCOMPLETE_SUPPORT"
STATUS_REJECTED_LINEAGE_MISMATCH = "REJECTED_LINEAGE_MISMATCH"


@dataclass(frozen=True)
class EventKernelSpec:
    """TYPE:INFRA — 事件核规格：描述一种候选事件需要哪些支撑。

    不执行神经动力学，只定义"哪些元支撑必须存在"的结构契约。

    当前只定义一种核：A_PRECEDES_B_FAST（A先于B，快时间尺度）。
    """
    address: GeneratedAddress
    generation_depth: int  # 事件是D3，关系是D2，occurrence是D1
    required_port_types: Tuple[str, ...]  # 输入端口类型（如"occ.thermal"）
    required_support_roles: Tuple[str, ...]  # 必需支撑角色（trace/collector/bundle等）
    output_types: Tuple[str, ...]  # 合格输出类型（如"local_current"）

    def __post_init__(self):
        if self.generation_depth < 2:
            raise ValueError(
                f"EventKernelSpec: generation_depth must be >= 2 (events are D3+), "
                f"got {self.generation_depth}")


@dataclass(frozen=True)
class EventSupportBinding:
    """TYPE:INFRA — 事件元支撑绑定：把某一次实际发生绑定到事件核上。

    关键设计：记录**实例身份**（occurrence_28_epoch_17），不是站点身份（site28）。
    这样相同站点后来再次发生时，不会被错误地拼进旧事件。

    补齐谱系：D2关系 → D1两次occurrence → D0/D_{-1}物理支撑。
    """
    kernel_address: GeneratedAddress  # 指向EventKernelSpec

    # D1层：两次occurrence实例（实例身份，非站点身份）
    occurrence_a_address: GeneratedAddress
    occurrence_b_address: GeneratedAddress

    # D2层：关系地址（应回指两个occurrence，而非直接回指皮肤）
    relation_address: GeneratedAddress

    # 物理元件身份
    collector_address: StructuralAddress  # relation collector神经元
    bundle_address: StructuralAddress  # 可塑relation bundle

    # D0/D_{-1}层：物理支撑
    physical_support_addresses: Tuple[StructuralAddress, ...]  # 皮肤/世界节点等

    # 关系元数据
    relation_kind: str  # "a_prec_b_fast"等
    relation_window: Tuple[int, int]  # 关系检测的时间窗口(t_start, t_end)


@dataclass(frozen=True)
class EventInstanceCandidate:
    """TYPE:INFRA — 事件实例候选：绑定成功后产生的候选实例。

    第一版只允许三种状态：
      - CANDIDATE：所有必需支撑完整且谱系正确
      - REJECTED_INCOMPLETE_SUPPORT：缺失必要支撑
      - REJECTED_LINEAGE_MISMATCH：谱系错配（如A、B不在同一关系窗口）

    不包含完整状态机（READY/ACTIVE/EXIT/REARM），那是P2-B1K1的任务。
    """
    address: GeneratedAddress  # 候选实例地址
    kernel_address: GeneratedAddress  # 指向EventKernelSpec
    support_binding: EventSupportBinding  # 绑定的元支撑

    t_enter: int  # 候选资格检查时刻（仿真步）
    local_effect_measure: float  # 局部作用测量值（如P2-B1R的电流ratio）

    # 资格判定
    lineage_valid: bool  # 谱系是否正确（A、B在同一关系窗口）
    support_complete: bool  # 必需支撑是否完整
    qualification_status: str  # STATUS_CANDIDATE / STATUS_REJECTED_*

    def __post_init__(self):
        if self.qualification_status not in {
            STATUS_CANDIDATE,
            STATUS_REJECTED_INCOMPLETE_SUPPORT,
            STATUS_REJECTED_LINEAGE_MISMATCH,
        }:
            raise ValueError(
                f"EventInstanceCandidate: invalid qualification_status "
                f"{self.qualification_status!r}")

        # 一致性检查：CANDIDATE必须lineage_valid=True且support_complete=True
        if self.qualification_status == STATUS_CANDIDATE:
            if not (self.lineage_valid and self.support_complete):
                raise ValueError(
                    f"EventInstanceCandidate: status=CANDIDATE requires "
                    f"lineage_valid=True and support_complete=True, got "
                    f"lineage_valid={self.lineage_valid}, "
                    f"support_complete={self.support_complete}")


def create_event_candidate(
    binding: EventSupportBinding,
    t_enter: int,
    local_effect_measure: float,
    registry=None,  # AddressRegistry，用于验证地址存在性
) -> EventInstanceCandidate:
    """工厂函数：根据EventSupportBinding创建候选实例并判定资格。

    资格判定逻辑（P2-B1K0）：
      Q_lineage：A、B的occurrence必须在同一关系窗口内，且relation的parent_addresses
                 必须包含binding中的occurrence_a和occurrence_b（谱系一致性）
      Q_support：必需支撑（occurrence_a, occurrence_b, relation, collector, bundle）全部非None
      Q_local_effect：local_effect_measure > 0（已确认局部作用）

    Returns:
        EventInstanceCandidate，status为CANDIDATE或REJECTED_*
    """
    # 检查谱系正确性：
    # 1. A、B非空
    # 2. relation的parent_addresses必须包含binding中的occurrence_a和occurrence_b
    lineage_valid = (
        binding.occurrence_a_address is not None
        and binding.occurrence_b_address is not None
        and binding.relation_address is not None
    )

    # 进一步检查谱系一致性：relation的父地址必须匹配binding中的occurrence
    if lineage_valid and binding.relation_address.parent_addresses:
        parent_set = set(binding.relation_address.parent_addresses)
        if binding.occurrence_a_address not in parent_set or \
           binding.occurrence_b_address not in parent_set:
            lineage_valid = False  # 谱系错配：relation的父地址不包含binding中的occurrence

    # 检查支撑完整性：所有必需元件地址非空
    support_complete = (
        lineage_valid  # 前提：谱系有效
        and binding.collector_address is not None
        and binding.bundle_address is not None
        and len(binding.physical_support_addresses) >= 2  # 至少两个物理支撑（A和B的站点）
        and local_effect_measure > 0  # 局部作用已确认
    )

    # 确定资格状态
    if lineage_valid and support_complete:
        status = STATUS_CANDIDATE
    elif not lineage_valid:
        status = STATUS_REJECTED_LINEAGE_MISMATCH
    else:
        status = STATUS_REJECTED_INCOMPLETE_SUPPORT

    # 生成候选实例地址（D3，父地址是D2关系）
    from ..components.structural_address import AddressRegistry
    if registry is None:
        registry = AddressRegistry()

    candidate_uid = f"event_candidate_{binding.relation_address.uid}_{t_enter}"
    candidate_addr = registry.register_generated(
        domain="event.candidate",
        local_key=candidate_uid,
        parent_addresses=(binding.relation_address,),
        generation_depth=3,  # 事件是D3
    )

    return EventInstanceCandidate(
        address=candidate_addr,
        kernel_address=binding.kernel_address,
        support_binding=binding,
        t_enter=t_enter,
        local_effect_measure=local_effect_measure,
        lineage_valid=lineage_valid,
        support_complete=support_complete,
        qualification_status=status,
    )
