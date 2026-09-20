"""state_intervention.py — Posterior-0 Step F2：状态移植（主因果门，
反馈 §十八；a8v2 tier1 先例；DIAGNOSTIC_INTERVENTION 登记）。

TYPE:INFRA（research/ 层）。

## 预注册

  t0 = q_up−1（washout 后、Q 前一步）。
  sham    ：(1,0) 重跑不移植——应与 Step D near_10 逐位（对照）。
  forward ：(1,0) 在 t0 处 cell.__dict__ ← deepcopy((1,1) 同刻状态)，
            随后完全相同 Q。等化判据：[t0,end) 轨迹 vs (1,1) 同窗
            RMSE < 1e-9（确定性系统，E3 先例）。
  reverse ：(1,1) 在 t0 处 ← (1,0) 状态（加固，反馈 §十八建议）。
  forward 等化 ⇒ POSTERIOR_MINIMAL_SUFFICIENT_STATE_CANDIDATE
  （= RelationCell 膜态单细胞载体）+ STOP_DEEPER_DECOMPOSITION。

## COMPUTE_BUDGET

  state_interventions = 3（sham/forward/reverse）≤ 4；
  源状态获取 = (1,1)/(1,0) 重跑至 t0 的 snapshot（干预协议内部阶段跑，
  记入 interventions 附注，不另计 prior replay——E3 stage-run 口径）。

复现入口：
  PYTHONIOENCODING=utf-8 python research/posterior_v0/state_intervention.py
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
    run_arm, w_composition)
from relation_physical_impl import PortWindow  # noqa: E402

TRACES = os.path.join(DATA, 'arm_traces')


def _load(name):
    xs = []
    with open(os.path.join(TRACES, f"{name}.csv"), newline='',
              encoding='utf-8') as f:
        for r in csv.DictReader(f):
            xs.append(float(r["x"]))
    return xs


def _rmse(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))


def main() -> int:
    with open(os.path.join(DATA, 'p0_timing_freeze.json'),
              encoding='utf-8') as f:
        tm = json.load(f)["timing"]
    q_up = tm["q_up_near_set"]
    t0 = q_up - 1
    t_total = tm["t_total_near_set"]
    rports, cwins = w_composition()
    near = PortWindow(tm["NEAR"]["window"][0], tm["NEAR"]["window"][2],
                      "delta.NEAR")
    qw = q_window(q_up)
    c11 = sorted(cwins + [near, qw], key=lambda w: w.t_up)
    c10 = sorted(cwins + [qw], key=lambda w: w.t_up)

    # 源状态（stage 跑，snapshot at t0）
    src11 = run_arm("iv_src_11", rports, c11, t_total=t_total,
                    snapshot_at=(t0,))
    src10 = run_arm("iv_src_10", rports, c10, t_total=t_total,
                    snapshot_at=(t0,))
    st11 = src11.snapshots[t0]["cell_state"]
    st10 = src10.snapshots[t0]["cell_state"]

    # sham / forward / reverse
    sham = run_arm("iv_sham_10", rports, c10, t_total=t_total)
    fwd = run_arm("iv_fwd_10_gets_11", rports, c10, t_total=t_total,
                  transplant_state=st11, transplant_at=t0 + 1)
    rev = run_arm("iv_rev_11_gets_10", rports, c11, t_total=t_total,
                  transplant_state=st10, transplant_at=t0 + 1)
    for tag, note in (("sham", "no transplant control"),
                      ("forward", "Z10<-Z11 at t0 (tier1 cell state)"),
                      ("reverse", "Z11<-Z10 at t0 (reinforcement)")):
        ledger_add("state_interventions", f"iv_{tag}", note
                   + "; stage source runs included in protocol")

    x11 = _load("near_11")
    x10 = _load("near_10")
    seg = slice(t0 + 1, t_total)
    res = {
        "t0": t0,
        "sham_vs_near10_rmse": _rmse(sham.xs[seg], x10[seg]),
        "forward_vs_near11_rmse": _rmse(fwd.xs[seg], x11[seg]),
        "reverse_vs_near10_rmse": _rmse(rev.xs[seg], x10[seg]),
        "baseline_divergence_11_10": _rmse(x11[seg], x10[seg]),
    }
    res["sham_preserves_divergence"] = (res["sham_vs_near10_rmse"] < 1e-12
                                        and res["baseline_divergence_11_10"]
                                        > 1e-6)
    res["forward_equalizes"] = res["forward_vs_near11_rmse"] < 1e-9
    res["reverse_equalizes"] = res["reverse_vs_near10_rmse"] < 1e-9
    res["verdict"] = (
        "POSTERIOR_MINIMAL_SUFFICIENT_STATE_CANDIDATE="
        "RelationCell membrane state (single cell); "
        "STOP_DEEPER_DECOMPOSITION"
        if res["forward_equalizes"] else "TRANSPLANT_NOT_SUFFICIENT")
    res["registration"] = "DIAGNOSTIC_INTERVENTION (research only)"
    with open(os.path.join(DATA, 'posterior_state_intervention.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    print(f"baseline 11-vs-10 rmse={res['baseline_divergence_11_10']:.4e}")
    print(f"sham rmse={res['sham_vs_near10_rmse']:.3e} "
          f"forward rmse={res['forward_vs_near11_rmse']:.3e} "
          f"reverse rmse={res['reverse_vs_near10_rmse']:.3e}")
    print(f"verdict: {res['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
