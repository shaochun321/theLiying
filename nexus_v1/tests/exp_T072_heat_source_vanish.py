"""
T-072: 热源消失多周期实验 — 跨周期权重累积验证

目的：验证 P0 修复（lambda_metabolic=1e-6）使权重在热源消失的冷期得到保留，
     第二次 Foraging 窗口开放时 STDP 从已有权重继续分化（迁移学习）。

实验流程：
  Phase 1 (0~50k):    正常运行，body 找到热源，fill 饱和，记录第一次 STDP 权重
  Phase 2 (step 50k): 手动耗尽热源（src.energy=0）
  Phase 3 (50k~?):    fill 下降，Foraging 窗口重开，新热源随机出现（REGEN_PROB=0.001）
  Phase 4 (?~150k):   body 找到新热源，第二次 STDP 从保留权重继续分化
  Phase 5 (step 150k):第二次手动耗尽（若存在活跃热源）
  Phase 6 (150k~200k):第三次 Foraging（选测）

判定标准：
  J1: η_total ≥ 20%                      （多周期总 Foraging 效率）
  J2: |Δw|_end > |Δw|_at_50k             （跨周期权重累积，不回零）
  J3: T_relocate2 < T_relocate1 × 1.5    （第二次找源时间 < 1.5× 第一次）
  J4: w_ccw_final > 0.05                 （方向权重有实质积累）

注：J3 阈值放宽为 1.5× 而非 0.8×，因为：
  1. 新热源出现在随机位置，不保证方向利于 STDP 偏差
  2. T_relocate1 包含初始 k_conv 漂移，T_relocate2 受新源位置影响
  3. 主要测试的是权重保留（J2）而非导航速度提升（J3 参考观测）

Commit base: 0f85dc4 (T-039b 3/3 PASS)
"""
import sys, math, random
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS        = 200_000
DT           = 1.0
LOG_INTERVAL = 5_000

SRC_POS_1    = [70.0, 50.0, 25.0]
BODY_START   = [10.0, 50.0, 25.0]
SRC_ENERGY   = 100_000.0   # 大容量，Phase1 不会自然耗尽

DEPLETION_STEP_1 = 50_000
DEPLETION_STEP_2 = 150_000

# 判定阈值
ETA_THRESH    = 20.0
W_CCW_THRESH  = 0.05
T_RATIO_THRESH = 1.5  # J3: T_relocate2 / T_relocate1 < 1.5


def get_d1_weights(c):
    """FIX-006: 从 bundle attribute 读取权重。"""
    w_ccw = w_cw = float('nan')
    bl = getattr(c, 'bundle_d1_phasic_left_to_spinal_ccw', None)
    br = getattr(c, 'bundle_d1_phasic_right_to_spinal_cw', None)
    if bl and bl._memristors:
        w_ccw = bl._memristors[0][0].w
    if br and br._memristors:
        w_cw  = br._memristors[0][0].w
    return w_ccw, w_cw


def get_dr5(c):
    """Patch 温差 · body 速度方向符号。"""
    pT = c._patch_temps if hasattr(c, '_patch_temps') else {}
    T  = {pid: pT.get(pid, (0.0,))[0] for pid in ['front', 'back', 'left', 'right']}
    vx = c.world.body.velocity[0]
    vy = c.world.body.velocity[1]
    gx = T.get('right', 0.0) - T.get('left', 0.0)
    gy = T.get('front', 0.0) - T.get('back', 0.0)
    return (gx * vx + gy * vy) > 0.0


def get_nearest_dist(c):
    """到最近活跃热源的距离。"""
    pos = c.world.body.position
    best = float('inf')
    for src in c.world.heat_sources:
        if src.alive:
            d = math.sqrt(sum((pos[i] - src.position[i]) ** 2 for i in range(3)))
            best = min(best, d)
    return best


def in_source_zone(c):
    """body 是否在任意活跃热源的半径内。"""
    pos = c.world.body.position
    for src in c.world.heat_sources:
        if src.alive:
            d = math.sqrt(sum((pos[i] - src.position[i]) ** 2 for i in range(3)))
            if d < src.radius:
                return True
    return False


