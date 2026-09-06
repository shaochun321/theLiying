"""T-RPP-R1′：P2-B1R 方案A′ — 局部因果复放（2026-07-29）。

评判依据：`cell-cell/交叉比对/document - 2026-07-29T132244.981.md`。

核心设计：录制训练期collector真实产生的pre_trace脉冲序列 ξ_ρ(t)，冻结学习后，
对learned权重和baseline权重状态回放相同序列，比较bundle产生的突触后电流差异。

两级资格：
  L1（必须）：学习后关系连接改变局部下游电流 I_ρ→DA(t)
  L2（非阻塞）：该局部改变足以改变整个DA池宏观轨迹
"""
import sys
sys.path.insert(0, '.')

import numpy as np
from tss.relations.temporal_r_prec_plastic import RPrecCircuitT1Plastic

DT = 0.001
_TRAIN_STEPS = 50000


def _record_trace_during_training(circuit, steps: int, da_concentration: float):
    """训练并录制collector的pre_trace脉冲序列。

    Returns:
        trace_sequence: shape (steps,) collector.pre_trace轨迹
    """
    trace_sequence = []

    for t in range(steps):
        inj_a = 1.0 if t < steps // 2 else 0.0
        inj_b = 1.0 if t >= steps // 3 else 0.0
        circuit.rprec_xi_a.step(inj_a, DT)
        circuit.rprec_xi_b.step(inj_b, DT)
        circuit.step_rprec_plastic(DT, da_concentration=da_concentration)

        # 录制collector的pre_trace（这是bundle.propagate()读取的源信号）
        trace_sequence.append(circuit.rprec_collector_a_prec_b_fast.pre_trace)

    return np.array(trace_sequence)


def _replay_trace_and_measure(circuit, trace_sequence, block_bundle: bool = False):
    """回放相同的pre_trace序列，测量bundle电流和DA膜电位。

    关键：直接设置collector.pre_trace，绕过collector自然激活，确保learned和
    baseline状态接收完全相同的关系输入ξ_ρ(t)。

    Args:
        circuit: RPrecCircuitT1Plastic实例（权重已固定）
        trace_sequence: 录制的pre_trace序列
        block_bundle: 若True，阻断bundle传播（同状态因果比较）

    Returns:
        (currents, da_voltages): bundle电流序列和DA膜电位序列
    """
    da_neurons = list(circuit.da_neurons.values())
    collector = circuit.rprec_collector_a_prec_b_fast
    bundle = circuit.bundle_rprec_to_da

    currents = []
    da_voltages = []

    for t, pre_trace_val in enumerate(trace_sequence):
        # 直接设置collector的pre_trace（录制的关系输入）
        collector.pre_trace = pre_trace_val

        # 传播：bundle读取collector.pre_trace计算电流
        if not block_bundle:
            target_currents = bundle.propagate()
            for i, tgt in enumerate(bundle.targets):
                tgt.step(target_currents[i] if i < len(target_currents) else 0.0, DT)
            currents.append(target_currents[0] if len(target_currents) > 0 else 0.0)
        else:
            currents.append(0.0)  # 阻断：不传播

        # 记录DA膜电位
        da_v = np.mean([n._membrane.voltage for n in da_neurons])
        da_voltages.append(da_v)

    return np.array(currents), np.array(da_voltages)


