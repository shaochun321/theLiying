"""calibration_rc2.py — D2-1 StepC：𝒞_{ρ₂} adaptive boundary 标定。

TYPE:INFRA（research/ 层）。

§10：𝒞_{ρ₂} 是新物理实例，禁抄 D2-0 资格参数——本脚本新鲜实测
u_silent / u_work / u_sat / g_dead / τ_decay2（χ_ρ₂ closure 参数属
final_qualification 推导）。§23：canonical→lower fail→upper fail→
bracket，禁二维全网格，只求 legal working region 非 optimal。

## 预注册（运行前冻结）

标定锚 = rc_main：ρ_a（cal_C3_m 的 χ_ρ^(1)，窗 [2617,3971)）
        + χ_23^(0)（s23_ov，窗 [2927,3566)）——重叠 633 步。
canonical 规则（端点锚定家族，D2-0 同风格）：g_rel2 使 rc_main 的
  peak x_ρ₂ ∈ [4.5, 5.5]（钳位 10 的线性区中点，2× 余量）；二分逼近。
起点 g=0.25 —— 仅作搜索起点使用（D2-0 canonical 的量级先验），
  是否成为 canonical 完全由本轮 rc_main 实测决定，非抄用。
u_silent：零驱动 8s 全程 max|x_ρ₂|（物理静息地板，不计入评估）。
u_sat：g 上探至 peak ≥ 9.9 的最小括号。
g_dead：g 下探至 peak < 100×u_silent+1e-6 的最大括号。
τ_decay2：canonical 下 rc_main 驱动结束后 x 从峰值衰减到 peak/e 的
  物理时长；对照设计值 τ_cell=0.5 s（偏离>2× 登记异常）。

## COMPUTE_BUDGET

  physical_trajectories=0; 标定参数点（**不同 g 值**）≤ 10（§22
  relation-2 calibration points，硬断言；同一 g 的重复评估=确定性重放，
  缓存去重不计新点）; interventions=0
  dead 下探步长 ÷64（程序性最小细化选择，§23——非资格数值）

## 诚实登记：首次运行中止（2026-09-21）

  首版脚本 sat/dead 循环对已知 canonical 点重复评估 3 次，10 次评估
  预算在 dead 搜索前耗尽（AssertionError 中止，未写任何标定输出）。
  该次运行探测的**不同参数点=8 个**，全部被本版确定性重放覆盖；
  修正=去重缓存+dead 步长 ÷64。累计不同参数点 ≤10 不变。

## hold 纪律

  本脚本只读 rc_main（ρ_a + s23_ov）——hold6 案例（H1~H6）零接触。

复现入口：
  PYTHONIOENCODING=utf-8 python research/d2_recursive_v1/calibration_rc2.py
"""
from __future__ import annotations

import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from d21_common import (  # noqa: E402
    DATA, DT_G, RHO_MAIN_TRAJ, load_relation_ports, load_site23_windows)
from recursive_physical_impl import (  # noqa: E402
    build_relation2, recursive_drives, run_relation2, step_relation2)

MAX_EVALS = 10
_CAL_SITE23 = "s23_ov"


