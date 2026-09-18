"""t1a_diagnostic_replay.py — T1-A 候选架构诊断重放套件（R1-R8）。

TYPE:INFRA（research/ 诊断原型层；§12 纪律：不修改 production，不被
nexus/tss import——本脚本只单向消费 nexus 三点皮肤刺激源）

依据：外部《T1-A 执行方案》§10-§18（经评判 A1-A5 修正）；候选定义与
度量合同先冻结于 `T1A_CANDIDATE_ARCHITECTURES_AND_METRICS.md`。

## 候选（参数=机制扫描代表值，§19：只冻结角色/量纲/合法域，不冻结值）

  legacy : u = clip[κ(q−q0)+b, 0, 0.04]          （负对照，原参数）
  A      : u = S·(q − Y_ref)                      S=κ_legacy, Y_ref=0（实测静息）
  B      : u = g·(q_t − q_{t−1})                  g=κ·τ_field=0.2751（显式单步
           寄存器状态——𝒫_Ṫ 物理身份=SkinPatch.dT 先例, world.py:263）
  C      : ẋ=(q−x)/τ_a, u=g_c·(q−x)              τ_a=200, g_c=κ_legacy
           （适应态高通；重复性判据见 §10.C）
  M      : u = a·asinh(s·(q−Y_ref))               MATHEMATICAL_CONTROL，
           a=0.005, s=0.05（非项目结构，仅对照）

## L1 读出（READ_ONLY 消费，公式复刻自 transducer_neurons.py:305-323）

  L1(u) = clip(max(0, u×200), 0, 10)

## 场景（R1-R8；除 R5 外 Y_B=BOUNDARY_REDUCED_N0=node0；R5=正对照协议）

  见 T1A_CANDIDATE_ARCHITECTURES_AND_METRICS.md §三 表。
  R4 的 ramp 末端幅值按线性叠加原理用单位 ramp 实测缩放（场线性已由 T0
  验证 dev=7e-16），保证 T_A(600)=T_B(600) 同峰值不同上升速度。

## 度量（§15-§18 合同）：绝对+归一并报/占用率/符号保留/峰时/假放大防护。

输出：../data/t1a_diagnostic_replay.json + ../data/candidate_response.csv
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..', '..')))

from nexus_v1.components.skin_three_point import (  # noqa: E402
    TEST_KAPPA_THREE_POINT, TEST_R_LEAK_AMBIENT_THREE_POINT,
    build_three_point_skin)
from tss.generators.skin_transduction import (  # noqa: E402
    REFERENCE_TRANSDUCTION_CONFIG as LEG, transduce)

DATA_DIR = os.path.abspath(os.path.join(_HERE, '..', 'data'))
KAPPA_L = LEG.kappa_i          # 参数角色: [u/T] 尺度（机制扫描代表值）
TAU_FIELD = 200.0              # TEST 档场时间常数（T0 实测谱）
EPS_ZERO = 1e-12


# ── 候选原型（reset/step 接口；状态显式声明） ───────────────────────────
class Legacy:
    name = "legacy"
    has_ceiling = True

    def reset(self):
        pass

    def step(self, q):
        return transduce(q, LEG)


class CandA:
    name = "A_thin_amplitude"
    has_ceiling = False

    def reset(self):
        pass

    def step(self, q):
        return KAPPA_L * (q - 0.0)     # Y_ref=0（rest_baseline 实测）


class CandB:
    name = "B_rate_port"
    has_ceiling = False

    def reset(self):
        self._prev = None              # 显式单步寄存器（SkinPatch.dT 先例）

    def step(self, q):
        u = 0.0 if self._prev is None else KAPPA_L * TAU_FIELD * (q - self._prev)
        self._prev = q
        return u


class CandC:
    name = "C_sensor_state"
    has_ceiling = False
    TAU_A = 200.0                      # 参数角色: 适应时间尺度 [step]

    def reset(self):
        self._x = 0.0                  # 适应态 x_D（物理载体待指派，见判定）

    def step(self, q):
        self._x += (q - self._x) / self.TAU_A
        return KAPPA_L * (q - self._x)


class MathCtrl:
    name = "M_math_control"            # MATHEMATICAL_CONTROL：非项目结构
    has_ceiling = False

    def reset(self):
        pass

    def step(self, q):
        return 0.005 * math.asinh(0.05 * q)


CANDIDATES = [Legacy(), CandA(), CandB(), CandC(), MathCtrl()]


def l1_readout(u):
    """L1 方程复刻（transducer_neurons.py:305-323，READ_ONLY 消费）。"""
    return min(max(0.0, u * 200.0), 10.0)


# ── 刺激源（三点皮肤 TEST 档；Y_B=node0 除 R5 声明外） ──────────────────
def run_field(plan, t_total, read_node=0):
    """plan: list of (t0,t1,node,amp) 或 callable(t)->{node:amp}"""
    g = build_three_point_skin(kappa=TEST_KAPPA_THREE_POINT,
                               r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)
    qs = []
    for t in range(t_total):
        if callable(plan):
            ext = plan(t)
        else:
            ext = {}
            for (t0, t1, node, amp) in plan:
                if t0 <= t < t1:
                    ext[node] = ext.get(node, 0.0) + amp
        g.step(1.0, ext)
        qs.append(g.cells[read_node].temperature)
    return qs


def build_scenarios():
    sc = {}
    sc["R1_rest_small"] = {"cfg": "REDUCED_N0", "q": run_field(
        [(0, 300, 0, 0.02)], 900), "drive_end": 300}
    sc["R2_slow_ramp"] = {"cfg": "REDUCED_N0", "q": run_field(
        lambda t: {0: 1.0 * t / 1500} if t < 1500 else {}, 2100),
        "drive_end": 1500}
    sc["R3_fast_step"] = {"cfg": "REDUCED_N0", "q": run_field(
        [(0, 1500, 0, 1.0)], 2100), "drive_end": 1500}
    # R4 同峰值不同上升速度：ramp 末端幅值按单位 ramp 实测缩放
    qa = run_field([(0, 600, 0, 1.0)], 1200)
    q_ramp_unit = run_field(lambda t: {0: t / 600} if t < 600 else {}, 1200)
    scale_b = qa[599] / q_ramp_unit[599]
    qb = run_field(lambda t: {0: scale_b * t / 600} if t < 600 else {}, 1200)
    assert abs(qa[599] - qb[599]) < 1e-9 * qa[599], "R4 same-peak failed"
    sc["R4_same_peak"] = {"cfg": "REDUCED_N0", "pair": (qa, qb),
                          "drive_end": 600,
                          "note": f"scale_b={scale_b:.6f}, T_peak={qa[599]:.4f}"}
    # R5 正对照协议原样（WT0 冻结）
    q5a = run_field([(0, 100, 0, 1.0)], 1100)
    q5b = run_field([(0, 100, 2, 1.996)], 1100)
    sc["R5_hidden_history"] = {"cfg": "REDUCED_N0 (positive-control)",
                               "pair": (q5a, q5b), "drive_end": 100}
    sc["R6_large"] = {"cfg": "REDUCED_N0", "q": run_field(
        [(0, 2000, 0, 50.0)], 2500), "drive_end": 2000}
    sc["R7_weak"] = {"cfg": "REDUCED_N0", "q": run_field(
        [(0, 2000, 0, 0.1)], 2500), "drive_end": 2000}
    # R8 脉冲 vs 持续（w0e Γ_A/Γ_C 等能量）
    q8a = run_field([(0, 300, 0, 1.0)], 2000)
    q8c = run_field([(0, 25, 0, 6.0), (500, 525, 0, 6.0)], 2000)
    sc["R8_pulse_vs_sustained"] = {"cfg": "REDUCED_N0", "pair": (q8a, q8c),
                                   "drive_end": 525}
    return sc


# ── 度量 ────────────────────────────────────────────────────────────────
def rms(xs):
    return math.sqrt(sum(v * v for v in xs) / len(xs))


def dist(xs, ys):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(xs, ys)) / len(xs))


def occupancy(us, cand):
    n = len(us)
    zero = sum(1 for u in us if abs(u) <= EPS_ZERO) / n
    sat = (sum(1 for u in us if u >= LEG.u_clip_max) / n
           if cand.has_ceiling else 0.0)
    interior = 1.0 - zero - sat
    return zero, sat, interior


def single_metrics(cand, qs, drive_end):
    cand.reset()
    us = [cand.step(q) for q in qs]
    l1s = [l1_readout(u) for u in us]
    zero, sat, interior = occupancy(us, cand)
    decay = us[drive_end:]
    neg_frac_decay = (sum(1 for u in decay if u < -EPS_ZERO) / len(decay)
                      if decay else 0.0)
    peak_dt = (max(range(len(us)), key=lambda i: abs(us[i]))
               - max(range(len(qs)), key=lambda i: qs[i]))
    return {"zero_occ": zero, "sat_occ": sat, "interior_occ": interior,
            "neg_frac_decay": neg_frac_decay, "peak_timing_offset": peak_dt,
            "u_min": min(us), "u_max": max(us),
            "L1_max": max(l1s), "L1_nonzero_frac":
                sum(1 for v in l1s if v > 0) / len(l1s)}, us


def pair_metrics(cand, qa, qb):
    cand.reset()
    ua = [cand.step(q) for q in qa]
    cand.reset()
    ub = [cand.step(q) for q in qb]
    la, lb = [l1_readout(u) for u in ua], [l1_readout(u) for u in ub]
    d_b_abs = dist(qa, qb)
    d_b_norm = d_b_abs / max(rms(qa), rms(qb), 1e-30)
    d_p_abs = dist(ua, ub)
    d_p_norm = d_p_abs / max(rms(ua), rms(ub), 1e-30)
    d_l_abs = dist(la, lb)
    d_l_norm = d_l_abs / max(rms(la), rms(lb), 1e-30)
    zero_a, _, _ = occupancy(ua, cand)
    zero_b, _, _ = occupancy(ub, cand)
    artifact = bool(d_p_norm > d_b_norm and (zero_a + zero_b) / 2 > 0.5)
    return {"D_boundary_abs": d_b_abs, "D_boundary_norm": d_b_norm,
            "D_port_abs": d_p_abs, "D_port_norm": d_p_norm,
            "D_L1_abs": d_l_abs, "D_L1_norm": d_l_norm,
            "zero_occ_mean": (zero_a + zero_b) / 2,
            "baseline_zeroing_artifact": artifact}


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 78)
    print("T1-A 诊断重放套件 R1-R8 × 5 候选（含双对照）")
    print("=" * 78)
    scenarios = build_scenarios()
    out = {"contract_ref": "T1A_CANDIDATE_ARCHITECTURES_AND_METRICS.md",
           "scenarios": {}}
    csv_rows = []
    # C↔B 重复性判据数据（R3 上的输出相关）
    for name, spec in scenarios.items():
        print(f"\n[{name}]  Y_B={spec['cfg']}"
              + (f"  ({spec['note']})" if 'note' in spec else ""))
        entry = {"y_b_config": spec["cfg"]}
        if "pair" in spec:
            for cand in CANDIDATES:
                m = pair_metrics(cand, *spec["pair"])
                entry[cand.name] = m
                csv_rows.append({"scenario": name, "candidate": cand.name,
                                 "kind": "pair", **m})
                print(f"  {cand.name:>18}: D_bnd={m['D_boundary_abs']:.4f}"
                      f"/{m['D_boundary_norm']:.3f}  "
                      f"D_port={m['D_port_abs']:.2e}/{m['D_port_norm']:.3f}  "
                      f"D_L1={m['D_L1_abs']:.3f}/{m['D_L1_norm']:.3f}  "
                      f"zero={m['zero_occ_mean']:.2f}  "
                      f"artifact={m['baseline_zeroing_artifact']}")
        else:
            for cand in CANDIDATES:
                m, _ = single_metrics(cand, spec["q"], spec["drive_end"])
                entry[cand.name] = m
                csv_rows.append({"scenario": name, "candidate": cand.name,
                                 "kind": "single", **m})
                print(f"  {cand.name:>18}: zero={m['zero_occ']:.3f} "
                      f"sat={m['sat_occ']:.3f} neg_decay={m['neg_frac_decay']:.2f} "
                      f"peakΔt={m['peak_timing_offset']:>5} "
                      f"u∈[{m['u_min']:.2e},{m['u_max']:.2e}] "
                      f"L1max={m['L1_max']:.2f} L1act={m['L1_nonzero_frac']:.2f}")
        out["scenarios"][name] = entry

    # C↔B 重复性：R3 场景两者输出皮尔逊相关
    q3 = scenarios["R3_fast_step"]["q"]
    b, c = CandB(), CandC()
    b.reset()
    ub = [b.step(q) for q in q3]
    c.reset()
    uc = [c.step(q) for q in q3]
    mb, mc = sum(ub) / len(ub), sum(uc) / len(uc)
    cov = sum((x - mb) * (y - mc) for x, y in zip(ub, uc))
    var = math.sqrt(sum((x - mb) ** 2 for x in ub)
                    * sum((y - mc) ** 2 for y in uc))
    corr_bc = cov / max(var, 1e-30)
    out["candidate_C_duplication"] = {"corr_uB_uC_on_R3": corr_bc,
                                      "tau_a": CandC.TAU_A}
    print(f"\nC↔B 重复性判据: corr(u_B, u_C)@R3 = {corr_bc:.4f} (τ_a=200)")

    path = os.path.join(DATA_DIR, "t1a_diagnostic_replay.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    csv_path = os.path.join(DATA_DIR, "candidate_response.csv")
    keys = sorted({k for r in csv_rows for k in r})
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(csv_rows)
    print(f"落盘: {path}\n落盘: {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
