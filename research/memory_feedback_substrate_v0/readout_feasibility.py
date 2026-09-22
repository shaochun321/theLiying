"""readout_feasibility.py — MFS0-E0 Step C2：M5 可行性的开工前解析判定。

TYPE:INFRA（research/ 层；production READ_ONLY）。

方案 §13.1（关键门）：给定 w0=0.90 与预期最小 Δw_min，**先解析计算**
G(w)、ΔG/G、ΔI 与下游最小理论 response 差，在主 factorial 之前回答

    ExpectedSignal_Q > epsilon_Q ?

解析上不可测 ⇒ READOUT_FEASIBILITY_FAIL，停止；**不得运行以后再调 w0**
（R-4 NO_RUNTIME_W0_SEARCH）。

## 为什么这道门必须在 factorial 之前

我方评判 E-4：LIM-RPREC-READOUT-001 已定量证明 `G(w)=1/(10−9.9w)` 的双曲
形式在低 w 端把相对效应压掉一个数量级（w≈0.109 处 ΔG/G=0.117% ≪
Δw/w=0.97%），且该压缩**与束数无关**（N-不变，多束并行读出被否证）。
R-4 选 w0=0.90 正是为了离开那个工作点。本脚本把"离开得够不够"算出来，
而不是跑完 factorial 才发现 M4 PASS 但 M5 FAIL（终态 E）。

## 预期 Δw 的来源（不引入新自由参数）

用 Step A / Step B 已资格化的**实测包络**做时间积分：

    I_write(k) = FET_e.conduct(e(k)) · FET_M.conduct(M(k))
    Δw         = −0.5 · Σ_k I_write(k) · dt          (WRITE_DT_CORRECTION)

e(k) 取 Step A 的 W=1 臂，M(k) 取 Step B 的 Δ=1 臂按候选 later 时点平移。
对四个合法 NEAR 候选各算一次，给 Step D 提供选点依据（本批不选点）。

运行：cd research/memory_feedback_substrate_v0 && python readout_feasibility.py
"""
from __future__ import annotations

import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import mfs0_common as M  # noqa: E402
import eligibility_physical as EA  # noqa: E402
import modulation_physical as MB  # noqa: E402
from nexus_v1.components.semiconductor import MOSFET  # noqa: E402
from persistent_state_audit import query_response, rms_diff  # noqa: E402

# LIM-RPREC-READOUT-001 的工作点（对照基准，degradation_registry.md:403-437）
W_LIM_RPREC = 0.109
R_MIN, R_MAX = 0.1, 10.0


def rel_sensitivity(w: float) -> float:
    """dG/G per unit dw = (r_max−r_min)/R(w)，R(w)=r_min+(r_max−r_min)(1−w)。"""
    r = R_MIN + (R_MAX - R_MIN) * (1.0 - w)
    return (R_MAX - R_MIN) / r


def abs_sensitivity(w: float) -> float:
    """dG/dw = (r_max−r_min)/R(w)^2。"""
    r = R_MIN + (R_MAX - R_MIN) * (1.0 - w)
    return (R_MAX - R_MIN) / (r * r)


def expected_dw(e_trace, delta_tid: str, t_total: int) -> dict:
    """按 later 时点算一次写入的预期 Δw（解析积分实测包络）。"""
    wins = M.delta_windows(delta_tid)
    drive = M.drive_from_ports(wins, t_total)
    p = M.build_modulation(f"feas_{delta_tid}")
    fe = MOSFET(v_threshold=M.FET_V_THRESHOLD, gm=M.FET_GM)
    fm = MOSFET(v_threshold=M.FET_V_THRESHOLD, gm=M.FET_GM)
    integral = 0.0
    steps_writing = 0
    i_peak = 0.0
    for k in range(t_total):
        m = M.step_modulation(p, drive[k].value)
        e = e_trace[k] if k < len(e_trace) else 0.0
        i_w = fe.conduct(e) * fm.conduct(m)
        if i_w > 0.0:
            steps_writing += 1
            i_peak = max(i_peak, i_w)
            integral += i_w * M.DT_G
    dw = -0.5 * integral
    return {"delta_tid": delta_tid,
            "delta_window": [wins[0].t_up, wins[0].t_rearm],
            "steps_with_nonzero_write_current": steps_writing,
            "I_write_peak": i_peak,
            "integral_I_dt": integral,
            "expected_dw": dw,
            "expected_abs_dw": abs(dw)}


