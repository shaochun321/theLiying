"""nexus_v1.relations.ratio_r_part — T3-B: 基础占比关系生成元原型 r_part
（真实 Neuron/Bundle 二元电路，共享分流池路径B）。

TYPE:HYBRID

方案依据：cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md
第十七节《我方决定：暂停世界模型扩张，转做 R2（T3-B 正式实施）》17.2。
本轮只做 Gate D 一级验收（合成脉冲电路原型），二级验收/真实ξ输入/三元
扩展/升格r_ρ 留作 T3-C，同 T1 拆 B1→B2 的既定节奏。

═══════════════════════════════════════════════════════════════════════
强制三问（每个新 Bundle 动手前必须先答，见 RULES.md / 方案约束7）
═══════════════════════════════════════════════════════════════════════

Q1. 生物对应物是什么？
    BIO: 分流抑制/横向抑制池是真实皮层机制（REF: Carandini & Heeger 2012,
    Nature Reviews Neuroscience——"Normalization as a canonical neural
    computation"）。本生成元让 ξ_a、ξ_b 两条通道共享**同一个**
    `DivisiveNormalizationReceptor` 池实例（而非各自独立池），物理对应
    "两个感受野竞争同一片横向抑制神经元"——这正是 T3 分析报告已确立、
    第十二节 12.2 第1点已用代码验证过合法性的路径B机制，本模块首次把它
    接成真正的 Neuron/Bundle 电路（此前只在 `_calib_t3_path_ab.py` 校准
    脚本里验证过接口合法性，未接成生产电路原型）。

Q2. 物理结构是什么？
    Sources → SynapticBundle → Targets，Sources/Targets 全部用已有
    `Neuron`/`NeuronConfig`/`SynapticBundle`/`BundleConfig`，DN 池复用
    既有 `DivisiveNormalizationReceptor`（`compensation.py`），不新造类：

      ξ_a (thermal_quantum_collectors["thermpt28_warm"]，复用T0/T1冻结点a)
          │
          └─(bundle, frozen)→ channel_a_collector (非spiking Neuron, RC 读出)
      ξ_b (thermal_quantum_collectors["thermpt31_warm"]，复用T0/T1冻结点b)
          │
          └─(bundle, frozen)→ channel_b_collector (非spiking Neuron, RC 读出)

      shared_pool = DivisiveNormalizationReceptor(...)  # a/b 共享同一实例

    DN 是插入在 `Bundle.propagate()` 输出电流和 `Neuron.step()` 输入
    电流之间的补偿级联（与 `compensation.py` 里 VoltageRegulator/
    BiasCurrent 的使用方式同构，不是新发明的写入路径）：先算两条 Bundle
    各自的原始电流 `i_a_raw`/`i_b_raw`（`propagate()` 本身无副作用，已读
    `bundle.py:229-266` 确认），用共享池按 `dt=0` 只读技术分别读出
    `y_a`/`y_b`（12.2 第1点已验证的合法实现），再显式 `.step(y_*, dt)`
    注入各自的 channel collector——这是"多路输入汇聚前先求和"8步调度
    协议的一个变体应用（这里"多路"指共享池的两路输入，池更新必须用
    `i_a_raw+i_b_raw` 之和，读出必须分别用 `dt=0`，顺序不能颠倒）。

Q3. 每个参数的依据是什么？
    - `_W_XI_TO_CHANNEL=0.3`：直接复用 T1 `_W_XI_TO_TRACE` 已验证的取值
      （`temporal_r_prec.py` EXP-T1-06 一带的标定史）——同一 ξ 源
      （`thermpt28_warm`/`thermpt31_warm`），pre_trace 量级同为 O(1)，
      沿用同一权重量级是合理的复用，不是重新拍脑袋。
    - DN 池参数（`sigma`/`pool_capacitance`/`pool_r_leak`）：首轮直接
      沿用 `DivisiveNormalizationReceptor` 类默认值（`sigma=1.0`，
      `pool_capacitance=5.0`，`pool_r_leak=5.0`），作为 EXP 起点——
      **明确预期需要 Model-before-tune 式多轮校准**（同 T1 report 记录
      的 5 轮标定史，不是一次到位；本模块首版参数未经过完整校准循环，
      如实标注）。
    - Channel collector（非spiking RC 读出器）：结构复用 T1
      `_trace_config()` 同款"显式 v_threshold=0，大 gm 补偿二次压缩"
      范式（T1 EXP-T1-02 已证实默认隐式 channel 会把小膜电压压到不可读
      量级），`_CHANNEL_GM` 首轮沿用 T1 trace 的量级（20.0），因为
      channel collector 面对的输入电流（DN 归一化后的 y_*）量级与 T1
      trace 的膜电压量级相近（均是 O(0.01~0.3) 范围）。
    - 权重范围 `0<w=w_max<1`：按约束2/批判二点10，禁止 w=1.0。

═══════════════════════════════════════════════════════════════════════

本模块**不修改** `VariantCircuit`/`variant_adapter.py`。仿照
`temporal_r_prec.py` 的 `RPrecCircuitT1(VariantCircuit)` 先例，用子类
叠加新组件——常规回归套件（直接实例化 `VariantCircuit()`）完全不受
影响，本原型只在专门的测试/探针里通过本子类实例化。
"""

