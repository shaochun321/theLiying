"""nexus_v1.tests.test_thermal_source_coupling — 世界模型重构 W2A 单元测试。

方案依据：cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md
第十六节《批判八评判：总纲清理 + W2A 启动》16.3/16.4。

W2A 范围：`nexus_v1.components.thermal_source_coupling`（`ThermalFieldLocator`/
`DynamicHeatSource`/`couple()`/`guarded_step()`）是世界定位 + 动态热源守恒
注入，不接皮肤（W2B 留待另行确认）。本文件只做单元测试级验证：

  T-TSC-1  Locator 权重非负且和为 1（多组随机世界坐标）
  T-TSC-2  总注入量等于热源本步释放功率
  T-TSC-3  热源剩余能量正确减少
  T-TSC-4  热源耗尽后不再注入
  T-TSC-5  移动热源位置后，注入总量仍精确等于释放功率
  T-TSC-6  guarded_step() 对不稳定配置在执行前拒绝，且 graph 状态不被修改
  T-TSC-7  couple_and_step() 原子性修复（第十八节 18.3，批判九发现的真实缺口）：
           不稳定配置下抛出前，source.energy_remaining 与 graph 状态均未被修改
           （旧的 couple()+guarded_step() 两次调用模式会先扣热源能量再失败，
           造成能量跨组件丢失——couple_and_step() 通过调整调用顺序修复）
"""

import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.components.dynamic_thermal_field import build_fibonacci_shell_graph
from nexus_v1.components.thermal_source_coupling import (
    ThermalFieldLocator, DynamicHeatSource, couple, guarded_step, couple_and_step,
)

_TEST_CAPACITANCE = 1.0
_TEST_KAPPA_0 = 0.05
_TEST_R_LEAK_AMBIENT = 200.0


def _build_test_graph(n_nodes=20, k_neighbors=4):
    return build_fibonacci_shell_graph(
        n_nodes=n_nodes, radius=2.0, k_neighbors=k_neighbors,
        capacitance=_TEST_CAPACITANCE, kappa=_TEST_KAPPA_0,
        r_leak_ambient=_TEST_R_LEAK_AMBIENT,
    )


def test_locator_weights_nonneg_sum_to_one():
    """T-TSC-1：多组随机世界坐标下，locate() 权重非负且和为 1。"""
    graph = _build_test_graph()
    locator = ThermalFieldLocator(k=4)
    rng = random.Random(42)

    for _ in range(20):
        x = (rng.uniform(-3, 3), rng.uniform(-3, 3), rng.uniform(-3, 3))
        weights = locator.locate(x, graph)
        assert len(weights) > 0, "T-TSC-1 FAIL: 权重字典为空"
        for nid, w in weights.items():
            assert w >= 0.0, f"T-TSC-1 FAIL: 权重为负 node{nid}={w}"
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-9, f"T-TSC-1 FAIL: 权重和不为1，实际={total}"

    # 恰好落在节点上的边界情况：单节点权重1。
    coincident_pos = graph.cells[0].position
    weights_exact = locator.locate(coincident_pos, graph)
    assert weights_exact == {0: 1.0}, (
        f"T-TSC-1 FAIL: 精确重合应返回单节点权重1，实际={weights_exact}"
    )
    print("  T-TSC-1 PASS: 20组随机坐标权重均非负且和为1；精确重合边界正确")


def test_total_injection_equals_released_power():
    """T-TSC-2：Σcouple(...).values() == source.release(dt)（浮点误差内）。"""
    graph = _build_test_graph()
    locator = ThermalFieldLocator(k=4)
    source = DynamicHeatSource(
        position=(0.3, 0.1, 1.9), energy_remaining=1000.0, power=3.5,
    )
    injections = couple(source, locator, graph, dt=1.0)
    total_injected = sum(injections.values())
    assert abs(total_injected - 3.5) < 1e-9, (
        f"T-TSC-2 FAIL: 总注入量 {total_injected} != 释放功率 3.5"
    )
    print(f"  T-TSC-2 PASS: 总注入量={total_injected:.6f} == 释放功率=3.5")


