"""HC-016 200k 长期验证：yaw 学习稳定性

热源在 +x 方向 [70,50,25]，body 初始 [50,50,25]（朝 +x）。
预期：T_r 约等于 T_l（对称接近），yaw 保持小幅偏转，
relay_to_da 权重 wR > wL（right patch 先感受热）。

重点追踪：yaw_ccw/yaw_cw 激活、yaw 角度、r2d 权重分化。
"""
import sys, os, time, math
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS        = 200_000
DT           = 0.001
LOG_INTERVAL = 20_000

src  = HeatSource(position=[70.0, 50.0, 25.0], energy=50_000.0,
                  temperature=5.0, radius=30.0)
src._drift = [0.0, 0.0, 0.0]
body = Body(position=[50.0, 50.0, 25.0])
world = World(heat_sources=[src], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

c = VariantCircuit()
c.world = world
c.somatosensory.LATERAL_GAIN = 0.3
for m in c.muscle_system.muscles:
    m.gain = 0.3


def _r2d_weights():
    bundles = c.bundles_relay_to_da
    patch_ids = list(c.somatosensory.patch_ids)
    result = {}
    for i, pid in enumerate(patch_ids):
        if i < len(bundles):
            wm = bundles[i].weight_matrix()
            result[pid] = round(sum(wm[0]) / max(len(wm[0]), 1), 5) if wm else 0.0
    return result

def _patch_T():
    pt = c._patch_temps
    if not pt:
        return {k: 0.0 for k in ('right','left','front','back')}
    return {pid: round(pt[pid][0], 3) for pid in pt}

_prev_dist_ring = [None] * 1000  # 1000-step ring buffer for DR5 distance comparison
_dist_ring_idx = 0

def _current_dist():
    pos = list(world.body.position)
    return math.sqrt(sum((pos[i] - src.position[i])**2 for i in range(3)))

def _dr5_approaching(current_d):
    """DR5: fraction of steps where body is closer than 1000 steps ago.

    Replaces patch-temperature dot-product (was 100% false-positive because
    patch ΔT direction and velocity direction happen to agree even when body
    moves away from source). Distance-decrease is the only unambiguous
    thermotaxis criterion.
    """
    global _dist_ring_idx
    past_d = _prev_dist_ring[_dist_ring_idx]
    _prev_dist_ring[_dist_ring_idx] = current_d
    _dist_ring_idx = (_dist_ring_idx + 1) % 1000
    if past_d is None:
        return False   # not enough history yet
    return current_d < past_d


t0 = time.time()
print("=" * 80)
print("HC-016 200k 长期验证  |  +x 热源 [70,50,25]  |  追踪 yaw 学习")
print("=" * 80)
print(f"\n初始 r2d: {_r2d_weights()}")

hdr = (f"{'step':>7}  {'d':>5} {'yaw°':>6}  "
       f"{'yaw_ccw':>8} {'yaw_cw':>8}  "
       f"{'T_r':>6} {'T_l':>6} {'T_f':>6} {'T_b':>6}  "
       f"{'r2d_R':>7} {'r2d_L':>7} {'r2d_F':>7} {'r2d_B':>7}  "
       f"{'DR5%':>5}")
print(f"\n{hdr}")
print("-" * len(hdr))

dr5_pos = dr5_tot = 0

for step in range(1, STEPS + 1):
    t = step * DT
    signal = {
        'yaw':   2.0 * math.sin(1.5 * t),
        'pitch': 1.5 * math.sin(1.0 * t),
        'roll':  1.0 * math.sin(0.7 * t),
        'oto_x': 6.0 * math.sin(2.0 * t),
        'oto_y': 6.0 * math.sin(2.5 * t + 0.3),
        'oto_z': 6.0 * math.sin(3.0 * t + 0.7),
    }
    c.step(signal, dt=DT)

    _d_now = _current_dist()
    _approaching = _dr5_approaching(_d_now)
    dr5_tot += 1
    if _approaching:
        dr5_pos += 1

    if step % LOG_INTERVAL == 0:
        d    = _d_now
        yaw_deg = math.degrees(world.body.yaw)
        ccw_act = c.yaw_ccw_neuron.activation
        cw_act  = c.yaw_cw_neuron.activation
        pt   = _patch_T()
        r2d  = _r2d_weights()
        dr5_pct = 100.0 * dr5_pos / max(dr5_tot, 1)

        print(f"{step:>7d}  {d:>5.1f} {yaw_deg:>6.2f}  "
              f"{ccw_act:>8.4f} {cw_act:>8.4f}  "
              f"{pt.get('right',0):>6.3f} {pt.get('left',0):>6.3f} "
              f"{pt.get('front',0):>6.3f} {pt.get('back',0):>6.3f}  "
              f"{r2d.get('right',0):>7.5f} {r2d.get('left',0):>7.5f} "
              f"{r2d.get('front',0):>7.5f} {r2d.get('back',0):>7.5f}  "
              f"{dr5_pct:>5.1f}")
        dr5_pos = dr5_tot = 0

elapsed = time.time() - t0
r2d_fin = _r2d_weights()
print(f"\n{'=' * 80}")
print(f"DONE  {STEPS}步  |  {elapsed:.0f}s")
print(f"最终 r2d: {r2d_fin}")
print(f"wR - wL = {r2d_fin.get('right',0) - r2d_fin.get('left',0):+.5f}  (期望 > 0)")
print(f"最终 yaw = {math.degrees(world.body.yaw):.2f}°")
print(f"最终 pos = {[round(x,1) for x in world.body.position]}")
