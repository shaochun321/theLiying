"""preregistration.py — MFS0-E0 Step 0：预注册 + 上游完整性封存 + 预算账本。

TYPE:INFRA（research/ 层；production READ_ONLY）。

方案 §10/§10.1：开工第一步**不得运行主实验**，先落三份产物——
  data/preregistration.json      冻结全部判据、参数与其出处
  data/frozen_upstream_seal.json SHA256 封存上游冻结产物（收口重算须相等）
  data/budget_ledger.json        预算账本（caps + counting_rules）

运行：PYTHONIOENCODING=utf-8 python -m research.memory_feedback_substrate_v0.preregistration
或   cd research/memory_feedback_substrate_v0 && python preregistration.py
"""
from __future__ import annotations

import hashlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import mfs0_common as M  # noqa: E402

_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))

# §10.1 封存清单——上游冻结产物 + 消费口源码 + 复用轨迹 + 谱系 manifest
SEAL_TARGETS = [
    # D2-0 冻结产物（relation v0 标定与候选）
    "research/d2_relation_v0/data/relation_calibration.json",
    "research/d2_relation_v0/data/relation_occurrence_candidates.csv",
    "research/d2_relation_v0/data/occurrence_parent_manifest.csv",
    # D2-1 冻结产物（relation2 标定、候选、本轮复用的两个 manifest）
    "research/d2_recursive_v1/data/relation2_calibration.json",
    "research/d2_recursive_v1/data/relation2_occurrence_candidates.csv",
    "research/d2_recursive_v1/data/relation_occurrence_manifest.csv",
    "research/d2_recursive_v1/data/site23_occurrence_manifest.csv",
    # typed 消费口（本轮唯一合法入口）
    "tss/adapters/relation_occurrence_port_v1.py",
    "tss/adapters/occurrence_port_v2.py",
    "tss/adapters/relation_replay_adapter.py",
    # 本轮复用的物理元件（production READ_ONLY 的机器级见证）
    "tss/relations/relation_event_adapter.py",
    "tss/relations/entry_gate.py",
    "tss/relations/history_kernel.py",
    "nexus_v1/components/semiconductor.py",
]


def sha256_of(rel: str) -> str:
    path = os.path.join(_ROOT, rel)
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def build_seal() -> dict:
    return {"targets": {rel: sha256_of(rel) for rel in SEAL_TARGETS},
            "rule": "recompute at closure; BEFORE == AFTER required, "
                    "otherwise MFS0-INTEGRITY = FAIL (plan §10.1)"}


