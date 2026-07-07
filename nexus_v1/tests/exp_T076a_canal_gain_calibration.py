"""
T-076a / Phase 0.5：半规管增益校准

目的：量化测量 canal（yaw）和 otolith（oto_x/y）在 mechanical_inputs 层级的
信号幅值，验证 ANGULAR_GAIN=5000 是否让两者在同一数量级。

判定标准：
  J1: mechanical_inputs['yaw'] 最大值 > 0 （canal 信号确实进入 VestibularChain）
  J2: MET_yaw 激活峰值 > 0.1 且 < 5.0（动态范围良好，非饱和）
  J3: MET_yaw 激活峰值 > 0.001 （canal 信号确实让 MET 激活）
  J4: 旋转期间 yaw 通路激活 > 静止期间 yaw 通路激活（方向性有意义）

  注：canal（角速度）与 otolith（线性加速度）物理量纲不同，不做幅值直接对比（原 J2）。

实验设计：
  Phase 1 (0~2k): 正常运动（CPG 驱动，体向热源移动）
  Phase 2 (2k~3k): 强制 body 旋转（施加角扭矩）
  Phase 3 (3k~5k): 停止旋转，观察 Undershoot（Cupula 弹回）
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

DT = 1.0

def main():
    print("="*68)
    print("  T-076a: 半规管增益校准 (Phase 0.5)")
    print("  判定: J1 canal>0 | J2 canal/oto比 | J3 MET_yaw激活 | J4 旋转vs静止")
    print("="*68)

    SRC_POS = [70.0, 50.0, 25.0]
    src = HeatSource(position=SRC_POS[:], energy=1_000_000.0,
                     temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=[10.0, 50.0, 25.0])
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world
    c.somatosensory.LATERAL_GAIN = 0.3
    for mn in c.motor_neurons.values():
        mn.config.output_gain = 0.1

    STEPS = 5000
    SPIN_START = 2000
    SPIN_STOP  = 3000

    # 监控变量
    yaw_mi_log   = []   # mechanical_inputs['yaw'] 实际值
    otox_mi_log  = []   # mechanical_inputs['oto_x'] 实际值
    met_yaw_log  = []   # MET_yaw 激活
    omega_log    = []   # body.angular_velocity
    theta_log    = []   # Cupula θ（内部状态）

    # 注入 mechanical_inputs 的中间值需要 monkey-patch
    # 我们通过在 step 前后读取来估算（不改母本代码）
    orig_step = c.vestibular.step.__func__

    captured = {}

    def patched_vest_step(self_v, mech_in, dt_v):
        captured['yaw_mi']  = mech_in.get('yaw', 0.0)
        captured['otox_mi'] = mech_in.get('oto_x', 0.0)
        return orig_step(self_v, mech_in, dt_v)

    import types
    c.vestibular.step = types.MethodType(patched_vest_step, c.vestibular)

    print(f"\n  {'step':>6} | {'omega':>8} | {'theta':>10} | {'yaw_mi':>10} | {'oto_x_mi':>10} | {'MET_yaw':>8} | {'phase':>6}")
    print("  " + "-" * 78)

    for step in range(1, STEPS + 1):
        # Phase 2: 强制旋转（施加角扭矩）
        if SPIN_START <= step < SPIN_STOP:
            SPIN_TORQUE = 0.02
            c.world.body.apply_yaw_torque(SPIN_TORQUE, DT)

        c.step({}, DT)

        # 读取后 Cupula 状态
        theta = getattr(c, '_cupula_theta', 0.0)
        omega = c.world.body.angular_velocity

        yaw_mi  = captured.get('yaw_mi', 0.0)
        otox_mi = captured.get('otox_mi', 0.0)

        # MET_yaw 激活
        met_yaw_n = c.vestibular.met_neurons.get('yaw', None)
        met_yaw = met_yaw_n.activation if met_yaw_n else 0.0

        yaw_mi_log.append(abs(yaw_mi))
        otox_mi_log.append(abs(otox_mi))
        met_yaw_log.append(met_yaw)
        omega_log.append(omega)
        theta_log.append(theta)

        if step % 500 == 0 or step == 1:
            phase = "SPIN" if SPIN_START <= step < SPIN_STOP else ("COAST" if step >= SPIN_STOP else "FREE")
            print(f"  {step:>6} | {omega:>8.5f} | {theta:>10.2e} | {yaw_mi:>10.2e} | {otox_mi:>10.2e} | {met_yaw:>8.4f} | {phase:>6}")

    # 分段统计
    def phase_stats(log, lo, hi):
        vals = [log[i] for i in range(lo, hi)]
        if not vals:
            return 0.0, 0.0
        return sum(vals)/len(vals), max(vals)

    free_yaw_mean, free_yaw_peak  = phase_stats(yaw_mi_log, 0, SPIN_START)
    spin_yaw_mean, spin_yaw_peak  = phase_stats(yaw_mi_log, SPIN_START, SPIN_STOP)
    free_oto_mean, free_oto_peak  = phase_stats(otox_mi_log, 0, SPIN_START)
    spin_oto_mean, spin_oto_peak  = phase_stats(otox_mi_log, SPIN_START, SPIN_STOP)
    free_met_mean, free_met_peak  = phase_stats(met_yaw_log, 0, SPIN_START)
    spin_met_mean, spin_met_peak  = phase_stats(met_yaw_log, SPIN_START, SPIN_STOP)

    print(f"\n  Phase 分析：")
    print(f"  {'区段':>12} | {'yaw_mi 均值':>12} | {'yaw_mi 峰值':>12} | {'oto_x 均值':>12} | {'oto_x 峰值':>12}")
    print(f"  " + "-" * 70)
    print(f"  {'FREE (0-2k)':>12} | {free_yaw_mean:>12.2e} | {free_yaw_peak:>12.2e} | {free_oto_mean:>12.2e} | {free_oto_peak:>12.2e}")
    print(f"  {'SPIN (2k-3k)':>12} | {spin_yaw_mean:>12.2e} | {spin_yaw_peak:>12.2e} | {spin_oto_mean:>12.2e} | {spin_oto_peak:>12.2e}")

    overall_yaw_peak = max(yaw_mi_log)
    overall_oto_peak = max(otox_mi_log)
    overall_met_peak = max(met_yaw_log)
    ratio = overall_yaw_peak / max(overall_oto_peak, 1e-12)

    j1 = overall_yaw_peak > 0.0
    j2 = 0.1 <= overall_met_peak < 5.0  # MET 在良好动态范围内（非饱和）
    j3 = overall_met_peak > 0.001
    j4 = spin_yaw_mean > free_yaw_mean * 1.5  # 旋转期信号 > 静止期 1.5×

    print(f"\n  全程 canal 信号峰值:  yaw_mi_peak = {overall_yaw_peak:.2e}")
    print(f"  全程 otolith 信号峰值: oto_x_peak = {overall_oto_peak:.2e}")
    print(f"  MET_yaw 最大激活:      {overall_met_peak:.4f}")
    print(f"  SPIN vs FREE 信号比:   {spin_yaw_mean / max(free_yaw_mean, 1e-12):.2f}×")
    print()
    print(f"  J1  canal信号>0                        {overall_yaw_peak:.2e}  → {'PASS ✅' if j1 else 'FAIL ❌'}")
    print(f"  J2  MET_yaw∈[0.1, 5.0) 非饱和  {overall_met_peak:.4f}  → {'PASS ✅' if j2 else 'FAIL ❌'}")
    print(f"  J3  MET_yaw峰值>0.001          {overall_met_peak:.4f}  → {'PASS ✅' if j3 else 'FAIL ❌'}")
    print(f"  J4  旋转>静止×1.5  {spin_yaw_mean/max(free_yaw_mean,1e-12):.2f}×  → {'PASS ✅' if j4 else 'FAIL ❌'}")
    passed = sum([j1, j2, j3, j4])
    print(f"\n  总计: {passed}/4 PASS")
    print("="*68)


if __name__ == '__main__':
    main()
