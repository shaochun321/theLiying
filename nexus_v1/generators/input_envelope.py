"""nexus_v1.generators.input_envelope — P2-A1a 生成元核心输入包络扫描工具。

TYPE:INFRA — 本模块无 BIO/SEMI 对应物；它是纯测量/标定工具，类比实验室
里对一个换能器做剂量-响应曲线扫描（dose-response sweep），不是新的物理
机制。它只反复调用 `BaseGenerator.tick()`（既有生产代码）并读出既有量
（`closure.events`/`closure.is_active`/`sense()`），不新建 Neuron/Bundle，
不修改生成元本身的行为。

方案依据：`cell-cell/交叉比对/评判_P2A1顺序倒置修正_2026-07-21.md` §一
（P2-A1 拆分为 P2-A1a/P2-A1b，P2-A1a 只用现有 `BaseGenerator.feed()` 扫描
输入端口 `u`，不涉及皮肤/κ，回答"十神经元生成元本身能消费什么范围的
输入"）。测量对象定义：`u ↦ (L_first, N_occ, f_occ, t_down, t_rearm,
S_sat)`。

**设计纪律**：本模块只产出结构化测量数据，不做任何边界分类（不判断
"这算 u_work 还是 u_sat"）——分类留给调用方（`exp_P2A1a_input_envelope_
scan.py`）基于测量数据事后判定，遵守"model before tune"：不能让工具
自己悄悄替标定下结论。

`S_sat`（评判文档给出的符号，未给出精确定义）本模块操作化为"扫描窗口内
`collector.pre_trace` 的峰值"——复用本项目已有的峰值测量方法论
（`relations/probes.py` 的 `PeakDecayRestProbe.peak` 同样只追踪峰值，
`test_basegen_thermal_t0.py` 的 T-T0-3 已验证此法有效），不是凭空新造
一个物理量。

RULES.md 强制三问：

  Q1 生物对应物：
    无——纯标定/测量工具，同 `trajectory.py`/`structural_address.py` 的
    TYPE:INFRA 定位。

  Q2 物理结构：
    只反复调用既有 `BaseGenerator.tick()`/`.sense()`/`.closure.events`/
    `.closure.is_active`，不创建新对象，不修改生成元内部状态之外的
    任何东西。

  Q3 参数依据：
    无新物理参数——`u_levels`/`steps_per_level` 是调用方提供的实验设计
    参数（本次扫多宽、每档观测多久），不是标定结论。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence

from .base_generator import BaseGenerator


@dataclass(frozen=True)
class InputEnvelopePoint:
    """单个输入档位 `u` 的扫描结果——纯测量记录，不含任何分类结论。

    字段：
      u:                本档恒定驱动的输入端口值。
      n_occ:            扫描窗口内完成的 `Occurrence` 数量
                        （来自 `closure.events`，不重新计算）。
      l_first:          首次触发延迟——第一个 `Occurrence.t_up`（若窗口内
                        从未触发过，为 None，即"静默"的直接证据）。
      mean_t_active:    窗口内各次发生的平均 ACTIVE 时长
                        （`t_down - t_up` 的均值；`n_occ==0` 时为 None）。
      f_occ:            发生频率 = `n_occ / steps_observed`。
      peak_pre_trace:   扫描窗口内 collector `pre_trace` 的峰值（`S_sat`
                        的操作化定义，见模块 docstring）。
      ends_active:      扫描结束时闭合状态机是否仍处 ACTIVE/REFRACTORY
                        （即从未退出过）——捕捉"持续饱和不退出"这一
                        T-P2AG-5 已验证过的边界情形，是判断"是否已进入
                        u_sat 区"的关键证据之一。
      steps_observed:   本档实际驱动的步数。
    """
    u: float
    n_occ: int
    l_first: Optional[int]
    mean_t_active: Optional[float]
    f_occ: float
    peak_pre_trace: float
    ends_active: bool
    steps_observed: int


def scan_input_envelope(
    build_generator: Callable[[], BaseGenerator],
    u_levels: Sequence[float],
    dt: float,
    steps_per_level: int,
) -> List[InputEnvelopePoint]:
    """对 `u_levels` 里每个输入档位做一次独立扫描，返回按输入顺序排列的
    `InputEnvelopePoint` 列表。

    每个档位调用一次 `build_generator()` 取得**全新**的 `BaseGenerator`
    句柄——生成元"相同输入、不同历史可导致不同响应"是既有设计特性
    （见 `occurrence.py` 模块 docstring），标定不同输入档位时必须从同一
    干净初始状态出发，否则跨档位比较会被历史依赖污染。`build_generator`
    由调用方提供（解耦本模块与 `VariantCircuit`/`wrap_base_generator`
    的具体构造细节）。
    """
    results: List[InputEnvelopePoint] = []
    for u in u_levels:
        handle = build_generator()
        peak = 0.0
        for t in range(steps_per_level):
            handle.tick(u, dt, t)
            v = handle.sense()
            if v > peak:
                peak = v

        events = handle.closure.events
        n_occ = len(events)
        l_first = events[0].t_up if events else None
        mean_t_active = (
            sum(e.t_down - e.t_up for e in events) / n_occ if n_occ else None
        )
        f_occ = n_occ / steps_per_level if steps_per_level else 0.0

        results.append(InputEnvelopePoint(
            u=u, n_occ=n_occ, l_first=l_first, mean_t_active=mean_t_active,
            f_occ=f_occ, peak_pre_trace=peak, ends_active=handle.closure.is_active,
            steps_observed=steps_per_level,
        ))
    return results
