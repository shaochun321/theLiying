"""interaction_analysis.py — Posterior-0 Step E：负对照 + §19 分离性审计
（反馈 §二十四 Step E；全部消费 Step D 落盘轨迹，零新 run）。

TYPE:INFRA（research/ 层）。

## 四件负对照（方案 §16-§18 + 反馈 §十九收紧）

  E-1 later-event-only：D1=RMS(Y11−Y10) vs D0=RMS(Y01−Y00)；相等 ⇒
      ADDITIVE_ONLY（方案 §16）。
  E-2 history-only：RMS(Y10−Y00)（W 自身残余，方案 §17——posterior
      效应不得仅等于 history residual）。
  E-3 timing-control：I_W(near) vs I_W(tc) 比值（§18 同剂量错时）。
  E-4 §19 分离性审计（PARALLEL_NEW_STATE 定量形态，本轮关键判据）：
      膜面 W 分量不变性 = RMSE[(v11−v01)−(v10−v00)] over [Δ_on, eval_end)
      —— 膜电压线性叠加下该量≈0 意味着 **Δ 没有改变 W 可归因的膜分量**
      （𝔅 在 Z-primary 载体上 = id），readout 面的非加法交互是阈值
      联合读出效应；per 反馈 §十九"不能因为最终 query 不同而判 PASS"，
      此时 POSTERIOR_REORGANIZATION(carrier)=NO，交互登记为
      THRESHOLD_READOUT_INTERACTION（真实、时序依赖、可因果干预，
      但载体级为加法）。

## 交互定位诊断（非门）

  找 eval 窗内逐点交互 |(x11−x10)−(x01−x00)| 最大处 k*，并报该处四臂
  vm 相对阈值 0.3 的位置——非加法性来源应在阈值穿越邻域（DEG-019
  硬截零 = load-bearing 非线性）。

复现入口：
  PYTHONIOENCODING=utf-8 python research/posterior_v0/interaction_analysis.py
"""
from __future__ import annotations

import csv
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from p0_common import DATA, EPSILON_NUM, rms  # noqa: E402

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
    with open(os.path.join(DATA, 'posterior_interaction.json'),
              encoding='utf-8') as f:
        inter = json.load(f)
    q_up = tm["q_up_near_set"]
    q_end = q_up + tm["q_window_len"] + tm["washout_steps"]
    d_on = tm["NEAR"]["window"][0]

    arms = {t: _load(f"near_{t}") for t in ("11", "10", "01", "00")}
    x, v = ({t: a[0] for t, a in arms.items()},
            {t: a[1] for t, a in arms.items()})

    ew = range(q_up, q_end)
    # E-1 later-event-only（加法性对照）
    d1_act = rms([x["11"][k] - x["10"][k] for k in ew])
    d0_act = rms([x["01"][k] - x["00"][k] for k in ew])
    d1_vm = rms([v["11"][k] - v["10"][k] for k in ew])
    d0_vm = rms([v["01"][k] - v["00"][k] for k in ew])
    # E-2 history-only
    hist_act = rms([x["10"][k] - x["00"][k] for k in ew])
    hist_vm = rms([v["10"][k] - v["00"][k] for k in ew])
    # E-3 timing-control 比值
    i_near = next(s for s in inter["sets"] if s["set"] == "near")
    i_tc = next(s for s in inter["sets"] if s["set"] == "timing_control")
    i_mid = next((s for s in inter["sets"] if s["set"] == "middle"), None)
    # E-4 §19 分离性审计（W 分量不变性，窗 [Δ_on, eval_end)）
    sw = range(d_on, q_end)
    w_component_shift_vm = rms([(v["11"][k] - v["01"][k])
                                - (v["10"][k] - v["00"][k]) for k in sw])
    w_component_shift_act = rms([(x["11"][k] - x["01"][k])
                                 - (x["10"][k] - x["00"][k]) for k in sw])
    carrier_additive = w_component_shift_vm < EPSILON_NUM

    # 交互定位诊断
    pt = [abs((x["11"][k] - x["10"][k]) - (x["01"][k] - x["00"][k]))
          for k in ew]
    k_star = q_up + max(range(len(pt)), key=lambda i: pt[i])
    loc = {"k_star": k_star, "pointwise_max": max(pt),
           "vm_at_k_star": {t: v[t][k_star] for t in v},
           "vm_threshold": 0.3}

    out = {
        "eval_window": [q_up, q_end],
        "E1_later_event_only": {
            "D1_act": d1_act, "D0_act": d0_act,
            "D1_vm": d1_vm, "D0_vm": d0_vm,
            "additive_on_activation": abs(d1_act - d0_act) < EPSILON_NUM,
            "additive_on_membrane": abs(d1_vm - d0_vm) < EPSILON_NUM},
        "E2_history_only": {"hist_act": hist_act, "hist_vm": hist_vm,
                            "interaction_exceeds_history_note":
                            "I_W measures W×Delta beyond history residual "
                            "by construction (double difference)"},
        "E3_timing_control": {
            "I_W_near_act": i_near["I_W_traj_activation"],
            "I_W_tc_act": i_tc["I_W_traj_activation"],
            "ratio_near_over_tc": (i_near["I_W_traj_activation"]
                                   / i_tc["I_W_traj_activation"]),
            "I_W_mid_act": (i_mid["I_W_traj_activation"] if i_mid
                            else None),
            "timing_dependent": (i_near["I_W_traj_activation"]
                                 > 3 * i_tc["I_W_traj_activation"])},
        "E4_separability_sec19": {
            "window": [d_on, q_end],
            "w_component_shift_membrane": w_component_shift_vm,
            "w_component_shift_activation": w_component_shift_act,
            "carrier_level_additive": carrier_additive,
            "ruling_input": ("PARALLEL_NEW_STATE(carrier)=TRUE: Delta did "
                            "not alter the W-attributable membrane "
                            "component (B=id on Z-primary); readout-level "
                            "interaction registered as "
                            "THRESHOLD_READOUT_INTERACTION"
                            if carrier_additive else
                            "W-attributable membrane component altered "
                            "by Delta — carrier-level reorganization "
                            "candidate")},
        "interaction_localization": loc,
    }
    with open(os.path.join(DATA, 'posterior_negative_controls.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"E1 additive? act={out['E1_later_event_only']['additive_on_activation']} "
          f"(D1={d1_act:.4e} D0={d0_act:.4e}) "
          f"vm={out['E1_later_event_only']['additive_on_membrane']} "
          f"(D1={d1_vm:.4e} D0={d0_vm:.4e})")
    print(f"E2 history residual: act={hist_act:.4e} vm={hist_vm:.4e}")
    print(f"E3 timing: near/tc={out['E3_timing_control']['ratio_near_over_tc']:.2f} "
          f"timing_dependent={out['E3_timing_control']['timing_dependent']}")
    print(f"E4 separability: w_shift_vm={w_component_shift_vm:.3e} "
          f"w_shift_act={w_component_shift_act:.3e} "
          f"carrier_additive={carrier_additive}")
    print(f"localization: k*={k_star} max={loc['pointwise_max']:.4e} "
          f"vm@k*={ {t: round(loc['vm_at_k_star'][t], 4) for t in loc['vm_at_k_star']} }")
    return 0


if __name__ == "__main__":
    sys.exit(main())
