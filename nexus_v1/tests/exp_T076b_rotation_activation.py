"""
T-076b / Phase 1：旋转激活验证

目的：验证 Cupula 高通滤波器的三个核心物理行为：
  1. 旋转开始时 MET_yaw 激活（onset response）
  2. 持续旋转时 MET_yaw 逐渐适应（adaptation）
  3. 旋转停止时 MET_yaw 短暂反向（undershoot / stop response）

判定标准：
  J1: onset_peak > baseline_mean + 3 × baseline_std（旋转触发激活超过基线 3σ）
  J2: adapt_late < onset_peak × 0.5（持续旋转后激活衰减 > 50%，适应发生）
  J3: theta_reversal = True（停止后 Cupula theta 反向，即 theta < 0；
      MET 经半波整流不可负，undershoot 在 theta 层可见）
  J4: baseline_max < 0.01（基线期噪声低，信号干净）

实验设计：
  Phase 0 (0~1k):  静止基线（无旋转，记录 MET_yaw 噪声水平）
  Phase 1 (1k~2k): onset — 持续施加旋转扭矩，观察激活上升
  Phase 2 (2k~4k): adapt — 维持旋转，观察 MET_yaw 衰减（Cupula 适应恒速）
  Phase 3 (4k~5k): stop — 移除扭矩，观察停止后 Undershoot
"""
import sys
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

DT = 1.0
SPIN_TORQUE = 0.05  # 较强扭矩，确保明显旋转

def main():
    print("="*68)
    print("  T-076b: 旋转激活验证 (Phase 1)")
    print("  判定: J1 onset>3σ | J2 适应>50% | J3 停止反向 | J4 基线噪声低")
    print("="*68)

    src = HeatSource(position=[70.0, 50.0, 25.0], energy=1_000_000.0,
                     temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=[10.0, 50.0, 25.0])
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world

    PHASE0_END = 1000
    PHASE1_END = 2000
    PHASE2_END = 4000
    PHASE3_END = 5000
    STEPS = PHASE3_END

    met_log = []
    omega_log = []
    theta_log = []

    print(f"\n  {'step':>6} | {'phase':>8} | {'omega':>8} | {'theta':>10} | {'MET_yaw':>8}")
    print("  " + "-" * 55)

    for step in range(1, STEPS + 1):
        phase = (
            "BASELINE" if step <= PHASE0_END else
            "ONSET"    if step <= PHASE1_END else
            "ADAPT"    if step <= PHASE2_END else
            "STOP"
        )
        # 旋转区间施加扭矩
        if PHASE0_END < step <= PHASE2_END:
            c.world.body.apply_yaw_torque(SPIN_TORQUE, DT)

        c.step({}, DT)

        met_n = c.vestibular.met_neurons.get('yaw', None)
        met = met_n.activation if met_n else 0.0
        omega = c.world.body.angular_velocity
        theta = getattr(c, '_cupula_theta', 0.0)

        met_log.append(met)
        omega_log.append(omega)
        theta_log.append(theta)

        if step % 500 == 0 or step == 1:
            print(f"  {step:>6} | {phase:>8} | {omega:>8.5f} | {theta:>10.2e} | {met:>8.4f}")

    # 分段统计
    baseline_vals = met_log[:PHASE0_END]
    onset_vals    = met_log[PHASE0_END:PHASE1_END]
    adapt_vals    = met_log[PHASE1_END:PHASE2_END]
    stop_vals     = met_log[PHASE2_END:PHASE3_END]

    baseline_mean = sum(baseline_vals) / len(baseline_vals)
    baseline_std  = (sum((x - baseline_mean)**2 for x in baseline_vals) / len(baseline_vals)) ** 0.5
    baseline_max  = max(baseline_vals)

    onset_peak    = max(onset_vals)
    adapt_early   = sum(onset_vals[:100]) / 100
    adapt_late    = sum(adapt_vals[-500:]) / 500  # 适应后期均值
    stop_min      = min(stop_vals)
    # J3: Cupula theta 反向（高通滤波器停止响应），MET 因半波整流不可负
    theta_stop_min = min(theta_log[PHASE2_END:PHASE3_END])
    theta_stop_reversal = theta_stop_min < 0.0

    j1 = onset_peak > baseline_mean + 3 * baseline_std
    j2 = adapt_late < onset_peak * 0.5
    j3 = theta_stop_reversal
    j4 = baseline_max < 0.01

    print(f"\n  基线统计 (0~1k):")
    print(f"    baseline_mean = {baseline_mean:.6f}, baseline_std = {baseline_std:.6f}")
    print(f"    baseline_max  = {baseline_max:.6f}")
    print(f"\n  旋转激活 (1k~2k):")
    print(f"    onset_peak    = {onset_peak:.4f}")
    print(f"    3σ阈值        = {baseline_mean + 3*baseline_std:.6f}")
    print(f"\n  适应衰减 (2k~4k):")
    print(f"    adapt_early   = {adapt_early:.4f}  （onset结束时）")
    print(f"    adapt_late    = {adapt_late:.4f}  （适应后期均值）")
    print(f"    衰减率        = {(1 - adapt_late/max(onset_peak, 1e-9))*100:.1f}%")
    print(f"\n  停止反向 (4k~5k):")
    print(f"    stop_min_met  = {stop_min:.6f} (MET，整流后不可负)")
    print(f"    theta_stop_min= {theta_stop_min:.2e} (Cupula theta，可反向)")
    print(f"    theta反向     = {theta_stop_reversal}")
    print()

    print(f"  J1  onset>基线+3σ  peak={onset_peak:.4f} > {baseline_mean+3*baseline_std:.6f}  → {'PASS ✅' if j1 else 'FAIL ❌'}")
    print(f"  J2  适应>50%       late={adapt_late:.4f} < {onset_peak*0.5:.4f}  → {'PASS ✅' if j2 else 'FAIL ❌'}")
    print(f"  J3  Cupula theta反向  theta_min={theta_stop_min:.2e} < 0  → {'PASS ✅' if j3 else 'FAIL ❌'}")
    print(f"  J4  基线噪声低     baseline_max={baseline_max:.6f} < 0.01  → {'PASS ✅' if j4 else 'FAIL ❌'}")

    passed = sum([j1, j2, j3, j4])
    print(f"\n  总计: {passed}/4 PASS")
    print("="*68)


if __name__ == '__main__':
    main()
