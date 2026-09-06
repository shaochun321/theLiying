"""tss.relations.r1_structure — P2-B1X2a：R1最小结构块定义。

TYPE:INFRA — 纯类型定义，不新建Neuron/SynapticBundle，不执行神经动力学。

方案依据：
  `cell-cell/交叉比对/document - 2026-07-31T205641.086.md`（P2-B1X2路线重写）
  `cell-cell/交叉比对/document - 2026-07-31T221144.140.md`（核心修正：ℓ_gen≠ℓ_out）
  `cell-cell/交叉比对/document - 2026-08-01T030645.402.md`（X2a'：ℓ_out移出R1本体）

评判030645核心修正（阻塞，本轮已执行）：
  X2a首版把ℓ_out设为R1StructureBlock的可选字段（Optional[R1OutputLink]），
  但这仍把"关系是否存在"和"关系是否已能向下游施力"放在同一个类里共享
  身份边界——没有bundle_rprec_to_da的普通RPrecCircuitT1，不应该因此"没有
  R1"。评判要求彻底拆成两个类：
    R1StructureBlock：本体，只含κ_A/κ_B/ℓ_gen/区间/耦合轨迹，不含ℓ_out
    R1OutputBinding：R1StructureBlock + ℓ_out + 下游目标 + measure_output_current()
  R1本体回答"A、B是否通过真实生成链路形成了关系"；R1OutputBinding回答
  "这个已经形成的关系能否向下游施力"——两个问题分属两个对象，不共享类。

评判221144核心修正（ℓ_gen≠ℓ_out的最初区分）：
  P2-B1X1e工作报告曾将"关系生成链路"和"关系输出链路"混写成一条。
  本文件按评判要求严格区分：

    ℓ_gen（关系生成链路）：A、B基元如何形成关系
      = A的trace/衰减结构 + B的当前发生输入 + 两者重合结构 + relation collector
      对应代码：rprec_xi_a → rprec_trace_a_fast/slow → rprec_collector_a_prec_b_fast
               rprec_xi_b(raw) → rprec_collector_a_prec_b_fast

    ℓ_out（关系输出链路）：已形成的关系如何向下游产生作用
      = relation collector → 下游目标节点
      对应代码：rprec_collector_a_prec_b_fast → bundle_rprec_to_da → DA neurons
               （仅在RPrecCircuitT1Plastic子类中存在）

  完整结构层次：
    κ_A^10, κ_B^10 —[ℓ_gen]→ ρ_AB —[ℓ_out]→ q（下游节点）

  两个切割测试分开定义（P2-B1X2c）：
    K_gen：切断ℓ_gen后relation collector是否失去活动，RelationOccurrence不再产生
    K_out：切断ℓ_out后下游Y是否消失（在R1已形成的前提下）

评判030645阻塞修正：ℓ_out不属于R1本体的必需字段。
  R1StructureBlock（本体）只含κ_A^10/κ_B^10/ℓ_gen/区间——"A、B是否形成了
  关系"不应依赖"关系是否已能向下游施力"。没有bundle_rprec_to_da的普通
  RPrecCircuitT1，只要ℓ_gen真实检测到A≺B，R1本体依然成立。
  ℓ_out相关内容独立成R1OutputBinding类（R1本体 + ℓ_out + 下游节点q +
  Y_q读出），只在RPrecCircuitT1Plastic场景下才能构造。

κ^10基元（十神经元基元）的工程映射（评判221144提醒必须明确到代码对象）：
  以site_a（thermptXX_warm）为例：
    L1（输入端口，唯一外周驱动接口）：
      thermal_quantum_l1_warm[pid]  ← ThermalDeltaNeuron，读 SkinPatch.dT
    L2（热觉毛细胞，HH等效）：
      thermal_quantum_hc_warm[pid]
    10 ensemble神经元（阶梯阈值温度计编码）：
      thermal_quantum_ensembles[f"{pid}_warm"]  ← List[Neuron]，长度=10
    AND-门 collector（输出端口，下游读此的pre_trace）：
      thermal_quantum_collectors[f"{pid}_warm"]  ← Neuron(spiking)
    内部bundle（基元内部，不参与关系生成）：
      bundles_thermal_quantum_l1_to_hc[...]   L1→HC
      bundles_thermal_quantum_in[...]          HC→ensemble(10)
      bundles_thermal_quantum_collect[...]     ensemble(10)→collector

  trace和relation collector属于ℓ_gen，不属于κ^10内部：
      rprec_trace_a_fast/slow           ← ℓ_gen的衰减积分器
      rprec_collector_a_prec_b_fast     ← ℓ_gen的重合检测输出（AND门）

RULES.md 强制三问：
  Q1 生物对应物：本模块无BIO对应物——纯INFRA类型定义，类比
     structural_address.py/occurrence.py的身份管理层。被包装的神经元/
     bundle的BIO对应物见各自构造函数的REF标注（variant_adapter.py中的
     _thermal_quantum_ensemble_config等）。
  Q2 物理结构：只持有已有对象的引用，不新建Neuron/SynapticBundle，
     不调用任何改变神经元状态的方法。
  Q3 参数依据：无物理参数（INFRA类型定义层）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple

from nexus_v1.components.neuron import Neuron
from nexus_v1.circuit.bundle import SynapticBundle
from nexus_v1.components.structural_address import GeneratedAddress, StructuralAddress
from ..generators.occurrence import OccurrenceInstanceId


# ── 关系生成链路类型常量 ──
LINK_TYPE_RPREC_FAST = "r_prec.fast_trace_and_gate"
LINK_TYPE_RPREC_SLOW = "r_prec.slow_trace_and_gate"

# ── 区间退出阈值（collector pre_trace跌落至此以下视为链路支撑消失） ──
_DEFAULT_INTERVAL_EXIT_THRESHOLD = 1e-4


@dataclass(frozen=True)
class KappaTen:
    """κ^10：以十神经元ensemble为最低功能核心的基础生成元（一个站点的温感量子元通路）。

    评判030645非阻塞澄清（"十"指什么）：
      κ^10 = (B_in, C^10, S_dyn, B_out)，即：
        C^10（不可约核心）  = ensemble中的10个神经元——最低功能规模
        B_in（输入边界）    = l1
        S_dyn（支持动力学） = hc
        B_out（输出边界）   = collector
      "十"描述核心的最小功能规模，不是整个物理装置的总元件数（l1/hc/
      collector都是维持该核心作为完整生成元工作所需的支撑结构，"不可约"
      指核心实现的最低项目功能不可再拆，不是说l1/hc/collector可以从
      实际运行结构中删除）。collector属于生成元整体，但不属于十神经元
      核心本身——这与ℓ_gen读取collector.pre_trace（输出端口，不是核心
      内部信号）的约定一致。

    对应代码：
      variant_adapter.py 中 `_init_quantum_thermal_pathways` 对每个站点
      (site_index, polarity) 构建的五层结构。

    工程映射（以site_index=28, polarity="warm"为例）：
      pid = f"thermpt{site_index}"
      label = f"{pid}_{polarity}"

      l1        = circuit.thermal_quantum_l1_warm[pid]
      hc        = circuit.thermal_quantum_hc_warm[pid]
      ensemble  = circuit.thermal_quantum_ensembles[label]   # List[Neuron], len=10
      collector = circuit.thermal_quantum_collectors[label]  # 输出端口

    外部接口约定：
      输入端口：l1（唯一合法驱动接口，via SkinPatch.dT → L1.step()）
      输出端口：collector.pre_trace（下游关系生成链路读此信号）
      内部组件（不暴露给关系层，不参与ℓ_gen）：hc, ensemble, 内部bundles
    """
    # 结构身份
    site_index: int
    polarity: str      # "warm" | "cool"

    # 组件引用（只读，由构造函数填入，不拥有驱动权）
    l1: Neuron         # 输入端口：ThermalDeltaNeuron，读SkinPatch.dT
    hc: Neuron         # L2热觉毛细胞（HH等效）
    ensemble: Tuple[Neuron, ...]   # 10个ensemble神经元（阶梯阈值）
    collector: Neuron  # 输出端口：AND门collector，downstream读.pre_trace

    # 结构地址（回指D0物理支撑）
    address: StructuralAddress     # skin.patch:thermptXX

    def __post_init__(self):
        if len(self.ensemble) != 10:
            raise ValueError(
                f"KappaTen({self.site_index},{self.polarity}): "
                f"ensemble必须恰好10个神经元，实际={len(self.ensemble)}")


@dataclass(frozen=True)
class RelationGenLink:
    """ℓ_gen：关系生成链路——A和B基元如何形成时序关系。

    对应代码（以a_prec_b_fast为例，temporal_r_prec.py）：
      trace_a:        circuit.rprec_trace_a_fast
      collector:      circuit.rprec_collector_a_prec_b_fast
      bundles_gen:    [
          rprec_xi_a_to_trace_fast   (xi_a.pre_trace → trace_a)
          rprec_trace_a_fast_to_col  (trace_a.activation → collector)
          rprec_raw_xi_b_to_col_fast (xi_b.pre_trace → collector)
      ]

    注意：这里xi_a/xi_b是κ_A^10/κ_B^10的collector（输出端口），
    不是trace或ensemble——ℓ_gen读取两个基元的输出信号，不修改基元内部。

    评判221144关键约定：
      ℓ_gen负责"A和B怎样形成关系"，不负责"关系向下游产生作用"。
      relation collector的pre_trace上升代表关系检测到，但关系向下游的
      作用由ℓ_out（R1OutputLink）负责，两者不能混为同一链路。

    `link_type` vs `relation_type`（P2-B1X2b新增字段时发现的真实区分，
    不是拍脑袋加字段）：
      link_type     = 链路**机制**类型（"用fast trace+AND门检测"，
                      LINK_TYPE_RPREC_FAST/SLOW，描述ℓ_gen本身怎么实现）
      relation_type = 链路**检测到的语义关系**类型（"A先于B"，
                      relation_occurrence.RELATION_TYPE_A_PREC_B_FAST，
                      描述ℓ_gen的输出代表什么关系事实）
      两者不能混用：同一个relation_type理论上可以用不同link_type检测
      （fast/slow trace是同一关系的两种时间尺度探测器），反之同一
      link_type机制（AND门重合）也可能检测不同方向的relation_type
      （a_prec_b vs b_prec_a，即当前代码里对称的两组collector）。
      P2B1X2b写project_to_relation_occurrence_fields()时如果直接拿
      link_type去填RelationOccurrence.relation_type，会把"用什么方法
      检测"和"检测到什么"两个不同概念混进同一个字段——这正是评判
      221144本想避免的"两条链路混成一条"问题在字段级的重演，因此
      单独补充本字段，不复用link_type。
    """
    link_type: str      # LINK_TYPE_RPREC_FAST / LINK_TYPE_RPREC_SLOW（机制）
    relation_type: str  # RELATION_TYPE_A_PREC_B_FAST等（语义关系，见relation_occurrence.py）
    trace_scale: str    # "fast" | "slow"

    # trace神经元（衰减积分器）
    trace_a: Neuron
    trace_b: Neuron

    # 关系collector（重合检测输出，也是ℓ_gen的最终节点）
    relation_collector: Neuron

    # ℓ_gen内部的bundles（只读引用，不拥有传播权）
    bundles: Tuple[SynapticBundle, ...]

    # 评判040602核心修正：collector地址与生成链路地址是两个不同概念，
    # 不能像relation_type/link_type那样再次混用：
    #   generation_link_address：标识整条ℓ_gen（trace+bundle+collector的组合）
    #   collector_address      ：标识relation_collector这一个检测节点本身
    # Neuron对象本身不带StructuralAddress（只有.id/.config），因此
    # collector_address必须由构造方显式提供，不能从
    # relation_collector.address这类不存在的属性读取。
    generation_link_address: StructuralAddress
    collector_address: StructuralAddress


@dataclass(frozen=True)
class R1OutputLink:
    """ℓ_out：关系输出链路——已形成的关系如何向下游节点产生作用。

    对应代码（RPrecCircuitT1Plastic，temporal_r_prec_plastic.py）：
      source:  rprec_collector_a_prec_b_fast（ℓ_gen的输出，ℓ_out的输入）
      bundle:  bundle_rprec_to_da（STDP可塑，学习门控在此层）
      targets: circuit.da_neurons.values()（DA池节点）

    与ℓ_gen的关系：
      source == ℓ_gen.relation_collector（同一个神经元对象，衔接两段链路）

    评判221144约定：
      Y_c(s) = I_{ρ→q,c}^local(s) 读取的是这条链路对下游节点的局部电流，
      即 bundle_rprec_to_da.propagate() 返回值——不是relation collector本身
      的活动（那是循环证明），也不是DA池全局平均电位。

    注意：ℓ_out仅在RPrecCircuitT1Plastic里存在。
    RPrecCircuitT1基类只有ℓ_gen（检测），没有ℓ_out（输出到下游）。
    P2-B1X2c实验需使用RPrecCircuitT1Plastic构建场景。
    """
    # 源节点（= ℓ_gen的relation_collector，衔接两段链路）
    source_collector: Neuron

    # 出口bundle（STDP可塑，learning发生在此）
    output_bundle: SynapticBundle

    # 下游目标节点（DA池）
    target_neurons: Tuple[Neuron, ...]

    # 出口链路地址
    link_address: StructuralAddress

    # 主读出接口（P2-B1X2c测量用）
    def measure_local_current(self) -> List[float]:
        """读取ℓ_out对下游目标节点的局部突触电流（不驱动，只读当步propagate结果）。

        注意：propagate()会根据source_collector的当前pre_trace计算电流，
        但不调用target_neurons的step()——测量是只读操作，不能进入执行回路。
        调用方负责在circuit.step_rprec()之后、不修改神经元状态时读取。
        """
        return self.output_bundle.propagate()


@dataclass
class R1PhysicalInterval:
    """R1本体区间 I_R1 = [s_candidate, s_enter, s_support_end, s_closed]。

    评判040602修正：区分R1PhysicalInterval（I_R1）与R1MeasurementWindow（W_Y*）。
    评判045235阻塞修正：RELAXING必须允许恢复到SUPPORTED（同一谱系内振荡=同一区间），
      并加迟滞阈值（θ_on > θ_off）和最短持续步数防止数值抖动触发状态切换。

    状态机（评判045235修正版）：
      UNBOUND：尚未满足进入条件
      SUPPORTED ⇄ RELAXING：双向——物理支撑短暂退出再恢复属同一区间
      CLOSED：残响彻底归零，且lineage_broken或正式满足关闭条件

    双向条件（评判045235）：
      RELAXING→SUPPORTED（只有在以下条件同时满足时允许）：
        1. lineage_broken == False（父epoch和generation_link_address均未改变）
        2. both_supported AND collector_in_band（物理支撑重新进入响应带）
        3. 尚未满足正式关闭条件

      一旦lineage_broken=True（父epoch变化），RELAXING只能走向CLOSED，不能恢复。

    迟滞与持续步数（评判045235非阻塞，已实现为可配置参数）：
      θ_on > θ_off：进入阈值 > 退出阈值，消除单点抖动
      m_on：进入SUPPORTED需要连续满足条件的步数（默认1，可配置）
      m_off：进入RELAXING需要连续不满足条件的步数（默认1，可配置）
      m_close：封闭需要trace+collector同时在基线带内的连续步数（默认1，可配置）

    候选时刻（评判045235非阻塞，已实现）：
      s_candidate：两个父发生第一次同时开始支撑ℓ_gen的时刻（s_candidate ≤ s_enter）
      s_enter：    R1取得成立资格（collector也进入响应带）
      s_support_end：主共同支撑解除（可多次更新，取最后一次SUPPORTED→RELAXING）
      s_closed：   残响结束、区间正式关闭

    关于区间的不变性：
      - R1区间由（parent_a_epoch_at_enter, parent_b_epoch_at_enter）定义谱系
      - 同一谱系内的振荡/短暂失配归属同一区间
      - 一旦父epoch改变（lineage_broken），旧区间不能恢复——新epoch开启新候选
    """
    # ── 迟滞阈值（θ_on > θ_off 消除抖动） ──
    threshold_on: float = 1e-3   # 进入SUPPORTED所需的信号强度（较高）
    threshold_off: float = 1e-4  # 进入RELAXING的信号强度（较低，评判045235迟滞）

    # ── 持续步数 ──
    m_on: int = 1     # 进入SUPPORTED需连续满足条件的步数（最小1）
    m_off: int = 1    # 进入RELAXING需连续不满足条件的步数
    m_close: int = 1  # 封闭需trace+collector同时在基线带内的连续步数

    # ── 时刻记录 ──
    s_candidate: Optional[int] = None     # 两父首次共同支撑的时刻（候选阶段起点）
    s_enter: Optional[int] = None         # 首次满足完整进入条件的时刻（R1正式成立）
    s_support_end: Optional[int] = None   # 最近一次SUPPORTED→RELAXING的时刻
    s_closed: Optional[int] = None        # 区间正式封闭时刻

    # ── 谱系锁（评判045235）──
    lineage_broken: bool = field(default=False)  # 父epoch改变后置True，禁止RELAXING→SUPPORTED

    # ── 状态 ──
    _state: "_R1IntervalState" = field(default=None, repr=False)

    # ── 内部持续计数器 ──
    _on_count: int = field(default=0, repr=False)   # 连续满足进入条件的步数
    _off_count: int = field(default=0, repr=False)  # 连续不满足退出条件的步数
    _close_count: int = field(default=0, repr=False)  # 连续满足封闭条件的步数

    def __post_init__(self):
        if self._state is None:
            object.__setattr__(self, '_state', _R1IntervalState.UNBOUND)
        if self.threshold_on <= self.threshold_off:
            raise ValueError(
                f"R1PhysicalInterval: threshold_on({self.threshold_on}) "
                f"must be > threshold_off({self.threshold_off})")

    @property
    def state(self) -> "_R1IntervalState":
        return self._state

    @property
    def is_active(self) -> bool:
        """区间已进入但尚未封闭（SUPPORTED或RELAXING）。"""
        return self._state in (_R1IntervalState.SUPPORTED, _R1IntervalState.RELAXING)

    @property
    def is_closed(self) -> bool:
        return self._state is _R1IntervalState.CLOSED

    @property
    def is_defined(self) -> bool:
        return self.s_enter is not None

    @property
    def duration(self) -> Optional[int]:
        if self.s_enter is not None and self.s_closed is not None:
            return self.s_closed - self.s_enter
        return None

    def update(
        self,
        t_step: int,
        support_a: float,
        support_b: float,
        collector_activity: float,
        parent_a_epoch: int,
        parent_b_epoch: int,
        _parent_a_epoch_at_enter: Optional[int] = None,
        _parent_b_epoch_at_enter: Optional[int] = None,
    ) -> "_R1IntervalState":
        """推进区间状态机一步，返回当前状态。

        不直接访问Neuron对象，由调用方传入信号读数。
        支持RELAXING→SUPPORTED双向恢复（同一谱系内振荡=同一区间）。
        """
        both_on = (support_a > self.threshold_on and
                   support_b > self.threshold_on and
                   collector_activity > self.threshold_on)

        both_off = (support_a < self.threshold_off or
                    support_b < self.threshold_off or
                    collector_activity < self.threshold_off)

        at_baseline = (support_a <= self.threshold_off and
                       support_b <= self.threshold_off and
                       collector_activity <= self.threshold_off)

        parent_changed = (
            _parent_a_epoch_at_enter is not None and
            (_parent_a_epoch_at_enter != parent_a_epoch or
             _parent_b_epoch_at_enter != parent_b_epoch)
        )

        if parent_changed and not self.lineage_broken:
            self.lineage_broken = True

        # 候选阶段：两父支撑超过off阈值（低门槛），记录s_candidate
        both_candidate = (support_a > self.threshold_off and
                          support_b > self.threshold_off)
        if self.s_candidate is None and both_candidate:
            self.s_candidate = t_step

        if self._state is _R1IntervalState.UNBOUND:
            if both_on:
                self._on_count += 1
                if self._on_count >= self.m_on:
                    self.s_enter = t_step
                    self._on_count = 0
                    object.__setattr__(self, '_state', _R1IntervalState.SUPPORTED)
            else:
                self._on_count = 0

        elif self._state is _R1IntervalState.SUPPORTED:
            if self.lineage_broken or both_off:
                self._off_count += 1
                if self._off_count >= self.m_off:
                    self.s_support_end = t_step
                    self._off_count = 0
                    object.__setattr__(self, '_state', _R1IntervalState.RELAXING)
            else:
                self._off_count = 0

        elif self._state is _R1IntervalState.RELAXING:
            # 评判045235阻塞修正：允许恢复到SUPPORTED（同一谱系，支撑重建）
            if not self.lineage_broken and both_on:
                self._on_count += 1
                self._close_count = 0
                if self._on_count >= self.m_on:
                    self._on_count = 0
                    object.__setattr__(self, '_state', _R1IntervalState.SUPPORTED)
            elif at_baseline:
                self._close_count += 1
                self._on_count = 0
                if self._close_count >= self.m_close:
                    self.s_closed = t_step
                    object.__setattr__(self, '_state', _R1IntervalState.CLOSED)
            else:
                self._on_count = 0
                self._close_count = 0

        return self._state


class _R1IntervalState(Enum):
    """R1区间内部状态，不直接暴露——调用方通过R1PhysicalInterval.state读取。"""
    UNBOUND = auto()    # 尚未获得两父实例共同支撑
    SUPPORTED = auto()  # 双父支撑中，collector在响应带内
    RELAXING = auto()   # 支撑已暂时解除，残响归属本区间（可恢复至SUPPORTED）
    CLOSED = auto()     # 区间正式封闭，后续残响另开新区间


@dataclass
class R1MeasurementWindow:
    """Y测量统一窗口 W_Y* = [s_start, s_end]。

    评判040602修正：X2c的反事实实验不能让每个条件（∅/A/B/AℓB/cut）
    各自使用不同长度/不同起点的区间——那样比较的是不同物理过程的量纲
    不可比的数字。

    正确做法：
      1. 先运行完整条件AℓB；
      2. 从这次真实物理过程得到 I_R1^{AℓB}；
      3. 再观察ℓ_out的电流何时回到基线带，得到s_relax^Y；
      4. W_Y* = [I_R1^{AℓB}.s_enter, s_relax^Y]；
      5. 对所有反事实条件（∅/A/B/gen-cut/out-cut）使用完全相同的W_Y*。

    W_Y*由完整物理过程后验产生，不是硬编码固定窗口。

    W_Y* ≥ I_R1 的原因：R1本体不含ℓ_out，ℓ_out的电流尾部可能在
    s_closed^R1之后仍未归零（s_closed^R1 ≤ s_relax^Y），
    所以需要专门跟踪ℓ_out电流的归零时刻。

    字段：
      reference_r1_interval_id：产生本窗口的R1区间标识符（供追溯）
      s_start：窗口起点（= I_R1^{AℓB}.s_enter）
      s_end：窗口终点（= s_relax^Y，ℓ_out电流归零后首步）
      baseline_band：Y基线带上界（|Y|< baseline_band时视为归零）
      target_address：Y的下游目标节点地址（对应R1OutputLink.target_neurons之一）
    """
    s_start: int
    s_end: int
    baseline_band: float
    target_address: StructuralAddress
    reference_r1_interval_id: Optional[str] = None   # 回指产生本窗口的R1实例

    def __post_init__(self):
        if self.s_start >= self.s_end:
            raise ValueError(
                f"R1MeasurementWindow: s_start({self.s_start}) >= s_end({self.s_end})，"
                f"窗口必须有正长度")

    @property
    def length(self) -> int:
        return self.s_end - self.s_start

    def contains(self, t_step: int) -> bool:
        return self.s_start <= t_step <= self.s_end

    @staticmethod
    def from_r1_run(
        r1_interval: "R1PhysicalInterval",
        y_trajectory: List[float],
        y_start_step: int,
        baseline_band: float,
        target_address: StructuralAddress,
        reference_r1_interval_id: Optional[str] = None,
    ) -> "R1MeasurementWindow":
        """从AℓB完整运行的结果后验构造统一测量窗口。

        y_trajectory：从y_start_step开始的Y(s)轨迹（即ℓ_out局部电流轨迹）。
        返回的窗口起点 = r1_interval.s_enter，
        终点 = Y轨迹中最后一个|Y| > baseline_band的步骤后一步（确保尾部被包含）。

        Y全程为零时（ℓ_out从未激活），以r1_interval.s_closed为终点。
        """
        if not r1_interval.is_defined:
            raise ValueError("R1MeasurementWindow.from_r1_run: r1_interval.s_enter未设定")

        # 找Y轨迹中最后一个超过基线带的步骤
        s_relax_y = r1_interval.s_closed  # 默认fallback：R1本身已封闭
        for i in range(len(y_trajectory) - 1, -1, -1):
            if abs(y_trajectory[i]) > baseline_band:
                # s_relax_y = 最后超阈步骤 + 1（首个回到基线的步骤）
                s_relax_y = y_start_step + i + 1
                break

        s_end = s_relax_y if s_relax_y is not None else (r1_interval.s_enter + len(y_trajectory))
        s_end = max(s_end, r1_interval.s_enter + 1)  # 窗口至少长度1

        return R1MeasurementWindow(
            s_start=r1_interval.s_enter,
            s_end=s_end,
            baseline_band=baseline_band,
            target_address=target_address,
            reference_r1_interval_id=reference_r1_interval_id,
        )


@dataclass
class R1StructureBlock:
    """R1本体：两个不可约基础结构通过真实生成链路在物理驱动区间内形成的耦合块。

    评判030645阻塞修正：本体**不含**ℓ_out——"关系是否存在"不应依赖"关系
    是否已能向下游施力"。没有bundle_rprec_to_da的普通RPrecCircuitT1，
    只要ℓ_gen真实检测到A≺B，R1本体依然成立。ℓ_out相关字段/方法已移至
    独立的 `R1OutputBinding` 类（见下）。

    评判205641定义：

        R1_AB[I] = (κ_A^10, κ_B^10, ℓ_gen, I, Γ_AB^I)

    其中：
      κ_A^10, κ_B^10：两个不可约基础结构（十神经元基元）
      ℓ_gen：使两者发生耦合的关系生成结构
      I：该耦合保持同一谱系的物理区间
      Γ_AB^I：区间内完整耦合轨迹（P2-B1X2c测量）

    身份：
      R1实例身份 = (parent_a_instance_id, parent_b_instance_id,
                    generation_link_address, interval_identity)
      其中interval_identity在X2d实现前暂用s_enter标识。

    去重规则（P2-B1X1e当前实现在RelationFinalizer._registered_keys）：
      同一父实例对、同一生成链路地址、同一区间，只产生一个R1实例。
      X2d完成后去重键可扩展为(parent_A, parent_B, ℓ_gen.generation_link_address, I)。
    """
    # ── 基元 ──
    kappa_a: KappaTen   # 基础结构A（十神经元基元）
    kappa_b: KappaTen   # 基础结构B

    # ── 关系生成链路（A和B怎样形成关系） ──
    link_gen: RelationGenLink

    # ── 物理区间（P2-B1X2d补全） ──
    interval: R1PhysicalInterval = field(default_factory=R1PhysicalInterval)

    # ── 谱系回指 ──
    # 两个父D1实例身份（与RelationOccurrence.parent_{a,b}_instance_id对应）
    parent_a_instance_id: Optional[OccurrenceInstanceId] = None
    parent_b_instance_id: Optional[OccurrenceInstanceId] = None

    # ── R1实例身份（待X2d填入完整区间标识符） ──
    r1_id: Optional[str] = None   # 暂用字符串占位，X2d替换为专用类型

    @property
    def relation_collector(self) -> Neuron:
        """快捷访问关系collector（ℓ_gen的输出端，也是R1OutputBinding.ℓ_out的输入端）。"""
        return self.link_gen.relation_collector


@dataclass
class R1OutputBinding:
    """R1输出资格：已形成的R1本体，绑定一条输出链路后能否向下游节点施力。

    评判030645定义（修正后）：

        Q_out = (R1_AB, ℓ_out, q, Y_q)

    它回答"这个已经形成的R1，能否沿某条出口链路对下游产生真实作用"——
    与R1本体是否成立（"A、B是否形成了关系"）是完全不同的问题，故不共享
    同一个类/身份边界。仅当R1本体所在的circuit是RPrecCircuitT1Plastic
    （或其他挂了ℓ_out的子类）时才能构造本类；RPrecCircuitT1基类的R1本体
    没有对应的R1OutputBinding，这是合法状态，不是"R1不完整"。

    评判221144约定：
      Y_c(s) = I_{ρ→q,c}^local(s) 读取的是ℓ_out对下游节点的局部电流，
      即 output_link.measure_local_current() 的返回值——不是relation
      collector本身的活动（那是循环证明），也不是DA池全局平均电位。
    """
    r1: R1StructureBlock       # 已形成的R1本体（不含ℓ_out）
    output_link: R1OutputLink  # 关系输出链路ℓ_out

    def __post_init__(self):
        if self.output_link.source_collector is not self.r1.relation_collector:
            raise ValueError(
                "R1OutputBinding: output_link.source_collector必须是"
                "r1.relation_collector同一对象（ℓ_gen与ℓ_out的衔接点），"
                "不能是不同的collector")

    def measure_output_current(self) -> List[float]:
        """读取ℓ_out对下游目标节点的局部突触电流（P2-B1X2c测量Y_c(s)用）。

        调用方应在circuit.step_rprec()之后调用，不能在circuit.step()前。
        """
        return self.output_link.measure_local_current()


def project_to_relation_occurrence_fields(
    r1: R1StructureBlock, t_detect: int, t_closed: int,
    occurrence_a_address: GeneratedAddress, occurrence_b_address: GeneratedAddress,
) -> dict:
    """P2-B1X2b：R1本体 → RelationOccurrence字段的显式投影映射 Π_τ(R1_AB[I])。

    评判205641/030645要求把`RelationOccurrence`重新定型为"R1本体在时间尺度
    上的一次投影"，而不是删除或修改现有`RelationOccurrence`类。本函数是
    这个投影关系的**可验证**版本——给定一个已构造的R1本体，返回构造一个
    对应`RelationOccurrence`所需的全部字段，字段来源全部可回指到R1本体：

      relation_type    ← r1.link_gen.relation_type（ℓ_gen检测到的语义关系，
                         不是link_type——两者区分见RelationGenLink docstring）
      parent_a/b       ← r1.parent_a/b_instance_id（同一个身份对象，非复制新值）
      collector_address← r1.link_gen.collector_address（评判040602修正：
                         relation collector这一个检测节点本身的地址，不是
                         generation_link_address——后者标识整条ℓ_gen，
                         RelationOccurrence.collector_address字段语义上
                         指"哪个collector产生了这次检测"，应对应前者）
      trace_scale      ← r1.link_gen.trace_scale

    调用方（如`RelationFinalizer`，P2-B1X2d/c完成后）可用本函数的返回值
    构造`RelationOccurrence(**project_to_relation_occurrence_fields(...),
    t_detect=..., t_closed=..., occurrence_a_address=..., occurrence_b_address=...)`，
    使"RelationOccurrence的字段确实是R1本体的时间投影"这件事从文档断言
    变成代码层可检验的事实（见`test_r1_structure.py::test_r1s_5_*`）。

    本函数不修改`RelationFinalizer`当前生产路径（仍直连字段赋值，见
    `relation_occurrence.py`），只提供投影关系的显式表达，供P2-B1X2c/d
    在需要时复用，避免两处各自维护一份"哪个字段对应哪个"的隐式约定。
    """
    if r1.parent_a_instance_id is None or r1.parent_b_instance_id is None:
        raise ValueError(
            "project_to_relation_occurrence_fields: R1本体的parent_a/b_instance_id"
            "尚未填入，无法投影为RelationOccurrence（父实例身份是必需字段）")
    return {
        "relation_type": r1.link_gen.relation_type,
        "parent_a_instance_id": r1.parent_a_instance_id,
        "parent_b_instance_id": r1.parent_b_instance_id,
        "collector_address": r1.link_gen.collector_address,
        "trace_scale": r1.link_gen.trace_scale,
        "t_detect": t_detect,
        "t_closed": t_closed,
        "occurrence_a_address": occurrence_a_address,
        "occurrence_b_address": occurrence_b_address,
    }
