"""w0e_history_discrimination.py — Phase W0-E 可区分世界历史（核心门）。

TYPE:INFRA（research/ 观测层，只读消费 nexus_v1 + tss 转导映射）

依据：《TSS 收尾与主线重启》§6 W0-E：构造非纯幅值差的世界历史
Γ_A/Γ_B/Γ_C，观察经局部支撑后 X^support 是否仍可区分；若
D_world≫0 而 D_support≈0 ⇒ 登记 WORLD_TO_SUPPORT_COLLAPSE。

## 实验设计

场 = P2-A 实际实例 build_three_point_skin()（TEST 档 κ=0.05,
r_leak=200，dt=1.0）。三历史**总注入能量相同**（E_tot = scale×300），
差异在空间分布与时序，非幅值：

  Γ_A 静止源   node0 恒流 I=scale     t∈[0,300)
  Γ_B 移动源   I=scale 依次 node0 [0,100) → node1 [100,200) → node2 [200,300)
  Γ_C 时序脉冲 node0 I=6×scale        t∈[0,25)∪[500,525)

两个幅度组：scale=1.0（温度落入 D_i^sim 标定域 [43.65,61.83] 附近，
T-STP 同量级）；scale=0.1（低温域，检验转导工作窗外行为）。

## support 层定义与范围声明

X^support = u_i(t) = transduce(T_i(t), REFERENCE_TRANSDUCTION_CONFIG)
（每节点独立 D_i；q_skin=皮肤节点温度，同 P2-A1b-3 接线语义）。
同时记录无 clip 线性读出 u_lin = κ·(q−q0)+b 作对照，以区分两种塌缩
机制：clip 截断（工作窗外）vs 线性压缩（κ 缩放不丢区分度）。
occurrence 级（G0 closure 输出）区分留待 G1——本轮 §26 禁改 G0 驱动
循环，support 读出止于 u_i（G0 入口合同处）。

## 度量契约（先于实验冻结）

  D(X,Y)   = RMS 轨迹距离 = sqrt(mean_t,i (x−y)²)，窗口 T=2000 步
  D̂(X,Y)  = D / max(RMS(X), RMS(Y))          （无量纲化）
  collapse_ratio(X,Y) = D̂_support / D̂_world
  判定/对: ratio < 0.01 → COLLAPSE；0.01~0.5 → PARTIAL_COMPRESSION；
           ≥0.5 → PRESERVED
  前提: D̂_world > 0.1（世界历史确实不同）；否则该对 N/A

审计边界：读取世界节点真值属 World 自身资格审计，非电路 benchmark
（HC-012 红线不适用，理由见 w0_structure_audit.py docstring）。

输出：data/w0e_history.json / data/w0e_traj_scale{1.0,0.1}.csv
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.components.skin_three_point import (
    TEST_KAPPA_THREE_POINT, TEST_R_LEAK_AMBIENT_THREE_POINT,
    build_three_point_skin)
from tss.generators.skin_transduction import (
    REFERENCE_TRANSDUCTION_CONFIG as CFG, transduce)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DT = 1.0
T_WINDOW = 2000


def scenario(name: str, scale: float):
    """返回 {node: [(t0,t1,I), ...]} 注入计划（三历史等能量 E=scale×300）。"""
    if name == "A":
        return {0: [(0, 300, scale)]}
    if name == "B":
        return {0: [(0, 100, scale)], 1: [(100, 200, scale)],
                2: [(200, 300, scale)]}
    if name == "C":
        return {0: [(0, 25, 6 * scale), (500, 525, 6 * scale)]}
    raise ValueError(name)


def run_history(name: str, scale: float):
    g = build_three_point_skin(kappa=TEST_KAPPA_THREE_POINT,
                               r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)
    plan = scenario(name, scale)
    world_traj, u_traj, ulin_traj = [], [], []
    injected = 0.0
    for t in range(T_WINDOW):
        ext = {}
        for nid, spans in plan.items():
            for (t0, t1, cur) in spans:
                if t0 <= t < t1:
                    ext[nid] = ext.get(nid, 0.0) + cur
        injected += sum(ext.values()) * DT
        g.step(DT, ext)
        temps = [g.cells[i].temperature for i in range(3)]
        world_traj.append(temps)
        u_traj.append([transduce(T, CFG) for T in temps])
        ulin_traj.append([CFG.kappa_i * (T - CFG.q_i0) + CFG.b_i
                          for T in temps])
    return {"world": world_traj, "u": u_traj, "ulin": ulin_traj,
            "injected": injected,
            "t_range": (min(min(r) for r in world_traj),
                        max(max(r) for r in world_traj))}


def rms(traj) -> float:
    return math.sqrt(sum(v * v for row in traj for v in row)
                     / (len(traj) * len(traj[0])))


def dist(x, y) -> float:
    return math.sqrt(sum((a - b) ** 2 for rx, ry in zip(x, y)
                         for a, b in zip(rx, ry)) / (len(x) * len(x[0])))


def dhat(x, y) -> float:
    denom = max(rms(x), rms(y), 1e-30)
    return dist(x, y) / denom


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 68)
    print("Phase W0-E 可区分世界历史（三历史等能量 × 两幅度组）")
    print("=" * 68)
    out = {"contract": {"collapse": "<0.01", "partial": "[0.01,0.5)",
                        "preserved": ">=0.5", "precondition_dworld": ">0.1"}}
    for scale in (1.0, 0.1):
        runs = {n: run_history(n, scale) for n in ("A", "B", "C")}
        e = {n: r["injected"] for n, r in runs.items()}
        print(f"\n[scale={scale}] 注入能量 A/B/C = "
              f"{e['A']:.1f}/{e['B']:.1f}/{e['C']:.1f}（等能量 ✓）  "
              f"温度范围 A={runs['A']['t_range'][0]:.2f}~"
              f"{runs['A']['t_range'][1]:.2f}"
              f"（标定域 [43.65,61.83]）")
        grp = {}
        for pair in (("A", "B"), ("A", "C"), ("B", "C")):
            x, y = pair
            dw = dhat(runs[x]["world"], runs[y]["world"])
            du = dhat(runs[x]["u"], runs[y]["u"])
            dl = dhat(runs[x]["ulin"], runs[y]["ulin"])
            ratio = du / max(dw, 1e-30)
            ratio_lin = dl / max(dw, 1e-30)
            if dw <= 0.1:
                verdict = "N/A(world 本身不可区分)"
            elif ratio < 0.01:
                verdict = "WORLD_TO_SUPPORT_COLLAPSE"
            elif ratio < 0.5:
                verdict = "PARTIAL_COMPRESSION"
            else:
                verdict = "PRESERVED"
            grp["-".join(pair)] = {
                "D_world_hat": dw, "D_support_hat": du,
                "D_support_linear_hat": dl, "collapse_ratio": ratio,
                "collapse_ratio_linear": ratio_lin, "verdict": verdict}
            print(f"  {x}-{y}: D̂_world={dw:.4f}  D̂_supp(clip)={du:.4f}  "
                  f"D̂_supp(lin)={dl:.4f}  ratio={ratio:.4f} "
                  f"(lin {ratio_lin:.4f})  ⇒ {verdict}")
        out[f"scale_{scale}"] = {"injected": e,
                                 "temp_range_A": runs["A"]["t_range"],
                                 "pairs": grp}
        # 轨迹落盘（world 温度 + u）
        with open(os.path.join(DATA_DIR, f"w0e_traj_scale{scale}.csv"),
                  "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["t"] + [f"{n}_T{i}" for n in "ABC" for i in range(3)]
                       + [f"{n}_u{i}" for n in "ABC" for i in range(3)])
            for t in range(T_WINDOW):
                w.writerow([t]
                           + [runs[n]["world"][t][i] for n in "ABC"
                              for i in range(3)]
                           + [runs[n]["u"][t][i] for n in "ABC"
                              for i in range(3)])
    path = os.path.join(DATA_DIR, "w0e_history.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n落盘: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
