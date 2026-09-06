"""tss.relations.temporal_r_prec_t2 — T2: 基础时间关系生成元 r≺（第二条边 28↔23）。

TYPE:BIO

方案依据：P2-C0——建立第二个同等级R1原语（评判document - 2026-08-01T222037.115.md）。
冻结站点依据：`site_selection.py` `FROZEN_THERMAL_SITES["t2_chain"]` 的第二条边
  CENTER(28) ↔ NB2(23)，d=1.1612。

**拓扑修正（评判document - 2026-08-01T230002.273.md）**：
  T1 检测 28≺31（站点28先于站点31发放）
  T2 检测 28≺23（站点28先于站点23发放）

  两条关系都以节点28为**共同起点（先发放节点）**，构成分叉型组合：
       31
      ↗
  28
      ↘
       23
  而不是传递链 31→28→23。

  P2-C0报告曾将T1/T2描述为"A≺B ∧ B≺C（传递链）"——这是错误的理论定位。
  正确组合是"(28≺31) ∧ (28≺23)"即**共同源分叉型R2**。
  评判明确这仍是真正的关系-关系生成（同一次28发生共同生成两条指向不同目标的R1），
  只是关系-关系的组合语义不同于传递闭包。P2-C1应以此为出发点，研究两条共同源
  关系能否形成"共同源关系"（不是传递A≺C）。

所有参数（_TAU_FAST_STEPS/SLOW/R_LEAK/TRACE_GM/COLLECTOR_*/W_*）直接复用 T1 的标定常量。
RULES.md 强制三问：
  Q1 同 T1（trace+AND门重合检测，BIO机制相同）。
  Q2 复用既有站点对象（thermal_quantum_collectors["thermpt28_warm"]/["thermpt23_warm"]），
     不新建Neuron/SynapticBundle以外的组件。所有bundle_id加"t2_"前缀避免碰撞。
  Q3 参数全部复用 T1 已验证常量（temporal_r_prec.py），不重新标定。
"""

from __future__ import annotations

from typing import Dict, Tuple

from .site_selection import FROZEN_THERMAL_SITES
from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.circuit.bundle import BundleConfig, SynapticBundle
from nexus_v1.components.neuron import Neuron, NeuronConfig, ChannelConfig

DT = 0.001

# ── 复用 T1 的标定常量（temporal_r_prec.py 已验证，不重新标定） ──
_TAU_FAST_STEPS = 50
_TAU_SLOW_STEPS = 600
_R_LEAK_TRACE = 5.0
_TRACE_CAPACITANCE_FAST = _TAU_FAST_STEPS * DT / _R_LEAK_TRACE   # = 0.01
_TRACE_CAPACITANCE_SLOW = _TAU_SLOW_STEPS * DT / _R_LEAK_TRACE   # = 0.12
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

RELATION_TYPE_B_PREC_C_FAST = "r_prec.b_prec_c_fast"
RELATION_TYPE_B_PREC_C_SLOW = "r_prec.b_prec_c_slow"


def _trace_config(label: str, tau_steps: int, capacitance: float,
                  r_leak: float, region: int = 0x01) -> NeuronConfig:
    return NeuronConfig(
        neuron_id=f"t2_rprec_trace_{label}_{tau_steps}",
        region=region,
        spiking=False,
        capacitance=capacitance,
        r_leak=r_leak,
        inertia=1.0,
        channels=[ChannelConfig(name="default", v_threshold=0.0, gm=_TRACE_GM)],
    )


def _collector_config(label: str, region: int = 0x01) -> NeuronConfig:
    return NeuronConfig(
        neuron_id=f"t2_rprec_collector_{label}",
        region=region,
        spiking=True,
        v_peak=_COLLECTOR_V_PEAK,
        v_reset=0.077,
        b_adapt=0.01,
        tau_w=1.0,
        capacitance=_COLLECTOR_CAPACITANCE,
        r_leak=_COLLECTOR_R_LEAK,
        inertia=1.0,
        channels=[ChannelConfig(
            name="default",
            v_threshold=_COLLECTOR_THRESHOLD,
            gm=_COLLECTOR_GM,
            tau_gate=_COLLECTOR_TAU_GATE,
            reversal=1.0,
            sign=1.0,
        )],
    )


def _frozen_bundle(bundle_id: str, sources, targets, weight: float) -> SynapticBundle:
    cfg = BundleConfig(
        bundle_id=bundle_id,
        learning_rule="frozen",
        initial_weight=weight,
        weight_max=weight,
        synapse_gain=1.0,
        bundle_role="feedforward",
        remodel_cost_kappa=0.0,
    )
    return SynapticBundle(cfg, sources, targets)


