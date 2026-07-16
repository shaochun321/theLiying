"""nexus_v1.tests.test_basegen_thermal_t1 — 基础生成元温感轨 T1 探针（Gate B，r≺）。

方案依据：cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md
《T1 —— r≺ 时间关系（二元，最小支撑）》。Gate B：可直接按方案设计进入。

测试覆盖：
  T-TRP-1  census（批判三修正点3）：r≺ 关系 Bundle 应出现在
           RPrecCircuitT1.get_all_bundles() 中（供 Noether/Xin 账本追踪，
           约束1原文要求）；关系神经元/Collector 仍不在 get_all_neurons()
           中（护 T4.1 energy_per_neuron）；relations.census 工具提供
           额外的关系层专项统计（神经元数/近似能耗等 get_all_bundles()
           不覆盖的维度）
  T-TRP-2  frozen 权重不变：驱动后所有 r≺ Bundle 权重逐项不变
  T-TRP-3  fast 时间尺度精确性：合成脉冲延迟扫描，验证"A 先 B 后"在
           ~0-50 步窗口内被 a_prec_b_fast 检出且 b_prec_a_fast 不响应
           （非对称、时间窗有限）
  T-TRP-4  slow 时间尺度精确性：持续脉冲延迟扫描，验证"A 先 B 后"在
           更长窗口（~100-600 步）内被 a_prec_b_slow 检出
  T-TRP-5  对称情形：A/B 同时触发时，两个方向的 collector 响应量级相近
           （无虚假方向偏置）
  T-TRP-6  静息：不驱动任何 xi 源时，所有 trace/collector 维持精确静息
  T-TRP-7  真实 ξ^occ 集成冒烟测试：用真实感温量子元链路（而非合成脉冲）
           驱动，只验证不崩溃、trace 神经元最终有响应——**已知复现性/
           时序说明见测试内注释**（真实源有 ~400 步启动延迟 + 驱动停止
           后的残余自励振荡，不适合作为精确时序判别的驱动源，这是 T1
           分析报告记录的已知局限，不是本测试要断言的正确性目标）

驱动方式：T-TRP-3~6 直接对 `RPrecCircuitT1` 的 `rprec_xi_a`/`rprec_xi_b`
（既有 spiking collector 神经元）手动赋值 `.pre_trace`，绕开真实感温
量子元链路的复杂自励动态——这是纯粹的 r≺ 生成元电路本身的单元测试
夹具，同 T0 对 delay_steps 的最小复现实验方法论一致。T-TRP-7 才用
真实链路做端到端冒烟测试。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.relations.temporal_r_prec import RPrecCircuitT1
from nexus_v1.relations.probes import snapshot_weights, check_frozen_weights_against
from nexus_v1.relations.census import get_relation_generator_stats

DT = 0.001


def _build_circuit():
    return RPrecCircuitT1()


def _propagate_xi_point(circuit, point_idx, dT_value, dt=DT):
    """驱动单个 thermpt 点的 warm/cool 三级链路一步（同 T0 探针）。"""
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


def _run_synthetic(delay, pulse_len, n_steps):
    """合成脉冲测试夹具：直接控制 xi_a/xi_b 的 pre_trace（绕开真实感温链路）。"""
    c = _build_circuit()
    peak = {"ab_fast": 0.0, "ba_fast": 0.0, "ab_slow": 0.0, "ba_slow": 0.0}
    for step in range(n_steps):
        c.rprec_xi_a.pre_trace = 1.0 if 0 <= step < pulse_len else 0.0
        c.rprec_xi_b.pre_trace = 1.0 if delay <= step < delay + pulse_len else 0.0
        c.step_rprec()
        peak["ab_fast"] = max(peak["ab_fast"], c.rprec_collector_a_prec_b_fast.pre_trace)
        peak["ba_fast"] = max(peak["ba_fast"], c.rprec_collector_b_prec_a_fast.pre_trace)
        peak["ab_slow"] = max(peak["ab_slow"], c.rprec_collector_a_prec_b_slow.pre_trace)
        peak["ba_slow"] = max(peak["ba_slow"], c.rprec_collector_b_prec_a_slow.pre_trace)
    return peak


# ─────────────────────────────────────────────────────────────
# T-TRP-1：census
# ─────────────────────────────────────────────────────────────
def test_census():
    c = _build_circuit()

    all_bundle_ids = {b.config.bundle_id for b in c.get_all_bundles()}
    rprec_bundle_ids = {b.config.bundle_id for b in c.rprec_relation_bundles()}
    # 批判三修正点3：约束1原文"新 bundles → 进 get_all_bundles()"——
    # 只有关系*神经元*应排除全局 census（护 T4.1），关系 *Bundle* 必须
    # 进入 census（供 Noether/Xin/运输成本账本读取）。RPrecCircuitT1 现已
    # 覆写 get_all_bundles() 追加这 12 条 Bundle，此处断言"应该在里面"，
    # 而非此前误判的"不应该在里面"。
    assert rprec_bundle_ids <= all_bundle_ids, \
        "r≺ Bundle 应该出现在 RPrecCircuitT1.get_all_bundles() 中（供 Noether/Xin 账本追踪）"

    all_neuron_ids = {n.config.neuron_id for n in c.get_all_neurons()}
    for n in c.rprec_relation_neurons() + c.rprec_relation_collectors():
        assert n.config.neuron_id not in all_neuron_ids, \
            f"{n.config.neuron_id} 不应出现在 get_all_neurons() 中"

    stats = get_relation_generator_stats(
        relation_neurons=c.rprec_relation_neurons(),
        relation_collectors=c.rprec_relation_collectors(),
        relation_bundles=c.rprec_relation_bundles(),
        baseline_circuit=c,
    )
    assert stats.n_neurons == 8   # 4 trace + 4 collector
    assert stats.n_bundles == 12  # 4 xi->trace + 8 (trace+raw)->collector
    print(f"  T-TRP-1 PASS: {stats.n_neurons} 关系神经元正确隔离于母本 get_all_neurons() 之外；"
          f"{stats.n_bundles} 关系束正确进入 get_all_bundles()；"
          f"relations.census 工具可提供额外的关系层专项统计")


# ─────────────────────────────────────────────────────────────
# T-TRP-2：frozen 权重不变
# ─────────────────────────────────────────────────────────────
def test_frozen_weights_unchanged():
    c = _build_circuit()
    bundles = c.rprec_relation_bundles()
    snapshots = [snapshot_weights(b) for b in bundles]

    for step in range(300):
        c.rprec_xi_a.pre_trace = 1.0 if step % 40 < 20 else 0.0
        c.rprec_xi_b.pre_trace = 1.0 if step % 40 >= 20 else 0.0
        c.step_rprec()

    for b, snap in zip(bundles, snapshots):
        err = check_frozen_weights_against(b, snap)
        assert err is None, err
    print(f"  T-TRP-2 PASS: {len(bundles)} 条 r≺ Bundle 驱动 300 步后权重逐项不变")


# ─────────────────────────────────────────────────────────────
# T-TRP-3：fast 时间尺度精确性（合成脉冲，短窗）
# ─────────────────────────────────────────────────────────────
def test_fast_timescale_precedence():
    # 明确重合：a_prec_b 应强响应，b_prec_a 应为 0（B 严格晚于 A 结束才开始）
    peak_clear = _run_synthetic(delay=30, pulse_len=20, n_steps=300)
    assert peak_clear["ab_fast"] > 0.5, \
        f"A 明确先于 B（delay=30，A脉冲仅20步）时，a_prec_b_fast 应强响应，实际={peak_clear['ab_fast']}"
    assert peak_clear["ba_fast"] == 0.0, \
        f"A 明确先于 B 时，b_prec_a_fast 不应响应，实际={peak_clear['ba_fast']}"

    # 超出 fast 窗口（远大于 tau_fast=50 步）：两者都不应响应
    peak_far = _run_synthetic(delay=150, pulse_len=20, n_steps=400)
    assert peak_far["ab_fast"] == 0.0 and peak_far["ba_fast"] == 0.0, \
        f"超出 fast 时间窗后不应有任何方向响应，实际 ab={peak_far['ab_fast']} ba={peak_far['ba_fast']}"

    print(f"  T-TRP-3 PASS: fast 时间尺度（tau=50步）——"
          f"delay=30 时 a_prec_b={peak_clear['ab_fast']:.3f}(响应) b_prec_a=0(不响应)；"
          f"delay=150 时两者均为 0（超出时间窗）")


# ─────────────────────────────────────────────────────────────
# T-TRP-4：slow 时间尺度精确性（持续脉冲，长窗）
# ─────────────────────────────────────────────────────────────
def test_slow_timescale_precedence():
    # slow 通道需要持续驱动（非brief脉冲）才能积累出可读信号，
    # 见 T1 分析报告《标定过程》：容量更大意味着需要更多累积电荷。
    peak_clear = _run_synthetic(delay=200, pulse_len=200, n_steps=1200)
    assert peak_clear["ab_slow"] > 0.5, \
        f"A 明确先于 B（delay=200，A持续200步）时，a_prec_b_slow 应强响应，实际={peak_clear['ab_slow']}"
    assert peak_clear["ba_slow"] == 0.0, \
        f"A 明确先于 B 时，b_prec_a_slow 不应响应，实际={peak_clear['ba_slow']}"

    print(f"  T-TRP-4 PASS: slow 时间尺度（tau=600步）——"
          f"delay=200(持续200步驱动) 时 a_prec_b={peak_clear['ab_slow']:.3f}(响应) "
          f"b_prec_a=0(不响应)，验证长程时间尺度的精确性")


# ─────────────────────────────────────────────────────────────
# T-TRP-5：对称情形（delay=0，同时触发）——无虚假方向偏置
# ─────────────────────────────────────────────────────────────
def test_symmetric_case_no_spurious_bias():
    peak = _run_synthetic(delay=0, pulse_len=20, n_steps=300)
    ab, ba = peak["ab_fast"], peak["ba_fast"]
    assert ab > 0.0 and ba > 0.0, "同时触发时两个方向都应有响应"
    ratio = max(ab, ba) / max(min(ab, ba), 1e-9)
    # 容差取 3.0（非最初的 1.5）：bundle.py:169-171 的 hash 对称性打破扰动对
    # 每条 Memristor 独立施加 ±25%，本场景两个方向各经过 3 条 bundle
    # （xi→trace, trace→collector, raw_xi→collector），复合后单方向偏差可能
    # 达到 (1.25)^3≈1.95 量级；两方向独立扰动最坏情况下比值可到 ~3.8。
    # 3.0 是"确认无系统性方向偏置"（区别于 T-TRP-3/4 那种有意义的方向
    # 差异）的合理宽松界，不依赖固定 PYTHONHASHSEED（T0 已记录此复现性
    # 风险，见 site_selection.py docstring）。
    assert ratio < 3.0, \
        f"同时触发（无先后关系）时两方向响应量级不应系统性偏置，实际 ab={ab:.4f} ba={ba:.4f} ratio={ratio:.2f}"
    print(f"  T-TRP-5 PASS: 同时触发时 a_prec_b={ab:.4f} b_prec_a={ba:.4f}，"
          f"量级接近（ratio={ratio:.2f}<3.0，含 hash 扰动容差），无系统性方向偏置")


# ─────────────────────────────────────────────────────────────
# T-TRP-6：静息
# ─────────────────────────────────────────────────────────────
def test_rest_state():
    c = _build_circuit()
    for step in range(200):
        c.rprec_xi_a.pre_trace = 0.0
        c.rprec_xi_b.pre_trace = 0.0
        c.step_rprec()
    for n in c.rprec_relation_neurons() + c.rprec_relation_collectors():
        assert abs(n.activation) <= 1e-9, \
            f"{n.config.neuron_id} 在零输入下应维持静息，实际 activation={n.activation}"
    print("  T-TRP-6 PASS: 零输入 200 步，全部 r≺ 关系神经元维持静息")


# ─────────────────────────────────────────────────────────────
# T-TRP-7：真实 ξ^occ 集成冒烟测试
# ─────────────────────────────────────────────────────────────
def test_real_xi_integration_smoke():
    """已知局限（见 T1 分析报告）：真实感温量子元链路单点驱动有 ~400 步
    启动延迟，且驱动停止后仍可能因内部 K+适应/bias 阶梯产生残余自励
    振荡——不适合作为"精确时序判别"的驱动源（那是 T-TRP-3/4 用合成脉冲
    覆盖的职责）。本测试只验证真实链路接入后系统不崩溃、且经过足够长
    驱动窗口后 trace 神经元确实能观察到非零响应（结构连通性验证）。
    """
    # 窗口取 3000 步（而非 T0 报告实测的 ~400 步启动延迟）是为了在
    # PYTHONHASHSEED 未固定时仍稳健通过——启动延迟受 bundle.py:169-171
    # 的 hash 对称性打破扰动影响，逐进程可能远超 400 步（T0 报告已记录
    # 该已知复现性风险，未固定种子时实测曾观察到 >2000 步）。
    c = _build_circuit()
    site_a = c.rprec_site_a
    peak_trace = 0.0
    for step in range(3000):
        _propagate_xi_point(c, site_a, dT_value=0.05)
        c.step_rprec()
        peak_trace = max(peak_trace, c.rprec_trace_a_fast.activation)
    assert peak_trace > 0.0, \
        "真实 ξ^occ 驱动 3000 步后，trace_a_fast 应至少有一次非零响应（结构连通性）"
    print(f"  T-TRP-7 PASS: 真实链路驱动 3000 步，trace_a_fast peak={peak_trace:.4f}，"
          f"结构连通性确认（精确时序判别见 T-TRP-3/4 合成脉冲测试）")


# ─────────────────────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────────────────────
TESTS = [
    ("T-TRP-1 census", test_census),
    ("T-TRP-2 frozen 权重不变", test_frozen_weights_unchanged),
    ("T-TRP-3 fast 时间尺度精确性", test_fast_timescale_precedence),
    ("T-TRP-4 slow 时间尺度精确性", test_slow_timescale_precedence),
    ("T-TRP-5 对称情形无偏置", test_symmetric_case_no_spurious_bias),
    ("T-TRP-6 静息", test_rest_state),
    ("T-TRP-7 真实ξ^occ集成冒烟测试", test_real_xi_integration_smoke),
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
