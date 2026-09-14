"""z_block_and_energy.py — P1-5 Z 物理阻断 + P1-6 能源账本。

TYPE:INFRA（research/ 隔离层）

## P1-5：物理阻断（禁止 `Z = 0`）

阻断方式必须是**物理断开**：
  A. 断开反馈 FET 支路（n_feedback_fets → 0，即去掉全部反馈器件）
  B. 断开供电源（v_rail → 0，反馈 FET 无电流可通）
**不修改候选当前电容状态**——状态由动力学自然演化。

要求：高态初始 → 阻断 → 5xxx 步自然衰减 → 同一 future probe 下
      readout_A(阻断) == readout_B(低态)。差异消失 ⇒ Z 因果必要性成立。

## P1-6：能源账本

记录 feedback 电流、rail 电流/电压、clamp 耗散、储能、反馈供能，
计算 E_hold(T) 随保持时间的增长；标注
  ENERGY_SUPPORT = EXTERNAL_IDEAL_RAIL
  GLOBAL_ENERGY_CLOSURE = NOT_ESTABLISHED
不得把"120k 步漂移 0"单独解释为无代价的无限持久性。

输出：data/z_block.csv, data/energy_ledger.csv
"""
from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from research.A8_state_audit.candidate_config import (
    CANONICAL, assert_fingerprint, energy_state)
from research.A8_state_audit.rail_latch import RailLatch
from tss.tests.test_c1_coupling import _synthetic_stack

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DRIVE = 0.17
DT2 = 50
BLOCK_STEPS = 5000


def new_latch(**over):
    kw = dict(capacitance=CANONICAL["C"], r_leak=CANONICAL["R"],
              theta=CANONICAL["theta"], gm=CANONICAL["gm"],
              n_feedback_fets=CANONICAL["n_feedback_fets"],
              v_rail=CANONICAL["v_rail"], rail_r_internal=CANONICAL["rail_r_internal"],
              clamp_mode=CANONICAL["clamp_mode"], clamp_gm=CANONICAL["clamp_gm"],
              clamp_threshold=CANONICAL["clamp_threshold"], k_in=CANONICAL["k_in"])
    kw.update(over)
    return RailLatch(**kw)


def future_probe_readout(v_init: float, blocked: bool, steps: int = 4000):
    """从给定初始态起（不设 Z=0），跑 future probe，返回**阈值读出**累加。

    读出级 = MOSFET(θ=0.3 默认) → 积分（同 twins Phase D 手法）。
    修正记录：初版误用裸电压累加，导致 blocked 后亚阈残压（2.4e-4）被
    4000 步积分成 0.144 伪差——阈值读出下该残压为精确零（DEG-019 硬截断）。
    """
    from nexus_v1.components.semiconductor import MOSFET
    over = {"n_feedback_fets": 0} if blocked else {}
    z = new_latch(**over)
    z._cap.charge = v_init * z.capacitance     # 初始态设定=审计手段，非阻断手段
    read_fet = MOSFET(v_threshold=0.3, gm=1.0)  # θ=gm=原语默认
    # washout（若阻断，高态应在此衰减）
    for _ in range(BLOCK_STEPS):
        z.step(0.0)
    v_after_washout = z.state
    # 相同 future probe：pair 事件序列（k_in=0.5 下单事件亚吸引域，不翻转低态）
    adx, ady, pair = _synthetic_stack()
    readout = 0.0
    for k in range(steps):
        adx.step(DRIVE if k == 100 else 0.0, 0.001)
        ady.step(DRIVE if k == 200 else 0.0, 0.001)
        c = pair.step(1000 + k, 0.001)
        readout += read_fet.conduct(z.step(c))
    return v_after_washout, readout


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    fp = assert_fingerprint(CANONICAL)
    print("=" * 70)
    print(f"P1-5 Z 物理阻断 / P1-6 能源账本（fingerprint={fp}）")
    print("=" * 70)

    rows = []
    print("\n[P1-5] 物理阻断（断开反馈器件，不设 Z=0）")
    for label, blocked in (("intact(反馈器件在位)", False),
                           ("blocked(反馈器件断开)", True)):
        v_w1, r1 = future_probe_readout(1.0, blocked)   # 高态初始
        v_w0, r0 = future_probe_readout(0.0, blocked)   # 低态初始
        d = abs(r1 - r0)
        print(f"  {label:<26} 高态起 washout 后 V={v_w1:.6f}  读出={r1:.6f}")
        print(f"  {'':<26} 低态起 washout 后 V={v_w0:.6f}  读出={r0:.6f}"
              f"   |Δreadout|={d:.3e}")
        rows.append({"case": label, "v_high_after_washout": v_w1,
                     "v_low_after_washout": v_w0, "readout_high": r1,
                     "readout_low": r0, "readout_diff": d,
                     "z_causal": d > 1e-9})

    intact = rows[0]["z_causal"]
    blocked = not rows[1]["z_causal"]
    print(f"\n  未阻断时 Z 有因果作用 = {intact}；阻断后差异消失 = {blocked}")
    print(f"  ⇒ Z causal necessity = {'SUPPORTED' if (intact and blocked) else 'NOT SUPPORTED'}")

    with open(os.path.join(DATA_DIR, "z_block.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ── P1-6 能源账本 ──
    print("\n" + "-" * 70)
    print("[P1-6] 能源账本（E_hold(T) 随保持时间增长）")
    print("-" * 70)
    z = new_latch()
    z._cap.charge = 1.0 * z.capacitance
    erows = []
    for T in (1204, 12000, 120000):
        z2 = new_latch()
        z2._cap.charge = 1.0 * z2.capacitance
        for _ in range(T):
            z2.step(0.0)
        led = z2.energy_ledger()
        erows.append({"hold_steps": T, **led})
        print(f"  T={T:<7} V={z2.state:.6f}  E_fb={led['feedback_energy']:.6e}  "
              f"E_clamp={led['clamp_dissipation']:.6e}  "
              f"stored={led['stored_energy']:.6e}")

    print(f"\n  {energy_state()}")
    print("  ⇒ 高态由外部轨持续供能维持，非免费永久保存；"
          "全局能量闭合未建立（Noether 未对该候选记账）")

    with open(os.path.join(DATA_DIR, "energy_ledger.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(erows[0].keys()))
        w.writeheader()
        w.writerows(erows)

    print(f"\n落盘: {os.path.join(DATA_DIR, 'z_block.csv')} / energy_ledger.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
