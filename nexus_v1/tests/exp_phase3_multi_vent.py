"""nexus_v1.tests.exp_phase3_multi_vent — World 2.0 Phase 3 多热泉觅食实验.

Phase 3 在 Phase 2 基础上解决三个物理瓶颈：
  P3-FIX-01: 3 个柱状热源（正三角形）→ 多次接近窗口，任何朝向均有热源覆盖
  P3-FIX-02: ThermalMouth.eta 0.15 → 0.50 → 能量正平衡可达
  P3-FIX-03: eligibility_gain 1e-5 → 3e-5 → 加速 STDP 方向学习
  P3-FIX-04: 流场风向标力矩（K_VANE=0.001）→ 防止 yaw 发散（受监控特殊构建）
              BIO: 流体中非对称刚体被动对齐流向（与对流漂移同构，均为物理直接力）
              监控约定：若 W14 PASS 且移除 P3-FIX-04 后 W14 FAIL，则 P3-FIX-04 有贡献。

参数继承（Phase 2 v3）：
  k_conv=0.50（phase 2 实测临界值 0.47，保持）
  YAW_GAIN=0.10（phase 1/2 验证）
  therm_left/right→move_y: 冻结（w=0，消除侧滑干扰）
  therm_front/back→move_x: weight_max=0.5（默认值，不降为 0.3），init_w=0.01

weight_max 说明：
  hebbian.py 中 therm→motor 束默认 weight_max=0.5（Phase 5 已验证安全）。
  Phase 2 将其降为 0.3 是保护性措施，Phase 3 恢复默认 0.5（分歧文档预警二）。
  因此本脚本不需要设置 weight_max，只需重置初始权重为 0.01。

起始位置说明：
  [50, 50, 25] 是三热源的几何中心（到三源距离均约 30，dist_surface≈24）。
  该处温度梯度因对称性抵消趋近零，Langevin 噪声驱动 body 向其中一热源漂移。
  这是中性的公平起点，避免 Phase 2 中偶然紧靠热源 1 的问题。

验收标准：
  W13: ≥2 次 dist_surface < 15 units（多次接近）
  W14: w_front / w_brake > 2.0 @ step 200k（STDP 学习成熟）
  W15: fill_fraction > 0.05 @ step 500k 全程（存活证明）
  W16: 21/21 回归 PASS（基础功能无退化）—— 在本脚本外提前确认

运行方式（从仓库根目录）：
  PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.exp_phase3_multi_vent
"""

import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.heat_source import CylindricalHeatSource

STEPS = 500_000
REPORT_INTERVAL = 10_000

# P3-FIX-04 风向标系数（受监控特殊构建）
K_VANE = 0.001
# 梯度奇点保护阈值（分歧文档预警一）
GRAD_MAG_SQ_MIN = 1e-8


def _dist_to_surface(body, src):
    """到柱状热源表面的水平距离。"""
    dx = body.position[0] - src.center[0]
    dy = body.position[1] - src.center[1]
    return math.sqrt(dx * dx + dy * dy) - src.radius


def nearest_dist_surface(body, sources):
    """到最近热源表面的距离。"""
    return min(_dist_to_surface(body, s) for s in sources if s.alive)


def nearest_source_idx(body, sources):
    """最近热源的索引。"""
    dists = [_dist_to_surface(body, s) for s in sources]
    return dists.index(min(dists))


def find_bundle(all_bundles, keyword):
    return next((b for b in all_bundles if keyword in b.config.bundle_id), None)


