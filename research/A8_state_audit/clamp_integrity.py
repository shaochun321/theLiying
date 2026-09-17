"""clamp_integrity.py — P1-2 钳位完整性（第四轮：等物理时长修正）。

TYPE:INFRA（research/ 隔离层）

## 第四轮勘误（方案 §十二）

第三轮版本 `steps = 200000 // div, dt = 0.001/div` 使总物理时长随 div²
缩水：div=100 档只积分 0.02 s = 0.033τ（τ=RC=0.6 s），其"高支 1.2586 趋近
连续预测"的读数是**未收敛值**。本版修正为等物理时长：

    steps = T_PHYSICAL / dt      （所有 dt 档积分同样的物理时间）

T_PHYSICAL = 20.0 s ≈ 33τ：从 v0=0.9 至稳态的弛豫在数 τ 内完成，33τ 提供
充分裕量；dt/1000 档为 2×10⁷ 步，是纯 Python 可承受上限。

## 三组对照（同 fingerprint，唯一权威动力学 = rail_latch.RailLatch）

  C1  hard clamp   ：cap.discharge_to(V_c)（项目既有惯例）
  C2  finite drain ：积分 -I_clamp·dt（I_clamp = clamp_gm·(V−V_c)）
  C3  小步长       ：C2 在 dt/10、dt/100、dt/1000 下重跑（等物理时长）

每档报告：
  convergence_error = |V_final(v0=0.9) − V_fp_discrete(dt)|
  fixed_point_error = |V_fp_discrete(dt) − V_continuous|

判定：C2/C3 下高态仍稳定存在 ⇒ PHYSICAL_BISTABILITY（或 DT_LIMITED）；
否则 ⇒ NUMERICAL_LATCH_ONLY。

## Legacy N=3 勘误段

canonical 已最小化为 N=1（连续高支 ≈1.0776）。为复核第三轮
PHYSICAL_BISTABILITY_DT_LIMITED（N=3，连续高支 ≈1.2997）在等物理时长下
是否仍成立，附 LEGACY_N3_DIAG 对照段——仅勘误用，不进资格结论。

输出：data/clamp_integrity.csv
"""
from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from research.A8_state_audit.candidate_config import (
    CANONICAL, LEGACY_N3_DIAG, assert_fingerprint)
from research.A8_state_audit.rail_latch import RailLatch

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
T_PHYSICAL = 20.0          # s；≈33τ（τ=0.6 s），见模块 docstring
DT_DIVS = (10, 100, 1000)


def _make(cfg: dict, mode: str, dt: float) -> RailLatch:
    return RailLatch(capacitance=cfg["C"], r_leak=cfg["R"],
                     theta=cfg["theta"], gm=cfg["gm"],
                     n_feedback_fets=cfg["n_feedback_fets"],
                     v_rail=cfg["v_rail"], rail_r_internal=cfg["rail_r_internal"],
                     clamp_mode=mode, clamp_gm=cfg["clamp_gm"],
                     clamp_threshold=cfg["clamp_threshold"], k_in=cfg["k_in"],
                     dt=dt)


def _run(cfg: dict, mode: str, dt: float) -> tuple[float, float, int]:
    """等物理时长跑 v0∈{0.0, 0.9}，返回 (v_from_0, v_from_09, steps)。"""
    steps = int(round(T_PHYSICAL / dt))
    results = []
    for v0 in (0.0, 0.9):
        z = _make(cfg, mode, dt)
        z._cap.charge = v0 * z.capacitance
        for _ in range(steps):
            z.step(0.0, dt)
        results.append(z.state)
    return results[0], results[1], steps


