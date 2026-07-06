"""
exp_T056_first_contact.py — 两阶段 Phase 2：首次接触热源

目标：引入热源（[70,50,25]），body 从热场边缘 [40,50,25] 启动，
      验证 IntakeSensor→DA 脉冲出现，yaw STDP 方向分化启动。

验收：
  F1: DA 脉冲峰值 > 0.5（首次接触时 IntakeSensor 触发）
  F2: |Δw| = |w_ccw - w_cw| > 0.01（yaw 方向分化启动）
  F3: 非接触期权重变化率 < 0.005/5k步（无同步饱和）
  F4: fill 有轻微回升（进食信号激活）
"""

import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS         = 20_000
DT            = 1.0
LOG_INTERVAL  = 2_000
SRC_POS       = [70.0, 50.0, 25.0]
BODY_START    = [40.0, 50.0, 25.0]   # 热场边缘（dist=30=radius）
SRC_TEMP      = 5.0
SRC_RADIUS    = 30.0
INITIAL_FILL  = 0.3

THRESH_DA_PEAK  = 0.5    # F1
THRESH_DW       = 0.01   # F2
THRESH_DW_RATE  = 0.005  # F3 每5k步权重变化率


def get_yaw_weights(c):
    """读取 bundle_relay_to_slow_left/right 平均权重。"""
    w_l = w_r = float('nan')
    bl = getattr(c, 'bundle_relay_to_slow_left',  None)
    br = getattr(c, 'bundle_relay_to_slow_right', None)
    if bl is not None:
        ws = [m.w for row in bl._memristors for m in row]
        if ws:
            w_l = sum(ws) / len(ws)
    if br is not None:
        ws = [m.w for row in br._memristors for m in row]
        if ws:
            w_r = sum(ws) / len(ws)
    return w_l, w_r


def main():
    print("=" * 70)
    print("  T-056: 两阶段 Phase 2 — 首次接触热源")
    print("=" * 70)
    print(f"  Steps={STEPS//1000}k  DT={DT}")
    print(f"  热源={SRC_POS}  body_start={BODY_START}  initial_fill={INITIAL_FILL}")
    print()

    src  = HeatSource(position=SRC_POS, energy=50_000.0, temperature=SRC_TEMP, radius=SRC_RADIUS)
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

    c.energy_store._cap.charge = c.energy_store.config.capacity * INITIAL_FILL
    initial_fill_actual = c.energy_store.fill_fraction

    w_l0, w_r0 = get_yaw_weights(c)
    print(f"  初始 fill={initial_fill_actual:.3f}  w_L0={w_l0:.4f}  w_R0={w_r0:.4f}")
    print()

    hdr = (f"{'Step':>7} | {'DA':>6} | {'fill':>6} | "
           f"{'w_L':>7} {'w_R':>7} {'|Dw|':>7} | {'dist':>6}")
    print(hdr)
    print("-" * len(hdr))

    da_peak = 0.0
    w_l_prev, w_r_prev = w_l0, w_r0
    dw_rate_max = 0.0
    RATE_WINDOW = 5_000

    for step in range(STEPS):
        c.step({}, DT)

        da = c.dopamine.concentration if hasattr(c.dopamine, 'concentration') else 0.0
        da_peak = max(da_peak, da)

        if (step + 1) % RATE_WINDOW == 0:
            w_l, w_r = get_yaw_weights(c)
            rate = abs(w_l - w_l_prev) + abs(w_r - w_r_prev)
            dw_rate_max = max(dw_rate_max, rate)
            w_l_prev, w_r_prev = w_l, w_r

        if step % LOG_INTERVAL == LOG_INTERVAL - 1:
            w_l, w_r = get_yaw_weights(c)
            dw  = abs(w_l - w_r) if not (math.isnan(w_l) or math.isnan(w_r)) else float('nan')
            fill = c.energy_store.fill_fraction
            pos  = c.world.body.position
            dist = math.sqrt(sum((pos[i]-SRC_POS[i])**2 for i in range(3)))
            print(f"{step+1:>7} | {da:>6.3f} | {fill:>6.3f} | "
                  f"{w_l:>7.4f} {w_r:>7.4f} {dw:>7.4f} | {dist:>6.1f}")

    # ── 最终结果 ──
    w_l_f, w_r_f = get_yaw_weights(c)
    dw_final = abs(w_l_f - w_r_f) if not (math.isnan(w_l_f) or math.isnan(w_r_f)) else 0.0
    fill_final = c.energy_store.fill_fraction

    f1 = da_peak > THRESH_DA_PEAK
    f2 = dw_final > THRESH_DW
    f3 = dw_rate_max < THRESH_DW_RATE
    f4 = fill_final > initial_fill_actual

    print()
    print("=" * 70)
    print(f"  DA 脉冲峰值:  {da_peak:.4f}  (阈值>{THRESH_DA_PEAK})   →  {'PASS ✅' if f1 else 'FAIL ❌'} F1")
    print(f"  |Δw| 末尾:    {dw_final:.4f}  (阈值>{THRESH_DW})    →  {'PASS ✅' if f2 else 'FAIL ❌'} F2")
    print(f"  dw 速率峰值:  {dw_rate_max:.4f}  (阈值<{THRESH_DW_RATE})   →  {'PASS ✅' if f3 else 'FAIL ❌'} F3")
    print(f"  fill 变化:    {initial_fill_actual:.4f}→{fill_final:.4f}  {'(回升)' if f4 else '(继续下降)'}  →  {'PASS ✅' if f4 else 'NOTE  -'} F4")
    print()
    all_pass = f1 and f2 and f3
    if all_pass:
        print("  [PASS] 首次接触验证通过：DA 脉冲 + yaw 方向分化启动")
        print("  下一步：T-057 200k 长程验证")
    else:
        print("  [FAIL] 部分指标未达标，请查阅上方详细结果")
    print("=" * 70)


if __name__ == '__main__':
    main()
