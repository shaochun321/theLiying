"""nexus_v1.relations.r1_structure — P2-B1X2a：R1最小结构块定义。

TYPE:INFRA — 纯类型定义，不新建Neuron/SynapticBundle，不执行神经动力学。

方案依据：
  `cell-cell/交叉比对/document - 2026-07-31T205641.086.md`（P2-B1X2路线重写）
  `cell-cell/交叉比对/document - 2026-07-31T221144.140.md`（核心修正：ℓ_gen≠ℓ_out）

评判核心修正（221144）：
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
from typing import List, Optional, Tuple

from ..components.neuron import Neuron
from ..circuit.bundle import SynapticBundle
from ..components.structural_address import GeneratedAddress, StructuralAddress
from ..generators.occurrence import OccurrenceInstanceId


# ── 关系生成链路类型常量 ──
LINK_TYPE_RPREC_FAST = "r_prec.fast_trace_and_gate"
LINK_TYPE_RPREC_SLOW = "r_prec.slow_trace_and_gate"

# ── 区间退出阈值（collector pre_trace跌落至此以下视为链路支撑消失） ──
_DEFAULT_INTERVAL_EXIT_THRESHOLD = 1e-4


@dataclass(frozen=True)
class KappaTen:
    """κ^10：十神经元不可约基础结构块（一个站点的温感量子元通路）。

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
    """
    link_type: str   # LINK_TYPE_RPREC_FAST / LINK_TYPE_RPREC_SLOW
    trace_scale: str # "fast" | "slow"

    # trace神经元（衰减积分器）
    trace_a: Neuron
    trace_b: Neuron

    # 关系collector（重合检测输出，也是ℓ_gen的最终节点）
    relation_collector: Neuron

    # ℓ_gen内部的bundles（只读引用，不拥有传播权）
    bundles: Tuple[SynapticBundle, ...]

    # 链路地址（供R1实例身份回指）
    link_address: StructuralAddress


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
    """R1结构块的物理区间 I = [s_enter, s_exit]。

    P2-B1X2d负责实现完整的区间进入/维持/退出判断逻辑。
    本文件只定义字段类型，为P2-B1X2a冻结类型做占位——字段可在X2d补全。

    当前最小定义：
      s_enter：外部物理支撑第一次开始作用的步骤
      s_exit：四种条件中耦合链路低于退出阈值的最晚步骤
              （取 max_c(s_relax,c)，确保耗散尾部被完整包含）
      is_active：当前是否在有效区间内

    评判221144指出：
      Y_c(s)的区间范数||Y||_{2,I}必须在明确的物理区间I上计算，
      不能用任意固定长度测试窗口替代——这是P2-B1X2d的任务。
    """
    s_enter: Optional[int] = None  # 耦合进入时刻
    s_exit: Optional[int] = None   # 耦合退出时刻（待X2d填入）
    exit_threshold: float = _DEFAULT_INTERVAL_EXIT_THRESHOLD

    @property
    def is_defined(self) -> bool:
        """区间是否已有明确的enter/exit定义（P2-B1X2d完成前为False）。"""
        return self.s_enter is not None and self.s_exit is not None

    @property
    def duration(self) -> Optional[int]:
        if self.is_defined:
            return self.s_exit - self.s_enter
        return None


@dataclass
class R1StructureBlock:
    """R1最小结构块：两个不可约基础结构通过真实链路在物理驱动区间内形成的耦合块。

    评判205641定义（修正后）：

        R1_AB[I] = (κ_A^10, κ_B^10, ℓ_gen, I, Γ_AB^I)

    其中：
      κ_A^10, κ_B^10：两个不可约基础结构（十神经元基元）
      ℓ_gen：使两者发生耦合的关系生成结构（不是输出链路）
      I：该耦合保持同一谱系的物理区间
      Γ_AB^I：区间内完整耦合轨迹（P2-B1X2c测量）

    关系向下游产生作用另由ℓ_out（R1OutputLink）表示：
        O_ρq = (R1_AB, ℓ_out, q, Y_q)

    层次清楚：
      R1块  ← 回答"A和B是否真正形成了关系"
      ℓ_out ← 回答"这个关系是否能向下游施力"（P2-B1X2c测量Y的位置）

    身份：
      R1实例身份 = (parent_a_instance_id, parent_b_instance_id,
                    link_address, interval_identity)
      其中interval_identity在X2d实现前暂用s_enter标识。

    去重规则（P2-B1X1e当前实现在RelationFinalizer._registered_keys）：
      同一父实例对、同一生成链路地址、同一区间，只产生一个R1实例。
      X2d完成后去重键可扩展为(parent_A, parent_B, ℓ_gen.link_address, I)。
    """
    # ── 基元 ──
    kappa_a: KappaTen   # 基础结构A（十神经元基元）
    kappa_b: KappaTen   # 基础结构B

    # ── 关系生成链路（A和B怎样形成关系） ──
    link_gen: RelationGenLink

    # ── 物理区间（P2-B1X2d补全） ──
    interval: R1PhysicalInterval = field(default_factory=R1PhysicalInterval)

    # ── 关系输出链路（可选，仅RPrecCircuitT1Plastic存在） ──
    link_out: Optional[R1OutputLink] = None

    # ── 谱系回指 ──
    # 两个父D1实例身份（与RelationOccurrence.parent_{a,b}_instance_id对应）
    parent_a_instance_id: Optional[OccurrenceInstanceId] = None
    parent_b_instance_id: Optional[OccurrenceInstanceId] = None

    # ── R1实例身份（待X2d填入完整区间标识符） ──
    r1_id: Optional[str] = None   # 暂用字符串占位，X2d替换为专用类型

    @property
    def has_output_link(self) -> bool:
        """是否已有关系输出链路（需RPrecCircuitT1Plastic）。"""
        return self.link_out is not None

    @property
    def relation_collector(self) -> Neuron:
        """快捷访问关系collector（ℓ_gen的输出端，ℓ_out的输入端）。"""
        return self.link_gen.relation_collector

    def measure_output_current(self) -> Optional[List[float]]:
        """读取ℓ_out对下游节点的局部电流（P2-B1X2c测量Y_c(s)用）。

        返回None若ℓ_out不存在（RPrecCircuitT1基类无输出链路）。
        调用方应在circuit.step_rprec()之后调用，不能在circuit.step()前。
        """
        if self.link_out is None:
            return None
        return self.link_out.measure_local_current()
