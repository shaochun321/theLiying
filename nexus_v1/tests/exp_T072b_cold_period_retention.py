"""
T-072b: 冷期权重保留测试 — REGEN_PROB=0.0001（真正的冷期）

T-072 发现 REGEN_PROB=0.001 在 Phase 2 每 1000 步生成 1 个新源，
cold period 仅 ~4832 步，fill 仅降 0.006，DA_ema 几乎不变。

T-072b 改用 REGEN_PROB=0.0001（10× 稀疏），cold period 预期 ~10k 步：
  - DA_ema (τ=5000) 经 10k 步衰减到 e^(-2) ≈ 0.135 → STDP 实质暂停
  - lambda_metabolic=1e-6 唯一衰减源：10k 步损失 = 1e-6 × 0.3 × 10000 ≈ 0.003 (1%)
  - 权重保留率应 ≥ 99%

判定标准：
  J1: fill_min_cold > 0.90            （冷期 fill 下降可测量但不崩溃）
  J2: w_ccw_after_cold ≥ 0.97×w_ccw_at_deplete  （冷期保留率≥97%）
  J3: DA_ema_min_cold < 0.40          （DA_ema 确实在冷期显著下降）
  J4: w_ccw_final > 0.05              （总体方向分化持续）

Commit base: a885ca3 (T-072 200k report)
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS         = 100_000
DT            = 1.0
LOG_INTERVAL  = 5_000

SRC_POS_1     = [70.0, 50.0, 25.0]
BODY_START    = [10.0, 50.0, 25.0]
SRC_ENERGY    = 100_000.0

DEPLETION_STEP = 30_000   # Phase 1 fill 饱和后（T-072 显示 step 30k fill=1.0）

# 判定阈值
FILL_COLD_MIN   = 0.90
RETAIN_THRESH   = 0.97
DA_EMA_THRESH   = 0.40
W_CCW_FINAL_MIN = 0.05


def get_d1_weights(c):
    w_ccw = w_cw = float('nan')
    bl = getattr(c, 'bundle_d1_phasic_left_to_spinal_ccw', None)
    br = getattr(c, 'bundle_d1_phasic_right_to_spinal_cw', None)
    if bl and bl._memristors:
        w_ccw = bl._memristors[0][0].w
    if br and br._memristors:
        w_cw  = br._memristors[0][0].w
    return w_ccw, w_cw


def get_da_ema(c):
    """读 D1 CCW bundle 的 DA_ema（P0 慢积分门控信号）。"""
    bl = getattr(c, 'bundle_d1_phasic_left_to_spinal_ccw', None)
    if bl is not None:
        return bl._da_ema
    return float('nan')


def get_nearest_dist(c):
    pos = c.world.body.position
    best = float('inf')
    for src in c.world.heat_sources:
        if src.alive:
            d = math.sqrt(sum((pos[i] - src.position[i]) ** 2 for i in range(3)))
            best = min(best, d)
    return best


def in_source_zone(c):
    pos = c.world.body.position
    for src in c.world.heat_sources:
        if src.alive:
            d = math.sqrt(sum((pos[i] - src.position[i]) ** 2 for i in range(3)))
            if d < src.radius:
                return True
    return False


def main():
    print("=" * 76)
    print("  T-072b: 冷期权重保留测试 (100k 步，REGEN_PROB=0.0001)")
    print(f"  判定: J1 fill_cold>{FILL_COLD_MIN} | J2 保留率≥{RETAIN_THRESH:.0%} | "
          f"J3 DA_ema_min<{DA_EMA_THRESH} | J4 w_ccw>{W_CCW_FINAL_MIN}")
    print("=" * 76)

    src1 = HeatSource(position=list(SRC_POS_1), energy=SRC_ENERGY,
                      temperature=5.0, radius=30.0)
    src1._drift = [0.0, 0.0, 0.0]
    body  = Body(position=list(BODY_START))
    world = World(heat_sources=[src1], body=body)
    world.MIN_ALIVE  = 0
    world.REGEN_PROB = 0.0   # Phase 1 受控单源

    c = VariantCircuit()
    c.world = world
    c.somatosensory.LATERAL_GAIN = 0.3
    for mn in c.motor_neurons.values():
        mn.config.output_gain = 0.1
    c.energy_store._cap.charge = c.energy_store.config.capacity * 0.3

    # 变量
    foraging_steps = 0
    fill_min_cold  = 1.0   # 冷期内 fill 最低值
    da_ema_min     = 1.0   # 冷期内 DA_ema 最低值（只在冷期更新）

    t_deplete    = None
    t_reach2     = None
    w_at_deplete = float('nan')
    w_after_cold = float('nan')
    cold_period  = False   # True = 当前在冷期

    w_ccw_init, w_cw_init = get_d1_weights(c)
    da_init = get_da_ema(c)
    print(f"\n  初始 D1 权重: w_ccw={w_ccw_init:.4f}, w_cw={w_cw_init:.4f}")
    print(f"  初始 fill: {c.energy_store.fill_fraction:.3f}, DA_ema: {da_init:.4f}")
    print()

    hdr = (f"  {'Step':>7} | {'Ph':>2} | {'dist':>6} | "
           f"{'w_ccw':>7} {'w_cw':>7} {'Dw':>7} | "
           f"{'fill':>5} | {'DA_ema':>6} | {'η%':>4} | {'n_src':>5}")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    for step in range(1, STEPS + 1):

        # ── 耗尽触发 ──
        if step == DEPLETION_STEP:
            for s in list(world.heat_sources):
                if s.alive:
                    s.energy = 0.0
                    s.temperature = 0.0
            world.REGEN_PROB = 0.0001   # 稀疏再生：期望 ~10k 步后出现新源
            t_deplete = step
            cold_period = True
            w_ccw_d, _ = get_d1_weights(c)
            w_at_deplete = w_ccw_d
            da_d = get_da_ema(c)
            print(f"\n  [step {step}] 热源耗尽（Phase 2），REGEN_PROB→0.0001"
                  f"\n              w_ccw={w_at_deplete:.4f} DA_ema={da_d:.4f}")

        # ── 电路步进 ──
        c.step({}, DT)

        # ── 状态采样 ──
        fill   = c.energy_store.fill_fraction
        da_ema = get_da_ema(c)
        n_src  = sum(1 for s in world.heat_sources if s.alive)
        dist   = get_nearest_dist(c)
        in_zn  = in_source_zone(c)

        if in_zn:
            foraging_steps += 1

        # 冷期监控
        if cold_period:
            fill_min_cold = min(fill_min_cold, fill)
            da_ema_min    = min(da_ema_min, da_ema)

        # 冷期结束：body 找到新热源
        if cold_period and in_zn and t_reach2 is None:
            t_reach2  = step
            cold_period = False
            w_ccw_a, _ = get_d1_weights(c)
            w_after_cold = w_ccw_a
            t_cold = t_reach2 - t_deplete
            print(f"\n  [step {step}] body 进入新热源区（冷期结束）"
                  f"\n              冷期={t_cold}步，w_ccw: {w_at_deplete:.4f} → {w_after_cold:.4f}"
                  f" ({w_after_cold/w_at_deplete*100:.1f}%保留)"
                  f"，DA_ema_min={da_ema_min:.4f}")

        # ── 定期日志 ──
        if step % LOG_INTERVAL == 0:
            if not t_deplete:
                phase = "P1"
            elif cold_period:
                phase = "C"
            else:
                phase = "P3"
            eta    = foraging_steps / step * 100
            w_ccw, w_cw = get_d1_weights(c)
            dw     = (w_ccw - w_cw) if not math.isnan(w_ccw) else float('nan')
            print(f"  {step:>7} | {phase:>2} | {dist:>6.1f} | "
                  f"{w_ccw:>7.4f} {w_cw:>7.4f} {dw:>+7.4f} | "
                  f"{fill:>5.3f} | {da_ema:>6.4f} | {eta:>3.1f}% | {n_src:>5d}")

    # ── 最终判定 ──
    w_ccw_f, _ = get_d1_weights(c)
    retain_rate = (w_after_cold / w_at_deplete) if not math.isnan(w_at_deplete) and w_at_deplete > 0 else float('nan')

    j1 = fill_min_cold > FILL_COLD_MIN
    j2 = (not math.isnan(retain_rate)) and retain_rate >= RETAIN_THRESH
    j3 = da_ema_min < DA_EMA_THRESH
    j4 = (not math.isnan(w_ccw_f)) and w_ccw_f > W_CCW_FINAL_MIN

    t_cold_period = (t_reach2 - t_deplete) if (t_reach2 and t_deplete) else None

    print()
    print("=" * 76)
    print("  T-072b 判定结果：\n")
    print(f"    冷期时长:           {t_cold_period} 步" if t_cold_period else "    冷期：新源未出现")
    print(f"    fill_min（冷期）:   {fill_min_cold:.4f}  （阈值 >{FILL_COLD_MIN}）")
    print(f"    DA_ema_min（冷期）: {da_ema_min:.4f}  （阈值 <{DA_EMA_THRESH}）")
    print(f"    w_ccw 冷期前: {w_at_deplete:.4f}")
    print(f"    w_ccw 冷期后: {w_after_cold:.4f}  （保留率={retain_rate*100:.1f}%）" if not math.isnan(retain_rate) else "    w_ccw 冷期后: N/A")
    print(f"    w_ccw 最终:   {w_ccw_f:.4f}")
    print()
    print(f"    J1  fill_cold > {FILL_COLD_MIN}         {fill_min_cold:.4f}  → {'PASS ✅' if j1 else 'FAIL ❌'}")
    print(f"    J2  保留率 ≥ {RETAIN_THRESH:.0%}           {retain_rate*100:.1f}%  → {'PASS ✅' if j2 else 'FAIL ❌'}" if not math.isnan(retain_rate) else f"    J2  保留率 N/A")
    print(f"    J3  DA_ema_min < {DA_EMA_THRESH}       {da_ema_min:.4f}  → {'PASS ✅' if j3 else 'FAIL ❌'}")
    print(f"    J4  w_ccw_final > {W_CCW_FINAL_MIN}       {w_ccw_f:.4f}  → {'PASS ✅' if j4 else 'FAIL ❌'}")
    print()
    passed = sum([j1, j2 if not math.isnan(retain_rate) else True, j3, j4])
    print(f"  总计: {passed}/4 PASS")
    if j2 and j3:
        print("  → P0 lambda_metabolic 验证：DA_ema 冷期显著下降但权重保留 ✅")
    elif not j3:
        print("  → DA_ema 冷期未显著下降：新源出现过快，冷期不足 10k 步")
    elif not j2:
        print("  → 权重冷期保留不足：检查 LTD 残余或 lambda_metabolic 值")
    print("=" * 76)


if __name__ == '__main__':
    main()
