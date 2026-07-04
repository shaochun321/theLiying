"""P3 验证：relay→yaw Push-Pull LTD 100k 实验

热源在 +x 方向 [70,50,25]，body 初始 [50,50,25]（朝 +x）。
与 P1 200k 条件相同，缩短到 100k 快速验证 push-pull 效果。

额外追踪：relay_to_yaw 权重（LTP束 wR/wL + LTD束 wR_ltd/wL_ltd）。

预期（vs P1 200k失败）：
  - wR-wL > 0 维持（不全部饱和至 0.300）
  - yaw 超调 < 30°（P1 超调到 -128° 后锁定）
  - DR5 > 60%（全程平均，P1 在 60k 后跌至 0）
"""
import sys, os, time, math
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS        = 100_000
DT           = 0.001
LOG_INTERVAL = 10_000

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


def _relay_yaw_weights():
    """Return (wR_ltp, wL_ltp, wR_ltd, wL_ltd) from bundles_relay_to_yaw."""
    result = {'ltp_cw': 0.0, 'ltp_ccw': 0.0, 'ltd_cw': 0.0, 'ltd_ccw': 0.0}
    for b in c.bundles_relay_to_yaw:
        bid = b.config.bundle_id
        wm = b.weight_matrix()
        w = round(sum(wm[0]) / max(len(wm[0]), 1), 5) if wm else 0.0
        if 'ltd' in bid:
            if 'yaw_cw' in bid:
                result['ltd_cw'] = w
            else:
                result['ltd_ccw'] = w
        else:
            if 'yaw_cw' in bid:
                result['ltp_cw'] = w
            else:
                result['ltp_ccw'] = w
    return result


def _patch_T():
    pt = c._patch_temps
    if not pt:
        return {k: 0.0 for k in ('right', 'left', 'front', 'back')}
    return {pid: round(pt[pid][0], 3) for pid in pt}


_prev_dist_ring = [None] * 1000
_dist_ring_idx = 0


def _current_dist():
    pos = list(world.body.position)
    return math.sqrt(sum((pos[i] - src.position[i])**2 for i in range(3)))


def _dr5_approaching(current_d):
    global _dist_ring_idx
    past_d = _prev_dist_ring[_dist_ring_idx]
    _prev_dist_ring[_dist_ring_idx] = current_d
    _dist_ring_idx = (_dist_ring_idx + 1) % 1000
    if past_d is None:
        return False
    return current_d < past_d


t0 = time.time()
print("=" * 90)
print("P3 验证：Push-Pull LTD  |  +x 热源 [70,50,25]  |  100k 步")
print("新增：relay_to_yaw LTP束(wCW/wCCW) + LTD束(wCW_ltd/wCCW_ltd)")
print("=" * 90)

hdr = (f"{'step':>7}  {'d':>5} {'yaw°':>7}  "
       f"{'y_ccw':>7} {'y_cw':>7}  "
       f"{'T_r':>6} {'T_l':>6}  "
       f"{'r2d_R':>7} {'r2d_L':>7}  "
       f"{'ltp_cw':>7} {'ltp_ccw':>7}  "
       f"{'ltd_cw':>7} {'ltd_ccw':>7}  "
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
    if _dr5_approaching(_d_now):
        dr5_pos += 1
    dr5_tot += 1

    if step % LOG_INTERVAL == 0:
        d       = _d_now
        yaw_deg = math.degrees(world.body.yaw)
        ccw_act = c.yaw_ccw_neuron.activation
        cw_act  = c.yaw_cw_neuron.activation
        pt      = _patch_T()
        r2d     = _r2d_weights()
        ryaw    = _relay_yaw_weights()
        dr5_pct = 100.0 * dr5_pos / max(dr5_tot, 1)

        print(f"{step:>7d}  {d:>5.1f} {yaw_deg:>7.2f}  "
              f"{ccw_act:>7.4f} {cw_act:>7.4f}  "
              f"{pt.get('right', 0):>6.3f} {pt.get('left', 0):>6.3f}  "
              f"{r2d.get('right', 0):>7.5f} {r2d.get('left', 0):>7.5f}  "
              f"{ryaw['ltp_cw']:>7.5f} {ryaw['ltp_ccw']:>7.5f}  "
              f"{ryaw['ltd_cw']:>7.5f} {ryaw['ltd_ccw']:>7.5f}  "
              f"{dr5_pct:>5.1f}")
        dr5_pos = dr5_tot = 0

elapsed = time.time() - t0
r2d_fin  = _r2d_weights()
ryaw_fin = _relay_yaw_weights()
yaw_fin  = math.degrees(world.body.yaw)
pos_fin  = [round(x, 1) for x in world.body.position]
d_fin    = _current_dist()

print(f"\n{'=' * 90}")
print(f"DONE  {STEPS}步  |  {elapsed:.0f}s")
print(f"最终 yaw    = {yaw_fin:.2f}°  (P1基线: -127.96°，期望 > -30°)")
print(f"最终 pos    = {pos_fin}")
print(f"最终 d      = {d_fin:.1f}  (P1基线: 25.2)")
print(f"最终 r2d    wR={r2d_fin.get('right',0):.5f}  wL={r2d_fin.get('left',0):.5f}  "
      f"wR-wL={r2d_fin.get('right',0)-r2d_fin.get('left',0):+.5f}")
print(f"最终 ltp    cw={ryaw_fin['ltp_cw']:.5f}  ccw={ryaw_fin['ltp_ccw']:.5f}  "
      f"diff={ryaw_fin['ltp_cw']-ryaw_fin['ltp_ccw']:+.5f}")
print(f"最终 ltd    cw={ryaw_fin['ltd_cw']:.5f}  ccw={ryaw_fin['ltd_ccw']:.5f}  (frozen, 应≈0.2)")

# 判定
yaw_ok  = -30.0 < yaw_fin < 90.0
dist_ok = d_fin < 20.0
wdiff_ok = r2d_fin.get('right', 0) - r2d_fin.get('left', 0) > 0.01

print()
print("[PASS] yaw 未超调锁定" if yaw_ok else f"[FAIL] yaw 超调锁定 ({yaw_fin:.1f}°)")
print("[PASS] 最终距离 < 20" if dist_ok else f"[WEAK] 最终距离 {d_fin:.1f} >= 20")
print("[PASS] wR > wL 维持" if wdiff_ok else "[FAIL] WTA 权重全饱和或反转")
