"""nexus_v1.tests.exp_phase4c_da_directional — World 2.0 Phase 4-C DA 方向化实验.

在 Phase 4-B 物理修正基础上，加入 v·∇T DA 方向门控（方案 A）：
  P4C-NEW-01: DA 方向化门控（monkeypatch da_gate.step）
              DA_gated = DA_rpe × direction_factor
              direction_factor = max(0, min(1, v·∇T / V_REF))
              V_REF = 0.003（由实测接近速度估算：v≈0.15 unit/s，|∇T|≈0.05，v·∇T≈0.007）
              物理合法性：v·∇T 与 k_conv 同构，均为物理量直接映射，属 L2:SELECTION 层

  P4C-NEW-02: Xin 张力监控（bundle.config.xin_tension，每 10k 步采样）
  P4C-NEW-03: 前庭-运动状态监控（column_neurons + motor_neurons，每 10k 步平均激活）
              分析长程运行中前庭-运动链路的实际行为模式

继承 Phase 4-B 全部修正：
  P4B-FIX-01: ThermalMouth 能量簿记（最近热源）
  P4B-FIX-02: 起始位置 [75,35,25]
  P4B-FIX-03: eligibility_gain = 1e-5
  P4B-FIX-04: Muscle gain = 0.5
  P4B-FIX-05: k_conv = 0.47
  继承 P3-FIX-04: K_VANE=0.001 风向标

停止条件：
  DEADLOCK: step>=100k AND w_front>0.35 AND w_brake>0.35 AND ratio∈[0.90,1.11]
  SUCCESS:  step>=100k AND ratio>2.0（方向性学习确认，继续到 500k 验证稳定性）
  NATURAL:  500k 步完成

验收标准：
  W18: w_front/w_brake > 1.5 @ ≤200k（方向性分化）
  W19: w_front/w_brake > 2.0 @ ≤500k
  W15: fill > 0.05 全程
  W13: approach_count >= 2
  W-DA: mean direction_factor > 0.3 @ 100k（DA 门控确实在接近时激活）

运行：
  PYTHONIOENCODING=utf-8 python -u -m nexus_v1.tests.exp_phase4c_da_directional
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
V_REF = 0.003    # v·∇T 饱和参考值（°C/s）

VEST_AXES = ['yaw', 'pitch', 'roll', 'oto_x', 'oto_y', 'oto_z']
MOTOR_KEYS = ['move_x', 'move_y', 'move_z']


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


# ── P4C-NEW-01: DA 方向化门控 ─────────────────────────────────────────────

def _make_da_directional(da_gate, world, body, v_ref=V_REF):
    """创建 v·∇T 方向门控的 DA step 函数，绑定到 da_gate 实例。

    P4C-NEW-01 物理论证：
    - v 是 body.velocity（惯性量），∇T 由 world.gradient_at() 提供（与 k_conv 同构）
    - v·∇T 编码"接近速率"：v 与 ∇T 同向（接近）→ 正；垂直（轨道）→ 零；反向（离开）→ 负
    - 属 L2:SELECTION：进化固化的先天接近性学习门控，与 YAW_GAIN 反射同构
    - 不涉及语义目标：不判断"应该朝哪里走"，仅编码"是否在接近热源"的物理事实
    """

    def step_directional(self, fill_fraction, dt=0.001):
        # 原始 RPE 计算（保留 clip_max）
        delta_fill = fill_fraction - self._fill_prev
        self._fill_prev = fill_fraction
        raw = self.config.eta_da * delta_fill / max(dt, 1e-9)
        rpe_raw = min(max(0.0, raw - self.config.threshold), self.config.clip_max)

        # v·∇T 方向因子
        v = body.velocity
        grad = world.gradient_at(body.position)
        approach_rate = v[0] * grad[0] + v[1] * grad[1]
        direction_factor = max(0.0, min(1.0, approach_rate / v_ref))

        # 门控 DA
        gated = rpe_raw * direction_factor
        self._da_output = gated

        # 监控字段（每步更新，供外部读取）
        self._approach_rate = approach_rate
        self._direction_factor = direction_factor

        return gated

    # 添加监控属性
    da_gate._approach_rate = 0.0
    da_gate._direction_factor = 0.0

    return types.MethodType(step_directional, da_gate)


# ── 主函数 ───────────────────────────────────────────────────────────────

def run():
    print("=" * 110)
    print("  World 2.0 Phase 4-C — DA Directional Gating (v·∇T) + Xin & Vestibular-Motor Analysis")
    print(f"  V_REF={V_REF}, {STEPS:,} steps, report every {REPORT_INTERVAL:,}")
    print("=" * 110)

    circuit = VariantCircuit()

    # ── 三热源（继承 Phase 3/4-B）──
    src1 = CylindricalHeatSource(
        center=[80.0, 50.0, 25.0], radius=6.0, height=16.0,
        T_surface=5.0, sigma=25.0, energy=8000.0, regeneration_rate=0.002)
    src2 = CylindricalHeatSource(
        center=[35.0, 76.0, 25.0], radius=6.0, height=16.0,
        T_surface=5.0, sigma=25.0, energy=8000.0, regeneration_rate=0.002)
    src3 = CylindricalHeatSource(
        center=[35.0, 24.0, 25.0], radius=6.0, height=16.0,
        T_surface=5.0, sigma=25.0, energy=8000.0, regeneration_rate=0.002)
    all_sources = [src1, src2, src3]
    circuit.world.heat_sources = []
    circuit.world.cylindrical_sources = all_sources

    # ── eta=0.50（继承）──
    circuit.thermal_mouth.eta = 0.50

    # ── P4B-FIX-01: 能量簿记 monkeypatch ──
    circuit.thermal_mouth.step = types.MethodType(
        _thermal_mouth_step_nearest, circuit.thermal_mouth)

    # ── P4B-FIX-02: 起始位置 ──
    circuit.world.body.position = [75.0, 35.0, 25.0]
    circuit.world.body.velocity = [0.0, 0.0, 0.0]
    circuit.world.body.yaw = 0.0

    # ── P4B-FIX-04: Muscle gain 0.5 ──
    for m in circuit.muscle_system.muscles:
        m.gain = 0.5

    # ── P4B-FIX-05: k_conv 0.47 ──
    circuit._conv_k = 0.47

    # ── P4C-NEW-01: DA 方向化门控 ──
    circuit.da_gate.step = _make_da_directional(
        circuit.da_gate, circuit.world, circuit.world.body, V_REF)

    # ── Bundle 覆写（P4B-FIX-03: eligibility_gain=1e-5，P4B-FIX-04 继承）──
    all_bundles = circuit.get_all_bundles()
    b_front = find_bundle(all_bundles, 'therm_therm_front_to_move_x')
    b_brake = find_bundle(all_bundles, 'therm_therm_back_to_move_x')
    b_left  = find_bundle(all_bundles, 'therm_therm_left_to_move_y')
    b_right = find_bundle(all_bundles, 'therm_therm_right_to_move_y')

    for b in [b_left, b_right]:
        if b is not None:
            b.config.weight_max = 0.0
            for row in b._memristors:
                for m in row:
                    m.w = 0.0

    for b in [b_front, b_brake]:
        if b is not None:
            b.config.eligibility_gain = 1e-5
            for row in b._memristors:
                for m in row:
                    m.w = 0.01

    # ── 前庭-运动监控：找可访问的列神经元 ──
    vest_cols = {}
    for ax in VEST_AXES:
        n = getattr(circuit, 'column_neurons', {}).get(ax, None)
        if n is None and hasattr(circuit, 'vestibular'):
            n = getattr(circuit.vestibular, f'col_{ax}', None)
        vest_cols[ax] = n

    motor_ns = {}
    for k in MOTOR_KEYS:
        motor_ns[k] = getattr(circuit, 'motor_neurons', {}).get(k, None)

    # ── 打印配置 ──
    print()
    print("Configuration:")
    print(f"  Start pos:     [75,35,25]  (dist_S1≈9.8)")
    print(f"  k_conv:        {circuit._conv_k}  |  Muscle gain: {circuit.muscle_system.muscles[0].gain}")
    print(f"  eta:           {circuit.thermal_mouth.eta}  |  K_VANE: {K_VANE}")
    print(f"  V_REF:         {V_REF}  (v·∇T saturation ref, °C/s)")
    print(f"  eligibility:   {b_front.config.eligibility_gain:.2e}  init_w=0.0100")
    print(f"  Vestibular cols: {[ax for ax,n in vest_cols.items() if n is not None]}")
    print(f"  Motor neurons:   {[k for k,n in motor_ns.items() if n is not None]}")
    print()

    # ── 主报告列头 ──
    print(f"{'step':>8} | {'d_surf':>6} | {'nr':>3} | {'yaw°':>7} | {'fill':>6} | "
          f"{'w_frt':>6} | {'w_brk':>6} | {'ratio':>5} | "
          f"{'DA_dir':>6} | {'xin_f':>6} | {'xin_b':>6} | {'#app':>4}")
    print("-" * 105)

    # ── 监控状态 ──
    approach_count = 0
    was_near = False
    intake_acc = 0.0
    dir_factor_acc = 0.0
    approach_rate_acc = 0.0
    step_acc = 0

    # 前庭-运动激活累积（每 10k 步平均）
    vest_act_acc  = {ax: 0.0 for ax in VEST_AXES}
    motor_act_acc = {k: 0.0 for k in MOTOR_KEYS}

    w18_pass_step = None
    w19_pass_step = None
    deadlock_detected = False
    result_note = "NATURAL COMPLETION"

    # 长程前庭-运动记录（每 50k 步快照）
    vest_motor_snapshots = []

    for step in range(1, STEPS + 1):
        circuit.step({}, dt=0.001)

        # P3-FIX-04: 风向标
        grad = circuit.world.gradient_at(circuit.world.body.position)
        grad_mag_sq = grad[0]**2 + grad[1]**2
        if grad_mag_sq > GRAD_MAG_SQ_MIN:
            flow_dir = math.atan2(grad[1], grad[0])
            angle_error = (circuit.world.body.yaw - flow_dir + math.pi) % (2*math.pi) - math.pi
            circuit.world.body.apply_yaw_torque(-K_VANE * math.sin(angle_error), dt=0.001)

        # 累积
        intake_acc += circuit.thermal_mouth.energy_intake
        da_df = getattr(circuit.da_gate, '_direction_factor', 0.0)
        da_ar = getattr(circuit.da_gate, '_approach_rate', 0.0)
        dir_factor_acc += da_df
        approach_rate_acc += da_ar
        step_acc += 1

        # 前庭-运动累积
        for ax in VEST_AXES:
            n = vest_cols.get(ax)
            if n is not None:
                act = getattr(n, 'activation', None) or getattr(n, '_activation', 0.0)
                vest_act_acc[ax] += abs(act)
        for k in MOTOR_KEYS:
            n = motor_ns.get(k)
            if n is not None:
                act = getattr(n, 'activation', None) or getattr(n, '_activation', 0.0)
                motor_act_acc[k] += abs(act)

        # 接近计数
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

        # ── 每 10k 步报告 ──
        if step % REPORT_INTERVAL == 0:
            body = circuit.world.body
            near_idx = nearest_source_idx(body, all_sources)
            yaw_deg = math.degrees(body.yaw)
            fill = circuit.energy_store.fill_fraction
            mean_df = dir_factor_acc / step_acc if step_acc > 0 else 0.0
            xin_f = b_front.config.xin_tension if b_front else 0.0
            xin_b = b_brake.config.xin_tension if b_brake else 0.0
            ratio_str = f"{wf/wb:.3f}" if wb > 1e-6 else "  N/A"

            print(f"{step:>8,} | {d_surf:>6.2f} | {'S'+str(near_idx+1):>3} | {yaw_deg:>7.1f} | "
                  f"{fill:>6.4f} | "
                  f"{wf:>6.4f} | {wb:>6.4f} | {ratio_str:>5} | "
                  f"{mean_df:>6.3f} | {xin_f:>6.4f} | {xin_b:>6.4f} | {approach_count:>4}")

            # ── 每 50k 步：前庭-运动状态快照 ──
            if step % 50_000 == 0:
                snap = {'step': step, 'fill': fill, 'd_surf': d_surf,
                        'yaw': yaw_deg, 'ratio': wf/wb if wb > 1e-6 else 0.0,
                        'mean_da_dir': mean_df,
                        'mean_approach_rate': approach_rate_acc / step_acc if step_acc > 0 else 0.0}
                for ax in VEST_AXES:
                    snap[f'vest_{ax}'] = vest_act_acc[ax] / step_acc if step_acc > 0 else 0.0
                for k in MOTOR_KEYS:
                    snap[f'motor_{k}'] = motor_act_acc[k] / step_acc if step_acc > 0 else 0.0
                vest_motor_snapshots.append(snap)

                print()
                print(f"  ─── Vestibular-Motor State @ {step:,} ───")
                print(f"  Vest. col (mean |act|): " +
                      " | ".join(f"{ax}={vest_act_acc[ax]/step_acc:.4f}"
                                 for ax in VEST_AXES if vest_cols.get(ax) is not None))
                print(f"  Motor    (mean |act|): " +
                      " | ".join(f"{k}={motor_act_acc[k]/step_acc:.4f}"
                                 for k in MOTOR_KEYS if motor_ns.get(k) is not None))
                print(f"  DA direction: mean_factor={mean_df:.3f}, "
                      f"mean_approach_rate={approach_rate_acc/step_acc:.5f}")
                print(f"  Xin tensions: front={xin_f:.6f}  brake={xin_b:.6f}")
                print(f"  Body: vel=({circuit.world.body.velocity[0]:.4f}, "
                      f"{circuit.world.body.velocity[1]:.4f})")
                print()

            # 重置累积（保持 10k 间隔平均）
            intake_acc = 0.0
            dir_factor_acc = 0.0
            approach_rate_acc = 0.0
            step_acc = 0
            for ax in VEST_AXES:
                vest_act_acc[ax] = 0.0
            for k in MOTOR_KEYS:
                motor_act_acc[k] = 0.0

            # ── 死锁检测 ──
            if is_deadlocked(step, wf, wb):
                print()
                print(f"  [DEADLOCK at step {step:,}] w_front={wf:.4f}, w_brake={wb:.4f}, ratio={wf/wb:.4f}")
                result_note = "DEADLOCK"
                deadlock_detected = True
                break

    # ── 最终报告 ──
    body = circuit.world.body
    fill_final = circuit.energy_store.fill_fraction
    wf_final = b_front.mean_weight() if b_front else 0.0
    wb_final = b_brake.mean_weight() if b_brake else 0.0
    d_surf_final = nearest_dist_surface(body, all_sources)
    ratio_final = wf_final / wb_final if wb_final > 1e-6 else float('nan')
    xin_f_final = b_front.config.xin_tension if b_front else 0.0
    xin_b_final = b_brake.config.xin_tension if b_brake else 0.0

    print("\n" + "=" * 110)
    print(f"  RESULT: {result_note}")
    print()
    print(f"  approach_count:    {approach_count}  (W13 target: >=2)")
    print(f"  w_front/w_brake:   {wf_final:.4f} / {wb_final:.4f} = {ratio_final:.3f}")
    print(f"  W18 (ratio>1.5):   {'step '+str(w18_pass_step) if w18_pass_step else 'NOT REACHED'}")
    print(f"  W19 (ratio>2.0):   {'step '+str(w19_pass_step) if w19_pass_step else 'NOT REACHED'}")
    print(f"  fill_fraction:     {fill_final:.4f}  (W15 target: >0.05)")
    print(f"  Xin tensions:      front={xin_f_final:.6f}  brake={xin_b_final:.6f}")
    print(f"  dist_surface:      {d_surf_final:.2f}")
    print(f"  Source energies:   S1={src1.energy:.0f}  S2={src2.energy:.0f}  S3={src3.energy:.0f}")
    print()

    w13 = approach_count >= 2
    w15 = fill_final > 0.05
    w18 = w18_pass_step is not None and w18_pass_step <= 200_000
    w19 = w19_pass_step is not None

    print(f"  {'[PASS]' if w13 else '[FAIL]'} W13: approach_count >= 2 (actual: {approach_count})")
    print(f"  {'[PASS]' if w18 else '[FAIL]'} W18: ratio>1.5 @ <=200k "
          f"({'step '+str(w18_pass_step) if w18_pass_step else 'NOT REACHED'})")
    print(f"  {'[PASS]' if w19 else '[FAIL]'} W19: ratio>2.0 "
          f"({'step '+str(w19_pass_step) if w19_pass_step else 'NOT REACHED'})")
    print(f"  {'[PASS]' if w15 else '[FAIL]'} W15: fill>0.05 (actual: {fill_final:.4f})")
    print()

    # ── 前庭-运动长程摘要 ──
    if vest_motor_snapshots:
        print("  ─── Vestibular-Motor Long-Run Summary ───")
        print(f"  {'step':>8} | {'d_surf':>6} | {'ratio':>5} | {'da_dir':>6} | "
              + " | ".join(f"{ax:>7}" for ax in VEST_AXES if vest_cols.get(ax) is not None)
              + " | " + " | ".join(f"{k:>8}" for k in MOTOR_KEYS if motor_ns.get(k) is not None))
        for s in vest_motor_snapshots:
            row = (f"  {s['step']:>8,} | {s['d_surf']:>6.2f} | {s['ratio']:>5.3f} | "
                   f"{s['mean_da_dir']:>6.3f} | "
                   + " | ".join(f"{s.get('vest_'+ax, 0):>7.4f}"
                                for ax in VEST_AXES if vest_cols.get(ax) is not None)
                   + " | " + " | ".join(f"{s.get('motor_'+k, 0):>8.5f}"
                                        for k in MOTOR_KEYS if motor_ns.get(k) is not None))
            print(row)

    print("=" * 110)

    return 0 if not deadlock_detected and (w13 and w18 and w15) else (2 if deadlock_detected else 1)


if __name__ == "__main__":
    sys.exit(run())
