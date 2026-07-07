"""
T-073: P0修复验证 — DA_ema 时间积分 + 权重保留率

目标：
  1. fill 饱和后 w_ccw 保留率 > 80%（P0修复核心判据）
  2. DA_ema 在饱和后渐进衰减（非瞬时归零，有 τ=5000步缓冲）
  3. fill_min > 0.20（无饿死风险）
  4. [附测] Motor 激活幅度（T-074 muscle.gain 标定前置数据）

对比基线：
  T-067 (P0前): fill饱和后~740步内 w 被 decay=0.025 冲洗至零
  P0后预期:     w_retained ≈ 84% over 175k steps (λ=1e-6, 公式推导)
  本实验50k步:  fill饱和约在25-35k步，实测15-25k步的保留率

Commit: 4d3526a (P0 DA_ema + lambda_metabolic)
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import World, HeatSource, Body

STEPS        = 50_000
DT           = 1.0
REPORT_EVERY = 5_000

# ─── 信号采集辅助函数 ─────────────────────────────────────────

def get_fill(c):
    return c.energy_store._cap.charge / c.energy_store.config.capacity

def get_da(c):
    try:
        da_n = getattr(c, 'dopamine_neuron', None) or getattr(c, 'da_neuron', None)
        return da_n.activation if da_n else c.dopamine.concentration
    except Exception:
        return 0.0

def get_weights(c):
    b_ccw = getattr(c, 'bundle_d1_phasic_left_to_spinal_ccw', None)
    b_cw  = getattr(c, 'bundle_d1_phasic_right_to_spinal_cw',  None)
    w_ccw = b_ccw._memristors[0][0].w if (b_ccw and b_ccw._memristors) else float('nan')
    w_cw  = b_cw._memristors[0][0].w  if (b_cw  and b_cw._memristors)  else float('nan')
    return w_ccw, w_cw

def get_da_ema(c):
    """P0新增：读取 bundle 上的 DA_ema 状态变量。"""
    b = getattr(c, 'bundle_d1_phasic_left_to_spinal_ccw', None)
    if b and hasattr(b, '_da_ema'):
        return b._da_ema
    return float('nan')

def get_motor_peak(c):
    """T-074前置：采集各Motor轴激活峰值（用于 muscle.gain 标定）。"""
    motors = getattr(c, 'motor_neurons', {})
    if not motors:
        return {}
    return {k: v.activation for k, v in motors.items()}

def dist(body, src):
    return math.sqrt(sum((body.position[i] - src.position[i])**2 for i in range(3)))


# ─── 主程序 ──────────────────────────────────────────────────

def run():
    print("=" * 72)
    print("  T-073: P0修复验证 (DA_ema + lambda_metabolic)")
    print("  判定: J1 w_retained>80% | J2 DA_ema渐衰 | J3 fill_min>0.20")
    print("=" * 72)

    src  = HeatSource(position=[70.0, 50.0, 25.0], temperature=5.0,
                      radius=30, energy=1000.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=[10.0, 50.0, 25.0])
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE  = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world
    c.somatosensory.LATERAL_GAIN = 0.3
    for mn in c.motor_neurons.values():
        mn.config.output_gain = 0.1
    c.energy_store._cap.charge = c.energy_store.config.capacity * 0.3

    # ── 追踪变量 ──
    fill_min   = 1.0
    sat_step   = None      # 第一次 fill ≥ 0.97 的步数
    w_at_sat   = (float('nan'), float('nan'))
    da_ema_at_sat_plus_5k = float('nan')  # 饱和后5k步的DA_ema
    motor_peak = {}        # 全程Motor峰值

    print(f"\n  {'Step':>7} | {'fill':>5} | {'DA':>5} | {'DA_ema':>6} | "
          f"{'w_ccw':>6} {'w_cw':>6} | {'dist':>6} | Motor_x")
    print("  " + "-" * 72)

    for step in range(1, STEPS + 1):
        c.step({}, DT)

        fill   = get_fill(c)
        da     = get_da(c)
        da_ema = get_da_ema(c)
        w_ccw, w_cw = get_weights(c)
        d      = dist(body, src)
        m      = get_motor_peak(c)
        fill_min = min(fill_min, fill)

        # 记录 Motor 峰值
        for k, v in m.items():
            motor_peak[k] = max(motor_peak.get(k, 0.0), abs(v))

        # 填充饱和检测
        if sat_step is None and fill >= 0.97:
            sat_step = step
            w_at_sat = (w_ccw, w_cw)
            print(f"\n  *** fill 饱和 @ step {step}: w_ccw={w_ccw:.4f}, "
                  f"DA_ema={da_ema:.4f} ***\n")

        if sat_step is not None and step == sat_step + 5000:
            da_ema_at_sat_plus_5k = da_ema

        if step % REPORT_EVERY == 0:
            mx = m.get('move_x', 0.0)
            print(f"  {step:>7} | {fill:>5.3f} | {da:>5.3f} | {da_ema:>6.4f} | "
                  f"{w_ccw:>6.4f} {w_cw:>6.4f} | {d:>6.1f} | {mx:>7.4f}")

    # ─── 判定 ────────────────────────────────────────────────
    w_ccw_final, w_cw_final = get_weights(c)
    w_ccw_sat = w_at_sat[0]
    retention = (w_ccw_final / w_ccw_sat) if (not math.isnan(w_ccw_sat)
                                               and w_ccw_sat > 1e-6) else float('nan')

    j1 = (not math.isnan(retention)) and retention >= 0.80
    j2 = (not math.isnan(da_ema_at_sat_plus_5k)) and da_ema_at_sat_plus_5k >= 0.05
    j3 = fill_min > 0.20

    # 对比 T-067 P0前的等效衰减速率（理论：0.025 × w × 0.18 / 步）
    if sat_step and not math.isnan(w_ccw_sat) and w_ccw_sat > 1e-6:
        steps_after_sat = STEPS - sat_step
        # 理论P0前衰减：每步 Δw ≈ 0.025 × w × w × 0.18 (multiplicative softbound)
        # 简化线性估计
        pre_p0_estimate = w_ccw_sat * (1.0 - 0.025 * 0.18) ** steps_after_sat
    else:
        pre_p0_estimate = float('nan')

    print()
    print("=" * 72)
    print("  T-073 判定结果：")
    print()
    if sat_step:
        print(f"    fill 饱和步数:          step {sat_step}")
        print(f"    饱和时 w_ccw:           {w_ccw_sat:.4f}")
        print(f"    最终  w_ccw (step {STEPS}): {w_ccw_final:.4f}")
        print(f"    保留率:                  {retention*100:.1f}%")
        print(f"    [对比] P0前理论残留:     {pre_p0_estimate:.4f} (decay_rate=0.025)")
        print()
        print(f"    DA_ema @ 饱和+5k步:     {da_ema_at_sat_plus_5k:.4f}")
    else:
        print("    WARNING: fill 未达到饱和（body 未找到热源？）")
    print()
    print(f"    J1  w_ccw 保留率 ≥ 80%   {retention*100:.1f}%  → {'PASS ✅' if j1 else 'FAIL ❌'}")
    print(f"    J2  DA_ema @sat+5k ≥ 0.05 {da_ema_at_sat_plus_5k:.4f}  → {'PASS ✅' if j2 else 'FAIL ❌'}")
    print(f"    J3  fill_min > 0.20       {fill_min:.4f}  → {'PASS ✅' if j3 else 'FAIL ❌'}")
    print()

    # ─── T-074 前置：Motor 激活峰值 ──────────────────────────
    print("  [T-074前置] Motor 激活峰值（muscle.gain 标定参考）：")
    for axis, peak in sorted(motor_peak.items()):
        print(f"    motor_{axis:<10} peak = {peak:.4f}")
    print()

    passed = sum([j1, j2, j3])
    print(f"  总计: {passed}/3 PASS")
    print("=" * 72)


if __name__ == '__main__':
    run()
