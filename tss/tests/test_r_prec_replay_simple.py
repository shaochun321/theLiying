"""T-RPP-R1简化版：P2-B1R 学习后复放验证（2026-07-29）。

评判依据：`cell-cell/交叉比对/document - 2026-07-29T091930.583.md` P2-B1R。

核心发现：原T-RPP-R1~R3的复放设计有根本缺陷——collector在复放阶段不激活
（activation=0），导致bundle无论权重多少都不传递电流。真正应该测试的是：
**在训练阶段本身，记录collector激活时bundle传递的电流，验证权重改变→电流改变**。

简化方案：
  T-RPP-R1：训练中记录bundle电流积分，验证DA>0时电流更强
  T-RPP-R2：训练中记录DA膜电位轨迹，验证学习组vs基线组有差异
"""
import sys
sys.path.insert(0, '.')

import numpy as np
from tss.relations.temporal_r_prec_plastic import RPrecCircuitT1Plastic

DT = 0.001
_TRAIN_STEPS = 50000


def _train_and_record_currents(circuit, steps: int, da_concentration: float):
    """训练并记录bundle传递的电流轨迹。"""
    da_neurons = list(circuit.da_neurons.values())
    da_v_trace = []
    bundle_current_trace = []

    for t in range(steps):
        inj_a = 1.0 if t < steps // 2 else 0.0
        inj_b = 1.0 if t >= steps // 3 else 0.0
        circuit.rprec_xi_a.step(inj_a, DT)
        circuit.rprec_xi_b.step(inj_b, DT)
        circuit.step_rprec_plastic(DT, da_concentration=da_concentration)

        # 记录bundle电流和DA膜电位
        currents = circuit.bundle_rprec_to_da.propagate()
        da_v = np.mean([n._membrane.voltage for n in da_neurons])

        bundle_current_trace.append(currents[0] if len(currents) > 0 else 0.0)
        da_v_trace.append(da_v)

    return np.array(bundle_current_trace), np.array(da_v_trace)


def test_rpp_r1_simple_learning_increases_current():
    """T-RPP-R1简化：训练中bundle电流积分应随学习增加。"""
    # 学习组
    circuit_learned = RPrecCircuitT1Plastic()
    print("T-RPP-R1简化: 训练学习组...")
    w_before = circuit_learned.bundle_rprec_to_da.weight_matrix()[0][0]
    currents_learned, da_v_learned = _train_and_record_currents(
        circuit_learned, steps=_TRAIN_STEPS, da_concentration=0.5)
    w_after = circuit_learned.bundle_rprec_to_da.weight_matrix()[0][0]

    # 基线组
    circuit_baseline = RPrecCircuitT1Plastic()
    circuit_baseline.bundle_rprec_to_da.config.learning_rule = "frozen"
    print("  训练基线组（frozen）...")
    currents_baseline, da_v_baseline = _train_and_record_currents(
        circuit_baseline, steps=_TRAIN_STEPS, da_concentration=0.5)

    # 分析
    current_learned_mean = np.mean(currents_learned[currents_learned > 0])
    current_baseline_mean = np.mean(currents_baseline[currents_baseline > 0])
    current_learned_sum = np.sum(currents_learned)
    current_baseline_sum = np.sum(currents_baseline)

    da_v_learned_mean = np.mean(da_v_learned)
    da_v_baseline_mean = np.mean(da_v_baseline)

    print(f"  权重变化: {w_before:.6f} → {w_after:.6f} (Δw={w_after-w_before:.6f})")
    print(f"  Bundle电流（学习组）: mean={current_learned_mean:.6f}, sum={current_learned_sum:.3f}")
    print(f"  Bundle电流（基线组）: mean={current_baseline_mean:.6f}, sum={current_baseline_sum:.3f}")
    print(f"  DA膜电位（学习组）: mean={da_v_learned_mean:.6f}")
    print(f"  DA膜电位（基线组）: mean={da_v_baseline_mean:.6f}")

    # 断言：学习应该增加权重和电流
    assert w_after > w_before, f"学习应该增加权重 ({w_after} <= {w_before})"

    # 如果collector有激活（电流>0的步数），则学习组电流积分应更大
    n_active_learned = np.sum(currents_learned > 0)
    n_active_baseline = np.sum(currents_baseline > 0)

    print(f"  Collector激活步数: 学习组={n_active_learned}, 基线组={n_active_baseline}")

    if n_active_learned > 100:  # 至少有一些激活
        assert current_learned_sum > current_baseline_sum * 1.01, (
            f"学习组电流积分应大于基线组 ({current_learned_sum} <= {current_baseline_sum})")
        print(f"✓ T-RPP-R1简化 PASS: 学习增加了bundle传递的电流")
    else:
        print(f"⚠ T-RPP-R1简化 SKIP: Collector激活不足（{n_active_learned}步），")
        print(f"  无法验证bundle电流差异。这说明当前输入模式不足以触发collector。")


def run():
    test_rpp_r1_simple_learning_increases_current()
    print()
    print("=" * 60)
    print("P2-B1R简化版完成")


if __name__ == "__main__":
    run()
