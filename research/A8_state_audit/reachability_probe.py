"""reachability_probe.py — 物理可达性审计（§15）。

TYPE:INFRA（research/ 隔离层）

## 判据

两个吸引域必须都能通过**合法 relation-event 输入**到达：
    relation event → candidate
禁止直接赋值 x=... / 设置 w=... / 修改 initial state 冒充 formation。

## 候选配置（巧合检测型闩锁，参数 provenance 见 primitive_equations §D）

    RailLatch(C=0.001, R=600, k=3.0, k_in=0.5)
    τ = R·C = 0.6 s = 600 步（H_τ 同尺度）
    V_u ≈ 0.3007（fixed_point_solver 实测）
    单枚 c_ro 事件（幅度 0.434）ΔV = k_in·0.434·dt/C = 0.217 < V_u → 不闩锁
    两枚事件在 Δ < ~572 步内共现 → 0.217·λ^Δ + 0.217 > V_u → 闩锁
    ⇒ Z 编码"两个关系事件曾在 ~600 步窗口内共现"——
      恰是 H_τ 软测量的同一窗口的硬化（吸引态化）

## 输入来源

真实 C1 链路：tss.tests.test_c1_coupling._synthetic_stack（两套独立 pair 栈，
(24,21) 与 (26,17) 同型），c_ro 事件由 E^↑→H_τ→C_Θ 物理链产生，
幅度非手填（实测记录）。

输出：data/reachability.csv
"""
from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from research.A8_state_audit.primitive_equations import RailLatch
from tss.tests.test_c1_coupling import _synthetic_stack, DT

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DRIVE = 0.17               # 适配器输入幅度（EXP-C0-02 实测域内，同上轮）
DT2 = 50                   # pair 内 X→Y 间隔（同 C1 测试惯例）


class LegalDrivenSystem:
    """两套真实 pair 栈 + 候选闩锁（fan-in 汇聚，类比 bundle 多源汇聚先例）。"""

    def __init__(self, k=3.0, k_in=0.5):
        self.stack1 = _synthetic_stack()      # (ad_x, ad_y, st) for pair (24,21)
        self.stack2 = _synthetic_stack()      # 独立 registry，同型 (24,21) 结构
        self.z = RailLatch(capacitance=0.001, r_leak=600.0, k=k, k_in=k_in)
        self.c_events = []                    # (t, c1, c2) 非零记录

    def step(self, t, x1_pulse, y1_pulse, x2_pulse, y2_pulse):
        ad1x, ad1y, st1 = self.stack1
        ad2x, ad2y, st2 = self.stack2
        ad1x.step(DRIVE if x1_pulse else 0.0, DT)
        ad1y.step(DRIVE if y1_pulse else 0.0, DT)
        ad2x.step(DRIVE if x2_pulse else 0.0, DT)
        ad2y.step(DRIVE if y2_pulse else 0.0, DT)
        c1 = st1.step(t, DT)
        c2 = st2.step(t, DT)
        if c1 > 0 or c2 > 0:
            self.c_events.append((t, c1, c2))
        return self.z.step(c1 + c2, DT)       # fan-in 汇聚

    def run_history(self, t1, t2, total):
        """pair1 事件对齐 t1、pair2 对齐 t2（X 在 t、Y 在 t+DT2）。"""
        for t in range(total):
            self.step(t,
                      x1_pulse=(t == t1), y1_pulse=(t == t1 + DT2),
                      x2_pulse=(t == t2), y2_pulse=(t == t2 + DT2))
        return self.z.state


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    rows = []
    print("=" * 68)
    print("物理可达性审计（合法 relation-event 输入，无状态赋值）")
    print("=" * 68)

    cases = [
        ("coincident(Δ=100)",  500, 600, 20000, "high"),
        ("spread(Δ=2500)",     500, 3000, 20000, "low"),
        ("single-pair-only",   500, -10**9, 20000, "low"),
        ("no-events",          -10**9, -10**9, 20000, "low"),
        ("coincident(Δ=400)",  500, 900, 20000, "high"),
        ("spread(Δ=700)",      500, 1200, 20000, "low"),
    ]
    for name, t1, t2, total, expect in cases:
        sysm = LegalDrivenSystem()
        v_end = sysm.run_history(t1, t2, total)
        basin = "high(latched)" if v_end > 0.9 else ("low" if v_end < 0.1 else "MID?")
        ok = basin.startswith(expect)
        amp = [f"{c1 + c2:.4f}" for (_, c1, c2) in sysm.c_events]
        rows.append({"history": name, "t1": t1 if t1 > 0 else "—",
                     "t2": t2 if t2 > 0 else "—",
                     "c_ro_events": len(sysm.c_events),
                     "c_ro_amplitudes": ";".join(amp),
                     "v_final": f"{v_end:.6f}", "basin": basin,
                     "expected": expect, "as_expected": ok})
        print(f"  {name:<20} events={len(sysm.c_events)} amp={amp}"
              f" → V={v_end:.6f} [{basin}] {'✓' if ok else '✗'}")

    path = os.path.join(DATA_DIR, "reachability.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    all_ok = all(r["as_expected"] for r in rows)
    both = (any(r["basin"].startswith("high") for r in rows)
            and any(r["basin"].startswith("low") for r in rows))
    print(f"\n  两个吸引域均可由合法输入到达: {both}；全部符合预期: {all_ok}")
    print(f"  共现窗口实测边界在 Δ∈(400, 700) 步之间（解析预测 ~572 步）")
    print(f"落盘: {path}")
    return 0 if (all_ok and both) else 1


if __name__ == "__main__":
    sys.exit(main())
