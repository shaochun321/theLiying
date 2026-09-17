"""exp_F1_rail_causality.py — P0-3 Rail causality test（方案 §七 + 契约 §三/§四）。

TYPE:INFRA（research/ 隔离层）

## 三个部分

A. 供电矩阵：Vrail ∈ {1.0, 0.5, 0.1, 0.0} × R_internal ∈ {0, 1, 10, 100}，
   高态初始 → 8.3τ 保持 → 记录终态/稳态 I_fb；vdd=0 期间逐步断言 I_fb==0.0
   （逐位；由 I_fb = G·vdd/(1+G·Rs) 结构保证）。
   物理预期说明：本 RC 泄漏极弱（1/R = 1.7e-3 S ≪ G_high ≈ 0.7 S），任何
   vdd>0 都足以维持高态——只有 vdd=0 必须失去维持，其余档位是实测记录。

B. 断电-恢复（契约 §三 T_off 判据）：canonical 供电 → 断电 T_off 步 →
   恢复供电 → 观察是否回高态。解析临界：
       V_res = exp(−T_off/τ_steps)，refire ⇔ V_res > V_u(离散)=0.301002506
       T_off* = 600·ln(1/V_u) ≈ 720.33 步
   T_off ≤ 720 重新点火 = DEVICE_HISTORY: CAPACITIVE_RESIDUE（电容残压物理
   残留，合法）；T_off ≥ 721 必须不回高态（无输入历史不得自动记起）。
   分界必须与解析一致（±1 步）。

C. 局部能源闭合残差收敛（契约 §四）：同一物理驱动情形在 dt、dt/10、dt/100
   下重跑，闭合残差相对值须按一阶收敛（每 dt 十倍 → 残差 ≈ 十倍缩小）
   ⇒ LOCAL_ENERGY_CLOSURE = AUDITABLE；否则 NOT_MET。

## M5-P 输出（供 f1_revalidation.py 消费）

  power_cut_zero_current  A/B 全部断电相位 I_fb 逐位 == 0.0
  power_cut_forgets       vdd=0 保持段高态衰减至低支，且恢复分界与解析一致
  energy_auditable        残差一阶收敛
  pass = 三者同时成立

输出：data/rail_causality.json, data/rail_causality_matrix.csv
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from research.A8_state_audit.candidate_config import CANONICAL, assert_fingerprint
from research.A8_state_audit.rail_latch import RailLatch

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
TAU_STEPS = 600                     # τ = R·C / dt = 0.6 s / 0.001
V_U_DISCRETE = None                 # 运行时由 fixed_points() 取（不手抄数字）


def new_latch(**over):
    kw = dict(capacitance=CANONICAL["C"], r_leak=CANONICAL["R"],
              theta=CANONICAL["theta"], gm=CANONICAL["gm"],
              n_feedback_fets=CANONICAL["n_feedback_fets"],
              v_rail=CANONICAL["v_rail"],
              rail_r_internal=CANONICAL["rail_r_internal"],
              clamp_mode=CANONICAL["clamp_mode"], clamp_gm=CANONICAL["clamp_gm"],
              clamp_threshold=CANONICAL["clamp_threshold"],
              k_in=CANONICAL["k_in"])
    kw.update(over)
    return RailLatch(**kw)


# ─────────────────────────────────────────────────────────────────────
# A. 供电矩阵
# ─────────────────────────────────────────────────────────────────────

def part_a(out: dict, rows: list) -> bool:
    print("\n[A] 供电矩阵（高态初始，保持 5000 步 ≈ 8.3τ）")
    zero_current_ok = True
    for vdd in (1.0, 0.5, 0.1, 0.0):
        for rs in (0.0, 1.0, 10.0, 100.0):
            z = new_latch(v_rail=vdd, rail_r_internal=rs)
            z._cap.charge = 1.0 * z.capacitance
            i_nonzero_when_off = 0
            for _ in range(5000):
                z.step(0.0)
                if vdd == 0.0 and z.last_i_fb != 0.0:
                    i_nonzero_when_off += 1
            basin = ("high" if z.state > 0.9
                     else ("low" if z.state < 0.1 else f"MID({z.state:.4f})"))
            if vdd == 0.0 and i_nonzero_when_off:
                zero_current_ok = False
            rows.append({"part": "A", "vdd": vdd, "rs": rs,
                         "v_final": z.state, "basin": basin,
                         "i_fb_final": z.last_i_fb,
                         "v_supply_final": z.last_v_supply,
                         "i_nonzero_when_off": i_nonzero_when_off})
        sub = [r for r in rows if r["part"] == "A" and r["vdd"] == vdd]
        print(f"  vdd={vdd:<4} " + "  ".join(
            f"Rs={r['rs']:<5g}→{r['basin']}(I={r['i_fb_final']:.3e})"
            for r in sub))
    print(f"  vdd=0 全相位 I_fb≡0（逐位）: {zero_current_ok}")
    out["matrix_zero_current_ok"] = zero_current_ok
    return zero_current_ok


# ─────────────────────────────────────────────────────────────────────
# B. 断电-恢复（T_off 扫描）
# ─────────────────────────────────────────────────────────────────────

def part_b(out: dict, rows: list) -> tuple[bool, bool]:
    z_ref = new_latch()
    v_u = next(f["v"] for f in z_ref.fixed_points() if f["stability"] == "unstable")
    t_off_star = TAU_STEPS * math.log(1.0 / v_u)
    print(f"\n[B] 断电-恢复（V_u(离散)={v_u:.9f}  解析临界 T_off*="
          f"{t_off_star:.2f} 步）")
    zero_ok = True
    boundary_measured = None
    scan = (60, 300, 600, 719, 720, 721, 723, 1200, 3000)
    for t_off in scan:
        z = new_latch()
        z._cap.charge = 1.0 * z.capacitance
        for _ in range(1000):                 # 供电保持段
            z.step(0.0)
        assert z.state > 0.9, "供电保持段高态丢失（前置失败）"
        z.v_rail = 0.0                        # 物理断电（结构：I_fb=G·0=0）
        z._rail.vdd = 0.0
        for _ in range(t_off):
            z.step(0.0)
            if z.last_i_fb != 0.0:
                zero_ok = False
        v_res = z.state
        z.v_rail = CANONICAL["v_rail"]        # 恢复供电
        z._rail.vdd = CANONICAL["v_rail"]
        for _ in range(5000):
            z.step(0.0)
        refired = z.state > 0.9
        predicted = v_res > v_u
        agree = refired == predicted
        rows.append({"part": "B", "t_off": t_off, "v_res": v_res,
                     "v_u": v_u, "refired": refired,
                     "predicted_refire": predicted, "agree": agree})
        tag = ("DEVICE_HISTORY:CAPACITIVE_RESIDUE" if refired else "forgets")
        print(f"  T_off={t_off:<5} V_res={v_res:.6f} → "
              f"{'重新点火' if refired else '不回高态'}  预测一致={agree}  [{tag}]")
        if boundary_measured is None and not refired:
            boundary_measured = t_off
    all_agree = all(r["agree"] for r in rows if r["part"] == "B")
    # 分界与解析一致（±1 步）：最后一个 refire 的 T_off 与 T_off* 取整比对
    last_refire = max((r["t_off"] for r in rows
                       if r["part"] == "B" and r["refired"]), default=None)
    boundary_ok = (last_refire is not None
                   and abs(last_refire - math.floor(t_off_star)) <= 1)
    # 长断电（≥2τ）必须失忆
    long_forget = all(not r["refired"] for r in rows
                      if r["part"] == "B" and r["t_off"] >= 1200)
    print(f"  逐点预测一致={all_agree}  实测分界 last_refire={last_refire} "
          f"vs ⌊T_off*⌋={math.floor(t_off_star)} （±1 步内: {boundary_ok}）")
    print(f"  长断电(≥2τ)不自动记起: {long_forget}")
    out["power_cut"] = {"v_u": v_u, "t_off_star": t_off_star,
                        "last_refire": last_refire, "boundary_ok": boundary_ok,
                        "all_agree": all_agree, "long_forget": long_forget,
                        "zero_current_during_off": zero_ok}
    return zero_ok, (all_agree and boundary_ok and long_forget)


# ─────────────────────────────────────────────────────────────────────
# C. 局部能源闭合残差收敛
# ─────────────────────────────────────────────────────────────────────

def part_c(out: dict) -> bool:
    print("\n[C] 局部能源闭合（同一物理情形：1 s 驱动 + 4 s 保持；dt 三档）")
    T_DRIVE, T_TOTAL, U = 1.0, 5.0, 0.4
    rels = []
    for div in (1, 10, 100):
        dt = CANONICAL["dt"] / div
        z = new_latch(dt=dt)
        n_total = int(round(T_TOTAL / dt))
        n_drive = int(round(T_DRIVE / dt))
        for n in range(n_total):
            z.step(U if n < n_drive else 0.0, dt)
        led = z.energy_ledger()
        throughput = (abs(led["feedback_energy"]) + abs(led["input_energy"])
                      + abs(led["leak_dissipation"])
                      + abs(led["clamp_dissipation"]) + abs(led["delta_stored"]))
        rel = abs(led["closure_residual"]) / max(throughput, 1e-30)
        rels.append(rel)
        print(f"  dt/{div:<4} residual={led['closure_residual']:+.6e}  "
              f"吞吐={throughput:.6e}  相对残差={rel:.3e}")
    ratio1 = rels[0] / max(rels[1], 1e-30)
    ratio2 = rels[1] / max(rels[2], 1e-30)
    first_order = (5.0 < ratio1 < 20.0) and (5.0 < ratio2 < 20.0)
    print(f"  收敛比 dt→dt/10: {ratio1:.2f}×   dt/10→dt/100: {ratio2:.2f}× "
          f"（一阶预期 ≈10×）")
    verdict = "AUDITABLE" if first_order else "NOT_MET"
    print(f"  ⇒ LOCAL_ENERGY_CLOSURE = {verdict}")
    out["energy_closure"] = {"relative_residuals": rels,
                             "ratios": [ratio1, ratio2],
                             "first_order": first_order, "verdict": verdict}
    return first_order


# ─────────────────────────────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────────────────────────────

def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    fp = assert_fingerprint(CANONICAL)
    print("=" * 70)
    print(f"P0-3 Rail causality test（fingerprint={fp}）")
    print("=" * 70)

    out: dict = {"fingerprint": fp}
    rows: list = []
    a_zero = part_a(out, rows)
    b_zero, b_forgets = part_b(out, rows)
    c_ok = part_c(out)

    m5p = {"power_cut_zero_current": a_zero and b_zero,
           "power_cut_forgets": b_forgets,
           "energy_auditable": c_ok,
           "pass": (a_zero and b_zero) and b_forgets and c_ok}
    out["M5P"] = m5p
    print("\n" + "=" * 70)
    print(f"M5-P physical support: {'PASS' if m5p['pass'] else 'FAIL'}")
    print(f"  断电零流={m5p['power_cut_zero_current']}  "
          f"断电失忆(含分界解析一致)={m5p['power_cut_forgets']}  "
          f"账本可审计={m5p['energy_auditable']}")

    with open(os.path.join(DATA_DIR, "rail_causality.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    with open(os.path.join(DATA_DIR, "rail_causality_matrix.csv"), "w",
              newline="", encoding="utf-8") as f:
        keys = sorted({k for r in rows for k in r})
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(f"\n落盘: {os.path.join(DATA_DIR, 'rail_causality.json')} / "
          f"rail_causality_matrix.csv")
    return 0 if m5p["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
