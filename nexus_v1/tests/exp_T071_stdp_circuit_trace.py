"""
T-071：STDP断路诊断

目标：找到 STDP 权重变化（|Δw|=0.3）但 DR5=50%（随机基线）的根本原因。
      通过测量各节点激活值和电流比，定位信号断路位置。

信号链（D1学习弧）：
    relay_left → phasic_left → [D1 STDP bundle] → spinal_ccw
              → bundle_spinal_ccw_to_yaw → yaw_ccw_neuron → body.angular_velocity

对照（HC-016 反射弧）：
    thermo_left → bundle_left_to_yaw → yaw_ccw_neuron

断路假说：
    H-A: spinal_ccw ≈ 0 即使 phasic_left > 0  →  D1 bundle 增益不足
    H-B: I_spinal_to_yaw << I_thermo_to_yaw (>10×)  →  反射弧压制学习弧
    H-C: yaw_ccw ≈ 0 即使 spinal_ccw > 0  →  spinal→yaw 阈值过高
    H-D: motor_angular_vel ≈ 0 即使 yaw_ccw > 0  →  yaw→行为传导弱

判定标准：
    J1: phasic_left 峰值激活 > 0.01（接近热源时有信号输入）
    J2: spinal_ccw 峰值激活 > 0.01（D1 bundle 传递信号）
    J3: yaw_ccw 峰值激活 > 0.01（yaw 层有激活）
    J4: I_spinal_peak / I_thermo_peak > 0.01（学习弧电流至少 1% 反射弧）

    额外输出：H-A/B/C/D 明确标注

步数：5000（τ_approach≈1931，体验一次完整接近过程）
"""
import sys
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

DT = 1.0

