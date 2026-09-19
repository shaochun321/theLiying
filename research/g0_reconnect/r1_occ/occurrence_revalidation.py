"""occurrence_revalidation.py — G0-R1 Step3：χ 全重验 + closure 阈值/rearm
真实秒制重标 + 三边界合同验证 + dose 结构检查（cal 集专用）。

TYPE:INFRA（research/ 层；production READ_ONLY——closure 是只读观察者，
阈值扫描在**录制轨迹上离线重放**完成，物理运行每 episode 只跑一次）。

账本偏离说明（exp-script 规范 vs 本脚本）：ν探针/Noether 账本挂在
`VariantCircuit.step()` 主循环上；本实验用 `handle.tick()` 手动驱动
（DEG-021 互锁禁止与 circuit.step() 混用），organism 主循环不运行，
故审计面按 R-2 裁定（2026-09-19）= 研究区自建账本：本脚本逐 episode
记录 11 个 G0 神经元能量和（energy_ledger.csv）+ 输入功率代理 Σ|u|。

## 预注册（运行前冻结，E-6 纪律——不得事后挑统计量/改期望）

统计量（occurrence 层验收面，§6/§10）：
  count / latency(t_up−t_support_on) / duration(t_down−t_up) /
  rearm_gap(t_rearm−t_down) / collector_peak / L1_sat_frac / energy_drop

阈值/rearm 扫描网格（离线重放，g=g_v2 固定——g 属 R1-2 已标定，本脚本
不回调 g）：
  theta_up ∈ {0.005, 0.01, 0.02, 0.05, 0.1}；theta_down = 0.1·theta_up
  （迟滞比固定为现行 v1 比例，登记不另扫）；rearm ∈ {0,200,500,1000,2000}
  （EXP-P2A1b3 同网格，v2 输入下重测）。

合法域规则（逐类期望，先声明）：
  K1/K2/K3/K4 → 完成 occurrence 数 == 1
  K8          → 完成 occurrence 数 == 2（相邻双脉冲）
  K7 sustain  → 必须发生 trigger（t_up 存在）；完成数 ∈ {0,1}
               （持续输入下 exit 可能落在 episode 外——合法，如实登记）
  K6 weak     → ∈ {0,1}（非鉴别类）；K5 twin → ∈ {0,1}（Step4 专用）
  合法域 = 使全部 cal episode 满足期望的 (theta_up, rearm) 组合集。

canonical 规则（连续性锚定，非最优搜索）：合法域内取与 v1 参考点
  (theta_up=0.01, rearm=500) 距离最近者（字典序：|log10 θ 比|, |Δrearm|）。

三边界合同（§7，canonical 参数，cal_K1a）：
  trigger 在物理支撑开始之后；sustain 有限且 >1 子步；exit 由状态机
  在 episode 运行中产生（§7 原文："输入结束**或内部动力学退出**后离开
  发生态"——两种 exit 模式都合法，登记 exit_mode 分类但不作 pass/fail）；
  rearm_gap == rearm_min_steps；禁止用 episode 标签指定时刻
  （全部时刻由状态机在真实信号上产生）。
  检查规格修订（2026-09-19 首轮实测后）：初版把 exit 错编码为
  "t_down ≥ 支撑衰减"（比合同更严）——collector 对 onset 瞬态响应后
  经内部动力学在支撑仍在场时退出（实测 t_down=1.697s < 支撑末端）
  是 §7 明文允许的第二种 exit 模式。原始测量数据保留在
  closure_timing.csv，修订仅对齐检查到合同原文。

dose 结构（§10）：K1 场景 power×{0.5,1.0,2.0}（A1<A2<A3，cal 侧附加，
  不动 hold），canonical 参数下上述统计量至少一维保持可测差异
  （确定性系统：相对差 >1% 计可测）；不要求 count 单调。

复现入口：
  PYTHONIOENCODING=utf-8 python research/g0_reconnect/r1_occ/occurrence_revalidation.py
"""
from __future__ import annotations

import csv
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', 'r0')))
sys.path.insert(0, _HERE)

from g0r0_common import fresh_g0  # noqa: E402
from r1_calibration import _rate_substeps, U_CLAMP_ONSET, DT_G  # noqa: E402
from r1_dataset import build_sets, _spec  # noqa: E402
from world_v2_core import SourceSpec  # noqa: E402
from tss.generators.occurrence import OccurrenceClosure  # noqa: E402

DATA = os.path.join(_HERE, 'data')

# 网格修订（首轮实测 2026-09-19：原 5×5 网格 25/25 全 LEGAL=不鉴别，
# TSS-2b"CG-0 资格不鉴别"教训重演——§8 要求 failure boundary，必须扩到
# 失败沿：theta_up 向 collector Zener 顶棚(~1.0)扩、rearm 向 K8 相邻
# 脉冲间隔(30s=30000 步)扩。这是定位边界，不是搜索更好参数。）
THETA_GRID = [0.005, 0.01, 0.02, 0.05, 0.1, 0.5, 0.9, 1.1]
REARM_GRID = [0, 200, 500, 1000, 2000, 10000, 25000, 40000]
V1_REF = (0.01, 500)

