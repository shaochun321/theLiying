"""naturalization_candidates.py — D2-0 Step2：N0-N3 自然化候选实现与
§19 七问独立资格（cal+attack 缓存专用；hold 轨迹不读，反馈 §21）。

TYPE:INFRA（research/ 层）。

## COMPUTE_BUDGET

  physical_trajectories = 0（只读 IMMUTABLE_CACHE）
  replays = 14 轨迹 × 只读扫描；n_parameter_points = 0；interventions = 0

## 候选定义（方案 §6-§7，反馈 §九冻结四候选、不新增）

  N0 count    ：n_i = 1（存在基准；预期 INSUFFICIENT——不预设失败，
                但不能事先赋予关系能力）
  N1 phase    ：ϑ_i(t) = (t−t↑)/(t_rearm−t↑) ∈[0,1]；同时保留
                τ_i^phys = t_rearm−t↑。**REPLAY_REFERENCE_ONLY**
                （分母含 t_rearm=完成后才可知，E-4/反馈 §五；
                CAUSAL_VARIANT_REQUIRED_BEFORE_LIVE_D2 已登记）
  N2 rel-time ：Δτ̂_ij = (t_j↑−t_i↑)/(f(τ_i,τ_j)+ε)，f=mean(τ_i,τ_j)
                ——分母只用实际 occurrence 时长（可追踪尺度，方案 §6-N2
                禁 arbitrary global constant）。**REPLAY_REFERENCE_ONLY**。
                同时保留原始 Δτ_ij。带符号——进入关系结构时按项目
                ± 半波双通道先例（thermal_quantum_l1_warm/cool）整流
                分裂，Step3 接口登记。
  N3 activity ：A_i = ∫_{W_i} a_i(t)dt，a_i=raw track 的 col_{site}，
                W_i=[t_up,t_rearm)；ρ_i = A_i/(ΣA_k+ε)。保留原始 A_i
                与 energy ledger（E-1 数据合同兑现点）。

## §19 七问（每候选独立回答，无 winner——反馈 §十）

  Q1 物理来源：全部字段仅派生自 OccurrencePortV2 + RawOccurrenceTrack
     （审计=来源字段清单）
  Q2 单位/量程主导：无量纲或以可追踪尺度归一（实测值域并报）
  Q3 进入同一关系结构：有界标量可作换能输入（带符号者半波分裂）
  Q4 时序保留：C3 s/m/l 的 Δτ̂ 严格有序（实测）
  Q5 dose 保留：cal 集内 dose 轴=触发/不触发二分（u=0.02 亚阈值无
     occurrence——诚实登记：触发内 dose 敏感性只能在 hold 盲评观察，
     不得用于调参）
  Q6 虚假 saturation：collector Zener 顶棚下 A_i 是否仍有区分度（实测
     跨 occurrence 变异）
  Q7 dt 稳健：全部量以 t_phys/积分定义；数值检查=对缓存 2× 抽稀重算
     A_i，相对差 <1%

复现入口：
  PYTHONIOENCODING=utf-8 python research/d2_relation_v0/naturalization_candidates.py
"""
from __future__ import annotations

import csv
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..')))

from d2_common import DATA, DT_G, read_track  # noqa: E402

EPS = 1e-12


