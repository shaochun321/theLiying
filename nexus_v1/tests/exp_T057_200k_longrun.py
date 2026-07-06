"""
exp_T057_200k_longrun.py — 200k 步长程验证（T-058 修复版）

变更（T-058 vs 原版）：
  P0-A: |Δw| 探针改用 bundle_d1_phasic_left_to_spinal_ccw/cw（原为不存在的 relay_to_slow_*）
  P0-A: T4.1 计算改用 c.bundles_col_to_motor 遍历（原为 c.vestibular.column 路径错误）
  P0-C: 新增 Foraging DR5 和 SDI（fill<0.85 窗口门控），作为诊断辅助，不替换全局 DR5

验收标准（主判据为全局指标）：
  L1: DR5% > 60%（全程累计）
  L2: |Δw| > 0.2（某 10k 窗口内）
  L3: T4.1 ≥ 3.0×（全程）
  L4: fill 不归零
  L5: 死锁率 < 10%

诊断辅助：
  Foraging DR5 > 60%（fill<0.85 且 DA>0.1 的步骤中）
  SDI > 30%（fill>0.8 的步数占比）
"""

import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS         = 200_000
DT            = 1.0
LOG_INTERVAL  = 10_000
SRC_POS       = [70.0, 50.0, 25.0]
BODY_START    = [10.0, 50.0, 25.0]

THRESH_DR5   = 60.0
THRESH_DW    = 0.2
THRESH_T41   = 3.0
THRESH_FILL  = 0.001
THRESH_LOCK  = 0.10


def get_dr5(c):
    """patch 温差 · body 速度符号 > 0（全局 DR5）。"""
    pT = c._patch_temps if hasattr(c, '_patch_temps') else {}
    T  = {pid: pT.get(pid, (0.0,))[0] for pid in ['front', 'back', 'left', 'right']}
    vx = c.world.body.velocity[0] if hasattr(c.world.body, 'velocity') else 0.0
    vy = c.world.body.velocity[1] if hasattr(c.world.body, 'velocity') else 0.0
    gx = T.get('right', 0.0) - T.get('left',  0.0)
    gy = T.get('front', 0.0) - T.get('back',  0.0)
    return (gx * vx + gy * vy) > 0.0


def get_yaw_weights(c):
    """P0-A fix: 使用真实 bundle 名字（bundle_d1_phasic_left/right_to_spinal_ccw/cw）。"""
    b_ccw = getattr(c, 'bundle_d1_phasic_left_to_spinal_ccw',  None)
    b_cw  = getattr(c, 'bundle_d1_phasic_right_to_spinal_cw', None)
    w_ccw = b_ccw._memristors[0][0].w if (b_ccw and b_ccw._memristors) else float('nan')
    w_cw  = b_cw._memristors[0][0].w  if (b_cw  and b_cw._memristors)  else float('nan')
    return w_ccw, w_cw


def get_t41_ratio(c):
    """P0-A fix: 遍历 c.bundles_col_to_motor（原为 c.vestibular.column 路径错误）。"""
    axis_ws, cross_ws = [], []
    for b in c.bundles_col_to_motor:
        ws = [m.w for row in b._memristors for m in row]
        if not ws:
            continue
        avg_w = sum(ws) / len(ws)
        if 'cross' not in b.id:
            axis_ws.append(avg_w)
        else:
            cross_ws.append(avg_w)
    avg_ax = sum(axis_ws) / max(len(axis_ws), 1)
    avg_cr = sum(cross_ws) / max(len(cross_ws), 1)
    return avg_ax, avg_cr, avg_ax / max(avg_cr, 1e-6)