def main() -> int:
    M.assert_no_step_era_import()
    M.ledger_add("persistent_baseline", "stepC2_readout_feasibility",
                 "analytic + numeric readout feasibility (plan §13.1)")

    w0 = M.INITIAL_W

    # ── 1. 解析灵敏度对照 ──
    rel_w0 = rel_sensitivity(w0)
    rel_lim = rel_sensitivity(W_LIM_RPREC)
    abs_w0 = abs_sensitivity(w0)
    abs_lim = abs_sensitivity(W_LIM_RPREC)

    # ── 2. 预期 Δw（四个合法 NEAR 候选，用实测包络积分）──
    M.ledger_add("persistent_baseline", "stepC2_e_envelope",
                 "re-run of the Step A W=1 arm to obtain e(t) for integration")
    e_arm = EA.run_arm(True, M.T_TOTAL_STEPB)
    e_trace = e_arm["e"]

    e_write_win = M.window_above(e_arm["i_gate"], 0.0)
    candidates = []
    for tid in ("s23_ov", "s23_hold_timing", "s23_lag", "s23_far_b"):
        try:
            r = expected_dw(e_trace, tid, M.T_TOTAL_STEPB)
        except KeyError:
            continue
        r["inside_e_write_window"] = (e_write_win[0] <= r["delta_window"][0]
                                      <= e_write_win[1])
        candidates.append(r)

    usable = [c for c in candidates if c["expected_abs_dw"] > 0.0]
    dw_min = min((c["expected_abs_dw"] for c in usable), default=0.0)
    dw_max = max((c["expected_abs_dw"] for c in usable), default=0.0)

    # ── 3. 数值：把预期 Δw 送进真实读出链，测 response 差 ──
    base = query_response(w0)
    sham = query_response(w0)                 # sham-repeat：同 w 重跑
    sham_diff = rms_diff(base, sham)          # replay floor 的直接测量
    resp = []
    for dw in (dw_min, dw_max):
        if dw <= 0.0:
            continue
        probe = query_response(w0 - dw)
        g_a, g_b = M.conductance(w0), M.conductance(w0 - dw)
        exact = (g_b - g_a) / g_a
        linear = -rel_w0 * dw
        resp.append({
            "delta_w": dw,
            "rms_response_diff": rms_diff(base, probe),
            "relative_dG_over_G_exact": exact,
            "relative_dG_over_G_linear_extrapolation": linear,
            "linear_approximation_valid": abs(linear) < 0.1,
            "note": ("linear extrapolation rel_w0*dw is only valid for small "
                     "dw; G(w) is hyperbolic, so at this dw the exact ratio "
                     "governs" if abs(linear) >= 0.1 else "")})

    # ── 4. epsilon_Q 冻结（预注册 deferred_to_step_C 的兑现）──
    # 方案 §18 优先级第一条：deterministic replay floor。本系统 replay
    # 逐位一致（D2-1 M6；本脚本 sham_diff 直接实测），故 floor = 0 ⇒
    # 退到数值精度地板。取 EPSILON_NUM，与 Posterior-0 同口径。
    eps_q = M.EPSILON_NUM
    signal = min((r["rms_response_diff"] for r in resp), default=0.0)
    feasible = signal > eps_q

    out = {
        "step": "C2",
        "gate": "READOUT_FEASIBILITY (plan §13.1) — decided BEFORE factorial",
        "w0": w0,
        "analytic_sensitivity": {
            "G_w0": M.conductance(w0),
            "R_w0": R_MIN + (R_MAX - R_MIN) * (1.0 - w0),
            "relative_dG_over_G_per_dw_at_w0": rel_w0,
            "relative_dG_over_G_per_dw_at_LIM_RPREC_point": rel_lim,
            "relative_improvement_vs_LIM_RPREC": rel_w0 / rel_lim,
            "absolute_dG_dw_at_w0": abs_w0,
            "absolute_dG_dw_at_LIM_RPREC_point": abs_lim,
            "absolute_improvement_vs_LIM_RPREC": abs_w0 / abs_lim,
            "honest_note":
                "The relative-effect improvement from moving w0 0.109 -> 0.90 "
                f"is {rel_w0 / rel_lim:.2f}x, NOT three orders of magnitude. "
                "The often-quoted dG/dw = 990 belongs to w -> 1.0 (R -> "
                "r_min = 0.1), not to w0 = 0.90 (R = 1.09). Our own critique "
                "quoted the w->1.0 limit; the operative number here is the "
                f"{rel_w0 / rel_lim:.2f}x relative gain.",
        },
        "lim_rprec_comparison": {
            "registry": "cell-cell/docs/degradation_registry.md "
                        "LIM-RPREC-READOUT-001",
            "its_measured_dG_over_G": 0.00117,
            "its_threshold": 0.01,
            "why_MFS0_is_not_bound_by_that_threshold":
                "LIM-RPREC's 1% is a PRE-REGISTERED EFFECT-SIZE criterion "
                "inherited from the r_prec round, where the readout competed "
                "with training-period integration dilution (stage B, 35.8x) "
                "in a live learning loop. MFS0's epsilon_Q is derived instead "
                "from plan §18's first priority — the deterministic replay "
                "floor — which this system measures as EXACTLY ZERO "
                f"(sham-repeat RMS = {sham_diff:.3e}). Any non-zero response "
                "difference is therefore resolvable here. This is a "
                "difference in what the threshold MEANS, not a relaxation of "
                "it.",
        },
        "expected_dw_from_measured_envelopes": {
            "method": "dw = -0.5 * sum_k conduct_e(e_k) * conduct_M(M_k) * dt "
                      "(WRITE_DT_CORRECTION applied)",
            "e_source": "Step A W=1 arm (qualified)",
            "M_source": "Step B Delta=1 chain, per candidate later timing",
            "e_write_reachable_window": list(e_write_win),
            "candidates": candidates,
            "expected_abs_dw_range": [dw_min, dw_max],
        },
        "numeric_readout": {
            "sham_repeat_rms": sham_diff,
            "replay_floor_is_exactly_zero": sham_diff == 0.0,
            "probes": resp,
        },
        "epsilon_Q_frozen_here": {
            "value": eps_q,
            "basis": "plan §18 priority 1 (deterministic replay floor) "
                     "measured as exactly 0 -> fall back to numeric precision "
                     "floor 1e-6, same convention as Posterior-0 EPSILON_NUM",
            "applies_to": "RMS of the readout membrane-voltage trajectory "
                          "difference under an identical Q",
        },
        "READOUT_FEASIBILITY": "PASS" if feasible else "FAIL",
        "verdict_note":
            ("Expected signal exceeds epsilon_Q — Step D/E may proceed once "
             "this batch is signed off."
             if feasible else
             "Expected signal does not clear epsilon_Q — READOUT_FEASIBILITY_"
             "FAIL; stop before the factorial and do NOT retune w0 (R-4)."),
    }
    M.write_json('readout_feasibility.json', out)

    print("MFS0-E0 Step C2 — Readout feasibility (decided BEFORE factorial)")
    print(f"  w0 = {w0}   R = {out['analytic_sensitivity']['R_w0']:.4f}   "
          f"G = {out['analytic_sensitivity']['G_w0']:.6f}")
    print(f"  relative dG/G per dw : {rel_w0:.4f}  (at LIM-RPREC point "
          f"{rel_lim:.4f})  -> {rel_w0 / rel_lim:.2f}x improvement")
    print(f"  absolute dG/dw       : {abs_w0:.4f}  (at LIM-RPREC point "
          f"{abs_lim:.4f})  -> {abs_w0 / abs_lim:.2f}x")
    print(f"  e write-reach window : {list(e_write_win)}")
    print("  expected |dw| per NEAR candidate:")
    for c in candidates:
        print(f"      {c['delta_tid']:<18} win={c['delta_window']}  "
              f"steps={c['steps_with_nonzero_write_current']:>4}  "
              f"I_peak={c['I_write_peak']:.4f}  "
              f"|dw|={c['expected_abs_dw']:.6e}  "
              f"in_e_win={c['inside_e_write_window']}")
    print(f"  sham-repeat RMS      : {sham_diff:.3e}  "
          f"(replay floor exactly zero = {sham_diff == 0.0})")
    for r in resp:
        flag = "" if r["linear_approximation_valid"] else "  [linear n/a]"
        print(f"  probe dw={r['delta_w']:.6e} -> RMS "
              f"{r['rms_response_diff']:.6e}   "
              f"dG/G(exact)={r['relative_dG_over_G_exact']:+.4f}   "
              f"(linear {r['relative_dG_over_G_linear_extrapolation']:+.4f})"
              f"{flag}")
    print(f"  epsilon_Q (frozen)   : {eps_q:.0e}")
    print(f"\n  READOUT_FEASIBILITY = {out['READOUT_FEASIBILITY']}")
    return 0 if feasible else 1


if __name__ == '__main__':
    raise SystemExit(main())
