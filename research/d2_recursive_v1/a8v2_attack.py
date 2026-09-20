"""a8v2_attack.py — D2-1 StepD/E3：A8-v2 twin（同父层当前状态/异关系
状态/同未来输入 ⇒ 异未来？）+ relation-state intervention（方案 §13-§15）。

TYPE:INFRA（research/ 层）。

⚠ DIAGNOSTIC_INTERVENTION 登记（E-9 家族先例）：状态移植（cell/换能
神经元 __dict__ 深拷贝）仅限研究区因果定位，禁止流入 production。

## COMPUTE_BUDGET

  physical_trajectories=0; twins = 1 对 ≤ 4; interventions = 3 ≤ 4
  （sham/tier0/tier1）; stage-2 分段 replay ≈ 8 段

## 设计（预注册）

  臂X 前史 = χ_ρa^(1) 相位驱动（R 通道，窗 [2617,3971)——ρ_a 被消费）
  臂Y 前史 = R 通道全零（关系发生未被消费）
  t0 = 4200：ρ 窗已闭（3971<t0）、未来探测未启（4577>t0）——两臂该
  时刻输入均为 (0,0)，父层当前接口状态 P 相同（无活跃 χ^(0) 窗、无
  活跃关系窗；§14：P=当前最小充分状态候选，不许用无限历史回放）。
  相同未来输入 U⁺ = χ_23^(0)（s23_far_b 窗 [4577,5216)，C 通道）。

判据：
  E3-1 基线分叉：x_X(t0) ≠ x_Y(t0)（>1e-6）且未来 RMSE > 1e-6
       ⇒ 父层当前状态 P 不充分（D21-M4 前半）。
  E3-2 干预（优先级=D2-0 反馈 §十七先例：relation cell 状态最先）：
       sham  不移植（分叉保持=对照）
       tier0 仅移植两个 RelationInputNeuron 状态（预期不消除——换能
             trace 短时标在 t0 已衰竭；如实登记）
       tier1 移植 RelationCell_2 完整状态 X→Y
       等化判据：RMSE(future_Y′, future_X) < 1e-9（确定性系统）。
  E3-3 裁定：tier1 等化 ⇒ G1_STATE_DIMENSION_CAUSALLY_SUPPORTED，
       最小充分候选 = RelationCell_2 膜态 ⇒ STOP_DEEPER_DECOMPOSITION
       （不再拆电容/bundle 微态）。
  登记观察（非门）：两臂未来峰相对 θ₂ 的位置（关系状态是否把未来
  χ_ρ₂ 从"不发生"推到"发生"——存在级分叉）。

复现入口：
  PYTHONIOENCODING=utf-8 python research/d2_recursive_v1/a8v2_attack.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from copy import deepcopy

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from d21_common import (  # noqa: E402
    DATA, RHO_MAIN_TRAJ, frozen_relation2_params, load_relation_ports,
    load_site23_windows)
from recursive_physical_impl import (  # noqa: E402
    T_TOTAL, build_relation2, recursive_drives, step_relation2)

T0 = 4200


def _rmse(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))


def _drives(arm, rho, s23_probe):
    """两臂驱动：X=消费 ρ_a；Y=未消费。未来探测（C 通道）相同。"""
    rports = [rho] if arm == "X" else []
    return recursive_drives(rports, s23_probe)


def _run_to(p, dr, dc, k_from, k_to, rec=None):
    for k in range(k_from, k_to):
        x = step_relation2(p, dr[k].value, dc[k].value)
        if rec is not None:
            rec.append(x)
    return p


def _transplant(dst, src, tier):
    if tier == "tier0":
        dst.tin_r.__dict__.update(deepcopy(src.tin_r.__dict__))
        dst.tin_c.__dict__.update(deepcopy(src.tin_c.__dict__))
    elif tier == "tier1":
        dst.cell.__dict__.update(deepcopy(src.cell.__dict__))
    elif tier == "sham":
        pass
    else:
        raise ValueError(tier)


def main() -> int:
    g, theta2, _rearm2 = frozen_relation2_params()
    rho = load_relation_ports()[RHO_MAIN_TRAJ]
    probe = load_site23_windows()["s23_far_b"]
    assert rho.t_rearm < T0 < probe[0].t_up, "t0 必须在 ρ 窗后、探测窗前"
    dX = _drives("X", rho, probe)
    dY = _drives("Y", rho, probe)
    assert dX[0][T0].value == dY[0][T0].value == 0.0
    assert dX[1][T0].value == dY[1][T0].value == 0.0

    # 基线：两臂到 t0，再跑相同未来
    pX = _run_to(build_relation2(g), *dX, 0, T0)
    pY = _run_to(build_relation2(g), *dY, 0, T0)
    x_X0, x_Y0 = pX.cell.activation, pY.cell.activation
    futX, futY = [], []
    _run_to(pX, *dX, T0, T_TOTAL, rec=futX)
    _run_to(pY, *dY, T0, T_TOTAL, rec=futY)
    base_rmse = _rmse(futX, futY)
    diverged = abs(x_X0 - x_Y0) > 1e-6 and base_rmse > 1e-6
    twin = {"t0": T0, "u_at_t0": [0.0, 0.0], "x_X_t0": x_X0,
            "x_Y_t0": x_Y0, "dx_t0": abs(x_X0 - x_Y0),
            "future_rmse": base_rmse,
            "future_peak_X": max(futX), "future_peak_Y": max(futY),
            "theta2": theta2,
            "existence_divergence": (max(futX) >= theta2) != (
                max(futY) >= theta2),
            "parent_state_insufficient": diverged}
    print(f"  twin: x(t0) X/Y = {x_X0:.5f}/{x_Y0:.5f} "
          f"future RMSE={base_rmse:.3e}")
    print(f"  future peak X/Y = {max(futX):.4f}/{max(futY):.4f} "
          f"vs theta2={theta2:.4f} "
          f"existence divergence={twin['existence_divergence']}")

    rows = [{"arm": "X_ref", "x_t0": x_X0, "rmse_vs_X": 0.0,
             "equalized": True},
            {"arm": "Y_baseline", "x_t0": x_Y0, "rmse_vs_X": base_rmse,
             "equalized": not diverged}]
    ruling = {"twin": twin}
    if diverged:
        for tier in ("sham", "tier0", "tier1"):
            pX2 = _run_to(build_relation2(g), *dX, 0, T0)
            pY2 = _run_to(build_relation2(g), *dY, 0, T0)
            _transplant(pY2, pX2, tier)
            fut = []
            _run_to(pY2, *dY, T0, T_TOTAL, rec=fut)
            r = _rmse(futX, fut)
            eq = r < 1e-9
            rows.append({"arm": f"Y+{tier}", "x_t0": pY2.cell.activation,
                         "rmse_vs_X": r, "equalized": eq})
            print(f"  intervention {tier:5s}: RMSE={r:.3e} equalized={eq}")
        eq = {r["arm"]: r["equalized"] for r in rows}
        if eq.get("Y+tier1"):
            ruling["ruling"] = "G1_STATE_DIMENSION_CAUSALLY_SUPPORTED"
            ruling["sham_ok"] = not eq.get("Y+sham", True)
            ruling["tier0_insufficient"] = not eq.get("Y+tier0", True)
            ruling["minimal_sufficient_state_candidate"] = \
                "RelationCell_2 membrane state (single-cell x_rho2 carrier)"
            ruling["stop"] = ("STOP_DEEPER_DECOMPOSITION "
                              "(D2-0 反馈§十三/§十七先例)")
        else:
            ruling["ruling"] = "CORRELATIONAL_ONLY"
            ruling["stop"] = "候选载体未确认——登记，不深挖"
    else:
        ruling["ruling"] = "NO_STATE_DIVERGENCE_AT_T0"
        ruling["stop"] = "twin 未分叉——D21-M4 证据缺失，走终态 B 评估"

    with open(os.path.join(DATA, 'a8v2_twins.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(twin))
        w.writeheader(); w.writerow(twin)
    with open(os.path.join(DATA, 'state_interventions.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    with open(os.path.join(DATA, 'd21_a8v2_ruling.json'), 'w',
              encoding='utf-8') as f:
        json.dump(ruling, f, indent=1, ensure_ascii=False)

    ok = ruling["ruling"] == "G1_STATE_DIMENSION_CAUSALLY_SUPPORTED"
    print(f"RULING: {ruling['ruling']} | {ruling.get('stop', '')}")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
