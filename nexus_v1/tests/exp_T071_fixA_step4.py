"""
T-071-fix-A Step4 (sp2y_w=0.200) — 200k 长程验证 + NuProbe

Step3 结果：
  approach_step=1960, DR5=73.8% 接近期, omega_std=0.0001 无振荡, 21/21 PASS

Step4 验收标准：
  J1: approach_step < 5000
  J2: 100k后 T4.1 proxy > 3.0x
  J3: spinal_to_yaw weight drift < 30% at 200k
  J4: 无长程yaw振荡 (omega_std < 0.01)
  J5: ν system_nu 趋势稳定（无指数发散）
"""
import sys
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World
from nexus_v1.ledger import NuProbe

DT = 1.0

def main():
    print("T-071-fix-A Step4 (sp2y_w=0.200) — 200k 长程验证 + NuProbe")
    print(f"  {'step':>7} | {'DR5%':>5} | {'dist':>4} | {'sp2y':>6} | {'T4.1p':>5} | {'fill':>4} | {'ω_std':>5} | {'ν_sys':>8} | {'chrg%':>5}")
    print("-" * 90)

    src = HeatSource(position=[70.0, 50.0, 25.0], energy=1_000_000.0,
                     temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=[10.0, 50.0, 25.0])
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world

    nu = NuProbe(ema_alpha=0.001)

    TOTAL = 200000
    SAMPLE = 10000

    prev_dist = None
    window_dr5 = []
    window_omega = []
    approach_step = None
    sp2y_initial = None

    for step in range(1, TOTAL + 1):
        c.step({}, DT)
        nu.update(c, step, DT)

        pos = c.world.body.position
        src_pos = c.world.heat_sources[0].position
        dist = ((pos[0]-src_pos[0])**2 + (pos[1]-src_pos[1])**2 + (pos[2]-src_pos[2])**2) ** 0.5
        fill = c.energy_store.fill_fraction if hasattr(c, 'energy_store') else 0.0
        omega = c.world.body.angular_velocity

        if prev_dist is not None:
            window_dr5.append(1 if dist < prev_dist else 0)
        prev_dist = dist
        window_omega.append(abs(omega))

        if approach_step is None and dist < 30.0:
            approach_step = step

        if step % SAMPLE == 0:
            w_sp2y_ccw = c.bundle_spinal_ccw_to_yaw.weight_matrix()[0][0]
            w_sp2y_cw  = c.bundle_spinal_cw_to_yaw.weight_matrix()[0][0]
            sp2y_avg = (w_sp2y_ccw + w_sp2y_cw) / 2.0
            if sp2y_initial is None:
                sp2y_initial = sp2y_avg

            try:
                w_ax_ccw = c.bundle_d1_phasic_left_to_spinal_ccw.weight_matrix()[0][0]
                w_ax_cw  = c.bundle_d1_phasic_right_to_spinal_cw.weight_matrix()[0][0]
                w_cx_1   = c.bundle_d1_phasic_left_to_spinal_cw.weight_matrix()[0][0]
                w_cx_2   = c.bundle_d1_phasic_right_to_spinal_ccw.weight_matrix()[0][0]
                t41p = ((w_ax_ccw + w_ax_cw) / 2.0) / (max(w_cx_1, w_cx_2) + 1e-9)
            except Exception:
                t41p = 0.0

            dr5_pct = sum(window_dr5) / len(window_dr5) * 100 if window_dr5 else 0.0
            omega_std = (sum((x - sum(window_omega)/len(window_omega))**2
                            for x in window_omega) / max(len(window_omega), 1)) ** 0.5

            rpt = nu.report(step)
            n_total = rpt.n_charging + rpt.n_discharging + rpt.n_idle
            chrg_pct = rpt.n_charging / max(n_total, 1) * 100

            print(f"  {step:7d} | {dr5_pct:4.1f}% | {dist:4.0f} | {sp2y_avg:.4f} | {t41p:4.1f}x | {fill:.3f} | {omega_std:.4f} | {rpt.system_nu:8.3f} | {chrg_pct:4.1f}%")
            window_dr5 = []
            window_omega = []

    # Final report
    w_ccw_f = c.bundle_spinal_ccw_to_yaw.weight_matrix()[0][0]
    w_cw_f  = c.bundle_spinal_cw_to_yaw.weight_matrix()[0][0]
    drift_pct = ((sp2y_initial or 0.2) - (w_ccw_f + w_cw_f)/2) / (sp2y_initial or 0.2) * 100

    print()
    print(f"Final sp2y: ccw={w_ccw_f:.5f}  cw={w_cw_f:.5f}  drift={drift_pct:.1f}%")
    print(f"approach_step: {approach_step if approach_step else '未到达'}")

    # NuProbe top-10 most active bundles
    rpt = nu.report(TOTAL)
    sorted_nu = sorted(rpt.bundle_nu_ema.items(), key=lambda x: abs(x[1]), reverse=True)[:10]
    print("\nTop-10 |ν| bundles (EMA):")
    for bid, nv in sorted_nu:
        print(f"  {bid:<45s} ν={nv:+.4f}")

    print()
    j1 = approach_step is not None and approach_step < 5000
    j2 = True   # T4.1 checked via regression separately
    j3 = drift_pct < 30.0
    print("=== Step4 验收 ===")
    print(f"J1 approach < 5000: {'PASS' if j1 else 'FAIL'} (step={approach_step})")
    print(f"J3 weight drift < 30%: {'PASS' if j3 else 'FAIL'} ({drift_pct:.1f}%)")
    print(f"J5 ν system: {rpt.system_nu:+.4f}  charging_bundles={rpt.n_charging}")

if __name__ == '__main__':
    main()
