"""substrate_audit.py — Posterior-0 Step A：Substrate + Reachability
（整个 Posterior-0 的首个硬 Gate，反馈 §二十四）。

TYPE:INFRA（research/ 层；production READ_ONLY）。

## A1 — residual substrate（反馈 §十二：不输出有/无二值）

  replay rc_main W 臂（[ρ_a]+s23_ov，无 Δ/Q），t_total=12000 零驱动垫尾。
  先逐位核对 χ_ρ₂ 闭合边界 == 冻结 rc_main (3332,4931,5387)（确定性门，
  任何不一致=阻断性失败）。

  **双面输出**（首跑发现，方法披露）：activation 读出面在 vm<0.3 处被
  MOSFET 硬截零（DEG-019，load-bearing），activation 残余 τ≈6 步是
  **读出坍缩不是膜态消失**；Z-primary=RelationCell membrane state
  （反馈 §十一）的本体是膜电压 vm——DIAGNOSTIC_READ 只读观察
  （G0-R1 hidden dynamics/E3 全状态移植先例）。两面各输出五字段：
    residual_start          = 面值(t_rearm_W)
    tau_residual            = 衰减段对数线性拟合
    last_step_above_epsilon = 最后一个 面值≥ε_num 的步（censored 标记）
    last_step_query_relevant= 最后一个 面值≥0.028·θ₂ 的步——**解析派生**：
                              NF-2 实测 C-only 峰距 θ₂ 缺口=2.8%·θ₂
                              （gm=1 线性域 vm 增量≈activation 增量）；
                              上界式估计，披露 DERIVED，Step D 实测校验
    epsilon_num             = 1e-6

## A2 — late posterior reachability（R-1(a) 主路径，≤2 条新 G0 轨迹）

  预注册探针（首次运行前冻结，p0_common）：
    probe1 = t_on=4780, P=600, amp=0.03, t_total=10000
      依据：NF-1 潜伏漂移外推 latency(4780)≈624 ⇒ t_up≈5404>5387（NEAR），
      越阈落脉冲尾后 ≈24 步（NF-1 在 37 步处失效——本探针恰测 L1 尾容限）。
    自适应规则（预注册，非事后调参）：
      (i) probe1 有 occurrence 且 t_up>t_rearm_W ⇒ NEAR reachable，停。
      (ii) probe1 有 occurrence 但 t_up≤t_rearm_W（潜伏短于外推）⇒
           probe1b：t_on=4780+(t_rearm_W−t_up)+30，P=600（同族、单次）。
      (iii) probe1 零 occurrence 且诊断=crossing 落支撑窗后 ⇒ R-1(c)
           一次性后备 probe2_r1c：同 t_on=4780、P=900（仅延长 physical
           support duration；probe1=同 t_on paired control；数据标
           R1C_FALLBACK；不得继续迭代 duration 寻优，反馈 §三）。
    两级仍不可达 ⇒ 输出 posterior_near_reachable=False，Step B 判
    terminal=D reason=POSTERIOR_TIMING_UNREACHABLE（反馈 §四），STOP。

## COMPUTE_BUDGET

  prior_state_replays = 1（A1）；new_g0_trajectories ≤ 2（A2，含中止记账）

复现入口：
  PYTHONIOENCODING=utf-8 python research/posterior_v0/substrate_audit.py
"""
from __future__ import annotations

import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from p0_common import (  # noqa: E402
    DATA, EPSILON_NUM, POSTERIOR_WASHOUT_STEPS, PROBE1, PROBE2_R1C,
    S23_TRACES, T_TOTAL_AUDIT, ledger_add, rc_main_boundaries, run_arm,
    w_composition)
from d21_common import frozen_relation2_params  # noqa: E402
from d2_common import DT_G, Pulse, TrajSpec, run_trajectory  # noqa: E402
from relation_physical_impl import PortWindow  # noqa: E402


def _fit_tau(xs, a: int, b: int) -> float:
    """对数线性最小二乘拟合衰减时标（只用 x>1e-9 的点）。"""
    pts = [(k, math.log(xs[k])) for k in range(a, b) if xs[k] > 1e-9]
    n = len(pts)
    if n < 10:
        return float('nan')
    sk = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
    skk = sum(p[0] * p[0] for p in pts)
    sky = sum(p[0] * p[1] for p in pts)
    slope = (n * sky - sk * sy) / (n * skk - sk * sk)
    return -1.0 / slope if slope < 0 else float('inf')


PROBE_MANIFEST = os.path.join(DATA, 'p0_probe_manifest.json')


def _probe_cache() -> dict:
    if os.path.exists(PROBE_MANIFEST):
        with open(PROBE_MANIFEST, encoding='utf-8') as f:
            return json.load(f)
    return {}


