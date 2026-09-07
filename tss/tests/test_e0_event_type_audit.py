"""tss.tests.test_e0_event_type_audit — E0：事件核/残差源类型审计测试(T-E0-1~4)。

TYPE:INFRA

路线依据：08_路线图 §8（E-1~E-5，开启条件"耦合走通"已由 c_ro §11 满足）
+ §10 E0 + §9 交付格式。契约：tss/events/event_core_contract.py。

测试映射：
  T-E0-1  契约自洽审计：六分量齐全、状态词合法、诚实守卫（至少一个 GAP、
          待裁定登记非空且编号规范）
  T-E0-2  可实例化审计：每个 EXISTS(_PARTIAL) 分量逐条对应真实对象——
          K=链路六元件类+地址谱系；θ=冻结常量共参；Π=D1→D2→D3 谱系可由
          既有 event_support 工厂走通；W=窗口 well-formed；𝒞=资格台账在盘
  T-E0-3  EXP-E0-01 复放算子地板：真实链路录制父关系电流 → 全新同参栈
          复放 → Y_replay 与 Y_live bit-exact（残差=REPLAY_RESIDUAL_FLOOR）；
          扰动录制（删除父 A 脉冲）→ 复放归零（复放对内容敏感，非同义反复）
  T-E0-4  越界守卫：契约模块零可执行结构（无函数/类/状态机）；
          create_event_candidate 拒绝路径仍生效（E-3 不授资格）；
          ℒ GAP 属实（tss 层元件不在 organism census）

真实链路测量（T-E0-3/4 共享）：单次外部发生 @site28，default 种子，
仅代表对 (24≺21) 涉及的 3 站点——录制即测量，一次驱动两个测试消费。
"""
import sys
sys.path.insert(0, '.')

import inspect
import os
import re

from nexus_v1.components.structural_address import (
    AddressRegistry, StructuralAddress, GeneratedAddress,
    DOMAIN_SKIN_PATCH, DOMAIN_OCC_THERMAL, DOMAIN_RELATION_PREC,
)
from nexus_v1.components.world import HeatSource
from tss.relations.boundary_process import CollectorBoundaryPort
from tss.relations.entry_gate import PhysicalEntryGate, make_entry_gate
from tss.relations.history_kernel import PhysicalHistoryKernel, make_history_kernel
from tss.relations.theta_comparator import PhysicalThetaComparator, make_theta_comparator
from tss.relations.relation_event_adapter import (
    RelationEventAdapter, RelationInputNeuron,
    _COLLECTOR_CAPACITANCE, _ADAPTER_PHYSICAL_SEED, _TRANSDUCER_WEIGHT,
)
from tss.relations.coupling_contract import QUALIFIED_LEVEL2_PAIRS
from tss.relations.temporal_r_prec import RPrecCircuitT1
from tss.tests.test_tss3a_theta_distance_audit import _reseed_site
from tss.tests.test_c1_coupling import (
    DT, N_STEPS, HEAT_RADIUS, SRC, T_READ, _make_l1_address, _PairStack,
)
from tss.events import event_core_contract as ecc
from tss.events import (
    EventSupportBinding, create_event_candidate,
    STATUS_CANDIDATE, STATUS_REJECTED_LINEAGE_MISMATCH,
)

_PAIR = (24, 21)   # C1 代表对（首轮唯一合格对，连续性）


# ─────────────────────────────────────────────────────────────────────
# 真实链路录制（T-E0-3/4 共享，惰性单次）
# ─────────────────────────────────────────────────────────────────────

def _fresh_pair_assembly(registry=None):
    """全新 (24≺21) 栈：与真实链路同标签同参的适配器 + _PairStack。

    标签与真实链路一致（relN） —— 虽然 physical_seed 显式共用已保证
    bundle_id 不污染物理（S0-bX1），复放审计仍取最强同一性形式。
    """
    registry = registry or AddressRegistry()
    a_i = _make_l1_address(registry, SRC)
    ax = _make_l1_address(registry, _PAIR[0])
    ay = _make_l1_address(registry, _PAIR[1])
    adapters = {
        _PAIR[0]: RelationEventAdapter(registry, a_i, ax, f"rel{SRC}p{_PAIR[0]}"),
        _PAIR[1]: RelationEventAdapter(registry, a_i, ay, f"rel{SRC}p{_PAIR[1]}"),
    }
    return adapters, _PairStack(registry, adapters, *_PAIR)


