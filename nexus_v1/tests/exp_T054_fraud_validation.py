"""
exp_T054_fraud_validation.py — 诈胡验证（STDP 全冻结）

目标：冻结所有可学习 bundle 的 STDP，保留 T-043/T-047/T-048 结构完整，
      检查 DR5% 是否退回随机基线（≤55%）。

验收：
  DR5 ≤ 55%  → PASS：方向性来自 STDP 学习，T-043 不创造硬连线方向
  DR5 > 55%  → FAIL：进入 T-054b T-043 消融验证
"""

import sys, math
sys.path.insert(0, '.')

PYTHONIOENCODING = 'utf-8'

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS        = 50_000
DT           = 1.0
LOG_INTERVAL = 5_000
SRC_POS      = [70.0, 50.0, 25.0]
BODY_START   = [10.0, 50.0, 25.0]
PASS_THRESH  = 55.0   # DR5 ≤ 55% → PASS


def freeze_all_stdp(circuit):
    """冻结全部可学习 bundle，返回 (已冻结数, bundle_id 列表)。"""
    count = 0
    ids = []
    for b in circuit.get_all_bundles():
        if b.config.learning_rule not in ("frozen",):
            b.config.stdp_lr = 0.0
            if hasattr(b.config, 'eligibility_gain'):
                b.config.eligibility_gain = 0.0
            count += 1
            ids.append(b.id)
    return count, ids


def get_dr5(c):
    """patch 温差 · body 速度符号 > 0（post-P0 正确指标，不使用 world.gradient_at）。"""
    pT = c._patch_temps if hasattr(c, '_patch_temps') else {}
    T  = {pid: pT.get(pid, (0.0,))[0] for pid in ['front', 'back', 'left', 'right']}
    vx = c.world.body.velocity[0] if hasattr(c.world.body, 'velocity') else 0.0
    vy = c.world.body.velocity[1] if hasattr(c.world.body, 'velocity') else 0.0
    gx = T.get('right', 0.0) - T.get('left', 0.0)
    gy = T.get('front', 0.0) - T.get('back', 0.0)
    return (gx * vx + gy * vy) > 0.0


def get_yaw_weights(c):
    """读取 relay_to_slow_left/right 的平均权重作为方向分化指标。"""
    w_l = w_r = float('nan')
    bl = getattr(c, 'bundle_relay_to_slow_left', None)
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
    print("  T-054: 诈胡验证 — 50k 步 STDP 全冻结")
    print("=" * 70)
    print(f"  Steps={STEPS//1000}k  DT={DT}")
    print(f"  热源={SRC_POS}  body_start={BODY_START}")
    print(f"  通过标准：DR5 ≤ {PASS_THRESH:.0f}%（≈50% 随机基线）")
    print()

    # ── 构建电路 ──
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
    c.energy_store._cap.charge = c.energy_store.config.capacity * 0.5

    # ── 冻结 STDP ──
    n_frozen, frozen_ids = freeze_all_stdp(c)
    print(f"  已冻结 {n_frozen} 条 STDP bundle（共 {len(c.get_all_bundles())} 条）")
    print()

    # ── T-043 bundle 状态确认 ──
    b_ccw_cw = getattr(c, 'bundle_spinal_ccw_to_yaw_cw', None)
    b_cw_ccw = getattr(c, 'bundle_spinal_cw_to_yaw_ccw', None)
    if b_ccw_cw:
        w = [m.w for row in b_ccw_cw._memristors for m in row]
        print(f"  T-043 bundle_spinal_ccw_to_yaw_cw: w={sum(w)/max(len(w),1):.4f} (frozen={b_ccw_cw.config.learning_rule=='frozen'})")
    if b_cw_ccw:
        w = [m.w for row in b_cw_ccw._memristors for m in row]
        print(f"  T-043 bundle_spinal_cw_to_yaw_ccw: w={sum(w)/max(len(w),1):.4f} (frozen={b_cw_ccw.config.learning_rule=='frozen'})")
    print()

    hdr = (f"{'Step':>7} | {'DR5%':>6} | {'dist':>6} | "
           f"{'w_L':>7} {'w_R':>7} {'Dw':>7} | "
           f"{'DA':>6} | {'fill':>5}")
    print(hdr)
    print("-" * len(hdr))

    dr5_count = 0
    for step in range(STEPS):
        c.step({}, DT)

        if get_dr5(c):
            dr5_count += 1

        if step % LOG_INTERVAL == LOG_INTERVAL - 1:
            dr5_pct = dr5_count / (step + 1) * 100
            pos  = c.world.body.position
            dist = math.sqrt(sum((pos[i] - SRC_POS[i]) ** 2 for i in range(3)))
            w_l, w_r = get_yaw_weights(c)
            dw   = (w_l - w_r) if not (math.isnan(w_l) or math.isnan(w_r)) else float('nan')
            da   = c.dopamine.concentration if hasattr(c.dopamine, 'concentration') else 0.0
            fill = c.energy_store.fill_fraction
            print(f"{step+1:>7} | {dr5_pct:>5.1f}% | {dist:>6.1f} | "
                  f"{w_l:>7.4f} {w_r:>7.4f} {dw:>+7.4f} | "
                  f"{da:>6.3f} | {fill:>5.3f}")

    # ── 最终判定 ──
    dr5_final = dr5_count / STEPS * 100
    passed    = dr5_final <= PASS_THRESH
    w_l, w_r  = get_yaw_weights(c)

    print()
    print("=" * 70)
    print(f"  最终 DR5%:  {dr5_final:.1f}%")
    print(f"  yaw 权重:   w_L={w_l:.4f}  w_R={w_r:.4f}  |Dw|={abs(w_l - w_r) if not math.isnan(w_l) else 'nan':.4f}")
    print(f"  已冻结束数: {n_frozen}")
    print()
    if passed:
        print(f"  [PASS] DR5={dr5_final:.1f}% ≤ {PASS_THRESH:.0f}% — 方向性来自 STDP，T-043 通过诈胡验证")
        print(f"  下一步：T-055 两阶段 Phase 1（冷区 BMR 验证）")
    else:
        print(f"  [FAIL] DR5={dr5_final:.1f}% > {PASS_THRESH:.0f}% — 存在硬连线方向性")
        print(f"  下一步：T-054b T-043 消融验证（归零 W_CROSS，重跑 50k）")
    print("=" * 70)


if __name__ == '__main__':
    main()