_EXPECT = {  # 预注册逐类期望（见 docstring）
    "K1": {1}, "K2": {1}, "K3": {1}, "K4": {1},
    "K5": {0, 1}, "K6": {0, 1}, "K7": {0, 1}, "K8": {2},
}


def _g_v2() -> float:
    with open(os.path.join(DATA, 'r1_calibration.json')) as f:
        return json.load(f)["canonical_reference"]["g_v2"]


def _run_episode(spec, g):
    """物理运行一次（g=g_v2, S0+B0），返回录制轨迹与能量账本行。"""
    rates = _rate_substeps(spec)
    h = fresh_g0()
    neurons = [h.l1, h.hc, *h.ensemble, h.collector]
    e0 = sum(n.energy for n in neurons)
    col, sup, uabs = [], [], []
    sat = 0
    for k, r in enumerate(rates):
        u = g * r
        h.tick(u, DT_G, k)
        col.append(h.collector.pre_trace)
        sup.append(h.l1.activation > 0.0)
        uabs.append(abs(u))
        if abs(u) > U_CLAMP_ONSET:
            sat += 1
    e1 = sum(n.energy for n in neurons)
    ledger = {"episode": spec.episode_id, "e_start": e0, "e_end": e1,
              "energy_drop": e0 - e1, "sum_abs_u": sum(uabs),
              "l1_sat_frac": sat / max(len(rates), 1),
              "col_peak": max(col) if col else 0.0}
    return col, sup, ledger


def _replay_closure(col, sup, theta_up, rearm):
    """录制轨迹上的离线 closure 重放（观察者语义，无物理副作用）。"""
    if not hasattr(_replay_closure, "_addr"):
        _replay_closure._addr = fresh_g0().closure.address
    h_addr = _replay_closure._addr
    cl = OccurrenceClosure(address=h_addr, theta_up=theta_up,
                           theta_down=0.1 * theta_up,
                           rearm_min_steps=rearm, dt=DT_G)
    triggered = False
    for k, (v, s) in enumerate(zip(col, sup)):
        cl.update(v, k, phys_support=s)
        if cl.is_active:
            triggered = True
    return cl.events, triggered


