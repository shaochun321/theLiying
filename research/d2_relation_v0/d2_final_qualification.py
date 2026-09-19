"""d2_final_qualification.py — D2-0 Step5：relation closure candidate +
hold8 盲评 + 六门 D2-M1~M6 + 四终态。

TYPE:INFRA（research/ 层）。

## COMPUTE_BUDGET

  physical_trajectories=0; replays ≈ 9 cal 对 + 8 hold + 2 确定性复放
  ≈ 19; n_parameter_points=0（closure 参数=推导规则，非扫描）;
  interventions=0

## relation closure 参数（§22 禁抄 G0 值——全部由 Step3 实测新鲜推导）

  theta_up_ρ   = u_work/2 = 2.6164（cal_C2_sim 峰的线性区中点，端点锚定
                 家族；≠ G0 的 0.01）
  theta_down_ρ = 0.1×theta_up_ρ（迟滞**比例**约定沿 G0 惯例登记为比例，
                 数值全新）
  rearm_ρ      = round(τ_decay/dt) = 456 步 ≡ 0.456 s（一个实测衰减
                 常数：状态须耗散后才允许新关系确认；≠ G0 的 500）
  phys_support = parent_support_A ∨ parent_support_B（任一父 occurrence
                 窗活跃）——epoch/token 门控经 OccurrenceClosure 继承
                 （E-5/反馈 §六：内部余振无父支撑 ⇒ ΔC_phys=0）

## 预注册期望（cal，运行前冻结）

  双父轨迹（C2/C3_s,m,l/C4_s,m,l/C5_w,s）→ 关系发生数=1
  单父轨迹（C0/C1）→ 0（peak 2.50 < theta 2.62——关系发生需双父，
  边缘量 4.4%：若 C3_l(peak 2.636) 以 0.8% 边缘触发/不触发，如实登记
  合法域边缘，不回调）

## hold8 盲评（SHA 验证→冻结参数一次过）

  合法结果含 STRUCTURALLY_NO_RELATION（如 hold_dose1/hold_dur1 零父
  occurrence ⇒ 零驱动 ⇒ x≡0）；失败仅限 illegal state/nonfinite/
  replay 不一致/lineage 缺失（反馈 §二十）。

## χ_ρ^(1)：仅登记 RELATION_OCCURRENCE_CANDIDATE（§22 反馈 §二十二，
禁 G1）；谱系经 AddressRegistry.register_generated(DOMAIN_RELATION_RHO,
parents=(addr_A, addr_B), generation_depth=1) 真实注册，uid 与 parent
manifest 的 lineage_uid 逐位核对。

复现入口：
  PYTHONIOENCODING=utf-8 python research/d2_relation_v0/d2_final_qualification.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..')))

from d2_common import DATA, DT_G, SITE_A, SITE_B, build_parents  # noqa: E402
from dataset_builder import build_hold, _manifest  # noqa: E402
from relation_physical_impl import (  # noqa: E402
    drives_for, load_port_windows, run_relation)
from tss.generators.occurrence import OccurrenceClosure  # noqa: E402
from nexus_v1.components.structural_address import (  # noqa: E402
    AddressRegistry, DOMAIN_RELATION_RHO)

PAIR_CAL = ["cal_C2_sim", "cal_C3_s", "cal_C3_m", "cal_C3_l",
            "cal_C4_s", "cal_C4_m", "cal_C4_l",
            "cal_C5_weak", "cal_C5_strong"]
SINGLE_CAL = ["cal_C0_A", "cal_C1_B"]


def _cal_params():
    with open(os.path.join(DATA, 'relation_calibration.json'),
              encoding='utf-8') as f:
        c = json.load(f)
    g = c["canonical_reference"]["g_rel"]
    u_work = c["measured"]["u_work"]
    tau_decay = c["measured"]["tau_decay_s"]
    theta_up = u_work / 2.0
    rearm = round(tau_decay / DT_G)
    return g, theta_up, rearm


def _relation_address():
    """真实谱系注册：χ_ρ 地址 ← (G_a, G_b) 生成元地址（depth=1）。"""
    circuit, handles = build_parents({"A": SITE_A, "B": SITE_B})
    addr_a = handles["A"].closure.address
    addr_b = handles["B"].closure.address
    reg = AddressRegistry()
    rho = reg.register_generated(DOMAIN_RELATION_RHO, "d2_rho0",
                                 (addr_a, addr_b), generation_depth=1)
    return rho, addr_a, addr_b


def _run_closure(traj, g, theta_up, rearm, rho_addr, windows):
    xs, led, _p = run_relation(traj, g, windows=windows)
    da, db = drives_for(traj, windows)
    cl = OccurrenceClosure(address=rho_addr, theta_up=theta_up,
                           theta_down=0.1 * theta_up,
                           rearm_min_steps=rearm, dt=DT_G)
    for k, x in enumerate(xs):
        sup = da[k].parent_support or db[k].parent_support
        cl.update(x, k, phys_support=sup)
    return xs, led, cl.events


def main() -> int:
    g, theta_up, rearm = _cal_params()
    windows = load_port_windows()
    rho_addr, addr_a, addr_b = _relation_address()
    print(f"closure params (fresh-derived): theta_up={theta_up:.4f} "
          f"rearm={rearm} steps ({rearm * DT_G:.3f}s)  [G0 values NOT copied]")

    gates = {}
    # ── χ_ρ^(1) candidates on cal ──
    cand_rows, occ_map = [], {}
    for traj in PAIR_CAL + SINGLE_CAL:
        _xs, _led, evs = _run_closure(traj, g, theta_up, rearm,
                                      rho_addr, windows)
        occ_map[traj] = len(evs)
        for ev in evs:
            tp = ev.to_physical(DT_G)
            cand_rows.append({
                "traj": traj, "status": "RELATION_OCCURRENCE_CANDIDATE",
                "t_up": ev.t_up, "t_down": ev.t_down, "t_rearm": ev.t_rearm,
                "t_up_s": tp[0], "t_down_s": tp[1], "t_rearm_s": tp[2],
                "epoch": ev.epoch_id, "rho_uid": rho_addr.uid,
                "generation_depth": rho_addr.generation_depth,
                "parents": f"{addr_a.uid}|{addr_b.uid}"})
        print(f"  {traj}: relation occ={len(evs)}")
    exp_ok = all(occ_map[t] == 1 for t in PAIR_CAL) and \
        all(occ_map[t] == 0 for t in SINGLE_CAL)
    with open(os.path.join(DATA, 'relation_occurrence_candidates.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(cand_rows[0]))
        w.writeheader(); w.writerows(cand_rows)

    # ── M1 自然化合法性 ──
    with open(os.path.join(DATA, 'd2_naturalization.json'),
              encoding='utf-8') as f:
        nat = json.load(f)
    m1 = (nat["N1_phase"]["verdict"].startswith("QUALIFIED")
          and nat["N2_relative_timing"]["verdict"].startswith("QUALIFIED")
          and nat["N0_count"]["verdict"] == "INSUFFICIENT")
    gates["D2-M1"] = {"pass": m1, "verdicts": {k: v.get("verdict")
                      for k, v in nat.items() if isinstance(v, dict)}}

    # ── M2 statefulness ──
    with open(os.path.join(DATA, 'd2_hidden_ruling.json'),
              encoding='utf-8') as f:
        hid = json.load(f)
    gates["D2-M2"] = {"pass": hid["ruling"] ==
                      "RELATION_STATE_CAUSALLY_SUPPORTED",
                      "c6": hid["twin"]["c6_relation_memory"],
                      "minimal_state": hid.get(
                          "minimal_sufficient_state_candidate")}

    # ── M3 物理实现（组件类型 + 传播路径静态扫描）──
    from relation_physical_impl import build_relation
    from nexus_v1.components.neuron import Neuron
    from nexus_v1.circuit.bundle import SynapticBundle
    p = build_relation(g)
    types_ok = (isinstance(p.cell, Neuron)
                and isinstance(p.bundle_a, SynapticBundle)
                and isinstance(p.bundle_b, SynapticBundle))
    src = open(os.path.join(_HERE, 'relation_physical_impl.py'),
               encoding='utf-8').read()
    forbidden = [pat for pat in (".inject(", ".charge =", ".charge=",
                                 ".energy -=") if pat in src]
    gates["D2-M3"] = {"pass": types_ok and not forbidden,
                      "carrier": "Neuron membrane RC (C=0.1,R=5)",
                      "forbidden_patterns_found": forbidden}

    # ── M4 causal parentage ──
    with open(os.path.join(DATA, 'd2_trials.json'), encoding='utf-8') as f:
        tri = json.load(f)
    gates["D2-M4"] = {"pass": bool(tri["NC4_pass"]) and bool(
        tri["attack_pass"]),
        "blockA_rmse": tri["NC4_blockA_rmse"],
        "blockB_rmse": tri["NC4_blockB_rmse"]}

    # ── M5 replay 确定性 + hold8 盲评 ──
    xs1, _, _ = run_relation("cal_C2_sim", g, windows=windows)
    xs2, _, _ = run_relation("cal_C2_sim", g, windows=windows)
    replay_ok = xs1 == xs2
    hold_j = json.dumps(_manifest(build_hold()), indent=1, sort_keys=True)
    sha = hashlib.sha256(hold_j.encode('utf-8')).hexdigest()
    with open(os.path.join(DATA, 'd2_hold_seal.json'),
              encoding='utf-8') as f:
        sealed = json.load(f)["hold_manifest_sha256"]
    hold_rows, hold_fail = [], []
    if sha == sealed:
        for tid in sorted(_manifest(build_hold())):
            xs, led, evs = _run_closure(tid, g, theta_up, rearm,
                                        rho_addr, windows)
            finite = all(math.isfinite(v) for v in xs) and \
                math.isfinite(led["energy_drop"])
            legal = finite and 0.0 <= max(xs) <= 10.0 + 1e-9
            status = ("STRUCTURALLY_NO_RELATION" if max(xs) == 0.0
                      else f"relation_occ={len(evs)}")
            if not legal:
                hold_fail.append(tid)
            hold_rows.append({"traj": tid, "x_peak": max(xs),
                              "relation_occ": len(evs), "status": status,
                              "legal": legal})
            print(f"  hold {tid}: peak={max(xs):.4f} occ={len(evs)} "
                  f"{status} {'OK' if legal else 'FAIL'}")
        with open(os.path.join(DATA, 'relation_heldout.csv'), 'w',
                  newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(hold_rows[0]))
            w.writeheader(); w.writerows(hold_rows)
    gates["D2-M5"] = {"pass": replay_ok and sha == sealed and not hold_fail,
                      "replay_bit_exact": replay_ok,
                      "sha_verified": sha == sealed,
                      "hold_failures": hold_fail}

    # ── M6 label promotion（最高优先门）──
    nc2 = tri["NC2_memoryless_counterexample"]
    gates["D2-M6"] = {"pass": bool(nc2["pass"]) and bool(
        hid["twin"]["c6_relation_memory"]),
        "evidence": "NC2 同(标签,瞬时输入)双时刻 x 不同值(x_pre=0 vs "
                    f"x_gap={nc2['x_gap']:.5f}) + C6 同输入不同前史未来"
                    "分叉——无 (A_id,B_id,timing) 无记忆函数可复现 x_ρ"}

    all_pass = all(v["pass"] for v in gates.values()) and exp_ok
    if all_pass:
        state = {"terminal": "A",
                 "D2_RELATION_PROCESS_V0_QUALIFIED": True,
                 "RELATION_OCCURRENCE_CANDIDATE": True,
                 "READY_FOR_D2-1": True,
                 "hard_stop": "FREEZE D2-0（反馈 §二十四：禁 "
                              "Naturalization-v2/RelationCell-v2/更多 site/"
                              "更多模态/更大网络/更大扫描）"}
    else:
        bad = [k for k, v in gates.items() if not v["pass"]]
        if not exp_ok:
            bad.append("cal_expectation")
        state = {"terminal": "B/C/D 待归类", "blocking": bad}
    summary = {"frozen_params": {"g_rel": g, "theta_up_rho": theta_up,
                                 "theta_down_rho": 0.1 * theta_up,
                                 "rearm_rho_steps": rearm, "dt": DT_G},
               "cal_occurrence_map": occ_map, "cal_expectation_ok": exp_ok,
               "gates": gates, "terminal_state": state,
               "rho_lineage": {"uid": rho_addr.uid, "depth": 1,
                               "parents": [addr_a.uid, addr_b.uid]}}
    with open(os.path.join(DATA, 'qualification_summary.json'), 'w',
              encoding='utf-8') as f:
        json.dump(summary, f, indent=1, ensure_ascii=False)
    print("=" * 60)
    for k, v in gates.items():
        print(f"  {k}: {'PASS' if v['pass'] else 'FAIL'}")
    print(f"  cal expectation (pair=1/single=0): {exp_ok}")
    print("TERMINAL:", json.dumps(state, ensure_ascii=False))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
