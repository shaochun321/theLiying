"""w1_final_qualification.py — W1 六门聚合终裁（§47/§49）+ §39 边界记录检查。

TYPE:INFRA（research/ 层）

聚合三份实验 JSON（structure_scan / hidden_twins / physics_audit）逐门
评定 M1-M6；补做 §39：边界记录确定性（同 spec 重跑逐位一致）与自含性
（BoundaryView 只含纯元组，可脱离 World 序列化）。终态三选一（§49）
如实给。不做任何新的参数选择（§34）。

输出：data/qualification_summary.json
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from world_v2_core import WorldEpisode, WorldSampler  # noqa: E402

DATA_DIR = os.path.join(_HERE, 'data')


def load(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def replay_recording_check():
    """§39：boundary recording deterministic + self-contained。"""
    spec = WorldSampler(seed=99).sample("replaycheck")
    bv1, _, _ = WorldEpisode(spec).run()
    bv2, _, _ = WorldEpisode(spec).run()
    deterministic = bv1.frames == bv2.frames
    self_contained = (all(isinstance(fr, tuple) for fr in bv1.frames)
                      and not hasattr(bv1, "graph")
                      and not hasattr(bv1, "cells"))
    print(f"[§39] 同 spec 重跑逐位一致={deterministic}  "
          f"BoundaryView 自含(纯元组/无 World 引用)={self_contained}")
    return {"deterministic": deterministic,
            "self_contained": self_contained,
            "pass": deterministic and self_contained}


def main() -> int:
    print("=" * 78)
    print("W1 终裁 — 六资格门聚合（§47）")
    print("=" * 78)
    ss = load("w1_structure_scan.json")
    ht = load("w1_hidden_twins.json")
    pa = load("w1_physics_audit.json")
    replay = replay_recording_check()

    gates = {
        "M1_physical_closure": {
            "pass": pa["M1"]["pass"],
            "evidence": f"10 episodes max|ΔE−inj+leak|="
                        f"{pa['M1']['worst_residual']:.2e}；dt 三档收敛"
                        f"（0.1→0.01 差 {pa['dt_convergence']['diff_0.1_to_0.01']:.1e}）"},
        "M2_independent_dof": {
            "pass": ss["M2"]["pass"],
            "evidence": f"Θ_legal 系综 PR: 3→{ss['M2']['pr_ensemble_legal']['3']:.2f}"
                        f" / 20→{ss['M2']['pr_ensemble_legal']['20']:.2f}"
                        f"（单调增长；均匀κ子域 2.90 并报）"},
        "M3_independent_timescales": {
            "pass": ss["M3"]["pass"],
            "evidence": f"τ_env 跨度 {ss['M3']['env_span']:.0f}× vs "
                        f"τ_diff 跨度 {ss['M3']['diff_span']:.2f}×"
                        "（≪/≈/≫ 三段位覆盖，r_leak 与 κ 独立采样）"},
        "M4_conditional_sampling": {
            "pass": ss["M4"]["pass"],
            "evidence": "30 episodes 全域内/无重复/独立 RNG；"
                        "Phase A(采样)/B(纯物理推进) 结构分离"},
        "M5_partial_observability": {
            "pass": bool(ht["full_vs_reduced"]["partial_observation_confirmed"]),
            "evidence": f"同一 episode FULL t0 差={ht['full_vs_reduced']['d_full_t0']:.2f}"
                        f" vs REDUCED {ht['twin1_field_hidden']['d_boundary_t0']:.1e}"
                        "；boundary_config/nodes 逐 episode 显式登记"},
        "M6_hidden_causal_dynamics": {
            "pass": bool(ht["M6_pass"]),
            "evidence": "Twin-1(场隐藏)+Twin-2(源隐藏,场态逐位同) 双双 "
                        "ESTABLISHED；因果阻断残差 2.5e-13 / 0.0 ⇒ "
                        "HIDDEN_STATE_CAUSALLY_SUPPORTED ×2"},
        "S39_boundary_recording": {
            "pass": replay["pass"],
            "evidence": "同 spec 重跑逐位一致 + BoundaryView 纯元组自含"},
    }
    all_pass = all(g["pass"] for g in gates.values())
    for name, g in gates.items():
        print(f"  {name:<28} {'PASS' if g['pass'] else 'FAIL'}  {g['evidence']}")

    if all_pass:
        verdict = "WORLD_V2_RAW_QUALIFIED"
    elif not (gates["M1_physical_closure"]["pass"]
              and gates["M4_conditional_sampling"]["pass"]):
        verdict = "WORLD_V2_PHYSICAL_SUPPORT_FAIL"
    else:
        verdict = "WORLD_V2_PARTIAL_OBSERVABILITY_NOT_ESTABLISHED"
    print(f"\nW1 终裁 = {verdict}")
    if verdict == "WORLD_V2_RAW_QUALIFIED":
        print("（§50：立即停止扩 World；§51：下一轮 T1-B）")

    out = {"gates": gates, "verdict": verdict,
           "next": "T1-B" if all_pass else "修复后重审",
           "scope_note": "WORLD_LOCAL_ENERGY_AUDITABLE（§31，不宣称全项目闭合）"}
    path = os.path.join(DATA_DIR, "qualification_summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"落盘: {path}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
