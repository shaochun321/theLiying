"""tss.relations.probes — 通用峰值/衰减/静息探针 + frozen 权重检查。

TYPE:INFRA

方案依据：cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md
《T0 —— 基线与夹具隔离》。

本模块把 `tests/test_thermal_coupling_generators.py`（Ω 层验证，
`_drive_points_synthetic_dT` / `test_frozen_weights_unchanged` 等）中
已验证过的探针方法论抽取为 T1~T4（温感轨）、M1~M4（运动轨）共用的
工具函数，避免每个 Phase 重复实现一套峰值追踪逻辑。

三类探针对应方案要求：
  - 峰值：驱动窗口内 `pre_trace` 的最大值（不是终态值——K+ 适应/爆发式
    发放会让终态值失真，必须追踪运行时最大值，同已有 Ω 层测试的
    `peak_pre_trace` 做法）。
  - 衰减：早期窗口均值 vs 晚期窗口均值对比（同 `test_level2_adaptation_present`
    的 early/late 均值比较）。
  - 静息：零输入驱动下，输出应为精确 0 或维持基线，不应有虚假发放。

frozen 权重检查：驱动前后对比 Memristor.w 逐项不变（<1e-12），同
`test_frozen_weights_unchanged`。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class PeakDecayRestProbe:
    """驱动一个可读 `pre_trace`/`activation` 的输出神经元 N 步，
    同时追踪峰值、早/晚期均值（衰减）、以及零输入下的静息基线。

    用法（典型接线，由调用方负责每步的具体传播逻辑）：
        probe = PeakDecayRestProbe()
        for step in range(n_steps):
            <驱动一步：propagate + neuron.step(...)>
            probe.record(collector.pre_trace)
        peak = probe.peak
        decayed = probe.is_decaying(early_frac=0.2, late_frac=0.2)
    """
    values: List[float] = field(default_factory=list)

    def record(self, value: float) -> None:
        self.values.append(value)

    @property
    def peak(self) -> float:
        """驱动窗口内的最大值，而非终态值（避免爆发式发放导致终态失真）。"""
        return max(self.values) if self.values else 0.0

    @property
    def n_steps(self) -> int:
        return len(self.values)

    def window_mean(self, start_frac: float, end_frac: float) -> float:
        n = self.n_steps
        if n == 0:
            return 0.0
        lo = int(n * start_frac)
        hi = max(lo + 1, int(n * end_frac))
        window = self.values[lo:hi]
        return sum(window) / len(window) if window else 0.0

    def is_decaying(self, early_frac: float = 0.2, late_frac: float = 0.2,
                     strict: bool = False) -> bool:
        """早期窗口均值是否显著高于晚期窗口均值（适应/衰减存在性检查）。

        strict=False（默认）：只要求 early_mean >= late_mean（不要求严格
        大于——某些生成元在稳态漂移小的情况下均值可能几乎相等，仍算未违反
        衰减假设）。strict=True 时要求 early_mean > late_mean 严格成立。
        """
        early = self.window_mean(0.0, early_frac)
        late = self.window_mean(1.0 - late_frac, 1.0)
        return (early > late) if strict else (early >= late)

    def is_resting_zero(self, tol: float = 1e-9) -> bool:
        """全窗口是否维持精确静息（用于零输入驱动场景）。"""
        return all(abs(v) <= tol for v in self.values)


def snapshot_weights(bundle) -> List[List[float]]:
    """拍摄 bundle._memristors 的权重快照（驱动前调用）。"""
    return [[m.w for m in row] for row in bundle._memristors]


def check_frozen_weights_against(
    bundle, snapshot: List[List[float]], tol: float = 1e-12
) -> Optional[str]:
    """驱动后调用：对比当前权重与 snapshot 是否逐项一致（<tol）。

    返回 None = 通过；否则返回描述第一处不一致的字符串。
    """
    for i_s, row in enumerate(bundle._memristors):
        for i_t, m in enumerate(row):
            before = snapshot[i_s][i_t]
            after = m.w
            if abs(after - before) >= tol:
                return (
                    f"Frozen bundle weight changed: source={i_s} target={i_t} "
                    f"before={before:.6f} after={after:.6f}"
                )
    return None
