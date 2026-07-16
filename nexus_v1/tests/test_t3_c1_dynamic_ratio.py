"""T-C1D-1~3：T3-C1 子任务1 动态比例变换 + 比例交叉正式验收。

方案依据：第二十节 20.2 第1点。诊断脚本 `_diag_t3_c1_dynamic_ratio.py` 已确认：
①中继输出与独立数值卷积基准误差 0.000e+00（实现正确性交叉验证通过）；
②比例交叉存在真实的翻转延迟（260步/300步窗口）与可观测过冲（6.45%）——
`GradedPotentialRelay` 的比例保真是"固定历史比例"下的精确特例，动态输入下
表现为批判十一②定义的窗口化射影关系 `r_ρ^τ`，本文件把该结论转为正式回归测试。
"""

from __future__ import annotations

import math

from nexus_v1.components.graded_potential_relay import (
    GradedPotentialRelay, DEFAULT_CAPACITANCE, DEFAULT_R_LEAK, DEFAULT_G_R, DEFAULT_A_MAX,
)

DT = 0.001
_KERNEL_MATCH_TOL = 1e-9


def _reference_convolution(y_trajectory, dt, r_leak=DEFAULT_R_LEAK,
                            capacitance=DEFAULT_CAPACITANCE, g_r=DEFAULT_G_R,
                            a_max=DEFAULT_A_MAX):
    tau = r_leak * capacitance
    decay = math.exp(-dt / max(tau, 0.01))
    q = 0.0
    out = []
    for y in y_trajectory:
        q = (q + y * dt) * decay
        v = q / capacitance
        out.append(max(0.0, min(g_r * v, a_max)))
    return out


def test_c1d_1_relay_matches_independent_convolution_kernel():
    """T-C1D-1: 中继输出与独立重新实现的RC核卷积基准误差在浮点精度内。"""
    segments = [(0.10, 0.10, 150), (0.20, 0.10, 150), (0.10, 0.30, 150), (0.10, 0.10, 150)]
    relay_a, relay_b = GradedPotentialRelay(), GradedPotentialRelay()
    traj_a, traj_b, z_a_list, z_b_list = [], [], [], []
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
    assert max_err_a < _KERNEL_MATCH_TOL, f"z_a 偏离独立卷积基准: {max_err_a}"
    assert max_err_b < _KERNEL_MATCH_TOL, f"z_b 偏离独立卷积基准: {max_err_b}"


def test_c1d_2_dynamic_ratio_lags_instant_input_ratio():
    """T-C1D-2: 动态比例场景下，中继输出比不应精确等于瞬时输入比（证伪"瞬时保真"
    的过强表述，与批判十一①的实测复现一致——中继表现窗口化历史参与关系）。
    固定比例场景（T-C1R）已证 eps_ratio=0，此处验证动态场景 eps_ratio 明显非零。
    """
    relay_a, relay_b = GradedPotentialRelay(), GradedPotentialRelay()
    for _ in range(150):
        relay_a.step(0.10, DT)
        relay_b.step(0.10, DT)
    z_a = z_b = 0.0
    for _ in range(150):
        z_a = relay_a.step(0.20, DT)  # 切换为 2:1
        z_b = relay_b.step(0.10, DT)
    y_ratio = 2.0
    z_ratio = z_a / z_b
    eps_ratio = abs(math.log(z_ratio / y_ratio))
    assert eps_ratio > 0.05, (
        f"动态比例切换后 eps_ratio={eps_ratio} 过小，"
        f"与批判十一①预期的滞后现象不符，需要重新核实中继动力学是否被意外改动")


def test_c1d_3_crossover_flip_and_bounded_overshoot():
    """T-C1D-3: 比例交叉后新占优通道确实反超（在给定窗口内），且过冲幅度有界
    （不应出现失控震荡——RC一阶系统本身不应产生大幅过冲，过冲只应来自离散化
    误差量级，此处用 50% 作为明显失控的粗粒度上限）。
    """
    relay_a, relay_b = GradedPotentialRelay(), GradedPotentialRelay()
    for _ in range(300):
        z_a = relay_a.step(0.30, DT)
        z_b = relay_b.step(0.10, DT)
    assert z_a > z_b  # 翻转前 a 占优

    flip_step = None
    history = []
    for i in range(600):
        z_a = relay_a.step(0.10, DT)
        z_b = relay_b.step(0.30, DT)
        history.append((z_a, z_b))
        if flip_step is None and z_b > z_a:
            flip_step = i

    assert flip_step is not None, "600步窗口内未观测到翻转，τ_r标定可能需要调整"
    assert z_b > z_a  # 窗口结束时 b 占优（新占优通道确实反超）

    tail_zb = [zb for (_, zb) in history[-100:]]
    steady_zb_approx = sum(tail_zb) / len(tail_zb)
    peak_zb = max(zb for (_, zb) in history)
    overshoot = (peak_zb - steady_zb_approx) / steady_zb_approx if steady_zb_approx > 0 else 0.0
    assert 0.0 <= overshoot < 0.5, f"过冲幅度异常: {overshoot}"


if __name__ == "__main__":
    test_c1d_1_relay_matches_independent_convolution_kernel()
    test_c1d_2_dynamic_ratio_lags_instant_input_ratio()
    test_c1d_3_crossover_flip_and_bounded_overshoot()
    print("T-C1D-1~3 ALL PASS")
