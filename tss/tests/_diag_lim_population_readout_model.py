"""_diag_lim_population_readout_model — LIM-RPREC-READOUT-001 独立设计轮
第一环：多束并行读出的标度律实测（EXP-LIM-01）。

TYPE:INFRA（diagnostic，不被 pytest 收集）

设计轮依据：degradation_registry LIM-RPREC-READOUT-001 解除路径候选①
"多束并行读出（√N 信噪比增益，参照 DEG-016 种群编码分析）" + 用户裁定
2026-09-07（方向=多束并行读出；禁止调阈值）。**模型先行纪律**：先实测
标度律，预测达标才建生产原型；预测不达标则定量收口，不堆结构。

## 中心问题：两个失败判据对并行束数 N 的标度不同

LIM 有两层失败判据，解除必须两层都达标：

  判据Ⅰ（test_r_prec_replay_simple 效应量层）：
    learned vs frozen 的**通路自身电流积分相对差** ≥ 1%。
    解析预判：N 条同源同参可塑束，pre/post/DA 全同 ⇒ 每束 Δw 相同 ⇒
    分子分母同乘 N ⇒ **N-不变**。上限被环节A钉死在 ΔG/G≈0.117%。

  判据Ⅱ（test_r_prec_replay R2 阻断距离层）：
    D(Y_learned, Y_blocked) ≥ 0.01（Y=下游响应；blocked=移除通路）。
    解析预判：距离≈通路对下游的绝对贡献，随 N 近线性（DA 饱和前）。

本脚本以 N∈{1,4} 的 plastic/frozen 孪生对**实测验证两个预判**，并给出
判据Ⅱ的 N* 外推与 DA 线性区检查。若判据Ⅰ的 N-不变性被证实，则多束
方向**结构上不能完全解除 LIM**（只能解除Ⅱ层）——这正是模型先行要在
建 132 束原型**之前**发现的事实。

## 物理纪律

  - 克隆束显式传 physical_seed=93000（S0-bX1：bundle_id 哈希不得污染
    物理；全部克隆束同 seed ⇒ 物理全同，标度测量干净）
  - 全部参数继承 temporal_r_prec_plastic 的 EXP-P2B1-001 常量，零新数字
  - 本脚本是测量诊断：N 束叠加只存在于脚本内实验电路，不动生产文件

入口：PYTHONIOENCODING=utf-8 python -m tss.tests._diag_lim_population_readout_model
（4×50k 步训练，约 6~10 分钟）
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np

from nexus_v1.circuit.bundle import BundleConfig, SynapticBundle
from tss.relations.temporal_r_prec_plastic import (
    RPrecCircuitT1Plastic,
    _INITIAL_WEIGHT, _WEIGHT_MAX, _STDP_LR, _ELIGIBILITY_TAU,
    _SYNAPSE_GAIN, _REMODEL_COST_KAPPA,
)

DT = 0.001
TRAIN_STEPS = 50000          # 与压缩诊断同长（da_ema_tau=50000 教训：不缩短）
_POP_PHYSICAL_SEED = 93000   # S0-bX1：克隆束显式共用 seed
_R2_MEASURED_DISTANCE = 0.000076   # LIM 登记的 R2 实测（N=1），外推基点
_R2_THRESHOLD = 0.01
_EFFECT_THRESHOLD = 0.01     # 判据Ⅰ的 1%（原样引用，不调）


class _PopulationReadoutCircuit(RPrecCircuitT1Plastic):
    """实验电路：在既有 1 条可塑束之外再克隆 N-1 条同参可塑束（合计 N）。

    仅供本诊断测量标度律；生产原型是否立项由本脚本结论决定。
    """

    def __init__(self, n_bundles: int):
        super().__init__()
        da_list = list(self.da_neurons.values())
        self.population_bundles = [self.bundle_rprec_to_da]
        for k in range(1, n_bundles):
            cfg = BundleConfig(
                bundle_id=f"rprec_a_prec_b_fast_to_da_pop{k}",
                learning_rule="stdp",
                use_eligibility_trace=True,
                eligibility_tau=_ELIGIBILITY_TAU,
                initial_weight=_INITIAL_WEIGHT,
                weight_max=_WEIGHT_MAX,
                stdp_lr=_STDP_LR,
                synapse_gain=_SYNAPSE_GAIN,
                bundle_role="feedforward",
                remodel_cost_kappa=_REMODEL_COST_KAPPA,
                physical_seed=_POP_PHYSICAL_SEED,
            )
            self.population_bundles.append(SynapticBundle(
                cfg, [self.rprec_collector_a_prec_b_fast], da_list))

    def step_population(self, dt: float, da_concentration: float) -> float:
        """父类检测传播 + 全部 N 条束传播/学习。返回本步通路总电流。"""
        self.step_rprec(dt)
        total = 0.0
        for b in self.population_bundles:
            currents = b.propagate()
            for i, tgt in enumerate(b.targets):
                tgt.step(currents[i] if i < len(currents) else 0.0, dt)
            total += sum(currents)
            b.learn(dt=dt, fill_fraction=1.0,
                    da_concentration=da_concentration)
            b.compute_xin(dt)
        return total


def _train_population(n_bundles: int, frozen: bool):
    """训练一个 N 束电路；返回 (通路电流积分, DA 末段活动均值, w 终值)。"""
    c = _PopulationReadoutCircuit(n_bundles)
    if frozen:
        for b in c.population_bundles:
            b.config.learning_rule = "frozen"
    path_integral = 0.0
    da_tail = []
    tail_from = int(TRAIN_STEPS * 0.9)
    da_list = list(c.da_neurons.values())
    for t in range(TRAIN_STEPS):
        inj_a = 1.0 if t < TRAIN_STEPS // 2 else 0.0
        inj_b = 1.0 if t >= TRAIN_STEPS // 3 else 0.0
        c.rprec_xi_a.step(inj_a, DT)
        c.rprec_xi_b.step(inj_b, DT)
        path_integral += c.step_population(DT, da_concentration=0.5)
        if t >= tail_from:
            da_tail.append(float(np.mean([n.activation for n in da_list])))
    w_final = c.population_bundles[0].weight_matrix()[0][0]
    return path_integral, float(np.mean(da_tail)), w_final


def main():
    print("=" * 72)
    print("EXP-LIM-01 多束并行读出标度律实测（模型先行，4×50k 步）")
    print("=" * 72)

    results = {}
    for n in (1, 4):
        print(f"\n训练 N={n} plastic ...")
        i_learn, da_l, w1 = _train_population(n, frozen=False)
        print(f"训练 N={n} frozen twin ...")
        i_base, da_b, w0 = _train_population(n, frozen=True)
        rel = (i_learn - i_base) / i_base if i_base else float("nan")
        results[n] = {"i_learn": i_learn, "i_base": i_base, "rel": rel,
                      "da_learn": da_l, "w0": w0, "w1": w1}
        print(f"  N={n}: 通路积分 learned={i_learn:.6f} frozen={i_base:.6f}"
              f"  相对差={rel * 100:.4f}%  Δw={w1 - w0:+.6f}"
              f"  DA末段活动={da_l:.6f}")

    r1, r4 = results[1], results[4]

    # ── 判据Ⅰ：N-不变性 ──
    print("\n── 判据Ⅰ（效应量层，1% 相对阈值）──")
    print(f"  N=1 相对效应 {r1['rel'] * 100:.4f}%   N=4 相对效应 "
          f"{r4['rel'] * 100:.4f}%")
    invariant = (abs(r4["rel"] - r1["rel"])
                 < max(abs(r1["rel"]), 1e-12) * 0.5)   # 半量级内视为不变
    print(f"  N-不变性: {'证实' if invariant else '未证实（出现 N 依赖！）'}")
    print(f"  达标判定: N=4 相对效应 {r4['rel'] * 100:.4f}% "
          f"{'≥' if r4['rel'] >= _EFFECT_THRESHOLD else '<'} 1% ⇒ "
          f"{'达标' if r4['rel'] >= _EFFECT_THRESHOLD else '不达标'}")

    # ── 判据Ⅱ：绝对贡献线性 + DA 线性区 ──
    print("\n── 判据Ⅱ（阻断距离层，0.01 绝对阈值）──")
    abs_scale = (r4["i_base"] / r1["i_base"]) if r1["i_base"] else float("nan")
    da_scale = (r4["da_learn"] / r1["da_learn"]) if r1["da_learn"] else float("nan")
    print(f"  通路绝对积分标度 (N=4/N=1): {abs_scale:.3f}（线性预期 4.0）")
    print(f"  DA 末段活动标度 (N=4/N=1): {da_scale:.3f}"
          f"（≈4 线性区 / <4 饱和压缩）")
    n_star = int(np.ceil(_R2_THRESHOLD / _R2_MEASURED_DISTANCE))
    print(f"  线性外推 N* = ceil(0.01 / {_R2_MEASURED_DISTANCE}) = {n_star}"
          "（以 LIM 登记 R2 实测为基点；DA 非线性会进一步抬高）")

    # ── 结论 ──
    print("\n" + "=" * 72)
    print("结论（设计轮判定输入）")
    print("=" * 72)
    if invariant and r4["rel"] < _EFFECT_THRESHOLD:
        print("  1. 判据Ⅰ N-不变性证实：多束并行读出**结构上不能**把效应量层")
        print(f"     推过 1%（上限=环节A 的 ΔG/G≈0.117%，与 N 无关）。")
        print(f"  2. 判据Ⅱ 随 N 近线性（实测 {abs_scale:.2f}×@N=4），但达标需")
        print(f"     N*≈{n_star} 束——且只解除两层判据中的一层。")
        print("  ⇒ 多束方向不能完全解除 LIM：按方案 D.3 FAIL 分支定量收口，")
        print("     LIM 条目补新增定量（√N 候选①已量化为不充分），")
        print("     不建 N* 束生产原型（模型先行避免了无效结构堆叠）。")
    else:
        print("  标度律与解析预判不符——先解释偏差再决定是否立项原型")
        print(f"  （invariant={invariant}, rel@N4={r4['rel']:.6f}）。")
    return results


if __name__ == "__main__":
    main()