from __future__ import annotations

from typing import Dict

from .site_selection import FROZEN_THERMAL_SITES
from ..circuit.variant_adapter import VariantCircuit
from ..circuit.bundle import BundleConfig, SynapticBundle
from ..components.neuron import Neuron, NeuronConfig, ChannelConfig
from ..components.compensation import DivisiveNormalizationReceptor

DT = 0.001  # 与 T1/T0 既有测试驱动约定一致

# ── T3-B 专属标定常量（EXP 起点，明确预期需要多轮校准，见模块 docstring Q3）──
_W_XI_TO_CHANNEL = 0.3   # 复用 T1 _W_XI_TO_TRACE 已验证取值（同一 ξ 源量级）

_CHANNEL_CAPACITANCE = 0.05   # EXP: 首轮起点，参照 T1 trace fast 量级(0.01~0.12)
_CHANNEL_R_LEAK = 5.0         # EXP: 首轮起点，同 T1 _R_LEAK_TRACE
_CHANNEL_GM = 20.0            # EXP: 同 T1 _TRACE_GM（见 Q3 说明）

# DN 池：首轮直接用类默认值，见 Q3 说明。
_DN_SIGMA = 1.0
_DN_POOL_CAPACITANCE = 5.0
_DN_POOL_R_LEAK = 5.0


