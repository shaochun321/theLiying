"""nexus_v1.tests.test_r2_x2c — P2-C1F-d：R2层不可约资格与双父切断测试。

方案依据：
  document - 2026-08-02T173204.373.md（K_R2定义与执行顺序）
  document - 2026-08-02T192053.677.md（命名修正：∅→R2_INPUT_NULL）
  沿用P2-B1X2c（test_r1_x2c.py）的方法论：Y(s)=ℓ_out局部电流轨迹，
  K = ||Y_组合 - Y_单独A - Y_单独B + Y_空||_2，切断法用synapse_gain=0。

优化（避免重演X2c调试成本）：不对T1/T2做L1边界回放——四条件
（R2_INPUT_NULL/T1-only/T2-only/T1∧T2）改用**同一次真实物理驱动**
（热源放站点28，复用T-R2F-3已验证参数），只切换R2输入bundle的
synapse_gain：
  R2_INPUT_NULL : bundle_r1t1_to_trace/bundle_r1t2_to_trace都切断
  T1-only       : 只切断bundle_r1t2_to_trace（T2信号不进入R2）
  T2-only       : 只切断bundle_r1t1_to_trace（T1信号不进入R2）
  T1∧T2         : 不切断（真实共同源场景）
T1/T2各自的relation_collector活动不受R2层切断影响（切断发生在R2
输入侧，不影响step_rprec()/step_rprec2()本身），四条件下T1/T2的
真实活动完全一致，只是"能否到达R2"不同——这与X2c的gen-cut/out-cut
是同一类"切断特定链路，不改变上游驱动"方法，不是新发明的机制。

命名修正（评判192053）：R2_INPUT_NULL条件**不是**"系统无任何活动"的
空条件——T1和T2在这个条件下仍在真实活动（circuit.step_rprec()/
step_rprec2()正常运行），只是两条R2输入链路被切断，导致R1活动无法
传入R2层。这与传统意义的∅（完全无外部输入）是不同的概念，本文件
统一改用R2_INPUT_NULL标识，避免误读为"整个系统没有发生任何活动"。

三个测试：
  T-R2C-0：切断复核（synapse_gain=0使R2输入bundle电流归零，同X2c CUT-0）
  T-R2C-1：K_R2 > ε_int（共同源产生不可加和的额外输出）
  T-R2C-2：K_out_R2 > ε_out（ℓ_out^R2的必要性——切断它后Y_R2应消失）
"""

import sys
import math

sys.path.insert(0, '.')

from nexus_v1.components.world import HeatSource
from nexus_v1.relations.r2_fork import R2ForkCircuitPlastic

DT = 0.001
N_STEPS = 2000   # R2 rising edge@564, T1/T2检测@530/535——2000步足够包含衰减尾


def _make_r2_input_null_circuit():
    """R2_INPUT_NULL条件：T1/T2真实活动照常发生，只是两条R2输入
    链路都被切断（不是"系统无任何活动"，见模块docstring命名修正）。"""
    return _make_driven_circuit(cut_t1_to_r2=True, cut_t2_to_r2=True)


def _make_driven_circuit(cut_t1_to_r2=False, cut_t2_to_r2=False, cut_out=False):
    """构造R2ForkCircuitPlastic，热源放站点28（复用T-R2F-3参数），
    按需切断R2输入/输出bundle的synapse_gain。"""
    circuit = R2ForkCircuitPlastic()
    site_28 = circuit.rprec_site_a
    patch_28 = circuit._thermal_quantum_patches[site_28]
    heat_pos = patch_28.world_position(circuit.world.body)
    circuit.world.heat_sources = [HeatSource(
        position=list(heat_pos), energy=100000.0,
        temperature=300.0, radius=5.0, _drift=[0.0, 0.0, 0.0],
    )]
    if cut_t1_to_r2:
        circuit.bundle_r1t1_to_trace.config.synapse_gain = 0.0
    if cut_t2_to_r2:
        circuit.bundle_r1t2_to_trace.config.synapse_gain = 0.0
    if cut_out:
        circuit.bundle_r2_to_da.config.synapse_gain = 0.0
    return circuit


