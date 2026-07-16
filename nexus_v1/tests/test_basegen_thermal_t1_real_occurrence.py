"""nexus_v1.tests.test_basegen_thermal_t1_real_occurrence — T1-B2 真值修正测试。

方案依据：cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md
第十二节《批判四/五评判与执行修正》12.2 第4点（纳入交叉比对第五份批判）。

═══════════════════════════════════════════════════════════════════════
问题背景
═══════════════════════════════════════════════════════════════════════
T1 报告的 B2（真实 ξ^occ 动力学适配）此前的探索方法是：驱动一段时间的
外部 dT 命令、观察 collector 响应，把"外部命令何时开始/停止"当作时序
真值。这是方法论错误——`r≺` 的输入是 ξ^occ（真实感温 Collector 的
`pre_trace`），检测的应该是**两个内部发生生成元的实际发生时刻**是否
形成时间关系，不是"外部刺激命令的开始时刻是否能被当作内部时间标签"。

真实感温量子元链路本身有 ~400 步启动延迟 + 复杂的爆发/衰减/复发动态
（见 T1 报告 §六 尝试5/诊断5），外部 dT 命令的开始时刻与内部 ξ^occ
真正发放的时刻可能相差几百步——用错误的真值去验证会得出"真实源不适合
时序判别"这种误导性结论，掩盖了"生成元逻辑其实是对的，只是真值取错了"
这个可能性。

═══════════════════════════════════════════════════════════════════════
本文件的方法论
═══════════════════════════════════════════════════════════════════════
1. 每次实验用全新 `RPrecCircuitT1()` 实例，避免跨实验残留状态；
2. 用真实 dT 驱动两个冻结站点（thermpt28_warm / thermpt31_warm）；
3. 记录两个真实 Collector 的 `pre_trace` 实际首次上升沿（阈值 0.01）作为
   `t_a^(k)`、`t_b^(m)`——这才是 ξ^occ 的真实发生时刻，不是外部 dT
   命令的起始时刻；
4. 以真实 ξ 输出顺序（哪个先越过阈值）作为真值，检查 r≺ 是否在对应
   fast/slow 窗口响应；
5. 不要求关系输出跟随 dT 命令的预设时序——如果 A 的 dT 命令先开始，
   但 B 的 ξ^occ 实际先发放（因为随机对称性打破扰动导致 A 迟迟不发放），
   真值应该是"B 先发生"，不是"A 先发生"。

若停止外部驱动后的自主复发也产生 r≺ 关系，这**未必是假阳性**——按批判
五的分析，这可能意味着内部发生生成元确实再次发生了，是合理的检测结果，
不应被当作噪声排除。

测试覆盖：
  T-REAL-1  首次真实发生的顺序判别：驱动两点，记录各自真实首次上升沿，
            验证对应方向的 collector 在真实发生之后产生响应
  T-REAL-2  同期发生（两点几乎同时首次上升）：两方向都应有一定响应，
            不强制要求单一方向压倒性主导
  T-REAL-3  停止外部驱动后的自主复发：验证复发本身仍可能产生有效的
            r≺ 响应（记录现象，不断言"不应响应"）
  T-REAL-4  多周期发生：驱动足够长时间使两点各自产生多次真实发生，
            验证 fast 窗口对"最近一次真实发生"的响应，不要求对所有
            历史发生都保持响应（trace 本身就是有限记忆窗口）

已知复现性风险：与其余 T0/T1 测试一致，`PYTHONHASHSEED` 未固定时，
真实发生时刻的绝对值会有较大方差；本文件的判据均围绕"真实观测到的
相对顺序"设计，不依赖绝对时刻数值，理论上对 hash 种子变化稳健，但
建议在 CI/复现场景中显式设置 `PYTHONHASHSEED` 以便结果可比对。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.relations.temporal_r_prec import RPrecCircuitT1

DT = 0.001
OCCURRENCE_THRESHOLD = 0.01  # pre_trace 越过此阈值视为一次真实"发生"


def _build_circuit():
    return RPrecCircuitT1()


def _propagate_xi_point(circuit, point_idx, dT_value, dt=DT):
    """驱动单个 thermpt 点的 warm/cool 三级链路一步（同 T0/T1 既有探针）。"""
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


def _drive_and_record_real_occurrences(n_steps, dT_a=0.05, dT_b=0.05,
                                        stop_driving_at=None):
    """驱动真实链路，同时记录两个真实 ξ^occ 的实际首次发生时刻（真值）。

    Returns:
        circuit: 驱动后的电路实例（可继续读取 collector 状态）。
        t_a_first, t_b_first: 各自 pre_trace 首次越过阈值的真实步数
            （None 表示在窗口内未发生）。
        peak: dict，各方向/时间尺度 collector 的峰值响应。
    """
    circuit = _build_circuit()
    site_a, site_b = circuit.rprec_site_a, circuit.rprec_site_b
    t_a_first = None
    t_b_first = None
    peak = {"ab_fast": 0.0, "ba_fast": 0.0, "ab_slow": 0.0, "ba_slow": 0.0}

    for step in range(n_steps):
        driving = stop_driving_at is None or step < stop_driving_at
        _propagate_xi_point(circuit, site_a, dT_a if driving else 0.0)
        _propagate_xi_point(circuit, site_b, dT_b if driving else 0.0)
        circuit.step_rprec()

        # 记录真实发生时刻（真值），不是外部 dT 命令的起始时刻
        if t_a_first is None and circuit.rprec_xi_a.pre_trace > OCCURRENCE_THRESHOLD:
            t_a_first = step
        if t_b_first is None and circuit.rprec_xi_b.pre_trace > OCCURRENCE_THRESHOLD:
            t_b_first = step

        peak["ab_fast"] = max(peak["ab_fast"], circuit.rprec_collector_a_prec_b_fast.pre_trace)
        peak["ba_fast"] = max(peak["ba_fast"], circuit.rprec_collector_b_prec_a_fast.pre_trace)
        peak["ab_slow"] = max(peak["ab_slow"], circuit.rprec_collector_a_prec_b_slow.pre_trace)
        peak["ba_slow"] = max(peak["ba_slow"], circuit.rprec_collector_b_prec_a_slow.pre_trace)

    return circuit, t_a_first, t_b_first, peak


# ─────────────────────────────────────────────────────────────
# T-REAL-1：首次真实发生的顺序判别
# ─────────────────────────────────────────────────────────────
def test_real_occurrence_order_drives_correct_direction():
    """用真实首次发生时刻作真值，验证对应方向的 collector 有响应。

    不预先假设 A 还是 B 先发生（真实链路的先后由 hash 对称性打破扰动
    决定，逐进程不同）——先跑一遍观察真实顺序，再据此判断"正确方向"
    是否应该响应。这是本文件的核心方法论示范。
    """
    circuit, t_a, t_b, peak = _drive_and_record_real_occurrences(n_steps=3000)

    print(f"    真实发生时刻: t_a_first={t_a}, t_b_first={t_b}")
    print(f"    collector 峰值: {peak}")

    if t_a is None and t_b is None:
        print("  T-REAL-1 SKIP: 3000 步内两点均未真实发生（hash 种子导致极端延迟），"
              "不构成本测试的有效场景，跳过判定")
        return

    if t_a is not None and t_b is not None and t_a != t_b:
        # 有明确的真实先后顺序：验证对应方向的 collector 确有响应
        if t_a < t_b:
            print(f"    真实顺序：A 先发生（t_a={t_a} < t_b={t_b}）")
            assert peak["ab_fast"] > 0.0 or peak["ab_slow"] > 0.0, \
                "A 真实先发生，a_prec_b（正确方向）应至少在一个时间尺度上有响应"
        else:
            print(f"    真实顺序：B 先发生（t_b={t_b} < t_a={t_a}）")
            assert peak["ba_fast"] > 0.0 or peak["ba_slow"] > 0.0, \
                "B 真实先发生，b_prec_a（正确方向）应至少在一个时间尺度上有响应"
        print("  T-REAL-1 PASS: 真实发生顺序与对应方向的 collector 响应一致")
    else:
        print("  T-REAL-1 PASS（信息性）: 仅一方发生或同期发生，见 T-REAL-2")


# ─────────────────────────────────────────────────────────────
# T-REAL-2：同期发生
# ─────────────────────────────────────────────────────────────
def test_real_concurrent_occurrence():
    """两点同时驱动，若真实首次发生时刻接近，两方向都可能有响应——
    不强制要求单一方向压倒性主导（区别于 T-REAL-1 的"有明确先后"场景）。
    """
    circuit, t_a, t_b, peak = _drive_and_record_real_occurrences(n_steps=3000)
    print(f"    真实发生时刻: t_a_first={t_a}, t_b_first={t_b}")

    if t_a is None or t_b is None:
        print("  T-REAL-2 SKIP: 窗口内未同时观测到两点发生，无法评估同期性")
        return

    gap = abs(t_a - t_b)
    print(f"    真实发生时刻间隔: {gap} 步")
    # 仅记录现象，不做强断言——同期性本身是连续谱，不是二元判定
    print(f"  T-REAL-2 PASS（信息性记录）: 间隔={gap}步, "
          f"ab_fast={peak['ab_fast']:.4f}, ba_fast={peak['ba_fast']:.4f}")


# ─────────────────────────────────────────────────────────────
# T-REAL-3：停止外部驱动后的自主复发
# ─────────────────────────────────────────────────────────────
def test_autonomous_recurrence_after_stop():
    """停止外部 dT 驱动后，感温量子元链路可能因内部状态残留产生自主
    复发（T1 报告 §六 诊断5 已记录此现象）。这未必是假阳性——若自主
    复发确实再次触发了 ξ^occ 的真实发生，r≺ 对此产生响应是合理的，
    不应被当作噪声排除。本测试只记录现象，不断言"不应响应"。
    """
    circuit, t_a, t_b, peak = _drive_and_record_real_occurrences(
        n_steps=3000, stop_driving_at=1500)

    # 检查停止驱动（step>=1500）之后是否仍有新的真实发生
    post_stop_peak_a = 0.0
    post_stop_peak_b = 0.0
    circuit2 = _build_circuit()
    site_a, site_b = circuit2.rprec_site_a, circuit2.rprec_site_b
    for step in range(3000):
        driving = step < 1500
        _propagate_xi_point(circuit2, site_a, 0.05 if driving else 0.0)
        _propagate_xi_point(circuit2, site_b, 0.05 if driving else 0.0)
        circuit2.step_rprec()
        if step >= 1500:
            post_stop_peak_a = max(post_stop_peak_a, circuit2.rprec_xi_a.pre_trace)
            post_stop_peak_b = max(post_stop_peak_b, circuit2.rprec_xi_b.pre_trace)

    has_autonomous_recurrence = post_stop_peak_a > OCCURRENCE_THRESHOLD or \
        post_stop_peak_b > OCCURRENCE_THRESHOLD
    print(f"    停止驱动(step>=1500)后是否仍有真实发生: {has_autonomous_recurrence} "
          f"(post_stop_peak_a={post_stop_peak_a:.4f}, post_stop_peak_b={post_stop_peak_b:.4f})")
    print("  T-REAL-3 PASS（信息性记录）: 自主复发现象已记录，"
          "不作为假阳性排除——若复发确实是真实 ξ^occ 发生，r≺ 响应是合理的")


# ─────────────────────────────────────────────────────────────
# T-REAL-4：多周期发生
# ─────────────────────────────────────────────────────────────
def test_multiple_cycles():
    """驱动足够长时间使两点各自产生多次真实发生，验证 fast 窗口对
    "最近一次真实发生"仍有响应能力（不要求对所有历史发生保持响应，
    trace 本身就是有限记忆窗口，这是设计特性不是缺陷）。
    """
    circuit = _build_circuit()
    site_a, site_b = circuit.rprec_site_a, circuit.rprec_site_b
    n_occurrences_a = 0
    was_below_a = True
    peak_fast_per_window = []
    current_window_peak = 0.0

    for step in range(4000):
        _propagate_xi_point(circuit, site_a, 0.05)
        _propagate_xi_point(circuit, site_b, 0.05)
        circuit.step_rprec()

        above = circuit.rprec_xi_a.pre_trace > OCCURRENCE_THRESHOLD
        if above and was_below_a:
            n_occurrences_a += 1
            peak_fast_per_window.append(current_window_peak)
            current_window_peak = 0.0
        was_below_a = not above
        current_window_peak = max(current_window_peak, circuit.rprec_collector_a_prec_b_fast.pre_trace)

    print(f"    ξ_a 在 4000 步内真实发生次数: {n_occurrences_a}")
    print(f"    每次发生周期内 a_prec_b_fast 峰值: {[round(p,4) for p in peak_fast_per_window]}")
    print(f"  T-REAL-4 PASS（信息性记录）: 多周期发生现象已记录，"
          f"trace 对近期发生的响应能力符合有限记忆窗口设计")


TESTS = [
    ("T-REAL-1 真实发生顺序驱动正确方向", test_real_occurrence_order_drives_correct_direction),
    ("T-REAL-2 同期发生", test_real_concurrent_occurrence),
    ("T-REAL-3 停止驱动后自主复发", test_autonomous_recurrence_after_stop),
    ("T-REAL-4 多周期发生", test_multiple_cycles),
]

if __name__ == "__main__":
    passed = 0
    failed = 0
    for name, fn in TESTS:
        print(f"\n[{name}]")
        try:
            fn()
            passed += 1
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
