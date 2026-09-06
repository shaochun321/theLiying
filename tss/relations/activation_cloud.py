"""tss.relations.activation_cloud — TSS-A0：物理支撑—地址—生成活动云
锚定契约。

TYPE:INFRA（纯类型定义，不新增神经电路）

方案依据：document - 2026-08-03T135526.068.md（TSS-A0裁定，紧接TSS-1之后）。

评判裁定的四个对象（本轮只定义，不新增动力学）：
  PhysicalSupportRef：记录外部物理发生的模态/地址/时间窗口/实例
  GeneratorAnchor：建立 α_phys → G_α 的锚定关系（皮肤物理结构↔基础生成元）
  ActivationCloudEntry：记录一次生成元实际活动(α_phys, α_gen, y(t), I, parent)
  GeneratorActivationCloud：汇总 ω[W] → C_ω[W]（同一外部发生产生的全部活动云）

桥接层的意义：
  TSS-1证明了"局部外部物理发生产生空间选择性活动云"（Σ_support^(1)），
  但没有明确地址化——哪个物理支撑对应哪个基础生成元、哪些生成元进入了
  这次活动云，目前只是collector.pre_trace的数值，没有结构化谱系记录。
  TSS-A0把现有HeatSource、皮肤站点、κ^10、collector和发生身份接起来，
  使"外部发生→物理支撑锚定→生成活动云"的链路在类型层面可追踪，供后续
  Θ/Σ/Λ/CG算子的输入端复用（算子接收的不是原始collector数值，而是有
  谱系记录的ActivationCloudEntry）。

主线位置（评判131304/135526明确的正确顺序）：
  皮肤外部发生 → 物理支撑锚定(TSS-A0) → 生成活动云 → Θ/Σ/Λ → 耦合生成元

RULES.md 强制三问：
  Q1 生物对应物：感受野地址化和感觉地图——类比皮肤体感地图（somatotopic
     map）中皮肤物理位置到皮层地址的系统映射，不是点对点复制外部坐标，
     而是通过换能链形成有谱系的内部地址（Mountcastle 1957 J Neurophysiol
     20:408-434：皮层柱的体感地址化）。本文件只冻结映射关系的类型，不
     新建实际的地图电路。
  Q2 物理结构：只引用已有StructuralAddress（components/structural_address.py）
     和OccurrenceInstanceId（generators/occurrence.py），不新建Neuron/
     SynapticBundle。GeneratorAnchor只持有已有KappaTen对象的引用。
  Q3 参数依据：无物理参数（纯类型定义层）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from nexus_v1.components.structural_address import StructuralAddress


@dataclass(frozen=True)
class PhysicalSupportRef:
    """外部物理发生的支撑参数记录。

    modality：物理模态（如"thermal_warm"，不含语义标签如"hot"/"cold"）
    support_address：皮肤站点的StructuralAddress（已有skin.patch:thermptXX）
    t_start：物理作用开始时刻
    t_end：物理作用结束时刻（None表示持续中）
    occurrence_instance_id：对应的D1发生实例ID（若已产生），可为None（发生
      尚未完成rearm时），与现有OccurrenceInstanceId兼容

    "模态"不是语义标签（不允许写"刺激太热了"），只是对物理换能通路的分类
    描述（warm通路/cool通路/mechanical等），与结构address配合唯一定位一条
    换能链路，不用于决定生成算子的输出。
    """
    modality: str
    support_address: StructuralAddress
    t_start: int
    t_end: Optional[int] = None
    occurrence_instance_id: Optional[Any] = None  # OccurrenceInstanceId


@dataclass(frozen=True)
class GeneratorAnchor:
    """α_phys → G_α 的锚定关系：皮肤物理结构↔基础生成元（κ^10）。

    physical_support_address：皮肤站点地址（skin.patch:thermptXX）
    kappa_ten：对应的κ^10对象引用（r1_structure.KappaTen实例）
    modality：换能极性（"warm"/"cool"），决定哪条L1→HC→ensemble→collector链路
    collector_address：collector的结构地址（可从kappa_ten.collector读取，
      这里显式记录供活动云快速查找，不需要每次重新遍历KappaTen）

    约束：物理地址+模态唯一决定一个KappaTen，不允许同一组合对应多个基础
    生成元（防止"地址歧义"）。这延续了site_selection.py冻结站点的唯一性
    约束。
    """
    physical_support_address: StructuralAddress
    modality: str
    kappa_ten: Any   # r1_structure.KappaTen实例
    collector_address: StructuralAddress


@dataclass
class ActivationCloudEntry:
    """一次生成元实际活动的记录：(α_phys, α_gen, y(t), I, parent_occurrence)。

    物理支撑地址、生成元标识、响应强度、活动区间和父发生实例——这五元组
    构成一次生成元激活的完整谱系，供Θ/Σ/Λ/CG算子读取时追踪活动来源。

    response_strength：实测的collector.pre_trace峰值（已有GeneratorSigmaReachability
      的probe.response_strength，不是算法计算的"强度标签"）
    physical_interval：R1PhysicalInterval实例（可选，供区间级算子使用）
    parent_occurrence_id：产生这次活动的父D1发生实例ID（可追溯到外部物理事件）

    注意：本类不含任何语义判断字段（无"激活了/没激活/应该激活"），只有
    测量数值——与P2的RelationOccurrence"不依赖DA"原则类似，这里是"活动云
    记录不依赖任何预期判断"。
    """
    anchor: GeneratorAnchor
    response_strength: float
    t_detect: int
    physical_interval: Optional[Any] = None  # R1PhysicalInterval实例（可选）
    parent_occurrence_id: Optional[Any] = None  # OccurrenceInstanceId（可选）


@dataclass
class GeneratorActivationCloud:
    """ω[W] → C_ω[W]：同一外部发生所产生的全部活动生成元集合。

    triggering_support：产生本活动云的外部物理发生（PhysicalSupportRef）
    entries：进入活动云的生成元列表（只包含response_strength超过阈值的）
    activation_threshold：进入活动云的最低响应阈值（默认0.01，避免把
      数值噪声计入活动云；不是语义门控，只是数值截断）

    这是"外部局部发生通过具体物理支撑和换能链，选择性地产生一个地址化
    生成活动云"（评判135526原文）的类型化体现——活动云不是预先规定哪些
    生成元应该进入，而是由真实响应测量决定。
    """
    triggering_support: PhysicalSupportRef
    entries: List[ActivationCloudEntry] = field(default_factory=list)
    activation_threshold: float = 0.01

    def add_entry(self, entry: ActivationCloudEntry) -> bool:
        """向活动云添加一个生成元活动记录。
        只有response_strength超过阈值的记录才被接受。
        返回True表示成功加入，False表示被数值截断过滤。
        """
        if entry.response_strength >= self.activation_threshold:
            self.entries.append(entry)
            return True
        return False

    @property
    def active_sites(self) -> List[int]:
        """进入活动云的皮肤站点索引列表（从support_address提取，供调试用）。
        注意：这是辅助读取接口，算子本体应通过entries中的anchor和
        response_strength操作，不应直接用site索引做决策（防止把site编号
        变成语义标签）。
        """
        result = []
        for e in self.entries:
            uid = e.anchor.physical_support_address.uid
            # uid格式: "skin.patch:thermptXX"
            if "thermpt" in uid:
                try:
                    idx = int(uid.split("thermpt")[1])
                    result.append(idx)
                except (ValueError, IndexError):
                    pass
        return result
