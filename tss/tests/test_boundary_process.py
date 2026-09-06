"""tss.tests.test_boundary_process — R0-3：CollectorBoundaryPort 六项资格测试。

TYPE:INFRA

方案依据：TSS-R0_执行计划_2026-08-04.md（R0-3，评判修正版）。

六项测试（T-R0-1~6）：
  T-R0-1：spike_output 来自真实物理过程（逐步等于 collector.activation）
  T-R0-2：关闭 OccurrenceClosure/Tap/Finalizer 后端口仍输出真实脉冲
  T-R0-3：Occurrence 可由 spike_output 生成；反方向不成立（因果方向守卫）
  T-R0-4：G_28 / G_31 / G_21 共用同一个 CollectorBoundaryPort 类型（跨生成元同型）
  T-R0-5：重命名 generator_address 不改变 spike_output 轨迹（身份解耦）
  T-R0-6：STDP=0 / DA=0 时仍成立（exists_without_learning=True，非学习存在）
"""
import sys
sys.path.insert(0, '.')

from nexus_v1.components.structural_address import (
    AddressRegistry, GeneratedAddress, StructuralAddress,
    DOMAIN_SKIN_PATCH, DOMAIN_OCC_THERMAL,
)
from nexus_v1.components.world import HeatSource
from tss.generators.occurrence import OccurrenceClosure
from tss.generators.occurrence_tap import wrap_collector_occurrence_tap
from tss.relations.boundary_process import CollectorBoundaryPort
from tss.relations.temporal_r_prec import RPrecCircuitT1

DT = 0.001
N_STEPS = 5000
HEAT_RADIUS = 3.0
HEAT_TEMPERATURE = 300.0
HEAT_ENERGY = 100000.0

# 测试用三个站点（T-R0-4 跨生成元同型）
_TEST_SITES = [28, 31, 21]


def _make_circuit_with_heat(site: int):
    """构造 RPrecCircuitT1 并在 site 上放 HeatSource，返回 circuit。"""
    circuit = RPrecCircuitT1()
    patch = circuit._thermal_quantum_patches[site]
    pos = patch.world_position(circuit.world.body)
    circuit.world.heat_sources = [HeatSource(
        position=list(pos), energy=HEAT_ENERGY,
        temperature=HEAT_TEMPERATURE, radius=HEAT_RADIUS,
        _drift=[0.0, 0.0, 0.0],
    )]
    return circuit


def _make_address(registry: AddressRegistry, site: int) -> GeneratedAddress:
    """为站点构造一个 GeneratedAddress（同 wrap_collector_occurrence_tap 的模式）。"""
    pid = f"thermpt{site}"
    label = f"{pid}_warm"
    parent_addr = registry.register_physical(DOMAIN_SKIN_PATCH, pid)
    return registry.register_generated(DOMAIN_OCC_THERMAL, label, (parent_addr,), 1)


# ─────────────────────────────────────────────────────────────────────────────

def test_r0_1_spike_output_equals_activation():
    """T-R0-1：spike_output 逐步等于真实 collector.activation。

    禁止从 OccurrenceInstanceId / 站点标签 / 外部坐标生成边界过程。
    """
    circuit = _make_circuit_with_heat(28)
    registry = AddressRegistry()
    addr = _make_address(registry, 28)
    collector = circuit.thermal_quantum_collectors["thermpt28_warm"]

    port = CollectorBoundaryPort(generator_address=addr, carrier_ref=collector)

    mismatches = []
    for t in range(N_STEPS):
        circuit.step({}, DT)
        expected = collector.activation      # 真实物理量
        actual = port.spike_output           # 端口读取
        if abs(actual - expected) > 1e-12:
            mismatches.append((t, expected, actual))

    assert len(mismatches) == 0, (
        f"T-R0-1: spike_output 与 collector.activation 逐步不符，"
        f"前三处不符：{mismatches[:3]}")

    print(f"T-R0-1: 驱动 {N_STEPS} 步，spike_output 与 collector.activation 逐步完全一致")
    print("✓ T-R0-1 PASS: spike_output 来自真实物理过程，非软件构造")


