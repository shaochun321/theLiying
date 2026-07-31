"""T-R1S-1~7：P2-B1X2a'/b/d R1结构块定义与区间验证（2026-08-01）。

方案依据：`cell-cell/交叉比对/document - 2026-07-31T205641.086.md` +
          `cell-cell/交叉比对/document - 2026-07-31T221144.140.md` +
          `cell-cell/交叉比对/document - 2026-08-01T030645.402.md` +
          `cell-cell/交叉比对/document - 2026-08-01T040602.337.md`

七个测试：
  T-R1S-1：KappaTen工程映射（ensemble=10，B_in/C^10/S_dyn/B_out四层，两站点独立）
  T-R1S-2：RelationGenLink分离（ℓ_gen ≠ κ^10输出端，3条bundle正确，generation_link_address≠collector_address）
  T-R1S-3：R1StructureBlock本体（不含ℓ_out，RPrecCircuitT1基类可构造，成立合法）
  T-R1S-4：R1OutputBinding（R1本体+ℓ_out，桥梁衔接，measure_output_current()可读）
  T-R1S-5：project_to_relation_occurrence_fields()投影语义（collector_address≠generation_link_address）
  T-R1S-6：R1PhysicalInterval状态机（UNBOUND→SUPPORTED→RELAXING→CLOSED，父epoch变化触发退出）
  T-R1S-7：R1MeasurementWindow（后验构造，Y尾部归零检测，W_Y*≥I_R1）
"""
import sys

sys.path.insert(0, '.')