def _channel_config(label: str, region: int = 0x01) -> NeuronConfig:
    """非 spiking RC 读出器：把 DN 归一化后的电流积分成可读的 activation。

    与 T1 `_trace_config()` 同款范式：显式 v_threshold=0（全程线性区，
    避免默认隐式 channel 的死区）+ 较大 gm 补偿二次压缩（T1 EXP-T1-02）。
    """
    return NeuronConfig(
        neuron_id=f"rpart_channel_{label}",
        region=region,
        spiking=False,
        capacitance=_CHANNEL_CAPACITANCE,
        r_leak=_CHANNEL_R_LEAK,
        inertia=1.0,
        channels=[ChannelConfig(name="default", v_threshold=0.0, gm=_CHANNEL_GM)],
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


class RPartCircuitT3(VariantCircuit):
    """TYPE:HYBRID — 温感轨 T3-B 原型：在冻结集合 {28,31} 上叠加 r_part 生成元。

    子类叠加，不修改母本 `VariantCircuit`（同 `RPrecCircuitT1`/
    `DecisionCircuit` 先例）。只在专项测试里实例化，常规回归套件不受影响。
    """

    def __init__(self):
        super().__init__()

        site_a = FROZEN_THERMAL_SITES["t1_pair"]["a"]   # 28，复用 T0/T1 同一对点
        site_b = FROZEN_THERMAL_SITES["t1_pair"]["b"]   # 31
        self.rpart_site_a = site_a
        self.rpart_site_b = site_b

        xi_a = self.thermal_quantum_collectors[f"thermpt{site_a}_warm"]
        xi_b = self.thermal_quantum_collectors[f"thermpt{site_b}_warm"]
        self.rpart_xi_a = xi_a
        self.rpart_xi_b = xi_b

        # ── channel collector：a/b 各一 ──
        self.rpart_channel_a = Neuron(_channel_config("a"))
        self.rpart_channel_b = Neuron(_channel_config("b"))

        # ── 共享分流池（路径B机制核心，两通道共享同一实例）──
        self.rpart_shared_pool = DivisiveNormalizationReceptor(
            sigma=_DN_SIGMA,
            pool_capacitance=_DN_POOL_CAPACITANCE,
            pool_r_leak=_DN_POOL_R_LEAK,
        )

        # ── bundles: xi → channel（各自独立，非共享目标，无需求和）──
        self.bundle_rpart_xi_a_to_channel = _frozen_bundle(
            "rpart_xi_a_to_channel", [xi_a], [self.rpart_channel_a], _W_XI_TO_CHANNEL)
        self.bundle_rpart_xi_b_to_channel = _frozen_bundle(
            "rpart_xi_b_to_channel", [xi_b], [self.rpart_channel_b], _W_XI_TO_CHANNEL)

        # ── 共享池关系层账本计数器（T3-C0 第4点，方案第十八节18.4）：
        # DivisiveNormalizationReceptor 本身不记录调用次数，由本类代持。
        self._rpart_pool_step_count = 0

    # ── 关系层账本用的枚举（不进全局 census，见方案约束1）──
    def rpart_relation_neurons(self):
        return [self.rpart_channel_a, self.rpart_channel_b]

    def rpart_relation_bundles(self):
        return [self.bundle_rpart_xi_a_to_channel, self.bundle_rpart_xi_b_to_channel]

    def rpart_relation_pool_stats(self) -> Dict[str, float]:
        """T3-C0 第4点（方案第十八节18.4）：共享分流池的关系层独立账本读数。

        DN 池既不是 Neuron 也不是 Bundle，不进入全局/关系层 census——
        这里作为补充读数暴露，供审计"每步只更新一次/新实例间不共享"等
        性质（同第七节约束1"关系层独立账本"的既定模式，不强行塞进
        get_all_neurons()/get_all_bundles()）。
        """
        return {
            "pool_instance_count": 1,  # 本电路只持有一个共享池实例
            "pool_step_count": self._rpart_pool_step_count,
            "pool_activity": self.rpart_shared_pool.pool_activity,
        }

    def get_all_bundles(self):
        """同 T1 `RPrecCircuitT1.get_all_bundles()` 的既定修正（批判三点3）：
        关系 *Bundle* 必须进入 census（供 Noether/Xin/运输成本/结构账本
        读取），关系 *神经元*才排除。纯子类覆写，不改 `VariantCircuit`
        本体。
        """
        return super().get_all_bundles() + self.rpart_relation_bundles()

    def step_rpart(self, dt: float = DT) -> Dict[str, float]:
        """手动传播一步 r_part 生成元链路（T3-B 原型不接入 circuit.step()
        主循环，独立由测试驱动，同 T1 `step_rprec()` 方法论）。

        返回 {"i_a_raw":..., "i_b_raw":..., "y_a":..., "y_b":...} 供测试
        直接读取中间值，不必逐层反查内部状态。
        """
        # 1. 各自 Bundle propagate，取原始电流（propagate() 无副作用）。
        currents_a = self.bundle_rpart_xi_a_to_channel.propagate()
        currents_b = self.bundle_rpart_xi_b_to_channel.propagate()
        i_a_raw = currents_a[0] if currents_a else 0.0
        i_b_raw = currents_b[0] if currents_b else 0.0

        # 2. 共享池按两路电流之和更新一次（真实 dt）。
        self.rpart_shared_pool.normalize(i_a_raw + i_b_raw, dt)
        self._rpart_pool_step_count += 1

        # 3. 分别只读读出（dt=0，不产生副作用，12.2 第1点已验证的技术）。
        y_a = self.rpart_shared_pool.normalize(i_a_raw, 0.0)
        y_b = self.rpart_shared_pool.normalize(i_b_raw, 0.0)

        # 4. 显式注入各自 channel collector。
        self.rpart_channel_a.step(y_a, dt)
        self.rpart_channel_b.step(y_b, dt)

        return {"i_a_raw": i_a_raw, "i_b_raw": i_b_raw, "y_a": y_a, "y_b": y_b}