def test_r0_2_no_closure_still_works():
    """T-R0-2：关闭 OccurrenceClosure/Tap/Finalizer 后端口仍输出真实脉冲。

    CollectorBoundaryPort 不依赖 Closure/Tap/Finalizer——
    这些审计组件的存在与否不影响 spike_output。
    """
    circuit = _make_circuit_with_heat(28)
    registry = AddressRegistry()
    addr = _make_address(registry, 28)
    collector = circuit.thermal_quantum_collectors["thermpt28_warm"]

    # 完全不构造 OccurrenceClosure / Tap / Finalizer
    port = CollectorBoundaryPort(generator_address=addr, carrier_ref=collector)
    # _closure 已从端口移除，Closure 由调用方单独持有

    spike_seen = False
    for t in range(N_STEPS):
        circuit.step({}, DT)
        if port.spike_output > 0.5:
            spike_seen = True
            break

    assert spike_seen, (
        "T-R0-2: 在不使用任何 OccurrenceClosure/Tap/Finalizer 的情况下，"
        "CollectorBoundaryPort 应仍能观测到真实 collector 脉冲")

    assert port.exists_without_learning is True

    print(f"T-R0-2: 无 Closure/Tap/Finalizer，端口在 t={t} 观测到 spike_output={port.spike_output}")
    print("✓ T-R0-2 PASS: 端口独立于审计组件存在，关闭后仍输出真实脉冲")


def test_r0_3_occurrence_from_port_not_reverse():
    """T-R0-3：Occurrence 可由 spike_output 生成；反方向不成立（因果守卫）。

    冻结因果方向：Occurrence = A[p_α]，不是 p_α = B[Occurrence]。
    测试：
      (a) 用 OccurrenceClosure 消费 spike_output（pre_trace），
          最终产生 Occurrence → 正向成立
      (b) CollectorBoundaryPort 不接受 Occurrence 作为构造参数
          → 反向在接口上被封死
    """
    circuit = _make_circuit_with_heat(28)
    registry = AddressRegistry()
    addr = _make_address(registry, 28)
    collector = circuit.thermal_quantum_collectors["thermpt28_warm"]
    l1 = circuit.thermal_quantum_l1_warm["thermpt28"]

    port = CollectorBoundaryPort(generator_address=addr, carrier_ref=collector)

    # 正向：独立构造 Tap（内部含 OccurrenceClosure）消费同一 collector
    tap = wrap_collector_occurrence_tap(
        collector, l1, registry, site_index=28, polarity="warm")

    for t in range(N_STEPS):
        circuit.step({}, DT)
        tap.observe(t)

    n_events = len(tap.closure.events)
    assert n_events > 0, "T-R0-3: 正向——Closure 应能从 collector 活动中产生 Occurrence"

    # 反向：CollectorBoundaryPort 的构造签名不接受 Occurrence 参数
    # （只接受 generator_address + carrier_ref，若尝试传 Occurrence 会是 TypeError）
    import inspect
    sig = inspect.signature(CollectorBoundaryPort.__init__)
    param_names = list(sig.parameters.keys())
    has_occurrence_param = any(
        "occurrence" in p.lower() or "t_up" in p or "t_down" in p
        for p in param_names
    )
    assert not has_occurrence_param, (
        f"T-R0-3: CollectorBoundaryPort 不应接受 Occurrence 相关参数，"
        f"实际参数列表={param_names}")

    print(f"T-R0-3: 正向 Occurrence={n_events} 次；反向参数封锁 params={param_names}")
    print("✓ T-R0-3 PASS: Occurrence=A[p_α]，反方向在接口层被封死")


def test_r0_4_same_type_across_generators():
    """T-R0-4：G_28 / G_31 / G_21 共用同一个 CollectorBoundaryPort 类型。

    不为每个站点单独建子类或专属端口。
    """
    circuit = _make_circuit_with_heat(28)
    registry = AddressRegistry()

    ports = {}
    for site in _TEST_SITES:
        addr = _make_address(registry, site)
        collector = circuit.thermal_quantum_collectors[f"thermpt{site}_warm"]
        port = CollectorBoundaryPort(generator_address=addr, carrier_ref=collector)
        ports[site] = port
        assert type(port) is CollectorBoundaryPort, (
            f"站点{site}的端口类型应是 CollectorBoundaryPort，实际是 {type(port)}")

    # 三个端口互相独立（不同 carrier_ref）
    assert ports[28].carrier_ref is not ports[31].carrier_ref
    assert ports[28].carrier_ref is not ports[21].carrier_ref
    assert ports[31].carrier_ref is not ports[21].carrier_ref

    print(f"T-R0-4: 站点 {_TEST_SITES} 全部使用 CollectorBoundaryPort，类型一致")
    print("✓ T-R0-4 PASS: 三个基础生成元共用同一端口类型，无站点专属子类")


