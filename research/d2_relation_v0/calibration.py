"""calibration.py — D2-0 Step3：关系结构 adaptive boundary 标定（cal 集）。

TYPE:INFRA（research/ 层）。

§22：关系结构是新物理结构，禁抄 G0 参数——本脚本重新实测
u_silent / u_work / u_sat / τ_decay（τ_rearm 属 Step5 closure 标定）。
§23/反馈 §十九：禁暴力网格；算法 = canonical→descend to fail→
ascend to fail→bracket（无非单调性证据不做二维补点）。

## 预注册（运行前冻结）

canonical 规则（端点锚定家族，非最优搜索）：g_rel 使 cal_C2_sim 的
  peak x_ρ ∈ [4.5, 5.5]（激活钳位 10 的线性区中点，2× 余量——与
  R1-2 g_v2 同风格）；二分逼近，评估次数计入预算。
u_silent：零驱动 8s 全程 max|x_ρ|（预期≈0，物理静息地板）。
u_work：canonical 下 cal_C2_sim 的 peak x_ρ。
u_sat：g 上探至 peak ≥ 9.9（钳位起点）的最小括号。
g_dead：g 下探至 peak < 100×u_silent+1e-6（响应湮灭）的最大括号。
τ_decay：canonical cal_C2_sim 驱动结束后 x 从峰值衰减到 peak/e 的
  物理时长；对照设计值 τ_cell=0.5 s（偏离>2× 则登记异常）。

## COMPUTE_BUDGET

  physical_trajectories=0; replays ≤ 16（评估计数硬断言）;
  n_parameter_points ≤ 16; interventions=0

复现入口：
  PYTHONIOENCODING=utf-8 python research/d2_relation_v0/calibration.py
"""
from __future__ import annotations

import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..')))

from d2_common import DATA, DT_G  # noqa: E402
from relation_physical_impl import (  # noqa: E402
    build_relation, load_port_windows, run_relation, step_relation)

MAX_EVALS = 16
_CAL_TRAJ = "cal_C2_sim"


def main() -> int:
    windows = load_port_windows()
    evals = {"n": 0}

    def peak_at(g: float) -> float:
        assert evals["n"] < MAX_EVALS, "COMPUTE_BUDGET 超限（≤16 评估）"
        evals["n"] += 1
        xs, _led, _p = run_relation(_CAL_TRAJ, g, windows=windows)
        pk = max(xs)
        print(f"  eval#{evals['n']:02d} g_rel={g:.6e} peak={pk:.4f}")
        return pk

    # u_silent（不计入 g 评估：零驱动同一结构一次运行）
    p0 = build_relation(g_rel=1.0)
    silent = 0.0
    for _ in range(8000):
        silent = max(silent, abs(step_relation(p0, 0.0, 0.0)))
    print(f"  u_silent = {silent:.3e}")

    # canonical 二分：从 g=1.0 起括号 [峰<4.5 → ×4 上探 | 峰>5.5 → /4 下探]
    g_lo, g_hi = None, None
    g = 1.0
    pk = peak_at(g)
    while pk < 4.5 or pk > 5.5:
        if pk < 4.5:
            g_lo = g
            if g_hi is None:
                g *= 4.0
            else:
                g = math.sqrt(g * g_hi)
        else:
            g_hi = g
            if g_lo is None:
                g /= 4.0
            else:
                g = math.sqrt(g * g_lo)
        pk = peak_at(g)
    g_canon, u_work = g, pk

    # 失败沿：上探 u_sat（peak≥9.9=钳位）、下探 g_dead（响应湮灭）
    g_sat = g_canon
    while peak_at(g_sat) < 9.9:
        g_sat *= 4.0
    g_dead = g_canon
    while peak_at(g_dead) > 100.0 * silent + 1e-6:
        g_dead /= 16.0

    # τ_decay：canonical 运行，驱动结束后衰减到 peak/e 的物理时长
    xs, led, _ = run_relation(_CAL_TRAJ, g_canon, windows=windows)
    da, _db = __import__("relation_physical_impl").drives_for(
        _CAL_TRAJ, windows)
    last_drive = max(k for k, s in enumerate(da) if s.value > 0)
    pk_k = max(range(len(xs)), key=lambda k: xs[k])
    target = xs[pk_k] / math.e
    k_e = next((k for k in range(max(pk_k, last_drive), len(xs))
                if xs[k] <= target), None)
    tau_decay = (k_e - max(pk_k, last_drive)) * DT_G if k_e else None

    out = {
        "parameter": "g_rel (relation transduction gain, frozen bundle "
                     "synapse_gain)",
        "physical_meaning": "phase-drive -> relation cell current gain; "
                            "x_rho must live in cell linear regime "
                            "(clamp 10)",
        "legal_region": {"lo_bracket_dead": g_dead, "hi_bracket_sat": g_sat,
                         "rule": "response above silent floor AND below "
                                 "activation clamp"},
        "failure_boundary": {"g_sat_bracket": g_sat, "g_dead_bracket": g_dead},
        "canonical_reference": {
            "g_rel": g_canon,
            "rule": "peak x(cal_C2_sim) in [4.5,5.5] (mid linear, "
                    "endpoint-anchoring family) — NOT optimum"},
        "provenance": "adaptive boundary search (canonical->descend->ascend"
                      "->bracket), evals<=16 (反馈§十九); tau_cell=0.5s "
                      "anchored Wang2002/delay-domain (impl Q3)",
        "measured": {"u_silent": silent, "u_work": u_work,
                     "tau_decay_s": tau_decay,
                     "tau_cell_design_s": 0.5,
                     "energy_drop_canonical": led["energy_drop"]},
        "n_evals": evals["n"],
    }
    with open(os.path.join(DATA, 'relation_calibration.json'), 'w',
              encoding='utf-8') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    tau_ok = tau_decay is not None and 0.25 <= tau_decay <= 1.0
    ok = (silent < 1e-6 and 4.5 <= u_work <= 5.5 and tau_ok
          and evals["n"] <= MAX_EVALS)
    print(f"\n  g_canon={g_canon:.6e} u_work={u_work:.3f} "
          f"tau_decay={tau_decay}s (design 0.5s) evals={evals['n']}")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