def test_source_energy_decreases_correctly():
    """T-TSC-3：热源剩余能量正确减少（差值 = 释放能量 = power*dt）。"""
    source = DynamicHeatSource(position=(0, 0, 0), energy_remaining=50.0, power=4.0)
    e_before = source.energy_remaining
    released = source.release(dt=2.0)
    e_after = source.energy_remaining
    assert abs((e_before - e_after) - released * 2.0) < 1e-9, (
        f"T-TSC-3 FAIL: 能量差 {e_before - e_after} != released*dt={released * 2.0}"
    )
    assert abs(released - 4.0) < 1e-9, f"T-TSC-3 FAIL: 未耗尽时应全额释放，实际={released}"
    print(f"  T-TSC-3 PASS: energy {e_before}->{e_after}, released={released}")


def test_source_stops_injecting_after_exhausted():
    """T-TSC-4：热源耗尽后不再注入，release() 返回 0，energy_remaining 不再变化。"""
    source = DynamicHeatSource(position=(0, 0, 0), energy_remaining=5.0, power=10.0)
    # 第一次调用：请求 10*1.0=10 > 剩余5，应该只释放5，耗尽。
    first = source.release(dt=1.0)
    assert abs(first - 5.0) < 1e-9, f"T-TSC-4 FAIL: 耗尽前应释放剩余全部5.0，实际={first}"
    assert abs(source.energy_remaining) < 1e-9, "T-TSC-4 FAIL: 耗尽后 energy_remaining 应为0"

    second = source.release(dt=1.0)
    assert second == 0.0, f"T-TSC-4 FAIL: 耗尽后应返回0，实际={second}"
    assert source.energy_remaining == 0.0, "T-TSC-4 FAIL: 耗尽后 energy_remaining 不应再变化"
    print(f"  T-TSC-4 PASS: 耗尽序列 first={first} second={second}, energy_remaining=0")


def test_moved_source_injection_still_conserved():
    """T-TSC-5：移动热源位置后，注入总量仍精确等于释放功率。"""
    graph = _build_test_graph()
    locator = ThermalFieldLocator(k=4)
    positions = [(0.0, 0.0, 2.0), (1.5, -0.5, 1.2), (-2.0, 1.0, 0.3)]

    for pos in positions:
        source = DynamicHeatSource(position=pos, energy_remaining=100.0, power=2.0)
        injections = couple(source, locator, graph, dt=1.0)
        total = sum(injections.values())
        assert abs(total - 2.0) < 1e-9, (
            f"T-TSC-5 FAIL: 位置{pos}下注入总量={total} != 释放功率=2.0"
        )
    print(f"  T-TSC-5 PASS: {len(positions)}个不同热源位置下注入总量均精确守恒")


def test_guarded_step_rejects_unstable_config():
    """T-TSC-6：guarded_step() 对不稳定配置在 step() 前拒绝，graph 状态不被修改。"""
    # 复用 T-DTF-7 同款构造：kappa 远大于 capacitance，dt=1.0 下扩散数远超1。
    graph = build_fibonacci_shell_graph(
        n_nodes=10, radius=2.0, k_neighbors=4,
        capacitance=1.0, kappa=1000.0, r_leak_ambient=None,
    )
    charges_before = {nid: c.capacitor.charge for nid, c in graph.cells.items()}

    raised = False
    try:
        guarded_step(graph, dt=1.0, external_injections={0: 5.0})
    except ValueError as e:
        raised = True
        assert "Unstable" in str(e), f"T-TSC-6 FAIL: 错误信息未包含诊断内容: {e}"

    assert raised, "T-TSC-6 FAIL: 不稳定配置应抛出 ValueError，但没有抛出"

    charges_after = {nid: c.capacitor.charge for nid, c in graph.cells.items()}
    assert charges_before == charges_after, (
        "T-TSC-6 FAIL: graph 状态在 guarded_step() 拒绝后被修改，fail-fast 未真正发生在 step() 之前"
    )
    print("  T-TSC-6 PASS: 不稳定配置被拒绝（ValueError），graph 状态未被修改")

    # 对照：稳定配置下 guarded_step() 应正常执行，不抛异常。
    stable_graph = _build_test_graph()
    guarded_step(stable_graph, dt=1.0, external_injections={0: 1.0})
    print("  T-TSC-6 PASS: 稳定配置下 guarded_step() 正常执行")


