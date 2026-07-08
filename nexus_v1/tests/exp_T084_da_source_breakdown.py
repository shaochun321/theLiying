"""
T-084: DA 源电流分解诊断 — 定位"谁把 DA 顶到 1.0"

背景：T-083 实测 DA≡1.0（撤源后仍不降）。但核对代码发现：
  - shadow col 是 spiking + calcium_rate 硬钳位 ≤1.0（shadow_sandbox.py:67-74）
  - shadow_to_da: 7 源 × ≤1.0 × w(0.05) = 上限 0.35 → 不可能顶到 1.0
  - _da_drive = _rpe_da（fill 上升率），Phase2 fill 下降时 = 0
所以顶住 DA 的另有其人。本诊断在我们的代码里逐源打印 da_input_currents。

方法：复现 T-083 场景（贴源饱腹→撤源），每 sample 打印：
  - 各 DA 源束 propagate() 电流（frozen/STDP 均为只读）
  - RPE 注入（fill_rate_sensor.activation × DA_INJECT_SCALE 代理）
  - da_neuron 内部态（activation / membrane voltage / energy）
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

DT   = 1.0
PH1  = 12_000
PH2  = 20_000
LOG  = 2_000


def _sum_bundle_list(bundles):
    tot = 0.0
    for b in bundles:
        cur = b.propagate()
        tot += sum(cur) if cur else 0.0
    return tot


def _sum_bundle(b):
    if b is None:
        return 0.0
    cur = b.propagate()
    return sum(cur) if cur else 0.0


def main():
    print("=" * 96)
    print("  T-084: DA 源电流分解 — 定位 DA=1.0 的真实驱动源")
    print("=" * 96)

    src = HeatSource(position=[70.0, 50.0, 25.0], energy=500_000.0,
                     temperature=5.0, radius=30.0)
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

    hdr = (f"  {'Step':>6}|{'Ph':>2}|{'DA':>6}|{'shdw':>6}|{'intake':>6}|{'relay':>6}|"
           f"{'cpg':>5}|{'thmD':>5}|{'hung':>5}|{'shN':>5}|{'sat':>6}|{'RPE':>5}|"
           f"{'fill':>5}|{'dist':>5}")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    for step in range(1, PH2 + 1):
        if step == PH1:
            for s in list(world.heat_sources):
                if s.alive:
                    s.energy = 0.0
                    s.temperature = 0.0

        c.step({}, DT)

        if step % LOG == 0 or step == PH1 or step == PH1 + 2:
            da = c.dopamine.concentration
            shdw = _sum_bundle_list(getattr(c, 'bundles_shadow_to_da', []))
            intake = _sum_bundle(getattr(c, 'bundle_intake_to_da_reward', None))
            relay = _sum_bundle_list(getattr(c, 'bundles_relay_to_da', []))
            cpg = _sum_bundle_list(getattr(c, 'bundles_cpg_to_da', []))
            thmD = _sum_bundle_list(getattr(c, 'bundles_thermo_delta_to_da', []))
            hung = _sum_bundle(getattr(c, 'bundle_hunger_to_da', None))
            shN = _sum_bundle(getattr(c, 'bundle_shadow_nu_to_da', None))
            sat = _sum_bundle(getattr(c, 'bundle_satiety_to_da', None))
            rpe = c.fill_rate_sensor_neuron.activation * 0.1  # DA_INJECT_SCALE
            fill = c.energy_store.fill_fraction
            pos = c.world.body.position
            spos = c.world.heat_sources[0].position if c.world.heat_sources else [0, 0, 0]
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(pos, spos))) if c.world.heat_sources else float('inf')
            ph = 1 if step < PH1 else 2
            print(f"  {step:>6}|P{ph:1d}|{da:>6.3f}|{shdw:>6.3f}|{intake:>6.3f}|{relay:>6.3f}|"
                  f"{cpg:>5.2f}|{thmD:>5.2f}|{hung:>5.2f}|{shN:>5.2f}|{sat:>+6.3f}|{rpe:>5.2f}|"
                  f"{fill:>5.3f}|{dist:>5.1f}")

    # da_neuron 内部态
    print("\n  ── da_neuron 内部态（末步）──")
    for nid, n in c.da_neurons.items():
        vm = n._membrane.voltage
        print(f"    {nid:<10} act={n.activation:>7.4f}  vm={vm:>7.4f}  energy={n.energy:>6.3f}"
              f"  spiking={n.config.spiking}")

    # RPE 门 + D2 自受体状态
    print(f"\n  da_gate(_rpe_da) 末步: fill_rate_sensor.act={c.fill_rate_sensor_neuron.activation:.4f}")
    print(f"  DA 浓度 = clamp(mean da_neuron.activation, 0, 1)")
    _mean = sum(n.activation for n in c.da_neurons.values()) / max(len(c.da_neurons), 1)
    print(f"  mean da_neuron.activation = {_mean:.4f}  → clamp = {max(0.0, min(1.0, _mean)):.4f}")
    print("=" * 96)


if __name__ == '__main__':
    main()
