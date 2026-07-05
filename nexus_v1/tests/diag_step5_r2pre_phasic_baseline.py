"""
Step 5 R2-Pre：slow_relay τ 修改前基线记录

测量当前 phasic 尾流时长（τ=5000 步），作为 τ=15000 修改后的对比基准。

指标：
  - 热前锋通过时 phasic 正向峰值
  - 峰值后回落到 0.01 以下的步数（=尾流长度）
  - 对比双侧 slow_relay 电压是否对称（偏差 < 10% → 修改双侧才是安全的）

运行：
  PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.diag_step5_r2pre_phasic_baseline
"""
import sys, os, math, statistics
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit

N_STEPS      = 20_000
REPORT_EVERY = 2_000
POS_THRESH   = 0.01   # phasic "活跃"阈值

def run():
    print("=== Step 5 R2-Pre：phasic 尾流基线（τ=5000 步，当前值）===\n")
    c = VariantCircuit()
    print(f"  slow_relay r_leak = {c.slow_relay_left.config.r_leak}（当前 τ ≈ {int(c.slow_relay_left.config.r_leak)} 步）\n")

    phasic_l_hist  = []
    phasic_r_hist  = []
    slow_l_hist    = []
    slow_r_hist    = []
    relay_l_hist   = []
    relay_r_hist   = []

    print(f"{'Step':>7}  {'ph_L':>8}  {'ph_R':>8}  {'slow_L':>8}  {'slow_R':>8}  {'relay_L':>8}  {'relay_R':>8}")
    print("-" * 72)

    for step in range(N_STEPS):
        c.step({}, dt=1.0)

        pl = c.phasic_left.activation
        pr = c.phasic_right.activation
        sl = c.slow_relay_left._membrane.voltage
        sr = c.slow_relay_right._membrane.voltage

        # relay neurons: thermo_relay_left / thermo_relay_right (or similar)
        rl = getattr(c, 'relay_left',  None)
        rr = getattr(c, 'relay_right', None)
        rl_v = rl._membrane.voltage if rl else 0.0
        rr_v = rr._membrane.voltage if rr else 0.0

        phasic_l_hist.append(pl)
        phasic_r_hist.append(pr)
        slow_l_hist.append(sl)
        slow_r_hist.append(sr)
        relay_l_hist.append(rl_v)
        relay_r_hist.append(rr_v)

        if (step + 1) % REPORT_EVERY == 0:
            print(f"{step+1:>7}  {pl:>8.4f}  {pr:>8.4f}  {sl:>8.4f}  {sr:>8.4f}  {rl_v:>8.4f}  {rr_v:>8.4f}")

    # ── 尾流分析 ──
    def tail_length(hist, thresh=POS_THRESH):
        """找所有正向峰（> thresh）后回落时长"""
        tails = []
        in_peak = False
        peak_end = None
        for i, v in enumerate(hist):
            if not in_peak and v >= thresh:
                in_peak = True
            elif in_peak and v < thresh:
                if peak_end is not None:
                    tails.append(i - peak_end)
                peak_end = i
                in_peak = False
        return tails

    tails_l = tail_length(phasic_l_hist)
    tails_r = tail_length(phasic_r_hist)

    all_phasic_pos = [v for v in phasic_l_hist + phasic_r_hist if v > POS_THRESH]
    p_max = max(phasic_l_hist + phasic_r_hist) if phasic_l_hist else 0.0

    # 对称性检验
    slow_diff = [abs(l - r) for l, r in zip(slow_l_hist, slow_r_hist)]
    slow_mean_l = statistics.mean(slow_l_hist)
    slow_mean_r = statistics.mean(slow_r_hist)
    asym = abs(slow_mean_l - slow_mean_r) / max(slow_mean_l + slow_mean_r, 1e-6)

    print("\n" + "=" * 60)
    print("== 基线测量结果 ==\n")
    print(f"当前 slow_relay r_leak = {c.slow_relay_left.config.r_leak}")
    print(f"  τ ≈ C × r_leak = {c.slow_relay_left.config.capacitance} × {c.slow_relay_left.config.r_leak} = {c.slow_relay_left.config.capacitance * c.slow_relay_left.config.r_leak:.0f} 步")
    print()
    print(f"Phasic 正向峰值 (> {POS_THRESH}):")
    print(f"  最大值: {p_max:.5f}")
    print(f"  Left 尾流段数: {len(tails_l)}  均值长度: {statistics.mean(tails_l):.0f} 步" if tails_l else f"  Left 无正向峰")
    print(f"  Right 尾流段数: {len(tails_r)}  均值长度: {statistics.mean(tails_r):.0f} 步" if tails_r else f"  Right 无正向峰")
    print()
    print(f"slow_relay 对称性:")
    print(f"  Left 均值: {slow_mean_l:.5f}  Right 均值: {slow_mean_r:.5f}")
    print(f"  不对称率: {asym*100:.2f}%  {'✓ < 10%，双侧同步修改安全' if asym < 0.1 else '⚠ > 10%，需分析原因'}")
    print()
    print(f"R2-Pre 结论：")
    print(f"  Step 5 修改参考：r_leak 5000 → 15000（τ 5000 → 15000 步）")
    print(f"  修改后验收标准：phasic 尾流约延长 3×（{int(statistics.mean(tails_l or [0]) * 3)} 步）")
    print(f"  对称性要求：双侧 slow_relay 同时修改，禁止单侧！")

if __name__ == '__main__':
    run()
