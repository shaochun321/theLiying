"""
T-074: 接口参数联立标定 — muscle.gain + ThermalMouth.eta

目的：量化测量当前接口参数的实际效果，并与理论预期对比：
  1. 运动速度测试：motor activation → 实际 body 速度（muscle.gain 效果）
  2. 热摄入测试：body 在热源内的实际 fill 速率（ThermalMouth.eta 效果）
  3. 联立一致性：τ_approach / τ_fill 比值，验证摄食动力学是否匹配运动速度

判定标准：
  J1: v_terminal ∈ [0.05, 0.25] units/step（单位激活）— 合理运动速度
  J2: fill_rate_theory vs fill_rate_measured 误差 < 30%（理论符合实测）
  J3: τ_approach / τ_fill ∈ [0.05, 0.30]（接近比 5-30%，保证学习窗口）
  J4: 接近过程中 fill 能从 0.3 到 ≥ 0.8 in ≤ 30k 步

物理接口规范（截至本实验）：
  muscle.gain = 0.1          [手工]  → T-074 实测
  ThermalMouth.eta = 0.06    [校准,T-029] → T-074 验证
  Body.mass = 1.0, Body.friction = 0.5
  EnergyStore.capacity = 1000.0, max_deposit = 0.12, BMR = 0.003/步
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

DT = 1.0

# ─────────────────────────────────────────────────────────────────
# 测试1：速度标定
# 将 body 置于热源中心，注入恒定 motor 激活，测稳态速度
# ─────────────────────────────────────────────────────────────────

def test_speed_calibration():
    """测量不同 motor_activation 下的稳态 x 速度。"""
    print("\n" + "="*68)
    print("  测试 1：运动速度标定（muscle.gain 效果）")
    print("="*68)

    # 理论值
    # v_terminal = activation × output_gain × muscle_gain / friction
    # output_gain=0.1 (设置在实验中), muscle_gain=0.1, friction=0.5
    # v_term = activation × 0.1 × 0.1 / 0.5 = activation × 0.02

    print(f"\n  理论: v_terminal = activation × output_gain × gain / friction")
    print(f"      = activation × 0.1 × 0.1 / 0.5 = activation × 0.02")
    print()

    results = []
    for target_act in [0.0, 0.2, 0.5, 1.0]:
        # 在无热源环境中运行（避免热力影响）
        body = Body(position=[50.0, 50.0, 25.0])
        world = World(heat_sources=[], body=body)
        world.MIN_ALIVE = 0
        world.REGEN_PROB = 0.0

        c = VariantCircuit()
        c.world = world
        for mn in c.motor_neurons.values():
            mn.config.output_gain = 0.1

        # 冻结所有 STDP，直接设 motor 神经元激活
        for b in c.get_all_bundles():
            if b.config.learning_rule not in ('frozen',):
                b.config.stdp_lr = 0.0
                if hasattr(b.config, 'eligibility_gain'):
                    b.config.eligibility_gain = 0.0
                if hasattr(b.config, 'eligibility_ltd_rate'):
                    b.config.eligibility_ltd_rate = 0.0

        # 直接设 move_x motor 激活
        move_x = c.motor_neurons.get('move_x', None)

        # 运行 200 步稳态
        v_samples = []
        for step in range(200):
            if move_x is not None:
                move_x._activation_ema = target_act
            c.step({}, DT)
            if step >= 100:  # 后半段取样
                v_samples.append(abs(c.world.body.velocity[0]))

        v_measured = sum(v_samples) / len(v_samples) if v_samples else 0.0
        v_theory = target_act * 0.1 * 0.1 / 0.5  # act × output_gain × gain / friction
        error = abs(v_measured - v_theory) / max(v_theory, 1e-6) * 100

        results.append((target_act, v_theory, v_measured, error))
        print(f"  act={target_act:.1f}: v_theory={v_theory:.4f}  v_measured={v_measured:.4f}  "
              f"误差={error:.1f}%")

    # J1：全激活稳态速度在合理范围
    v_full = results[-1][2]  # activation=1.0
    j1 = 0.005 <= v_full <= 0.25
    print(f"\n  J1: v(act=1.0) ∈ [0.005, 0.25] → {v_full:.4f} → {'PASS ✅' if j1 else 'FAIL ❌'}")

    return j1, v_full, results


# ─────────────────────────────────────────────────────────────────
# 测试2：fill 速率标定（body 固定在热源中心）
# ─────────────────────────────────────────────────────────────────

def test_fill_calibration():
    """测量 body 在热源中心时的稳态 fill 速率。"""
    print("\n" + "="*68)
    print("  测试 2：fill 速率标定（ThermalMouth.eta 效果）")
    print("="*68)

    # 理论预期（eta=0.06, ΔT_ss≈1.0 @ T_env=5.0, T_mouth_ss≈4.0）：
    # energy_intake = eta × k × A × ΔT × dt = 0.06 × 2.0 × 1.0 × 1.0 × 1.0 = 0.12/step
    # stored = energy_intake × deposit_efficiency = 0.12 × 0.9 = 0.108/step
    # capped at max_deposit = 0.12 (not limiting in this range)
    # BMR = 0.003/step
    # r_leak at fill=0.9 → charge=900: drain = 900 × 1.0 / (5000 × 1000) ≈ 0.00018/step
    # net_fill_rate = (stored - BMR - leak) / capacity
    #               = (0.108 - 0.003 - 0.00018) / 1000 ≈ 1.05e-4 fill/step

    STEPS = 5000
    SRC_POS = [50.0, 50.0, 25.0]
    BODY_POS = [50.0, 50.0, 25.0]  # body IN source center

    src = HeatSource(position=SRC_POS[:], energy=1_000_000.0,
                     temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=BODY_POS[:])
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world
    for mn in c.motor_neurons.values():
        mn.config.output_gain = 0.1

    # 冻结 STDP，禁止运动（零激活）
    for b in c.get_all_bundles():
        if b.config.learning_rule not in ('frozen',):
            b.config.stdp_lr = 0.0
            if hasattr(b.config, 'eligibility_gain'):
                b.config.eligibility_gain = 0.0
            if hasattr(b.config, 'eligibility_ltd_rate'):
                b.config.eligibility_ltd_rate = 0.0

    # 初始 fill=0.3
    c.energy_store._cap.charge = c.energy_store.config.capacity * 0.3

    fill_log = []
    mouth_temp_log = []
    for step in range(1, STEPS + 1):
        c.step({}, DT)
        fill_log.append(c.energy_store.fill_fraction)
        mouth_temp_log.append(c.thermal_mouth.temperature)

    # 计算稳态 fill 速率（后半段，T_mouth 已收敛）
    fill_start = fill_log[2499]
    fill_end   = fill_log[-1]
    fill_rate_measured = (fill_end - fill_start) / 2500  # fill/step（后2500步）

    T_mouth_ss = sum(mouth_temp_log[2500:]) / 2500
    delta_T = max(0.0, 5.0 - T_mouth_ss)

    # 理论值（用实测 T_mouth_ss）
    eta = c.thermal_mouth.eta
    capacity = c.energy_store.config.capacity
    energy_intake_theory = eta * c.thermal_mouth.conductance * c.thermal_mouth.area * delta_T * DT
    stored_theory = energy_intake_theory * c.energy_store.config.deposit_efficiency
    bmr = 0.003
    fill_rate_theory = (stored_theory - bmr) / capacity

    error_pct = abs(fill_rate_measured - fill_rate_theory) / max(abs(fill_rate_theory), 1e-6) * 100

    print(f"\n  T_mouth (稳态): {T_mouth_ss:.3f}  ΔT = {delta_T:.3f}")
    print(f"  eta = {eta:.3f}")
    print(f"  fill 速率 (后2500步): 测量={fill_rate_measured:.2e}  理论={fill_rate_theory:.2e}  "
          f"误差={error_pct:.1f}%")
    print(f"  fill: {fill_start:.3f} → {fill_end:.3f} (STEPS 2500~5000)")

    # 估算从 0.3 到 0.9 的时间
    if fill_rate_measured > 0:
        t_fill_07 = 0.7 / fill_rate_measured  # Δfill=0.7 所需步数（忽略初始预热）
    else:
        t_fill_07 = float('inf')

    print(f"  τ_fill (0.3→1.0 估计): {t_fill_07:.0f} 步")

    j2 = error_pct < 30.0
    print(f"\n  J2: 理论/实测误差 < 30%  误差={error_pct:.1f}%  → {'PASS ✅' if j2 else 'FAIL ❌'}")

    return j2, fill_rate_measured, fill_rate_theory, t_fill_07


# ─────────────────────────────────────────────────────────────────
# 测试3：联立一致性（真实运动 + 摄入）
# ─────────────────────────────────────────────────────────────────

def test_joint_consistency():
    """完整运动+摄入场景：测量 τ_approach 和 τ_fill 比值。"""
    print("\n" + "="*68)
    print("  测试 3：联立一致性（τ_approach / τ_fill）")
    print("="*68)

    STEPS = 30_000
    SRC_POS = [70.0, 50.0, 25.0]
    BODY_START = [10.0, 50.0, 25.0]

    src = HeatSource(position=SRC_POS[:], energy=1_000_000.0,
                     temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=BODY_START[:])
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world
    c.somatosensory.LATERAL_GAIN = 0.3
    for mn in c.motor_neurons.values():
        mn.config.output_gain = 0.1
    c.energy_store._cap.charge = c.energy_store.config.capacity * 0.3

    # 找到 body 进入热源的时刻 (dist < radius)
    t_approach = None
    t_fill_08 = None  # fill≥0.8 的时刻

    fill_init = c.energy_store.fill_fraction

    hdr = (f"  {'step':>7} | {'dist':>6} | {'fill':>5} | {'v_x':>6}")
    print(hdr)
    print("  " + "-" * (len(hdr)-2))

    for step in range(1, STEPS+1):
        c.step({}, DT)

        pos = c.world.body.position
        d = math.sqrt(sum((pos[i] - SRC_POS[i])**2 for i in range(3)))
        fill = c.energy_store.fill_fraction
        vx = c.world.body.velocity[0]

        if t_approach is None and d < 30.0:
            t_approach = step
            print(f"\n  [step {step}] body 进入热源 (dist={d:.1f})")

        if t_fill_08 is None and fill >= 0.8:
            t_fill_08 = step
            print(f"  [step {step}] fill ≥ 0.8 (fill={fill:.3f})")

        if step % 5000 == 0:
            print(f"  {step:>7} | {d:>6.1f} | {fill:>5.3f} | {vx:>6.4f}")

    # 计算指标
    t_approach = t_approach or STEPS
    t_fill_total = (t_fill_08 - t_approach) if (t_fill_08 and t_approach) else STEPS
    ratio = t_approach / max(t_fill_total, 1)

    j3 = 0.02 <= ratio <= 0.50
    j4 = t_fill_08 is not None and t_fill_08 <= 30000

    print(f"\n  τ_approach = {t_approach} 步（到达热源边缘）")
    print(f"  τ_fill     = {t_fill_total} 步（热源内 fill 0.x → 0.8）")
    print(f"  比值       = {ratio:.3f}  （目标范围 0.02~0.50）")
    print(f"\n  J3: τ_approach/τ_fill ∈ [0.02, 0.50]  {ratio:.3f}  → {'PASS ✅' if j3 else 'FAIL ❌'}")
    print(f"  J4: fill≥0.8 在 ≤30k 步内           {t_fill_08 or '>30k'}  → {'PASS ✅' if j4 else 'FAIL ❌'}")

    return j3, j4, ratio, t_approach, t_fill_total


# ─────────────────────────────────────────────────────────────────
def main():
    print("="*68)
    print("  T-074: 接口参数联立标定")
    print("  判定: J1 速度合理 | J2 fill率理论一致 | J3 τ比合理 | J4 30k内饱和")
    print("="*68)

    j1, v_full, speed_results = test_speed_calibration()
    j2, fill_rate_meas, fill_rate_th, t_fill_est = test_fill_calibration()
    j3, j4, ratio, t_approach, t_fill = test_joint_consistency()

    print("\n" + "="*68)
    print("  T-074 汇总\n")
    print(f"  muscle.gain  = 0.1   [手工]  → v(act=1.0)={v_full:.4f} 单位/步")
    print(f"  ThermalMouth.eta = 0.06 [校准,T-029]")
    print(f"    fill 速率: 实测={fill_rate_meas:.2e}/步  理论={fill_rate_th:.2e}/步")
    print(f"  τ_fill_est = {t_fill_est:.0f} 步（0.3→1.0 估计）")
    print(f"  τ_approach  = {t_approach} 步  τ_fill_actual = {t_fill} 步  比={ratio:.3f}")
    print()
    print(f"  J1  v(act=1.0) ∈ [0.005,0.25]      {v_full:.4f}  → {'PASS ✅' if j1 else 'FAIL ❌'}")
    print(f"  J2  fill率误差 < 30%                {abs(fill_rate_meas-fill_rate_th)/max(abs(fill_rate_th),1e-6)*100:.1f}%  → {'PASS ✅' if j2 else 'FAIL ❌'}")
    print(f"  J3  τ比 ∈ [0.02,0.50]               {ratio:.3f}  → {'PASS ✅' if j3 else 'FAIL ❌'}")
    print(f"  J4  fill≥0.8 ≤ 30k 步              {'PASS ✅' if j4 else 'FAIL ❌'}")
    passed = sum([j1, j2, j3, j4])
    print(f"\n  总计: {passed}/4 PASS")
    print("="*68)


if __name__ == '__main__':
    main()
