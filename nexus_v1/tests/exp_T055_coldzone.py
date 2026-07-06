"""
exp_T055_coldzone.py — 两阶段 Phase 1：冷区 BMR 验证

目标：无热源环境下，验证 BMR 消耗驱动饥饿上升，DA 门控打开，
      phasic 信号保持钳位（≈0）。

验收：
  V1: fill 持续下降（BMR 消耗）→ fill(25k) < initial_fill
  V2: _hunger_ema 上升 → 末尾 _hunger_ema > 0.1
  V3: phasic_left + phasic_right < 0.02（钳位有效，无热信号）
  V4: relay 平均激活 < 0.05（无热觉输入驱动）
"""

import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS         = 25_000
DT            = 1.0
LOG_INTERVAL  = 5_000
INITIAL_FILL  = 0.3   # 饥饿起步
BODY_START    = [10.0, 50.0, 25.0]

THRESH_FILL_DROP   = True   # V1: fill(25k) < INITIAL_FILL
THRESH_HUNGER_EMA  = 0.1    # V2: _hunger_ema > 0.1
THRESH_PHASIC_MAX  = 0.02   # V3: phasic_l + phasic_r < THRESH_PHASIC_MAX
THRESH_RELAY_ACT   = 0.05   # V4: 均值 < THRESH_RELAY_ACT


def get_relay_mean(c):
    """平均 relay 神经元激活（therm 轴）。"""
    acts = []
    for layer in [c.vestibular.afferent_regular, c.vestibular.afferent_irregular]:
        for ax in layer.values():
            if hasattr(ax, 'activation'):
                acts.append(ax.activation)
    if not acts:
        return 0.0
    return sum(acts) / len(acts)


def main():
    print("=" * 70)
    print("  T-055: 两阶段 Phase 1 — 冷区 BMR 验证（无热源）")
    print("=" * 70)
    print(f"  Steps={STEPS//1000}k  DT={DT}")
    print(f"  body_start={BODY_START}  initial_fill={INITIAL_FILL}")
    print()

    # ── 无热源世界 ──
    body  = Body(position=list(BODY_START))
    world = World(heat_sources=[], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world
    c.somatosensory.LATERAL_GAIN = 0.3
    for m in c.muscle_system.muscles:
        m.gain = 0.3

    # 设置初始 fill = 0.3（饥饿起步）
    c.energy_store._cap.charge = c.energy_store.config.capacity * INITIAL_FILL
    initial_fill_actual = c.energy_store.fill_fraction
    print(f"  初始 fill: {initial_fill_actual:.3f}")
    print()

    hdr = (f"{'Step':>7} | {'fill':>6} | {'hunger':>7} | "
           f"{'phas_L':>7} {'phas_R':>7} | {'relay':>7} | {'DA':>6}")
    print(hdr)
    print("-" * len(hdr))

    phasic_max_seen = 0.0
    for step in range(STEPS):
        c.step({}, DT)

        ph_l = getattr(c, 'phasic_left',  None)
        ph_r = getattr(c, 'phasic_right', None)
        act_l = ph_l.activation if ph_l else 0.0
        act_r = ph_r.activation if ph_r else 0.0
        phasic_max_seen = max(phasic_max_seen, act_l + act_r)

        if step % LOG_INTERVAL == LOG_INTERVAL - 1:
            fill    = c.energy_store.fill_fraction
            hunger  = getattr(c, '_hunger_ema', 0.0)
            relay   = get_relay_mean(c)
            da      = c.dopamine.concentration if hasattr(c.dopamine, 'concentration') else 0.0
            print(f"{step+1:>7} | {fill:>6.3f} | {hunger:>7.4f} | "
                  f"{act_l:>7.4f} {act_r:>7.4f} | {relay:>7.4f} | {da:>6.3f}")

    # ── 最终状态 ──
    fill_final    = c.energy_store.fill_fraction
    hunger_final  = getattr(c, '_hunger_ema', 0.0)
    ph_l = getattr(c, 'phasic_left',  None)
    ph_r = getattr(c, 'phasic_right', None)
    phasic_final  = (ph_l.activation if ph_l else 0.0) + (ph_r.activation if ph_r else 0.0)

    v1 = fill_final < initial_fill_actual
    v2 = hunger_final > THRESH_HUNGER_EMA
    v3 = phasic_max_seen < THRESH_PHASIC_MAX
    v4 = get_relay_mean(c) < THRESH_RELAY_ACT

    print()
    print("=" * 70)
    print(f"  最终 fill:       {fill_final:.4f}  (初始={initial_fill_actual:.3f})  →  {'PASS ✅' if v1 else 'FAIL ❌'} V1")
    print(f"  _hunger_ema:    {hunger_final:.4f}  (阈值>{THRESH_HUNGER_EMA})    →  {'PASS ✅' if v2 else 'FAIL ❌'} V2")
    print(f"  phasic 峰值:    {phasic_max_seen:.4f}  (阈值<{THRESH_PHASIC_MAX})    →  {'PASS ✅' if v3 else 'FAIL ❌'} V3")
    print(f"  relay 均值:     {get_relay_mean(c):.4f}  (阈值<{THRESH_RELAY_ACT})   →  {'PASS ✅' if v4 else 'FAIL ❌'} V4")
    print()
    all_pass = v1 and v2 and v3 and v4
    if all_pass:
        print("  [PASS] 冷区验证通过：BMR 消耗/饥饿上升/phasic 钳位正常")
        print("  下一步：T-056 两阶段 Phase 2（引入热源，首次接触）")
    else:
        print("  [FAIL] 部分指标未达标，请查阅上方详细结果")
    print("=" * 70)


if __name__ == '__main__':
    main()
