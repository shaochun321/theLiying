"""nexus_v1.generators.occurrence_tap — P2-B1X1b：只读 occurrence 观察适配器。

TYPE:INFRA — 观察器，不驱动物理动力学（同 `occurrence.py` Q2 的既定定位）。

方案依据：`cell-cell/交叉比对/document - 2026-07-30T113327.179.md`
（P2-B1X1b：只读 occurrence tap）。

背景：评判裁定地基2采用**方案乙**——在既有物理通路（母本 `VariantCircuit.
step()` 已经驱动的 L1/HC/ensemble/collector）上外挂只读的 `OccurrenceClosure`，
不使用 `wrap_base_generator()`/`BaseGenerator.tick()` 再次驱动同一通路（那会
造成双重驱动，`base_generator.py:171-182` 已明确警告过这个互斥）。

`CollectorOccurrenceTap` 只做"测量"，不做"驱动"：
  - 拥有：collector 引用、对应 L1 引用、OccurrenceClosure、D1 地址、
    在线 transition 输出、occurrence 完成输出。
  - 不拥有：L1/HC/ensemble/collector 的物理驱动权（不调用 `feed()`/
    `tick()`/`_propagate()`，不修改任何 Neuron 的膜电位/激活值）。

`phys_support` 门控必须使用对应 L1 的 `activation > 0`（评判明确要求），
不能用 collector 自身活动或固定 True——否则会重新允许 HC 慢态残留内部
续命（`occurrence.py` 模块文档已记录的 P2-A1b-3R 教训）。

RULES.md 强制三问：
  Q1 生物对应物：本模块无新增 BIO 机制——它读取的 L1.activation/
     collector.pre_trace 都是既有神经元的既有输出量，观察方式与
     `BaseGenerator.tick()` 内部读取 `self.l1.activation`/`self.sense()`
     完全相同，只是不经过 `BaseGenerator` 这层驱动包装。
  Q2 物理结构：只读引用已有 Neuron 对象（母本 `VariantCircuit` 已构造好的
     `thermal_quantum_l1_{warm,cool}`/`thermal_quantum_collectors`），不
     新建 Neuron/SynapticBundle，不调用任何会改变神经元状态的方法
     （只调用 `.activation`/`.pre_trace` 属性读取和 `closure.update()`
     的状态机记账——后者本身也不改变被观测对象的状态，只是外部记账）。
  Q3 参数依据：`OccurrenceClosure` 复用其既有默认参数（theta_up=0.01/
     theta_down=0.001/rearm_min_steps=500），不为本模块重新标定——评判
     明确要求"第一版复用现有参数，不独立重新标定"，因为读取的是与
     `BaseGenerator` 相同类型（甚至同一个实例）的 warm collector 和 L1
     通路，若重新标定会制造两套 D1 语义（同一物理通路在 BaseGenerator
     看来是一个 occurrence，在 tap 看来却是另一种 occurrence）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..components.neuron import Neuron
from ..components.structural_address import (
    AddressRegistry, DOMAIN_SKIN_PATCH, GeneratedAddress,
)
from .base_generator import register_occ_thermal
from .occurrence import Occurrence, OccurrenceClosure, TransitionEvent


@dataclass
class CollectorOccurrenceTap:
    """只读观察适配器：外挂 `OccurrenceClosure` 到已有 collector+L1 通路上。

    与 `BaseGenerator` 的关键区别：`BaseGenerator` **拥有驱动权**（`feed()`/
    `tick()` 会调用 `_propagate()` 推进 L1→HC→ensemble→collector 的电流传播）；
    本类**不拥有驱动权**，只在外部驱动完成后（如 `circuit.step()` 跑完一步）
    读取 collector/L1 的当前状态，推进闭合状态机。

    字段：
      collector: 既有 collector Neuron 引用（如 `thermal_quantum_collectors`
                 或 `RPrecCircuitT1.rprec_collector_*`），只读 `.pre_trace`。
      l1:        对应 L1 引用（如 `thermal_quantum_l1_warm[pid]`），只读
                 `.activation`，作为 `phys_support` 门控信号源。
      closure:   状态机本体，复用既有默认参数（Q3）。
    """
    collector: Neuron
    l1: Neuron
    closure: OccurrenceClosure

    def observe(self, t_step: int) -> Optional[Occurrence]:
        """读取一步。**不驱动任何神经元**——只调用 `.pre_trace`/`.activation`
        属性读取（母本 `circuit.step()` 或调用方已在此之前完成了真实驱动），
        以及 `closure.update()`（状态机记账，不改变被观测神经元本身）。

        `phys_support = self.l1.activation > 0`（评判明确要求的门控信号源，
        同 `BaseGenerator.tick()` 的既定逻辑，见模块文档）。
        """
        return self.closure.update(
            self.collector.pre_trace, t_step, phys_support=(self.l1.activation > 0))

    @property
    def last_transitions(self) -> Tuple[TransitionEvent, ...]:
        return self.closure.last_transitions

    @property
    def address(self) -> GeneratedAddress:
        return self.closure.address


def wrap_collector_occurrence_tap(
    collector: Neuron, l1: Neuron, registry: AddressRegistry,
    *, site_index: int, polarity: str,
    theta_up: Optional[float] = None, theta_down: Optional[float] = None,
) -> CollectorOccurrenceTap:
    """从既有 collector+L1 引用构造 tap，地址挂载复用
    `register_occ_thermal`（与 `wrap_base_generator` 相同的地址注册模式，
    保证 tap 产生的 `Occurrence.address` 与 `BaseGenerator` 产生的地址
    在相同 `(site_index, polarity)` 下 uid 一致——这是等价性测试
    `T-OCC-TAP-1` 的前提，不是各自发明一套命名。）

    `theta_up`/`theta_down` 为 None 时使用 `OccurrenceClosure` 默认值
    （Q3：第一版不重新标定）。
    """
    pid = f"thermpt{site_index}"
    label = f"{pid}_{polarity}"

    parent_addr = registry.register_physical(DOMAIN_SKIN_PATCH, pid)
    address = register_occ_thermal(registry, label, parent_addr)

    closure_kwargs = {"address": address}
    if theta_up is not None:
        closure_kwargs["theta_up"] = theta_up
    if theta_down is not None:
        closure_kwargs["theta_down"] = theta_down
    closure = OccurrenceClosure(**closure_kwargs)

    return CollectorOccurrenceTap(collector=collector, l1=l1, closure=closure)
