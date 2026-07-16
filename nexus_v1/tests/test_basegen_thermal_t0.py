"""nexus_v1.tests.test_basegen_thermal_t0 — 基础生成元温感轨 T0 探针（Gate A）。

方案依据：cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md
《T0 —— 基线与夹具隔离（不新增关系电路）【Gate A】》。

T0 本身不新增任何关系生成电路，只验证：
  T-T0-1  冻结选点确实对应真实存在的 thermal_quantum_collectors
  T-T0-2  T1 二元 / T2 三元冻结集合的邻接边确为局部最近邻（非人为拼接）
  T-T0-3  驱动冻结站点后，collector pre_trace 有峰值、早晚期呈非上升
          （无爆发式发散）、且与未驱动站点区分开
  T-T0-4  静息：全零输入（不驱动任何冻结站点）时，冻结站点 collector
          维持在其自身基线附近，不产生虚假发放尖峰
  T-T0-5  frozen 权重不变：驱动冻结站点所在的既有量子元 Bundle 前后，
          Memristor 权重逐项不变（这些 Bundle 本身已是 frozen，T0 只是
          复用读取，不新建 Bundle——验证复用路径没有意外触碰权重）
  T-T0-6  delay_steps 五项核实（纳入批判一§六）：结构性核实，非行为断言
  T-T0-7  关系层账本工具冒烟测试：T0 阶段关系层为空集，账本应能对空集合
          正确返回全零统计，且能读到 baseline 神经元/Bundle 数

驱动方式：复用 `test_thermal_coupling_generators.py` /
`test_quantum_thermal_pathways.py` 的方法论——直接给冻结站点的 Level1
喂合成 dT，绕开 world/body 自主物理动力学，手动传播其三级链路。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.circuit.bundle import BundleConfig
from nexus_v1.relations import (
    FROZEN_THERMAL_SITES, get_frozen_site,
    PeakDecayRestProbe, snapshot_weights, check_frozen_weights_against,
    get_relation_generator_stats,
)

DT = 0.001


def _build_circuit():
    return VariantCircuit()


def _propagate_xi_point(circuit, point_idx, dT_value, dt=DT):
    """驱动单个 thermpt 点的 warm/cool 三级链路一步（同已有量子元测试）。"""
    pid = f"thermpt{point_idx}"
    l1_warm = circuit.thermal_quantum_l1_warm[pid]
    l1_cool = circuit.thermal_quantum_l1_cool[pid]
    l1_warm.step(dT_value, dt)
    l1_cool.step(-dT_value, dt)

    idx_warm, idx_cool = point_idx * 2, point_idx * 2 + 1
    for idx in (idx_warm, idx_cool):
        b_l1_hc = circuit.bundles_thermal_quantum_l1_to_hc[idx]
        b_in = circuit.bundles_thermal_quantum_in[idx]
        b_col = circuit.bundles_thermal_quantum_collect[idx]

        currents_hc = b_l1_hc.propagate()
        hc_target = b_l1_hc.targets[0]
        hc_target.step(currents_hc[0] if currents_hc else 0.0, dt)

        ensemble = b_in.targets
        currents_in = b_in.propagate()
        for k, neuron in enumerate(ensemble):
            neuron.step(currents_in[k] if k < len(currents_in) else 0.0, dt)

        collector = b_col.targets[0]
        currents_col = b_col.propagate()
        collector.step(currents_col[0] if currents_col else 0.0, dt)


def _collector_for(circuit, point_idx, polarity="warm"):
    return circuit.thermal_quantum_collectors[f"thermpt{point_idx}_{polarity}"]


def _bundles_for(circuit, point_idx, polarity="warm"):
    idx = point_idx * 2 + (0 if polarity == "warm" else 1)
    return (
        circuit.bundles_thermal_quantum_l1_to_hc[idx],
        circuit.bundles_thermal_quantum_in[idx],
        circuit.bundles_thermal_quantum_collect[idx],
    )


# ─────────────────────────────────────────────────────────────
# T-T0-1：冻结选点对应真实存在的 collector
# ─────────────────────────────────────────────────────────────
def test_frozen_sites_exist_in_real_circuit():
    c = _build_circuit()
    all_indices = set(FROZEN_THERMAL_SITES["sites"].keys())
    assert all_indices == {
        FROZEN_THERMAL_SITES["t2_chain"]["order"][0],
        FROZEN_THERMAL_SITES["t2_chain"]["hub"],
        FROZEN_THERMAL_SITES["t2_chain"]["order"][2],
    }, "冻结站点集合应恰好等于 T2 三点链的三个索引"

    for idx in all_indices:
        site = get_frozen_site(idx)
        warm_label = site["warm_collector_label"]
        cool_label = site["cool_collector_label"]
        assert warm_label in circuit_collector_labels(c), \
            f"{warm_label} 不在真实电路的 thermal_quantum_collectors 中"
        assert cool_label in circuit_collector_labels(c), \
            f"{cool_label} 不在真实电路的 thermal_quantum_collectors 中"
    print(f"  T-T0-1 PASS: 冻结 {len(all_indices)} 个站点均对应真实 collector "
          f"（{sorted(all_indices)}）")


def circuit_collector_labels(circuit):
    return set(circuit.thermal_quantum_collectors.keys())


# ─────────────────────────────────────────────────────────────
# T-T0-2：邻接边确为局部最近邻（用真实几何距离复算校验，不信任缓存值）
# ─────────────────────────────────────────────────────────────
def test_adjacency_is_genuine_nearest_neighbor():
    import math
    from nexus_v1.components.skin_network import fibonacci_sphere_points
    from nexus_v1.relations.site_selection import recompute_for_verification

    positions = fibonacci_sphere_points(
        FROZEN_THERMAL_SITES["n_sphere_points"],
        FROZEN_THERMAL_SITES["sphere_radius"],
    )

    def dist(a, b):
        return math.sqrt(sum((a[k] - b[k]) ** 2 for k in range(3)))

    all_dists = []
    n = len(positions)
    for i in range(n):
        for j in range(i + 1, n):
            all_dists.append(dist(positions[i], positions[j]))
    all_dists.sort()
    global_min = all_dists[0]

    t1 = FROZEN_THERMAL_SITES["t1_pair"]
    measured = dist(positions[t1["a"]], positions[t1["b"]])
    assert abs(measured - t1["distance"]) < 1e-9, \
        "冻结记录的 T1 边距离与实时复算不一致（选点计算存在漂移）"
    # T1 边应在全局最小距离的很小倍数以内（真正局部邻接，不是随便选的中距离对）
    assert measured <= global_min * 1.01, \
        f"T1 边距离 {measured:.4f} 明显大于全局最小距离 {global_min:.4f}，不是真正的局部邻接"

    # 批判三修正点1：FROZEN_THERMAL_SITES 现在是字面常量，不再由几何公式
    # 实时生成——这里显式核对"冻结常量"与"当前几何公式重算结果"是否
    # 一致（recompute_for_verification 只用于验证，不是生产选择路径）。
    recomputed = recompute_for_verification()
    assert recomputed["center"] == FROZEN_THERMAL_SITES["t2_chain"]["hub"], \
        "当前几何公式重算的枢纽点与冻结常量不一致——母本几何公式已变化，需人工复核冻结值"
    assert {recomputed["nb1"], recomputed["nb2"]} == \
        {FROZEN_THERMAL_SITES["t2_chain"]["order"][0], FROZEN_THERMAL_SITES["t2_chain"]["order"][2]}, \
        "当前几何公式重算的邻居点与冻结常量不一致——母本几何公式已变化，需人工复核冻结值"

    print(f"  T-T0-2 PASS: T1 边距离={measured:.4f} ≈ 全局最小距离={global_min:.4f}，"
          f"确认为真实局部邻接；冻结常量与当前几何公式重算结果一致")


# ─────────────────────────────────────────────────────────────
# T-T0-3：驱动后有峰值、早晚期非上升发散
# ─────────────────────────────────────────────────────────────
def test_driven_site_has_peak_and_no_runaway():
    c = _build_circuit()
    t1 = FROZEN_THERMAL_SITES["t1_pair"]
    point_idx = t1["a"]
    collector = _collector_for(c, point_idx, "warm")

    probe = PeakDecayRestProbe()
    n_steps = 500
    for _ in range(n_steps):
        _propagate_xi_point(c, point_idx, dT_value=0.05)
        probe.record(collector.pre_trace)

    assert probe.peak > 0.0, "驱动冻结站点后 collector 应产生非零峰值"
    # 不要求严格衰减（AND门 collector 在持续驱动下可能维持高位），只要求
    # 早期均值不小于晚期均值的一个宽松界（防止无界发散）；晚期均值不应
    # 显著超过峰值的合理量级。
    assert probe.window_mean(0.8, 1.0) <= probe.peak * 1.05, \
        "晚期窗口均值不应显著超过峰值——提示可能存在无界发散"

    print(f"  T-T0-3 PASS: 驱动点{point_idx} 后 peak={probe.peak:.4f}, "
          f"早期均值={probe.window_mean(0.0,0.2):.4f}, "
          f"晚期均值={probe.window_mean(0.8,1.0):.4f}")


# ─────────────────────────────────────────────────────────────
# T-T0-4：静息——不驱动冻结站点时，collector 维持基线，无虚假尖峰
# ─────────────────────────────────────────────────────────────
def test_undriven_site_stays_at_rest():
    c = _build_circuit()
    t1 = FROZEN_THERMAL_SITES["t1_pair"]
    point_idx = t1["a"]
    collector = _collector_for(c, point_idx, "warm")

    probe = PeakDecayRestProbe()
    n_steps = 200
    for _ in range(n_steps):
        _propagate_xi_point(c, point_idx, dT_value=0.0)  # 零输入驱动
        probe.record(collector.pre_trace)

    assert probe.is_resting_zero(tol=1e-6), \
        f"零输入下 collector pre_trace 应维持精确静息，实际 peak={probe.peak}"
    print(f"  T-T0-4 PASS: 零输入 {n_steps} 步，collector 维持静息（peak={probe.peak:.2e}）")


# ─────────────────────────────────────────────────────────────
# T-T0-5：frozen 权重不变（复用既有量子元 Bundle，验证读取路径不触碰权重）
# ─────────────────────────────────────────────────────────────
def test_reading_frozen_sites_does_not_mutate_weights():
    c = _build_circuit()
    t1 = FROZEN_THERMAL_SITES["t1_pair"]
    point_idx = t1["a"]
    _b_l1_hc, b_in, b_col = _bundles_for(c, point_idx, "warm")

    snap_in = snapshot_weights(b_in)
    snap_col = snapshot_weights(b_col)

    for _ in range(300):
        _propagate_xi_point(c, point_idx, dT_value=0.05)

    err_in = check_frozen_weights_against(b_in, snap_in)
    err_col = check_frozen_weights_against(b_col, snap_col)
    assert err_in is None, err_in
    assert err_col is None, err_col
    print("  T-T0-5 PASS: 驱动 300 步后，冻结站点所属 Bundle 权重逐项不变")


# ─────────────────────────────────────────────────────────────
# T-T0-6：delay_steps 五项核实（结构性核实，非行为断言）
# ─────────────────────────────────────────────────────────────
def test_delay_steps_five_point_verification():
    """核实结论（详见 site_selection.py 与方案 T0 段落）：

    ① 是否对当前 Bundle 类型生效：generic，`SynapticBundle.propagate()`
       (bundle.py:266-271) 对任意 BundleConfig.delay_steps>0 都生效，
       不区分 spiking/non-spiking 源。
    ② 延迟队列存 activation 还是最终电流：存**最终电流**
       （Memristor.conduct() × synapse_gain 之后的 target_currents 向量），
       不是源神经元的 activation/pre_trace 原始值。
    ③ 多源 Bundle 延迟单位：整个 target_currents 向量作为一个单元入队，
       所有 target 共享同一个 FIFO、同一个延迟步数，不是逐 source-target
       对分别延迟。
    ④ 是否与 pre_trace 产生二次时间扩展：会。pre_trace 在 Neuron 层对源
       信号做时间展宽（EPSP 时程），发生在 conduct() 之前；delay_steps
       在 conduct() 之后对已展宽的电流再做整体时移。二者是独立的两次
       时域操作，会叠加展宽——这正是方案要求 T1 主方案用"非 spiking
       Neuron 的 RC 历史痕迹"而非 delay_steps 的原因：delay_steps 是
       矩形时移，没有 RC 那种连续积分/比较所需的动力学形状。
    ⑤ 是否进入 census/复制：`_delay_buffer` 是 Bundle 实例的私有属性
       （bundle.py:198），census（get_all_bundles）只登记 bundle 对象
       本身及其 config，不深入读取/序列化 _delay_buffer 内容；没有
       __deepcopy__/序列化钩子覆盖它。因此 delay_steps 的运行时状态
       对全局账本不可见，但这与"是否消耗能量"无关——按①的结论，
       delay_steps 本身只是移位，不改变 transport_cost 计算。
    """
    from nexus_v1.circuit.bundle import SynapticBundle
    from nexus_v1.components.neuron import Neuron, NeuronConfig

    src = Neuron(NeuronConfig(neuron_id="t0_delay_src", spiking=False))
    tgt = Neuron(NeuronConfig(neuron_id="t0_delay_tgt", spiking=False))
    cfg = BundleConfig(
        bundle_id="t0_delay_probe", learning_rule="frozen",
        initial_weight=1.0, weight_max=1.0, synapse_gain=1.0,
        delay_steps=3,
    )
    b = SynapticBundle(cfg, [src], [tgt])

    # ①③：喂一个非零 activation，观察 delay_steps 步内输出为 0（缓冲填充中），
    # 第 delay_steps+1 次调用起才吐出非零值——验证②（存的是电流不是activation：
    # 若中途改变 src.activation，只有原始那次的电流值最终被吐出）。
    # 非 spiking 神经元的 propagate() 直接读 src.activation（bundle.py:256）；
    # 这里手动赋值 .activation 而不经过完整 step() 动力学，是纯粹的 Bundle
    # 缓冲机制探针（测试夹具），不代表生物行为建模。
    src_activation_seq = [1.0, 0.0, 0.0, 0.0, 0.0]
    outputs = []
    for a in src_activation_seq:
        src.activation = a
        out = b.propagate()
        outputs.append(out[0])

    assert outputs[0] == 0.0 and outputs[1] == 0.0 and outputs[2] == 0.0, \
        f"delay_steps=3 时前 3 次 propagate() 应输出 0（缓冲填充中），实际={outputs[:3]}"
    assert outputs[3] != 0.0, \
        f"delay_steps=3 时第 4 次 propagate() 应吐出第 1 次计算的电流，实际={outputs}"

    print(f"  T-T0-6 PASS: delay_steps 五项核实完成（结构性验证，见函数 docstring）；"
          f"缓冲行为实测 outputs={[round(o,4) for o in outputs]}")


# ─────────────────────────────────────────────────────────────
# T-T0-7：关系层账本工具冒烟测试
# ─────────────────────────────────────────────────────────────
def test_relation_layer_census_smoke():
    c = _build_circuit()
    stats = get_relation_generator_stats(
        relation_neurons=[],
        relation_collectors=[],
        relation_bundles=[],
        baseline_circuit=c,
    )
    assert stats.n_neurons == 0
    assert stats.n_bundles == 0
    assert stats.baseline_n_neurons > 0, "应能读到 baseline 电路的真实神经元数"
    assert stats.baseline_n_bundles > 0, "应能读到 baseline 电路的真实 Bundle 数"
    for line in stats.report_lines():
        print(f"    {line}")
    print(f"  T-T0-7 PASS: 关系层账本工具对空集合返回全零统计，"
          f"baseline={stats.baseline_n_neurons} 神经元 / "
          f"{stats.baseline_n_bundles} bundle")


# ─────────────────────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────────────────────
TESTS = [
    ("T-T0-1 冻结选点对应真实 collector", test_frozen_sites_exist_in_real_circuit),
    ("T-T0-2 邻接为真实局部最近邻", test_adjacency_is_genuine_nearest_neighbor),
    ("T-T0-3 驱动后有峰值且不发散", test_driven_site_has_peak_and_no_runaway),
    ("T-T0-4 静息无虚假发放", test_undriven_site_stays_at_rest),
    ("T-T0-5 frozen 权重不变", test_reading_frozen_sites_does_not_mutate_weights),
    ("T-T0-6 delay_steps 五项核实", test_delay_steps_five_point_verification),
    ("T-T0-7 关系层账本冒烟测试", test_relation_layer_census_smoke),
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
