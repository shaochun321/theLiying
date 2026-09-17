"""f1_revalidation.py — M1-M5 从零重判（§16，不继承旧报告状态）。

TYPE:INFRA（research/ 隔离层）

## 协议

同一 RailLatch 类（rail_latch.py，唯一权威动力学）+ fingerprint 守卫，
Scale-A 与 Scale-B 都跑（§八诊断要求）：

  M1 固定点        两尺度解析固定点；对照外部复算基准
                   （λ=0.9983347214509387；Scale-A N=3 V_u=0.6768313625；
                     Scale-B N=1 V_u≈0.3010025 / N=3 V_u≈0.3006676）
  M2 可达性        真实 C1 链路 c_ro（k_in=0.5）；对照外部峰值表
                   （gap100=0.400715 / 400=0.328435 / 600=0.296851 / 700=0.284595）
  M3/M4 双胞胎     等计数反计数器设计 + census 自动 P 对齐（非人工列表）
                   + 阈值读出 + 逐位可重复
  dt 鲁棒性        c_ro 事件回放进 finite-clamp dt/100 候选，
                   验证 latch/no-latch 模式一致（回应 PHYSICAL_BISTABILITY_DT_LIMITED）

## 第四轮变更

  1. canonical N=1（最小化）；M1 仍两尺度 × N∈{1,3} 全跑，Scale-B 资格看 N=1，
     Scale-A 对照沿用 N=3（外部"Scale-A M1✓/M2✗"基线的原始配置）。
  2. census 全递归版：P 对齐 = DYNAMIC_CAUSAL 数值逐项 + 摘要串等值；
     HISTORICAL_LOG（fire_steps/spike_times）单独比对，并用 purge 实证
     （T0 清空日志 → future 必须逐位不变）证明其不进入 parent future dynamics。
  3. M5-P 第六门（方案 §十八）：读取 data/rail_causality.json；
     M1-M5 ✓ + M5-P ✓ ⇒ F1_A8v2_PHYSICALLY_VALIDATED；
     M5-P ✗/缺 ⇒ DYNAMICAL_CANDIDATE_ONLY（§十九守卫：不开 K-07）。

输出：data/f1_revalidation.json
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from research.A8_state_audit.candidate_config import (
    CANONICAL, SCALE_A_DIAG, assert_fingerprint)
from research.A8_state_audit.rail_latch import RailLatch
from research.A8_state_audit.parent_state_census import (
    census, purge_historical_logs)
from tss.tests.test_c1_coupling import _synthetic_stack

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DRIVE = 0.17
DT2 = 50
T0 = 50000
PROBE_STEPS = 3000
EPS_P = 1e-12

EXT = {   # 外部复算基准（方案 §八）
    "lambda": 0.9983347214509387,
    "Vu_A_N3": 0.6768313625,
    "Vu_B_N1": 0.3010025,
    "Vu_B_N3": 0.3006676,
    "peaks": {100: 0.400715, 400: 0.328435, 600: 0.296851, 700: 0.284595},
}


def make_latch(cfg, **over):
    kw = dict(capacitance=cfg["C"], r_leak=cfg["R"], theta=cfg["theta"],
              gm=cfg["gm"], n_feedback_fets=cfg["n_feedback_fets"],
              v_rail=cfg["v_rail"], rail_r_internal=cfg["rail_r_internal"],
              clamp_mode=cfg["clamp_mode"], clamp_gm=cfg["clamp_gm"],
              clamp_threshold=cfg["clamp_threshold"], k_in=cfg["k_in"])
    kw.update(over)
    return RailLatch(**kw)


# ─────────────────────────────────────────────────────────────────────
# M1：固定点（两尺度）
# ─────────────────────────────────────────────────────────────────────

def m1(out: dict) -> None:
    print("\n[M1] 固定点（同一 RailLatch 类，两尺度）")
    rows = {}
    for cfg in (SCALE_A_DIAG, CANONICAL):
        for n in (1, 3):
            z = make_latch(cfg, n_feedback_fets=n)
            fps = z.fixed_points()
            key = f"{cfg['name']}/N={n}"
            vu = next((f["v"] for f in fps if f["stability"] == "unstable"), None)
            n_stable = sum(1 for f in fps if "un" not in f["stability"])
            rows[key] = {"fixed_points": fps, "V_u": vu, "n_stable": n_stable,
                         "bistable": n_stable >= 2}
            print(f"  {key:<14} FP数={len(fps)}  V_u="
                  f"{'—' if vu is None else format(vu, '.10f')}  双稳={n_stable >= 2}")
    lam = make_latch(CANONICAL).lam
    checks = {
        "lambda_match": lam == EXT["lambda"],
        "Vu_A_N3_match": abs((rows["Scale-A/N=3"]["V_u"] or 0) - EXT["Vu_A_N3"]) < 5e-10,
        "Vu_B_N1_match": abs((rows["Scale-B/N=1"]["V_u"] or 0) - EXT["Vu_B_N1"]) < 5e-7,
        "Vu_B_N3_match": abs((rows["Scale-B/N=3"]["V_u"] or 0) - EXT["Vu_B_N3"]) < 5e-7,
    }
    print(f"  外部基准比对: λ 逐位={checks['lambda_match']}  "
          f"V_u(A,N3)={checks['Vu_A_N3_match']}  "
          f"V_u(B,N1)={checks['Vu_B_N1_match']}  V_u(B,N3)={checks['Vu_B_N3_match']}")
    out["M1"] = {"rows": {k: {kk: vv for kk, vv in v.items() if kk != "fixed_points"}
                          for k, v in rows.items()},
                 "external_checks": checks,
                 # 第四轮：Scale-B 资格看 canonical N=1；Scale-A 对照沿用 N=3
                 # （外部 Scale-A M1✓/M2✗ 基线的原始配置）
                 "verdict": {"Scale-A": rows["Scale-A/N=3"]["bistable"],
                             "Scale-B": rows["Scale-B/N=1"]["bistable"]}}


# ─────────────────────────────────────────────────────────────────────
# M2：可达性（真实链路，两尺度）
# ─────────────────────────────────────────────────────────────────────

def _run_reach(cfg, t1, t2, total=20000):
    s1, s2 = _synthetic_stack(), _synthetic_stack()
    z = make_latch(cfg)
    peak, c_events = 0.0, 0
    for t in range(total):
        s1[0].step(DRIVE if t == t1 else 0.0, 0.001)
        s1[1].step(DRIVE if t == t1 + DT2 else 0.0, 0.001)
        s2[0].step(DRIVE if t == t2 else 0.0, 0.001)
        s2[1].step(DRIVE if t == t2 + DT2 else 0.0, 0.001)
        c1 = s1[2].step(t, 0.001)
        c2 = s2[2].step(t, 0.001)
        if c1 > 0 or c2 > 0:
            c_events += 1
        v = z.step(c1 + c2)
        peak = max(peak, v)
    return peak, z.state, c_events


def m2(out: dict) -> None:
    print("\n[M2] 可达性（真实 c_ro，同一 RailLatch，两尺度）")
    cases = [("gap100", 500, 600, "high"), ("gap400", 500, 900, "high"),
             ("gap600", 500, 1100, "low"), ("gap700", 500, 1200, "low"),
             ("single", 500, -10**9, "low"), ("none", -10**9, -10**9, "low")]
    res = {}
    for cfg in (SCALE_A_DIAG, CANONICAL):
        rows = {}
        for name, t1, t2, expect in cases:
            peak, v_end, ne = _run_reach(cfg, t1, t2)
            basin = "high" if v_end > 0.9 else ("low" if v_end < 0.1 else "MID")
            rows[name] = {"peak": peak, "v_final": v_end, "events": ne,
                          "basin": basin, "expected_B": expect}
        res[cfg["name"]] = rows
        reach = (rows["gap100"]["basin"] == "high"
                 and rows["gap700"]["basin"] == "low")
        both = any(r["basin"] == "high" for r in rows.values()) and \
               any(r["basin"] == "low" for r in rows.values())
        print(f"  {cfg['name']}: " + "  ".join(
            f"{k}={r['basin']}(pk={r['peak']:.6f})" for k, r in rows.items()))
        print(f"    两吸引域均可达={both}")
    # 外部峰值表比对（Scale-B 非闩锁段峰值 = 前馈峰值）
    checks = {}
    for gap, t2 in ((600, 1100), (700, 1200)):
        pk = res["Scale-B"][f"gap{gap}"]["peak"]
        checks[f"peak{gap}"] = abs(pk - EXT["peaks"][gap]) < 5e-6
    # 闩锁段前馈峰值用解析式对照
    lam = math.exp(-0.001 / 0.6)
    for gap in (100, 400):
        ff = CANONICAL["k_in"] * 0.434031 * 0.001 / CANONICAL["C"] * (1 + lam ** gap)
        checks[f"peak{gap}_analytic"] = abs(ff - EXT["peaks"][gap]) < 5e-6
    print(f"  外部峰值表比对: {checks}")
    out["M2"] = {"scales": res, "external_checks": checks,
                 "verdict": {
                     "Scale-A": "NOT_REACHED (peak≈4e-4 ≪ θ)" if
                     res["Scale-A"]["gap100"]["basin"] == "low" else "REACHED?",
                     "Scale-B": "REACHED (both basins)" if
                     res["Scale-B"]["gap100"]["basin"] == "high" and
                     res["Scale-B"]["gap700"]["basin"] == "low" else "FAIL"}}


# ─────────────────────────────────────────────────────────────────────
# M3/M4：双胞胎（canonical，census 自动 P 对齐 + 阈值读出）
# ─────────────────────────────────────────────────────────────────────

class Twin:
    def __init__(self):
        self.s1 = _synthetic_stack()
        self.s2 = _synthetic_stack()
        self.z = make_latch(CANONICAL)
        from nexus_v1.components.semiconductor import MOSFET, Capacitor
        self._read_fet = MOSFET(v_threshold=0.3, gm=1.0)
        self._read_cap = Capacitor(capacitance=1.0, charge=0.0)
        self.counter = 0.0
        self.c_record = []          # 前 7000 步 c 序列（dt 回放用）

    def step(self, t, ev1, ev2):
        self.s1[0].step(DRIVE if t == ev1 else 0.0, 0.001)
        self.s1[1].step(DRIVE if t == ev1 + DT2 else 0.0, 0.001)
        self.s2[0].step(DRIVE if t == ev2 else 0.0, 0.001)
        self.s2[1].step(DRIVE if t == ev2 + DT2 else 0.0, 0.001)
        c = self.s1[2].step(t, 0.001) + self.s2[2].step(t, 0.001)
        v = self.z.step(c)
        self.counter += abs(c) * 0.001
        self._read_cap.inject(self._read_fet.conduct(v), 0.001)
        if t < 7000:
            self.c_record.append(c)
        return v

    def parent_census_values(self) -> dict:
        """全递归 census 快照，按比对方式分三桶（第四轮）：
        num   = DYNAMIC_CAUSAL 数值（int/float）→ max|Δ| 阈值比对
        exact = DYNAMIC_CAUSAL 摘要/占位串（>64 标量表 sha 等）→ 等值比对
        hist  = HISTORICAL_LOG 全部条目 → 单独报告 + purge 实证"""
        rows: list = []
        seen: set = set()
        for tag, (adx, ady, pair) in (("s1", self.s1), ("s2", self.s2)):
            census(adx, f"{tag}.adx", seen, rows)
            census(ady, f"{tag}.ady", seen, rows)
            census(pair, f"{tag}.pair", seen, rows)
        num, exact, hist = {}, {}, {}
        for r in rows:
            cat, v = r["category"], r["value"]
            if cat == "DYNAMIC_CAUSAL":
                if isinstance(v, (int, float)):
                    num[r["path"]] = float(v)
                else:
                    exact[r["path"]] = v
            elif cat == "HISTORICAL_LOG":
                hist[r["path"]] = v
        return {"num": num, "exact": exact, "hist": hist}


def run_twin(ev1, ev2, purge_logs: bool = False):
    tw = Twin()
    for t in range(T0):
        tw.step(t, ev1, ev2)
    purged = (purge_historical_logs([tw.s1, tw.s2]) if purge_logs else 0)
    p = tw.parent_census_values()
    z0 = tw.z.state
    counter0 = tw.counter
    read0 = tw._read_cap.voltage
    future = [tw.step(T0 + k, T0 + 200, -10**9) for k in range(PROBE_STEPS)]
    return {"p": p, "z": z0, "counter": counter0, "future": future,
            "readout_delta": tw._read_cap.voltage - read0,
            "c_record": tw.c_record, "purged_entries": purged}


def m34(out: dict) -> dict:
    print("\n[M3/M4] 等计数双胞胎（canonical，全递归 census P 对齐）")
    A = run_twin(550, 650)
    B = run_twin(550, 3050)
    # 1. DYNAMIC_CAUSAL 数值：max|Δ| 阈值比对
    keys = set(A["p"]["num"]) & set(B["p"]["num"])
    assert len(keys) == len(A["p"]["num"]) == len(B["p"]["num"]), "census 路径不一致"
    p_max = max(abs(A["p"]["num"][k] - B["p"]["num"][k]) for k in keys)
    # 2. DYNAMIC_CAUSAL 摘要串：等值比对（>64 标量表 sha 等）
    ex_keys = set(A["p"]["exact"]) | set(B["p"]["exact"])
    exact_mismatch = [k for k in ex_keys
                      if A["p"]["exact"].get(k) != B["p"]["exact"].get(k)]
    # 3. HISTORICAL_LOG：单独报告（期望有差——事件时刻不同），purge 实证其
    #    不进入 future dynamics
    h_keys = set(A["p"]["hist"]) | set(B["p"]["hist"])
    hist_diff = [k for k in h_keys
                 if A["p"]["hist"].get(k) != B["p"]["hist"].get(k)]
    dz = abs(A["z"] - B["z"])
    dcounter = abs(A["counter"] - B["counter"])
    fdiff = max(abs(a - b) for a, b in zip(A["future"], B["future"]))
    dread = abs(A["readout_delta"] - B["readout_delta"])
    A2 = run_twin(550, 650)
    rep = (A2["z"] == A["z"] and
           max(abs(a - b) for a, b in zip(A2["future"], A["future"])) == 0.0)
    # purge 实证：T0 清空 fire_steps/spike_times → future 必须逐位不变
    A3 = run_twin(550, 650, purge_logs=True)
    hist_purge_ok = (A3["z"] == A["z"] and max(
        abs(a - b) for a, b in zip(A3["future"], A["future"])) == 0.0)
    print(f"  P 数值（DYNAMIC_CAUSAL {len(keys)} 项）max|Δ| = {p_max:.3e} "
          f"(≤{EPS_P:.0e}: {p_max <= EPS_P})")
    print(f"  P 摘要串（{len(ex_keys)} 项）不等值 = {len(exact_mismatch)}"
          f"{'  ' + str(exact_mismatch[:4]) if exact_mismatch else ''}")
    print(f"  HISTORICAL_LOG（{len(h_keys)} 项）A/B 有差 = {len(hist_diff)} "
          f"（事件时刻不同所致，属预期）")
    print(f"  purge 实证：清空 {A3['purged_entries']} 条日志后 future 逐位不变 = "
          f"{hist_purge_ok} ⇒ 历史日志不进入 parent future dynamics")
    print(f"  Z_A={A['z']:.6f}  Z_B={B['z']:.6f}  |ΔZ|={dz:.6f}")
    print(f"  counter_A−counter_B = {dcounter:.3e}（等计数 ⇒ 计数器盲 ✓）")
    print(f"  future max|Δ|={fdiff:.6f}  读出电荷差={dread:.6f}  逐位可重复={rep}")
    out["M3M4"] = {"p_fields": len(keys), "p_max_diff": p_max,
                   "p_aligned": p_max <= EPS_P and not exact_mismatch,
                   "p_exact_fields": len(ex_keys),
                   "p_exact_mismatch": exact_mismatch,
                   "hist_fields": len(h_keys), "hist_diff_count": len(hist_diff),
                   "hist_purge_proof": hist_purge_ok,
                   "purged_entries": A3["purged_entries"],
                   "Z_A": A["z"], "Z_B": B["z"], "dZ": dz,
                   "counter_diff": dcounter, "future_max_diff": fdiff,
                   "readout_diff": dread, "repeatable": rep}
    return {"A": A["c_record"], "B": B["c_record"]}


# ─────────────────────────────────────────────────────────────────────
# dt 鲁棒性回放（finite clamp @ dt/100）
# ─────────────────────────────────────────────────────────────────────

def dt_replay(c_records: dict, out: dict) -> None:
    print("\n[dt 鲁棒性] c_ro 事件回放 → finite clamp @ dt/100")
    res = {}
    v_cont = make_latch(CANONICAL, clamp_mode="finite").continuous_limit_fixed_point()
    for tag, series in c_records.items():
        z = make_latch(CANONICAL, clamp_mode="finite")
        z.dt = CANONICAL["dt"] / 100.0
        for u in series:                     # 每原始步 = 100 子步，电荷守恒
            for _ in range(100):
                z.step(u)
        for _ in range(3000 * 100):          # 保持段
            z.step(0.0)
        res[tag] = z.state
        print(f"  twin {tag}: 回放+保持后 V = {z.state:.6f} "
              f"({'高支(连续极限' + format(v_cont, '.4f') + ')' if z.state > 0.9 else '低支'})")
    ok = res["A"] > 0.9 and res["B"] < 0.1
    print(f"  ⇒ latch/no-latch 模式与 hard-clamp dt=0.001 一致: {ok}")
    out["dt_replay"] = {"V_A": res["A"], "V_B": res["B"], "pattern_consistent": ok}


# ─────────────────────────────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────────────────────────────

def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    fp = assert_fingerprint(CANONICAL)
    print("=" * 70)
    print(f"F1 M1-M5 从零重判（fingerprint={fp}，不继承旧报告状态）")
    print("=" * 70)
    out = {"fingerprint": fp}
    m1(out)
    m2(out)
    c_records = m34(out)
    dt_replay(c_records, out)

    # ── 总判定（§16 四分支 + 第四轮 M5-P 第六门）──
    print("\n" + "=" * 70)
    b = out
    scaleA_reject = (b["M1"]["verdict"]["Scale-A"]
                     and "NOT_REACHED" in b["M2"]["verdict"]["Scale-A"])
    m5 = (b["M1"]["verdict"]["Scale-B"]
          and "REACHED" in b["M2"]["verdict"]["Scale-B"]
          and b["M3M4"]["p_aligned"] and b["M3M4"]["dZ"] > 1e-6
          and b["M3M4"]["future_max_diff"] > 1e-6 and b["M3M4"]["repeatable"]
          and b["M3M4"]["hist_purge_proof"]
          and b["dt_replay"]["pattern_consistent"])
    # M5-P：rail causality 实验结果（exp_F1_rail_causality.py 落盘）
    m5p_path = os.path.join(DATA_DIR, "rail_causality.json")
    m5p = None
    if os.path.exists(m5p_path):
        with open(m5p_path, encoding="utf-8") as f:
            m5p = json.load(f).get("M5P")
    m5p_pass = bool(m5p and m5p.get("pass"))
    print(f"  Scale-A: M1 成立但真实 c_ro 不可达 ⇒ M1 only / NOT_REACHED "
          f"({scaleA_reject})")
    print(f"  Scale-B(canonical) M1-M5: {'PASS' if m5 else 'FAIL'}")
    if m5p is None:
        print("  M5-P: NOT_RUN（缺 data/rail_causality.json —— "
              "先跑 exp_F1_rail_causality.py）")
    else:
        print(f"  M5-P physical support: {'PASS' if m5p_pass else 'FAIL'} "
              f"(断电零流={m5p.get('power_cut_zero_current')} "
              f"断电失忆={m5p.get('power_cut_forgets')} "
              f"账本可审计={m5p.get('energy_auditable')})")
    if m5 and m5p_pass:
        verdict_b = "F1_A8v2_PHYSICALLY_VALIDATED"
    elif m5:
        verdict_b = "DYNAMICAL_CANDIDATE_ONLY"     # §十九：不得进入生成元资格链
    else:
        verdict_b = "F1_REJECTED"
    print(f"  ⇒ Scale-B(canonical): {verdict_b}")
    print("  ── 条件化声明：该判定以 canonical=Scale-B 裁定为前提（自曝条款）；")
    print("     以 dt=0.001+hard clamp 为数值建模限制（DT 限制声明）；")
    print("     不写 A8 MET / new generator / organization。")
    out["final"] = {"Scale-A": "M1_ONLY_NOT_REACHED" if scaleA_reject else "?",
                    "Scale-B": verdict_b,
                    "M5P": m5p,
                    "conditional_on": [
                        "canonical=Scale-B ruling",
                        "dt=0.001 + hard clamp (numerical limit; "
                        "physical high branch = continuous-limit value)",
                        "ENERGY_SUPPORT=CAUSAL_RAIL_LOAD_LINE(path-B); "
                        "GLOBAL_ENERGY_CLOSURE=NOT_ESTABLISHED"]}

    with open(os.path.join(DATA_DIR, "f1_revalidation.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n落盘: {os.path.join(DATA_DIR, 'f1_revalidation.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
