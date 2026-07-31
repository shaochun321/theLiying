"""T-R1S-1~4：P2-B1X2a' R1最小结构块定义验证（2026-08-01，评判030645修正）。

方案依据：`cell-cell/交叉比对/document - 2026-07-31T205641.086.md` +
          `cell-cell/交叉比对/document - 2026-07-31T221144.140.md` +
          `cell-cell/交叉比对/document - 2026-08-01T030645.402.md`

评判030645修正：T-R1S-3改为验证R1StructureBlock（本体，无ℓ_out字段），
新增T-R1S-4验证R1OutputBinding（R1本体+ℓ_out），并验证RPrecCircuitT1
（基类）构造的R1本体在无ℓ_out时仍然合法（不是"R1不完整"）。

四个测试：
  T-R1S-1：KappaTen工程映射（ensemble=10，B_in/C^10/S_dyn/B_out四层，两站点独立）
  T-R1S-2：RelationGenLink分离（ℓ_gen ≠ κ^10输出端，3条bundle正确）
  T-R1S-3：R1StructureBlock本体（不含ℓ_out，RPrecCircuitT1基类可构造，成立合法）
  T-R1S-4：R1OutputBinding（R1本体+ℓ_out，桥梁衔接，measure_output_current()可读）
"""
import sys

sys.path.insert(0, '.')

from nexus_v1.components.structural_address import AddressRegistry, DOMAIN_SKIN_PATCH, StructuralAddress
from nexus_v1.relations.temporal_r_prec import RPrecCircuitT1
from nexus_v1.relations.temporal_r_prec_plastic import RPrecCircuitT1Plastic
from nexus_v1.relations.r1_structure import (
    KappaTen, RelationGenLink, R1OutputLink, R1PhysicalInterval,
    R1StructureBlock, R1OutputBinding, LINK_TYPE_RPREC_FAST,
)


def _build_kappa_ten(circuit, site_index: int, polarity: str) -> KappaTen:
    """从RPrecCircuitT1构造一个κ^10（工程映射辅助函数）。"""
    pid = f"thermpt{site_index}"
    label = f"{pid}_{polarity}"
    addr = StructuralAddress(domain=DOMAIN_SKIN_PATCH, uid=f"skin.patch:{pid}")

    l1 = (circuit.thermal_quantum_l1_warm[pid] if polarity == "warm"
          else circuit.thermal_quantum_l1_cool[pid])
    hc = (circuit.thermal_quantum_hc_warm[pid] if polarity == "warm"
          else circuit.thermal_quantum_hc_cool[pid])
    ensemble_list = circuit.thermal_quantum_ensembles[label]
    collector = circuit.thermal_quantum_collectors[label]

    return KappaTen(
        site_index=site_index, polarity=polarity,
        l1=l1, hc=hc,
        ensemble=tuple(ensemble_list),
        collector=collector,
        address=addr,
    )


def _build_link_gen(circuit) -> RelationGenLink:
    """从RPrecCircuitT1构造ℓ_gen（a_prec_b_fast）。"""
    # ℓ_gen内部bundle = trace输入 + trace到collector + raw xi_b到collector
    relevant_bundles = []
    for b in circuit.rprec_relation_bundles():
        bid = b.config.bundle_id
        if bid in ("rprec_xi_a_to_trace_fast",
                   "rprec_trace_a_fast_to_col",
                   "rprec_raw_xi_b_to_col_fast"):
            relevant_bundles.append(b)

    link_addr = StructuralAddress(
        domain="relation.gen_link",
        uid="r_prec.a_prec_b_fast.gen_link",
    )

    return RelationGenLink(
        link_type=LINK_TYPE_RPREC_FAST,
        trace_scale="fast",
        trace_a=circuit.rprec_trace_a_fast,
        trace_b=circuit.rprec_trace_b_fast,
        relation_collector=circuit.rprec_collector_a_prec_b_fast,
        bundles=tuple(relevant_bundles),
        link_address=link_addr,
    )


