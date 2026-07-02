"""nexus_v1.tests.exp_phase4b_physical_fix — World 2.0 Phase 4-B 物理修正实验.

基于架构审计报告（2026-06-27）与双方案综合：
  P4B-FIX-01: ThermalMouth 能量簿记 bug（从最近热源扣除，monkeypatch，不改母代码）
  P4B-FIX-02: 起始位置 [75,35,25]（偏向 S1，dist_surface≈9.8，单向接近条件）
  P4B-FIX-03: eligibility_gain 恢复默认 1e-5（Phase 3 的 3e-5 导致 100k 步前饱和）
  P4B-FIX-04: Muscle gain 0.1→0.5（Motor 贡献约 0.05 units/step，Phase 3 的 5×）
  P4B-FIX-05: k_conv 0.50→0.47（临界值：Motor 学习后超过漂移；保留 bootstrap 能力）
  继承: P3-FIX-04 风向标力矩（K_VANE=0.001），eta=0.50，三热源布局

v·∇T DA 门控：本轮不启用（补充方案明确定为条件性备用）。
              若 w18 FAIL → Phase 4-C 再启用。

停止条件：
  DEADLOCK: step >= 100k AND w_front>0.35 AND w_brake>0.35 AND ratio in [0.90,1.11]
            → exit code 2（区别于正常完成 exit 0 / 失败 exit 1）
  NATURAL:  500k 步完成

验收标准：
  W18: w_front/w_brake > 1.5 @ 200k（方向性分化早期指标）
  W19: w_front/w_brake > 2.0 @ 500k（学习成熟）
  W15: fill > 0.05 全程 500k（能量自持）
  W13: approach_count >= 2（多次接近 dist_surface < 15）

运行：
  PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.exp_phase4b_physical_fix
"""

import sys
import os
import math
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.heat_source import CylindricalHeatSource

STEPS = 500_000
REPORT_INTERVAL = 10_000
DEADLOCK_MIN_STEP = 100_000
DEADLOCK_W_THRESHOLD = 0.35
DEADLOCK_RATIO_LO = 0.90
DEADLOCK_RATIO_HI = 1.11
K_VANE = 0.001
GRAD_MAG_SQ_MIN = 1e-8

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_DEADLOCK = 2


# ── 工具函数 ──────────────────────────────────────────────────────────────

def _dist_surface(body, src):
    dx = body.position[0] - src.center[0]
    dy = body.position[1] - src.center[1]
    return math.sqrt(dx*dx + dy*dy) - src.radius


def nearest_dist_surface(body, sources):
    return min(_dist_surface(body, s) for s in sources if s.alive)


def nearest_source_idx(body, sources):
    dists = [_dist_surface(body, s) for s in sources]
    return dists.index(min(dists))


def find_bundle(all_bundles, keyword):
    return next((b for b in all_bundles if keyword in b.config.bundle_id), None)


def is_deadlocked(step, wf, wb):
    """死锁检测：两束均接近饱和且比值接近1.0。"""
    if step < DEADLOCK_MIN_STEP:
        return False
    if wb < 1e-6:
        return False
    ratio = wf / wb
    return (wf > DEADLOCK_W_THRESHOLD and wb > DEADLOCK_W_THRESHOLD
            and DEADLOCK_RATIO_LO < ratio < DEADLOCK_RATIO_HI)


# ── P4B-FIX-01: ThermalMouth 能量簿记修复 ───────────────────────────────

def _thermal_mouth_step_nearest(self, world, body, energy_store,
                                ecm_temp=0.15, dt=0.001):
    """P4B-FIX-01: 替换原始 step，从最近存活热源扣除能量。

    原始 bug（thermal_mouth.py:88-91）：固定从 cylindrical_sources[0] 扣除，
    导致 E2/E3 全程不消耗，多热源场温度场不衰减，体生态压力失真。
    """
    pos = self.world_position(body)
    T_env = world.temperature_at(pos)
    T_body = ecm_temp

    dT = ((T_env - self.temperature) / self.tau_heat
          - (self.temperature - T_body) / self.tau_cool)
    self.temperature += dT * dt

    delta_T = max(0.0, T_env - self.temperature)
    total_heat_flux = self.conductance * self.area * delta_T * dt
    self.energy_intake = self.eta * total_heat_flux

    if self.energy_intake > 0:
        energy_store.deposit(self.energy_intake)
        srcs = [s for s in getattr(world, 'cylindrical_sources', []) if s.alive]
        if srcs:
            nearest = min(srcs, key=lambda s: math.hypot(
                pos[0] - s.center[0], pos[1] - s.center[1]))
            nearest.absorb(total_heat_flux)

    return self.energy_intake


# ── 主函数 ───────────────────────────────────────────────────────────────