def test_couple_and_step_atomic_on_rejection():
    """T-TSC-7：couple_and_step() 原子性修复（第十八节18.3，批判九发现的真实缺口）。

    不稳定配置下拒绝时，source.energy_remaining 与 graph 状态均未被修改——
    验证的正是"旧模式 couple()+guarded_step() 两次独立调用会先扣热源能量
    再失败，能量在跨组件提交窗口中丢失"这个真实 bug 已被修复。
    """
    graph = build_fibonacci_shell_graph(
        n_nodes=10, radius=2.0, k_neighbors=4,
        capacitance=1.0, kappa=1000.0, r_leak_ambient=None,
    )
    locator = ThermalFieldLocator(k=4)
    source = DynamicHeatSource(position=graph.cells[0].position, energy_remaining=100.0, power=2.0)
    charges_before = {nid: c.capacitor.charge for nid, c in graph.cells.items()}
    energy_before = source.energy_remaining

    raised = False
    try:
        couple_and_step(source, locator, graph, dt=1.0)
    except ValueError as e:
        raised = True
        assert "Unstable" in str(e), f"T-TSC-7 FAIL: 错误信息未包含诊断内容: {e}"

    assert raised, "T-TSC-7 FAIL: 不稳定配置应抛出 ValueError"
    assert source.energy_remaining == energy_before, (
        f"T-TSC-7 FAIL: 不稳定配置拒绝后 source.energy_remaining 被修改"
        f"（{energy_before} -> {source.energy_remaining}），能量跨组件丢失的原bug未修复"
    )
    charges_after = {nid: c.capacitor.charge for nid, c in graph.cells.items()}
    assert charges_before == charges_after, (
        "T-TSC-7 FAIL: 不稳定配置拒绝后 graph 状态被修改"
    )
    print(f"  T-TSC-7 PASS: 不稳定配置拒绝后 source.energy_remaining={source.energy_remaining} "
          f"未变（原bug已修复），graph 状态也未被修改")

    # 对照：稳定配置下 couple_and_step() 应正常执行且能量确实被扣（不是永远不扣）。
    stable_graph = _build_test_graph()
    stable_source = DynamicHeatSource(
        position=stable_graph.cells[0].position, energy_remaining=100.0, power=2.0)
    couple_and_step(stable_source, locator, stable_graph, dt=1.0)
    assert stable_source.energy_remaining == 98.0, (
        f"T-TSC-7 FAIL: 稳定配置下应正常扣账，实际energy_remaining={stable_source.energy_remaining}"
    )
    print(f"  T-TSC-7 PASS: 稳定配置下 couple_and_step() 正常执行，"
          f"energy_remaining={stable_source.energy_remaining}")


# ─────────────────────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────────────────────
TESTS = [
    ("T-TSC-1 Locator权重非负且和为1", test_locator_weights_nonneg_sum_to_one),
    ("T-TSC-2 总注入量等于释放功率", test_total_injection_equals_released_power),
    ("T-TSC-3 热源剩余能量正确减少", test_source_energy_decreases_correctly),
    ("T-TSC-4 热源耗尽后不再注入", test_source_stops_injecting_after_exhausted),
    ("T-TSC-5 移动热源注入仍守恒", test_moved_source_injection_still_conserved),
    ("T-TSC-6 guarded_step拒绝不稳定配置", test_guarded_step_rejects_unstable_config),
    ("T-TSC-7 couple_and_step原子性修复", test_couple_and_step_atomic_on_rejection),
]

if __name__ == "__main__":
    passed = 0
    failed = 0
    for name, fn in TESTS:
        print(f"\n[{name}]")
        try:
            fn()
            passed += 1
            print("  -> PASS")
        except AssertionError as e:
            failed += 1
            print(f"  -> FAIL: {e}")
        except Exception as e:
            failed += 1
            import traceback
            print(f"  -> ERROR: {e}")
            traceback.print_exc()

    print(f"\n{'='*55}")
    print(f"  {passed} passed, {failed} failed")
    print(f"{'='*55}")
    exit(0 if failed == 0 else 1)
