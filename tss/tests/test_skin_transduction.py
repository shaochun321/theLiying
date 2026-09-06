"""T-TRANS-N：P2-A1b-2 皮肤-生成元转导映射契约测试。

TYPE:INFRA — 验证 `nexus_v1/generators/skin_transduction.py` 的校准
是否达成目标：参考物理过程集合(T-STP-6/7/8六场景)映射进𝒟_disc^G内部
区间；静息态不产生虚假激活；极端输入被安全压缩；映射方向正确。
"""
import sys

sys.path.insert(0, '.')

from tss.generators.skin_transduction import (
    TransductionConfig, transduce, REFERENCE_TRANSDUCTION_CONFIG,
)

# 六个参考场景的完整[T0,T1,T2]数据，直接取自P2-A1b-1报告实测结果
# （`cell-cell/工作报告/P2-A1b-0边界复核与生成元级可区分度_
# P2-A1b-1皮肤输出分布_2026-07-21.md`第三部分）。
REFERENCE_SCENARIOS = {
    "Gamma_A": [61.8260, 49.5116, 43.6483],
    "Gamma_B": [43.6483, 49.5116, 61.8260],
    "Gamma_C": [43.6522, 49.5116, 61.8221],
    "Gamma_D": [61.8221, 49.5116, 43.6522],
    "Gamma_E": [49.5116, 55.9627, 49.5116],
    "Gamma_F": [52.7371, 49.5116, 52.7371],
}


def test_reference_scenarios_map_into_interior_target_band():
    """六场景全部18个温度值经transduce()后应落在[0.005,0.03]目标区间内
    （允许浮点误差），验证校准达成"参考集合映射进𝒟_disc^G内部"的目标。"""
    lo, hi = 0.005, 0.03
    tol = 1e-6
    for name, q_vec in REFERENCE_SCENARIOS.items():
        for q in q_vec:
            u = transduce(q, REFERENCE_TRANSDUCTION_CONFIG)
            assert lo - tol <= u <= hi + tol, (
                f"{name}: q={q} -> u={u} 超出目标区间[{lo},{hi}]")


def test_rest_baseline_clamped_to_floor():
    """静息基线q=0（P2-A1b-1实测的[T0,T1,T2]=[0,0,0]）映射后应被
    u_clip_min=0.0钳位——验证零输入不产生虚假激活。"""
    u = transduce(0.0, REFERENCE_TRANSDUCTION_CONFIG)
    assert u == REFERENCE_TRANSDUCTION_CONFIG.u_clip_min


def test_extreme_dose_scenario_clamped_to_ceiling():
    """P2-A1b-1剂量扫描的极端场景（50.0注入，q≈3091.2987，s1稳态）映射
    后应精确等于u_clip_max=0.04——验证极端值被安全压缩，不越界送入
    生成元的𝒮_cap区。"""
    q_extreme = 3091.2987
    u = transduce(q_extreme, REFERENCE_TRANSDUCTION_CONFIG)
    assert u == REFERENCE_TRANSDUCTION_CONFIG.u_clip_max


def test_monotonic_before_clipping():
    """clip前的线性部分：q越大，u越大（验证映射方向正确，不是巧合数值）。
    用未clip的自定义宽范围config逐一核对严格单调递增。"""
    wide_config = TransductionConfig(
        q_i0=0.0, kappa_i=REFERENCE_TRANSDUCTION_CONFIG.kappa_i,
        b_i=REFERENCE_TRANSDUCTION_CONFIG.b_i,
        u_clip_min=-1e9, u_clip_max=1e9,  # 实质不生效的宽clip，只测线性段
    )
    q_values = [0.0, 10.0, 43.6483, 50.0, 61.8260, 100.0, 3091.2987]
    u_values = [transduce(q, wide_config) for q in q_values]
    for i in range(len(u_values) - 1):
        assert u_values[i] < u_values[i + 1], (
            f"q={q_values[i]}->u={u_values[i]} 应严格小于 "
            f"q={q_values[i+1]}->u={u_values[i+1]}")


def test_two_point_calibration_exact():
    """两点线性求解应精确命中目标端点：q=43.6483(参考集合最小值)->
    u=0.005，q=61.8260(参考集合最大值)->u=0.03（校准推导的直接验证）。"""
    tol = 1e-4
    u_lo = transduce(43.6483, REFERENCE_TRANSDUCTION_CONFIG)
    u_hi = transduce(61.8260, REFERENCE_TRANSDUCTION_CONFIG)
    assert abs(u_lo - 0.005) < tol
    assert abs(u_hi - 0.03) < tol


if __name__ == "__main__":
    test_reference_scenarios_map_into_interior_target_band()
    test_rest_baseline_clamped_to_floor()
    test_extreme_dose_scenario_clamped_to_ceiling()
    test_monotonic_before_clipping()
    test_two_point_calibration_exact()
    print("All T-TRANS tests passed.")
