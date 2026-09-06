"""tss.relations.temporal_r_prec_t3 — T3: 基础时间关系生成元 r≺（28≺21）。

TYPE:BIO

方案依据：document - 2026-08-03T220325.594.md（评判裁定构造28≺21）+
document - 2026-08-03T212639.904.md（三问审计框架）。
冻结站点依据：`nexus_v1/tests/test_tss3a_theta_distance_audit.py`
（TSS-3a距离-延迟审计，commit 1a79fa6）实测结果——21号点在5组
physical_seed下Δt=328~353步（相对抖动7%），50<Δt<600全覆盖T1 slow窗口。

Q1 生物对应物：同T1（trace+AND门重合检测，BIO机制相同——Willis &
   Coggeshall 2004脊髓背角WDR神经元时序会聚），不依赖STDP/DA。
Q2 为什么是21：TSS-3a实测5个候选站点(31/15/12/21/24)的onset延迟后，
   21是除T1现有目标31外相对抖动最小、且距slow窗口上限(600步)有余量
   的站点（328~353，极差25步<Δt本身）。12被排除（Δt≥600超出T1适用域，
   延迟异常来源未钉死）；24留作局部对照，本轮不同时构造（评判明确禁止）。
   **21号点在几何上属于TSS-2a审计中radius=2.0~3.0之间的候选集合，
   本文件不读取该归属做任何运行时判断——选点理由完全来自TSS-3a的
   实测Δt/W_Θ覆盖判据，见上，不引用N_Δ或任何集合成员常量。**
Q3 参数依据：与T2同例，全部复用T1已验证常量（temporal_r_prec.py），
   不重新标定。TSS-3a已确认21号点的Δt落在T1 slow窗口(0<Δt<600)内，
   满足"覆盖则直接复用"的停止条件1。

所有参数（_TAU_FAST_STEPS/SLOW/R_LEAK/TRACE_GM/COLLECTOR_*/W_*）
直接复用 T1 的标定常量，与temporal_r_prec_t2.py完全一致的做法。

命名：站点28（源）本文件称site_a（与T1一致，同一物理站点），
站点21称site_d（沿用T1=b/T2=c的字母序，避免与T2的site_b/site_c混淆）。

不新建学习机制。本文件不含Plastic子类——评判本轮边界未要求STDP/DA
链路，留待后续需要时按T2Plastic同例追加。
"""

from __future__ import annotations

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.circuit.bundle import BundleConfig, SynapticBundle
from nexus_v1.components.neuron import Neuron, NeuronConfig, ChannelConfig

DT = 0.001

# ── 站点：字面冻结，来源见模块文档Q2。不做运行时集合归属判断。 ──
SITE_SOURCE = 28   # 与T1/T2共享的源站点（同一物理collector对象）
SITE_TARGET = 21   # TSS-3a实测选定目标

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

# EXP-T3-02 失败记录（2026-08-03）— 参数已撤回，不留在代码里。
# 三条件诊断结果（T1原值下）：
#   V_trace=0.024, V_raw=0.082, V_both=0.105, θ=0.23
#   统一放大区间倒置（lo=2.415 > hi=2.233），不可统一缩放。
# 尝试独立缩放 s_trace=5.3/s_raw=1.6 后验证失败：
#   V_trace(only)=0.209 > 0.8θ=0.184  → trace单路已超阈，AND选择性破坏
#   V_both=0.209 ≈ V_trace  → collector进入饱和区，叠加无增量
# 结论：当前MOSFET动力学下，在T1原值权重区附近不存在同时满足
#   AND选择性与双路触发的工作区；下一步应先分析collector在该动力学
#   下是否存在满足三条件的参数空间，而非继续猜权重。
# T3当前冻结状态：拓扑已建、父Occurrence链通过、AND选择性尚未成立。

RELATION_TYPE_A_PREC_D_FAST = "r_prec.a_prec_d_fast"
RELATION_TYPE_A_PREC_D_SLOW = "r_prec.a_prec_d_slow"


def _trace_config(label: str, tau_steps: int, capacitance: float,
                  r_leak: float, region: int = 0x01) -> NeuronConfig:
    return NeuronConfig(
        neuron_id=f"t3_rprec_trace_{label}_{tau_steps}",
        region=region,
        spiking=False,
        capacitance=capacitance,
        r_leak=r_leak,
        inertia=1.0,
        channels=[ChannelConfig(name="default", v_threshold=0.0, gm=_TRACE_GM)],
    )


