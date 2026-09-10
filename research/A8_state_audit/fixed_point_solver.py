"""fixed_point_solver.py — F1-F4 固定点求解（§9，多初值+解析+区域穷举）。

TYPE:INFRA（research/ 隔离层）

方法（修订稿 §C 分类含边界固定点）：
  F1  1D 分段仿射 → 逐区解析
  F2  2D 分段仿射（4 区域）→ 区域穷举闭式解 + 一致性过滤
  F3  同 F2（背景驱动 vdd/r_supply 模式）
  F4  w 流函数符号扫描（边际连续统检测）

输出：data/fixed_points.csv
"""
from __future__ import annotations

import csv
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from research.A8_state_audit.primitive_equations import (
    DT, RailLatch, MutualExcitation, MutualInhibition, memristor_flow)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def solve_f1(k: float, capacitance: float = 1.0, r_leak: float = 0.6) -> list[dict]:
    z = RailLatch(k=k, capacitance=capacitance, r_leak=r_leak)
    out = []
    for fp in z.fixed_points():
        out.append({"topology": "F1", "param": f"k={k},C={capacitance}",
                    "x": round(fp["v"], 9), "y": "",
                    "type": fp["type"], "deriv_or_eigs": f"{fp['deriv']:.6f}",
                    "stability": fp["stability"]})
    return out


def solve_f2(k: float) -> list[dict]:
    """F2 区域穷举：x'=−ax+k·gm·max(0,y−θ)·Vr/C（连续近似，λ 换算回报）。

    区域 (x≷θ, y≷θ) 4 种，各区域内系统仿射，解 2×2 线性方程组，
    过滤解是否落在假设区域内；钳位边界点单独检查。
    """
    a = 1.0 / 0.6
    gm, vr, theta, clamp = 1.0, 1.0, 0.3, 1.0
    rows = []

    def eig_2x2(j11, j12, j21, j22):
        tr, det = j11 + j22, j11 * j22 - j12 * j21
        disc = tr * tr - 4 * det
        if disc >= 0:
            r = math.sqrt(disc)
            return (tr + r) / 2, (tr - r) / 2
        return complex(tr / 2, math.sqrt(-disc) / 2), complex(tr / 2, -math.sqrt(-disc) / 2)

    # 区域 LL（x<θ,y<θ）：x'=−ax, y'=−ay → (0,0)
    rows.append({"topology": "F2", "param": f"k={k}", "x": 0.0, "y": 0.0,
                 "type": "interior", "deriv_or_eigs": f"({-a:.3f},{-a:.3f})",
                 "stability": "stable"})

    b = k * gm * vr
    # 区域 HH（x,y>θ）：x'=−ax+b(y−θ)，对称解 x=y=s：−as+b(s−θ)=0 → s=bθ/(b−a)
    if b > a:
        s = b * theta / (b - a)
        if theta < s < clamp:
            e1, e2 = eig_2x2(-a, b, b, -a)   # 特征值 −a±b
            st = "unstable(saddle)" if (max(e1.real if isinstance(e1, complex) else e1,
                                            e2.real if isinstance(e2, complex) else e2) > 0) else "stable"
            rows.append({"topology": "F2", "param": f"k={k}", "x": round(s, 6),
                         "y": round(s, 6), "type": "interior",
                         "deriv_or_eigs": f"({-a+b:.3f},{-a-b:.3f})", "stability": st})
        # 钳位角 (1,1)：流入检查 −a·1+b(1−θ) > 0 ?
        if -a * clamp + b * (clamp - theta) > 0:
            rows.append({"topology": "F2", "param": f"k={k}", "x": clamp, "y": clamp,
                         "type": "boundary(clamp)", "deriv_or_eigs": "one-sided 0",
                         "stability": "stable(one-sided)"})
    # 非对称区域 HL（x>θ,y<θ）：x'=−ax（y<θ ⇒ 无供流）→ x→0 与 x>θ 矛盾 ⇒ 无固定点
    return rows


