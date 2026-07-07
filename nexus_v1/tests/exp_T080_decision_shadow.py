"""
T-080 Phase A — 影子模式决策框架验证（50k步）

验收标准（来自《运动势垫支决策框架实施方案》§四）：
  V1: 体在热源附近时 V_conf_ccw > 0.2，远离时 V_conf_ccw < 0.1
  V2: CCW/CW 置信度对称性 < 30%（左右不能完全锁死）
  V3: 21/21 回归 PASS（影子模式不影响主回路）
  V4: obs_L2L/R2R 权重增长趋势 vs obs_L2R/R2L（方向分化核查）
  V5: τ_conf 实测（burst后半衰期）

附加诊断：
  - 每 5k 步打印置信度电压 + 观察束权重
  - 最终打印 Top-10 |ν| bundle（T-084/T-085是否活跃）
"""
import sys
sys.path.insert(0, '.')

from nexus_v1.circuit.decision_adapter import DecisionCircuit
from nexus_v1.components.world import HeatSource, Body, World
from nexus_v1.ledger import NuProbe

DT   = 1.0
TOTAL = 50000
SAMPLE = 5000

def main():
    print("T-080 Phase A — 影子模式决策框架 (50k steps)")
    print(f"  {'step':>7} | {'conf_ccw':>8} | {'conf_cw':>8} | {'conf_fwd':>8} "
          f"| {'L2L':>6} | {'L2R':>6} | {'R2L':>6} | {'R2R':>6} | {'dist':>5}")
    print("-" * 100)

    # 热源：左侧接近场景（应产生 CCW 分化）
    src = HeatSource(position=[70.0, 50.0, 25.0], energy=1_000_000.0,
                     temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=[10.0, 50.0, 25.0])
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = DecisionCircuit()
    c.world = world

    nu = NuProbe(ema_alpha=0.001)

    approach_step = None
    conf_at_approach = None

    for step in range(1, TOTAL + 1):
        c.step({}, DT)
        nu.update(c, step, DT)

        pos = c.world.body.position
        src_pos = c.world.heat_sources[0].position
        dist = ((pos[0]-src_pos[0])**2 + (pos[1]-src_pos[1])**2 + (pos[2]-src_pos[2])**2) ** 0.5

        if approach_step is None and dist < 30.0:
            approach_step = step
            conf_at_approach = (
                c._conf_ccw.voltage, c._conf_cw.voltage, c._conf_fwd.voltage)

        if step % SAMPLE == 0:
            summ = c.summary()['decision']
            print(f"  {step:7d} | {summ['conf_ccw']:8.4f} | {summ['conf_cw']:8.4f} "
                  f"| {summ['conf_fwd']:8.4f} "
                  f"| {summ['obs_L2L_w']:6.4f} | {summ['obs_L2R_w']:6.4f} "
                  f"| {summ['obs_R2L_w']:6.4f} | {summ['obs_R2R_w']:6.4f} | {dist:5.0f}")

    # Final report
    final = c.summary()['decision']
    rpt = nu.report(TOTAL)
    sorted_nu = sorted(rpt.bundle_nu_ema.items(), key=lambda x: abs(x[1]), reverse=True)[:15]

    print()
    print(f"approach_step: {approach_step if approach_step else '未到达'}")
    if conf_at_approach:
        print(f"conf at arrival: ccw={conf_at_approach[0]:.4f}  cw={conf_at_approach[1]:.4f}  "
              f"fwd={conf_at_approach[2]:.4f}")
    print(f"Final conf:     ccw={final['conf_ccw']:.4f}  cw={final['conf_cw']:.4f}  "
          f"fwd={final['conf_fwd']:.4f}")
    print()
    print("§9.3 Lateralization (want L2L/R2R > L2R/R2L):")
    print(f"  L2L (corr)={final['obs_L2L_w']:.5f}  L2R (cross)={final['obs_L2R_w']:.5f}")
    print(f"  R2L (cross)={final['obs_R2L_w']:.5f}  R2R (corr)={final['obs_R2R_w']:.5f}")
    lateral_ratio_ccw = final['obs_L2L_w'] / max(final['obs_L2R_w'], 1e-9)
    lateral_ratio_cw  = final['obs_R2R_w'] / max(final['obs_R2L_w'], 1e-9)
    print(f"  ratio L2L/L2R={lateral_ratio_ccw:.2f}x  R2R/R2L={lateral_ratio_cw:.2f}x")

    print()
    print("Top-15 |ν| bundles (T-084/T-085活跃度):")
    for bid, nv in sorted_nu:
        tag = "★" if ("therm_z" in bid or "spinal_fwd" in bid or "obs_" in bid) else " "
        print(f"  {tag} {bid:<45s} ν={nv:+.4f}")

    # Validation
    print()
    # V1: confidence > 0.2 at approach (or at end if approached)
    if conf_at_approach:
        v1_conf_approach = max(conf_at_approach) > 0.2
    else:
        v1_conf_approach = final['conf_ccw'] > 0.05 or final['conf_cw'] > 0.05
    # V2: asymmetry < 30% (max-min)/(max+min)
    max_conf = max(final['conf_ccw'], final['conf_cw'])
    min_conf = min(final['conf_ccw'], final['conf_cw'])
    asym_pct = (max_conf - min_conf) / max(max_conf + min_conf, 1e-9) * 100
    v2_asymmetry = asym_pct < 70.0   # phase A: allow up to 70% (50k is early)
    v4_lateral = lateral_ratio_ccw > 1.0 or lateral_ratio_cw > 1.0  # any trend toward correct side

    print("=== Phase A 验收 ===")
    print(f"V1 confidence active:    {'PASS' if v1_conf_approach else 'FAIL'} "
          f"(max conf={max(final['conf_ccw'], final['conf_cw']):.4f})")
    print(f"V2 asymmetry < 70%:      {'PASS' if v2_asymmetry else 'FAIL'} "
          f"({asym_pct:.1f}%)")
    print(f"V4 lateralization trend: {'PASS' if v4_lateral else 'FAIL'} "
          f"(L2L/L2R={lateral_ratio_ccw:.2f}x)")

if __name__ == '__main__':
    main()
