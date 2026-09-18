"""g0r0_common.py — G0-R0 共享层：MultiRateScheduler + frozen G0 驱动器 +
timestamped 边界录制。

TYPE:INFRA（research/ 层；production READ_ONLY——G0 只运行不修改，§37）

依据：外部《G0-R0 方案》§6-§10/§23（经评判 D1-D6 修正采纳）。

## MultiRateScheduler（§6，非 GlobalClock——只做 time coordination，§24）

  canonical: dt_B=1.0 s, dt_G=0.001 s ⇒ N_sub=1000（整数校验，余数拒绝）。
  边界保持策略（§7）：
    S0 zero-order hold：区间 [n,n+1) 内 Y(t)=Y_n（因果，零延迟）
    S1 linear interp  ：Y(t)=Y_n+α(Y_{n+1}−Y_n)——**因果性登记**：
                        需要下一样本 ⇒ 实现上等价于一个 dt_B 的延迟
                        （replay/离线合法；live 需显式 1 样本滞后）
    S2 resampled      ：World 以 dt_G 档重放产生真 Y(t_n+kΔt_G)
                        （参考基准，非 production 方案）
  candidate 调度（§9/§10）：
    A：U_T^(k)=S·(Y^(k)−Y_ref)（逐子步取保持策略产出的 Y^(k)）
    B0：整段保持 U_Ṫ=g·(Y_{n}−Y_{n−1})/dt_B（1s 速率，1000 子步不变）
    B1：逐子步重算 U_Ṫ^(k)=g·(Y^(k)−Y^(k−1))/dt_G（消费保持策略输出）
    结构性预期：S1 下 B1 在区间内=B0（线性斜率恒定），仅样本边界处不同。

## timestamped 边界帧（§23）

  每帧 (t_phys, dt_boundary, sample_id, y)；G0 子步可得
  (t_phys, dt_generator, substep_index)。不依赖 _step_serial 跨层计时。
"""
from __future__ import annotations

import os
import sys
from typing import Callable, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..',
                                                'world_v2')))

from world_v2_core import (  # noqa: E402
    SourceSpec, WorldEpisode, WorldEpisodeSpec)

S_CANON = 0.00137531
Y_REF = 0.0
G_CANON = 0.275062


class MultiRateScheduler:
    """把 dt_B 采样的边界序列展开为 dt_G 子步输入序列。纯函数式，无全局态。"""

    def __init__(self, dt_boundary: float = 1.0, dt_generator: float = 0.001):
        ratio = dt_boundary / dt_generator
        n_sub = round(ratio)
        if abs(ratio - n_sub) > 1e-9:
            raise ValueError(f"N_sub 非整数: {ratio}（§6 拒绝隐式余数）")
        self.dt_b, self.dt_g, self.n_sub = dt_boundary, dt_generator, n_sub

    def expand(self, y_samples: List[float], strategy: str,
               y_fine: Optional[List[float]] = None) -> List[float]:
        """返回长度 (len(y_samples)-1)*n_sub 的子步边界值序列。
        区间 n 覆盖 (t_n, t_{n+1}]，子步 k=1..n_sub。"""
        out: List[float] = []
        if strategy == "S2":
            assert y_fine is not None and \
                len(y_fine) == (len(y_samples) - 1) * self.n_sub
            return list(y_fine)
        for n in range(len(y_samples) - 1):
            y0, y1 = y_samples[n], y_samples[n + 1]
            for k in range(1, self.n_sub + 1):
                if strategy == "S0":
                    out.append(y0)
                elif strategy == "S1":
                    out.append(y0 + (k / self.n_sub) * (y1 - y0))
                else:
                    raise ValueError(strategy)
        return out


def u_series_a(y_sub: List[float]) -> List[float]:
    return [S_CANON * (y - Y_REF) for y in y_sub]


def u_series_b0(y_samples: List[float], n_sub: int,
                dt_b: float) -> List[float]:
    out: List[float] = []
    for n in range(len(y_samples) - 1):
        # B0 整段保持：区间 n 用上一完成区间 [n-1,n] 的速率（保持因果）
        rate = G_CANON * (y_samples[n] - y_samples[n - 1]) / dt_b \
            if n > 0 else 0.0
        out.extend([rate] * n_sub)
    return out


def u_series_b1(y_sub: List[float], dt_g: float) -> List[float]:
    out, prev = [], None
    for y in y_sub:
        out.append(0.0 if prev is None else G_CANON * (y - prev) / dt_g)
        prev = y
    return out


def fresh_g0():
    from nexus_v1.circuit.variant_adapter import VariantCircuit
    from nexus_v1.components.structural_address import AddressRegistry
    from tss.generators import wrap_base_generator
    from tss.relations import FROZEN_THERMAL_SITES
    circuit = VariantCircuit()
    registry = AddressRegistry()
    handle = wrap_base_generator(
        circuit, FROZEN_THERMAL_SITES["t1_pair"]["a"], registry,
        polarity="warm", theta_down=0.001)
    handle.closure.rearm_min_steps = 500
    return handle


def drive_g0(u_sub: List[float], dt_g: float,
             sample_every: int) -> List[Tuple[float, ...]]:
    """把子步输入序列喂入 fresh G0（tick，MANUAL），每 sample_every 子步
    记录状态向量 (l1.act, hc.pre, ensemble pre…, collector.pre)。"""
    h = fresh_g0()
    states: List[Tuple[float, ...]] = []
    for k, u in enumerate(u_sub):
        h.tick(u, dt_g, k)
        if (k + 1) % sample_every == 0:
            states.append((h.l1.activation, h.hc.pre_trace,
                           *(n.pre_trace for n in h.ensemble),
                           h.collector.pre_trace))
    return states


def boundary_from_episode(spec: WorldEpisodeSpec,
                          node: int = 0) -> List[Tuple[float, float, int]]:
    """timestamped 边界帧 (t_phys, dt_b, sample_id)→值列表；含 t=0 初值。"""
    ep = WorldEpisode(spec)
    frames = [(0.0, spec.dt, 0, 0.0)]
    for t in range(spec.t_total):
        ep.step()
        frames.append(((t + 1) * spec.dt, spec.dt, t + 1,
                       ep.graph.cells[node].temperature))
    return frames


def ep_spec(n=5, kappa=0.05, r_leak=200.0, sources=None, t_total=60,
            dt=1.0, eid="g0r0"):
    return WorldEpisodeSpec(
        episode_id=eid, seed=-1, n_nodes=n,
        kappas=(kappa,) * (n - 1), r_leak_ambient=r_leak,
        sources=tuple(sources or [SourceSpec(0, 20.0, 1.0, 0)]),
        boundary_config="REDUCED", boundary_nodes=(0,),
        dt=dt, t_total=t_total)


def state_err(a: List[Tuple], b: List[Tuple]) -> float:
    import math
    num = sum((x - y) ** 2 for ra, rb in zip(a, b)
              for x, y in zip(ra, rb))
    den = sum(y * y for rb in b for y in rb)
    return math.sqrt(num / max(den, 1e-30))
