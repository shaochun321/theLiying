"""wt0_cross_pair_matrix.py — Cross-Pair Matrix + 信息缩减两端审计（WT0 §11/§12）。

TYPE:INFRA（research/ 观测层，纯场+转导纯函数，无 G0；零母体改动）

依据：外部《WT0 方案》§12（World v1 合法参数变化 × 同一套 legacy D 合同
交叉；本轮禁止新 κ/b/clip——§8）+ §11（必须同时报最强保留/最强丢失两端
案例，禁止只报平均）+ T1-A §8 新度量契约（本轮即启用：D_world /
D_boundary / D_transduced 绝对值+归一值并报，附占用率，禁止裸 ratio）。

## 实验网格（先冻结）

  World 参数（保持 r_leak=10/κ 绑定——解绑属 W1，本轮不越界）：
    κ ∈ {0.025, 0.05, 0.1} ⇒ r_leak_ambient ∈ {400, 200, 100}
  历史参数（每 κ 下 12 条历史）：
    驱动节点 ∈ {node0, node2} × 幅值 a ∈ {0.65, 1.0, 1.5}
    × 时序 ∈ {sustained: I=a, t∈[0,300) | pulse: I=6a, t∈[0,25)∪[500,525)}
  观测窗 T=2000 步，dt=1.0。配对：同 κ 内两两配对（C(12,2)=66 对 ×3κ
  =198 行）。幅值轴差异是合法历史差异（剂量维度），不做等能量约束，
  每历史登记注入能量。

## 度量（每对，全部并报）

  D_world_abs / D̂_world        —— 3 节点全态 RMS 距离（绝对+归一）
  D_bnd_red_abs / D̂_bnd_red    —— Y_B=node0 reduced-boundary 配置
  D_tr_full_abs / D̂_tr_full    —— u(3 节点)（Y_B=三节点全可见配置）
  D_tr_red_abs / D̂_tr_red      —— u(node0)
  retention_full/red = D̂_tr/D̂_world（**必须连同上述分子分母同читать**，
  单独引用即违反 T1-A §8）
  每历史：floor/ceiling/interior 占用率 + 注入能量。

## 两端案例提取（§11）

  前提 D̂_world>0.1；D_preserve^max = retention 最大对；
  D_loss^max = retention 最小对（理想形态：世界差大而转导差≈0）。
  两种边界配置各自提取。

输出：data/WT0_CROSS_PAIR_MATRIX.csv + data/wt0_cross_pair_summary.json
"""
from __future__ import annotations

import csv
import itertools
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..')))

from nexus_v1.components.skin_three_point import build_three_point_skin  # noqa: E402
from tss.generators.skin_transduction import (  # noqa: E402
    REFERENCE_TRANSDUCTION_CONFIG as CFG, transduce)

DATA_DIR = os.path.join(_HERE, 'data')
T_WINDOW = 2000
KAPPAS = [0.025, 0.05, 0.1]
NODES = [0, 2]
AMPS = [0.65, 1.0, 1.5]
TIMINGS = ["sus", "pulse"]
U_INTERIOR = (0.005, 0.03)


def injection_plan(node: int, amp: float, timing: str):
    if timing == "sus":
        return {node: [(0, 300, amp)]}
    return {node: [(0, 25, 6 * amp), (500, 525, 6 * amp)]}


def run_history(kappa: float, node: int, amp: float, timing: str):
    g = build_three_point_skin(kappa=kappa, r_leak_ambient=10.0 / kappa)
    plan = injection_plan(node, amp, timing)
    world, u_full = [], []
    injected = 0.0
    floor = ceil_ = interior = 0
    for t in range(T_WINDOW):
        ext = {}
        for nid, spans in plan.items():
            for (t0, t1, cur) in spans:
                if t0 <= t < t1:
                    ext[nid] = ext.get(nid, 0.0) + cur
        injected += sum(ext.values())
        g.step(1.0, ext)
        temps = [g.cells[i].temperature for i in range(3)]
        world.append(temps)
        us = [transduce(T, CFG) for T in temps]
        u_full.append(us)
        for T in temps:
            u_lin = CFG.kappa_i * (T - CFG.q_i0) + CFG.b_i
            if u_lin <= CFG.u_clip_min:
                floor += 1
            elif u_lin >= CFG.u_clip_max:
                ceil_ += 1
        for u in us:
            if U_INTERIOR[0] <= u <= U_INTERIOR[1]:
                interior += 1
    n = T_WINDOW * 3
    return {"world": world, "u_full": u_full, "injected": injected,
            "floor_frac": floor / n, "ceil_frac": ceil_ / n,
            "interior_frac": interior / n}


def rms(traj) -> float:
    return math.sqrt(sum(v * v for row in traj for v in row)
                     / (len(traj) * len(traj[0])))


def dist(x, y) -> float:
    return math.sqrt(sum((a - b) ** 2 for rx, ry in zip(x, y)
                         for a, b in zip(rx, ry)) / (len(x) * len(x[0])))