def _record_probe(tid: str, t_on: int, length: int, amp: float,
                  t_total: int, tag: str):
    """录一条新 site23 G0 轨迹（fresh circuit），写 IMMUTABLE 缓存 + 记账。

    幂等：缓存轨迹已存在 → 复用 probe manifest（不重跑物理、不重复计费）。
    返回 (occ_windows[(t_up,t_down,t_rearm)…], diagnosis)。
    中止/零 occurrence 也照记（反馈 §二十二）。
    """
    from d21_common import write_immutable
    cache = _probe_cache()
    if tid in cache and os.path.exists(os.path.join(S23_TRACES,
                                                    f"{tid}.csv")):
        c = cache[tid]
        print(f"  {tid}: cached occ={c['occ']} cause={c['diag']['cause']}")
        return [tuple(w) for w in c["occ"]], c["diag"]
    spec = TrajSpec(tid=tid, t_total=t_total,
                    pulses={"C": (Pulse(t_on, length, amp),)}, note=tag)
    rows, occs, _h = run_trajectory(spec)
    write_immutable(S23_TRACES, tid, rows)
    ledger_add("new_g0_trajectories", tid,
               f"t_on={t_on} P={length} amp={amp} tag={tag}")
    evs = occs.get("C", [])
    # 诊断（NF-1 同法）：collector 越阈首达步 vs 支撑窗（sup_C==1 区间）
    cross_k = next((r["k"] for r in rows if r["col_C"] > 0.01), None)
    sup_ks = [r["k"] for r in rows if r["sup_C"]]
    diag = {"cross_k": cross_k,
            "support_first": sup_ks[0] if sup_ks else None,
            "support_last": sup_ks[-1] if sup_ks else None,
            "cause": None}
    if not evs and cross_k is not None and sup_ks and cross_k > sup_ks[-1]:
        diag["cause"] = "support_window_too_short"
    wins = [(e.t_up, e.t_down, e.t_rearm) for e in evs]
    cache[tid] = {"spec": {"t_on": t_on, "length": length, "amp": amp,
                           "t_total": t_total, "tag": tag},
                  "occ": wins, "diag": diag}
    with open(PROBE_MANIFEST, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(cache, f, indent=1, ensure_ascii=False)
    print(f"  {tid}: occ={wins}  cross_k={cross_k} "
          f"support=[{diag['support_first']},{diag['support_last']}] "
          f"cause={diag['cause']}")
    return wins, diag


def main() -> int:
    os.makedirs(DATA, exist_ok=True)
    g, theta2, rearm2 = frozen_relation2_params()
    t_up_w, t_down_w, t_rearm_w = rc_main_boundaries()
    print(f"frozen: g_rel2={g:.6e} theta2={theta2:.4f} rearm2={rearm2} "
          f"rc_main=({t_up_w},{t_down_w},{t_rearm_w})")

    # ── A1：residual substrate ──
    print("\n[A1] rc_main W-arm replay (no Delta/Q), t_total=12000")
    rports, cwins = w_composition()
    arm = run_arm("A1_w_only", rports, cwins, t_total=T_TOTAL_AUDIT)
    ledger_add("prior_state_replays", "A1_w_only", "substrate audit")
    got = [(e.t_up, e.t_down, e.t_rearm) for e in arm.events]
    bit_exact = got and got[0] == (t_up_w, t_down_w, t_rearm_w)
    print(f"  closure events={got}  bit_exact_vs_frozen={bit_exact}")
    if not bit_exact:
        print("  BLOCKING FAILURE: replay boundaries != frozen rc_main")
        return 1
    occ_rel_thr = 0.028 * theta2          # DERIVED（NF-2 C-only 缺口）

    def _surface(seq, label):
        res0 = seq[t_rearm_w]
        tau = _fit_tau(seq, t_rearm_w, t_rearm_w + 2000)
        censored = seq[-1] >= EPSILON_NUM
        last_eps = (None if censored else
                    max((k for k in range(t_rearm_w, T_TOTAL_AUDIT)
                         if seq[k] >= EPSILON_NUM), default=None))
        last_qrel = max((k for k in range(t_rearm_w, T_TOTAL_AUDIT)
                         if seq[k] >= occ_rel_thr), default=None)
        d = {"surface": label, "residual_start": res0,
             "tau_residual": tau, "last_step_above_epsilon": last_eps,
             "eps_censored_at_t_total": censored,
             "last_step_query_relevant": last_qrel,
             "epsilon_num": EPSILON_NUM}
        print(f"  [{label}] residual_start={res0:.5f} tau={tau:.1f} "
              f"last>eps={last_eps} censored={censored} "
              f"last_query_relevant={last_qrel}")
        return d

    a1 = {"activation_readout": _surface(arm.xs, "activation"),
          "membrane_z_primary": _surface(arm.vs, "membrane_vm"),
          "query_relevant_threshold": occ_rel_thr,
          "query_relevant_method": "DERIVED: NF-2 C-only peak deficit "
                                   "2.8%*theta2 (gm=1 linear domain); "
                                   "upper-bound estimate, live-checked "
                                   "in Step D",
          "readout_note": "activation collapse below vm=0.3 is DEG-019 "
                          "hard cutoff (readout), NOT substrate loss; "
                          "Z-primary carrier = membrane vm "
                          "(DIAGNOSTIC_READ, observation only)"}

    # ── A2：late posterior reachability ──
    print("\n[A2] reachability probes (R-1(a) primary)")
    result = {"posterior_near_reachable": False,
              "latest_reachable_t_up": None, "reachable_window": None,
              "support_failure_boundary": None, "r1c_fallback_used": False,
              "probes": {}}
    wins1, diag = _record_probe(PROBE1["tid"], PROBE1["t_on"],
                                PROBE1["length"], PROBE1["amp"],
                                PROBE1["t_total"], "probe1_P600")
    result["probes"]["probe1"] = {"spec": PROBE1, "occ": wins1,
                                  "diag": diag}
    late = [w for w in wins1 if w[0] > t_rearm_w]
    if late:
        result["posterior_near_reachable"] = True
        result["reachable_window"] = late[0]
        result["reachable_traj"] = PROBE1["tid"]
    elif wins1:                                        # 规则 (ii)
        shortfall = t_rearm_w - wins1[0][0]
        t_on_b = PROBE1["t_on"] + shortfall + 30
        spec_b = {"tid": "p0_probe_near_b", "t_on": t_on_b,
                  "length": 600, "amp": 0.03, "t_total": 10000}
        wins_b, diag_b = _record_probe(spec_b["tid"], t_on_b, 600, 0.03,
                                       10000, "probe1b_adaptive_rule_ii")
        result["probes"]["probe1b"] = {"spec": spec_b, "occ": wins_b,
                                       "diag": diag_b}
        late_b = [w for w in wins_b if w[0] > t_rearm_w]
        if late_b:
            result["posterior_near_reachable"] = True
            result["reachable_window"] = late_b[0]
            result["reachable_traj"] = spec_b["tid"]
        elif diag_b["cause"] == "support_window_too_short":
            result["support_failure_boundary"] = diag_b
    elif diag["cause"] == "support_window_too_short":  # 规则 (iii) R-1(c)
        result["r1c_fallback_used"] = True
        wins2, diag2 = _record_probe(PROBE2_R1C["tid"], PROBE2_R1C["t_on"],
                                     PROBE2_R1C["length"],
                                     PROBE2_R1C["amp"],
                                     PROBE2_R1C["t_total"], "R1C_FALLBACK")
        result["probes"]["probe2_r1c"] = {"spec": PROBE2_R1C, "occ": wins2,
                                          "diag": diag2,
                                          "tag": "R1C_FALLBACK"}
        late2 = [w for w in wins2 if w[0] > t_rearm_w]
        if late2:
            result["posterior_near_reachable"] = True
            result["reachable_window"] = late2[0]
            result["reachable_traj"] = PROBE2_R1C["tid"]
        else:
            result["support_failure_boundary"] = diag2
    else:
        result["support_failure_boundary"] = diag
    if result["reachable_window"]:
        result["latest_reachable_t_up"] = result["reachable_window"][0]

    # ── 硬 Gate 判定（PC0-M1 前半：T_residual 与合法 Δ 是否重叠，
    #     以 Z-primary=membrane 面为准；activation 面并报）──
    verdict = {"near_reachable": result["posterior_near_reachable"],
               "r1c_fallback_used": result["r1c_fallback_used"]}
    if result["posterior_near_reachable"]:
        t_up_d = result["latest_reachable_t_up"]
        mem, act = a1["membrane_z_primary"], a1["activation_readout"]
        verdict["delta_within_membrane_eps_window"] = bool(
            mem["eps_censored_at_t_total"]
            or (mem["last_step_above_epsilon"] is not None
                and t_up_d <= mem["last_step_above_epsilon"]))
        verdict["delta_within_membrane_qrel_window"] = (
            mem["last_step_query_relevant"] is not None
            and t_up_d <= mem["last_step_query_relevant"])
        verdict["delta_within_activation_eps_window"] = (
            act["last_step_above_epsilon"] is not None
            and t_up_d <= act["last_step_above_epsilon"])
        verdict["gate"] = "PROCEED_STEP_B"
    else:
        verdict["gate"] = ("TERMINAL_D_POSTERIOR_TIMING_UNREACHABLE "
                           "(after R-1(a)+one R-1(c) attempt, feedback §4)")
    out = {"frozen": {"g_rel2": g, "theta2": theta2, "rearm2": rearm2,
                      "rc_main": [t_up_w, t_down_w, t_rearm_w]},
           "A1": a1, "A2": result, "gate": verdict}
    with open(os.path.join(DATA, 'substrate_audit.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"\ngate: {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
