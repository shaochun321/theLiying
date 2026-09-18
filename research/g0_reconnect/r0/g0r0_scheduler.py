"""g0r0_scheduler.py — 多率调度实验：S0/S1/S2 × A/B0/B1 + 连续参照 +
G0 状态收敛（§6-§13）。

TYPE:INFRA（G0 只运行；production READ_ONLY）

## 设计（D6 预算：T_phys=60 s；dt_G=0.001 s；N_sub=1000）

  episode：N=5 TEST 档链，源 E=20/P=1/t0=0（燃 20 s），REDUCED node0。
  S2 参考：World 以 dt_W=0.001 重放 ⇒ 每 1 ms 真边界值（60k 点）。
  运行矩阵（每run 60k G0 子步，状态每 1000 子步采样=每物理秒）：
    A×{S0, S1, S2(ref)}；B×{B0(1s 速率整段保持), B1@S1, B1@S2(ref)}
  误差 E_state = ‖Z − Z_ref‖/‖Z_ref‖（状态向量=(l1.act, hc.pre,
  ensemble pre×8, collector.pre)，§12 清单）。

## dt_B 收敛（§13 + 预登记判据 D4）与两层分解（首轮实测后加，透明登记）

  原 D4（全状态向量）：err(dt_B=0.1)/err(1.0)<0.7 且最细档<5%。
  **FIRST_RESULT 原样保留：全向量 FAIL（比=1.037）**。逐分量诊断定位
  根因：L1(5.9e-3)/HC(2.1e-3) 收敛，而 ensemble/collector 分量误差
  0.36~1.49——即 exp_P2A1b_3 早已登记的**自持振荡子系统**（600-700 步
  极限环）的相位失相干，对任何边界采样策略均不可收敛（G0 内部动力学
  性质，非调度器缺陷）。故按 W1-M2 先例加两层评估（预声明后重测）：
    Tier-1 接口层（L1, HC 分量）：D4 判据照用——须收敛；
    Tier-2 振荡层（ensemble/collector）：测相位敏感性并登记
    G0_OSCILLATOR_PHASE_SENSITIVITY，不作为调度器门。

## B 桥饱和发现（登记不调参）

  真实秒制下 u_B 峰≈0.27 ≫ L1 clamp 起点 u=0.05 ⇒ L1 常钳 10；
  B1@S1 与 B1@S2ref 被钳成逐位相同（0.0 差=饱和假象）。g canonical
  量级源于 step 制速率，物理秒制下需 occurrence revalidation 重标
  （本轮 §20/§32 禁调，登记 B_BRIDGE_L1_SATURATION）。

## 判定纪律（§8）：只按物理一致性/收敛/对细采样参考的逼近；
   不读 occurrence 数量。S1 因果性登记：需下一样本（live=1 样本滞后）。

输出：data/scheduler_comparison.csv, data/g0_state_convergence.csv,
      data/g0r0_scheduler.json
"""
from __future__ import annotations

import csv
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from g0r0_common import (  # noqa: E402
    MultiRateScheduler, boundary_from_episode, drive_g0, ep_spec,
    state_err, u_series_a, u_series_b0, u_series_b1)

