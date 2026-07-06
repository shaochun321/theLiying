"""T-044: 50k 步 T-043 交叉抑制束快速验证

目标：验证 T-043（yaw 层交叉抑制束）实装后的效果：
  P4-1: DR5% ≥ 60%（热趋性方向正确）
  P4-2: |Δw| 增长（STDP 学习有效，非静态漂移死锁）
  P4-3: yaw_ccw / yaw_cw 不同时归零（差分有效）
  P4-4: T4.1 Motor 轴权重比 > 0.1（Motor coupling 稳定）
  P4-5: 无死锁（yaw 差值持续不为零）

消融检验基线：冻结 STDP 后 DR5% 应跌回 ~50%（T-039 已确认）。
本实验开启 STDP，DR5% ≥ 60% 才能证明 T-043 没有破坏学习。

世界设置：单热源，body 从侧面出发（x 方向偏移），需要 yaw 转向才能接近。
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

# 与 T-038/T-041 相同的世界设置，便于对比
src = HeatSource(position=[70.0, 50.0, 25.0], energy=50_000.0,
                 temperature=5.0, radius=30.0)
src._drift = [0.0, 0.0, 0.0]
body = Body(position=[10.0, 50.0, 25.0])   # 从 x=10 侧面出发，距热源 60 单位
world = World(heat_sources=[src], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

c = VariantCircuit()
c.world = world
c.somatosensory.LATERAL_GAIN = 0.3
for m in c.muscle_system.muscles:
    m.gain = 0.3


def get_yaw_weights():
    b_ccw = c.bundle_d1_phasic_left_to_spinal_ccw
    b_cw  = c.bundle_d1_phasic_right_to_spinal_cw
    w_ccw = b_ccw._memristors[0][0].w if b_ccw and b_ccw._memristors else float('nan')
    w_cw  = b_cw._memristors[0][0].w  if b_cw  and b_cw._memristors  else float('nan')
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
    return (patch_grad_x * vx + patch_grad_y * vy) > 0


def main():
    print("=" * 90)
    print("  T-044: 50k 步 T-043 交叉抑制束验证")
    print("=" * 90)
    print(f"  Steps={STEPS//1000}k, DT={DT}, 热源=[70,50,25], body_start=[10,50,25]")
    print(f"  T-043: spinal_ccw→yaw_cw / spinal_cw→yaw_ccw  W=0.020 sg=-1.0 (frozen)")
    print()

    src_pos = src.position

    hdr = (f"{'Step':>7} | "
           f"{'x':>7} {'dist':>7} | "
           f"{'w_ccw':>7} {'w_cw':>7} {'Δw':>7} | "
           f"{'fill':>6} | "
           f"{'T41':>6} | "
           f"{'DA':>6} {'sp_cc':>6} {'sp_cw':>6} | "
           f"{'ycc':>6} {'ycw':>6} | "
           f"{'DR5%':>6}")
    print(hdr)
    print("-" * len(hdr))

    dr5_count   = 0
    dr5_log     = []    # 每 LOG_INTERVAL 的 DR5 瞬时值
    yaw_deadlock_steps = 0   # 两路同时 < 0.001 的步数（死锁指标）
    sp_peak_ccw = 0.0
    sp_peak_cw  = 0.0
    t_start = time.time()

    for step in range(STEPS):
        c.step({}, DT)

        # 追踪 spinal 峰值（验证 T-043 工作点）
        sc = c.spinal_ccw.activation
        sw = c.spinal_cw.activation
        if sc > sp_peak_ccw:
            sp_peak_ccw = sc
        if sw > sp_peak_cw:
            sp_peak_cw = sw

        # 死锁检测
        ycc = c.yaw_ccw_neuron.activation
        ycw = c.yaw_cw_neuron.activation
        if abs(ycc) < 0.001 and abs(ycw) < 0.001:
            yaw_deadlock_steps += 1

        if get_dr5():
            dr5_count += 1

        if step % LOG_INTERVAL == LOG_INTERVAL - 1:
            w_ccw, w_cw = get_yaw_weights()
            dw = (w_ccw - w_cw) if (not math.isnan(w_ccw) and not math.isnan(w_cw)) else float('nan')

            pos     = c.world.body.position
            dist    = math.sqrt(sum((pos[i] - src_pos[i]) ** 2 for i in range(3)))
            fill    = c.energy_store.fill_fraction
            _, _, t41 = get_t41_ratio()
            da      = c.dopamine.concentration if hasattr(c.dopamine, 'concentration') else 0.0

            dr5_pct = dr5_count / (step + 1) * 100
            dr5_log.append(dr5_pct)

            print(f"{step+1:>7} | "
                  f"{pos[0]:>7.2f} {dist:>7.2f} | "
                  f"{w_ccw:>7.4f} {w_cw:>7.4f} {dw:>+7.4f} | "
                  f"{fill:>6.4f} | "
                  f"{t41:>6.2f}x | "
                  f"{da:>6.4f} {sc:>6.3f} {sw:>6.3f} | "
                  f"{ycc:>6.3f} {ycw:>6.3f} | "
                  f"{dr5_pct:>5.1f}%")

    elapsed = time.time() - t_start

    # 最终状态
    pos_f  = c.world.body.position
    dist_f = math.sqrt(sum((pos_f[i] - src_pos[i]) ** 2 for i in range(3)))
    w_ccw_f, w_cw_f = get_yaw_weights()
    dw_f = w_ccw_f - w_cw_f
    _, _, t41_f = get_t41_ratio()
    dr5_final = dr5_count / STEPS * 100
    deadlock_pct = yaw_deadlock_steps / STEPS * 100

    print()
    print("=" * 90)
    print(f"  完成: {STEPS//1000}k 步, 耗时 {elapsed:.1f}s")
    print()

    # P4-1: DR5%
    p41_pass = dr5_final >= 60.0
    print(f"  P4-1 热趋性 DR5%: {dr5_final:.1f}% → {'PASS (≥60%)' if p41_pass else 'FAIL (<60%)'}")

    # P4-2: STDP 分化
    p42_pass = abs(dw_f) > 0.05
    print(f"  P4-2 STDP 分化: w_ccw={w_ccw_f:.4f} w_cw={w_cw_f:.4f} |Δw|={abs(dw_f):.4f} "
          f"→ {'PASS (|Δw|>0.05)' if p42_pass else 'FAIL'}")

    # P4-3: 无死锁
    p43_pass = deadlock_pct < 10.0
    print(f"  P4-3 无死锁: yaw_deadlock={deadlock_pct:.1f}% 步 → {'PASS (<10%)' if p43_pass else 'FAIL (死锁)'}")

    # P4-4: T4.1 Motor coupling
    p44_pass = t41_f > 0.1
    print(f"  P4-4 T4.1 Motor coupling: {t41_f:.2f}x → {'PASS (>0.1x)' if p44_pass else 'FAIL'}")

    # P4-5: spinal peak（交叉抑制工作点确认）
    print(f"\n  [参考] spinal 峰值: sp_peak_ccw={sp_peak_ccw:.4f} sp_peak_cw={sp_peak_cw:.4f}")
    print(f"  [参考] 最终距离: {dist_f:.2f} 单位")

    all_pass = p41_pass and p42_pass and p43_pass and p44_pass
    print()
    print(f"  总体: {'PASS' if all_pass else 'FAIL'} "
          f"(P4-1={'✓' if p41_pass else '✗'} "
          f"P4-2={'✓' if p42_pass else '✗'} "
          f"P4-3={'✓' if p43_pass else '✗'} "
          f"P4-4={'✓' if p44_pass else '✗'})")
    if not p43_pass:
        print(f"  ⚠️  死锁超阈值，建议将 W_CROSS 从 0.020 降至 0.015")


if __name__ == "__main__":
    main()
