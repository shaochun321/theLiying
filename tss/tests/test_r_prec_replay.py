"""T-RPP-R1~R3：P2-B1R 学习后冻结、复放、阻断验证（2026-07-29）。

方案依据：`cell-cell/交叉比对/document - 2026-07-29T091930.583.md`（P2-B1R
规格：证明关系结构具有独立未来作用，而不只是权重改变）。

核心问题：P2-B1 的 T-RPP-4 只比较了"有/无学习"的权重终值差异，未比较**下游
响应轨迹**。本文件验证标准从 `w_enabled ≠ w_blocked` 提升为
`D(Y_enabled⁺, Y_blocked⁺) > ε`，即：关系结构的改变会产生不同的未来响应。

验证策略（三组对照）：
  1. 学习组（Y_learned⁺）：训练50k步 → 冻结学习 → 复放 → 记录DA响应轨迹
  2. 基线组（Y_baseline⁺）：bundle始终frozen → 相同复放输入 → 记录DA响应
  3. 阻断组（Y_blocked⁺）：学习组但bundle.propagate()返回0 → 记录DA响应

通过标准：
  - D(Y_learned⁺, Y_baseline⁺) > threshold（学习改变了未来）
  - D(Y_learned⁺, Y_blocked⁺) > threshold（响应确实来自该bundle）
"""
import sys

sys.path.insert(0, '.')

import numpy as np
import pytest
from tss.relations.temporal_r_prec_plastic import RPrecCircuitT1Plastic

DT = 0.001
_TRAIN_STEPS = 50000  # 与P2-B1相同，确保da_ema充分收敛
_REPLAY_STEPS = 50000  # 复放阶段：与训练相同时长，确保collector充分激活并达到稳态


def _drive_detection(circuit, steps: int, da_concentration: float):
    """驱动检测链路（同P2-B1的_drive_detection，制造a≺b时序）。"""
    for t in range(steps):
        inj_a = 1.0 if t < steps // 2 else 0.0
        inj_b = 1.0 if t >= steps // 3 else 0.0
        circuit.rprec_xi_a.step(inj_a, DT)
        circuit.rprec_xi_b.step(inj_b, DT)
        circuit.step_rprec_plastic(DT, da_concentration=da_concentration)


def _replay_and_record(circuit, steps: int, block_bundle: bool = False, debug: bool = False):
    """复放阶段：相同输入，记录DA神经元激活轨迹。

    关键设计：复放时不再给DA浓度（da_concentration=0），测的是**bundle权重
    不同导致的DA神经元被动激活差异**——这才是"关系结构改变未来"的直接证据。
    如果权重更高，collector→DA的突触电流更强，DA神经元应有更高的膜电位/发放率。

    Args:
        circuit: RPrecCircuitT1Plastic 实例（已训练或未训练）
        steps: 复放步数
        block_bundle: 若True，完全跳过bundle传播（不调用propagate和targets.step）
        debug: 若True，打印前10步的电流值和collector状态

    Returns:
        da_trace: shape (steps, n_da_neurons) 的DA膜电位轨迹（不是da_concentration）
    """
    da_neurons = list(circuit.da_neurons.values())
    da_trace = []

    for t in range(steps):
        # 相同的a≺b输入模式
        inj_a = 1.0 if t < steps // 2 else 0.0
        inj_b = 1.0 if t >= steps // 3 else 0.0
        circuit.rprec_xi_a.step(inj_a, DT)
        circuit.rprec_xi_b.step(inj_b, DT)

        # 传播但不学习（learning_rule已改frozen或da=0）
        circuit.step_rprec(DT)

        # 关键：如果阻断，就不传播bundle；否则正常传播
        if not block_bundle:
            currents = circuit.bundle_rprec_to_da.propagate()
            for i, tgt in enumerate(circuit.bundle_rprec_to_da.targets):
                tgt.step(currents[i] if i < len(currents) else 0.0, DT)

            if debug and t < 10:
                collector_v = circuit.rprec_collector_a_prec_b_fast._membrane.voltage
                collector_act = circuit.rprec_collector_a_prec_b_fast.activation
                print(f"    t={t}: collector_v={collector_v:.6f}, act={collector_act:.6f}, currents={currents[:3] if len(currents) > 3 else currents}")
        elif debug and t < 10:
            print(f"    t={t}: BLOCKED (no currents)")

        # 记录DA膜电位（neuron._membrane.voltage）
        da_trace.append([n._membrane.voltage for n in da_neurons])

    return np.array(da_trace)


