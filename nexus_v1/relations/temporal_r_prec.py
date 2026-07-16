"""nexus_v1.relations.temporal_r_prec — T1: 基础时间关系生成元 r≺（双向历史痕迹耦合）。

TYPE:BIO

方案依据：cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md
《T1 —— r≺ 时间关系（二元，最小支撑）》。Gate B：可直接按方案设计进入，
不需要像 T2/T3 那样先出独立设计报告。

═══════════════════════════════════════════════════════════════════════
强制三问（每个新 Bundle 动手前必须先答，见 RULES.md / 方案约束7）
═══════════════════════════════════════════════════════════════════════

Q1. 生物对应物是什么？
    BIO: 历史痕迹 + 当前信号的重合检测，与本项目已有的 STDP eligibility
    trace 机制（`circuit/bundle.py` 三因子学习：`E(t)` 是"前突触活动的
    leaky capacitor 积分"，当后突触事件在 trace 仍存活时到达才产生强
    LTP）是**同一个物理原理**，只是这里不做学习、只做检测：
      - trace 支路 = STDP eligibility trace 的"资格窗口"部分；
      - collector = "resolve 阶段"：trace 仍存活 且 当前事件到达 → 强响应。
    REF: Bi & Poo 1998 J Neurosci 18:10464（STDP 时间窗）；
         Song, Miller & Abbott 2000 Nat Neurosci 3:919（trace-based STDP）；
         本项目 `decision_adapter.py` 的观察者 STDP 束已用
         `eligibility_tau=300.0` 实现同一机制（先例）。

Q2. 物理结构是什么？
    Sources → SynapticBundle → Targets，全部用已有 `Neuron`/`NeuronConfig`/
    `SynapticBundle`/`BundleConfig`，不新造类：

    ξ_a (既有 thermal_quantum_collectors["thermpt28_warm"], spiking)
        │
        ├─(bundle, frozen)→ trace_a_fast (非spiking Neuron, RC 膜积分器)─┐
        │                                                                ├→(bundle)→ collector_a_prec_b_fast (AND门 collector)
        ├─(bundle, frozen)→ trace_a_slow (非spiking Neuron, RC 膜积分器)─┤
        │                                                                │
    ξ_b (既有 thermpt31_warm) ──────(bundle, frozen)────────────────────┘×2 (fast/slow 各一条到对应 collector)

    对称地，ξ_b → trace_b_fast/slow → collector_b_prec_a_fast/slow，
    同时 ξ_a 的原始信号也接入这两个 collector。

    与 Ω/xi 层"ensemble(10)+collector"的两级结构不同：本生成元只有
    2 个源，不需要种群编码 ensemble 中继层——直接用一个 2 输入 AND门
    collector 即可，仍完全由 Bundle 接线，不绕过 Bundle 私读膜电位。

Q3. 每个参数的依据是什么？
    - trace 膜时间常数（fast=15 steps, slow=150 steps）：
      # EXP: fast 取 15 steps，锚定 2026-07-15《感温Ω耦合生成元层》报告
      实测的 xi 层阵发性爆发时长(~10-15 steps)——trace 应能在"一次爆发
      持续期"内保持存活，才能检测"同一次爆发内谁先谁后"。slow 取
      fast 的 10 倍(150 steps)，量级对齐 `variant_adapter.py` 已有的
      `NU_ALPHA=0.01`(~100-step EMA 窗口)先例，检测"跨越多次爆发的
      持续性领先"。
    - r_leak 换算：本项目 Capacitor.leak() 用 `decay=exp(-dt/tau)`，
      `tau=r_leak*capacitance`，dt 与驱动本生成元的测试夹具一致取
      0.001（同温感量子元链路既有测试的 DT 约定，非 CLAUDE.md 警告的
      dt=1.0 陷阱）。故 `r_leak = tau_steps * dt / capacitance`。
    - collector 阈值/权重：无先验解析解，按"Model before tune"实测标定
      （见 T1 分析报告 §标定过程），非拍脑袋填数字。
    - 权重范围 `0<w=w_max<1`：按批判二点10 + `memory:
      project_memristor_saturation_edge_bug`，禁止 w=1.0（对称性打破
      扰动+PowerRail饱和会导致假性不对称）。

═══════════════════════════════════════════════════════════════════════

本模块**不修改** `VariantCircuit`/`variant_adapter.py`。仿照
`circuit/decision_adapter.py` 的 `DecisionCircuit(VariantCircuit)` 先例，
用子类叠加新组件——这样常规回归套件（直接实例化 `VariantCircuit()`）
完全不受影响，T1 原型只在专门的测试/探针里通过本子类实例化。
"""