def _record_real_run():
    """真实链路单次外部发生：录制父关系电流 r_x/r_y + 现场 Y_live。"""
    circuit = RPrecCircuitT1()
    for s in (SRC,) + _PAIR:
        _reseed_site(circuit, s, None)
    patch = circuit._thermal_quantum_patches[SRC]
    pos = patch.world_position(circuit.world.body)
    circuit.world.heat_sources = [HeatSource(
        position=list(pos), energy=100000.0, temperature=300.0,
        radius=HEAT_RADIUS, _drift=[0.0, 0.0, 0.0])]

    registry = AddressRegistry()
    ports, gates, kernels = {}, {}, {}
    for s in (SRC,) + _PAIR:
        addr = _make_l1_address(registry, s)
        coll = circuit.thermal_quantum_collectors[f"thermpt{s}_warm"]
        ports[s] = CollectorBoundaryPort(generator_address=addr, carrier_ref=coll)
        gates[s] = make_entry_gate(ports[s])
        kernels[s] = make_history_kernel(gates[s])
    comps1 = {x: make_theta_comparator(kernels[SRC], gates[x]) for x in _PAIR}

    adapters = {x: RelationEventAdapter(
        registry, kernels[SRC].generator_address, gates[x].generator_address,
        f"rel{SRC}p{x}") for x in _PAIR}
    stack = _PairStack(registry, adapters, *_PAIR)

    r_rec = {x: [] for x in _PAIR}
    for t in range(N_STEPS):
        circuit.step({}, DT)
        b1, h1 = {}, {}
        for s in (SRC,) + _PAIR:
            b1[s] = gates[s].step(ports[s].spike_output, DT)
            h1[s] = kernels[s].step(b1[s], DT)
        for x in _PAIR:
            r = comps1[x].step(h1[SRC], b1[x], DT)
            r_rec[x].append(r)
            adapters[x].step(r, DT)
        stack.step(t, DT)

    census = circuit.get_all_neurons()
    tss_in_census = any(
        n is adapters[x].collector or n is adapters[x].input_neuron
        for x in _PAIR for n in census)
    return {
        "r_rec": r_rec,
        "live_fires": list(stack.fire_steps),
        "live_v": stack.downstream.voltage,
        "tss_in_census": tss_in_census,
    }


_RECORDED = None


def _recorded():
    global _RECORDED
    if _RECORDED is None:
        _RECORDED = _record_real_run()
        print(f"    [record] live_fires={_RECORDED['live_fires']} "
              f"live_v={_RECORDED['live_v']:.6f}")
    return _RECORDED


def _replay(r_rec):
    """把录制的父关系电流馈入全新同参栈（唯一合法注入点=声明父输入端口）。"""
    adapters, stack = _fresh_pair_assembly()
    for t in range(len(r_rec[_PAIR[0]])):
        for x in _PAIR:
            adapters[x].step(r_rec[x][t], DT)
        stack.step(t, DT)
    return list(stack.fire_steps), stack.downstream.voltage


# ─────────────────────────────────────────────────────────────────────
# T-E0-1：契约自洽审计
# ─────────────────────────────────────────────────────────────────────

def test_e0_1_contract_self_consistency():
    """T-E0-1：六分量齐全、状态词合法、诚实守卫。"""
    symbols = [row[0] for row in ecc.EVENT_KERNEL_COMPONENT_AUDIT]
    assert symbols == ["K", "theta", "Pi", "W", "L", "C"], (
        f"T-E0-1: 𝔈 六分量应恰好按序齐全，得到 {symbols}")

    statuses = [row[4] for row in ecc.EVENT_KERNEL_COMPONENT_AUDIT] + \
               [row[2] for row in ecc.ORGANIZATION_CONSTRAINT_AUDIT]
    for st in statuses:
        assert st in ecc._VALID_AUDIT_STATUSES, f"T-E0-1: 非法状态词 {st!r}"

    # 诚实守卫：类型审计不允许"全绿"——ℒ 缺口与 E-4 约束二待裁定必须可见
    assert ecc.AUDIT_GAP in statuses, "T-E0-1: 审计表必须保留真实缺口（ℒ）"
    assert ecc.AUDIT_RULING_REQUIRED in statuses, (
        "T-E0-1: E-4 约束二必须保持 RULING_REQUIRED，契约不得代行裁定")

    assert len(ecc.RULING_REQUIRED_REGISTRY) >= 1
    ids = [r[0] for r in ecc.RULING_REQUIRED_REGISTRY]
    assert len(ids) == len(set(ids)), "T-E0-1: 待裁定编号重复"
    for rid in ids:
        assert re.fullmatch(r"R-E0-\d+", rid), f"T-E0-1: 编号不规范 {rid!r}"

    assert len(ecc.RESIDUAL_SOURCE_CLASSES) == 4
    assert len(ecc.FORBIDDEN_CLAIMS) >= 4
    print("[PASS] T-E0-1 契约自洽：六分量/状态词/诚实守卫/待裁定登记")


