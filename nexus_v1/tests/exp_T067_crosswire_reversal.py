"""
T-067: 交叉接线翻转实验（防诈胡第三层）

设计：
  - 软断开原 D1 束（phasic_left→spinal_ccw, phasic_right→spinal_cw），权重→0.001
  - 注入 2 组竞争束（各1条），初始权重相同（0.010）：
      SWAP_L：phasic_left → spinal_cw  （错误接线）
      CORRECT_L：phasic_left → spinal_ccw（正确接线，与原D1一致）
      SWAP_R：phasic_right → spinal_ccw（错误接线）
      CORRECT_R：phasic_right → spinal_cw（正确接线，与原D1一致）
  - 运行 200k 步，记录正确/错误束权重分化

timing注意事项：
  - c.step() 内部已手动步进 spinal_ccw/cw（variant_adapter.py:1426）
  - 额外束在 c.step() 后调用 propagate()+apply_to_targets()：spinal 多步进一次
  - 对非 spiking 神经元的影响：traces 衰减略快，不影响定性结论（200k 步量级）

判定标准：
  - PASS：末态 w_correct_L > w_swap_L 且 w_correct_R > w_swap_R（正确束胜出）
  - SECONDARY: DR5% > 45%（热趋性行为保留）
  - FAIL：错误束胜出 → 说明空间梯度学习存在问题
"""
import sys
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.circuit.bundle import SynapticBundle, BundleConfig
from nexus_v1.components.world import World, HeatSource, Body

STEPS        = 200_000
DT           = 1.0
REPORT_EVERY = 20_000


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def get_fill(c):
    try:
        return c.energy_store._cap.charge / c.energy_store.config.capacity
    except Exception:
        return 0.0


def get_da(c):
    try:
        da_n = getattr(c, 'dopamine_neuron', None) or getattr(c, 'da_neuron', None)
        if da_n:
            return da_n.activation
        return c.dopamine.concentration
    except Exception:
        return 0.0


def get_bundle_weight(b):
    try:
        return b._memristors[0][0].w
    except Exception:
        return float('nan')


def get_dr5(c):
    try:
        pts = c._patch_temps
        vx  = c.world.body.velocity[0]
        vy  = c.world.body.velocity[1]
        lr  = pts.get('right', 0) - pts.get('left', 0)
        fb  = pts.get('front', 0) - pts.get('back', 0)
        return (lr * vx + fb * vy) > 0
    except Exception:
        return False


def get_dist(c):
    try:
        bpos = c.world.body.position
        spos = c.world.heat_sources[0].position
        return ((bpos[0]-spos[0])**2 + (bpos[1]-spos[1])**2 + (bpos[2]-spos[2])**2)**0.5
    except Exception:
        return float('nan')