def test_rpp_r1_prime_L1_current_causality():
    """T-RPP-R1′-L1：学习后关系连接改变局部下游电流。

    验证标准（L1）：D(I_learned, I_baseline) > ε_I
    """
    # === 阶段1：训练learned组并录制trace ===
    circuit_learned = RPrecCircuitT1Plastic()
    print("T-RPP-R1′-L1: 训练learned组并录制collector trace...")
    w_before = circuit_learned.bundle_rprec_to_da.weight_matrix()[0][0]

    trace_sequence = _record_trace_during_training(
        circuit_learned, steps=_TRAIN_STEPS, da_concentration=0.5)

    w_after = circuit_learned.bundle_rprec_to_da.weight_matrix()[0][0]
    circuit_learned.bundle_rprec_to_da.config.learning_rule = "frozen"  # 冻结

    print(f"  权重变化: {w_before:.6f} → {w_after:.6f} (Δw={w_after-w_before:.6f})")
    print(f"  录制trace序列长度: {len(trace_sequence)}")
    print(f"  trace非零步数: {np.sum(trace_sequence > 1e-6)}")

    # === 阶段2：baseline组（权重冻结，不学习）===
    circuit_baseline = RPrecCircuitT1Plastic()
    circuit_baseline.bundle_rprec_to_da.config.learning_rule = "frozen"
    print("  训练baseline组（frozen权重）...")

    # baseline也需要相同的驱动（但不学习）
    for t in range(_TRAIN_STEPS):
        inj_a = 1.0 if t < _TRAIN_STEPS // 2 else 0.0
        inj_b = 1.0 if t >= _TRAIN_STEPS // 3 else 0.0
        circuit_baseline.rprec_xi_a.step(inj_a, DT)
        circuit_baseline.rprec_xi_b.step(inj_b, DT)
        circuit_baseline.step_rprec_plastic(DT, da_concentration=0.5)

    w_baseline = circuit_baseline.bundle_rprec_to_da.weight_matrix()[0][0]
    print(f"  baseline权重: {w_baseline:.6f}")

    # === 阶段3：回放相同trace，比较电流 ===
    print("  回放learned组...")
    currents_learned, da_v_learned = _replay_trace_and_measure(
        circuit_learned, trace_sequence, block_bundle=False)

    print("  回放baseline组...")
    currents_baseline, da_v_baseline = _replay_trace_and_measure(
        circuit_baseline, trace_sequence, block_bundle=False)

    # === 分析L1：局部下游电流差异 ===
    # 只比较trace>0的活跃步（collector有输出时）
    active_mask = trace_sequence > 1e-6
    n_active = np.sum(active_mask)

    if n_active < 100:
        print(f"⚠ T-RPP-R1′-L1 SKIP: collector活跃步数不足（{n_active}步）")
        return

    i_learned_active = currents_learned[active_mask]
    i_baseline_active = currents_baseline[active_mask]

    i_learned_mean = np.mean(i_learned_active)
    i_baseline_mean = np.mean(i_baseline_active)
    i_learned_sum = np.sum(i_learned_active)
    i_baseline_sum = np.sum(i_baseline_active)

    current_diff = i_learned_sum - i_baseline_sum
    current_ratio = i_learned_sum / i_baseline_sum if i_baseline_sum > 0 else 1.0

    print(f"\n  L1 局部电流分析（{n_active}个活跃步）：")
    print(f"    learned: mean={i_learned_mean:.8f}, sum={i_learned_sum:.6f}")
    print(f"    baseline: mean={i_baseline_mean:.8f}, sum={i_baseline_sum:.6f}")
    print(f"    差异: Δsum={current_diff:.8f}, ratio={current_ratio:.6f}")

    # L1资格断言：learned电流积分应大于baseline
    threshold_ratio = 1.001  # 0.1%差异阈值（权重增长1%，电流应增长约0.1%）
    assert current_ratio > threshold_ratio, (
        f"L1失败：learned电流积分应大于baseline "
        f"(ratio={current_ratio:.6f} <= {threshold_ratio})")

    print(f"✓ T-RPP-R1′-L1 PASS: 学习后权重改变局部下游电流 (ratio={current_ratio:.6f})")


def test_rpp_r2_prime_same_state_ablation():
    """T-RPP-R2′：同状态阻断因果比较。

    从同一learned状态复制两个副本，一个启用bundle一个阻断，验证：
    D(I_enabled, I_blocked) > ε_I
    """
    # === 训练并录制 ===
    circuit = RPrecCircuitT1Plastic()
    print("T-RPP-R2′: 训练并录制...")
    trace_sequence = _record_trace_during_training(
        circuit, steps=_TRAIN_STEPS, da_concentration=0.5)
    circuit.bundle_rprec_to_da.config.learning_rule = "frozen"

    w_learned = circuit.bundle_rprec_to_da.weight_matrix()[0][0]
    print(f"  learned权重: {w_learned:.6f}")

    # === 回放：启用vs阻断 ===
    print("  回放enabled（正常传播）...")
    currents_enabled, _ = _replay_trace_and_measure(
        circuit, trace_sequence, block_bundle=False)

    # 重新实例化相同learned状态
    circuit2 = RPrecCircuitT1Plastic()
    _record_trace_during_training(circuit2, steps=_TRAIN_STEPS, da_concentration=0.5)
    circuit2.bundle_rprec_to_da.config.learning_rule = "frozen"

    print("  回放blocked（阻断传播）...")
    currents_blocked, _ = _replay_trace_and_measure(
        circuit2, trace_sequence, block_bundle=True)

    # === 分析：阻断应消除电流 ===
    active_mask = trace_sequence > 1e-6
    n_active = np.sum(active_mask)

    i_enabled_sum = np.sum(currents_enabled[active_mask])
    i_blocked_sum = np.sum(currents_blocked[active_mask])

    print(f"\n  同状态阻断分析（{n_active}个活跃步）：")
    print(f"    enabled电流积分: {i_enabled_sum:.6f}")
    print(f"    blocked电流积分: {i_blocked_sum:.6f}")
    print(f"    差异: {i_enabled_sum - i_blocked_sum:.6f}")

    assert i_enabled_sum > i_blocked_sum * 10, (
        f"阻断应显著移除电流 (enabled={i_enabled_sum:.6f} <= blocked={i_blocked_sum:.6f}×10)")

    print(f"✓ T-RPP-R2′ PASS: 阻断bundle消除了关系连接的局部作用")