# ─────────────────────────────────────────────────────────────────────
# T-E0-2：可实例化审计（EXISTS 状态逐条对应真实对象）
# ─────────────────────────────────────────────────────────────────────

def test_e0_2_component_instantiability():
    """T-E0-2：K/θ/Π/W/𝒞 逐分量落到真实对象或在盘资产。"""
    registry = AddressRegistry()
    adapters, stack = _fresh_pair_assembly(registry)

    # K：链路六元件全部为既有类实例，地址谱系已登记
    chain = [adapters[_PAIR[0]], adapters[_PAIR[1]],
             stack.gate2_x, stack.gate2_y, stack.kernel2_x, stack.comp2]
    expected = [RelationEventAdapter, RelationEventAdapter,
                PhysicalEntryGate, PhysicalEntryGate,
                PhysicalHistoryKernel, PhysicalThetaComparator]
    for obj, cls in zip(chain, expected):
        assert isinstance(obj, cls), f"T-E0-2(K): {obj!r} 不是 {cls.__name__}"
    for x in _PAIR:
        ga = adapters[x].generator_address
        assert isinstance(ga, GeneratedAddress)
        assert len(ga.parent_addresses) == 2 and ga.generation_depth == 2, (
            "T-E0-2(K/Π): 适配器地址应为深度2、双父谱系")

    # θ：冻结常量共参（全实例同一份——T-C1-7 的共参纪律在此复核最小面）
    for x in _PAIR:
        cfg = adapters[x].bundle.config
        assert cfg.physical_seed == _ADAPTER_PHYSICAL_SEED
        assert cfg.initial_weight == cfg.weight_max == _TRANSDUCER_WEIGHT
        assert abs(adapters[x].collector.config.capacitance
                   - _COLLECTOR_CAPACITANCE) == 0.0

    # Π：D1→D2→D3 谱系由既有 event_support 工厂走通（D3 仅候选登记）
    skin_a = registry.register_physical(DOMAIN_SKIN_PATCH, "e0_skin_a")
    skin_b = registry.register_physical(DOMAIN_SKIN_PATCH, "e0_skin_b")
    occ_a = registry.register_generated(
        DOMAIN_OCC_THERMAL, "e0_occ_a_epoch_1", (skin_a,), 1)
    occ_b = registry.register_generated(
        DOMAIN_OCC_THERMAL, "e0_occ_b_epoch_1", (skin_b,), 1)
    rel = registry.register_generated(
        DOMAIN_RELATION_PREC, "e0_rel_a_prec_b", (occ_a, occ_b), 2)
    kernel_addr = registry.register_generated(
        "event.kernel", "e0_kernel", (skin_a, skin_b), 2)
    binding = EventSupportBinding(
        kernel_address=kernel_addr,
        occurrence_a_address=occ_a, occurrence_b_address=occ_b,
        relation_address=rel,
        collector_address=StructuralAddress("neuron.collector", "e0_col", 0),
        bundle_address=StructuralAddress("bundle.relation", "e0_bun", 0),
        physical_support_addresses=(skin_a, skin_b),
        relation_kind="a_prec_b_fast", relation_window=(0, 100))
    cand = create_event_candidate(binding, t_enter=100,
                                  local_effect_measure=0.1, registry=registry)
    assert cand.qualification_status == STATUS_CANDIDATE
    assert cand.address.generation_depth == 3, (
        "T-E0-2(Π): D3 候选地址深度应为 3")

    # W：窗口 well-formed（0 < min ≤ max < 可读窗 723）
    for (x, y, mn, mx) in QUALIFIED_LEVEL2_PAIRS:
        assert 0 < mn <= mx < T_READ, (
            f"T-E0-2(W): ({x},{y}) 窗口 [{mn},{mx}] 越界")

    # 𝒞：资格台账在盘且含 C1 记录
    ledger_path = os.path.join(os.path.dirname(__file__), "..",
                               "QUALIFICATION_LEDGER.md")
    assert os.path.exists(ledger_path), "T-E0-2(𝒞): QUALIFICATION_LEDGER 缺失"
    with open(ledger_path, encoding="utf-8") as f:
        assert "c_ro" in f.read(), "T-E0-2(𝒞): 台账应含 c_ro 资格记录"
    print("[PASS] T-E0-2 可实例化：K/θ/Π/W/𝒞 逐条对应真实对象")


# ─────────────────────────────────────────────────────────────────────
# T-E0-3：EXP-E0-01 复放算子地板
# ─────────────────────────────────────────────────────────────────────

