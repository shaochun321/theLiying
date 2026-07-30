"""nexus_v1.generators — P2-A 基础生成元核心：抽取、地址、闭合状态机。

TYPE:INFRA（包本身不含新物理机制；见各模块内 TYPE 标注）

本包不新建任何神经元/Bundle 电路本身——十神经元量子热通路（10 ensemble +
collector）已存在于 `circuit/variant_adapter.py`（`_init_quantum_thermal_pathways`）。
本包只提供 P2-A 交叉比对四轮共识裁定的三样东西（详见
`cell-cell/交叉比对/评判_反馈自然单位概念修正_2026-07-20.md` §九步骤 1-3）：

  - occurrence.py:      χ=(t_up,t_down,t_rearm) 闭合状态机 + 最小组织记录
                          （不含任何无量纲测度，χ ≠ 自然单位）
  - base_generator.py:  从既有 VariantCircuit 抽取生成元核心的句柄
                          （wrap，不重建）+ D_i^sim 输入端口 + 地址挂载
  - trajectory.py:      Λ^phys 轨迹记录器（可选挂载，逐步记录 u_i/ensemble/
                          collector 原始值，供 P2-B 自然化候选测度检验）
  - input_envelope.py:  P2-A1a 输入包络扫描工具（纯测量，不做边界分类，
                          详见 `评判_P2A1顺序倒置修正_2026-07-21.md`）
  - skin_transduction.py: P2-A1b-2 皮肤输出→生成元输入转导映射（纯函数，
                          不接入BaseGenerator实际驱动循环，详见
                          `document - 2026-07-21T145017.166.md`）
  - natural_unit.py:    P2-B0 单 occurrence 自然化接口（𝒩_i^(0): χ↦𝔲^(1)，
                          两个明确标注的候选测度 count/duration，不冻结最终
                          NaturalUnit，详见
                          `document - 2026-07-28T183325.248.md`）

严格遵守「不改母本代码」——不修改 `circuit/variant_adapter.py` 的
`_init_quantum_thermal_pathways`，只读取其已构造的属性。
"""

from .occurrence import Occurrence, OccurrenceClosure, OccurrenceInstanceId, TransitionEvent
from .base_generator import BaseGenerator, wrap_base_generator, register_occ_thermal
from .trajectory import TrajectoryRecord, GeneratorTrajectory
from .input_envelope import InputEnvelopePoint, scan_input_envelope
from .skin_transduction import (
    TransductionConfig, transduce, REFERENCE_TRANSDUCTION_CONFIG,
)
from .natural_unit import SiteCalibration, NaturalUnit, naturalize
from .occurrence_identity import OccurrenceIdentityRegistry
from .occurrence_tap import CollectorOccurrenceTap, wrap_collector_occurrence_tap

__all__ = [
    'Occurrence', 'OccurrenceClosure', 'OccurrenceInstanceId', 'TransitionEvent',
    'BaseGenerator', 'wrap_base_generator', 'register_occ_thermal',
    'TrajectoryRecord', 'GeneratorTrajectory',
    'InputEnvelopePoint', 'scan_input_envelope',
    'TransductionConfig', 'transduce', 'REFERENCE_TRANSDUCTION_CONFIG',
    'SiteCalibration', 'NaturalUnit', 'naturalize',
    'OccurrenceIdentityRegistry',
    'CollectorOccurrenceTap', 'wrap_collector_occurrence_tap',
]
