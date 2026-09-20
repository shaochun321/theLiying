"""future_action_attack.py — D2-1 StepD/E4：with/block 未来行为作用
（方案 §16：Γ_with ≁ Γ_blocked，差异须体现在下一 relation trajectory /
closure / reachable state / resource path 之一）。

TYPE:INFRA（research/ 层；全部 stage-2 replay，确定性）。

## COMPUTE_BUDGET

  physical_trajectories=0; stage-2 runs = 3（with 重放 + blockR + blockC）;
  interventions=0（通道置零=replay 编排，非状态移植）

## 预注册判据（运行前冻结）

  Γ_with    = rc_main（R=χ_ρa^(1) + C=χ_23^(0)，closure 全程）
  Γ_blockR  = 阻断关系发生（R 通道置零）——主判据（方案 §16 的
              "阻断 relation state"）
  PASS ⇔ RMSE(x_blockR, x_with) > 1e-3 且（χ_ρ₂ 计数不同 或 三边界
  移位 >10 步 或 energy path 差 >1e-6）。
  预期（E1 已示的可证伪预期）：blockR ⇒ C 单通道峰 2.547 < θ₂ ⇒
  occ 1→0（存在级差异）。
  次级登记（NF-2 后果面，非门）：Γ_blockC（阻断 site23）——occ 预期
  保持 1 但边界移位（site23 亲缘=轨迹/边界级）。

复现入口：
  PYTHONIOENCODING=utf-8 python research/d2_recursive_v1/future_action_attack.py
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
from recursive_physical_impl import (  # noqa: E402
    T_TOTAL, build_relation2, recursive_drives, step_relation2)
from tss.generators.occurrence import OccurrenceClosure  # noqa: E402


def _rmse(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))


def _run(rports, cwins, g, theta2, rearm2, rho2_addr):
    dr, dc = recursive_drives(rports, cwins)
    p = build_relation2(g)
    cl = OccurrenceClosure(address=rho2_addr, theta_up=theta2,
                           theta_down=0.1 * theta2,
                           rearm_min_steps=rearm2, dt=DT_G)
    neurons = (p.tin_r, p.tin_c, p.cell)
    e0 = sum(n.energy for n in neurons)
    xs = []
    for k in range(T_TOTAL):
        x = step_relation2(p, dr[k].value, dc[k].value)
        cl.update(x, k, phys_support=dr[k].parent_support
                  or dc[k].parent_support)
        xs.append(x)
    e1 = sum(n.energy for n in neurons)
    return xs, cl.events, e0 - e1


def main() -> int:
    g, theta2, rearm2 = frozen_relation2_params()
    rho2_addr, _rho, _c = relation2_address()
    rho = load_relation_ports()[RHO_MAIN_TRAJ]
    s23 = load_site23_windows()["s23_ov"]

    xs_w, ev_w, de_w = _run([rho], s23, g, theta2, rearm2, rho2_addr)
    xs_br, ev_br, de_br = _run([], s23, g, theta2, rearm2, rho2_addr)
    xs_bc, ev_bc, de_bc = _run([rho], [], g, theta2, rearm2, rho2_addr)

    def _bounds(evs):
        return [(e.t_up, e.t_down, e.t_rearm) for e in evs]

    r_br = _rmse(xs_br, xs_w)
    shift_br = (len(ev_br) != len(ev_w)
                or any(abs(a - b) > 10 for ea, eb in zip(ev_br, ev_w)
                       for a, b in zip((ea.t_up, ea.t_down, ea.t_rearm),
                                       (eb.t_up, eb.t_down, eb.t_rearm))))
    de_diff = abs(de_br - de_w)
    e4_pass = r_br > 1e-3 and (len(ev_br) != len(ev_w) or shift_br
                               or de_diff > 1e-6)

    r_bc = _rmse(xs_bc, xs_w)
    out = {
        "with": {"peak": max(xs_w), "occ": len(ev_w),
                 "bounds": _bounds(ev_w), "energy_drop": de_w},
        "blockR": {"peak": max(xs_br), "occ": len(ev_br),
                   "bounds": _bounds(ev_br), "energy_drop": de_br,
                   "rmse_vs_with": r_br,
                   "existence_level_difference": len(ev_br) != len(ev_w)},
        "blockC_secondary": {"peak": max(xs_bc), "occ": len(ev_bc),
                             "bounds": _bounds(ev_bc),
                             "rmse_vs_with": r_bc,
                             "note": "NF-2 consequence registration: "
                                     "site23 parentage is trajectory/"
                                     "boundary-level, not existence-level"},
        "verdict": ("FUTURE_CAUSAL_ACTION_CONFIRMED" if e4_pass
                    else "FUTURE_CAUSAL_ACTION_NOT_MET"),
    }
    with open(os.path.join(DATA, 'future_action_attack.json'), 'w',
              encoding='utf-8') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    print(f"  with:   peak={max(xs_w):.4f} occ={len(ev_w)} "
          f"bounds={_bounds(ev_w)}")
    print(f"  blockR: peak={max(xs_br):.4f} occ={len(ev_br)} "
          f"RMSE={r_br:.4e} existence diff={len(ev_br) != len(ev_w)}")
    print(f"  blockC: peak={max(xs_bc):.4f} occ={len(ev_bc)} "
          f"bounds={_bounds(ev_bc)} RMSE={r_bc:.4e} (secondary, NF-2)")
    print("VERDICT:", out["verdict"])
    print("RESULT:", "PASS" if e4_pass else "FAIL")
    return 0 if e4_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
