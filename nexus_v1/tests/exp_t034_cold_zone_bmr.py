"""T-034: 两阶段实验第一阶段 — 纯冷区 BMR / hunger / DA 链路验证

目标（来源：两阶段实验.md + 两阶段实验评判报告_2026-07-05.md）：
  P3-1: fill 从 initial_fill=0.3 持续下降（BMR净消耗 ≈ -0.0011/step）
  P3-2: DA 保持 > 0（satiety低时不抑制DA）
  P3-3: phasic 全程 ≈ 0（无热感知输入）

设置：
  - 无热源（World with no HeatSource）
  - Body 初始位置 [50, 50, 25]（任意，无热场不影响）
  - initial_fill = 0.3（饥饿状态起步）
  - 20k 步，LOG_INTERVAL = 2000
"""

from __future__ import annotations

import sys
import os
import time
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.stdout.reconfigure(line_buffering=True)

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import Body, World

STEPS        = 20_000
LOG_INTERVAL = 2_000
DT           = 1.0
INIT_FILL    = 0.3    # 从饥饿状态起步

body  = Body(position=[50.0, 50.0, 25.0])
world = World(heat_sources=[], body=body)   # 无热源
world.MIN_ALIVE    = 0
world.REGEN_PROB   = 0.0
world.ambient_temp = 0.0  # 真正的冷区：去除 ambient 0.1 热量，否则 ThermalMouth 从环境温度摄能

c = VariantCircuit()
c.world = world

# 设置初始 fill = 0.3（饥饿状态）
c.energy_store._cap.charge = c.energy_store.config.capacity * INIT_FILL
c.somatosensory.LATERAL_GAIN = 0.3
for m in c.muscle_system.muscles:
    m.gain = 0.3


def main():
    print("=" * 70)
    print("  T-034: 纯冷区 BMR / hunger / DA 链路验证")
    print("=" * 70)
    print(f"  Steps={STEPS//1000}k, DT={DT}, LOG={LOG_INTERVAL//1000}k, init_fill={INIT_FILL}")
    print(f"  热源: 无（纯冷区）")
    print()

    hdr = (f"{'Step':>6} | "
           f"{'fill':>6} {'Δfill':>7} | "
           f"{'satiety':>7} | "
           f"{'DA':>6} | "
           f"{'pL':>6} {'pR':>6} | "
           f"{'deliver':>7}")
    print(hdr)
    print("-" * len(hdr))

    fill_prev     = INIT_FILL
    phasic_max    = 0.0
    da_values     = []
    t_start       = time.time()

    for step in range(STEPS):
        c.step({}, DT)

        pl = c.phasic_left.activation
        pr = c.phasic_right.activation
        phasic_max = max(phasic_max, abs(pl), abs(pr))

        if step % LOG_INTERVAL == LOG_INTERVAL - 1:
            fill    = c.energy_store.fill_fraction
            delta_f = fill - fill_prev
            sat     = c.satiety_neuron.activation if hasattr(c, 'satiety_neuron') else 0.0
            da      = c.dopamine.concentration if hasattr(c.dopamine, 'concentration') else 0.0
            deliver = c.energy_store.delivery_factor()

            da_values.append(da)
            print(f"{step+1:>6} | "
                  f"{fill:>6.4f} {delta_f:>+7.4f} | "
                  f"{sat:>7.4f} | "
                  f"{da:>6.4f} | "
                  f"{pl:>6.3f} {pr:>6.3f} | "
                  f"{deliver:>7.4f}")
            fill_prev = fill

    elapsed = time.time() - t_start
    fill_f  = c.energy_store.fill_fraction

    print()
    print("=" * 70)
    print(f"  完成: {STEPS//1000}k 步, 耗时 {elapsed:.1f}s")
    print()
    print("  === P3 验证（冷区基线）===")

    # P3-1: fill 下降
    p31_pass = fill_f < INIT_FILL
    drop = INIT_FILL - fill_f
    print(f"  P3-1 BMR fill下降: {INIT_FILL:.3f} → {fill_f:.4f} (Δ={-drop:+.4f}) "
          f"→ {'PASS (fill↓)' if p31_pass else 'FAIL (fill未下降)'}")

    # P3-2: DA 不为零
    da_mean = sum(da_values) / max(len(da_values), 1)
    p32_pass = da_mean > 0.02
    print(f"  P3-2 DA保持非零: DA均值={da_mean:.4f} "
          f"→ {'PASS (>0.02)' if p32_pass else 'FAIL (DA熄灭)'}")

    # P3-3: phasic 为零（无热感知）
    p33_pass = phasic_max < 0.05
    print(f"  P3-3 phasic≈0: |phasic|_max={phasic_max:.4f} "
          f"→ {'PASS (<0.05)' if p33_pass else 'WARN (有意外热信号)'}")

    total = p31_pass and p32_pass and p33_pass
    print()
    print(f"  总体: {'PASS' if total else 'PARTIAL'} "
          f"(P3-1={'✓' if p31_pass else '✗'} "
          f"P3-2={'✓' if p32_pass else '✗'} "
          f"P3-3={'✓' if p33_pass else '✗'})")

    if p31_pass:
        rate = drop / STEPS
        print(f"  BMR 净消耗率: {rate:.6f}/step (理论 ≈ 0.0011/step)")


if __name__ == "__main__":
    main()
