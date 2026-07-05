"""T-033: 50k 步 P0 修复验证实验

目标：验证三条 P0 物理防线修复（commit cac24ca）的效果：
  P0-1: phasic 不再出现 -10.0 极端负值（K+ 逆转电位钳位）
  P0-2: DA 在热源附近不再熄灭（IntakeSensor→DA 进食奖励脉冲）
  P0-3: 冷区 fill 开始下降（BMR 0.002/步）

来源方案:
  - 最终架构裁决：T-032 实验失败的物理根因与修复指令（2026-07-05）
  - P0修复实施评判报告_2026-07-05.md

世界设置: 单热源，与 T-032 相同，便于对比。
"""

from __future__ import annotations

import sys
import os
import time
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.stdout.reconfigure(line_buffering=True)

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS        = 50_000
LOG_INTERVAL = 5_000
DT           = 1.0

src = HeatSource(position=[70.0, 50.0, 25.0], energy=50_000.0,
                 temperature=5.0, radius=30.0)
src._drift = [0.0, 0.0, 0.0]
body = Body(position=[50.0, 50.0, 25.0])
world = World(heat_sources=[src], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

c = VariantCircuit()
c.world = world
c.somatosensory.LATERAL_GAIN = 0.3
for m in c.muscle_system.muscles:
    m.gain = 0.3


def get_yaw_weights():
    w_ccw = float('nan')
    w_cw  = float('nan')
    b_ccw = c.bundle_d1_phasic_left_to_spinal_ccw
    b_cw  = c.bundle_d1_phasic_right_to_spinal_cw
    if b_ccw and b_ccw._memristors:
        w_ccw = b_ccw._memristors[0][0].w
    if b_cw and b_cw._memristors:
        w_cw = b_cw._memristors[0][0].w
    return w_ccw, w_cw


def get_t41_ratio():
    axis_ws, cross_ws = [], []
    for b in c.bundles_col_to_motor:
        ws = [m.w for row in b._memristors for m in row]
        if not ws:
            continue
        avg_w = sum(ws) / len(ws)
        if 'cross' not in b.id:
            axis_ws.append(avg_w)
        else:
            cross_ws.append(avg_w)
    avg_ax = sum(axis_ws) / max(len(axis_ws), 1)
    avg_cr = sum(cross_ws) / max(len(cross_ws), 1)
    return avg_ax, avg_cr, avg_ax / max(avg_cr, 1e-6)


def get_dr5():
    pT = c._patch_temps if hasattr(c, '_patch_temps') else {}
    T = {pid: pT.get(pid, (0.0,))[0] for pid in ['front', 'back', 'left', 'right']}
    vx = c.world.body.velocity[0] if hasattr(c.world.body, 'velocity') else 0.0
    vy = c.world.body.velocity[1] if hasattr(c.world.body, 'velocity') else 0.0
    patch_grad_x = T.get('right', 0) - T.get('left', 0)
    patch_grad_y = T.get('front', 0) - T.get('back', 0)
    dot = patch_grad_x * vx + patch_grad_y * vy
    return dot > 0


def main():
    print("=" * 80)
    print("  T-033: 50k 步 P0 修复验证实验")
    print("=" * 80)
    print(f"  Steps={STEPS//1000}k, DT={DT}, log_interval={LOG_INTERVAL//1000}k")
    src_pos = src.position
    print(f"  P0-1: phasic K+ floor (-0.1V) | P0-2: intake→DA | P0-3: BMR=0.002/步")
    print()

    hdr = (f"{'Step':>7} | "
           f"{'x':>7} {'dist':>7} | "
           f"{'w_ccw':>7} {'w_cw':>7} {'Δw':>7} | "
           f"{'fill':>6} {'satiety':>6} | "
           f"{'ax/cr':>6} | "
           f"{'DA':>6} {'pL':>6} {'pR':>6} | "
           f"{'iDR':>6} {'DR5%':>5}")
    print(hdr)
    print("-" * len(hdr))

    phasic_min_l = 0.0   # track minimum phasic (P0-1 验证)
    phasic_min_r = 0.0
    dr5_count    = 0
    da_at_src    = []    # DA values when dist < 20
    t_start      = time.time()

    for step in range(STEPS):
        c.step({}, DT)

        # 实时追踪 phasic 极值
        pl = c.phasic_left.activation
        pr = c.phasic_right.activation
        phasic_min_l = min(phasic_min_l, pl)
        phasic_min_r = min(phasic_min_r, pr)

        # 追踪 DA@热源
        pos = c.world.body.position
        dist = math.sqrt(sum((pos[i] - src_pos[i]) ** 2 for i in range(3)))
        if dist < 20:
            da = c.dopamine.concentration if hasattr(c.dopamine, 'concentration') else 0.0
            da_at_src.append(da)

        if step % LOG_INTERVAL == LOG_INTERVAL - 1:
            w_ccw, w_cw = get_yaw_weights()
            dw = (w_cw - w_ccw) if (not math.isnan(w_ccw) and not math.isnan(w_cw)) else float('nan')

            fill  = c.energy_store.fill_fraction
            sat   = c.satiety_neuron.activation if hasattr(c, 'satiety_neuron') else 0.0
            avg_ax, avg_cr, ratio = get_t41_ratio()
            da    = c.dopamine.concentration if hasattr(c.dopamine, 'concentration') else 0.0
            p_l   = c.phasic_left.activation
            p_r   = c.phasic_right.activation

            # intake_sensor (P0-2 验证)
            i_dr = c.intake_sensor_neuron.activation if hasattr(c, 'intake_sensor_neuron') else 0.0

            if get_dr5():
                dr5_count += 1
            dr5_pct = dr5_count / ((step + 1) / LOG_INTERVAL) * 100

            print(f"{step+1:>7} | "
                  f"{pos[0]:>7.2f} {dist:>7.2f} | "
                  f"{w_ccw:>7.4f} {w_cw:>7.4f} {dw:>+7.4f} | "
                  f"{fill:>6.4f} {sat:>6.4f} | "
                  f"{ratio:>6.2f}x | "
                  f"{da:>6.4f} {p_l:>6.3f} {p_r:>6.3f} | "
                  f"{i_dr:>6.4f} {dr5_pct:>5.1f}%")

    elapsed = time.time() - t_start
    w_ccw_f, w_cw_f = get_yaw_weights()
    _, _, t41_f = get_t41_ratio()
    fill_f = c.energy_store.fill_fraction

    print()
    print("=" * 80)
    print(f"  完成: {STEPS//1000}k 步, 耗时 {elapsed:.1f}s")
    print()
    print("  === P0 修复验证 ===")

    # P0-1
    p01_pass = phasic_min_l >= -0.15 and phasic_min_r >= -0.15
    print(f"  P0-1 phasic 下限钳位: pL_min={phasic_min_l:.3f} pR_min={phasic_min_r:.3f} "
          f"→ {'PASS (≥-0.15)' if p01_pass else 'FAIL (<-0.15)'}")

    # P0-2
    da_src_mean = sum(da_at_src) / max(len(da_at_src), 1)
    p02_pass = da_src_mean > 0.05 and len(da_at_src) > 10
    print(f"  P0-2 DA@热源(dist<20): 采样 {len(da_at_src)} 次，均值={da_src_mean:.4f} "
          f"→ {'PASS (>0.05)' if p02_pass else f'FAIL ({len(da_at_src)} 次, mean={da_src_mean:.4f})'}")

    # P0-3
    p03_pass = fill_f < 0.999   # 冷区/暖区混合后 fill 应低于饱和值
    print(f"  P0-3 BMR 饥饿压力: fill_final={fill_f:.4f} "
          f"→ {'PASS (<0.999, 有消耗)' if p03_pass else 'FAIL (仍饱和)'}")

    print()
    print("  === 最终状态 ===")
    print(f"  yaw STDP: w_ccw={w_ccw_f:.4f}, w_cw={w_cw_f:.4f}, Δw={w_cw_f-w_ccw_f:+.4f}")
    print(f"  T4.1: {t41_f:.2f}x | fill: {fill_f:.4f}")
    print()
    print(f"  总体: {'PASS' if (p01_pass and p02_pass and p03_pass) else 'PARTIAL'} "
          f"(P0-1={'✓' if p01_pass else '✗'} "
          f"P0-2={'✓' if p02_pass else '✗'} "
          f"P0-3={'✓' if p03_pass else '✗'})")


if __name__ == "__main__":
    main()
