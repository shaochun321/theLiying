"""dataset_builder.py — Posterior-0 Step B+C：冻结时点 + 数据集 + hold lock
（反馈 §二十四 Step B/C）。

TYPE:INFRA（research/ 层；production READ_ONLY）。

## Step B — Freeze Timing（消费 substrate_audit.json 硬 Gate 输出）

  NEAR   = p0_probe_near_r1c 窗 (5402,5541,6041)，tag=R1C_FALLBACK
           （落膜面 query-relevant 残余窗 [5387,6131] 内，重叠 729 步）
  MIDDLE = conditional（反馈 §三"若数据允许"）：新轨迹 t_on=5660/P=900/
           amp=0.03（预注册；潜伏外推 ≈674 ⇒ t_up≈6334——落 qrel 窗外、
           ε 窗（→11732）内 = §19 boundary 弧的中点；P=900 沿 R-1(c)
           一次冻结的 support duration，不迭代寻优）
  FAR    = NOT_ATTEMPTED：登记 LIM-POSTERIOR-TIMING（reason=
           new_g0 预算 4/4 耗尽；外推 t_on≈6540/P=900 或可达但未测——
           如实登记为"未尝试"而非"不可达"）
  TIMING-CONTROL（方案 §18 同剂量错时）= s23_far_b 窗 (4577,5216)：
           同 duration 639、置于 t_rearm_W 之前（故意违反 posterior 时序，
           标 CONTROL，非法定 posterior 条件）

## Step C — Dataset（全部窗/放置在本脚本冻结，SHA lock 后零回调）

  Q = 标准化相位斜坡 639 步（QUERY_WINDOW_SELECTION）：
    NEAR/TC 集：t_q=6497（=NEAR Δ rearm 6041+washout 456；TC 共用同一
    Q 放置，washout 距 TC Δ 尾 1281≥456 合法）
    MID 集：t_q=Δ_mid.rearm+456（集内四臂逐位同）
  臂结构（W=0=R 通道全零、C 通道逐位同——E3 Y 臂/H6 先例，NF-2 阈下）：
    (1,1) R=[ρ_a] C=[s23_ov, Δ, Q] / (1,0) R=[ρ_a] C=[s23_ov, Q]
    (0,1) R=[]    C=[s23_ov, Δ, Q] / (0,0) R=[]    C=[s23_ov, Q]
  hold6（先 SHA 后运行，盲评零回调）：
    H1 unseen_W_rc_lead        W=(ρ_a+s23_lead)  Δ=NEAR  Q std
    H2 unseen_W_rc_R_only      W=(ρ_a only)      Δ=NEAR  Q std
    H3 unseen_posterior_timing W=rc_main  Δ=新轨迹 t_on=5000/P=900
                               （与 NF-1 失败点同 t_on 的 duration 配对）
    H4 unseen_Q_timing         W=rc_main  Δ=NEAR  Q 放置 +300
                               （washout 456 下限不变，Q 更晚=合法）
    H5 unseen_W_no_posterior   W=rc_lead  Δ=sham  Q std
    H6 structural_no_posterior W=rc_main  Δ=sham  Q std（反馈 §二十七.6）
  合法失败仅限 illegal state/nonfinite/replay 不一致/lineage 缺失
  （D2-1 惯例）；null/negative 结果合法。
  H2 择 rc_R_only 而非 rc_lag 的原因：rc_lag t_rearm=6007>Δ t_up=5402，
  Δ 落其发生窗内=非 closed past，不合法（时序审计淘汰，非挑数据）。

## COMPUTE_BUDGET

  new_g0_trajectories：middle ×1 + H3 hold ×1（累计 4/4，含 A2 两条）
  本脚本无 relation replay。

复现入口：
  PYTHONIOENCODING=utf-8 python research/posterior_v0/dataset_builder.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from p0_common import (  # noqa: E402
    DATA, POSTERIOR_WASHOUT_STEPS, Q_WINDOW_LEN, RHO_W_TRAJ, S23_W_TID,
    rc_main_boundaries)
from substrate_audit import _record_probe  # noqa: E402

MIDDLE_SPEC = {"tid": "p0_middle", "t_on": 5660, "length": 900,
               "amp": 0.03, "t_total": 10000, "tag": "middle_R1C_duration"}
H3_SPEC = {"tid": "p0_hold_timing", "t_on": 5000, "length": 900,
           "amp": 0.03, "t_total": 10000, "tag": "hold_unseen_timing_R1C"}
TC_WINDOW = (4577, 4716, 5216)   # s23_far_b（既有冻结窗，CONTROL）


def main() -> int:
    with open(os.path.join(DATA, 'substrate_audit.json'),
              encoding='utf-8') as f:
        audit = json.load(f)
    assert audit["gate"]["gate"] == "PROCEED_STEP_B", audit["gate"]
    t_up_w, t_down_w, t_rearm_w = rc_main_boundaries()
    near = tuple(audit["A2"]["reachable_window"])
    near_traj = audit["A2"]["reachable_traj"]
    qrel_last = audit["A1"]["membrane_z_primary"]["last_step_query_relevant"]
    eps_last = audit["A1"]["membrane_z_primary"]["last_step_above_epsilon"]
    print(f"NEAR frozen: {near} from {near_traj} (R1C_FALLBACK); "
          f"qrel window end={qrel_last} eps end={eps_last}")

    # ── Step B：MIDDLE conditional 探测 + H3 hold 轨迹（物理录制）──
    wins_m, diag_m = _record_probe(MIDDLE_SPEC["tid"], MIDDLE_SPEC["t_on"],
                                   MIDDLE_SPEC["length"], MIDDLE_SPEC["amp"],
                                   MIDDLE_SPEC["t_total"], MIDDLE_SPEC["tag"])
    mid = next((w for w in wins_m if w[0] > t_rearm_w), None)
    wins_h, diag_h = _record_probe(H3_SPEC["tid"], H3_SPEC["t_on"],
                                   H3_SPEC["length"], H3_SPEC["amp"],
                                   H3_SPEC["t_total"], H3_SPEC["tag"])
    h3 = next((w for w in wins_h if w[0] > t_rearm_w), None)

    lim = []
    lim.append({"id": "LIM-POSTERIOR-TIMING-FAR",
                "status": "NOT_ATTEMPTED",
                "reason": "new_g0 budget 4/4 exhausted (probe1+r1c+middle"
                          "+hold); extrapolation t_on~6540/P=900 possibly "
                          "reachable but untested — honest registration, "
                          "not proven unreachable"})
    if mid is None:
        lim.append({"id": "LIM-POSTERIOR-TIMING-MIDDLE",
                    "status": "UNREACHABLE_MEASURED", "diag": diag_m})

    # ── Step C：时点冻结 + 臂计划 ──
    q_near = near[2] + POSTERIOR_WASHOUT_STEPS          # 6041+456=6497
    timing = {"W": {"traj": "rc_main", "rho_port": RHO_W_TRAJ,
                    "s23": S23_W_TID,
                    "boundaries": [t_up_w, t_down_w, t_rearm_w]},
              "NEAR": {"window": list(near), "traj": near_traj,
                       "tag": "R1C_FALLBACK",
                       "paired_control": "p0_probe_near (t_on=4780 P=600, "
                                         "occ=0, feedback §3 clause 6)"},
              "MIDDLE": ({"window": list(mid), "traj": MIDDLE_SPEC["tid"],
                          "tag": "R1C_FALLBACK",
                          "position_vs_residual": "outside qrel window "
                          f"(end {qrel_last}), inside eps window "
                          f"(end {eps_last}) — §19 boundary point"}
                         if mid else None),
              "TIMING_CONTROL": {"window": list(TC_WINDOW),
                                 "traj": "s23_far_b", "tag": "CONTROL",
                                 "note": "same duration 639, placed "
                                         "pre-rearm; NOT a legal "
                                         "posterior condition"},
              "H3_HOLD": {"window": list(h3) if h3 else None,
                          "traj": H3_SPEC["tid"], "tag": "R1C_FALLBACK"},
              "washout_steps": POSTERIOR_WASHOUT_STEPS,
              "q_window_len": Q_WINDOW_LEN,
              "q_up_near_set": q_near,
              "q_up_mid_set": (mid[2] + POSTERIOR_WASHOUT_STEPS
                               if mid else None),
              "t_total_near_set": 8000,
              "t_total_mid_set": 9000,
              "eval_window": "[q_up, q_up+639+456) per set",
              "parallel_new_state_window": f"[{t_rearm_w}, q_up)"}

    hold6 = [
        {"case": "H1_unseen_W_rc_lead", "W": "rc_lead", "delta": "NEAR",
         "q": "std"},
        {"case": "H2_unseen_W_rc_R_only", "W": "rc_R_only",
         "delta": "NEAR", "q": "std"},
        {"case": "H3_unseen_posterior_timing", "W": "rc_main",
         "delta": "H3_HOLD", "q": "delta_rearm+456"},
        {"case": "H4_unseen_Q_timing", "W": "rc_main", "delta": "NEAR",
         "q": "std+300"},
        {"case": "H5_unseen_W_no_posterior", "W": "rc_lead",
         "delta": "sham", "q": "std"},
        {"case": "H6_structural_no_posterior", "W": "rc_main",
         "delta": "sham", "q": "std"},
    ]
    hold_manifest = {
        "cases": hold6, "timing": timing,
        "w_arm_rejection_audit": {
            "rc_lag": "t_rearm=6007 > NEAR t_up=5402 — delta inside its "
                      "occurrence window, not a closed past; excluded by "
                      "timing audit (not data picking)"},
        "legality": "legal outcomes include null/negative; failures "
                    "limited to illegal state/nonfinite/replay mismatch/"
                    "lineage missing (D2-1 convention)"}
    hold_j = json.dumps(hold_manifest, indent=1, sort_keys=True,
                        ensure_ascii=False)
    sha = hashlib.sha256(hold_j.encode('utf-8')).hexdigest()
    with open(os.path.join(DATA, 'p0_hold_manifest.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        f.write(hold_j)
    with open(os.path.join(DATA, 'p0_hold_seal.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        json.dump({"hold_manifest_sha256": sha, "sealed": "2026-09-21",
                   "discipline": "no parameter/threshold/window may be "
                                 "tuned from hold cases; hold exposure "
                                 "=> FAIL, no re-run (zero-recall)"},
                  f, indent=1)

    with open(os.path.join(DATA, 'p0_timing_freeze.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        json.dump({"timing": timing, "limits": lim,
                   "hold_sha256": sha}, f, indent=1, ensure_ascii=False)
    print(f"\nfrozen: NEAR={near} MIDDLE={mid} TC={TC_WINDOW} H3={h3}")
    print(f"q_up(near set)={q_near} q_up(mid set)="
          f"{timing['q_up_mid_set']}")
    print(f"hold6 sealed sha256={sha[:16]}…  limits={[l['id'] for l in lim]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
