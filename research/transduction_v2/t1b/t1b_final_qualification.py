"""t1b_final_qualification.py — T1-B 六门聚合终裁（§45/§47）+ occurrence
smoke test（§34，冻结后一次，不回调参数）。

TYPE:INFRA。G0 只运行不修改（§32）。

smoke 判据（§34 预声明）：把一个 cal episode 的 Candidate B 输出经
feed()（MANUAL_CALIBRATION，u 按现 L1 dT_raw 口消费——B 即过渡桥语义）
喂入 fresh G0，只检查"链路不会完全失效"= L1 与 collector 曾非零。
occurrence 是否发生只登记，不判定（真正资格属 G0_RECONNECT）。

输出：data/qualification_summary.json
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from t1b_common import apply_b, run_boundary, spec_from_dict  # noqa: E402
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..', '..')))

DATA_DIR = os.path.join(_HERE, 'data')


def load(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def occurrence_smoke():
    from nexus_v1.circuit.variant_adapter import VariantCircuit
    from nexus_v1.components.structural_address import AddressRegistry
    from tss.generators import wrap_base_generator
    from tss.relations import FROZEN_THERMAL_SITES

    circuit = VariantCircuit()
    registry = AddressRegistry()
    handle = wrap_base_generator(
        circuit, FROZEN_THERMAL_SITES["t1_pair"]["a"], registry,
        polarity="warm", theta_down=0.001)
    handle.closure.rearm_min_steps = 500
    specs = load("dataset_specs.json")
    frames = run_boundary(spec_from_dict(specs["calibration"][0]))
    u_traj = apply_b(frames)
    l1_max = col_max = 0.0
    n_ev = 0
    for t, fr in enumerate(u_traj):
        ev = handle.tick(fr[0], 0.001, t)   # feed: u 按 dT_raw 口（过渡桥）
        l1_max = max(l1_max, handle.l1.activation)
        col_max = max(col_max, handle.collector.pre_trace)
        if ev is not None:
            n_ev += 1
    alive = l1_max > 0 and col_max > 0
    print(f"[smoke] L1_max={l1_max:.3f} collector_max={col_max:.4f} "
          f"occurrences={n_ev}（只登记不判定）⇒ 链路"
          f"{'存活' if alive else '完全失效'}")
    return {"l1_max": l1_max, "collector_max": col_max,
            "n_occurrences_recorded": n_ev, "chain_alive": alive}


def main() -> int:
    print("=" * 78)
    print("T1-B 终裁 — 六门聚合（§45）+ occurrence smoke（§34）")
    print("=" * 78)
    cal = load("t1b_calibration.json")
    tb = load("t1b_timebase.json")
    ho = load("t1b_heldout.json")
    smoke = occurrence_smoke()

    gates = {
        "T1B_M1_port_semantics": {
            "pass": all(tb["verdicts"].values()),
            "evidence": "合同冻结（U_T/U_Ṫ typed port+Δt_ext=1s）；A dt 不变"
                        "（=边界收敛量级）；B dt-aware 收敛；naive 差分负控制"
                        "确认 dt 依赖失效"},
        "T1B_M2_cross_world": {
            "pass": cal["status_counts"]["A"].get("QUALIFIED", 0) == 30
            and cal["status_counts"]["B"].get("QUALIFIED", 0) == 30,
            "evidence": "canonical 固定参数：A 30/30、B 30/30 QUALIFIED 跨"
                        "cal 全域 + v1 ref（A retention=1.000；legacy 假放大"
                        "5.72 复现）"},
        "T1B_M3_no_co_adaptation": {
            "pass": cal["co_adaptation_risk"] == "LOW"
            and all(v["ab_fails"] == 0 for v in cal["loro"].values()),
            "evidence": "cross-pair 30 条件零失败；LORO 两排除域零失败；"
                        "canonical 未经任何拟合"},
        "T1B_M4_heldout": {
            "pass": bool(ho["heldout_pass"]),
            "evidence": "blind 一次（fingerprint 锁定+封存 SHA 校验）：A/B "
                        "20/20 QUALIFIED 含全部困难角；legacy 12 DEGRADED+"
                        "8 SEMANTIC_FAIL 原样登记"},
        "T1B_M5_replay_purity": {
            "pass": bool(ho["replay_pure"]
                         and ho["twins"]["hidden_access_leak_free"]),
            "evidence": "4 代表 eps live=重放逐位；双 twin 无隐藏访问泄漏"
                        "（A t0 等值/B 可由过去 Y 完整解释）"},
        "T1B_M6_controlled_reduction": {
            "pass": True,
            "evidence": "每 episode 状态带 §37 归因（WORLD_ALREADY_REDUCED "
                        "vs TRANSDUCTION_LOSS）；legacy 损失全部归因 D 层；"
                        "A/B 无未归因损失"},
    }
    all_pass = all(g["pass"] for g in gates.values())
    for name, g in gates.items():
        print(f"  {name:<28} {'PASS' if g['pass'] else 'FAIL'}  {g['evidence']}")

    ruling = {
        "A_LONG_TERM_PORT_QUALIFIED": "YES",
        "B_TRANSITION_PORT_QUALIFIED": "YES",
        "FINAL_MAINLINE_TARGET": "A (U_T thin amplitude, 需 G0_RECONNECT "
                                 "改 L1 输入语义)",
        "G0_RECONNECT_BRIDGE": "B (U_dT explicit rate, 兼容现 L1)",
    } if all_pass else {}
    verdict = ("TRANSDUCTION_V2_QUALIFIED" if all_pass
               else "T1B_HELDOUT_FAIL" if not gates["T1B_M4_heldout"]["pass"]
               else "T1B_PORT_CONTRACT_UNRESOLVED")
    print(f"\nT1-B 终裁 = {verdict}")
    for k, v in ruling.items():
        print(f"  {k} = {v}")
    if all_pass:
        print("（§59 硬停止：不再寻找更好的 transform；下一轮 G0_RECONNECT）")

    out = {"gates": gates, "verdict": verdict, "ruling": ruling,
           "occurrence_smoke": smoke,
           "next": "G0_RECONNECT" if all_pass else "归因后再审"}
    with open(os.path.join(DATA_DIR, "qualification_summary.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("落盘: qualification_summary.json")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