class RPrecCircuitT2(VariantCircuit):
    """TYPE:BIO — 温感轨 T2 原型：在冻结集合 {28,23} 上叠加 r≺ 生成元（第二条边）。

    子类叠加，不修改母本 `VariantCircuit`（同 `RPrecCircuitT1` 先例）。
    站点：site_b=CENTER(28), site_c=NB2(23)，来自 FROZEN_THERMAL_SITES["t2_chain"]。
    """

    def __init__(self):
        super().__init__()

        chain = FROZEN_THERMAL_SITES["t2_chain"]
        # T2 使用链的第二条边：hub(28) → nb2(23)
        site_b = chain["hub"]        # 28，与 T1 的 site_a 是同一站点
        site_c = chain["order"][-1]  # 23，NB2

        self.rprec2_site_b = site_b
        self.rprec2_site_c = site_c

        xi_b = self.thermal_quantum_collectors[f"thermpt{site_b}_warm"]
        xi_c = self.thermal_quantum_collectors[f"thermpt{site_c}_warm"]
        self.rprec2_xi_b = xi_b
        self.rprec2_xi_c = xi_c

        # ── trace 神经元：b/c × fast/slow ──
        self.rprec2_trace_b_fast = Neuron(_trace_config(
            "b", _TAU_FAST_STEPS, _TRACE_CAPACITANCE_FAST, _R_LEAK_TRACE))
        self.rprec2_trace_b_slow = Neuron(_trace_config(
            "b", _TAU_SLOW_STEPS, _TRACE_CAPACITANCE_SLOW, _R_LEAK_TRACE))
        self.rprec2_trace_c_fast = Neuron(_trace_config(
            "c", _TAU_FAST_STEPS, _TRACE_CAPACITANCE_FAST, _R_LEAK_TRACE))
        self.rprec2_trace_c_slow = Neuron(_trace_config(
            "c", _TAU_SLOW_STEPS, _TRACE_CAPACITANCE_SLOW, _R_LEAK_TRACE))

        # ── collector：b≺c / c≺b × fast/slow ──
        self.rprec2_collector_b_prec_c_fast = Neuron(_collector_config("b_prec_c_fast"))
        self.rprec2_collector_b_prec_c_slow = Neuron(_collector_config("b_prec_c_slow"))
        self.rprec2_collector_c_prec_b_fast = Neuron(_collector_config("c_prec_b_fast"))
        self.rprec2_collector_c_prec_b_slow = Neuron(_collector_config("c_prec_b_slow"))

        # ── bundles: xi → trace ──
        self.bundles_rprec2_xi_to_trace = [
            _frozen_bundle("t2_rprec_xi_b_to_trace_fast", [xi_b], [self.rprec2_trace_b_fast], _W_XI_TO_TRACE),
            _frozen_bundle("t2_rprec_xi_b_to_trace_slow", [xi_b], [self.rprec2_trace_b_slow], _W_XI_TO_TRACE),
            _frozen_bundle("t2_rprec_xi_c_to_trace_fast", [xi_c], [self.rprec2_trace_c_fast], _W_XI_TO_TRACE),
            _frozen_bundle("t2_rprec_xi_c_to_trace_slow", [xi_c], [self.rprec2_trace_c_slow], _W_XI_TO_TRACE),
        ]

        # ── bundles: trace + raw xi → collector ──
        self.bundles_rprec2_to_collector = [
            _frozen_bundle("t2_rprec_trace_b_fast_to_col", [self.rprec2_trace_b_fast],
                           [self.rprec2_collector_b_prec_c_fast], _W_TRACE_TO_COLLECTOR),
            _frozen_bundle("t2_rprec_raw_xi_c_to_col_fast", [xi_c],
                           [self.rprec2_collector_b_prec_c_fast], _W_RAW_XI_TO_COLLECTOR),

            _frozen_bundle("t2_rprec_trace_b_slow_to_col", [self.rprec2_trace_b_slow],
                           [self.rprec2_collector_b_prec_c_slow], _W_TRACE_TO_COLLECTOR),
            _frozen_bundle("t2_rprec_raw_xi_c_to_col_slow", [xi_c],
                           [self.rprec2_collector_b_prec_c_slow], _W_RAW_XI_TO_COLLECTOR),

            _frozen_bundle("t2_rprec_trace_c_fast_to_col", [self.rprec2_trace_c_fast],
                           [self.rprec2_collector_c_prec_b_fast], _W_TRACE_TO_COLLECTOR),
            _frozen_bundle("t2_rprec_raw_xi_b_to_col_fast", [xi_b],
                           [self.rprec2_collector_c_prec_b_fast], _W_RAW_XI_TO_COLLECTOR),

            _frozen_bundle("t2_rprec_trace_c_slow_to_col", [self.rprec2_trace_c_slow],
                           [self.rprec2_collector_c_prec_b_slow], _W_TRACE_TO_COLLECTOR),
            _frozen_bundle("t2_rprec_raw_xi_b_to_col_slow", [xi_b],
                           [self.rprec2_collector_c_prec_b_slow], _W_RAW_XI_TO_COLLECTOR),
        ]

    def rprec2_relation_neurons(self):
        return [
            self.rprec2_trace_b_fast, self.rprec2_trace_b_slow,
            self.rprec2_trace_c_fast, self.rprec2_trace_c_slow,
        ]

    def rprec2_relation_collectors(self):
        return [
            self.rprec2_collector_b_prec_c_fast, self.rprec2_collector_b_prec_c_slow,
            self.rprec2_collector_c_prec_b_fast, self.rprec2_collector_c_prec_b_slow,
        ]

    def rprec2_relation_bundles(self):
        return self.bundles_rprec2_xi_to_trace + self.bundles_rprec2_to_collector

    def get_all_bundles(self):
        return super().get_all_bundles() + self.rprec2_relation_bundles()

    def step_rprec2(self, dt: float = DT):
        """传播一步 T2 r≺ 生成元链路（与 step_rprec() 完全对称）。"""
        for b in self.bundles_rprec2_xi_to_trace:
            currents = b.propagate()
            for i, tgt in enumerate(b.targets):
                tgt.step(currents[i] if i < len(currents) else 0.0, dt)

        collector_currents: dict = {}
        collector_objs: dict = {}
        for b in self.bundles_rprec2_to_collector:
            currents = b.propagate()
            for i, tgt in enumerate(b.targets):
                key = id(tgt)
                collector_currents[key] = collector_currents.get(key, 0.0) + \
                    (currents[i] if i < len(currents) else 0.0)
                collector_objs[key] = tgt

        for key, total_current in collector_currents.items():
            collector_objs[key].step(total_current, dt)


