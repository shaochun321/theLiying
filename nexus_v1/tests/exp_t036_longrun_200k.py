"""T-036: 200k 步长程热趋性实验

基于 T-035（50k PASS）的设置，验证 yaw 方向性分化的长期稳定性。

设置（与 T-035 完全相同）：
  - 单热源 [70, 50, 25]，T=5.0，r=30，energy=50000
  - Body 初始位置 [10, 50, 25]，dist ≈ 60（冷区起步，在热场外）
  - initial_fill = 0.3（饥饿状态）
  - 200k 步，LOG_INTERVAL = 10000

成功标准：
  P4-1: step 100k 后 |Δw| 维持（不回弹到 <0.1）— yaw 方向性稳定
  P4-2: DR5% 在 step 100k 后 > 50% — 热趋性方向正确
  P4-3: 不出现 w_ccw 完全崩溃（w_ccw > 0.05 at step 200k）
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
INIT_FILL    = 0.3

src  = HeatSource(position=[70.0, 50.0, 25.0], energy=50_000.0,
                  temperature=5.0, radius=30.0)
src._drift = [0.0, 0.0, 0.0]
body = Body(position=[10.0, 50.0, 25.0])
world = World(heat_sources=[src], body=body)
world.MIN_ALIVE  = 0
world.REGEN_PROB = 0.0

c = VariantCircuit()
c.world = world

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
    print("=" * 100)
    print("  T-036: 200k 步长程热趋性实验（基于 T-035 PASS 设置）")
    print("=" * 100)
    print(f"  Body 初始 dist ≈ 60（热场外），init_fill={INIT_FILL}（饥饿）")
    print(f"  Steps={STEPS//1000}k, DT={DT}, LOG={LOG_INTERVAL//1000}k")
    print(f"  热源: [70,50,25] T=5.0 r=30")
    print()

    hdr = (f"{'Step':>7} | "
           f"{'x':>7} {'dist':>6} | "
           f"{'w_ccw':>6} {'w_cw':>6} {'Δw':>7} | "
           f"{'fill':>6} {'sat':>5} | "
           f"{'T41':>5} | "
           f"{'DA':>6} {'pL':>7} {'pR':>7} | "
           f"{'pPeak':>6} {'iDR':>5} | DR5%")
    print(hdr)
    print("-" * len(hdr))

    phasic_win_max = 0.0
    phasic_all_max = 0.0
    dr5_count      = 0
    log_count      = 0
    da_window      = []
    t_start        = time.time()
    t_window       = time.time()

    # 记录早期首次接触
    first_contact_step = None

    for step in range(STEPS):
        c.step({}, DT)

        pos  = c.world.body.position
        dist = math.sqrt(sum((pos[i] - src_pos[i]) ** 2 for i in range(3)))
        pl   = c.phasic_left.activation
        pr   = c.phasic_right.activation
        phasic_win_max = max(phasic_win_max, pl, pr)
        phasic_all_max = max(phasic_all_max, pl, pr)

        if dist < 30 and first_contact_step is None:
            first_contact_step = step
            print(f"  >>> 首次接触热场！step={step}, dist={dist:.2f}")

        da = c.dopamine.concentration if hasattr(c.dopamine, 'concentration') else 0.0
        da_window.append(da)

        if step % LOG_INTERVAL == LOG_INTERVAL - 1:
            log_count += 1
            w_ccw, w_cw = get_yaw_weights()
            dw   = (w_cw - w_ccw) if not (math.isnan(w_ccw) or math.isnan(w_cw)) else float('nan')
            fill = c.energy_store.fill_fraction
            sat  = c.satiety_neuron.activation if hasattr(c, 'satiety_neuron') else 0.0
            t41  = get_t41_ratio()
            i_dr = c.intake_sensor_neuron.activation if hasattr(c, 'intake_sensor_neuron') else 0.0
            da_win_avg = sum(da_window) / max(len(da_window), 1)

            if get_dr5():
                dr5_count += 1
            dr5_pct = dr5_count / log_count * 100

            elapsed_win = time.time() - t_window
            t_window = time.time()

            print(f"{step+1:>7} | "
                  f"{pos[0]:>7.2f} {dist:>6.2f} | "
                  f"{w_ccw:>6.4f} {w_cw:>6.4f} {dw:>+7.4f} | "
                  f"{fill:>6.4f} {sat:>5.3f} | "
                  f"{t41:>5.2f}x | "
                  f"{da_win_avg:>6.4f} {pl:>7.3f} {pr:>7.3f} | "
                  f"{phasic_win_max:>6.3f} {i_dr:>5.4f} | {dr5_pct:.1f}%  [{elapsed_win:.0f}s]")

            phasic_win_max = 0.0
            da_window = []

    elapsed   = time.time() - t_start
    w_ccw_f, w_cw_f = get_yaw_weights()
    fill_f = c.energy_store.fill_fraction

    print()
    print("=" * 100)
    print(f"  完成: {STEPS//1000}k 步, 耗时 {elapsed:.1f}s ({elapsed/60:.1f}min)")
    print()
    print("  === P4 验证（200k 长程热趋性）===")

    # P4-1: 100k 后 Δw 维持
    dw_final = abs(w_cw_f - w_ccw_f) if not math.isnan(w_ccw_f) else 0.0
    p41_pass = dw_final > 0.1
    print(f"  P4-1 yaw方向性维持: |Δw|={dw_final:.4f} (w_ccw={w_ccw_f:.4f}, w_cw={w_cw_f:.4f}) "
          f"→ {'PASS (>0.1)' if p41_pass else 'FAIL (方向性回弹或崩溃)'}")

    # P4-2: DR5% > 50%
    final_dr5 = dr5_count / log_count * 100
    p42_pass = final_dr5 > 50.0
    print(f"  P4-2 热趋性方向正确: DR5%={final_dr5:.1f}% "
          f"→ {'PASS (>50%)' if p42_pass else 'FAIL (<50%)'}")

    # P4-3: w_ccw 未崩溃
    p43_pass = (not math.isnan(w_ccw_f)) and w_ccw_f > 0.05
    print(f"  P4-3 CCW束未崩溃: w_ccw={w_ccw_f:.4f} "
          f"→ {'PASS (>0.05)' if p43_pass else 'FAIL (w_ccw过低)'}")

    total = p41_pass and p42_pass and p43_pass
    print()
    print(f"  总体: {'PASS' if total else 'PARTIAL'} "
          f"(P4-1={'✓' if p41_pass else '✗'} "
          f"P4-2={'✓' if p42_pass else '✗'} "
          f"P4-3={'✓' if p43_pass else '✗'})")
    print(f"  fill_final={fill_f:.4f}, phasic_all_max={phasic_all_max:.4f}")
    print(f"  首次接触: step={first_contact_step}")


if __name__ == "__main__":
    main()