def test_rpp_r3_prime_L2_DA_pool_sensitivity():
    """T-RPP-R3′-L2：DA池整体轨迹差异（非阻塞资格）。

    验证标准（L2）：D(V_DA_learned, V_DA_baseline) > ε_V
    若通过则获得更高级资格；若不通过则登记为能力边界（LIM-RPREC-READOUT-001）。
    """
    # === 训练并录制 ===
    circuit_learned = RPrecCircuitT1Plastic()
    print("T-RPP-R3′-L2: 训练learned组...")
    trace_sequence = _record_trace_during_training(
        circuit_learned, steps=_TRAIN_STEPS, da_concentration=0.5)
    circuit_learned.bundle_rprec_to_da.config.learning_rule = "frozen"

    circuit_baseline = RPrecCircuitT1Plastic()
    circuit_baseline.bundle_rprec_to_da.config.learning_rule = "frozen"
    print("  训练baseline组...")
    for t in range(_TRAIN_STEPS):
        inj_a = 1.0 if t < _TRAIN_STEPS // 2 else 0.0
        inj_b = 1.0 if t >= _TRAIN_STEPS // 3 else 0.0
        circuit_baseline.rprec_xi_a.step(inj_a, DT)
        circuit_baseline.rprec_xi_b.step(inj_b, DT)
        circuit_baseline.step_rprec_plastic(DT, da_concentration=0.5)

    # === 回放并测量DA池轨迹 ===
    print("  回放learned组...")
    _, da_v_learned = _replay_trace_and_measure(
        circuit_learned, trace_sequence, block_bundle=False)

    print("  回放baseline组...")
    _, da_v_baseline = _replay_trace_and_measure(
        circuit_baseline, trace_sequence, block_bundle=False)

    # === 分析L2：DA池整体轨迹差异 ===
    da_v_diff = np.mean(np.abs(da_v_learned - da_v_baseline))
    da_v_learned_mean = np.mean(da_v_learned)
    da_v_baseline_mean = np.mean(da_v_baseline)

    print(f"\n  L2 DA池轨迹分析：")
    print(f"    learned DA膜电位: mean={da_v_learned_mean:.6f}")
    print(f"    baseline DA膜电位: mean={da_v_baseline_mean:.6f}")
    print(f"    平均差异: {da_v_diff:.6f}")

    threshold_v = 0.001  # DA池差异阈值（可调节）

    if da_v_diff > threshold_v:
        print(f"✓ T-RPP-R3′-L2 PASS: 单束作用足以改变DA池宏观轨迹 (D={da_v_diff:.6f})")
    else:
        print(f"○ T-RPP-R3′-L2 资格未达：单束作用在DA池中信噪比不足")
        print(f"  (D={da_v_diff:.6f} <= {threshold_v})。")
        print(f"  建议登记 LIM-RPREC-READOUT-001：单关系束的全局下游可辨识度有限。")


def run():
    test_rpp_r1_prime_L1_current_causality()
    test_rpp_r2_prime_same_state_ablation()
    test_rpp_r3_prime_L2_DA_pool_sensitivity()
    print()
    print("=" * 60)
    print("P2-B1R 方案A′ 完成：局部因果复放验证")
    print("=" * 60)


if __name__ == "__main__":
    run()
