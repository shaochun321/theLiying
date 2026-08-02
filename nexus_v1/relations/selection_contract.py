"""nexus_v1.relations.selection_contract — S0-a：内生竞争选择资格与反硬编码边界。

TYPE:INFRA（纯类型定义与审计契约，不执行竞争动力学）

方案依据：document - 2026-08-02T204821.549.md（内生竞争性选择路线，
本轮明确只做S0-a：定义存在与保留分离、允许/禁止读取量、候选统一构造
契约、资源约束占位，以及标签置换/无固定偏向两项自动化审计）。

评判核心裁定：
  下一步不是"构造自然选择"，而是"让多个无语义特权的同等级物理候选，
  第一次在有限资源下产生非预指定的胜负"。这与自然选择不同——人设计
  候选如何产生、如何竞争，但不指定某一次实验的胜者；胜者由输入历史、
  物理支撑和有限资源决定；环境改变后，胜者能够改变。

  S0-a只冻结候选、本体身份、允许读取量、禁止读取量、资源约束和五项
  通过标准的**类型契约**，不写竞争电路（公共抑制/STDP/资源消耗动力学
  留给S0-b/c/d）。本文件不新建Neuron/SynapticBundle。

第一原则（评判"最重要的原则"）——存在与保留分离：
  ρ_i^obs（关系是否由物理链路真实发生，R1/R2已有的RelationOccurrence/
          R2Occurrence机制）
  ρ_i^retain（候选以后获得多少权重/能量/输出机会/可塑性/结构维持时间）
  ρ_i^obs ≠ ρ_i^retain：候选失败不能篡改历史宣布"这条关系从未发生"，
  候选获胜也不能反向伪造关系发生。这延续了本项目已有原则"关系被观察
  到 ≠ 关系被DA强化"（见relation_occurrence.py核心语义边界），本文件
  只是把同一原则从"观察vs学习"推广到"观察vs竞争保留"这个新维度，不是
  另立一套新逻辑。

RULES.md 强制三问：
  Q1 生物对应物：候选间竞争资源的机制类比神经发育中的突触竞争/神经
     元竞争性存活（synaptic/neuronal competition for limited trophic
     support，Purves & Lichtman 1980 Science 210:153），资源有限迫使
     候选竞争，但竞争结果由候选各自获得的真实支撑量决定，不是预先
     指定的胜者。本文件只冻结契约类型，具体动力学电路留给S0-c/d实现
     时补充完整REF。
  Q2 物理结构：本文件为S0-a阶段，不涉及具体Neuron/SynapticBundle构造。
     `SelectionCandidate`只是对候选身份的类型包装（引用已有R1/R2对象），
     不新建电路。
  Q3 参数依据：无物理参数（契约定义层）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, FrozenSet, List, Optional, Tuple

from ..components.structural_address import StructuralAddress


# ═══════════════════════════════════════════════════════════════════════
# 第一原则：存在与保留分离
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ObservedExistence:
    """ρ_i^obs：候选对应的关系是否由物理链路真实发生。

    只读引用已有的观察记录（R1的RelationOccurrence或R2的R2Occurrence），
    不复制/不修改其字段——本类只是一个"存在性"标记的类型包装，供竞争层
    读取"这条候选此刻是否真实观察到过"，不允许竞争层直接篡改。

    评判核心约束：候选失败不能篡改occurrence_ref使其"看起来从未发生"；
    候选获胜也不能在没有真实occurrence_ref的情况下伪造存在。本类
    frozen=True，构造后不可变，从物理上防止竞争层反向篡改。
    """
    candidate_id: str            # 无语义身份，见CANDIDATE_ID_PATTERN
    occurrence_ref: Any          # RelationOccurrence或R2Occurrence对象引用（只读）
    t_observed: int               # 观察记录产生的时刻（来自occurrence_ref.t_detect）


@dataclass
class RetainedStanding:
    """ρ_i^retain：候选以后获得多少权重/能量/输出机会/可塑性/结构维持时间。

    这是竞争层**唯一**可以修改的量。本类不含任何语义字段（不含
    relation_type/candidate意图描述），只含五个数值化的"保留资源"槲位，
    对应评判列出的五种可竞争资源。

    S0-a只冻结字段类型，不实现更新动力学（dot_w_i等）——留给S0-c/d。
    """
    candidate_id: str
    weight: float = 0.0            # 权重份额
    energy: float = 0.0            # 能量份额
    output_opportunity: float = 0.0  # 输出机会（如ℓ_out的通行带宽）
    plasticity_budget: float = 0.0   # 可塑性预算
    structural_lifetime: float = 0.0  # 结构维持时间


# ═══════════════════════════════════════════════════════════════════════
# 候选统一构造契约
# ═══════════════════════════════════════════════════════════════════════

# 候选ID必须匹配此模式：candidate_N（N为非负整数），不允许任何语义前缀
# （如short_/medium_/long_/winner_），见评判"无语义身份"要求。
_CANDIDATE_ID_PREFIX = "candidate_"


def make_candidate_id(index: int) -> str:
    """生成无语义身份的候选ID。竞争层构造候选时必须通过此函数取得ID，
    不允许手写候选名称字符串（评判明确禁止short_candidate/winner等写法）。
    """
    if index < 0:
        raise ValueError(f"make_candidate_id: index必须非负，实际={index}")
    return f"{_CANDIDATE_ID_PREFIX}{index}"


def is_valid_candidate_id(candidate_id: str) -> bool:
    """校验候选ID是否符合无语义身份约定（candidate_N格式）。"""
    if not candidate_id.startswith(_CANDIDATE_ID_PREFIX):
        return False
    suffix = candidate_id[len(_CANDIDATE_ID_PREFIX):]
    return suffix.isdigit()


@dataclass(frozen=True)
class SelectionCandidate:
    """同构候选的统一包装：相同输入、相同输出目标、相同collector类型、
    相同代码构造器，只有纯物理参数不同（评判"第二步"的三条件同构候选）。

    评判要求"最好从同一个构造循环生成，避免三套手写代码产生结构偏置"，
    故本类的`physical_params`字段设计为dict（构造循环遍历同一份参数表，
    每次只替换其中的时间尺度等纯数值，不产生分支代码路径差异）。

    S0-a只定义类型，不在本文件构造具体的R1/R2电路实例——真正的三条候选
    池（RPrecCircuitT1一类的具体对象）留给S0-b实现。本类持有的是"候选的
    身份与参数描述"，不是候选电路本身。
    """
    candidate_id: str             # 必须由make_candidate_id()生成
    physical_params: dict         # 纯数值参数（如trace_tau_steps），无语义键名的值
    # 关联的观察/保留记录（S0-a阶段可为None，S0-b起才真正产生非None值）
    existence: Optional[ObservedExistence] = None
    standing: Optional[RetainedStanding] = None

    def __post_init__(self):
        if not is_valid_candidate_id(self.candidate_id):
            raise ValueError(
                f"SelectionCandidate: candidate_id={self.candidate_id!r} "
                f"不符合无语义身份约定，必须用make_candidate_id()生成"
                f"（格式：{_CANDIDATE_ID_PREFIX}N）")


# ═══════════════════════════════════════════════════════════════════════
# 允许/禁止读取量契约（评判"前沿局部契约"五问之二、五）
# ═══════════════════════════════════════════════════════════════════════

# 竞争层允许读取的量——只能是纯物理/数值量，不含任何语义标签。
ALLOWED_READ_FIELDS: FrozenSet[str] = frozenset({
    "candidate_id",           # 无语义身份（candidate_N格式，非relation_type）
    "physical_params",        # 纯数值参数
    "t_observed",              # 观察时刻（数值）
    "weight", "energy", "output_opportunity",
    "plasticity_budget", "structural_lifetime",  # RetainedStanding的五个数值槲位
})

# 竞争层绝对禁止读取的量——语义信息、身份标签、预期结果。
# 评判明确列出："relation_type"/"candidate_id"（此处指语义化的候选名称，
# 非make_candidate_id()生成的无语义ID）/"站点名称字符串"/"预期胜者"/
# "测试场景名称"。
FORBIDDEN_READ_FIELDS: FrozenSet[str] = frozenset({
    "relation_type",           # R1/R2的语义关系类型
    "link_type",                # 链路机制类型（同样是语义标签）
    "site_index", "site_name",  # 站点名称/索引字符串
    "expected_winner",          # 预期胜者（不允许存在这个字段本身）
    "scenario_name", "test_name",  # 测试场景名称
    "occurrence_a_address", "occurrence_b_address",  # 谱系地址（属于观察层，非竞争层）
    "generation_link_address", "collector_address",  # R1的地址字段（同上）
})


def audit_forbidden_reads(read_field_names: FrozenSet[str]) -> List[str]:
    """审计一组被竞争层实际读取的字段名，返回其中违反禁止读取契约的字段列表。

    竞争层实现（S0-b/c/d）在读取任何SelectionCandidate/ObservedExistence/
    RetainedStanding字段前，应能被此函数静态审计——空列表表示合规。
    """
    return sorted(read_field_names & FORBIDDEN_READ_FIELDS)


# ═══════════════════════════════════════════════════════════════════════
# 资源约束占位（评判"第四步"，S0-a只占位类型，不实现动力学）
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class LocalResourcePool:
    """有限资源池占位：sum_i p_i(t) <= P_max_local。

    S0-a只定义容量上限和当前占用总量的记账接口，不实现具体的竞争动力学
    （公共抑制h、竞争强度γ等留给S0-c）。
    """
    capacity: float
    _allocated: float = field(default=0.0, repr=False)

    @property
    def available(self) -> float:
        return max(0.0, self.capacity - self._allocated)

    def try_allocate(self, amount: float) -> bool:
        """尝试分配amount资源，成功返回True并记账，超出容量返回False不记账。

        S0-a阶段本方法只做资源记账占位，不含任何候选选择逻辑——由谁调用
        本方法、调用顺序如何决定，都是S0-c要解决的竞争动力学问题，不在
        本类范围内。
        """
        if amount < 0:
            raise ValueError("try_allocate: amount必须非负")
        if amount > self.available:
            return False
        self._allocated += amount
        return True

    def release(self, amount: float) -> None:
        self._allocated = max(0.0, self._allocated - amount)


# ═══════════════════════════════════════════════════════════════════════
# 五项通过标准（评判"最低通过条件"，类型占位——真正的判定逻辑留给S0-d）
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SelectionQualificationResult:
    """五项通过标准的结构化记录（S0-a只定义字段，真正的判定值在S0-d填入）。

    winner_not_prespecified：结果中没有任何代码路径使用候选名称/索引
        选择胜者（由audit_forbidden_reads()等静态审计支撑）
    environment_reversible：E_A→ρ_1, E_B→ρ_3这类环境决定胜者的可逆性
    resource_bounded：sum_i P_i(t) <= P_max_local始终成立
    losing_candidate_decays：长期无后续物理支撑的候选w_i(t)→0或降至阈值下
    winner_removal_reorganizes：切断占优候选后系统重新组织而非整体死亡
    label_permutation_invariant：候选索引重排后胜负仍由物理参数/环境决定
    """
    winner_not_prespecified: Optional[bool] = None
    environment_reversible: Optional[bool] = None
    resource_bounded: Optional[bool] = None
    losing_candidate_decays: Optional[bool] = None
    winner_removal_reorganizes: Optional[bool] = None
    label_permutation_invariant: Optional[bool] = None

    @property
    def all_passed(self) -> bool:
        fields = (self.winner_not_prespecified, self.environment_reversible,
                  self.resource_bounded, self.losing_candidate_decays,
                  self.winner_removal_reorganizes, self.label_permutation_invariant)
        return all(f is True for f in fields)
