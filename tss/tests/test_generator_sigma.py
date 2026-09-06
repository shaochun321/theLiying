"""tss.tests.test_generator_sigma — TSS-1：Σ_support^(1)物理支撑
局部性投影原型验证（资格修正版）。

方案依据：document - 2026-08-03T135526.068.md（评判修正：宣称过强，
降格为Σ_support^(1)物理支撑局部性投影）。

冻结结论：局部外部物理发生能够通过锚定链路，产生具有空间选择性的内部
生成活动云。禁止宣称：已证明生成元间可达性/皮肤物理传播/内部空间距离。

三个测试不变（物理实验结果有效），只修正资格宣称措辞：
  T-TSS1-1：局部物理支撑选择性——近邻站点进入活动云，远方站点不进入
  T-TSS1-2：阻断实验——切断内部链路后collector响应归零（依赖内部
            神经链路，不是皮肤物理传播边）
  T-TSS1-3：Σ_support契约禁止字段审计
"""
import sys

sys.path.insert(0, '.')

from tss.relations.temporal_r_prec import RPrecCircuitT1
from tss.relations.generator_sigma import (
    GeneratorSigmaReachability, block_experiment,
)


def test_tss1_1_local_support_selectivity():
    """T-TSS1-1：物理支撑局部性——近邻站点（31，d=1.09）进入活动云，
    远方站点（11，d=3.81）不进入，差异来自HeatSource衰减（近邻在
    radius=2.0内，远方在radius外，衰减因子直接为0）。

    这证明：外部局部物理支撑→内部生成元活动范围（Σ_support^(1)）。
    不证明：基础生成元G_i经皮肤物理链传播到G_j（Σ_reach^(1)——那需要
    目标不被外部场直接刺激，并切断皮肤物理耦合边而非内部链路）。
    """
    circuit = RPrecCircuitT1()
    probe = GeneratorSigmaReachability(circuit=circuit, source_site=28)
    probe.add_target(31)
    probe.add_target(11)
    probe.measure_reachability()

    near = next(p for p in probe.probes if p.target_site == 31)
    far = next(p for p in probe.probes if p.target_site == 11)

    assert near.response_strength > 0.5
    assert far.response_strength < 0.01

    print(f"T-TSS1-1: near(31).response={near.response_strength:.4f}, "
          f"far(11).response={far.response_strength:.4f}")
    print("✓ T-TSS1-1 PASS: 局部外部物理支撑产生空间选择性活动云"
          "（Σ_support^(1)，非可达性）")


def test_tss1_2_internal_link_dependency():
    """T-TSS1-2：切断内部神经链路（ensemble→collector的bundle）后
    collector响应归零，证明活动云依赖完整内部链路。

    注意：这切断的是内部神经链路，不是皮肤物理空间中的传播边——评判
    明确这是Σ_support^(1)（内部链路依赖性）而非Σ_reach^(1)。
    """
    r_with_link, r_cut = block_experiment(
        lambda: RPrecCircuitT1(), source_site=28, target_site=31,
        bundle_id_to_cut="thermq_collect_thermpt31_warm")

    assert r_with_link > 0.5
    assert r_cut < 1e-6

    print(f"T-TSS1-2: with_link={r_with_link:.4f}, cut={r_cut:.6f}")
    print("✓ T-TSS1-2 PASS: 活动云依赖内部神经链路（切断internal bundle→归零）")


def test_tss1_3_sigma_support_contract():
    """T-TSS1-3：Σ_support契约不含欧氏坐标等禁止字段。"""
    circuit = RPrecCircuitT1()
    probe = GeneratorSigmaReachability(circuit=circuit, source_site=28)
    probe.add_target(31)
    probe.measure_reachability()

    contract = probe.build_contract()
    assert "euclidean_coordinate" in contract.forbidden_decision_fields
    assert contract.output_readable_fields.isdisjoint(contract.forbidden_decision_fields)
    assert contract.operator_type == "sigma"
    assert contract.exists_without_learning is True

    print(f"T-TSS1-3: operator_type=sigma, exists_without_learning=True")
    print("✓ T-TSS1-3 PASS: Σ_support契约禁止字段正确，不含坐标语义")


def run():
    test_tss1_1_local_support_selectivity()
    test_tss1_2_internal_link_dependency()
    test_tss1_3_sigma_support_contract()
    print()
    print("=" * 60)
    print("T-TSS1-1~3 ALL PASS (Σ_support^(1) 物理支撑局部性投影)")
    print("=" * 60)


if __name__ == "__main__":
    run()