def test_e0_3_replay_operator_floor():
    """T-E0-3：frozen 链复放 bit-exact；扰动录制则输出归零。"""
    m = _recorded()
    assert m["live_fires"], (
        "T-E0-3 前提：(24≺21) 现场应产生 c_ro（T-C1-1 已资格）")

    fires_rp, v_rp = _replay(m["r_rec"])
    residual = abs(v_rp - m["live_v"])
    print(f"    [replay] fires={fires_rp} v={v_rp:.6f} residual={residual:.3e}")
    assert fires_rp == m["live_fires"], (
        f"T-E0-3: 复放产生步 {fires_rp} ≠ 现场 {m['live_fires']}")
    assert residual == ecc.REPLAY_RESIDUAL_FLOOR, (
        f"T-E0-3: 复放残差 {residual:.3e} ≠ 契约地板 "
        f"{ecc.REPLAY_RESIDUAL_FLOOR}——若为实测漂移，更新契约常量并溯源，"
        "不得当阈值调")

    # 扰动敏感性：删除父 A 的关系脉冲 → 复放必须归零（非同义反复守卫）
    r_cut = {_PAIR[0]: [0.0] * len(m["r_rec"][_PAIR[0]]),
             _PAIR[1]: m["r_rec"][_PAIR[1]]}
    fires_cut, v_cut = _replay(r_cut)
    assert fires_cut == [] and v_cut == 0.0, (
        f"T-E0-3: 删除父A后复放仍产生 fires={fires_cut} v={v_cut}")
    print("[PASS] T-E0-3 EXP-E0-01：复放 bit-exact（残差 0.0）+ 扰动归零")


# ─────────────────────────────────────────────────────────────────────
# T-E0-4：越界守卫
# ─────────────────────────────────────────────────────────────────────

def test_e0_4_no_overreach_guards():
    """T-E0-4：契约零可执行结构；E-3 拒绝路径生效；ℒ GAP 属实。"""
    # 契约模块必须是纯常量——无函数、无类、无状态机可执行体
    defined = [(n, o) for n, o in vars(ecc).items()
               if not n.startswith("__")
               and (inspect.isfunction(o) or inspect.isclass(o))
               and getattr(o, "__module__", None) == ecc.__name__]
    assert defined == [], (
        f"T-E0-4: 契约模块不得定义可执行结构，发现 {[n for n, _ in defined]}")

    # E-3 守卫：谱系错配仍被拒绝（登记≠资格）
    registry = AddressRegistry()
    skin_a = registry.register_physical(DOMAIN_SKIN_PATCH, "e0g_skin_a")
    skin_b = registry.register_physical(DOMAIN_SKIN_PATCH, "e0g_skin_b")
    occ_a = registry.register_generated(
        DOMAIN_OCC_THERMAL, "e0g_occ_a", (skin_a,), 1)
    occ_b = registry.register_generated(
        DOMAIN_OCC_THERMAL, "e0g_occ_b", (skin_b,), 1)
    occ_c = registry.register_generated(
        DOMAIN_OCC_THERMAL, "e0g_occ_c", (skin_b,), 1)
    rel_ab = registry.register_generated(
        DOMAIN_RELATION_PREC, "e0g_rel_ab", (occ_a, occ_b), 2)
    kernel_addr = registry.register_generated(
        "event.kernel", "e0g_kernel", (skin_a, skin_b), 2)
    binding_mismatch = EventSupportBinding(
        kernel_address=kernel_addr,
        occurrence_a_address=occ_a, occurrence_b_address=occ_c,  # 错配：c∉rel父
        relation_address=rel_ab,
        collector_address=StructuralAddress("neuron.collector", "e0g_col", 0),
        bundle_address=StructuralAddress("bundle.relation", "e0g_bun", 0),
        physical_support_addresses=(skin_a, skin_b),
        relation_kind="a_prec_b_fast", relation_window=(0, 100))
    cand = create_event_candidate(binding_mismatch, t_enter=100,
                                  local_effect_measure=0.1, registry=registry)
    assert cand.qualification_status == STATUS_REJECTED_LINEAGE_MISMATCH, (
        "T-E0-4: 谱系错配必须被拒绝——E-3 登记不授资格")

    # ℒ GAP 属实：tss 层适配器元件不在 organism census（真实链路实测）
    m = _recorded()
    assert m["tss_in_census"] is False, (
        "T-E0-4: tss 适配器元件出现在 organism census——ℒ GAP 判定需修订")
    print("[PASS] T-E0-4 越界守卫：契约纯常量 / E-3 拒绝生效 / ℒ GAP 属实")


def main():
    test_e0_1_contract_self_consistency()
    test_e0_2_component_instantiability()
    test_e0_3_replay_operator_floor()
    test_e0_4_no_overreach_guards()
    print()
    print("=" * 60)
    print("T-E0-1~4 ALL PASS — E0 类型审计（E-1~E-5）交付")
    print("=" * 60)


if __name__ == "__main__":
    main()
