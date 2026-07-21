"""T-P2AG-1~10：P2-A 生成元核心验收（抽取 + 地址 + D_i^sim 输入合同 + 闭合状态机
+ Λ^phys 轨迹记录）。

方案依据：`cell-cell/交叉比对/评判_反馈自然单位概念修正_2026-07-20.md` §九
执行顺序步骤 1-3。四轮交叉比对（203329→203750→我方评判#1→211325→我方评判
#2→反馈）已收敛的核心裁定：

  - 十神经元结构已存在（`circuit/variant_adapter.py:_init_quantum_thermal_
    pathways`），本轮任务是抽取（`nexus_v1.generators.wrap_base_generator`），
    不是从零重建；
  - 发生检测需要正式的触发—退出—重整（trigger/exit/rearm）三边界闭合合同
    （`nexus_v1.generators.OccurrenceClosure`），不能只记首次上升沿；
  - 一次闭合 χ（`Occurrence`）≠ 自然单位 𝔫——本轮只交付可计数、带谱系的
    发生记录，不冻结任何无量纲测度字段。

测试分两层：
  - T-P2AG-1/2/3/4/7/8/9/10：对真实 `VariantCircuit` 抽取的 `BaseGenerator`
    做集成验证（延续 `test_basegen_thermal_t0.py` 的 `_propagate_xi_point`
    传播方法论，现改为调用生产代码 `BaseGenerator.feed()`）；
  - T-P2AG-5/6：对 `OccurrenceClosure` 状态机本身做精确受控的单元测试
    （直接喂合成信号序列，不依赖神经元动力学的具体数值时间尺度）。

T-P2AG-9/10 验证 `generators/trajectory.py` 的 `GeneratorTrajectory`——补齐
工作报告"未完成项"里的 Λ^phys 窗口聚合 + 10 ensemble 逐步激活轨缺口（见
`cell-cell/交叉比对/评判_P2A核心确认与生长机制来源存疑_2026-07-21.md` §一）。
"""

from __future__ import annotations

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.structural_address import (
    AddressRegistry, DOMAIN_OCC_THERMAL, DOMAIN_SKIN_PATCH,
    GeneratedAddress, StructuralAddress,
)
from nexus_v1.generators import (
    BaseGenerator, OccurrenceClosure, wrap_base_generator, register_occ_thermal,
    GeneratorTrajectory,
)
from nexus_v1.relations import FROZEN_THERMAL_SITES, snapshot_weights, check_frozen_weights_against

DT = 0.001


def _dummy_address(uid_suffix: str = "test") -> GeneratedAddress:
    """构造一个独立于真实电路的 GeneratedAddress，供纯 OccurrenceClosure
    单元测试使用（T-P2AG-5/6 不需要真实生成元，只测状态机本身）。"""
    parent = StructuralAddress(domain=DOMAIN_SKIN_PATCH, uid=f"skin.patch:{uid_suffix}")
    return GeneratedAddress(
        domain=DOMAIN_OCC_THERMAL, uid=f"occ.thermal:{uid_suffix}",
        parent_addresses=(parent,), generation_depth=1,
    )


# ─────────────────────────────────────────────────────────────
# T-P2AG-1：抽取一致性——句柄引用与母本对象同一性，不新建
# ─────────────────────────────────────────────────────────────
def test_wrap_references_same_objects_as_mother_circuit():
    circuit = VariantCircuit()
    registry = AddressRegistry()
    site_index = FROZEN_THERMAL_SITES["t1_pair"]["a"]  # 28
    pid = f"thermpt{site_index}"
    label = f"{pid}_warm"

    handle = wrap_base_generator(circuit, site_index, registry, polarity="warm")

    assert len(handle.ensemble) == 10, "生成元核心应恰为 10 个 ensemble 神经元"
    assert handle.ensemble is circuit.thermal_quantum_ensembles[label], \
        "ensemble 必须是母本既有对象的引用，不是重建的副本"
    assert handle.collector is circuit.thermal_quantum_collectors[label]
    assert handle.l1 is circuit.thermal_quantum_l1_warm[pid]
    assert handle.hc is circuit.thermal_quantum_hc_warm[pid]

    idx = site_index * 2
    assert handle.bundle_l1_hc is circuit.bundles_thermal_quantum_l1_to_hc[idx]
    assert handle.bundle_in is circuit.bundles_thermal_quantum_in[idx]
    assert handle.bundle_col is circuit.bundles_thermal_quantum_collect[idx]


