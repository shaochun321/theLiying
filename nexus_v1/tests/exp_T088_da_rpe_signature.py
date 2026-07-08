"""
T-088: DA 的 RPE signature 验证 — 确认重标后 DA 编码奖励预测误差

背景：DA 源重标（commit 928d92a）把 DA 从钉死 1.0 恢复为动态。本测试验证 DA 现在
      符合 Schultz 1997 的 RPE 极性签名，而非饱和直流。

四条件（世界受控切换）：
  A 静息（无源）      → DA ≈ baseline(0.09)     无奖励、无预测误差
  B 新奇奖励（源出现）→ DA 相位爆发 > 0.4        正向 RPE（预期外奖励）
  C 稳态奖励（贴源饱）→ DA 回落至 0.1~0.3        预期内奖励，无新信息
  D 奖励缺失（撤源）  → DA dip，低于 C           负向 RPE（预期落空）

判定：
  S1 静息 DA ∈ [0.03, 0.25]（非 0 非 1）
  S2 新奇爆发 DA_peak > 静息 + 0.2（相位爆发存在）
  S3 撤源 dip：DA_D_mean < DA_C_mean（奖励缺失使 DA 下降）
  S4 全程非饱和：DA 不长时间钉在 1.0（railed 比例 < 30%）
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

DT = 1.0
PA = 4_000    # 静息结束
PB = 14_000   # 新奇奖励接近结束
PC = 26_000   # 稳态奖励结束
PD = 34_000   # 撤源结束
LOG = 2_000

FAR = [500.0, 500.0, 500.0]   # 远到无热贡献 = 等效无源
SRC = [70.0, 50.0, 25.0]
BODY = [10.0, 50.0, 25.0]


def main():
    print("=" * 84)
    print("  T-088: DA 的 RPE signature 验证（重标后）")
    print("=" * 84)

    # 起始：源放极远（等效无源静息）
    src = HeatSource(position=list(FAR), energy=500_000.0, temperature=5.0, radius=30.0)
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

    rec = {'A': [], 'B': [], 'C': [], 'D': []}
    railed = 0

    print(f"  {'Step':>6} | {'Ph':>2} | {'DA':>6} | {'fill':>5} | {'dist':>6} | note")
    print("  " + "-" * 56)

    for step in range(1, PD + 1):
        # 相位切换
        if step == PA:
            src.position = list(SRC)      # 源出现（新奇奖励）
        if step == PC:
            src.energy = 0.0              # 撤源（奖励缺失）
            src.temperature = 0.0

        c.step({}, DT)
        da = c.dopamine.concentration
        if da >= 0.999:
            railed += 1
        fill = c.energy_store.fill_fraction
        pos = c.world.body.position
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(pos, src.position)))

        ph = 'A' if step < PA else ('B' if step < PB else ('C' if step < PC else 'D'))
        rec[ph].append(da)

        if step % LOG == 0 or step in (PA, PA + 2, PC, PC + 2):
            note = {'A': '静息无源', 'B': '新奇奖励', 'C': '稳态贴源', 'D': '撤源'}[ph]
            print(f"  {step:>6} | {ph:>2} | {da:>6.3f} | {fill:>5.3f} | {dist:>6.1f} | {note}")

    def stats(xs):
        if not xs:
            return (float('nan'),) * 3
        return (min(xs), sum(xs) / len(xs), max(xs))

    a_min, a_mean, a_max = stats(rec['A'])
    b_min, b_mean, b_max = stats(rec['B'])
    c_min, c_mean, c_max = stats(rec['C'])
    d_min, d_mean, d_max = stats(rec['D'])
    railed_pct = railed / PD * 100

    print("\n  分条件 DA 统计 (min/mean/max):")
    print(f"    A 静息:     {a_min:.3f}/{a_mean:.3f}/{a_max:.3f}")
    print(f"    B 新奇奖励: {b_min:.3f}/{b_mean:.3f}/{b_max:.3f}")
    print(f"    C 稳态贴源: {c_min:.3f}/{c_mean:.3f}/{c_max:.3f}")
    print(f"    D 撤源:     {d_min:.3f}/{d_mean:.3f}/{d_max:.3f}")
    print(f"    railed(DA≥0.999) 占比: {railed_pct:.1f}%")

    s1 = 0.03 <= a_mean <= 0.25
    s2 = b_max > a_mean + 0.2
    s3 = d_mean < c_mean
    s4 = railed_pct < 30.0

    print("\n  === 判定 ===")
    print(f"  S1 静息 DA∈[0.03,0.25] (非0非1):     {'PASS' if s1 else 'FAIL'}  (A_mean={a_mean:.3f})")
    print(f"  S2 新奇爆发 > 静息+0.2 (相位爆发):    {'PASS' if s2 else 'FAIL'}  (B_max={b_max:.3f} vs {a_mean+0.2:.3f})")
    print(f"  S3 撤源 dip: D_mean < C_mean:         {'PASS' if s3 else 'FAIL'}  ({d_mean:.3f} < {c_mean:.3f})")
    print(f"  S4 全程非饱和 (railed<30%):           {'PASS' if s4 else 'FAIL'}  ({railed_pct:.1f}%)")
    print(f"\n  总计: {sum([s1, s2, s3, s4])}/4 PASS")
    if all([s1, s2, s3, s4]):
        print("  → DA 恢复 RPE 编码：新奇→爆发，稳态→回落，缺失→dip。总闸门打开。")
    print("=" * 84)


if __name__ == '__main__':
    main()
