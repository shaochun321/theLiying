"""heldout_eval.py — Posterior-0 Step G1：hold6 一次盲评（零回调）。

TYPE:INFRA（research/ 层）。

先验证 p0_hold_manifest.json SHA == p0_hold_seal.json（先封后跑）；
每例一次运行，合法失败仅限 illegal state/nonfinite/replay 不一致/
lineage 缺失（W 发生边界须与 D2-1 冻结候选逐位一致）；null/negative
结果合法（如 occ_Q=0、PNS=False）。结果只登记不回调。

W 组合冻结边界（relation2_occurrence_candidates.csv，运行时读）：
  rc_main (3332,4931,5387) / rc_lead (3540,4826,5282) /
  rc_R_only (3658,4802,5258)——NEAR Δ (t_up=5402) 对三者均为 closed past。

## COMPUTE_BUDGET： heldout = 6/6

复现入口：
  PYTHONIOENCODING=utf-8 python research/posterior_v0/heldout_eval.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from p0_common import (  # noqa: E402
    DATA, POSTERIOR_WASHOUT_STEPS, Q_WINDOW_LEN, events_in, ledger_add,
    peak_in, q_window, run_arm)
from d21_common import (  # noqa: E402
    DATA as D21_DATA, frozen_relation2_params, load_relation_ports,
    load_site23_windows)
from relation_physical_impl import PortWindow  # noqa: E402

X_CLAMP = 10.0


def _frozen_w_boundaries():
    out = {}
    with open(os.path.join(D21_DATA, 'relation2_occurrence_candidates.csv'),
              newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            out[r["run"]] = (int(r["t_up"]), int(r["t_down"]),
                             int(r["t_rearm"]))
    return out


def main() -> int:
    with open(os.path.join(DATA, 'p0_hold_manifest.json'), 'rb') as f:
        raw = f.read()
    sha = hashlib.sha256(raw).hexdigest()
    with open(os.path.join(DATA, 'p0_hold_seal.json'),
              encoding='utf-8') as f:
        seal = json.load(f)
    assert sha == seal["hold_manifest_sha256"], "HOLD SEAL MISMATCH"
    man = json.loads(raw.decode('utf-8'))
    tm = man["timing"]
    _, theta2, _ = frozen_relation2_params()
    fb = _frozen_w_boundaries()
    rho = load_relation_ports()["cal_C3_m"]
    s23 = load_site23_windows()

    w_defs = {"rc_main": ([rho], list(s23["s23_ov"])),
              "rc_lead": ([rho], list(s23["s23_lead"])),
              "rc_R_only": ([rho], [])}
    d_defs = {"NEAR": tm["NEAR"]["window"],
              "H3_HOLD": tm["H3_HOLD"]["window"], "sham": None}

    rows, failures = [], []
    for case in man["cases"]:
        cid, wname, dname, qspec = (case["case"], case["W"],
                                    case["delta"], case["q"])
        rports, cwins = w_defs[wname]
        dwin = d_defs[dname]
        if qspec == "std":
            q_up = tm["q_up_near_set"]
        elif qspec == "std+300":
            q_up = tm["q_up_near_set"] + 300
        else:                       # delta_rearm+456
            q_up = dwin[2] + POSTERIOR_WASHOUT_STEPS
        q_end = q_up + Q_WINDOW_LEN + POSTERIOR_WASHOUT_STEPS
        cw = list(cwins)
        if dwin:
            cw.append(PortWindow(dwin[0], dwin[2], f"delta.{dname}"))
        cw.append(q_window(q_up))
        res = run_arm(f"hold_{cid}", rports,
                      sorted(cw, key=lambda w: w.t_up), t_total=8000,
                      snapshot_at=(q_up - 1,))
        ledger_add("heldout", cid, f"W={wname} delta={dname} q={qspec}")
        occ = [(e.t_up, e.t_down, e.t_rearm) for e in res.events]
        w_occ = occ[0] if occ else None
        t_rearm_w = fb[wname][2]
        checks = {
            "finite": all(abs(v) <= X_CLAMP for v in res.xs),
            "w_boundary_bitexact": w_occ == fb[wname],
            "delta_is_closed_past": (dwin is None
                                     or dwin[0] > t_rearm_w),
        }
        row = {"case": cid, "W": wname, "delta": dname, "q_up": q_up,
               "occ_all": json.dumps(occ),
               "pns_delta_epoch": json.dumps(
                   [(e.t_up, e.t_down, e.t_rearm) for e in
                    events_in(res.events, t_rearm_w, q_up)][1:]
                   if occ and occ[0][0] < t_rearm_w else []),
               "occ_q": json.dumps([(e.t_up, e.t_down, e.t_rearm) for e in
                                    events_in(res.events, q_up, q_end)]),
               "m_q": peak_in(res.xs, q_up, q_end) - theta2,
               "z_pre_q_membrane": res.vs[q_up - 1],
               "x_peak": res.ledger["x_peak"],
               "legal": all(checks.values()),
               "checks": json.dumps(checks)}
        rows.append(row)
        if not row["legal"]:
            failures.append(cid)
        print(f"  {cid}: W_occ={w_occ} legal={row['legal']} "
              f"M_Q={row['m_q']:+.4f} occ_q={row['occ_q']} "
              f"z_vm(q-1)={row['z_pre_q_membrane']:.4f}")

    with open(os.path.join(DATA, 'posterior_heldout.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    verdict = {"sha_verified": True, "n_cases": len(rows),
               "failures": failures, "one_pass_zero_recall": not failures}
    with open(os.path.join(DATA, 'posterior_heldout_verdict.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        json.dump(verdict, f, indent=1)
    print(f"\nhold6: {len(rows) - len(failures)}/{len(rows)} legal; "
          f"failures={failures}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