def build_preregistration() -> dict:
    port = M.w_relation_port()
    return {
        "round": "MFS0-E0",
        "plan": "MAINLINE V2 — MFS0-E0 修订执行方案 (2026-09-23, 34 sections)",
        "plan_status": "ADOPTED_WITH_AMENDMENTS",
        "critique": "cell-cell/交叉比对/MFS0-E0方案评判_2026-09-23.md "
                    "(E-1..E-12 INCORPORATED)",
        "scope_this_batch": "Step 0 / A / B / C only — plan §34 sets "
                            "READY_FOR_MAIN_FACTORIAL = NO until A/B/C pass; "
                            "§31 forbids skipping steps",

        "rulings": {
            "R-1_modulation_source": M.M_SOURCE,
            "R-2_multiplication_tier": M.MULTIPLICATION_TIER,
            "R-2_limitation": M.TIER2_LIMITATION,
            "R-3_posterior0": "POSTERIOR0_TERMINAL_C_FROZEN = TRUE "
                              "(applied 2026-09-23 as RULING-P0-1; MFS0 must "
                              "not retroactively modify Posterior-0)",
            "R-4_initial_w": M.INITIAL_W,
            "R-4_no_runtime_w0_search": M.NO_RUNTIME_W0_SEARCH,
        },

        "frozen_parameters": {
            "TAU_E_s": M.TAU_E,
            "C_E": M.C_E,
            "R_E": M.R_E,
            "TAU_E_TOLERANCE_rel": M.TAU_E_TOLERANCE,
            "TAU_M_s": M.TAU_M,
            "INITIAL_W": M.INITIAL_W,
            "W_METABOLIC_LEAK": M.W_METABOLIC_LEAK,
            "WRITE_POLARITY": M.WRITE_POLARITY,
            "POST_TRACE_UNIT": M.POST_TRACE_UNIT,
            "FET_V_THRESHOLD": M.FET_V_THRESHOLD,
            "FET_GM": M.FET_GM,
            "ELIGIBILITY_AMPLITUDE_ENCODING": M.ELIGIBILITY_AMPLITUDE_ENCODING,
            "ELIGIBILITY_CANONICAL_STATE": M.ELIGIBILITY_CANONICAL_STATE,
            "NEW_G0_TRAJECTORIES": M.NEW_G0_TRAJECTORIES,
            "PRODUCTION": M.PRODUCTION_MODE,
            "dt_G_s": 0.001,
        },

        "tau_e_basis": {
            "value_s": M.TAU_E,
            "plan_derivation_rejected":
                "Plan §4.2 derived 0.300 s as '300 legacy eligibility steps x "
                "dt 0.001'. That chain does not hold: bundle.py:126 "
                "eligibility_tau=300 enters decay_factor = 1 - dt/tau "
                "(bundle.py:459-460), so at dt=0.001 it is an effective time "
                "constant of 300 SECONDS, not 0.3 s — a 1000x gap (critique "
                "E-10). The numeric coincidence with 300 is not a derivation.",
            "basis_a_bio":
                "Presynaptic residual Ca2+ / short-term facilitation decays on "
                "a sub-second scale. REF: Zucker & Regehr 2002, Annu Rev "
                "Physiol 64:355 (same citation chain already used by "
                "tss/relations/history_kernel.py Q1 and "
                "nexus_v1/components/compensation.py CalciumRateIntegrator).",
            "basis_b_struct":
                "The eligibility window must be SHORTER than the decay window "
                "of the relation occurrence it marks, otherwise NC3 (TIMING "
                "CONTROL requires e_W(t_delta) ~ 0) cannot be constructed "
                "inside the existing occurrence inventory. Neighbouring "
                "project time constants: tau_2 = 0.456 s (D2-1 RelationCell "
                "measured) and tau_h = 0.600 s (H_tau frozen). "
                "tau_e = 0.300 s < tau_2 < tau_h, giving a measurable tail of "
                "~3*tau_e = 0.9 s.",
            "no_step_era_inheritance": True,
        },

        "write_polarity_basis": {
            "polarity": M.WRITE_POLARITY,
            "reason":
                "Memristor bounds are w in [0,1] (semiconductor.py:246-265). "
                "R-4 freezes w0=0.90, leaving only 0.10 headroom upward vs "
                "0.90 downward. The project has a registered failure mode for "
                "high-w clamping producing spurious asymmetry "
                "(new-component skill; memory project_memristor_saturation_"
                "edge_bug). Depletion writing avoids the w_max clamp.",
            "implementation":
                "Memristor.update(current=I_write, pre_trace=0.0, "
                "post_trace=1.0) => dw = 0.5*I*(0-1) = -0.5*I",
            "honest_note":
                "pre/post trace here carry ONLY polarity and scale; they are "
                "API constants, not physical quantities. All of the "
                "multiplicative physics lives in the TIER-2 dual-FET gate.",
            "sensitivity_unaffected":
                "dG/G = 9.9*dw/R; at w=0.90 R=1.09, a depleting dw=-0.01 moves "
                "R to 1.189 (<10% sensitivity change), still far better than "
                "the LIM-RPREC operating point w~0.109 (R=8.92).",
        },

        "thresholds": {
            "EPSILON_NUM": M.EPSILON_NUM,
            "EPSILON_E": M.EPSILON_E,
            "EPSILON_M": M.EPSILON_M,
            "EPSILON_Z": M.EPSILON_Z,
            "RETENTION_W_MIN": M.RETENTION_W_MIN,
            "floor_provenance":
                "Plan §18 priority order: deterministic replay floor -> "
                "sham-repeat difference -> numeric precision. This system is "
                "bit-exact on replay (D2-1 M6) => eps_replay = 0 => the "
                "numeric-precision floor 1e-6 governs (same as Posterior-0 "
                "EPSILON_NUM).",
            "deferred_to_step_C":
                ["EPSILON_Q", "EPSILON_SEL", "S_MIN", "predicted_Iz"],
            "deferred_reason":
                "eps_Q must be tied to the analytically reachable signal "
                "computed in Step C (plan §13.1); eps_sel / S_min / "
                "predicted_Iz depend on the measured e and M envelopes from "
                "Steps A and B. They are frozen at the end of Step C, before "
                "any factorial run (plan §17: all three thresholds "
                "pre-registered; §16: predicted_Iz stated before measurement).",
        },

        "two_windows_must_be_reported_separately": {
            "existence_window": "{t : e(t) > EPSILON_E} — canonical readout is "
                                "the capacitor voltage (plan §4.4)",
            "write_reachable_window":
                "{t : FET_e.conduct(e(t)) > 0} — the real constraint on "
                "choosing NEAR in Step D, because sub-threshold e is hard-"
                "zeroed by DEG-019 and produces exactly zero write current",
            "why": "critique E-8: 'exists' is not 'usable'. Posterior-0 Step A "
                   "hit this exact surface (membrane tau=500 steps vs "
                   "activation tau=6.4 steps, a 78x gap).",
        },

        "path_independence_R1": {
            "past_chain": "RelationOccurrencePortV1 -> build_phase_drive -> "
                          "RelationInputNeuron -> frozen SynapticBundle -> "
                          "Neuron(_membrane=Capacitor) -> e",
            "later_chain": "site23 window -> build_phase_drive -> "
                           "RelationEventAdapter -> PhysicalEntryGate -> "
                           "PhysicalHistoryKernel(H_tau^Delta) -> M",
            "enforcement": "assert_paths_independent() does object-identity "
                           "checks; W is never fed into H_tau^Delta",
        },

        "materials": {
            "W_relation_traj": M.W_RELATION_TRAJ,
            "W_occurrence_id": port.occurrence_id,
            "W_window_steps": [port.t_up, port.t_down, port.t_rearm],
            "W_lineage": port.relation_lineage,
            "delta_site23_tid_stepB": M.DELTA_S23_TID_STEPB,
            "delta_note": "Step B only demonstrates Delta -> M is physical; "
                          "the formal NEAR / TIMING CONTROL choice happens in "
                          "Step D (not in this batch)",
        },

        "execution_order": ["Step 0 preregistration + seal + ledger",
                            "Step A physical eligibility",
                            "Step B semantic erasure audit -> physical "
                            "modulation",
                            "Step C persistent baseline -> analytic readout "
                            "feasibility -> RailLatch positive control"],
        "gate_to_next_batch":
            "READY_FOR_MAIN_FACTORIAL flips to YES only if Step A, B and C all "
            "PASS (plan §34).",
    }


def main() -> int:
    M.assert_no_step_era_import()
    prereg = build_preregistration()
    seal = build_seal()
    M.ledger_init()
    p1 = M.write_json('preregistration.json', prereg)
    p2 = M.write_json('frozen_upstream_seal.json', seal)
    print("MFS0-E0 Step 0 — pre-registration written")
    print(f"  {os.path.relpath(p1, _ROOT)}")
    print(f"  {os.path.relpath(p2, _ROOT)}  ({len(seal['targets'])} targets)")
    print(f"  {os.path.relpath(M.LEDGER_PATH, _ROOT)}")
    print()
    print(f"  TIER={M.MULTIPLICATION_TIER}  M_SOURCE={M.M_SOURCE}  "
          f"TAU_E={M.TAU_E}s  W0={M.INITIAL_W}  "
          f"POLARITY={M.WRITE_POLARITY}  NEW_G0={M.NEW_G0_TRAJECTORIES}")
    print(f"  W window (t_up,t_down,t_rearm) = "
          f"{prereg['materials']['W_window_steps']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
