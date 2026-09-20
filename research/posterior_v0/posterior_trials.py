"""posterior_trials.py — Posterior-0 Step D：2×2 主交互 + timing-control
（反馈 §二十四 Step D / §十六双表面判据）。

TYPE:INFRA（research/ 层；production READ_ONLY）。

## 预注册（运行前冻结）

  臂（NEAR 集，t_total=8000，Q@6497；MID 集 t_total=9000，Q@7439）：
    (1,1) R=[ρ_a] C=[s23_ov, Δ, Q]   (1,0) R=[ρ_a] C=[s23_ov, Q]
    (0,1) R=[]    C=[s23_ov, Δ, Q]   (0,0) R=[]    C=[s23_ov, Q]
  TC 半集（共用 NEAR 集 (1,0)/(0,0)）：(1,1_tc)/(0,1_tc)，Δ=s23_far_b
  （CONTROL，置于 rearm 前——同剂量错时，方案 §18）。

  判据表面（反馈 §十六）：
    PRIMARY continuous  = I_W^traj(activation)（typed 读出面；
                          eval 窗 [q_up, q_up+639+456)）
    corroborating       = I_W^traj(membrane vm)（Z-primary 面，
                          DIAGNOSTIC_READ）
    event               = occ_Q 存在/边界（仅加固，不能替代 continuous）
  每臂并报：M_Q=peak_Q−θ₂（probe margin，反馈 §七）、
  washout 后 Z11 vs Z10（membrane=PC0-M3 面；activation 并报）、
  energy（RESOURCE_TRACE_ONLY，不得撑 M3）。

  PARALLEL_NEW_STATE 检查（反馈 §六/§十九）：Δ 期窗 [t_rearm_W, q_up)
  内新 χ_ρ₂ occurrence ⇒ 该 Δ 条件标 PARALLEL_NEW_STATE=TRUE，
  不得直接用于终态 A；并报 closure 在 q_up 的 rearm 状态（occ_Q 读出
  可比性披露——若某臂 q_up 时仍处 rearm，occ_Q 面失效仅 continuous 有效）。

  Q 窗内注册的 occurrence = probe 读出（occ_Q），不进入 χ_ρ₂ 谱系申索。

## PL 分层（反馈 §十五）

  PL0 = Δ 输入期差异；PL1 = washout 后 Z11≠Z10（membrane>ε）；
  PL2 = I_W^traj > ε_num（prior-dependent，PC0-M4）。

## COMPUTE_BUDGET

  prior_state_replays：near(1,1)+(1,0)、tc(1,1)、mid(1,1)+(1,0) = 5
  factorial_sets：NEAR、MID、TC(半) = 3 ≤ 4
  posterior_timing_points：NEAR、MIDDLE、TC = 3 ≤ 4

复现入口：
  PYTHONIOENCODING=utf-8 python research/posterior_v0/posterior_trials.py
"""
from __future__ import annotations

import csv
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from p0_common import (  # noqa: E402
    DATA, EPSILON_NUM, Q_WINDOW_LEN, POSTERIOR_WASHOUT_STEPS,
    events_in, interaction_traj, ledger_add, peak_in, q_window,
    rc_main_boundaries, run_arm, w_composition)
from d21_common import frozen_relation2_params  # noqa: E402
from relation_physical_impl import PortWindow  # noqa: E402


TRACES = os.path.join(DATA, 'arm_traces')


def _load_timing():
    with open(os.path.join(DATA, 'p0_timing_freeze.json'),
              encoding='utf-8') as f:
        return json.load(f)["timing"]


def _dump_trace(res):
    """逐步轨迹落盘（Step E 分析消费；确定性重放产物，可再生）。"""
    os.makedirs(TRACES, exist_ok=True)
    with open(os.path.join(TRACES, f"{res.name}.csv"), 'w', newline='',
              encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["k", "x", "vm"])
        for k, (x, v) in enumerate(zip(res.xs, res.vs)):
            w.writerow([k, repr(x), repr(v)])


def _pw(win, wid):
    return PortWindow(win[0], win[2], wid)