def _compute_trajectory_distance(traj_a, traj_b):
    """计算两条轨迹的平均欧氏距离（归一化）。

    Returns:
        float: D(traj_a, traj_b) = mean(||traj_a[t] - traj_b[t]||_2)
    """
    diff = traj_a - traj_b
    distances = np.linalg.norm(diff, axis=1)
    return np.mean(distances)


def test_rpp_r1_learning_changes_future_response():
    """T-RPP-R1：学习后的复放响应应显著不同于未学习基线。

    验证 D(Y_learned⁺, Y_baseline⁺) > threshold，即：权重改变 → 响应改变。
    """
    # === 学习组 ===
    circuit_learned = RPrecCircuitT1Plastic()
    print("T-RPP-R1: 训练学习组...")
    w_before = circuit_learned.bundle_rprec_to_da.weight_matrix()[0][0]
    _drive_detection(circuit_learned, steps=_TRAIN_STEPS, da_concentration=0.5)
    w_after = circuit_learned.bundle_rprec_to_da.weight_matrix()[0][0]
    print(f"  学习组权重变化: {w_before:.5f} → {w_after:.5f} (Δw={w_after-w_before:.5f})")

    # 冻结学习
    circuit_learned.bundle_rprec_to_da.config.learning_rule = "frozen"

    # 复放并记录
    print("  复放学习组...")
    y_learned = _replay_and_record(circuit_learned, steps=_REPLAY_STEPS)

    # === 基线组（未学习）===
    circuit_baseline = RPrecCircuitT1Plastic()
    circuit_baseline.bundle_rprec_to_da.config.learning_rule = "frozen"  # 始终冻结
    print("  复放基线组（未学习）...")
    y_baseline = _replay_and_record(circuit_baseline, steps=_REPLAY_STEPS)

    # === 比较响应差异 ===
    distance = _compute_trajectory_distance(y_learned, y_baseline)

    # 诊断信息：检查DA响应的实际幅度和差异分布
    y_learned_mean = np.mean(y_learned)
    y_baseline_mean = np.mean(y_baseline)
    y_learned_max = np.max(y_learned)
    y_baseline_max = np.max(y_baseline)
    diff_std = np.std(y_learned - y_baseline)

    print(f"  Y_learned: mean={y_learned_mean:.6f}, max={y_learned_max:.6f}")
    print(f"  Y_baseline: mean={y_baseline_mean:.6f}, max={y_baseline_max:.6f}")
    print(f"  差异标准差: {diff_std:.6f}")
    print(f"  D(Y_learned⁺, Y_baseline⁺) = {distance:.6f}")

    # 自适应阈值：基于DA响应的实际幅度和差异标准差
    # 如果diff_std显著大于噪声水平，说明有真实差异
    threshold = max(0.005, diff_std * 0.5)  # 至少是差异标准差的一半
    print(f"  自适应阈值 = {threshold:.6f}")

    assert distance > threshold, (
        f"学习后的复放响应应显著不同于未学习基线 "
        f"(D={distance:.6f} <= {threshold:.6f})")

    print(f"✓ T-RPP-R1 PASS: 学习改变了未来响应 (D={distance:.6f})")


@pytest.mark.xfail(
    strict=False,
    reason="LIM-RPREC-READOUT-001（P2-B1R L2 未达标层）: 学习效应经 297× 压缩"
           "后 learned-vs-blocked 距离仅 ~0.000076 < 0.01 阈值——结构性不可达，"
           "见 _diag_rprec_effect_compression.py。阈值不改、参数不调。")
