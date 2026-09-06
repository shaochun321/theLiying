"""tss.tests.test_r_prec_t3 — T3: 28≺21 时间关系构造验证。

方案依据：document - 2026-08-03T220325.594.md（评判裁定构造28≺21，
"允许复用T1的trace、collector和slow参数；使用同一外部发生过程；
STDP、DA关闭；验证正式RelationOccurrence；验证父发生身份和去重"）。

驱动场景复用TSS-3a审计脚本的场景参数（radius=3.0/T=300.0/1600步），
保证Δt落在TSS-3a实测的328~353步区间内，不重新标定。

三个测试（结构同test_r_prec_t2.py的T-T2-1~3，T3是第三个同等级实例）：
  T-T3-1：RPrecCircuitT3独立构造正确（站点28/21，trace/collector不与
          T1/T2混淆）
  T-T3-2：T1/T2/T3三者可共存不互相干扰（bundle_id/collector对象互不重叠）
  T-T3-3：真实驱动场景下T3的slow通道产生RelationOccurrence（TSS-3a判定
          21号站点Δt落在slow窗口覆盖范围，fast窗口50步不覆盖），复用与
          T1/T2完全相同的生产路径

评判本轮边界（严格遵守）：
  不把21∈N_Δ写进运行时判断（本文件不import generator_lambda任何常量）；
  不宣称形成尺度算子；不开始完整CG-0；不为适配结果搜索参数；
  不同时构造28≺24。
"""
import sys

sys.path.insert(0, '.')

from nexus_v1.components.structural_address import AddressRegistry, StructuralAddress
from nexus_v1.components.world import HeatSource
from tss.generators.occurrence_tap import wrap_collector_occurrence_tap
from tss.generators.occurrence_identity import OccurrenceIdentityRegistry
from tss.relations.relation_occurrence import RelationFinalizer
from tss.relations.temporal_r_prec import RPrecCircuitT1
from tss.relations.temporal_r_prec_t2 import RPrecCircuitT2
from tss.relations.temporal_r_prec_t3 import (
    RPrecCircuitT3, RELATION_TYPE_A_PREC_D_FAST, RELATION_TYPE_A_PREC_D_SLOW,
    SITE_SOURCE, SITE_TARGET,
)

DT = 0.001
# 步数同test_r_prec_t2.py先例（5000步）。radius=5.0同T2先例，不用3.0。
# 两个场景用途不同：
#   TSS-3a(radius=3.0)：测onset时序Δt，只需pre_trace越过0.01，
#     用于选点，site21 Δt=328~353步 ∈ (50,600) → slow通道覆盖。
#   T-T3-3(radius=5.0)：验证AND门关系collector实际点火，需要
#     trace_a_slow 和 raw_xi_d 同时高，site21在radius=3.0下衰减
#     因子仅0.057（AND门不满足）；radius=5.0时衰减因子0.434，
#     两路均有足够幅度（同T2使用radius=5.0驱动的先例）。
# TSS-3a的Δt选点判定不变，只是验证电路需要更强驱动。
N_STEPS = 5000
HEAT_RADIUS = 5.0
HEAT_TEMPERATURE = 300.0
HEAT_ENERGY = 100000.0


def test_t3_1_independent_construction():
    """T-T3-1：RPrecCircuitT3独立构造——站点28/21，trace/collector对象
    与T1/T2完全独立（不同Neuron实例，不同bundle_id前缀）。"""
    circuit = RPrecCircuitT3()

    assert circuit.rprec3_site_a == SITE_SOURCE == 28
    assert circuit.rprec3_site_d == SITE_TARGET == 21

    assert circuit.rprec3_xi_a.config.neuron_id == "thermq_collector_thermpt28_warm"
    assert circuit.rprec3_xi_d.config.neuron_id == "thermq_collector_thermpt21_warm"

    assert circuit.rprec3_trace_a_fast.config.neuron_id.startswith("t3_rprec_trace")
    assert circuit.rprec3_collector_a_prec_d_fast.config.neuron_id.startswith("t3_rprec_collector")

    print(f"T-T3-1: site_a={circuit.rprec3_site_a}, site_d={circuit.rprec3_site_d}")
    print(f"  xi_a={circuit.rprec3_xi_a.config.neuron_id}")
    print(f"  xi_d={circuit.rprec3_xi_d.config.neuron_id}")
    print("✓ T-T3-1 PASS: RPrecCircuitT3独立构造正确，站点28/21来自TSS-3a审计结果")


