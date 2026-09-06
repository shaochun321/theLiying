"""tss.relations.site_selection — T0 冻结 ξ^occ 选点（温感轨最小支撑）。

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
  T2（r_edge-lag，三元）取整条链：31 ↔ 28 ↔ 23（28 为中枢/邻接双向节点）。

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

  历史复现性风险（已修复，2026-07-21）：`SynapticBundle.__init__`
  （`circuit/bundle.py`）对每个 Memristor 初始权重施加基于
  (bundle_id, i_s, i_t) 的 ±25% 对称性打破扰动。**曾经**用 Python 内置
  `hash()` 生成扰动种子，而 Python 字符串 hash() 默认逐进程随机化
  （PYTHONHASHSEED 未固定）——这是母本代码既有机制的历史缺陷，已被
  P2-A1b-0 边界复核实测坐实（u=0.0005 三次独立进程给出0/1/0次不同
  触发）。**修复**：改用 `zlib.crc32` 对 `f"{bundle_id}:{i_s}:{i_t}"`
  字符串取稳定摘要，跨进程/跨解释器完全确定，不再依赖 PYTHONHASHSEED。
  数学不变（仍是[-0.25,+0.25]均匀分布扰动），只是随机性来源从进程相关
  变为进程无关。修复后，本模块冻结的选点拓扑结构（索引/邻接/极性）与
  驱动这些点测得的响应数值都跨进程确定可复现。

═══════════════════════════════════════════════════════════════════════
批判三修正（2026-07-16，纳入交叉比对第三份批判点1）
═══════════════════════════════════════════════════════════════════════
原版本在模块导入时调用 `_compute_adjacent_triplet()` 重新计算最近邻，
即使无随机性、结果确定，仍是"确定性重算"而非真正的冻结——若未来
`fibonacci_sphere_points` 的实现、半径参数、或并列最近邻时的遍历顺序
发生变化，"冻结"结果会跟着悄悄改变，不符合"选点结果必须冻结保存、
T1~T4 只读该冻结集合"的要求。

修正：`FROZEN_THERMAL_SITES` 现在是**字面常量**（下方直接写死点索引/
坐标/边/极性），与生成公式完全解耦。`_compute_adjacent_triplet()` +
`fibonacci_sphere_points()` 的调用**只保留在 `recompute_for_verification()`
函数里**，仅供测试复核"冻结值是否仍与当前几何公式一致"使用（如
`test_basegen_thermal_t0.py` 的 T-T0-2），不再用于生产选择路径。
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

# 与 circuit/variant_adapter.py 中 _THERM_LOCAL_N / _THERM_LOCAL_R 保持一致。
# 不直接 import variant_adapter（避免仅为取两个常量就承担整个模块的导入
# 开销/循环导入风险）；数值来源已在上方 docstring 注明，若母本常量变更，
# 本模块的 test_basegen_thermal_t0.py 会通过一致性检查探测到不匹配。
_THERM_LOCAL_N = 32
_THERM_LOCAL_R = 2.0

# ── 冻结的字面常量：2026-07-16 用 fibonacci_sphere_points(32, 2.0) 计算一次
# 后固定写死，此后不再随生成公式变化而改变。若母本几何公式变更，用
# recompute_for_verification() 复核是否仍与这组常量一致（见 T-T0-2）。 ──
_CENTER = 28
_NB1 = 31
_NB2 = 23
_D1 = 1.091637724820349     # dist(28, 31)
_D2 = 1.161205457079701     # dist(28, 23)
_POSITIONS = {
    28: (-0.4225361867232139, -1.1747582393451876, -1.5625),
    31: (0.268297904125101, -0.41726488546495033, -1.9375),
    23: (0.3877493405739026, -1.7235846944332336, -0.9375),
}

# 主探测极性：全部站点统一用 warm（+dT 通道）。
_PRIMARY_POLARITY = "warm"


def _site(idx: int) -> Dict:
    return {
        "point_index": idx,
        "position": _POSITIONS[idx],
        "warm_collector_label": f"thermpt{idx}_warm",
        "cool_collector_label": f"thermpt{idx}_cool",
        "primary_polarity": _PRIMARY_POLARITY,
    }


# ── 冻结产物：T1~T4（温感轨）只读此结构，不得重新动态搜索最近邻。 ──
FROZEN_THERMAL_SITES: Dict = {
    "n_sphere_points": _THERM_LOCAL_N,
    "sphere_radius": _THERM_LOCAL_R,
    "sites": {
        _CENTER: _site(_CENTER),
        _NB1: _site(_NB1),
        _NB2: _site(_NB2),
    },
    # T1 (r≺，二元)：链中最短边。
    "t1_pair": {
        "a": _CENTER,
        "b": _NB1,
        "distance": _D1,
        "rationale": (
            f"点{_CENTER}↔{_NB1} 是链中最短边（d={_D1:.4f}），"
            f"属全局 32 点中最小点对距离之一。"
        ),
    },
    # T2 (r_edge-lag，三元)：完整链，center 为枢纽/双向邻接节点。
    "t2_chain": {
        "order": [_NB1, _CENTER, _NB2],
        "edges": [(_NB1, _CENTER, _D1), (_CENTER, _NB2, _D2)],
        "hub": _CENTER,
        "rationale": (
            f"链 {_NB1}↔{_CENTER}↔{_NB2}：{_CENTER} 是两条最短出边的共同端点，"
            f"两条边 (d={_D1:.4f}, d={_D2:.4f}) 均为该点的最近邻，"
            f"是真实几何邻接而非人为拼接。"
        ),
    },
    "known_reproducibility_caveat": (
        "选点拓扑（索引/邻接/极性）是字面冻结常量，确定性可复现；"
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


# ═══════════════════════════════════════════════════════════════════════
# 验证工具（不用于生产选择路径，只供测试复核冻结常量是否仍与当前几何
# 公式一致，见 test_basegen_thermal_t0.py 的 T-T0-2）
# ═══════════════════════════════════════════════════════════════════════

def _dist(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return math.sqrt(sum((a[k] - b[k]) ** 2 for k in range(3)))


def _compute_adjacent_triplet(n: int, radius: float):
    """在 n 个 Fibonacci-sphere 点中找真正局部邻接的三点链（中枢+两最近邻）。

    返回 (center_idx, neighbor1_idx, neighbor2_idx, d1, d2, positions)。
    纯几何计算，无随机性，确定性可复现。**仅供验证使用**，不再是
    `FROZEN_THERMAL_SITES` 的生成路径（见模块 docstring 批判三修正）。
    """
    from nexus_v1.components.skin_network import fibonacci_sphere_points

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


def recompute_for_verification() -> Dict:
    """用当前的几何公式重新计算一遍，供测试比对是否仍与冻结常量一致。

    返回 {"center":.., "nb1":.., "nb2":.., "d1":.., "d2":..}。若与
    `_CENTER`/`_NB1`/`_NB2`/`_D1`/`_D2` 不一致，说明母本几何公式已变化，
    需要人工决定是否要更新冻结常量（不应自动覆盖——那样又会退回
    "确定性重算"）。
    """
    center, nb1, nb2, d1, d2, _positions = _compute_adjacent_triplet(
        _THERM_LOCAL_N, _THERM_LOCAL_R)
    return {"center": center, "nb1": nb1, "nb2": nb2, "d1": d1, "d2": d2}
