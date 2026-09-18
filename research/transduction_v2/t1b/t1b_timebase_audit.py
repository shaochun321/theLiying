"""t1b_timebase_audit.py — timebase 合同实测：A 的 dt 不变性 + B 的 dt-aware
收敛 +（负控制）naive 每步差分的 dt 依赖失效。

TYPE:INFRA。依据：外部《T1-B 方案》§9-§11 + 合同 C2
（Δt_ext=1 s；World dt=积分粒度）。

## 设计
  同一物理 episode（N=5, κ=0.05, r_leak=200, 源 E=300/P=1.0,
  T_phys=2000 s）用积分 dt∈{1, 0.1, 0.01} 三档跑（W1 dt 收敛机制复用），
  边界在整秒物理时刻 t_ext=k·1s 采样为 Y(k)。
  - Candidate A：u_A(k)=S·Y(k)——AMPLITUDE_PORT_DT_INVARIANT 判据：
    跨档相对差随 dt 细化收敛且 ≤ 边界自身收敛量级。
  - Candidate B（dt-aware，合同式）：u_B(k)=g·(Y(k)−Y(k−1))/Δt_ext，
    Δt_ext=1 s 固定，与积分 dt 无关——判据：跨档收敛。
  - 负控制 naive-B：u=g·ΔY(每积分步)——预期随 dt 细化按 ~dt 比例缩小
    ⇒ RATE_PORT_DT_DEPENDENT_FAIL（证明 §10 升级的必要性）。

输出：data/timebase_convergence.csv, data/t1b_timebase.json
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from t1b_common import DT_EXT, G_CANON, S_CANON  # noqa: E402
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..',
                                                'world_v2')))
from world_v2_core import (  # noqa: E402
    SourceSpec, WorldEpisode, WorldEpisodeSpec)

DATA_DIR = os.path.join(_HERE, 'data')
T_PHYS = 2000.0


def run_at_dt(dt: float):
    steps = int(round(T_PHYS / dt))
    sp = WorldEpisodeSpec(
        episode_id=f"tb_dt{dt:g}", seed=-1, n_nodes=5,
        kappas=(0.05,) * 4, r_leak_ambient=200.0,
        sources=(SourceSpec(0, 300.0, 1.0, 0),),
        boundary_config="REDUCED", boundary_nodes=(0,),
        dt=dt, t_total=steps)
    ep = WorldEpisode(sp)
    y_sec, naive_last = [], []
    per = int(round(1.0 / dt))
    prev_step_y = None
    for t in range(steps):
        ep.step()
        y = ep.boundary_frame()[0]
        if (t + 1) % per == 0:
            y_sec.append(y)                       # 整秒采样
            naive_last.append(0.0 if prev_step_y is None
                              else G_CANON * (y - prev_step_y))
        prev_step_y = y
    return y_sec, naive_last


def series_reldiff(a, b):
    num = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))
    den = math.sqrt(sum(y * y for y in b) / len(b))
    return num / max(den, 1e-30)


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 78)
    print("T1-B timebase 审计 — A dt 不变性 / B dt-aware 收敛 / naive 负控制")
    print("=" * 78)
    data = {dt: run_at_dt(dt) for dt in (1.0, 0.1, 0.01)}

    def u_a(y_sec):
        return [S_CANON * y for y in y_sec]

    def u_b(y_sec):
        out, prev = [], None
        for y in y_sec:
            out.append(0.0 if prev is None
                       else G_CANON * (y - prev) / DT_EXT)
            prev = y
        return out

    rows, summary = [], {}
    for kind, fn in (("boundary", lambda ys: ys), ("A", u_a), ("B", u_b)):
        s1, s01, s001 = (fn(data[dt][0]) for dt in (1.0, 0.1, 0.01))
        d10 = series_reldiff(s1, s01)
        d01 = series_reldiff(s01, s001)
        conv = d01 < d10 and d01 < 0.01
        summary[kind] = {"diff_1.0_to_0.1": d10, "diff_0.1_to_0.01": d01,
                         "converges": conv}
        rows.append({"series": kind, "diff_1_01": d10, "diff_01_001": d01,
                     "converges": conv})
        print(f"[{kind:>8}] 1.0→0.1={d10:.3e}  0.1→0.01={d01:.3e}  "
              f"{'收敛 ✓' if conv else 'FAIL'}")

    # 负控制：naive 每步差分（同物理时刻取"最后一个积分步差分"）
    n1, n01, n001 = (data[dt][1] for dt in (1.0, 0.1, 0.01))
    r10 = series_reldiff(n01, n1)
    r01 = series_reldiff(n001, n01)
    m10 = (math.sqrt(sum(v * v for v in n01) / len(n01))
           / max(math.sqrt(sum(v * v for v in n1) / len(n1)), 1e-30))
    m01 = (math.sqrt(sum(v * v for v in n001) / len(n001))
           / max(math.sqrt(sum(v * v for v in n01) / len(n01)), 1e-30))
    naive_fails = m10 < 0.5 and m01 < 0.5   # 幅值随 dt 缩水 ⇒ dt 依赖
    print(f"[naive-B] 幅值比 dt0.1/dt1={m10:.3f}  dt0.01/dt0.1={m01:.3f} "
          f"⇒ {'RATE_PORT_DT_DEPENDENT_FAIL（负控制成立：naive 形式必须弃用）' if naive_fails else '未复现 dt 依赖（需查）'}")

    verdicts = {
        "AMPLITUDE_PORT_DT_INVARIANT": summary["A"]["converges"],
        "RATE_PORT_DT_AWARE_CONVERGES": summary["B"]["converges"],
        "NAIVE_RATE_DT_DEPENDENT_FAIL_CONFIRMED": naive_fails,
    }
    ok = all(verdicts.values())
    print(f"\ntimebase 三判据 ⇒ {'全 PASS' if ok else 'FAIL'}")
    with open(os.path.join(DATA_DIR, "timebase_convergence.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(DATA_DIR, "t1b_timebase.json"), "w",
              encoding="utf-8") as f:
        json.dump({"summary": summary, "naive_magnitude_ratio":
                   {"0.1/1.0": m10, "0.01/0.1": m01},
                   "naive_series_reldiff": {"0.1vs1": r10, "0.01vs0.1": r01},
                   "verdicts": verdicts}, f, indent=2)
    print("落盘: timebase_convergence.csv / t1b_timebase.json")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
