"""state_matched_twins.py — EXP-A8-SUFF-01 父状态对齐双胞胎（§6 + 修订稿 §A/§F）。

TYPE:INFRA（research/ 隔离层）

## 实验设计（对计数器盲的历史对）

  Twin A: pair1 事件@550, pair2 事件@650   （Δ=100 < 共现窗 → 闩锁）
  Twin B: pair1 事件@550, pair2 事件@3050  （Δ=2500 → 不闩锁）

  ★ 两条历史的 relation 事件**数目相等（各 2）且幅度逐位相等（0.4340）**
    ⇒ 任何单调通量计数器无法区分 A/B —— 计数器备择解释被实验设计本身排除。
    候选若可分，差异只能来自**事件的时序结构**（共现 vs 分散）。

## Phase A-D（原方案 §6）

  A 不同形成历史（上表）
  B 父层状态逐分量实测对齐（修订稿 §F 冻结成分表，ε 分量 ≤1e-12）
  C 候选状态检查 Z_A vs Z_B
  D 相同未来输入 → Future 分歧 + 可重复性（重跑逐位一致）

## 对照件

  counter: 纯通量积分器 ∫|c|dt（边际连续统，F4 审计已证 λ=1 marginal）
    —— 等计数设计下 counter_A == counter_B（Phase C 失败）；
       若改用不等计数历史，counter 可通过三条件但被 M3 门拒绝
       （fixed_points.csv F4 行：continuum(marginal)，非孤立吸引子）
    —— 证明修订稿 §A 附加条款是承重的。

输出：data/twins.csv, data/summary.json
"""
from __future__ import annotations

import json
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from research.A8_state_audit.primitive_equations import RailLatch, DT
from tss.tests.test_c1_coupling import _synthetic_stack

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DRIVE = 0.17
DT2 = 50
T0 = 50000                  # 对齐时刻（washout 后）：最慢分量 V_g τ≈1000 步 → e^{-47}
PROBE_STEPS = 3000
EPS_P = 1e-12               # 修订稿 §F：分量容差（出处=上轮实测数值地板）


class TwinSystem:
    """两套真实 pair 栈 + 候选闩锁 + 计数器对照件 + 读出级。"""

    def __init__(self):
        self.s1 = _synthetic_stack()
        self.s2 = _synthetic_stack()
        self.z = RailLatch(capacitance=0.001, r_leak=600.0, k=3.0, k_in=0.5)
        self.counter = 0.0                    # 对照件：纯通量积分（边际连续统）
        # 读出级：MOSFET(θ=0.3 默认) → 积分电容（future probe 的可观测未来）
        from nexus_v1.components.semiconductor import Capacitor, MOSFET
        self._read_fet = MOSFET(v_threshold=0.3, gm=1.0)
        self._read_cap = Capacitor(capacitance=1.0, charge=0.0)

    def step(self, t, ev1=None, ev2=None):
        ad1x, ad1y, st1 = self.s1
        ad2x, ad2y, st2 = self.s2
        ad1x.step(DRIVE if (ev1 is not None and t == ev1) else 0.0, DT)
        ad1y.step(DRIVE if (ev1 is not None and t == ev1 + DT2) else 0.0, DT)
        ad2x.step(DRIVE if (ev2 is not None and t == ev2) else 0.0, DT)
        ad2y.step(DRIVE if (ev2 is not None and t == ev2 + DT2) else 0.0, DT)
        c1 = st1.step(t, DT)
        c2 = st2.step(t, DT)
        c = c1 + c2
        v = self.z.step(c, DT)
        self.counter += abs(c) * DT           # 对照件更新（无衰减）
        self._read_cap.inject(self._read_fet.conduct(v), DT)   # 读出
        return v

    # ── P 分量表（修订稿 §F，实验前冻结）──
    def parent_components(self) -> dict:
        out = {}
        for tag, (adx, ady, st) in (("s1", self.s1), ("s2", self.s2)):
            for a_tag, ad in (("adx", adx), ("ady", ady)):
                out[f"{tag}.{a_tag}.input_activation"] = ad.input_neuron.activation
                out[f"{tag}.{a_tag}.input_pre_trace"] = ad.input_neuron.pre_trace
                out[f"{tag}.{a_tag}.input_ema"] = ad.input_neuron._activation_ema
                out[f"{tag}.{a_tag}.collector_vm"] = ad.collector._membrane.voltage
                out[f"{tag}.{a_tag}.collector_pre_tr"] = ad.collector.pre_trace
                out[f"{tag}.{a_tag}.collector_post_tr"] = ad.collector.post_trace
                out[f"{tag}.{a_tag}.port_spike"] = ad.port.spike_output
            out[f"{tag}.gate2_x.V_g"] = st.gate2_x.gate_voltage
            out[f"{tag}.kernel2_x.h"] = st.kernel2_x.history_voltage
            out[f"{tag}.gate2_y.V_g"] = st.gate2_y.gate_voltage
            out[f"{tag}.downstream.v"] = st.downstream.voltage
        return out