def main() -> int:
    g = _g_v2()
    print("=" * 60)
    print(f"G0-R1 Step3 — occurrence revalidation (g_v2={g:.6e}, S0+B0)")
    print("=" * 60)
    cal, _hold = build_sets()  # hold 封存不触（E-8）
    _replay_closure._addr = fresh_g0().closure.address

    # ── Phase A：cal 16 episodes 物理运行 + 录制 ──
    traces, ledgers = {}, []
    for eid, spec in sorted(cal.items()):
        col, sup, led = _run_episode(spec, g)
        traces[eid] = (col, sup)
        ledgers.append(led)
        print(f"  [A] {eid}: col_peak={led['col_peak']:.4f} "
              f"sat={led['l1_sat_frac']:.3f} dE={led['energy_drop']:.4f}")

    # ── Phase B：阈值/rearm 离线扫描 ──
    trial_rows, legal = [], []
    for th in THETA_GRID:
        for rm in REARM_GRID:
            ok_all = True
            for eid, (col, sup) in sorted(traces.items()):
                cls = eid.split("_")[1][:2]
                evs, trig = _replay_closure(col, sup, th, rm)
                n = len(evs)
                exp = _EXPECT[cls]
                ok = n in exp and (cls != "K7" or trig)
                ok_all = ok_all and ok
                trial_rows.append({"episode": eid, "theta_up": th,
                                   "rearm": rm, "occ": n,
                                   "triggered": trig, "ok": ok})
            if ok_all:
                legal.append((th, rm))
            print(f"  [B] theta_up={th} rearm={rm}: "
                  f"{'LEGAL' if ok_all else 'out'}")

    if legal:
        can = min(legal, key=lambda p: (abs(__import__('math').log10(
            p[0] / V1_REF[0])), abs(p[1] - V1_REF[1])))
    else:
        can = None
    print(f"  legal combos: {len(legal)}/{len(THETA_GRID) * len(REARM_GRID)}; "
          f"canonical={can} (v1 连续性锚定规则)")

    # ── Phase C：三边界合同验证（canonical, cal_K1a）──
    contract = {}
    if can:
        th, rm = can
        col, sup = traces["cal_K1a"]
        evs, _ = _replay_closure(col, sup, th, rm)
        first_sup = next((i for i, s in enumerate(sup) if s), None)
        last_sup = max((i for i, s in enumerate(sup) if s), default=None)
        if evs and first_sup is not None:
            ev = evs[0]
            contract = {
                "trigger_after_support_on": ev.t_up >= first_sup,
                "latency_steps": ev.t_up - first_sup,
                "sustain_finite_gt1": 1 < (ev.t_down - ev.t_up) < len(col),
                "duration_steps": ev.t_down - ev.t_up,
                # §7 exit：状态机在 episode 内自行退出（两种模式均合法）
                "exit_by_state_machine": ev.t_down < len(col) - 1,
                "exit_mode": ("input_end" if ev.t_down >= last_sup
                              else "internal_dynamics"),
                "rearm_gap_eq_rearm_min": (ev.t_rearm - ev.t_down) == rm,
                "t_phys_s": ev.to_physical(DT_G),
            }
        contract["all_pass"] = all(v for k, v in contract.items()
                                   if isinstance(v, bool))
        print(f"  [C] contract: {contract}")

    # ── Phase D：dose 结构（K1 power×{0.5,1.0,2.0}）──
    dose_rows = []
    if can:
        th, rm = can
        for tag, pw in [("A1", 0.5), ("A2", 1.0), ("A3", 2.0)]:
            spec = _spec(f"dose_{tag}", sources=[SourceSpec(0, 20.0, pw, 0)])
            col, sup, led = _run_episode(spec, g)
            evs, trig = _replay_closure(col, sup, th, rm)
            first_sup = next((i for i, s in enumerate(sup) if s), 0)
            row = {"dose": tag, "power": pw, "occ": len(evs),
                   "latency": (evs[0].t_up - first_sup) if evs else None,
                   "duration": (evs[0].t_down - evs[0].t_up) if evs else None,
                   "col_peak": led["col_peak"],
                   "l1_sat_frac": led["l1_sat_frac"],
                   "energy_drop": led["energy_drop"],
                   "sum_abs_u": led["sum_abs_u"]}
            dose_rows.append(row)
            print(f"  [D] {tag} power={pw}: {row}")

    def _distinct(key):
        vals = [r[key] for r in dose_rows if r[key] is not None]
        if len(vals) < 3 or 0.0 in vals[:1]:
            return False
        return all(abs(a - b) / max(abs(a), abs(b), 1e-12) > 0.01
                   for a, b in zip(vals, vals[1:]))
    dose_dims = {k: _distinct(k) for k in
                 ("latency", "duration", "col_peak", "l1_sat_frac",
                  "energy_drop", "sum_abs_u")}
    dose_pass = any(dose_dims.values())

    # ── 输出 ──
    with open(os.path.join(DATA, 'occurrence_trials.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(trial_rows[0]))
        w.writeheader(); w.writerows(trial_rows)
    with open(os.path.join(DATA, 'energy_ledger.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ledgers[0]))
        w.writeheader(); w.writerows(ledgers)
    with open(os.path.join(DATA, 'dose_structure.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(dose_rows[0]))
        w.writeheader(); w.writerows(dose_rows)
    timing = []
    if can:
        th, rm = can
        for eid, (col, sup) in sorted(traces.items()):
            for ev in _replay_closure(col, sup, th, rm)[0]:
                tp = ev.to_physical(DT_G)
                timing.append({"episode": eid, "t_up": ev.t_up,
                               "t_down": ev.t_down, "t_rearm": ev.t_rearm,
                               "t_up_s": tp[0], "t_down_s": tp[1],
                               "t_rearm_s": tp[2], "epoch": ev.epoch_id})
        with open(os.path.join(DATA, 'closure_timing.csv'), 'w',
                  newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(timing[0]))
            w.writeheader(); w.writerows(timing)

    summary = {
        "g_v2_used": g, "grid": {"theta_up": THETA_GRID,
                                 "rearm": REARM_GRID},
        "legal_combos": legal, "canonical": can,
        "canonical_rule": "closest to v1 (0.01,500) in legal region — "
                          "continuity anchor, NOT optimum",
        "contract_K1a": {k: (list(v) if isinstance(v, tuple) else v)
                         for k, v in contract.items()},
        "dose_dims_distinct": dose_dims, "dose_pass": dose_pass,
        "params_五元组": {
            "theta_up": {"physical_meaning": "collector pre_trace 触发阈",
                         "legal_region": sorted({t for t, _ in legal}),
                         "failure_boundary": "网格外沿(见 trials.csv)",
                         "canonical": can[0] if can else None,
                         "provenance": "本脚本预注册期望+cal16 离线重放"},
            "rearm": {"physical_meaning": "退出后重新武装最小间隔(步)",
                      "legal_region": sorted({r for _, r in legal}),
                      "failure_boundary": "网格外沿(见 trials.csv)",
                      "canonical": can[1] if can else None,
                      "provenance": "EXP-P2A1b3 同网格 v2 输入重测"},
        },
    }
    with open(os.path.join(DATA, 'r1_revalidation.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=1, ensure_ascii=False)

    ok = bool(legal) and can is not None and \
        contract.get("all_pass", False) and dose_pass
    print("=" * 60)
    print(f"RESULT: {'PASS' if ok else 'FAIL'}  canonical={can} "
          f"contract={contract.get('all_pass')} dose={dose_pass}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
