"""tss.relations.relation_event_adapter — C1：关系事件 → 脉冲的物理适配器。

TYPE:BIO|SEMI

路线依据：coupling_contract.py §6.2②（耦合物理结构）。
拓扑裁定（2026-09-06 调研）：HC-009 换能先例（拓扑 A）——三条候选拓扑中
先例最干净、保留 bundle 审计可见性的一条；直接 `collector.step(r, dt)`
（拓扑 B）即 HC-009 原违规，被否。

## 这是什么

    r_{i≺j}(t) ──[本适配器]──> spike_output(t) ∈ {0,1}

把 PhysicalThetaComparator 输出的分级关系电流（EXP-C0-02 实测幅度
[0.0026, 0.366]）转换为 CollectorBoundaryPort 语义的 0/1 脉冲，供 level-2
的 PhysicalEntryGate / PhysicalHistoryKernel / PhysicalThetaComparator
递归复用（三件套默认参数零改动——共参验证的载体）。

## 物理链路（每步，无跨步延迟）

    1. RelationInputNeuron.step(r, dt)    # 换能边界（同 ThermalInputNeuron）
    2. bundle.propagate()                 # frozen 换能束（可审计、无可塑）
    3. collector.step(current, dt)        # spiking 积分-发放（同步内成脉冲）
    4. port.spike_output                  # 0/1，供 level-2 gate 消费

## RULES.md 强制三问

Q1 生物对应物：NMDA 符合电流触发**树突 NMDA 棘波**——符合检测器（M2 的
   NMDA 受体）产生的内向电流在树突热区引发局部再生性放电，把分级符合
   信号转换为全或无事件。
   REF: Schiller et al. 2000 Nature 404:285 — NMDA spikes in basal dendrites.
   REF: Major et al. 2013 Annu Rev Neurosci 36:1 — active dendritic events.
   项目内先例：HC-009 换能模式（somatosensory/transducer_neurons.py——
   原始非突触量经换能 Neuron + frozen bundle 合法进入神经元层）。

Q2 物理结构：RelationInputNeuron（换能边界，覆写 step 同 ThermalInputNeuron
   先例）→ frozen SynapticBundle → spiking collector Neuron →
   CollectorBoundaryPort。全部既有类，零新原语。
   换能束 learning_rule="frozen"：树突棘波的触发耦合是通道分布决定的
   固定物理性质，不是逐个学习的参数（同 transducer_neurons.py 三层论证）。

Q3 参数依据（EXP-C1-01 响应曲线反解，exp_C1_adapter_calibration.py）：
     v_peak = 0.23        ← T1 collector 既有惯例（temporal_r_prec.py）
     r_leak = 1.5         ← 同上（T1 collector 既有值）
     w = 0.3 (frozen)     ← Memristor 饱和边缘教训（transducer_neurons.py
                            make_thermo_l1_to_hc Q3 / DEG-014 家族）：w 高位
                            会被 ±25% 扰动推入 G=1/r_min 饱和区
     synapse_gain = 1.0   ← 单位增益，无隐藏放大
     physical_seed = 91000 ← S0-bX1 纪律（DEG-020 教训）：显式传种子，
                            身份命名不得污染物理；**全部适配器实例共用
                            同一种子** ⇒ 同扰动同行为（共参的组成部分）
     capacitance          ← EXP-C1-01 反解：单点响应测得比例系数 k
                            （ΔV = k·r / C），取 C = k·r_min/(2·v_peak)，
                            使实测最小关系幅度 r_min=0.0026（EXP-C0-02）
                            的单步脉冲以 2× 裕量必越 v_peak。
                            阴性无需裕量——负例 r 是精确零（DEG-019
                            硬截零），本适配器无噪声地板问题。

## 禁止字段/禁止读取

  无 _phase/t_step/计步器/站点专属参数；step() 不读 pre_trace/Occurrence/
  地址内容。地址仅谱系（DOMAIN_RELATION_PREC，深度2，父=关系两端）。
"""

from __future__ import annotations

from nexus_v1.components.neuron import Neuron, NeuronConfig
from nexus_v1.components.structural_address import (
    AddressRegistry, GeneratedAddress, DOMAIN_RELATION_PREC,
)
from nexus_v1.circuit.bundle import SynapticBundle, BundleConfig
# G0-R1 D1: shared dt-aware trace decay helper (single source of truth).
from nexus_v1.somatosensory.transducer_neurons import trace_decay_factor
from .boundary_process import CollectorBoundaryPort

# ─────────────────────────────────────────────────────────────────────
# 物理参数 —— 来源见模块 Q3；全部适配器实例共用同一份（共参）
# ─────────────────────────────────────────────────────────────────────

_COLLECTOR_V_PEAK = 0.23       # T1 collector 既有惯例
_COLLECTOR_R_LEAK = 1.5        # T1 collector 既有值
_TRANSDUCER_WEIGHT = 0.3       # Memristor 饱和边缘教训（Q3）
_TRANSDUCER_GAIN = 1.0         # 单位增益
_ADAPTER_PHYSICAL_SEED = 91000  # S0-bX1：显式种子，全实例共用（Q3）

# EXP-C1-01（exp_C1_adapter_calibration.py，2026-09-06 实测反解）：
#   单点响应实测 k = ΔV·C/r = 1.401306e-04；
#   C = k·r_min/(2·v_peak) = 1.4013e-04×0.0026/(2×0.23)，r_min=0.0026
#   （EXP-C0-02 实测下界）。验证：全幅度域 4 点单脉冲必发放、500 步零
#   输入零发放、1204 步间隔可重复触发——EXP-C1-01 PASS。
_COLLECTOR_CAPACITANCE = 7.920427e-07


