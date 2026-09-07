"""T-RPP-R1简化版：P2-B1R 学习后复放验证（2026-07-29；双层拆分 2026-09-06）。

评判依据：`cell-cell/交叉比对/document - 2026-07-29T091930.583.md` P2-B1R。

核心发现：原T-RPP-R1~R3的复放设计有根本缺陷——collector在复放阶段不激活
（activation=0），导致bundle无论权重多少都不传递电流。真正应该测试的是：
**在训练阶段本身，记录collector激活时bundle传递的电流，验证权重改变→电流改变**。

═══ 双层资格拆分（2026-09-06，外部实测反馈清单 §1/§8）═══

外部独立实测确认：机制层（Δw=+0.001052，+0.97%）稳定成立，效应量层
（下游电流积分 +0.0033% < 1% 阈值）稳定失败，3 个 hashseed 复现。
根因诊断（`_diag_rprec_effect_compression.py`）：总压缩 297× = 环节A
8.3×（Memristor 低 w 工作点 ΔG/G=0.117%）× 环节B 35.8×（训练期积分
稀释——活动窗口在前中期而权重增量后置，25% Δw 到 step 31500 才到位，
两窗口不相交）。即使消除环节B，效应上限 0.117% 仍低于阈值一个数量级
——**结构性不可达，非参数问题**（LIM-RPREC-READOUT-001，见
cell-cell/docs/degradation_registry.md）。

按反馈 §8 拆成两层，不合并宣告：
  test_rpp_r1_mechanism    机制资格：学习发生（Δw>0）        —— PASS
  test_rpp_r1_effect_size  效应量资格：下游 ≥1%（阈值不改）  —— xfail
                           （预期失败标记保留红色断言，不掩盖负结果；
                            修复须走独立设计轮，禁止调阈值/调参放行）
"""
import sys
sys.path.insert(0, '.')

import numpy as np
import pytest
from tss.relations.temporal_r_prec_plastic import RPrecCircuitT1Plastic

DT = 0.001
_TRAIN_STEPS = 50000


def _train_and_record_currents(circuit, steps: int, da_concentration: float):
    """训练并记录bundle传递的电流轨迹。"""
    da_neurons = list(circuit.da_neurons.values())
    da_v_trace = []
    bundle_current_trace = []

    for t in range(steps):
        inj_a = 1.0 if t < steps // 2 else 0.0
        inj_b = 1.0 if t >= steps // 3 else 0.0
        circuit.rprec_xi_a.step(inj_a, DT)
        circuit.rprec_xi_b.step(inj_b, DT)
        circuit.step_rprec_plastic(DT, da_concentration=da_concentration)

        # 记录bundle电流和DA膜电位
        currents = circuit.bundle_rprec_to_da.propagate()
        da_v = np.mean([n._membrane.voltage for n in da_neurons])

        bundle_current_trace.append(currents[0] if len(currents) > 0 else 0.0)
        da_v_trace.append(da_v)

    return np.array(bundle_current_trace), np.array(da_v_trace)


_CACHED = None


def _train_both_groups():
    """训练学习组与 frozen 基线组一次，机制层/效应量层共享测量（惰性缓存）。"""
    global _CACHED
    if _CACHED is not None:
        return _CACHED
    circuit_learned = RPrecCircuitT1Plastic()
    print("T-RPP-R1: 训练学习组...")
    w_before = circuit_learned.bundle_rprec_to_da.weight_matrix()[0][0]
    currents_learned, da_v_learned = _train_and_record_currents(
        circuit_learned, steps=_TRAIN_STEPS, da_concentration=0.5)
    w_after = circuit_learned.bundle_rprec_to_da.weight_matrix()[0][0]

    circuit_baseline = RPrecCircuitT1Plastic()
    circuit_baseline.bundle_rprec_to_da.config.learning_rule = "frozen"
    print("  训练基线组（frozen）...")
    currents_baseline, da_v_baseline = _train_and_record_currents(
        circuit_baseline, steps=_TRAIN_STEPS, da_concentration=0.5)

    _CACHED = dict(
        w_before=w_before, w_after=w_after,
        currents_learned=currents_learned, currents_baseline=currents_baseline,
        da_v_learned=da_v_learned, da_v_baseline=da_v_baseline,
    )
    return _CACHED


def test_rpp_r1_mechanism():
    """机制资格层：学习确实发生（Δw>0，DA 门控下）。当前状态：PASS。"""
    d = _train_both_groups()
    print(f"  权重变化: {d['w_before']:.6f} → {d['w_after']:.6f} "
          f"(Δw={d['w_after'] - d['w_before']:+.6f})")
    assert d['w_after'] > d['w_before'], (
        f"机制层: 学习应增加权重 ({d['w_after']} <= {d['w_before']})")
    print("✓ T-RPP-R1-MECH PASS: 学习机制成立（权重在 DA 门控下增长）")


@pytest.mark.xfail(
    strict=False,
    reason="LIM-RPREC-READOUT-001: 效应量结构性不可达——总压缩 297×"
           "（Memristor 工作点 8.3× × 训练期积分稀释 35.8×，活动窗口与"
           "权重增长窗口不相交），即使消除稀释上限 0.117% < 1% 阈值。"
           "见 _diag_rprec_effect_compression.py 与 degradation_registry。"
           "阈值不改、参数不调；修复须走独立读出结构设计轮。")
def test_rpp_r1_effect_size():
    """效应量资格层：下游电流积分应随学习增加 ≥1%。当前状态：预期失败。

    断言与阈值保持原样（不掩盖负结果，反馈 §8）；xfail 标记表达
    "已知未达标的已登记限制"，不是删除判据。
    """
    d = _train_both_groups()
    currents_learned, currents_baseline = d['currents_learned'], d['currents_baseline']
    current_learned_sum = np.sum(currents_learned)
    current_baseline_sum = np.sum(currents_baseline)
    n_active_learned = int(np.sum(currents_learned > 0))
    print(f"  Bundle电流积分: 学习组={current_learned_sum:.6f} vs "
          f"基线组={current_baseline_sum:.6f} "
          f"(相对差 {(current_learned_sum / current_baseline_sum - 1) * 100:.4f}%)")
    print(f"  Collector激活步数: 学习组={n_active_learned}")

    assert n_active_learned > 100, "效应量层前提: collector 需有激活"
    assert current_learned_sum > current_baseline_sum * 1.01, (
        f"效应量层: 学习组电流积分应大于基线组 1% "
        f"({current_learned_sum} <= {current_baseline_sum} * 1.01) "
        f"[LIM-RPREC-READOUT-001 已登记]")
    print("✓ T-RPP-R1-EFFECT PASS: 下游效应量达标")


def run():
    test_rpp_r1_mechanism()
    print()
    try:
        test_rpp_r1_effect_size()
        effect = "PASS"
    except AssertionError as e:
        effect = f"UNMET（已登记限制 LIM-RPREC-READOUT-001）"
        print(f"⚠ T-RPP-R1-EFFECT {effect}")
        print(f"  断言原文: {e}")
    print()
    print("=" * 60)
    print(f"P2-B1R 双层资格: MECH=PASS, EFFECT={effect}")
    print("（效应量未达标为已登记结构性限制，非本轮回归退化——"
          "见 degradation_registry LIM 节；机制层通过即本入口退出码 0）")


if __name__ == "__main__":
    run()