class RPrecCircuitT2Plastic(RPrecCircuitT2):
    """`RPrecCircuitT2` + 一条新增的可塑 bundle（T2 候选关系算子 ρ 的载体）。

    复用 T1Plastic（temporal_r_prec_plastic.py）相同的STDP常量，
    直接叠加 b≺c_fast → DA 的可塑链路。
    """

    def __init__(self):
        super().__init__()

        from nexus_v1.circuit.bundle import BundleConfig, SynapticBundle

        _INITIAL_WEIGHT = 0.1
        _WEIGHT_MAX = 0.3
        _STDP_LR = 0.005
        _ELIGIBILITY_TAU = 300.0
        _SYNAPSE_GAIN = 0.2
        _REMODEL_COST_KAPPA = 0.001

        da_list = list(self.da_neurons.values())
        cfg = BundleConfig(
            bundle_id="t2_rprec_b_prec_c_fast_to_da",
            learning_rule="stdp",
            use_eligibility_trace=True,
            eligibility_tau=_ELIGIBILITY_TAU,
            initial_weight=_INITIAL_WEIGHT,
            weight_max=_WEIGHT_MAX,
            stdp_lr=_STDP_LR,
            synapse_gain=_SYNAPSE_GAIN,
            bundle_role="feedforward",
            remodel_cost_kappa=_REMODEL_COST_KAPPA,
        )
        self.bundle_rprec2_to_da = SynapticBundle(
            cfg, [self.rprec2_collector_b_prec_c_fast], da_list)

    def step_rprec2_plastic(self, dt: float, da_concentration: float,
                            fill_fraction: float = 1.0) -> None:
        self.step_rprec2(dt)
        currents = self.bundle_rprec2_to_da.propagate()
        for i, tgt in enumerate(self.bundle_rprec2_to_da.targets):
            tgt.step(currents[i] if i < len(currents) else 0.0, dt)
        self.bundle_rprec2_to_da.learn(
            dt=dt, fill_fraction=fill_fraction, da_concentration=da_concentration)
        self.bundle_rprec2_to_da.compute_xin(dt)