class RelationInputNeuron(Neuron):
    """TYPE:BIO — 关系电流换能边界（树突 NMDA 电流受体侧）。

    BIO: NMDA 符合电流到达树突棘波起始区；电流→局部去极化是通道的固定
         物理性质，不逐个学习。
    REF: Schiller et al. 2000 Nature 404:285。
    PHYS: step() 直通（同 ThermalInputNeuron 先例）——符合检测已在上游
          比较器完成，此处再加 RC 会双重滤波。
    """

    # G0-R1 D1: per-step factor AT dt=0.001 (canonical GENERATOR_DT);
    # actual per-call factor is trace_decay_factor(0.99, dt) — same debt
    # family as the three transducer neurons (this class cites the
    # ThermalInputNeuron precedent), fixed under the same R-4 ruling.
    _TRACE_DECAY: float = 0.99

    def __init__(self, ident: str, position: tuple = (0.0, 0.0, 0.0)) -> None:
        config = NeuronConfig(
            neuron_id=f"rel_event_in_{ident}",
            position=position,
            capacitance=0.001,
            r_leak=1.0,
            inertia=0.0,
            vdd=2.0,
            r_supply=0.01,
        )
        super().__init__(config)

    def step(self, r_current: float, dt: float = 1.0) -> float:
        """从关系电流更新换能状态（直通；r 由上游保证非负）。"""
        if r_current < 0.0:
            raise ValueError(
                f"RelationInputNeuron: 关系电流必须非负，收到 {r_current!r}"
                "——上游必须是 PhysicalThetaComparator 输出")
        self.activation = r_current
        # G0-R1 D1: dt-aware decay (bit-exact 0.99 at dt=0.001, see helper).
        self.pre_trace = (self.pre_trace * trace_decay_factor(self._TRACE_DECAY, dt)
                          + abs(self.activation))
        self.pre_trace = min(self.pre_trace, 10.0)
        self._activation_ema += 0.01 * (abs(self.activation) - self._activation_ema)
        self._prev_activation = self.activation
        return self.activation


def _relation_collector_config(ident: str,
                               capacitance: float) -> NeuronConfig:
    """spiking 积分-发放 collector：树突棘波起始区（全或无转换点）。

    v_peak/r_leak 取 T1 collector 既有值；capacitance 由 EXP-C1-01 反解
    （见模块 Q3）。不配显式 channels——对 spiking 输出无功能作用
    （temporal_r_prec.py _COLLECTOR_THRESHOLD 注释的既有结论）。
    """
    return NeuronConfig(
        neuron_id=f"rel_event_col_{ident}",
        capacitance=capacitance,
        r_leak=_COLLECTOR_R_LEAK,
        spiking=True,
        v_peak=_COLLECTOR_V_PEAK,
    )


def make_relation_transducer_bundle(ident: str,
                                    rel_input: RelationInputNeuron,
                                    collector: Neuron) -> SynapticBundle:
    """frozen 换能束：RelationInputNeuron → relation collector。

    参数来源见模块 Q3；physical_seed 显式共用（S0-bX1 纪律）。
    """
    return SynapticBundle(
        config=BundleConfig(
            bundle_id=f"rel_event_transducer_{ident}",
            learning_rule="frozen",
            initial_weight=_TRANSDUCER_WEIGHT,
            weight_max=_TRANSDUCER_WEIGHT,
            synapse_gain=_TRANSDUCER_GAIN,
            bundle_role="feedforward",
            physical_seed=_ADAPTER_PHYSICAL_SEED,
        ),
        sources=[rel_input],
        targets=[collector],
    )


class RelationEventAdapter:
    """TYPE:BIO|SEMI — 关系电流→脉冲适配器（组合件，无新原语）。

    用法（每步显式串联，同 make_* 家族接口纯度约定）：
        spike = adapter.step(r, dt)          # r 来自 level-1 比较器
        b2 = gate2.step(adapter.port.spike_output, dt)   # 或直接用返回值
    """

    def __init__(self, registry: AddressRegistry,
                 address_i: GeneratedAddress, address_j: GeneratedAddress,
                 label: str,
                 capacitance: float = _COLLECTOR_CAPACITANCE):
        # 谱系：DOMAIN_RELATION_PREC，父=关系两端地址，深度2
        self.generator_address = registry.register_generated(
            DOMAIN_RELATION_PREC, label, (address_i, address_j), 2)
        self.input_neuron = RelationInputNeuron(label)
        self.collector = Neuron(_relation_collector_config(label, capacitance))
        self.bundle = make_relation_transducer_bundle(
            label, self.input_neuron, self.collector)
        self.port = CollectorBoundaryPort(
            generator_address=self.generator_address,
            carrier_ref=self.collector)

    def step(self, r_current: float, dt: float) -> float:
        """推进一步：换能 → frozen 束传播 → collector 积分-发放。

        返回本步 spike_output（0.0/1.0），同步内完成（无跨步延迟——
        保持 level-2 Δt₂ 与底层关系产生步一致）。
        """
        self.input_neuron.step(r_current, dt)
        currents = self.bundle.propagate()
        self.collector.step(currents[0], dt)
        return self.port.spike_output
