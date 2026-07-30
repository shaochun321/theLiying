"""T-OCC-TAP-1：P2-B1X1b 只读occurrence观察适配器验证（2026-07-30）。

方案依据：`cell-cell/交叉比对/document - 2026-07-30T113327.179.md`
（P2-B1X1b：只读 occurrence tap）。

验证方案乙（外挂只读`OccurrenceClosure`，不用`wrap_base_generator()`
再次驱动通路）满足评判裁定的三项要求：
  1. `phys_support`使用对应L1.activation>0门控（不是collector自身活动）；
  2. 与`BaseGenerator`产生的occurrence等价（同一真实驱动下，两条独立
     closure状态机——一条内嵌在BaseGenerator里，一条是外挂tap——观测
     同一批collector/L1对象，应产生完全一致的occurrence序列）；
  3. tap本身不改变被观测神经元的任何状态（观察器不是隐藏的第二次驱动）。

驱动方式：只用`BaseGenerator.tick_from_skin()`驱动一次（唯一驱动权），
`CollectorOccurrenceTap`只读观测同一批Neuron对象——不重复调用
`wrap_base_generator`产生第二个驱动源，避免双重驱动。
"""
import sys

sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.structural_address import AddressRegistry
from nexus_v1.components.skin_three_point import (
    TEST_KAPPA_THREE_POINT, TEST_R_LEAK_AMBIENT_THREE_POINT, build_three_point_skin,
)
from nexus_v1.generators import (
    wrap_base_generator, wrap_collector_occurrence_tap, REFERENCE_TRANSDUCTION_CONFIG,
)
from nexus_v1.relations import FROZEN_THERMAL_SITES

DT = 0.001
CONFIG = REFERENCE_TRANSDUCTION_CONFIG
SITE_INDEX = FROZEN_THERMAL_SITES["t1_pair"]["a"]  # 28


def _fresh_skin():
    return build_three_point_skin(
        kappa=TEST_KAPPA_THREE_POINT, r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)


def test_occ_tap_1_equivalent_to_base_generator():
    """T-OCC-TAP-1：同一真实驱动下，BaseGenerator内嵌closure与独立tap
    观测同一批collector/L1对象，occurrence序列应完全等价（epoch数量/
    t_up/t_down/t_rearm 逐一相同），且tap不改变原始神经状态。

    驱动权只属于`BaseGenerator.tick_from_skin()`——它是本测试唯一调用
    `feed_from_skin()`/`_propagate()`的入口。`tap`只在每步驱动完成后
    读取同一批已被驱动过的Neuron对象的当前状态，不重复驱动。
    """
    circuit = VariantCircuit()
    registry = AddressRegistry()

    # 唯一的驱动权持有者
    handle = wrap_base_generator(circuit, SITE_INDEX, registry, polarity="warm")

    # 独立的只读tap，观测同一个collector（handle.collector）和同一个L1
    # （handle.l1）——不是新建对象，是引用同一批既有Neuron。
    tap = wrap_collector_occurrence_tap(
        collector=handle.collector, l1=handle.l1, registry=registry,
        site_index=SITE_INDEX, polarity="warm")

    graph = _fresh_skin()
    t = 0
    base_gen_events = []
    tap_events = []

    # 驱动900步（有真实dT输入）+ 3500步（撤去输入，观察是否有伪occurrence/
    # 自主复发）——与test_natural_unit.py的_run_to_one_occurrence同一驱动预算。
    for _ in range(900):
        graph.step(dt=1.0, external_injections={0: 1.0})
        q = graph.cells[0].temperature
        ev_base = handle.tick_from_skin(q, CONFIG, DT, t)  # 唯一驱动
        ev_tap = tap.observe(t)  # 只读观测，同一步的collector/L1状态
        if ev_base is not None:
            base_gen_events.append(ev_base)
        if ev_tap is not None:
            tap_events.append(ev_tap)
        t += 1

    for _ in range(3500):
        graph.step(dt=1.0, external_injections={})
        q = graph.cells[0].temperature
        ev_base = handle.tick_from_skin(q, CONFIG, DT, t)
        ev_tap = tap.observe(t)
        if ev_base is not None:
            base_gen_events.append(ev_base)
        if ev_tap is not None:
            tap_events.append(ev_tap)
        t += 1

    print(f"T-OCC-TAP-1: BaseGenerator产生 {len(base_gen_events)} 次occurrence，"
          f"tap产生 {len(tap_events)} 次occurrence")

    # 核心断言1：occurrence数量相同
    assert len(base_gen_events) == len(tap_events), (
        f"BaseGenerator与tap观测到的occurrence数量应相同，"
        f"实际 base={len(base_gen_events)}, tap={len(tap_events)}")
    assert len(base_gen_events) > 0, "本驱动预算内应至少产生一次occurrence（否则测试无效）"

    # 核心断言2：逐一比较t_up/t_down/t_rearm完全一致
    for i, (ev_b, ev_t) in enumerate(zip(base_gen_events, tap_events)):
        assert ev_b.t_up == ev_t.t_up, f"第{i}次occurrence的t_up不一致: base={ev_b.t_up}, tap={ev_t.t_up}"
        assert ev_b.t_down == ev_t.t_down, f"第{i}次occurrence的t_down不一致"
        assert ev_b.t_rearm == ev_t.t_rearm, f"第{i}次occurrence的t_rearm不一致"
        assert ev_b.epoch_id == ev_t.epoch_id, f"第{i}次occurrence的epoch_id不一致"
        print(f"    occurrence[{i}]: t_up={ev_b.t_up}, t_down={ev_b.t_down}, "
              f"t_rearm={ev_b.t_rearm}, epoch_id={ev_b.epoch_id} — base/tap一致")

    print("✓ T-OCC-TAP-1 PASS: tap产生的occurrence序列与BaseGenerator完全等价")


