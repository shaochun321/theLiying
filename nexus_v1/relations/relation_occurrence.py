"""nexus_v1.relations.relation_occurrence — P2-B1X1c：在线D2关系实例闭合
（P2-B1X1e：补充去重防线）。

TYPE:INFRA（数据结构与状态机，不执行神经动力学）

方案依据：`cell-cell/交叉比对/document - 2026-07-30T130442.029.md`（P2-B1X1c）+
`cell-cell/交叉比对/document - 2026-07-31T203403.976.md`（P2-B1X1e：去重防线）。

P2-B1X1e 背景：P2-B1X1d端到端场景调试时发现，连续（非脉冲）驱动下collector
可能因神经元残余振荡在同一对父occurrence的rearm间隔内产生第二次上升沿，
若不加防线会重复登记两份"同一件事"的RelationOccurrence。本轮在
`RelationFinalizer`加(relation_type, parent_a_instance_id,
parent_b_instance_id, trace_scale)去重键——不是修改`OccurrenceClosure`
本身的迟滞参数（那会影响D1层语义），只在D2登记处拦截重复。

核心语义边界（评判明确要求）：
  关系实例的成立**不能依赖DA**——DA=0时仍必须生成 ρ_obs（观察到的关系）。
  应分开三件事：
    ρ^obs   = 实际观察到的关系（本模块负责）
    e^elig  = 关系活动留下的学习资格迹（SynapticBundle eligibility trace）
    Δw^DA   = DA门控后的结构沉积（variant_adapter.py中的learn()调用）
  P2-B1R所证明的局部作用资格属于关系载体类型，不是每个RelationOccurrence
  成立的必填条件。

执行时序（每步固定顺序，评判明确要求）：
  1. circuit.step()          实际驱动物理通路（唯一驱动权）
  2. tap_a.observe(t)        读取D1 occurrence（只读）
  3. tap_b.observe(t)        读取D1 occurrence（只读）
  4. finalizer.step(t)       根据tap产生的D1 transition + relation collector活动更新状态

RULES.md 强制三问：
  Q1 生物对应物：本模块无BIO对应物——纯身份管理与状态机基础设施（INFRA），
     类比OccurrenceClosure对D1 occurrence的管理，本模块对D2关系实例做同等
     管理。不执行突触传播、不修改权重、不影响神经元状态。
  Q2 物理结构：只读取已有tap/closure的输出（Occurrence对象/last_transitions），
     不新建Neuron/SynapticBundle，不调用任何会改变神经元状态的方法。
  Q3 参数依据：无物理参数。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..components.structural_address import GeneratedAddress, StructuralAddress
from ..generators.occurrence import OccurrenceInstanceId
from ..generators.occurrence_identity import OccurrenceIdentityRegistry
from ..generators.occurrence_tap import CollectorOccurrenceTap


# ── 关系类型常量 ──
RELATION_TYPE_A_PREC_B_FAST = "r_prec.a_prec_b_fast"
RELATION_TYPE_A_PREC_B_SLOW = "r_prec.a_prec_b_slow"

# ── 草稿状态 ──
DRAFT_STATUS_OPEN = "OPEN_RELATION_DRAFT"
DRAFT_STATUS_CLOSED = "CLOSED_INTO_OCCURRENCE"
DRAFT_STATUS_EXPIRED = "EXPIRED"
DRAFT_STATUS_REJECTED_EPOCH = "REJECTED_PARENT_EPOCH_UNRESOLVED"


@dataclass
class RelationDraft:
    """关系草稿：关系collector上升沿时创建，保存在线实例键。

    此时父occurrence可能尚未rearm（OccurrenceClosure处于ACTIVE/REFRACTORY
    状态），因此只保存(GeneratorAddress, EpochID)在线实例键，不要求
    OccurrenceInstanceId已被registry登记——父实例完成后registry会更新。

    关键语义：RelationDraft的成立不依赖DA，DA=0时同样可以创建draft。
    """
    relation_type: str

    # 父实例的在线身份键（collector激活时捕获，不等待父occurrence完成rearm）
    parent_a_instance_id: OccurrenceInstanceId
    parent_b_instance_id: OccurrenceInstanceId

    collector_address: StructuralAddress
    trace_scale: str          # "fast" / "slow"
    t_detect: int             # 关系collector首次越过阈值的时刻

    # 候选关系窗口（t_detect开始，持续到trace消失或被finalizer关闭）
    relation_window_start: int
    relation_window_end: Optional[int] = None

    status: str = DRAFT_STATUS_OPEN


@dataclass(frozen=True)
class RelationOccurrence:
    """正式D2关系实例：父A/B两次D1 occurrence都完成rearm并被registry登记后，
    由RelationFinalizer自动完成闭合。

    谱系：RelationOccurrence^(2) → NaturalUnitA^(1) / NaturalUnitB^(1)
          → OccurrenceA/B^(1) → Generator → D0/D_{-1}物理支撑。

    关键语义：成立不依赖DA（ρ^obs独立于e^elig和Δw^DA）。
    """
    relation_type: str
    parent_a_instance_id: OccurrenceInstanceId
    parent_b_instance_id: OccurrenceInstanceId

    t_detect: int    # 关系collector首次激活时刻
    t_closed: int    # 两个父实例都就绪、draft转为正式实例的时刻

    collector_address: StructuralAddress
    trace_scale: str

    # 父occurrence地址（从registry解析得到，完整谱系回指D1→D0）
    occurrence_a_address: GeneratedAddress
    occurrence_b_address: GeneratedAddress

    # 可选：物理账本快照（可供P2-B1X2切割实验使用）
    ledger_summary: Optional[str] = None


@dataclass
class RelationFinalizer:
    """监听D1 occurrence完成事件，自动将OPEN的RelationDraft转为正式RelationOccurrence。

    每步调用一次step(t_step)，传入两个tap（A/B各一）和OccurrenceIdentityRegistry。
    工作逻辑（每步固定顺序）：
      1. 读取tap_a/tap_b本步产生的Occurrence（若有），登记到registry；
      2. 读取relation_collector的当前状态，在上升沿创建RelationDraft；
      3. 对所有OPEN的draft，检查两个父实例是否已在registry中，若是则闭合为
         RelationOccurrence；
      4. 对超过关系窗口（trace已消失）但父实例仍未就绪的draft，标记为EXPIRED。

    关系collector上升沿判断（评判提醒：不是每步激活都创建draft）：
      draft只在collector从inactive→active的跳变时创建，而不是在每个
      pre_trace>threshold的步骤都创建——避免一次持续的collector活动制造
      大量重复实例。

    P2-B1X1e 去重防线（`document - 2026-07-31T203403.976.md`评判）：
      同一 (relation_type, parent_a_instance_id, parent_b_instance_id,
      trace_scale) 组合，无论已闭合为RelationOccurrence还是仍是OPEN
      draft，都只允许存在一份——collector在同一对父occurrence的rearm
      间隔内因残余振荡产生的第二次上升沿不会再创建新draft。只有当至少
      一个父生成元进入新的epoch（真正产生了新的D1 occurrence），
      dedup_key才会变化，才允许新关系登记。
    """
    tap_a: CollectorOccurrenceTap
    tap_b: CollectorOccurrenceTap
    registry: OccurrenceIdentityRegistry
    relation_collector: object  # Neuron（关系collector，只读.pre_trace/.spiked）
    collector_address: StructuralAddress
    relation_type: str
    trace_scale: str

    # 状态
    _was_collector_active: bool = field(default=False, repr=False)
    _open_drafts: List[RelationDraft] = field(default_factory=list, repr=False)
    completed_relations: List[RelationOccurrence] = field(default_factory=list)

    # P2-B1X1e：已登记的 (relation_type, parent_a, parent_b, trace_scale)
    # 组合键集合，防止同一对父实例被重复登记为多个 RelationOccurrence/
    # RelationDraft（见 document - 2026-07-31T203403.976.md 评判：残余
    # 振荡可能让 collector 在同一对父 occurrence 的 rearm 间隔内产生
    # 第二次上升沿，若不去重会生成两份"同一件事"的关系记录）。
    _registered_keys: set = field(default_factory=set, repr=False)

    # 关系窗口过期判据：collector pre_trace跌落到此值以下则关系窗口关闭
    _RELATION_CLOSE_THRESHOLD: float = 1e-4

    def step(self, t_step: int) -> Optional[RelationOccurrence]:
        """每步调用一次（在circuit.step()完成之后、relation layer step之后）。

        返回本步新完成的RelationOccurrence（若有），否则None。
        """
        # 1. 读取tap本步产生的D1 occurrence，登记到registry
        for tap in (self.tap_a, self.tap_b):
            for _ in range(10):  # 防止无限循环，正常情况每步至多1次
                # 已在tap.observe()里完成，这里只需读tap.closure.events最后一个
                break
        # 从tap.closure.events检查本步新增（由外部tap.observe()在同一步调用完成）
        # 实际做法：检查tap.closure.last_transitions里的"rearm"事件
        for tap in (self.tap_a, self.tap_b):
            for ev in tap.last_transitions:
                if ev.kind == "rearm":
                    # 取tap.closure.events最后一个（恰好是本步刚emit的）
                    if tap.closure.events:
                        occ = tap.closure.events[-1]
                        self.registry.register_occurrence(occ)

        # 2. 关系collector上升沿检测（评判提醒：不是每步都创建）
        collector_active = self.relation_collector.pre_trace > self._RELATION_CLOSE_THRESHOLD
        if collector_active and not self._was_collector_active:
            # 上升沿：捕获此时两个tap的当前epoch_id作为父实例在线键
            instance_id_a = OccurrenceInstanceId(
                generator_address=self.tap_a.address,
                epoch_id=self.tap_a.closure.epoch_id,
            )
            instance_id_b = OccurrenceInstanceId(
                generator_address=self.tap_b.address,
                epoch_id=self.tap_b.closure.epoch_id,
            )
            if instance_id_a.epoch_id > 0 and instance_id_b.epoch_id > 0:
                # P2-B1X1e 去重键：同一(关系类型, 父A实例, 父B实例, 尺度)
                # 组合只允许存在一份记录——不管是已完成的 RelationOccurrence
                # 还是仍在等待父实例就绪的 OPEN draft。残余振荡若在同一对
                # 父occurrence的rearm间隔内让collector再次产生上升沿，此处
                # 直接跳过，不追加新draft（不是修改 OccurrenceClosure 本身
                # 的迟滞参数，只在 D2 登记处拦截——同评判要求的修复位置）。
                dedup_key = (self.relation_type, instance_id_a, instance_id_b,
                             self.trace_scale)
                already_open = any(
                    d.relation_type == self.relation_type
                    and d.parent_a_instance_id == instance_id_a
                    and d.parent_b_instance_id == instance_id_b
                    and d.trace_scale == self.trace_scale
                    and d.status == DRAFT_STATUS_OPEN
                    for d in self._open_drafts)
                if dedup_key not in self._registered_keys and not already_open:
                    draft = RelationDraft(
                        relation_type=self.relation_type,
                        parent_a_instance_id=instance_id_a,
                        parent_b_instance_id=instance_id_b,
                        collector_address=self.collector_address,
                        trace_scale=self.trace_scale,
                        t_detect=t_step,
                        relation_window_start=t_step,
                    )
                    self._open_drafts.append(draft)
        self._was_collector_active = collector_active

        # 3. 尝试闭合OPEN的draft
        newly_closed = None
        still_open = []
        for draft in self._open_drafts:
            if draft.status != DRAFT_STATUS_OPEN:
                continue
            # 检查两个父实例是否已在registry
            occ_a = self.registry.lookup_occurrence(draft.parent_a_instance_id)
            occ_b = self.registry.lookup_occurrence(draft.parent_b_instance_id)
            if occ_a is not None and occ_b is not None:
                # 两个父实例都就绪，闭合为正式RelationOccurrence
                ro = RelationOccurrence(
                    relation_type=draft.relation_type,
                    parent_a_instance_id=draft.parent_a_instance_id,
                    parent_b_instance_id=draft.parent_b_instance_id,
                    t_detect=draft.t_detect,
                    t_closed=t_step,
                    collector_address=draft.collector_address,
                    trace_scale=draft.trace_scale,
                    occurrence_a_address=occ_a.address,
                    occurrence_b_address=occ_b.address,
                )
                self.completed_relations.append(ro)
                draft.status = DRAFT_STATUS_CLOSED
                newly_closed = ro
                # 登记去重键：这一对父实例的这种关系类型/尺度已经产生过
                # 正式记录，后续任何残余振荡触发的上升沿都不会再为它建
                # 新draft（见上方"上升沿检测"处的dedup_key检查）。
                self._registered_keys.add((
                    draft.relation_type, draft.parent_a_instance_id,
                    draft.parent_b_instance_id, draft.trace_scale))
            elif not collector_active and t_step - draft.t_detect > 5000:
                # 关系窗口已过期（超过5000步仍未解析），标记EXPIRED
                draft.status = DRAFT_STATUS_EXPIRED
            else:
                still_open.append(draft)
        self._open_drafts = still_open

        return newly_closed
