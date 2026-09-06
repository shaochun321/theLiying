"""tss.tests.test_entry_boundary — TSS-R1a：EntryBoundaryDetector六项资格测试。

TYPE:INFRA

方案依据：document - 2026-08-04T220649.641.md（评判裁定版本A，六项资格
要求：首次进入输出一次/重复spike不重复输出/退出重新武装后才能再次输出/
实时不读t_down/跨站点同结构同参数/地址不参与判断）。

资格范围（document - 2026-08-05T010306.536.md）：本文件验证的是**判定规则
正确性**，不是物理生成算子资格。通过后本检测器成为TSS-R1b物理实现的对照
标准（b^↑_physical ≡ b^↑_reference），不代表E^↑已有物理载体。

六个测试：
  T-R1A-1：持续发生首次进入时输出一次脉冲（ARMED→ACTIVE跳变）
  T-R1A-2：持续发生中的重复spike不重复输出
  T-R1A-3：真实退出（冷却gap_steps）并重新武装（rearm_min_steps）后才能再次输出
  T-R1A-4：实时运行——不依赖任何Occurrence/t_down，纯粹靠spike_output序列判断
  T-R1A-5：28/31/21/24共用同一个EntryBoundaryDetector类型与同一组参数
  T-R1A-6：地址重命名不改变判断结果（身份解耦）
"""
import sys
sys.path.insert(0, '.')

from nexus_v1.components.structural_address import (
    AddressRegistry, DOMAIN_SKIN_PATCH, DOMAIN_OCC_THERMAL,
)
from nexus_v1.components.world import HeatSource
from tss.relations.boundary_process import CollectorBoundaryPort
from tss.relations.entry_boundary import EntryBoundaryDetector, make_entry_detector
from tss.relations.temporal_r_prec import RPrecCircuitT1

DT = 0.001
N_STEPS = 8000
HEAT_RADIUS = 5.0
HEAT_TEMPERATURE = 300.0
GAP_STEPS = 500
REARM_MIN_STEPS = 500

_TEST_SITES = [28, 31, 21, 24]


def _make_circuit_with_heat(site: int = 28):
    circuit = RPrecCircuitT1()
    patch = circuit._thermal_quantum_patches[site]
    pos = patch.world_position(circuit.world.body)
    circuit.world.heat_sources = [HeatSource(
        position=list(pos), energy=100000.0, temperature=HEAT_TEMPERATURE,
        radius=HEAT_RADIUS, _drift=[0.0, 0.0, 0.0])]
    return circuit


def _make_address(registry: AddressRegistry, site: int):
    pid = f"thermpt{site}"
    label = f"{pid}_warm"
    parent_addr = registry.register_physical(DOMAIN_SKIN_PATCH, pid)
    return registry.register_generated(DOMAIN_OCC_THERMAL, label, (parent_addr,), 1)


def test_r1a_1_single_entry_pulse_on_first_spike():
    """T-R1A-1：持续发生首次进入时输出一次脉冲（ARMED→ACTIVE跳变）。"""
    circuit = _make_circuit_with_heat(28)
    registry = AddressRegistry()
    addr = _make_address(registry, 28)
    collector = circuit.thermal_quantum_collectors["thermpt28_warm"]
    port = CollectorBoundaryPort(generator_address=addr, carrier_ref=collector)
    detector = make_entry_detector(port, gap_steps=GAP_STEPS, rearm_min_steps=REARM_MIN_STEPS)

    first_entry_t = None
    for t in range(N_STEPS):
        circuit.step({}, DT)
        entered = detector.update(port.spike_output, t)
        if entered and first_entry_t is None:
            first_entry_t = t

    assert first_entry_t is not None, "T-R1A-1: 应至少产生一次首次进入事件"
    print(f"T-R1A-1: 首次进入 t={first_entry_t}, entry_count={detector.entry_count}")
    print("✓ T-R1A-1 PASS: 首次进入时输出一次脉冲")


