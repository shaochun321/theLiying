"""dataset_builder.py — D2-0 Step1：parent 轨迹生成 + RawOccurrenceTrack
IMMUTABLE_CACHE + OccurrencePortV2 + cal/hold SHA 封存。

TYPE:INFRA（research/ 层；production READ_ONLY）。

## COMPUTE_BUDGET（§24/反馈 §十八，运行前登记）

  physical_trajectories = 22（cal12 + hold8 + attack2）≤ 24 ✓
  replays               = 0（本脚本只生成缓存）
  n_parameter_points    = 0
  estimated_state_updates ≈ 22 × 8000 子步 × ~2 handle ≈ 3.6e5 handle-tick
  interventions         = 0

## 场景编排（反馈 §十三：delay 只取 short/medium/long 三档代表）

时基：dt=0.001s，轨迹长 8000 子步（8s）。脉冲长 600 子步（0.6s），
u=0.03。G0-R1 实测锚点：occurrence latency≈0.56s、duration≈0.14s、
rearm=0.5s ⇒ 单脉冲的完整 χ 在起点后 ~1.3s 内完成，8s 轨迹充分容纳。
delay 三档（B 相对 A 的脉冲起点差）：short=200(0.2s)/medium=600(0.6s)/
long=1500(1.5s)。overlap：weak=起点差 450（重叠 150 子步）/strong=150
（重叠 450）。

cal12（覆盖反馈 §27 清单：single/simultaneous/A→B/B→A/weak+strong
overlap）：
  cal_C0_A     单 A                  cal_C1_B     单 B
  cal_C2_sim   同时                  cal_C2_sim2  同时（幅值 0.02 变体）
  cal_C3_s/m/l A→B 三档 delay        cal_C4_s/m/l B→A 三档 delay
  cal_C5_weak  弱重叠                cal_C5_strong 强重叠

hold8（未见 delay/duration/dose/hidden-variant 各 2，SHA 冻结后仅
final_qualification 冻结参数盲评；反馈 §21：raw track 可在冻结后生成，
但任何参数不得据 hold 轨迹调整）：
  hold_delay1/2    未见 delay（400/1000）
  hold_dur1/2      未见脉冲长（300/900）
  hold_dose1/2     未见幅值（0.02/0.04，均在 L1 线性域）
  hold_hist1/2     hidden-variant（相同当前脉冲对，前史多一个早期脉冲）

attack2（site23=G_c，R-1 仅攻击用途）：
  atk_replaceB     A→C medium（site 替换攻击：G_c 顶替 G_b 的位置）
  atk_CtoA         C→A medium（泛化方向）

复现入口：
  PYTHONIOENCODING=utf-8 python research/d2_relation_v0/dataset_builder.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..')))

from d2_common import (  # noqa: E402
    DATA, DT_G, Pulse, TrajSpec, U_DRIVE, run_trajectory, write_track)
from tss.adapters.occurrence_port_v2 import from_occurrence  # noqa: E402

T = 8000
P = 600
_S, _M, _L = 200, 600, 1500
A0 = 1000  # A 基准起点（前置 1s 静息基线）


def _spec(tid, a_pulses=None, b_pulses=None, c_pulses=None, note=""):
    pulses = {}
    if a_pulses is not None:
        pulses["A"] = tuple(a_pulses)
    if b_pulses is not None:
        pulses["B"] = tuple(b_pulses)
    if c_pulses is not None:
        pulses["C"] = tuple(c_pulses)
    return TrajSpec(tid=tid, t_total=T, pulses=pulses, note=note)


def build_cal():
    return [
        _spec("cal_C0_A", a_pulses=[Pulse(A0, P)], b_pulses=[]),
        _spec("cal_C1_B", a_pulses=[], b_pulses=[Pulse(A0, P)]),
        _spec("cal_C2_sim", [Pulse(A0, P)], [Pulse(A0, P)]),
        _spec("cal_C2_sim2", [Pulse(A0, P, 0.02)], [Pulse(A0, P, 0.02)]),
        _spec("cal_C3_s", [Pulse(A0, P)], [Pulse(A0 + _S, P)]),
        _spec("cal_C3_m", [Pulse(A0, P)], [Pulse(A0 + _M, P)]),
        _spec("cal_C3_l", [Pulse(A0, P)], [Pulse(A0 + _L, P)]),
        _spec("cal_C4_s", [Pulse(A0 + _S, P)], [Pulse(A0, P)]),
        _spec("cal_C4_m", [Pulse(A0 + _M, P)], [Pulse(A0, P)]),
        _spec("cal_C4_l", [Pulse(A0 + _L, P)], [Pulse(A0, P)]),
        _spec("cal_C5_weak", [Pulse(A0, P)], [Pulse(A0 + 450, P)]),
        _spec("cal_C5_strong", [Pulse(A0, P)], [Pulse(A0 + 150, P)]),
    ]


def build_hold():
    return [
        _spec("hold_delay1", [Pulse(A0, P)], [Pulse(A0 + 400, P)]),
        _spec("hold_delay2", [Pulse(A0, P)], [Pulse(A0 + 1000, P)]),
        _spec("hold_dur1", [Pulse(A0, 300)], [Pulse(A0 + _M, 300)]),
        _spec("hold_dur2", [Pulse(A0, 900)], [Pulse(A0 + _M, 900)]),
        _spec("hold_dose1", [Pulse(A0, P, 0.02)], [Pulse(A0 + _M, P, 0.02)]),
        _spec("hold_dose2", [Pulse(A0, P, 0.04)], [Pulse(A0 + _M, P, 0.04)]),
        _spec("hold_hist1", [Pulse(200, 300), Pulse(A0 + 2000, P)],
              [Pulse(A0 + 2000 + _M, P)],
              note="前史变体：A 侧多一个早期脉冲，当前脉冲对同 hold_hist2"),
        _spec("hold_hist2", [Pulse(A0 + 2000, P)],
              [Pulse(A0 + 2000 + _M, P)],
              note="与 hist1 的当前脉冲对相同、前史不同（C6 素材）"),
    ]


def build_attack():
    return [
        _spec("atk_replaceB", a_pulses=[Pulse(A0, P)],
              c_pulses=[Pulse(A0 + _M, P)],
              note="site 替换攻击：G_c(site23) 顶替 G_b 位置"),
        _spec("atk_CtoA", a_pulses=[Pulse(A0 + _M, P)],
              c_pulses=[Pulse(A0, P)], note="泛化方向 C→A"),
    ]


def _manifest(specs):
    return {s.tid: {"t_total": s.t_total, "note": s.note,
                    "pulses": {k: [(p.t_on, p.length, p.amp) for p in v]
                               for k, v in sorted(s.pulses.items())}}
            for s in specs}


def main() -> int:
    os.makedirs(DATA, exist_ok=True)
    cal, hold, atk = build_cal(), build_hold(), build_attack()
    assert len(cal) + len(hold) + len(atk) <= 24, "COMPUTE_BUDGET 超限"

    # hold manifest SHA 先冻结（写盘即入下一次 commit；评估仅在
    # final_qualification 冻结参数盲评一次）
    hold_j = json.dumps(_manifest(hold), indent=1, sort_keys=True)
    sha = hashlib.sha256(hold_j.encode('utf-8')).hexdigest()
    with open(os.path.join(DATA, 'd2_hold_manifest.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        f.write(hold_j)
    with open(os.path.join(DATA, 'd2_hold_seal.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        json.dump({"hold_manifest_sha256": sha, "sealed": "2026-09-20",
                   "discipline": "naturalization/relation/closure params "
                                 "MUST NOT be tuned from hold trajectories; "
                                 "hold exposure => FAIL, no re-run (反馈§21)"},
                  f, indent=1)
    with open(os.path.join(DATA, 'd2_cal_manifest.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        json.dump(_manifest(cal + atk), f, indent=1, sort_keys=True)

    # 生成全部轨迹 + raw track 缓存 + ports
    port_rows = []
    for s in cal + hold + atk:
        rows, occs, _h = run_trajectory(s)
        path = write_track(s.tid, rows)
        ref = os.path.relpath(path, os.path.abspath(
            os.path.join(_HERE, '..', '..'))).replace(os.sep, '/')
        n_occ = 0
        for label, evs in sorted(occs.items()):
            for ev in evs:
                port = from_occurrence(ev, DT_G, raw_track_ref=ref,
                                       typed_input_ports=("U_dotT",))
                port_rows.append({
                    "traj": s.tid, "parent": label,
                    "occurrence_id": port.occurrence_id,
                    "lineage_uid": port.lineage_uid,
                    "n_parent_uids": len(port.parent_uids),
                    "t_up": port.t_up, "t_down": port.t_down,
                    "t_rearm": port.t_rearm,
                    "t_up_s": port.t_up_s, "t_down_s": port.t_down_s,
                    "t_rearm_s": port.t_rearm_s,
                    "raw_track_ref": port.raw_track_ref,
                })
                n_occ += 1
        print(f"  {s.tid}: occ={n_occ} "
              f"({', '.join(f'{k}:{len(v)}' for k, v in sorted(occs.items()))})")

    import csv as _csv
    with open(os.path.join(DATA, 'occurrence_parent_manifest.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = _csv.DictWriter(f, fieldnames=list(port_rows[0]))
        w.writeheader()
        w.writerows(port_rows)

    print(f"\ntrajectories: {len(cal)} cal + {len(hold)} hold + "
          f"{len(atk)} attack = {len(cal) + len(hold) + len(atk)} (≤24)")
    print(f"parent occurrences (ports): {len(port_rows)}")
    print(f"hold SHA256 = {sha[:16]}… SEALED")
    # 基本健全性：cal 单脉冲轨迹每个受驱 parent 至少 1 次 occurrence
    ok = all(any(r["traj"] == t for r in port_rows)
             for t in ("cal_C0_A", "cal_C1_B", "cal_C2_sim"))
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
