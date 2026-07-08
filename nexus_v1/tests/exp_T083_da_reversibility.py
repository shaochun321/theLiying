"""
T-083: DA 可逆性对照实验 — 验证"DA=1.0 修订版方案"Fix-2 是否把 DA 钉死

背景：《DA=1.0 根因诊断与修复方案（修订版）》提出 Fix-2：
      satiety_to_da 的 synapse_gain -1.0 → -5.0, initial_weight 0.3 → 1.0，
      并声称"贴源静止 fill=1 时 DA≈0.01，远离源 fill<0.5 时 DA≈0.07"。

质疑（本实验验证）：
  1. DA 浓度 = clamp(mean(da_neuron.activation), 0, 1)（variant_adapter.py:2224-2225），
     modulator baseline=0.1 被旁路。净负输入 → DA 精确为 0.0，不是 0.01。
  2. satiety 输入受 intake_sensor 慢电容（τ≈5000）主导，撤源后 5000+ 步仍在放电。
     sg=-5.0 使该残余在"再动员窗口"往 DA 灌约 -1.0，淹没 +0.30 bc 托底 → DA≡0。
  3. 结果：撤源后 DA 无法回升 → 身体无法被重新驱动去找新源 → 跨周期学习被摧毁。

实验设计（三段，两条件对照）：
  Phase 1 (0~PH1):      贴源饱腹     — fill↑, satiety↑, DA 应从接近期高 → 饱和期回落
  Phase 2 (PH1~PH2):    撤源再动员   — fill↓, hunger↑, DA 应回升（可逆性关键窗口）
  Phase 3 (PH2~PH3):    新源重现     — body 应重新接近, DA 应支持学习

对照：
  A. baseline: satiety sg=-1.0, w=0.3（当前母本）
  B. fix2:     satiety sg=-5.0, w=1.0（修订版方案）— 实例级 mutate，不改母本

判定：
  R1 baseline 撤源后 DA 回升 > baseline(0.1)     — 证明当前系统可逆
  R2 fix2 撤源后 DA_min 显著低于 baseline         — 证明 Fix-2 压制再动员
  R3 fix2 DA 在再动员窗口是否被钉在 ~0            — 核心质疑证实
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

DT   = 1.0
PH1  = 30_000    # 贴源饱腹结束
PH2  = 50_000    # 再动员窗口结束
PH3  = 60_000    # 新源重现结束
LOG  = 5_000

SRC_POS_1  = [70.0, 50.0, 25.0]
SRC_POS_2  = [30.0, 50.0, 25.0]   # 新源在身体另一侧，需重新导航
BODY_START = [10.0, 50.0, 25.0]
SRC_ENERGY = 500_000.0


def apply_fix2(c):
    """实例级施加修订版 Fix-2：satiety_to_da sg=-5.0, w=1.0。不改母本。"""
    b = c.bundle_satiety_to_da
    b.config.synapse_gain = -5.0
    b.config.weight_max = 1.0
    for row in b._memristors:
        for m in row:
            m.w = 1.0
    return b.mean_weight()


def nearest_dist(c):
    pos = c.world.body.position
    best = float('inf')
    for src in c.world.heat_sources:
        if src.alive:
            d = math.sqrt(sum((pos[i] - src.position[i]) ** 2 for i in range(3)))
            best = min(best, d)
    return best


def run(condition):
    """condition ∈ {'baseline', 'fix2'}. 返回逐段 DA/satiety/fill 记录。"""
    src1 = HeatSource(position=list(SRC_POS_1), energy=SRC_ENERGY,
                      temperature=5.0, radius=30.0)
    src1._drift = [0.0, 0.0, 0.0]
    body  = Body(position=list(BODY_START))
    world = World(heat_sources=[src1], body=body)
    world.MIN_ALIVE  = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world
    c.somatosensory.LATERAL_GAIN = 0.3
    for mn in c.motor_neurons.values():
        mn.config.output_gain = 0.1

    print(f"\n{'='*78}")
    print(f"  条件: {condition}"
          + ("  (satiety_to_da: sg=-5.0, w=1.0 修订版 Fix-2)" if condition == 'fix2'
             else "  (satiety_to_da: sg=-1.0, w=0.3 母本默认)"))
    print(f"{'='*78}")
    _fix2_applied = False
    hdr = (f"  {'Step':>6} | {'Ph':>2} | {'DA':>6} | {'sat_act':>7} | "
           f"{'satDA_I':>7} | {'fill':>5} | {'dist':>6} | {'n_src':>5}")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    rec = {'phase2_da': [], 'phase3_da': [], 'phase1_tail_da': []}
    src2_added = False

    for step in range(1, PH3 + 1):
        # ── 段切换 ──
        if step == PH1:
            for s in list(world.heat_sources):
                if s.alive:
                    s.energy = 0.0
                    s.temperature = 0.0
        if step == PH2 and not src2_added:
            src2 = HeatSource(position=list(SRC_POS_2), energy=SRC_ENERGY,
                              temperature=5.0, radius=30.0)
            src2._drift = [0.0, 0.0, 0.0]
            world.heat_sources.append(src2)
            src2_added = True

        c.step({}, DT)

        # satiety_to_da 是 lazy 初始化（首次 step 内建），故在此延迟施加 Fix-2
        if condition == 'fix2' and not _fix2_applied and c.bundle_satiety_to_da is not None:
            _w = apply_fix2(c)
            print(f"    [step {step}] Fix-2 施加: satiety_to_da sg=-5.0, mean_w={_w:.3f}")
            _fix2_applied = True

        da   = c.dopamine.concentration
        sact = c.satiety_neuron.activation
        # satiety→DA 注入电流（frozen 束，只读重算；无 STDP 副作用）
        _sat_cur = c.bundle_satiety_to_da.propagate()
        satDA_I  = _sat_cur[0] if _sat_cur else 0.0
        fill = c.energy_store.fill_fraction
        dist = nearest_dist(c)
        n_src = sum(1 for s in world.heat_sources if s.alive)

        if PH1 - 3000 <= step < PH1:
            rec['phase1_tail_da'].append(da)
        if PH1 <= step < PH2:
            rec['phase2_da'].append(da)
        if PH2 <= step < PH3:
            rec['phase3_da'].append(da)

        if step % LOG == 0 or step == PH1 or step == PH2:
            ph = 1 if step < PH1 else (2 if step < PH2 else 3)
            print(f"  {step:>6} | P{ph:1d} | {da:>6.4f} | {sact:>7.4f} | "
                  f"{satDA_I:>+7.3f} | {fill:>5.3f} | {dist:>6.1f} | {n_src:>5d}")

    def _stats(xs):
        if not xs:
            return (float('nan'), float('nan'), float('nan'))
        return (min(xs), sum(xs) / len(xs), max(xs))

    p1_min, p1_mean, p1_max = _stats(rec['phase1_tail_da'])
    p2_min, p2_mean, p2_max = _stats(rec['phase2_da'])
    p3_min, p3_mean, p3_max = _stats(rec['phase3_da'])
    final_dist = nearest_dist(c)

    print(f"\n  [{condition}] 分段 DA 统计:")
    print(f"    Phase1 尾段(饱腹): DA min/mean/max = {p1_min:.4f}/{p1_mean:.4f}/{p1_max:.4f}")
    print(f"    Phase2 (撤源再动员): DA min/mean/max = {p2_min:.4f}/{p2_mean:.4f}/{p2_max:.4f}")
    print(f"    Phase3 (新源重现): DA min/mean/max = {p3_min:.4f}/{p3_mean:.4f}/{p3_max:.4f}")
    print(f"    Phase3 末 body→最近源距离: {final_dist:.1f}")

    return {
        'condition': condition,
        'p1': (p1_min, p1_mean, p1_max),
        'p2': (p2_min, p2_mean, p2_max),
        'p3': (p3_min, p3_mean, p3_max),
        'final_dist': final_dist,
    }


def main():
    print("=" * 78)
    print("  T-083: DA 可逆性对照实验 — Fix-2 是否把 DA 钉死于再动员窗口")
    print("=" * 78)

    base = run('baseline')
    fix2 = run('fix2')

    BASELINE = 0.1  # modulator baseline
    print("\n" + "=" * 78)
    print("  对照判定")
    print("=" * 78)
    print(f"\n  {'指标':<32} | {'baseline':>12} | {'fix2':>12}")
    print("  " + "-" * 62)
    print(f"  {'Phase2 撤源再动员 DA_mean':<28} | {base['p2'][1]:>12.4f} | {fix2['p2'][1]:>12.4f}")
    print(f"  {'Phase2 撤源再动员 DA_min':<29} | {base['p2'][0]:>12.4f} | {fix2['p2'][0]:>12.4f}")
    print(f"  {'Phase3 新源重现 DA_mean':<29} | {base['p3'][1]:>12.4f} | {fix2['p3'][1]:>12.4f}")
    print(f"  {'Phase3 末 body→源距离':<30} | {base['final_dist']:>12.1f} | {fix2['final_dist']:>12.1f}")

    # R1: baseline 撤源后 DA 能回升到 > baseline
    r1 = base['p2'][2] > BASELINE
    # R2: fix2 撤源期 DA_mean 显著低于 baseline 条件
    r2 = fix2['p2'][1] < base['p2'][1] * 0.5
    # R3: fix2 撤源期 DA 被钉在 ~0（min < 0.02 且 mean < 0.05）
    r3 = fix2['p2'][0] < 0.02 and fix2['p2'][1] < 0.05

    print()
    print(f"  R1 baseline 撤源后 DA 可回升>{BASELINE} (系统可逆):  "
          f"{'PASS ✅' if r1 else 'FAIL ❌'}  (p2_max={base['p2'][2]:.4f})")
    print(f"  R2 fix2 撤源期 DA_mean < baseline条件×0.5:      "
          f"{'PASS ✅' if r2 else 'FAIL ❌'}  ({fix2['p2'][1]:.4f} vs {base['p2'][1]*0.5:.4f})")
    print(f"  R3 fix2 撤源期 DA 被钉在~0 (核心质疑证实):      "
          f"{'PASS ✅' if r3 else 'FAIL ❌'}  (min={fix2['p2'][0]:.4f}, mean={fix2['p2'][1]:.4f})")
    print()
    if r2 and r3:
        print("  → 结论：Fix-2 在再动员窗口把 DA 压制/钉零，可逆性被破坏。质疑成立。")
    elif r1 and not r2:
        print("  → 结论：Fix-2 未显著压制 DA，质疑不成立（需复核参数生效）。")
    print("=" * 78)


if __name__ == '__main__':
    main()
