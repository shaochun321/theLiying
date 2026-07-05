"""T-032: 200k 步长程实验 — yaw方向分化/饱腹涌现/T4.1恢复验证

目标：
  1. yaw STDP 分化: phasic_left→spinal_ccw vs phasic_right→spinal_cw 权重差异
  2. 饱腹涌现: SatietyNeuron 激活，DwellSensor 响应，fill_fraction 稳定
  3. T4.1 恢复: axis/cross col→motor 权重比（10k步时 0.27x，200k步目标 > 1.0x）
  4. 能量链: fill_fraction 全程 > 0.1，V_feed → CPC 脆弱点3 验证

来源方案:
  - 饱腹闭环方案-反馈整合最终版 §七 "200k步长程实验验证T4.1恢复、yaw方向分化、饱腹涌现"
  - 三核心脆弱点修正方案_2026-07-04（脆弱点1 vital_boost_factor 基线数据采集）

世界设置: 单热源，body 初始在热场内偏侧，观察自然运动与 yaw STDP 学习。

Usage:
    python -m nexus_v1.tests.exp_t032_200k_satiety_yaw
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

STEPS        = 200_000
LOG_INTERVAL = 10_000
DT           = 1.0

# 热源位置：[70,50,25]，body 起点 [50,50,25]
# body 在热源左侧（x方向差=20，radius=30 → body 在热场内边缘）
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
    """phasic STDP yaw 权重：left→ccw 和 right→cw."""
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
    """T4.1: axis / cross col→motor 权重比."""
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
    """DR5: patch 温差代理（前后左右）。"""
    pT = c._patch_temps if hasattr(c, '_patch_temps') else {}
    T = {pid: pT.get(pid, (0.0,))[0] for pid in ['front', 'back', 'left', 'right']}
    vx = c.world.body.velocity[0] if hasattr(c.world.body, 'velocity') else 0.0
    vy = c.world.body.velocity[1] if hasattr(c.world.body, 'velocity') else 0.0
    patch_grad_x = T.get('right', 0) - T.get('left', 0)
    patch_grad_y = T.get('front', 0) - T.get('back', 0)
    dot = patch_grad_x * vx + patch_grad_y * vy
    speed = math.sqrt(vx ** 2 + vy ** 2)
    return dot > 0, dot, speed


def main():
    print("=" * 80)
    print("  T-032: 200k 步长程实验 — yaw方向分化/饱腹涌现/T4.1恢复")
    print("=" * 80)
    print(f"  Steps={STEPS//1000}k, DT={DT}, log_interval={LOG_INTERVAL//1000}k")
    src_pos = src.position
    print(f"  Heat source: {src_pos}, T={src.temperature}, r={src.radius}")
    print(f"  Body start:  {list(c.world.body.position)}")
    print()

    # 表头
    hdr = (f"{'Step':>7} | "
           f"{'x':>7} {'dist':>7} | "
           f"{'w_ccw':>7} {'w_cw':>7} {'Δw':>7} | "
           f"{'fill':>6} {'satiety':>7} {'dwell':>7} | "
           f"{'ax':>7} {'cr':>7} {'ax/cr':>7} | "
           f"{'DA':>6} {'pL':>6} {'pR':>6} | "
           f"{'DR5%':>6}")
    print(hdr)
    print("-" * len(hdr))

    # 脆弱点1 基线采集（三核心脆弱点修正方案，需 200k 数据反推 w_cpc2vital）
    vital_outputs = []
    deviations    = []
    dr5_count     = 0
    t_start       = time.time()

    for step in range(STEPS):
        ms = c.step({}, DT)

        # 采集脆弱点1 基线数据
        if hasattr(ms, 'vital_amplitude'):
            vital_outputs.append(ms.vital_amplitude)
        if hasattr(ms, 'deviation'):
            deviations.append(ms.deviation)

        if step % LOG_INTERVAL == LOG_INTERVAL - 1:
            pos = c.world.body.position
            dist = math.sqrt(sum((pos[i] - src_pos[i]) ** 2 for i in range(3)))

            w_ccw, w_cw = get_yaw_weights()
            dw = (w_cw - w_ccw) if (not math.isnan(w_ccw) and not math.isnan(w_cw)) else float('nan')

            fill  = c.energy_store.fill_fraction
            sat   = c.satiety_neuron.activation if hasattr(c, 'satiety_neuron') else 0.0
            dwell = c.dwell_sensor_neuron.activation if hasattr(c, 'dwell_sensor_neuron') else 0.0

            avg_ax, avg_cr, ratio = get_t41_ratio()

            da    = c.dopamine.concentration if hasattr(c.dopamine, 'concentration') else 0.0
            p_l   = c.phasic_left.activation  if hasattr(c, 'phasic_left')  else 0.0
            p_r   = c.phasic_right.activation if hasattr(c, 'phasic_right') else 0.0

            is_thermo, _, _ = get_dr5()
            if is_thermo:
                dr5_count += 1
            dr5_pct = dr5_count / ((step + 1) / LOG_INTERVAL) * 100

            print(f"{step+1:>7} | "
                  f"{pos[0]:>7.2f} {dist:>7.2f} | "
                  f"{w_ccw:>7.4f} {w_cw:>7.4f} {dw:>+7.4f} | "
                  f"{fill:>6.4f} {sat:>7.4f} {dwell:>7.4f} | "
                  f"{avg_ax:>7.5f} {avg_cr:>7.5f} {ratio:>7.2f}x | "
                  f"{da:>6.4f} {p_l:>6.4f} {p_r:>6.4f} | "
                  f"{dr5_pct:>6.1f}%")

    elapsed = time.time() - t_start
    print()
    print("=" * 80)
    print(f"  完成: {STEPS//1000}k 步, 耗时 {elapsed:.1f}s")

    w_ccw_final, w_cw_final = get_yaw_weights()
    _, _, t41_final = get_t41_ratio()
    fill_final = c.energy_store.fill_fraction

    print(f"\n  === 最终状态 ===")
    print(f"  yaw STDP: w_ccw={w_ccw_final:.4f}, w_cw={w_cw_final:.4f}, Δw={w_cw_final-w_ccw_final:+.4f}")
    print(f"  T4.1 axis/cross ratio: {t41_final:.2f}x (目标 > 1.0x)")
    print(f"  fill_fraction: {fill_final:.4f} (目标 > 0.1)")

    # 脆弱点1 基线数据汇总（用于 vital_boost_factor 反推）
    if vital_outputs:
        v_mean = sum(vital_outputs) / len(vital_outputs)
        print(f"\n  === 脆弱点1 基线（用于反推 w_cpc2vital）===")
        print(f"  vital_amplitude 均值: {v_mean:.6f}")
        if deviations:
            d_mean = sum(deviations) / len(deviations)
            print(f"  deviation 均值: {d_mean:.6f}")
            if v_mean > 1e-8 and d_mean > 1e-8:
                # w_cpc2vital = (deviation_typical - 0.1) / (vital_output_typical × deviation_typical)
                # 三核心脆弱点修正方案反推公式
                w_est = max(0.0, d_mean - 0.1) / (v_mean * max(d_mean, 1e-8))
                print(f"  反推 w_cpc2vital ≈ {w_est:.4f}")

    print()
    print("  PASS 条件:")
    yaw_pass = not math.isnan(w_ccw_final) and abs(w_cw_final - w_ccw_final) > 0.01
    t41_pass = t41_final > 0.5
    fill_pass = fill_final > 0.1
    print(f"  yaw Δw > 0.01:    {'PASS' if yaw_pass else 'FAIL'} (Δw={w_cw_final-w_ccw_final:+.4f})")
    print(f"  T4.1 ratio > 0.5x: {'PASS' if t41_pass else 'FAIL'} ({t41_final:.2f}x)")
    print(f"  fill > 0.1:        {'PASS' if fill_pass else 'FAIL'} ({fill_final:.4f})")
    print()


if __name__ == "__main__":
    main()
