"""tss.tests.test_basegen_thermal_t3_ratio — T3-B r_part 一级验收（Gate D）。

方案依据：cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md
第十七节 17.2/17.3。本轮只验证 Gate D 一级验收（合成脉冲，同 T1 Gate B1
方法论）：

  T-RPT-1  较大输入→较大输出
  T-RPT-2  交换输入则输出交换（同 T1 T-TRP-8 交换协变性方法论）
  T-RPT-3  单输入时对应通道占优
  T-RPT-4  等强输入输出近似相等
  T-RPT-5  静默时无虚假占比
  T-RPT-6  census 覆写正确（关系 Bundle 进census，关系神经元不进，同
           T1 T-TRP-1 的既定修正模式）

二级验收（共同尺度不变性/真实ξ输入/三元扩展/升格r_ρ）留作 T3-C，
本文件不覆盖。

已知发现（方案第十七节 17.5，容差已在 T3-C0 按实测数据收紧，见十八.4
第3/5点）：`bundle_rpart_xi_a_to_channel`/`bundle_rpart_xi_b_to_channel`
用不同 `bundle_id` 字符串，`Memristor` 按 `hash((bundle_id,i_s,i_t))`
施加对称性打破扰动（`bundle.py:169-171`，T1 已记录的同一机制），导致
两条 Bundle 标称权重相同但实际电导不同。这是电路结构本身的真实特性
（DN 池数学本身精确对称，扰动来自更上游的 Bundle 级），T-RPT-2/T-RPT-4
因此用容差断言而非精确相等——同 T1 T-TRP-5/T-TRP-8 先例，测试应适应
这个已知的物理噪声源，不强行让它"消失"。

容差校准（`_diag_t3_c0_multiseed.py` 实测，3个固定 PYTHONHASHSEED={0,1,42}）：
eps_equal/eps_swap/eps_ratio 实测范围 [0.0000, 0.0525]，1.5x 余量后取
`_HASH_JITTER_REL_TOL=0.08`（原 0.25 是首次发现时的粗略保守值，未经
实测校准；本次基于真实多 seed 数据收紧，不是拍脑袋改数字）。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tss.relations.ratio_r_part import RPartCircuitT3
from nexus_v1.circuit.variant_adapter import VariantCircuit

DT = 0.001
_N_STEPS = 200  # 驱动步数，足够让 channel collector RC 积分到稳态

# Bundle 级 hash 扰动容差：T3-C0 多seed实测范围[0,0.0525]（3个固定seed），
# 但不设PYTHONHASHSEED的常规测试运行中观测到~0.07量级（说明3个采样点
# 未覆盖全部扰动范围），故取约2x余量=0.10，而非1.5x的0.08——留更多
# 安全边际，避免固定seed样本量不足导致偶发失败（见模块docstring"容差校准"）。
_HASH_JITTER_REL_TOL = 0.10


def _drive(i_a: float, i_b: float, n_steps: int = _N_STEPS) -> dict:
    """构造一个新电路，用恒定 pre_trace 驱动 n_steps 步，返回最终读数。"""
    c = RPartCircuitT3()
    result = {}
    for _ in range(n_steps):
        c.rpart_xi_a.pre_trace = i_a
        c.rpart_xi_b.pre_trace = i_b
        result = c.step_rpart(dt=DT)
    result["channel_a_activation"] = c.rpart_channel_a.activation
    result["channel_b_activation"] = c.rpart_channel_b.activation
    return result


def test_bigger_input_bigger_output():
    """T-RPT-1：较大输入→较大输出（i_a > i_b ⟹ y_a > y_b）。"""
    r = _drive(i_a=1.0, i_b=0.3)
    assert r["y_a"] > r["y_b"], (
        f"T-RPT-1 FAIL: i_a=1.0 > i_b=0.3 但 y_a={r['y_a']:.4g} 未大于 y_b={r['y_b']:.4g}"
    )
    print(f"  T-RPT-1 PASS: i_a=1.0>i_b=0.3 -> y_a={r['y_a']:.4g} > y_b={r['y_b']:.4g}")


def test_swap_covariance():
    """T-RPT-2：交换输入则输出交换（同 T1 T-TRP-8 方法论）。

    容差说明：channel_a/channel_b 各走独立 Bundle（不同 bundle_id），
    Memristor 按 hash((bundle_id,i,j)) 施加的对称性打破扰动导致两条
    Bundle 标称权重相同但实际电导有 ~5% 量级差异（方案第十七节 17.5
    已核实根因）——这是电路结构本身的真实特性，交换协变性用相对容差
    而非精确相等来验证，容差覆盖该已知扰动幅度。
    """
    r1 = _drive(i_a=1.0, i_b=0.3)
    r2 = _drive(i_a=0.3, i_b=1.0)

    rel_diff_a = abs(r1["y_a"] - r2["y_b"]) / max(r1["y_a"], r2["y_b"])
    rel_diff_b = abs(r1["y_b"] - r2["y_a"]) / max(r1["y_b"], r2["y_a"])
    assert rel_diff_a < _HASH_JITTER_REL_TOL, (
        f"T-RPT-2 FAIL: 交换后 y_a(before)={r1['y_a']:.6g} 与 y_b(after)={r2['y_b']:.6g} "
        f"相对差 {rel_diff_a:.3f} 超出容差 {_HASH_JITTER_REL_TOL}"
    )
    assert rel_diff_b < _HASH_JITTER_REL_TOL, (
        f"T-RPT-2 FAIL: 交换后 y_b(before)={r1['y_b']:.6g} 与 y_a(after)={r2['y_a']:.6g} "
        f"相对差 {rel_diff_b:.3f} 超出容差 {_HASH_JITTER_REL_TOL}"
    )
    print(f"  T-RPT-2 PASS: 交换协变近似成立（容差{_HASH_JITTER_REL_TOL}）"
          f"({r1['y_a']:.4g},{r1['y_b']:.4g}) <-> ({r2['y_a']:.4g},{r2['y_b']:.4g})，"
          f"rel_diff=({rel_diff_a:.3f},{rel_diff_b:.3f})")


def test_single_input_dominance():
    """T-RPT-3：单输入时对应通道占优。"""
    r_a_only = _drive(i_a=1.0, i_b=0.0)
    assert r_a_only["y_a"] > 0.0, "T-RPT-3 FAIL: 单驱动a时y_a应为正"
    assert r_a_only["y_b"] == 0.0, f"T-RPT-3 FAIL: 单驱动a时y_b应为0，实际={r_a_only['y_b']}"

    r_b_only = _drive(i_a=0.0, i_b=1.0)
    assert r_b_only["y_b"] > 0.0, "T-RPT-3 FAIL: 单驱动b时y_b应为正"
    assert r_b_only["y_a"] == 0.0, f"T-RPT-3 FAIL: 单驱动b时y_a应为0，实际={r_b_only['y_a']}"
    print(f"  T-RPT-3 PASS: 单驱动a -> (y_a={r_a_only['y_a']:.4g}, y_b=0)；"
          f"单驱动b -> (y_a=0, y_b={r_b_only['y_b']:.4g})")


def test_equal_input_approximately_equal_output():
    """T-RPT-4：等强输入输出近似相等（容差覆盖 Bundle 级 hash 扰动，见 T-RPT-2 说明）。"""
    r = _drive(i_a=1.0, i_b=1.0)
    rel_diff = abs(r["y_a"] - r["y_b"]) / max(r["y_a"], r["y_b"])
    assert rel_diff < _HASH_JITTER_REL_TOL, (
        f"T-RPT-4 FAIL: 等强输入 y_a={r['y_a']:.6g} 与 y_b={r['y_b']:.6g} "
        f"相对差 {rel_diff:.3f} 超出容差 {_HASH_JITTER_REL_TOL}"
    )
    print(f"  T-RPT-4 PASS: 等强输入近似对称（容差{_HASH_JITTER_REL_TOL}）"
          f"y_a={r['y_a']:.6g}, y_b={r['y_b']:.6g}, rel_diff={rel_diff:.3f}")


def test_silence_no_spurious_ratio():
    """T-RPT-5：静默时无虚假占比（i_a=i_b=0 ⟹ y_a=y_b=0）。"""
    r = _drive(i_a=0.0, i_b=0.0)
    assert r["y_a"] == 0.0, f"T-RPT-5 FAIL: 静默时y_a应为0，实际={r['y_a']}"
    assert r["y_b"] == 0.0, f"T-RPT-5 FAIL: 静默时y_b应为0，实际={r['y_b']}"
    assert r["channel_a_activation"] == 0.0, (
        f"T-RPT-5 FAIL: 静默时channel_a activation应为0，实际={r['channel_a_activation']}"
    )
    assert r["channel_b_activation"] == 0.0, (
        f"T-RPT-5 FAIL: 静默时channel_b activation应为0，实际={r['channel_b_activation']}"
    )
    print("  T-RPT-5 PASS: 静默时 y_a=y_b=0，channel activation 均为0，无虚假占比")


def test_census_override_correct():
    """T-RPT-6：census 覆写正确——关系 Bundle 进 get_all_bundles()，
    关系神经元不进 get_all_neurons()（同 T1 T-TRP-1 的既定修正模式，
    这里直接验证正确，避免重蹈 T1 曾经的实现 bug）。
    """
    c = RPartCircuitT3()
    base = VariantCircuit()

    all_bundles = c.get_all_bundles()
    base_bundle_count = len(base.get_all_bundles())
    assert len(all_bundles) == base_bundle_count + 2, (
        f"T-RPT-6 FAIL: census bundle 数应为基线+2，实际基线={base_bundle_count}，"
        f"实际={len(all_bundles)}"
    )
    assert c.bundle_rpart_xi_a_to_channel in all_bundles, (
        "T-RPT-6 FAIL: bundle_rpart_xi_a_to_channel 未进入 get_all_bundles()"
    )
    assert c.bundle_rpart_xi_b_to_channel in all_bundles, (
        "T-RPT-6 FAIL: bundle_rpart_xi_b_to_channel 未进入 get_all_bundles()"
    )

    all_neurons = c.get_all_neurons()
    assert c.rpart_channel_a not in all_neurons, (
        "T-RPT-6 FAIL: rpart_channel_a 不应出现在 get_all_neurons()（护 T4.1 energy_per_neuron）"
    )
    assert c.rpart_channel_b not in all_neurons, (
        "T-RPT-6 FAIL: rpart_channel_b 不应出现在 get_all_neurons()"
    )
    print(f"  T-RPT-6 PASS: census bundle={base_bundle_count}+2，关系神经元正确排除")


def test_pool_relation_ledger():
    """T-RPT-7：共享池关系层账本（T3-C0第4点，方案第十八节18.4）。

    验证：① 每步只更新一次（pool_step_count == 驱动步数）；② 两路 dt=0
    读出不改变池状态（已在 T3 路径判别阶段验证过，这里额外确认账本计数
    不会被只读读出误计入）；③ 新实例之间 pool 不共享（不同电路实例的
    共享池是不同对象，互不干扰）。
    """
    c1 = RPartCircuitT3()
    stats0 = c1.rpart_relation_pool_stats()
    assert stats0["pool_instance_count"] == 1, "T-RPT-7 FAIL: pool_instance_count应为1"
    assert stats0["pool_step_count"] == 0, "T-RPT-7 FAIL: 初始pool_step_count应为0"
    assert stats0["pool_activity"] == 0.0, "T-RPT-7 FAIL: 初始pool_activity应为0"

    n_steps = 50
    for _ in range(n_steps):
        c1.rpart_xi_a.pre_trace = 1.0
        c1.rpart_xi_b.pre_trace = 0.5
        c1.step_rpart(dt=DT)
    stats1 = c1.rpart_relation_pool_stats()
    assert stats1["pool_step_count"] == n_steps, (
        f"T-RPT-7 FAIL: {n_steps}步驱动后pool_step_count应为{n_steps}，"
        f"实际={stats1['pool_step_count']}（每步只更新一次，dt=0只读不应计入）"
    )
    assert stats1["pool_activity"] > 0.0, "T-RPT-7 FAIL: 驱动后pool_activity应大于0"

    c2 = RPartCircuitT3()
    assert c1.rpart_shared_pool is not c2.rpart_shared_pool, (
        "T-RPT-7 FAIL: 不同电路实例的共享池不应是同一对象"
    )
    stats2 = c2.rpart_relation_pool_stats()
    assert stats2["pool_step_count"] == 0, (
        "T-RPT-7 FAIL: 新实例的pool_step_count不应受c1驱动影响"
    )
    assert stats2["pool_activity"] == 0.0, (
        "T-RPT-7 FAIL: 新实例的pool_activity不应受c1驱动影响"
    )
    print(f"  T-RPT-7 PASS: pool_step_count={stats1['pool_step_count']}（=驱动步数），"
          f"pool_activity={stats1['pool_activity']:.4g}，新实例不共享池")


# ─────────────────────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────────────────────
TESTS = [
    ("T-RPT-1 较大输入更大输出", test_bigger_input_bigger_output),
    ("T-RPT-2 交换协变性", test_swap_covariance),
    ("T-RPT-3 单输入对应通道占优", test_single_input_dominance),
    ("T-RPT-4 等强输入近似相等", test_equal_input_approximately_equal_output),
    ("T-RPT-5 静默无虚假占比", test_silence_no_spurious_ratio),
    ("T-RPT-6 census覆写正确", test_census_override_correct),
    ("T-RPT-7 共享池关系层账本", test_pool_relation_ledger),
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