def main():
    print("=" * 80)
    print("  T-057 (T-058 fix): 200k 步长程验证")
    print("  P0-A: bundle 探针修复  P0-B: gain_max 1.5→1.15  P0-C: 状态门控指标")
    print("=" * 80)
    print(f"  Steps={STEPS//1000}k  DT={DT}")
    print(f"  热源={SRC_POS}  body_start={BODY_START}")
    print()

    src  = HeatSource(position=SRC_POS, energy=50_000.0, temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=list(BODY_START))
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world
    c.somatosensory.LATERAL_GAIN = 0.3
    for m in c.muscle_system.muscles:
        m.gain = 0.3

    # 确认探针可访问
    b_ccw = getattr(c, 'bundle_d1_phasic_left_to_spinal_ccw', None)
    b_cw  = getattr(c, 'bundle_d1_phasic_right_to_spinal_cw', None)
    print(f"  探针验证: bundle_d1_phasic_left_to_spinal_ccw = {'✅' if b_ccw else '❌ 未找到'}")
    print(f"  探针验证: bundle_d1_phasic_right_to_spinal_cw = {'✅' if b_cw else '❌ 未找到'}")
    t41_check = len(list(c.bundles_col_to_motor))
    print(f"  探针验证: bundles_col_to_motor count = {t41_check}")
    print()

    hdr = (f"{'Step':>8} | {'DR5%':>6} | {'w_ccw':>7} {'w_cw':>7} {'|Dw|':>6} | "
           f"{'T4.1':>6} | {'fill':>6} | {'lock%':>6} | {'fDR5':>6} | {'dist':>6}")
    print(hdr)
    print("-" * len(hdr))

    dr5_count   = 0
    fdr5_count  = 0   # foraging DR5（fill<0.85, DA>0.1）
    fdr5_steps  = 0   # 符合 foraging 条件的步数
    sdi_count   = 0   # fill>0.8 步数（SDI）
    lock_count  = 0
    dw_max      = 0.0
    t41_min     = float('inf')
    fill_min    = 1.0

    LOCK_VEL_THRESH = 1e-5
    LOCK_WINDOW = 500
    vel_history = []

    for step in range(STEPS):
        c.step({}, DT)

        is_dr5 = get_dr5(c)
        if is_dr5:
            dr5_count += 1

        fill = c.energy_store.fill_fraction
        da   = c.dopamine.concentration if hasattr(c.dopamine, 'concentration') else 0.0
        fill_min = min(fill_min, fill)

        # Foraging DR5（P0-C 状态门控）
        if fill < 0.85 and da > 0.1:
            fdr5_steps += 1
            if is_dr5:
                fdr5_count += 1

        # SDI
        if fill > 0.8:
            sdi_count += 1

        # 死锁检测
        vel = c.world.body.velocity if hasattr(c.world.body, 'velocity') else [0.0]*3
        spd = math.sqrt(sum(v**2 for v in vel))
        vel_history.append(spd < LOCK_VEL_THRESH)
        if len(vel_history) > LOCK_WINDOW:
            vel_history.pop(0)
        if len(vel_history) == LOCK_WINDOW and all(vel_history):
            lock_count += 1

        if step % LOG_INTERVAL == LOG_INTERVAL - 1:
            dr5_pct  = dr5_count / (step + 1) * 100
            fdr5_pct = (fdr5_count / fdr5_steps * 100) if fdr5_steps > 0 else float('nan')
            lock_pct = lock_count / max(step + 1 - LOCK_WINDOW, 1) * 100

            w_ccw, w_cw = get_yaw_weights(c)
            dw = abs(w_ccw - w_cw) if not (math.isnan(w_ccw) or math.isnan(w_cw)) else float('nan')
            if not math.isnan(dw):
                dw_max = max(dw_max, dw)

            _, _, t41 = get_t41_ratio(c)
            if not math.isnan(t41) and t41 < float('inf'):
                t41_min = min(t41_min, t41)

            pos  = c.world.body.position
            dist = math.sqrt(sum((pos[i]-SRC_POS[i])**2 for i in range(3)))

            fdr5_str = f"{fdr5_pct:5.1f}%" if not math.isnan(fdr5_pct) else "  N/A"
            print(f"{step+1:>8} | {dr5_pct:>5.1f}% | {w_ccw:>7.4f} {w_cw:>7.4f} {dw:>6.4f} | "
                  f"{t41:>6.2f}x | {fill:>6.3f} | {lock_pct:>5.1f}% | {fdr5_str} | {dist:>6.1f}")

    # ── 最终判定 ──
    dr5_final   = dr5_count / STEPS * 100
    fdr5_final  = (fdr5_count / fdr5_steps * 100) if fdr5_steps > 0 else float('nan')
    sdi_final   = sdi_count / STEPS * 100
    lock_final  = lock_count / max(STEPS - LOCK_WINDOW, 1) * 100

    l1 = dr5_final  > THRESH_DR5
    l2 = dw_max     > THRESH_DW
    l3 = t41_min    >= THRESH_T41 if t41_min < float('inf') else False
    l4 = fill_min   > THRESH_FILL
    l5 = lock_final < THRESH_LOCK * 100

    t41_str = f"{t41_min:.2f}x" if t41_min < float('inf') else "N/A"

    print()
    print("=" * 80)
    print("  主判据（全局指标）：")
    print(f"    DR5%:       {dr5_final:.1f}%  (>{THRESH_DR5}%)  →  {'PASS ✅' if l1 else 'FAIL ❌'} L1")
    print(f"    |Δw| 峰值:  {dw_max:.4f}  (>{THRESH_DW})   →  {'PASS ✅' if l2 else 'FAIL ❌'} L2")
    print(f"    T4.1 最低:  {t41_str}  (≥{THRESH_T41}x)    →  {'PASS ✅' if l3 else 'FAIL ❌'} L3")
    print(f"    fill 最低:  {fill_min:.4f}  (>{THRESH_FILL})  →  {'PASS ✅' if l4 else 'FAIL ❌'} L4")
    print(f"    死锁率:     {lock_final:.1f}%  (<{THRESH_LOCK*100:.0f}%)   →  {'PASS ✅' if l5 else 'FAIL ❌'} L5")
    print()
    fdr5_str2 = f"{fdr5_final:.1f}%" if not math.isnan(fdr5_final) else "N/A"
    print(f"  诊断辅助（P0-C 状态门控）：")
    print(f"    Foraging DR5: {fdr5_str2}  (fill<0.85, DA>0.1 的 {fdr5_steps} 步)")
    print(f"    SDI:          {sdi_final:.1f}%  (fill>0.8 的步数占比)")
    print()
    all_pass = l1 and l2 and l3 and l4 and l5
    if all_pass:
        print("  [PASS] 200k 长程验证通过：热趋性行为稳定涌现")
    else:
        print("  [FAIL] 部分指标未达标，请查阅上方详细结果")
    print("=" * 80)


if __name__ == '__main__':
    main()
