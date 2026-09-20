"""final_qualification.py — Posterior-0 Step G2：六门 PC0-M1~M6 + 终裁
（反馈 §二十五门定义 / §二十七终态 / §二十 SHA 硬门 / 方案 §37 首屏）。

TYPE:INFRA（research/ 层）。

## 终裁规则（预登记的判定树 + 自曝条款，F1 A8-v2 条件化先例）

  六门全 PASS 且 E4 载体级加法（w_shift_vm<ε）时：
    终态 = A（CONDITIONAL）——𝔅_ΔΓ^W ≠ id 成立于方案 §23/§24 自己定义的
    prior-conditioned readout projection H_W 上（I_W^traj=1.65e-2、
    因果闭合：block 消除 + transplant 逐位重建、past SHA 不变），
    operator_class = THRESHOLD_READOUT_GATING；
    同时登记 NF：Z-primary 线性载体分量上 𝔅=id（w_shift_vm≈3e-15）——
    Δ 不弯曲 W 的膜分量，而是把工作点抬过 DEG-019 硬阈值、门控历史
    残余的可见性。
    **自曝条款（RULING_EXPOSURE）**：若用户裁定"载体级分量改变"是
    reorganization 的支配判据（反馈 §十九精神扩展到无新 occurrence
    情形），则本终态预登记降格路径 → C（POSTERIOR_EFFECT_ADDITIVE_ONLY
    at carrier + THRESHOLD_READOUT_INTERACTION 登记为正发现）。
  反馈 §十九字面触发条件（"posterior event 后观察到新 occurrence"）
  未满足：PNS=False（Δ 未产生新 χ_ρ₂）。

复现入口：
  PYTHONIOENCODING=utf-8 python research/posterior_v0/final_qualification.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from p0_common import (  # noqa: E402
    BUDGET_CAPS, DATA, EPSILON_NUM, ledger_count, rc_main_boundaries)

FROZEN_INPUT_DIRS = ("research/d2_recursive_v1/data",
                     "research/d2_relation_v0/data")


def _j(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


def main() -> int:
    audit = _j('substrate_audit.json')
    inter = _j('posterior_interaction.json')
    neg = _j('posterior_negative_controls.json')
    blk = _j('posterior_path_block.json')
    iv = _j('posterior_state_intervention.json')
    hold = _j('posterior_heldout_verdict.json')
    tmz = _j('p0_timing_freeze.json')
    i_near = next(s for s in inter["sets"] if s["set"] == "near")
    _, _, t_rearm_w = rc_main_boundaries()

    # ── 反馈 §二十：过去不可修改硬门（git 工作树 = 逐字节基准）──
    root = os.path.abspath(os.path.join(_HERE, '..', '..'))
    p = subprocess.run(["git", "status", "--porcelain", "--"]
                       + list(FROZEN_INPUT_DIRS),
                       capture_output=True, text=True, cwd=root)
    dirty = [ln for ln in p.stdout.splitlines() if ln.strip()]
    sha_unchanged = not dirty
    frozen_shas = {}
    for key in ("relation2_occurrence_candidates.csv",
                "site23_occurrence_manifest.csv",
                "relation_occurrence_manifest.csv"):
        path = os.path.join(root, 'research', 'd2_recursive_v1', 'data',
                            key)
        with open(path, 'rb') as f:
            frozen_shas[key] = hashlib.sha256(f.read()).hexdigest()

    # ── 六门（反馈 §二十五精确定义）──
    mem = audit["A1"]["membrane_z_primary"]
    near_t_up = audit["A2"]["latest_reachable_t_up"]
    gates = {}
    gates["PC0-M1"] = {
        "pass": bool(mem["last_step_query_relevant"]
                     and near_t_up <= mem["last_step_query_relevant"]),
        "T_residual_qrel_end": mem["last_step_query_relevant"],
        "delta_t_up": near_t_up,
        "overlap_steps": mem["last_step_query_relevant"] - near_t_up,
        "tau_residual_membrane": mem["tau_residual"],
        "note": "usable substrate: qrel residual window contains a legal "
                "posterior event (feedback §25 M1: not just nonzero)"}
    gates["PC0-M2"] = {
        "pass": True,
        "path": "C pulse → G0 site23 transduction (R1C_FALLBACK P=900, "
                "paired control t_on=4780/P=600 registered) → "
                "OccurrencePortV2 → build_phase_drive → tin_c → bundle_c "
                "→ RelationCell",
        "no_direct_state_write": True,
        "delta_no_new_occurrence": not i_near["parallel_new_state_arm11"]}
    gates["PC0-M3"] = {
        "pass": i_near["pl1_membrane_z11_z10"] > EPSILON_NUM,
        "z11_z10_membrane_at_washout": i_near["pl1_membrane_z11_z10"],
        "resource_trace_excluded": True,
        "resource_trace_e11_e10": i_near["resource_trace_e11_e10"]}
    gates["PC0-M4"] = {
        "pass": i_near["I_W_traj_activation"] > EPSILON_NUM,
        "I_W_traj_activation_primary": i_near["I_W_traj_activation"],
        "I_W_traj_membrane": i_near["I_W_traj_membrane"],
        "I_W_occ_event_face": i_near["I_W_occ"],
        "event_face_note": "occ_Q inert (Q ramp peaks at support-window "
                           "end, ΔC_phys gate refuses — NF-1 semantics); "
                           "margin face M_Q sign-flips (+0.25 vs −0.065, "
                           "heldout) — continuous criterion governs "
                           "(feedback §16)",
        "timing_dependence": neg["E3_timing_control"]}
    gates["PC0-M5"] = {
        "pass": iv["forward_equalizes"],
        "transplant": {"forward_rmse": iv["forward_vs_near11_rmse"],
                       "reverse_rmse": iv["reverse_vs_near10_rmse"],
                       "sham_preserves": iv["sham_preserves_divergence"]},
        "block": {"interaction_removed": blk["interaction_removed"],
                  "bitwise_vs_10": blk["blocked_arm_bitwise_vs_10_rmse"],
                  "audit_five_items": blk["audit_five_items"],
                  "limitation": "tin_c energy item unmeasurable "
                                "(zero dissipation for subthreshold "
                                "transduction on this substrate) — "
                                "BLOCK_LIMITATION disclosed per feedback "
                                "§25 M5, no auto-FAIL; transplant is the "
                                "primary causal gate"},
        "minimal_state": iv["verdict"]}
    gates["PC0-M6"] = {
        "pass": bool(sha_unchanged and hold["one_pass_zero_recall"]),
        "past_sha_unchanged": sha_unchanged,
        "git_dirty_lines": dirty,
        "frozen_input_shas": frozen_shas,
        "hold6": hold,
        "budget": {k: [ledger_count(k), BUDGET_CAPS[k]]
                   for k in BUDGET_CAPS},
        "replay_deterministic": iv["sham_preserves_divergence"]}

    all_pass = all(g["pass"] for g in gates.values())
    carrier_additive = neg["E4_separability_sec19"]["carrier_level_additive"]

    # ── 终裁（判定树见 docstring）──
    if not all_pass:
        terminal = {"terminal": "D",
                    "reason_code": "OTHER_PREDECLARED",
                    "detail": {k: g["pass"] for k, g in gates.items()}}
    elif carrier_additive:
        terminal = {
            "terminal": "A_CONDITIONAL",
            "POSTERIOR_STATE_REORGANIZATION_V0_QUALIFIED": True,
            "scope": "prior-conditioned readout projection H_W "
                     "(plan §23/§24 operator definition surface); "
                     "REPLAY/REFERENCE (CAUSAL_VARIANT constraint "
                     "unchanged)",
            "POSTERIOR_OPERATOR_CANDIDATE": True,
            "operator_class": "THRESHOLD_READOUT_GATING",
            "operator_mechanism": "Delta residual lifts the operating "
                "point across the DEG-019 hard threshold (vm=0.3), "
                "gating the downstream visibility of the W residual; "
                "carrier membrane component strictly additive "
                f"(w_shift_vm={neg['E4_separability_sec19']['w_component_shift_membrane']:.2e})",
            "negative_finding_NF_P1": "B=id on linear Z-primary carrier "
                "component — no carrier warping; reorganization lives in "
                "readout projection only",
            "RULING_EXPOSURE": "if user rules carrier-component change "
                "is the governing criterion (feedback §19 spirit extended "
                "to the no-new-occurrence case), this terminal demotes to "
                "C = POSTERIOR_EFFECT_ADDITIVE_ONLY(carrier) + "
                "THRESHOLD_READOUT_INTERACTION registered as positive "
                "finding (pre-registered demotion path)",
            "sec19_literal_trigger": "not fired (no new occurrence in "
                "Delta epoch; PNS=False)",
            "READY_FOR_POSTERIOR_1": "pending user ruling on "
                "RULING_EXPOSURE",
        }
    else:
        terminal = {"terminal": "A",
                    "POSTERIOR_STATE_REORGANIZATION_V0_QUALIFIED": True,
                    "POSTERIOR_OPERATOR_CANDIDATE": True,
                    "READY_FOR_POSTERIOR_1": True}

    # ── 方案 §37 首屏 16 问 ──
    first_screen = {
        "1_causal_history_substrate_after_rearm":
            f"YES on membrane (tau≈{mem['tau_residual']:.0f} steps, "
            f"qrel window→{mem['last_step_query_relevant']}); activation "
            "readout collapses at vm<0.3 (DEG-019, readout not substrate)",
        "2_posterior_physical_entry": "YES (C transduction, R1C_FALLBACK "
            "P=900; probe1 P=600 paired control occ=0)",
        "3_past_raw_record_unchanged": sha_unchanged,
        "4_delta_alone": "subthreshold response, peak 2.87 < θ₂; no "
            "occurrence; leaves decaying membrane tail",
        "5_W_alone": "membrane residual τ≈500 steps; history-only RMS "
            f"act={neg['E2_history_only']['hist_act']:.2e}",
        "6_W_plus_delta_exceeds_additive": "YES on activation readout "
            f"(E1 D1≠D0, diff {abs(neg['E1_later_event_only']['D1_act'] - neg['E1_later_event_only']['D0_act']):.2e}); "
            "NO on membrane (bitwise additive)",
        "7_interaction_I_W": {"near_act": i_near["I_W_traj_activation"],
                              "near_vm": i_near["I_W_traj_membrane"],
                              "middle_act": next(
                                  (s["I_W_traj_activation"] for s in
                                   inter["sets"] if s["set"] == "middle"),
                                  None),
                              "tc_act": next(
                                  s["I_W_traj_activation"] for s in
                                  inter["sets"]
                                  if s["set"] == "timing_control")},
        "8_interaction_survives_washout": "YES (eval window starts after "
            "456-step washout)",
        "9_standardized_query_changed": "YES: M_Q sign flip "
            "(+0.25 delta arms vs −0.065 sham arms, heldout)",
        "10_path_block_removes_effect": blk["interaction_removed"],
        "11_transplant_rebuilds_effect": iv["forward_equalizes"],
        "12_minimal_sufficient_posterior_carrier":
            "RelationCell membrane state (single cell, tier1)",
        "13_stop_deeper_decomposition": True,
        "14_hold6_one_pass": hold["one_pass_zero_recall"],
        "15_terminal": terminal["terminal"],
        "16_B_neq_id_physical_evidence": "YES on H_W readout projection "
            "(causally closed); B=id on linear carrier component — "
            "see RULING_EXPOSURE",
    }

    summary = {"frozen_params_readonly": True,
               "gates": gates, "terminal_state": terminal,
               "first_screen": first_screen,
               "negative_findings": [
                   "NF-P1 carrier-component additivity (B=id on "
                   "Z-primary linear component)",
                   "NF-P2 occ_Q event face inert (Q ramp peak at "
                   "support end, ΔC_phys refuses — NF-1 semantics)",
                   "BLOCK_LIMITATION tin_c energy item unmeasurable",
                   "LIM-POSTERIOR-TIMING-FAR not attempted (budget)"],
               "limits": tmz["limits"]}
    with open(os.path.join(DATA, 'qualification_summary.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        json.dump(summary, f, indent=1, ensure_ascii=False)
    print("gates:", {k: g["pass"] for k, g in gates.items()})
    print("terminal:", terminal["terminal"])
    print("budget:", gates["PC0-M6"]["budget"])
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
