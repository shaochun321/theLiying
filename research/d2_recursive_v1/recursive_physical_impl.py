"""recursive_physical_impl.py — D2-1 StepC：递归关系结构的物理实现
𝒞_{ρ₂}：χ_ρ^(1)+χ_23^(0) → 𝒩 → RelationInputNeuron → frozen
SynapticBundle → RelationCell_2。

TYPE:HYBRID（research/ 层组装；全部元件为既有 production 原语，零母本
修改）。结构模板复用 D2-0 relation_physical_impl（方案 §10 明确允许：
RelationInputNeuron / frozen SynapticBundle / RelationCell architecture
可复用），但 𝒞_{ρ₂} 是**新的物理实例**——g_rel2 由 calibration_rc2
新鲜 adaptive boundary 标定，禁止抄 D2-0 的 g_rel=0.25/θ=2.6164/
rearm=456（§10 禁令，机器兑现：本文件不 import 那些数值）。

RULES.md 强制三问：

  Q1 生物对应物：
    与 D2-0 RelationCell 同一 BIO 家族——树突符合检测/慢时间尺度关联
    积分器（REF: Schiller et al. 2000 Nature 404:285 NMDA 树突棘波符合
    检测；REF: Wang 2002 Neuron 36:955 NMDA 慢积分 τ~100-500ms）。
    递归输入侧：χ_ρ^(1) 经与基础发生同族的相位驱动 ϑ 进入（方案 §6：
    复用 ϑ_ρ(t) 与 τ_ρ^phys，不新增 N4/N5）。

  Q2 物理结构：
    ϑ_ρ(t)  ─→ RelationInputNeuron_R ─→ frozen SynapticBundle_R ─┐
                                                                  ├→ RelationCell_2(x_ρ₂)
    ϑ_23(t) ─→ RelationInputNeuron_C ─→ frozen SynapticBundle_C ─┘
    两束电流求和后单次 cell.step（somatosensory/chain.py:467 先例）。
    Sources/Targets 全是真实 Neuron 对象；传播全经
    SynapticBundle.propagate()。
    驱动展开 = tss.adapters.relation_replay_adapter.build_phase_drive
    ——**同一函数**同时消费 RelationOccurrencePortV1（depth-1）与
    site23 的 occurrence 窗（depth-0），RC-1 typed acceptance 的机器
    兑现点：递归消费无手工解包、无语义判断。

  Q3 参数依据：
    - cell τ = capacitance×r_leak = 0.1×5.0 = 0.5 s：输入窗时距域与
      D2-0 同量级（关系窗 ~1.35s / site23 窗 ~0.64s / 间隙 0.19~0.61s），
      沿用 Wang 2002 慢积分锚定；τ_decay2 由标定实测确认（偏离>2× 登记）。
    - bundle initial_weight=1.0 frozen（关系换能系数非可塑，transducer
      先例）；synapse_gain=g_rel2 由 calibration_rc2.py adaptive boundary
      search 新鲜标定（≤10 评估，§22/§23）。
    - physical_seed=84251（无语义数值，≠ D2-0 的 73142——新物理实例
      独立扰动）**两束相同** ⇒ R/C 通道增益对称——E2 降深替换/单通道
      对照不被通道不对称混淆（设计约束登记，非调参）。
    - cell 其余 config 沿 D2-0/transducer 先例（vdd=2.0/r_supply=0.01/
      inertia=0.0）；activation 钳位 ±10=母本既有约定；PowerRail energy
      =账本载体。

## 访问纪律（方案 §5）

  本模块只消费 RelationOccurrencePortV1 / site23 occurrence manifest
  暴露的字段——不回读 D2-0 RelationCell 微观内部态、不读 G0 neuron
  state（DIAGNOSTIC_INTERVENTION 实验在 a8v2_attack.py 单独登记）。

## COMPUTE_BUDGET

  physical_trajectories = 0（消费 StepB IMMUTABLE 缓存）
  replays/标定评估 = 调用方登记
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from d21_common import DT_G  # noqa: E402  (path setup side-effect included)
from nexus_v1.components.neuron import Neuron, NeuronConfig  # noqa: E402
from nexus_v1.circuit.bundle import SynapticBundle, BundleConfig  # noqa: E402
from tss.relations.relation_event_adapter import RelationInputNeuron  # noqa: E402
from tss.adapters.relation_replay_adapter import build_phase_drive  # noqa: E402

_PHYSICAL_SEED = 84251   # 无语义；两束相同=通道对称；≠ D2-0 实例（Q3）
T_TOTAL = 8000
X_CLAMP = 10.0


@dataclass
class Relation2Parts:
    tin_r: RelationInputNeuron   # depth-1 关系发生通道
    tin_c: RelationInputNeuron   # depth-0 site23 通道
    bundle_r: SynapticBundle
    bundle_c: SynapticBundle
    cell: Neuron


def build_relation2(g_rel2: float, tau_cell: float = 0.5) -> Relation2Parts:
    tin_r = RelationInputNeuron("d21_r")
    tin_c = RelationInputNeuron("d21_c")
    cell = Neuron(NeuronConfig(
        neuron_id="d21_relation_cell_2",
        capacitance=0.1, r_leak=tau_cell / 0.1,   # τ = C×R
        inertia=0.0, vdd=2.0, r_supply=0.01, spiking=False))
    mk = lambda bid, src: SynapticBundle(BundleConfig(  # noqa: E731
        bundle_id=bid, learning_rule="frozen", initial_weight=1.0,
        synapse_gain=g_rel2, bundle_role="feedforward",
        physical_seed=_PHYSICAL_SEED), [src], [cell])
    return Relation2Parts(tin_r, tin_c, mk("d21_rel_r2cell", tin_r),
                          mk("d21_rel_c2cell", tin_c), cell)


def step_relation2(p: Relation2Parts, yr: float, yc: float,
                   dt: float = DT_G) -> float:
    """物理链一步：换能→两束传播→求和→cell 单次 step。"""
    p.tin_r.step(yr, dt)
    p.tin_c.step(yc, dt)
    cr = p.bundle_r.propagate()
    cc = p.bundle_c.propagate()
    i_total = (cr[0] if cr else 0.0) + (cc[0] if cc else 0.0)
    p.cell.step(i_total, dt)
    return p.cell.activation


def recursive_drives(rho_ports: Sequence, site23_windows: Sequence,
                     t_total: int = T_TOTAL):
    """𝒩：typed 端口 → 双通道相位驱动（同一 build_phase_drive 消费
    depth-1 与 depth-0 端口——RC-1 typed acceptance）。空序列=全零通道。"""
    dr = build_phase_drive(t_total, DT_G, rho_ports)
    dc = build_phase_drive(t_total, DT_G, site23_windows)
    return dr, dc


def run_relation2(rho_ports: Sequence, site23_windows: Sequence,
                  g_rel2: float, tau_cell: float = 0.5,
                  parts: Optional[Relation2Parts] = None,
                  t_total: int = T_TOTAL
                  ) -> Tuple[List[float], dict, Relation2Parts]:
    """整条组合 replay：返回 (x_ρ₂(t), 账本, parts)。"""
    dr, dc = recursive_drives(rho_ports, site23_windows, t_total)
    p = parts if parts is not None else build_relation2(g_rel2, tau_cell)
    neurons = (p.tin_r, p.tin_c, p.cell)
    e0 = sum(n.energy for n in neurons)
    xs = []
    for sr, sc in zip(dr, dc):
        xs.append(step_relation2(p, sr.value, sc.value))
    e1 = sum(n.energy for n in neurons)
    ledger = {"g_rel2": g_rel2, "x_peak": max(xs), "x_end": xs[-1],
              "e_start": e0, "e_end": e1, "energy_drop": e0 - e1,
              "transport_cost": p.bundle_r.transport_cost
              + p.bundle_c.transport_cost}
    return xs, ledger, p
