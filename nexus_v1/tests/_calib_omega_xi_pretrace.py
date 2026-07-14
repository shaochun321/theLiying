"""nexus_v1.tests._calib_omega_xi_pretrace — 一次性标定脚本（非回归测试）。

目的：测量 xi collector (thermal_quantum_collectors) 的 pre_trace 实际量级，
为 Omega 层的 _RF_BASE_WEIGHT / _RF_COLLECT_THR / _DIV_CENTER_W /
_DIV_SURROUND_W 提供数值依据（model-before-tune，禁止照抄未经验证的假设值）。

方法沿用（v2）：真实 World 热扩散驱动测过——20000 步(20s, dt=0.001)内 64 个
collector 的 pre_trace 峰值全部为 0，膜电位在 +X/-X 两侧几乎相等(~0.12，即
v_rest)。原因不是标定脚本的 body/热源位置错误（已排除），而是 xi 层本身
只在现有测试 test_quantum_thermal_pathways.py 的合成 dT 直接注入方式下被验证
过（docstring 明确标注 TODO-CALIBRATE）：真实世界经 SkinPatch 热惯性
(tau=5000步=5s) 传导的 dT 增量在 20s 内太小/太慢，不足以让 3 级链路
(L1->L2->L3 ensemble->collector) 积累到 collector 阈值。

改用与该测试文件相同的方法论：直接给 thermpt0 的 Level1 喂合成 dT（绕开
world/body 物理传导延迟），跑足够步数，读 collector.pre_trace 峰值。所有
32 个点结构参数相同，只有 position 不同，故用 point0 做代表性测量即可。

用完即弃：这是标定脚本，不是回归套件的一部分，不放进 TESTS 列表。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit

DT = 0.001
AMPLITUDES = [0.001, 0.005, 0.02, 0.05, 0.1]
N_STEPS = 2000


def _drive_point0_synthetic_dT(circuit, dT_value, n_steps, dt=DT):
    """同 test_quantum_thermal_pathways.py 的驱动方法，额外读 collector.pre_trace。"""
    l1_warm = circuit.thermal_quantum_l1_warm["thermpt0"]
    l1_cool = circuit.thermal_quantum_l1_cool["thermpt0"]
    idx_warm, idx_cool = 0, 1
    peak_pre_trace_warm = 0.0
    peak_vm_warm = 0.0

    for _ in range(n_steps):
        l1_warm.step(dT_value, dt)
        l1_cool.step(-dT_value, dt)
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

        col_warm = circuit.thermal_quantum_collectors["thermpt0_warm"]
        if col_warm.pre_trace > peak_pre_trace_warm:
            peak_pre_trace_warm = col_warm.pre_trace
        vm = col_warm._membrane.voltage if hasattr(col_warm, '_membrane') else 0.0
        if vm > peak_vm_warm:
            peak_vm_warm = vm

    return peak_pre_trace_warm, peak_vm_warm


def main():
    print(f"{'dT amplitude':>14} | {'collector peak pre_trace':>26} | {'collector peak vm':>18}")
    print("-" * 64)
    for amp in AMPLITUDES:
        c = VariantCircuit()
        peak_pt, peak_vm = _drive_point0_synthetic_dT(c, amp, N_STEPS)
        print(f"{amp:>14.4f} | {peak_pt:>26.6f} | {peak_vm:>18.6f}")


if __name__ == "__main__":
    main()
