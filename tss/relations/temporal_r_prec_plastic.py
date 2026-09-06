"""tss.relations.temporal_r_prec_plastic — P2-B1：r≺ 关系载体的学习资格验证。

TYPE:BIO

方案依据：`cell-cell/交叉比对/document - 2026-07-28T185716.294.md`（P2-B1 三步走
规格）+ `cell-cell/交叉比对/评判_反馈自然单位概念修正_2026-07-20.md`（P2-B 核心
问题："自然单位化是否真的有用"）。

背景：`temporal_r_prec.py` 的 `RPrecCircuitT1` 已经是真实电路，把两个 D1
occurrence（站点 28/31 的 `thermal_quantum_collectors`）接入一个时序先后
检测器（trace + collector，AND 门重合判据），**但全部 12 条 bundle 都是
`frozen`**——只做检测，从未做过学习（`temporal_r_prec.py` 模块 docstring 原文：
"这里只做检测不做学习"）。`test_basegen_thermal_t1.py` 的 T-TRP-2 断言"驱动
300 步后权重逐项不变"，故本模块**不修改** `RPrecCircuitT1`/`temporal_r_prec.py`
本身（会破坏该断言），改用子类叠加**新增**一条 bundle。

**DEG-016 教训（重要）**：不能假设"STDP 应该没问题"。本模块的学习资格必须在
独立、可控的驱动条件下真实测得（`test_r_prec_plastic_learning.py`），不援引
其他电路（如 `bundles_relay_to_da`）STDP works 过就默认这里也行——只是复用
其**已验证的参数常量**（避免裸填数字），机制本身必须重新验证。

RULES.md 强制三问：

  Q1 生物对应物：
    与 `bundles_relay_to_da`（`variant_adapter.py:3803-3828`）同一三因子
    eligibility-trace Hebbian 机制（Izhikevich 2007 Cereb Cortex 17:2443；
    Gerstner et al. 2018 Nat Neurosci 21:555）——DA 门控 LTP，无 DA 时只有
    LTD+代谢衰减，不发生盲目增强。这里应用到"时序先后检测通路"：collector
    发放（检测到 a≺b）且 DA 为正（代表 VTA 广播的行为相关性/显著性信号）时，
    该检测通路发生 LTP，代表"这个时序关系被行为相关信号确认/巩固"——与
    `bundles_relay_to_da`"热趋近方向被确认后 LTP"是同一范畴的机制，只是
    上游信号从"温度差"换成"时序先后检测结果"。

  Q2 物理结构：
    Sources → SynapticBundle → Targets，全部复用已有对象：
    `RPrecCircuitT1.rprec_collector_a_prec_b_fast`（既有 spiking collector，
    不新建）→ [新 SynapticBundle，`use_eligibility_trace=True`] →
    `self.da_neurons`（既有 DA 神经元池，`variant_adapter.py:972`，不新建）。
    **只新增 1 条 bundle**，不修改 `RPrecCircuitT1` 现有 12 条 frozen bundle，
    不新建 Neuron。

  Q3 参数依据：
    `initial_weight`/`weight_max`/`stdp_lr`/`eligibility_tau`/`synapse_gain`
    **直接复用** `bundles_relay_to_da` 已验证的常量
    （`variant_adapter.py:3820-3823`：0.1/0.3/0.005/300.0/0.2）——因为是
    结构上同一种三因子 STDP 机制（同 Q1），不新造数字。`remodel_cost_kappa`
    同样复用该处的 0.001。
"""

from __future__ import annotations

from nexus_v1.circuit.bundle import BundleConfig, SynapticBundle
from .temporal_r_prec import RPrecCircuitT1

# EXP-P2B1-001：直接复用 bundles_relay_to_da 已验证的三因子STDP常量
# （variant_adapter.py:3820-3823），不新造数字（见模块文档 Q3）。
_INITIAL_WEIGHT = 0.1
_WEIGHT_MAX = 0.3
_STDP_LR = 0.005
_ELIGIBILITY_TAU = 300.0
_SYNAPSE_GAIN = 0.2
_REMODEL_COST_KAPPA = 0.001


class RPrecCircuitT1Plastic(RPrecCircuitT1):
    """`RPrecCircuitT1` + 一条新增的可塑 bundle（候选关系算子 ρ 的载体）。

    子类叠加，不修改 `RPrecCircuitT1`/`temporal_r_prec.py` 本身（同该类自身
    "子类叠加不改母本"的既定模式，见 `temporal_r_prec.py` 类文档）。
    """

    def __init__(self):
        super().__init__()

        da_list = list(self.da_neurons.values())
        cfg = BundleConfig(
            bundle_id="rprec_a_prec_b_fast_to_da",
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
        # 候选关系算子ρ的具体载体：a≺b 检测输出 → DA（STDP 可塑）。
        self.bundle_rprec_to_da = SynapticBundle(
            cfg, [self.rprec_collector_a_prec_b_fast], da_list)

    def step_rprec_plastic(
        self, dt: float, da_concentration: float, fill_fraction: float = 1.0,
    ) -> None:
        """先跑父类的检测传播（`step_rprec`，全部 frozen，不受影响），再
        传播+学习新增的可塑 bundle。

        `da_concentration`/`fill_fraction` 由调用方显式传入（独立驱动，
        不依赖 `circuit.step()` 主循环或 DEG-016 可能受影响的完整趋热行为
        回路——同 P2-A3 的隔离验证方法论）。
        """
        self.step_rprec(dt)

        currents = self.bundle_rprec_to_da.propagate()
        for i, tgt in enumerate(self.bundle_rprec_to_da.targets):
            tgt.step(currents[i] if i < len(currents) else 0.0, dt)

        self.bundle_rprec_to_da.learn(
            dt=dt, fill_fraction=fill_fraction, da_concentration=da_concentration)
        self.bundle_rprec_to_da.compute_xin(dt)