def col(traj, i):
    return [[row[i]] for row in traj]


def pair_metrics(hx, hy):
    def both(x, y):
        d = dist(x, y)
        return d, d / max(rms(x), rms(y), 1e-30)
    dw, dw_h = both(hx["world"], hy["world"])
    db, db_h = both(col(hx["world"], 0), col(hy["world"], 0))
    dtf, dtf_h = both(hx["u_full"], hy["u_full"])
    dtr, dtr_h = both(col(hx["u_full"], 0), col(hy["u_full"], 0))
    return {"D_world_abs": dw, "D_world_hat": dw_h,
            "D_bnd_red_abs": db, "D_bnd_red_hat": db_h,
            "D_tr_full_abs": dtf, "D_tr_full_hat": dtf_h,
            "D_tr_red_abs": dtr, "D_tr_red_hat": dtr_h,
            "retention_full": dtf_h / max(dw_h, 1e-30),
            "retention_red": dtr_h / max(db_h, 1e-30)}


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 78)
    print("WT0 §11/§12 — Cross-Pair Matrix（198 对）+ 信息缩减两端审计")
    print("=" * 78)
    rows = []
    extremes = {"full": {"preserve": None, "loss": None},
                "red": {"preserve": None, "loss": None}}
    for kappa in KAPPAS:
        hists = {}
        for node, amp, timing in itertools.product(NODES, AMPS, TIMINGS):
            label = f"n{node}_a{amp:g}_{timing}"
            hists[label] = run_history(kappa, node, amp, timing)
        for (lx, hx), (ly, hy) in itertools.combinations(hists.items(), 2):
            m = pair_metrics(hx, hy)
            row = {"kappa": kappa, "r_leak": 10.0 / kappa,
                   "hist_x": lx, "hist_y": ly,
                   "E_x": hx["injected"], "E_y": hy["injected"],
                   **m,
                   "floor_x": hx["floor_frac"], "floor_y": hy["floor_frac"],
                   "ceil_x": hx["ceil_frac"], "ceil_y": hy["ceil_frac"],
                   "int_x": hx["interior_frac"], "int_y": hy["interior_frac"]}
            rows.append(row)
            if m["D_world_hat"] > 0.1:
                for cfg_name, ret_key in (("full", "retention_full"),
                                          ("red", "retention_red")):
                    e = extremes[cfg_name]
                    if e["preserve"] is None or m[ret_key] > e["preserve"][ret_key]:
                        e["preserve"] = row
                    if e["loss"] is None or m[ret_key] < e["loss"][ret_key]:
                        e["loss"] = row

    # 汇总统计（辅助阅读，不替代两端案例）
    n_zero_full = sum(1 for r in rows
                      if r["D_world_hat"] > 0.1 and r["D_tr_full_abs"] == 0.0)
    n_zero_red = sum(1 for r in rows
                     if r["D_world_hat"] > 0.1 and r["D_tr_red_abs"] == 0.0)
    n_valid = sum(1 for r in rows if r["D_world_hat"] > 0.1)
    print(f"\n配对总数={len(rows)}  前提有效(D̂_world>0.1)={n_valid}  "
          f"完全湮灭: full={n_zero_full}  reduced={n_zero_red}")
    for cfg_name in ("full", "red"):
        for kind in ("preserve", "loss"):
            r = extremes[cfg_name][kind]
            if r is None:
                continue
            key = "retention_full" if cfg_name == "full" else "retention_red"
            print(f"[{cfg_name}] D_{kind}^max: κ={r['kappa']:g} "
                  f"{r['hist_x']} vs {r['hist_y']}  "
                  f"D̂_world={r['D_world_hat']:.4f} "
                  f"D_tr_abs={(r['D_tr_full_abs'] if cfg_name == 'full' else r['D_tr_red_abs']):.6f} "
                  f"retention={r[key]:.4f}  "
                  f"fl={r['floor_x']:.2f}/{r['floor_y']:.2f} "
                  f"ce={r['ceil_x']:.2f}/{r['ceil_y']:.2f}")

    csv_path = os.path.join(DATA_DIR, "WT0_CROSS_PAIR_MATRIX.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    summary = {"grid": {"kappas": KAPPAS, "nodes": NODES, "amps": AMPS,
                        "timings": TIMINGS, "t_window": T_WINDOW,
                        "r_leak_binding": "10/kappa (W1 前不解绑)"},
               "n_pairs": len(rows), "n_valid": n_valid,
               "n_annihilated_full": n_zero_full,
               "n_annihilated_red": n_zero_red,
               "extremes": {c: {k: (None if v is None else v)
                                for k, v in e.items()}
                            for c, e in extremes.items()}}
    json_path = os.path.join(DATA_DIR, "wt0_cross_pair_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"落盘: {csv_path}\n落盘: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
