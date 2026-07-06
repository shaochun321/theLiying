"""
T-063: 双热源鞍点实验

物理意义：两等强热源的中垂线是不稳定鞍点。
微弱CPG噪声使body向一侧偏移→该侧phasic信号增强→STDP正反馈→对称性破缺。

配置：
  热源A: [70, 30, 25], T=5, r=30
  热源B: [70, 70, 25], T=5, r=30
  Body初始: [10, 50, 25]（两源中垂线）

验收：
  - 选择一侧（dist_A<10 or dist_B<10）
  - L2a Δw_peak > 0.2（双热源场景需求更强分化）
  - SDI > 80%（选定后驻留）
  - 死锁率 < 10%（y方向永久徘徊在48-52之间）
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
DEADLOCK_Y_LO, DEADLOCK_Y_HI = 48.0, 52.0  # 中垂线死锁区

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

def get_patch_dr5_vote(c, src_a, src_b):
    """DR5: 体朝最近热源方向移动"""
    try:
        pos = c.world.body.position
        da = math.sqrt(sum((pos[i] - src_a.position[i])**2 for i in range(3)))
        db = math.sqrt(sum((pos[i] - src_b.position[i])**2 for i in range(3)))
        nearest_src = src_a if da < db else src_b
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
    print("=" * 80)
    print("  T-063: 双热源鞍点实验（200k步）")
    print("  A=[70,30,25]  B=[70,70,25]  body=[10,50,25]")
    print("=" * 80)

    src_a = HeatSource(position=[70.0, 30.0, 25.0], temperature=5.0, radius=30, energy=1000.0)
    src_b = HeatSource(position=[70.0, 70.0, 25.0], temperature=5.0, radius=30, energy=1000.0)
    src_a._drift = [0.0, 0.0, 0.0]
    src_b._drift = [0.0, 0.0, 0.0]
    body = Body(position=[10.0, 50.0, 25.0])
    world = World(heat_sources=[src_a, src_b], body=body)
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
    sdi_votes = 0
    deadlock_votes = 0  # y 在 48-52 之间

    # 最终选择追踪
    final_side = None  # 'A', 'B', or 'None'

    print(f"\n  {'Step':>7} | {'DR5%':>6} | {'fDR5%':>6} | {'w_ccw':>6} {'w_cw':>6} {'Δw_F':>6} | "
          f"{'DSI':>5} | {'η%':>5} | {'fill':>5} | {'dA':>6} {'dB':>6} | {'y':>5}")
    print("  " + "-" * 94)

    for step in range(1, STEPS + 1):
        c.step({}, DT)

        fill = get_fill(c)
        da   = get_da(c)
        fill_min = min(fill_min, fill)
        if fill > 0.8:
            sdi_votes += 1

        pos  = c.world.body.position
        dist_a = math.sqrt(sum((pos[i] - src_a.position[i]) ** 2 for i in range(3)))
        dist_b = math.sqrt(sum((pos[i] - src_b.position[i]) ** 2 for i in range(3)))

        # 死锁检测：y 在中垂线附近
        if DEADLOCK_Y_LO <= pos[1] <= DEADLOCK_Y_HI:
            deadlock_votes += 1

        vote = get_patch_dr5_vote(c, src_a, src_b)
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
            print(f"  {step:>7} | {dr5_pct:>5.1f}% | {f_dr5:>5.1f}% | "
                  f"{w_ccw:>6.4f} {w_cw:>6.4f} {dw_peak_foraging:>6.4f} | "
                  f"{dsi_peak:>5.2f} | {eta_pct:>4.1f}% | "
                  f"{fill:>5.3f} | {dist_a:>6.1f} {dist_b:>6.1f} | {pos[1]:>5.1f}")

    # 最终位置判定
    final_pos  = c.world.body.position
    dist_a_fin = math.sqrt(sum((final_pos[i] - src_a.position[i]) ** 2 for i in range(3)))
    dist_b_fin = math.sqrt(sum((final_pos[i] - src_b.position[i]) ** 2 for i in range(3)))
    if dist_a_fin < 10.0:
        final_side = 'A'
    elif dist_b_fin < 10.0:
        final_side = 'B'
    else:
        final_side = 'NONE'

    dr5_final     = dr5_votes / STEPS * 100
    f_dr5_final   = f_dr5_votes / max(f_steps, 1) * 100
    eta_final     = f_steps / STEPS * 100
    sdi_final     = sdi_votes / STEPS * 100
    deadlock_pct  = deadlock_votes / STEPS * 100
    t41_final     = get_t41_ratio(c)
    w_ccw, w_cw   = get_yaw_weights(c)

    print()
    print("=" * 80)
    print("  T-063 最终判定：")
    print()

    def chk(label, val, thr, op='>', fmt=".4f"):
        ok = (val > thr) if op == '>' else (val < thr)
        mark = "PASS ✅" if ok else "FAIL ❌"
        print(f"    {label:<36} {val:{fmt}}  ({op}{thr})  →  {mark}")
        return ok

    r1 = final_side in ('A', 'B')
    print(f"    {'选定一侧热源':<36} {final_side}  (A or B)  →  {'PASS ✅' if r1 else 'FAIL ❌'}")
    print(f"    {'最终 dist_A / dist_B':<36} {dist_a_fin:.1f} / {dist_b_fin:.1f}")
    r2 = chk("L2a Δw_peak(Foraging)",  dw_peak_foraging, 0.2)
    r3 = chk("L2b DSI_peak",           dsi_peak,         1.0)
    r4 = chk("SDI (fill>0.8 占比)",    sdi_final,        80.0, fmt=".1f")
    r5 = chk("死锁率（中垂线徘徊）",   deadlock_pct,     10.0, op='<', fmt=".1f")
    r6 = fill_min > 0.001
    print(f"    {'fill最低':<36} {fill_min:.4f}  (>0.001)  →  {'PASS ✅' if r6 else 'FAIL ❌'}")
    print()
    print(f"    DR5%（全程）: {dr5_final:.1f}%   Foraging DR5%: {f_dr5_final:.1f}%")
    print(f"    T4.1: {t41_final:.2f}x   η_{{E→L}}: {eta_final:.1f}%")
    print(f"    w_ccw: {w_ccw:.4f}   w_cw: {w_cw:.4f}   |Δw|_final: {abs(w_ccw-w_cw):.4f}")

    passed = sum([r1, r2, r3, r4, r5, r6])
    print(f"\n  总计：{passed}/6 指标 PASS")
    print("=" * 80)


if __name__ == '__main__':
    run()
