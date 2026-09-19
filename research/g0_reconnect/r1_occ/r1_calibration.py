"""r1_calibration.py — G0-R1 R1-2：B 桥增益 g 的真实秒制重标（cal 集）。

TYPE:INFRA（research/ 层；production READ_ONLY——本脚本只测量与标定，
不写任何 production 参数）。

依据：外部《G0-R1/OCC 方案》§3-R1-2/§8（评判 ADOPT，R-1~R-4 已裁定）。
G0-R0 登记信号：B_BRIDGE_L1_SATURATION——旧 canonical g=0.275062（v1
尺度，g=S×τ_field）在真实秒制下使 33.3% 子步 u>0.05（L1 钳位起点），
B1@S1 与 B1@S2ref 被钳成逐位相同（饱和假象）。方案 §8：重标顺序
timebase fix → port fix → measure → calibrate，禁止为 occurrence 数量
好看调参，不寻找"最佳值"。

## 预注册判据（运行前冻结，§8/E-6 纪律）

物理量：u_clamp_onset = 0.05 —— L1（ThermalDeltaNeuron）钳位起点
  （_ACTIVATION_MAX=10 与 _WARM_ONSET_GAIN=200 之比，FIX-019 登记值，
  非本脚本新造）。

1. sat_frac(g)：cal 场景全体子步中 |u|>u_clamp_onset 的占比（u 对 g
   线性 ⇒ 解析可扫，无需逐 g 跑 G0）。
2. 合法域（legal region）：{g : sat_frac(g)=0 且 G0 探针运行链路存活}
   ——链路存活 = collector.pre_trace 峰值 > theta_up(0.01) 至少一次
   （occurrence 计数只登记不作合格判据——closure 阈值本身属 Step 3
   重资格化对象，不得在本脚本用 occ 数反推 g）。
3. 失败边界（failure boundary）：
   g_sat_onset：sat_frac 首次 >0 的最小 g（上边界）；
   g_dead：collector 峰值跌破 theta_up 的最大 g（下边界，G0 探针实测）。
4. canonical g_v2（推导规则先于测量声明，非搜索所得）：
   g_v2 = (u_clamp_onset / 2) / max|Ṫ|_cal
   物理意义：cal 场景最大温升率映射到 L1 线性区中点（2× 余量），
   与 T1-B S 标定"稳态端点"同风格的端点锚定；CANONICAL_REFERENCE
   ≠ OPTIMAL。
5. 每参数输出五元组：physical meaning / legal region / failure
   boundary / canonical reference / provenance（§8）。

## cal 场景（三类，不含 held-out——hold 集属 Step 3 数据集，本脚本不触）

  C1 normal    ：ep_spec 默认（单源 20T@node0, κ=0.05, r_leak=200, 60s）
  C2 dissip    ：强耗散 r_leak_ambient=20
  C3 multisrc  ：双源（node0 20T@t0 + node2 12T@t20）
  边界展开：LIVE_CAUSAL_POLICY=S0（R-3 裁定：live 禁未来样本）；
  桥式=**B0**（上一完成区间速率 (Y_n−Y_{n−1})/Δt_ext 整段保持，因果）。

## 负结果登记（首轮实测，2026-09-19）

  S0+B1（逐子步差分）配对是**结构性错误**：ZOH 使区间内 ΔY=0、全部
  变化集中在样本边界单个子步 ⇒ Ṫ 被放大 N_sub=1000×（实测
  max|Ṫ|=995.0 T/s 脉冲伪影），链路被单子步脉冲饿死（g_v1 探针
  col_max=0.0）。与 G0-R0 登记的结构预期一致（"S1 下 B1 区间内=B0，
  仅样本边界不同"——B1 只有在 S1/S2 平滑重建下才有意义）。裁定：
  live 因果桥 = S0+B0；B1 保留给 reference/replay（S1/S2）语境。
  详细登记 → NEGATIVE_RESULTS。

复现入口：
  PYTHONIOENCODING=utf-8 python research/g0_reconnect/r1_occ/r1_calibration.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', 'r0')))

from g0r0_common import (  # noqa: E402  (REUSE NOT REBUILD, §11)
    MultiRateScheduler, boundary_from_episode, ep_spec, fresh_g0)
from world_v2_core import SourceSpec  # noqa: E402
from tss.adapters.typed_ports import LIVE_CAUSAL_POLICY  # noqa: E402

DATA = os.path.join(_HERE, 'data')
os.makedirs(DATA, exist_ok=True)

U_CLAMP_ONSET = 0.05     # L1 钳位起点（FIX-019：10/200，非本脚本新造）
THETA_UP = 0.01          # 现行 closure 触发阈（EXP-T1 沿用；Step 3 重资格化）
G_CANON_V1 = 0.275062    # T1-B v1 canonical（33.3% 饱和的登记值）
DT_G = 0.001

_SCENARIOS = {
    "C1_normal": ep_spec(eid="r1cal_normal"),
    "C2_dissip": ep_spec(r_leak=20.0, eid="r1cal_dissip"),
    "C3_multisrc": ep_spec(
        sources=[SourceSpec(0, 20.0, 1.0, 0), SourceSpec(2, 12.0, 1.0, 20)],
        eid="r1cal_multisrc"),
}


def _rate_substeps(spec) -> list:
    """S0+B0 因果桥的（未乘 g 的）子步速率序列 Ṫ^(k) [T/s]。

    B0：区间 n 整段保持上一完成区间的速率 (Y_n−Y_{n−1})/Δt_ext（两个
    过去样本，因果；镜像 g0r0_common.u_series_b0，此处输出未乘 g 的
    裸速率以支持解析 g 扫描）。区间 0 无历史 ⇒ 0（T1-B C5 初始化合同）。
    """
    frames = boundary_from_episode(spec)
    y_samples = [f[3] for f in frames]
    n_sub = MultiRateScheduler(1.0, DT_G).n_sub
    assert LIVE_CAUSAL_POLICY == "S0"  # R-3 裁定语境；B0 本身不依赖展开
    out = []
    for n in range(len(y_samples) - 1):
        rate = (y_samples[n] - y_samples[n - 1]) / 1.0 if n > 0 else 0.0
        out.extend([rate] * n_sub)
    return out


def main() -> int:
    print("=" * 60)
    print("G0-R1 R1-2 — B bridge g recalibration (real-seconds, cal set)")
    print("=" * 60)

    # ── 阶段一：解析扫描（u = g·Ṫ 线性 ⇒ sat_frac 对 g 解析）──
    rates = {name: _rate_substeps(spec) for name, spec in _SCENARIOS.items()}
    max_rate = max(max(abs(r) for r in rs) for rs in rates.values())
    n_total = sum(len(rs) for rs in rates.values())

    # canonical 推导（预注册规则 4，先于任何 G0 运行）
    g_v2 = (U_CLAMP_ONSET / 2.0) / max_rate
    # 解析上边界：sat_frac(g)>0 ⟺ g·max|Ṫ| > u_clamp_onset
    g_sat_onset = U_CLAMP_ONSET / max_rate

    grid = [g_v2 * (10.0 ** (k / 4.0)) for k in range(-12, 9)] + \
        [G_CANON_V1, g_sat_onset, g_v2]
    rows = []
    for g in sorted(set(grid)):
        n_sat = sum(1 for rs in rates.values() for r in rs
                    if abs(g * r) > U_CLAMP_ONSET)
        rows.append({"g": g, "sat_frac": n_sat / n_total,
                     "max_u": g * max_rate})

    # ── 阶段二：G0 探针（少数 g 点实测链路存活；不以 occ 数选 g）──
    probe_gs = [g_v2 * 1e-3, g_v2 * 1e-2, g_v2 * 0.1, g_v2, g_sat_onset,
                G_CANON_V1]
    probes = []
    for g in probe_gs:
        h = fresh_g0()
        col_max, occ = 0.0, 0
        for k, r in enumerate(rates["C1_normal"]):
            ev = h.tick(g * r, DT_G, k)
            col_max = max(col_max, h.collector.pre_trace)
            if ev is not None:
                occ += 1
        alive = col_max > THETA_UP
        probes.append({"g": g, "collector_max": col_max,
                       "alive": alive, "occ_registered_only": occ})
        print(f"  probe g={g:.6e}: col_max={col_max:.4f} alive={alive} "
              f"occ={occ}(登记不判定)")

    # 下边界 g_dead：探针中 alive=False 的最大 g（若全 alive 则未观测到）
    dead = [p["g"] for p in probes if not p["alive"]]
    g_dead = max(dead) if dead else None
    legal_lo = min(p["g"] for p in probes if p["alive"]) if any(
        p["alive"] for p in probes) else None

    with open(os.path.join(DATA, 'port_calibration.csv'), 'w',
              newline='') as f:
        w = csv.DictWriter(f, fieldnames=["g", "sat_frac", "max_u"])
        w.writeheader()
        w.writerows(rows)

    summary = {
        "parameter": "g (B bridge, U_dotT gain)",
        "physical_meaning": "rate->L1-current gain; u=g*dY/dt_ext must stay "
                            "inside L1 linear regime (clamp onset u=0.05)",
        "legal_region": {"lo_observed_alive": legal_lo,
                         "hi_analytic": g_sat_onset,
                         "rule": "sat_frac==0 AND chain alive"},
        "failure_boundary": {"g_sat_onset": g_sat_onset, "g_dead": g_dead},
        "canonical_reference": {
            "g_v2": g_v2,
            "rule": "(u_clamp_onset/2)/max|dY/dt|_cal — pre-registered, "
                    "NOT searched; CANONICAL_REFERENCE != OPTIMAL"},
        "provenance": "G0R0 B_BRIDGE_L1_SATURATION(33.3%@g_v1) + FIX-019 "
                      "clamp constants + T1B endpoint-anchoring style; "
                      "scenarios C1/C2/C3 cal-only (held-out untouched)",
        "v1_reference": {"g_v1": G_CANON_V1,
                         "sat_frac_v1": next(r["sat_frac"] for r in rows
                                             if r["g"] == G_CANON_V1)},
        "max_rate_cal": max_rate,
        "scheduler": {"live": "S0", "note": "R-3 ruling 2026-09-19"},
        "probes": probes,
    }
    with open(os.path.join(DATA, 'r1_calibration.json'), 'w') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n  max|dY/dt|_cal = {max_rate:.6f} T/s over {n_total} substeps")
    print(f"  g_v2 (canonical) = {g_v2:.6e}   g_sat_onset = {g_sat_onset:.6e}")
    print(f"  g_v1 = {G_CANON_V1} sat_frac = "
          f"{summary['v1_reference']['sat_frac_v1']:.3f}")
    print(f"  legal region ≈ [{legal_lo}, {g_sat_onset:.6e}] (rule-based)")
    ok = (g_v2 < g_sat_onset and
          any(p["alive"] and p["g"] <= g_v2 for p in probes))
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