def test_r1a_2_repeated_spikes_no_repeated_entry():
    """T-R1A-2：持续发生中的重复spike不重复输出。

    验证：在detector处于ACTIVE阶段期间（同一次持续发生窗口内），即使
    collector反复spike，update()不应再返回True。
    """
    circuit = _make_circuit_with_heat(28)
    registry = AddressRegistry()
    addr = _make_address(registry, 28)
    collector = circuit.thermal_quantum_collectors["thermpt28_warm"]
    port = CollectorBoundaryPort(generator_address=addr, carrier_ref=collector)
    detector = make_entry_detector(port, gap_steps=GAP_STEPS, rearm_min_steps=REARM_MIN_STEPS)

    entries_while_active = 0
    spikes_while_active = 0
    for t in range(N_STEPS):
        circuit.step({}, DT)
        was_active = detector.is_active
        entered = detector.update(port.spike_output, t)
        if was_active and port.spike_output > 0.5:
            spikes_while_active += 1
            if entered:
                entries_while_active += 1

    assert spikes_while_active > 0, (
        "T-R1A-2: 应观测到ACTIVE阶段内的重复spike（否则测试场景本身无意义）")
    assert entries_while_active == 0, (
        f"T-R1A-2: ACTIVE阶段内的重复spike不应产生新的进入事件，"
        f"实际有{entries_while_active}次误判")

    print(f"T-R1A-2: ACTIVE阶段内观测到{spikes_while_active}次重复spike，"
          f"其中{entries_while_active}次误判为新进入")
    print("✓ T-R1A-2 PASS: 重复spike不重复输出")


def test_r1a_3_reentry_requires_full_exit_and_rearm():
    """T-R1A-3：真实退出（冷却gap_steps）并重新武装（rearm_min_steps）
    后才能再次输出。

    构造一个模拟spike序列（脱离真实电路，直接控制输入），精确验证
    状态机的三段式闭环：ARMED→ACTIVE→(冷却)→REFRACTORY→(冷却)→ARMED。
    """
    from nexus_v1.components.structural_address import AddressRegistry as _AR
    registry = _AR()
    addr = _make_address(registry, 28)
    detector = EntryBoundaryDetector(
        generator_address=addr, gap_steps=10, rearm_min_steps=10)

    # t=0: 首次spike → 应进入ACTIVE，返回True
    assert detector.update(1.0, 0) is True
    assert detector.is_active is True

    # t=1~5: 持续spike（同一次发生），不应再返回True
    for t in range(1, 6):
        assert detector.update(1.0, t) is False

    # t=6~15: 静默10步（gap_steps=10）→ 触发ACTIVE→REFRACTORY，
    # 但REFRACTORY阶段本身也不应返回True
    for t in range(6, 16):
        assert detector.update(0.0, t) is False
    assert detector.is_active is True, "T-R1A-3: REFRACTORY仍算is_active（未完全武装）"

    # 此时应已进入REFRACTORY（t_exit=15，因为第10个静默步是t=15）
    # 继续静默直到rearm完成：需要 t - t_exit >= rearm_min_steps=10
    reentered = False
    for t in range(16, 30):
        result = detector.update(0.0, t)
        if result:
            reentered = True
            break
    assert not reentered, (
        "T-R1A-3: 静默期内（无新spike）不应产生进入事件，"
        "即使rearm_min_steps已满足——重新武装后仍需真实spike才能进入ACTIVE")
    assert detector.is_active is False, "T-R1A-3: 冷却完成后应回到ARMED（is_active=False）"

    # 现在已ARMED，喂一个新spike → 应该再次返回True（第二次进入）
    t_second_entry = 30
    assert detector.update(1.0, t_second_entry) is True
    assert detector.entry_count == 2

    print(f"T-R1A-3: 第一次进入t=0，冷却+重新武装后，"
          f"第二次进入t={t_second_entry}，entry_count={detector.entry_count}")
    print("✓ T-R1A-3 PASS: 真实退出并重新武装后才能再次输出")


def test_r1a_4_realtime_no_occurrence_dependency():
    """T-R1A-4：实时运行——不依赖任何Occurrence/t_down/完整闭合记录。

    验证：EntryBoundaryDetector的构造签名和update()签名都不接受
    Occurrence相关参数；只用spike_output和t_step两个实时量做判断。
    """
    import inspect

    sig_init = inspect.signature(EntryBoundaryDetector.__init__)
    sig_update = inspect.signature(EntryBoundaryDetector.update)

    init_params = list(sig_init.parameters.keys())
    update_params = list(sig_update.parameters.keys())

    forbidden_tokens = ("occurrence", "t_down", "t_up", "closure")
    for params, name in [(init_params, "__init__"), (update_params, "update")]:
        for p in params:
            assert not any(tok in p.lower() for tok in forbidden_tokens), (
                f"T-R1A-4: {name}参数'{p}'疑似依赖Occurrence/t_down等"
                f"事后信息，违反实时性要求")

    assert update_params == ["self", "spike_output", "t_step"], (
        f"T-R1A-4: update()签名应只有spike_output和t_step两个实时输入，"
        f"实际={update_params}")

    # 构造签名应只有三个真正的配置参数，内部状态字段（_phase等）
    # 不应作为构造参数暴露（否则调用方可跳过状态机直接注入状态）
    assert init_params == ["self", "generator_address", "gap_steps", "rearm_min_steps"], (
        f"T-R1A-4: __init__签名应只暴露三个配置参数，"
        f"内部状态字段不应可从外部构造注入，实际={init_params}")

    print(f"T-R1A-4: __init__参数={init_params}")
    print(f"         update参数={update_params}")
    print("✓ T-R1A-4 PASS: 不依赖Occurrence/t_down，纯实时判断")