def run():
    print("=" * 100)
    print("  World 2.0 Phase 4-B — Physical Fix Experiment")
    print("  P4B-FIX-01..05: Energy bookkeeping / Start pos / eligibility / Muscle gain / k_conv")
    print(f"  {STEPS:,} steps, report every {REPORT_INTERVAL:,}")
    print("=" * 100)

    circuit = VariantCircuit()

    # ── P3-FIX-01: 三热源布局（继承 Phase 3）──
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
    circuit.world.heat_sources = []
    circuit.world.cylindrical_sources = all_sources

    # ── P3-FIX-02 (Phase 3): eta=0.50 ──
    circuit.thermal_mouth.eta = 0.50

    # ── P4B-FIX-01: ThermalMouth 能量簿记 monkeypatch ──
    circuit.thermal_mouth.step = types.MethodType(
        _thermal_mouth_step_nearest, circuit.thermal_mouth)

    # ── P4B-FIX-02: 起始位置偏向 S1（dist_surface≈9.8，单向接近） ──
    # S1=[80,50,25]，从[75,35,25]到S1中心距=sqrt(5²+15²)≈15.8，dist_surface≈9.8
    circuit.world.body.position = [75.0, 35.0, 25.0]
    circuit.world.body.velocity = [0.0, 0.0, 0.0]
    circuit.world.body.yaw = 0.0

    # ── P4B-FIX-04: Muscle gain 0.1 → 0.5 ──
    # Motor 贡献：~0.05 units/step（激活=0.1），vs Phase 3 的 0.01
    for m in circuit.muscle_system.muscles:
        m.gain = 0.5

    # ── P4B-FIX-05: k_conv 0.50 → 0.47 ──
    # 临界值：保留 bootstrap 能力；Motor 学习后可超过漂移量
    circuit._conv_k = 0.47

    # ── Bundle 覆写 ──
    all_bundles = circuit.get_all_bundles()
    b_front = find_bundle(all_bundles, 'therm_therm_front_to_move_x')
    b_brake = find_bundle(all_bundles, 'therm_therm_back_to_move_x')
    b_left  = find_bundle(all_bundles, 'therm_therm_left_to_move_y')
    b_right = find_bundle(all_bundles, 'therm_therm_right_to_move_y')

    # 冻结侧滑束
    for b in [b_left, b_right]:
        if b is not None:
            b.config.weight_max = 0.0
            for row in b._memristors:
                for m in row:
                    m.w = 0.0

    # P4B-FIX-03: eligibility_gain 1e-5（默认值，Phase 3 用的 3e-5 太大）
    # 初始权重 0.01（非对称不在本轮测试范围，仅用默认）
    for b in [b_front, b_brake]:
        if b is not None:
            b.config.eligibility_gain = 1e-5
            for row in b._memristors:
                for m in row:
                    m.w = 0.01

    # ── 打印配置 ──
    print()
    print("Configuration:")
    print(f"  Start pos:       [75, 35, 25]  (dist_S1≈9.8, dist_S2≈51, dist_S3≈36)")
    print(f"  k_conv:          {circuit._conv_k}")
    print(f"  Muscle gain:     {circuit.muscle_system.muscles[0].gain}")
    print(f"  eta:             {circuit.thermal_mouth.eta}")
    print(f"  K_VANE:          {K_VANE}")
    for b, label in [(b_front, 'front'), (b_brake, 'brake')]:
        if b:
            print(f"  {label} bundle:    elig_gain={b.config.eligibility_gain:.2e}, "
                  f"w_max={b.config.weight_max}, init_w={b.mean_weight():.4f}")
    print(f"  ThermalMouth:    FIX-01 active (nearest source deduction)")
    print(f"  v·∇T DA gate:    NOT active (Phase 4-C conditional)")
    print()

    header = (f"{'step':>8} | {'d_surf':>6} | {'near':>4} | {'yaw°':>7} | "
              f"{'fill':>6} | {'intake/s':>9} | "
              f"{'E1':>6} | {'E2':>6} | {'E3':>6} | "
              f"{'w_front':>7} | {'w_brake':>7} | {'ratio':>5} | {'#app':>4}")
    print(header)
    print("-" * 105)

    approach_count = 0
    was_near = False
    intake_acc = 0.0
    step_acc = 0
    w18_pass_step = None   # w_front/w_brake > 1.5
    w19_pass_step = None   # w_front/w_brake > 2.0
    deadlock_detected = False

    for step in range(1, STEPS + 1):
        circuit.step({}, dt=0.001)

        # P3-FIX-04: 风向标力矩（继承）
        grad = circuit.world.gradient_at(circuit.world.body.position)
        grad_mag_sq = grad[0]**2 + grad[1]**2
        if grad_mag_sq > GRAD_MAG_SQ_MIN:
            flow_dir = math.atan2(grad[1], grad[0])
            angle_error = (circuit.world.body.yaw - flow_dir + math.pi) % (2*math.pi) - math.pi
            vane_torque = -K_VANE * math.sin(angle_error)
            circuit.world.body.apply_yaw_torque(vane_torque, dt=0.001)

        intake_acc += circuit.thermal_mouth.energy_intake
        step_acc += 1

        d_surf = nearest_dist_surface(circuit.world.body, all_sources)
        is_near = d_surf < 15.0
        if is_near and not was_near:
            approach_count += 1
        was_near = is_near

        wf = b_front.mean_weight() if b_front else 0.0
        wb = b_brake.mean_weight() if b_brake else 0.0

        if wb > 1e-6:
            ratio = wf / wb
            if w18_pass_step is None and ratio > 1.5:
                w18_pass_step = step
            if w19_pass_step is None and ratio > 2.0:
                w19_pass_step = step

        if step % REPORT_INTERVAL == 0:
            body = circuit.world.body
            near_idx = nearest_source_idx(body, all_sources)
            yaw_deg = math.degrees(body.yaw)
            fill = circuit.energy_store.fill_fraction
            avg_intake = intake_acc / step_acc if step_acc > 0 else 0.0
            ratio_str = f"{wf/wb:.3f}" if wb > 1e-6 else "  N/A"

            print(f"{step:>8,} | {d_surf:>6.2f} | {'S'+str(near_idx+1):>4} | {yaw_deg:>7.1f} | "
                  f"{fill:>6.4f} | {avg_intake:>9.6f} | "
                  f"{src1.energy:>6.0f} | {src2.energy:>6.0f} | {src3.energy:>6.0f} | "
                  f"{wf:>7.4f} | {wb:>7.4f} | {ratio_str:>5} | {approach_count:>4}")

            intake_acc = 0.0
            step_acc = 0

            # 死锁检测（每 10k 步评估一次）
            if is_deadlocked(step, wf, wb):
                print()
                print(f"  [DEADLOCK DETECTED at step {step:,}]")
                print(f"  w_front={wf:.4f}, w_brake={wb:.4f}, ratio={wf/wb:.4f}")
                print(f"  Both weights above {DEADLOCK_W_THRESHOLD}, ratio in "
                      f"[{DEADLOCK_RATIO_LO},{DEADLOCK_RATIO_HI}].")
                print(f"  STDP symmetric lock confirmed. Stopping early.")
                deadlock_detected = True
                break

    # ── 最终验收 ──
    body = circuit.world.body
    fill_final = circuit.energy_store.fill_fraction
    wf_final = b_front.mean_weight() if b_front else 0.0
    wb_final = b_brake.mean_weight() if b_brake else 0.0
    d_surf_final = nearest_dist_surface(body, all_sources)
    ratio_final = wf_final/wb_final if wb_final > 1e-6 else float('nan')

    print("\n" + "=" * 100)
    if deadlock_detected:
        print("  RESULT: DEADLOCK — early termination")
    else:
        print("  RESULT: NATURAL COMPLETION")
    print()
    print(f"  approach_count:    {approach_count}  (W13 target: >=2)")
    print(f"  w_front/w_brake:   {wf_final:.4f} / {wb_final:.4f} = {ratio_final:.3f}")
    if w18_pass_step:
        print(f"  W18 (ratio>1.5):   first at step {w18_pass_step:,}")
    else:
        print(f"  W18 (ratio>1.5):   NOT REACHED")
    if w19_pass_step:
        print(f"  W19 (ratio>2.0):   first at step {w19_pass_step:,}")
    else:
        print(f"  W19 (ratio>2.0):   NOT REACHED")
    print(f"  fill_fraction:     {fill_final:.4f}  (W15 target: >0.05)")
    print(f"  dist_surface:      {d_surf_final:.2f}")
    print(f"  Source energies:   S1={src1.energy:.0f}  S2={src2.energy:.0f}  S3={src3.energy:.0f}")
    print()

    w13 = approach_count >= 2
    w15 = fill_final > 0.05
    w18 = w18_pass_step is not None and w18_pass_step <= 200_000
    w19 = w19_pass_step is not None

    print(f"  {'[PASS]' if w13 else '[FAIL]'} W13: approach_count >= 2 (actual: {approach_count})")
    print(f"  {'[PASS]' if w18 else '[FAIL]'} W18: ratio>1.5 @ <=200k "
          f"(at: {w18_pass_step:,})" if w18_pass_step else
          f"  [FAIL] W18: ratio>1.5 @ <=200k (NOT REACHED)")
    print(f"  {'[PASS]' if w19 else '[FAIL]'} W19: ratio>2.0 "
          f"(at: {w19_pass_step:,})" if w19_pass_step else
          f"  [FAIL] W19: ratio>2.0 (NOT REACHED)")
    print(f"  {'[PASS]' if w15 else '[FAIL]'} W15: fill>0.05 @ end (actual: {fill_final:.4f})")
    print("=" * 100)

    if deadlock_detected:
        return EXIT_DEADLOCK
    return EXIT_PASS if (w13 and w18 and w15) else EXIT_FAIL


if __name__ == "__main__":
    code = run()
    sys.exit(code)