def solve_f3(k_inh: float, r_supply: float = 1.2) -> list[dict]:
    """F3 区域穷举（连续近似）：x'=−ax+(vdd−x)/(Rs·C)−k·gm·max(0,y−θ)。"""
    a = 1.0 / 0.6
    gm, vdd, theta, clamp = 1.0, 1.0, 0.3, 1.0
    s_ = 1.0 / r_supply
    rows = []
    # 基线（无抑制）：−ax+(vdd−x)s = 0 → x0 = vdd·s/(a+s)
    x0 = vdd * s_ / (a + s_)
    both_active = x0 > theta

    # 对称激活区（x,y>θ）：−ax+(vdd−x)s−k(x... 对称 x=y=s*：
    #   −a·s* + (vdd−s*)·s_ − k·gm·(s*−θ) = 0
    denom = a + s_ + k_inh * gm
    s_sym = (vdd * s_ + k_inh * gm * theta) / denom
    if s_sym > theta:
        # Jacobian（激活区）：J = [[−a−s_, −k·gm],[−k·gm, −a−s_]]
        e_sym = -a - s_ + k_inh * gm     # 反对称模态特征值（决定 pitchfork）
        e_com = -a - s_ - k_inh * gm
        st = "unstable(pitchfork)" if e_sym > 0 else "stable"
        rows.append({"topology": "F3", "param": f"k_inh={k_inh},Rs={r_supply}",
                     "x": round(s_sym, 6), "y": round(s_sym, 6), "type": "interior",
                     "deriv_or_eigs": f"({e_sym:.3f},{e_com:.3f})", "stability": st})
    # 赢者区（x>θ, y<θ）：x'=−ax+(vdd−x)s（y 不抑制 x），
    #                    y'=−ay+(vdd−y)s−k(x−θ)
    x_w = x0
    y_l = (vdd * s_ - k_inh * gm * (x_w - theta)) / (a + s_)
    if x_w > theta and y_l < theta:
        e1 = -a - s_        # x 方向
        e2 = -a - s_        # y 方向（y<θ ⇒ 无耦合项）
        rows.append({"topology": "F3", "param": f"k_inh={k_inh},Rs={r_supply}",
                     "x": round(x_w, 6), "y": round(max(y_l, 0.0), 6),
                     "type": "interior(winner-x)",
                     "deriv_or_eigs": f"({e1:.3f},{e2:.3f})", "stability": "stable"})
        rows.append({"topology": "F3", "param": f"k_inh={k_inh},Rs={r_supply}",
                     "x": round(max(y_l, 0.0), 6), "y": round(x_w, 6),
                     "type": "interior(winner-y)",
                     "deriv_or_eigs": f"({e1:.3f},{e2:.3f})", "stability": "stable"})
    return rows


def solve_f4(n_grid: int = 101) -> list[dict]:
    """F4：w 流函数符号结构（u=0 与 u=0.17 两种输入条件）。"""
    rows = []
    for u in (0.0, 0.17):
        signs = []
        for i in range(n_grid):
            w = i / (n_grid - 1)
            dw = memristor_flow(w, u)
            signs.append((w, dw))
        n_zero = sum(1 for _, d in signs if d == 0.0)
        n_pos = sum(1 for _, d in signs if d > 0.0)
        n_neg = sum(1 for _, d in signs if d < 0.0)
        if u == 0.0 and n_zero == n_grid:
            rows.append({"topology": "F4", "param": f"u={u}", "x": "[0,1]", "y": "",
                         "type": "continuum(marginal)",
                         "deriv_or_eigs": "1.0(=marginal)",
                         "stability": "marginal — M2 慢变量签名，非 M3"})
        else:
            rows.append({"topology": "F4", "param": f"u={u}",
                         "x": f"zeros={n_zero}/{n_grid}", "y": "",
                         "type": f"flow(+:{n_pos} −:{n_neg})",
                         "deriv_or_eigs": "monotone" if n_neg == 0 else "mixed",
                         "stability": ("single attractor at window edge"
                                        if n_neg == 0 and n_pos > 0 else "see scan")})
    return rows


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    rows = []
    for k in (1.0, 2.0, 3.0, 7.5):
        rows += solve_f1(k)
    rows += solve_f1(3.0, capacitance=0.001, r_leak=600.0)   # 小电容变体（同 τ）
    for k in (1.0, 3.0):
        rows += solve_f2(k)
    for k_inh in (0.5, 3.0):
        rows += solve_f3(k_inh)
    rows += solve_f4()

    path = os.path.join(DATA_DIR, "fixed_points.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["topology", "param", "x", "y", "type",
                                          "deriv_or_eigs", "stability"])
        w.writeheader()
        w.writerows(rows)

    print("=" * 68)
    print("固定点求解（F1-F4）")
    print("=" * 68)
    for r in rows:
        print(f"  {r['topology']:<4} {r['param']:<20} ({r['x']},{r['y']})"
              f" {r['type']:<22} eig={r['deriv_or_eigs']:<20} {r['stability']}")
    print(f"\n落盘: {path}  ({len(rows)} 行)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
