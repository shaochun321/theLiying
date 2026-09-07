"""tss.events.kernel_ledger — E0 修复：𝔈 的 ℒ（资源账本）与 K/𝒞（持久存储）承载。

TYPE:INFRA（只读观察者 + 序列化基础设施，零动力学、零新物理载体）

修复依据：event_core_contract.py E-1 审计——ℒ 原判 GAP（tss 层元件不在
organism census，nexus_v1.ledger 不可见）、K 原判 EXISTS_PARTIAL（无持久
存储）。用户裁定 2026-09-07：K/𝒞 存储形式 = **契约代码 + JSON 快照**
（R-E0-1，零新物理载体）；ℒ = 本模块只读能量观察者。

## 三个部件

1. `KernelCensus` — 𝔈 结构骨架 K 的元件普查：显式接收 c_ro 链元件
   （适配器/门/核/比较器），枚举神经元、束、电容。对齐 organism 的
   get_all_neurons()/get_all_bundles() 语义，但独立于母体（依赖方向
   纪律：tss→nexus_v1 单向）。
2. `KernelEnergyProbe` — ℒ 只读观察者（模式对照 nexus_v1.ledger.
   EntropyLedger.record，独立类不塞母体分层逻辑）。逐步采样：
   - 神经元 energy / heat_output（Neuron 既有口径；**量纲注意**：
     heat_output 是"该步已扣除的能量"（energy per step），不是功率——
     累加时不乘 dt。DEG-024 曾因误乘 dt 少记 1000×，T-KL-5 跨账本守恒
     测试防复发）
   - 电容储能 E = Q²/2C（由 charge 推算，纯读）
   - 泄漏耗散 P·dt = V²/r_leak·dt（由状态推算，纯读）
   - 门 Zener 钳位热 clamp_heat（entry_gate 既有累积器）
   **诚实边界（ℒ 仍为 EXISTS_PARTIAL 的原因）**：MOSFET 开关/导通
   耗散不建模——比较器与门的 FET 导通路径没有电阻耗散记账；
   补齐需给 MOSFET 原语加耗散口径（母体改动），本轮不做。
3. `snapshot_kernel` / `write_snapshot` / `load_snapshot` — K/𝒞 JSON
   快照：地址谱系（uid/domain/parents/depth）、各元件实际物理参数
   （与 relation_event_adapter 冻结常量可逐项核对）、类名清单、
   资格台账指针。快照是**记录**不是**载体主张**——重建实例仍须走
   构造函数物理过程，快照不允许直接写回元件状态（对齐 E-2 注入纪律：
   唯一合法注入点是声明父输入端口）。

## RULES.md 强制三问

  Q1 生物/物理对应物：INFRA 审计/记账基础设施（同 AddressRegistry /
     EntropyLedger 先例），不对应具体物理机制，不执行动力学。
  Q2 物理结构：零新结构。只读引用既有对象属性（energy/heat_output/
     charge/voltage/clamp_heat/config），不调用任何改变状态的方法
     （不 inject/leak/step）。只读性由 T-KL-2 以 bit-exact 复放对照
     守卫（挂 probe 与不挂 probe 输出完全一致）。
  Q3 参数依据：零新物理参数。电容储能 Q²/2C 与泄漏功率 V²/R 是
     电路学恒等式，非设计值。
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from nexus_v1.components.neuron import Neuron
from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.circuit.bundle import SynapticBundle

_MIN_CAPACITANCE = 1e-6   # 同 Capacitor.voltage 的既有防除零下限

SNAPSHOT_SCHEMA_VERSION = 1


# ─────────────────────────────────────────────────────────────────────
# 1. KernelCensus — K 的元件普查
# ─────────────────────────────────────────────────────────────────────

class KernelCensus:
    """TYPE:INFRA — 𝔈 结构骨架的显式元件普查（只读持有引用）。

    显式接收链元件（不做魔法发现——census 的完整性由构造方负责，
    T-KL-1 守卫双适配器栈的标准形态）。任何元件重复传入即 fail-fast。
    """

    def __init__(self, adapters=(), gates=(), kernels=(), comparators=()):
        self.adapters = tuple(adapters)
        self.gates = tuple(gates)
        self.kernels = tuple(kernels)
        self.comparators = tuple(comparators)
        all_parts = (list(self.adapters) + list(self.gates)
                     + list(self.kernels) + list(self.comparators))
        if len(set(map(id, all_parts))) != len(all_parts):
            raise ValueError("KernelCensus: 同一元件重复传入")

    def neurons(self) -> List[Neuron]:
        """适配器的换能/收集神经元（Neuron 既有能量口径）。"""
        out: List[Neuron] = []
        for ad in self.adapters:
            out.append(ad.input_neuron)
            out.append(ad.collector)
        return out

    def bundles(self) -> List[SynapticBundle]:
        """适配器的 frozen 换能束。"""
        return [ad.bundle for ad in self.adapters]

    def capacitors(self) -> List[Tuple[str, Capacitor, Optional[float]]]:
        """(标签, Capacitor, r_leak) 三元组；无泄漏路径者 r_leak=None。

        比较器无电容（无状态 NMDA 检测器）——如实不出现在此清单。
        """
        out: List[Tuple[str, Capacitor, Optional[float]]] = []
        for i, g in enumerate(self.gates):
            out.append((f"gate[{i}]._gate_cap", g._gate_cap, g.r_leak))
        for i, k in enumerate(self.kernels):
            out.append((f"kernel[{i}]._hist_cap", k._hist_cap, k.r_leak))
        return out

    def clamp_heats(self) -> List[Tuple[str, float]]:
        """门的 Zener 钳位累积热（既有只读记账字段）。"""
        return [(f"gate[{i}]", g.clamp_heat) for i, g in enumerate(self.gates)]


# ─────────────────────────────────────────────────────────────────────
# 2. KernelEnergyProbe — ℒ 只读观察者
# ─────────────────────────────────────────────────────────────────────

@dataclass
class KernelEnergyProbe:
    """TYPE:INFRA — 𝔈 能量账本（观察，永不修改；同 EntropyLedger 语义）。

    用法（与链路 step 同节拍）：
        probe = KernelEnergyProbe()
        for t in range(N):
            ...链路各元件 step...
            probe.record(census, dt)
        report = probe.summary()
    """

    total_steps: int = 0
    total_time: float = 0.0
    # 神经元侧（Neuron 口径）
    total_neuron_heat: float = field(default=0.0)
    # 电容泄漏耗散积分 Σ V²/R·dt（推算，只读）
    total_leak_dissipation: float = field(default=0.0)
    # 采样轨迹（每步一点；供审计画像/断言）
    neuron_energy_trace: List[float] = field(default_factory=list, repr=False)
    cap_energy_trace: List[float] = field(default_factory=list, repr=False)

    def record(self, census: KernelCensus, dt: float) -> None:
        self.total_steps += 1
        self.total_time += dt

        neuron_energy = 0.0
        for n in census.neurons():
            neuron_energy += n.energy
            # DIMENSION (DEG-024, 外部评判 2026-09-07 实测发现):
            # Neuron.heat_output = energy per simulation step（该步实际扣除
            # 的能量 actual_drain，见 neuron.py step() 末段），NOT power——
            # 严禁再乘 dt（旧实现 `* dt` 导致账本少记 1000×，ratio 恰为
            # dt=0.001）。跨账本守恒由 T-KL-5 对 Σ n._cumulative_heat_out
            # 增量以浮点级容差守卫。
            self.total_neuron_heat += n.heat_output

        cap_energy = 0.0
        for _label, cap, r_leak in census.capacitors():
            c = max(cap.capacitance, _MIN_CAPACITANCE)
            cap_energy += 0.5 * cap.charge * cap.charge / c   # E = Q²/2C
            if r_leak is not None and r_leak > 0.0:
                v = cap.voltage
                self.total_leak_dissipation += (v * v / r_leak) * dt  # V²/R·dt

        self.neuron_energy_trace.append(neuron_energy)
        self.cap_energy_trace.append(cap_energy)

    def summary(self, census: Optional[KernelCensus] = None) -> Dict:
        """账目汇总；传入 census 时附上钳位热终值（累积器在门上）。"""
        out = {
            "total_steps": self.total_steps,
            "total_time": self.total_time,
            "total_neuron_heat": self.total_neuron_heat,
            "total_leak_dissipation": self.total_leak_dissipation,
            "final_neuron_energy": (self.neuron_energy_trace[-1]
                                    if self.neuron_energy_trace else 0.0),
            "final_cap_energy": (self.cap_energy_trace[-1]
                                 if self.cap_energy_trace else 0.0),
            # 诚实边界声明（ℒ EXISTS_PARTIAL 的原因，随账目一起输出）
            "not_modeled": "MOSFET conduction/switching dissipation",
        }
        if census is not None:
            out["clamp_heat"] = {label: h for label, h in census.clamp_heats()}
        return out

    def has_nan(self) -> bool:
        return any(math.isnan(x)
                   for x in self.neuron_energy_trace + self.cap_energy_trace)


# ─────────────────────────────────────────────────────────────────────
# 3. K/𝒞 JSON 快照（R-E0-1 裁定：契约代码 + JSON 快照）
# ─────────────────────────────────────────────────────────────────────

def _address_record(addr) -> Dict:
    """地址→可序列化谱系记录（递归父谱系只记 uid，避免深拷贝整棵树）。"""
    rec = {"uid": addr.uid, "domain": addr.domain}
    parents = getattr(addr, "parent_addresses", None)
    if parents is not None:
        rec["parents"] = [p.uid for p in parents]
        rec["generation_depth"] = addr.generation_depth
    return rec


def snapshot_kernel(census: KernelCensus, stamp: str = "") -> Dict:
    """𝔈 的 K/𝒞 持久化记录（记录，非载体——不允许写回实例状态）。"""
    components = []
    for ad in census.adapters:
        components.append({
            "role": "relation_event_adapter",
            "class": type(ad).__name__,
            "address": _address_record(ad.generator_address),
            "neurons": [ad.input_neuron.config.neuron_id,
                        ad.collector.config.neuron_id],
            "bundle": {
                "bundle_id": ad.bundle.config.bundle_id,
                "learning_rule": ad.bundle.config.learning_rule,
                "initial_weight": ad.bundle.config.initial_weight,
                "weight_max": ad.bundle.config.weight_max,
                "synapse_gain": ad.bundle.config.synapse_gain,
                "physical_seed": ad.bundle.config.physical_seed,
            },
            "collector_capacitance": ad.collector.config.capacitance,
        })
    for g in census.gates:
        components.append({
            "role": "entry_gate", "class": type(g).__name__,
            "address": _address_record(g.generator_address),
            "params": {"capacitance": g.capacitance, "r_leak": g.r_leak,
                       "v_clamp": g.v_clamp, "theta_gate": g.theta_gate,
                       "q_spike": g.q_spike, "gm_clamp": g.gm_clamp},
        })
    for k in census.kernels:
        components.append({
            "role": "history_kernel", "class": type(k).__name__,
            "address": _address_record(k.generator_address),
            "params": {"capacitance": k.capacitance, "r_leak": k.r_leak},
        })
    for c in census.comparators:
        components.append({
            "role": "theta_comparator", "class": type(c).__name__,
            "address_i": _address_record(c.address_i),
            "address_j": _address_record(c.address_j),
            "params": {"theta_h": c.theta_h, "theta_g": c.theta_g, "gm": c.gm},
        })
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "kernel_kind": "c_ro_pair_stack",
        "stamp": stamp,
        "components": components,
        "qualification_refs": [
            "tss/QUALIFICATION_LEDGER.md#C1", "tss/QUALIFICATION_LEDGER.md#E0"],
        "contract_ref": "tss/events/event_core_contract.py",
        "note": ("record-only: rebuilding instances must go through "
                 "constructors; direct state write-back is forbidden "
                 "(E-2 injection discipline)"),
    }


def write_snapshot(snap: Dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2, sort_keys=True)


def load_snapshot(path: str) -> Dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
