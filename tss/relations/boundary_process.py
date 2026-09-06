"""tss.relations.boundary_process — TSS-R0：基础生成元实时发生边界端口。

TYPE:INFRA

方案依据：TSS-R0_基础生成元-统一关系生成算子接口重审_2026-08-04.md
         + document - 2026-08-04T010613.482.md（评判修正因果方向）。

## 设计原则

旧 RPrec 结构直接读取 `collector.pre_trace`（连续模拟量），把
"是否发生"与"发生强度/延迟"混在一起，导致 AND 门的可行工作区
随站点链路增益/距离变化，无法跨生成元复用（T3 失败反例）。

本模块不创造新信号，只对现有物理过程提供有类型的统一访问入口：

    collector.activation(t)   ← 实时二值脉冲（0 或 1）
          ↓              ↓
    CollectorBoundaryPort    OccurrenceClosure
    （本模块，实时接口）     （审计记录，是 p_α 的下游产物）

冻结因果方向：Occurrence = A[p_α]，反方向不成立。

## CollectorBoundaryPort

轻量只读对象，两个字段：
- `generator_address`：物理谱系定位，不决定算子是否成立
- `carrier_ref`：指向真实 collector Neuron 对象（非字符串声明）

OccurrenceClosure 是 p_α 的并列下游消费者，不是端口的组成部分。
调用方可在端口旁独立持有 Closure，两者之间无依赖关系。

RULES.md 强制三问：
  Q1 生物对应物：无 BIO 对应物——纯 INFRA 接口层，类比信号线的有类型连接器，
     不引入任何新的神经元、突触或动力学。
  Q2 物理结构：只读取既有 collector Neuron 的 .activation 属性，
     不新建 Neuron/SynapticBundle，不调用任何会改变神经元状态的方法。
  Q3 参数依据：无物理参数。
"""

from __future__ import annotations

from dataclasses import dataclass

from nexus_v1.components.neuron import Neuron
from nexus_v1.components.structural_address import GeneratedAddress


@dataclass
class CollectorBoundaryPort:
    """TYPE:INFRA — 基础生成元发生边界端口。

    对基础生成元 collector 的实时脉冲输出提供有类型的统一访问。
    不创造新信号，不保存历史，不判断发生是否完成。

    两个字段：
      generator_address：物理谱系定位，只用于追踪，不决定输出是否产生。
      carrier_ref：指向真实 collector Neuron 对象（非字符串声明）。

    OccurrenceClosure 是该过程的**并列下游消费者**，不是端口的组成部分：
        collector.activation(t) → CollectorBoundaryPort.spike_output
        collector.activation(t) → OccurrenceClosure → Occurrence
    两条路径完全独立。Closure 由调用方单独持有，端口不包含对它的引用。

    冻结因果方向（TSS-R0 通过后确立）：
        Occurrence = A[p_α]，反方向 p_α ≠ B[Occurrence] 不成立。

    关键属性：
      spike_output：本步实时脉冲 = carrier_ref.activation（0.0 或 1.0）
      exists_without_learning：永为 True（STDP=0 / DA=0 时仍成立）

    禁止字段（评判 010613 明确）：
      站点语义名称、direction、near/far、local/broad、欧氏坐标、
      人工关系类别、physical_carrier 字符串声明、OccurrenceClosure 引用。
    """
    generator_address: GeneratedAddress
    carrier_ref: Neuron

    @property
    def spike_output(self) -> float:
        """本步实时脉冲：= collector.activation。

        对 spiking 神经元：本步发火 → 1.0，否则 → 0.0。
        不依赖 OccurrenceClosure/Tap/Finalizer，即使外部不调用
        tap.observe() 也始终有效。
        """
        return self.carrier_ref.activation

    @property
    def exists_without_learning(self) -> bool:
        """STDP=0 / DA=0 时 collector 仍然发火 → 永为 True。"""
        return True