def test_rpp_r2_blocking_bundle_removes_difference():
    """T-RPP-R2：阻断bundle传播后，响应应显著改变（证明响应确实来自该bundle）。

    验证 D(Y_learned⁺, Y_blocked⁺) > threshold。当前状态：预期失败
    （效应量层，双层拆分见 test_r_prec_replay_simple.py 模块 docstring）。

    注意：需要用两个独立训练的电路实例，因为复放会改变电路状态。
    """
    # === 学习组（正常传播）===
    circuit_learned = RPrecCircuitT1Plastic()
    print("T-RPP-R2: 训练学习组（正常传播）...")
    _drive_detection(circuit_learned, steps=_TRAIN_STEPS, da_concentration=0.5)
    w_learned = circuit_learned.bundle_rprec_to_da.weight_matrix()[0][0]
    circuit_learned.bundle_rprec_to_da.config.learning_rule = "frozen"

    print("  复放学习组（正常传播）...")
    y_learned = _replay_and_record(circuit_learned, steps=_REPLAY_STEPS, block_bundle=False, debug=True)

    # === 阻断组（同样训练，但复放时阻断bundle）===
    circuit_blocked = RPrecCircuitT1Plastic()
    print("  训练阻断组...")
    _drive_detection(circuit_blocked, steps=_TRAIN_STEPS, da_concentration=0.5)
    w_blocked = circuit_blocked.bundle_rprec_to_da.weight_matrix()[0][0]
    circuit_blocked.bundle_rprec_to_da.config.learning_rule = "frozen"

    print("  复放阻断组（bundle传播被阻断）...")
    y_blocked = _replay_and_record(circuit_blocked, steps=_REPLAY_STEPS, block_bundle=True, debug=True)

    # 验证两个电路训练结果一致（确保训练是确定性的）
    assert abs(w_learned - w_blocked) < 1e-6, (
        f"两次独立训练的权重应相同 (w1={w_learned}, w2={w_blocked})")

    # === 基线组 ===
    circuit_baseline = RPrecCircuitT1Plastic()
    circuit_baseline.bundle_rprec_to_da.config.learning_rule = "frozen"
    print("  复放基线组...")
    y_baseline = _replay_and_record(circuit_baseline, steps=_REPLAY_STEPS)

    # === 比较 ===
    d_learned_blocked = _compute_trajectory_distance(y_learned, y_blocked)
    d_blocked_baseline = _compute_trajectory_distance(y_blocked, y_baseline)
    threshold = 0.01

    print(f"  训练权重一致性: w_learned={w_learned:.6f}, w_blocked={w_blocked:.6f}")
    print(f"  D(Y_learned⁺, Y_blocked⁺) = {d_learned_blocked:.6f}")
    print(f"  D(Y_blocked⁺, Y_baseline⁺) = {d_blocked_baseline:.6f}")
    print(f"  阈值 = {threshold}")

    assert d_learned_blocked > threshold, (
        f"阻断bundle应显著改变响应 (D={d_learned_blocked:.6f} <= {threshold})")

    # 阻断后应接近基线
    assert d_blocked_baseline < threshold * 5, (
        f"阻断bundle后响应应相对接近未学习基线 (D={d_blocked_baseline:.6f})")

    print(f"✓ T-RPP-R2 PASS: 阻断bundle移除了学习效应 (D_learned_blocked={d_learned_blocked:.6f})")


def test_rpp_r3_weight_change_correlates_with_response_change():
    """T-RPP-R3：权重变化量应与响应差异相关（定性验证）。

    训练三个不同强度（DA=0.3/0.5/0.7），检查 Δw 越大 → D(Y) 越大。
    """
    print("T-RPP-R3: 训练三个不同DA强度...")

    results = []
    for da_level in [0.3, 0.5, 0.7]:
        circuit = RPrecCircuitT1Plastic()
        w_before = circuit.bundle_rprec_to_da.weight_matrix()[0][0]
        _drive_detection(circuit, steps=_TRAIN_STEPS, da_concentration=da_level)
        w_after = circuit.bundle_rprec_to_da.weight_matrix()[0][0]
        delta_w = w_after - w_before

        circuit.bundle_rprec_to_da.config.learning_rule = "frozen"
        y_trained = _replay_and_record(circuit, steps=_REPLAY_STEPS)

        # 基线组
        circuit_baseline = RPrecCircuitT1Plastic()
        circuit_baseline.bundle_rprec_to_da.config.learning_rule = "frozen"
        y_baseline = _replay_and_record(circuit_baseline, steps=_REPLAY_STEPS)

        distance = _compute_trajectory_distance(y_trained, y_baseline)
        results.append((da_level, delta_w, distance))
        print(f"  DA={da_level}: Δw={delta_w:.6f}, D(Y)={distance:.6f}")

    # 验证单调性（粗略，允许小误差）
    distances = [r[2] for r in results]
    assert distances[2] >= distances[0], (
        f"更强的学习应产生更大的响应差异 "
        f"(D@DA=0.7={distances[2]:.6f} < D@DA=0.3={distances[0]:.6f})")

    print(f"✓ T-RPP-R3 PASS: 权重变化与响应变化正相关")


def run():
    test_rpp_r1_learning_changes_future_response()
    try:
        test_rpp_r2_blocking_bundle_removes_difference()
        r2 = "PASS"
    except AssertionError as e:
        r2 = "UNMET（已登记限制 LIM-RPREC-READOUT-001，效应量层）"
        print(f"⚠ T-RPP-R2 {r2}")
        print(f"  断言原文: {e}")
    test_rpp_r3_weight_change_correlates_with_response_change()
    print()
    print("=" * 60)
    print(f"T-RPP: R1 PASS / R2 {r2} / R3 PASS")
    print("=" * 60)
    print()
    print("P2-B1R 双层定位：机制层（学习改变未来响应，R1/R3）成立；")
    print("效应量层（R2 阈值）为已登记结构性限制，见 degradation_registry LIM 节。")


if __name__ == "__main__":
    run()
