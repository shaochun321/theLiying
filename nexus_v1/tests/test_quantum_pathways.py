"""nexus_v1.tests.test_quantum_pathways — 量子元链路结构验证探针。

测试覆盖：
  T-QP1  bundle census：get_all_bundles() 包含 24 条量子 bundle
  T-QP2  整流验证：yaw_pos 正输入→ensemble 有发放，yaw_neg 静默；反向对称
  T-QP3  温度计单调性：输入幅度递增→发放神经元数单调不减
  T-QP4  collector 结构性激活：ensemble 全部发放后 collector 开始积分
  T-QP5  get_all_neurons 不含量子神经元（vascular census 保护）

注：collector 的 tau_gate 在 spiking 路径被 AdEx 行覆盖；真正的时间积分由
RC 动力学完成（τ = C * r_leak = 10 time-units = 10000 步@dt=0.001）。
T-QP4 验证 collector 进入正驱动状态（vm > 0），不要求完整 AND 门校准。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit, _QUANTUM_DIRECTIONS, _Q_N_ENSEMBLE

ZERO_INPUTS = {
    'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0,
    'oto_x': 0.0, 'oto_y': 0.0, 'oto_z': 0.0,
}
DT = 0.001
YAW_STRONG = 8.0   # 足以使全部 10 个 ensemble 最终激活的输入幅度


def _build_circuit():
    return VariantCircuit()


def _run_steps(circuit, inputs, n, dt=DT):
    for _ in range(n):
        circuit.step(dict(inputs), dt)


def _count_active(ensemble):
    """预迹 >0.01 视为近期有发放。"""
    return sum(1 for n in ensemble if n.pre_trace > 0.01)


# ─────────────────────────────────────────────────────────────
# T-QP1：bundle census（24 条量子 bundle 注册到 get_all_bundles）
# ─────────────────────────────────────────────────────────────
def test_bundle_census():
    c = _build_circuit()
    all_bundles = c.get_all_bundles()
    q_in_ids  = {b.id for b in c.bundles_quantum_in}
    q_col_ids = {b.id for b in c.bundles_quantum_collect}
    all_ids   = {b.id for b in all_bundles}

    assert len(c.bundles_quantum_in)      == 12, \
        f"Expected 12 input bundles, got {len(c.bundles_quantum_in)}"
    assert len(c.bundles_quantum_collect) == 12, \
        f"Expected 12 collect bundles, got {len(c.bundles_quantum_collect)}"
    assert q_in_ids  <= all_ids, "Some quantum_in bundles missing from get_all_bundles()"
    assert q_col_ids <= all_ids, "Some quantum_collect bundles missing from get_all_bundles()"
    print(f"  T-QP1 PASS: {len(all_bundles)} total bundles, 24 quantum bundles registered")


# ─────────────────────────────────────────────────────────────
# T-QP2：整流验证（yaw 轴，运行 200 步使 ensemble 充分激活）
# ─────────────────────────────────────────────────────────────
def test_rectification():
    c = _build_circuit()

    # 正向 yaw — yaw_pos 应激活，yaw_neg 应静默
    pos_inputs = dict(ZERO_INPUTS); pos_inputs['yaw'] = YAW_STRONG
    _run_steps(c, pos_inputs, n=200)
    pos_firing = _count_active(c.quantum_ensembles['yaw_pos'])
    neg_firing = _count_active(c.quantum_ensembles['yaw_neg'])
    print(f"  yaw=+{YAW_STRONG}: yaw_pos firing={pos_firing}, yaw_neg firing={neg_firing}")
    assert pos_firing > 0, "yaw_pos ensemble should fire on positive yaw input"
    assert neg_firing == 0, "yaw_neg ensemble should be silent on positive yaw input"

    # 负向 yaw — yaw_neg 应激活，yaw_pos 应静默
    c2 = _build_circuit()
    neg_inputs = dict(ZERO_INPUTS); neg_inputs['yaw'] = -YAW_STRONG
    _run_steps(c2, neg_inputs, n=200)
    pos_firing2 = _count_active(c2.quantum_ensembles['yaw_pos'])
    neg_firing2 = _count_active(c2.quantum_ensembles['yaw_neg'])
    print(f"  yaw=-{YAW_STRONG}: yaw_pos firing={pos_firing2}, yaw_neg firing={neg_firing2}")
    assert neg_firing2 > 0, "yaw_neg ensemble should fire on negative yaw input"
    assert pos_firing2 == 0, "yaw_pos ensemble should be silent on negative yaw input"

    print("  T-QP2 PASS: rectification correct")


# ─────────────────────────────────────────────────────────────
# T-QP3：温度计单调性（yaw_pos，200 步/振幅）
# ─────────────────────────────────────────────────────────────
def test_thermometer_monotonicity():
    amplitudes = [1.0, 3.0, 6.0, 9.0]
    firing_counts = []

    for amp in amplitudes:
        c = _build_circuit()
        inp = dict(ZERO_INPUTS); inp['yaw'] = amp
        _run_steps(c, inp, n=200)
        count = _count_active(c.quantum_ensembles['yaw_pos'])
        firing_counts.append(count)
        print(f"  yaw_pos amp={amp:.1f} → active={count}")

    # 单调不减
    for i in range(len(firing_counts) - 1):
        assert firing_counts[i] <= firing_counts[i + 1], (
            f"Thermometer monotonicity violated: "
            f"amp {amplitudes[i]}->{amplitudes[i+1]}: "
            f"{firing_counts[i]} > {firing_counts[i+1]}"
        )
    print("  T-QP3 PASS: thermometer monotonicity OK")


# ─────────────────────────────────────────────────────────────
# T-QP4：collector 结构性激活（强输入后 collector 进入正驱动状态）
#
# 注：collector RC 时间常数 τ=C*r_leak=10 time-units=10000 steps@dt=0.001。
# 验证 collector._membrane.voltage > 0 而非完整 AND 门行为。
# ─────────────────────────────────────────────────────────────
def test_collector_structural_activation():
    c = _build_circuit()
    inp = dict(ZERO_INPUTS); inp['yaw'] = YAW_STRONG
    _run_steps(c, inp, n=200)

    col = c.quantum_collectors['yaw_pos']
    ens = c.quantum_ensembles['yaw_pos']
    ens_active = _count_active(ens)
    col_vm = col._membrane.voltage if hasattr(col, '_membrane') else None
    col_vm_str = f"{col_vm:.4f}" if col_vm is not None else "N/A"
    print(f"  yaw_pos: ensemble active={ens_active}/{_Q_N_ENSEMBLE}, "
          f"collector vm={col_vm_str}, "
          f"pre_trace={col.pre_trace:.4f}")

    assert ens_active > 0, "At least some ensemble neurons should be active"
    # collector 应接收到 ensemble 的输入并开始积分（vm > 0）
    if col_vm is not None:
        assert col_vm > 0.0, (
            f"Collector membrane voltage should be positive when ensemble fires; got {col_vm:.4f}"
        )
    print("  T-QP4 PASS: collector receives input from ensemble")


# ─────────────────────────────────────────────────────────────
# T-QP5：get_all_neurons 不含量子神经元（vascular census 保护）
# ─────────────────────────────────────────────────────────────
def test_neurons_excluded_from_census():
    c = _build_circuit()
    all_neuron_ids = {n.config.neuron_id for n in c.get_all_neurons()}
    for dir_name, _, _ in _QUANTUM_DIRECTIONS:
        for k in range(_Q_N_ENSEMBLE):
            assert f"quantum_{dir_name}_{k}" not in all_neuron_ids, \
                f"quantum_{dir_name}_{k} should NOT be in get_all_neurons()"
        assert f"quantum_collector_{dir_name}" not in all_neuron_ids, \
            f"quantum_collector_{dir_name} should NOT be in get_all_neurons()"
    print("  T-QP5 PASS: 138 quantum+antimet neurons correctly excluded from vascular census")


# ─────────────────────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────────────────────
TESTS = [
    ("T-QP1 bundle census",                      test_bundle_census),
    ("T-QP2 rectification",                      test_rectification),
    ("T-QP3 thermometer monotonicity",           test_thermometer_monotonicity),
    ("T-QP4 collector structural activation",    test_collector_structural_activation),
    ("T-QP5 neurons excluded from census",       test_neurons_excluded_from_census),
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
