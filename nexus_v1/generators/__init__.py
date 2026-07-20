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

严格遵守「不改母本代码」——不修改 `circuit/variant_adapter.py` 的
`_init_quantum_thermal_pathways`，只读取其已构造的属性。
"""

from .occurrence import Occurrence, OccurrenceClosure
from .base_generator import BaseGenerator, wrap_base_generator, register_occ_thermal

__all__ = [
    'Occurrence', 'OccurrenceClosure',
    'BaseGenerator', 'wrap_base_generator', 'register_occ_thermal',
]