from __future__ import annotations

from typing import Dict, Tuple

from .site_selection import FROZEN_THERMAL_SITES
from ..circuit.variant_adapter import VariantCircuit
from ..circuit.bundle import BundleConfig, SynapticBundle
from ..components.neuron import Neuron, NeuronConfig, ChannelConfig

DT = 0.001  # 与温感量子元链路既有测试驱动约定一致（非 CLAUDE.md 警告的 dt=1.0 陷阱）

# ── T1 专属标定常量（独立于 xi 层 0.5 / Ω 层 0.05,0.002；批判一点4/约束3） ──
_TAU_FAST_STEPS = 50     # EXP-T1-01: 实测单点 xi 首次发放延迟 ~380-400 步
_TAU_SLOW_STEPS = 600    # （PYTHONHASHSEED=0, dT=0.05），随后每 ~120-150 步复发一次
                         # 爆发，每次衰减尾 ~100-150 步。fast 捕捉"同一次爆发衰减
                         # 尾内的重合"，slow 需覆盖"上一次爆发 → 下一次事件"的
                         # 完整间隔，故取 600（> 400+150 的实测间隔量级）。
                         # 见 T1 分析报告《标定过程》：原拍脑袋值 15/150 步在
                         # 实测下过短——单点 xi 并非"阵发~10-15步"，那是 Ω 报告
                         # 里"发放后瞬时爆发脉冲串"的特征，不是"两次独立驱动
                         # 事件之间需要多久才能被同一 trace 联系起来"的时间尺度，
                         # 二者是不同的物理量，不能直接套用。
# EXP-T1-03: Capacitor 稳态电压 V_ss = I_inject × R_leak，与 C 无关（C 只决定
# 到达稳态的时间常数 tau=R×C）。这让 R_leak 与 C 可以独立设定：先固定
# R_leak（决定"稳态增益"），再用 C = tau_steps×dt / R_leak 反解出各时间
# 尺度所需的电容——而不是像最初拍脑袋那样直接套用 C=1.0 导致 R_leak 被
# tau 目标值绑死、稳态电压压到 O(0.001) 量级不可用（见下方 gm 注释）。
_R_LEAK_TRACE = 5.0   # EXP-T1-04: 实测 R_leak=1.0 时 V_ss≈0.02（xi_a 单次爆发,
                      # 450步窗口），gm=20 二次压缩后 activation≈0.02，量级过小、
                      # 与 raw ξ_b(pre_trace 达 1.0 量级)相差 ~50倍，无法在
                      # collector 端构成有效"trace+raw 重合"AND判据。提高
                      # R_leak 至 5.0（V_ss∝R_leak，与C无关）把 V_ss 抬到 ~0.1
                      # 量级，配合 gm 使 activation 落入 O(0.1~0.3)，与 raw ξ
                      # 量级可比。
_TRACE_CAPACITANCE_FAST = _TAU_FAST_STEPS * DT / _R_LEAK_TRACE   # = 0.01
_TRACE_CAPACITANCE_SLOW = _TAU_SLOW_STEPS * DT / _R_LEAK_TRACE   # = 0.12
_TRACE_GM = 20.0   # 见 _trace_config() 内 EXP-T1-02 注释：补偿门控二次压缩

