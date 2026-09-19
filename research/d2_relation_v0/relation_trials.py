"""relation_trials.py — D2-0 Step4：C0-C5 输入矩阵 + 负对照 NC1-NC4。

TYPE:INFRA（research/ 层；全部 replay，读 IMMUTABLE_CACHE）。

## COMPUTE_BUDGET

  physical_trajectories=0; replays ≈ 12 cal + 2 attack + 4 对照变体 ≈ 18;
  n_parameter_points=1（canonical g_rel）; interventions=0（Step4b 另计）

## 预注册判据（运行前冻结）

结构预判 T1（可证伪预测，先于运行声明）：对称双通道求和细胞下，
  C3_m 与 C4_m 互为通道镜像 ⇒ i_total(t) 逐位相同 ⇒ x_ρ 轨迹**逐位
  相同**（RMSE < 1e-12）。若成立：v0 候选=重叠/|Δt| 检测器，**方向盲**
  ——如实登记（反馈 §N2 本就禁止宣称 order/direction，无 D2-M 门要求
  符号敏感；带符号方向性留待有物理依据的非对称结构，非本轮）。
  若不成立：说明存在未理解的通道不对称，必须停下查根因。

T2 |Δt| 轴：peak(C3_s) > peak(C3_m) > peak(C3_l) 严格有序（重叠越少
   峰越低——真实动力学对相对时距的响应）。
T3 共时 vs 时序：RMSE(x_C2, x_C3m) > 1e-6 且峰相对差 > 1%。
T4 overlap 居间：peak(C2) ≥ peak(C5_strong) ≥ peak(C5_weak) ≥ peak(C3_m)。
T5 R2 耗散：全部 cal 运行 x_end < 0.05×peak（输入停后回落静息）。
T6 R3 有限：全部 peak ≤ 10（母本钳位）；u_sat 括号已在标定实测。
T7 叠加性：peak(C2) > max(peak(C0), peak(C1))（双父 ≠ 单父）。

负对照（反馈 §十四，不得删减）：
NC1 纯共现 r(t)=ϑ_a·ϑ_b（瞬时,无状态）：C2/C5 上信号非零
    （RELATION_SIGNAL=YES）但按构造无历史（RELATION_PROCESS=NO 登记）。
NC2 无历史映射：机器证据=同一轨迹内取两个瞬时输入相同 (ϑ_a,ϑ_b)=(0,0)
    的时刻（驱动前 vs 两窗之间），无历史映射必然同值，而物理 x_ρ
    不同值（残余衰减>0）——**没有任何 (标签,瞬时输入)→输出 的无记忆
    函数能复现 x_ρ**（同时构成 D2-M6 label-promotion 的核心证据）。
NC3 自激：零驱动 8s x≡0 且无父支撑 ⇒ 物理确认增量=0（cell 为无源 RC，
    无自持振荡——如实登记）。
NC4 lineage block：C3_m 上分别阻断 A/B 通道（replay 驱动置零），
    x 轨迹须显著改变（RMSE>1e-3）；attack: atk_replaceB（A+C 通道）
    过程成立=泛化登记。

复现入口：
  PYTHONIOENCODING=utf-8 python research/d2_relation_v0/relation_trials.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..')))

from d2_common import DATA, DT_G  # noqa: E402
from relation_physical_impl import (  # noqa: E402
    build_relation, drives_for, load_port_windows, run_relation,
    step_relation)

EPS = 1e-12


def _rmse(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))


def _g_canon():
    with open(os.path.join(DATA, 'relation_calibration.json'),
              encoding='utf-8') as f:
        return json.load(f)["canonical_reference"]["g_rel"]


def main() -> int:
    g = _g_canon()
    windows = load_port_windows()
    runs, ledgers = {}, []
    cal_ids = ["cal_C0_A", "cal_C1_B", "cal_C2_sim", "cal_C3_s", "cal_C3_m",
               "cal_C3_l", "cal_C4_s", "cal_C4_m", "cal_C4_l",
               "cal_C5_weak", "cal_C5_strong"]
    for tid in cal_ids:
        xs, led, _ = run_relation(tid, g, windows=windows)
        runs[tid] = xs
        ledgers.append(led)
        print(f"  {tid}: peak={led['x_peak']:.4f} end={led['x_end']:.5f} "
              f"dE={led['energy_drop']:.4f}")
    pk = {t: max(x) for t, x in runs.items()}

    checks = {}
    # T1 镜像对称结构预判
    t1 = _rmse(runs["cal_C3_m"], runs["cal_C4_m"])
    checks["T1_mirror_rmse"] = t1
    checks["T1_pass_prediction"] = t1 < 1e-12
    # T2 |Δt| 轴严格有序
    checks["T2_dt_axis"] = [pk["cal_C3_s"], pk["cal_C3_m"], pk["cal_C3_l"]]
    checks["T2_pass"] = pk["cal_C3_s"] > pk["cal_C3_m"] > pk["cal_C3_l"]
    # T3 共时 vs 时序
    t3r = _rmse(runs["cal_C2_sim"], runs["cal_C3_m"])
    checks["T3_rmse"] = t3r
    checks["T3_pass"] = t3r > 1e-6 and abs(
        pk["cal_C2_sim"] - pk["cal_C3_m"]) / pk["cal_C2_sim"] > 0.01
    # T4 overlap 居间
    checks["T4_order"] = [pk["cal_C2_sim"], pk["cal_C5_strong"],
                          pk["cal_C5_weak"], pk["cal_C3_m"]]
    checks["T4_pass"] = (pk["cal_C2_sim"] >= pk["cal_C5_strong"]
                         >= pk["cal_C5_weak"] >= pk["cal_C3_m"])
    # T5 耗散 / T6 有限
    checks["T5_pass"] = all(l["x_end"] < 0.05 * l["x_peak"]
                            for l in ledgers if l["x_peak"] > 0)
    checks["T6_pass"] = all(l["x_peak"] <= 10.0 + EPS for l in ledgers)
    # T7 叠加
    checks["T7_pass"] = pk["cal_C2_sim"] > max(pk["cal_C0_A"],
                                               pk["cal_C1_B"])

    # NC1 纯共现（瞬时积）
    da2, db2 = drives_for("cal_C2_sim", windows)
    nc1_c2 = max(a.value * b.value for a, b in zip(da2, db2))
    da3, db3 = drives_for("cal_C3_l", windows)
    nc1_c3l = max(a.value * b.value for a, b in zip(da3, db3))
    checks["NC1"] = {"signal_C2": nc1_c2, "signal_C3l": nc1_c3l,
                     "RELATION_SIGNAL": nc1_c2 > 0,
                     "RELATION_PROCESS": "NO (stateless by construction)"}
    # NC2 无历史映射反例对：C3_l 内 (ϑa,ϑb)=(0,0) 的两时刻
    xs3l = runs["cal_C3_l"]
    zero_ts = [k for k, (a, b) in enumerate(zip(da3, db3))
               if a.value == 0.0 and b.value == 0.0]
    t_pre = next(k for k in zero_ts if k < 900)
    # A 窗结束后、B 窗开始前的间隙时刻（残余衰减非零）
    gap_ts = [k for k in zero_ts if 2300 < k < 3000]
    t_gap = gap_ts[len(gap_ts) // 4] if gap_ts else None
    nc2 = {"t_pre": t_pre, "x_pre": xs3l[t_pre],
           "t_gap": t_gap, "x_gap": xs3l[t_gap] if t_gap else None}
    nc2["pass"] = (t_gap is not None and xs3l[t_pre] == 0.0
                   and xs3l[t_gap] > 1e-4)
    checks["NC2_memoryless_counterexample"] = nc2
    # NC3 自激：零驱动
    p0 = build_relation(g)
    x0max = 0.0
    for _ in range(8000):
        x0max = max(x0max, abs(step_relation(p0, 0.0, 0.0)))
    checks["NC3"] = {"x_max_zero_input": x0max, "pass": x0max == 0.0,
                     "note": "无源 RC，无自持振荡；无父支撑⇒ΔC_phys=0"}
    # NC4 lineage block（C3_m 阻断 A / 阻断 B）
    base = runs["cal_C3_m"]
    da, db = drives_for("cal_C3_m", windows)
    for tag, (za, zb) in {"blockA": (True, False),
                          "blockB": (False, True)}.items():
        p = build_relation(g)
        xs = [step_relation(p, 0.0 if za else sa.value,
                            0.0 if zb else sb.value)
              for sa, sb in zip(da, db)]
        checks[f"NC4_{tag}_rmse"] = _rmse(base, xs)
    checks["NC4_pass"] = (checks["NC4_blockA_rmse"] > 1e-3
                          and checks["NC4_blockB_rmse"] > 1e-3)
    # attack：site 替换泛化（A+C 通道）
    xs_atk, led_atk, _ = run_relation("atk_replaceB", g, windows=windows,
                                      ch_a="A", ch_b="C")
    checks["attack_replaceB_peak"] = led_atk["x_peak"]
    checks["attack_pass"] = 0.0 < led_atk["x_peak"] <= 10.0

    # 输出
    with open(os.path.join(DATA, 'relation_trials.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ledgers[0]))
        w.writeheader(); w.writerows(ledgers)
    with open(os.path.join(DATA, 'relation_energy_ledger.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ledgers[0]))
        w.writeheader(); w.writerows(ledgers)
    with open(os.path.join(DATA, 'd2_trials.json'), 'w',
              encoding='utf-8') as f:
        json.dump(checks, f, indent=1, ensure_ascii=False, default=str)

    gate_keys = ["T2_pass", "T3_pass", "T4_pass", "T5_pass", "T6_pass",
                 "T7_pass", "NC4_pass", "attack_pass"]
    ok = all(checks[k] for k in gate_keys) and checks["NC2_memoryless_counterexample"]["pass"] \
        and checks["NC3"]["pass"]
    print("\n  T1 mirror rmse:", f"{t1:.3e}",
          "(方向盲预判", "成立" if checks["T1_pass_prediction"] else "不成立",
          ")")
    for k in gate_keys:
        print(f"  {k}: {checks[k]}")
    print(f"  NC2: {nc2['pass']}  NC3: {checks['NC3']['pass']}")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
