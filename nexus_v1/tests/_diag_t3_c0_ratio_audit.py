"""nexus_v1.tests._diag_t3_c0_ratio_audit — T3-C0：导出比例四层信号审计。

方案依据：cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md
第十八节 18.4。第九份交叉比对批判指出：T3-B 的共享分流池（DN）输出比例
`y_a/y_b` 精确等于源电流比 `i_a/i_b`，但注入的两个 channel Neuron 用
`v_threshold=0`、`tau_gate=0` 的单通道门控，其公开 `activation` 满足
`gm×(vm-vth)²`（T1 EXP-T1-02 已证的二次门控压缩）——结合 Capacitor 稳态
`V_ss=I×R_leak`（T1 EXP-T1-03 已证，与C无关），理论推导：

    activation_a / activation_b ≈ (y_a / y_b)²

本脚本按项目既有 `_diag_*.py`/`_calib_*.py` 一次性诊断脚本惯例（非
pass/fail 测试），实测验证这个理论推导，并记录四层信号：
    x_i = ξ pre_trace（测试设定的驱动强度）
    i_i = Bundle propagate() 后的原始电流（Bundle 有效电流，非名义驱动值）
    y_i = 共享 DN 池输出（dt=0 只读读出）
    o_i = channel Neuron 的公开 activation（真正可被下游 Bundle 读取的值）

同时做共同尺度扫描（第十八节18.4第2点）：固定输入比 1:1/2:1/3:1，扫描
共同放大系数 α∈{0.25,0.5,1,2,4,8}，验证 [y_a:y_b] 与 [o_a:o_b] 是否
分别稳定（即使 o 层是 y 层的平方，比值本身在不同 α 下应仍然稳定——
这里要实测确认，不是假设）。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.relations.ratio_r_part import RPartCircuitT3

DT = 0.001
_N_STEPS = 300  # 比 T-RPT 用的 200 步更长，确保 channel Neuron 稳态积分更充分


def _drive_and_measure(i_a, i_b, n_steps=_N_STEPS):
    """驱动电路 n_steps 步，返回四层信号的稳态读数。"""
    c = RPartCircuitT3()
    r = {}
    for _ in range(n_steps):
        c.rpart_xi_a.pre_trace = i_a
        c.rpart_xi_b.pre_trace = i_b
        r = c.step_rpart(dt=DT)
    return {
        "x_a": i_a, "x_b": i_b,
        "i_a": r["i_a_raw"], "i_b": r["i_b_raw"],
        "y_a": r["y_a"], "y_b": r["y_b"],
        "o_a": c.rpart_channel_a.activation,
        "o_b": c.rpart_channel_b.activation,
    }


def _ratio(a, b):
    return a / b if b != 0 else float("inf")


def audit_four_layer_chain():
    """T3-C0 第1点：四层信号同时记录，验证 o_a/o_b ≈ (y_a/y_b)² 是否成立。"""
    print("\n[T3-C0-1] 四层信号审计（x=pre_trace, i=Bundle电流, y=DN输出, o=Neuron activation）")
    print(f"{'场景':<12}{'x_a/x_b':>10}{'i_a/i_b':>12}{'y_a/y_b':>12}{'o_a/o_b':>12}{'(y比)²':>12}{'o比/(y比)²':>14}")

    scenarios = [
        ("2:1", 1.0, 0.5),
        ("3:1", 1.5, 0.5),
        ("4:1", 2.0, 0.5),
    ]
    for label, i_a, i_b in scenarios:
        m = _drive_and_measure(i_a, i_b)
        r_x = _ratio(m["x_a"], m["x_b"])
        r_i = _ratio(m["i_a"], m["i_b"])
        r_y = _ratio(m["y_a"], m["y_b"])
        r_o = _ratio(m["o_a"], m["o_b"])
        r_y_sq = r_y ** 2
        match = r_o / r_y_sq if r_y_sq != 0 else float("inf")
        print(f"{label:<12}{r_x:>10.4f}{r_i:>12.4f}{r_y:>12.4f}{r_o:>12.4f}{r_y_sq:>12.4f}{match:>14.4f}")

    print("\n  结论判读：若最后一列(o比/(y比)²)接近1.0，说明批判九的平方假说被证实；")
    print("  若接近(y比)本身，说明实际是线性关系（假说不成立）；否则是介于两者之间的其他关系。")


def scan_common_scale():
    """T3-C0 第2点：共同尺度扫描，验证 y 层/o 层比例是否分别对共同放大稳定。"""
    print("\n[T3-C0-2] 共同尺度扫描（固定输入比，扫描共同放大系数 α）")

    fixed_ratios = [("1:1", 1.0, 1.0), ("2:1", 2.0, 1.0), ("3:1", 3.0, 1.0)]
    alphas = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]

    for label, base_a, base_b in fixed_ratios:
        print(f"\n  固定比 {label}:")
        print(f"    {'α':>6}{'y_a/y_b':>12}{'o_a/o_b':>12}")
        y_ratios = []
        o_ratios = []
        for alpha in alphas:
            m = _drive_and_measure(base_a * alpha, base_b * alpha)
            r_y = _ratio(m["y_a"], m["y_b"])
            r_o = _ratio(m["o_a"], m["o_b"])
            y_ratios.append(r_y)
            o_ratios.append(r_o)
            print(f"    {alpha:>6.2f}{r_y:>12.4f}{r_o:>12.4f}")
        y_spread = (max(y_ratios) - min(y_ratios)) / max(y_ratios)
        o_spread = (max(o_ratios) - min(o_ratios)) / max(o_ratios)
        print(f"    y层比值相对散布={y_spread:.4f}，o层比值相对散布={o_spread:.4f}"
              f"（越接近0说明该层比值对共同放大越稳定）")


if __name__ == "__main__":
    audit_four_layer_chain()
    scan_common_scale()
