"""T3-C1R 诊断脚本：路径 R-A（现有二次 channel，降增益）vs 路径 R-B
（`GradedPotentialRelay`）读出机制判别。

方案依据：`cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md`
第十九节 19.3。非 pass/fail 测试，同项目既有 `_diag_*`/`_calib_*` 探索性
诊断惯例（如 `_diag_t3_c0_ratio_audit.py`）。

运行方式（固定 PYTHONHASHSEED 以保证可复现，见方案 19.1 第⑥点折中方案）：
    PYTHONIOENCODING=utf-8 PYTHONHASHSEED=0 python -m tss.tests._diag_t3_c1r_readout_ab

方法：驱动真实 `RPartCircuitT3` 电路（沿用 T3-B/T3-C0 同一冻结点对
28/31），逐步记录共享 DN 池的输出 `y_a(t)`/`y_b(t)`（比例保真的真值层，
T3-C0 已证明其精确线性）；每一步把 `y_a(t)`/`y_b(t)` 同时喂给两条候选
读出通路（R-A 现有二次 channel 降增益 / R-B GradedPotentialRelay），
在扫描窗口结束时读取各自输出比例，与真值 `y_a/y_b` 做 log-ratio 比较：

    eps_ratio = |log((o_a/o_b) / (y_a/y_b))|

covers 输入比 1:1/2:1/3:1/4:1 × 共同放大 α∈{0.25,0.5,1,2,4,8}。
"""

from __future__ import annotations

# 启动方式统一(2026-09-06, 外部实测反馈清单 §3): 补标准 shim,使
# `python tss/tests/_diag_....py` 直接路径运行与 `python -m` 等效。
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', '..'))

import math

from tss.relations.ratio_r_part import RPartCircuitT3, DT
from nexus_v1.components.neuron import Neuron, NeuronConfig, ChannelConfig
from nexus_v1.components.graded_potential_relay import GradedPotentialRelay

N_STEPS = 300

# R-A：现有二次 channel 同款配置，但降低 gm（批判十建议的"降增益"对照组）
_RA_GM_LOWERED = 2.0  # 原 _CHANNEL_GM=20.0 的 1/10，目标只为避免过早钳位


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
    """驱动电路 n_steps 步，同步跑 R-A/R-B 两条候选读出，返回终态四值。"""
    circuit = RPartCircuitT3()
    ra_a = Neuron(_ra_channel_config("a"))
    ra_b = Neuron(_ra_channel_config("b"))
    rb_a = GradedPotentialRelay()
    rb_b = GradedPotentialRelay()

    y_a = y_b = 0.0
    for _ in range(n_steps):
        circuit.rpart_xi_a.pre_trace = i_a
        circuit.rpart_xi_b.pre_trace = i_b
        r = circuit.step_rpart(dt=DT)
        y_a, y_b = r["y_a"], r["y_b"]

        ra_a.step(y_a, DT)
        ra_b.step(y_b, DT)
        o_ra_a = ra_a.activation
        o_ra_b = ra_b.activation

        o_rb_a = rb_a.step(y_a, DT)
        o_rb_b = rb_b.step(y_b, DT)

    return {
        "y_a": y_a, "y_b": y_b,
        "o_ra_a": o_ra_a, "o_ra_b": o_ra_b,
        "o_rb_a": o_rb_a, "o_rb_b": o_rb_b,
    }


def _eps_ratio(o_a: float, o_b: float, y_a: float, y_b: float) -> float:
    if o_b == 0.0 or y_b == 0.0 or o_a <= 0.0 or y_a <= 0.0:
        return float("nan")
    return abs(math.log((o_a / o_b) / (y_a / y_b)))


def scan_readout_ab():
    print("[T3-C1R] R-A(降增益二次channel) vs R-B(GradedPotentialRelay) 判别扫描")
    print(f"{'ratio':<8}{'alpha':<8}{'y_a/y_b':<12}{'o_ra/o_rb':<12}"
          f"{'eps_ra':<10}{'o_rb比':<12}{'eps_rb':<10}")

    base_ratios = [(1, 1), (2, 1), (3, 1), (4, 1)]
    alphas = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]

    worst_ra, worst_rb = 0.0, 0.0
    for (ra, rb) in base_ratios:
        for alpha in alphas:
            i_a, i_b = ra * alpha, rb * alpha
            m = _drive_and_measure(i_a, i_b)
            y_ratio = m["y_a"] / m["y_b"] if m["y_b"] != 0 else float("nan")
            ra_ratio = m["o_ra_a"] / m["o_ra_b"] if m["o_ra_b"] != 0 else float("nan")
            rb_ratio = m["o_rb_a"] / m["o_rb_b"] if m["o_rb_b"] != 0 else float("nan")
            eps_ra = _eps_ratio(m["o_ra_a"], m["o_ra_b"], m["y_a"], m["y_b"])
            eps_rb = _eps_ratio(m["o_rb_a"], m["o_rb_b"], m["y_a"], m["y_b"])
            if not math.isnan(eps_ra):
                worst_ra = max(worst_ra, eps_ra)
            if not math.isnan(eps_rb):
                worst_rb = max(worst_rb, eps_rb)
            print(f"{ra}:{rb:<6}{alpha:<8}{y_ratio:<12.4f}{ra_ratio:<12.4f}"
                  f"{eps_ra:<10.4f}{rb_ratio:<12.4f}{eps_rb:<10.4f}")

    print()
    print(f"R-A 最大 eps_ratio = {worst_ra:.4f}")
    print(f"R-B 最大 eps_ratio = {worst_rb:.4f}")
    print()
    print("判读：eps_ratio 越接近 0，说明读出比例越贴近 DN 真值比例。")
    print("预期：R-A（二次门控）即使降增益，eps_ratio 仍随共同放大 alpha 增大而"
          "系统性增长（平方关系的log-ratio = log(y比)，非0）；")
    print("R-B（线性中继）eps_ratio 应在数值精度范围内恒为 0（LTI系统比例保真，"
          "不依赖是否到达稳态，见 graded_potential_relay.py Q3 说明）。")


if __name__ == "__main__":
    scan_readout_ab()
