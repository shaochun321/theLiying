"""
Step 2 诊断：SatietyNeuron V_ss 脉冲积分验证 + R3-Pre phasic 基线采样

目标：
  1. 在真实进食场景（热源在场，organism 可接近）下运行 30k 步
  2. 记录 satiety_neuron.activation 是否能超过 0.1
  3. 计算 V_ss_real = I_peak × R × Duty_Cycle 理论值并与实测对比
  4. 输出 phasic_left/right 幅度的 [min, mean, max, σ] 供 Step 3 R3-Pre 使用

运行：
  PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.diag_step2_satiety_vss
"""
import sys, os, math, statistics
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit

N_STEPS       = 30_000
REPORT_EVERY  = 1000
SATIETY_PASS  = 0.1   # 通过阈值

def run():
    print("=== Step 2: SatietyNeuron V_ss 诊断 ===\n")
    c = VariantCircuit()
    # 使用默认 World（8个热源 + 圆柱热源），body 初始位置 [63,25,25]，最近热源 [75,25,25] 距离≈12

    # ── 采样缓冲 ──
    satiety_history    = []
    dwell_history      = []
    intake_history     = []
    fillrate_history   = []
    phasic_left_hist   = []
    phasic_right_hist  = []
    deposit_rate_hist  = []
    fill_frac_history  = []

    satiety_first_pass = None   # 首次超过 SATIETY_PASS 的步数

    print(f"{'Step':>7}  {'satiety':>8}  {'dwell_V':>8}  {'intake':>7}  {'fill_frac':>9}  {'v_feed':>8}  {'phasic_L':>9}  {'phasic_R':>9}")
    print("-" * 88)

    for step in range(N_STEPS):
        c.step({}, dt=1.0)

        sat_act  = c.satiety_neuron.activation
        dwell_v  = c.dwell_sensor_neuron._membrane.voltage
        intake_a = c.intake_sensor_neuron.activation
        fill_a   = c.fill_rate_sensor_neuron.activation
        phasic_l = c.phasic_left.activation  if hasattr(c, 'phasic_left')  else 0.0
        phasic_r = c.phasic_right.activation if hasattr(c, 'phasic_right') else 0.0
        dep_r    = getattr(c, '_v_feed', 0.0)   # FeedRateCapacitor 电压（进食信号代理）
        ff       = c.energy_store.fill_fraction

        satiety_history.append(sat_act)
        dwell_history.append(dwell_v)
        intake_history.append(intake_a)
        fillrate_history.append(fill_a)
        phasic_left_hist.append(phasic_l)
        phasic_right_hist.append(phasic_r)
        deposit_rate_hist.append(dep_r)
        fill_frac_history.append(ff)

        if satiety_first_pass is None and sat_act >= SATIETY_PASS:
            satiety_first_pass = step

        if (step + 1) % REPORT_EVERY == 0:
            print(f"{step+1:>7}  {sat_act:>8.4f}  {dwell_v:>8.4f}  {intake_a:>7.4f}  {ff:>9.4f}  {dep_r:>8.5f}  {phasic_l:>9.5f}  {phasic_r:>9.5f}")

    # ── 分析 ──
    print("\n" + "=" * 60)
    print("== 结果分析 ==")
    print()

    # Satiety
    sat_max  = max(satiety_history)
    sat_final= satiety_history[-1]
    print(f"Satiety neuron:")
    print(f"  最大值:   {sat_max:.4f}")
    print(f"  最终值:   {sat_final:.4f}")
    print(f"  通过阈值: {SATIETY_PASS}")
    if satiety_first_pass is not None:
        print(f"  首次超过阈值: step {satiety_first_pass}")
    else:
        print(f"  ⚠ 全程未超过阈值 {SATIETY_PASS}")

    # 占空比分析
    intake_nonzero = [v for v in intake_history if v > 0.001]
    duty_cycle = len(intake_nonzero) / N_STEPS
    intake_peak = max(intake_history) if intake_history else 0.0
    # satiety R = r_leak = 1.0, intake bundle w=0.975, sg=1.0
    # I_intake_eff = intake_mean_active × w × sg (approximate)
    intake_mean_active = statistics.mean(intake_nonzero) if intake_nonzero else 0.0
    I_eff = intake_mean_active * 0.975 * duty_cycle
    V_ss_theory = I_eff * 1.0   # r_leak=1.0
    print()
    print(f"占空比分析 (intake_sensor):")
    print(f"  有效步数比例: {duty_cycle:.3f} ({int(duty_cycle*N_STEPS)}/{N_STEPS})")
    print(f"  激活期均值:   {intake_mean_active:.4f}")
    print(f"  峰值:         {intake_peak:.4f}")
    print(f"  理论 V_ss (intake alone): {V_ss_theory:.4f}  (= mean_active × w × duty_cycle × R)")

    # Dwell
    dwell_max  = max(dwell_history)
    dwell_mean = statistics.mean(dwell_history)
    print()
    print(f"DwellSensor (V_ss_design = bc × R = 0.02 × 50 = 1.0):")
    print(f"  最大电压: {dwell_max:.4f}")
    print(f"  均值:     {dwell_mean:.4f}")

    # Fill fraction
    ff_min  = min(fill_frac_history)
    ff_mean = statistics.mean(fill_frac_history)
    ff_final= fill_frac_history[-1]
    print()
    print(f"EnergyStore fill_fraction:")
    print(f"  最小值: {ff_min:.4f}  均值: {ff_mean:.4f}  最终: {ff_final:.4f}")
    if ff_min < 0.05:
        print(f"  !! 能量链告警: fill_fraction 跌破 0.05 (death threshold)")

    # v_feed
    vfeed_max  = max(deposit_rate_hist)
    vfeed_mean = statistics.mean(deposit_rate_hist)
    nonzero_vf = [v for v in deposit_rate_hist if v > 1e-4]
    vfeed_duty = len(nonzero_vf) / N_STEPS
    print()
    print(f"v_feed (FeedRateCapacitor, 进食信号代理):")
    print(f"  最大值: {vfeed_max:.5f}  均值: {vfeed_mean:.5f}  有效占空比: {vfeed_duty:.3f}")

    # Phasic (R3-Pre)
    all_phasic = phasic_left_hist + phasic_right_hist
    p_min  = min(all_phasic)
    p_max  = max(all_phasic)
    p_mean = statistics.mean(all_phasic)
    p_std  = statistics.stdev(all_phasic) if len(all_phasic) > 1 else 0.0
    quiet  = [v for v in all_phasic if v < 0.005]
    q_std  = statistics.stdev(quiet) if len(quiet) > 1 else 0.0
    q_mean = statistics.mean(quiet) if quiet else 0.0
    print()
    print(f"Phasic 幅度 (R3-Pre 施密特阈值校准):")
    print(f"  全程 min={p_min:.5f}  mean={p_mean:.5f}  max={p_max:.5f}  σ={p_std:.5f}")
    print(f"  静默段 (< 0.005): n={len(quiet)}  mean={q_mean:.5f}  σ={q_std:.5f}")
    on_thresh_suggest  = max(0.01, p_max * 0.5)
    off_thresh_suggest = max(0.005, q_mean + 2 * q_std)
    print(f"  建议 on_thresh  = max(peak×0.5, 0.01) = {on_thresh_suggest:.5f}")
    print(f"  建议 off_thresh = max(q_mean+2σ, 0.005) = {off_thresh_suggest:.5f}")

    # 总结
    print()
    sat_ok = sat_max >= SATIETY_PASS
    ff_ok  = ff_min > 0.05
    print(f"{'✓' if sat_ok else '✗'} SatietyNeuron 超过阈值 {SATIETY_PASS}: {'PASS' if sat_ok else 'FAIL'}")
    print(f"{'✓' if ff_ok  else '✗'} EnergyStore 全程 > 0.05: {'PASS' if ff_ok else 'FAIL (能量链断裂风险)'}")
    if not sat_ok:
        print(f"\n⚠ SatietyNeuron 未达阈值，最大仅 {sat_max:.4f}。")
        print(f"  原因：V_ss_real = I_peak × R × Duty_Cycle ≈ {V_ss_theory:.4f} (intake 路径)")
        print(f"  如果占空比不足，需调整 dwell_to_satiety 权重或降低饱腹激活阈值。")

if __name__ == '__main__':
    run()