# ─────────────────────────────────────────────────────────────
# T-P2AG-2：多实例隔离——同电路三站点句柄互不相同；跨电路同站点句柄也互不相同
# ─────────────────────────────────────────────────────────────
def test_multi_instance_isolation_across_sites_and_circuits():
    circuit = VariantCircuit()
    registry = AddressRegistry()
    order = FROZEN_THERMAL_SITES["t2_chain"]["order"]  # [31, 28, 23]

    handles = [wrap_base_generator(circuit, idx, registry, polarity="warm") for idx in order]

    collectors = [h.collector for h in handles]
    assert len(set(id(c) for c in collectors)) == 3, "三站点 collector 必须是三个不同对象"
    ensembles_flat_ids = [id(n) for h in handles for n in h.ensemble]
    assert len(set(ensembles_flat_ids)) == 30, "三站点合计 30 个 ensemble 神经元应互不相同"
    uids = [h.address.uid for h in handles]
    assert len(set(uids)) == 3, "三站点地址 uid 必须互不相同"

    # 跨电路：同一站点索引在两个独立 VariantCircuit 实例上应得到不同对象
    circuit_b = VariantCircuit()
    registry_b = AddressRegistry()
    handle_a = wrap_base_generator(circuit, order[0], registry, polarity="warm")
    handle_b = wrap_base_generator(circuit_b, order[0], registry_b, polarity="warm")
    assert handle_a.collector is not handle_b.collector, \
        "同一站点索引在两个独立电路实例上必须是不同对象（无隐藏全局单例）"


# ─────────────────────────────────────────────────────────────
# T-P2AG-3：地址挂载契约——domain/uid/parent/depth + 幂等
# ─────────────────────────────────────────────────────────────
def test_address_contract_and_idempotency():
    circuit = VariantCircuit()
    registry = AddressRegistry()
    site_index = FROZEN_THERMAL_SITES["t1_pair"]["a"]  # 28
    handle = wrap_base_generator(circuit, site_index, registry, polarity="warm")

    addr = handle.address
    assert addr.domain == DOMAIN_OCC_THERMAL
    assert addr.uid == f"occ.thermal:thermpt{site_index}_warm"
    assert addr.generation_depth == 1
    assert len(addr.parent_addresses) == 1
    parent = addr.parent_addresses[0]
    assert parent.domain == DOMAIN_SKIN_PATCH
    assert parent.uid == f"skin.patch:thermpt{site_index}"

    # 幂等：对同一 (domain, local_key) 重复调用 register_generated 返回同一地址对象
    addr_again = register_occ_thermal(registry, f"thermpt{site_index}_warm", parent)
    assert addr_again.uid == addr.uid
    assert addr_again.version == addr.version

    # 不同站点得到不同 uid
    other_index = FROZEN_THERMAL_SITES["t1_pair"]["b"]  # 31
    handle_other = wrap_base_generator(circuit, other_index, registry, polarity="warm")
    assert handle_other.address.uid != addr.uid


# ─────────────────────────────────────────────────────────────
# T-P2AG-4：端到端单次发生——脉冲驱动→退出→恰好 emit 一个 Occurrence
# ─────────────────────────────────────────────────────────────
def test_end_to_end_single_occurrence_via_real_drive():
    circuit = VariantCircuit()
    registry = AddressRegistry()
    site_index = FROZEN_THERMAL_SITES["t1_pair"]["a"]  # 28
    handle = wrap_base_generator(circuit, site_index, registry, polarity="warm")

    t = 0
    emitted = []

    # 驱动阶段：持续 dT=0.05（同 test_basegen_thermal_t0.py 的 T-T0-3 已验证
    # 能产生非零峰值），直到闭合状态机报告已 ACTIVE 或用尽预算。
    drive_budget = 1000
    for _ in range(drive_budget):
        ev = handle.tick(0.05, DT, t)
        t += 1
        if ev is not None:
            emitted.append(ev)
        if handle.closure.is_active:
            break
    assert handle.closure.is_active, \
        f"驱动 {drive_budget} 步后闭合状态机应已进入 ACTIVE（跨越 theta_up）"
    assert emitted == [], "驱动阶段（尚未跌破 theta_down）不应 emit 任何 Occurrence"

    # 退出阶段：切换为零输入，等待 pre_trace 衰减跌破 theta_down 并完成重整。
    decay_budget = 5000
    for _ in range(decay_budget):
        ev = handle.tick(0.0, DT, t)
        t += 1
        if ev is not None:
            emitted.append(ev)
            break
    else:
        raise AssertionError(
            f"零输入驱动 {decay_budget} 步后仍未完成一次闭合——"
            f"当前 pre_trace={handle.sense():.6f}, theta_down={handle.closure.theta_down}")

    assert len(emitted) == 1, f"整个驱动-退出周期应恰好 emit 一次 Occurrence，实际 {len(emitted)}"
    occ = emitted[0]
    assert occ.t_up < occ.t_down <= occ.t_rearm
    assert occ.count == 1
    assert occ.address is handle.address
    assert handle.closure.occurrence_count == 1
    assert not handle.closure.is_active, "完成一次闭合后应重新回到 ARMED"


