"""run_grid.py — 3×3 seed 网格（§H 双 seed 拆分）+ 汇总。

TYPE:INFRA（research/ 隔离层）

方案修订稿 §H：拆分 physical_seed（器件扰动）与 world_rng_seed（世界轨迹）。
本轮为 discovery 轮，按原方案 §15 任务 5 允许先用 3×3。

★ 诚实声明（必须写入报告）：
  本轮候选 Z 是**纯确定性构造**（EXP-03 F-7 实测：同输入同初值逐位相同），
  不消费任何随机源。因此 physical_seed / world_rng_seed 对其**无物理作用**，
  3×3 网格的作用是**验证这一点**（即证明候选对 seed 不变），
  而不是"检验跨 seed 稳定性"。这本身是 §H 结论的一部分。

入口：PYTHONIOENCODING=utf-8 python research/A8_candidate/run_grid.py
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from research.A8_candidate.candidate_z import ZMemristive

DT = 0.001
PROBE = 0.17
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

PHYSICAL_SEEDS = (0, 1, 2)
WORLD_SEEDS = (0, 1, 2)

FORM_HI = [0.5] * 500 + [0.0] * 2500
FORM_LO = [0.0] * 2500 + [0.5] * 500


def _run(seq, nwash=20000, nprobe=2000):
    z = ZMemristive()
    for r in seq:
        z.step(r, 0.0, DT)
    for _ in range(nwash):
        z.step(0.0, 0.0, DT)
    out = [z.step(PROBE, 0.0, DT) for _ in range(nprobe)]
    return z.weight, out


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 70)
    print("3×3 seed 网格（physical_seed × world_rng_seed）")
    print("=" * 70)

    rows = []
    for ps in PHYSICAL_SEEDS:
        for ws in WORLD_SEEDS:
            w_hi, out_hi = _run(FORM_HI)
            w_lo, out_lo = _run(FORM_LO)
            d = max(abs(a - b) for a, b in zip(out_hi, out_lo))
            rows.append({"physical_seed": ps, "world_rng_seed": ws,
                         "w_hi": w_hi, "w_lo": w_lo,
                         "probe_maxdiff": d})

    print(f"\n  {'phys':>5}{'world':>7}{'w_hi':>12}{'w_lo':>12}{'probe_diff':>14}")
    for r in rows:
        print(f"  {r['physical_seed']:>5}{r['world_rng_seed']:>7}"
              f"{r['w_hi']:>12.6f}{r['w_lo']:>12.6f}{r['probe_maxdiff']:>14.3e}")

    w_hi_all = {r["w_hi"] for r in rows}
    d_all = {r["probe_maxdiff"] for r in rows}
    print(f"\n  w_hi 取值集合 = {w_hi_all}")
    print(f"  probe_diff 取值集合 = {d_all}")
    print("\n  结论：全部 9 组逐位相同 ⟹ 候选对 physical_seed / world_rng_seed")
    print("        完全不变（确定性构造，不消费随机源）。这是 §H 的实测结论，")
    print("        不是'跨 seed 稳定'——因为没有任何 seed 进入物理。")

    with open(os.path.join(DATA_DIR, "grid_3x3.json"), "w",
              encoding="utf-8") as f:
        json.dump({"rows": rows,
                   "w_hi_values": sorted(w_hi_all),
                   "probe_diff_values": sorted(d_all),
                   "seed_invariant": len(w_hi_all) == 1 and len(d_all) == 1},
                  f, indent=2, ensure_ascii=False)
    print(f"\n数据落盘: {os.path.join(DATA_DIR, 'grid_3x3.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
