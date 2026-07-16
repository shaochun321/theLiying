"""T3-C1 子任务1 诊断脚本：动态比例变换 + 比例交叉。

方案依据：`cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md`
第二十节 20.2 第1点。批判十一（`document - 2026-07-17T001314.696.md`）指出
`GradedPotentialRelay` 的"任意时刻比例保真"表述过强——中继实际是卷积
`V_i(t)=∫h(t-s)y_i(s)ds`，只有固定历史比例下才有 `V_a(t)=c·V_b(t)`。

本脚本两部分：
1. 分段驱动 1:1→2:1→1:3→1:1，验证中继输出 `z_i(t)` 与独立数值卷积基准
   `ẑ_i(t)=(h_τ*y_i)(t)`（脚本内独立重新实现，不调用 `GradedPotentialRelay`
   本体，作为实现正确性交叉检验）是否一致——验证的是"中继是否正确实现了
   自己声明的 RC 核动力学"，不是重新论证"瞬时无记忆"这个已知不成立的假设。
2. 比例交叉（y_a>y_b → y_a<y_b）：测量翻转延迟/是否过冲/是否存在错误
   双占优时长，给 τ_r 一个真正可观测、可标定的时间尺度。

运行：PYTHONIOENCODING=utf-8 PYTHONHASHSEED=0 python -m nexus_v1.tests._diag_t3_c1_dynamic_ratio
"""

from __future__ import annotations

import math

from nexus_v1.components.graded_potential_relay import (
    GradedPotentialRelay, DEFAULT_CAPACITANCE, DEFAULT_R_LEAK, DEFAULT_G_R, DEFAULT_A_MAX,
)

DT = 0.001


def _reference_convolution(y_trajectory, dt, r_leak=DEFAULT_R_LEAK,
                            capacitance=DEFAULT_CAPACITANCE, g_r=DEFAULT_G_R,
                            a_max=DEFAULT_A_MAX):
    """独立重新实现的 RC 核卷积基准 ẑ_i(t)（不调用 GradedPotentialRelay 本体，
    只依据其 docstring 声明的动力学方程 τ_r·dV/dt=-V+k_i·y_i 重新推导离散
    递推：Q_{n+1}=(Q_n+y_n·dt)·decay，decay=exp(-dt/τ)，与 Capacitor.inject()
    +leak() 的调用顺序保持数学等价，但代码路径独立，用于交叉验证实现正确性。
    """
    tau = r_leak * capacitance
    decay = math.exp(-dt / max(tau, 0.01))
    q = 0.0
    out = []
    for y in y_trajectory:
        q = (q + y * dt) * decay
        v = q / capacitance
        a = max(0.0, min(g_r * v, a_max))
        out.append(a)
    return out


def part1_dynamic_ratio_matches_kernel():
    print("[T3-C1-1a] 动态比例：中继输出 z_i(t) vs 独立卷积基准 ẑ_i(t)")
    segments = [(0.10, 0.10, 150), (0.20, 0.10, 150), (0.10, 0.30, 150), (0.10, 0.10, 150)]

    relay_a, relay_b = GradedPotentialRelay(), GradedPotentialRelay()
    traj_a, traj_b = [], []
    z_a_list, z_b_list = [], []
    for (ya, yb, n) in segments:
        for _ in range(n):
            traj_a.append(ya)
            traj_b.append(yb)
            z_a_list.append(relay_a.step(ya, DT))
            z_b_list.append(relay_b.step(yb, DT))

    ref_a = _reference_convolution(traj_a, DT)
    ref_b = _reference_convolution(traj_b, DT)

    max_err_a = max(abs(z - r) for z, r in zip(z_a_list, ref_a))
    max_err_b = max(abs(z - r) for z, r in zip(z_b_list, ref_b))
    print(f"  z_a vs ẑ_a 最大绝对误差: {max_err_a:.3e}")
    print(f"  z_b vs ẑ_b 最大绝对误差: {max_err_b:.3e}")
    print(f"  判读：误差应在浮点精度量级(<1e-9)，证实中继正确实现了 RC 核卷积。")

    print()
    print("  分段末尾比值对照（瞬时y比 vs 中继z比，验证批判十一①的滞后现象仍然复现）：")
    idx = 0
    for (ya, yb, n) in segments:
        idx += n
        y_ratio = ya / yb if yb else float("nan")
        z_ratio = z_a_list[idx - 1] / z_b_list[idx - 1] if z_b_list[idx - 1] else float("nan")
        print(f"    段末(t={idx}) y比={y_ratio:.3f}  z比={z_ratio:.3f}")

    return max_err_a, max_err_b


def part2_crossover_timing():
    print()
    print("[T3-C1-1b] 比例交叉：y_a>y_b → y_a<y_b 翻转延迟/过冲/双占优")
    # 前段 y_a 占优（0.30 vs 0.10），后段反转（0.10 vs 0.30）
    relay_a, relay_b = GradedPotentialRelay(), GradedPotentialRelay()
    n_pre, n_post = 300, 600
    flip_step = None
    max_overshoot_ratio = 0.0
    z_a = z_b = 0.0
    for i in range(n_pre):
        z_a = relay_a.step(0.30, DT)
        z_b = relay_b.step(0.10, DT)
    pre_dominant = "a" if z_a > z_b else "b"

    history = []
    for i in range(n_post):
        z_a = relay_a.step(0.10, DT)
        z_b = relay_b.step(0.30, DT)
        history.append((i, z_a, z_b))
        if flip_step is None and z_b > z_a:
            flip_step = i

    post_dominant = "a" if z_a > z_b else "b"
    # 过冲：翻转后 z_b 是否短暂超过其自身最终稳态附近的合理范围（用后半段均值近似稳态参考）
    tail_zb = [zb for (_, _, zb) in history[-100:]]
    steady_zb_approx = sum(tail_zb) / len(tail_zb)
    peak_zb = max(zb for (_, _, zb) in history)
    overshoot = (peak_zb - steady_zb_approx) / steady_zb_approx if steady_zb_approx > 0 else 0.0

    print(f"  翻转前占优通道: {pre_dominant}；翻转后占优通道: {post_dominant}")
    print(f"  翻转延迟（新占优通道反超所需步数）: {flip_step} 步（占 τ_r={DEFAULT_R_LEAK*DEFAULT_CAPACITANCE:.2f} 的比例请对照 dt={DT}）")
    print(f"  过冲幅度: {overshoot*100:.2f}%（相对后段近似稳态值）")
    print(f"  判读：翻转延迟给出 τ_r 在当前 dt 约定下的实际可观测时间尺度。")

    return flip_step, overshoot


if __name__ == "__main__":
    part1_dynamic_ratio_matches_kernel()
    part2_crossover_timing()
