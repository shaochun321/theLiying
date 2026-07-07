"""
T-078: w_cw 异常衰减单步追踪

目的：定位 T-039b 中 w_cw 衰减 0.0473 (vs 预期 ~0.0005) 的根本原因。

策略：
  1. 冻结所有 STDP 后，记录每步 w_cw 和 w_ccw 的变化
  2. 同时记录 DA 浓度、pre_trace、post_act 等中间量
  3. 比较两束的衰减速率，找出不对称来源

步数：5000（足以看趋势，快速）
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

DT = 1.0


def freeze_all_stdp(circuit):
    count = 0
    for b in circuit.get_all_bundles():
        cfg = b.config
        if cfg.learning_rule not in ("frozen",):
            cfg.stdp_lr = 0.0
            if hasattr(cfg, 'eligibility_gain'):
                cfg.eligibility_gain = 0.0
            if hasattr(cfg, 'eligibility_ltd_rate'):
                cfg.eligibility_ltd_rate = 0.0
            count += 1
    return count


def main():
    print("=" * 72)
    print("  T-078: w_cw 异常衰减单步追踪")
    print("=" * 72)

    src = HeatSource(position=[70.0, 50.0, 25.0], energy=1_000_000.0,
                     temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=[10.0, 50.0, 25.0])
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world

    n = freeze_all_stdp(c)
    print(f"\n  已冻结 {n}/{len(c.get_all_bundles())} 条 STDP bundle\n")

    bl = c.bundle_d1_phasic_left_to_spinal_ccw
    br = c.bundle_d1_phasic_right_to_spinal_cw

    w_ccw_init = bl._memristors[0][0].w
    w_cw_init  = br._memristors[0][0].w
    print(f"  初始: w_ccw={w_ccw_init:.6f}  w_cw={w_cw_init:.6f}")
    print(f"  bl.config.use_eligibility_trace = {bl.config.use_eligibility_trace}")
    print(f"  br.config.use_eligibility_trace = {br.config.use_eligibility_trace}")
    print(f"  bl.config.lambda_metabolic = {bl.config.lambda_metabolic}")
    print(f"  br.config.lambda_metabolic = {br.config.lambda_metabolic}")
    print(f"  bl.config.eligibility_gain = {bl.config.eligibility_gain}")
    print(f"  br.config.eligibility_gain = {br.config.eligibility_gain}")
    print(f"  bl.config.eligibility_ltd_rate = {bl.config.eligibility_ltd_rate}")
    print(f"  br.config.eligibility_ltd_rate = {br.config.eligibility_ltd_rate}")
    print()

    STEPS = 5000
    SAMPLE = 500

    print(f"  {'step':>6} | {'w_ccw':>8} {'Δ_ccw':>9} | {'w_cw':>8} {'Δ_cw':>9} | "
          f"{'pL':>6} {'pR':>6} | {'da':>6} | {'fill':>5}")
    print("  " + "-"*80)

    # 获取 DA
    da_list = list(c.da_neurons.values()) if hasattr(c, 'da_neurons') else []
    da_neuron = da_list[0] if da_list else None

    for step in range(1, STEPS + 1):
        c.step({}, DT)

        if step % SAMPLE == 0:
            w_ccw = bl._memristors[0][0].w
            w_cw  = br._memristors[0][0].w
            d_ccw = w_ccw - w_ccw_init
            d_cw  = w_cw  - w_cw_init
            pL  = c.phasic_left.activation
            pR  = c.phasic_right.activation
            da  = da_neuron.activation if da_neuron else 0.0
            fill = c.energy_store.fill_fraction if hasattr(c, 'energy_store') else 0.0
            print(f"  {step:>6} | {w_ccw:>8.5f} {d_ccw:>+9.5f} | {w_cw:>8.5f} {d_cw:>+9.5f} | "
                  f"{pL:>6.4f} {pR:>6.4f} | {da:>6.4f} | {fill:>5.3f}")

    w_ccw_f = bl._memristors[0][0].w
    w_cw_f  = br._memristors[0][0].w
    delta_ccw = w_ccw_f - w_ccw_init
    delta_cw  = w_cw_f  - w_cw_init

    print(f"\n  ── 5k步总结 ──")
    print(f"  w_ccw: {w_ccw_init:.6f} → {w_ccw_f:.6f}  Δ={delta_ccw:+.6f}")
    print(f"  w_cw:  {w_cw_init:.6f} → {w_cw_f:.6f}  Δ={delta_cw:+.6f}")
    print(f"  比值  |Δw_cw/Δw_ccw| = {abs(delta_cw)/max(abs(delta_ccw),1e-12):.1f}×")

    # 理论预测（无 soft bounds）
    lam = bl.config.lambda_metabolic
    theory_linear = lam * w_ccw_init * STEPS
    theory_softb  = lam * w_ccw_init * w_ccw_init * STEPS   # with soft bounds ×(w-0)
    print(f"\n  理论（lambda={lam:.1e}）：")
    print(f"    线性 decay = λ×w×t = {theory_linear:.6f}")
    print(f"    软边界 decay = λ×w²×t = {theory_softb:.6f}")
    print()

    # 异常诊断
    ratio = abs(delta_cw) / max(abs(delta_ccw), 1e-12)
    if ratio > 5:
        print(f"  ❌ 异常：w_cw 衰减 {ratio:.0f}× 于 w_ccw。根因未知，需进一步追踪。")
        # 检查 _da_ema
        print(f"\n  bundle_l._da_ema = {bl._da_ema:.6f}")
        print(f"  bundle_r._da_ema = {br._da_ema:.6f}")
    elif abs(delta_cw) < 0.001:
        print(f"  ✅ 两束衰减对称，均 < 0.001（问题已消失或从未出现在此版本）")
    else:
        print(f"  ℹ️  两束衰减不对称（{ratio:.1f}×）但差异较小，需要更长时间观察")

    print("=" * 72)


if __name__ == '__main__':
    main()
