"""dataset_builder.py — D2-1 StepB：RelationOccurrencePortV1 manifest +
relation track 重放重建缓存 + 新 site23 轨迹 + hold6 封存。

TYPE:INFRA（research/ 层；production READ_ONLY）。

## COMPUTE_BUDGET（方案 §22，运行前登记）

  new G0 physical trajectories = 7（site23：cal4+far_b 补充 + hold2）≤ 8 ✓
  depth-1 relation replays     = 4（重建 cal_C3_m/C2_sim/C5_weak/C5_strong）
                                 ≤ 16（余 12 留后续步骤）
  relation-2 calibration points = 0（StepC 另计）
  A8 twins / interventions      = 0

脚本幂等：IMMUTABLE 缓存已存在的轨迹/relation track 直接跳过复用既有
manifest 行——不重跑物理、不覆盖缓存（补充 s23_far_b 时的最小增量路径）。

## site23 轨迹编排（相对主 ρ_a 窗 [2617,3971) 的时序覆盖）

  site23 锚点（D2-0 attack 实测）：pulse t_on→t_up 潜伏 ≈521 步，
  占用窗长 [t_up,t_rearm) ≈639 步。脉冲长 600/幅值 0.03 沿 D2-0 cal 约定。

  cal（StepC 标定 + StepD E1 只许消费这些 + D2-0 既有 atk 窗）：
    s23_ov    t_on=2400 → C=[2927,3566)  中心重叠（标定锚）
    s23_lead  t_on=1500 → C=[2022,2661)  前沿轻接触
    s23_lag   t_on=3600 → C=[4159,4798)  ρ 窗后（间隙 188 < τ_decay）
    s23_far   t_on=5000 → **零 occurrence（登记负结果 NF-1）**
    s23_far_b t_on=4000 → 远距（间隙 > τ_decay=456 步，替代 far 角色）
  hold2（封存后不得用于任何调参）：
    s23_hold_timing  t_on=3000 → C=[3542,4181)  未见相对时序（跨 ρ 窗尾）
    s23_hold_dose    t_on=2400, amp=0.04        未见剂量（D2-0 hold_dose2
                     先例：0.04 在 L1 线性域内且可触发）

## NF-1 负结果（首轮实测，如实登记，非 bug）

  换能潜伏期随起搏时刻单调漂移：t_on 1000→521 步 / 2400→527 / 3000→542 /
  3600→559 / 5000→637（VariantCircuit 代谢动态使运行点随空转时间漂移）。
  t_on=5000 时 collector 越阈（>0.01）首达 k=5637，晚于支撑窗（脉冲
  [5000,5600)+L1 尾）关闭 ⇒ 无父支撑 ⇒ ΔC_phys=0 门拒绝确认 ⇒ 零
  occurrence——**门按设计工作**；s23_far 缓存保留为该负结果证据。

## hold6 评估集（方案 §24 六项逐一覆盖，先 SHA 后运行零回调）

  H1 未见 relation duration   ρ(cal_C2_sim)   + s23_ov
  H2 未见 relative timing     ρ_a(cal_C3_m)   + s23_hold_timing
  H3 site23 dose variant      ρ_a             + s23_hold_dose
  H4 weak relation occ        ρ(cal_C5_weak)  + s23_ov
  H5 stronger relation occ    ρ(cal_C5_strong)+ s23_ov
  H6 structural-no-relation   无 ρ（R 通道全零）+ s23_ov
  合法结果含 STRUCTURALLY_NO_RELATION；失败仅限 illegal state/nonfinite/
  replay 不一致/lineage 缺失（D2-0 反馈 §20 规则沿用）。

## 重建 = 逐位核对（非重标定）

  4 条 relation track 以 D2-0 冻结参数重放，闭合边界与
  relation_occurrence_candidates.csv 冻结值逐位比对；任何不一致 =
  阻断性失败（不回调、不重跑，直接报告）。

复现入口：
  PYTHONIOENCODING=utf-8 python research/d2_recursive_v1/dataset_builder.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from d21_common import (  # noqa: E402
    DATA, REBUILD_TRAJS, REL_TRACES, RHO_MAIN_TRAJ, S23_TRACES,
    TYPED_PROVENANCE, frozen_candidates, frozen_relation_params,
    parent_instance_ids, rebuild_relation_track, relation_address,
    write_immutable)
from d2_common import DT_G, Pulse, TrajSpec, run_trajectory  # noqa: E402
from relation_physical_impl import load_port_windows  # noqa: E402
from tss.adapters.occurrence_port_v2 import from_occurrence  # noqa: E402

T = 8000
P = 600

S23_CAL = [
    ("s23_ov", 2400, 0.03, "中心重叠（StepC 标定锚）"),
    ("s23_lead", 1500, 0.03, "前沿轻接触"),
    ("s23_lag", 3600, 0.03, "ρ 窗后间隙"),
    ("s23_far", 5000, 0.03, "NF-1 负结果证据（零 occurrence，见 docstring）"),
    ("s23_far_b", 4000, 0.03, "远距负对照素材（间隙>τ_decay）"),
]
# NF-1：预期零 occurrence 的轨迹（负结果登记，不计入 cal 消费面）
EXPECT_NO_OCC = {"s23_far"}
S23_HOLD = [
    ("s23_hold_timing", 3000, 0.03, "未见相对时序（跨 ρ 窗尾）"),
    ("s23_hold_dose", 2400, 0.04, "未见剂量（hold_dose2 先例域内）"),
]

HOLD6 = [
    {"case": "H1_unseen_rho_duration", "rho_traj": "cal_C2_sim",
     "site23": "s23_ov"},
    {"case": "H2_unseen_rel_timing", "rho_traj": RHO_MAIN_TRAJ,
     "site23": "s23_hold_timing"},
    {"case": "H3_site23_dose", "rho_traj": RHO_MAIN_TRAJ,
     "site23": "s23_hold_dose"},
    {"case": "H4_weak_rho", "rho_traj": "cal_C5_weak", "site23": "s23_ov"},
    {"case": "H5_strong_rho", "rho_traj": "cal_C5_strong",
     "site23": "s23_ov"},
    {"case": "H6_structural_no_relation", "rho_traj": None,
     "site23": "s23_ov"},
]


def _s23_spec(tid, t_on, amp, note):
    return TrajSpec(tid=tid, t_total=T,
                    pulses={"C": (Pulse(t_on, P, amp),)}, note=note)


def main() -> int:
    os.makedirs(DATA, exist_ok=True)
    n_traj = len(S23_CAL) + len(S23_HOLD)
    assert n_traj <= 8, "COMPUTE_BUDGET 超限（site23 轨迹 ≤8）"
    assert len(REBUILD_TRAJS) <= 16, "COMPUTE_BUDGET 超限（重放 ≤16）"

    # ── 1. hold6 封存（先 SHA 后生成/运行，零回调）──
    hold_manifest = {
        "cases": HOLD6,
        "site23_hold_specs": {tid: {"t_on": t_on, "length": P, "amp": amp,
                                    "note": note}
                              for tid, t_on, amp, note in
                              [(t, o, a, n) for t, o, a, n in S23_HOLD]},
        "legality": "legal outcomes include STRUCTURALLY_NO_RELATION; "
                    "failures limited to illegal state/nonfinite/replay "
                    "mismatch/lineage missing (D2-0 反馈§20 rule)",
    }
    hold_j = json.dumps(hold_manifest, indent=1, sort_keys=True,
                        ensure_ascii=False)
    sha = hashlib.sha256(hold_j.encode('utf-8')).hexdigest()
    with open(os.path.join(DATA, 'd21_hold_manifest.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        f.write(hold_j)
    with open(os.path.join(DATA, 'd21_hold_seal.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        json.dump({"hold_manifest_sha256": sha, "sealed": "2026-09-21",
                   "discipline": "RelationCell_2/adapter params MUST NOT "
                                 "be tuned from hold cases; hold exposure "
                                 "=> FAIL, no re-run"}, f, indent=1)

    # ── 2. 新 site23 物理轨迹（fresh circuit each，production 只运行；
    #        幂等：缓存已存在 → 跳过物理运行，复用既有 manifest 行）──
    s23_manifest = os.path.join(DATA, 'site23_occurrence_manifest.csv')
    existing_rows = []
    if os.path.exists(s23_manifest):
        with open(s23_manifest, newline='', encoding='utf-8') as f:
            existing_rows = list(csv.DictReader(f))
    s23_rows, n_new_traj = [], 0
    for tid, t_on, amp, note in S23_CAL + S23_HOLD:
        if os.path.exists(os.path.join(S23_TRACES, f"{tid}.csv")):
            kept = [r for r in existing_rows if r["traj"] == tid]
            s23_rows.extend(kept)
            print(f"  {tid}: cached (occ={len(kept)})  ({note})")
            continue
        spec = _s23_spec(tid, t_on, amp, note)
        rows, occs, _h = run_trajectory(spec)
        n_new_traj += 1
        path = write_immutable(S23_TRACES, tid, rows)
        ref = os.path.relpath(path, os.path.abspath(
            os.path.join(_HERE, '..', '..'))).replace(os.sep, '/')
        for ev in occs.get("C", []):
            port = from_occurrence(ev, DT_G, raw_track_ref=ref,
                                   typed_input_ports=("U_dotT",))
            s23_rows.append({
                "traj": tid, "parent": "C",
                "occurrence_id": port.occurrence_id,
                "lineage_uid": port.lineage_uid,
                "t_up": port.t_up, "t_down": port.t_down,
                "t_rearm": port.t_rearm,
                "t_up_s": port.t_up_s, "t_down_s": port.t_down_s,
                "t_rearm_s": port.t_rearm_s,
                "raw_track_ref": port.raw_track_ref})
        got = {k: len(v) for k, v in occs.items()}
        print(f"  {tid}: occ={got}  ({note})")
    with open(s23_manifest, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(s23_rows[0]))
        w.writeheader(); w.writerows(s23_rows)

    # ── 3. relation track 重放重建 + 逐位核对 + port manifest ──
    g, theta_up, rearm = frozen_relation_params()
    print(f"\nfrozen D2-0 params: g_rel={g} theta_up={theta_up:.4f} "
          f"rearm={rearm} (read-only, no recalibration)")
    rel_manifest = os.path.join(DATA, 'relation_occurrence_manifest.csv')
    rel_ledger = os.path.join(DATA, 'relation_rebuild_ledger.csv')
    old_ports = {}
    old_ledgers = {}
    if os.path.exists(rel_manifest):
        with open(rel_manifest, newline='', encoding='utf-8') as f:
            old_ports = {r["traj"]: r for r in csv.DictReader(f)}
    if os.path.exists(rel_ledger):
        with open(rel_ledger, newline='', encoding='utf-8') as f:
            old_ledgers = {r["traj"]: r for r in csv.DictReader(f)}
    rho_addr = relation_address()
    windows = load_port_windows()
    cands = frozen_candidates()
    port_rows, ledgers, mismatch, n_replays = [], [], [], 0
    for traj in REBUILD_TRAJS:
        if (traj in old_ports and traj in old_ledgers
                and os.path.exists(os.path.join(REL_TRACES, f"{traj}.csv"))):
            port_rows.append(old_ports[traj])
            ledgers.append(old_ledgers[traj])
            print(f"  {traj}: cached (port manifest reused)")
            continue
        rows, events, led = rebuild_relation_track(
            traj, g, theta_up, rearm, rho_addr, windows)
        n_replays += 1
        c = cands[traj]
        ok = (len(events) == 1
              and events[0].t_up == int(c["t_up"])
              and events[0].t_down == int(c["t_down"])
              and events[0].t_rearm == int(c["t_rearm"])
              and events[0].epoch_id == int(c["epoch"])
              and rho_addr.uid == c["rho_uid"])
        if not ok:
            mismatch.append(traj)
            print(f"  {traj}: REBUILD MISMATCH — frozen "
                  f"({c['t_up']},{c['t_down']},{c['t_rearm']}) vs "
                  f"{[(e.t_up, e.t_down, e.t_rearm) for e in events]}")
            continue
        path = write_immutable(REL_TRACES, traj, rows)
        ref = os.path.relpath(path, os.path.abspath(
            os.path.join(_HERE, '..', '..'))).replace(os.sep, '/')
        ledgers.append(led)
        resource_ref = ("research/d2_recursive_v1/data/"
                        f"relation_rebuild_ledger.csv#{traj}")
        ev = events[0]
        port_rows.append({
            "traj": traj,
            "occurrence_id": f"{c['rho_uid']}#e{ev.epoch_id}",
            "relation_lineage": c["rho_uid"],
            "parent_occurrence_ids": "|".join(parent_instance_ids(traj)),
            "t_up": ev.t_up, "t_down": ev.t_down, "t_rearm": ev.t_rearm,
            "t_up_s": ev.t_up * DT_G, "t_down_s": ev.t_down * DT_G,
            "t_rearm_s": ev.t_rearm * DT_G, "dt": DT_G,
            "raw_relation_track_ref": ref,
            "typed_input_provenance": "|".join(TYPED_PROVENANCE),
            "resource_ref": resource_ref,
            "generation_depth": 1})
        print(f"  {traj}: rebuilt bit-exact "
              f"({ev.t_up},{ev.t_down},{ev.t_rearm}) peak={led['x_peak']:.4f}")
    with open(os.path.join(DATA, 'relation_rebuild_ledger.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ledgers[0]))
        w.writeheader(); w.writerows(ledgers)
    with open(os.path.join(DATA, 'relation_occurrence_manifest.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(port_rows[0]))
        w.writeheader(); w.writerows(port_rows)

    # ── 4. NF-1 负结果登记 + 预算账本 + 判定 ──
    with open(os.path.join(DATA, 'd21_negative_findings.json'), 'w',
              encoding='utf-8') as f:
        json.dump({"NF-1": {
            "finding": "transduction latency drifts with pulse onset "
                       "(t_on 1000→521 steps / 2400→527 / 3000→542 / "
                       "3600→559 / 5000→637); at t_on=5000 collector "
                       "crossing (k=5637) lands outside support window "
                       "=> ΔC_phys=0 gate refuses confirmation => zero "
                       "occurrence (gate working as designed, honest "
                       "registration)",
            "evidence": "data/site23_traces/s23_far.csv (immutable)",
            "consequence": "far-gap role reassigned to s23_far_b "
                           "(t_on=4000, gap>tau_decay)"}},
            f, indent=1, ensure_ascii=False)

    budget = {"new_G0_physical_trajectories": n_traj,
              "depth1_relation_replays": len(REBUILD_TRAJS),
              "relation2_calibration_points": 0,
              "a8_twins": 0, "interventions": 0}
    with open(os.path.join(DATA, 'd21_budget_ledger.json'), 'w',
              encoding='utf-8') as f:
        json.dump({"stepB": budget}, f, indent=1)

    occ_count = {t: sum(1 for r in s23_rows if r["traj"] == t)
                 for t, *_ in S23_CAL + S23_HOLD}
    cal_ok = all((occ_count[t] == 0) if t in EXPECT_NO_OCC
                 else (occ_count[t] >= 1) for t in occ_count)
    ok = cal_ok and not mismatch and len(port_rows) == len(REBUILD_TRAJS)
    print(f"\nsite23 trajectories: {n_traj} (≤8, new this run: {n_new_traj})"
          f"  relation rebuilds: {len(REBUILD_TRAJS)} "
          f"(≤16, new this run: {n_replays})")
    print(f"relation ports: {len(port_rows)}  hold SHA256={sha[:16]}… SEALED")
    print(f"occ map: {occ_count}  (NF-1 expects s23_far=0)")
    if mismatch:
        print("BLOCKING: rebuild mismatch on", mismatch)
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