def run():
    print("=" * 100)
    print("  World 2.0 Phase 3 — Multi-Vent STDP Thermotaxis (W13/W14/W15)")
    print(f"  {STEPS:,} steps, reporting every {REPORT_INTERVAL:,} steps")
    print("=" * 100)

    circuit = VariantCircuit()

    # ── P3-FIX-01: 三热源正三角形布局 ──
    # 几何中心 [50, 50, 25]，三顶点等距约 30 units
    # S1=[80,50], S2=[35,76], S3=[35,24]；到中心距 30（S2/S3: sqrt(901)≈30.0）
    src1 = CylindricalHeatSource(
        center=[80.0, 50.0, 25.0], radius=6.0, height=16.0,
        T_surface=5.0, sigma=25.0, energy=8000.0, regeneration_rate=0.002,
    )
    src2 = CylindricalHeatSource(
        center=[35.0, 76.0, 25.0], radius=6.0, height=16.0,
        T_surface=5.0, sigma=25.0, energy=8000.0, regeneration_rate=0.002,
    )
    src3 = CylindricalHeatSource(
        center=[35.0, 24.0, 25.0], radius=6.0, height=16.0,
        T_surface=5.0, sigma=25.0, energy=8000.0, regeneration_rate=0.002,
    )
    all_sources = [src1, src2, src3]

    # 替换 world 中的热源列表（variant_adapter 的碰撞检测/再生遍历 cylindrical_sources）
    circuit.world.heat_sources = []
    circuit.world.cylindrical_sources = all_sources

    # ── P3-FIX-02: 进食效率提升 ──
    # BIO: eta=0.50 使 dist_surface<15 时供能可覆盖代谢消耗（Phase 2 实测 23% 不足）
    circuit.thermal_mouth.eta = 0.50

    # ── 起始位置：三热源几何中心（dist_surface≈24 对所有源均等）──
    circuit.world.body.position = [50.0, 50.0, 25.0]
    circuit.world.body.velocity = [0.0, 0.0, 0.0]
    circuit.world.body.yaw = 0.0

    # ── Bundle 覆写 ──
    all_bundles = circuit.get_all_bundles()

    b_front = find_bundle(all_bundles, 'therm_therm_front_to_move_x')
    b_brake = find_bundle(all_bundles, 'therm_therm_back_to_move_x')
    b_left  = find_bundle(all_bundles, 'therm_therm_left_to_move_y')
    b_right = find_bundle(all_bundles, 'therm_therm_right_to_move_y')

    # 冻结侧滑束（消除 move_y 干扰）
    for b in [b_left, b_right]:
        if b is not None:
            b.config.weight_max = 0.0
            for row in b._memristors:
                for m in row:
                    m.w = 0.0

    # 重置前进/制动束：初始权重 0.01，weight_max 保持默认 0.5
    # P3-FIX-03: eligibility_gain 1e-5 → 3e-5（加速 STDP，分歧文档确认）
    for b in [b_front, b_brake]:
        if b is not None:
            # weight_max 不变（默认已是 0.5，分歧文档预警二）
            b.config.eligibility_gain = 3e-5   # P3-FIX-03
            for row in b._memristors:
                for m in row:
                    m.w = 0.01

    # ── 打印初始配置 ──
    print()
    print("Sources (triangular layout):")
    for i, s in enumerate(all_sources, 1):
        print(f"  S{i}: center={s.center}, energy={s.energy:.0f}, sigma={s.sigma}")
    print()
    print("Bundle config:")
    _front_str = f"w_max={b_front.config.weight_max}, elig_gain={b_front.config.eligibility_gain:.2e}, mean_w={b_front.mean_weight():.4f}" if b_front else "NOT FOUND"
    _brake_str = f"w_max={b_brake.config.weight_max}, elig_gain={b_brake.config.eligibility_gain:.2e}, mean_w={b_brake.mean_weight():.4f}" if b_brake else "NOT FOUND"
    print(f"  therm_front→move_x: {_front_str}")
    print(f"  therm_back →move_x: {_brake_str}")
    print(f"  therm_left/right→move_y: frozen (w=0)")
    print(f"  eta={circuit.thermal_mouth.eta}, K_VANE={K_VANE}, k_conv={getattr(circuit, '_conv_k', 0.5)}")
    print()

    # ── 列头 ──
    print(f"{'step':>8} | {'d_surf':>6} | {'near':>4} | {'yaw°':>7} | "
          f"{'fill':>6} | {'intake/s':>9} | "
          f"{'E1':>6} | {'E2':>6} | {'E3':>6} | "
          f"{'w_front':>7} | {'w_brake':>7} | {'#appr':>5}")
    print("-" * 100)

    # ── 监控状态 ──
    approach_count = 0
    was_near = False          # 上次是否处于 dist_surface < 15 区间（用于计算接近次数）
    intake_acc = 0.0
    step_acc = 0
    w14_pass_step = None      # 首次达到 w_front/w_brake > 2.0 的步数

    for step in range(1, STEPS + 1):
        circuit.step({}, dt=0.001)

        # ── P3-FIX-04：流场风向标力矩（受监控特殊构建）──
        # PHYS: 对流漂移方向 = 温度梯度方向（热源流向 body）
        # 非对称刚体在流场中被动对齐（同 k_conv 漂移，属环境直接力，非神经通路）
        # 梯度奇点保护：在三热源鞍点处梯度趋零，atan2 数值不稳定，跳过
        grad = circuit.world.gradient_at(circuit.world.body.position)
        grad_mag_sq = grad[0] ** 2 + grad[1] ** 2
        if grad_mag_sq > GRAD_MAG_SQ_MIN:
            flow_dir = math.atan2(grad[1], grad[0])
            angle_error = (circuit.world.body.yaw - flow_dir + math.pi) % (2 * math.pi) - math.pi
            vane_torque = -K_VANE * math.sin(angle_error)
            circuit.world.body.apply_yaw_torque(vane_torque, dt=0.001)

        # ── 监控累积 ──
        intake_acc += circuit.thermal_mouth.energy_intake
        step_acc += 1

        # 接近计数：从 >15 穿越到 <15 算一次新接近
        d_surf = nearest_dist_surface(circuit.world.body, all_sources)
        is_near = d_surf < 15.0
        if is_near and not was_near:
            approach_count += 1
        was_near = is_near

        # W14 首次达到时记录
        if w14_pass_step is None and b_front is not None and b_brake is not None:
            wf = b_front.mean_weight()
            wb = b_brake.mean_weight()
            if wb > 1e-6 and wf / wb > 2.0:
                w14_pass_step = step

        if step % REPORT_INTERVAL == 0:
            body = circuit.world.body
            d_surf = nearest_dist_surface(body, all_sources)
            near_idx = nearest_source_idx(body, all_sources)
            yaw_deg = math.degrees(body.yaw)
            fill = circuit.energy_store.fill_fraction
            avg_intake = intake_acc / step_acc if step_acc > 0 else 0.0
            wf = b_front.mean_weight() if b_front else 0.0
            wb = b_brake.mean_weight() if b_brake else 0.0

            print(f"{step:>8,} | {d_surf:>6.2f} | {'S'+str(near_idx+1):>4} | {yaw_deg:>7.1f} | "
                  f"{fill:>6.4f} | {avg_intake:>9.6f} | "
                  f"{src1.energy:>6.0f} | {src2.energy:>6.0f} | {src3.energy:>6.0f} | "
                  f"{wf:>7.4f} | {wb:>7.4f} | {approach_count:>5}")

            intake_acc = 0.0
            step_acc = 0

    # ── 最终验收 ──
    body = circuit.world.body
    fill_final = circuit.energy_store.fill_fraction
    wf_final = b_front.mean_weight() if b_front else 0.0
    wb_final = b_brake.mean_weight() if b_brake else 0.0
    d_surf_final = nearest_dist_surface(body, all_sources)

    print("\n" + "=" * 100)
    print("  FINAL ASSESSMENT")
    print(f"  approach_count:    {approach_count}  (W13 target: ≥2)")
    print(f"  w_front/w_brake:   {wf_final:.4f} / {wb_final:.4f} = "
          f"{wf_final/wb_final:.3f}" if wb_final > 1e-6 else "  w_front/w_brake:  N/A")
    if w14_pass_step:
        print(f"  W14 first reached: step {w14_pass_step:,}")
    else:
        print(f"  W14 first reached: NOT REACHED")
    print(f"  fill_fraction:     {fill_final:.4f}  (W15 target: >0.05)")
    print(f"  dist_surface:      {d_surf_final:.2f} units")
    print(f"  Source energies:   S1={src1.energy:.0f}  S2={src2.energy:.0f}  S3={src3.energy:.0f}")
    print()

    # W13: 多次接近（≥2 次 dist_surface < 15）
    w13 = approach_count >= 2
    # W14: 步 200k 前 w_front/w_brake > 2.0
    w14 = w14_pass_step is not None and w14_pass_step <= 200_000
    # W15: 500k 步结束时 fill > 0.05
    w15 = fill_final > 0.05

    print(f"  {'[PASS]' if w13 else '[FAIL]'} W13: approach_count ≥ 2 (actual: {approach_count})")
    if wb_final > 1e-6:
        print(f"  {'[PASS]' if w14 else '[FAIL]'} W14: w_front/w_brake > 2.0 @ ≤200k "
              f"(first at: step {w14_pass_step:,} = {wf_final/wb_final:.3f})" if w14_pass_step
              else f"  [FAIL] W14: w_front/w_brake > 2.0 @ ≤200k (NOT REACHED, final: {wf_final/wb_final:.3f})")
    else:
        print(f"  [FAIL] W14: w_brake~0 (cannot compute ratio)")
    print(f"  {'[PASS]' if w15 else '[FAIL]'} W15: fill > 0.05 @ 500k (actual: {fill_final:.4f})")
    print("=" * 100)

    return w13, w14, w15


if __name__ == "__main__":
    results = run()
    ok = all(results)
    sys.exit(0 if ok else 1)