def test_occ_tap_2_does_not_mutate_observed_neurons():
    """T-OCC-TAP-2（补充）：证明tap是纯观察器——同一份驱动，有tap观测
    和无tap观测两种情形下，collector/L1本身的膜电位/pre_trace轨迹完全
    一致（tap不是隐藏的第二次驱动）。"""
    # 情形A：只驱动，不挂tap
    circuit_a = VariantCircuit()
    registry_a = AddressRegistry()
    handle_a = wrap_base_generator(circuit_a, SITE_INDEX, registry_a, polarity="warm")
    graph_a = _fresh_skin()

    # 情形B：驱动+挂tap观测
    circuit_b = VariantCircuit()
    registry_b = AddressRegistry()
    handle_b = wrap_base_generator(circuit_b, SITE_INDEX, registry_b, polarity="warm")
    tap_b = wrap_collector_occurrence_tap(
        collector=handle_b.collector, l1=handle_b.l1, registry=registry_b,
        site_index=SITE_INDEX, polarity="warm")
    graph_b = _fresh_skin()

    pre_trace_a, pre_trace_b = [], []
    activation_a, activation_b = [], []

    for t in range(1500):
        graph_a.step(dt=1.0, external_injections={0: 1.0} if t < 900 else {})
        q_a = graph_a.cells[0].temperature
        handle_a.tick_from_skin(q_a, CONFIG, DT, t)
        pre_trace_a.append(handle_a.collector.pre_trace)
        activation_a.append(handle_a.l1.activation)

        graph_b.step(dt=1.0, external_injections={0: 1.0} if t < 900 else {})
        q_b = graph_b.cells[0].temperature
        handle_b.tick_from_skin(q_b, CONFIG, DT, t)
        tap_b.observe(t)  # 挂tap观测，纯读取，不应改变handle_b的状态
        pre_trace_b.append(handle_b.collector.pre_trace)
        activation_b.append(handle_b.l1.activation)

    assert pre_trace_a == pre_trace_b, (
        "挂tap观测后collector.pre_trace轨迹应与不挂tap完全一致（tap不改变被观测状态）")
    assert activation_a == activation_b, (
        "挂tap观测后L1.activation轨迹应与不挂tap完全一致")

    print(f"✓ T-OCC-TAP-2 PASS: {len(pre_trace_a)}步逐一比较，"
          f"tap不改变被观测神经元的任何状态")


def run():
    test_occ_tap_1_equivalent_to_base_generator()
    test_occ_tap_2_does_not_mutate_observed_neurons()
    print()
    print("T-OCC-TAP-1~2 ALL PASS")


if __name__ == "__main__":
    run()
