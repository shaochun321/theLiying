"""
T-039b: 诈胡核查重跑 — P0 修复后全冻结 STDP 验证

目的：区分 P0/P1 改善来自"STDP 真实学习"还是"增益效应"。
全冻结 STDP 后，若 DR5% 退回随机基线（≤55%），说明改善来自真实学习。

对比：
  T-054 (旧基线):   STDP冻结 DR5%=51.0% → PASS（T-043 不创造硬连线）
  T-039b (P0后):   预期同样 DR5%≤55%（P0=EMA门控，不应改变方向涌现机制）

验收：
  J1: DR5% ≤ 55%    → PASS：方向性依赖 STDP，P0 不硬写方向
  J2: w_ccw 无变化  → PASS：冻结有效，权重不涨不跌
  J3: fill_min > 0.10 → PASS：P0 的 BMR 保护不会导致饿死

Commit base: e9607f6 (DEG-006/FIX-006)
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS        = 50_000
DT           = 1.0
LOG_INTERVAL = 5_000
SRC_POS      = [70.0, 50.0, 25.0]
BODY_START   = [10.0, 50.0, 25.0]

DR5_THRESH   = 55.0   # DR5 ≤ 55% → PASS（随机基线）


def freeze_all_stdp(circuit):
    """冻结全部可学习 bundle（含 eligibility-trace 类型）。"""
    count = 0
    ids = []
    for b in circuit.get_all_bundles():
        cfg = b.config
        if cfg.learning_rule not in ("frozen",):
            cfg.stdp_lr = 0.0
            if hasattr(cfg, 'eligibility_gain'):
                cfg.eligibility_gain = 0.0
            if hasattr(cfg, 'eligibility_ltd_rate'):
                cfg.eligibility_ltd_rate = 0.0
            count += 1
            ids.append(b.id)
    return count, ids


def get_dr5(c, src_pos):
    """patch 温差 · body 速度符号 > 0。FIX-006: 不用 activation，不需要 Motor 神经元。"""
    pT = c._patch_temps if hasattr(c, '_patch_temps') else {}
    T  = {pid: pT.get(pid, (0.0,))[0] for pid in ['front', 'back', 'left', 'right']}
    vx = c.world.body.velocity[0]
    vy = c.world.body.velocity[1]
    gx = T.get('right', 0.0) - T.get('left', 0.0)
    gy = T.get('front', 0.0) - T.get('back', 0.0)
    return (gx * vx + gy * vy) > 0.0


def get_d1_weights(c):
    """读 D1 spinal 束权重。FIX-006: 用 'phasic' in bundle_id 而非等值匹配。"""
    w_ccw = w_cw = float('nan')
    bl = getattr(c, 'bundle_d1_phasic_left_to_spinal_ccw', None)
    br = getattr(c, 'bundle_d1_phasic_right_to_spinal_cw', None)
    if bl and bl._memristors:
        w_ccw = bl._memristors[0][0].w
    if br and br._memristors:
        w_cw  = br._memristors[0][0].w
    return w_ccw, w_cw


def get_motor_ema(c):
    """FIX-006: 读 _activation_ema（firing rate），不读 activation（瞬时 0/1）。"""
    result = {}
    for key, mn in c.motor_neurons.items():
        result[key] = mn._activation_ema
    return result


def main():
    print("=" * 72)
    print("  T-039b: 诈胡核查重跑 (P0后) — 全冻结 STDP，50k 步")
    print(f"  判定: J1 DR5%≤{DR5_THRESH:.0f}% | J2 w_ccw冻结 | J3 fill_min>0.10")
    print("=" * 72)

    src  = HeatSource(position=SRC_POS[:], energy=50_000.0,
                      temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=list(BODY_START))
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE  = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world
    c.somatosensory.LATERAL_GAIN = 0.3
    for mn in c.motor_neurons.values():
        mn.config.output_gain = 0.1
    c.energy_store._cap.charge = c.energy_store.config.capacity * 0.3

    # ── 冻结全部 STDP ──
    n_frozen, _ = freeze_all_stdp(c)
    print(f"\n  已冻结 {n_frozen}/{len(c.get_all_bundles())} 条 STDP bundle")

    # ── 初始权重快照 ──
    w_ccw_init, w_cw_init = get_d1_weights(c)
    print(f"  初始 D1 权重: w_ccw={w_ccw_init:.4f}, w_cw={w_cw_init:.4f}\n")

    hdr = (f"  {'Step':>7} | {'DR5%':>6} | {'dist':>6} | "
           f"{'w_ccw':>7} {'w_cw':>7} {'Dw':>7} | "
           f"{'fill':>5} | {'Motor_ema_x':>11}")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    dr5_count = 0
    fill_min  = 1.0

    for step in range(1, STEPS + 1):
        c.step({}, DT)

        fill = c.energy_store.fill_fraction
        fill_min = min(fill_min, fill)

        if get_dr5(c, SRC_POS):
            dr5_count += 1

        if step % LOG_INTERVAL == 0:
            dr5_pct  = dr5_count / step * 100
            pos      = c.world.body.position
            dist     = math.sqrt(sum((pos[i] - SRC_POS[i]) ** 2 for i in range(3)))
            w_ccw, w_cw = get_d1_weights(c)
            dw       = (w_ccw - w_cw) if not math.isnan(w_ccw) else float('nan')
            # FIX-006: motor EMA
            m_ema    = get_motor_ema(c).get('move_x', float('nan'))
            print(f"  {step:>7} | {dr5_pct:>5.1f}% | {dist:>6.1f} | "
                  f"{w_ccw:>7.4f} {w_cw:>7.4f} {dw:>+7.4f} | "
                  f"{fill:>5.3f} | {m_ema:>11.4f}")

    # ── 最终判定 ──
    dr5_final       = dr5_count / STEPS * 100
    w_ccw_f, w_cw_f = get_d1_weights(c)
    dw_init  = abs(w_ccw_init - w_cw_init) if not math.isnan(w_ccw_init) else float('nan')
    dw_final = abs(w_ccw_f    - w_cw_f   ) if not math.isnan(w_ccw_f)    else float('nan')
    w_drift  = abs(w_ccw_f - w_ccw_init)   if not math.isnan(w_ccw_init) else float('nan')

    j1 = dr5_final <= DR5_THRESH
    j2 = (not math.isnan(w_drift)) and w_drift < 0.01  # 权重几乎不变
    j3 = fill_min > 0.10

    print()
    print("=" * 72)
    print("  T-039b 判定结果：\n")
    print(f"    DR5% (全程):         {dr5_final:.1f}%   (阈值 ≤{DR5_THRESH:.0f}%)")
    print(f"    w_ccw: {w_ccw_init:.4f} → {w_ccw_f:.4f}  漂移={w_drift:.4f}")
    print(f"    w_cw:  {w_cw_init:.4f} → {w_cw_f:.4f}")
    print(f"    fill_min:            {fill_min:.4f}")
    print()
    print(f"    J1  DR5% ≤ 55%          {dr5_final:.1f}%  → {'PASS ✅' if j1 else 'FAIL ❌'}")
    print(f"    J2  w_ccw 漂移 < 0.01   {w_drift:.4f} → {'PASS ✅' if j2 else 'FAIL ❌'}")
    print(f"    J3  fill_min > 0.10     {fill_min:.4f} → {'PASS ✅' if j3 else 'FAIL ❌'}")
    print()
    passed = sum([j1, j2, j3])
    print(f"  总计: {passed}/3 PASS")
    if j1:
        print("  → P0 不创造硬连线方向性，改善来自真实 STDP 学习（与 T-054 结论一致）")
    else:
        print("  → DR5%>55%：对流漂移或结构硬编码在 STDP 冻结下仍提供方向性 — 需调查")
    print("=" * 72)


if __name__ == '__main__':
    main()
