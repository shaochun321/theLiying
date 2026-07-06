"""
T-061: 前庭消融验证

目的：验证方向性学习内容来自热感觉空间梯度，而非前庭固有偏置。
方法：将 body.acceleration（oto 信号来源）缩放至 α=0.02（2%），
      保留所有 STDP、饥饿敏化、影子层输入、能量链。
对照：α=1.0（正常）vs 实验：α=0.02（消融）

通过标准：DR5 下降 < 15%（实验组仍 > 61%）
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import World, HeatSource, Body

STEPS        = 50_000
DT           = 1.0
REPORT_EVERY = 10_000

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
        return c.dopamine_neuron.activation
    except Exception:
        return 0.0

def get_fill(c):
    try:
        return c.energy_store._cap.charge / c.energy_store.config.capacity
    except Exception:
        return 0.0


class AccelerationProxy:
    """Wraps Body，读取 acceleration 时缩放，写入时透传到原对象。

    body.step() 在原对象上写 acceleration（不经过代理），
    variant_adapter.step() 读 acc = self.world.body.acceleration 时经过代理缩放。
    """
    def __init__(self, body, alpha):
        object.__setattr__(self, '_body', body)
        object.__setattr__(self, '_alpha', alpha)

    def __getattr__(self, name):
        val = getattr(object.__getattribute__(self, '_body'), name)
        if name == 'acceleration':
            alpha = object.__getattribute__(self, '_alpha')
            return [a * alpha for a in val]
        return val

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, '_body'), name, value)


def make_circuit(alpha=1.0):
    src = HeatSource(position=[70.0, 50.0, 25.0], temperature=5.0, radius=30, energy=1000.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=[10.0, 50.0, 25.0])
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world
    if alpha != 1.0:
        c.world.body = AccelerationProxy(body, alpha)

    c.somatosensory.LATERAL_GAIN = 0.3
    for mn in c.motor_neurons.values():
        mn.config.output_gain = 0.1
    c.energy_store._cap.charge = c.energy_store.config.capacity * 0.3
    return c


def run_group(alpha, label):
    print(f"\n  {'─'*60}")
    print(f"  {label}（α={alpha}）")
    print(f"  {'─'*60}")
    print(f"  {'Step':>7} | {'DR5%':>6} | {'fDR5%':>6} | "
          f"{'w_ccw':>6} {'w_cw':>6} | {'fill':>5} | {'dist':>6}")
    print("  " + "-" * 65)

    c = make_circuit(alpha)
    src = c.world.heat_sources[0]

    dr5_votes = 0
    f_dr5_votes = 0
    f_steps = 0
    fill_min = 1.0

    for step in range(1, STEPS + 1):
        c.step({}, DT)

        fill = get_fill(c)
        da   = get_da(c)
        fill_min = min(fill_min, fill)

        vote = get_patch_dr5_vote(c)
        if vote:
            dr5_votes += 1

        if fill < 0.85 and da > 0.1:
            f_steps += 1
            if vote:
                f_dr5_votes += 1

        if step % REPORT_EVERY == 0:
            pos  = c.world.body.position
            dist = math.sqrt(sum((pos[i] - src.position[i]) ** 2 for i in range(3)))
            dr5_pct  = dr5_votes / step * 100
            f_dr5    = f_dr5_votes / max(f_steps, 1) * 100
            w_ccw, w_cw = get_yaw_weights(c)
            print(f"  {step:>7} | {dr5_pct:>5.1f}% | {f_dr5:>5.1f}% | "
                  f"{w_ccw:>6.4f} {w_cw:>6.4f} | {fill:>5.3f} | {dist:>6.1f}")

    dr5_final = dr5_votes / STEPS * 100
    f_dr5_final = f_dr5_votes / max(f_steps, 1) * 100
    t41 = get_t41_ratio(c)
    return dr5_final, f_dr5_final, t41, fill_min


def run():
    print("=" * 72)
    print("  T-061: 前庭消融验证（α=0.02 vs α=1.0，各50k步）")
    print("=" * 72)

    dr5_ctrl, fdr5_ctrl, t41_ctrl, fill_ctrl = run_group(1.0,  "对照组（正常前庭）")
    dr5_abl,  fdr5_abl,  t41_abl,  fill_abl  = run_group(0.02, "实验组（前庭消融α=0.02）")

    drop     = dr5_ctrl - dr5_abl
    f_drop   = fdr5_ctrl - fdr5_abl

    print()
    print("=" * 72)
    print("  T-061 最终判定：")
    print()
    print(f"  对照组 DR5%：      {dr5_ctrl:.1f}%  (Foraging: {fdr5_ctrl:.1f}%)")
    print(f"  实验组 DR5%：      {dr5_abl:.1f}%  (Foraging: {fdr5_abl:.1f}%)")
    print(f"  DR5 下降：         {drop:.1f}%  (Foraging下降: {f_drop:.1f}%)")
    print()

    passed = drop < 15.0
    if passed:
        print(f"  DR5下降 {drop:.1f}% < 15% → PASS ✅")
        print("  结论：方向性学习来源于热感觉空间梯度，非前庭固有偏置")
    elif drop < 25.0:
        print(f"  DR5下降 {drop:.1f}%（15-25%）→ ⚠️ 边缘（前庭有轻度贡献）")
        print("  建议：检查前庭链路不对称性")
    else:
        print(f"  DR5下降 {drop:.1f}% > 25% → FAIL ❌（前庭是主要方向来源）")

    print(f"\n  T4.1: 对照={t41_ctrl:.2f}x  消融={t41_abl:.2f}x")
    print(f"  fill最低: 对照={fill_ctrl:.4f}  消融={fill_abl:.4f}")
    print("=" * 72)


if __name__ == '__main__':
    run()