# collector 标定：见 T1 分析报告《标定过程》一节。
# EXP-T1-05: 对 spiking 神经元，实测确认 `channels=[...]` 的 gated_conduct
# 计算结果不影响脉冲判定——脉冲判定只看 raw 膜电压是否越过 v_peak（原始
# 电流直接注入膜电容，channel 路径只计算 self.activation，而 spiking 分支
# 会在同一步内用 spike 二值覆盖 self.activation，见 neuron.py:530）。因此
# collector 的"AND门"效果完全由 v_peak + capacitance/r_leak + 两路输入
# 电流的相对大小决定，不依赖 channels 阈值。
#
# EXP-T1-06: 首版试验用等权重(0.3/0.3)标定，实测 raw ξ 峰值(≈1.0)远大于
# trace 峰值(fast≈0.5, slow≈0.17，取决于驱动时长)——若两路权重相等，
# "raw 单独"与"trace+raw 重合"两种情形的膜电压差距太窄，standing margin
# 不足以稳定区分（尤其 slow 支路，trace 峰值更小，几乎无法把 collector
# 推过阈值）。改为**非对称权重**：降低 raw 支路权重、提高 trace 支路权重，
# 使 raw 单独贡献与 trace 贡献量级更接近，从而让"两路都在"与"只有 raw"
# 产生更大 margin。
#
# 标定目标：raw ξ_b 单独驱动时膜电压稳态 < v_peak（不产生假阳性）；
# trace_a + raw ξ_b 同时驱动时膜电压稳态 > v_peak（真正重合才发放）。
# 取 w_trace=0.5（conductance≈0.198），w_raw=0.15（conductance≈0.117）：
#   raw 单独:      V_ss = 0.117×1.0×R_leak
#   trace+raw(快): V_ss = (0.117×1.0 + 0.198×0.5)×R_leak = 0.216×R_leak
# 取 R_leak=1.5：raw 单独 Vss=0.117×1.5≈0.176（< v_peak 0.23，安全）；
# 重合 Vss=0.216×1.5≈0.324（> v_peak 0.23，安全越阈）。
_COLLECTOR_CAPACITANCE = 0.007   # tau = 0.01/1.5 ≈ 7 steps，快速响应重合窗口
_COLLECTOR_R_LEAK = 1.5
_COLLECTOR_V_PEAK = 0.23        # 与既有量子元 collector v_peak 惯例一致
_COLLECTOR_THRESHOLD = 0.15     # channels 阈值：对 spiking 神经元功能上不生效
_COLLECTOR_GM = 3.0             # （见上方 EXP-T1-05），保留仅为占位一致性
_COLLECTOR_TAU_GATE = 2.0

# 权重：0<w=w_max<1，见 Q3。
_W_XI_TO_TRACE = 0.3     # xi(pre_trace 量级 O(1)) → trace 膜积分器
_W_TRACE_TO_COLLECTOR = 0.5     # 见上方 EXP-T1-06：非对称权重的高端
_W_RAW_XI_TO_COLLECTOR = 0.15   # 见上方 EXP-T1-06：非对称权重的低端


def _trace_config(label: str, tau_steps: int, capacitance: float, r_leak: float,
                   region: int = 0x01) -> NeuronConfig:
    """非 spiking RC 历史痕迹积分器：leaky integrator，衰减常数 tau_steps。

    与 STDP eligibility trace 同一物理机制（见模块 docstring Q1），
    这里只做检测不做学习——没有 use_eligibility_trace，只是单纯的膜积分。

    # EXP-T1-02: 单通道模式的 `activation = gated_conduct(vm) = m_gate ×
    # conduct(vm)`；当 `tau_gate=0` 时 `m_gate=min(1, gm×(vm-vth)/gm)=
    # min(1, vm-vth)`，故 `gated_conduct = gm×(vm-vth)²`——对小膜电压是
    # **二次**压缩（HH 门控本身的非线性，非 bug）。实测本生成元的膜电压
    # 稳态量级在 O(0.01~0.05)（由 xi 层电流经 frozen bundle 注入决定），
    # 若沿用默认隐式 channel（v_threshold=0.3, gm=1.0）会被二次压缩到
    # 几乎不可读的量级。显式设 v_threshold=0.0（全程线性区，无死区）+
    # gm=20.0（# EXP: 标定后取值，使 vm≈0.03 时 activation≈20×0.03²=0.018，
    # 量级足以被下游 collector 阈值 0.15 在多路叠加后触达，见 T1 分析报告
    # 《标定过程》）。
    """
    return NeuronConfig(
        neuron_id=f"rprec_trace_{label}_{tau_steps}",
        region=region,
        spiking=False,
        capacitance=capacitance,
        r_leak=r_leak,
        inertia=1.0,
        channels=[ChannelConfig(name="default", v_threshold=0.0, gm=_TRACE_GM)],
    )


