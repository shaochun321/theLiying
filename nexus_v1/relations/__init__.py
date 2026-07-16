"""nexus_v1.relations — 基础生成元 (r≺/r→/r_part) 双轨基础设施。

TYPE:INFRA

本包不定义任何新的关系生成电路本身（那是 T1/T2/T3 各自的 `_init_*` 方法，
按方案挂在 `VariantCircuit` 上）。本包只提供 Phase 0（Gate A）建立的、
T1~T4 与运动轨 M0~M4 共用的基础设施：

  - site_selection.py:  ξ^occ 冻结选点（温感轨最小支撑：3 个局部邻接点）
  - probes.py:           通用峰值/衰减/静息探针 + frozen 权重检查工具
  - census.py:           关系层独立账本（神经元/Collector/膜积分次数/近似能耗）

方案依据：cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md
本包严格遵守「不改母本代码」——不导入/不修改 VariantCircuit，只提供纯函数
工具，由 T1~T4 的测试/构造代码调用。
"""

from .site_selection import FROZEN_THERMAL_SITES, get_frozen_site
from .probes import PeakDecayRestProbe, snapshot_weights, check_frozen_weights_against
from .census import RelationLayerCensus, get_relation_generator_stats

__all__ = [
    'FROZEN_THERMAL_SITES', 'get_frozen_site',
    'PeakDecayRestProbe', 'snapshot_weights', 'check_frozen_weights_against',
    'RelationLayerCensus', 'get_relation_generator_stats',
]