# ─────────────────────────────────────────────────────────────
# T-P2AG-5：长饱和不重复计数（OccurrenceClosure 单元测试）
# ─────────────────────────────────────────────────────────────
def test_sustained_saturation_does_not_double_count():
    closure = OccurrenceClosure(address=_dummy_address("t5"))

    # 持续高位（远超 theta_up）1000 步，从不跌破 theta_down——
    # ACTIVE 窗口应保持打开，不产生任何"多次发生"的伪造计数。
    for t in range(1000):
        ev = closure.update(1.0, t)
        assert ev is None, f"持续饱和期间不应 emit（第 {t} 步却 emit 了）"
    assert closure.is_active
    assert closure.occurrence_count == 0

    # 之后真正跌落，应恰好完成一次（而不是"因为持续了很久就该算多次"）。
    ev = closure.update(0.0, 1000)
    assert ev is not None
    assert ev.t_up == 0
    assert ev.t_down == 1000
    assert closure.occurrence_count == 1


# ─────────────────────────────────────────────────────────────
# T-P2AG-6：阈值抖动去抖（OccurrenceClosure 单元测试）
# ─────────────────────────────────────────────────────────────
def test_hysteresis_absorbs_jitter_without_spurious_occurrences():
    theta_up, theta_down = 0.01, 0.001
    closure = OccurrenceClosure(address=_dummy_address("t6"), theta_up=theta_up, theta_down=theta_down)

    t = 0
    ev = closure.update(theta_up, t); t += 1  # 触发进入 ACTIVE
    assert ev is None
    assert closure.is_active

    # 在 (theta_down, theta_up) 迟滞带内反复抖动 200 步——从未真正跌破
    # theta_down，不应产生任何 emit（即便信号在阈值附近来回穿越 theta_up）。
    jitter_values = [theta_up * 1.5, theta_down * 5, theta_up * 0.9, theta_down * 3] * 50
    for v in jitter_values:
        ev = closure.update(v, t)
        t += 1
        assert ev is None, f"迟滞带内抖动不应 emit（第 {t} 步却 emit 了，value={v}）"
    assert closure.occurrence_count == 0, "抖动期间不应产生任何伪造发生"

    # 真正跌破 theta_down 才完成一次。
    ev = closure.update(theta_down * 0.5, t)
    assert ev is not None
    assert closure.occurrence_count == 1


# ─────────────────────────────────────────────────────────────
# T-P2AG-7：静息——零输入驱动不产生虚假发放，不 emit
# ─────────────────────────────────────────────────────────────
def test_undriven_generator_stays_at_rest_and_never_emits():
    circuit = VariantCircuit()
    registry = AddressRegistry()
    site_index = FROZEN_THERMAL_SITES["t1_pair"]["a"]
    handle = wrap_base_generator(circuit, site_index, registry, polarity="warm")

    for t in range(200):
        ev = handle.tick(0.0, DT, t)
        assert ev is None
        assert abs(handle.sense()) <= 1e-6, \
            f"零输入下 pre_trace 应维持精确静息，实际={handle.sense()}"
    assert handle.closure.occurrence_count == 0
    assert not handle.closure.is_active


