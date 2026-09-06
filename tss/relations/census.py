"""tss.relations.census — 关系层独立账本。

TYPE:INFRA

方案依据：cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md
《批判二点9：census 隔离必须增加"关系层独立账本"》。

背景：关系生成元（r≺/r→/r_part）的神经元按既定策略**排除**出全局
`get_all_neurons()`（保护 T4.1 energy_per_neuron），但这只是暂时隔离，
不代表零能耗。若只统计 Bundle（进入 `get_all_bundles()`）而长期不统计
神经元，会产生物理账本缺口：E_relation = E_bundles + E_neurons，而全局
系统只看得见前一部分。

本模块提供独立于全局 census 的统计入口，供 T0（建立）与 T4（强制验收）
使用。T0 阶段没有任何关系生成元神经元/Bundle（Gate A 明确不新增关系
电路），因此这里只提供**工具函数**，由 T1~T4 在各自构造完成后调用，
传入自己持有的神经元/Bundle 列表——不修改 VariantCircuit，不新增
`get_relation_generator_neurons()`/`get_relation_generator_bundles()`
公开方法挂到 VariantCircuit 上（那样会改母本代码）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List


@dataclass
class RelationLayerCensus:
    """一次关系层账本快照。"""
    n_neurons: int = 0
    n_collectors: int = 0
    n_bundles: int = 0
    membrane_integrations_per_step: int = 0
    approx_stored_energy: float = 0.0
    baseline_n_neurons: int = 0
    baseline_n_bundles: int = 0

    @property
    def neuron_count_ratio(self) -> float:
        """相对原系统神经元数量的增量比例。"""
        if self.baseline_n_neurons <= 0:
            return 0.0
        return self.n_neurons / self.baseline_n_neurons

    @property
    def bundle_count_ratio(self) -> float:
        """相对原系统 Bundle 数量的增量比例。"""
        if self.baseline_n_bundles <= 0:
            return 0.0
        return self.n_bundles / self.baseline_n_bundles

    def report_lines(self) -> List[str]:
        return [
            f"关系中继神经元数（含 Collector）: {self.n_neurons}",
            f"  其中 Collector 数: {self.n_collectors}",
            f"新 Bundle 数: {self.n_bundles}",
            f"每步膜积分调用次数（估计，= 关系神经元数 × 每步 step() 次数）: "
            f"{self.membrane_integrations_per_step}",
            f"近似存储能量 (0.5*C*V^2 累加, 仅膜电容部分): "
            f"{self.approx_stored_energy:.6f}",
            f"相对原系统神经元数量增量: {self.neuron_count_ratio*100:.2f}% "
            f"({self.n_neurons}/{self.baseline_n_neurons})",
            f"相对原系统 Bundle 数量增量: {self.bundle_count_ratio*100:.2f}% "
            f"({self.n_bundles}/{self.baseline_n_bundles})",
            "注：排除全局 census 是暂时隔离，不是无能耗——以上数字即为"
            "关系层实际占用，供 T4 强制验收对照。",
        ]


def _neuron_stored_energy(neuron) -> float:
    """估算单个神经元膜电容存储能量 E=0.5*C*V^2（Capacitor: E=0.5*q^2/C）。

    防御式实现：不是所有神经元内部结构都暴露同名属性（多通道/复合神经元
    可能没有单一 `_membrane`），拿不到就记 0，不让统计整体失败。
    """
    membrane = getattr(neuron, "_membrane", None)
    if membrane is None:
        return 0.0
    capacitance = getattr(membrane, "capacitance", None)
    charge = getattr(membrane, "charge", None)
    if not capacitance or charge is None:
        return 0.0
    return 0.5 * (charge ** 2) / capacitance


def get_relation_generator_stats(
    relation_neurons: Iterable,
    relation_collectors: Iterable,
    relation_bundles: Iterable,
    baseline_circuit=None,
    steps_driven: int = 1,
) -> RelationLayerCensus:
    """计算一批关系层神经元/Collector/Bundle 的独立账本统计。

    Args:
        relation_neurons: 关系层全部中继神经元（含 ensemble 等，
            不含 collector；如无区分可传空列表，用 relation_collectors
            承载全部）。
        relation_collectors: 关系层 Collector 神经元。
        relation_bundles: 关系层新增 Bundle。
        baseline_circuit: 若提供，读取其 `get_all_neurons()` /
            `get_all_bundles()` 长度作为基线，用于计算相对增量比例；
            不提供则增量比例记 0（T0 阶段没有任何关系电路，可不传）。
        steps_driven: 若这批神经元在统计窗口内每步都会被 `step()` 调用
            一次，传入驱动步数用于估算总积分调用次数；默认 1（每步一次）。
    """
    neurons = list(relation_neurons)
    collectors = list(relation_collectors)
    bundles = list(relation_bundles)
    all_neurons = neurons + collectors

    approx_energy = sum(_neuron_stored_energy(n) for n in all_neurons)

    baseline_n_neurons = 0
    baseline_n_bundles = 0
    if baseline_circuit is not None:
        baseline_n_neurons = len(baseline_circuit.get_all_neurons())
        baseline_n_bundles = len(baseline_circuit.get_all_bundles())

    return RelationLayerCensus(
        n_neurons=len(all_neurons),
        n_collectors=len(collectors),
        n_bundles=len(bundles),
        membrane_integrations_per_step=len(all_neurons) * max(1, steps_driven),
        approx_stored_energy=approx_energy,
        baseline_n_neurons=baseline_n_neurons,
        baseline_n_bundles=baseline_n_bundles,
    )
