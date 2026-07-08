"""Context-gated gain modulation of the innate thermotaxis reflex (死锁二 MVE).

TYPE:HYBRID — learned presynaptic gain control of a frozen reflex arc.

死锁二（缺陷1 学习目标冗余）修复：STDP 学的应是"在什么上下文下放大/抑制天生反射"
（增益调制），而非重建已由硬连线提供的方向极性。

机制（物理乘法，非 Python `*`）：
    hunger 上下文 ──[DA-gated STDP Bundle]──→ gain_gate 神经元(Capacitor, 慢τ)
                                                    │ activation
                                                    ↓
                                     MOSFET 跨导 update_gate → m_gate ∈ [0,1]
                                                    │
                                                    ↓ 有界仿射(物理工作区)
                                     gain = g_min + (g_max-g_min)·m_gate ∈ [0.3, 2.0]

返回的 gain 由 adapter 乘到 thermo→yaw 反射束的 synapse_gain（=突触前电导调制），
在 super().step() 读取前设置 → 同一步内完成物理增益门控。

设计要点（见 死锁二_增益调制_设计方案 v2）：
  - 单一全局门：同 gain 调制 L/R 两侧 → 方向 100% 留给 frozen 反射 → 与方向零重叠=非冗余。
  - 增益方向（hunger 促进）是先天符号（如 thermo→yaw 符号先天），magnitude/schedule 由 STDP 学。
  - 门下界 g_min=0.3：保护性反射不可关断（Rudomin 1999 突触前抑制约 2~3×，极少全抑）。
  - m_gate 慢积分放在 gain_gate 神经元膜(τ≈1000, 匹配 hunger 上下文)；MOSFET tau_gate=0 只做有界变换。
  - 学习=DA-gated 三因子 STDP（DA 现编码 RPE，锁一已解）→ "增益在何时带来奖励"可学。

Q1 BIO: 突触前抑制门控初级传入反射增益(Rudomin & Schmidt 1999, Exp Brain Res 129:1);
        动机态(饥饿)易化觅食反射(Sternson 2013, Neuron 77:810)。
Q2 结构: hunger → [STDP,DA-gated] → gain_gate → MOSFET → gain → thermo→yaw synapse_gain。
Q3 参数: 见各字段注释推导。
"""
from __future__ import annotations

from ..components.neuron import Neuron, NeuronConfig, ChannelConfig
from ..components.semiconductor import MOSFET
from ..circuit.bundle import SynapticBundle, BundleConfig


class GatedReflexArc:
    """TYPE:HYBRID — 上下文门控的反射增益调制弧（死锁二 MVE）。"""

    def __init__(self, hunger_neuron: Neuron,
                 g_min: float = 0.3, g_max: float = 2.0):
        # ── gain_gate 神经元：慢积分上下文 → 增益指令 ──
        # Q3: C=200, r_leak=5.0 → τ=1000 步，匹配 hunger 上下文时间尺度(方案 v2 §9.4)。
        #     无 bc 基线：full(hunger→0) 时 vm→0 → m_gate→0 → gain→g_min=0.3(抑制热趋, 期望态)；
        #     hungry 时 hunger 电流抬 vm → gain↑。V_ss=I·r_leak=I·5(对 hunger 敏感)。
        #     gate 信号用膜电位 vm(干净线性积分), 避开 activation 非线性压缩。
        #     maturation_stage=0: 使入射束走 STDP(spine 可塑)。
        self.gain_gate = Neuron(NeuronConfig(
            neuron_id="gain_gate",
            capacitance=200.0, r_leak=5.0, v_rest=0.0, region=0x04,
            channels=[ChannelConfig(name="default", v_threshold=0.01, gm=1.0)],
            use_bias_current=False, bc_current=0.0,
            energy=10.0, spiking=False, maturation_stage=0,
            trace_tau_pre=20.0, trace_tau_post=20.0,
        ))

        # ── hunger → gain_gate：DA-gated 三因子 STDP 束 ──
        # Q3: initial_weight=0 + synapse_gain=0.15 → 初始 hunger 耦合被压到门下限附近
        #     (I(w=0)=hunger·G(0)=0.1·0.15≈0.024/hunger_unit → 弱)。**关键: 让学习成为开门主因**——
        #     Memristor G(w) 在 w>0.5 陡升(0.1→0.9), STDP 把权重推进陡峭区 → 学习主导 hunger→gain,
        #     避免"未学习也能开门"重蹈缺陷1。先天符号=兴奋(饥饿促觅食), magnitude 由 STDP 学。
        #     eligibility_gain=1e-4(确保 100k 内可见学习), da_ema_tau=5000(DA 现编码 RPE)。
        self.bundle = SynapticBundle(BundleConfig(
            bundle_id="hunger_to_gain_gate",
            learning_rule="stdp",
            initial_weight=0.0, weight_min=0.0, weight_max=1.0,
            stdp_lr=0.01, synapse_gain=0.15,
            bundle_role="feedforward", remodel_cost_kappa=0.0,
            use_eligibility_trace=True, eligibility_tau=500.0,
            eligibility_gain=1e-4, eligibility_ltd_rate=0.01,
            da_ema_tau=5000.0, lambda_metabolic=1e-6,
        ), [hunger_neuron], [self.gain_gate])

        # ── MOSFET 跨导：gate 激活 → 有界 m_gate ──
        # Q3: v_threshold=0.0, gm=1.0, tau_gate=0 → m_gate=clamp(gate.act,0,1)。
        #     慢动力学已在 gain_gate 膜(τ=1000)，MOSFET 只做有界非线性变换。
        self.mosfet = MOSFET(v_threshold=0.0, gm=1.0, tau_gate=0.0)

        # ── 增益工作区(物理有界) ──
        # Q3: g_min=0.3(保护性反射不可关断,Rudomin 1999); g_max=2.0(最大易化~2×)。
        self.g_min = g_min
        self.g_max = g_max

        self._gain = 1.0
        self.frozen = False   # E2' 差分消融: True → 冻结学习(权重停在初值), 隔离已学增量

    def step(self, da_concentration: float, dt: float) -> float:
        """推进一步，返回当前增益因子。hunger 由上一步(慢, 一步延迟可忽略)。"""
        # 1. hunger → gate 传播
        cur = self.bundle.propagate()
        i_gate = cur[0] if cur else 0.0
        # 2. 步进 gain_gate 神经元(慢积分)
        self.gain_gate.step(i_gate, dt)
        # 3. MOSFET: gate 膜电位 vm(线性积分) → 有界 m_gate
        self.mosfet.update_gate(self.gain_gate._membrane.voltage, dt)
        m = self.mosfet.m_gate
        # 4. 有界增益因子(物理工作区仿射映射)
        self._gain = self.g_min + (self.g_max - self.g_min) * m
        # 5. DA-gated 三因子 STDP 学习(frozen 时跳过 → 权重停在初值, E2' 用)
        if not self.frozen:
            self.bundle.learn(dt=dt, da_concentration=da_concentration)
            self.bundle.compute_xin(dt)
        return self._gain

    @property
    def gain(self) -> float:
        return self._gain

    def mean_weight(self) -> float:
        return self.bundle.mean_weight()

    def state(self) -> dict:
        return {
            "gain": self._gain,
            "gate_act": self.gain_gate.activation,
            "m_gate": self.mosfet.m_gate,
            "w_hunger_gate": self.bundle.mean_weight(),
            "frozen": self.frozen,
        }
