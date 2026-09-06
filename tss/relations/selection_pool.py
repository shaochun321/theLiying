"""tss.relations.selection_pool — S0-b：同构候选池（不接入竞争）。

TYPE:INFRA（候选池装配）+ BIO（复用T1的trace/collector机制）

方案依据：document - 2026-08-02T211341.334.md（S0-b范围裁定）。

评判裁定的S0-b边界（严格遵守，本文件不越界）：
  应当做：
    - 用同一个构造循环生成N条候选（不写N份手写代码块）；
    - 相同输入（同一对xi_a/xi_b）、相同输出目标类型、相同collector类型、
      相同连接模板；
    - 只允许trace_tau_steps等纯物理参数不同；
    - 候选ID用selection_contract.make_candidate_id()（无语义）。
  禁止加入（本文件完全不包含）：
    - LocalResourcePool分配；
    - 公共抑制；
    - winner字段；
    - DA/STDP竞争更新；
    - CPC评分；
    - 环境胜者切换；
    - 按索引打破平局。

关键产物不是"谁赢"，而是确认：候选池本身没有结构和执行顺序偏置，
且物理参数差异（tau_steps）能产生可测响应差异（见
test_selection_pool.py的T-S0B-3/4/5）。

RULES.md 强制三问：
  Q1 生物对应物：与temporal_r_prec.py Q1同一机制（trace+AND门重合检测，
     STDP eligibility trace同一物理原理，"资格窗口"部分）。本文件把
     该机制并联复制N份、只改变时间常数，类比同一群体神经元对同一输入
     用不同时间常数积分（如不同亚型的树突时间常数差异），不引入新BIO
     假设。
  Q2 物理结构：复用RPrecCircuitT1已有的xi_a/xi_b（site_a=28/site_b=31，
     FROZEN_THERMAL_SITES t1_pair），只新增N条trace+collector候选链，
     不修改T1本身的12条bundle，不新建站点。
  Q3 参数依据：candidate trace/collector的固定参数（capacitance公式/
     R_LEAK/GM/collector阈值等）全部复用temporal_r_prec.py已验证常量，
     只有tau_steps作为候选间的自由变量（DEFAULT_CANDIDATE_TAUS是纯数值
     占位，不代表标定结果，S0-c/d如需真实环境实验可另行标定）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from nexus_v1.components.neuron import Neuron, NeuronConfig, ChannelConfig
from nexus_v1.circuit.bundle import BundleConfig, SynapticBundle
from .temporal_r_prec import RPrecCircuitT1
from .selection_contract import make_candidate_id

DT = 0.001

# ── 候选trace/collector参数（复用T1标定值，不重新标定，见Q3） ──
_R_LEAK_TRACE = 5.0
_TRACE_GM = 20.0
_COLLECTOR_CAPACITANCE = 0.007
_COLLECTOR_R_LEAK = 1.5
_COLLECTOR_V_PEAK = 0.23
_COLLECTOR_THRESHOLD = 0.15
_COLLECTOR_GM = 3.0
_COLLECTOR_TAU_GATE = 2.0
_W_XI_TO_TRACE = 0.3
_W_TRACE_TO_COLLECTOR = 0.5
_W_RAW_XI_TO_COLLECTOR = 0.15

# 候选tau集合：纯数值占位（不是标定结果），S0-b只用于验证"tau不同→
# 响应窗口不同"这一物理事实，不代表任何环境适配的真实标定。
DEFAULT_CANDIDATE_TAUS: Tuple[int, ...] = (30, 100, 400)

# S0-bX1（评判document-2026-08-03T125656.528.md）：候选物理初始化种子，
# 与candidate_id（0,1,2...编号）刻意采用不同数值区间，避免视觉上让人
# 误以为physical_seed是candidate_id的派生值——两者概念独立（s_physical
# vs s_audit）。基数471030本身无任何语义（不是"谁该赢"的暗示），只是
# 一个远离0/1/2编号的任意起点，避免与candidate_id数值混淆。
_PHYSICAL_SEED_BASE = 471030
DEFAULT_PHYSICAL_SEEDS: Tuple[int, ...] = tuple(
    _PHYSICAL_SEED_BASE + i for i in range(8))  # 预留够用的默认池

# 同一候选内三条bundle的角色偏移量——让同一physical_seed在
# xi_to_trace/trace_to_collector/raw_xi_to_collector三条链路上产生
# 不同（但确定性、可复现）的扰动，避免三条bundle退化成同一份权重。
# 偏移量本身是结构角色标记（"这是第几条链路"），不是候选身份，无语义。
_SEED_OFFSET_XI_TO_TRACE = 0
_SEED_OFFSET_TRACE_TO_COLLECTOR = 100000
_SEED_OFFSET_RAW_XI_TO_COLLECTOR = 200000


def _candidate_trace_config(candidate_id: str, capacitance: float) -> NeuronConfig:
    """候选trace的NeuronConfig构造——neuron_id只含candidate_id（无语义），
    不含tau_steps本身（tau已体现在capacitance里，不需要在id里重复暴露
    "谁跑得快"这种语义信息给下游读取）。"""
    return NeuronConfig(
        neuron_id=f"sel_trace_{candidate_id}",
        region=0x01,
        spiking=False,
        capacitance=capacitance,
        r_leak=_R_LEAK_TRACE,
        inertia=1.0,
        channels=[ChannelConfig(name="default", v_threshold=0.0, gm=_TRACE_GM)],
    )


def _candidate_collector_config(candidate_id: str) -> NeuronConfig:
    return NeuronConfig(
        neuron_id=f"sel_collector_{candidate_id}",
        region=0x01,
        spiking=True,
        v_peak=_COLLECTOR_V_PEAK,
        v_reset=0.077,
        b_adapt=0.01,
        tau_w=1.0,
        capacitance=_COLLECTOR_CAPACITANCE,
        r_leak=_COLLECTOR_R_LEAK,
        inertia=1.0,
        channels=[ChannelConfig(
            name="default", v_threshold=_COLLECTOR_THRESHOLD, gm=_COLLECTOR_GM,
            tau_gate=_COLLECTOR_TAU_GATE, reversal=1.0, sign=1.0,
        )],
    )


def _frozen_bundle(bundle_id: str, sources, targets, weight: float,
                   physical_seed=None) -> SynapticBundle:
    """S0-bX1（评判document-2026-08-03T125656.528.md）：physical_seed默认
    None时完全走旧路径（种子取自bundle_id，兼容既有P2链路数值不变）。
    候选池显式传入physical_seed时，Memristor初始权重扰动改用该数值种子，
    与bundle_id（可能嵌入candidate_id等审计名称）完全脱钩。
    """
    cfg = BundleConfig(
        bundle_id=bundle_id, learning_rule="frozen",
        initial_weight=weight, weight_max=weight, synapse_gain=1.0,
        bundle_role="feedforward", remodel_cost_kappa=0.0,
        physical_seed=physical_seed,
    )
    return SynapticBundle(cfg, sources, targets)


@dataclass
class CandidateChain:
    """单个候选的物理链路引用集合（只读容器，不含选择逻辑）。

    S0-bX1新增physical_seed字段：候选的物理初始化种子，与candidate_id
    （审计/谱系身份）解耦——两者是不同的s_audit/s_physical概念（评判
    "种子需要分三种用途"）。physical_seed是无语义数值，不暗示预期胜负。
    """
    candidate_id: str
    tau_steps: int
    physical_seed: int
    trace: Neuron
    collector: Neuron
    bundle_xi_to_trace: SynapticBundle
    bundle_trace_to_collector: SynapticBundle
    bundle_raw_xi_to_collector: SynapticBundle


class SelectionPoolCircuit(RPrecCircuitT1):
    """T1（站点28≺31）+ N条同构候选链，同时读取相同的xi_a/xi_b。

    评判裁定的核心结构：所有候选共享同一对输入（RPrecCircuitT1的
    rprec_xi_a/rprec_xi_b），相同collector类型、相同连接模板（AND门：
    trace_i + raw_xi_b → collector_i），唯一的自由变量是tau_steps
    （通过capacitance换算，同temporal_r_prec.py的_TRACE_CAPACITANCE_FAST/
    SLOW换算公式：capacitance = tau_steps * dt / r_leak）。

    构造循环（评判要求"最好从同一个构造循环生成，避免手写代码产生结构
    偏置"）：__init__对taus列表做一次for循环，每次迭代产生的
    CandidateChain结构完全相同，只有capacitance数值不同——不存在
    if candidate_id == "candidate_0": ... 这类分支代码。

    S0-bX1（评判document-2026-08-03T125656.528.md）：新增physical_seeds
    参数，与candidate_id完全解耦——candidate_id只用于查找/报告/谱系记录
    （s_audit），physical_seeds只决定Memristor初始扰动（s_physical）。
    两者在构造循环里各自独立传入，bundle_id字符串不再是唯一的扰动来源。
    """

    def __init__(self, taus: Tuple[int, ...] = DEFAULT_CANDIDATE_TAUS,
                physical_seeds: Tuple[int, ...] = None):
        super().__init__()

        if physical_seeds is None:
            physical_seeds = DEFAULT_PHYSICAL_SEEDS[:len(taus)]
        if len(physical_seeds) < len(taus):
            raise ValueError(
                f"physical_seeds长度({len(physical_seeds)})不足以覆盖"
                f"taus长度({len(taus)})")

        xi_a = self.rprec_xi_a  # 站点28（先发生）
        xi_b = self.rprec_xi_b  # 站点31（后发生，AND门的raw输入）

        self.candidates: List[CandidateChain] = []
        # ── 唯一的构造循环：每次迭代生成结构完全相同的候选，只有
        # capacitance（对应tau_steps）和physical_seed（对应扰动种子）
        # 不同——两者都通过参数列表传入，不从candidate_id派生 ──
        for i, tau_steps in enumerate(taus):
            cid = make_candidate_id(i)
            p_seed = physical_seeds[i]
            capacitance = tau_steps * DT / _R_LEAK_TRACE

            trace = Neuron(_candidate_trace_config(cid, capacitance))
            collector = Neuron(_candidate_collector_config(cid))

            b_xi_to_trace = _frozen_bundle(
                f"sel_{cid}_xi_a_to_trace", [xi_a], [trace], _W_XI_TO_TRACE,
                physical_seed=p_seed + _SEED_OFFSET_XI_TO_TRACE)
            b_trace_to_col = _frozen_bundle(
                f"sel_{cid}_trace_to_col", [trace], [collector],
                _W_TRACE_TO_COLLECTOR,
                physical_seed=p_seed + _SEED_OFFSET_TRACE_TO_COLLECTOR)
            b_raw_xi_to_col = _frozen_bundle(
                f"sel_{cid}_raw_xi_b_to_col", [xi_b], [collector],
                _W_RAW_XI_TO_COLLECTOR,
                physical_seed=p_seed + _SEED_OFFSET_RAW_XI_TO_COLLECTOR)

            self.candidates.append(CandidateChain(
                candidate_id=cid, tau_steps=tau_steps, physical_seed=p_seed,
                trace=trace, collector=collector,
                bundle_xi_to_trace=b_xi_to_trace,
                bundle_trace_to_collector=b_trace_to_col,
                bundle_raw_xi_to_collector=b_raw_xi_to_col,
            ))

    def candidate_bundles(self) -> List[SynapticBundle]:
        bundles = []
        for c in self.candidates:
            bundles.extend([c.bundle_xi_to_trace, c.bundle_trace_to_collector,
                            c.bundle_raw_xi_to_collector])
        return bundles

    def get_all_bundles(self):
        return super().get_all_bundles() + self.candidate_bundles()

    def step_candidates(self, dt: float = DT) -> None:
        """传播一步全部候选链路（禁止按候选ID做任何分支——评判裁定的
        "禁止按索引打破平局"在结构层面的体现：本方法对每个候选执行
        完全相同的代码路径，遍历顺序不影响每个候选各自的独立状态更新
        （各candidate.trace/collector只依赖自己的输入，不共享状态，
        故遍历顺序在S0-b阶段不产生任何交叉影响——这与S0-c引入共享
        资源池后"遍历顺序才可能产生交叉影响"的情况不同）。
        """
        for c in self.candidates:
            trace_current = c.bundle_xi_to_trace.propagate()
            c.trace.step(trace_current[0] if trace_current else 0.0, dt)

            col_current = 0.0
            for b in (c.bundle_trace_to_collector, c.bundle_raw_xi_to_collector):
                currents = b.propagate()
                col_current += (currents[0] if currents else 0.0)
            c.collector.step(col_current, dt)
