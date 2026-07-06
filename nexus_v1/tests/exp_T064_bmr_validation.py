"""
T-064: BMR 上调验证（0.002 → 0.0025）

目标：确认 BMR+25% 后 Foraging 窗口占比 η 提升至 >8%，且 fill 不跌破 0.2。
若 PASS → 进入 T-066/T-063；若 FAIL → 诊断摄食速率是否始终 > BMR。
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import World, HeatSource, Body

STEPS        = 50_000
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


def run():
    print("=" * 70)
    print("  T-064: BMR 0.0025 验证（50k步）")
    print("  目标：η≥8% 且 fill_min>0.2")
    print("=" * 70)

    src = HeatSource(position=[70.0, 50.0, 25.0], temperature=5.0, radius=30, energy=1000.0)
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

    f_steps = 0
    fill_min = 1.0

    print(f"\n  {'Step':>7} | {'η%':>5} | {'fill':>5} | {'dist':>6} | {'DA':>5} | {'w_ccw':>6} {'w_cw':>6}")
    print("  " + "-" * 60)

    for step in range(1, STEPS + 1):
        c.step({}, DT)

        fill = get_fill(c)
        da   = get_da(c)
        fill_min = min(fill_min, fill)

        if fill < 0.85 and da > 0.1:
            f_steps += 1

        if step % REPORT_EVERY == 0:
            pos  = c.world.body.position
            dist = math.sqrt(sum((pos[i] - src.position[i]) ** 2 for i in range(3)))
            eta  = f_steps / step * 100
            w_ccw, w_cw = get_yaw_weights(c)
            print(f"  {step:>7} | {eta:>4.1f}% | {fill:>5.3f} | {dist:>6.1f} | {da:>5.3f} | {w_ccw:>6.4f} {w_cw:>6.4f}")

    eta_final = f_steps / STEPS * 100

    print()
    print("=" * 70)
    print("  T-064 最终判定：")
    print()

    r1 = eta_final >= 8.0
    r2 = fill_min > 0.2
    print(f"    {'η_{E→L}%':<30} {eta_final:.2f}%  (≥8%)   → {'PASS ✅' if r1 else 'FAIL ❌'}")
    print(f"    {'fill 最低值':<30} {fill_min:.4f}  (>0.2)  → {'PASS ✅' if r2 else 'FAIL ❌'}")

    w_ccw, w_cw = get_yaw_weights(c)
    print(f"\n    w_ccw={w_ccw:.4f}  w_cw={w_cw:.4f}  |Δw|={abs(w_ccw-w_cw):.4f}")

    if not r1:
        print()
        print("  ⚠ FAIL 诊断：η 未达标，可能原因：")
        print("    1. body 持续在热源中心（摄食速率 > BMR），fill 不降")
        print("    2. DA 持续 < 0.1（饱腹抑制），Foraging 窗口无法开启")
        print("    → 建议检查 dist@10k 和 DA@热源 数值")

    passed = sum([r1, r2])
    print(f"\n  总计：{passed}/2 指标 PASS")
    print("=" * 70)


if __name__ == '__main__':
    run()
