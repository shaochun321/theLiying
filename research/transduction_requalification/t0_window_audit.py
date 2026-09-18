"""t0_window_audit.py — Phase T0 𝒟_i 转导合同重资格化（T0-A/B/C）。

TYPE:INFRA（research/ 观测层，只读消费 nexus_v1 + tss 转导映射；
nexus_v1/ 与 tss/ 零改动；度量函数 import 复用 W0-E 冻结契约脚本，
不改动该脚本）

依据：主线重启 R1 收口（fbccfa1）W0-E 判定"塌缩在 D_i 转导窗非场层"；
BACKLOG 登记 Phase T0（2026-09-18，方案经用户批准）。

## 度量契约（继承 W0-E，先冻结后实验）

  D(X,Y)=RMS 轨迹距离（T=2000 步）；D̂=D/max(RMS)；
  collapse_ratio=D̂_support/D̂_world；
  判定/对: ratio<0.01→COLLAPSE；[0.01,0.5)→PARTIAL_COMPRESSION；
           ≥0.5→PRESERVED；前提 D̂_world>0.1 否则 N/A。
  实现直接 import w0e_history_discrimination 的 run_history/dhat/
  scenario，保证与 W0-E 已冻结数值逐位可比。

## 解析预测（先登记、后实测——R1b oracle 教训：手算阈值必须实测）

  合同（REFERENCE_TRANSDUCTION_CONFIG）：u=clip[κ(q−q0)+b]，
  κ≈0.0013759, b≈−0.0550663, clip=[0, 0.04]。
  T_floor = −b/κ ≈ 40.02（u_lin 过 0，地板死区边界）
  T_ceil  = (0.04−b)/κ ≈ 69.14（顶棚 clip 起点）
  场线性 ⇒ T_peak ∝ scale（W0-E 实测 scale=1.0 时 T_peak=61.826）
  ⇒ 预测地板侧塌缩转变 s ≈ 40.02/61.826 ≈ 0.647 附近；
    顶棚起夹 s ≈ 69.14/61.826 ≈ 1.118 附近。均为预测，以实测为准。

## T0-A 资格窗边界测绘

  scale 扫描 {0.1, 0.3, 0.5, 0.6, 0.65, 0.7, 0.8, 1.0, 1.12, 1.5,
  3.0, 10, 50}（预测边界附近加密）；一轮自动加密：相邻档任一对
  verdict 类别跳变时插入几何中点 sqrt(s1·s2)，至多 4 档。

## T0-B 塌缩机制三段分解（乘法）

  stage1 纯 κ 缩放 u=κ(q−q0)          —— 预期 ratio≡1.0（自检门）
  stage2 +偏置    u=κ(q−q0)+b（=u_lin）—— f_bias = r2/r1
  stage3 +clip    u=clip[u_lin]        —— f_clip = r3/r2
  r3 即 W0-E 的 collapse_ratio。

## T0-C 窗内 clip 放大审计

  逐 scale×历史统计：地板命中率（u_lin≤0）/顶棚命中率（u_lin≥0.04）/
  u_interior=[0.005,0.03] 内占比——回答合同宣称的 u_interior 保证对
  参考类轨迹是否真实成立，还是瞬态已出窗被 clip（ratio>1 放大来源）。

## 自检门

  ① 各 scale×历史注入能量 = scale×300（相对误差<1e-9）；
  ② stage1 ratio 与 D̂_world 之比 ≡ 1.0（<1e-9，纯缩放不变性）；
  ③ T_peak/scale 恒定性（线性场复核，只记录最大偏差不判死）。

审计边界：同 w0_structure_audit.py——读取世界节点真值属 World/转导
自身资格审计，非电路 benchmark（HC-012 红线不适用）。support 读出
止于 u_i（G0 入口合同处），occurrence/closure 级留 G1（§26 禁改
G0 驱动循环仍有效）。

输出：data/t0_window.json；verdict 跳变桥接档轨迹 CSV（≤4 份）。
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, '..', '..'))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, 'research', 'world_requalification'))

import w0e_history_discrimination as w0e  # noqa: E402  (frozen metric contract)
from tss.generators.skin_transduction import (  # noqa: E402
    REFERENCE_TRANSDUCTION_CONFIG as CFG)

DATA_DIR = os.path.join(_HERE, 'data')
SCALES = [0.1, 0.3, 0.5, 0.6, 0.65, 0.7, 0.8, 1.0, 1.12, 1.5, 3.0, 10.0, 50.0]
PAIRS = (("A", "B"), ("A", "C"), ("B", "C"))
U_INTERIOR = (0.005, 0.03)
MAX_REFINE = 4

T_FLOOR_PRED = -CFG.b_i / CFG.kappa_i
T_CEIL_PRED = (CFG.u_clip_max - CFG.b_i) / CFG.kappa_i


def verdict_of(dw: float, ratio: float) -> str:
    """W0-E 判定契约（阈值原文复刻，不重新发明）。"""
    if dw <= 0.1:
        return "N/A"
    if ratio < 0.01:
        return "WORLD_TO_SUPPORT_COLLAPSE"
    if ratio < 0.5:
        return "PARTIAL_COMPRESSION"
    return "PRESERVED"


def stage1_traj(world_traj):
    """stage1 纯 κ 缩放（无偏置无 clip）。"""
    return [[CFG.kappa_i * (T - CFG.q_i0) for T in row] for row in world_traj]


def clip_stats(u_traj, ulin_traj):
    """T0-C：地板/顶棚命中率与 u_interior 占比（按样本 (t,i) 统计）。"""
    n = len(ulin_traj) * len(ulin_traj[0])
    floor = sum(1 for row in ulin_traj for v in row if v <= CFG.u_clip_min)
    ceil_ = sum(1 for row in ulin_traj for v in row if v >= CFG.u_clip_max)
    interior = sum(1 for row in u_traj for v in row
                   if U_INTERIOR[0] <= v <= U_INTERIOR[1])
    return {"floor_frac": floor / n, "ceil_frac": ceil_ / n,
            "interior_frac": interior / n}


def audit_scale(scale: float):
    """跑三历史，返回该 scale 的全部 T0-A/B/C 度量。"""
    runs = {n: w0e.run_history(n, scale) for n in ("A", "B", "C")}
    for n, r in runs.items():  # 自检门①：等能量
        expect = scale * 300.0
        assert abs(r["injected"] - expect) <= 1e-9 * expect, \
            f"energy check failed: {n}@{scale}: {r['injected']} != {expect}"
    t_peak = max(r["t_range"][1] for r in runs.values())
    pairs_out = {}
    for x, y in PAIRS:
        dw = w0e.dhat(runs[x]["world"], runs[y]["world"])
        r1 = w0e.dhat(stage1_traj(runs[x]["world"]),
                      stage1_traj(runs[y]["world"])) / max(dw, 1e-30)
        assert abs(r1 - 1.0) <= 1e-9, \
            f"stage1 self-check failed @{scale} {x}-{y}: r1={r1}"  # 自检门②
        r2 = w0e.dhat(runs[x]["ulin"], runs[y]["ulin"]) / max(dw, 1e-30)
        r3 = w0e.dhat(runs[x]["u"], runs[y]["u"]) / max(dw, 1e-30)
        pairs_out["-".join((x, y))] = {
            "D_world_hat": dw, "ratio_stage1_scale": r1,
            "ratio_stage2_bias": r2, "ratio_stage3_clip": r3,
            "f_bias": r2 / max(r1, 1e-30), "f_clip": r3 / max(r2, 1e-30),
            "verdict": verdict_of(dw, r3)}
    return {"t_peak": t_peak,
            "clip_stats": {n: clip_stats(runs[n]["u"], runs[n]["ulin"])
                           for n in ("A", "B", "C")},
            "pairs": pairs_out}, runs


def verdict_class(entry) -> tuple:
    """相邻档比较用：三对 verdict 元组。"""
    return tuple(entry["pairs"]["-".join(p)]["verdict"] for p in PAIRS)


def dump_csv(scale: float, runs) -> str:
    path = os.path.join(DATA_DIR, f"t0_traj_scale{scale:g}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t"] + [f"{n}_T{i}" for n in "ABC" for i in range(3)]
                   + [f"{n}_u{i}" for n in "ABC" for i in range(3)])
        for t in range(w0e.T_WINDOW):
            w.writerow([t]
                       + [runs[n]["world"][t][i] for n in "ABC"
                          for i in range(3)]
                       + [runs[n]["u"][t][i] for n in "ABC" for i in range(3)])
    return path


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 72)
    print("Phase T0 — D_i 转导合同重资格化（T0-A 窗边界 / T0-B 分解 / T0-C clip）")
    print("=" * 72)
    print(f"解析预测(先登记): T_floor={T_FLOOR_PRED:.2f} "
          f"T_ceil={T_CEIL_PRED:.2f} "
          f"s_low*≈{T_FLOOR_PRED / 61.826:.3f} s_ceil≈{T_CEIL_PRED / 61.826:.3f}")

    results = {}
    runs_cache = {}
    for s in SCALES:
        results[s], runs_cache[s] = audit_scale(s)

    # 一轮自动加密：相邻档 verdict 类别跳变 → 插入几何中点（至多 MAX_REFINE）
    refined = []
    ordered = sorted(results)
    for a, b in zip(ordered, ordered[1:]):
        if verdict_class(results[a]) != verdict_class(results[b]) \
                and len(refined) < MAX_REFINE:
            mid = round(math.sqrt(a * b), 4)
            if mid not in results:
                results[mid], runs_cache[mid] = audit_scale(mid)
                refined.append(mid)

    # 汇总打印 + 边界定位
    print(f"\n加密档: {refined or '无'}")
    hdr = (f"{'scale':>8} {'T_peak':>9} | " +
           " | ".join(f"{'-'.join(p)}: r3(f_bias·f_clip) verdict"
                      for p in PAIRS))
    print(hdr)
    t_peak_ratio = []
    for s in sorted(results):
        e = results[s]
        t_peak_ratio.append(e["t_peak"] / s)
        cells = []
        for p in PAIRS:
            d = e["pairs"]["-".join(p)]
            cells.append(f"{d['ratio_stage3_clip']:.4f}"
                         f"({d['f_bias']:.3f}·{d['f_clip']:.3f}) "
                         f"{d['verdict'][:9]}")
        print(f"{s:>8g} {e['t_peak']:>9.2f} | " + " | ".join(cells))

    # 自检门③：T_peak/scale 线性复核（记录不判死）
    lin_dev = (max(t_peak_ratio) - min(t_peak_ratio)) / max(t_peak_ratio)
    print(f"\n线性复核 T_peak/scale: max_rel_dev={lin_dev:.3e}")

    # 边界档（verdict 跳变的桥接对）→ CSV（≤4 份，取跳变处两侧档）
    boundary_scales = []
    ordered = sorted(results)
    for a, b in zip(ordered, ordered[1:]):
        if verdict_class(results[a]) != verdict_class(results[b]):
            for s in (a, b):
                if s not in boundary_scales and len(boundary_scales) < 4:
                    boundary_scales.append(s)
    csv_paths = [dump_csv(s, runs_cache[s]) for s in boundary_scales]

    # T0-C 打印（参考档 + 边界档）
    print("\nT0-C clip 审计（floor/ceil 命中率, u_interior 占比）:")
    for s in sorted(set([1.0] + boundary_scales)):
        st = results[s]["clip_stats"]
        row = "  ".join(f"{n}: fl={st[n]['floor_frac']:.3f}"
                        f" ce={st[n]['ceil_frac']:.3f}"
                        f" int={st[n]['interior_frac']:.3f}"
                        for n in "ABC")
        print(f"  scale={s:g}: {row}")

    out = {
        "contract": {"inherited_from": "w0e_history_discrimination.py",
                     "collapse": "<0.01", "partial": "[0.01,0.5)",
                     "preserved": ">=0.5", "precondition_dworld": ">0.1"},
        "analytic_predictions": {"T_floor": T_FLOOR_PRED,
                                 "T_ceil": T_CEIL_PRED,
                                 "s_low_pred": T_FLOOR_PRED / 61.826,
                                 "s_ceil_pred": T_CEIL_PRED / 61.826},
        "scales_scanned": sorted(results), "refined_scales": refined,
        "boundary_scales": boundary_scales,
        "t_peak_linearity_max_rel_dev": lin_dev,
        "u_interior": U_INTERIOR,
        "per_scale": {str(s): results[s] for s in sorted(results)},
        "csv_files": [os.path.basename(p) for p in csv_paths],
    }
    path = os.path.join(DATA_DIR, "t0_window.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n落盘: {path}")
    for p in csv_paths:
        print(f"落盘: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
