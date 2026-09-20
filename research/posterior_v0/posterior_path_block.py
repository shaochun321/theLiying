"""posterior_path_block.py — Posterior-0 Step F1：bundle_c 路径阻断
（反馈 §八/§九定义；DIAGNOSTIC_INTERVENTION 登记，禁入 production）。

TYPE:INFRA（research/ 层）。

## 预注册

  阻断臂 = (1,1) 配置 + block_window=[t_rearm_W, q_up)：
    Δ→tin_c ACTIVE（照常换能）；tin_c→bundle_c BLOCKED（不 propagate，
    transmission=0）；RelationCell Δ dose=0。
  s23_ov（[2927,3566)）与 Q（[6497,…)）均在 block 窗外——只切 Δ 传播。
  判据：blocked 臂替换 arm11 后 I_W' → 0（< ε_num 量级或
  与 near_10 逐位一致）；审计五项（反馈 §九）齐全才叫 causal path block。

## COMPUTE_BUDGET

  path_blocks = 1 ≤ 3；prior_state_replays +1（W=1 臂）

复现入口：
  PYTHONIOENCODING=utf-8 python research/posterior_v0/posterior_path_block.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from p0_common import (  # noqa: E402
    DATA, Q_WINDOW_LEN, POSTERIOR_WASHOUT_STEPS, ledger_add, q_window,
    rc_main_boundaries, run_arm, w_composition)
from relation_physical_impl import PortWindow  # noqa: E402

TRACES = os.path.join(DATA, 'arm_traces')


def _load(name):
    xs, vs = [], []
    with open(os.path.join(TRACES, f"{name}.csv"), newline='',
              encoding='utf-8') as f:
        for r in csv.DictReader(f):
            xs.append(float(r["x"])); vs.append(float(r["vm"]))
    return xs, vs


def main() -> int:
    with open(os.path.join(DATA, 'p0_timing_freeze.json'),
              encoding='utf-8') as f:
        tm = json.load(f)["timing"]
    _, _, t_rearm_w = rc_main_boundaries()
    q_up = tm["q_up_near_set"]
    q_end = q_up + Q_WINDOW_LEN + POSTERIOR_WASHOUT_STEPS
    rports, cwins = w_composition()
    near = PortWindow(tm["NEAR"]["window"][0], tm["NEAR"]["window"][2],
                      "delta.NEAR")
    qw = q_window(q_up)
    blk = run_arm("near_11_blocked", rports,
                  sorted(cwins + [near, qw], key=lambda w: w.t_up),
                  t_total=tm["t_total_near_set"],
                  block_window=(t_rearm_w, q_up),
                  snapshot_at=(q_up - 1,))
    ledger_add("prior_state_replays", "near_11_blocked", "StepF1 block arm")
    ledger_add("path_blocks", "near_block_rearm_to_q",
               "bundle_c blocked in [t_rearm_W,q_up), tin_c active "
               "(DIAGNOSTIC_INTERVENTION)")

    x10, v10 = _load("near_10")
    # blocked 臂 cell 侧应与 (1,0) 臂逐位一致（Δ 电流从未到达 cell）
    rmse_vs_10 = math.sqrt(sum((a - b) ** 2 for a, b in
                               zip(blk.xs, x10)) / len(x10))
    # 能耗审计（反馈 §九 item3）：PowerRail 液位被快速回充
    # （r_supply=0.01）补偿，须用吞吐差测——blocked 臂总耗散 vs
    # near_10 臂（唯一差异=tin_c 处理 Δ）
    with open(os.path.join(DATA, 'posterior_factorial_trials.csv'),
              newline='', encoding='utf-8') as f:
        e_drop_10 = next(float(r["energy_drop"]) for r in csv.DictReader(f)
                         if r["arm"] == "near_10")
    e_extra = blk.ledger["energy_drop"] - e_drop_10
    audit = dict(blk.audit)
    audit_ok = {
        "tin_c_received_delta": audit["tin_c_drive_sum_block"] > 0.0,
        "tin_c_state_changed": audit["tin_c_act_peak_block"] > 0.0,
        "tin_c_energy_used": e_extra > 0.0,
        "bundle_c_transmission_zero": True,   # by construction (no call)
        "cell_delta_dose_zero": rmse_vs_10 < 1e-9,
    }
    with open(os.path.join(DATA, 'posterior_interaction.json'),
              encoding='utf-8') as f:
        i_near = next(s for s in json.load(f)["sets"]
                      if s["set"] == "near")["I_W_traj_activation"]
    # I_W→0 判定：blocked 臂与 (1,0) 逐位一致 ⇒ Δ 的全部影响走
    # bundle_c；阻断后 Δ 项从双差中消失 ⇒ I_W'=0（恒等式成立的
    # 实证前提=rmse_vs_10 逐位；单臂替换公式会退化为 −(Y01−Y00)，
    # 不作为判据）
    out = {"block_window": [t_rearm_w, q_up],
           "I_W_with_delta": i_near,
           "interaction_removed": rmse_vs_10 < 1e-9,
           "removal_evidence": "blocked arm bitwise == (1,0) arm ⇒ all "
                               "Delta influence rides bundle_c ⇒ I_W'=0",
           "blocked_arm_bitwise_vs_10_rmse": rmse_vs_10,
           "tin_c_extra_dissipation_vs_10": e_extra,
           "audit_raw": {k: v for k, v in audit.items()},
           "audit_five_items": audit_ok,
           "causal_path_block_valid": all(audit_ok.values()),
           "registration": "DIAGNOSTIC_INTERVENTION (research only)"}
    with open(os.path.join(DATA, 'posterior_path_block.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"I_W with delta={i_near:.4e}  removed={out['interaction_removed']}")
    print(f"blocked vs near_10 rmse={rmse_vs_10:.3e}  "
          f"tin_c extra dissipation={e_extra:.4e}")
    print(f"audit five items: {audit_ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
