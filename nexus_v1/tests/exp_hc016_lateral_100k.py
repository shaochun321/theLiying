"""HC-016 侧向热源验证：yaw 转向功能测试

热源在 +y 方向 [50,70,25]，body 初始 [50,50,25]、yaw=0（朝 +x）。
体坐标：left=[0,+r,0] → 旋转后为 +y 世界方向。

预期行为：
  T_l > T_r  （左侧 patch 更热）
  yaw_ccw > yaw_cw  （CCW 转矩，左侧推动）
  yaw 增大（CCW 为正）→ body 朝向逐渐转向 +y
  转向后 d 减小，body 接近热源

失败判据：yaw 不变 or 向错方向转 → HC-016B 或 bundle 信号异常
"""
import sys, os, time, math
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS        = 100_000
DT           = 0.001
LOG_INTERVAL = 10_000

# 热源在 +y（body 初始朝 +x，热源在左侧）
src  = HeatSource(position=[50.0, 70.0, 25.0], energy=50_000.0,
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


def _patch_T():
    pt = c._patch_temps
    if not pt:
        return {k: 0.0 for k in ('right','left','front','back')}
    return {pid: round(pt[pid][0], 3) for pid in pt}

def _dr5():
    pt = c._patch_temps
    if not pt:
        return 0.0
    T_r = pt.get('right', (0,))[0]; T_l = pt.get('left', (0,))[0]
    T_f = pt.get('front', (0,))[0]; T_b = pt.get('back', (0,))[0]
    bv = world.body.velocity
    return (T_r - T_l) * bv[0] + (T_f - T_b) * bv[1]

def _r2d_weights():
    bundles = c.bundles_relay_to_da
    patch_ids = list(c.somatosensory.patch_ids)
    result = {}
    for i, pid in enumerate(patch_ids):
        if i < len(bundles):
            wm = bundles[i].weight_matrix()
            result[pid] = round(sum(wm[0]) / max(len(wm[0]), 1), 5) if wm else 0.0
    return result


t0 = time.time()
print("=" * 80)
print("HC-016 侧向热源验证  |  +y 热源 [50,70,25]  |  初始 yaw=0（朝 +x）")
print("预期：T_l > T_r → yaw_ccw > yaw_cw → yaw 增大 → 转向 +y")
print("=" * 80)

hdr = (f"{'step':>7}  {'d':>5} {'yaw°':>7}  "
       f"{'yaw_ccw':>8} {'yaw_cw':>8}  "
       f"{'T_r':>6} {'T_l':>6} {'T_f':>6} {'T_b':>6}  "
       f"{'pos_x':>7} {'pos_y':>7}  "
       f"{'r2d_R':>7} {'r2d_L':>7}  "
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

    dv = _dr5()
    bv = world.body.velocity
    if dv != 0.0 or any(abs(v) > 1e-8 for v in bv):
        dr5_tot += 1
        if dv > 0:
            dr5_pos += 1

    if step % LOG_INTERVAL == 0:
        pos  = list(world.body.position)
        d    = math.sqrt(sum((pos[i] - src.position[i])**2 for i in range(3)))
        yaw_deg = math.degrees(world.body.yaw)
        ccw_act = c.yaw_ccw_neuron.activation
        cw_act  = c.yaw_cw_neuron.activation
        pt   = _patch_T()
        r2d  = _r2d_weights()
        dr5_pct = 100.0 * dr5_pos / max(dr5_tot, 1)

        print(f"{step:>7d}  {d:>5.1f} {yaw_deg:>7.2f}  "
              f"{ccw_act:>8.4f} {cw_act:>8.4f}  "
              f"{pt.get('right',0):>6.3f} {pt.get('left',0):>6.3f} "
              f"{pt.get('front',0):>6.3f} {pt.get('back',0):>6.3f}  "
              f"{pos[0]:>7.2f} {pos[1]:>7.2f}  "
              f"{r2d.get('right',0):>7.5f} {r2d.get('left',0):>7.5f}  "
              f"{dr5_pct:>5.1f}")
        dr5_pos = dr5_tot = 0

elapsed = time.time() - t0
r2d_fin = _r2d_weights()
yaw_fin = math.degrees(world.body.yaw)
pos_fin = [round(x, 1) for x in world.body.position]
d_fin   = math.sqrt(sum((world.body.position[i] - src.position[i])**2 for i in range(3)))

print(f"\n{'=' * 80}")
print(f"DONE  {STEPS}步  |  {elapsed:.0f}s")
print(f"最终 yaw   = {yaw_fin:.2f}°  (期望 > 0，CCW 转向 +y)")
print(f"最终 pos   = {pos_fin}")
print(f"最终 d     = {d_fin:.1f}  (期望 < 20)")
print(f"最终 r2d_L = {r2d_fin.get('left',0):.5f}  r2d_R = {r2d_fin.get('right',0):.5f}")

# 方向判定
if yaw_fin > 5.0:
    print("\n[PASS] yaw 向 CCW 方向偏转，转向热源方向正确")
elif yaw_fin < -5.0:
    print("\n[FAIL] yaw 向 CW 偏转，转向方向错误（热源在左侧应 CCW）")
else:
    print(f"\n[WEAK] yaw={yaw_fin:.2f}°，转向幅度不足（可能需要更长时间）")