def _sweep(cfg: dict, tag: str, rows: list) -> dict:
    """对一个配置跑 C1/C2/C3 全套，返回判定要素。"""
    base_dt = cfg["dt"]
    ref = _make(cfg, "finite", base_dt)
    v_cont = ref.continuous_limit_fixed_point()
    print(f"\n[{tag}] N={cfg['n_feedback_fets']}  连续极限高支 V*_cont = "
          f"{v_cont if v_cont is None else round(v_cont, 6)}")

    lo, hi, steps = _run(cfg, "hard", base_dt)
    bi_hard = (lo < 0.1 and hi > 0.9)
    print(f"  C1 hard   dt={base_dt:<7} T={T_PHYSICAL}s ({steps} 步)  "
          f"v0=0→{lo:.6f} | v0=.9→{hi:.6f}  双稳={bi_hard}")
    rows.append({"config": tag, "case": "C1_hard", "dt": base_dt,
                 "steps": steps, "v_from_0": lo, "v_from_09": hi,
                 "bistable": bi_hard, "v_fp_discrete": "", "map_deriv": "",
                 "convergence_error": "", "fixed_point_error": ""})

    small_dt_ok = []
    bi_finite_base = False
    for div in (1,) + DT_DIVS:
        dt = base_dt / div
        fp = ref.finite_discrete_fixed_point(dt)
        lo2, hi2, steps = _run(cfg, "finite", dt)
        ok = (lo2 < 0.1 and hi2 > 0.9)
        conv_err = abs(hi2 - fp["v"]) if fp else float("nan")
        fp_err = (abs(fp["v"] - v_cont)
                  if (fp and v_cont is not None) else float("nan"))
        label = "C2 finite" if div == 1 else f"C3 dt/{div}"
        print(f"  {label:<10} dt={dt:<8.0e} T={T_PHYSICAL}s ({steps} 步)  "
              f"v0=0→{lo2:.6f} | v0=.9→{hi2:.6f}  双稳={ok}")
        if fp:
            print(f"             V*_disc(dt)={fp['v']:.9f} deriv={fp['map_deriv']:+.4f} "
                  f"stable={fp['stable']}  conv_err={conv_err:.3e}  "
                  f"fp_err={fp_err:.3e}")
        rows.append({"config": tag, "case": "C2_finite" if div == 1
                     else f"C3_finite_dt/{div}", "dt": dt, "steps": steps,
                     "v_from_0": lo2, "v_from_09": hi2, "bistable": ok,
                     "v_fp_discrete": fp["v"] if fp else "",
                     "map_deriv": fp["map_deriv"] if fp else "",
                     "convergence_error": conv_err,
                     "fixed_point_error": fp_err})
        if div == 1:
            bi_finite_base = ok
        else:
            small_dt_ok.append(ok)

    if bi_finite_base:
        verdict = "PHYSICAL_BISTABILITY"
    elif all(small_dt_ok):
        verdict = "PHYSICAL_BISTABILITY_DT_LIMITED"
    else:
        verdict = "NUMERICAL_LATCH_ONLY"
    print(f"  ⇒ [{tag}] 判定: {verdict}")
    return {"tag": tag, "verdict": verdict, "v_cont": v_cont}


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    fp = assert_fingerprint(CANONICAL)
    print("=" * 68)
    print("P1-2 钳位完整性（等物理时长版；canonical fingerprint = %s）" % fp)
    print("=" * 68)

    rows: list = []
    res_canon = _sweep(CANONICAL, "canonical_N1", rows)
    res_legacy = _sweep(LEGACY_N3_DIAG, "legacy_N3_erratum", rows)

    print("\n" + "-" * 68)
    print(f"canonical(N=1) 判定: {res_canon['verdict']}")
    print(f"legacy(N=3) 勘误复核: {res_legacy['verdict']}  "
          f"（第三轮同名结论的证据当时来自 div² 缩水时长，此处为等时长复测）")
    print("  ★ Z 高态读数 1.0 = hard clamp 钳位值；物理高支值 = 上表 V*_cont。")

    path = os.path.join(DATA_DIR, "clamp_integrity.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n落盘: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
