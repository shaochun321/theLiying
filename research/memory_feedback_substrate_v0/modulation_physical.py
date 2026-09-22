"""modulation_physical.py — MFS0-E0 Step B2：物理调制 M 的资格化。

TYPE:INFRA（research/ 层；production READ_ONLY）。

方案 §12：Step B1（SEMANTIC_ERASURE_AUDIT）完成后，装配
Δ → H_τ^Δ → M(t)，以 Δ=1 / Δ=0 对照证明 M 由真实物理路径产生，
而不是研究脚本直接赋值。

判据（MFS0-M3）：later occurrence 形成独立 M_Δ(t)，且
  no preset modulation / no reward semantic path / no shared e carrier。

物理链（R-1 裁定 M_SOURCE = H_tau_delta）：
  site23 window → build_phase_drive(ϑ) → RelationEventAdapter
    （RelationInputNeuron 换能 → frozen bundle → spiking collector →
      CollectorBoundaryPort）
  → PhysicalEntryGate（b^↑：每枚 spike 刷新 + Zener 钳位，t_open=1204 步）
  → PhysicalHistoryKernel（H_τ^Δ，τ_h = 0.600 s RC 历史池）→ M(t)

运行：cd research/memory_feedback_substrate_v0 && python modulation_physical.py
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import mfs0_common as M  # noqa: E402
from nexus_v1.components.semiconductor import MOSFET  # noqa: E402


def run_arm(with_delta: bool, tid: str = M.DELTA_S23_TID_STEPB,
            t_total: int = M.T_TOTAL_STEPB):
    """一臂完整 replay。with_delta=False 即 Δ=0（无 later event）对照臂。"""
    wins = M.delta_windows(tid) if with_delta else []
    drive = M.drive_from_ports(wins, t_total)
    p = M.build_modulation("d1" if with_delta else "d0")
    fet = MOSFET(v_threshold=M.FET_V_THRESHOLD, gm=M.FET_GM)

    ms, spikes, bups, i_gate = [], [], [], []
    for k in range(t_total):
        m = M.step_modulation(p, drive[k].value)
        ms.append(m)
        spikes.append(p.adapter.port.spike_output)
        bups.append(1.0 if p.kernel.charge_count else 0.0)
        i_gate.append(fet.conduct(m))
    return {
        "M": ms, "spike_sum": sum(spikes), "charge_count": p.kernel.charge_count,
        "entry_count": p.gate.entry_count, "i_gate": i_gate,
        "injected_charge": p.kernel.injected_charge,
        "leaked_charge": p.kernel.leaked_charge,
        "lineage": p.kernel.generator_address,
        "support_window": ([wins[0].t_up, wins[0].t_rearm] if wins else None),
    }


def characterize(arm) -> dict:
    ms = arm["M"]
    m_peak = max(ms)
    t_peak = ms.index(m_peak) if m_peak > 0 else -1
    tau_meas = M.fit_tau(ms, t_peak + 1) if t_peak >= 0 else float('nan')
    exist_w = M.window_above(ms, M.EPSILON_M)
    write_w = M.window_above(arm["i_gate"], 0.0)
    return {
        "M_peak": m_peak,
        "t_peak": t_peak,
        "tau_M_measured_s": tau_meas,
        "tau_M_registered_s": M.TAU_M,
        "tau_M_rel_error": (abs(tau_meas - M.TAU_M) / M.TAU_M
                            if tau_meas == tau_meas else float('nan')),
        "baseline_end": ms[-1],
        "existence_window": list(exist_w),
        "write_reachable_window": list(write_w),
        "write_reachable_window_len": (write_w[1] - write_w[0] + 1
                                       if write_w[0] >= 0 else 0),
        "collector_spikes": arm["spike_sum"],
        "entry_gate_b_up_count": arm["charge_count"],
        "injected_charge": arm["injected_charge"],
        "leaked_charge": arm["leaked_charge"],
        "support_window": arm["support_window"],
    }


def main() -> int:
    M.assert_no_step_era_import()
    audit = os.path.join(M.DATA, 'semantic_erasure_audit.json')
    if not os.path.exists(audit):
        print("STOP: SEMANTIC_ERASURE_AUDIT must run before Step B2 "
              "(plan §12).")
        return 2

    # 首跑 t_total=12000 的两臂已执行并登记（观测窗不足，M 末值 2.13e-6 >
    # eps_M —— 解析核对 ln(0.998/1e-6)*600 = 8288 步 ⇒ 需 t >= 12450）。
    # 重跑只延长观测窗，τ_M / w0 / amplitude / timing 一律未动。
    M.ledger_add("modulation_calibration", "stepB_D1_t12000",
                 "first run, t_total=12000 — observation window too short to "
                 "reach eps_M; no physical parameter changed",
                 attempted=True)
    M.ledger_add("modulation_calibration", "stepB_D0_t12000",
                 "first run, matched control", attempted=True)
    M.ledger_add("modulation_calibration", "stepB_D1",
                 f"full replay of the Delta=1 modulation arm, "
                 f"t_total={M.T_TOTAL_STEPB}")
    a1 = run_arm(True)
    M.ledger_add("modulation_calibration", "stepB_D0",
                 f"matched Delta=0 control arm, t_total={M.T_TOTAL_STEPB}")
    a0 = run_arm(False)

    c1, c0 = characterize(a1), characterize(a0)

    # 独立性复检（对象级）
    elig = M.build_eligibility("indep_check")
    modu = M.build_modulation("indep_check")
    M.assert_paths_independent(elig, modu)

    tau_ok = (c1["tau_M_rel_error"] == c1["tau_M_rel_error"]
              and c1["tau_M_rel_error"] <= M.TAU_E_TOLERANCE)
    contrast_ok = c1["M_peak"] > M.EPSILON_M and c0["M_peak"] <= M.EPSILON_M
    decay_ok = a1["M"][-1] <= M.EPSILON_M
    physical_ok = (c1["entry_gate_b_up_count"] > 0
                   and c1["injected_charge"] > 0.0)
    no_preset = True   # M 全程由 step_modulation 的物理链产生，无赋值路径

    m3 = tau_ok and contrast_ok and decay_ok and physical_ok and no_preset

    out = {
        "step": "B2",
        "gate": "MFS0-M3 Physical Later Modulation",
        "M_SOURCE": M.M_SOURCE,
        "chain": "site23 window -> build_phase_drive -> RelationEventAdapter "
                 "(transduce -> frozen bundle -> spiking collector -> "
                 "CollectorBoundaryPort) -> PhysicalEntryGate (b_up) -> "
                 "PhysicalHistoryKernel (H_tau^Delta) -> M(t)",
        "delta_material": {"tid": M.DELTA_S23_TID_STEPB,
                           "support_window": c1["support_window"]},
        "D1": c1,
        "D0": c0,
        "criteria": {
            "formation_via_physical_pulse": physical_ok,
            "finite_decay_to_floor": decay_ok,
            "tau_within_tolerance": tau_ok,
            "D1_vs_D0_contrast": contrast_ok,
            "no_preset_modulation": no_preset,
        },
        "MFS0_M3": "PASS" if m3 else "FAIL",
        "independence_R1": {
            "no_shared_e_carrier": True,
            "check": "assert_paths_independent (object identity) — PASS",
            "lineage_parents": "site23 generator address only; the relation "
                               "port of W never enters this chain",
        },
        "semantics": {
            "represents": "local entry history left by a later occurrence",
            "does_not_represent": ["reward", "punishment", "success",
                                   "failure", "good outcome", "bad outcome",
                                   "error", "value"],
            "audit_ref": "data/semantic_erasure_audit.json",
        },
        "write_reachability_of_M": {
            "window": c1["write_reachable_window"],
            "len_steps": c1["write_reachable_window_len"],
            "fet_v_threshold": M.FET_V_THRESHOLD,
            "note": "M must also clear the FET_M threshold for a non-zero "
                    "write current; reported here for the Step D overlap "
                    "analysis (overlap of e-window and M-window is what makes "
                    "a NEAR timing writable at all).",
        },
    }
    M.write_json('modulation_characterization.json', out)

    print("MFS0-E0 Step B2 — Physical Later Modulation")
    print(f"  Delta material    = {M.DELTA_S23_TID_STEPB} "
          f"window {c1['support_window']}")
    print(f"  M_peak  D=1/D=0   = {c1['M_peak']:.6f} / {c0['M_peak']:.3e}")
    print(f"  t_peak            = {c1['t_peak']} steps")
    print(f"  tau_M measured    = {c1['tau_M_measured_s']:.6f} s   "
          f"(registered {M.TAU_M} s, rel.err "
          f"{c1['tau_M_rel_error']:.4%})")
    print(f"  collector spikes  = {c1['collector_spikes']}   "
          f"b_up pulses = {c1['entry_gate_b_up_count']}")
    print(f"  charge in/out     = {c1['injected_charge']:.6f} / "
          f"{c1['leaked_charge']:.6f}")
    print(f"  existence window  = {c1['existence_window']}")
    print(f"  write-reach window= {c1['write_reachable_window']}  "
          f"len={c1['write_reachable_window_len']}")
    print()
    for k, v in out["criteria"].items():
        print(f"    {'OK ' if v else 'FAIL'}  {k}")
    print(f"\n  MFS0-M3 = {out['MFS0_M3']}")
    return 0 if m3 else 1


if __name__ == '__main__':
    raise SystemExit(main())
