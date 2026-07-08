"""
T-089: 热趋性保全验证 — DA 源重标是否破坏了原本在工作的学习/行为

关键风险：DA 从"钉死 1.0"降到"动态 0.06~1.0"。DA 门控 STDP (LTP=elig×E×DA_ema)。
         DA 变低可能削弱 relay/D1 束的权重分化，退化热趋性。本测试确认没有退化。

对比基线（重标前，DA≡1.0 时）:
  T-036 (200k): |Δw|=0.2991, DR5%=60%, 体到达热源
  T-072 (200k): w_ccw→0.30

设计：100k 单源，body[10,50,25] → src[70,50,25]。追踪：
  - approach_step（首次进入源区 dist<30）
  - D1 权重 w_ccw/w_cw 分化 |Δw|
  - DR5%（patch温差·速度方向符号）
  - DA 分布（确认动态而非饱和）

判定（保全 = 不比重标前差）:
  P1 体到达热源 (approach_step 存在)
  P2 D1 权重分化 |Δw| > 0.05 (STDP 学习存活)
  P3 DR5% ≥ 50% (方向性不退化到随机以下)
  P4 DA 动态 (railed<50% 且 mean∈[0.1,0.9]) — 确认在有意义区间学习
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

DT = 1.0
STEPS = 100_000
LOG = 10_000

SRC = [70.0, 50.0, 25.0]
BODY = [10.0, 50.0, 25.0]


def get_d1_weights(c):
    w_ccw = w_cw = float('nan')
    bl = getattr(c, 'bundle_d1_phasic_left_to_spinal_ccw', None)
    br = getattr(c, 'bundle_d1_phasic_right_to_spinal_cw', None)
    if bl and bl._memristors:
        w_ccw = bl._memristors[0][0].w
    if br and br._memristors:
        w_cw = br._memristors[0][0].w
    return w_ccw, w_cw


def get_dr5(c):
    pT = c._patch_temps if hasattr(c, '_patch_temps') else {}
    T = {pid: pT.get(pid, (0.0,))[0] for pid in ['front', 'back', 'left', 'right']}
    vx = c.world.body.velocity[0]
    vy = c.world.body.velocity[1]
    gx = T.get('right', 0.0) - T.get('left', 0.0)
    gy = T.get('front', 0.0) - T.get('back', 0.0)
    return (gx * vx + gy * vy) > 0.0


def nearest_dist(c):
    pos = c.world.body.position
    best = float('inf')
    for src in c.world.heat_sources:
        if src.alive:
            best = min(best, math.sqrt(sum((pos[i] - src.position[i]) ** 2 for i in range(3))))
    return best


def main():
    print("=" * 88)
    print("  T-089: 热趋性保全验证（DA 重标后 100k）")
    print("  基线对比: T-036 |Δw|=0.299/DR5=60%/到源")
    print("=" * 88)

    src = HeatSource(position=list(SRC), energy=500_000.0, temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=list(BODY))
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world
    c.somatosensory.LATERAL_GAIN = 0.3
    for mn in c.motor_neurons.values():
        mn.config.output_gain = 0.1

    w0_ccw, w0_cw = get_d1_weights(c)
    approach_step = None
    dr5_count = 0
    da_sum = 0.0
    da_railed = 0

    print(f"\n  初始 D1: w_ccw={w0_ccw:.4f} w_cw={w0_cw:.4f}\n")
    print(f"  {'Step':>7} | {'DA':>6} | {'w_ccw':>7} {'w_cw':>7} {'|Dw|':>6} | "
          f"{'DR5%':>5} | {'dist':>6} | {'fill':>5}")
    print("  " + "-" * 68)

    for step in range(1, STEPS + 1):
        c.step({}, DT)

        da = c.dopamine.concentration
        da_sum += da
        if da >= 0.999:
            da_railed += 1
        if get_dr5(c):
            dr5_count += 1
        dist = nearest_dist(c)
        if approach_step is None and dist < 30.0:
            approach_step = step

        if step % LOG == 0:
            w_ccw, w_cw = get_d1_weights(c)
            dw = abs(w_ccw - w_cw) if not math.isnan(w_ccw) else 0.0
            print(f"  {step:>7} | {da:>6.3f} | {w_ccw:>7.4f} {w_cw:>7.4f} {dw:>6.4f} | "
                  f"{dr5_count/step*100:>4.1f}% | {dist:>6.1f} | {c.energy_store.fill_fraction:>5.3f}")

    w_ccw, w_cw = get_d1_weights(c)
    dw_final = abs(w_ccw - w_cw) if not math.isnan(w_ccw) else 0.0
    dr5_pct = dr5_count / STEPS * 100
    da_mean = da_sum / STEPS
    railed_pct = da_railed / STEPS * 100

    print("\n  === 最终 ===")
    print(f"  approach_step: {approach_step if approach_step else '未到达'}")
    print(f"  w_ccw: {w0_ccw:.4f}→{w_ccw:.4f}  w_cw: {w0_cw:.4f}→{w_cw:.4f}  |Δw|={dw_final:.4f}")
    print(f"  DR5%={dr5_pct:.1f}%  DA_mean={da_mean:.3f}  railed={railed_pct:.1f}%")

    p1 = approach_step is not None
    p2 = dw_final > 0.05
    p3 = dr5_pct >= 50.0
    p4 = railed_pct < 50.0 and 0.1 <= da_mean <= 0.9

    print("\n  === 判定（保全 = 不比重标前差）===")
    print(f"  P1 体到达热源:              {'PASS' if p1 else 'FAIL'}  (approach={approach_step})")
    print(f"  P2 D1权重分化 |Δw|>0.05:    {'PASS' if p2 else 'FAIL'}  (|Δw|={dw_final:.4f})")
    print(f"  P3 DR5% ≥ 50%:              {'PASS' if p3 else 'FAIL'}  ({dr5_pct:.1f}%)")
    print(f"  P4 DA 动态且在学习区间:     {'PASS' if p4 else 'FAIL'}  (mean={da_mean:.3f}, railed={railed_pct:.1f}%)")
    print(f"\n  总计: {sum([p1, p2, p3, p4])}/4 PASS")
    if all([p1, p2, p3, p4]):
        print("  → 热趋性保全：DA 重标未破坏学习/行为，且 DA 现在在动态区间门控 STDP。")
    elif not p2:
        print("  → 警告：权重分化退化，DA 变低可能削弱了 LTP。需诊断 phasic 期 DA_ema。")
    print("=" * 88)


if __name__ == '__main__':
    main()
