"""T-C1R-1~4：T3-C1R 路径 R-A/R-B 读出机制判别验收。

方案依据：`cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md`
第十九节 19.3。诊断脚本 `_diag_t3_c1r_readout_ab.py`（固定
`PYTHONHASHSEED=0` 复现）已扫描 1:1/2:1/3:1/4:1 × α∈{0.25,...,8} 共 24
组场景，结果：R-B（`GradedPotentialRelay`）eps_ratio 全部精确为 0.0000，
R-A（现有二次 channel 降增益）eps_ratio 最大 1.4157 且非单调（部分饱和
干扰）。本文件把该结论转为正式回归测试。

运行：PYTHONIOENCODING=utf-8 PYTHONHASHSEED=0 python -m nexus_v1.tests.test_t3_c1r_readout_ab
"""

from __future__ import annotations

import math

from nexus_v1.relations.ratio_r_part import RPartCircuitT3, DT
from nexus_v1.components.neuron import Neuron, NeuronConfig, ChannelConfig
from nexus_v1.components.graded_potential_relay import GradedPotentialRelay

N_STEPS = 300
_RA_GM_LOWERED = 2.0

# R-B 是 LTI 系统，比例保真理论上精确成立；容差只吸收浮点误差，非物理容差。
_EPS_RATIO_TOL_RB = 1e-9
# R-A 用于证明"即使降增益，二次门控仍不具备比例保真"——判定它在扫描网格里
# 至少有若干场景明显偏离（诊断脚本实测最大 1.4157），门槛取远低于该值。
_EPS_RATIO_DISQUALIFY_THRESHOLD_RA = 0.05


def _ra_channel_config(label: str) -> NeuronConfig:
    return NeuronConfig(
        neuron_id=f"c1r_ra_channel_{label}",
        region=0x01,
        spiking=False,
        capacitance=0.05,
        r_leak=5.0,
        inertia=1.0,
        channels=[ChannelConfig(name="default", v_threshold=0.0, gm=_RA_GM_LOWERED)],
    )


def _drive_and_measure(i_a: float, i_b: float, n_steps: int = N_STEPS) -> dict:
    circuit = RPartCircuitT3()
    ra_a = Neuron(_ra_channel_config("a"))
    ra_b = Neuron(_ra_channel_config("b"))
    rb_a = GradedPotentialRelay()
    rb_b = GradedPotentialRelay()

    y_a = y_b = 0.0
    o_ra_a = o_ra_b = o_rb_a = o_rb_b = 0.0
    for _ in range(n_steps):
        circuit.rpart_xi_a.pre_trace = i_a
        circuit.rpart_xi_b.pre_trace = i_b
        r = circuit.step_rpart(dt=DT)
        y_a, y_b = r["y_a"], r["y_b"]

        ra_a.step(y_a, DT)
        ra_b.step(y_b, DT)
        o_ra_a, o_ra_b = ra_a.activation, ra_b.activation

        o_rb_a = rb_a.step(y_a, DT)
        o_rb_b = rb_b.step(y_b, DT)

    return {
        "y_a": y_a, "y_b": y_b,
        "o_ra_a": o_ra_a, "o_ra_b": o_ra_b,
        "o_rb_a": o_rb_a, "o_rb_b": o_rb_b,
    }


def _eps_ratio(o_a: float, o_b: float, y_a: float, y_b: float) -> float:
    return abs(math.log((o_a / o_b) / (y_a / y_b)))


_SCAN_GRID = [
    (ra, rb, alpha)
    for (ra, rb) in [(1, 1), (2, 1), (3, 1), (4, 1)]
    for alpha in [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
]


def test_c1r_1_rb_ratio_fidelity_across_grid():
    """T-C1R-1: R-B 在全部 24 组 (比例×共同放大) 场景下比例保真（eps_ratio≈0）。"""
    for (ra, rb, alpha) in _SCAN_GRID:
        m = _drive_and_measure(ra * alpha, rb * alpha)
        eps_rb = _eps_ratio(m["o_rb_a"], m["o_rb_b"], m["y_a"], m["y_b"])
        assert eps_rb < _EPS_RATIO_TOL_RB, (
            f"R-B eps_ratio 超出容差: ratio={ra}:{rb} alpha={alpha} eps={eps_rb}")


def test_c1r_2_rb_output_bounded_and_nonneg():
    """T-C1R-2: R-B 输出非负且不超过 a_max（大幅值场景下也不例外）。"""
    relay = GradedPotentialRelay()
    for _ in range(N_STEPS):
        o = relay.step(2.61, dt=DT)  # T3-C0 实测的较大 y 值场景
    assert 0.0 <= o <= relay.a_max


def test_c1r_3_rb_silent_zero_ratio():
    """T-C1R-3: 静默(y_a=y_b=0)时 R-B 输出精确为 0，不产生虚假比例。"""
    relay_a = GradedPotentialRelay()
    relay_b = GradedPotentialRelay()
    for _ in range(N_STEPS):
        o_a = relay_a.step(0.0, dt=DT)
        o_b = relay_b.step(0.0, dt=DT)
    assert o_a == 0.0
    assert o_b == 0.0


def test_c1r_4_ra_control_group_disqualified():
    """T-C1R-4: R-A（现有二次 channel 降增益）对照组——扫描网格中至少存在
    明显偏离真值比例的场景（disqualify 阈值 0.05），确认降增益不能修复
    二次门控的传递函数类型问题（方案十九节 19.1 第②点数学结论的实测确认）。
    """
    max_eps_ra = 0.0
    for (ra, rb, alpha) in _SCAN_GRID:
        m = _drive_and_measure(ra * alpha, rb * alpha)
        eps_ra = _eps_ratio(m["o_ra_a"], m["o_ra_b"], m["y_a"], m["y_b"])
        max_eps_ra = max(max_eps_ra, eps_ra)
    assert max_eps_ra > _EPS_RATIO_DISQUALIFY_THRESHOLD_RA, (
        f"R-A 对照组预期应显著偏离真值比例，实测最大eps_ratio={max_eps_ra}"
        f"未超过判定阈值——需要重新核实二次门控假设是否仍然成立")


if __name__ == "__main__":
    test_c1r_1_rb_ratio_fidelity_across_grid()
    test_c1r_2_rb_output_bounded_and_nonneg()
    test_c1r_3_rb_silent_zero_ratio()
    test_c1r_4_ra_control_group_disqualified()
    print("T-C1R-1~4 ALL PASS")