def test_r1a_5_same_type_same_params_across_sites():
    """T-R1A-5：28/31/21/24共用同一个EntryBoundaryDetector类型与同一组参数。"""
    circuit = _make_circuit_with_heat(28)
    registry = AddressRegistry()

    detectors = {}
    for site in _TEST_SITES:
        addr = _make_address(registry, site)
        collector = circuit.thermal_quantum_collectors[f"thermpt{site}_warm"]
        port = CollectorBoundaryPort(generator_address=addr, carrier_ref=collector)
        detector = make_entry_detector(port, gap_steps=GAP_STEPS, rearm_min_steps=REARM_MIN_STEPS)
        detectors[site] = detector
        assert type(detector) is EntryBoundaryDetector
        assert detector.gap_steps == GAP_STEPS
        assert detector.rearm_min_steps == REARM_MIN_STEPS

    print(f"T-R1A-5: 站点{_TEST_SITES}全部使用EntryBoundaryDetector，"
          f"gap_steps={GAP_STEPS}, rearm_min_steps={REARM_MIN_STEPS}统一")
    print("✓ T-R1A-5 PASS: 跨站点同结构同参数，无专属子类或专属数值")


def test_r1a_6_address_rename_no_effect():
    """T-R1A-6：地址重命名不改变判断结果（身份解耦）。

    两个EntryBoundaryDetector用不同generator_address但喂入完全相同的
    spike_output序列，update()的返回值序列必须完全一致。
    """
    registry_a = AddressRegistry()
    registry_b = AddressRegistry()
    addr_a = _make_address(registry_a, 28)

    pa = registry_b.register_physical(DOMAIN_SKIN_PATCH, "renamed_patch")
    addr_b = registry_b.register_generated(DOMAIN_OCC_THERMAL, "renamed_label", (pa,), 1)

    detector_a = EntryBoundaryDetector(
        generator_address=addr_a, gap_steps=GAP_STEPS, rearm_min_steps=REARM_MIN_STEPS)
    detector_b = EntryBoundaryDetector(
        generator_address=addr_b, gap_steps=GAP_STEPS, rearm_min_steps=REARM_MIN_STEPS)

    assert detector_a.generator_address != detector_b.generator_address

    # 构造一段确定性的spike序列（含首次进入+重复spike+冷却+重新进入）
    spike_seq = [1.0] * 3 + [0.0] * (GAP_STEPS + 5) + [1.0] * 2 + [0.0] * (REARM_MIN_STEPS + 5) + [1.0]

    results_a = [detector_a.update(s, t) for t, s in enumerate(spike_seq)]
    results_b = [detector_b.update(s, t) for t, s in enumerate(spike_seq)]

    assert results_a == results_b, (
        f"T-R1A-6: 重命名address后判断结果不应改变，"
        f"a={results_a} vs b={results_b}")

    print(f"T-R1A-6: addr_a≠addr_b 但update()结果序列完全一致"
          f"（{len(spike_seq)}步，{sum(results_a)}次进入事件）")
    print("✓ T-R1A-6 PASS: generator_address是谱系标识，不参与判断")


def run():
    test_r1a_1_single_entry_pulse_on_first_spike()
    test_r1a_2_repeated_spikes_no_repeated_entry()
    test_r1a_3_reentry_requires_full_exit_and_rearm()
    test_r1a_4_realtime_no_occurrence_dependency()
    test_r1a_5_same_type_same_params_across_sites()
    test_r1a_6_address_rename_no_effect()
    print()
    print("=" * 60)
    print("T-R1A-1~6 ALL PASS")
    print("=" * 60)


if __name__ == "__main__":
    run()
