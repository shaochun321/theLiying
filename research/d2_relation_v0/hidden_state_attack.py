"""hidden_state_attack.py — D2-0 Step4b：C6（同当前输入/不同前史）+
关系 Hidden Dynamics Closure（反馈 §十六：C6 即入口，不另设阶段）。

TYPE:INFRA（research/ 层）。

⚠ DIAGNOSTIC_INTERVENTION 登记（E-9 家族）：状态移植（cell/换能神经元
__dict__ 拷贝）仅限研究区因果定位，禁止流入 production。

## COMPUTE_BUDGET

  physical_trajectories=0（组合驱动=对 IMMUTABLE_CACHE 窗的 replay 编排，
  无新物理轨迹）; replays ≈ 8; interventions = 3 ≤ 6（反馈 §十七）

## 设计（预注册）

C6 双臂（不同前史，相同未来探测）：
  臂X 前史 = cal_C2_sim 的 A+B 窗（双父共时）
  臂Y 前史 = cal_C0_A 的 A 窗（单父）
  相同未来探测 = cal_C3_l 的 B 窗（晚发，B 通道，t_up≈3127）
  t0 = 3000（前史窗结束后 ~800 子步、探测前；两臂该时刻输入均为 (0,0)）

C6 判据：x_X(t0) ≠ x_Y(t0)（同当前输入不同状态）且未来轨迹 RMSE>1e-6
  ⇒ relation memory 成立（D2-M2 的直接机器证据）。

Hidden Dynamics（干预优先级=反馈 §十七：relation capacitor/state 最先）：
  sham    ：不移植（基线分叉保持——对照）
  tier0   ：仅移植两个 RelationInputNeuron 状态（预期不消除——换能
            trace τ≈0.1s 在 t0 已衰竭）
  tier1   ：移植 RelationCell 完整状态（膜电容等）X→Y
等化判据：干预后 Y′ 未来与 X 未来 RMSE<1e-9（确定性系统）。
裁定：tier1 等化 ⇒ 最小充分候选 = RelationCell 状态（单细胞膜态）⇒
  RELATION_MINIMAL_SUFFICIENT_STATE_CANDIDATE + STOP_DEEPER_DECOMPOSITION
  （不再拆电容/bundle 微态——反馈 §十三）。

复现入口：
  PYTHONIOENCODING=utf-8 python research/d2_relation_v0/hidden_state_attack.py
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
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..')))

from d2_common import DATA, DT_G  # noqa: E402
from relation_physical_impl import (  # noqa: E402
    PortWindow, build_relation, load_port_windows, step_relation)
from tss.adapters.relation_replay_adapter import build_phase_drive  # noqa: E402

T_TOTAL = 8000
T0 = 3000


def _g_canon():
    with open(os.path.join(DATA, 'relation_calibration.json'),
              encoding='utf-8') as f:
        return json.load(f)["canonical_reference"]["g_rel"]


def _rmse(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))


def _arm_drives(windows, arm):
    """组合驱动：前史窗 + 相同未来探测窗（全部来自缓存端口）。"""
    probe_b = windows["cal_C3_l"]["B"]      # 晚发 B 窗（未来探测）
    if arm == "X":
        wa = windows["cal_C2_sim"]["A"]
        wb = list(windows["cal_C2_sim"]["B"]) + list(probe_b)
    elif arm == "Y":
        wa = windows["cal_C0_A"]["A"]
        wb = list(probe_b)
    else:
        raise ValueError(arm)
    da = build_phase_drive(T_TOTAL, DT_G, wa)
    db = build_phase_drive(T_TOTAL, DT_G, wb)
    return da, db


def _run_to(p, da, db, k_from, k_to, rec=None):
    for k in range(k_from, k_to):
        x = step_relation(p, da[k].value, db[k].value)
        if rec is not None:
            rec.append(x)
    return p


def _transplant(dst, src, tier):
    if tier == "tier0":
        dst.tin_a.__dict__.update(deepcopy(src.tin_a.__dict__))
        dst.tin_b.__dict__.update(deepcopy(src.tin_b.__dict__))
    elif tier == "tier1":
        dst.cell.__dict__.update(deepcopy(src.cell.__dict__))
    elif tier == "sham":
        pass
    else:
        raise ValueError(tier)


def main() -> int:
    g = _g_canon()
    windows = load_port_windows()
    probe_t_up = windows["cal_C3_l"]["B"][0].t_up
    assert T0 < probe_t_up, "t0 必须在探测窗之前"
    dX, dY = _arm_drives(windows, "X"), _arm_drives(windows, "Y")
    assert dX[0][T0].value == dY[0][T0].value == 0.0
    assert dX[1][T0].value == dY[1][T0].value == 0.0

    # 基线：两臂到 t0，记录状态差；再跑相同未来
    pX = _run_to(build_relation(g), *dX, 0, T0)
    pY = _run_to(build_relation(g), *dY, 0, T0)
    x_X0, x_Y0 = pX.cell.activation, pY.cell.activation
    futX, futY = [], []
    _run_to(pX, *dX, T0, T_TOTAL, rec=futX)
    _run_to(pY, *dY, T0, T_TOTAL, rec=futY)   # Y 的未来探测与 X 相同（probe_b）
    base_rmse = _rmse(futX, futY)
    diverged = abs(x_X0 - x_Y0) > 1e-6 and base_rmse > 1e-6
    twin = {"t0": T0, "u_at_t0": [0.0, 0.0], "x_X_t0": x_X0,
            "x_Y_t0": x_Y0, "dx_t0": abs(x_X0 - x_Y0),
            "future_rmse": base_rmse, "c6_relation_memory": diverged}
    print(f"  C6: x(t0) X/Y = {x_X0:.5f}/{x_Y0:.5f} "
          f"future RMSE={base_rmse:.3e} ⇒ "
          f"{'MEMORY CONFIRMED' if diverged else 'NO MEMORY'}")

    rows = [{"arm": "X_ref", "x_t0": x_X0, "rmse_vs_X": 0.0,
             "equalized": True},
            {"arm": "Y_baseline", "x_t0": x_Y0, "rmse_vs_X": base_rmse,
             "equalized": not diverged}]
    ruling = {"twin": twin}
    if diverged:
        for tier in ("sham", "tier0", "tier1"):
            pX2 = _run_to(build_relation(g), *dX, 0, T0)
            pY2 = _run_to(build_relation(g), *dY, 0, T0)
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
            ruling["ruling"] = "RELATION_STATE_CAUSALLY_SUPPORTED"
            ruling["sham_ok"] = not eq.get("Y+sham", True)
            ruling["tier0_insufficient"] = not eq.get("Y+tier0", True)
            ruling["minimal_sufficient_state_candidate"] = \
                "RelationCell membrane state (single-cell x_rho carrier)"
            ruling["stop"] = ("RELATION_MINIMAL_SUFFICIENT_STATE_CANDIDATE"
                              " + STOP_DEEPER_DECOMPOSITION (反馈§十三/§十七)")
        else:
            ruling["ruling"] = "CORRELATIONAL_ONLY"
            ruling["stop"] = "候选载体未确认——登记，不深挖"
    else:
        ruling["ruling"] = "NO_RELATION_MEMORY_AT_T0"
        ruling["stop"] = "C6 未分叉——D2-M2 证据缺失，须走终态 C 评估"

    with open(os.path.join(DATA, 'relation_hidden_twins.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(twin))
        w.writeheader(); w.writerow(twin)
    with open(os.path.join(DATA, 'relation_interventions.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    with open(os.path.join(DATA, 'd2_hidden_ruling.json'), 'w',
              encoding='utf-8') as f:
        json.dump(ruling, f, indent=1, ensure_ascii=False)

    ok = ruling["ruling"] in ("RELATION_STATE_CAUSALLY_SUPPORTED",)
    print(f"RULING: {ruling['ruling']} | {ruling.get('stop', '')}")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
