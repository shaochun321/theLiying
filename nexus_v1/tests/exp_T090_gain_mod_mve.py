"""
T-090: 死锁二增益调制 MVE 验证 — hunger 门控热趋反射增益

验证 GatedReflexArc（commit 待定）：hunger 上下文经 DA-gated STDP 学到增益指令，
经 MOSFET 物理乘法调制 thermo→yaw 反射的 synapse_gain。

两条件对照（除 frozen 标志外完全相同）：
  ON     : gate 学习开启
  FROZEN : gate 学习冻结（权重停初值 0，仅 Memristor G(0) 泄漏）— E2' 差分基线

判定（方案 v2 §9.5）：
  E1  上下文调制: mean gain(hungry, fill<0.5) − mean gain(full, fill>0.85) > 0.3
  E2' 差分因果:   E1(ON) − E1(FROZEN) > 0.1   （学习增量, 隔离先天泄漏+hunger→DA 直接路径）
  E3  权重分化:   w_hunger_gate(ON) > 0.05
  E4  对称性:     |sg_L − sg_R| < 5%  （单一全局门, 应为 0）
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.gain_mod_adapter import GainModCircuit
from nexus_v1.components.world import HeatSource, Body, World

DT = 1.0
STEPS = 60_000
LOG = 10_000

SRC = [70.0, 50.0, 25.0]
BODY = [10.0, 50.0, 25.0]


def nearest_dist(c):
    pos = c.world.body.position
    best = float('inf')
    for s in c.world.heat_sources:
        if s.alive:
            best = min(best, math.sqrt(sum((pos[i] - s.position[i]) ** 2 for i in range(3))))
    return best


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
    # 起始半饥饿, 促成觅食循环
    c.energy_store._cap.charge = c.energy_store.config.capacity * 0.3

    tag = "FROZEN" if frozen else "ON"
    print(f"\n{'='*80}\n  条件: gate-{tag}\n{'='*80}")
    print(f"  {'Step':>6} | {'gain':>5} | {'m_gate':>6} | {'w':>7} | {'hunger':>6} | "
          f"{'fill':>5} | {'dist':>6}")
    print("  " + "-" * 62)

    gain_hungry, n_hungry = 0.0, 0
    gain_full, n_full = 0.0, 0

    for step in range(1, STEPS + 1):
        c.step({}, DT)
        s = c.gate_state()
        fill = c.energy_store.fill_fraction
        # 只在后 2/3(学习后)统计增益调制
        if step > STEPS // 3:
            if fill < 0.5:
                gain_hungry += s["gain"]; n_hungry += 1
            elif fill > 0.85:
                gain_full += s["gain"]; n_full += 1

        if step % LOG == 0:
            print(f"  {step:>6} | {s['gain']:>5.3f} | {s['m_gate']:>6.3f} | "
                  f"{s['w_hunger_gate']:>7.4f} | {c.hypothalamus_hunger.activation:>6.3f} | "
                  f"{fill:>5.3f} | {nearest_dist(c):>6.1f}")

    gh = gain_hungry / max(n_hungry, 1)
    gf = gain_full / max(n_full, 1)
    e1 = gh - gf
    sgL = c.bundle_left_to_yaw.config.synapse_gain
    sgR = c.bundle_right_to_yaw.config.synapse_gain
    w = c.gate_state()["w_hunger_gate"]

    print(f"\n  [gate-{tag}] gain(hungry,fill<0.5)={gh:.3f} (n={n_hungry})  "
          f"gain(full,fill>0.85)={gf:.3f} (n={n_full})")
    print(f"  [gate-{tag}] E1 调制幅度 = {e1:.3f}   w_hunger_gate={w:.4f}   "
          f"sg_L={sgL:.4f} sg_R={sgR:.4f}")
    return {"e1": e1, "gh": gh, "gf": gf, "w": w, "sgL": sgL, "sgR": sgR}


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
    print(f"  {'指标':<28} | {'ON':>10} | {'FROZEN':>10}")
    print("  " + "-" * 54)
    print(f"  {'E1 gain调制幅度':<24} | {on['e1']:>10.3f} | {fr['e1']:>10.3f}")
    print(f"  {'w_hunger_gate':<26} | {on['w']:>10.4f} | {fr['w']:>10.4f}")
    print()

    E1 = on["e1"] > 0.3
    E2 = e2 > 0.1
    E3 = on["w"] > 0.05
    E4 = sg_asym < 0.05

    print(f"  E1 上下文调制 (ON gain差>0.3):     {'PASS' if E1 else 'FAIL'}  ({on['e1']:.3f})")
    print(f"  E2' 差分因果 (ON−FROZEN>0.1):      {'PASS' if E2 else 'FAIL'}  ({e2:.3f})")
    print(f"  E3 权重分化 (w>0.05):              {'PASS' if E3 else 'FAIL'}  ({on['w']:.4f})")
    print(f"  E4 对称性 (|sgL−sgR|<5%):          {'PASS' if E4 else 'FAIL'}  ({sg_asym*100:.2f}%)")
    print(f"\n  总计: {sum([E1, E2, E3, E4])}/4 PASS")
    if E1 and E2 and E3:
        print("  → 增益调制涌现：hunger 门控热趋增益，且调制由学习增强(非仅先天泄漏)。")
    elif E1 and not E2:
        print("  → 警告：调制存在但主要来自先天泄漏，学习增量不足。需诊断学习/门标定。")
    print("=" * 80)


if __name__ == '__main__':
    main()
