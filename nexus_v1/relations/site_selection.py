"""nexus_v1.relations.site_selection — T0 冻结 ξ^occ 选点（温感轨最小支撑）。

TYPE:INFRA

方案依据：cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md
《T0 —— 基线与夹具隔离》《批判二点11：T0 选点结果必须冻结保存》。

选点方法：
  在感温量子元系统的 32 个 Fibonacci-sphere 采样点（`_THERM_LOCAL_N=32`,
  `_THERM_LOCAL_R=2.0`，见 `circuit/variant_adapter.py`）上，计算全部
  C(32,2)=496 对点的欧氏距离，取真正局部邻接（距离最小）的三点链，
  而非从 64 个 ξ^occ collector 中任意挑选——任意挑选无法代表"局部邻接"。

  计算结果（2026-07-16 用 fibonacci_sphere_points(32, 2.0) 复算确认）：
    全局最小点对距离 = 1.0916（点 28↔31，并列 点 0↔3）。
    以点 28 为枢纽的两条最短出边：28↔31 (d=1.0916)、28↔23 (d=1.1612)，
    构成链 31 ↔ 28 ↔ 23，链长 2.2528，是本模块扫描到的最紧邻三点链。

  T1（r≺，二元）取链中最短的一条边：28 ↔ 31。
  T2（r→，三元）取整条链：31 ↔ 28 ↔ 23（28 为中枢/邻接双向节点）。

  选点理由（对应「选点理由」字段要求）：
    - 用真实球面几何距离筛选，不是拍脑袋挑索引；
    - 28↔31 是全局最小点对距离之一，物理上代表"最紧邻"的一对感受野；
    - 28 同时是 T1 边的一端与 T2 链的枢纽，T1/T2 共享冻结集合，
      避免两个 Phase 各自选点导致的支撑不一致。

  极性（warm/cool）：每个感温点物理上同时存在 warm 与 cool 两条通道
  （collector label 形如 `thermpt{i}_warm` / `thermpt{i}_cool`，见
  `VariantCircuit._init_quantum_thermal_pathways`）。本轮统一取
  **warm 为主探测极性**——warm 对应 +dT（升温），与 Ω 层 div_exc 的
  "center=升温"约定一致，作为默认驱动方向；cool 通道仍记录在冻结集
  合中，供后续对照实验使用，但 T1~T4 首版只驱动 warm。

  已知复现性风险（须写入 T0 报告）：`SynapticBundle.__init__`
  （`circuit/bundle.py:169-171`）对每个 Memristor 初始权重施加
  `hash((bundle_id, i_s, i_t))` 驱动的 ±25% 对称性打破扰动，而 Python
  字符串 hash() 默认逐进程随机化（PYTHONHASHSEED 未固定）——这是母本
  代码既有机制，非本次改动引入。后果：本模块冻结的是**选点的拓扑结构**
  （索引/邻接/极性），是纯几何计算，确定可复现；但驱动这些点后测得的
  "输入峰值与爆发周期"数值会因进程而有 ±25% 量级波动。T1~T4 的探针
  测试如需跨进程比较绝对数值，应显式设置 PYTHONHASHSEED，或只断言
  相对关系（如"该点响应 > 未驱动点"），不断言绝对数值。
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

from ..components.skin_network import fibonacci_sphere_points

# 与 circuit/variant_adapter.py 中 _THERM_LOCAL_N / _THERM_LOCAL_R 保持一致。
# 不直接 import variant_adapter（避免仅为取两个常量就承担整个模块的导入
# 开销/循环导入风险）；数值来源已在上方 docstring 注明，若母本常量变更，
# 本模块的 test_basegen_thermal_t0.py 会通过一致性检查探测到不匹配。
_THERM_LOCAL_N = 32
_THERM_LOCAL_R = 2.0


def _dist(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return math.sqrt(sum((a[k] - b[k]) ** 2 for k in range(3)))


def _compute_adjacent_triplet(n: int, radius: float):
    """在 n 个 Fibonacci-sphere 点中找真正局部邻接的三点链（中枢+两最近邻）。

    返回 (center_idx, neighbor1_idx, neighbor2_idx, d1, d2, positions)。
    纯几何计算，无随机性，确定性可复现。
    """
    positions = fibonacci_sphere_points(n, radius)
    best = None
    for c in range(n):
        dlist = sorted(
            (_dist(positions[c], positions[j]), j) for j in range(n) if j != c
        )
        d1, n1 = dlist[0]
        d2, n2 = dlist[1]
        total = d1 + d2
        if best is None or total < best[0]:
            best = (total, c, n1, n2, d1, d2)
    _total, center, nb1, nb2, d1, d2 = best
    return center, nb1, nb2, d1, d2, positions


# ── 冻结计算（模块导入时执行一次，纯几何，无随机性） ──
_center, _nb1, _nb2, _d1, _d2, _positions = _compute_adjacent_triplet(
    _THERM_LOCAL_N, _THERM_LOCAL_R)

# 主探测极性：全部站点统一用 warm（+dT 通道）。
_PRIMARY_POLARITY = "warm"


def _site(idx: int) -> Dict:
    return {
        "point_index": idx,
        "position": _positions[idx],
        "warm_collector_label": f"thermpt{idx}_warm",
        "cool_collector_label": f"thermpt{idx}_cool",
        "primary_polarity": _PRIMARY_POLARITY,
    }


# ── 冻结产物：T1~T4（温感轨）只读此结构，不得重新动态搜索最近邻。 ──
FROZEN_THERMAL_SITES: Dict = {
    "n_sphere_points": _THERM_LOCAL_N,
    "sphere_radius": _THERM_LOCAL_R,
    "sites": {
        _center: _site(_center),
        _nb1: _site(_nb1),
        _nb2: _site(_nb2),
    },
    # T1 (r≺，二元)：链中最短边。
    "t1_pair": {
        "a": _center,
        "b": _nb1,
        "distance": _d1,
        "rationale": (
            f"点{_center}↔{_nb1} 是链中最短边（d={_d1:.4f}），"
            f"属全局 32 点中最小点对距离之一。"
        ),
    },
    # T2 (r→，三元)：完整链，center 为枢纽/双向邻接节点。
    "t2_chain": {
        "order": [_nb1, _center, _nb2],
        "edges": [(_nb1, _center, _d1), (_center, _nb2, _d2)],
        "hub": _center,
        "rationale": (
            f"链 {_nb1}↔{_center}↔{_nb2}：{_center} 是两条最短出边的共同端点，"
            f"两条边 (d={_d1:.4f}, d={_d2:.4f}) 均为该点的最近邻，"
            f"是真实几何邻接而非人为拼接。"
        ),
    },
    "known_reproducibility_caveat": (
        "选点拓扑（索引/邻接/极性）是纯几何计算，确定性可复现；"
        "但驱动后测得的输入峰值/爆发周期数值受 bundle.py:169-171 的 "
        "hash() 对称性打破扰动影响，逐进程有 ±25% 波动，"
        "除非固定 PYTHONHASHSEED。"
    ),
}


def get_frozen_site(point_index: int) -> Dict:
    """按点索引查询冻结站点信息。仅允许查询 FROZEN_THERMAL_SITES 内已冻结的点。

    T1~T4 应通过本函数读取选点，禁止重新调用 fibonacci_sphere_points +
    最近邻搜索去"重新发现"支撑集合（那样不同调用点可能因浮点误差或未来
    N/R 变更而选出不同的点，破坏可重复性）。
    """
    if point_index not in FROZEN_THERMAL_SITES["sites"]:
        raise KeyError(
            f"点 {point_index} 不在冻结选点集合中。T0 冻结集合仅含 "
            f"{sorted(FROZEN_THERMAL_SITES['sites'].keys())}；"
            f"如需扩展支撑集合，需走「全网络扩展」独立阶段，不得在 T1~T4 "
            f"内直接改动本冻结常量。"
        )
    return FROZEN_THERMAL_SITES["sites"][point_index]
