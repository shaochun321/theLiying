"""nexus_v1.relations.r2_fork.py — P2-C1F：共同源分叉型R2关系（关系-关系生成）。

TYPE:INFRA（R2Occurrence/R2ForkFinalizer）+ BIO（R2ForkCircuit的新bundle）

方案依据：
  document - 2026-08-01T230002.273.md（共同源分叉型路线）
  document - 2026-08-01T232255.527.md（R2层语义+共同源资格必须核验同一OccurrenceInstanceId）

拓扑：
       31
      ↗  (T1: 28≺31的relation_collector)
  28                             → R2 fork collector → R2Occurrence
      ↘  (T2: 28≺23的relation_collector)
       23

R2 collector的输入：
  T1 rprec_collector_a_prec_b_fast.pre_trace（28≺31被检测到时活跃）
  T2 rprec2_collector_b_prec_c_fast.pre_trace（28≺23被检测到时活跃）
两路同时活跃才触发R2 collector，类比R1的trace+raw AND门结构。

共同源资格（评判232255关键修正）：
  ρ_1（T1）的共同起点 = OccurrenceInstanceId(site28, epoch_n)
  ρ_2（T2）的共同起点 = OccurrenceInstanceId(site28, epoch_n)
  两者必须是**同一个**OccurrenceInstanceId，不是相同地址不同epoch。
  仅当 parent_a_instance_id(ro_t1) == parent_b_instance_id_of_source(ro_t2)
  即两条关系的"站点28 D1实例"相同时，才生成R2Occurrence。

R2层命名规范（评判232255）：
  D1 = 基础发生
  R1 = 发生-发生关系（现有RelationOccurrence/T1/T2）
  R2 = 关系-关系关系（本文件的R2Occurrence/R2ForkFinalizer）
  不说"D2关系"——D2是旧的D0/D1/D2深度体系，与R1/R2生成层次不是同一维度。

资格目标（第一版P2-C1F）：
  同一个u_{28,n}支撑的两条活跃R1，通过新物理链路生成共同源型R2，
  产生非零、双父R1依赖的R2输出（不宣称散度/因果树/高阶涌现）。

RULES.md 强制三问：
  Q1 BIO: R2 collector复用R1的AND门+trace检测机制（同T1/T2的collector，
     BIO已在temporal_r_prec.py Q1中说明）。两条R1关系同时活跃时触发R2，
     类比"多路STDP eligibility trace重合"的时序整合机制。
  Q2 物理结构：
     新增2条frozen bundle（T1 col → R2 col，T2 col → R2 col）和
     1个R2 collector Neuron。不新建D1路径，不修改T1/T2已有bundle。
     复用CollectorOccurrenceTap + OccurrenceIdentityRegistry已有接口。
  Q3 参数：R2 collector参数全部复用T1/T2的collector标定值（已验证），
     bundle权重参照T1的_W_RAW_XI_TO_COLLECTOR（两路都是"直接raw"输入，
     无trace积分，因为R1 collector已经是集成后的信号），不重新标定。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..circuit.bundle import BundleConfig, SynapticBundle
from ..components.neuron import Neuron, NeuronConfig, ChannelConfig
from ..generators.occurrence import OccurrenceInstanceId
from ..generators.occurrence_tap import CollectorOccurrenceTap
from ..components.structural_address import StructuralAddress, GeneratedAddress
from .temporal_r_prec import RPrecCircuitT1
from .temporal_r_prec_t2 import RPrecCircuitT2

DT = 0.001

# ── R2 collector参数（复用T1标定值） ──
_R2_COLLECTOR_CAPACITANCE = 0.007
_R2_COLLECTOR_R_LEAK = 1.5
_R2_COLLECTOR_V_PEAK = 0.23
_R2_COLLECTOR_THRESHOLD = 0.15
_R2_COLLECTOR_GM = 3.0
_R2_COLLECTOR_TAU_GATE = 2.0
_R2_W_INPUT = 0.15   # 复用T1 _W_RAW_XI_TO_COLLECTOR：两路R1 collector直接接入

RELATION_TYPE_FORK_R2_FAST = "r2.fork.28prec31_and_28prec23"
_R2_CLOSE_THRESHOLD = 1e-4


def _r2_collector_config() -> NeuronConfig:
    return NeuronConfig(
        neuron_id="r2_fork_collector",
        region=0x01,
        spiking=True,
        v_peak=_R2_COLLECTOR_V_PEAK,
        v_reset=0.077,
        b_adapt=0.01,
        tau_w=1.0,
        capacitance=_R2_COLLECTOR_CAPACITANCE,
        r_leak=_R2_COLLECTOR_R_LEAK,
        inertia=1.0,
        channels=[ChannelConfig(
            name="default",
            v_threshold=_R2_COLLECTOR_THRESHOLD,
            gm=_R2_COLLECTOR_GM,
            tau_gate=_R2_COLLECTOR_TAU_GATE,
            reversal=1.0,
            sign=1.0,
        )],
    )


def _frozen_bundle(bundle_id: str, sources, targets, weight: float) -> SynapticBundle:
    cfg = BundleConfig(
        bundle_id=bundle_id,
        learning_rule="frozen",
        initial_weight=weight,
        weight_max=weight,
        synapse_gain=1.0,
        bundle_role="feedforward",
        remodel_cost_kappa=0.0,
    )
    return SynapticBundle(cfg, sources, targets)


# ── R2Occurrence：关系-关系实例 ──────────────────────────────────────────────

@dataclass(frozen=True)
class R2Occurrence:
    """R2关系实例：同一个u_{28,n}支撑的两条R1关系同时被检测后的组合记录。

    字段设计：
      shared_source_instance_id：两条R1关系的共同起点D1实例（u_{28,n}），
          必须是相同的OccurrenceInstanceId（site28, epoch_n）。
      parent_r1_t1_instance_key：T1关系（28≺31）的身份键，为四元组
          (relation_type, parent_a_instance_id, parent_b_instance_id, trace_scale)
          或等价的RelationOccurrence哈希；轻量不持有整个RelationOccurrence对象。
      parent_r1_t2_instance_key：T2关系（28≺23）的身份键，同上。

    R2层语义（不是D2记录层）：
      此实例证明"同一次u_{28,n}支撑下，两条R1关系同时被检测为真"——
      不宣称传递闭包A≺C、不宣称高阶涌现，只记录这个组合事实发生过。
    """
    relation_type: str  # RELATION_TYPE_FORK_R2_FAST

    # 共同源D1实例（两条R1都从此发出）——评判232255关键要求
    shared_source_instance_id: OccurrenceInstanceId

    # 两个父R1关系的身份键（轻量四元组，不是完整对象引用）
    parent_r1_t1_key: Tuple   # (relation_type, parent_a_id, parent_b_id, trace_scale)
    parent_r1_t2_key: Tuple

    t_detect: int   # R2 collector首次激活时刻
    t_closed: int   # 两个父R1都就绪时的时刻

    r2_collector_address: StructuralAddress

    # 可选：局部输出快照（供切断验证用）
    ledger_summary: Optional[str] = None


# ── R2ForkCircuit ─────────────────────────────────────────────────────────────

class R2ForkCircuit(RPrecCircuitT1, RPrecCircuitT2):
    """T1 + T2 + R2 fork collector的组合电路。

    继承链：R2ForkCircuit → RPrecCircuitT1 → RPrecCircuitT2 → VariantCircuit。
    MRO保证__init__顺序：T1先初始化（获得T1的trace/collector），
    T2通过super().__init__()链继续初始化（获得T2的trace/collector），
    最后R2新增自己的组件。

    站点28的xi collector（thermal_quantum_collectors["thermpt28_warm"]）
    在T1中被赋给rprec_xi_a，在T2中被赋给rprec2_xi_b——两者指向同一对象
    （已通过实测确认：rprec_xi_a is rprec2_xi_b == True），天然共享，
    这正是共同源结构的物理基础。
    """

    def __init__(self):
        super().__init__()  # 初始化T1→T2→VariantCircuit全链

        # ── R2 fork collector ──
        self.r2_fork_collector = Neuron(_r2_collector_config())

        # ── R2 input bundles：T1 collector → R2 col，T2 collector → R2 col ──
        self.bundle_r1t1_to_r2 = _frozen_bundle(
            "r2_fork_r1t1_to_collector",
            [self.rprec_collector_a_prec_b_fast],
            [self.r2_fork_collector],
            _R2_W_INPUT,
        )
        self.bundle_r1t2_to_r2 = _frozen_bundle(
            "r2_fork_r1t2_to_collector",
            [self.rprec2_collector_b_prec_c_fast],
            [self.r2_fork_collector],
            _R2_W_INPUT,
        )

    def r2_relation_bundles(self) -> List[SynapticBundle]:
        return [self.bundle_r1t1_to_r2, self.bundle_r1t2_to_r2]

    def get_all_bundles(self):
        return super().get_all_bundles() + self.r2_relation_bundles()

    def step_r2(self, dt: float = DT):
        """传播一步R2 fork层（在step_rprec()和step_rprec2()之后调用）。"""
        collector_current = 0.0
        for b in self.r2_relation_bundles():
            currents = b.propagate()
            collector_current += (currents[0] if currents else 0.0)
        self.r2_fork_collector.step(collector_current, dt)


# ── R2ForkFinalizer ───────────────────────────────────────────────────────────

@dataclass
class R2ForkFinalizer:
    """监听R2 collector活动，验证共同源资格，生成R2Occurrence。

    执行时序（每步固定）：
      1. circuit.step() + step_rprec() + step_rprec2() + step_r2()
      2. tap_28.observe(t)  只读site28的D1 occurrence
      3. r1_finalizer_t1.step(t)  T1关系闭合
      4. r1_finalizer_t2.step(t)  T2关系闭合
      5. r2_finalizer.step(t)     R2关系闭合（本类）

    共同源核验（评判232255阻塞修正）：
      当R2 collector产生上升沿时，查找最近的T1和T2 RelationOccurrence，
      核验 t1_ro.parent_a_instance_id == t2_ro.parent_a_instance_id，
      即两条关系的"站点28 D1实例"必须是同一个OccurrenceInstanceId。
      若不同（例如T1来自epoch_n而T2来自epoch_m，n≠m），则不生成R2Occurrence。
    """
    r2_collector: Neuron
    r2_collector_address: StructuralAddress
    r1_finalizer_t1: object   # RelationFinalizer实例（T1）
    r1_finalizer_t2: object   # RelationFinalizer实例（T2）

    _was_r2_active: bool = field(default=False, repr=False)
    completed_r2: List[R2Occurrence] = field(default_factory=list)
    _open_r2_drafts: List[dict] = field(default_factory=list, repr=False)
    _registered_r2_keys: set = field(default_factory=set, repr=False)

    def step(self, t_step: int) -> Optional[R2Occurrence]:
        """每步调用一次，返回本步新生成的R2Occurrence（若有），否则None。"""
        r2_active = self.r2_collector.pre_trace > _R2_CLOSE_THRESHOLD

        # R2 collector上升沿检测
        if r2_active and not self._was_r2_active:
            # 共同源核验：取两个finalizer最近的RelationOccurrence各一个
            t1_ro = (self.r1_finalizer_t1.completed_relations[-1]
                     if self.r1_finalizer_t1.completed_relations else None)
            t2_ro = (self.r1_finalizer_t2.completed_relations[-1]
                     if self.r1_finalizer_t2.completed_relations else None)

            if (t1_ro is not None and t2_ro is not None
                    and t1_ro.parent_a_instance_id == t2_ro.parent_a_instance_id):
                # 两条R1的共同起点（站点28的D1实例）是同一个OccurrenceInstanceId
                shared_src = t1_ro.parent_a_instance_id
                r2_key = (RELATION_TYPE_FORK_R2_FAST, shared_src)
                if r2_key not in self._registered_r2_keys:
                    draft = {
                        "shared_src": shared_src,
                        "t1_key": (t1_ro.relation_type, t1_ro.parent_a_instance_id,
                                   t1_ro.parent_b_instance_id, t1_ro.trace_scale),
                        "t2_key": (t2_ro.relation_type, t2_ro.parent_a_instance_id,
                                   t2_ro.parent_b_instance_id, t2_ro.trace_scale),
                        "t_detect": t_step,
                        "r2_key": r2_key,
                    }
                    already_open = any(
                        d["r2_key"] == r2_key for d in self._open_r2_drafts)
                    if not already_open:
                        self._open_r2_drafts.append(draft)

        self._was_r2_active = r2_active

        # 尝试闭合：一旦检测到就立即闭合（R2无需等待进一步rearm）
        newly_closed = None
        still_open = []
        for draft in self._open_r2_drafts:
            ro = R2Occurrence(
                relation_type=RELATION_TYPE_FORK_R2_FAST,
                shared_source_instance_id=draft["shared_src"],
                parent_r1_t1_key=draft["t1_key"],
                parent_r1_t2_key=draft["t2_key"],
                t_detect=draft["t_detect"],
                t_closed=t_step,
                r2_collector_address=self.r2_collector_address,
            )
            self.completed_r2.append(ro)
            self._registered_r2_keys.add(draft["r2_key"])
            newly_closed = ro

        self._open_r2_drafts = still_open  # 全部已闭合（R2无等待期）
        return newly_closed
