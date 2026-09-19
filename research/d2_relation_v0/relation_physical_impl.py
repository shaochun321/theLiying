"""relation_physical_impl.py — D2-0 Step3：关系过程的物理实现
𝒞_{ρ,0}：ŷ → RelationInputNeuron → frozen SynapticBundle → RelationCell。

TYPE:HYBRID（research/ 层组装；全部元件为既有 production 原语，零母本
修改）。E-3 硬合同兑现：无 inject/无直接设电荷/无 Python-only 状态——
x_ρ 由真实 RC 膜电容承担。

RULES.md 强制三问：

  Q1 生物对应物：
    RelationCell = 树突符合检测/慢时间尺度关联积分器。
    REF: Schiller et al. 2000 Nature 404:285 — NMDA 树突棘波符合检测
         （与既有 relation collector 同一 BIO 家族，
         tss/relations/relation_event_adapter.py 先例）。
    REF: Wang 2002 Neuron 36:955 — NMDA 慢积分（τ~100-500ms）支撑
         跨输入时距的时间整合；本 cell τ=0.5s 落在该尺度并匹配
         parent delay 域 [0.2, 1.5]s。
    RelationInputNeuron = NMDA 电流受体侧换能边界（该类自有 BIO 注释）。

  Q2 物理结构：
    ϑ_a(t) ─→ RelationInputNeuron_a ─→ frozen SynapticBundle_a ─┐
                                                                 ├→ RelationCell(x_ρ)
    ϑ_b(t) ─→ RelationInputNeuron_b ─→ frozen SynapticBundle_b ─┘
    两束电流求和后单次 cell.step（somatosensory/chain.py:467 既有先例：
    多束汇聚目标先求和再一次 step，避免同一 dt 内重复积分泄漏）。
    Sources/Targets 全是真实 Neuron 对象；传播全经
    SynapticBundle.propagate()。

  Q3 参数依据：
    - cell τ = capacitance×r_leak = 0.1×5.0 = 0.5 s：匹配 parent delay
      域（0.2-1.5s）与 NMDA 慢积分尺度（Wang 2002）；RC 时间尺度失配
      教训（Ω 层）前置规避——τ_decay 由 calibration 实测确认。
    - bundle initial_weight=1.0 frozen（关系换能系数非可塑，同
      transducer bundle 先例）；synapse_gain=g_rel 由 calibration.py
      adaptive boundary search 标定（五元组输出，禁抄 G0 数值 §22）。
    - physical_seed=73142（无语义数值，S0-bX1 纪律）**两束相同** ⇒
      两通道 ±25% 初始扰动一致，A/B 增益对称——C3 vs C4 方向对比不被
      通道不对称混淆（登记为设计约束，非调参）。
    - cell 其余 config 沿 transducer 先例（vdd=2.0/r_supply=0.01/
      inertia=0.0），activation 钳位 ±10=母本既有约定（R3 有限响应）；
      PowerRail energy=R4 账本载体。

## COMPUTE_BUDGET

  physical_trajectories = 0（消费 IMMUTABLE_CACHE 的 ports）
  replays = 调用方登记；interventions = 0
"""
from __future__ import annotations

import csv
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..')))

from d2_common import DATA, DT_G  # noqa: E402
from nexus_v1.components.neuron import Neuron, NeuronConfig  # noqa: E402
from nexus_v1.circuit.bundle import SynapticBundle, BundleConfig  # noqa: E402
from tss.relations.relation_event_adapter import RelationInputNeuron  # noqa: E402
from tss.adapters.relation_replay_adapter import build_phase_drive  # noqa: E402

_PHYSICAL_SEED = 73142   # 无语义；两束相同=通道对称（Q3）
T_TOTAL = 8000
X_CLAMP = 10.0           # 母本 Neuron.step 激活钳位（R3）


@dataclass(frozen=True)
class PortWindow:
    """驱动窗（duck-typed 满足 build_phase_drive 所需 t_up/t_rearm）。"""
    t_up: int
    t_rearm: int
    occurrence_id: str = ""


