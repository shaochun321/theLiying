"""T-040: 热源侧向反转实验 — 方向性辅助验证

目的：验证方向性学习（Δw）随热源空间位置真实翻转，排除固定方向偏置。

几何设计（修正原文档错误 G2=[30,50,25]→仍在右侧）：
  Body 初始面朝 +x 方向（默认 yaw=0）。热源放在 ±y 方向（body 的正左/正右），
  确保左/右 sensor patch 温差方向确定。

  G1（热在左）：body=[50,10,25], heat=[50,70,25], dist=60
    → left_patch 更近热源 → phasic_left 正值 → CCW 应胜（w_ccw > w_cw）

  G2（热在右）：body=[50,90,25], heat=[50,30,25], dist=60
    → right_patch 更近热源 → phasic_right 正值 → CW 应胜（w_cw > w_ccw）

判定标准：
  P7-1: G1 结果 w_ccw > w_cw（Δw = w_cw - w_ccw < 0）
  P7-2: G2 结果 w_cw > w_ccw（Δw = w_cw - w_ccw > 0）
  P7-3: G1 和 G2 的 Δw 符号相反（真实方向翻转）
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

CONFIGS = {
    'G1_heat_left': {
        'body_pos':  [50.0, 10.0, 25.0],
        'heat_pos':  [50.0, 70.0, 25.0],
        'label':     'G1: 热源在左(+y)  body=[50,10,25] heat=[50,70,25]',
        'expected':  'w_ccw > w_cw (CCW偏好，phasic_left应激活)',
    },
    'G2_heat_right': {
        'body_pos':  [50.0, 90.0, 25.0],
        'heat_pos':  [50.0, 30.0, 25.0],
        'label':     'G2: 热源在右(-y)  body=[50,90,25] heat=[50,30,25]',
        'expected':  'w_cw > w_ccw (CW偏好，phasic_right应激活)',
    },
}


def run_one_config(cfg_key: str, cfg: dict) -> dict:
    """运行单个配置，返回结果字典。"""
    src  = HeatSource(position=cfg['heat_pos'], energy=50_000.0,
                      temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=cfg['body_pos'])
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE  = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world
    c.energy_store._cap.charge = c.energy_store.config.capacity * INIT_FILL
    c.somatosensory.LATERAL_GAIN = 0.3
    for m in c.muscle_system.muscles:
        m.gain = 0.3

    src_pos = src.position

    def get_yaw_weights():
        b_ccw = c.bundle_d1_phasic_left_to_spinal_ccw
        b_cw  = c.bundle_d1_phasic_right_to_spinal_cw
        w_ccw = b_ccw._memristors[0][0].w if b_ccw and b_ccw._memristors else float('nan')
        w_cw  = b_cw._memristors[0][0].w  if b_cw  and b_cw._memristors  else float('nan')
        return w_ccw, w_cw

    def get_dr5():
        pT  = c._patch_temps if hasattr(c, '_patch_temps') else {}
        T   = {pid: pT.get(pid, (0.0,))[0] for pid in ['front', 'back', 'left', 'right']}
        vx  = c.world.body.velocity[0] if hasattr(c.world.body, 'velocity') else 0.0
        vy  = c.world.body.velocity[1] if hasattr(c.world.body, 'velocity') else 0.0
        pgx = T.get('right', 0) - T.get('left', 0)
        pgy = T.get('front', 0) - T.get('back', 0)
        return pgx * vx + pgy * vy > 0

    print(f"\n{'─'*90}")
    print(f"  {cfg['label']}")
    print(f"  预期：{cfg['expected']}")
    print(f"{'─'*90}")
    hdr = (f"{'Step':>6} | "
           f"{'y':>7} {'dist':>6} | "
           f"{'w_ccw':>6} {'w_cw':>6} {'Δw':>7} | "
           f"{'fill':>6} | "
           f"{'DA':>6} {'pL':>7} {'pR':>7} | "
           f"{'pPeak':>6} | DR5%")
    print(hdr)
    print("-" * len(hdr))

    phasic_all_max = 0.0
    dr5_count = 0
    first_contact = None
    t_start = time.time()

    for step in range(STEPS):
        c.step({}, DT)

        pos  = c.world.body.position
        dist = math.sqrt(sum((pos[i] - src_pos[i]) ** 2 for i in range(3)))
        pl   = c.phasic_left.activation
        pr   = c.phasic_right.activation
        phasic_all_max = max(phasic_all_max, abs(pl), abs(pr))

        if dist < 30 and first_contact is None:
            first_contact = step
            print(f"  >>> 首次接触！step={step}, dist={dist:.2f}, "
                  f"pL={pl:.4f}, pR={pr:.4f}")

        if step % LOG_INTERVAL == LOG_INTERVAL - 1:
            w_ccw, w_cw = get_yaw_weights()
            dw   = (w_cw - w_ccw) if not math.isnan(w_ccw) else float('nan')
            fill = c.energy_store.fill_fraction
            da   = c.dopamine.concentration if hasattr(c.dopamine, 'concentration') else 0.0

            if get_dr5():
                dr5_count += 1
            dr5_pct = dr5_count / ((step + 1) / LOG_INTERVAL) * 100

            print(f"{step+1:>6} | "
                  f"{pos[1]:>7.2f} {dist:>6.2f} | "
                  f"{w_ccw:>6.4f} {w_cw:>6.4f} {dw:>+7.4f} | "
                  f"{fill:>6.4f} | "
                  f"{da:>6.4f} {pl:>7.3f} {pr:>7.3f} | "
                  f"{phasic_all_max:>6.3f} | {dr5_pct:.1f}%")
            phasic_all_max = 0.0

    elapsed = time.time() - t_start
    w_ccw_f, w_cw_f = get_yaw_weights()
    dw_final = w_cw_f - w_ccw_f if not math.isnan(w_ccw_f) else 0.0
    dr5_final = dr5_count / (STEPS / LOG_INTERVAL) * 100
    print(f"\n  完成：{STEPS//1000}k步, {elapsed:.1f}s")
    print(f"  最终: w_ccw={w_ccw_f:.4f}, w_cw={w_cw_f:.4f}, Δw={dw_final:+.4f}, DR5%={dr5_final:.1f}%")

    return {
        'cfg_key': cfg_key,
        'w_ccw':   w_ccw_f,
        'w_cw':    w_cw_f,
        'dw':      dw_final,
        'dr5':     dr5_final,
        'first_contact': first_contact,
    }


def main():
    print("=" * 90)
    print("  T-040: 热源侧向反转实验（诈胡辅助验证）")
    print("=" * 90)
    print(f"  Body 初始面朝 +x，热源置于 ±y 方向（body正左/正右），dist=60")
    print(f"  Steps={STEPS//1000}k, fill={INIT_FILL}（饥饿），连续运行两组")

    results = {}
    for cfg_key, cfg in CONFIGS.items():
        results[cfg_key] = run_one_config(cfg_key, cfg)

    # ── 汇总判定 ──────────────────────────────────────────────────────────────
    print()
    print("=" * 90)
    print("  === P7 验证（热源方向反转）===")
    r1 = results['G1_heat_left']
    r2 = results['G2_heat_right']

    # G1: 热在左，期望 w_ccw > w_cw → Δw < 0
    p71_pass = r1['w_ccw'] > r1['w_cw']
    print(f"  P7-1 G1(热在左) w_ccw>{r1['w_ccw']:.4f} vs w_cw={r1['w_cw']:.4f}: "
          f"{'PASS (CCW胜，预期正确)' if p71_pass else 'FAIL (方向不符预期)'}")

    # G2: 热在右，期望 w_cw > w_ccw → Δw > 0
    p72_pass = r2['w_cw'] > r2['w_ccw']
    print(f"  P7-2 G2(热在右) w_cw={r2['w_cw']:.4f} vs w_ccw={r2['w_ccw']:.4f}: "
          f"{'PASS (CW胜，预期正确)' if p72_pass else 'FAIL (方向不符预期)'}")

    # P7-3: Δw 符号相反
    p73_pass = (r1['dw'] * r2['dw'] < 0)   # 符号相反则乘积为负
    print(f"  P7-3 Δw符号相反: G1Δw={r1['dw']:+.4f}, G2Δw={r2['dw']:+.4f}: "
          f"{'PASS (方向真实翻转)' if p73_pass else 'FAIL (方向未翻转，存在固定偏置)'}")

    total = p71_pass and p72_pass and p73_pass
    print()
    print(f"  总体: {'PASS' if total else 'PARTIAL/FAIL'} "
          f"(P7-1={'✓' if p71_pass else '✗'} "
          f"P7-2={'✓' if p72_pass else '✗'} "
          f"P7-3={'✓' if p73_pass else '✗'})")

    if total:
        print()
        print("  ✓ 方向翻转验证通过：方向性学习真实跟随热源空间位置，排除固定偏置。")
    else:
        print()
        print("  ✗ 部分未通过。可能原因：")
        print("    - 50k 步不足以建立稳定偏好（CPG 随机性）")
        print("    - 初始 CPG 相位偶然导致与热源位置相同的方向被首先强化")
        print("    - 建议：增加步数至 100k-200k 再判断")


if __name__ == "__main__":
    main()
