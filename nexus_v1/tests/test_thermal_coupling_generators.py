"""nexus_v1.tests.test_thermal_coupling_generators — 感温耦合生成元 Ω 结构验证探针。

测试覆盖：
  T-Ω1  census：Ω 束在 get_all_bundles() 中，Ω 神经元不在 get_all_neurons() 中
  T-Ω2  方向选择性：thermpt0(+X 半球)合成 dT 驱动升温 → RF_{+X} collector
        的 pre_trace/膜电位 应高于 RF_{-X}
  T-Ω3  连续性：cos²(θ) 几何权重随方向角单调变化（构造期权重本身的性质，
        不依赖运行时驱动）
  T-Ω4  散度响应：单点热驱动 vs 全部64源同时热驱动，div_collector 响应
        应随"同时热的源数量"变化（对应标定发现：xi pre_trace 近乎二值，
        Ω 差异来自"多少源同时越过阈值"）
  T-Ω5  frozen 权重不变：驱动多步后，Ω 束的 Memristor.w 与构造时写入值一致

驱动方式：复用 test_quantum_thermal_pathways.py 的方法论——直接给指定
thermpt 的 Level1 喂合成 dT，绕开 world/body 自主物理动力学，手动传播其
三级链路，再手动传播 Ω 层三级链路（bundle→ensemble→collector）。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit, _THERM_LOCAL_N, _RF_DIRECTIONS

DT = 0.001


def _build_circuit():
    return VariantCircuit()


def _propagate_xi_point(circuit, point_idx, dT_value, dt=DT):
    """驱动单个 thermpt 点的 warm/cool 三级链路一步（同 test_quantum_thermal_pathways）。"""
    pid = f"thermpt{point_idx}"
    l1_warm = circuit.thermal_quantum_l1_warm[pid]
    l1_cool = circuit.thermal_quantum_l1_cool[pid]
    l1_warm.step(dT_value, dt)
    l1_cool.step(-dT_value, dt)

    idx_warm, idx_cool = point_idx * 2, point_idx * 2 + 1
    for idx in (idx_warm, idx_cool):
        b_l1_hc = circuit.bundles_thermal_quantum_l1_to_hc[idx]
        b_in = circuit.bundles_thermal_quantum_in[idx]
        b_col = circuit.bundles_thermal_quantum_collect[idx]

        currents_hc = b_l1_hc.propagate()
        hc_target = b_l1_hc.targets[0]
        hc_target.step(currents_hc[0] if currents_hc else 0.0, dt)

        ensemble = b_in.targets
        currents_in = b_in.propagate()
        for k, neuron in enumerate(ensemble):
            neuron.step(currents_in[k] if k < len(currents_in) else 0.0, dt)

        collector = b_col.targets[0]
        currents_col = b_col.propagate()
        collector.step(currents_col[0] if currents_col else 0.0, dt)


def _propagate_omega(circuit, dt=DT):
    """驱动 Ω 层三级链路一步（同 _step_thermal_coupling_generators 逻辑）。"""
    for d_idx in range(len(_RF_DIRECTIONS)):
        bundle_in = circuit.bundles_rf[d_idx * 2]
        bundle_col = circuit.bundles_rf[d_idx * 2 + 1]
        ensemble = circuit.rf_ensembles[d_idx]

        currents_in = bundle_in.propagate()
        for k, neuron in enumerate(ensemble):
            neuron.step(currents_in[k] if k < len(currents_in) else 0.0, dt)

        collector = circuit.rf_collectors[d_idx]
        currents_col = bundle_col.propagate()
        collector.step(currents_col[0] if currents_col else 0.0, dt)

    currents_exc = circuit.bundles_div_exc.propagate()
    currents_inh = circuit.bundles_div_inh.propagate()
    for k, neuron in enumerate(circuit.div_ensemble):
        c_exc = currents_exc[k] if k < len(currents_exc) else 0.0
        c_inh = currents_inh[k] if k < len(currents_inh) else 0.0
        neuron.step(c_exc + c_inh, dt)

    currents_div_col = circuit.bundle_div_collect.propagate()
    circuit.div_collector.step(
        currents_div_col[0] if currents_div_col else 0.0, dt)


def _drive_points_synthetic_dT(circuit, point_indices, dT_value, n_steps, dt=DT):
    """驱动一组 thermpt 点 n_steps 步（xi 层 + Ω 层），返回各方向 collector 的
    pre_trace 峰值字典 {dir_idx: peak_pre_trace} 和 div_collector 峰值。
    """
    peak_rf = {d: 0.0 for d in range(len(_RF_DIRECTIONS))}
    peak_div = 0.0
    for _ in range(n_steps):
        for pt in point_indices:
            _propagate_xi_point(circuit, pt, dT_value, dt)
        _propagate_omega(circuit, dt)
        for d_idx, col in circuit.rf_collectors.items():
            if col.pre_trace > peak_rf[d_idx]:
                peak_rf[d_idx] = col.pre_trace
        if circuit.div_collector.pre_trace > peak_div:
            peak_div = circuit.div_collector.pre_trace
    return peak_rf, peak_div


# ─────────────────────────────────────────────────────────────
# T-Ω1：census
# ─────────────────────────────────────────────────────────────
def test_census():
    c = _build_circuit()

    all_bundles = c.get_all_bundles()
    all_bundle_ids = {b.config.bundle_id for b in all_bundles}
    rf_bundle_ids = {b.config.bundle_id for b in c.bundles_rf}
    assert rf_bundle_ids <= all_bundle_ids, "Omega RF bundles missing from get_all_bundles()"
    assert c.bundles_div_exc.config.bundle_id in all_bundle_ids
    assert c.bundles_div_inh.config.bundle_id in all_bundle_ids
    assert c.bundle_div_collect.config.bundle_id in all_bundle_ids

    all_neuron_ids = {n.config.neuron_id for n in c.get_all_neurons()}
    for d_idx in range(len(_RF_DIRECTIONS)):
        collector = c.rf_collectors[d_idx]
        assert collector.config.neuron_id not in all_neuron_ids, \
            f"Omega RF_{d_idx} collector should NOT be in get_all_neurons()"
        for n in c.rf_ensembles[d_idx]:
            assert n.config.neuron_id not in all_neuron_ids, \
                f"Omega RF_{d_idx} ensemble neuron should NOT be in get_all_neurons()"
    assert c.div_collector.config.neuron_id not in all_neuron_ids
    for n in c.div_ensemble:
        assert n.config.neuron_id not in all_neuron_ids

    print(f"  T-Ω1 PASS: {len(rf_bundle_ids)+3} omega bundles in census, "
          f"{6*11+11}=77 omega neurons correctly excluded")


# ─────────────────────────────────────────────────────────────
# T-Ω2：方向选择性
#
# 诊断发现（2026-07-14，_diag_omega_current_chain.py）：xi 层各点的
# L1→L2/L2→ensemble/ensemble→collector 束按 hash((bundle_id,i_s,i_t)) 做
# ±25% 对称性打破扰动（bundle.py:170-171），而 Python 字符串 hash() 默认
# 逐进程随机化（PYTHONHASHSEED 未固定）——同一 dT 驱动下哪些点能可靠发放
# 因进程而异，单点/少数点结果不可复现。这是 xi 层既有特性（母本代码，不
# 在本次改动范围），Ω 层对此的正确应对是种群编码冗余：驱动整个 +X 半球
# （约一半点，cos_x>0）而非少数几个点，只要半球内有足够点可靠发放即可
# 产生方向信号，不依赖任何单点的运气。
# ─────────────────────────────────────────────────────────────
def test_directional_selectivity():
    from nexus_v1.components.skin_network import fibonacci_sphere_points
    positions = fibonacci_sphere_points(_THERM_LOCAL_N, 2.0)

    px_points = [i for i in range(_THERM_LOCAL_N) if positions[i][0] > 0]
    print(f"  driving {len(px_points)}/{_THERM_LOCAL_N} points in +X hemisphere")

    c = _build_circuit()
    peak_rf, _peak_div = _drive_points_synthetic_dT(c, px_points, dT_value=0.02, n_steps=2000)

    idx_px, idx_nx = 0, 1  # _RF_DIRECTIONS[0]=(1,0,0)=+X, [1]=(-1,0,0)=-X
    print(f"  +X points driven: {px_points}")
    print(f"  RF_+X peak pre_trace={peak_rf[idx_px]:.4f}, "
          f"RF_-X peak pre_trace={peak_rf[idx_nx]:.4f}")
    assert peak_rf[idx_px] > peak_rf[idx_nx], (
        "RF_+X collector should respond more strongly than RF_-X "
        "when +X-hemisphere xi sources are driven"
    )
    print("  T-Ω2 PASS: directional selectivity confirmed")


# ─────────────────────────────────────────────────────────────
# T-Ω3：cos² 几何权重连续性（构造期权重本身的性质）
# ─────────────────────────────────────────────────────────────
def test_cos_squared_continuity():
    from nexus_v1.components.skin_network import (
        fibonacci_sphere_points, compute_coupling_weights)

    positions = fibonacci_sphere_points(_THERM_LOCAL_N, 2.0)
    directions = [(1.0, 0.0, 0.0)]
    weights = compute_coupling_weights(positions, directions, sharpness=2.0, base_weight=0.5)[0]

    # 按点与 +X 的夹角排序，权重应随夹角增大单调不增
    import math
    def angle_from_x(p):
        norm = math.sqrt(p[0]**2 + p[1]**2 + p[2]**2)
        cos_t = p[0] / norm if norm > 0 else 0.0
        cos_t = max(-1.0, min(1.0, cos_t))
        return math.acos(cos_t)

    order = sorted(range(_THERM_LOCAL_N), key=lambda i: angle_from_x(positions[i]))
    ordered_weights = [weights[i] for i in order]
    for i in range(len(ordered_weights) - 1):
        assert ordered_weights[i] >= ordered_weights[i + 1] - 1e-9, (
            f"cos^2 weight should be non-increasing with angle: "
            f"{ordered_weights[i]:.4f} < {ordered_weights[i+1]:.4f}"
        )
    # 背向点（cos<=0）权重应恰为 0（半波整流）
    n_zero = sum(1 for w in weights if w == 0.0)
    assert n_zero > 0, "Some points behind +X should have exactly zero weight"
    print(f"  T-Ω3 PASS: cos^2 weights monotonic with angle, "
          f"{n_zero}/{_THERM_LOCAL_N} points rectified to 0")


# ─────────────────────────────────────────────────────────────
# T-Ω4：散度响应——同时热的源数量越多，div_collector 响应越强
#
# 同 T-Ω2 的种群编码冗余考量：稀疏侧用少数点会因 xi 层逐进程哈希随机化
# （见 T-Ω2 注释）在个别运行中意外发放，比较用 8 点(约1/4球面) vs 全部
# 32 点，两侧都留了统计冗余，同时用严格大于（而非 >=）避免不产生真实
# 差异也能"通过"的弱断言。
# ─────────────────────────────────────────────────────────────
def test_divergence_scales_with_active_count():
    c_sparse = _build_circuit()
    sparse_points = list(range(8))
    _peak_rf_sparse, peak_div_sparse = _drive_points_synthetic_dT(
        c_sparse, sparse_points, dT_value=0.02, n_steps=2000)

    c_dense = _build_circuit()
    all_points = list(range(_THERM_LOCAL_N))
    _peak_rf_dense, peak_div_dense = _drive_points_synthetic_dT(
        c_dense, all_points, dT_value=0.02, n_steps=2000)

    print(f"  {len(sparse_points)} points driven: div peak pre_trace={peak_div_sparse:.4f}")
    print(f"  {_THERM_LOCAL_N} points driven: div peak pre_trace={peak_div_dense:.4f}")
    assert peak_div_dense > peak_div_sparse, (
        "div_collector response should increase when more xi sources are hot "
        f"(sparse={peak_div_sparse:.4f}, dense={peak_div_dense:.4f})"
    )
    print("  T-Ω4 PASS: divergence response scales with simultaneously-active xi count")


# ─────────────────────────────────────────────────────────────
# T-Ω5：frozen 权重不变
# ─────────────────────────────────────────────────────────────
def test_frozen_weights_unchanged():
    c = _build_circuit()

    bundle_in_0 = c.bundles_rf[0]
    snapshot = [[m.w for m in row] for row in bundle_in_0._memristors]

    _drive_points_synthetic_dT(c, list(range(_THERM_LOCAL_N)), dT_value=0.05, n_steps=500)

    for i_s, row in enumerate(bundle_in_0._memristors):
        for i_t, m in enumerate(row):
            assert abs(m.w - snapshot[i_s][i_t]) < 1e-12, (
                f"Frozen bundle weight changed: source={i_s} target={i_t} "
                f"before={snapshot[i_s][i_t]:.6f} after={m.w:.6f}"
            )
    print("  T-Ω5 PASS: frozen Omega bundle weights unchanged after 500 driven steps")


# ─────────────────────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────────────────────
TESTS = [
    ("T-Ω1 census",                              test_census),
    ("T-Ω2 directional selectivity",             test_directional_selectivity),
    ("T-Ω3 cos^2 weight continuity",             test_cos_squared_continuity),
    ("T-Ω4 divergence scales with active count", test_divergence_scales_with_active_count),
    ("T-Ω5 frozen weights unchanged",            test_frozen_weights_unchanged),
]

if __name__ == "__main__":
    passed = 0
    failed = 0
    for name, fn in TESTS:
        print(f"\n[{name}]")
        try:
            fn()
            passed += 1
            print(f"  -> PASS")
        except AssertionError as e:
            failed += 1
            print(f"  -> FAIL: {e}")
        except Exception as e:
            failed += 1
            import traceback
            print(f"  -> ERROR: {e}")
            traceback.print_exc()

    print(f"\n{'='*55}")
    print(f"  {passed} passed, {failed} failed")
    print(f"{'='*55}")
    exit(0 if failed == 0 else 1)