def test_r1s_1_kappa_ten_mapping():
    """T-R1S-1：KappaTen工程映射——从RPrecCircuitT1按(site_index, polarity)
    构造κ^10，验证：
    - ensemble恰好10个神经元
    - l1是输入端口（ThermalDeltaNeuron），collector是输出端口（spiking）
    - l1 ≠ collector（不同对象）
    - 对两个站点分别构造，彼此独立（l1_a ≠ l1_b，collector_a ≠ collector_b）
    """
    circuit = RPrecCircuitT1()
    site_a = circuit.rprec_site_a
    site_b = circuit.rprec_site_b

    kappa_a = _build_kappa_ten(circuit, site_a, "warm")
    kappa_b = _build_kappa_ten(circuit, site_b, "warm")

    # ensemble必须恰好10个
    assert len(kappa_a.ensemble) == 10, f"κ_a ensemble应有10个神经元，实际{len(kappa_a.ensemble)}"
    assert len(kappa_b.ensemble) == 10

    # 输入端口与输出端口是不同对象
    assert kappa_a.l1 is not kappa_a.collector
    assert kappa_b.l1 is not kappa_b.collector

    # 输出端口是spiking（collector）
    assert kappa_a.collector.config.spiking, "κ_a的collector应是spiking神经元（AND门）"
    assert kappa_b.collector.config.spiking

    # 两个基元的对象互相独立
    assert kappa_a.l1 is not kappa_b.l1, "κ_a和κ_b的L1应是不同对象（不同站点）"
    assert kappa_a.collector is not kappa_b.collector

    print(f"T-R1S-1: κ_a(site={site_a}) l1={kappa_a.l1.config.neuron_id}, "
          f"collector={kappa_a.collector.config.neuron_id}")
    print(f"         κ_b(site={site_b}) l1={kappa_b.l1.config.neuron_id}, "
          f"collector={kappa_b.collector.config.neuron_id}")
    print("✓ T-R1S-1 PASS: KappaTen工程映射正确，输入端口=L1，输出端口=collector，两站点独立")


def test_r1s_2_link_gen_separation():
    """T-R1S-2：RelationGenLink字段验证——ℓ_gen包含trace/relation_collector/
    相关bundle；且ℓ_gen.relation_collector 是新的AND门（不是κ_A/κ_B的collector，
    即不把基元内部collector和关系检测collector混为一谈）。

    这是评判221144最重要的修正：
      κ_A.collector（thermptXX_warm的AND门）= κ^10的输出端口
      ℓ_gen.relation_collector（rprec_collector_a_prec_b_fast）= 关系检测的AND门
      两者是不同的Neuron对象。
    """
    circuit = RPrecCircuitT1()
    site_a = circuit.rprec_site_a
    site_b = circuit.rprec_site_b

    kappa_a = _build_kappa_ten(circuit, site_a, "warm")
    kappa_b = _build_kappa_ten(circuit, site_b, "warm")
    link_gen = _build_link_gen(circuit)

    # ℓ_gen包含trace神经元
    assert link_gen.trace_a is circuit.rprec_trace_a_fast
    assert link_gen.trace_b is circuit.rprec_trace_b_fast

    # ℓ_gen.relation_collector 是关系检测AND门（rprec_collector_a_prec_b_fast）
    assert link_gen.relation_collector is circuit.rprec_collector_a_prec_b_fast

    # 关键：ℓ_gen.relation_collector ≠ κ_A.collector（不是同一对象）
    assert link_gen.relation_collector is not kappa_a.collector, (
        "ℓ_gen的relation_collector（关系检测AND门）不应等同于κ_A的collector"
        "（基元内部AND门）——这是评判221144的核心修正")
    assert link_gen.relation_collector is not kappa_b.collector

    # ℓ_gen包含3条相关bundle（xi_a→trace, trace_a→col, raw_xi_b→col）
    assert len(link_gen.bundles) == 3, (
        f"ℓ_gen应包含3条bundle，实际{len(link_gen.bundles)}")

    print(f"T-R1S-2: ℓ_gen.relation_collector={link_gen.relation_collector.config.neuron_id}")
    print(f"         κ_a.collector={kappa_a.collector.config.neuron_id} (不同对象，正确)")
    print(f"         ℓ_gen.bundles={[b.config.bundle_id for b in link_gen.bundles]}")
    print("✓ T-R1S-2 PASS: ℓ_gen与κ^10的输出端口分开定义，两段链路不混淆")