@dataclass
class RelationParts:
    tin_a: RelationInputNeuron
    tin_b: RelationInputNeuron
    bundle_a: SynapticBundle
    bundle_b: SynapticBundle
    cell: Neuron


def build_relation(g_rel: float, tau_cell: float = 0.5) -> RelationParts:
    tin_a = RelationInputNeuron("d2_a")
    tin_b = RelationInputNeuron("d2_b")
    cell = Neuron(NeuronConfig(
        neuron_id="d2_relation_cell",
        capacitance=0.1, r_leak=tau_cell / 0.1,   # τ = C×R
        inertia=0.0, vdd=2.0, r_supply=0.01, spiking=False))
    mk = lambda bid, src: SynapticBundle(BundleConfig(  # noqa: E731
        bundle_id=bid, learning_rule="frozen", initial_weight=1.0,
        synapse_gain=g_rel, bundle_role="feedforward",
        physical_seed=_PHYSICAL_SEED), [src], [cell])
    return RelationParts(tin_a, tin_b, mk("d2_rel_a2cell", tin_a),
                         mk("d2_rel_b2cell", tin_b), cell)


def step_relation(p: RelationParts, ya: float, yb: float,
                  dt: float = DT_G) -> float:
    """物理链一步：换能→两束传播→求和→cell 单次 step（chain.py 先例）。"""
    p.tin_a.step(ya, dt)
    p.tin_b.step(yb, dt)
    ca = p.bundle_a.propagate()
    cb = p.bundle_b.propagate()
    i_total = (ca[0] if ca else 0.0) + (cb[0] if cb else 0.0)
    p.cell.step(i_total, dt)
    return p.cell.activation


def load_port_windows() -> Dict[str, Dict[str, List[PortWindow]]]:
    """从 parent manifest 读全部驱动窗：{traj: {parent: [PortWindow…]}}。"""
    out: Dict[str, Dict[str, List[PortWindow]]] = {}
    with open(os.path.join(DATA, 'occurrence_parent_manifest.csv'),
              newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            out.setdefault(r["traj"], {}).setdefault(r["parent"], []).append(
                PortWindow(int(r["t_up"]), int(r["t_rearm"]),
                           r["occurrence_id"]))
    return out


def drives_for(traj: str, windows=None,
               ch_a: str = "A", ch_b: str = "B",
               t_total: int = T_TOTAL):
    """一条轨迹的双通道 replay 驱动序列（无该通道 occurrence 则全零）。"""
    if windows is None:
        windows = load_port_windows()
    w = windows.get(traj, {})
    da = build_phase_drive(t_total, DT_G, w.get(ch_a, []))
    db = build_phase_drive(t_total, DT_G, w.get(ch_b, []))
    return da, db


def run_relation(traj: str, g_rel: float, tau_cell: float = 0.5,
                 windows=None, ch_a: str = "A", ch_b: str = "B",
                 parts: RelationParts = None
                 ) -> Tuple[List[float], dict, RelationParts]:
    """整条轨迹 replay：返回 (x_ρ(t) 序列, 账本, parts)。"""
    da, db = drives_for(traj, windows, ch_a, ch_b)
    p = parts if parts is not None else build_relation(g_rel, tau_cell)
    neurons = (p.tin_a, p.tin_b, p.cell)
    e0 = sum(n.energy for n in neurons)
    xs = []
    for sa, sb in zip(da, db):
        xs.append(step_relation(p, sa.value, sb.value))
    e1 = sum(n.energy for n in neurons)
    ledger = {"traj": traj, "g_rel": g_rel, "x_peak": max(xs),
              "x_end": xs[-1], "e_start": e0, "e_end": e1,
              "energy_drop": e0 - e1,
              "transport_cost": p.bundle_a.transport_cost
              + p.bundle_b.transport_cost}
    return xs, ledger, p
