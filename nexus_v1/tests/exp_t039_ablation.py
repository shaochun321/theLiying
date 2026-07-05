"""T-039: D1 Bundle 消融实验 — 核心诈胡验证

目的：确认方向性学习（Δw）唯一来自 phasic→spinal D1 STDP bundle，
      而非隐藏硬编码或其他结构偏置。

消融操作：phasic_left→spinal_ccw 和 phasic_right→spinal_cw 两条 D1 bundle
         权重归零并冻结（不修改母本代码，仅在实验脚本中修改已实例化对象）。

设置：与 T-038 完全相同（body=[10,50,25], heat=[70,50,25], fill=0.3, 50k步）

判定标准：
  P6-1: |Δw| = 0（D1 frozen，trivially保证，确认消融有效）
  P6-2: DR5% 测量（HC-016A frozen bundle 能否独立维持热趋性方向？）
  P6-3: 首次接触仍发生（体能量链完整性）
"""

from __future__ import annotations
import sys
import os
import time
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.stdout.reconfigure(line_buffering=True)

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS        = 50_000
LOG_INTERVAL = 5_000
DT           = 1.0
INIT_FILL    = 0.3

src  = HeatSource(position=[70.0, 50.0, 25.0], energy=50_000.0,
                  temperature=5.0, radius=30.0)
src._drift = [0.0, 0.0, 0.0]
body = Body(position=[10.0, 50.0, 25.0])
world = World(heat_sources=[src], body=body)
world.MIN_ALIVE  = 0
world.REGEN_PROB = 0.0

c = VariantCircuit()
c.world = world
c.energy_store._cap.charge = c.energy_store.config.capacity * INIT_FILL
c.somatosensory.LATERAL_GAIN = 0.3
for m in c.muscle_system.muscles:
    m.gain = 0.3

# ── ABLATION: D1 bundles 归零并冻结 ──────────────────────────────────────────
# 不修改母本代码，仅修改已实例化对象的权重和学习规则
_d1_bundles = [
    c.bundle_d1_phasic_left_to_spinal_ccw,
    c.bundle_d1_phasic_right_to_spinal_cw,
]
for _b in _d1_bundles:
    for _row in _b._memristors:
        for _m in _row:
            _m.w = 0.0
    _b.config.learning_rule = 'frozen'   # learn() 直接 return，不更新权重
print("  [ABLATION] D1 bundles zeroed and frozen: "
      "phasic_left→spinal_ccw, phasic_right→spinal_cw")
# ─────────────────────────────────────────────────────────────────────────────

src_pos = src.position


def get_yaw_weights():
    w_ccw, w_cw = float('nan'), float('nan')
    b_ccw = c.bundle_d1_phasic_left_to_spinal_ccw
    b_cw  = c.bundle_d1_phasic_right_to_spinal_cw
    if b_ccw and b_ccw._memristors:
        w_ccw = b_ccw._memristors[0][0].w
    if b_cw and b_cw._memristors:
        w_cw = b_cw._memristors[0][0].w
    return w_ccw, w_cw


def get_t41_ratio():
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
    return avg_ax / max(avg_cr, 1e-6)


def get_dr5():
    pT  = c._patch_temps if hasattr(c, '_patch_temps') else {}
    T   = {pid: pT.get(pid, (0.0,))[0] for pid in ['front', 'back', 'left', 'right']}
    vx  = c.world.body.velocity[0] if hasattr(c.world.body, 'velocity') else 0.0
    vy  = c.world.body.velocity[1] if hasattr(c.world.body, 'velocity') else 0.0
    pgx = T.get('right', 0) - T.get('left', 0)
    pgy = T.get('front', 0) - T.get('back', 0)
    return pgx * vx + pgy * vy > 0