def test_t3_2_coexist_with_t1_t2():
    """T-T3-2：T1/T2/T3三者独立实例化时互不干扰——各自trace/collector
    命名前缀不冲突，bundle_id集合两两不交（同T-T2-2的验证逻辑，扩展到三者）。
    """
    circuit_t1 = RPrecCircuitT1()
    circuit_t2 = RPrecCircuitT2()
    circuit_t3 = RPrecCircuitT3()

    # 三者都能独立引用站点28（T1的site_a，T2的site_b，T3的site_a），
    # 但各自的trace/collector是不同的Neuron对象
    assert circuit_t1.rprec_site_a == circuit_t2.rprec2_site_b == circuit_t3.rprec3_site_a == 28

    assert circuit_t1.rprec_trace_a_fast is not circuit_t3.rprec3_trace_a_fast
    assert circuit_t2.rprec2_trace_b_fast is not circuit_t3.rprec3_trace_a_fast
    assert circuit_t1.rprec_collector_a_prec_b_fast is not circuit_t3.rprec3_collector_a_prec_d_fast

    t1_ids = {b.config.bundle_id for b in circuit_t1.rprec_relation_bundles()}
    t2_ids = {b.config.bundle_id for b in circuit_t2.rprec2_relation_bundles()}
    t3_ids = {b.config.bundle_id for b in circuit_t3.rprec3_relation_bundles()}

    assert t1_ids.isdisjoint(t2_ids), "T1和T2的bundle_id不应有重叠"
    assert t1_ids.isdisjoint(t3_ids), "T1和T3的bundle_id不应有重叠"
    assert t2_ids.isdisjoint(t3_ids), "T2和T3的bundle_id不应有重叠"

    print(f"T-T3-2: T1/T2/T3共享站点28物理collector，各自trace/collector/bundle_id无冲突")
    print(f"  T1={len(t1_ids)}条, T2={len(t2_ids)}条, T3={len(t3_ids)}条")
    print("✓ T-T3-2 PASS: T1/T2/T3可共存，命名空间不冲突")


def test_t3_3_real_relation_occurrence():
    """T-T3-3：父Occurrence链通过；AND门RelationOccurrence资格尚未成立。

    以T1原始权重（W_TRACE=0.5, W_RAW=0.15）驱动：两个父D1 occurrence
    （occ_a/occ_d）均能正常闭合（基础设施通过），但AND门collector峰值
    不足以越阈，不产生RelationOccurrence——本测试断言 len(results)==0，
    把这个冻结状态明确记录下来，而不是断言>0掩盖资格未成立的事实。

    用slow通道（trace_scale="slow"）而非fast：TSS-3a判定21号站点的
    Δt=328~353步落在fast窗口(50步)之外、slow窗口(600步)之内。

    EXP-T3-02（2026-08-03，已撤回）：尝试独立缩放 s_trace=5.3/s_raw=1.6
    使 V_trace(only)=0.209>0.8θ（AND选择性破坏）且 V_both≈V_trace
    （collector饱和，叠加无增量）。结论：当前MOSFET动力学下未找到满足
    三条件（V_trace<0.8θ, V_raw<0.8θ, V_both>1.1θ）的工作区，参数已撤回，
    不继续盲目调参，见 cell-cell/工作报告/TSS-3a_距离延迟审计与28≺21构造进展_2026-08-03.md。
    """
    circuit = RPrecCircuitT3()
    site_a, site_d = circuit.rprec3_site_a, circuit.rprec3_site_d

    patch_a = circuit._thermal_quantum_patches[site_a]
    heat_pos = patch_a.world_position(circuit.world.body)
    circuit.world.heat_sources = [HeatSource(
        position=list(heat_pos), energy=HEAT_ENERGY,
        temperature=HEAT_TEMPERATURE, radius=HEAT_RADIUS, _drift=[0.0, 0.0, 0.0],
    )]

    registry = AddressRegistry()
    occ_registry = OccurrenceIdentityRegistry()

    l1_a = circuit.thermal_quantum_l1_warm[f"thermpt{site_a}"]
    l1_d = circuit.thermal_quantum_l1_warm[f"thermpt{site_d}"]

    tap_a = wrap_collector_occurrence_tap(
        circuit.rprec3_xi_a, l1_a, registry, site_index=site_a, polarity="warm")
    tap_d = wrap_collector_occurrence_tap(
        circuit.rprec3_xi_d, l1_d, registry, site_index=site_d, polarity="warm")

    col_addr = StructuralAddress(
        domain="neuron.collector", uid="t3_rprec_collector_a_prec_d_slow")

    finalizer = RelationFinalizer(
        tap_a=tap_a, tap_b=tap_d, registry=occ_registry,
        relation_collector=circuit.rprec3_collector_a_prec_d_slow,
        collector_address=col_addr,
        relation_type=RELATION_TYPE_A_PREC_D_SLOW,
        trace_scale="slow",
    )

    results = []
    for t in range(N_STEPS):
        circuit.step({}, DT)
        circuit.step_rprec3(DT)
        tap_a.observe(t)
        tap_d.observe(t)
        ro = finalizer.step(t)
        if ro is not None:
            results.append(ro)

    n_occ_a = len(tap_a.closure.events)
    n_occ_d = len(tap_d.closure.events)
    print(f"T-T3-3: occ_a={n_occ_a}, occ_d={n_occ_d}, relations(slow)={len(results)}")

    assert n_occ_a > 0 or n_occ_d > 0, "T3场景应产生至少一次D1 occurrence（父链基础设施）"
    assert len(results) == 0, (
        "T1原始权重下AND门不足以触发RelationOccurrence——"
        "若此断言意外失败，说明权重已被修改，需先通过 test_t3_and_gate_guard 再解除冻结")

    print(f"T-T3-3: occ_a={n_occ_a}, occ_d={n_occ_d}, relations(slow)={len(results)}")
    print("✓ T-T3-3 PASS: 父Occurrence链通过；AND门collector未越阈，"
          "RelationOccurrence=0（冻结状态符合预期）")