def _run_and_collect_y(circuit, n_steps=N_STEPS):
    """驱动n_steps步，收集Y_R2(s)轨迹（DA池第0个目标的局部电流）。"""
    y_traj = []
    for t in range(n_steps):
        circuit.step({}, DT)
        circuit.step_rprec(DT)
        circuit.step_rprec2(DT)
        circuit.step_r2(DT)
        y = circuit.measure_r2_output_current()
        y_traj.append(y[0] if y else 0.0)
    return y_traj


def _l2_norm(traj):
    return math.sqrt(sum(y ** 2 for y in traj))


def test_r2c_0_cut_verification():
    """T-R2C-0：R2层切断复核——synapse_gain=0使bundle_r1t1_to_trace的
    电流归零（同X2c CUT-0已验证的机制，这里在R2层复核一次，非重新
    发明）。"""
    circuit = R2ForkCircuitPlastic()
    circuit.rprec_collector_a_prec_b_fast.pre_trace = 0.5

    currents_before = circuit.bundle_r1t1_to_trace.propagate()
    assert max(abs(x) for x in currents_before) > 1e-6

    circuit.bundle_r1t1_to_trace.config.synapse_gain = 0.0
    currents_after = circuit.bundle_r1t1_to_trace.propagate()
    assert max(abs(x) for x in currents_after) < 1e-12

    print(f"T-R2C-0: before={[round(x,6) for x in currents_before]}, after={currents_after}")
    print("✓ T-R2C-0 PASS: R2层synapse_gain=0切断复核有效")


def test_r2c_1_and_2_irreducibility_and_output_necessity():
    """T-R2C-1/2：K_R2不可约资格 + ℓ_out^R2输出必要性。"""
    y_null = _run_and_collect_y(_make_r2_input_null_circuit())
    y_t1 = _run_and_collect_y(_make_driven_circuit(cut_t2_to_r2=True))
    y_t2 = _run_and_collect_y(_make_driven_circuit(cut_t1_to_r2=True))
    y_both = _run_and_collect_y(_make_driven_circuit())
    y_out_cut = _run_and_collect_y(_make_driven_circuit(cut_out=True))

    kappa = [y_both[t] - y_t1[t] - y_t2[t] + y_null[t] for t in range(N_STEPS)]
    K_R2 = _l2_norm(kappa)
    K_out_R2 = _l2_norm([y_both[t] - y_out_cut[t] for t in range(N_STEPS)])
    eps = _l2_norm(y_null) * 3 + 1e-10

    print(f"\n  Y_R2_INPUT_NULL norm={_l2_norm(y_null):.6f}, Y_T1 norm={_l2_norm(y_t1):.6f}, "
          f"Y_T2 norm={_l2_norm(y_t2):.6f}, Y_T1∧T2 norm={_l2_norm(y_both):.6f}")
    print(f"  K_R2={K_R2:.6f} (eps={eps:.6f}) -> {'PASS' if K_R2 > eps else 'FAIL'}")
    print(f"  K_out_R2={K_out_R2:.6f} (eps={eps:.6f}) -> {'PASS' if K_out_R2 > eps else 'FAIL'}")

    assert K_R2 > eps, f"T-R2C-1 FAIL: K_R2={K_R2:.6f} <= eps={eps:.6f}"
    print("✓ T-R2C-1 PASS: K_R2 > eps_int（共同源产生不可加和的额外R2输出）")

    assert K_out_R2 > eps, f"T-R2C-2 FAIL: K_out_R2={K_out_R2:.6f} <= eps={eps:.6f}"
    print("✓ T-R2C-2 PASS: K_out_R2 > eps_out（ell_out^R2确实传递R2的下游作用）")

    return K_R2, K_out_R2, eps


def run():
    test_r2c_0_cut_verification()
    K_R2, K_out_R2, eps = test_r2c_1_and_2_irreducibility_and_output_necessity()
    print()
    print("=" * 60)
    print("T-R2C-0~2 ALL PASS")
    print(f"  K_R2={K_R2:.4f}, K_out_R2={K_out_R2:.4f}, eps={eps:.4f}")
    print("=" * 60)


if __name__ == "__main__":
    run()
