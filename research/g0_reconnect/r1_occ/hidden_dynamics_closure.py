"""hidden_dynamics_closure.py — G0-R1 Step4：Hidden Dynamics Closure 第一例
（振荡相位，§13-§15 + §14 停止规则）。

TYPE:INFRA（research/ 层）。

⚠ DIAGNOSTIC_INTERVENTION 登记（E-9 边界，评判裁定 2026-09-19）：
本脚本的"状态移植"（Z_B←Z_A，经 neuron.__dict__ 拷贝）是**直接写内部
状态**的诊断性干预——先例：P2-B1R 直接设 collector.pre_trace。只允许
在研究区因果定位实验中使用，**禁止任何形式流入 production 机制**；
production 的行为路径必须全部经 SynapticBundle.propagate() 产生。

## 实验设计（利用 G0_OSCILLATOR_PHASE_SENSITIVITY，G0-R0 登记）

构造 twin：A/B 两个 fresh G0，等量预驱动脉冲（u=0.03<钳位起点, 900 子步）
但起始时刻错开 Δ=300 子步（≈先证振荡周期 600-700 步之半）⇒ 撤驱动后
自持振荡相位失相干。在静息窗 [4000,6000] 内取
t0 = argmin |collector_A − collector_B|（可见面近似相等，内部相位不同）。

## 预注册（运行前冻结）

可见面 Y_visible(t0)：(l1.activation, collector.pre_trace)——G0 对外
  暴露的口（sense() 即 collector.pre_trace）；内部 ensemble/hc 状态不属
  可见面。
未来协议：t0 后 1000 子步施加相同探测脉冲（u=0.03, 500 子步），观测窗
  到 t0+6000。
未来指标：next_occ_latency（探测脉冲起点→下一次 t_up 的子步数）/
  future_occ_count / collector 轨迹 RMSE（对 A 未来轨迹）。
分叉判据：baseline B vs A 的 latency 差 ≥ 1 子步 或 RMSE > 1e-6
  ⇒ 未来不同（相位是候选隐藏态）；否则 OSCILLATOR_PHASE=MICROSTATE_ONLY
  ⇒ 登记并停（§15，两种结局都合法）。
干预臂（若未来不同）：
  sham   ：只移植 L1 状态（负对照——预期不消除分叉）
  Z_low  ：只移植 hc+ensemble+collector 的 pre_trace（10 维低维表示）
  Z_full ：移植 hc+ensemble+collector 完整状态（__dict__ 深拷贝）
等化判据：干预后 B′ 与 A 未来 latency 差=0 且 RMSE<1e-9（确定性系统）。
裁定规则（§14）：Z_full 等化 ⇒ HIDDEN_STATE_CAUSALLY_SUPPORTED；
  最小充分态 = Z_low 若其亦等化，否则 Z_full；登记
  CURRENT_MINIMAL_SUFFICIENT_STATE_CANDIDATE + STOP_DEEPER_DECOMPOSITION
  （禁止继续拆 Z→Z1→Z2；禁止把全部 neuron state 提升为生成元状态——
  这里的裁定只授予"当前分辨率下的最小充分**候选**"）。

复现入口：
  PYTHONIOENCODING=utf-8 python research/g0_reconnect/r1_occ/hidden_dynamics_closure.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from copy import deepcopy

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', 'r0')))

from g0r0_common import fresh_g0  # noqa: E402

DATA = os.path.join(_HERE, 'data')
DT_G = 0.001
U_DRIVE = 0.03          # < 钳位起点 0.05，R1-2 合法域内
PRE_LEN = 900
DELTA = 300             # 相位错开（≈600-700 步周期之半）
T0_WIN = (4000, 6000)
FUT_PULSE_AT = 1000     # t0 后到探测脉冲的间隔
FUT_PULSE_LEN = 500
FUT_WIN = 6000


def _drive(h, t_from, t_to, pulses, rec=None):
    """tick h 从 t_from 到 t_to（不含），pulses=[(a,b)] 区间内 u=U_DRIVE。"""
    for k in range(t_from, t_to):
        u = U_DRIVE if any(a <= k < b for a, b in pulses) else 0.0
        h.tick(u, DT_G, k)
        if rec is not None:
            rec.append(h.collector.pre_trace)


def _osc_neurons(h):
    return [h.hc, *h.ensemble, h.collector]


def _future(h, t0, occ_before):
    """相同未来协议：脉冲 + 观测窗；返回 (latency, occ_count, col_traj)。"""
    traj = []
    pulse = (t0 + FUT_PULSE_AT, t0 + FUT_PULSE_AT + FUT_PULSE_LEN)
    _drive(h, t0, t0 + FUT_WIN, [pulse], rec=traj)
    fut_evs = h.closure.events[occ_before:]
    lat = None
    for ev in fut_evs:
        if ev.t_up >= pulse[0]:
            lat = ev.t_up - pulse[0]
            break
    return lat, len(fut_evs), traj


def _rmse(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / max(len(a), 1))


def _build_pair():
    """构造 A/B twin 到 t0，返回 (hA, hB, t0, 可见面记录)。"""
    hA, hB = fresh_g0(), fresh_g0()
    colA, colB = [], []
    _drive(hA, 0, T0_WIN[1], [(0, PRE_LEN)], rec=colA)
    _drive(hB, 0, T0_WIN[1], [(DELTA, DELTA + PRE_LEN)], rec=colB)
    # 注意：上面把两臂都推进到 T0_WIN[1]，t0 取该点（窗内 argmin 需要重建
    # ——确定性系统允许直接重建到任意 t0）。先在录制轨迹上选 t0：
    t0 = min(range(*T0_WIN), key=lambda k: abs(colA[k] - colB[k]))
    # 重建两臂到精确 t0（fresh + 相同驱动序列，确定性 ⇒ 逐位同态）
    hA, hB = fresh_g0(), fresh_g0()
    _drive(hA, 0, t0, [(0, PRE_LEN)])
    _drive(hB, 0, t0, [(DELTA, DELTA + PRE_LEN)])
    vis = {
        "t0": t0,
        "visible_l1_A": hA.l1.activation, "visible_l1_B": hB.l1.activation,
        "visible_col_A": hA.collector.pre_trace,
        "visible_col_B": hB.collector.pre_trace,
        "visible_col_absdiff": abs(hA.collector.pre_trace
                                   - hB.collector.pre_trace),
        # 相位代理（诊断记录，非可见面）：ensemble pre_trace 向量 L2 距离
        "hidden_ens_l2": math.sqrt(sum(
            (a.pre_trace - b.pre_trace) ** 2
            for a, b in zip(_osc_neurons(hA), _osc_neurons(hB)))),
    }
    return hA, hB, t0, vis


def _transplant(dst, src, tier):
    """DIAGNOSTIC_INTERVENTION：把 src 臂候选状态写入 dst 臂（研究区专用）。"""
    if tier == "sham":
        dst.l1.__dict__.update(deepcopy(src.l1.__dict__))
        return
    for nd, ns in zip(_osc_neurons(dst), _osc_neurons(src)):
        if tier == "Z_low":
            nd.pre_trace = ns.pre_trace
        elif tier == "Z_full":
            nd.__dict__.update(deepcopy(ns.__dict__))
        else:
            raise ValueError(tier)


def main() -> int:
    print("=" * 60)
    print("G0-R1 Step4 — Hidden Dynamics Closure #1: oscillator phase")
    print("=" * 60)

    # ── twin 构造与基线未来 ──
    hA, hB, t0, vis = _build_pair()
    print(f"  t0={t0}  visible col A/B = {vis['visible_col_A']:.6f}/"
          f"{vis['visible_col_B']:.6f} (|Δ|={vis['visible_col_absdiff']:.2e})"
          f"  hidden ens L2={vis['hidden_ens_l2']:.4f}")
    latA, occA, trajA = _future(hA, t0, len(hA.closure.events))
    latB, occB, trajB = _future(hB, t0, len(hB.closure.events))
    base_rmse = _rmse(trajA, trajB)
    diverged = (latA != latB) or base_rmse > 1e-6
    print(f"  baseline futures: lat A/B = {latA}/{latB}  occ {occA}/{occB}"
          f"  RMSE={base_rmse:.3e}  ⇒ {'DIVERGED' if diverged else 'SAME'}")

    rows = [{"arm": "A_ref", "latency": latA, "occ": occA, "rmse_vs_A": 0.0,
             "equalized": True},
            {"arm": "B_baseline", "latency": latB, "occ": occB,
             "rmse_vs_A": base_rmse, "equalized": not diverged}]
    ruling = {"twin": vis, "baseline_diverged": diverged}

    if not diverged:
        ruling["ruling"] = "OSCILLATOR_PHASE_MICROSTATE_ONLY"
        ruling["stop"] = "STOP_DEEPER_DECOMPOSITION (§15: 相位不改变未来)"
    else:
        # ── 干预臂（每臂重建 B 到 t0，移植，跑相同未来）──
        for tier in ("sham", "Z_low", "Z_full"):
            hA2, hB2 = fresh_g0(), fresh_g0()
            _drive(hA2, 0, t0, [(0, PRE_LEN)])
            _drive(hB2, 0, t0, [(DELTA, DELTA + PRE_LEN)])
            _transplant(hB2, hA2, tier)
            lat, occ, traj = _future(hB2, t0, len(hB2.closure.events))
            r = _rmse(trajA, traj)
            eq = (lat == latA) and r < 1e-9
            rows.append({"arm": f"B+{tier}", "latency": lat, "occ": occ,
                         "rmse_vs_A": r, "equalized": eq})
            print(f"  intervention {tier:7s}: lat={lat} occ={occ} "
                  f"RMSE={r:.3e} equalized={eq}")
        eq_map = {r["arm"]: r["equalized"] for r in rows}
        causal = eq_map.get("B+Z_full", False)
        sham_neg = not eq_map.get("B+sham", True)
        if causal:
            minimal = "Z_low(pre_trace×10)" if eq_map.get("B+Z_low") \
                else "Z_full(hc+ensemble+collector full state)"
            ruling["ruling"] = "HIDDEN_STATE_CAUSALLY_SUPPORTED"
            ruling["sham_negative_control_ok"] = sham_neg
            ruling["minimal_sufficient_state_candidate"] = minimal
            ruling["stop"] = ("CURRENT_MINIMAL_SUFFICIENT_STATE_CANDIDATE + "
                              "STOP_DEEPER_DECOMPOSITION (§14)")
        else:
            ruling["ruling"] = "CORRELATIONAL_ONLY"
            ruling["stop"] = "候选载体未确认——按§13登记，不深挖"

    # ── 输出 ──
    with open(os.path.join(DATA, 'hidden_twin_pairs.csv'), 'w',
              newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(vis))
        w.writeheader(); w.writerow(vis)
    with open(os.path.join(DATA, 'hidden_interventions.csv'), 'w',
              newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    with open(os.path.join(DATA, 'minimal_state_ruling.json'), 'w') as f:
        json.dump(ruling, f, indent=1, ensure_ascii=False)

    print("=" * 60)
    print(f"RULING: {ruling['ruling']}  |  {ruling['stop']}")
    ok = ruling["ruling"] in ("HIDDEN_STATE_CAUSALLY_SUPPORTED",
                              "OSCILLATOR_PHASE_MICROSTATE_ONLY")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