def main():
    print("="*72)
    print("  T-071: STDP断路诊断")
    print("  信号链: relay_L→phasic_L→[D1]→spinal_ccw→yaw_ccw 对照 thermo_L→yaw_ccw")
    print("="*72)

    src = HeatSource(position=[70.0, 50.0, 25.0], energy=1_000_000.0,
                     temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=[10.0, 50.0, 25.0])
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world

    STEPS = 5000
    SAMPLE = 100  # 每100步采样一次

    # 读取所需对象
    relay_left  = c.somatosensory.relays.get('left')
    thermo_left = c.somatosensory.thermo_inputs.get('left')
    phasic_left = c.phasic_left
    spinal_ccw  = c.spinal_ccw
    yaw_ccw     = c.yaw_ccw_neuron
    bundle_d1   = c.bundle_d1_phasic_left_to_spinal_ccw
    bundle_sp2y = c.bundle_spinal_ccw_to_yaw
    bundle_th2y = c.bundle_left_to_yaw
    da_neurons_list = list(c.da_neurons.values()) if hasattr(c, 'da_neurons') else []
    da_neuron   = da_neurons_list[0] if da_neurons_list else None

    # 采样日志
    log_relay_l  = []
    log_thermo_l = []
    log_phasic_l = []
    log_spinal_c = []
    log_yaw_c    = []
    log_omega    = []
    log_d1_w     = []
    log_da_ema   = []
    log_fill     = []
    log_dist     = []

    print(f"\n  {'step':>6} | {'dist':>6} | {'thermo_L':>8} | {'relay_L':>8} | {'phasic_L':>8} | "
          f"{'spinal_C':>8} | {'yaw_ccw':>8} | {'d1_w':>6} | {'DA_ema':>7}")
    print("  " + "-" * 95)

    for step in range(1, STEPS + 1):
        c.step({}, DT)

        if step % SAMPLE == 0:
            dist = ((c.world.body.position[0] - 70.0)**2 +
                    (c.world.body.position[1] - 50.0)**2) ** 0.5
            rl  = relay_left.activation  if relay_left  else 0.0
            tl  = thermo_left.activation if thermo_left else 0.0
            pl  = phasic_left.activation
            sc  = spinal_ccw.activation
            yc  = yaw_ccw.activation
            w   = bundle_d1.mean_weight()
            da_ema = da_neuron.activation if da_neuron else getattr(c, '_da_ema', 0.0)
            fill   = c.energy_store.fill_fraction if hasattr(c, 'energy_store') else 0.0

            log_relay_l.append(rl)
            log_thermo_l.append(tl)
            log_phasic_l.append(pl)
            log_spinal_c.append(sc)
            log_yaw_c.append(yc)
            log_omega.append(c.world.body.angular_velocity)
            log_d1_w.append(w)
            log_da_ema.append(da_ema)
            log_fill.append(fill)
            log_dist.append(dist)

            print(f"  {step:>6} | {dist:>6.1f} | {tl:>8.4f} | {rl:>8.4f} | {pl:>8.4f} | "
                  f"{sc:>8.4f} | {yc:>8.4f} | {w:>6.4f} | {da_ema:>7.4f}")

    # 统计
    def safe_max(lst): return max(lst) if lst else 0.0
    def safe_mean(lst): return sum(lst)/len(lst) if lst else 0.0

    relay_peak  = safe_max([abs(x) for x in log_relay_l])
    thermo_peak = safe_max([abs(x) for x in log_thermo_l])
    phasic_peak = safe_max([abs(x) for x in log_phasic_l])
    spinal_peak = safe_max([abs(x) for x in log_spinal_c])
    yaw_peak    = safe_max([abs(x) for x in log_yaw_c])
    d1_w_final  = log_d1_w[-1] if log_d1_w else 0.0

    # 电流估算（比例：w × act × sg）
    # bundle_spinal_ccw_to_yaw：weight，sg，source=spinal_ccw
    sp2y_w  = bundle_sp2y.mean_weight()
    sp2y_sg = bundle_sp2y.config.synapse_gain
    th2y_w  = bundle_th2y.mean_weight() if bundle_th2y else 0.0
    th2y_sg = bundle_th2y.config.synapse_gain if bundle_th2y else 1.0

    I_spinal_peak = spinal_peak * sp2y_w * abs(sp2y_sg)
    I_thermo_peak = thermo_peak * th2y_w * abs(th2y_sg)
    ratio = I_spinal_peak / max(I_thermo_peak, 1e-9)

    print(f"\n  ── 峰值统计 ──")
    print(f"  thermo_left.act 峰值:   {thermo_peak:.4f}")
    print(f"  relay_left.act 峰值:    {relay_peak:.4f}")
    print(f"  phasic_left.act 峰值:   {phasic_peak:.4f}")
    print(f"  spinal_ccw.act 峰值:    {spinal_peak:.4f}")
    print(f"  yaw_ccw.act 峰值:       {yaw_peak:.4f}")
    print(f"  D1 bundle weight 末值:  {d1_w_final:.4f}")
    print()
    print(f"  ── 电流比（估算） ──")
    print(f"  I_spinal→yaw (≈spinal×{sp2y_w:.2f}×{sp2y_sg:.1f}): {I_spinal_peak:.4e}")
    print(f"  I_thermo→yaw (≈thermo×{th2y_w:.2f}×{th2y_sg:.1f}): {I_thermo_peak:.4e}")
    print(f"  比值 I_spinal/I_thermo: {ratio:.4f} ({ratio*100:.2f}%)")
    print()

    j1 = phasic_peak > 0.01
    j2 = spinal_peak > 0.01
    j3 = yaw_peak    > 0.01
    j4 = ratio > 0.01  # 学习弧至少达到反射弧电流 1%

    print(f"  J1  phasic_left峰值>0.01    {phasic_peak:.4f}  → {'PASS ✅' if j1 else 'FAIL ❌'}")
    print(f"  J2  spinal_ccw峰值>0.01     {spinal_peak:.4f}  → {'PASS ✅' if j2 else 'FAIL ❌'}")
    print(f"  J3  yaw_ccw峰值>0.01        {yaw_peak:.4f}  → {'PASS ✅' if j3 else 'FAIL ❌'}")
    print(f"  J4  I_spinal/I_thermo>1%    {ratio:.4f}  → {'PASS ✅' if j4 else 'FAIL ❌'}")

    passed = sum([j1, j2, j3, j4])
    print(f"\n  总计: {passed}/4 PASS")
    print()

    # 断路结论
    print(f"  ── 断路位置诊断 ──")
    if not j1:
        print(f"  ❌ H-A: phasic_left 无信号。relay→phasic 通路断路（W_P={0.02} 增益不足？）")
    elif not j2:
        print(f"  ❌ H-A: phasic_left 有信号({phasic_peak:.3f}) 但 spinal_ccw≈0。D1 bundle 增益/weight不足。")
        print(f"          D1 weight={d1_w_final:.4f}，检查 D1 学习速率和 DA gating。")
    elif not j3:
        print(f"  ❌ H-C: spinal_ccw 有信号({spinal_peak:.3f}) 但 yaw_ccw≈0。")
        print(f"          sp2y_w={sp2y_w:.4f}，检查 bundle_spinal_ccw_to_yaw 增益。")
    elif not j4:
        print(f"  ❌ H-B: 学习弧电流 ({I_spinal_peak:.2e}) << 反射弧电流 ({I_thermo_peak:.2e})。")
        print(f"          比值={ratio:.4f}（<1%）。D1弧被 thermo→yaw 反射弧压制。")
    else:
        print(f"  ✅ 所有链路正常。DR5=50% 可能是方向选择性问题（两弧对称，无偏置）。")
        print(f"     建议检查：w_ccw 与 w_cw 是否同步上升（双向强化，无差异化）？")
    print("="*72)


if __name__ == '__main__':
    main()