def main() -> int:
    rho = load_relation_ports()[RHO_MAIN_TRAJ]
    s23 = load_site23_windows()[_CAL_SITE23]
    probed = {}   # g → peak（确定性重放去重：同一点不计新预算）

    def peak_at(g: float) -> float:
        if g in probed:
            return probed[g]
        assert len(probed) < MAX_EVALS, "COMPUTE_BUDGET 超限（≤10 参数点）"
        xs, _led, _p = run_relation2([rho], s23, g)
        pk = max(xs)
        probed[g] = pk
        print(f"  point#{len(probed):02d} g_rel2={g:.6e} peak={pk:.4f}")
        return pk

    # u_silent（不计入 g 评估：零驱动一次运行）
    p0 = build_relation2(g_rel2=1.0)
    silent = 0.0
    for _ in range(8000):
        silent = max(silent, abs(step_relation2(p0, 0.0, 0.0)))
    print(f"  u_silent = {silent:.3e}")

    # canonical 二分（起点 0.25 = 量级先验，非抄用）
    g_lo, g_hi = None, None
    g = 0.25
    pk = peak_at(g)
    while pk < 4.5 or pk > 5.5:
        if pk < 4.5:
            g_lo = g
            g = g * 4.0 if g_hi is None else math.sqrt(g * g_hi)
        else:
            g_hi = g
            g = g / 4.0 if g_lo is None else math.sqrt(g * g_lo)
        pk = peak_at(g)
    g_canon, u_work = g, pk

    # 失败沿：上探 u_sat（钳位）、下探 g_dead（响应湮灭；步长 ÷64）
    g_sat = g_canon
    while peak_at(g_sat) < 9.9:
        g_sat *= 4.0
    g_dead = g_canon
    while peak_at(g_dead) > 100.0 * silent + 1e-6:
        g_dead /= 64.0

    # τ_decay2：canonical 运行，驱动结束后衰减到 peak/e 的物理时长
    xs, led, _ = run_relation2([rho], s23, g_canon)
    dr, dc = recursive_drives([rho], s23)
    last_drive = max(k for k in range(len(dr))
                     if dr[k].value > 0 or dc[k].value > 0)
    pk_k = max(range(len(xs)), key=lambda k: xs[k])
    target = xs[pk_k] / math.e
    k0 = max(pk_k, last_drive)
    k_e = next((k for k in range(k0, len(xs)) if xs[k] <= target), None)
    tau_decay2 = (k_e - k0) * DT_G if k_e else None

    out = {
        "parameter": "g_rel2 (recursive relation transduction gain, frozen "
                     "bundle synapse_gain, NEW physical instance)",
        "physical_meaning": "phase-drive (depth-1 rho + depth-0 site23) -> "
                            "relation cell 2 current gain; x_rho2 in cell "
                            "linear regime (clamp 10)",
        "anchor": {"rho": rho.occurrence_id, "rho_window": [rho.t_up,
                                                            rho.t_rearm],
                   "site23": _CAL_SITE23,
                   "s23_window": [s23[0].t_up, s23[0].t_rearm]},
        "legal_region": {"lo_bracket_dead": g_dead, "hi_bracket_sat": g_sat,
                         "rule": "response above silent floor AND below "
                                 "activation clamp"},
        "canonical_reference": {
            "g_rel2": g_canon,
            "rule": "peak x(rc_main) in [4.5,5.5] (mid linear, "
                    "endpoint-anchoring family) — NOT optimum; freshly "
                    "measured, D2-0 value NOT copied as qualification"},
        "provenance": "adaptive boundary search (canonical->descend->ascend"
                      "->bracket), distinct parameter points<=10 (§22/§23); "
                      "tau_cell=0.5s anchored Wang2002/input-window-domain "
                      "(impl Q3)",
        "provenance_note": "first run 2026-09-21 aborted at budget assert "
                           "(duplicate evaluations of known canonical point "
                           "in sat/dead loops); probed 8 distinct points, "
                           "all deterministically replayed by this run; fix "
                           "= dedupe cache + dead step /64; no output was "
                           "written by the aborted run",
        "measured": {"u_silent": silent, "u_work": u_work,
                     "tau_decay2_s": tau_decay2,
                     "tau_cell_design_s": 0.5,
                     "energy_drop_canonical": led["energy_drop"]},
        "n_parameter_points": len(probed),
    }
    with open(os.path.join(DATA, 'relation2_calibration.json'), 'w',
              encoding='utf-8') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    tau_ok = tau_decay2 is not None and 0.25 <= tau_decay2 <= 1.0
    ok = (silent < 1e-6 and 4.5 <= u_work <= 5.5 and tau_ok
          and len(probed) <= MAX_EVALS)
    print(f"\n  g_canon2={g_canon:.6e} u_work={u_work:.3f} "
          f"tau_decay2={tau_decay2}s (design 0.5s) points={len(probed)}")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