def test_r0_5_rename_address_no_effect():
    """T-R0-5：重命名 generator_address 不改变 spike_output 轨迹（身份解耦）。

    重新构造一个不同 address 的端口，指向同一 carrier_ref，
    两者的 spike_output 序列必须完全相同。
    """
    circuit = _make_circuit_with_heat(28)
    registry_a = AddressRegistry()
    registry_b = AddressRegistry()

    addr_a = _make_address(registry_a, 28)
    # 用不同 registry 和不同 label 构造一个"改名"后的地址
    pa = registry_b.register_physical(DOMAIN_SKIN_PATCH, "renamed_patch")
    addr_b = registry_b.register_generated(DOMAIN_OCC_THERMAL, "renamed_label", (pa,), 1)

    collector = circuit.thermal_quantum_collectors["thermpt28_warm"]

    port_a = CollectorBoundaryPort(generator_address=addr_a, carrier_ref=collector)
    port_b = CollectorBoundaryPort(generator_address=addr_b, carrier_ref=collector)

    # 重命名后两个端口的 generator_address 不同
    assert port_a.generator_address != port_b.generator_address

    # 但 spike_output 逐步完全相同（共享同一 carrier_ref）
    mismatches = []
    for t in range(N_STEPS):
        circuit.step({}, DT)
        sa, sb = port_a.spike_output, port_b.spike_output
        if abs(sa - sb) > 1e-12:
            mismatches.append((t, sa, sb))

    assert len(mismatches) == 0, (
        f"T-R0-5: 重命名 address 后 spike_output 不应改变，"
        f"前三处不符：{mismatches[:3]}")

    print(f"T-R0-5: addr_a≠addr_b 但 spike_output 逐步完全一致（{N_STEPS}步 0 mismatches）")
    print("✓ T-R0-5 PASS: generator_address 是谱系标识，不决定物理输出")


def test_r0_6_exists_without_learning():
    """T-R0-6：STDP=0 / DA=0 时端口仍输出真实脉冲（非学习存在）。

    RPrecCircuitT1 本身就是 STDP/DA 关闭状态（frozen bundle）；
    额外断言 exists_without_learning 属性值及 DA 关闭后仍有 spike。
    """
    circuit = _make_circuit_with_heat(28)
    registry = AddressRegistry()
    addr = _make_address(registry, 28)
    collector = circuit.thermal_quantum_collectors["thermpt28_warm"]

    port = CollectorBoundaryPort(generator_address=addr, carrier_ref=collector)

    # 确认属性声明
    assert port.exists_without_learning is True

    # DA 关闭：circuit 里的 DA 神经元置零（Capacitor.voltage 是只读属性，用 discharge_to）
    for da_neuron in circuit.da_neurons.values():
        da_neuron._membrane.discharge_to(0.0)

    spike_seen = False
    for t in range(N_STEPS):
        circuit.step({}, DT)
        if port.spike_output > 0.5:
            spike_seen = True
            break

    assert spike_seen, (
        "T-R0-6: DA=0 的情况下端口仍应能观测到真实脉冲——"
        "collector 由 HeatSource 直接驱动，不依赖 DA")

    print(f"T-R0-6: DA=0 条件下端口在 t={t} 观测到 spike，exists_without_learning=True")
    print("✓ T-R0-6 PASS: 端口非学习存在，STDP/DA 关闭后仍有效")


def run():
    test_r0_1_spike_output_equals_activation()
    test_r0_2_no_closure_still_works()
    test_r0_3_occurrence_from_port_not_reverse()
    test_r0_4_same_type_across_generators()
    test_r0_5_rename_address_no_effect()
    test_r0_6_exists_without_learning()
    print()
    print("=" * 60)
    print("T-R0-1~6 ALL PASS")
    print("=" * 60)


if __name__ == "__main__":
    run()
