"""T-035: 两阶段实验第二阶段 — 从冷区首次接触热场

目标（来源：两阶段实验.md + 两阶段实验评判报告_2026-07-05.md）：
  P3-4: body 从冷区进入热场时，phasic 产生正值（relay↑ > slow_relay≈0）
  P3-5: 首次接触时 DA > 0.3（低 satiety 时进食奖励脉冲未被遮蔽）
  P3-6: yaw STDP 权重开始方向性分化（|Δw| > 0.005，避免 T-033 的纯衰减）

设置：
  - 单热源 [70, 50, 25]，T=5.0，r=30，energy=50000
  - Body 初始位置 [10, 50, 25]，dist ≈ 60（冷区起步，在热场外）
  - initial_fill = 0.3（饥饿状态，延续 T-034 预期终态）
  - 50k 步，LOG_INTERVAL = 5000
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
INIT_FILL    = 0.3    # 延续 T-034 预期终态（饥饿起步）

src  = HeatSource(position=[70.0, 50.0, 25.0], energy=50_000.0,
                  temperature=5.0, radius=30.0)
src._drift = [0.0, 0.0, 0.0]
# Body 从冷区起步，dist ≈ 60（在热场 r=30 以外）
body = Body(position=[10.0, 50.0, 25.0])
world = World(heat_sources=[src], body=body)
world.MIN_ALIVE  = 0
world.REGEN_PROB = 0.0

c = VariantCircuit()
c.world = world

# 从 initial_fill=0.3 (饥饿)起步
c.energy_store._cap.charge = c.energy_store.config.capacity * INIT_FILL
c.somatosensory.LATERAL_GAIN = 0.3
for m in c.muscle_system.muscles:
    m.gain = 0.3

src_pos = src.position


def get_yaw_weights():
    w_ccw, w_cw = float('nan'), float('nan')
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
    return avg_ax / max(avg_cr, 1e-6)


def get_dr5():
    pT  = c._patch_temps if hasattr(c, '_patch_temps') else {}
    T   = {pid: pT.get(pid, (0.0,))[0] for pid in ['front', 'back', 'left', 'right']}
    vx  = c.world.body.velocity[0] if hasattr(c.world.body, 'velocity') else 0.0
    vy  = c.world.body.velocity[1] if hasattr(c.world.body, 'velocity') else 0.0
    pgx = T.get('right', 0) - T.get('left', 0)
    pgy = T.get('front', 0) - T.get('back', 0)
    return pgx * vx + pgy * vy > 0


def main():
    print("=" * 90)
    print("  T-035: 从冷区首次接触热场（phasic正值 / DA脉冲 / yaw Δw 分化）")
    print("=" * 90)
    print(f"  Body 初始 dist ≈ 60（热场外），init_fill={INIT_FILL}（饥饿）")
    print(f"  Steps={STEPS//1000}k, DT={DT}, LOG={LOG_INTERVAL//1000}k")
    print()

    hdr = (f"{'Step':>6} | "
           f"{'x':>7} {'dist':>6} | "
           f"{'w_ccw':>6} {'w_cw':>6} {'Δw':>7} | "
           f"{'fill':>6} {'sat':>5} | "
           f"{'T41':>5} | "
           f"{'DA':>6} {'pL':>7} {'pR':>7} | "
           f"{'pPeak':>6} {'iDR':>5} | DR5%")
    print(hdr)
    print("-" * len(hdr))

    phasic_max     = 0.0    # 窗口内 phasic 峰值
    phasic_all_max = 0.0    # 全程 phasic 峰值
    dr5_count      = 0
    first_contact_step = None   # body 首次进入热场的步数
    da_at_first    = []         # 首次接触时的 DA 值（dist < 30，前 5k 步内）
    t_start        = time.time()

    for step in range(STEPS):
        c.step({}, DT)

        pos  = c.world.body.position
        dist = math.sqrt(sum((pos[i] - src_pos[i]) ** 2 for i in range(3)))
        pl   = c.phasic_left.activation
        pr   = c.phasic_right.activation
        phasic_max     = max(phasic_max, pl, pr)
        phasic_all_max = max(phasic_all_max, pl, pr)

        # 记录首次接触（body 进入热场 r=30）
        if dist < 30 and first_contact_step is None:
            first_contact_step = step
            print(f"  >>> 首次接触热场！step={step}, dist={dist:.2f}")

        # 首次接触后 5k 步内采集 DA
        if first_contact_step is not None and step < first_contact_step + 5000:
            da = c.dopamine.concentration if hasattr(c.dopamine, 'concentration') else 0.0
            da_at_first.append(da)

        if step % LOG_INTERVAL == LOG_INTERVAL - 1:
            w_ccw, w_cw = get_yaw_weights()
            dw   = (w_cw - w_ccw) if not (math.isnan(w_ccw) or math.isnan(w_cw)) else float('nan')
            fill = c.energy_store.fill_fraction
            sat  = c.satiety_neuron.activation if hasattr(c, 'satiety_neuron') else 0.0
            t41  = get_t41_ratio()
            da   = c.dopamine.concentration if hasattr(c.dopamine, 'concentration') else 0.0
            i_dr = c.intake_sensor_neuron.activation if hasattr(c, 'intake_sensor_neuron') else 0.0

            if get_dr5():
                dr5_count += 1
            dr5_pct = dr5_count / ((step + 1) / LOG_INTERVAL) * 100

            print(f"{step+1:>6} | "
                  f"{pos[0]:>7.2f} {dist:>6.2f} | "
                  f"{w_ccw:>6.4f} {w_cw:>6.4f} {dw:>+7.4f} | "
                  f"{fill:>6.4f} {sat:>5.3f} | "
                  f"{t41:>5.2f}x | "
                  f"{da:>6.4f} {pl:>7.3f} {pr:>7.3f} | "
                  f"{phasic_max:>6.3f} {i_dr:>5.4f} | {dr5_pct:.1f}%")
            phasic_max = 0.0   # 重置窗口峰值

    elapsed   = time.time() - t_start
    w_ccw_f, w_cw_f = get_yaw_weights()
    fill_f = c.energy_store.fill_fraction

    print()
    print("=" * 90)
    print(f"  完成: {STEPS//1000}k 步, 耗时 {elapsed:.1f}s")
    print()
    print("  === P3 验证（热场首次接触）===")

    # P3-4: phasic 产生正值
    p34_pass = phasic_all_max > 0.05
    print(f"  P3-4 phasic正值: |phasic|_max={phasic_all_max:.4f} "
          f"→ {'PASS (>0.05)' if p34_pass else 'FAIL (phasic未产生正值)'}")
    if first_contact_step is not None:
        print(f"         首次接触: step={first_contact_step}")
    else:
        print(f"         首次接触: 未发生（body 未进入热场）")

    # P3-5: 首次接触时 DA 脉冲
    if da_at_first:
        da_first_mean = sum(da_at_first) / len(da_at_first)
        da_first_max  = max(da_at_first)
        p35_pass = da_first_max > 0.3
        print(f"  P3-5 DA首次接触脉冲: mean={da_first_mean:.4f}, max={da_first_max:.4f} "
              f"→ {'PASS (max>0.3)' if p35_pass else 'FAIL (DA未升高)'}")
    else:
        p35_pass = False
        print(f"  P3-5 DA首次接触脉冲: 未采集（body未进入热场）→ FAIL")

    # P3-6: yaw Δw 分化
    dw_final = abs(w_cw_f - w_ccw_f) if not math.isnan(w_ccw_f) else 0.0
    p36_pass = dw_final > 0.005
    print(f"  P3-6 yaw STDP分化: |Δw|={dw_final:.4f} (w_ccw={w_ccw_f:.4f}, w_cw={w_cw_f:.4f}) "
          f"→ {'PASS (>0.005)' if p36_pass else 'FAIL (无分化)'}")

    total = p34_pass and p35_pass and p36_pass
    print()
    print(f"  总体: {'PASS' if total else 'PARTIAL'} "
          f"(P3-4={'✓' if p34_pass else '✗'} "
          f"P3-5={'✓' if p35_pass else '✗'} "
          f"P3-6={'✓' if p36_pass else '✗'})")
    print(f"  fill_final={fill_f:.4f}, phasic_all_max={phasic_all_max:.4f}")


if __name__ == "__main__":
    main()