def make_d1_bundle(bid, src, tgt):
    """同原 D1 束参数，initial_weight=0.010（与软断开后的原D1竞争）。"""
    cfg = BundleConfig(
        bundle_id=bid,
        learning_rule='stdp',
        initial_weight=0.010,
        weight_max=0.3,
        stdp_lr=0.005,
        synapse_gain=1.0,
        bundle_role='feedforward',
        remodel_cost_kappa=0.0,
        use_eligibility_trace=True,
    )
    return SynapticBundle(cfg, [src], [tgt])


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def run():
    print("=" * 70)
    print("T-067: 交叉接线翻转实验（防诈胡第三层）")
    print("=" * 70)

    # ── 1. 初始化电路 ──
    src  = HeatSource(position=[70, 50, 25], temperature=5.0, radius=30, energy=1000.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=[10, 50, 25])
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE   = 0
    world.REGEN_PROB  = 0.0

    c = VariantCircuit()
    c.world = world
    c.somatosensory.LATERAL_GAIN = 0.3
    for mn in c.motor_neurons.values():
        mn.config.output_gain = 0.1
    c.energy_store._cap.charge = c.energy_store.config.capacity * 0.3

    # ── 2. 软断开原 D1 束 ──
    orig_names = ['bundle_d1_phasic_left_to_spinal_ccw',
                  'bundle_d1_phasic_right_to_spinal_cw']
    print("\n[SETUP] 软断开原 D1 束...")
    for name in orig_names:
        b = getattr(c, name, None)
        if b is None:
            print(f"  ⚠️  {name} not found!")
            continue
        for row in b._memristors:
            for m in row:
                m.w = 0.001
        print(f"  {name}: w → 0.001")

    # ── 3. 注入竞争束 ──
    # CORRECT bundles = 与原D1方向相同（正确接线）
    b_correct_L = make_d1_bundle('t067_correct_L', c.phasic_left,  c.spinal_ccw)
    b_correct_R = make_d1_bundle('t067_correct_R', c.phasic_right, c.spinal_cw)
    # SWAP bundles = 反接（错误接线）
    b_swap_L    = make_d1_bundle('t067_swap_L',    c.phasic_left,  c.spinal_cw)
    b_swap_R    = make_d1_bundle('t067_swap_R',    c.phasic_right, c.spinal_ccw)

    extra_bundles = [b_correct_L, b_correct_R, b_swap_L, b_swap_R]

    print("\n[SETUP] 注入竞争束（各 initial_weight=0.010）：")
    print(f"  CORRECT_L: phasic_left  → spinal_ccw  w0={get_bundle_weight(b_correct_L):.4f}")
    print(f"  CORRECT_R: phasic_right → spinal_cw   w0={get_bundle_weight(b_correct_R):.4f}")
    print(f"  SWAP_L:    phasic_left  → spinal_cw   w0={get_bundle_weight(b_swap_L):.4f}")
    print(f"  SWAP_R:    phasic_right → spinal_ccw  w0={get_bundle_weight(b_swap_R):.4f}")

    # ── 4. 步进循环 ──
    dr5_votes = 0
    f_steps   = 0
    fill_min  = 1.0

    print(f"\n{'Step':>8} | {'DR5%':>5} | {'η%':>5} | {'fill':>5} | {'dist':>5} | "
          f"{'w_cL':>6} {'w_cR':>6} | {'w_sL':>6} {'w_sR':>6} | {'Δcorr_L':>8}")
    print("  " + "-" * 76)

    for step in range(1, STEPS + 1):
        c.step({}, DT)

        fill = get_fill(c)
        da   = get_da(c)
        fill_min = min(fill_min, fill)

        # 驱动额外束：1步延迟（spinal 已被 c.step 步进过一次）
        for b in extra_bundles:
            currents = b.propagate()
            b.apply_to_targets(currents, DT)
            b.learn(DT, 1.0, fill, da)

        if get_dr5(c):
            dr5_votes += 1
        if fill < 0.85 and da > 0.1:
            f_steps += 1

        if step % REPORT_EVERY == 0:
            w_cL = get_bundle_weight(b_correct_L)
            w_cR = get_bundle_weight(b_correct_R)
            w_sL = get_bundle_weight(b_swap_L)
            w_sR = get_bundle_weight(b_swap_R)
            dr5  = dr5_votes / step * 100.0
            eta  = f_steps / step * 100.0
            dist = get_dist(c)
            dw_L = w_cL - w_sL
            print(f"  {step:8d} | {dr5:5.1f} | {eta:5.1f} | {fill:5.3f} | {dist:5.1f} | "
                  f"{w_cL:6.4f} {w_cR:6.4f} | {w_sL:6.4f} {w_sR:6.4f} | {dw_L:+8.4f}")

    # ── 5. 最终结果 ──
    w_cL = get_bundle_weight(b_correct_L)
    w_cR = get_bundle_weight(b_correct_R)
    w_sL = get_bundle_weight(b_swap_L)
    w_sR = get_bundle_weight(b_swap_R)
    # 原 D1 束末态
    w_orig_L = get_bundle_weight(c.bundle_d1_phasic_left_to_spinal_ccw)
    w_orig_R = get_bundle_weight(c.bundle_d1_phasic_right_to_spinal_cw)

    dr5_pct  = dr5_votes / STEPS * 100.0
    eta_pct  = f_steps   / STEPS * 100.0

    print("\n" + "=" * 70)
    print("最终结果")
    print("=" * 70)
    print(f"  CORRECT_L (phasic_L→ccw):  w = {w_cL:.4f}")
    print(f"  SWAP_L    (phasic_L→cw):   w = {w_sL:.4f}")
    print(f"  Δw_L = correct - swap     = {w_cL - w_sL:+.4f}")
    print(f"  CORRECT_R (phasic_R→cw):   w = {w_cR:.4f}")
    print(f"  SWAP_R    (phasic_R→ccw):  w = {w_sR:.4f}")
    print(f"  Δw_R = correct - swap     = {w_cR - w_sR:+.4f}")
    print(f"  原D1束末态: L={w_orig_L:.4f}  R={w_orig_R:.4f}")
    print(f"  DR5%: {dr5_pct:.1f}%")
    print(f"  η (Foraging%): {eta_pct:.1f}%")
    print(f"  fill_min: {fill_min:.3f}")

    # ── 6. 判定 ──
    print("\n" + "-" * 70)
    pass_correct_L = w_cL > w_sL
    pass_correct_R = w_cR > w_sR
    pass_dr5       = dr5_pct > 45.0

    results = [
        ("J1 CORRECT_L > SWAP_L", pass_correct_L,
         f"w_correct={w_cL:.4f} vs w_swap={w_sL:.4f}"),
        ("J2 CORRECT_R > SWAP_R", pass_correct_R,
         f"w_correct={w_cR:.4f} vs w_swap={w_sR:.4f}"),
        ("J3 DR5% > 45%",         pass_dr5,
         f"{dr5_pct:.1f}%"),
    ]
    all_pass = all(r[1] for r in results)

    for name, ok, detail in results:
        status = "PASS ✓" if ok else "FAIL ✗"
        print(f"  [{status}] {name}  ({detail})")

    n_pass = sum(1 for r in results if r[1])
    print(f"\n  总计：{n_pass}/{len(results)} PASS  →  "
          f"{'✅ 防诈胡第三层通过：STDP选择空间梯度正确方向' if all_pass else '❌ FAIL — 分析见下方'}")

    if not all_pass:
        if not pass_correct_L or not pass_correct_R:
            print("  → 正确束未能击败错误束：可能原因：")
            print("    1. CPG随机性主导（需多次运行）")
            print("    2. 200k步不够长（LTD未完成清洗）")
            print("    3. double-step timing artifact 干扰 spinal traces")
        if not pass_dr5:
            print("  → DR5%<45%：热趋性行为受损（可能正确+错误束竞争混淆运动）")


if __name__ == '__main__':
    run()