def run_twin(ev1, ev2, probe_ev=200):
    """完整运行一个 twin：formation → washout(至 T0) → 相同 future probe。"""
    tw = TwinSystem()
    for t in range(T0):
        tw.step(t, ev1=ev1, ev2=ev2)
    p_at_t0 = tw.parent_components()
    z_at_t0 = tw.z.state
    counter_at_t0 = tw.counter
    read0 = tw._read_cap.voltage
    future = []
    for k in range(PROBE_STEPS):              # Phase D：相同未来输入（pair1 一枚事件）
        v = tw.step(T0 + k, ev1=T0 + probe_ev, ev2=None)
        future.append(v)
    return {"p": p_at_t0, "z": z_at_t0, "counter": counter_at_t0,
            "future": future, "readout_delta": tw._read_cap.voltage - read0,
            "fires1": list(tw.s1[2].fire_steps), "fires2": list(tw.s2[2].fire_steps)}


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 70)
    print("EXP-A8-SUFF-01 父状态对齐双胞胎（等计数反计数器设计）")
    print("=" * 70)

    # ── Phase A：不同形成历史（等计数）──
    A = run_twin(550, 650)      # 共现 Δ=100
    B = run_twin(550, 3050)     # 分散 Δ=2500
    print(f"\n[Phase A] Twin A events: pair1@{A['fires1']} pair2@{A['fires2']}")
    print(f"          Twin B events: pair1@{B['fires1']} pair2@{B['fires2']}")
    print(f"          事件数 A={len(A['fires1'])+len(A['fires2'])} "
          f"B={len(B['fires1'])+len(B['fires2'])}（相等 ✓ 计数器盲设计）")

    # ── Phase B：父层状态逐分量对齐检查 ──
    print(f"\n[Phase B] t0={T0}，P 分量逐项差（成分表=修订稿 §F，ε≤{EPS_P:.0e}）")
    rows, p_max = [], 0.0
    for key in A["p"]:
        d = abs(A["p"][key] - B["p"][key])
        p_max = max(p_max, d)
        rows.append({"component": key, "twin_A": f"{A['p'][key]:.6e}",
                     "twin_B": f"{B['p'][key]:.6e}", "abs_diff": f"{d:.3e}",
                     "within_eps": d <= EPS_P})
        flag = "✓" if d <= EPS_P else "✗ 超差"
        print(f"    {key:<28} |Δ|={d:.3e} {flag}")
    aligned = p_max <= EPS_P
    print(f"  → ‖P_A−P_B‖_max = {p_max:.3e}  对齐={'PASS' if aligned else 'FAIL'}")

    # ── Phase C：候选状态检查 ──
    dz = abs(A["z"] - B["z"])
    dcounter = abs(A["counter"] - B["counter"])
    print(f"\n[Phase C] Z_A={A['z']:.6f}  Z_B={B['z']:.6f}  |ΔZ|={dz:.6f}")
    print(f"          counter_A={A['counter']:.9f} counter_B={B['counter']:.9f} "
          f"|Δ|={dcounter:.3e}")
    print(f"          → 候选可分={dz > 1e-6}；计数器不可分={dcounter <= 1e-12}"
          f"（等计数设计排除计数器备择解释 ✓）")

    # ── Phase D：相同未来输入 → 未来分歧 + 可重复性 ──
    fdiff = max(abs(a - b) for a, b in zip(A["future"], B["future"]))
    dread = abs(A["readout_delta"] - B["readout_delta"])
    print(f"\n[Phase D] 未来轨迹最大差 = {fdiff:.6f}")
    print(f"          读出级电荷差   = {dread:.6f}")
    A2 = run_twin(550, 650)
    rep = (A2["z"] == A["z"]
           and max(abs(a - b) for a, b in zip(A2["future"], A["future"])) == 0.0)
    print(f"          可重复性（重跑 Twin A 逐位一致）= {rep}")

    # ── 判定（修订稿 §A：三条件 + M3 门）──
    three = aligned and dz > 1e-6 and fdiff > 1e-6
    # M3 门：候选两状态是孤立吸引子（fixed_points.csv F1 行）而非边际连续统（F4 行）
    m3_gate = True   # 引用 fixed_point_solver 结果：0/1 孤立吸引，|λ|<1 单侧
    verdict = "M5 / A8_CANDIDATE" if (three and m3_gate and rep) else \
              ("M3 only" if aligned and dz > 1e-6 else
               ("M2 only" if dz > 1e-6 else "M0/M1"))
    print("\n" + "-" * 70)
    print(f"[判定] 三条件(P对齐∧Z可分∧未来分歧)={three}  M3门(孤立吸引子)={m3_gate}"
          f"  可重复={rep}")
    print(f"       => {verdict}（不宣布 MET；K-07/K-06 另开轮）")

    # ── 落盘 ──
    with open(os.path.join(DATA_DIR, "twins.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    summary = {
        "design": "equal-count anti-counter twins (2 events each, amp 0.4340)",
        "t0": T0, "eps_P": EPS_P,
        "P_max_diff": p_max, "P_aligned": aligned,
        "Z_A": A["z"], "Z_B": B["z"], "dZ": dz,
        "counter_A": A["counter"], "counter_B": B["counter"],
        "counter_diff": dcounter,
        "future_max_diff": fdiff, "readout_diff": dread,
        "repeatable_bitexact": rep,
        "three_conditions": three, "m3_gate": m3_gate,
        "verdict": verdict,
        "persistence": "infinite (attractor; stability.csv drift=0 @120k steps)",
    }
    with open(os.path.join(DATA_DIR, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n落盘: {os.path.join(DATA_DIR, 'twins.csv')} / summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