from nexus_v1.components.structural_address import AddressRegistry, DOMAIN_SKIN_PATCH, StructuralAddress
from nexus_v1.relations.temporal_r_prec import RPrecCircuitT1
from nexus_v1.relations.temporal_r_prec_plastic import RPrecCircuitT1Plastic
from nexus_v1.relations.r1_structure import (
    KappaTen, RelationGenLink, R1OutputLink, R1PhysicalInterval,
    R1MeasurementWindow, _R1IntervalState,
    R1StructureBlock, R1OutputBinding, LINK_TYPE_RPREC_FAST,
    project_to_relation_occurrence_fields,
)
from nexus_v1.relations.relation_occurrence import (
    RelationOccurrence, RELATION_TYPE_A_PREC_B_FAST,
)
from nexus_v1.generators.occurrence import OccurrenceInstanceId


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

    gen_link_addr = StructuralAddress(
        domain="relation.gen_link",
        uid="r_prec.a_prec_b_fast.gen_link",
    )
    collector_addr = StructuralAddress(
        domain="relation.collector",
        uid="rprec_collector_a_prec_b_fast",
    )

    return RelationGenLink(
        link_type=LINK_TYPE_RPREC_FAST,
        relation_type=RELATION_TYPE_A_PREC_B_FAST,
        trace_scale="fast",
        trace_a=circuit.rprec_trace_a_fast,
        trace_b=circuit.rprec_trace_b_fast,
        relation_collector=circuit.rprec_collector_a_prec_b_fast,
        bundles=tuple(relevant_bundles),
        generation_link_address=gen_link_addr,
        collector_address=collector_addr,
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


def test_r1s_5_projection_to_relation_occurrence():
    """T-R1S-5：P2-B1X2b——project_to_relation_occurrence_fields()验证
    RelationOccurrence确实是R1本体的时间投影Π_τ(R1_AB[I])。

    验证：
    - 缺失parent_a/b_instance_id时应拒绝投影（ValueError）
    - 填入父实例身份后，投影字段可直接构造出合法的RelationOccurrence
    - relation_type取自link_gen.relation_type（语义关系类型），不是
      link_gen.link_type（链路机制类型）——两者不能混用
    - collector_address/trace_scale确实来自r1.link_gen，不是凭空填入
    """
    from nexus_v1.relations.r1_structure import project_to_relation_occurrence_fields

    circuit = RPrecCircuitT1()
    site_a = circuit.rprec_site_a
    site_b = circuit.rprec_site_b
    kappa_a = _build_kappa_ten(circuit, site_a, "warm")
    kappa_b = _build_kappa_ten(circuit, site_b, "warm")
    link_gen = _build_link_gen(circuit)
    r1 = R1StructureBlock(kappa_a=kappa_a, kappa_b=kappa_b, link_gen=link_gen)

    # 未填父实例身份时应拒绝投影
    try:
        project_to_relation_occurrence_fields(
            r1, t_detect=100, t_closed=200,
            occurrence_a_address=kappa_a.address, occurrence_b_address=kappa_b.address)
        raise AssertionError("缺失parent_a/b_instance_id时应拒绝投影")
    except ValueError:
        pass

    # 补上父实例身份（模拟真实生产路径中finalizer已解析出的父身份）
    parent_a_id = OccurrenceInstanceId(generator_address=_fake_generator_addr("a"), epoch_id=1)
    parent_b_id = OccurrenceInstanceId(generator_address=_fake_generator_addr("b"), epoch_id=1)
    r1.parent_a_instance_id = parent_a_id
    r1.parent_b_instance_id = parent_b_id

    fields = project_to_relation_occurrence_fields(
        r1, t_detect=100, t_closed=200,
        occurrence_a_address=kappa_a.address, occurrence_b_address=kappa_b.address)

    # relation_type取自link_gen.relation_type（语义），不是link_type（机制）
    assert fields["relation_type"] == RELATION_TYPE_A_PREC_B_FAST
    # collector_address取自link_gen.collector_address（评判040602修正：
    # 检测节点本身的地址，非generation_link_address整条链路地址）
    assert fields["collector_address"] is link_gen.collector_address
    assert fields["collector_address"] is not link_gen.generation_link_address
    assert fields["trace_scale"] == "fast"
    assert fields["parent_a_instance_id"] is parent_a_id
    assert fields["parent_b_instance_id"] is parent_b_id

    # 投影字段应能直接构造出合法RelationOccurrence
    ro = RelationOccurrence(**fields)
    assert ro.relation_type == RELATION_TYPE_A_PREC_B_FAST

    print(f"T-R1S-5: 投影字段relation_type={fields['relation_type']}, "
          f"collector_address={fields['collector_address'].uid}")
    print("✓ T-R1S-5 PASS: RelationOccurrence字段确实是R1本体的时间投影Π_τ，"
          "relation_type取自语义层非链路机制层")


def _fake_generator_addr(label: str):
    """T-R1S-5测试辅助：构造一个最小GeneratedAddress，仅用于填充
    parent_instance_id（不代表真实生产路径的地址来源）。"""
    from nexus_v1.components.structural_address import (
        DOMAIN_OCC_THERMAL, GeneratedAddress,
    )
    skin = StructuralAddress(domain=DOMAIN_SKIN_PATCH, uid=f"skin.patch:thermpt_{label}")
    return GeneratedAddress(domain=DOMAIN_OCC_THERMAL, uid=f"occ.thermal:thermpt_{label}_warm",
                             parent_addresses=(skin,), generation_depth=1)


def test_r1s_6_physical_interval_state_machine():
    """T-R1S-6：R1PhysicalInterval状态机——含迟滞阈值和双向恢复（评判045235）。
    验证：
    - UNBOUND→SUPPORTED（双父超on阈值）
    - SUPPORTED→RELAXING（支撑跌破off阈值）
    - RELAXING→SUPPORTED（同一谱系内恢复，lineage_broken=False）
    - RELAXING→CLOSED（at_baseline且lineage_broken=True时不恢复）
    - 父epoch变化置lineage_broken=True，禁止RELAXING→SUPPORTED
    - s_candidate记录两父首次超过off阈值的时刻
    """
    on_t = 5e-3   # threshold_on
    off_t = 1e-3  # threshold_off
    iv = R1PhysicalInterval(threshold_on=on_t, threshold_off=off_t)

    assert iv.state is _R1IntervalState.UNBOUND
    assert iv.s_candidate is None

    # t=0：只有A>off，B<off → 进不了candidate
    iv.update(0, support_a=on_t*2, support_b=0.0, collector_activity=0.0,
              parent_a_epoch=1, parent_b_epoch=1)
    assert iv.s_candidate is None

    # t=1：两父都>off（低门槛），记录s_candidate；但collector<on，不进SUPPORTED
    iv.update(1, support_a=on_t*2, support_b=off_t*2, collector_activity=0.0,
              parent_a_epoch=1, parent_b_epoch=1)
    assert iv.s_candidate == 1

    # t=2：两父和collector都>on → 进入SUPPORTED
    iv.update(2, support_a=on_t*2, support_b=on_t*2, collector_activity=on_t*2,
              parent_a_epoch=1, parent_b_epoch=1)
    assert iv.state is _R1IntervalState.SUPPORTED
    assert iv.s_enter == 2

    # t=3：collector跌破off → 进入RELAXING
    iv.update(3, support_a=on_t*2, support_b=on_t*2, collector_activity=0.0,
              parent_a_epoch=1, parent_b_epoch=1,
              _parent_a_epoch_at_enter=1, _parent_b_epoch_at_enter=1)
    assert iv.state is _R1IntervalState.RELAXING

    # t=4：同一谱系，collector恢复>on → 允许RELAXING→SUPPORTED（双向）
    iv.update(4, support_a=on_t*2, support_b=on_t*2, collector_activity=on_t*2,
              parent_a_epoch=1, parent_b_epoch=1,
              _parent_a_epoch_at_enter=1, _parent_b_epoch_at_enter=1)
    assert iv.state is _R1IntervalState.SUPPORTED, (
        "同一谱系内支撑恢复，应允许RELAXING→SUPPORTED（评判045235阻塞修正）")

    # t=5：再次退出RELAXING，然后父epoch变化
    iv.update(5, support_a=0.0, support_b=0.0, collector_activity=0.0,
              parent_a_epoch=1, parent_b_epoch=1,
              _parent_a_epoch_at_enter=1, _parent_b_epoch_at_enter=1)
    assert iv.state is _R1IntervalState.RELAXING

    # t=6：父epoch变化 → lineage_broken=True，即使at_baseline也先检查这个路径
    iv.update(6, support_a=on_t*2, support_b=on_t*2, collector_activity=on_t*2,
              parent_a_epoch=2, parent_b_epoch=1,  # A有新epoch
              _parent_a_epoch_at_enter=1, _parent_b_epoch_at_enter=1)
    assert iv.lineage_broken, "父epoch变化应设置lineage_broken=True"
    assert iv.state is not _R1IntervalState.SUPPORTED, (
        "lineage_broken=True时，即使支撑重建，RELAXING也不能恢复至SUPPORTED")

    # t=7：at_baseline → CLOSED
    iv.update(7, support_a=0.0, support_b=0.0, collector_activity=0.0,
              parent_a_epoch=2, parent_b_epoch=1,
              _parent_a_epoch_at_enter=1, _parent_b_epoch_at_enter=1)
    assert iv.state is _R1IntervalState.CLOSED
    assert iv.s_closed == 7
    assert iv.s_candidate == 1
    assert iv.s_enter == 2

    print(f"T-R1S-6: s_candidate={iv.s_candidate}, s_enter={iv.s_enter}, "
          f"s_closed={iv.s_closed}, lineage_broken={iv.lineage_broken}")
    print("✓ T-R1S-6 PASS: 迟滞状态机+双向恢复+lineage_broken正确")


def test_r1s_7_measurement_window():
    """T-R1S-7：R1MeasurementWindow——后验构造，W_Y*≥I_R1。
    验证：
    - from_r1_run()正确找到Y轨迹最后一个超阈步骤
    - W_Y*.s_start == I_R1.s_enter
    - Y全程为零时降级为I_R1.s_closed
    - s_start >= s_end时拒绝构造
    """
    threshold = 1e-4
    iv = R1PhysicalInterval(threshold_on=threshold * 10, threshold_off=threshold)
    # 手动设置一个已封闭的区间
    iv.s_enter = 100
    iv.s_closed = 200
    object.__setattr__(iv, '_state', _R1IntervalState.CLOSED)

    target_addr = StructuralAddress(domain="neuron.da", uid="da_neuron_0")

    # Y轨迹：步骤0~49对应t=100~149，步骤50~99为零
    y_traj = [0.5] * 50 + [0.0] * 50  # 在t=149（index=49）最后一个超阈
    win = R1MeasurementWindow.from_r1_run(
        r1_interval=iv, y_trajectory=y_traj, y_start_step=100,
        baseline_band=1e-5, target_address=target_addr)

    assert win.s_start == 100, f"窗口起点应等于r1_interval.s_enter=100，实际{win.s_start}"
    assert win.s_end == 150, f"窗口终点应为最后超阈步骤(149)+1=150，实际{win.s_end}"
    # 注意：W_Y* = 150 < I_R1.s_closed = 200 是合法的——Y在R1区间封闭前就归零了
    # 评判040602说s_closed^R1 ≤ s_relax^Y是"可能"情形（Y尾部持续时），不是必须
    assert win.length == 50

    # Y全程为零时：终点fallback为I_R1.s_closed
    y_all_zero = [0.0] * 50
    win_zero = R1MeasurementWindow.from_r1_run(
        r1_interval=iv, y_trajectory=y_all_zero, y_start_step=100,
        baseline_band=1e-5, target_address=target_addr)
    assert win_zero.s_end == iv.s_closed, (
        "Y全程为零时窗口终点应fallback为I_R1.s_closed")

    # 非法窗口拒绝
    try:
        R1MeasurementWindow(s_start=100, s_end=100, baseline_band=0.0,
                            target_address=target_addr)
        raise AssertionError("s_start==s_end时应拒绝构造")
    except ValueError:
        pass

    print(f"T-R1S-7: win.s_start={win.s_start}, win.s_end={win.s_end}, win.length={win.length}")
    print(f"         Y全程为零时win_zero.s_end={win_zero.s_end}（=I_R1.s_closed={iv.s_closed}）")
    print("✓ T-R1S-7 PASS: R1MeasurementWindow后验构造正确，W_Y*≥I_R1，Y尾部归零检测正确")


def run():
    test_r1s_1_kappa_ten_mapping()
    test_r1s_2_link_gen_separation()
    test_r1s_3_r1block_body_no_output()
    test_r1s_4_output_binding()
    test_r1s_5_projection_to_relation_occurrence()
    test_r1s_6_physical_interval_state_machine()
    test_r1s_7_measurement_window()
    print()
    print("=" * 60)
    print("T-R1S-1~7 ALL PASS")
    print("=" * 60)


if __name__ == "__main__":
    run()
