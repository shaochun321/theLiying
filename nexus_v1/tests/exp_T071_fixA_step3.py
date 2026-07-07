"""
T-071-fix-A Step3 (sp2y_w=0.200) — 50k DR5验证

目标：验证 sp2y_w=0.200（10x 原始值）是否引起 yaw 振荡或 T4.1 下降。

Step2结果 (sp2y_w=0.100)：
  体在5k步内进入热源半径 (dist=21)，fill=1.0 at 25k。
  T4.1 50k末 = 7.5x (增长)；approach-phase DR5=57%（方向正确）。
  结论：T4.1未下降，进入Step3。

Step3 观察指标：
  - yaw振荡：|omega_std| > 3x baseline = 触发回滚
  - T4.1 < 5.5x = 触发回滚
  - 接近速度：体到达热源步数

回滚条件：yaw振荡 > 3x 或 T4.1 < 5.5x → 回退到 0.100
"""
import sys
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

DT = 1.0

def main():
    print("T-071-fix-A Step3 (sp2y_w=0.200) — 50k DR5验证")
    print(f"  {'step':>7} | {'DR5%':>6} | {'dist':>5} | {'w_ccw':>6} {'w_cw':>6} | {'T4.1':>6} | {'fill':>6} | {'omega_std':>9}")
    print("-" * 80)

    src = HeatSource(position=[70.0, 50.0, 25.0], energy=1_000_000.0,
                     temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=[10.0, 50.0, 25.0])
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world

    TOTAL = 50000
    SAMPLE = 5000

    prev_dist = None
    window_dr5 = []
    window_omega = []
    all_dr5 = []
    approach_step = None

    for step in range(1, TOTAL + 1):
        c.step({}, DT)

        pos = c.world.body.position
        src_pos = c.world.heat_sources[0].position
        dist = ((pos[0] - src_pos[0])**2 + (pos[1] - src_pos[1])**2 + (pos[2] - src_pos[2])**2) ** 0.5
        fill = c.energy_store.fill_fraction if hasattr(c, 'energy_store') else 0.0
        omega = c.world.body.angular_velocity

        if prev_dist is not None:
            dr5 = 1 if dist < prev_dist else 0
            window_dr5.append(dr5)
            all_dr5.append(dr5)
        prev_dist = dist

        window_omega.append(abs(omega))

        if approach_step is None and dist < 30.0:
            approach_step = step

        if step % SAMPLE == 0:
            # Get weights from frozen bundles (weight_matrix()[src][tgt])
            w_ccw = c.bundle_spinal_ccw_to_yaw.weight_matrix()[0][0] if hasattr(c, 'bundle_spinal_ccw_to_yaw') else 0.0
            w_cw  = c.bundle_spinal_cw_to_yaw.weight_matrix()[0][0]  if hasattr(c, 'bundle_spinal_cw_to_yaw')  else 0.0

            # T4.1 proxy: axis/cross weight ratio
            try:
                from nexus_v1.tests.test_regression import _run_t4_axis_cross
                t41 = 0.0
            except Exception:
                t41 = 0.0

            # Estimate T4.1 from ccw/cw d1 bundles
            try:
                w_d1_ccw = c.bundle_d1_phasic_left_to_spinal_ccw.weight_matrix()[0][0]
                w_d1_cw  = c.bundle_d1_phasic_right_to_spinal_cw.weight_matrix()[0][0]
                w_cross = max(
                    c.bundle_d1_phasic_left_to_spinal_cw.weight_matrix()[0][0],
                    c.bundle_d1_phasic_right_to_spinal_ccw.weight_matrix()[0][0]
                )
                axis_avg = (w_d1_ccw + w_d1_cw) / 2.0
                t41_proxy = axis_avg / (w_cross + 1e-9)
            except Exception:
                t41_proxy = 0.0

            dr5_pct = sum(window_dr5) / len(window_dr5) * 100 if window_dr5 else 0.0
            omega_std = (sum((x - sum(window_omega)/len(window_omega))**2 for x in window_omega) / len(window_omega))**0.5 if window_omega else 0.0

            print(f"  {step:7d} | {dr5_pct:5.1f}% | {dist:5.0f} | {w_ccw:.4f} {w_cw:.4f} | {t41_proxy:5.1f}x | {fill:.3f} | {omega_std:.4f}")
            window_dr5 = []
            window_omega = []

    # Final report
    total_dr5 = sum(all_dr5) / len(all_dr5) * 100 if all_dr5 else 0.0
    print()
    print(f"Final w_ccw={c.bundle_spinal_ccw_to_yaw.weight_matrix()[0][0]:.5f}  w_cw={c.bundle_spinal_cw_to_yaw.weight_matrix()[0][0]:.5f}")
    print(f"Overall DR5={total_dr5:.1f}%  approach_step={'未到达' if approach_step is None else approach_step}")

    # Rollback check
    print()
    print("=== Step3 回滚判断 ===")
    print(f"T4.1 proxy at 50k: see above (rollback if < 5.5x)")
    print(f"Approach to heat source: {approach_step}")

if __name__ == '__main__':
    main()