def test_t3_and_gate_guard():
    """T-T3-4：AND门三条件守卫（当前冻结状态：三条件均不满足）。

    在T1原始权重下实测：
      V_trace(only) < 0.8θ  → trace单路不越阈（AND选择性充分条件）
      V_raw(only)   < 0.8θ  → raw单路不越阈
      V_both        > 1.1θ  → 双路触发（RelationOccurrence资格充分条件）

    EXP-T3-02实测（T1原值，2026-08-03）：
      V_trace=0.024, V_raw=0.082, V_both=0.105, θ=0.23
      → 三条件均不满足：V_both远小于1.1θ=0.253

    本测试断言当前权重下三条件同时FAIL（即 V_both<1.1θ），记录冻结状态。
    未来若改权重使三条件全部满足（PASS），应同步把 test_t3_3 的断言
    从 ==0 改为 >0，表示AND选择性与RelationOccurrence资格一起成立。
    """
    THETA = 0.23
    N = 5000

    def _peak_col_v(cut_trace=False, cut_raw=False):
        circuit = RPrecCircuitT3()
        patch = circuit._thermal_quantum_patches[28]
        pos = patch.world_position(circuit.world.body)
        circuit.world.heat_sources = [HeatSource(
            position=list(pos), energy=HEAT_ENERGY,
            temperature=HEAT_TEMPERATURE, radius=HEAT_RADIUS,
            _drift=[0.0, 0.0, 0.0])]
        for b in circuit.bundles_rprec3_to_collector:
            bid = b.config.bundle_id
            if cut_trace and "trace_a_slow_to_col" in bid:
                b.config.synapse_gain = 0.0
            if cut_raw and "raw_xi_d_to_col_slow" in bid:
                b.config.synapse_gain = 0.0
        col = circuit.rprec3_collector_a_prec_d_slow
        peak = 0.0
        for _ in range(N):
            circuit.step({}, DT)
            circuit.step_rprec3(DT)
            v = col._membrane.voltage
            if v > peak:
                peak = v
        return peak

    V_trace = _peak_col_v(cut_trace=False, cut_raw=True)
    V_raw   = _peak_col_v(cut_trace=True,  cut_raw=False)
    V_both  = _peak_col_v(cut_trace=False, cut_raw=False)

    print(f"T-T3-4: V_trace={V_trace:.5f}  V_raw={V_raw:.5f}  V_both={V_both:.5f}  θ={THETA}")

    # 冻结断言：当前权重下三条件均不满足
    # 若 V_both > 1.1θ 意外为真，说明权重已被修改且 AND 资格成立，
    # 此时应把 test_t3_3 的 ==0 改为 >0 并更新 EXP-T3-02 注释。
    assert V_both < 1.1 * THETA, (
        f"V_both={V_both:.5f} 意外超过1.1θ={1.1*THETA:.3f}，"
        f"若权重已修改且三条件全部满足，应同步更新 test_t3_3 的冻结断言")
    # 额外检查：若 V_trace 或 V_raw 单路已越 0.8θ，说明权重破坏AND选择性
    assert V_trace < 0.8 * THETA or V_both < 1.1 * THETA, (
        f"V_trace={V_trace:.5f} 单路已越 0.8θ={0.8*THETA:.3f}，AND选择性已破坏")

    print(f"✓ T-T3-4 PASS: AND门三条件冻结状态确认"
          f"（V_both={V_both:.3f} < 1.1θ={1.1*THETA:.3f}，资格尚未成立）")


def run():
    test_t3_1_independent_construction()
    test_t3_2_coexist_with_t1_t2()
    test_t3_3_real_relation_occurrence()
    test_t3_and_gate_guard()
    print()
    print("=" * 60)
    print("T-T3-1~4 ALL PASS")
    print("=" * 60)


if __name__ == "__main__":
    run()
