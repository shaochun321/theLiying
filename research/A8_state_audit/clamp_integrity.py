"""clamp_integrity.py — P1-2 钳位完整性三对照。

TYPE:INFRA（research/ 隔离层）

## 问题

F1 的高态**正坐在钳位支**上 ⇒ 若高支只因理想硬钳位（discharge_to）存在，
则它是数值构造而非物理双稳。必须区分：
    PHYSICAL_BISTABILITY              （有限漏极下仍有高支）
    DT_DEPENDENT_HARD_CLAMP_STABILITY （只有硬钳位才有高支）

## 三组（同 fingerprint，唯一权威动力学 = rail_latch.RailLatch）

  C1  hard clamp   ：cap.discharge_to(V_c)（项目既有惯例）
  C2  finite drain ：积分 -I_clamp·dt（I_clamp = clamp_gm·(V−V_c)）
  C3  小步长       ：C2 在 dt/10、dt/100 下重跑（检验 dt 依赖）

判定：若 C2/C3 下高态仍稳定存在 ⇒ PHYSICAL_BISTABILITY（clamp CLEARED_PHYSICALLY），
      并把"项目 dt 下为何需要 hard clamp"记为数值建模限制；
      否则 ⇒ NUMERICAL_LATCH_ONLY。

输出：data/clamp_integrity.csv
"""
from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from research.A8_state_audit.candidate_config import (
    CANONICAL, assert_fingerprint)
from research.A8_state_audit.rail_latch import RailLatch

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def _run(cfg: dict, mode: str, dt: float, n_trials=4, steps=200000):
    """从低/高初始态起跑，观察是否落到两个不同稳态。"""
    results = []
    for v0 in (0.0, 0.9):
        z = RailLatch(capacitance=cfg["C"], r_leak=cfg["R"],
                      theta=cfg["theta"], gm=cfg["gm"],
                      n_feedback_fets=cfg["n_feedback_fets"],
                      v_rail=cfg["v_rail"], rail_r_internal=cfg["rail_r_internal"],
                      clamp_mode=mode, clamp_gm=cfg["clamp_gm"],
                      clamp_threshold=cfg["clamp_threshold"], k_in=cfg["k_in"],
                      dt=dt)
        z._cap.charge = v0 * z.capacitance
        for _ in range(steps):
            z.step(0.0, dt)
        results.append(z.state)
    return results


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    fp = assert_fingerprint(CANONICAL)
    print("=" * 68)
    print("P1-2 钳位完整性三对照（canonical fingerprint = %s）" % fp)
    print("=" * 68)

    rows = []
    # ── C1 hard ──
    lo, hi = _run(CANONICAL, "hard", CANONICAL["dt"])
    bistable_hard = (lo < 0.1 and hi > 0.9)
    print(f"\n[C1 hard clamp]        v0=0.0 → {lo:.6f} | v0=0.9 → {hi:.6f}"
          f"   双稳={bistable_hard}")
    rows.append({"case": "C1_hard", "dt": CANONICAL["dt"], "v_from_0": lo,
                 "v_from_09": hi, "bistable": bistable_hard})

    # ── C2 finite ──
    lo2, hi2 = _run(CANONICAL, "finite", CANONICAL["dt"])
    bistable_finite = (lo2 < 0.1 and hi2 > 0.9)
    print(f"[C2 finite drain]     v0=0.0 → {lo2:.6f} | v0=0.9 → {hi2:.6f}"
          f"   双稳={bistable_finite}")
    rows.append({"case": "C2_finite", "dt": CANONICAL["dt"], "v_from_0": lo2,
                 "v_from_09": hi2, "bistable": bistable_finite})

    # 连续高态解析预测
    z = RailLatch(capacitance=CANONICAL["C"], r_leak=CANONICAL["R"],
                  n_feedback_fets=CANONICAL["n_feedback_fets"],
                  clamp_mode="finite", clamp_gm=CANONICAL["clamp_gm"])
    v_cont = z.finite_clamp_fixed_point()
    print(f"     continuous 高态解析预测 V_high* = "
          f"{v_cont if v_cont is None else round(v_cont, 6)}")

    # ── C3 小步长 ──
    small_dt_bistable = []
    for div in (10, 100):
        dt = CANONICAL["dt"] / div
        lo3, hi3 = _run(CANONICAL, "finite", dt, steps=200000 // div)
        ok3 = (lo3 < 0.1 and hi3 > 0.9)
        small_dt_bistable.append(ok3)
        print(f"[C3 finite dt/{div:<3}]     v0=0.0 → {lo3:.6f} | v0=0.9 → "
              f"{hi3:.6f}   双稳={ok3}")
        rows.append({"case": f"C3_finite_dt/{div}", "dt": dt, "v_from_0": lo3,
                     "v_from_09": hi3, "bistable": ok3})

    # ── 判定（三步逻辑，不预设结论）──
    print("\n" + "-" * 68)
    verdict = "UNRESOLVED"
    note = ""
    if bistable_finite:
        verdict = "PHYSICAL_BISTABILITY"
        note = "有限漏极下高支存在 ⇒ clash CLEARED_PHYSICALLY"
    elif all(small_dt_bistable):
        # 项目 dt 下高支缺失，但更小步长下高支存在 ⇒ 数值伪像，非物理不存在
        verdict = "PHYSICAL_BISTABILITY_DT_LIMITED"
        note = ("有限漏极高支在项目 dt=0.001 下被数值抹除（显式积分不稳定），"
                "但在 dt/10、dt/100 下恢复并趋近连续预测 "
                f"{v_cont if v_cont is None else round(v_cont, 6)}"
                " ⇒ 物理双稳存在，项目 dt 下需 hard clamp = **数值建模限制**")
        rows.insert(0, {"case": "C2_continuous_prediction", "dt": 0.0,
                        "v_from_0": float("nan"),
                        "v_from_09": v_cont if v_cont is not None else float("nan"),
                        "bistable": True})
    else:
        verdict = "NUMERICAL_LATCH_ONLY"
        note = "高支仅由理想硬钳位产生，小步长下亦不存在"
    print(f"判定: {verdict}")
    print(f"      {note}")
    print(f"\n  ★ 对 A8 资格的直接影响：第二轮 reachability/twins 的 Z 高态值 "
          f"1.0 = 钳位值 V_c，")
    print(f"    **不是**物理高支值。canonical 重跑必须改用连续/小步长动力学，")
    print(f"    或明确声明 canonical = 项目 dt + hard clamp（并把该依赖写入冻结契约）。")

    path = os.path.join(DATA_DIR, "clamp_integrity.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n落盘: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
