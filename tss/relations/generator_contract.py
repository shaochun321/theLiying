"""tss.relations.generator_contract — TSS-0：时间/空间/尺度生成算子
的有类型接口与现有资产映射。

TYPE:INFRA（纯类型定义，不写新动力学）

方案依据：document - 2026-08-03T131304.153.md（主线纠偏：恢复"基础生成元
→时间/空间/尺度生成元→耦合生成元"路线，S0竞争路线暂停）。

评判核心裁定：
  正确主线：
    基础生成元 → 时间/空间/尺度生成元 → 耦合生成元
  每一级生成元首先都是"由物理结构实现的算子，而不是学习结果"。
  生成元存在资格 ⊥ STDP/DA：一个非学习型生成元必须在STDP=0、DA=0时
  仍能接受物理输入、完成算子作用、产生输出、形成可追踪区间、进入
  下一级耦合——这是"关系被观察到≠被DA强化"原则的自然延伸，不是新
  造规则。

TSS-0范围（本文件严格遵守，不越界）：
  只做定义与现有代码映射，不写新动力学：
    Θ^(1)：时间生成算子
    Σ^(1)：空间生成算子（评判明确：暂未有真实资产可映射，只冻结类型）
    Λ^(1)：尺度生成算子（同上，只冻结类型）
  每个类型只固定六项：
    1. 输入基础生成元（哪些κ^10对象）
    2. 物理载体（哪些真实Neuron/SynapticBundle）
    3. 作用区间（何时算子生效）
    4. 输出（下游可读的量）
    5. 可被下游读取的量（对应S0-a的ALLOWED_READ_FIELDS概念，但这里是
       生成元层面的读取契约，不是竞争层契约）
    6. 禁止用来决定输出的语义字段（对应S0-a的FORBIDDEN_READ_FIELDS）

R1现状归位（评判"当前时间R1"一节）：
  T1（28≺31）是Θ^(1)的一个**原型**（GeneratorThetaBinding），只覆盖
  "≺"这一种时间投影，不代表完整的时间生成元族。RelationOccurrence是
  这次算子作用的投影记录（Π_τ），不是算子本体——算子本体是
  R1StructureBlock（ℓ_gen驱动的耦合结构）。

R2现状归位（评判"当前共同源R2"一节）：
  当前R2^fork是"关系活动的AND型再组合"，是高阶链路可行性实验，
  不等于耦合生成元体系（方向/梯度/散度）。不应继续扩展R2-R2（评判
  明确暂停）。

S0记录（评判"S0竞争路线现在暂停"）：
  S0-a/S0-b/S0-bX1的成果重新归类为"未来软竞争与保留机制的辅助支线"，
  不删除代码，不继续推进S0-c/d。`candidate_id → bundle_id → 权重扰动`
  问题已在S0-bX1修复（BundleConfig.physical_seed），登记为S0恢复前的
  已知阻塞记录，本文件不重复处理。

RULES.md 强制三问：
  Q1 生物对应物：本文件是纯类型契约层，无新增BIO机制——Θ^(1)包装的是
     temporal_r_prec.py已有的trace+AND门检测（BIO对应物见该文件Q1）。
     Σ^(1)/Λ^(1)目前无对应真实电路，只冻结类型定义本身无BIO内容。
  Q2 物理结构：GeneratorThetaBinding只读引用RPrecCircuitT1/T2已有对象
     （trace/relation_collector/bundles），不新建Neuron/SynapticBundle。
  Q3 参数依据：无物理参数（纯类型定义层）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, FrozenSet, List, Optional, Tuple

from nexus_v1.components.structural_address import StructuralAddress


# ═══════════════════════════════════════════════════════════════════════
# 通用生成算子契约基类（六项固定字段的共同结构）
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GeneratorOperatorContract:
    """时间/空间/尺度生成算子的通用六项契约。

    评判裁定的六项：
      input_generators：输入基础生成元（κ^10对象引用列表）
      physical_carriers：物理载体（真实Neuron/SynapticBundle引用列表）
      active_interval：作用区间描述（何时算子生效，可为None表示待冻结）
      output_readable_fields：可被下游读取的量（字段名集合）
      forbidden_decision_fields：禁止用来决定输出的语义字段（同S0-a的
        FORBIDDEN_READ_FIELDS概念，但适用范围是生成元层，不是竞争层）
      exists_without_learning：True表示该算子在STDP=0、DA=0时仍能完整
        完成"接受物理输入→完成算子作用→产生输出→形成可追踪区间→进入
        下一级耦合"整条链路（评判"生成元存在资格⊥STDP/DA"的可验证标记）
    """
    operator_type: str   # "theta" | "sigma" | "lambda"
    input_generators: Tuple[Any, ...]
    physical_carriers: Tuple[Any, ...]
    active_interval: Optional[Any]
    output_readable_fields: FrozenSet[str]
    forbidden_decision_fields: FrozenSet[str]
    exists_without_learning: bool


# ═══════════════════════════════════════════════════════════════════════
# Θ^(1)：时间生成算子
# ═══════════════════════════════════════════════════════════════════════

# Θ算子允许读取的量：只读物理/数值量，不含语义标签（同r1_structure.py
# 已有的ℓ_gen/ℓ_out区分原则）。
THETA_ALLOWED_READ_FIELDS: FrozenSet[str] = frozenset({
    "relation_collector_pre_trace",   # 检测输出（数值）
    "trace_activation",                # 中间trace状态（数值）
    "t_detect", "t_closed",            # 时刻（数值）
})

# Θ算子禁止用来决定输出的语义字段——沿用selection_contract.py已冻结的
# 命名（relation_type/link_type等），因为同一类语义泄漏风险在生成元层
# 同样存在：算子的物理输出不应由这些字符串标签决定。
THETA_FORBIDDEN_DECISION_FIELDS: FrozenSet[str] = frozenset({
    "relation_type", "link_type", "site_index", "site_name",
    "candidate_id", "expected_direction",
})


@dataclass(frozen=True)
class GeneratorThetaBinding:
    """Θ^(1)：时间生成算子的现有资产绑定（评判裁定的映射，不新建电路）。

    评判归位判断：T1（28≺31）是Θ^(1)的一个**原型**，只覆盖"≺"这一种
    时间投影，不代表完整的时间生成元族。本类把现有RPrecCircuitT1/T2的
    对象引用绑定为Θ^(1)契约的六项字段，供未来扩展"≺"之外的时间投影
    （如r_edge-lag/时间共现等）时复用同一套契约形状，不是本轮新增功能。

    六项映射（以T1为例，site_a=28≺site_b=31）：
      input_generators = (κ_A^10, κ_B^10) — 即r1_structure.KappaTen实例
      physical_carriers = (trace_a, trace_b, relation_collector) — ℓ_gen
        的物理组件（temporal_r_prec.py已有对象）
      active_interval = R1PhysicalInterval实例（已有，evaluator 045235
        双向状态机）
      output_readable_fields = THETA_ALLOWED_READ_FIELDS
      forbidden_decision_fields = THETA_FORBIDDEN_DECISION_FIELDS
      exists_without_learning = True — RPrecCircuitT1的12条bundle全部
        frozen（不含STDP），relation_collector的检测不依赖任何DA信号
        （见temporal_r_prec.py模块docstring"这里只做检测不做学习"），
        本条为可验证事实，不是假设
    """
    projection_kind: str          # 当前只有"prec"（"≺"），未来可扩展
    kappa_a: Any                  # r1_structure.KappaTen
    kappa_b: Any
    trace_a: Any                  # Neuron（衰减积分器）
    trace_b: Any
    relation_collector: Any       # Neuron（AND门检测输出）
    physical_interval: Any        # r1_structure.R1PhysicalInterval实例（可选）
    contract: GeneratorOperatorContract = field(default=None)

    def __post_init__(self):
        if self.contract is None:
            object.__setattr__(self, 'contract', GeneratorOperatorContract(
                operator_type="theta",
                input_generators=(self.kappa_a, self.kappa_b),
                physical_carriers=(self.trace_a, self.trace_b,
                                   self.relation_collector),
                active_interval=self.physical_interval,
                output_readable_fields=THETA_ALLOWED_READ_FIELDS,
                forbidden_decision_fields=THETA_FORBIDDEN_DECISION_FIELDS,
                exists_without_learning=True,
            ))

    def is_projection_record_only(self, obj: Any) -> bool:
        """判断给定对象是否只是"算子作用的投影记录"（如RelationOccurrence），
        不是算子本体本身。评判归位判断：RelationOccurrence是Π_τ投影记录，
        R1StructureBlock才是算子本体（ℓ_gen驱动的耦合结构）。

        本方法只做类型名称的字符串归类，供TSS-0阶段整理现有代码时快速
        判断"这个类应该算作Θ^(1)本体的哪一部分"，不涉及运行时判定逻辑。
        """
        type_name = type(obj).__name__
        projection_record_types = {"RelationOccurrence", "R2Occurrence"}
        return type_name in projection_record_types


def build_theta_binding_from_rprec_t1(circuit) -> GeneratorThetaBinding:
    """从真实RPrecCircuitT1实例构造Θ^(1)绑定（映射，不新建任何对象）。

    调用方需自行构造r1_structure.KappaTen对象作为kappa_a/kappa_b
    （本函数不重复KappaTen的构造逻辑，避免和r1_structure.py产生
    重复定义——TSS-0是映射层，不是第二套实现）。
    """
    return GeneratorThetaBinding(
        projection_kind="prec",
        kappa_a=None,   # 调用方按需传入r1_structure.KappaTen实例
        kappa_b=None,
        trace_a=circuit.rprec_trace_a_fast,
        trace_b=circuit.rprec_trace_b_fast,
        relation_collector=circuit.rprec_collector_a_prec_b_fast,
        physical_interval=None,  # 调用方按需传入R1PhysicalInterval实例
    )


# ═══════════════════════════════════════════════════════════════════════
# Σ^(1)：空间生成算子（评判明确：暂无真实资产，只冻结类型）
# ═══════════════════════════════════════════════════════════════════════

SIGMA_ALLOWED_READ_FIELDS: FrozenSet[str] = frozenset({
    "adjacency_response_diff",   # 局部传播/阻断实验产生的响应差异（数值）
    "t_detect", "t_closed",
})

SIGMA_FORBIDDEN_DECISION_FIELDS: FrozenSet[str] = frozenset({
    "euclidean_coordinate",   # 评判明确：不能直接读取外部欧氏坐标
    "site_index", "site_name", "candidate_id", "expected_direction",
})


@dataclass(frozen=True)
class GeneratorSigmaBinding:
    """Σ^(1)：空间生成算子契约占位（TSS-1才构造真实资产，本轮只冻结类型）。

    评判裁定的构造原则（供TSS-1实现时遵守，本类不实现）：
      不能直接读取外部欧氏坐标，应来自：
        - 实际可达链
        - 局部传播
        - 阻断实验
        - 邻接与方向性作用
        - 结构之间的响应差异
    """
    input_generators: Tuple[Any, ...] = ()
    physical_carriers: Tuple[Any, ...] = ()
    active_interval: Optional[Any] = None
    contract: GeneratorOperatorContract = field(default=None)

    def __post_init__(self):
        if self.contract is None:
            object.__setattr__(self, 'contract', GeneratorOperatorContract(
                operator_type="sigma",
                input_generators=self.input_generators,
                physical_carriers=self.physical_carriers,
                active_interval=self.active_interval,
                output_readable_fields=SIGMA_ALLOWED_READ_FIELDS,
                forbidden_decision_fields=SIGMA_FORBIDDEN_DECISION_FIELDS,
                exists_without_learning=True,
            ))


# ═══════════════════════════════════════════════════════════════════════
# Λ^(1)：尺度生成算子（评判明确：暂无真实资产，只冻结类型）
# ═══════════════════════════════════════════════════════════════════════

LAMBDA_ALLOWED_READ_FIELDS: FrozenSet[str] = frozenset({
    "window_projection_diff",   # 同一物理过程在不同结构窗口下的投影差异
    "t_detect", "t_closed",
})

LAMBDA_FORBIDDEN_DECISION_FIELDS: FrozenSet[str] = frozenset({
    "resolution_label",   # 评判明确：不能给数据贴"粗/细"标签
    "site_index", "site_name", "candidate_id", "expected_direction",
})


@dataclass(frozen=True)
class GeneratorLambdaBinding:
    """Λ^(1)：尺度生成算子契约占位（TSS-2才构造真实资产，本轮只冻结类型）。

    评判裁定的构造原则（供TSS-2实现时遵守，本类不实现）：
      同一个物理过程通过不同结构窗口或分辨率产生不同投影：
        Λ^(1): (G, I_λa, I_λb) ↦ 可继续作用的尺度关系
      尺度不是给数据贴"粗/细"标签，而是实际改变下游可见结构和作用方式
      的算子。
    """
    input_generators: Tuple[Any, ...] = ()
    physical_carriers: Tuple[Any, ...] = ()
    active_interval: Optional[Any] = None
    contract: GeneratorOperatorContract = field(default=None)

    def __post_init__(self):
        if self.contract is None:
            object.__setattr__(self, 'contract', GeneratorOperatorContract(
                operator_type="lambda",
                input_generators=self.input_generators,
                physical_carriers=self.physical_carriers,
                active_interval=self.active_interval,
                output_readable_fields=LAMBDA_ALLOWED_READ_FIELDS,
                forbidden_decision_fields=LAMBDA_FORBIDDEN_DECISION_FIELDS,
                exists_without_learning=True,
            ))


# ═══════════════════════════════════════════════════════════════════════
# 生成元存在资格审计（评判"生成元存在资格⊥STDP/DA"）
# ═══════════════════════════════════════════════════════════════════════

def audit_exists_without_learning(contract: GeneratorOperatorContract) -> bool:
    """核验一个生成算子契约是否满足"存在资格⊥STDP/DA"——即
    exists_without_learning标记为True，且该标记不是凭空声明的（本函数
    只做字段存在性检查，真正的可验证证据来自调用方在构造GeneratorXBinding
    时引用的真实电路是否frozen——如temporal_r_prec.py的12条bundle全部
    learning_rule="frozen"）。
    """
    return contract.exists_without_learning is True
