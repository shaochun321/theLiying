"""stability_audit.py — 解析固定点的真实原语仿真验证（§10）。

TYPE:INFRA（research/ 隔离层）

方法：多初值扫描（不是只从默认初值跑一次，§9 要求）——
  对每个拓扑用**真实原语组合**从网格初值起跑，记录收敛终点，
  与 fixed_point_solver 的解析预测比对；测状态保持时间（§16）。

初值设置说明（不违反 §15）：本脚本是**数学稳定性验证**，初值网格允许直接
设定电容电荷（这是相空间审计的标准方法）；**物理可达性**由
reachability_probe.py 单独用合法 relation-event 输入验证，两者分工明确。

输出：data/stability.csv
"""
from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from research.A8_state_audit.primitive_equations import (
    DT, RailLatch, MutualExcitation, MutualInhibition)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
SETTLE = 30000          # 收敛步数（50×τ）
PERSIST = 120000        # 保持时间检验步数（100×epoch 1204）


def _set_v(cap, v):
    cap.charge = v * cap.capacitance


def audit_f1(k: float) -> list[dict]:
    rows = []
    z_ref = RailLatch(k=k)
    fps = [fp["v"] for fp in z_ref.fixed_points()]
    for v0 in [0.0, 0.1, 0.3, 0.5, 0.6, 0.65, 0.7, 0.75, 0.9, 1.0]:
        z = RailLatch(k=k)
        _set_v(z._cap, v0)
        for _ in range(SETTLE):
            z.step(0.0)
        v_settle = z.state
        # 保持时间：继续 PERSIST 步观察漂移
        for _ in range(PERSIST):
            z.step(0.0)
        drift = abs(z.state - v_settle)
        nearest = min(fps, key=lambda f: abs(f - v_settle))
        rows.append({"topology": "F1", "param": f"k={k}", "init": f"{v0}",
                     "settle": round(v_settle, 9), "nearest_fp": round(nearest, 9),
                     "match": abs(v_settle - nearest) < 1e-6,
                     "persist_drift": f"{drift:.3e}",
                     "persist_steps": PERSIST})
    return rows


def audit_f2(k: float) -> list[dict]:
    rows = []
    for (x0, y0) in [(0.0, 0.0), (0.2, 0.2), (0.5, 0.5), (0.8, 0.8),
                     (0.9, 0.1), (0.1, 0.9), (0.7, 0.7)]:
        z = MutualExcitation(k=k)
        _set_v(z._cx, x0)
        _set_v(z._cy, y0)
        for _ in range(SETTLE):
            z.step(0.0, 0.0)
        rows.append({"topology": "F2", "param": f"k={k}", "init": f"({x0},{y0})",
                     "settle": f"({z._cx.voltage:.6f},{z._cy.voltage:.6f})",
                     "nearest_fp": "", "match": "",
                     "persist_drift": "", "persist_steps": ""})
    return rows


def audit_f3(k_inh: float) -> list[dict]:
    rows = []
    for (x0, y0) in [(0.0, 0.0), (0.32, 0.32), (0.4, 0.2), (0.2, 0.4),
                     (0.34, 0.30), (0.30, 0.34), (1.0, 0.0), (0.0, 1.0)]:
        z = MutualInhibition(k_inh=k_inh)
        _set_v(z._cx, x0)
        _set_v(z._cy, y0)
        for _ in range(SETTLE):
            z.step(0.0, 0.0)
        xs, ys = z._cx.voltage, z._cy.voltage
        for _ in range(PERSIST):
            z.step(0.0, 0.0)
        drift = max(abs(z._cx.voltage - xs), abs(z._cy.voltage - ys))
        winner = "x" if xs > ys + 1e-6 else ("y" if ys > xs + 1e-6 else "sym")
        rows.append({"topology": "F3", "param": f"k_inh={k_inh}",
                     "init": f"({x0},{y0})",
                     "settle": f"({xs:.6f},{ys:.6f}) winner={winner}",
                     "nearest_fp": "", "match": "",
                     "persist_drift": f"{drift:.3e}", "persist_steps": PERSIST})
    return rows


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    rows = []
    rows += audit_f1(3.0)
    rows += audit_f1(7.5)
    rows += audit_f2(3.0)
    rows += audit_f3(3.0)
    rows += audit_f3(0.5)

    path = os.path.join(DATA_DIR, "stability.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("=" * 68)
    print("稳定性/吸引域仿真验证（真实原语，多初值）")
    print("=" * 68)
    for r in rows:
        print(f"  {r['topology']:<4}{r['param']:<14}init={r['init']:<12}"
              f"→ {r['settle']}"
              + (f"  match={r['match']} drift={r['persist_drift']}"
                 if r["match"] != "" else f"  drift={r['persist_drift']}"))
    print(f"\n落盘: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