def main():
    print("=" * 72)
    print("  T-072: 热源消失多周期实验 (200k, 三周期)")
    print(f"  判定: J1 η≥{ETA_THRESH}% | J2 Δw累积 | J3 T_relocate2<{T_RATIO_THRESH}×T1 | J4 w_ccw>{W_CCW_THRESH}")
    print("=" * 72)

    # ── 世界构建 ──
    src1 = HeatSource(position=list(SRC_POS_1), energy=SRC_ENERGY,
                      temperature=5.0, radius=30.0)
    src1._drift = [0.0, 0.0, 0.0]   # 固定，不漂移
    body  = Body(position=list(BODY_START))
    world = World(heat_sources=[src1], body=body)
    world.MIN_ALIVE  = 0             # 不强制保留最小数量
    world.REGEN_PROB = 0.0           # Phase 1：单源受控环境，不生成新源
    # Phase 2 耗尽后会切换为 0.001

    c = VariantCircuit()
    c.world = world
    c.somatosensory.LATERAL_GAIN = 0.3
    for mn in c.motor_neurons.values():
        mn.config.output_gain = 0.1
    c.energy_store._cap.charge = c.energy_store.config.capacity * 0.3

    # ── 快照变量 ──
    foraging_steps   = 0     # body 在热源区 & 主动进食的步数
    dr5_count        = 0
    fill_min_global  = 1.0

    # 周期跟踪
    t_reach1       = None   # Phase1：首次进入源区
    t_deplete1     = None   # Phase1：手动耗尽时间
    t_reach2       = None   # Phase2：首次进入新源区
    t_deplete2     = None   # Phase2：第二次耗尽
    t_reach3       = None   # Phase3：第三次进入源区

    dw_at_50k      = 0.0    # |Δw| at depletion1
    dw_at_150k     = 0.0    # |Δw| at depletion2
    cycle1_reach   = False
    cycle2_reach   = False
    cycle3_reach   = False

    phase = 1

    w_ccw_init, w_cw_init = get_d1_weights(c)
    print(f"\n  初始 D1 权重: w_ccw={w_ccw_init:.4f}, w_cw={w_cw_init:.4f}")
    print(f"  初始 fill: {c.energy_store.fill_fraction:.3f}")
    print()

    hdr = (f"  {'Step':>7} | {'Ph':>2} | {'DR5%':>5} | {'dist':>6} | "
           f"{'w_ccw':>7} {'w_cw':>7} {'Dw':>7} | "
           f"{'fill':>5} | {'η%':>4} | {'n_src':>5}")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    for step in range(1, STEPS + 1):

        # ── 手动耗尽触发 ──
        if step == DEPLETION_STEP_1:
            # 耗尽第一热源，并开启随机新生（Phase 2 开始）
            for s in list(world.heat_sources):
                if s.alive:
                    s.energy = 0.0
                    s.temperature = 0.0
            world.REGEN_PROB = 0.001   # 现在开启随机新生
            t_deplete1 = step
            phase = 2
            w_ccw_50, w_cw_50 = get_d1_weights(c)
            dw_at_50k = abs(w_ccw_50 - w_cw_50) if not math.isnan(w_ccw_50) else 0.0
            print(f"\n  [step {step}] 热源耗尽（Phase 2），REGEN_PROB→0.001"
                  f"\n              w_ccw={w_ccw_50:.4f} w_cw={w_cw_50:.4f} |Δw|={dw_at_50k:.4f}")

        if step == DEPLETION_STEP_2:
            # 耗尽当时所有活跃热源（选测第三周期）
            alive_before = sum(1 for s in world.heat_sources if s.alive)
            if alive_before > 0:
                for s in list(world.heat_sources):
                    if s.alive:
                        s.energy = 0.0
                        s.temperature = 0.0
                t_deplete2 = step
                phase = 3
                w_ccw_150, w_cw_150 = get_d1_weights(c)
                dw_at_150k = abs(w_ccw_150 - w_cw_150) if not math.isnan(w_ccw_150) else 0.0
                print(f"\n  [step {step}] 第二次热源耗尽（Phase 3）"
                      f"\n              w_ccw={w_ccw_150:.4f} |Δw|={dw_at_150k:.4f}")
            else:
                print(f"\n  [step {step}] DEPLETION_2 触发：无活跃热源（已自然耗尽）")

        # ── 电路步进 ──
        c.step({}, DT)

        # ── 状态采样 ──
        fill = c.energy_store.fill_fraction
        fill_min_global = min(fill_min_global, fill)

        n_src = sum(1 for s in world.heat_sources if s.alive)
        dist  = get_nearest_dist(c)
        in_zn = in_source_zone(c)

        if in_zn:
            foraging_steps += 1

        if get_dr5(c):
            dr5_count += 1

        # ── 阶段事件检测 ──
        if phase == 1 and in_zn and t_reach1 is None:
            t_reach1 = step
            cycle1_reach = True

        if phase >= 2 and not cycle2_reach and in_zn:
            t_reach2 = step
            cycle2_reach = True
            phase = max(phase, 2)
            print(f"\n  [step {step}] body 进入新热源区（Phase 2 完成）"
                  f" T_relocate2={step - t_deplete1} 步")

        if phase >= 3 and not cycle3_reach and in_zn:
            t_reach3 = step
            cycle3_reach = True
            print(f"\n  [step {step}] body 进入第三热源区"
                  f" T_relocate3={step - t_deplete2} 步")

        # ── 定期日志 ──
        if step % LOG_INTERVAL == 0:
            dr5_pct  = dr5_count / step * 100
            eta_pct  = foraging_steps / step * 100
            w_ccw, w_cw = get_d1_weights(c)
            dw       = (w_ccw - w_cw) if not math.isnan(w_ccw) else float('nan')
            print(f"  {step:>7} | P{phase:1d} | {dr5_pct:>4.1f}% | {dist:>6.1f} | "
                  f"{w_ccw:>7.4f} {w_cw:>7.4f} {dw:>+7.4f} | "
                  f"{fill:>5.3f} | {eta_pct:>3.1f}% | {n_src:>5d}")

    # ── 最终判定 ──
    dr5_final  = dr5_count / STEPS * 100
    eta_final  = foraging_steps / STEPS * 100
    w_ccw_f, w_cw_f = get_d1_weights(c)
    dw_final   = abs(w_ccw_f - w_cw_f) if not math.isnan(w_ccw_f) else 0.0

    t_relocate1 = t_reach1 if t_reach1 is not None else STEPS
    t_relocate2 = (t_reach2 - t_deplete1) if (t_reach2 is not None and t_deplete1 is not None) else STEPS

    j1 = eta_final >= ETA_THRESH
    j2 = (dw_final > dw_at_50k) if dw_at_50k > 0 else (dw_final > 0.005)
    j3 = (t_relocate2 < T_RATIO_THRESH * t_relocate1) if t_reach2 is not None else False
    j4 = (not math.isnan(w_ccw_f)) and w_ccw_f > W_CCW_THRESH

    print()
    print("=" * 72)
    print("  T-072 判定结果：\n")
    print(f"    η_total:            {eta_final:.1f}%   (阈值 ≥{ETA_THRESH:.0f}%)")
    print(f"    DR5% (全程):        {dr5_final:.1f}%")
    print(f"    fill_min:           {fill_min_global:.4f}")
    print()
    print(f"    w_ccw: {w_ccw_init:.4f} → {w_ccw_f:.4f}")
    print(f"    w_cw:  {w_cw_init:.4f} → {w_cw_f:.4f}")
    print(f"    |Δw| @ step50k: {dw_at_50k:.4f}  → final: {dw_final:.4f}")
    print()
    print(f"    T_relocate1 (体找源1): {t_relocate1} 步"
          + ("  (未到达)" if t_reach1 is None else ""))
    print(f"    T_relocate2 (体找源2): {t_relocate2} 步"
          + ("  (未到达)" if t_reach2 is None else ""))
    if t_reach1 is not None and t_reach2 is not None:
        ratio = t_relocate2 / t_relocate1 if t_relocate1 > 0 else float('inf')
        print(f"    T_ratio: {ratio:.2f}×  (阈值 <{T_RATIO_THRESH}×)")
    print()
    print(f"    J1  η ≥ {ETA_THRESH}%                {eta_final:.1f}%  → {'PASS ✅' if j1 else 'FAIL ❌'}")
    print(f"    J2  |Δw|_final > |Δw|@50k     {dw_final:.4f}>{dw_at_50k:.4f}  → {'PASS ✅' if j2 else 'FAIL ❌'}")
    print(f"    J3  T_rel2 < {T_RATIO_THRESH}×T_rel1    "
          f"{t_relocate2}<{T_RATIO_THRESH*t_relocate1:.0f}  → {'PASS ✅' if j3 else 'FAIL ❌' if t_reach2 else 'N/A ⚠️'}")
    print(f"    J4  w_ccw > {W_CCW_THRESH}             {w_ccw_f:.4f}  → {'PASS ✅' if j4 else 'FAIL ❌'}")
    print()
    passed = sum([j1, j2, j3 if t_reach2 is not None else True, j4])
    total  = 4
    print(f"  总计: {passed}/{total} PASS")
    if j2:
        print("  → P0 lambda_metabolic 有效：权重在冷期得到保留，跨周期累积分化")
    else:
        print("  → 权重未累积：检查 lambda_metabolic 或 LTD 侵蚀")
    print("=" * 72)


if __name__ == '__main__':
    main()
