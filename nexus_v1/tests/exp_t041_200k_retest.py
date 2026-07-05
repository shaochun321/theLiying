"""T-041: 200k 步长程复测（T4.1 饱腹期稳定性确认）

目的：确认 T4.1 修复（commit 44214c9）在 200k 步全程中，包括饱腹后 DA 沉寂期，
     T4.1 ratio 不再崩溃（修复前 T-036 从 4.0x → 0.01x）。

设置：与 T-036 完全相同（body=[10,50,25], heat=[70,50,25], fill=0.3, 200k步）

成功标准：
  P8-1: T4.1 全程（所有 20 个 LOG 点）≥ 2.0x（修复前最终值 0.01x）
  P8-2: T4.1 在 step 100k+ 时仍 ≥ 2.0x（DA 沉寂期不崩溃）
  P8-3: |Δw| 最终 > 0.2（方向性分化持续）
  P8-4: DR5% 最终 > 50%
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
    print("  T-041: 200k 步长程复测（T4.1 饱腹期稳定性）")
    print("=" * 90)
    print(f"  T4.1 fix 已生效 (commit 44214c9): axis bundles frozen from STDP")
    print(f"  设置: Body=[10,50,25], Heat=[70,50,25], fill={INIT_FILL}（饥饿）")
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

    phasic_max     = 0.0
    phasic_all_max = 0.0
    dr5_count      = 0
    first_contact  = None
    t41_all        = []   # 记录所有 LOG 点的 T4.1 值
    t_start = time.time()

    for step in range(STEPS):
        c.step({}, DT)

        pos  = c.world.body.position
        dist = math.sqrt(sum((pos[i] - src_pos[i]) ** 2 for i in range(3)))
        pl   = c.phasic_left.activation
        pr   = c.phasic_right.activation
        phasic_max     = max(phasic_max, abs(pl), abs(pr))
        phasic_all_max = max(phasic_all_max, abs(pl), abs(pr))

        if dist < 30 and first_contact is None:
            first_contact = step
            print(f"  >>> 首次接触热场！step={step}, dist={dist:.2f}")

        if step % LOG_INTERVAL == LOG_INTERVAL - 1:
            w_ccw, w_cw = get_yaw_weights()
            dw   = (w_cw - w_ccw) if not math.isnan(w_ccw) else float('nan')
            fill = c.energy_store.fill_fraction
            sat  = c.satiety_neuron.activation if hasattr(c, 'satiety_neuron') else 0.0
            t41  = get_t41_ratio()
            t41_all.append(t41)
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
            phasic_max = 0.0

    elapsed   = time.time() - t_start
    w_ccw_f, w_cw_f = get_yaw_weights()
    fill_f = c.energy_store.fill_fraction
    dw_final = abs(w_cw_f - w_ccw_f) if not math.isnan(w_ccw_f) else 0.0
    dr5_final = dr5_count / (STEPS / LOG_INTERVAL) * 100
    t41_min   = min(t41_all) if t41_all else 0.0
    t41_min100k = min(t41_all[10:]) if len(t41_all) > 10 else t41_min  # 100k 步以后

    print()
    print("=" * 90)
    print(f"  完成: {STEPS//1000}k 步, 耗时 {elapsed:.1f}s ({elapsed/60:.1f}分钟)")
    print()
    print("  === P8 验证（200k T4.1 长程稳定性）===")

    p81_pass = t41_min >= 2.0
    print(f"  P8-1 T4.1 全程 ≥2.0x: 最小值={t41_min:.2f}x "
          f"→ {'PASS' if p81_pass else 'FAIL (T4.1 仍在崩溃!)'}")

    p82_pass = t41_min100k >= 2.0
    print(f"  P8-2 T4.1 100k+步 ≥2.0x (饱腹期): 最小值={t41_min100k:.2f}x "
          f"→ {'PASS' if p82_pass else 'FAIL (饱腹期 T4.1 崩溃!)'}")

    p83_pass = dw_final > 0.2
    print(f"  P8-3 |Δw| > 0.2 (step200k): {dw_final:.4f} "
          f"→ {'PASS' if p83_pass else 'FAIL'}")

    p84_pass = dr5_final > 50.0
    print(f"  P8-4 DR5% > 50%: {dr5_final:.1f}% "
          f"→ {'PASS' if p84_pass else 'FAIL'}")

    total = p81_pass and p82_pass and p83_pass and p84_pass
    print()
    print(f"  总体: {'PASS' if total else 'PARTIAL/FAIL'} "
          f"(P8-1={'✓' if p81_pass else '✗'} "
          f"P8-2={'✓' if p82_pass else '✗'} "
          f"P8-3={'✓' if p83_pass else '✗'} "
          f"P8-4={'✓' if p84_pass else '✗'})")
    print(f"  T4.1: {t41_all[:5]}... → {t41_all[-5:]} (全程{len(t41_all)}点)")
    print(f"  fill_final={fill_f:.4f}, phasic_all_max={phasic_all_max:.4f}")
    print(f"  首次接触: {'step='+str(first_contact) if first_contact else '未发生'}")


if __name__ == "__main__":
    main()