def test_r1s_3_r1block_body_no_output():
    """T-R1S-3：R1StructureBlock本体——评判030645阻塞修正验证。

    用RPrecCircuitT1**基类**（没有bundle_rprec_to_da，没有ℓ_out）构造R1本体，
    验证：
    - R1本体成立完全不需要ℓ_out（R1StructureBlock不再有link_out字段）
    - relation_collector快捷属性正确指向ℓ_gen输出端
    - "没有输出链路"不是"R1不完整"——这是合法状态
    """
    circuit = RPrecCircuitT1()  # 注意：基类，没有bundle_rprec_to_da
    site_a = circuit.rprec_site_a
    site_b = circuit.rprec_site_b

    kappa_a = _build_kappa_ten(circuit, site_a, "warm")
    kappa_b = _build_kappa_ten(circuit, site_b, "warm")
    link_gen = _build_link_gen(circuit)

    r1 = R1StructureBlock(kappa_a=kappa_a, kappa_b=kappa_b, link_gen=link_gen)

    # relation_collector快捷属性应指向ℓ_gen.relation_collector
    assert r1.relation_collector is link_gen.relation_collector
    assert r1.relation_collector is circuit.rprec_collector_a_prec_b_fast

    # R1StructureBlock不应再有link_out字段（评判030645核心修正）
    assert not hasattr(r1, "link_out"), (
        "R1StructureBlock不应含link_out字段——ℓ_out已移至独立的R1OutputBinding类")
    assert not hasattr(r1, "has_output_link")
    assert not hasattr(r1, "measure_output_current")

    print(f"T-R1S-3: R1本体（RPrecCircuitT1基类，无bundle_rprec_to_da）构造成功")
    print(f"  relation_collector = {r1.relation_collector.config.neuron_id}")
    print("✓ T-R1S-3 PASS: R1本体不含ℓ_out仍合法成立，'关系存在'与'关系能否施力'已解耦")


def test_r1s_4_output_binding():
    """T-R1S-4：R1OutputBinding——R1本体+ℓ_out的组合绑定。

    用RPrecCircuitT1Plastic构造R1本体，再绑定ℓ_out为R1OutputBinding，
    验证：
    - output_link.source_collector 与 r1.relation_collector 是同一对象（桥梁）
    - 若二者不是同一对象，__post_init__应拒绝构造（ValueError）
    - measure_output_current()能正确读取局部电流
    """
    circuit = RPrecCircuitT1Plastic()
    site_a = circuit.rprec_site_a
    site_b = circuit.rprec_site_b

    kappa_a = _build_kappa_ten(circuit, site_a, "warm")
    kappa_b = _build_kappa_ten(circuit, site_b, "warm")
    link_gen = _build_link_gen(circuit)
    r1 = R1StructureBlock(kappa_a=kappa_a, kappa_b=kappa_b, link_gen=link_gen)

    out_addr = StructuralAddress(
        domain="relation.out_link", uid="r_prec.a_prec_b_fast.out_link")
    link_out = R1OutputLink(
        source_collector=circuit.rprec_collector_a_prec_b_fast,
        output_bundle=circuit.bundle_rprec_to_da,
        target_neurons=tuple(circuit.bundle_rprec_to_da.targets),
        link_address=out_addr,
    )

    binding = R1OutputBinding(r1=r1, output_link=link_out)

    assert binding.output_link.source_collector is binding.r1.relation_collector, (
        "ℓ_out.source_collector应与R1本体.relation_collector是同一对象（桥梁）")

    currents = binding.measure_output_current()
    assert currents is not None
    assert len(currents) == len(link_out.target_neurons)

    # 桥梁校验：用不匹配的collector构造应拒绝
    mismatched_link = R1OutputLink(
        source_collector=circuit.rprec_collector_b_prec_a_fast,  # 错误：不是同一collector
        output_bundle=circuit.bundle_rprec_to_da,
        target_neurons=tuple(circuit.bundle_rprec_to_da.targets),
        link_address=out_addr,
    )
    try:
        R1OutputBinding(r1=r1, output_link=mismatched_link)
        raise AssertionError("应拒绝source_collector与r1.relation_collector不一致的绑定")
    except ValueError:
        pass

    print(f"T-R1S-4: R1OutputBinding构造完成")
    print(f"  output_link.source_collector = {link_out.source_collector.config.neuron_id} (同一对象)")
    print(f"  measure_output_current() 返回 {len(currents)} 个电流值")
    print("✓ T-R1S-4 PASS: R1OutputBinding正确绑定R1本体+ℓ_out，桥梁校验生效")


def run():
    test_r1s_1_kappa_ten_mapping()
    test_r1s_2_link_gen_separation()
    test_r1s_3_r1block_body_no_output()
    test_r1s_4_output_binding()
    print()
    print("=" * 60)
    print("T-R1S-1~4 ALL PASS")
    print("=" * 60)


if __name__ == "__main__":
    run()
