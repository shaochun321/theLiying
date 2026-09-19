"""final_qualification.py — G0-R1/OCC 六门裁定（OCC-M1~M6）与终态输出。

TYPE:INFRA（research/ 层；production READ_ONLY）。

六门（方案 §22；§23 明令不存在 M7/M8/M9"完美动力学"门）：
  OCC-M1 Physical Time   ：occurrence 三边界/delay/rearm 均可映射 t_phys
  OCC-M2 Typed Chain     ：速率/幅值语义类型层强制（机器化检查）
  OCC-M3 Finite Closure  ：trigger→sustain→exit→rearm 真实完成
                           （Step3 合同验证结果）
  OCC-M4 Held-out        ：hold12 冻结参数盲评一次过，无结构性失败
  OCC-M5 Physical Ledger ：能量/lineage 可审计（R-2 裁定审计面=研究区
                           账本+kernel_ledger 旁路；无隐藏 side channel
                           ——端口对象不含研究者语义标签）
  OCC-M6 Hidden Dynamics ：same-visible/different-future→定位→干预→
                           stop/deepen 至少一轮正式完成（Step4 结果）

## OCC-M4 盲评纪律（E-8）

hold 清单 SHA256 已于评估前提交（r1_hold_seal.json, commit 4b95339）；
本脚本先验证 SHA 匹配再运行；冻结参数 = g_v2（R1-2）+ canonical
(theta_up=0.01, rearm=500)（Step3）；逐类期望与 cal 预注册完全相同；
**一次评估，不回调任何参数**。

终态（§24 三选一）：
  A: G0_OCCURRENCE_V2_QUALIFIED + D1_SUFFICIENT_FOR_D2
  B: G0_OCCURRENCE_PARTIAL + BLOCKING_DEFECT=<具体缺陷>
  C: G0_OCCURRENCE_ARCHITECTURE_FAIL（仅当发生合同跨 World 不成立）

复现入口：
  PYTHONIOENCODING=utf-8 python research/g0_reconnect/r1_occ/final_qualification.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', 'r0')))
sys.path.insert(0, _HERE)

from g0r0_common import fresh_g0  # noqa: E402
from r1_calibration import DT_G  # noqa: E402
from r1_dataset import build_sets  # noqa: E402
from occurrence_revalidation import (  # noqa: E402
    _EXPECT, _g_v2, _replay_closure, _run_episode)
from tss.adapters.typed_ports import UdotTSample, UTSample  # noqa: E402
from tss.adapters.occurrence_port_v2 import from_occurrence  # noqa: E402

DATA = os.path.join(_HERE, 'data')
CANONICAL = (0.01, 500)  # Step3 冻结（r1_revalidation.json）


def gate_m1() -> dict:
    """物理时间映射：三边界/delay/rearm 全部可出物理秒。"""
    from nexus_v1.circuit.bundle import SynapticBundle, BundleConfig
    from nexus_v1.somatosensory.transducer_neurons import ThermalInputNeuron
    h = fresh_g0()
    from tss.generators.occurrence import Occurrence
    ev = Occurrence(t_up=100, t_down=239, t_rearm=739,
                    address=h.closure.address, epoch_id=1)
    tp = ev.to_physical(DT_G)
    a, b = ThermalInputNeuron('m1a'), ThermalInputNeuron('m1b')
    bu = SynapticBundle(BundleConfig(bundle_id='m1', delay_tau_s=0.005),
                        [a], [b], dt=DT_G)
    ok = (abs(tp[0] - 0.1) < 1e-9 and abs(tp[2] - 0.739) < 1e-9
          and bu.config.delay_steps == 5
          and abs(500 * DT_G - 0.5) < 1e-12)
    return {"pass": ok, "occurrence_t_phys": list(tp),
            "delay_tau_0.005s->steps": bu.config.delay_steps,
            "rearm_500steps_s": 500 * DT_G}


def gate_m2() -> dict:
    """typed chain：速率口接受 UdotTSample、拒绝 UTSample（语义混用禁令）。"""
    h = fresh_g0()
    accepted = rejected = False
    h.tick_rate_port(UdotTSample(0.01, 0.0), DT_G, 0)
    accepted = True
    try:
        h.tick_rate_port(UTSample(0.01, 0.0), DT_G, 1)
    except TypeError:
        rejected = True
    return {"pass": accepted and rejected,
            "rate_sample_accepted": accepted,
            "amplitude_sample_rejected": rejected}


def gate_m3() -> dict:
    with open(os.path.join(DATA, 'r1_revalidation.json')) as f:
        s = json.load(f)
    c = s["contract_K1a"]
    return {"pass": bool(c.get("all_pass")), "contract": c,
            "canonical": s["canonical"]}


def gate_m4(g) -> dict:
    """held-out 盲评：SHA 验证 → hold12 冻结参数一次过。"""
    _cal, hold = build_sets()
    from dataclasses import asdict
    hold_j = json.dumps({k: asdict(v) for k, v in sorted(hold.items())},
                        indent=1, sort_keys=True)
    sha = hashlib.sha256(hold_j.encode('utf-8')).hexdigest()
    with open(os.path.join(DATA, 'r1_hold_seal.json')) as f:
        sealed = json.load(f)["hold_manifest_sha256"]
    if sha != sealed:
        return {"pass": False, "blocking": "HOLD_MANIFEST_SHA_MISMATCH"}
    th, rm = CANONICAL
    rows, fails = [], []
    for eid, spec in sorted(hold.items()):
        col, sup, led = _run_episode(spec, g)
        evs, trig = _replay_closure(col, sup, th, rm)
        cls = eid.split("_")[1][:2]
        n = len(evs)
        finite = all(math.isfinite(v) for v in
                     (led["col_peak"], led["energy_drop"]))
        ok = finite and n in _EXPECT[cls] and (cls != "K7" or trig)
        if not ok:
            fails.append(eid)
        rows.append({"episode": eid, "class": cls, "occ": n,
                     "triggered": trig, "col_peak": led["col_peak"],
                     "l1_sat_frac": led["l1_sat_frac"],
                     "energy_drop": led["energy_drop"], "ok": ok})
        print(f"    hold {eid}: occ={n} trig={trig} "
              f"peak={led['col_peak']:.4f} {'OK' if ok else 'FAIL'}")
    with open(os.path.join(DATA, 'occurrence_heldout.csv'), 'w',
              newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    return {"pass": not fails, "sha_verified": True, "n": len(rows),
            "failures": fails}


def gate_m5() -> dict:
    """账本可审计（R-2 审计面）+ 端口无研究者语义标签 + lineage 完整。"""
    ok_ledger = ok_port = ok_lineage = False
    with open(os.path.join(DATA, 'energy_ledger.csv')) as f:
        rows = list(csv.DictReader(f))
        ok_ledger = len(rows) == 16 and all(
            math.isfinite(float(r["energy_drop"])) and
            float(r["energy_drop"]) >= 0 for r in rows)
    # 端口构造实测（D2 消费冒烟）：hold 用不了（盲评已过），用 cal_K1a 重放
    cal, _ = build_sets()
    col, sup, _led = _run_episode(cal["cal_K1a"], _g_v2())
    evs, _ = _replay_closure(col, sup, *CANONICAL)
    if evs:
        port = from_occurrence(evs[0], DT_G,
                               raw_track_ref="r1_occ/data/closure_timing.csv",
                               typed_input_ports=("U_dotT",))
        d = port.__dict__
        ok_port = ("hidden_state" not in d and "important_relation" not in d
                   and port.generation_depth == 0)
        ok_lineage = bool(port.lineage_uid) and len(port.parent_uids) >= 1
    return {"pass": ok_ledger and ok_port and ok_lineage,
            "ledger_rows_finite": ok_ledger,
            "port_no_semantic_labels": ok_port,
            "lineage_present": ok_lineage}


def gate_m6() -> dict:
    with open(os.path.join(DATA, 'minimal_state_ruling.json')) as f:
        r = json.load(f)
    ok = (r.get("ruling") in ("HIDDEN_STATE_CAUSALLY_SUPPORTED",
                              "OSCILLATOR_PHASE_MICROSTATE_ONLY")
          and "STOP" in r.get("stop", ""))
    return {"pass": ok, "ruling": r.get("ruling"), "stop": r.get("stop"),
            "minimal_state": r.get("minimal_sufficient_state_candidate")}


def main() -> int:
    g = _g_v2()
    print("=" * 60)
    print("G0-R1/OCC — FINAL QUALIFICATION (six gates)")
    print("=" * 60)
    gates = {}
    for name, fn in [("OCC-M1", gate_m1), ("OCC-M2", gate_m2),
                     ("OCC-M3", gate_m3),
                     ("OCC-M4", lambda: gate_m4(g)),
                     ("OCC-M5", gate_m5), ("OCC-M6", gate_m6)]:
        print(f"  [{name}] running…")
        gates[name] = fn()
        print(f"  [{name}] {'PASS' if gates[name]['pass'] else 'FAIL'}")

    all_pass = all(v["pass"] for v in gates.values())
    if all_pass:
        state = {"terminal": "A",
                 "G0_OCCURRENCE_V2_QUALIFIED": True,
                 "D1_SUFFICIENT_FOR_D2": True,
                 "hard_stop": "FREEZE G0-CENTRIC MAINLINE (§25)"}
    else:
        blocking = [k for k, v in gates.items() if not v["pass"]]
        state = {"terminal": "B", "G0_OCCURRENCE_PARTIAL": True,
                 "BLOCKING_DEFECT": blocking}
    summary = {"frozen_params": {"g_v2": g, "theta_up": CANONICAL[0],
                                 "rearm": CANONICAL[1], "dt_g": DT_G,
                                 "live_policy": "S0", "bridge": "B0"},
               "gates": gates, "terminal_state": state}
    with open(os.path.join(DATA, 'qualification_summary.json'), 'w') as f:
        json.dump(summary, f, indent=1, ensure_ascii=False)
    print("=" * 60)
    print("TERMINAL STATE:", json.dumps(state, ensure_ascii=False))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