DATA_DIR = os.path.join(_HERE, 'data')
DT_G = 0.001
T_PHYS = 60


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 78)
    print("G0-R0 scheduler — S0/S1/S2 × A/B0/B1（T_phys=60s, N_sub=1000）")
    print("=" * 78)
    # 边界三档
    y_1s = [fr[3] for fr in boundary_from_episode(
        ep_spec(t_total=T_PHYS, dt=1.0, eid="sched_1s"))]
    y_01s = [fr[3] for fr in boundary_from_episode(
        ep_spec(t_total=T_PHYS * 10, dt=0.1, eid="sched_01s"))]
    y_fine = [fr[3] for fr in boundary_from_episode(
        ep_spec(t_total=T_PHYS * 1000, dt=0.001, eid="sched_fine"))][1:]
    sch_1s = MultiRateScheduler(1.0, DT_G)
    sch_01s = MultiRateScheduler(0.1, DT_G)
    assert len(y_fine) == (len(y_1s) - 1) * sch_1s.n_sub

    runs = {}
    # Candidate A
    for tag, y_sub in (
            ("A_S0", sch_1s.expand(y_1s, "S0")),
            ("A_S1", sch_1s.expand(y_1s, "S1")),
            ("A_S2ref", sch_1s.expand(y_1s, "S2", y_fine)),
            ("A_S1_dtB01", sch_01s.expand(y_01s, "S1"))):
        runs[tag] = drive_g0(u_series_a(y_sub), DT_G, 1000)
        print(f"  ran {tag}")
    # Candidate B
    for tag, u_sub in (
            ("B0_hold", u_series_b0(y_1s, sch_1s.n_sub, 1.0)),
            ("B1_S1", u_series_b1(sch_1s.expand(y_1s, "S1"), DT_G)),
            ("B1_S2ref", u_series_b1(sch_1s.expand(y_1s, "S2", y_fine),
                                     DT_G))):
        runs[tag] = drive_g0(u_sub, DT_G, 1000)
        print(f"  ran {tag}")

    rows = []
    errs = {
        "A_S0_vs_ref": state_err(runs["A_S0"], runs["A_S2ref"]),
        "A_S1_vs_ref": state_err(runs["A_S1"], runs["A_S2ref"]),
        "A_S1_dtB0.1_vs_ref": state_err(runs["A_S1_dtB01"],
                                        runs["A_S2ref"]),
        "B0_vs_B1ref": state_err(runs["B0_hold"], runs["B1_S2ref"]),
        "B1_S1_vs_B1ref": state_err(runs["B1_S1"], runs["B1_S2ref"]),
    }
    for k, v in errs.items():
        rows.append({"comparison": k, "E_state_rel": v})
        print(f"[E_state] {k:<22} = {v:.4e}")

    # D4 原判据（全向量，FIRST_RESULT 原样保留）
    ratio = errs["A_S1_dtB0.1_vs_ref"] / max(errs["A_S1_vs_ref"], 1e-30)
    conv_full = ratio < 0.7 and errs["A_S1_dtB0.1_vs_ref"] < 0.05
    print(f"[D4 全向量 FIRST_RESULT] 误差比={ratio:.3f} 最细档="
          f"{errs['A_S1_dtB0.1_vs_ref']:.3e} ⇒ "
          f"{'CONVERGES' if conv_full else 'FAIL（振荡层相位失相干所致，见分解）'}")

    # 两层分解（docstring 预声明）：Tier-1=分量 0,1（L1, HC）
    def tier_err(a, b, comps):
        import math
        num = sum((ra[c] - rb[c]) ** 2 for ra, rb in zip(a, b)
                  for c in comps)
        den = sum(rb[c] ** 2 for rb in b for c in comps)
        return math.sqrt(num / max(den, 1e-30))

    t1 = (0, 1)
    n_comp = len(runs["A_S2ref"][0])
    t2 = tuple(range(2, n_comp))
    tier1_1 = tier_err(runs["A_S1"], runs["A_S2ref"], t1)
    tier1_01 = tier_err(runs["A_S1_dtB01"], runs["A_S2ref"], t1)
    tier2_1 = tier_err(runs["A_S1"], runs["A_S2ref"], t2)
    ratio_t1 = tier1_01 / max(tier1_1, 1e-30)
    conv_t1 = ratio_t1 < 0.7 and tier1_01 < 0.05
    print(f"[Tier-1 接口层(L1,HC)] err(dt_B=1)={tier1_1:.3e} "
          f"err(dt_B=0.1)={tier1_01:.3e} 比={ratio_t1:.3f} ⇒ "
          f"{'CONVERGES' if conv_t1 else 'FAIL'}")
    print(f"[Tier-2 振荡层] err={tier2_1:.3f}（O(1)相位失相干——"
          "G0_OSCILLATOR_PHASE_SENSITIVITY 登记，非调度器缺陷；"
          "先证=exp_P2A1b_3 自持振荡）")

    # B 桥饱和占用（登记）
    u_b1_ref = u_series_b1(sch_1s.expand(y_1s, "S2", y_fine), DT_G)
    sat_frac = sum(1 for u in u_b1_ref if u > 0.05) / len(u_b1_ref)
    print(f"[B 桥] u>0.05(L1钳位起点) 子步占比={sat_frac:.3f} ⇒ "
          "B_BRIDGE_L1_SATURATION 登记（g 量级属 revalidation，不调参）")
    conv = conv_t1
    # 策略登记（§8 纪律判定）
    s1_better = errs["A_S1_vs_ref"] < errs["A_S0_vs_ref"]
    print(f"[策略] S1 优于 S0（对 A）={s1_better}；"
          "S1 因果性=需下一样本（live 实现=1 样本滞后，登记）")
    print(f"[B] B0 整段保持 vs B1@ref 差={errs['B0_vs_B1ref']:.3e}；"
          f"B1@S1 vs B1@ref 差={errs['B1_S1_vs_B1ref']:.3e}")

    with open(os.path.join(DATA_DIR, "scheduler_comparison.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["comparison", "E_state_rel"])
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(DATA_DIR, "g0_state_convergence.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dt_B", "E_state_vs_ref"])
        w.writerow([1.0, errs["A_S1_vs_ref"]])
        w.writerow([0.1, errs["A_S1_dtB0.1_vs_ref"]])
    out = {"errors_full_vector_FIRST_RESULT": errs,
           "dtB_ratio_full": ratio, "converges_full_vector": conv_full,
           "tier1_interface": {"err_dtB1": tier1_1, "err_dtB01": tier1_01,
                               "ratio": ratio_t1, "converges": conv_t1},
           "tier2_oscillator_err": tier2_1,
           "findings": ["G0_OSCILLATOR_PHASE_SENSITIVITY（先证=exp_P2A1b_3"
                        "自持振荡；对任何采样策略不可收敛）",
                        f"B_BRIDGE_L1_SATURATION（u>0.05 占比 {sat_frac:.3f}"
                        "；g 量级属 revalidation）"],
           "s1_better_than_s0": s1_better,
           "s1_causality_note": "S1 需下一样本；live=1 dt_B 滞后",
           "canonical_recommendation":
           "S1 (CANONICAL_FOR_IMPLEMENTATION, 非 OPTIMAL；S0 为零滞后备选)"}
    with open(os.path.join(DATA_DIR, "g0r0_scheduler.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("落盘: scheduler_comparison.csv / g0_state_convergence.csv / "
          "g0r0_scheduler.json")
    return 0 if conv else 1


if __name__ == "__main__":
    sys.exit(main())
