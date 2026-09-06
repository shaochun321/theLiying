"""
P2-A1a：生成元核心输入包络扫描（首轮粗网格）

目标：只用现有 `BaseGenerator.feed()` 扫描输入端口 `u`，不涉及皮肤/κ/q_skin
（那是 P2-A2+P2-A1b 的工作），回答"十神经元生成元本身能消费什么范围的输入"。

方案依据：`cell-cell/交叉比对/评判_P2A1顺序倒置修正_2026-07-21.md` §一——
P2-A1 原定义（标定 κ·q_skin）在 P2-A2 建皮肤之前字面上无对象可标定，已拆分
为 P2-A1a（本实验，纯生成元输入包络）→ P2-A2（三点皮肤）→ P2-A1b（皮肤-
生成元接口标定）。

判定标准（首轮粗网格，找边界不要求精确）：
  u_silent：最高的、全程零发生且未处于ACTIVE状态的档位（从未触发）
  u_on    ：第一个至少发生一次的档位
  u_work  ：n_occ≥1 且未持续ACTIVE的档位区间（有真实的开合周期）
  u_sat   ：第一个扫描结束时仍处于ACTIVE/REFRACTORY（从不退出）的档位
  u_unsafe：peak_pre_trace 出现 NaN/inf/负值的档位（安全性检查，预期不
            应触发；若触发需要单独处理，不能忽略）

扫描网格：4个数量级、13档，每档 5000 步观测预算（复用 T-P2AG-4/10 已验证
的衰减步数量级）。首轮目的是找粗略边界，非最终标定精度。
"""
import math
import sys

sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.structural_address import AddressRegistry
from tss.generators import scan_input_envelope, wrap_base_generator
from tss.relations import FROZEN_THERMAL_SITES

DT = 0.001
STEPS_PER_LEVEL = 5000
SITE_INDEX = FROZEN_THERMAL_SITES["t1_pair"]["a"]  # 28（冻结选点，不动态搜索）

U_LEVELS = [
    0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05,
    0.1, 0.2, 0.5, 1.0, 2.0, 5.0,
]


def build_generator():
    """每个档位调用一次，返回全新句柄——避免跨档位历史依赖污染比较。"""
    circuit = VariantCircuit()
    registry = AddressRegistry()
    return wrap_base_generator(circuit, SITE_INDEX, registry, polarity="warm")


def classify_boundaries(points):
    """事后边界分类——判据写在这里（实验脚本），不在工具函数里。"""
    u_silent = None
    u_on = None
    u_sat = None
    u_unsafe = []

    for p in points:
        is_silent = (p.n_occ == 0 and not p.ends_active)
        if is_silent:
            u_silent = p.u  # 保留遇到的最高静默档
        if p.n_occ >= 1 and u_on is None:
            u_on = p.u
        if p.ends_active and u_sat is None:
            u_sat = p.u
        if (math.isnan(p.peak_pre_trace) or math.isinf(p.peak_pre_trace)
                or p.peak_pre_trace < 0.0):
            u_unsafe.append(p.u)

    u_work_points = [p.u for p in points if p.n_occ >= 1 and not p.ends_active]
    return {
        "u_silent": u_silent,
        "u_on": u_on,
        "u_work_range": (min(u_work_points), max(u_work_points)) if u_work_points else None,
        "u_sat": u_sat,
        "u_unsafe": u_unsafe,
    }


def run():
    print("=" * 78)
    print("  P2-A1a：生成元核心输入包络扫描（首轮粗网格，13档 x 5000步）")
    print("=" * 78)

    points = scan_input_envelope(build_generator, U_LEVELS, DT, STEPS_PER_LEVEL)

    header = f"{'u':>10} | {'n_occ':>6} | {'l_first':>8} | {'mean_t_active':>14} | " \
             f"{'f_occ':>10} | {'peak_pre_trace':>15} | {'ends_active':>12}"
    print(header)
    print("-" * len(header))
    for p in points:
        l_first_str = f"{p.l_first}" if p.l_first is not None else "-"
        mta_str = f"{p.mean_t_active:.2f}" if p.mean_t_active is not None else "-"
        print(f"{p.u:>10.4f} | {p.n_occ:>6} | {l_first_str:>8} | {mta_str:>14} | "
              f"{p.f_occ:>10.6f} | {p.peak_pre_trace:>15.6f} | {str(p.ends_active):>12}")

    boundaries = classify_boundaries(points)
    print("\n" + "=" * 78)
    print("  边界分类结果")
    print("=" * 78)
    print(f"  u_silent   = {boundaries['u_silent']}")
    print(f"  u_on       = {boundaries['u_on']}")
    print(f"  u_work区间  = {boundaries['u_work_range']}")
    print(f"  u_sat      = {boundaries['u_sat']}")
    print(f"  u_unsafe   = {boundaries['u_unsafe']}"
          + ("（安全，未触发）" if not boundaries['u_unsafe'] else "（！需要处理）"))
    print("=" * 78)

    assert not boundaries['u_unsafe'], \
        f"检测到不安全档位（NaN/inf/负值），需要单独处理：{boundaries['u_unsafe']}"

    return points, boundaries


if __name__ == "__main__":
    run()
