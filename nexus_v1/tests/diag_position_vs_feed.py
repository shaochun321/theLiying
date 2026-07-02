"""diag_position_vs_feed.py — 定位代谢壁根因：身体位置 vs 热源距离 vs 进食率

假设：生物体在 ~100 步后漂离热源，T_local→0，P_in→0。
验证方法：打印前 500 步的 position/distance/T_local/energy_absorbed。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from nexus_v1.circuit.variant_adapter import VariantCircuit

c = VariantCircuit()
world = c.world
store = c.energy_store

# 获取热源列表
sources = world.heat_sources
print("=== 热源位置 ===")
for i, src in enumerate(sources):
    pos = getattr(src, 'position', None) or getattr(src, 'pos', None)
    strength = getattr(src, 'strength', None) or getattr(src, 'temperature', None)
    radius = getattr(src, 'radius', None)
    print(f"  src[{i}]: pos={pos}  strength={strength}  radius={radius}")

print(f"\n=== 初始身体位置 ===")
print(f"  body.position = {world.body.position}")
print()

# 计算到最近热源距离的函数
def dist_to_nearest(body_pos):
    import math
    min_d = float('inf')
    for src in sources:
        sp = getattr(src, 'position', None) or getattr(src, 'pos', None)
        if sp is not None:
            d = math.sqrt(sum((a-b)**2 for a,b in zip(body_pos, sp)))
            min_d = min(min_d, d)
    return min_d

print("step | pos_x   pos_y   pos_z | dist_nearest | T_local | energy_abs | fill")
print("-" * 80)

STEPS = 600
prev_dep = store._total_deposited

for step in range(1, STEPS + 1):
    c.step({'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0}, dt=1.0)

    dep_now = store._total_deposited
    energy_this_step = dep_now - prev_dep
    prev_dep = dep_now

    if step <= 20 or step % 50 == 0:
        pos = world.body.position
        dist = dist_to_nearest(pos)
        T_local = world.temperature_at(pos)
        fill = store.fill_fraction

        print(f"{step:4d} | {pos[0]:+7.3f} {pos[1]:+7.3f} {pos[2]:+7.3f} "
              f"| {dist:12.3f} | {T_local:7.4f} | {energy_this_step:10.5f} | {fill:.4f}")

print()
print("=== 诊断结论 ===")
pos_final = world.body.position
dist_final = dist_to_nearest(pos_final)
T_final = world.temperature_at(pos_final)
print(f"  最终位置: {pos_final}")
print(f"  最终距离最近热源: {dist_final:.3f}")
print(f"  最终 T_local: {T_final:.4f}")
print(f"  最终 fill: {store.fill_fraction:.4f}")

if dist_final > 20:
    print("  [!!] 生物体已漂离热源 (dist > 20) -- 这是 P_in=0 的根因")
elif T_final < 0.01:
    print("  [!!] T_local 接近零 -- 热源可能耗尽或 consume_nearby 无效")
else:
    print("  [OK] 生物体仍在热源附近 -- 需检查 consume_nearby 返回值逻辑")

# 额外：检查 world.consume_nearby 签名
print()
print("=== World.consume_nearby 参数检查 ===")
import inspect
try:
    sig = inspect.signature(world.consume_nearby)
    print(f"  consume_nearby{sig}")
except Exception as e:
    print(f"  无法获取签名: {e}")

try:
    sig2 = inspect.signature(world.temperature_at)
    print(f"  temperature_at{sig2}")
except Exception as e:
    print(f"  无法获取签名: {e}")
