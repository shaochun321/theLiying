"""T-022 诊断：12贴片 → thermal_stability → CPC 信号验证。"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource

def run():
    c = VariantCircuit()

    # 单热源，固定位置
    c.world.heat_sources = [HeatSource(
        position=[50.0, 50.0, 25.0],
        temperature=1.5,   # 适中（sim units 0.1-1.5）
        radius=25.0,
        energy=1e9,
    )]

    # 身体从 x=75 接近热源 (x=50)
    c.world.body.position = [75.0, 50.0, 25.0]
    c.world.body.velocity = [-0.05, 0.0, 0.0]

    dt = 0.001
    STEPS = 5000

    # 前3步打印 soma_output 全部字段
    for step in range(3):
        c.step({}, dt)
    so = c.somatosensory.get_output()
    print("=== soma_output (patch sample) ===")
    if so:
        pid0 = list(so.keys())[0]
        print(f"  patches: {list(so.keys())}")
        print(f"  {pid0}: {so[pid0]}")
    else:
        print("  EMPTY!")
    print()

    # 计算 thermal_stability 和 feed_alignment 以了解量级
    relay_vals  = [so[p]["relay_activation"] for p in so]
    thermo_vals = [so[p]["thermo_activation"] for p in so]
    ts  = max(0.0, 1.0 - sum(relay_vals)/max(len(relay_vals),1))
    fa  = max(thermo_vals) - min(thermo_vals) if thermo_vals else 0.0
    print(f"thermal_stability={ts:.4f}  feed_align={fa:.4f}")
    print(f"relay_avg={sum(relay_vals)/max(len(relay_vals),1):.4f}  "
          f"thermo_max={max(thermo_vals):.4f}  thermo_min={min(thermo_vals):.4f}")
    print()

    # 运行到 5000 步，每 500 步打印 CPC 状态
    print(f"{'step':>6} | {'dist':>6} | {'therm_s':>8} | {'feed_al':>8} | "
          f"{'v_homeo':>7} | {'v_motor':>7} | {'v_feed':>7} | {'dev':>8} | {'rho_h':>6}")
    print("-" * 82)

    for step in range(3, STEPS + 1):
        c.step({}, dt)
        ms = c.motion_state
        if step % 500 == 0:
            pos = c.world.body.position
            dist = ((pos[0]-50)**2 + (pos[1]-50)**2 + (pos[2]-25)**2)**0.5

            so2 = c.somatosensory.get_output()
            rv = [so2[p]["relay_activation"] for p in so2]
            tv = [so2[p]["thermo_activation"] for p in so2]
            ts2 = max(0.0, 1.0 - sum(rv)/max(len(rv),1))
            fa2 = max(tv) - min(tv) if tv else 0.0

            vh  = getattr(ms, 'homeo_amplitude', 0.0)
            vm  = getattr(ms, 'motor_amplitude', 0.0)
            vf  = getattr(ms, 'feed_amplitude', 0.0)
            dev = getattr(ms, 'homeo_deviation', 0.0)
            rh  = getattr(ms, 'rho_homeo', 0.0)

            print(f"{step:>6} | {dist:>6.1f} | {ts2:>8.4f} | {fa2:>8.4f} | "
                  f"{vh:>7.4f} | {vm:>7.4f} | {vf:>7.4f} | {dev:>8.4f} | {rh:>6.4f}")

    print("\n[完成]")

if __name__ == '__main__':
    run()
