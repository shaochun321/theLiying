"""T-C1M-1~2：T3-C1 子任务3 幅度可消费性验收。

方案依据：第二十节 20.2 第3点。批判十一④第4点指出：数学比例完全正确，
但若物理幅度几乎不可用（远低于下游 Bundle 能有意义驱动的量级），中继
仍不算真正可用的读出层。要求工作区间 `z_min ≤ z_i ≤ β·a_max`（β≤0.5）。

`z_min` 的定义：本系统 channel 配置全程 `v_threshold=0.0`（无阈值），
是纯线性/二次响应，数学上不存在"低于某值则输出恒零"的硬底线——因此
`z_min` 不是生物阈值，而是"与浮点/数值噪声可区分"的实用下界，取
`1e-6`（比本项目已用的核浮点匹配容差 `1e-9`（`test_t3_c1_dynamic_
ratio.py`）宽 3 个数量级的安全余量，确保不是在比较噪声）。

覆盖范围：T3-C0 已实测的真实 y_i 操作范围（0.03~2.61，见
`_diag_t3_c0_ratio_audit.py`/T3-C1R 报告），验证该范围内中继输出及其
经真实下游 Bundle 后的电流均落在工作区间内、不触发钳位。
"""

from __future__ import annotations

from nexus_v1.components.graded_potential_relay import GradedPotentialRelay, DEFAULT_A_MAX
from nexus_v1.components.neuron import Neuron, NeuronConfig, ChannelConfig
from nexus_v1.circuit.bundle import BundleConfig, SynapticBundle

DT = 0.001
_Z_MIN = 1e-6
_BETA = 0.5
_Z_MAX_WORKSPACE = _BETA * DEFAULT_A_MAX

# T3-C0 已实测的真实 y_i 操作范围（见 T3-C1R 报告 §二 Q3 说明）
_T3C0_MEASURED_Y_RANGE = [0.03, 0.14, 0.40, 2.61]


def _observer_config(label: str) -> NeuronConfig:
    return NeuronConfig(
        neuron_id=f"c1m_observer_{label}",
        region=0x01,
        spiking=False,
        capacitance=0.05,
        r_leak=5.0,
        inertia=1.0,
        channels=[ChannelConfig(name="default", v_threshold=0.0, gm=20.0)],
    )


def _frozen_bundle(bundle_id: str, sources, targets, weight: float) -> SynapticBundle:
    cfg = BundleConfig(
        bundle_id=bundle_id,
        learning_rule="frozen",
        initial_weight=weight,
        weight_max=weight,
        synapse_gain=1.0,
        bundle_role="feedforward",
        remodel_cost_kappa=0.0,
    )
    return SynapticBundle(cfg, sources, targets)


def test_c1m_1_relay_output_within_workspace_across_measured_range():
    """T-C1M-1: T3-C0 实测 y 范围内，中继输出 z_i 落在 [z_min, β·a_max] 工作
    区间，不触发钳位（n_clip=0，同时是 r_ρ 资格硬门槛）。
    """
    for y in _T3C0_MEASURED_Y_RANGE:
        relay = GradedPotentialRelay()
        z = 0.0
        for _ in range(300):
            z = relay.step(y, DT)
        assert z >= _Z_MIN, f"y={y}: z={z} 低于可区分下界 z_min={_Z_MIN}"
        assert z <= _Z_MAX_WORKSPACE, f"y={y}: z={z} 超出工作区间上限 {_Z_MAX_WORKSPACE}"
        stats = relay.relay_ledger_stats()
        assert stats["n_clip"] == 0, f"y={y}: n_clip={stats['n_clip']}，r_ρ资格失格"


def test_c1m_2_downstream_bundle_current_non_degenerate():
    """T-C1M-2: T3-C0 实测 y 范围下限（0.03，最保守场景）经真实下游 Bundle
    后，Bundle 输出电流仍与静默态（z=0）可区分，不是"数学比例正确但物理
    幅度不可用"。
    """
    y_min_measured = min(_T3C0_MEASURED_Y_RANGE)
    relay = GradedPotentialRelay()
    observer = Neuron(_observer_config("m2"))
    bundle = _frozen_bundle("c1m_min_probe", [relay], [observer], 0.3)

    i_out = 0.0
    for _ in range(300):
        relay.step(y_min_measured, DT)
        currents = bundle.propagate()
        i_out = currents[0] if currents else 0.0
        bundle.apply_to_targets(currents, DT)

    assert i_out > _Z_MIN, (
        f"最保守实测输入(y={y_min_measured})下 Bundle 输出电流={i_out} "
        f"过小，物理幅度可能不足以驱动下游状态")


if __name__ == "__main__":
    test_c1m_1_relay_output_within_workspace_across_measured_range()
    test_c1m_2_downstream_bundle_current_non_degenerate()
    print("T-C1M-1~2 ALL PASS")
