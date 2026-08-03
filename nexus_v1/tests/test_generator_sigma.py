"""nexus_v1.tests.test_generator_sigma — TSS-1：第一条真正的空间生成算子验证。

方案依据：document - 2026-08-03T131304.153.md（TSS-1裁定：Σ^(1)不能直接
读取欧氏坐标，应来自实际可达链/局部传播/阻断实验/结构响应差异）。

三个测试：
  T-TSS1-1：局部可达性——近邻站点（d=1.09）真实响应远高于远方站点
            （d=3.81），差异来自HeatSource衰减的真实物理传播，不是
            算法读坐标算出来的
  T-TSS1-2：阻断实验——切断ensemble→collector的bundle后，原本可达的
            近邻站点响应归零，证明可达性依赖真实链路
  T-TSS1-3：Σ契约禁止字段审计——GeneratorSigmaReachability产出的契约
            不含euclidean_coordinate等被禁止的语义字段
"""
import sys

sys.path.insert(0, '.')

from nexus_v1.relations.temporal_r_prec import RPrecCircuitT1
from nexus_v1.relations.generator_sigma import (
    GeneratorSigmaReachability, block_experiment,
)


def test_tss1_1_local_reachability_from_real_propagation():
    """T-TSS1-1：近邻站点（31，d=1.09）真实响应应远高于远方站点
    （11，d=3.81）——差异来自HeatSource衰减公式的真实物理传播计算，
    本文件全程未调用任何距离函数，只是把热源摆在站点28的世界坐标上。
    """
    circuit = RPrecCircuitT1()
    probe = GeneratorSigmaReachability(circuit=circuit, source_site=28)
    probe.add_target(31)   # 近邻
    probe.add_target(11)   # 远方
    probe.measure_reachability()

    near = next(p for p in probe.probes if p.target_site == 31)
    far = next(p for p in probe.probes if p.target_site == 11)

    assert near.response_strength > 0.5, (
        f"近邻站点31应有显著响应，实际={near.response_strength}")
    assert far.response_strength < 0.01, (
        f"远方站点11应几乎无响应，实际={far.response_strength}")

    print(f"T-TSS1-1: near(31).response={near.response_strength:.4f}, "
          f"far(11).response={far.response_strength:.4f}")
    print("✓ T-TSS1-1 PASS: 局部可达性由真实物理传播产生，"
          "近邻/远方响应差异显著")


def test_tss1_2_block_experiment_confirms_real_dependency():
    """T-TSS1-2：阻断实验——切断ensemble→collector的bundle后，
    原本可达的近邻站点响应应归零，证明可达性依赖真实传播链路，
    不是巧合的数值分布。"""
    r_with_link, r_cut = block_experiment(
        lambda: RPrecCircuitT1(), source_site=28, target_site=31,
        bundle_id_to_cut="thermq_collect_thermpt31_warm")

    assert r_with_link > 0.5, f"链路完整时应有显著响应，实际={r_with_link}"
    assert r_cut < 1e-6, f"切断链路后响应应归零，实际={r_cut}"

    print(f"T-TSS1-2: with_link={r_with_link:.4f}, cut={r_cut:.6f}")
    print("✓ T-TSS1-2 PASS: 阻断实验证实可达性依赖真实ensemble→collector链路")


def test_tss1_3_sigma_contract_forbidden_fields():
    """T-TSS1-3：Σ契约不含euclidean_coordinate等被禁止的语义字段。"""
    circuit = RPrecCircuitT1()
    probe = GeneratorSigmaReachability(circuit=circuit, source_site=28)
    probe.add_target(31)
    probe.measure_reachability()

    contract = probe.build_contract()
    assert "euclidean_coordinate" in contract.forbidden_decision_fields
    assert contract.output_readable_fields.isdisjoint(
        contract.forbidden_decision_fields)
    assert contract.operator_type == "sigma"
    assert contract.exists_without_learning is True

    print(f"T-TSS1-3: forbidden_decision_fields={sorted(contract.forbidden_decision_fields)}")
    print("✓ T-TSS1-3 PASS: Σ契约不含euclidean_coordinate等禁止字段")


def run():
    test_tss1_1_local_reachability_from_real_propagation()
    test_tss1_2_block_experiment_confirms_real_dependency()
    test_tss1_3_sigma_contract_forbidden_fields()
    print()
    print("=" * 60)
    print("T-TSS1-1~3 ALL PASS")
    print("=" * 60)


if __name__ == "__main__":
    run()