def _arm_row(res, set_name, q_up, q_end, theta2, t_rearm_w):
    occ_all = [(e.t_up, e.t_down, e.t_rearm) for e in res.events]
    occ_delta = [(e.t_up, e.t_down, e.t_rearm)
                 for e in events_in(res.events, t_rearm_w, q_up)]
    occ_q = [(e.t_up, e.t_down, e.t_rearm)
             for e in events_in(res.events, q_up, q_end)]
    in_rearm_at_q = any(e.t_up < q_up <= e.t_rearm for e in res.events)
    snap = res.snapshots[q_up - 1]
    return {"set": set_name, "arm": res.name,
            "occ_all": json.dumps(occ_all),
            "occ_delta_epoch": json.dumps(occ_delta),
            "occ_q": json.dumps(occ_q),
            "closure_in_rearm_at_q": int(in_rearm_at_q),
            "m_q": peak_in(res.xs, q_up, q_end) - theta2,
            "z_pre_q_activation": snap["x"],
            "z_pre_q_membrane": snap["cell_state"]["_membrane"].voltage
            if hasattr(snap["cell_state"].get("_membrane"), "voltage")
            else res.vs[q_up - 1],
            "energy_end": res.ledger["e_end"],
            "energy_drop": res.ledger["energy_drop"],
            "x_peak": res.ledger["x_peak"]}


def _run_set(set_name, rports, cwins_base, delta_win, q_up, t_total,
             theta2, t_rearm_w, budget_note):
    """跑一个 2×2 集（或半集），返回 {arm: ArmResult} 与行记录。"""
    q_end = q_up + Q_WINDOW_LEN + POSTERIOR_WASHOUT_STEPS
    qw = q_window(q_up)
    arms = {}
    snap = (q_up - 1,)
    specs = {"11": (rports, cwins_base + ([delta_win] if delta_win else [])
                    + [qw]),
             "10": (rports, cwins_base + [qw]),
             "01": ([], cwins_base + ([delta_win] if delta_win else [])
                    + [qw]),
             "00": ([], cwins_base + [qw])}
    for tag, (rp, cw) in specs.items():
        name = f"{set_name}_{tag}"
        arms[tag] = run_arm(name, rp, sorted(cw, key=lambda w: w.t_up),
                            t_total=t_total, snapshot_at=snap)
        if tag in ("11", "10"):
            ledger_add("prior_state_replays", name, budget_note)
        _dump_trace(arms[tag])
        print(f"  {name}: peak={arms[tag].ledger['x_peak']:.4f} "
              f"occ={[(e.t_up, e.t_down, e.t_rearm) for e in arms[tag].events]}")
    rows = [_arm_row(arms[t], set_name, q_up, q_end, theta2, t_rearm_w)
            for t in ("11", "10", "01", "00")]
    ew = (q_up, q_end)
    inter = {
        "set": set_name, "eval_window": list(ew),
        "I_W_traj_activation": interaction_traj(
            arms["11"].xs, arms["10"].xs, arms["01"].xs, arms["00"].xs, ew),
        "I_W_traj_membrane": interaction_traj(
            arms["11"].vs, arms["10"].vs, arms["01"].vs, arms["00"].vs, ew),
        "I_W_occ": ((len(events_in(arms["11"].events, *ew))
                     - len(events_in(arms["10"].events, *ew)))
                    - (len(events_in(arms["01"].events, *ew))
                       - len(events_in(arms["00"].events, *ew)))),
        "pl1_membrane_z11_z10": abs(arms["11"].vs[q_up - 1]
                                    - arms["10"].vs[q_up - 1]),
        "pl1_activation_z11_z10": abs(arms["11"].xs[q_up - 1]
                                      - arms["10"].xs[q_up - 1]),
        "resource_trace_e11_e10": abs(arms["11"].ledger["e_end"]
                                      - arms["10"].ledger["e_end"]),
        "parallel_new_state_arm11": bool(
            events_in(arms["11"].events, t_rearm_w, q_up)),
        "parallel_new_state_arm01": bool(
            events_in(arms["01"].events, t_rearm_w, q_up)),
    }
    inter["PL1_pass_membrane"] = inter["pl1_membrane_z11_z10"] > EPSILON_NUM
    inter["PL2_pass_primary_activation"] = (
        inter["I_W_traj_activation"] > EPSILON_NUM)
    return arms, rows, inter


