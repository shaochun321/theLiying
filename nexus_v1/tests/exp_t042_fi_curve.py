"""T-042: F-I 曲线诊断 + Ia 互抑对照扫描

目的：量化 D1 bundle 权重 → spinal 激活 → yaw 激活的传递函数，
     以及 Step 6 Ia 互抑束对该传递函数的压制比例。

设计：
  扫描 A（有 Ia）：Ia 互抑束保持默认（sg=-1.0, w=0.1）
  扫描 B（无 Ia）：Ia 互抑束权重归零（实验脚本内动态修改，不改母本）

  D1 bundle 在扫描期间冻结于目标权重（learning_rule='frozen'），
  确保 STDP 不在诊断期间改变权重，获得干净的静态 F-I 曲线。

  每个配置：8k步（前2k热身，后6k统计均值/峰值）
  自然热场驱动 phasic 信号（与 T-038 相同的热源设置）

输出：
  - 两组 F-I 曲线表格
  - rheobase_A（有 Ia 时 spinal>0.05 的最低 D1 权重）
  - rheobase_B（无 Ia 时 spinal>0.05 的最低 D1 权重）
  - suppression_ratio = rheobase_A / rheobase_B（Ia压制倍数）
  - 是否当前 w=0.1 已处于饱和区
"""

from __future__ import annotations
import sys, os, time, math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.stdout.reconfigure(line_buffering=True)

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

WARMUP  = 2_000
MEASURE = 6_000
TOTAL   = WARMUP + MEASURE
DT      = 1.0

# 与 T-038 相同的热场设置（已知 phasic 信号稳定产生）
SRC_POS  = [70.0, 50.0, 25.0]
BODY_POS = [10.0, 50.0, 25.0]

# D1 权重扫描范围
W_LIST = [0.001, 0.003, 0.005, 0.010, 0.020, 0.050, 0.100, 0.200, 0.300]

# spinal 激活阈值：超过此值认为"开始点火"
FIRE_THRESHOLD = 0.05


def build_world():
    src  = HeatSource(position=SRC_POS[:], energy=50_000.0,
                      temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=BODY_POS[:])
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE  = 0
    world.REGEN_PROB = 0.0
    return world


def run_one(w_d1: float, disable_ia: bool) -> dict:
    """一个配置的完整运行，返回统计数据。"""
    world = build_world()
    c = VariantCircuit()
    c.world = world
    # 充满能量，避免饱腹/饥饿影响（纯诊断模式）
    c.energy_store._cap.charge = c.energy_store.config.capacity * 0.8
    c.somatosensory.LATERAL_GAIN = 0.3
    for m in c.muscle_system.muscles:
        m.gain = 0.3

    # ── 固定 D1 权重（冻结于目标值，STDP 停用）──────────────────────────
    for b in [c.bundle_d1_phasic_left_to_spinal_ccw,
              c.bundle_d1_phasic_right_to_spinal_cw]:
        for row in b._memristors:
            for mem in row:
                mem.w = w_d1
        b.config.learning_rule = 'frozen'
        b.config.weight_max    = w_d1

    # ── 可选：禁用 Ia 互抑束 ─────────────────────────────────────────────
    if disable_ia:
        for b in [c.bundle_spinal_ccw_to_cw, c.bundle_spinal_cw_to_ccw]:
            for row in b._memristors:
                for mem in row:
                    mem.w = 0.0   # Ia 权重归零；frozen 本身不变（无 STDP）

    # ── 运行 ─────────────────────────────────────────────────────────────
    sp_ccw_vals, sp_cw_vals  = [], []
    yaw_ccw_vals, yaw_cw_vals = [], []
    phasic_l_vals, phasic_r_vals = [], []

    for step in range(TOTAL):
        c.step({}, DT)
        if step >= WARMUP:
            sp_ccw_vals.append(c.spinal_ccw.activation)
            sp_cw_vals.append(c.spinal_cw.activation)
            yaw_ccw_vals.append(c.yaw_ccw_neuron.activation)
            yaw_cw_vals.append(c.yaw_cw_neuron.activation)
            phasic_l_vals.append(c.phasic_left.activation)
            phasic_r_vals.append(c.phasic_right.activation)

    def stats(vals):
        if not vals:
            return 0.0, 0.0
        return sum(vals) / len(vals), max(abs(v) for v in vals)

    sp_ccw_mean, sp_ccw_peak  = stats(sp_ccw_vals)
    sp_cw_mean,  sp_cw_peak   = stats(sp_cw_vals)
    yaw_ccw_mean, yaw_ccw_peak = stats(yaw_ccw_vals)
    yaw_cw_mean,  yaw_cw_peak  = stats(yaw_cw_vals)
    pl_mean, pl_peak = stats(phasic_l_vals)
    pr_mean, pr_peak = stats(phasic_r_vals)

    return {
        'w_d1':       w_d1,
        'ia_off':     disable_ia,
        'sp_ccw_mean': sp_ccw_mean, 'sp_ccw_peak': sp_ccw_peak,
        'sp_cw_mean':  sp_cw_mean,  'sp_cw_peak':  sp_cw_peak,
        'yaw_ccw_mean': yaw_ccw_mean, 'yaw_ccw_peak': yaw_ccw_peak,
        'yaw_cw_mean':  yaw_cw_mean,  'yaw_cw_peak':  yaw_cw_peak,
        'pl_mean': pl_mean, 'pl_peak': pl_peak,
        'pr_mean': pr_mean, 'pr_peak': pr_peak,
    }


