"""
T-090: 死锁二增益调制 MVE 验证 — hunger 门控热趋反射增益

验证 GatedReflexArc：hunger 上下文经 DA-gated STDP 学到增益指令，经 MOSFET 物理乘法
调制 thermo→yaw 反射的 synapse_gain。方向 100% 留给 frozen 反射 → 与方向零重叠=非冗余。

结构（学习相 + 探针相，避免依赖涌现的 fill 循环）：
  学习相(0~LEARN): 周期撤源/复源 → 饥饿复发 + 饥饿-奖励共现(eligibility 桥接) → 门学习。
  探针相: 冻结门(测静态学到的函数), 外部钳制 fill 高/低, 测 gain 对饥饿的响应。

两条件对照(除 frozen 外全同):
  ON     : 学习相开启学习
  FROZEN : 全程冻结(权重停 0, 仅 Memristor G(0) 泄漏) — E2' 差分基线

判定(方案 v2 §9.5):
  E1  上下文调制: gain(hungry probe) − gain(full probe) > 0.3
  E2' 差分因果:   E1(ON) − E1(FROZEN) > 0.1   (学习增量, 隔离先天泄漏+hunger→DA 直接路径)
  E3  权重分化:   w_hunger_gate(ON) > 0.05
  E4  对称性:     |sg_L − sg_R| < 5%  (单一全局门)
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.gain_mod_adapter import GainModCircuit
from nexus_v1.components.world import HeatSource, Body, World

DT = 1.0
LEARN = 40_000
CYCLE = 20_000
ON_STEPS = 8_000
PROBE_SETTLE = 2_500     # 探针钳制后等 hunger/gate 平衡
PROBE_MEASURE = 1_000    # 测量窗口

SRC = [70.0, 50.0, 25.0]
BODY = [10.0, 50.0, 25.0]


def _probe(c, fill_target):
    """钳制 fill 到目标, 等平衡, 返回平均 gain。"""
    cap = c.energy_store.config.capacity
    src = c.world.heat_sources[0]
    src.energy = 500_000.0; src.temperature = 5.0   # 源在(热场存在)
    for _ in range(PROBE_SETTLE):
        c.energy_store._cap.charge = cap * fill_target
        c.step({}, DT)
    g = 0.0
    for _ in range(PROBE_MEASURE):
        c.energy_store._cap.charge = cap * fill_target
        c.step({}, DT)
        g += c.gate_state()["gain"]
    return g / PROBE_MEASURE


def run(frozen: bool):
    src = HeatSource(position=list(SRC), energy=500_000.0, temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=list(BODY))
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = GainModCircuit()
    c.world = world
    c.somatosensory.LATERAL_GAIN = 0.3
    for mn in c.motor_neurons.values():
        mn.config.output_gain = 0.1
    c.set_gate_frozen(frozen)
    c.energy_store._cap.charge = c.energy_store.config.capacity * 0.3

    tag = "FROZEN" if frozen else "ON"
    print(f"\n{'='*80}\n  条件: gate-{tag}\n{'='*80}")

    # ── 学习相：周期撤源/复源 ──
    for step in range(1, LEARN + 1):
        on = (step % CYCLE) < ON_STEPS
        if on:
            src.energy = 500_000.0; src.temperature = 5.0
        else:
            src.energy = 0.0; src.temperature = 0.0
        c.step({}, DT)
        if step % 10_000 == 0:
            s = c.gate_state()
            print(f"  [learn {step:>6}] gain={s['gain']:.3f} m_gate={s['m_gate']:.3f} "
                  f"w={s['w_hunger_gate']:.4f} hunger={c.hypothalamus_hunger.activation:.3f} "
                  f"fill={c.energy_store.fill_fraction:.3f}")

    w_learned = c.gate_state()["w_hunger_gate"]

    # ── 探针相：冻结门, 钳制 fill 高/低, 测 gain ──
    c.set_gate_frozen(True)
    g_hungry = _probe(c, 0.10)   # 饥饿
    hunger_h = c.hypothalamus_hunger.activation
    g_full = _probe(c, 0.95)     # 饱腹
    hunger_f = c.hypothalamus_hunger.activation

    e1 = g_hungry - g_full
    sgL = c.bundle_left_to_yaw.config.synapse_gain
    sgR = c.bundle_right_to_yaw.config.synapse_gain

    print(f"  [probe] gain(hungry,fill=0.10)={g_hungry:.3f} (hunger={hunger_h:.2f})  "
          f"gain(full,fill=0.95)={g_full:.3f} (hunger={hunger_f:.2f})")
    print(f"  [gate-{tag}] E1={e1:.3f}  w_learned={w_learned:.4f}  sg_L={sgL:.4f} sg_R={sgR:.4f}")
    return {"e1": e1, "gh": g_hungry, "gf": g_full, "w": w_learned, "sgL": sgL, "sgR": sgR}


def main():
    print("=" * 80)
    print("  T-090: 死锁二增益调制 MVE — hunger 门控热趋反射增益")
    print("=" * 80)

    on = run(frozen=False)
    fr = run(frozen=True)

    e2 = on["e1"] - fr["e1"]
    sg_asym = abs(on["sgL"] - on["sgR"]) / max(abs(on["sgL"]), 1e-9)

    print("\n" + "=" * 80)
    print("  对照判定")
    print("=" * 80)
    print(f"  {'指标':<26} | {'ON':>10} | {'FROZEN':>10}")
    print("  " + "-" * 52)
    print(f"  {'E1 gain调制(hungry-full)':<22} | {on['e1']:>10.3f} | {fr['e1']:>10.3f}")
    print(f"  {'gain hungry':<24} | {on['gh']:>10.3f} | {fr['gh']:>10.3f}")
    print(f"  {'gain full':<25} | {on['gf']:>10.3f} | {fr['gf']:>10.3f}")
    print(f"  {'w_hunger_gate':<24} | {on['w']:>10.4f} | {fr['w']:>10.4f}")
    print()

    E1 = on["e1"] > 0.3
    E2 = e2 > 0.1
    E3 = on["w"] > 0.05
    E4 = sg_asym < 0.05

    print(f"  E1 上下文调制 (gain差>0.3):        {'PASS' if E1 else 'FAIL'}  ({on['e1']:.3f})")
    print(f"  E2' 差分因果 (ON−FROZEN>0.1):      {'PASS' if E2 else 'FAIL'}  ({e2:.3f})")
    print(f"  E3 权重分化 (w>0.05):              {'PASS' if E3 else 'FAIL'}  ({on['w']:.4f})")
    print(f"  E4 对称性 (|sgL−sgR|<5%):          {'PASS' if E4 else 'FAIL'}  ({sg_asym*100:.2f}%)")
    print(f"\n  总计: {sum([E1, E2, E3, E4])}/4 PASS")
    if E1 and E2 and E3:
        print("  → 增益调制涌现：hunger 门控热趋增益，且调制由学习增强(非仅先天泄漏)。死锁二 MVE 成立。")
    elif E1 and not E2:
        print("  → 调制存在但主要来自先天泄漏，学习增量不足。需诊断学习/门标定。")
    print("=" * 80)


if __name__ == '__main__':
    main()
