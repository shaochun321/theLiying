"""depth_collapse_attack.py — D2-1 StepD/E2：降深替换攻击（方案 §12，
评判修正=功能面判据）。

TYPE:INFRA（research/ 层；全部 stage-2 replay）。

用 ρ_a 的原始父输入 (χ_28^(0), χ_31^(0)) 替换 χ_ρ^(1) 进入 R 通道，
检查能否完全重构 Full 条件的功能面。替换必须走**同一 𝒩 家族**（相位
驱动）——typed 接口纪律下不允许 bespoke 解码器（该边界如实登记）。

## COMPUTE_BUDGET

  physical_trajectories=0; stage-2 runs = 3（full 重放 + S1 + S2）;
  interventions=0

## 预注册判据（功能面，运行前冻结）

  DEPTH_COLLAPSE ⇔ 替换条件同时满足：
    (a) x_ρ₂ 轨迹 RMSE(x_sub, x_full) < 1e-6
    (b) χ_ρ₂ occurrence 计数相同且三边界逐位相等
  两个替换变体（同 𝒩 家族内的最强重构尝试）：
    S1 sum      ：R ← ϑ_28(t) + ϑ_31(t)（cal_C3_m 父窗 A[1521,2160)+
                  B[2127,2766) 各自相位驱动求和）
    S2 envelope ：R ← 包络伪窗 [1521,2766) 单相位驱动
  任一变体达成 (a)+(b) ⇒ DEPTH_COLLAPSE，本轮不得宣称新生成深度（§12）。
  预期（可证伪）：父窗活动整体早于 ρ 窗 ~1000 步 ⇒ 功能面显著不同 ⇒
  M3 Depth Non-Collapse。附带如实登记：功能面距离（RMSE/边界移位/计数）。

复现入口：
  PYTHONIOENCODING=utf-8 python research/d2_recursive_v1/depth_collapse_attack.py
"""
from __future__ import annotations

import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from d21_common import (  # noqa: E402
    DATA, DT_G, RHO_MAIN_TRAJ, frozen_relation2_params,
    load_relation_ports, load_site23_windows, relation2_address)
from relation_physical_impl import PortWindow, load_port_windows  # noqa: E402
from recursive_physical_impl import (  # noqa: E402
    T_TOTAL, build_relation2, recursive_drives, step_relation2)
from tss.adapters.relation_replay_adapter import build_phase_drive  # noqa: E402
from tss.generators.occurrence import OccurrenceClosure  # noqa: E402


def _rmse(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))


def _run(yr_seq, yc_seq, sup_seq, g, theta2, rearm2, rho2_addr):
    p = build_relation2(g)
    cl = OccurrenceClosure(address=rho2_addr, theta_up=theta2,
                           theta_down=0.1 * theta2,
                           rearm_min_steps=rearm2, dt=DT_G)
    xs = []
    for k in range(T_TOTAL):
        x = step_relation2(p, yr_seq[k], yc_seq[k])
        cl.update(x, k, phys_support=sup_seq[k])
        xs.append(x)
    return xs, cl.events


def main() -> int:
    g, theta2, rearm2 = frozen_relation2_params()
    rho2_addr, _rho, _c = relation2_address()
    rho = load_relation_ports()[RHO_MAIN_TRAJ]
    s23 = load_site23_windows()["s23_ov"]
    parent_w = load_port_windows()[RHO_MAIN_TRAJ]   # cal_C3_m 父窗 A/B

    # Full：χ_ρ^(1) + χ_23^(0)
    dr, dc = recursive_drives([rho], s23)
    yr_full = [s.value for s in dr]
    yc = [s.value for s in dc]
    sup_full = [dr[k].parent_support or dc[k].parent_support
                for k in range(T_TOTAL)]
    xs_full, ev_full = _run(yr_full, yc, sup_full, g, theta2, rearm2,
                            rho2_addr)

    # S1 sum：R ← ϑ_28 + ϑ_31
    dA = build_phase_drive(T_TOTAL, DT_G, parent_w["A"])
    dB = build_phase_drive(T_TOTAL, DT_G, parent_w["B"])
    yr_s1 = [dA[k].value + dB[k].value for k in range(T_TOTAL)]
    sup_s1 = [dA[k].parent_support or dB[k].parent_support
              or dc[k].parent_support for k in range(T_TOTAL)]
    xs_s1, ev_s1 = _run(yr_s1, yc, sup_s1, g, theta2, rearm2, rho2_addr)

    # S2 envelope：R ← 包络伪窗单相位驱动
    env = PortWindow(min(w.t_up for w in parent_w["A"] + parent_w["B"]),
                     max(w.t_rearm for w in parent_w["A"] + parent_w["B"]),
                     "envelope_pseudo_window")
    dE = build_phase_drive(T_TOTAL, DT_G, [env])
    yr_s2 = [s.value for s in dE]
    sup_s2 = [dE[k].parent_support or dc[k].parent_support
              for k in range(T_TOTAL)]
    xs_s2, ev_s2 = _run(yr_s2, yc, sup_s2, g, theta2, rearm2, rho2_addr)

    def _bounds(evs):
        return [(e.t_up, e.t_down, e.t_rearm) for e in evs]

    out = {"functional_criterion": "collapse iff RMSE<1e-6 AND same occ "
                                   "count AND bit-equal boundaries",
           "full": {"peak": max(xs_full), "occ": len(ev_full),
                    "bounds": _bounds(ev_full)}}
    collapse = False
    for tag, xs, evs in (("S1_sum", xs_s1, ev_s1),
                         ("S2_envelope", xs_s2, ev_s2)):
        r = _rmse(xs, xs_full)
        same_occ = (len(evs) == len(ev_full)
                    and _bounds(evs) == _bounds(ev_full))
        this_collapse = r < 1e-6 and same_occ
        collapse = collapse or this_collapse
        out[tag] = {"rmse_vs_full": r, "peak": max(xs), "occ": len(evs),
                    "bounds": _bounds(evs), "boundaries_equal": same_occ,
                    "collapse": this_collapse}
        print(f"  {tag}: RMSE={r:.4e} occ={len(evs)} bounds={_bounds(evs)}"
              f" collapse={this_collapse}")
    out["verdict"] = "DEPTH_COLLAPSE" if collapse else "DEPTH_NON_COLLAPSE"
    out["scope_note"] = ("substitution restricted to the same naturalization"
                         " family (phase drives) — bespoke decoders are "
                         "outside the typed-interface contract (registered "
                         "boundary of this attack)")
    print(f"  full: occ={len(ev_full)} bounds={_bounds(ev_full)} "
          f"peak={max(xs_full):.4f}")

    with open(os.path.join(DATA, 'depth_collapse_attack.json'), 'w',
              encoding='utf-8') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    ok = not collapse and len(ev_full) == 1
    print("VERDICT:", out["verdict"])
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