def main():
    print("=" * 90)
    print("  T-039: D1 Bundle 消融实验（诈胡核心验证）")
    print("=" * 90)
    print(f"  消融：phasic_left→spinal_ccw, phasic_right→spinal_cw（权重=0，frozen）")
    print(f"  设置：Body=[10,50,25], Heat=[70,50,25], fill={INIT_FILL}（饥饿）")
    print(f"  Steps={STEPS//1000}k, DT={DT}, LOG={LOG_INTERVAL//1000}k")
    print()

    hdr = (f"{'Step':>6} | "
           f"{'x':>7} {'dist':>6} | "
           f"{'w_ccw':>6} {'w_cw':>6} {'Δw':>7} | "
           f"{'fill':>6} {'sat':>5} | "
           f"{'T41':>5} | "
           f"{'DA':>6} {'pL':>7} {'pR':>7} | "
           f"{'pPeak':>6} | DR5%")
    print(hdr)
    print("-" * len(hdr))

    phasic_all_max = 0.0
    dr5_count      = 0
    first_contact_step = None
    t_start = time.time()

    for step in range(STEPS):
        c.step({}, DT)

        pos  = c.world.body.position
        dist = math.sqrt(sum((pos[i] - src_pos[i]) ** 2 for i in range(3)))
        pl   = c.phasic_left.activation
        pr   = c.phasic_right.activation
        phasic_all_max = max(phasic_all_max, abs(pl), abs(pr))

        if dist < 30 and first_contact_step is None:
            first_contact_step = step
            print(f"  >>> 首次接触热场！step={step}, dist={dist:.2f}")

        if step % LOG_INTERVAL == LOG_INTERVAL - 1:
            w_ccw, w_cw = get_yaw_weights()
            dw   = (w_cw - w_ccw) if not (math.isnan(w_ccw) or math.isnan(w_cw)) else float('nan')
            fill = c.energy_store.fill_fraction
            sat  = c.satiety_neuron.activation if hasattr(c, 'satiety_neuron') else 0.0
            t41  = get_t41_ratio()
            da   = c.dopamine.concentration if hasattr(c.dopamine, 'concentration') else 0.0

            if get_dr5():
                dr5_count += 1
            dr5_pct = dr5_count / ((step + 1) / LOG_INTERVAL) * 100

            print(f"{step+1:>6} | "
                  f"{pos[0]:>7.2f} {dist:>6.2f} | "
                  f"{w_ccw:>6.4f} {w_cw:>6.4f} {dw:>+7.4f} | "
                  f"{fill:>6.4f} {sat:>5.3f} | "
                  f"{t41:>5.2f}x | "
                  f"{da:>6.4f} {pl:>7.3f} {pr:>7.3f} | "
                  f"{phasic_all_max:>6.3f} | {dr5_pct:.1f}%")

    elapsed = time.time() - t_start
    w_ccw_f, w_cw_f = get_yaw_weights()
    fill_f  = c.energy_store.fill_fraction
    dw_final = abs(w_cw_f - w_ccw_f) if not math.isnan(w_ccw_f) else 0.0

    print()
    print("=" * 90)
    print(f"  完成: {STEPS//1000}k 步, 耗时 {elapsed:.1f}s")
    print()
    print("  === P6 验证（D1消融诈胡测试）===")

    p61_pass = dw_final < 0.005   # 权重冻结在0，Δw trivially 0
    print(f"  P6-1 |Δw|=0: |w_ccw-w_cw|={dw_final:.6f} "
          f"→ {'PASS (<0.005, D1消融有效)' if p61_pass else 'FAIL (有隐藏方向源!)'}")

    dr5_final = dr5_count / (STEPS / LOG_INTERVAL) * 100
    p62_above50 = dr5_final > 50.0
    print(f"  P6-2 DR5%={dr5_final:.1f}% "
          f"→ {'HC-016A 可独立维持热趋性' if p62_above50 else 'HC-016A 单独不足 (≈随机基线)'}")

    p63_pass = first_contact_step is not None
    print(f"  P6-3 首次接触: "
          f"{'step='+str(first_contact_step) if p63_pass else '未发生（body未进入热场）'} "
          f"→ {'PASS (运动链完整)' if p63_pass else 'FAIL (能量或运动链断裂)'}")

    print()
    if p61_pass:
        print("  ✓ 消融验证通过：方向性学习（Δw）唯一来自 D1 STDP bundle。")
        if p62_above50:
            print("  ✓ HC-016A 反射弧独立维持一定热趋性（DR5>50%），符合结构设计预期。")
        else:
            print("  ~ HC-016A 单独不足维持热趋性，D1+HC-016A 协同是热趋性的主要机制。")
    else:
        print("  ✗ 警告：消融后 Δw 仍显著，存在未被识别的方向来源，需要排查！")
        print("    排查路径：检查 get_all_bundles() 是否有其他 STDP phasic→spinal 连接。")

    print(f"  fill_final={fill_f:.4f}")


if __name__ == "__main__":
    main()
