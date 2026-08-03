"""nexus_v1.tests.test_generator_contract — TSS-0：时间/空间/尺度生成算子
类型契约验证。

方案依据：document - 2026-08-03T131304.153.md（TSS-0范围裁定）。

四个测试：
  T-TSS0-1：Θ^(1)六项契约字段完整（禁止/允许读取集合互斥，
            exists_without_learning=True）
  T-TSS0-2：从真实RPrecCircuitT1构造Θ绑定，物理载体是真实Neuron对象
            （不是占位符/字符串）
  T-TSS0-3：evidence验证——RPrecCircuitT1的ℓ_gen全部12条bundle确实
            learning_rule="frozen"，支撑Θ绑定的exists_without_learning=True
            不是凭空声明
  T-TSS0-4：Σ^(1)/Λ^(1)只是类型占位（input_generators/physical_carriers
            默认为空），不含任何真实电路引用——确认TSS-0没有越界新增
            动力学
"""
import sys

sys.path.insert(0, '.')

from nexus_v1.relations.temporal_r_prec import RPrecCircuitT1
from nexus_v1.relations.generator_contract import (
    GeneratorThetaBinding, GeneratorSigmaBinding, GeneratorLambdaBinding,
    THETA_ALLOWED_READ_FIELDS, THETA_FORBIDDEN_DECISION_FIELDS,
    audit_exists_without_learning, build_theta_binding_from_rprec_t1,
)


def test_tss0_1_theta_contract_fields():
    """T-TSS0-1：Θ契约六项字段完整，允许/禁止读取集合互斥。"""
    circuit = RPrecCircuitT1()
    binding = build_theta_binding_from_rprec_t1(circuit)
    c = binding.contract

    assert c.operator_type == "theta"
    assert len(c.physical_carriers) == 3  # trace_a, trace_b, relation_collector
    assert c.output_readable_fields == THETA_ALLOWED_READ_FIELDS
    assert c.forbidden_decision_fields == THETA_FORBIDDEN_DECISION_FIELDS
    assert c.output_readable_fields.isdisjoint(c.forbidden_decision_fields), (
        "允许读取字段和禁止读取字段不应有交集")
    assert c.exists_without_learning is True

    print(f"T-TSS0-1: operator_type={c.operator_type}, "
          f"physical_carriers数量={len(c.physical_carriers)}")
    print("✓ T-TSS0-1 PASS: Θ契约六项字段完整，允许/禁止读取互斥")


def test_tss0_2_binding_uses_real_objects():
    """T-TSS0-2：Θ绑定的physical_carriers是真实Neuron对象，不是字符串
    占位或mock。"""
    circuit = RPrecCircuitT1()
    binding = build_theta_binding_from_rprec_t1(circuit)

    assert binding.trace_a is circuit.rprec_trace_a_fast
    assert binding.trace_b is circuit.rprec_trace_b_fast
    assert binding.relation_collector is circuit.rprec_collector_a_prec_b_fast
    # 确认是真实Neuron对象（有.config属性），不是字符串
    assert hasattr(binding.trace_a, "config")
    assert hasattr(binding.relation_collector, "config")

    print(f"T-TSS0-2: trace_a={binding.trace_a.config.neuron_id}, "
          f"relation_collector={binding.relation_collector.config.neuron_id}")
    print("✓ T-TSS0-2 PASS: Θ绑定引用的是真实RPrecCircuitT1对象，非占位符")


def test_tss0_3_evidence_frozen_bundles():
    """T-TSS0-3：验证RPrecCircuitT1的ℓ_gen全部bundle确实learning_rule=
    "frozen"，支撑exists_without_learning=True不是凭空声明。"""
    circuit = RPrecCircuitT1()
    bundles = circuit.rprec_relation_bundles()

    assert len(bundles) == 12  # 4条xi→trace + 8条trace/raw→collector
    non_frozen = [b.config.bundle_id for b in bundles
                 if b.config.learning_rule != "frozen"]
    assert non_frozen == [], (
        f"Θ算子存在资格声明exists_without_learning=True要求ℓ_gen全部"
        f"frozen，实际发现非frozen bundle: {non_frozen}")

    binding = build_theta_binding_from_rprec_t1(circuit)
    assert audit_exists_without_learning(binding.contract) is True

    print(f"T-TSS0-3: {len(bundles)}条ℓ_gen bundle全部learning_rule='frozen'")
    print("✓ T-TSS0-3 PASS: exists_without_learning=True有真实电路证据支撑，"
          "非凭空声明")


def test_tss0_4_sigma_lambda_are_placeholders_only():
    """T-TSS0-4：Σ^(1)/Λ^(1)只是类型占位，不含任何真实电路引用——
    确认TSS-0未越界新增动力学。"""
    sigma = GeneratorSigmaBinding()
    lambda_ = GeneratorLambdaBinding()

    assert sigma.input_generators == ()
    assert sigma.physical_carriers == ()
    assert sigma.contract.operator_type == "sigma"

    assert lambda_.input_generators == ()
    assert lambda_.physical_carriers == ()
    assert lambda_.contract.operator_type == "lambda"

    # 确认禁止字段包含评判明确点名的语义标签
    assert "euclidean_coordinate" in sigma.contract.forbidden_decision_fields
    assert "resolution_label" in lambda_.contract.forbidden_decision_fields

    print(f"T-TSS0-4: sigma.input_generators={sigma.input_generators}, "
          f"lambda.input_generators={lambda_.input_generators}（均为空占位）")
    print("✓ T-TSS0-4 PASS: Σ/Λ仅冻结类型，无真实电路引用，未越界新增动力学")


def run():
    test_tss0_1_theta_contract_fields()
    test_tss0_2_binding_uses_real_objects()
    test_tss0_3_evidence_frozen_bundles()
    test_tss0_4_sigma_lambda_are_placeholders_only()
    print()
    print("=" * 60)
    print("T-TSS0-1~4 ALL PASS")
    print("=" * 60)


if __name__ == "__main__":
    run()