def find_rheobase(results: list[dict]) -> float:
    """spinal 均值首次超过 FIRE_THRESHOLD 的最低 D1 权重。"""
    for r in sorted(results, key=lambda x: x['w_d1']):
        sp_avg = (r['sp_ccw_mean'] + r['sp_cw_mean']) / 2.0
        if sp_avg > FIRE_THRESHOLD:
            return r['w_d1']
    return float('nan')


def print_table(results: list[dict], label: str):
    hdr = (f"{'w_D1':>7} | "
           f"{'pL_mean':>8} {'pL_peak':>8} | "
           f"{'sp_mean':>8} {'sp_peak':>8} | "
           f"{'yaw_mean':>9} {'yaw_peak':>9}")
    print(f"\n  [{label}]")
    print(f"  {hdr}")
    print("  " + "-" * len(hdr))
    for r in results:
        sp_mean = (r['sp_ccw_mean'] + r['sp_cw_mean']) / 2.0
        sp_peak = max(r['sp_ccw_peak'], r['sp_cw_peak'])
        yaw_mean = (r['yaw_ccw_mean'] + r['yaw_cw_mean']) / 2.0
        yaw_peak = max(r['yaw_ccw_peak'], r['yaw_cw_peak'])
        fire_flag = " ←FIRE" if sp_mean > FIRE_THRESHOLD else ""
        sat_flag  = " ←SAT"  if sp_mean > 0.8 else ""
        print(f"  {r['w_d1']:>7.3f} | "
              f"{r['pl_mean']:>8.4f} {r['pl_peak']:>8.4f} | "
              f"{sp_mean:>8.4f} {sp_peak:>8.4f} | "
              f"{yaw_mean:>9.5f} {yaw_peak:>9.5f}"
              f"{fire_flag}{sat_flag}")