def _collector_config(label: str, region: int = 0x01) -> NeuronConfig:
    return NeuronConfig(
        neuron_id=f"t3_rprec_collector_{label}",
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


class RPrecCircuitT3(VariantCircuit):
    """TYPE:BIO — 温感轨 T3 原型：在冻结集合 {28,21} 上叠加 r≺ 生成元。

    子类叠加，不修改母本 `VariantCircuit`（同 `RPrecCircuitT1`/T2 先例）。
    站点：SITE_SOURCE(28) → SITE_TARGET(21)，选点依据见模块文档Q2。
    """

    def __init__(self):
        super().__init__()

        self.rprec3_site_a = SITE_SOURCE
        self.rprec3_site_d = SITE_TARGET

        xi_a = self.thermal_quantum_collectors[f"thermpt{SITE_SOURCE}_warm"]
        xi_d = self.thermal_quantum_collectors[f"thermpt{SITE_TARGET}_warm"]
        self.rprec3_xi_a = xi_a
        self.rprec3_xi_d = xi_d

        # ── trace 神经元：a/d × fast/slow ──
        self.rprec3_trace_a_fast = Neuron(_trace_config(
            "a", _TAU_FAST_STEPS, _TRACE_CAPACITANCE_FAST, _R_LEAK_TRACE))
        self.rprec3_trace_a_slow = Neuron(_trace_config(
            "a", _TAU_SLOW_STEPS, _TRACE_CAPACITANCE_SLOW, _R_LEAK_TRACE))
        self.rprec3_trace_d_fast = Neuron(_trace_config(
            "d", _TAU_FAST_STEPS, _TRACE_CAPACITANCE_FAST, _R_LEAK_TRACE))
        self.rprec3_trace_d_slow = Neuron(_trace_config(
            "d", _TAU_SLOW_STEPS, _TRACE_CAPACITANCE_SLOW, _R_LEAK_TRACE))

        # ── collector：a≺d / d≺a × fast/slow ──
        self.rprec3_collector_a_prec_d_fast = Neuron(_collector_config("a_prec_d_fast"))
        self.rprec3_collector_a_prec_d_slow = Neuron(_collector_config("a_prec_d_slow"))
        self.rprec3_collector_d_prec_a_fast = Neuron(_collector_config("d_prec_a_fast"))
        self.rprec3_collector_d_prec_a_slow = Neuron(_collector_config("d_prec_a_slow"))

        # ── bundles: xi → trace ──
        self.bundles_rprec3_xi_to_trace = [
            _frozen_bundle("t3_rprec_xi_a_to_trace_fast", [xi_a], [self.rprec3_trace_a_fast], _W_XI_TO_TRACE),
            _frozen_bundle("t3_rprec_xi_a_to_trace_slow", [xi_a], [self.rprec3_trace_a_slow], _W_XI_TO_TRACE),
            _frozen_bundle("t3_rprec_xi_d_to_trace_fast", [xi_d], [self.rprec3_trace_d_fast], _W_XI_TO_TRACE),
            _frozen_bundle("t3_rprec_xi_d_to_trace_slow", [xi_d], [self.rprec3_trace_d_slow], _W_XI_TO_TRACE),
        ]

        # ── bundles: trace + raw xi → collector ──
        self.bundles_rprec3_to_collector = [
            _frozen_bundle("t3_rprec_trace_a_fast_to_col", [self.rprec3_trace_a_fast],
                           [self.rprec3_collector_a_prec_d_fast], _W_TRACE_TO_COLLECTOR),
            _frozen_bundle("t3_rprec_raw_xi_d_to_col_fast", [xi_d],
                           [self.rprec3_collector_a_prec_d_fast], _W_RAW_XI_TO_COLLECTOR),

            _frozen_bundle("t3_rprec_trace_a_slow_to_col", [self.rprec3_trace_a_slow],
                           [self.rprec3_collector_a_prec_d_slow], _W_TRACE_TO_COLLECTOR),
            _frozen_bundle("t3_rprec_raw_xi_d_to_col_slow", [xi_d],
                           [self.rprec3_collector_a_prec_d_slow], _W_RAW_XI_TO_COLLECTOR),

            _frozen_bundle("t3_rprec_trace_d_fast_to_col", [self.rprec3_trace_d_fast],
                           [self.rprec3_collector_d_prec_a_fast], _W_TRACE_TO_COLLECTOR),
            _frozen_bundle("t3_rprec_raw_xi_a_to_col_fast", [xi_a],
                           [self.rprec3_collector_d_prec_a_fast], _W_RAW_XI_TO_COLLECTOR),

            _frozen_bundle("t3_rprec_trace_d_slow_to_col", [self.rprec3_trace_d_slow],
                           [self.rprec3_collector_d_prec_a_slow], _W_TRACE_TO_COLLECTOR),
            _frozen_bundle("t3_rprec_raw_xi_a_to_col_slow", [xi_a],
                           [self.rprec3_collector_d_prec_a_slow], _W_RAW_XI_TO_COLLECTOR),
        ]

    def rprec3_relation_neurons(self):
        return [
            self.rprec3_trace_a_fast, self.rprec3_trace_a_slow,
            self.rprec3_trace_d_fast, self.rprec3_trace_d_slow,
        ]

    def rprec3_relation_collectors(self):
        return [
            self.rprec3_collector_a_prec_d_fast, self.rprec3_collector_a_prec_d_slow,
            self.rprec3_collector_d_prec_a_fast, self.rprec3_collector_d_prec_a_slow,
        ]

    def rprec3_relation_bundles(self):
        return self.bundles_rprec3_xi_to_trace + self.bundles_rprec3_to_collector

    def get_all_bundles(self):
        return super().get_all_bundles() + self.rprec3_relation_bundles()

    def step_rprec3(self, dt: float = DT):
        """传播一步 T3 r≺ 生成元链路（与 step_rprec()/step_rprec2() 完全对称）。"""
        for b in self.bundles_rprec3_xi_to_trace:
            currents = b.propagate()
            for i, tgt in enumerate(b.targets):
                tgt.step(currents[i] if i < len(currents) else 0.0, dt)

        collector_currents: dict = {}
        collector_objs: dict = {}
        for b in self.bundles_rprec3_to_collector:
            currents = b.propagate()
            for i, tgt in enumerate(b.targets):
                key = id(tgt)
                collector_currents[key] = collector_currents.get(key, 0.0) + \
                    (currents[i] if i < len(currents) else 0.0)
                collector_objs[key] = tgt

        for key, total_current in collector_currents.items():
            collector_objs[key].step(total_current, dt)
