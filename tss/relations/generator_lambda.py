"""tss.relations.generator_lambda — TSS-2b：同一活动云、双物理窗口、
双独立输出的**嵌套支撑范围** Λ_nested^(1)（Σ_support 的子情形）。

**资格降格（TSS-2b修正，实测依据）**：
  初版命名为"尺度生成算子原型 Λ_support^(1)"并列为与 Θ_≺/Σ_support 并列的
  第三个基础算子——**该定位过强，已撤下**。对齐 physical_seed 后实测：

      Y_broad 限制到 N_LOCAL 支撑集 ≡ Y_local （diff = 0.00e+00 逐位相同）

  即不存在两个算子，只有**一个求和 collector 作用在两张输入表上**。
  local/broad 的差异全部来自成员集合大小，没有任何尺度专属变换。
  此外 Y_broad=3.5424 而 Y_local+Y_delta=3.9983（ratio 0.886）——次可加性
  仅来自 collector 自身的 v_peak 钳位与漏电非线性，而 local 用的是同一个
  非线性，广域侧没有出现任何新信息。

**当前实际取得的资格**：
  同一片生成活动云可以同时进入两个嵌套的物理支撑范围（N_local ⊂ N_broad），
  产生两个独立、可切断验证的下游输出。

**禁止宣称**：
  - 这是一个尺度算子（缺不可约性：Y_broad 可由细尺度同类运算重构）
  - 已实现粗粒化或重整化
  - 系统自行发现了局部与广域尺度（成员集合是外部标定后字面冻结的）
  - 不同尺度之间可以互相转换
  - 当前两个窗口适用于其他模态和环境

**升格为真正尺度算子所缺的检验**（参照 P2-C1F-d 对 K_R2 的不可约性检验）：
  必须证明 Y_broad 无法由 {Y_local, Y_delta} 经细尺度同类运算重构——
  即广域侧存在细尺度不可见的量。当前 test_generator_lambda.py 的恒等断言
  正是该门槛的守卫：任何"尺度专属变换"的宣称必须先让那条断言失败。

TYPE:BIO（复用已有量子元collector机制）+ INFRA（双尺度绑定）

方案依据：document - 2026-08-03T201310.154.md（TSS-2b裁定）。

评判核心要求：
  同一个外部发生、同一片生成活动云，同时进入两个不同结构窗口：
    ω[W] → C_ω[W] → { Λ_local^(1) → Y_local, Λ_broad^(1) → Y_broad }
  两个collector必须是独立物理载体，不能在测试代码里直接
  sum(local_sites)/sum(broad_sites)做软件聚合。
  成员集合必须由结构地址和物理连接**在构造期固定**，运行时不得读取
  欧氏距离或HeatSource半径决定归属。

TSS-2a修正记录（评判201310指出的两点，本文件据此设计）：
  1. radius=2.0/3.0是两次不同的外部发生过程（ω_{r=2}≠ω_{r=3}），不是
     同一活动云被两个内部尺度算子同时处理——TSS-2b必须用**同一次**
     HeatSource驱动，local/broad两个collector同时读取同一次驱动产生
     的活动云，不能分两次驱动再对比。
  2. TSS-2a"几何预测与实测不一致"的原因只是候选机制记录（皮肤节点间
     传播/上游残余状态/公共内部链路/生成元阈值与饱和的共同作用等），
     未钉死为memristor哈希扰动，本文件不依赖该归因。

最低工程结构（评判裁定，本文件严格实现）：
  同一次HeatSource发生
        ↓
  32点基础生成元活动云（已有，复用thermal_quantum_collectors）
        ├─→ local bundles → local scale collector → Y_local
        └─→ broad bundles → broad scale collector → Y_broad
  （local站点集合 ⊂ broad站点集合，两组bundle在__init__时按固定列表
   构造，不依赖任何运行时坐标/半径判断）

最关键的资格测试（评判裁定）：
  N_Δ = N_broad \\ N_local（广域独有部分）
  切断N_Δ到broad collector的链路后：
    Y_local^cut == Y_local（不受影响）
    Y_broad^cut ≠ Y_broad（受影响）
  证明两个输出差异来自真实结构支撑范围，不是名称或软件标签。

RULES.md 强制三问：
  Q1 生物对应物：与temporal_r_prec.py同一机制（多路输入AND门/求和
     collector，同一物理原理：多个传入神经元汇聚到同一目标，收敛范围
     决定感受野大小，Willis & Coggeshall 2004脊髓背角WDR神经元空间
     会聚——本文件把该机制复制两份、只改变汇聚范围）。
  Q2 物理结构：复用已有的thermal_quantum_collectors（32点量子元阵列，
     不新建L1/HC/ensemble），新增2个collector Neuron（local/broad）+
     对应frozen bundle（各collector的sources是固定的站点collector列表）。
  Q3 参数依据：collector参数复用temporal_r_prec.py的_collector_config
     标定值。站点集合（N_local/N_broad）来自TSS-2a的真实几何审计结果
     （固定为字面常量，构造期冻结，不重新计算）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, List, Tuple

from nexus_v1.circuit.bundle import BundleConfig, SynapticBundle
from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.neuron import Neuron, NeuronConfig, ChannelConfig

DT = 0.001

# ── collector参数（复用temporal_r_prec.py标定值） ──
_COLLECTOR_CAPACITANCE = 0.007
_COLLECTOR_R_LEAK = 1.5
_COLLECTOR_V_PEAK = 0.23
_COLLECTOR_THRESHOLD = 0.15
_COLLECTOR_GM = 3.0
_COLLECTOR_TAU_GATE = 2.0
_W_SITE_TO_COLLECTOR = 0.15  # 复用T1的_W_RAW_XI_TO_COLLECTOR

# ── 站点集合：构造期字面冻结（评判要求"不得在运行时读取欧氏距离或
# HeatSource半径决定归属"），来自TSS-2a的真实几何审计结果（
# test_tss2a_scale_audit.py._CANDIDATE_SITES的radius=2.0/3.0实测激活
# 集合），本文件不重新计算距离，只固定字面列表。 ──
SOURCE_SITE = 28
N_LOCAL: FrozenSet[int] = frozenset({20, 23, 24, 25, 26, 27, 29, 30, 31})
N_BROAD: FrozenSet[int] = frozenset({20, 23, 24, 25, 26, 27, 29, 30, 31,
                                     10, 12, 15, 17, 18, 21, 22})
N_DELTA: FrozenSet[int] = N_BROAD - N_LOCAL  # 广域独有部分


def _lambda_collector_config(label: str) -> NeuronConfig:
    return NeuronConfig(
        neuron_id=f"lambda_collector_{label}",
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


# ── physical_seed基址（S0-bX1身份-扰动解耦，commit 9c8528d） ──
# FIX(TSS-2b修正)：初版两组bundle的id分别是lambda_local_site20_to_col和
# lambda_broad_site20_to_col，bundle.py:194-204用bundle_id的crc32生成±25%
# 权重扰动 → 同一物理站点在local/broad两个窗口里拿到不同权重。实测后果：
# 对齐physical_seed前 Y_broad^cut=2.4918 vs Y_local=2.3280（7%差被误读为
# 结构效应）；对齐后 Y_broad^cut≡Y_local（diff=0.00e+00）。该7%全部是
# 命名污染物理，无结构成分。S0-bX1已为此冻结physical_seed字段（无语义
# 数值，不得嵌入审计名称），本文件据此改用站点号基址：同一站点在两个
# 窗口共享同一物理权重，窗口差异只来自成员集合本身。
_PHYS_SEED_BASE = 70000


def _frozen_bundle(bundle_id: str, sources, targets, weight: float,
                   phys_seed: object = None) -> SynapticBundle:
    cfg = BundleConfig(
        bundle_id=bundle_id, learning_rule="frozen",
        initial_weight=weight, weight_max=weight, synapse_gain=1.0,
        bundle_role="feedforward", remodel_cost_kappa=0.0,
        physical_seed=phys_seed,
    )
    return SynapticBundle(cfg, sources, targets)


class LambdaScaleCircuit(VariantCircuit):
    """同一次外部发生驱动local/broad两个嵌套支撑范围collector。

    命名保留 `LambdaScaleCircuit` 只为不打断已有 import；语义上它是
    **嵌套支撑范围**（Σ_support 子情形），不是尺度算子——见模块文档
    的资格降格说明。

    N_local/N_broad在构造期字面冻结（模块常量），__init__只按固定列表
    构造bundle，不做任何距离/半径判断。local_bundles的sources只包含
    N_LOCAL站点的collector，broad_bundles的sources包含N_BROAD站点的
    collector——两组bundle在物理上独立（不同SynapticBundle对象，不同
    Memristor矩阵），不是同一份数据的两次读取。
    """

    def __init__(self):
        super().__init__()

        self.lambda_local_collector = Neuron(_lambda_collector_config("local"))
        self.lambda_broad_collector = Neuron(_lambda_collector_config("broad"))

        self.bundles_local: List[SynapticBundle] = []
        for site in sorted(N_LOCAL):
            src = self.thermal_quantum_collectors[f"thermpt{site}_warm"]
            self.bundles_local.append(_frozen_bundle(
                f"lambda_local_site{site}_to_col", [src],
                [self.lambda_local_collector], _W_SITE_TO_COLLECTOR,
                _PHYS_SEED_BASE + site))

        self.bundles_broad: List[SynapticBundle] = []
        for site in sorted(N_BROAD):
            src = self.thermal_quantum_collectors[f"thermpt{site}_warm"]
            self.bundles_broad.append(_frozen_bundle(
                f"lambda_broad_site{site}_to_col", [src],
                [self.lambda_broad_collector], _W_SITE_TO_COLLECTOR,
                _PHYS_SEED_BASE + site))

    def lambda_bundles(self) -> List[SynapticBundle]:
        return self.bundles_local + self.bundles_broad

    def get_all_bundles(self):
        return super().get_all_bundles() + self.lambda_bundles()

    def step_lambda(self, dt: float = DT) -> None:
        """传播local/broad两个collector各一步（不共享中间聚合变量，
        每个collector各自独立求和自己的输入bundle）。"""
        local_current = 0.0
        for b in self.bundles_local:
            currents = b.propagate()
            local_current += (currents[0] if currents else 0.0)
        self.lambda_local_collector.step(local_current, dt)

        broad_current = 0.0
        for b in self.bundles_broad:
            currents = b.propagate()
            broad_current += (currents[0] if currents else 0.0)
        self.lambda_broad_collector.step(broad_current, dt)

    def cut_delta_bundles(self) -> None:
        """切断N_Δ（广域独有部分）到broad collector的链路——只切
        bundles_broad中对应N_DELTA站点的bundle，local bundles不受影响
        （物理上是不同的SynapticBundle对象）。"""
        for b in self.bundles_broad:
            for site in N_DELTA:
                if f"site{site}_to_col" in b.config.bundle_id:
                    b.config.synapse_gain = 0.0