def _collector_config(label: str, region: int = 0x01) -> NeuronConfig:
    """r≺ Collector：2 输入 AND 门（trace 支路 + 当前 ξ 支路重合才强发放）。"""
    return NeuronConfig(
        neuron_id=f"rprec_collector_{label}",
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


class RPrecCircuitT1(VariantCircuit):
    """TYPE:BIO — 温感轨 T1 原型：在冻结集合 {28,31} 上叠加 r≺ 生成元。

    子类叠加，不修改母本 `VariantCircuit`（同 `DecisionCircuit` 先例）。
    只在专项测试里实例化，常规回归套件不受影响。
    """

    def __init__(self):
        super().__init__()

        site_a = FROZEN_THERMAL_SITES["t1_pair"]["a"]   # 28
        site_b = FROZEN_THERMAL_SITES["t1_pair"]["b"]   # 31
        self.rprec_site_a = site_a
        self.rprec_site_b = site_b

        xi_a = self.thermal_quantum_collectors[f"thermpt{site_a}_warm"]
        xi_b = self.thermal_quantum_collectors[f"thermpt{site_b}_warm"]
        self.rprec_xi_a = xi_a
        self.rprec_xi_b = xi_b

        # ── trace 神经元：a/b × fast/slow ──
        self.rprec_trace_a_fast = Neuron(_trace_config(
            "a", _TAU_FAST_STEPS, _TRACE_CAPACITANCE_FAST, _R_LEAK_TRACE))
        self.rprec_trace_a_slow = Neuron(_trace_config(
            "a", _TAU_SLOW_STEPS, _TRACE_CAPACITANCE_SLOW, _R_LEAK_TRACE))
        self.rprec_trace_b_fast = Neuron(_trace_config(
            "b", _TAU_FAST_STEPS, _TRACE_CAPACITANCE_FAST, _R_LEAK_TRACE))
        self.rprec_trace_b_slow = Neuron(_trace_config(
            "b", _TAU_SLOW_STEPS, _TRACE_CAPACITANCE_SLOW, _R_LEAK_TRACE))

        # ── collector：a≺b / b≺a × fast/slow ──
        self.rprec_collector_a_prec_b_fast = Neuron(_collector_config("a_prec_b_fast"))
        self.rprec_collector_a_prec_b_slow = Neuron(_collector_config("a_prec_b_slow"))
        self.rprec_collector_b_prec_a_fast = Neuron(_collector_config("b_prec_a_fast"))
        self.rprec_collector_b_prec_a_slow = Neuron(_collector_config("b_prec_a_slow"))

        # ── bundles: xi → trace ──
        self.bundles_rprec_xi_to_trace = [
            _frozen_bundle("rprec_xi_a_to_trace_fast", [xi_a], [self.rprec_trace_a_fast], _W_XI_TO_TRACE),
            _frozen_bundle("rprec_xi_a_to_trace_slow", [xi_a], [self.rprec_trace_a_slow], _W_XI_TO_TRACE),
            _frozen_bundle("rprec_xi_b_to_trace_fast", [xi_b], [self.rprec_trace_b_fast], _W_XI_TO_TRACE),
            _frozen_bundle("rprec_xi_b_to_trace_slow", [xi_b], [self.rprec_trace_b_slow], _W_XI_TO_TRACE),
        ]

        # ── bundles: trace + raw xi → collector ──
        self.bundles_rprec_to_collector = [
            _frozen_bundle("rprec_trace_a_fast_to_col", [self.rprec_trace_a_fast],
                            [self.rprec_collector_a_prec_b_fast], _W_TRACE_TO_COLLECTOR),
            _frozen_bundle("rprec_raw_xi_b_to_col_fast", [xi_b],
                            [self.rprec_collector_a_prec_b_fast], _W_RAW_XI_TO_COLLECTOR),

            _frozen_bundle("rprec_trace_a_slow_to_col", [self.rprec_trace_a_slow],
                            [self.rprec_collector_a_prec_b_slow], _W_TRACE_TO_COLLECTOR),
            _frozen_bundle("rprec_raw_xi_b_to_col_slow", [xi_b],
                            [self.rprec_collector_a_prec_b_slow], _W_RAW_XI_TO_COLLECTOR),

            _frozen_bundle("rprec_trace_b_fast_to_col", [self.rprec_trace_b_fast],
                            [self.rprec_collector_b_prec_a_fast], _W_TRACE_TO_COLLECTOR),
            _frozen_bundle("rprec_raw_xi_a_to_col_fast", [xi_a],
                            [self.rprec_collector_b_prec_a_fast], _W_RAW_XI_TO_COLLECTOR),

            _frozen_bundle("rprec_trace_b_slow_to_col", [self.rprec_trace_b_slow],
                            [self.rprec_collector_b_prec_a_slow], _W_TRACE_TO_COLLECTOR),
            _frozen_bundle("rprec_raw_xi_a_to_col_slow", [xi_a],
                            [self.rprec_collector_b_prec_a_slow], _W_RAW_XI_TO_COLLECTOR),
        ]

    # ── 关系层账本用的枚举（不进全局 census，见方案约束1） ──
    def rprec_relation_neurons(self):
        return [
            self.rprec_trace_a_fast, self.rprec_trace_a_slow,
            self.rprec_trace_b_fast, self.rprec_trace_b_slow,
        ]

    def rprec_relation_collectors(self):
        return [
            self.rprec_collector_a_prec_b_fast, self.rprec_collector_a_prec_b_slow,
            self.rprec_collector_b_prec_a_fast, self.rprec_collector_b_prec_a_slow,
        ]

    def rprec_relation_bundles(self):
        return self.bundles_rprec_xi_to_trace + self.bundles_rprec_to_collector

    def get_all_bundles(self):
        """批判三修正点3：约束1原文"新 bundles → 进 get_all_bundles()"，
        只有关系*神经元*应排除全局 census（护 T4.1 energy_per_neuron），
        关系 *Bundle* 必须进入 census，供 Noether/Xin/运输成本/结构账本
        读取——初版遗漏了这个覆写，是真实的实现 bug（T-TRP-1 曾把"Bundle
        不在 census 里"断言成 PASS，与本计划自己的约束正面冲突，现已改回）。

        纯子类覆写，不改动 `VariantCircuit.get_all_bundles()` 本体——普通
        `VariantCircuit()` 实例不受影响，只有 `RPrecCircuitT1` 的账本能看到
        这 12 条新增关系 Bundle。
        """
        return super().get_all_bundles() + self.rprec_relation_bundles()

    def step_rprec(self, dt: float = DT):
        """手动传播一步 r≺ 生成元链路（T1 原型不接入 circuit.step() 主循环，
        独立由测试驱动，同 Ω/xi 层测试的手动传播方法论）。"""
        for b in self.bundles_rprec_xi_to_trace:
            currents = b.propagate()
            for i, tgt in enumerate(b.targets):
                tgt.step(currents[i] if i < len(currents) else 0.0, dt)

        # collector 的两条输入束需要在同一步内先各自 propagate 再叠加注入,
        # 因为两条 bundle 的 targets 相同（同一个 collector），必须避免
        # 后一条覆盖前一条：按 bundle_id 分组，同一 collector 的多路输入求和。
        collector_currents: Dict[int, float] = {}
        collector_objs: Dict[int, object] = {}
        for b in self.bundles_rprec_to_collector:
            currents = b.propagate()
            for i, tgt in enumerate(b.targets):
                key = id(tgt)
                collector_currents[key] = collector_currents.get(key, 0.0) + \
                    (currents[i] if i < len(currents) else 0.0)
                collector_objs[key] = tgt

        for key, total_current in collector_currents.items():
            collector_objs[key].step(total_current, dt)