def main() -> int:
    g, theta2, rearm2 = frozen_relation2_params()
    t_up_w, t_down_w, t_rearm_w = rc_main_boundaries()
    tm = _load_timing()
    rports, cwins = w_composition()
    near = _pw(tm["NEAR"]["window"], "delta.NEAR")
    tc = _pw(tm["TIMING_CONTROL"]["window"], "delta.TC")
    mid = (_pw(tm["MIDDLE"]["window"], "delta.MIDDLE")
           if tm["MIDDLE"] else None)

    all_rows, inters, arm_cache = [], [], {}

    print("[NEAR set]")
    arms_n, rows, inter = _run_set(
        "near", rports, cwins, near, tm["q_up_near_set"],
        tm["t_total_near_set"], theta2, t_rearm_w, "StepD near set")
    all_rows += rows; inters.append(inter); arm_cache["near"] = arms_n

    print("[TC half-set] (same Q placement; CONTROL, not legal posterior)")
    q_up, q_end = tm["q_up_near_set"], (tm["q_up_near_set"]
                                        + Q_WINDOW_LEN
                                        + POSTERIOR_WASHOUT_STEPS)
    qw = q_window(q_up)
    tc11 = run_arm("tc_11", rports,
                   sorted(cwins + [tc, qw], key=lambda w: w.t_up),
                   t_total=tm["t_total_near_set"], snapshot_at=(q_up - 1,))
    ledger_add("prior_state_replays", "tc_11", "StepD timing control")
    tc01 = run_arm("tc_01", [],
                   sorted(cwins + [tc, qw], key=lambda w: w.t_up),
                   t_total=tm["t_total_near_set"], snapshot_at=(q_up - 1,))
    _dump_trace(tc11); _dump_trace(tc01)
    print(f"  tc_11 peak={tc11.ledger['x_peak']:.4f}  "
          f"tc_01 peak={tc01.ledger['x_peak']:.4f}")
    ew = (q_up, q_end)
    inter_tc = {
        "set": "timing_control", "eval_window": list(ew),
        "I_W_traj_activation": interaction_traj(
            tc11.xs, arms_n["10"].xs, tc01.xs, arms_n["00"].xs, ew),
        "I_W_traj_membrane": interaction_traj(
            tc11.vs, arms_n["10"].vs, tc01.vs, arms_n["00"].vs, ew),
        "note": "CONTROL: delta placed pre-rearm (inside W occurrence); "
                "tests dose-sum alternative (plan §18)"}
    all_rows.append(_arm_row(tc11, "timing_control", q_up, q_end, theta2,
                             t_rearm_w))
    all_rows.append(_arm_row(tc01, "timing_control", q_up, q_end, theta2,
                             t_rearm_w))
    inters.append(inter_tc)
    arm_cache["tc"] = {"11": tc11, "01": tc01}

    if mid is not None:
        print("[MID set]")
        arms_m, rows_m, inter_m = _run_set(
            "middle", rports, cwins, mid, tm["q_up_mid_set"],
            tm["t_total_mid_set"], theta2, t_rearm_w, "StepD mid set")
        all_rows += rows_m; inters.append(inter_m)
        arm_cache["middle"] = arms_m

    with open(os.path.join(DATA, 'posterior_factorial_trials.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0]))
        w.writeheader(); w.writerows(all_rows)
    with open(os.path.join(DATA, 'posterior_interaction.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        json.dump({"epsilon_num": EPSILON_NUM, "theta2": theta2,
                   "sets": inters}, f, indent=1, ensure_ascii=False)
    for it in inters:
        act = it.get("I_W_traj_activation")
        mem = it.get("I_W_traj_membrane")
        print(f"\n{it['set']}: I_W(act)={act:.3e} I_W(vm)={mem:.3e} "
              f"occ={it.get('I_W_occ')} "
              f"PL1(vm)={it.get('pl1_membrane_z11_z10', '—')} "
              f"PNS(11)={it.get('parallel_new_state_arm11', '—')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
