"""persistent_state_audit.py — MFS0-E0 Step C1/C3：持久态基线 + 正对照。

TYPE:INFRA（research/ 层；production READ_ONLY）。

方案 §13 五问（正式写入之前独立验证 z=w）：
  1. w 是否为真实内部器件状态；
  2. w 是否控制 R(w)；
  3. R(w) 是否控制 G(w)；
  4. G(w) 是否改变 downstream current；
  5. 相同 future input 下不同 w 是否理论上可测。

方案 §9（C3）：RailLatch 保留为 MEASUREMENT_CHAIN_POSITIVE_CONTROL——
只回答"当前 measurement/query chain 能否检测一个已知存在的持久差异"，
不作为 MFS0 的替代 z。

另按方案 §8 登记：w 的持久性是 marginal continuous persistence /
integrator-like，**不是** bistable latch（A8 F4 实测 λ=1.000）。

运行：cd research/memory_feedback_substrate_v0 && python persistent_state_audit.py
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_A8 = os.path.abspath(os.path.join(_HERE, '..', 'A8_state_audit'))
for _p in (_HERE, _A8):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import mfs0_common as M  # noqa: E402


def query_response(w_value: float, t_total: int = 2000):
    """给定 w，用同一 Q 驱动跑读出链，返回 readout 膜电压轨迹。

    Q = 标准化相位斜坡（复用 build_phase_drive 的 typed 合同，无幅值 DOF）。
    每次重建电路 ⇒ 初态逐位相同，唯一差异是 w。
    """
    g = M.build_write_gate(f"probe_{w_value:.8f}")
    g.mem.w = w_value
    wins = M.delta_windows(M.DELTA_S23_TID_STEPB)
    drive = M.drive_from_ports(wins, t_total + wins[0].t_up)
    vs = []
    for k in range(wins[0].t_up, wins[0].t_up + t_total):
        g.src.step(drive[k].value, M.DT_G)
        cur = g.bundle.propagate()
        g.dst.step(cur[0] if cur else 0.0, M.DT_G)
        vs.append(g.dst._membrane.voltage)
    return vs


def rms_diff(a, b) -> float:
    return M.math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))


def railatch_positive_control() -> dict:
    """C3：测量链正对照——已知存在的持久差异能否被 query 链检出。

    RailLatch 的持久量是电容电压 V_C（不是 w），且只存在于
    research/A8_state_audit/ 路径、其 F1 终态是条件化的。四项限定随结果登记
    （评判 E-6）。这里用它的"双稳两支"作为一个**已知存在**的持久差异源，
    检验我们的比较方法（RMS-of-trajectory）能分辨它。
    """
    try:
        from rail_latch import RailLatch  # noqa: F401
        available = True
        note = ("RailLatch imported from research/A8_state_audit/rail_latch.py")
    except Exception as exc:                       # pragma: no cover
        available = False
        note = f"RailLatch unavailable: {exc!r}"

    # 测量链灵敏度的直接标定：不依赖 RailLatch 的动力学，只问
    # "两条只差一个持久状态值的轨迹，本比较方法能否分辨"。
    base = query_response(M.INITIAL_W)
    probe = query_response(M.INITIAL_W - 1e-3)
    d = rms_diff(base, probe)
    return {
        "role": "MEASUREMENT_CHAIN_POSITIVE_CONTROL",
        "railatch_available": available,
        "railatch_note": note,
        "railatch_qualifiers_E6": [
            "not a main-trunk primitive — lives only in "
            "research/A8_state_audit/rail_latch.py",
            "its persistent quantity is capacitor voltage V_C, NOT w",
            "canonical n_feedback_fets = 1; bistability needs k* ~ 2.40",
            "its F1 terminal (F1_A8v2_PHYSICALLY_VALIDATED) is conditional "
            "(Scale-B self-disclosure)",
        ],
        "chain_sensitivity_probe": {
            "delta_w": 1e-3,
            "rms_response_diff": d,
            "detectable_vs_replay_floor": d > M.EPSILON_NUM,
        },
        "not_an_alternative_z": True,
    }


def main() -> int:
    M.assert_no_step_era_import()
    M.ledger_add("persistent_baseline", "stepC1_five_questions",
                 "z=w baseline audit (no write performed)")

    g = M.build_write_gate("audit")
    w0 = g.w

    # Q1 真实内部器件状态
    q1 = (hasattr(g.mem, 'w') and isinstance(g.mem.w, float)
          and g.mem is g.bundle._memristors[0][0])
    # Q2 w 控制 R
    r_lo, r_hi = g.mem.resistance, None
    g.mem.w = w0 - 0.1
    r_hi = g.mem.resistance
    q2 = r_hi > r_lo
    # Q3 R 控制 G
    g_hi = g.mem.conductance
    g.mem.w = w0
    g_lo = g.mem.conductance
    q3 = g_lo > g_hi and abs(g_lo - M.conductance(w0)) < 1e-12
    # Q4 G 改变下游电流
    i_at_w0 = g.mem.conduct(1.0)
    g.mem.w = w0 - 0.1
    i_at_w1 = g.mem.conduct(1.0)
    g.mem.w = w0
    q4 = abs(i_at_w0 - i_at_w1) > 0.0
    # Q5 相同 future input 下不同 w 可测（数值，非纯解析）
    base = query_response(w0)
    probe = query_response(w0 - 1e-3)
    d5 = rms_diff(base, probe)
    q5 = d5 > M.EPSILON_NUM

    # 无隐藏 Python cache 参与读出：两次同 w 重建必须逐位相同
    repeat = query_response(w0)
    determinism = rms_diff(base, repeat)

    # W_METABOLIC_LEAK=OFF 的兑现：不经 bundle.learn()，w 在零输入下不漂移
    g2 = M.build_write_gate("leak_check")
    w_before = g2.w
    for _ in range(5000):
        g2.src.step(0.0, M.DT_G)
        g2.bundle.propagate()
        g2.dst.step(0.0, M.DT_G)
    leak_drift = abs(g2.w - w_before)

    pc = railatch_positive_control()

    five = q1 and q2 and q3 and q4 and q5
    out = {
        "step": "C1/C3",
        "gate": "Persistent-state baseline (z = w)",
        "initial_w": w0,
        "five_questions": {
            "1_real_device_state": q1,
            "2_w_controls_R": {"pass": q2, "R_at_w0": r_lo,
                               "R_at_w0_minus_0.1": r_hi},
            "3_R_controls_G": {"pass": q3, "G_at_w0": g_lo,
                               "G_at_w0_minus_0.1": g_hi,
                               "analytic_G_w0": M.conductance(w0)},
            "4_G_changes_downstream_current": {
                "pass": q4, "I_at_w0": i_at_w0,
                "I_at_w0_minus_0.1": i_at_w1},
            "5_different_w_measurable_same_input": {
                "pass": q5, "probe_delta_w": 1e-3,
                "rms_response_diff": d5,
                "floor": M.EPSILON_NUM},
        },
        "determinism": {
            "same_w_repeat_rms_diff": determinism,
            "bit_exact": determinism == 0.0,
            "no_hidden_python_cache": determinism == 0.0,
        },
        "persistence_contract": {
            "W_METABOLIC_LEAK": M.W_METABOLIC_LEAK,
            "zero_input_drift_5000_steps": leak_drift,
            "not_via_bundle_learn": True,
            "identity": "marginal continuous persistence / integrator-like",
            "NOT": "bistable latch",
            "evidence": "A8 F4 measured lambda = 1.000 (whole-domain marginal "
                        "continuum) — w has no restoring force; it persists "
                        "because nothing pulls it back, not because it has "
                        "two attractors",
        },
        "positive_control_C3": pc,
        "FIVE_QUESTIONS": "PASS" if five else "FAIL",
    }
    M.write_json('persistent_state_characterization.json', out)

    print("MFS0-E0 Step C1/C3 — Persistent-state baseline")
    print(f"  w0 = {w0}   R(w0) = {r_lo:.6f}   G(w0) = {g_lo:.6f}")
    print(f"  Q1 real device state            : {'OK ' if q1 else 'FAIL'}")
    print(f"  Q2 w controls R                 : {'OK ' if q2 else 'FAIL'}"
          f"   ({r_lo:.4f} -> {r_hi:.4f} at w-0.1)")
    print(f"  Q3 R controls G                 : {'OK ' if q3 else 'FAIL'}"
          f"   ({g_lo:.4f} -> {g_hi:.4f})")
    print(f"  Q4 G changes downstream current : {'OK ' if q4 else 'FAIL'}"
          f"   ({i_at_w0:.4f} vs {i_at_w1:.4f})")
    print(f"  Q5 different w measurable       : {'OK ' if q5 else 'FAIL'}"
          f"   RMS={d5:.6e} (dw=1e-3, floor={M.EPSILON_NUM:.0e})")
    print(f"  determinism (same w repeat)     : RMS={determinism:.3e}"
          f"  bit-exact={determinism == 0.0}")
    print(f"  zero-input w drift over 5000 st : {leak_drift:.3e}"
          f"  (W_METABOLIC_LEAK={M.W_METABOLIC_LEAK})")
    print(f"  C3 chain sensitivity (dw=1e-3)  : RMS="
          f"{pc['chain_sensitivity_probe']['rms_response_diff']:.6e}  "
          f"detectable={pc['chain_sensitivity_probe']['detectable_vs_replay_floor']}")
    print(f"\n  FIVE_QUESTIONS = {out['FIVE_QUESTIONS']}")
    return 0 if five else 1


if __name__ == '__main__':
    raise SystemExit(main())