def load_ports():
    ports = []
    with open(os.path.join(DATA, 'occurrence_parent_manifest.csv'),
              newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r["traj"].startswith("hold_"):
                continue  # hold 不触（反馈 §21）
            ports.append({"traj": r["traj"], "parent": r["parent"],
                          "occurrence_id": r["occurrence_id"],
                          "t_up": int(r["t_up"]), "t_down": int(r["t_down"]),
                          "t_rearm": int(r["t_rearm"])})
    return ports


def natural_values(ports):
    """逐 occurrence 计算 τ_phys 与 A_i（读缓存轨迹）；逐轨迹计算 Δτ̂。"""
    rows, pair_rows = [], []
    by_traj = {}
    for p in ports:
        by_traj.setdefault(p["traj"], []).append(p)
    for tid, plist in sorted(by_traj.items()):
        track = read_track(tid)
        a_sum = 0.0
        vals = []
        for p in plist:
            tau_phys = (p["t_rearm"] - p["t_up"]) * DT_G
            col_key = f"col_{p['parent']}"
            a_i = sum(track[k][col_key]
                      for k in range(p["t_up"], p["t_rearm"])) * DT_G
            # Q7 数值检查：2× 抽稀重算
            a_i_coarse = sum(track[k][col_key]
                             for k in range(p["t_up"], p["t_rearm"], 2)) \
                * (2 * DT_G)
            vals.append((p, tau_phys, a_i, a_i_coarse))
            a_sum += a_i
        for p, tau_phys, a_i, a_c in vals:
            rows.append({
                "traj": tid, "parent": p["parent"],
                "occurrence_id": p["occurrence_id"],
                "n0_count": 1,
                "n1_tau_phys_s": tau_phys,
                "n3_A_i": a_i,
                "n3_rho_i": a_i / (a_sum + EPS),
                "q7_A_coarse_reldiff": abs(a_i - a_c) / (abs(a_i) + EPS),
            })
        if len(vals) == 2:
            (pi, ti, _, _), (pj, tj, _, _) = sorted(
                vals, key=lambda v: v[0]["parent"])[:2]
            dt_raw = (pj["t_up"] - pi["t_up"]) * DT_G
            pair_rows.append({
                "traj": tid, "pair": f"{pi['parent']}->{pj['parent']}",
                "delta_tau_raw_s": dt_raw,
                "n2_delta_tau_hat": dt_raw / ((ti + tj) / 2.0 + EPS),
                "tau_i_s": ti, "tau_j_s": tj,
            })
    return rows, pair_rows


def main() -> int:
    ports = load_ports()
    rows, pairs = natural_values(ports)
    with open(os.path.join(DATA, 'naturalized_values.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    with open(os.path.join(DATA, 'naturalized_pairs.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(pairs[0]))
        w.writeheader(); w.writerows(pairs)

    # ── §19 七问实测 ──
    by = {r["traj"]: r for r in pairs}
    # Q4 时序保留：C3 s/m/l 与 C4 s/m/l 的 Δτ̂ 严格有序且符号相反
    c3 = [by[f"cal_C3_{k}"]["n2_delta_tau_hat"] for k in ("s", "m", "l")]
    c4 = [by[f"cal_C4_{k}"]["n2_delta_tau_hat"] for k in ("s", "m", "l")]
    q4_n2 = (c3[0] < c3[1] < c3[2]) and (c4[0] > c4[1] > c4[2]) and \
        all(v > 0 for v in c3) and all(v < 0 for v in c4)
    # N1/τ 的时序保留：τ_phys 与 ϑ 定义式本身保留窗口（值域检查）
    taus = [r["n1_tau_phys_s"] for r in rows]
    q2_n1 = all(0.0 < t < 8.0 for t in taus)
    # Q6 N3 区分度：跨 occurrence A_i 相对变异（顶棚下是否仍可区分）
    a_vals = [r["n3_A_i"] for r in rows]
    a_spread = (max(a_vals) - min(a_vals)) / (max(a_vals) + EPS)
    q6_n3 = a_spread > 0.01
    # Q7 dt 稳健：A_i 抽稀重算相对差
    q7_max = max(r["q7_A_coarse_reldiff"] for r in rows)
    q7_n3 = q7_max < 0.01
    # N0：所有 occurrence 的 n0 恒 1 ⇒ 无时序/无 dose/无区分（定义性）
    verdicts = {
        "N0_count": {"verdict": "INSUFFICIENT",
                     "reason": "恒 1，无时序/剂量/历史区分能力（存在基准，"
                               "预期兑现，反馈 §九）"},
        "N1_phase": {"verdict": "QUALIFIED_REFERENCE",
                     "tag": "REPLAY_REFERENCE_ONLY",
                     "q2_range_ok": q2_n1,
                     "note": "ϑ∈[0,1]+τ_phys 保留；live 因果变体已登记"
                             "CAUSAL_VARIANT_REQUIRED_BEFORE_LIVE_D2"},
        "N2_relative_timing": {"verdict": "QUALIFIED_REFERENCE" if q4_n2
                               else "INSUFFICIENT",
                               "tag": "REPLAY_REFERENCE_ONLY",
                               "q4_ordering": {"C3": c3, "C4": c4,
                                               "strict": q4_n2},
                               "note": "带符号→Step3 半波双通道整流分裂"
                                       "（warm/cool 先例）"},
        "N3_activity": {"verdict": "QUALIFIED" if (q6_n3 and q7_n3)
                        else "INSUFFICIENT",
                        "q6_spread": a_spread, "q7_max_reldiff": q7_max,
                        "note": "E-1 raw track 合同兑现；ρ_i 同时保留 A_i"},
        "Q5_dose_note": "cal 集 dose 轴=触发/不触发二分（u=0.02 亚阈值零 "
                        "occurrence 实测）；触发内 dose 敏感性留 hold 盲评"
                        "观察，不用于调参",
    }
    with open(os.path.join(DATA, 'naturalization_comparison.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["candidate", "verdict", "detail"])
        for k, v in verdicts.items():
            if isinstance(v, dict):
                w.writerow([k, v.get("verdict", ""), json.dumps(
                    {kk: vv for kk, vv in v.items() if kk != "verdict"},
                    ensure_ascii=False)])
    with open(os.path.join(DATA, 'd2_naturalization.json'), 'w',
              encoding='utf-8') as f:
        json.dump(verdicts, f, indent=1, ensure_ascii=False)

    print("N2 Δτ̂ C3(s,m,l) =", [f"{v:.4f}" for v in c3])
    print("N2 Δτ̂ C4(s,m,l) =", [f"{v:.4f}" for v in c4])
    print(f"N3 A_i spread={a_spread:.4f}  q7_max_reldiff={q7_max:.2e}")
    for k, v in verdicts.items():
        if isinstance(v, dict) and "verdict" in v:
            print(f"  {k}: {v['verdict']}")
    ok = q4_n2 and q2_n1
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
