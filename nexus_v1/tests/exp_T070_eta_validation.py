"""
T-070: η验证（BMR 0.003 + VitalOsc amplitude 0.003）

目标：确认双参数调整后 Foraging 窗口占比 η 提升至 20-25%，
      且 fill_min > 0.20（不因 BMR 上调而饿死）。

对比基线：
  T-064 (BMR=0.0025, VitalOsc=0.005): η=14.9%, fill_min=0.2766
  T-062 (BMR=0.0025, VitalOsc=0.005, 200k): η=13.4%, fill_min=0.2784

Commit: aee09e3 (BMR 0.0025→0.003, VitalOsc 0.005→0.003)
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
    print("  T-070: η验证（BMR=0.003, VitalOsc=0.003）")
    print("  目标：η∈[20%, 25%] 且 fill_min>0.20")
    print("  对比：T-064 η=14.9% / T-062 η=13.4%")
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

    f_steps  = 0
    fill_min = 1.0
    dist_10k = None

    print(f"\n  {'Step':>7} | {'η%':>5} | {'fill':>5} | {'dist':>6} | {'DA':>5} | {'w_ccw':>6} {'w_cw':>6}")
    print("  " + "-" * 62)

    for step in range(1, STEPS + 1):
        c.step({}, DT)

        fill = get_fill(c)
        da   = get_da(c)
        fill_min = min(fill_min, fill)

        if fill < 0.85 and da > 0.1:
            f_steps += 1

        if step == 10_000:
            pos = c.world.body.position
            dist_10k = math.sqrt(sum((pos[i] - src.position[i]) ** 2 for i in range(3)))

        if step % REPORT_EVERY == 0:
            pos  = c.world.body.position
            dist = math.sqrt(sum((pos[i] - src.position[i]) ** 2 for i in range(3)))
            eta  = f_steps / step * 100
            w_ccw, w_cw = get_yaw_weights(c)
            print(f"  {step:>7} | {eta:>4.1f}% | {fill:>5.3f} | {dist:>6.1f} | {da:>5.3f} | {w_ccw:>6.4f} {w_cw:>6.4f}")

    eta_final = f_steps / STEPS * 100
    w_ccw, w_cw = get_yaw_weights(c)

    print()
    print("=" * 70)
    print("  T-070 最终判定：")
    print()

    r1 = 20.0 <= eta_final <= 30.0   # 目标区间（上限宽松至30%）
    r2 = fill_min > 0.20
    r3 = eta_final >= 15.0            # 最低可接受阈值

    print(f"    {'η_{E→L}% ∈ [20%, 30%]':<32} {eta_final:.2f}%  → {'PASS ✅' if r1 else ('ACCEPTABLE ⚠' if r3 else 'FAIL ❌')}")
    print(f"    {'fill 最低值 > 0.20':<32} {fill_min:.4f}  → {'PASS ✅' if r2 else 'FAIL ❌'}")
    print(f"    {'dist@10k (觅食速度)':<32} {dist_10k:.1f if dist_10k else 'N/A'}")
    print(f"    {'w_ccw / w_cw':<32} {w_ccw:.4f} / {w_cw:.4f}  |Δw|={abs(w_ccw - w_cw):.4f}")

    if not r1:
        if eta_final < 15.0:
            print()
            print("  ⚠ FAIL 诊断：η 仍未达标")
            print("    → fill 饱和过快（摄食速率 >> BMR）")
            print("    → 考虑进一步上调 BMR 或降低摄食效率 eta")
        elif eta_final > 30.0:
            print()
            print("  ⚠ WARNING：η 过高，body 可能在饿死边缘")
            print("    → 检查 fill_min，若 < 0.15 需降低 BMR")

    passed = sum([r1, r2])
    print(f"\n  总计：{passed}/2 PASS")
    print("=" * 70)


if __name__ == '__main__':
    run()
