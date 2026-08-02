"""nexus_v1.relations.r2_fork.py — P2-C1F：共同源分叉型R2关系（关系-关系生成）。

TYPE:INFRA（R2Occurrence/R2ForkFinalizer）+ BIO（R2ForkCircuit的新bundle）

方案依据：
  document - 2026-08-01T230002.273.md（共同源分叉型路线）
  document - 2026-08-01T232255.527.md（R2层语义+共同源资格必须核验同一OccurrenceInstanceId）
  document - 2026-08-02T164327.921.md（P2-C1F-b：共同源≠瞬时同步，需加R2层trace）

拓扑：
       31
      ↗  (T1: 28≺31的relation_collector)
  28                             → R2 fork collector → R2Occurrence
      ↘  (T2: 28≺23的relation_collector)
       23

评判164327核心修正（P2-C1F-b，阻塞，本轮已执行）：
  最初版本让R2 collector直接AND两路R1 collector的**原始**pre_trace，
  要求两条R1的检测峰在同一采样步瞬时重叠。评判指出这是错误的判据——
  "共同源"要求的是"两条R1的起点是同一个OccurrenceInstanceId"，不是
  "两条R1活动必须瞬时同步"。28≺31（d=1.09）和28≺23（d=1.16）两条通路
  物理距离/响应延迟不同，同一次站点28发生完全可能先形成28≺31、稍后
  形成28≺23，仍是同一共同源分叉，只是检测峰没有瞬时重叠。

  修正：在R2输入侧为两条R1各增加一个短时物理保持痕迹（trace）：
    R1_T1.relation_collector.pre_trace → z_T1^R2（衰减积分器）
    R1_T2.relation_collector.pre_trace → z_T2^R2（衰减积分器）
  R2 collector改为AND门读取z_T1^R2和z_T2^R2（而不是直接读原始collector
  pre_trace）——这正是T1自己检测A≺B时用的"trace+AND门重合"机制（见
  temporal_r_prec.py Q1），只是把它复用到R2层，让两条自然错开的R1活动
  能在R2 trace的衰减窗口内产生物理重叠。不修改T1/T2本身（不改变已冻结
  的R1语义），不搜索HeatSource参数，不放宽R2 collector阈值，不直接读取
  两个RelationOccurrence后创建R2（那是纯软件组合，不经过真实物理链路）。

  两道门的分工（评判164327）：
    物理活动重叠门：R2 collector的trace+AND门（本文件新增，属于ℓ_gen^R2）
    共同父实例谱系门：R2ForkFinalizer核验parent_28^T1 == parent_28^T2
      （原有逻辑不变，已在T-R2F-2验证过拒绝不同epoch的组合）
  前者防止纯软件组合，后者防止把不同epoch的站点28错误绑定。

R2 collector的输入（修正后）：
  z_T1_r2.activation（R1_T1 relation_collector.pre_trace经trace衰减后）
  z_T2_r2.activation（R1_T2 relation_collector.pre_trace经trace衰减后）
两路trace同时在响应带内才触发R2 collector。

共同源资格（评判232255关键修正，仍然有效）：
  ρ_1（T1）的共同起点 = OccurrenceInstanceId(site28, epoch_n)
  ρ_2（T2）的共同起点 = OccurrenceInstanceId(site28, epoch_n)
  两者必须是**同一个**OccurrenceInstanceId，不是相同地址不同epoch。
  由R2ForkFinalizer核验，独立于R2 collector的物理重叠判据。

R2层命名规范（评判232255）：
  D1 = 基础发生
  R1 = 发生-发生关系（现有RelationOccurrence/T1/T2）
  R2 = 关系-关系关系（本文件的R2Occurrence/R2ForkFinalizer）
  不说"D2关系"——D2是旧的D0/D1/D2深度体系，与R1/R2生成层次不是同一维度。

资格目标（第一版P2-C1F）：
  同一个u_{28,n}支撑的两条活跃R1，通过新物理链路（含R2层trace的
  物理重叠窗口）生成共同源型R2，产生非零、双父R1依赖的R2输出
  （不宣称散度/因果树/高阶涌现）。

P2-C1F-d0（评判document - 2026-08-02T173204.373.md，阻塞修正）：
  R2Occurrence成立只证明"两条R1经trace重合触发了R2 collector"，尚未
  定义ℓ_out^R2（R2 collector→下游节点q的真实输出链路）。若直接把
  r2_fork_collector.pre_trace当Y_R2，构成循环证明（AND门被两路输入
  触发，就拿它自己的输出证明"需要两路输入"）。新增R2ForkCircuitPlastic
  （bundle_r2_to_da，同R1Plastic模式），Y_R2(s)=measure_r2_output_current()
  读取这条独立于collector自身状态的局部电流。P2-C1F-d（K_R2不可约与
  切断测试）建立在此之上，本轮只完成d0（定义链路），K_R2测试留待下一步。

RULES.md 强制三问：
  Q1 BIO: R2 trace复用T1自身的trace+AND门重合检测机制（temporal_r_prec.py
     的_trace_config/Q1原文：STDP eligibility trace同一物理原理，"资格
     窗口"部分）——把它应用到R2层：R1_T1/R1_T2各自的检测活动经衰减
     积分后，在窗口内的重合代表"同一次共同源发生的两条分支关系都已
     被确认"。R2 collector是"resolve阶段"（trace仍存活且两路都到达）。
  Q2 物理结构：
     新增2条trace Neuron（z_T1_r2/z_T2_r2）+ 2条frozen bundle
     （T1 collector→trace，T2 collector→trace）+ 2条frozen bundle
     （trace→R2 collector）+ 1个R2 collector Neuron。不新建D1路径，
     不修改T1/T2已有bundle/collector本身。复用CollectorOccurrenceTap +
     OccurrenceIdentityRegistry已有接口。
  Q3 参数：R2 trace/collector参数全部复用T1的_trace_config/_collector_config
     标定值（fast tau=50步）——理由：R2层要处理的时间尺度问题与T1完全
     同构（"两个独立检测事件之间要留多久窗口才算同一次共同源"，同T1的
     "两个站点各自发放之间要留多久窗口才算同一次先后关系"是同一类物理
     问题），故复用同一套已验证常量，不重新标定。
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

# ── R2 trace参数（复用T1 fast trace标定值，见temporal_r_prec.py） ──
_TAU_FAST_STEPS = 50
_R_LEAK_TRACE = 5.0
_TRACE_CAPACITANCE_FAST = _TAU_FAST_STEPS * DT / _R_LEAK_TRACE   # = 0.01
_TRACE_GM = 20.0

# ── R2 collector参数（复用T1标定值） ──
_R2_COLLECTOR_CAPACITANCE = 0.007
_R2_COLLECTOR_R_LEAK = 1.5
_R2_COLLECTOR_V_PEAK = 0.23
_R2_COLLECTOR_THRESHOLD = 0.15
_R2_COLLECTOR_GM = 3.0
_R2_COLLECTOR_TAU_GATE = 2.0

# 评判164327修正：R1 collector → R2 trace 用T1的_W_XI_TO_TRACE(0.3)；
# R2 trace → R2 collector 用T1的_W_TRACE_TO_COLLECTOR(0.5)——两段链路
# 分别对应T1里"xi→trace"和"trace→collector"的同构复用，不是拍脑袋数字。
_R2_W_R1_TO_TRACE = 0.3
_R2_W_TRACE_TO_COLLECTOR = 0.5

RELATION_TYPE_FORK_R2_FAST = "r2.fork.28prec31_and_28prec23"
_R2_CLOSE_THRESHOLD = 1e-4


def _r2_trace_config(label: str) -> NeuronConfig:
    """R2层的物理保持痕迹（评判164327新增）：让两条自然错开的R1检测活动
    能在衰减窗口内产生物理重叠，不要求瞬时同步。复用T1的trace机制
    （非spiking RC leaky integrator），同一物理原理见temporal_r_prec.py Q1。
    """
    return NeuronConfig(
        neuron_id=f"r2_fork_trace_{label}",
        region=0x01,
        spiking=False,
        capacitance=_TRACE_CAPACITANCE_FAST,
        r_leak=_R_LEAK_TRACE,
        inertia=1.0,
        channels=[ChannelConfig(name="default", v_threshold=0.0, gm=_TRACE_GM)],
    )


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

        # ── R2层物理保持痕迹（评判164327修正：让两条自然错开的R1检测
        # 活动在衰减窗口内产生物理重叠，不要求瞬时同步） ──
        self.r2_trace_t1 = Neuron(_r2_trace_config("t1"))
        self.r2_trace_t2 = Neuron(_r2_trace_config("t2"))

        # ── R2 fork collector（AND门，读取两条trace而不是原始collector输出） ──
        self.r2_fork_collector = Neuron(_r2_collector_config())

        # ── bundles: T1/T2 relation_collector → 各自R2 trace ──
        self.bundle_r1t1_to_trace = _frozen_bundle(
            "r2_fork_r1t1_to_trace",
            [self.rprec_collector_a_prec_b_fast],
            [self.r2_trace_t1],
            _R2_W_R1_TO_TRACE,
        )
        self.bundle_r1t2_to_trace = _frozen_bundle(
            "r2_fork_r1t2_to_trace",
            [self.rprec2_collector_b_prec_c_fast],
            [self.r2_trace_t2],
            _R2_W_R1_TO_TRACE,
        )

        # ── bundles: 各自R2 trace → R2 fork collector（AND门重合判据） ──
        self.bundle_trace_t1_to_r2 = _frozen_bundle(
            "r2_fork_trace_t1_to_collector",
            [self.r2_trace_t1],
            [self.r2_fork_collector],
            _R2_W_TRACE_TO_COLLECTOR,
        )
        self.bundle_trace_t2_to_r2 = _frozen_bundle(
            "r2_fork_trace_t2_to_collector",
            [self.r2_trace_t2],
            [self.r2_fork_collector],
            _R2_W_TRACE_TO_COLLECTOR,
        )

    def r2_relation_bundles(self) -> List[SynapticBundle]:
        return [self.bundle_r1t1_to_trace, self.bundle_r1t2_to_trace,
                self.bundle_trace_t1_to_r2, self.bundle_trace_t2_to_r2]

    def get_all_bundles(self):
        return super().get_all_bundles() + self.r2_relation_bundles()

    def step_r2(self, dt: float = DT):
        """传播一步R2 fork层（在step_rprec()和step_rprec2()之后调用）。

        两段传播（评判164327新增的trace中继层）：
          1. R1 collector → R2 trace（各自独立衰减积分，不要求同步）
          2. R2 trace → R2 collector（AND门重合判据，读trace而非原始collector）
        """
        # 段1：R1 collector → 各自trace
        for b, trace_neuron in ((self.bundle_r1t1_to_trace, self.r2_trace_t1),
                                (self.bundle_r1t2_to_trace, self.r2_trace_t2)):
            currents = b.propagate()
            trace_neuron.step(currents[0] if currents else 0.0, dt)

        # 段2：trace → R2 collector（两路求和后一次性注入，同T1 collector的
        # "同一collector多路输入求和"约定，见temporal_r_prec.py step_rprec()）
        collector_current = 0.0
        for b in (self.bundle_trace_t1_to_r2, self.bundle_trace_t2_to_r2):
            currents = b.propagate()
            collector_current += (currents[0] if currents else 0.0)
        self.r2_fork_collector.step(collector_current, dt)


class R2ForkCircuitPlastic(R2ForkCircuit):
    """`R2ForkCircuit` + ℓ_out^R2（R2 collector → DA的可塑bundle）。

    评判173204阻塞修正（P2-C1F-d0）：R2Occurrence只证明了"两条R1的检测
    活动经trace重合后触发了R2 collector"，尚未证明"这个共同源关系向下游
    产生了真实的、可独立测量的局部作用"。直接把r2_fork_collector.pre_trace
    当作Y_R2会构成循环证明（AND门被两路输入触发，就拿它自己的输出证明
    "两路输入触发了AND门"，未验证任何独立于collector自身状态的事实）。

    本类新增ℓ_out^R2：r2_fork_collector → DA（STDP可塑，同R1Plastic的
    bundle_rprec_to_da模式）。Y_R2(s)读取这条bundle的propagate()输出——
    是collector下游、独立于collector自身pre_trace的局部电流，才是合法
    的R2层输出量。

    子类叠加（同RPrecCircuitT1Plastic先例），不修改R2ForkCircuit本身。
    """

    def __init__(self):
        super().__init__()

        # 复用RPrecCircuitT1Plastic（temporal_r_prec_plastic.py）已验证的
        # 三因子STDP常量，不重新标定（同一种机制，见该文件Q1/Q3）。
        _INITIAL_WEIGHT = 0.1
        _WEIGHT_MAX = 0.3
        _STDP_LR = 0.005
        _ELIGIBILITY_TAU = 300.0
        _SYNAPSE_GAIN = 0.2
        _REMODEL_COST_KAPPA = 0.001

        da_list = list(self.da_neurons.values())
        cfg = BundleConfig(
            bundle_id="r2_fork_collector_to_da",
            learning_rule="stdp",
            use_eligibility_trace=True,
            eligibility_tau=_ELIGIBILITY_TAU,
            initial_weight=_INITIAL_WEIGHT,
            weight_max=_WEIGHT_MAX,
            stdp_lr=_STDP_LR,
            synapse_gain=_SYNAPSE_GAIN,
            bundle_role="feedforward",
            remodel_cost_kappa=_REMODEL_COST_KAPPA,
        )
        # ℓ_out^R2的具体载体：R2 collector → DA（STDP可塑）。
        self.bundle_r2_to_da = SynapticBundle(cfg, [self.r2_fork_collector], da_list)

    def measure_r2_output_current(self) -> List[float]:
        """读取ℓ_out^R2对DA池的局部突触电流——P2-C1F-d的Y_R2(s)读出接口。

        不是r2_fork_collector.pre_trace（那是collector自身状态，直接拿来
        当Y_R2会构成循环证明，见评判173204）。propagate()只读当步电流，
        不驱动/不学习——调用方应在step_r2()之后调用。
        """
        return self.bundle_r2_to_da.propagate()

    def step_r2_plastic(self, dt: float, da_concentration: float,
                        fill_fraction: float = 1.0) -> None:
        self.step_r2(dt)
        currents = self.bundle_r2_to_da.propagate()
        for i, tgt in enumerate(self.bundle_r2_to_da.targets):
            tgt.step(currents[i] if i < len(currents) else 0.0, dt)
        self.bundle_r2_to_da.learn(
            dt=dt, fill_fraction=fill_fraction, da_concentration=da_concentration)
        self.bundle_r2_to_da.compute_xin(dt)


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
    # R2 collector上升沿的候选时刻，等待T1/T2都产生RelationOccurrence后
    # 才转为正式draft（见step()方法文档：两者时间尺度不同，不能同刻核验）。
    _pending_since: Optional[int] = field(default=None, repr=False)

    def step(self, t_step: int) -> Optional[R2Occurrence]:
        """每步调用一次，返回本步新生成的R2Occurrence（若有），否则None。

        实测发现（评判164327落地时定位）：R2 collector的AND门在T1/T2的
        relation_collector各自越阈后很快就上升沿（本轮实测t=564），
        但T1/T2的正式RelationOccurrence要等父D1 occurrence完成完整的
        rearm延迟（rearm_min_steps=500，见occurrence.py）才闭合（本轮
        实测T1 t_closed=1289，T2 t_closed=1559）——R2 collector的物理
        重叠窗口和T1/T2从检测到闭合所需时间是两个完全不同的时间尺度，
        不是"瞬时同步"问题。因此R2共同源核验改为：R2 collector上升沿时
        只记录候选（open draft），持续检查直到T1和T2**都**产生了正式
        RelationOccurrence后再做共同源核验并闭合——类比RelationFinalizer
        本身"draft等待父occurrence rearm"的既定模式（relation_occurrence.py），
        不是本模块特例发明的新机制。
        """
        r2_active = self.r2_collector.pre_trace > _R2_CLOSE_THRESHOLD

        # R2 collector上升沿：记录候选（不在此刻做共同源核验，
        # 因为T1/T2的RelationOccurrence可能尚未闭合）
        if r2_active and not self._was_r2_active:
            if not self._open_r2_drafts:  # 避免同一物理重叠窗口内重复挂起候选
                self._pending_since = t_step
        self._was_r2_active = r2_active

        # 每步检查：T1和T2是否都已产生RelationOccurrence，若是则核验共同源
        if self._pending_since is not None:
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
                        "t_detect": self._pending_since,  # R2 collector真实上升沿时刻
                        "r2_key": r2_key,
                    }
                    already_open = any(
                        d["r2_key"] == r2_key for d in self._open_r2_drafts)
                    if not already_open:
                        self._open_r2_drafts.append(draft)
                        self._pending_since = None  # 已转为draft，清空候选态

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
