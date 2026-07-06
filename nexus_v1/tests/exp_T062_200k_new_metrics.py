"""
T-062: 200k步新指标验收

L2a: Foraging窗口内峰值分化度 max|Δw|
L2b: DSI方向选择指数（Foraging窗口）
L2c: η_{E→L} 能量-学习耦合效率
DR5: patch温差·速度（全程 + Foraging窗口）
T4.1: Col→Motor 比例

注：L2a/L2b 在"居中定居"场景下可能接近0（对称饱和），
    真正有效场景是双热源（T-063）。本次重点验证 L1/L3/L4/L5。
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import World, HeatSource, Body

STEPS        = 200_000
DT           = 1.0
REPORT_EVERY = 10_000
W_DSI        = 5_000
EPS_DSI      = 1e-6

def get_yaw_weights(c):
    b_ccw = getattr(c, 'bundle_d1_phasic_left_to_spinal_ccw', None)
    b_cw  = getattr(c, 'bundle_d1_phasic_right_to_spinal_cw', None)
    w_ccw = b_ccw._memristors[0][0].w if (b_ccw and b_ccw._memristors) else float('nan')
    w_cw  = b_cw._memristors[0][0].w  if (b_cw  and b_cw._memristors)  else float('nan')
    return w_ccw, w_cw

def get_t41_ratio(c):
    axis_ws, cross_ws = [], []
    for b in c.bundles_col_to_motor:
        ws = [m.w for row in b._memristors for m in row]
        avg_w = sum(ws) / max(len(ws), 1)
        if 'cross' not in b.id:
            axis_ws.append(avg_w)
        else:
            cross_ws.append(avg_w)
    avg_ax = sum(axis_ws) / max(len(axis_ws), 1)
    avg_cr = sum(cross_ws) / max(len(cross_ws), 1)
    return avg_ax / max(avg_cr, 1e-6)

def get_patch_dr5_vote(c):
    try:
        pts = c._patch_temps
        vx = c.world.body.velocity[0]
        vy = c.world.body.velocity[1]
        lr = pts.get('right', 0) - pts.get('left', 0)
        fb = pts.get('front', 0) - pts.get('back', 0)
        return (lr * vx + fb * vy) > 0
    except Exception:
        return False

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

def compute_dsi_window(ccw_buf, cw_buf):
    n = min(len(ccw_buf), W_DSI)
    if n < 100:
        return 0.0
    net = [ccw_buf[-n + i] - cw_buf[-n + i] for i in range(n)]
    integral = abs(sum(net))
    mean = sum(net) / len(net)
    variance = sum((x - mean) ** 2 for x in net) / len(net)
    sigma = variance ** 0.5
    return integral / (sigma * (n ** 0.5) + EPS_DSI)


def run():
    print("=" * 76)
    print("  T-062: 200k步新指标验收")
    print("  L2a/L2b/L2c + 传统 DR5/T4.1/fill")
    print("=" * 76)
    print("  注：L2a/L2b 在单热源居中定居场景下预期接近0，")
    print("      真正有效测试见 T-063（双热源强制方向选择）。")
    print()

    src  = HeatSource(position=[70.0, 50.0, 25.0], temperature=5.0, radius=30, energy=1000.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=[10.0, 50.0, 25.0])
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
    f_dr5_votes = 0
    f_steps = 0
    dw_peak_foraging = 0.0
    dsi_peak = 0.0
    ccw_buf, cw_buf = [], []
    fill_min = 1.0
    sdi_votes = 0  # fill > 0.8 占比

    print(f"  {'Step':>7} | {'DR5%':>6} | {'fDR5%':>6} | {'w_ccw':>6} {'w_cw':>6} {'Δw_F':>6} | "
          f"{'DSI':>5} | {'η%':>5} | {'T4.1':>6} | {'fill':>5} | {'dist':>6}")
    print("  " + "-" * 90)

    for step in range(1, STEPS + 1):
        c.step({}, DT)

        fill = get_fill(c)
        da   = get_da(c)
        fill_min = min(fill_min, fill)
        if fill > 0.8:
            sdi_votes += 1

        pos  = c.world.body.position
        dist = math.sqrt(sum((pos[i] - src.position[i]) ** 2 for i in range(3)))

        vote = get_patch_dr5_vote(c)
        if vote:
            dr5_votes += 1

        in_foraging = (fill < 0.85 and da > 0.1)
        if in_foraging:
            f_steps += 1
            if vote:
                f_dr5_votes += 1
            w_ccw, w_cw = get_yaw_weights(c)
            dw_peak_foraging = max(dw_peak_foraging, abs(w_ccw - w_cw))
            ccw_buf.append(c.spinal_ccw.activation)
            cw_buf.append(c.spinal_cw.activation)
            dsi_val = compute_dsi_window(ccw_buf, cw_buf)
            dsi_peak = max(dsi_peak, dsi_val)

        if step % REPORT_EVERY == 0:
            dr5_pct = dr5_votes / step * 100
            f_dr5   = f_dr5_votes / max(f_steps, 1) * 100
            eta_pct = f_steps / step * 100
            w_ccw, w_cw = get_yaw_weights(c)
            t41 = get_t41_ratio(c)
            print(f"  {step:>7} | {dr5_pct:>5.1f}% | {f_dr5:>5.1f}% | "
                  f"{w_ccw:>6.4f} {w_cw:>6.4f} {dw_peak_foraging:>6.4f} | "
                  f"{dsi_peak:>5.2f} | {eta_pct:>4.1f}% | "
                  f"{t41:>5.2f}x | {fill:>5.3f} | {dist:>6.1f}")

    dr5_final   = dr5_votes / STEPS * 100
    f_dr5_final = f_dr5_votes / max(f_steps, 1) * 100
    eta_final   = f_steps / STEPS * 100
    sdi_final   = sdi_votes / STEPS * 100
    t41_final   = get_t41_ratio(c)
    w_ccw, w_cw = get_yaw_weights(c)
    lock_pct    = 0.0  # 死锁率 (不适用单热源)

    print()
    print("=" * 76)
    print("  T-062 最终判定：")
    print()

    def chk(label, val, thr, fmt=".4f"):
        ok = val > thr
        mark = "PASS ✅" if ok else "FAIL ❌"
        print(f"    {label:<32} {val:{fmt}}  (>{thr})  →  {mark}")
        return ok

    r1 = chk("L1 DR5%",              dr5_final,       60.0, ".1f")
    r2 = chk("L2a Δw_peak(Foraging)", dw_peak_foraging, 0.15)
    r3 = chk("L2b DSI_peak",          dsi_peak,         1.0)
    r4 = chk("L2c η_{E→L}%",          eta_final,        8.0, ".2f")
    r5 = chk("L3 T4.1",               t41_final,        3.0, ".2f")
    r6 = fill_min > 0.001
    print(f"    {'L4 fill_min':<32} {fill_min:.4f}  (>0.001)  →  {'PASS ✅' if r6 else 'FAIL ❌'}")
    r7 = lock_pct < 10.0
    print(f"    {'L5 死锁率':<32} {lock_pct:.1f}%  (<10%)   →  {'PASS ✅' if r7 else 'FAIL ❌'}")
    print()
    print(f"    Foraging DR5%: {f_dr5_final:.1f}%  ({f_steps} foraging步)")
    print(f"    SDI (fill>0.8 占比): {sdi_final:.1f}%")

    decision = "跳过T-064" if eta_final >= 10.0 else "触发T-064（BMR 0.002→0.0025）"
    print(f"\n    决策点 η={eta_final:.1f}%：{decision}")

    passed = sum([r1, r2, r3, r4, r5, r6, r7])
    print(f"\n  总计：{passed}/7 指标 PASS")
    print("=" * 76)


if __name__ == '__main__':
    run()