def main():
    print("=" * 90)
    print("  T-042: F-I 曲线诊断 + Ia 互抑对照扫描")
    print("=" * 90)
    print(f"  扫描范围: {W_LIST}")
    print(f"  每个配置: {TOTAL}步（热身{WARMUP}步 + 统计{MEASURE}步）")
    print(f"  D1 束冻结于目标权重（STDP 停用）")
    print(f"  热场: body={BODY_POS}, heat={SRC_POS}")
    print(f"  spinal 点火阈值: {FIRE_THRESHOLD}")
    print()

    results_a = []   # 有 Ia
    results_b = []   # 无 Ia

    # ── 扫描 A（有 Ia）───────────────────────────────────────────────────
    print("  [扫描A] 有 Ia 互抑（Step 6 默认）")
    t0 = time.time()
    for w in W_LIST:
        r = run_one(w, disable_ia=False)
        results_a.append(r)
        sp = (r['sp_ccw_mean'] + r['sp_cw_mean']) / 2.0
        flag = " ←点火" if sp > FIRE_THRESHOLD else ""
        print(f"    w={w:.3f}: spinal_mean={sp:.5f}, yaw_mean="
              f"{(r['yaw_ccw_mean']+r['yaw_cw_mean'])/2:.5f}{flag}")
    print(f"  扫描A完成, 耗时{time.time()-t0:.1f}s")

    # ── 扫描 B（无 Ia）───────────────────────────────────────────────────
    print()
    print("  [扫描B] 无 Ia 互抑（Ia 束权重归零）")
    t0 = time.time()
    for w in W_LIST:
        r = run_one(w, disable_ia=True)
        results_b.append(r)
        sp = (r['sp_ccw_mean'] + r['sp_cw_mean']) / 2.0
        flag = " ←点火" if sp > FIRE_THRESHOLD else ""
        print(f"    w={w:.3f}: spinal_mean={sp:.5f}, yaw_mean="
              f"{(r['yaw_ccw_mean']+r['yaw_cw_mean'])/2:.5f}{flag}")
    print(f"  扫描B完成, 耗时{time.time()-t0:.1f}s")

    # ── 完整表格 ─────────────────────────────────────────────────────────
    print_table(results_a, "扫描A：有 Ia 互抑（实际工作条件）")
    print_table(results_b, "扫描B：无 Ia 互抑（D1 原始能力）")

    # ── 分析 ─────────────────────────────────────────────────────────────
    rh_a = find_rheobase(results_a)
    rh_b = find_rheobase(results_b)

    print()
    print("=" * 90)
    print("  === 分析结论 ===")
    print(f"  rheobase_A（有Ia）: {rh_a:.3f}  →  spinal 在此权重以上才能稳定激活")
    print(f"  rheobase_B（无Ia）: {rh_b:.3f}  →  D1 本身的原始阈值")
    if not math.isnan(rh_a) and not math.isnan(rh_b) and rh_b > 0:
        sr = rh_a / rh_b
        print(f"  Ia 压制比: {sr:.1f}×  (rheobase_A / rheobase_B)")
        print(f"  → Ia 互抑将 D1 有效阈值抬高了 {sr:.1f}×")
    else:
        print("  （无法计算压制比：某条曲线在扫描范围内未触发阈值）")

    # 当前值评估
    for results, label in [(results_a, '有Ia'), (results_b, '无Ia')]:
        r_100 = next((r for r in results if abs(r['w_d1'] - 0.100) < 0.001), None)
        if r_100:
            sp_now = (r_100['sp_ccw_mean'] + r_100['sp_cw_mean']) / 2.0
            sp_hi  = results[-1]   # w=0.300
            sp_max = (sp_hi['sp_ccw_mean'] + sp_hi['sp_cw_mean']) / 2.0
            regime = "饱和区" if sp_now > sp_max * 0.85 else "线性区"
            print(f"  当前 w=0.1（{label}）: spinal_mean={sp_now:.4f}，处于{regime}"
                  f"（最大值={sp_max:.4f}，占比{sp_now/max(sp_max,1e-9)*100:.1f}%）")

    print()
    print("  === 对阶段二/四的参数建议 ===")
    if not math.isnan(rh_a) and rh_a > 0.005:
        print(f"  阶段二 initial_weight 建议值: {rh_a:.3f}（等于rheobase_A，确保Ia下仍能点火）")
        print(f"  不要降至 0.005（< rheobase_A={rh_a:.3f}），会被 Ia 完全压制，学习不可能发生")
    elif not math.isnan(rh_a):
        print(f"  rheobase_A={rh_a:.3f}，Ia 压制有限，initial_weight=0.005 可能可行")
        print(f"  但 constitutive LTD 仍会在饱腹期把 0.005 的权重压归零，风险保留")

    print()
    for results, label in [(results_a, '有Ia'), (results_b, '无Ia')]:
        r_100 = next((r for r in results if abs(r['w_d1'] - 0.100) < 0.001), None)
        if r_100:
            yaw_mean = (r_100['yaw_ccw_mean'] + r_100['yaw_cw_mean']) / 2.0
            sp_mean = (r_100['sp_ccw_mean'] + r_100['sp_cw_mean']) / 2.0
            if sp_mean > 0 and yaw_mean > 0:
                gain = yaw_mean / sp_mean
                print(f"  D1→yaw 增益（{label}，w=0.1）: {gain:.4f}（yaw/spinal ratio）")
                print(f"  → 阶段四 cross-inhibition 参数估计：")
                print(f"     目标：cross-inhibition ≈ 50% 正向增益 → sg_cross × w_cross ≈ {gain*0.5:.4f}")
                print(f"     示例：sg_cross=-1.0, w_cross={gain*0.5:.4f}（待阶段四验证）")


if __name__ == '__main__':
    main()
