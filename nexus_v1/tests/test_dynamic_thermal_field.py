"""nexus_v1.tests.test_dynamic_thermal_field — 世界模型重构 W1 单元测试。

方案依据：cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md
第十四节《世界模型重构立项》W1（局部热状态网络，独立新模块，不接入生产电路）。

W1 范围：`nexus_v1.components.dynamic_thermal_field` 是完全独立的旁路模块，
不连接 SkinPatch/Body/VariantCircuit。本文件只做单元测试级验证：

  T-DTF-1  数值稳定性：长程运行（多步）不发散、无 NaN
  T-DTF-2  能量守恒：ThermalFieldGraph.conservation_residual() ≈ 0
           （内部扩散转移守恒 + 外部注入/环境耗散精确记账）
  T-DTF-3  热源局部注入后正确形成空间梯度（被注入节点温度 > 远端节点）
  T-DTF-4  ThermalLink 通量方向物理正确（净流动方向从热到冷，Fourier 定律符号）
  T-DTF-5  纯扩散（无注入无耗散）应使全场趋向均匀（熵增/梯度耗散方向正确）
  T-DTF-6  数值稳定守卫（W1.5）：稳定参数下 is_stable()=True 且长程运行确认不发散
  T-DTF-7  数值稳定守卫（W1.5）：明显超过 η=1 的参数下 is_stable()=False 能被正确
           识别（只验证诊断准确，不断言系统必须崩溃——诊断职责与行为兜底分离）

全量回归 21/21 的确认作为独立步骤单独运行（`python -m nexus_v1.tests.test_regression`），
不嵌入本文件——嵌套子进程运行完整回归套件会引入不必要的超时/缓冲复杂度，
且与本文件其余测试的粒度（单元级）不一致。

测试尺度参数说明：`dynamic_thermal_field.py` 的 DEFAULT_KAPPA_0/
DEFAULT_R_LEAK_AMBIENT 是从真实海水热扩散率 + 项目 dt=0.001s 换算得到的
一阶物理锚定值（EXP: 待 W2+ 接入真实 dt/网格后重新标定，同 Ω 层教训）。
在真实锚定尺度下，扩散时间常数 ~3.6×10^5 步，不适合单元测试在合理步数内
观测到梯度形成——因此本文件对 T-DTF-3/4/5 使用显式的**测试尺度覆盖参数**
（kappa/capacitance 提高到可在数百步内观测扩散的量级），与生产候选的
DEFAULT_* 常量分开验证：T-DTF-1/2 用 DEFAULT_* 验证稳定性和守恒性（不要求
观测到扩散，因为在该尺度下扩散确实极慢，这本身就是物理真实的），
T-DTF-3/4/5 用测试尺度覆盖参数验证扩散机制本身的方向性/正确性。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.components.dynamic_thermal_field import (
    ThermalCell, ThermalLink, ThermalFieldGraph, build_fibonacci_shell_graph,
    DEFAULT_CAPACITANCE, DEFAULT_KAPPA_0, DEFAULT_R_LEAK_AMBIENT,
    diffusion_number, is_stable,
)
from nexus_v1.components.semiconductor import Capacitor


# ── 测试尺度覆盖参数（EXP，仅用于本文件的单元测试，不进入生产 DEFAULT_*）──
_TEST_CAPACITANCE = 1.0
_TEST_KAPPA_0 = 0.05        # 使两节点 RC 时间常数 tau=1/kappa=20 步，数百步内可观测
_TEST_R_LEAK_AMBIENT = 200.0  # 比扩散慢 10x，保证梯度先形成再被环境抹平


def test_numerical_stability_long_run():
    """T-DTF-1：DEFAULT_* 生产候选参数下，长程运行数值稳定、无 NaN/无发散。"""
    graph = build_fibonacci_shell_graph(n_nodes=50, radius=2.0, k_neighbors=4)
    for step in range(2000):
        injections = {0: 1.0} if step < 500 else {}
        graph.step(dt=1.0, external_injections=injections)

    for cell in graph.cells.values():
        t = cell.temperature
        assert t == t, "T-DTF-1 FAIL: 温度出现 NaN"  # NaN != NaN
        assert abs(t) < 1e6, f"T-DTF-1 FAIL: 温度发散 T={t}"
    print(f"  T-DTF-1 PASS: 50 节点 2000 步后无 NaN/无发散，"
          f"node0.T={graph.cells[0].temperature:.6g}")


def test_energy_conservation_residual():
    """T-DTF-2：conservation_residual() ≈ 0（内部转移+外部注入+环境耗散精确记账）。"""
    graph = build_fibonacci_shell_graph(
        n_nodes=30, radius=2.0, k_neighbors=4,
        capacitance=_TEST_CAPACITANCE, kappa=_TEST_KAPPA_0,
        r_leak_ambient=_TEST_R_LEAK_AMBIENT,
    )
    for step in range(500):
        injections = {0: 2.0, 5: -0.5} if step % 3 == 0 else {}
        graph.step(dt=1.0, external_injections=injections)

    residual = graph.conservation_residual()
    assert residual < 1e-6, f"T-DTF-2 FAIL: 能量守恒残差过大 residual={residual}"
    print(f"  T-DTF-2 PASS: 500 步（含正负注入+环境耗散）后 "
          f"conservation_residual={residual:.3e}")

    # 逐节点 KCL 也应精确闭合（Capacitor 自带的记账）。
    max_kcl = max(c.kcl_imbalance for c in graph.cells.values())
    assert max_kcl < 1e-6, f"T-DTF-2 FAIL: 单节点 KCL 不闭合 max={max_kcl}"
    print(f"  T-DTF-2 PASS: 逐节点 KCL max_imbalance={max_kcl:.3e}")


def test_gradient_forms_under_injection():
    """T-DTF-3：持续向单节点注热后，该节点温度显著高于远端未注入节点。"""
    graph = build_fibonacci_shell_graph(
        n_nodes=40, radius=2.0, k_neighbors=4,
        capacitance=_TEST_CAPACITANCE, kappa=_TEST_KAPPA_0,
        r_leak_ambient=_TEST_R_LEAK_AMBIENT,
    )
    source_node = 0
    # 找一个与 source_node 空间距离最远的节点作为"远端"对照。
    import math
    def _dist(a, b):
        return math.sqrt(sum((a[k] - b[k]) ** 2 for k in range(3)))
    src_pos = graph.cells[source_node].position
    far_node = max(graph.cells.keys(),
                    key=lambda nid: _dist(src_pos, graph.cells[nid].position))

    for _ in range(300):
        graph.step(dt=1.0, external_injections={source_node: 1.0})

    t_source = graph.cells[source_node].temperature
    t_far = graph.cells[far_node].temperature
    assert t_source > t_far, (
        f"T-DTF-3 FAIL: 注入点温度 {t_source:.4g} 未显著高于远端 {t_far:.4g}"
    )
    assert t_source > 0.1, f"T-DTF-3 FAIL: 注入点温度过低，梯度未形成 T={t_source:.4g}"
    print(f"  T-DTF-3 PASS: 注入点(node{source_node}) T={t_source:.4g} > "
          f"远端(node{far_node}) T={t_far:.4g}")


def test_link_flux_direction_correct():
    """T-DTF-4：ThermalLink 通量方向遵循 Fourier 定律符号（热流从高温到低温）。"""
    hot = ThermalCell(node_id=0, position=(0, 0, 0),
                       capacitor=Capacitor(capacitance=1.0, charge=5.0))
    cold = ThermalCell(node_id=1, position=(1, 0, 0),
                        capacitor=Capacitor(capacitance=1.0, charge=0.0))
    link = ThermalLink(i=0, j=1, kappa=0.1)

    cells = {0: hot, 1: cold}
    j_01 = link.flux(cells)
    assert j_01 > 0, f"T-DTF-4 FAIL: 热→冷通量应为正，实际={j_01}"

    # 反向：交换哪个节点更热，通量符号应随之翻转（方向从结构涌现，非硬编码符号）。
    hot.capacitor.charge, cold.capacitor.charge = 0.0, 5.0
    j_01_after = link.flux(cells)
    assert j_01_after < 0, f"T-DTF-4 FAIL: 温度反转后通量应变负，实际={j_01_after}"
    print(f"  T-DTF-4 PASS: 通量方向随温度差符号正确翻转 "
          f"({j_01:.4g} -> {j_01_after:.4g})")


def test_pure_diffusion_equalizes_field():
    """T-DTF-5：无注入无耗散时，纯扩散应使全场温度趋向均匀（梯度单调衰减）。"""
    graph = build_fibonacci_shell_graph(
        n_nodes=20, radius=2.0, k_neighbors=6,
        capacitance=_TEST_CAPACITANCE, kappa=_TEST_KAPPA_0,
        r_leak_ambient=None,  # 关闭环境耗散，纯扩散
    )
    # 用 step() 的正规注入接口打一次能量脉冲，制造初始梯度——不能直接改
    # capacitor.charge（会绕过 KCL/graph 账本记账，导致 conservation_residual
    # 假阳性失败：账本压根不知道这份能量是"合法进入"的）。
    graph.step(dt=1.0, external_injections={0: 10.0})

    def _spread():
        temps = [c.temperature for c in graph.cells.values()]
        return max(temps) - min(temps)

    spread_initial = _spread()
    for _ in range(300):
        graph.step(dt=1.0, external_injections={})
    spread_final = _spread()

    assert spread_final < spread_initial, (
        f"T-DTF-5 FAIL: 纯扩散后梯度未衰减 "
        f"initial={spread_initial:.4g} final={spread_final:.4g}"
    )
    # 总能量应精确守恒（纯扩散、无源无汇）。
    residual = graph.conservation_residual()
    assert residual < 1e-6, f"T-DTF-5 FAIL: 纯扩散能量不守恒 residual={residual}"
    print(f"  T-DTF-5 PASS: 梯度从 {spread_initial:.4g} 衰减到 {spread_final:.4g}，"
          f"能量守恒 residual={residual:.3e}")


def test_stability_guard_accepts_stable_params():
    """T-DTF-6（W1.5）：稳定参数下 is_stable()=True 且长程运行确认不发散。"""
    graph = build_fibonacci_shell_graph(
        n_nodes=30, radius=2.0, k_neighbors=4,
        capacitance=_TEST_CAPACITANCE, kappa=_TEST_KAPPA_0,
        r_leak_ambient=_TEST_R_LEAK_AMBIENT,
    )
    assert is_stable(graph, dt=1.0), (
        f"T-DTF-6 FAIL: 测试尺度参数被诊断为不稳定，"
        f"max diffusion_number={max(diffusion_number(graph, dt=1.0).values()):.4g}"
    )
    for step in range(500):
        graph.step(dt=1.0, external_injections={0: 1.0} if step < 200 else {})
    for cell in graph.cells.values():
        t = cell.temperature
        assert t == t, "T-DTF-6 FAIL: 温度出现 NaN"
        assert abs(t) < 1e6, f"T-DTF-6 FAIL: 温度发散 T={t}"
    print(f"  T-DTF-6 PASS: is_stable=True，500步后无NaN/无发散，"
          f"max diffusion_number={max(diffusion_number(graph, dt=1.0).values()):.4g}")


def test_stability_guard_flags_unstable_params():
    """T-DTF-7（W1.5）：明显超过 η=1 的参数下 is_stable()=False 能被正确识别。

    只验证诊断准确，不断言系统"必须崩溃"——诊断职责与行为兜底分离（不做
    隐式子步进/不做参数拒绝，只如实报告）。
    """
    # kappa 远大于 capacitance，dt=1.0 下扩散数远超 1（一步转移的能量超过
    # 发送节点当前持有的能量，是显式欧拉扩散失稳的典型构造）。
    graph = build_fibonacci_shell_graph(
        n_nodes=10, radius=2.0, k_neighbors=4,
        capacitance=1.0, kappa=1000.0,
        r_leak_ambient=None,
    )
    dn = diffusion_number(graph, dt=1.0)
    assert max(dn.values()) > 1.0, (
        f"T-DTF-7 FAIL: 构造的参数未能产生扩散数>1，"
        f"max diffusion_number={max(dn.values()):.4g}（测试构造本身有误）"
    )
    assert not is_stable(graph, dt=1.0, eta=1.0), (
        "T-DTF-7 FAIL: 扩散数已超过 η=1，但 is_stable() 仍返回 True"
    )
    print(f"  T-DTF-7 PASS: 不稳定参数被正确识别，"
          f"max diffusion_number={max(dn.values()):.4g} > η=1.0")


# ─────────────────────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────────────────────
TESTS = [
    ("T-DTF-1 数值稳定性长程运行", test_numerical_stability_long_run),
    ("T-DTF-2 能量守恒残差", test_energy_conservation_residual),
    ("T-DTF-3 注入后梯度形成", test_gradient_forms_under_injection),
    ("T-DTF-4 通量方向正确", test_link_flux_direction_correct),
    ("T-DTF-5 纯扩散场趋于均匀", test_pure_diffusion_equalizes_field),
    ("T-DTF-6 稳定参数诊断正确", test_stability_guard_accepts_stable_params),
    ("T-DTF-7 不稳定参数诊断正确", test_stability_guard_flags_unstable_params),
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
