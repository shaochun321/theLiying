"""world_v2_core.py — World v2 episode 采样层（W1，MAINLINE V2 第一建设轮）。

TYPE:INFRA（research/ 层包装；production 组件只复用零改动——§55；
不被 nexus/tss import）

依据：外部《MAINLINE V2 — W1》§2/§4/§6/§37-§38（经评判 B1-B6 修正采纳）。

## 对象与职责（§6 模块化，无 God Object）

  WorldEpisodeSpec — 纯参数描述（Phase A 产物）：初始条件+物理参数+源
                     计划+边界配置+seed+dt。不含任何动力学。
  SourceSpec       — (node, energy, power, t_start) 纯参数。
  WorldSampler     — Phase A：从预登记合法域 Θ_legal 条件采样 spec。
                     B5 纪律：random.Random(seed) 独立实例，不碰全局 RNG。
  WorldEpisode     — Phase B：组装 production 组件（ThermalCell/
                     ThermalLink/ThermalFieldGraph + DynamicHeatSource）
                     并只按物理方程推进；开始后不再修改参数（§4）。
  BoundaryView     — §38 结构隔离：只接收 episode 喂给它的
                     boundary_frame 纯元组，不持有 graph/cells/sources。
  WorldLedger      — §30 能量谱系：E_field/E_source/E_injected/E_leaked/
                     conservation_residual 每步记录（复用图内建账本）。

## Θ_legal（预登记合法域——§34 只声明域，不找最佳点）

  n_nodes ∈ {3,5,10,20}（链拓扑；ring/grid 属后续）
  每边 κ ∈ [0.01, 0.2]（log-均匀）
  r_leak_ambient ∈ [20, 2000]（log-均匀；**与 κ 独立采样 = M3 解绑**）
  源数 ∈ {1,2,3}；node ∈ [0,N)；E ∈ [30, 3000]（log-均匀）；
  P ∈ [0.2, 5.0]；t_start ∈ [0, 500)
  dt = 1.0；t_total = 2000；boundary_config ∈ {FULL, REDUCED(1~2 节点)}

  条件 c 只限制以上物理范围；不含任何 occurrence/G0/relation 条件（§3）。

## 语义纪律（§43/§44）

  一切 id 为纯物理地址（episode_id/node/source 序号），只做
  lineage/audit/replay，不参与动力学。无语义标签。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..')))

from nexus_v1.components.dynamic_thermal_field import (  # noqa: E402
    ThermalCell, ThermalFieldGraph, ThermalLink)
from nexus_v1.components.semiconductor import Capacitor  # noqa: E402
from nexus_v1.components.thermal_source_coupling import (  # noqa: E402
    DynamicHeatSource)


@dataclass(frozen=True)
class SourceSpec:
    node: int
    energy: float
    power: float
    t_start: int


@dataclass(frozen=True)
class WorldEpisodeSpec:
    episode_id: str
    seed: int
    n_nodes: int
    kappas: Tuple[float, ...]          # 每边独立 κ（链：N-1 条）
    r_leak_ambient: float
    sources: Tuple[SourceSpec, ...]
    boundary_config: str               # "FULL" | "REDUCED"
    boundary_nodes: Tuple[int, ...]
    dt: float = 1.0
    t_total: int = 2000
    initial_charges: Tuple[float, ...] = ()   # 空=全静息；否则每节点初始 Q


THETA_LEGAL = {
    "n_nodes": (3, 5, 10, 20),
    "kappa": (0.01, 0.2),              # log-uniform
    "r_leak": (20.0, 2000.0),          # log-uniform，独立于 κ（M3）
    "n_sources": (1, 2, 3),
    "energy": (30.0, 3000.0),          # log-uniform
    "power": (0.2, 5.0),
    "t_start": (0, 500),
    "dt": 1.0,
    "t_total": 2000,
}


class WorldSampler:
    """Phase A：条件采样。独立 RNG（B5），同 seed 逐位复现。"""

    def __init__(self, seed: int):
        self._rng = random.Random(seed)
        self._seed = seed

    def _log_uniform(self, lo: float, hi: float) -> float:
        import math
        return math.exp(self._rng.uniform(math.log(lo), math.log(hi)))

    def sample(self, episode_id: str) -> WorldEpisodeSpec:
        rng, th = self._rng, THETA_LEGAL
        n = rng.choice(th["n_nodes"])
        kappas = tuple(self._log_uniform(*th["kappa"]) for _ in range(n - 1))
        r_leak = self._log_uniform(*th["r_leak"])
        n_src = rng.choice(th["n_sources"])
        sources = tuple(SourceSpec(
            node=rng.randrange(n),
            energy=self._log_uniform(*th["energy"]),
            power=rng.uniform(*th["power"]),
            t_start=rng.randrange(*th["t_start"]),
        ) for _ in range(n_src))
        if rng.random() < 0.5:
            cfg, bnodes = "FULL", tuple(range(n))
        else:
            k = rng.choice((1, 2))
            bnodes = tuple(sorted(rng.sample(range(n), k)))
            cfg = "REDUCED"
        return WorldEpisodeSpec(
            episode_id=episode_id, seed=self._seed, n_nodes=n,
            kappas=kappas, r_leak_ambient=r_leak, sources=sources,
            boundary_config=cfg, boundary_nodes=bnodes,
            dt=th["dt"], t_total=th["t_total"])


class BoundaryView:
    """§38：只持纯元组帧；不持有任何 World 内部对象引用。"""

    def __init__(self, config: str, nodes: Tuple[int, ...]):
        self.config = config
        self.nodes = nodes
        self.frames: List[Tuple[float, ...]] = []

    def append(self, frame: Tuple[float, ...]) -> None:
        self.frames.append(frame)


class WorldLedger:
    """§30 能量谱系（复用图内建账本，不重复计账）。"""

    def __init__(self):
        self.rows: List[Dict[str, float]] = []

    def record(self, t: int, graph: ThermalFieldGraph,
               sources: List[DynamicHeatSource]) -> None:
        self.rows.append({
            "t": t,
            "E_field": graph.total_energy(),
            "E_source_remaining": sum(s.energy_remaining for s in sources),
            "E_injected_cum": graph._total_injected,
            "E_leaked_cum": graph._total_leaked_ambient,
            "conservation_residual": graph.conservation_residual(),
        })


class WorldEpisode:
    """Phase B：纯物理推进。构造后参数冻结（§4）；无下游反馈通道。"""

    def __init__(self, spec: WorldEpisodeSpec):
        self.spec = spec
        cells = [ThermalCell(node_id=i, position=(float(i), 0.0, 0.0),
                             capacitor=Capacitor(capacitance=1.0))
                 for i in range(spec.n_nodes)]
        if spec.initial_charges:
            for c, q in zip(cells, spec.initial_charges):
                c.capacitor.charge = q
        links = [ThermalLink(i=i, j=i + 1, kappa=spec.kappas[i])
                 for i in range(spec.n_nodes - 1)]
        self.graph = ThermalFieldGraph(
            cells, links, r_leak_ambient=spec.r_leak_ambient)
        self.sources = [DynamicHeatSource(
            position=(float(s.node), 0.0, 0.0),
            energy_remaining=s.energy, power=s.power)
            for s in spec.sources]
        self._t = 0
        self.ledger = WorldLedger()

    def full_state(self) -> Tuple[float, ...]:
        return tuple(self.graph.cells[i].temperature
                     for i in range(self.spec.n_nodes))

    def boundary_frame(self) -> Tuple[float, ...]:
        return tuple(self.graph.cells[i].temperature
                     for i in self.spec.boundary_nodes)

    def step(self) -> None:
        inj: Dict[int, float] = {}
        for s_spec, src in zip(self.spec.sources, self.sources):
            if self._t >= s_spec.t_start:
                p = src.release(self.spec.dt)
                if p > 0.0:
                    inj[s_spec.node] = inj.get(s_spec.node, 0.0) + p
        self.graph.step(self.spec.dt, inj)
        self._t += 1

    def run(self, record_full: bool = False):
        """跑满 t_total；返回 (BoundaryView, ledger, full_traj|None)。"""
        bv = BoundaryView(self.spec.boundary_config,
                          self.spec.boundary_nodes)
        full = [] if record_full else None
        for t in range(self.spec.t_total):
            self.step()
            bv.append(self.boundary_frame())
            if record_full:
                full.append(self.full_state())
            self.ledger.record(t, self.graph, self.sources)
        return bv, self.ledger, full
