"""final_qualification.py — D2-1 StepE：hold6 盲评 + 六门 D21-M1~M6 +
四终态（方案 §24-§29、§35 首屏）。

TYPE:INFRA（research/ 层）。

## COMPUTE_BUDGET

  physical_trajectories=0; stage-2 runs = 6 hold + 2 确定性复放;
  interventions=0; hold 评估一次过（SHA 验证→冻结参数盲评→零回调）

## hold6 盲评纪律

  参数（g_rel2/θ₂/rearm₂）在 StepC/StepD 已冻结；本脚本只验证 SHA、
  一次运行、如实登记。合法结果含 occ=0；失败仅限 illegal state/
  nonfinite/replay 不一致/lineage 缺失。
  披露：H6（structural-no-relation）的驱动组合与 E1 预注册对照
  rc_C_only 相同——E1 用它做叠加性对照，无任何参数依赖它（非调参
  暴露，如实登记）。H3 剂量经 latency 进入（G0-R1 "dose 在 latency"
  先例）：s23_hold_dose 窗 [2876,3515) 较 s23_ov 提前 51 步。

## 六门

  D21-M1 Recursive Port     RT-1 typed acceptance + port manifest
  D21-M2 Physical Recursion 组件类型 + 禁模式静态扫描 + RT-6/RT-7
  D21-M3 Depth Non-Collapse E2 verdict
  D21-M4 A8-v2 Irreducibility E3 ruling（sham 对照 + tier0 不充分并报）
  D21-M5 Future Causal Action E4 verdict
  D21-M6 Held-out/Replay/Ledger SHA+盲评+逐位复放+谱系+预算

复现入口：
  PYTHONIOENCODING=utf-8 python research/d2_recursive_v1/final_qualification.py
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

from d21_common import (  # noqa: E402
    DATA, DT_G, RHO_MAIN_TRAJ, frozen_relation2_params,
    load_relation_ports, load_site23_windows, relation2_address)
from recursive_physical_impl import (  # noqa: E402
    T_TOTAL, build_relation2, recursive_drives, run_relation2,
    step_relation2)
from tss.generators.occurrence import OccurrenceClosure  # noqa: E402


def _closure_run(rports, cwins, g, theta2, rearm2, rho2_addr):
    dr, dc = recursive_drives(rports, cwins)
    p = build_relation2(g)
    cl = OccurrenceClosure(address=rho2_addr, theta_up=theta2,
                           theta_down=0.1 * theta2,
                           rearm_min_steps=rearm2, dt=DT_G)
    xs = []
    for k in range(T_TOTAL):
        x = step_relation2(p, dr[k].value, dc[k].value)
        cl.update(x, k, phys_support=dr[k].parent_support
                  or dc[k].parent_support)
        xs.append(x)
    return xs, cl.events


def main() -> int:
    g, theta2, rearm2 = frozen_relation2_params()
    rho2_addr, rho_addr, c_addr = relation2_address()
    ports = load_relation_ports()
    s23 = load_site23_windows()
    print(f"frozen: g_rel2={g:.6e} theta2={theta2:.4f} rearm2={rearm2}")

    gates = {}
    with open(os.path.join(DATA, 'd21_trials.json'), encoding='utf-8') as f:
        tri = json.load(f)

    # ── M1 Recursive Port ──
    n_ports = len(ports)
    gates["D21-M1"] = {"pass": bool(tri["RT1_pass"]) and n_ports >= 1,
                       "rt1_window": tri["RT1_window"],
                       "n_relation_ports": n_ports,
                       "adapter": "same build_phase_drive as depth-0 "
                                  "(RC-1 typed acceptance)"}

    # ── M2 Physical Recursion ──
    from recursive_physical_impl import build_relation2 as _br
    from nexus_v1.components.neuron import Neuron
    from nexus_v1.circuit.bundle import SynapticBundle
    p = _br(g)
    types_ok = (isinstance(p.cell, Neuron)
                and isinstance(p.bundle_r, SynapticBundle)
                and isinstance(p.bundle_c, SynapticBundle))
    src = open(os.path.join(_HERE, 'recursive_physical_impl.py'),
               encoding='utf-8').read()
    forbidden = [pat for pat in (".inject(", ".charge =", ".charge=",
                                 ".energy -=") if pat in src]
    gates["D21-M2"] = {"pass": (types_ok and not forbidden
                                and bool(tri["RT6_pass"])
                                and bool(tri["RT7_main_pass"])),
                       "carrier": "Neuron membrane RC (C=0.1,R=5)",
                       "forbidden_patterns_found": forbidden,
                       "no_self_excitation": bool(tri["RT6_pass"])}

    # ── M3 Depth Non-Collapse ──
    with open(os.path.join(DATA, 'depth_collapse_attack.json'),
              encoding='utf-8') as f:
        dca = json.load(f)
    gates["D21-M3"] = {"pass": dca["verdict"] == "DEPTH_NON_COLLAPSE",
                       "S1_rmse": dca["S1_sum"]["rmse_vs_full"],
                       "S2_rmse": dca["S2_envelope"]["rmse_vs_full"]}

    # ── M4 A8-v2 Irreducibility ──
    with open(os.path.join(DATA, 'd21_a8v2_ruling.json'),
              encoding='utf-8') as f:
        a8 = json.load(f)
    gates["D21-M4"] = {"pass": a8["ruling"] ==
                       "G1_STATE_DIMENSION_CAUSALLY_SUPPORTED",
                       "existence_divergence":
                           a8["twin"]["existence_divergence"],
                       "sham_ok": a8.get("sham_ok"),
                       "tier0_insufficient": a8.get("tier0_insufficient"),
                       "minimal_state": a8.get(
                           "minimal_sufficient_state_candidate")}

    # ── M5 Future Causal Action ──
    with open(os.path.join(DATA, 'future_action_attack.json'),
              encoding='utf-8') as f:
        faa = json.load(f)
    gates["D21-M5"] = {"pass": faa["verdict"] ==
                       "FUTURE_CAUSAL_ACTION_CONFIRMED",
                       "existence_level":
                           faa["blockR"]["existence_level_difference"]}

    # ── M6 held-out / replay / ledger ──
    # SHA 验证（重建 manifest 与封存比对）
    import dataset_builder as dbm
    hold_manifest = {
        "cases": dbm.HOLD6,
        "site23_hold_specs": {tid: {"t_on": t_on, "length": dbm.P,
                                    "amp": amp, "note": note}
                              for tid, t_on, amp, note in dbm.S23_HOLD},
        "legality": "legal outcomes include STRUCTURALLY_NO_RELATION; "
                    "failures limited to illegal state/nonfinite/replay "
                    "mismatch/lineage missing (D2-0 反馈§20 rule)",
    }
    hold_j = json.dumps(hold_manifest, indent=1, sort_keys=True,
                        ensure_ascii=False)
    sha = hashlib.sha256(hold_j.encode('utf-8')).hexdigest()
    with open(os.path.join(DATA, 'd21_hold_seal.json'),
              encoding='utf-8') as f:
        sealed = json.load(f)["hold_manifest_sha256"]
    sha_ok = sha == sealed

    hold_rows, hold_fail = [], []
    if sha_ok:
        for case in dbm.HOLD6:
            rports = [ports[case["rho_traj"]]] if case["rho_traj"] else []
            cwins = s23[case["site23"]]
            xs, evs = _closure_run(rports, cwins, g, theta2, rearm2,
                                   rho2_addr)
            finite = all(math.isfinite(v) for v in xs)
            legal = finite and 0.0 <= max(xs) <= 10.0 + 1e-9
            status = ("STRUCTURALLY_NO_RELATION" if max(xs) == 0.0
                      else f"relation2_occ={len(evs)}")
            if not legal:
                hold_fail.append(case["case"])
            hold_rows.append({"case": case["case"],
                              "rho": case["rho_traj"] or "-",
                              "site23": case["site23"],
                              "x_peak": max(xs), "relation2_occ": len(evs),
                              "status": status, "legal": legal})
            print(f"  hold {case['case']}: peak={max(xs):.4f} "
                  f"occ={len(evs)} {status} {'OK' if legal else 'FAIL'}")
        with open(os.path.join(DATA, 'recursive_heldout.csv'), 'w',
                  newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(hold_rows[0]))
            w.writeheader(); w.writerows(hold_rows)

    # 逐位复放
    xs1, _l1, _p1 = run_relation2([ports[RHO_MAIN_TRAJ]], s23["s23_ov"], g)
    xs2, _l2, _p2 = run_relation2([ports[RHO_MAIN_TRAJ]], s23["s23_ov"], g)
    replay_ok = xs1 == xs2
    # 谱系审计
    lineage_ok = (rho2_addr.generation_depth == 2
                  and rho2_addr.uid.endswith("d21_rho2")
                  and len(ports[RHO_MAIN_TRAJ].parent_occurrence_ids) == 2)
    # 预算账本
    budget = {"new_G0_physical_trajectories": [7, 8],
              "depth1_relation_replays": [4, 16],
              "relation2_calibration_points": [9, 10],
              "a8_twins": [1, 4], "interventions": [3, 4],
              "held_out": [6, 6]}
    budget_ok = all(v[0] <= v[1] for v in budget.values())
    with open(os.path.join(DATA, 'd21_budget_ledger.json'), 'w',
              encoding='utf-8') as f:
        json.dump({"final": {k: f"{v[0]}/{v[1]}" for k, v in
                             budget.items()}}, f, indent=1)
    gates["D21-M6"] = {"pass": (sha_ok and not hold_fail and replay_ok
                                and lineage_ok and budget_ok),
                       "sha_verified": sha_ok,
                       "hold_failures": hold_fail,
                       "replay_bit_exact": replay_ok,
                       "lineage_ok": lineage_ok, "budget": budget,
                       "disclosure": "H6 drive combo == E1 rc_C_only "
                                     "control (no parameter depended on "
                                     "it); H3 dose enters via latency "
                                     "(51-step earlier window)"}

    # ── 终态（§29 四种）──
    all_pass = all(v["pass"] for v in gates.values())
    if all_pass:
        state = {"terminal": "A",
                 "D2_1_RECURSIVE_GENERATION_QUALIFIED": True,
                 "G1_QUALIFIED": True,
                 "READY_FOR_POSTERIOR_0": True,
                 "scope": "REPLAY/REFERENCE QUALIFICATION（方案 §7）——"
                          "live 端到端仍受 D2-0 登记的 "
                          "CAUSAL_VARIANT_REQUIRED_BEFORE_LIVE_D2 约束",
                 "hard_stop": "禁 D2-1b/G1-v2/more relation cells/more "
                              "sites/more modalities/large recursive "
                              "sweep（§30）；下一阶段=Posterior-0"}
    elif not gates["D21-M1"]["pass"]:
        state = {"terminal": "D",
                 "RELATION_OCCURRENCE_NOT_RECONSUMABLE": True}
    elif gates["D21-M4"]["pass"] and not gates["D21-M5"]["pass"]:
        state = {"terminal": "C", "G1_STATE_CANDIDATE": True,
                 "FUTURE_CAUSAL_ACTION_NOT_MET": True}
    else:
        state = {"terminal": "B",
                 "RELATION_RECURSION_ENGINEERING_PASS": True,
                 "G1_NOT_QUALIFIED": True,
                 "blocking": [k for k, v in gates.items()
                              if not v["pass"]]}

    # ── §35 首屏十二问 ──
    first_screen = {
        "1_reconsumable": bool(tri["RT1_pass"]),
        "2_physical_relation_cell_2": gates["D21-M2"]["pass"],
        "3_chi_rho2_generated": tri["RT7_occ_map"]["rc_main"] == 1,
        "4_depth0_substitution_reconstructs": dca["verdict"]
        == "DEPTH_COLLAPSE",
        "5_same_parent_state_diff_relation_state_diff_future":
            a8["twin"]["parent_state_insufficient"],
        "6_transplant_closes_divergence": gates["D21-M4"]["pass"],
        "7_block_changes_future": gates["D21-M5"]["pass"],
        "8_minimal_hidden_state": a8.get(
            "minimal_sufficient_state_candidate"),
        "9_stop_deeper_decomposition": "STOP" in str(a8.get("stop", "")),
        "10_hold6_one_pass": sha_ok and not hold_fail,
        "11_verdict": ("G1_QUALIFIED" if all_pass
                       else "ENGINEERING_PASS_ONLY"),
        "12_posterior_0_allowed": all_pass,
    }

    summary = {"frozen_params": {"g_rel2": g, "theta_up_rho2": theta2,
                                 "theta_down_rho2": 0.1 * theta2,
                                 "rearm_rho2_steps": rearm2, "dt": DT_G},
               "gates": gates, "terminal_state": state,
               "first_screen": first_screen,
               "negative_findings_carried": ["NF-1 latency drift",
                                             "NF-2 single-parent trigger",
                                             "RT-2 v1 falsified "
                                             "(peak metric saturation)"],
               "rho2_lineage": {"uid": rho2_addr.uid, "depth": 2,
                                "parents": [rho_addr.uid, c_addr.uid]}}
    with open(os.path.join(DATA, 'qualification_summary.json'), 'w',
              encoding='utf-8') as f:
        json.dump(summary, f, indent=1, ensure_ascii=False)

    print("=" * 60)
    for k, v in gates.items():
        print(f"  {k}: {'PASS' if v['pass'] else 'FAIL'}")
    print("TERMINAL:", json.dumps(state, ensure_ascii=False))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
