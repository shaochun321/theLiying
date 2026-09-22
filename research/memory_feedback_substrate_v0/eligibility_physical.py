"""eligibility_physical.py — MFS0-E0 Step A：物理资格载体 e 的资格化。

TYPE:INFRA（research/ 层；production READ_ONLY）。

方案 §11：装配 RelationOccurrencePortV1 → build_phase_drive →
RelationInputNeuron → frozen SynapticBundle → C_e，输出 e 的完整表征，
并以 W=1 / W=0 对照证明 e 是历史的物理函数而非常量。

判据（MFS0-M2）：存在真实 e(t)=V_{C_e}，有形成、有限衰减、物理时间常数、
物理载体；Python trace 不单独算 PASS。
实测 tau_e 必须落在预注册容差内（禁止运行后改 R_e, C_e）。

**两个窗口分别报告**（预注册 two_windows_must_be_reported_separately）：
  存在窗     {t : e(t) > EPSILON_E}        ← M2
  写入可达窗 {t : FET_e.conduct(e(t)) > 0} ← Step D 选 NEAR 的真实约束

运行：cd research/memory_feedback_substrate_v0 && python eligibility_physical.py
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import mfs0_common as M  # noqa: E402
from nexus_v1.components.semiconductor import MOSFET  # noqa: E402


def run_arm(with_w: bool, t_total: int = M.T_TOTAL_STEPA):
    """一臂完整 replay。with_w=False 即 W=0（无历史输入）对照臂。

    W=0 的定义：typed 端口列表为空 ⇒ build_phase_drive 全程 ϑ=0。
    物理链、时长、初态与 W=1 臂逐位相同（只有驱动内容不同）。
    """
    ports = [M.w_relation_port()] if with_w else []
    drive = M.drive_from_ports(ports, t_total)
    p = M.build_eligibility("w1" if with_w else "w0")
    fet = MOSFET(v_threshold=M.FET_V_THRESHOLD, gm=M.FET_GM)

    es, acts, i_gate, qs = [], [], [], []
    for k in range(t_total):
        e = M.step_eligibility(p, drive[k].value)
        es.append(e)
        acts.append(p.e_activation)
        i_gate.append(fet.conduct(e))
        qs.append(p.cell._membrane.charge)
    energy = p.cell.energy + p.tin.energy
    return {"e": es, "act": acts, "i_gate": i_gate, "charge": qs,
            "transport_cost": p.bundle.transport_cost, "energy_end": energy,
            "q_in": p.cell._membrane._q_in, "q_out": p.cell._membrane._q_out}


def characterize(arm, t_peak_hint: int) -> dict:
    es = arm["e"]
    e_peak = max(es)
    t_peak = es.index(e_peak)
    tau_meas = M.fit_tau(es, t_peak + 1)
    exist_w = M.window_above(es, M.EPSILON_E)
    write_w = M.window_above(arm["i_gate"], 0.0)
    return {
        "e_peak": e_peak,
        "t_peak": t_peak,
        "t_peak_s": t_peak * 0.001,
        "tau_e_measured_s": tau_meas,
        "tau_e_registered_s": M.TAU_E,
        "tau_e_rel_error": (abs(tau_meas - M.TAU_E) / M.TAU_E
                            if tau_meas == tau_meas else float('nan')),
        "last_step_above_epsilon": M.last_above(es, M.EPSILON_E),
        "existence_window": list(exist_w),
        "existence_window_len": (exist_w[1] - exist_w[0] + 1
                                 if exist_w[0] >= 0 else 0),
        "write_reachable_window": list(write_w),
        "write_reachable_window_len": (write_w[1] - write_w[0] + 1
                                       if write_w[0] >= 0 else 0),
        "i_gate_peak": max(arm["i_gate"]),
        "activation_peak_DIAGNOSTIC_ONLY": max(arm["act"]),
        "charge_in": arm["q_in"],
        "charge_out": arm["q_out"],
        "transport_cost": arm["transport_cost"],
        "energy_end": arm["energy_end"],
    }


def main() -> int:
    M.assert_no_step_era_import()
    port = M.w_relation_port()

    M.ledger_add("eligibility_calibration", "stepA_W1",
                 "full replay of the W=1 eligibility arm")
    a1 = run_arm(True)
    M.ledger_add("eligibility_calibration", "stepA_W0",
                 "matched W=0 control arm (empty typed port list)")
    a0 = run_arm(False)

    c1 = characterize(a1, port.t_rearm)
    c0 = characterize(a0, port.t_rearm)

    # ── 判据 ──
    tau_ok = (c1["tau_e_rel_error"] == c1["tau_e_rel_error"]
              and c1["tau_e_rel_error"] <= M.TAU_E_TOLERANCE)
    contrast_ok = (c1["e_peak"] > M.EPSILON_E
                   and c0["e_peak"] <= M.EPSILON_E)
    decay_ok = a1["e"][-1] <= M.EPSILON_E          # e(t) -> 0
    formation_ok = c1["t_peak"] > 0
    carrier_ok = a1["q_in"] > 0.0                  # 真实电荷经电容注入
    write_reachable = c1["write_reachable_window_len"] > 0

    m2 = tau_ok and contrast_ok and decay_ok and formation_ok and carrier_ok

    out = {
        "step": "A",
        "gate": "MFS0-M2 Physical Eligibility",
        "W_material": {"traj": M.W_RELATION_TRAJ,
                       "occurrence_id": port.occurrence_id,
                       "window_steps": [port.t_up, port.t_down, port.t_rearm],
                       "lineage": port.relation_lineage},
        "chain": "RelationOccurrencePortV1 -> build_phase_drive -> "
                 "RelationInputNeuron -> frozen SynapticBundle -> "
                 "Neuron(_membrane=Capacitor)",
        "canonical_readout": "capacitor voltage (plan §4.4)",
        "W1": c1,
        "W0": c0,
        "criteria": {
            "formation": formation_ok,
            "finite_decay_to_floor": decay_ok,
            "tau_within_tolerance": tau_ok,
            "physical_carrier_charge_flow": carrier_ok,
            "W1_vs_W0_contrast": contrast_ok,
        },
        "MFS0_M2": "PASS" if m2 else "FAIL",
        "write_reachability": {
            "reachable": write_reachable,
            "window": c1["write_reachable_window"],
            "window_len_steps": c1["write_reachable_window_len"],
            "fet_v_threshold": M.FET_V_THRESHOLD,
            "note": "This is NOT part of M2. It is the Step D constraint: "
                    "sub-threshold e produces exactly zero write current "
                    "(DEG-019 hard cutoff), so NEAR must be chosen inside "
                    "this window, not merely inside the existence window.",
        },
    }
    M.write_json('eligibility_characterization.json', out)

    print("MFS0-E0 Step A — Physical Eligibility")
    print(f"  W window          = [{port.t_up}, {port.t_rearm}) "
          f"({port.occurrence_id})")
    print(f"  e_peak  W=1/W=0   = {c1['e_peak']:.6f} / {c0['e_peak']:.3e}")
    print(f"  t_peak            = {c1['t_peak']} steps "
          f"({c1['t_peak_s']:.3f} s)")
    print(f"  tau_e measured    = {c1['tau_e_measured_s']:.6f} s   "
          f"(registered {M.TAU_E} s, rel.err "
          f"{c1['tau_e_rel_error']:.4%}, tol {M.TAU_E_TOLERANCE:.0%})")
    print(f"  existence window  = {c1['existence_window']}  "
          f"len={c1['existence_window_len']}")
    print(f"  write-reach window= {c1['write_reachable_window']}  "
          f"len={c1['write_reachable_window_len']}  "
          f"(FET theta={M.FET_V_THRESHOLD})")
    print(f"  activation peak   = {c1['activation_peak_DIAGNOSTIC_ONLY']:.6f} "
          "(DIAGNOSTIC_ONLY)")
    print(f"  charge in/out     = {a1['q_in']:.6f} / {a1['q_out']:.6f}")
    print()
    for k, v in out["criteria"].items():
        print(f"    {'OK ' if v else 'FAIL'}  {k}")
    print(f"\n  MFS0-M2 = {out['MFS0_M2']}")
    if not write_reachable:
        print("  [!] write-reachable window is EMPTY — Step D cannot place a "
              "NEAR timing; see report before proceeding.")
    return 0 if m2 else 1


if __name__ == '__main__':
    raise SystemExit(main())