# ─────────────────────────────────────────────────────────────
# T-P2AG-8：frozen 权重不变——驱动前后 bundle_in/bundle_col 权重逐项不变
# ─────────────────────────────────────────────────────────────
def test_driving_generator_does_not_mutate_frozen_weights():
    circuit = VariantCircuit()
    registry = AddressRegistry()
    site_index = FROZEN_THERMAL_SITES["t1_pair"]["a"]
    handle = wrap_base_generator(circuit, site_index, registry, polarity="warm")

    snap_in = snapshot_weights(handle.bundle_in)
    snap_col = snapshot_weights(handle.bundle_col)

    for t in range(300):
        handle.tick(0.05, DT, t)

    err_in = check_frozen_weights_against(handle.bundle_in, snap_in)
    err_col = check_frozen_weights_against(handle.bundle_col, snap_col)
    assert err_in is None, err_in
    assert err_col is None, err_col


# ─────────────────────────────────────────────────────────────
# T-P2AG-9：轨迹记录完整性——record_trajectory=True 时逐步记录与真实值一致
# ─────────────────────────────────────────────────────────────
def test_trajectory_records_match_real_drive_values():
    circuit = VariantCircuit()
    registry = AddressRegistry()
    site_index = FROZEN_THERMAL_SITES["t1_pair"]["a"]
    handle = wrap_base_generator(
        circuit, site_index, registry, polarity="warm", record_trajectory=True)

    assert isinstance(handle.trajectory, GeneratorTrajectory)
    assert handle.trajectory.records == []

    n_steps = 50
    dT = 0.05
    for t in range(n_steps):
        handle.tick(dT, DT, t)

    assert len(handle.trajectory.records) == n_steps, \
        "轨迹记录条数应恰好等于驱动步数（一步一记，不多不少）"

    for i, rec in enumerate(handle.trajectory.records):
        assert rec.step_index == i
        assert rec.u_i == dT, "当前最小映射下 u_i 应与喂入的 dT_raw 完全一致"
        assert len(rec.ensemble_pre_trace) == 10, "应记录恰好 10 个 ensemble 的 pre_trace"
        assert all(v >= 0.0 for v in rec.ensemble_pre_trace), \
            "pre_trace 是 |activation| 的 EMA，理论上非负"
        assert isinstance(rec.collector_pre_trace, float)

    # 末尾记录的 collector_pre_trace 应与驱动结束后 handle.sense() 的实时值一致
    # （驱动循环里最后一次 tick 之后没有再产生新状态变化）。
    assert handle.trajectory.records[-1].collector_pre_trace == handle.sense()


# ─────────────────────────────────────────────────────────────
# T-P2AG-10：窗口切片对齐 Occurrence 边界——window(t_up,t_rearm) 不多不少
# ─────────────────────────────────────────────────────────────
def test_trajectory_window_aligns_with_occurrence_boundaries():
    circuit = VariantCircuit()
    registry = AddressRegistry()
    site_index = FROZEN_THERMAL_SITES["t1_pair"]["a"]
    handle = wrap_base_generator(
        circuit, site_index, registry, polarity="warm", record_trajectory=True)

    t = 0
    occurrence = None

    # 复刻 T-P2AG-4 的脉冲驱动场景：先驱动到 ACTIVE，再切零输入等待完整闭合。
    drive_budget = 1000
    for _ in range(drive_budget):
        ev = handle.tick(0.05, DT, t)
        t += 1
        if ev is not None:
            occurrence = ev
        if handle.closure.is_active:
            break
    assert handle.closure.is_active

    decay_budget = 5000
    for _ in range(decay_budget):
        ev = handle.tick(0.0, DT, t)
        t += 1
        if ev is not None:
            occurrence = ev
            break
    assert occurrence is not None, "应产生恰好一次完整发生供窗口切片测试"

    window = handle.trajectory.window(occurrence.t_up, occurrence.t_rearm)

    assert len(window) == occurrence.t_rearm - occurrence.t_up, \
        "窗口切片记录数应恰好等于 [t_up, t_rearm) 半开区间的步数"
    assert window[0].step_index == occurrence.t_up, "窗口首条记录应正好落在 t_up"
    assert window[-1].step_index == occurrence.t_rearm - 1, \
        "窗口末条记录应正好落在 t_rearm-1（半开区间不含 t_rearm 本身）"
    # 窗口外紧邻的两条记录不应被包含进来（边界不多不少的双向核实）。
    all_indices = {r.step_index for r in window}
    assert (occurrence.t_up - 1) not in all_indices
    assert occurrence.t_rearm not in all_indices
