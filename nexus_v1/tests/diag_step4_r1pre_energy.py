"""
Step 4 R1-Pre：能量链独立验证（禁用 consume_nearby 模拟移除效果）

目标：确认移除 consume_nearby 后，仅靠 YolkSac + ThermalMouth/DigestiveInterface，
      fill_fraction 在 50k 步内全程 > 0.1（安全余量 2× death threshold=0.05）

方法：monkey-patch world.consume_nearby 返回 0.0，模拟移除效果。

通过标准：
  - fill_fraction 全程 > 0.1
  - deposit_rate (v_feed) 有效占空比 > 0（ThermalMouth 确实在工作）
  - 若失败：报告 fill_fraction 跌破阈值的步数和当时 v_feed 值

运行：
  PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.diag_step4_r1pre_energy
"""
import sys, os, statistics
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit

N_STEPS       = 50_000
REPORT_EVERY  = 5_000
FF_PASS_MIN   = 0.1    # 通过阈值（2× death threshold）
FF_WARN_LEVEL = 0.15   # 预警线

def run():
    print("=== Step 4 R1-Pre：能量链独立验证（consume_nearby 禁用）===\n")
    c = VariantCircuit()

    # ── Monkey-patch: 禁用 consume_nearby，模拟移除后效果 ──
    _orig_consume_nearby = c.world.consume_nearby
    c.world.consume_nearby = lambda pos, rate, dt: 0.0
    print("  [PATCH] world.consume_nearby → 0.0（模拟移除）")
    print(f"  YolkSac 初始存量: {c.yolk_sac._level:.1f}，lambda={c.yolk_sac.config.lambda_yolk}/step")
    print(f"  预期 YolkSac 耗尽: {int(c.yolk_sac.config.initial_level / c.yolk_sac.config.lambda_yolk):,} 步")
    print()

    fill_history   = []
    vfeed_history  = []
    yolk_history   = []
    fail_step      = None
    warn_step      = None

    print(f"{'Step':>7}  {'fill_frac':>9}  {'v_feed':>8}  {'yolk_lvl':>10}  {'status':>8}")
    print("-" * 60)

    for step in range(N_STEPS):
        c.step({}, dt=1.0)

        ff   = c.energy_store.fill_fraction
        vf   = c._v_feed
        yk   = c.yolk_sac._level

        fill_history.append(ff)
        vfeed_history.append(vf)
        yolk_history.append(yk)

        if fail_step is None and ff < FF_PASS_MIN:
            fail_step = step
        if warn_step is None and ff < FF_WARN_LEVEL:
            warn_step = step

        if (step + 1) % REPORT_EVERY == 0:
            status = "OK" if ff >= FF_PASS_MIN else "!! FAIL"
            if FF_PASS_MIN <= ff < FF_WARN_LEVEL:
                status = "WARN"
            print(f"{step+1:>7}  {ff:>9.4f}  {vf:>8.5f}  {yk:>10.2f}  {status:>8}")

    # ── 分析 ──
    ff_min   = min(fill_history)
    ff_final = fill_history[-1]
    ff_mean  = statistics.mean(fill_history)

    vf_nonzero = [v for v in vfeed_history if v > 1e-4]
    vf_duty    = len(vf_nonzero) / N_STEPS
    vf_max     = max(vfeed_history)
    vf_mean_active = statistics.mean(vf_nonzero) if vf_nonzero else 0.0

    yolk_final = yolk_history[-1]
    yolk_spent = c.yolk_sac.config.initial_level - yolk_final

    print("\n" + "=" * 60)
    print("== 结果分析 ==\n")

    print(f"EnergyStore fill_fraction:")
    print(f"  最小值: {ff_min:.4f}  均值: {ff_mean:.4f}  最终: {ff_final:.4f}")
    if warn_step:
        print(f"  ⚠ 首次跌破预警线 {FF_WARN_LEVEL}: step {warn_step}")
    if fail_step:
        print(f"  !! 首次跌破阈值 {FF_PASS_MIN}: step {fail_step}")
    else:
        print(f"  全程 > {FF_PASS_MIN}: ✓")

    print()
    print(f"YolkSac:")
    print(f"  已消耗: {yolk_spent:.1f} / {c.yolk_sac.config.initial_level:.1f}  ({yolk_spent/c.yolk_sac.config.initial_level*100:.1f}%)")
    print(f"  剩余:   {yolk_final:.1f}")

    print()
    print(f"ThermalMouth / DigestiveInterface (v_feed 代理):")
    print(f"  有效占空比: {vf_duty:.3f}  最大值: {vf_max:.5f}  激活期均值: {vf_mean_active:.5f}")
    if vf_duty < 0.1:
        print(f"  ⚠ ThermalMouth 进食信号几乎为零（占空比 < 10%）")

    print()
    ok_ff  = ff_min >= FF_PASS_MIN
    ok_vf  = vf_duty > 0.0
    print(f"{'✓' if ok_ff else '✗'} fill_fraction 全程 > {FF_PASS_MIN}: {'PASS' if ok_ff else 'FAIL'}")
    print(f"{'✓' if ok_vf else '✗'} ThermalMouth 有效进食: {'PASS (占空比=' + f'{vf_duty:.3f})' if ok_vf else 'FAIL'}")

    if not ok_ff:
        print(f"\n=> 移除 consume_nearby 不安全。")
        print(f"   需先提升 ThermalMouth eta 或 DigestiveInterface g_digest 使进食率充足。")
        # 估算所需 v_feed: 需维持 fill_fraction ≥ 0.1
        # fill_fraction = Q/capacity；需要 deposit_rate 足以补偿 drain
        print(f"\n   参考：当前 YolkSac 贡献 {c.yolk_sac.config.lambda_yolk}/step")
        print(f"   ThermalMouth 贡献：v_feed 均值 × capacity 换算需进一步推算。")
    else:
        print(f"\n=> 移除 consume_nearby 安全，可执行 Step 4 代码修改。")

if __name__ == '__main__':
    run()
