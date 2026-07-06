"""
T-060: L2指标重构 + 50k步基线验证

新指标体系：
  L2a: Foraging窗口内权重峰值分化度 (max|Δw| when fill<0.85 AND DA>0.1)
  L2b: DSI方向选择指数 (foraging窗口内积分/标准差)
  L2c: η_{E→L} 能量-学习耦合效率 (foraging步数/总步数)
  DR5: patch温差·速度>0 的步数比（全程）
  Foraging DR5: foraging窗口内的 DR5
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import World, HeatSource, Body

STEPS       = 50_000
DT          = 1.0
REPORT_EVERY = 5_000
W_DSI       = 5_000   # DSI 积分窗口
EPS_DSI     = 1e-6

# ── 辅助函数（与 T-059 一致，P0-A 修复版） ──

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
    return avg_ax, avg_cr, avg_ax / max(avg_cr, 1e-6)

def get_patch_dr5_vote(c):
    """patch温差·速度 符号是否>0"""
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
        return c.dopamine_neuron.activation
    except Exception:
        return 0.0

def get_fill(c):
    try:
        return c.energy_store._cap.charge / c.energy_store.config.capacity
    except Exception:
        return 0.0

def compute_dsi_window(ccw_buf, cw_buf):
    """计算最近 W_DSI 步内的 DSI"""
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
    print("=" * 72)
    print("  T-060: 新指标体系基线验证（50k步）")
    print("  L2a=Foraging峰值分化  L2b=DSI  L2c=η_{E→L}")
    print("=" * 72)

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
    c.energy_store._cap.charge = c.energy_store.config.capacity * 0.3  # fill=0.3

    # ── 状态追踪 ──
    dr5_votes = 0
    foraging_dr5_votes = 0
    foraging_steps = 0
    total_steps_done = 0

    dw_peak_foraging = 0.0
    dsi_peak = 0.0
    ccw_buf, cw_buf = [], []

    fill_min = 1.0

    print(f"\n  {'Step':>7} | {'DR5%':>6} | {'fDR5%':>6} | {'w_ccw':>6} {'w_cw':>6} {'Δw_F':>6} | "
          f"{'DSI':>5} | {'η%':>5} | {'T4.1':>6} | {'fill':>5} | {'dist':>6}")
    print("  " + "-" * 88)

    for step in range(1, STEPS + 1):
        c.step({}, DT)
        total_steps_done = step

        fill = get_fill(c)
        da   = get_da(c)
        fill_min = min(fill_min, fill)

        pos  = c.world.body.position
        dist = math.sqrt(sum((pos[i] - src.position[i]) ** 2 for i in range(3)))

        vote = get_patch_dr5_vote(c)
        if vote:
            dr5_votes += 1

        in_foraging = (fill < 0.85 and da > 0.1)

        if in_foraging:
            foraging_steps += 1
            if vote:
                foraging_dr5_votes += 1

            # L2a
            w_ccw, w_cw = get_yaw_weights(c)
            dw = abs(w_ccw - w_cw)
            dw_peak_foraging = max(dw_peak_foraging, dw)

            # L2b 缓冲
            ccw_buf.append(c.spinal_ccw.activation)
            cw_buf.append(c.spinal_cw.activation)
            dsi_val = compute_dsi_window(ccw_buf, cw_buf)
            dsi_peak = max(dsi_peak, dsi_val)

        if step % REPORT_EVERY == 0:
            dr5_pct  = dr5_votes / step * 100
            f_dr5    = foraging_dr5_votes / max(foraging_steps, 1) * 100
            eta_pct  = foraging_steps / step * 100
            w_ccw, w_cw = get_yaw_weights(c)
            _, _, t41 = get_t41_ratio(c)
            print(f"  {step:>7} | {dr5_pct:>5.1f}% | {f_dr5:>5.1f}% | "
                  f"{w_ccw:>6.4f} {w_cw:>6.4f} {dw_peak_foraging:>6.4f} | "
                  f"{dsi_peak:>5.2f} | {eta_pct:>4.1f}% | "
                  f"{t41:>5.2f}x | {fill:>5.3f} | {dist:>6.1f}")

    # ── 最终指标 ──
    dr5_final  = dr5_votes / total_steps_done * 100
    f_dr5_final = foraging_dr5_votes / max(foraging_steps, 1) * 100
    eta_final  = foraging_steps / total_steps_done * 100
    _, _, t41_final = get_t41_ratio(c)
    w_ccw, w_cw = get_yaw_weights(c)

    print()
    print("=" * 72)
    print("  最终判定：")
    print()

    def chk(label, val, thr, direction='>'):
        ok = (val > thr) if direction == '>' else (val < thr)
        mark = "PASS ✅" if ok else "FAIL ❌"
        print(f"    {label:<30} {val:>8.4f}  (>{thr})  →  {mark}")
        return ok

    r_dr5  = chk("DR5%（全程）",      dr5_final,       60.0)
    r_fdr5 = chk("Foraging DR5%",     f_dr5_final,     60.0)
    r_l2a  = chk("L2a Δw_peak (Foraging)", dw_peak_foraging, 0.15)
    r_l2b  = chk("L2b DSI_peak",      dsi_peak,        1.0)
    r_l2c  = chk("L2c η_{E→L}%",     eta_final,        8.0)
    r_t41  = chk("T4.1（Col→Motor）", t41_final,        3.0)

    print()
    print(f"    fill最低: {fill_min:.4f}  (>0.001)  →  {'PASS ✅' if fill_min > 0.001 else 'FAIL ❌'}")
    print(f"    Foraging步数: {foraging_steps} / {total_steps_done}")

    decision = "跳过T-064" if eta_final >= 10.0 else "触发T-064（BMR 0.002→0.0025）"
    print(f"\n    决策点 η={eta_final:.1f}%：{decision}")

    pass_count = sum([r_dr5, r_l2a, r_l2b, r_l2c, r_t41])
    print(f"\n  总计：{pass_count}/5 主指标 PASS")
    print("=" * 72)


if __name__ == '__main__':
    run()
