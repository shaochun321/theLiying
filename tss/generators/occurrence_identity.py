"""tss.generators.occurrence_identity — P2-B1X1a：D1实例身份查找表。

TYPE:INFRA — 纯身份管理，不涉及神经动力学（同 `structural_address.py`/
`occurrence.py` 的 INFRA 定位）。

方案依据：`cell-cell/交叉比对/document - 2026-07-30T113327.179.md`
（P2-B1X1a：D1实例身份闭合）。

背景：`Occurrence`/`NaturalUnit` 现在都携带 `OccurrenceInstanceId =
(generator_address, epoch_id)`（见 `occurrence.py`/`natural_unit.py` 本轮
修改），但目前没有任何地方**登记**这个身份到具体的 `Occurrence`/
`NaturalUnit` 对象——即无法从 `(generator, epoch)` 反查到"那一次发生的
完整记录是什么"。本模块提供该查找表，供未来 `RelationDraft`（P2-B1X1c，
本轮**不实现**）在两个父实例都完成后回填正式身份时使用。

RULES.md 强制三问：
  Q1 生物对应物：本模块无 BIO 对应物——纯身份管理基础设施，类比
     `AddressRegistry`。
  Q2 物理结构：只读注册已有的 `Occurrence`/`NaturalUnit` 对象引用，不
     修改它们，不新建 Neuron/SynapticBundle。
  Q3 参数依据：无物理参数。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from .natural_unit import NaturalUnit
from .occurrence import Occurrence, OccurrenceInstanceId


@dataclass
class OccurrenceIdentityRegistry:
    """`OccurrenceInstanceId ↔ Occurrence/NaturalUnit` 双向可查找登记表。

    与 `structural_address.AddressRegistry` 的关系：`AddressRegistry` 管理
    的是"哪个地址对应哪个 local_key"（地址本身的身份连续性）；本类管理的
    是"哪一次具体发生（generator+epoch）对应哪个完整 Occurrence/NaturalUnit
    记录"（实例级的内容登记），两者是不同层次，不合并。
    """

    _occurrences: Dict[OccurrenceInstanceId, Occurrence] = field(default_factory=dict)
    _natural_units: Dict[OccurrenceInstanceId, NaturalUnit] = field(default_factory=dict)

    def register_occurrence(self, occurrence: Occurrence) -> OccurrenceInstanceId:
        """登记一个已完成的 Occurrence。幂等——同一 instance_id 重复登记
        覆盖为最新值（同一 (generator, epoch) 理论上只应产生一次
        Occurrence，重复登记通常意味着调用方逻辑有误，但本方法本身不
        禁止，交由调用方自行保证）。
        """
        instance_id = occurrence.instance_id
        self._occurrences[instance_id] = occurrence
        return instance_id

    def register_natural_unit(self, natural_unit: NaturalUnit) -> OccurrenceInstanceId:
        """登记一个 NaturalUnit。要求其 `source_occurrence_instance_id`
        非 None（`naturalize()` 生产路径总是填充该字段；只有测试手工构造
        且未传该字段时才可能是 None，此时拒绝登记，防止无法追溯来源的
        NaturalUnit 进入查找表）。
        """
        instance_id = natural_unit.source_occurrence_instance_id
        if instance_id is None:
            raise ValueError(
                "OccurrenceIdentityRegistry.register_natural_unit: "
                "natural_unit.source_occurrence_instance_id is None — "
                "cannot register a NaturalUnit without traceable source identity "
                "(手工构造的 NaturalUnit 若未传 source_occurrence_instance_id，"
                "不允许登记进查找表)")
        self._natural_units[instance_id] = natural_unit
        return instance_id

    def lookup_occurrence(self, instance_id: OccurrenceInstanceId) -> Optional[Occurrence]:
        return self._occurrences.get(instance_id)

    def lookup_natural_unit(self, instance_id: OccurrenceInstanceId) -> Optional[NaturalUnit]:
        return self._natural_units.get(instance_id)

    def is_resolved(self, instance_id: OccurrenceInstanceId) -> bool:
        """该实例身份是否已有登记的 Occurrence（供 P2-B1X1c 的
        `RelationDraft` 判断父实例是否已完成——本轮不实现该消费方，只
        提供查询接口）。"""
        return instance_id in self._occurrences
