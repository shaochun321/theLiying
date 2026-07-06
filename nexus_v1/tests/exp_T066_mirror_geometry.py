"""
T-066: 镜像几何实验（防诈胡第二层）

原理：翻转热源与body的空间关系，检验权重胜出方向是否随接近方向翻转。
  G1（正常）：body=[10,50,25] → src=[70,50,25]（从-x方向接近）
  G2（镜像）：body=[90,50,25] → src=[30,50,25]（从+x方向接近）

判定：
  - G1 和 G2 的权重胜出方（CCW vs CW）相反 → STDP 追踪空间梯度（真正学习）
  - G1 和 G2 胜出方相同 → 结构性偏置（STDP 只锁定随机初始非对称性）

通过标准：
  - 两组均出现方向分化（|Δw| > 0.15）
  - G1 vs G2 胜出方向不同（w_dominant_G1 ≠ w_dominant_G2）
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import World, HeatSource, Body

STEPS        = 200_000
DT           = 1.0
REPORT_EVERY = 20_000
W_DSI        = 5_000
EPS_DSI      = 1e-6


def get_yaw_weights(c):
    b_ccw = getattr(c, 'bundle_d1_phasic_left_to_spinal_ccw', None)
    b_cw  = getattr(c, 'bundle_d1_phasic_right_to_spinal_cw', None)
    w_ccw = b_ccw._memristors[0][0].w if (b_ccw and b_ccw._memristors) else float('nan')
    w_cw  = b_cw._memristors[0][0].w  if (b_cw  and b_cw._memristors)  else float('nan')
    return w_ccw, w_cw


def get_da(c):
    try:
        da_n = getattr(c, 'dopamine_neuron', None) or getattr(c, 'da_neuron', None)
        if da_n:
            return da_n.activation
        return c.dopamine.concentration
    except Exception:
        return 0.0


def get_fill(c):
    try:
        return c.energy_store._cap.charge / c.energy_store.config.capacity
    except Exception:
        return 0.0


def get_patch_dr5(c, src):
    try:
        pts = c._patch_temps
        vx  = c.world.body.velocity[0]
        vy  = c.world.body.velocity[1]
        lr  = pts.get('right', 0) - pts.get('left', 0)
        fb  = pts.get('front', 0) - pts.get('back', 0)
        return (lr * vx + fb * vy) > 0
    except Exception:
        return False


def run_group(label, body_pos, src_pos):
    print(f"\n  {'─'*60}")
    print(f"  {label}")
    print(f"  body={body_pos}  src={src_pos}")
    print(f"  {'─'*60}")

    src  = HeatSource(position=list(src_pos), temperature=5.0, radius=30, energy=1000.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=list(body_pos))
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world
    c.somatosensory.LATERAL_GAIN = 0.3
    for mn in c.motor_neurons.values():
        mn.config.output_gain = 0.1
    c.energy_store._cap.charge = c.energy_store.config.capacity * 0.3

    dr5_votes = 0
    f_steps   = 0
    dw_peak   = 0.0
    fill_min  = 1.0

    print(f"  {'Step':>7} | {'DR5%':>5} | {'η%':>5} | {'fill':>5} | {'dist':>6} | {'w_ccw':>6} {'w_cw':>6} | {'Δw_F':>6}")
    print("  " + "-" * 68)

    for step in range(1, STEPS + 1):
        c.step({}, DT)

        fill = get_fill(c)
        da   = get_da(c)
        fill_min = min(fill_min, fill)

        if get_patch_dr5(c, src):
            dr5_votes += 1

        if fill < 0.85 and da > 0.1:
            f_steps += 1
            w_ccw, w_cw = get_yaw_weights(c)
            dw_peak = max(dw_peak, abs(w_ccw - w_cw))

        if step % REPORT_EVERY == 0:
            pos  = c.world.body.position
            dist = math.sqrt(sum((pos[i] - src.position[i]) ** 2 for i in range(3)))
            eta  = f_steps / step * 100
            dr5  = dr5_votes / step * 100
            w_ccw, w_cw = get_yaw_weights(c)
            dw_f = dw_peak
            print(f"  {step:>7} | {dr5:>4.1f}% | {eta:>4.1f}% | {fill:>5.3f} | {dist:>6.1f} | {w_ccw:>6.4f} {w_cw:>6.4f} | {dw_f:>6.4f}")

    w_ccw_f, w_cw_f = get_yaw_weights(c)
    winner = 'CCW' if w_ccw_f > w_cw_f else 'CW'
    eta_f  = f_steps / STEPS * 100
    dr5_f  = dr5_votes / STEPS * 100

    print(f"\n  最终：w_ccw={w_ccw_f:.4f}  w_cw={w_cw_f:.4f}  |Δw|={abs(w_ccw_f-w_cw_f):.4f}")
    print(f"        胜出方向={winner}  DR5%={dr5_f:.1f}%  η={eta_f:.1f}%  fill_min={fill_min:.3f}")

    return {
        'winner': winner,
        'w_ccw': w_ccw_f,
        'w_cw': w_cw_f,
        'dw': abs(w_ccw_f - w_cw_f),
        'dw_peak': dw_peak,
        'dr5': dr5_f,
        'eta': eta_f,
        'fill_min': fill_min,
    }


def run():
    print("=" * 70)
    print("  T-066: 镜像几何实验（防诈胡第二层，各200k步）")
    print("  G1=正常几何  G2=body/src位置沿x轴翻转")
    print("=" * 70)

    g1 = run_group("G1（正常）", body_pos=[10.0, 50.0, 25.0], src_pos=[70.0, 50.0, 25.0])
    g2 = run_group("G2（镜像）", body_pos=[90.0, 50.0, 25.0], src_pos=[30.0, 50.0, 25.0])

    print()
    print("=" * 70)
    print("  T-066 最终判定：")
    print()

    diff_ok  = g1['dw_peak'] > 0.15 and g2['dw_peak'] > 0.15
    flip_ok  = g1['winner'] != g2['winner']

    print(f"    G1 胜出方向：{g1['winner']}  |Δw|_peak={g1['dw_peak']:.4f}")
    print(f"    G2 胜出方向：{g2['winner']}  |Δw|_peak={g2['dw_peak']:.4f}")
    print()
    r1 = diff_ok
    r2 = flip_ok
    print(f"    {'两组均出现方向分化（|Δw|_peak>0.15）':<40} → {'PASS ✅' if r1 else 'FAIL ❌'}")
    print(f"    {'G1/G2 胜出方向相反（学习非偏置）':<40} → {'PASS ✅' if r2 else 'FAIL ❌'}")

    if not r2:
        print()
        print("  ⚠ 若胜出方向相同：")
        print("    结论：STDP 在该权重初始化下锁定结构性偏置，非空间梯度追踪。")
        print("    → 建议：多 seed 重复实验（5 次），统计 CCW/CW 胜出率。")
        print("    → 建议：若 CCW 胜率 >80%，存在结构性偏置，需重新评估热趋性方向学习的来源。")

    passed = sum([r1, r2])
    print(f"\n  总计：{passed}/2 判定 PASS")
    print("=" * 70)


if __name__ == '__main__':
    run()
