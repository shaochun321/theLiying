"""nexus_v1.generators.occurrence — χ 闭合状态机与最小组织记录（P2-A 核心）。

TYPE:INFRA — 本模块无 BIO/SEMI 对应物本身；它是对既有神经元 `pre_trace`
信号的**状态机记账**，不构造任何新的 Neuron/SynapticBundle（Q2 见下）。

方案依据：`cell-cell/交叉比对/评判_反馈自然单位概念修正_2026-07-20.md`
§四(闭合合同)、§五(自然单位当前工作定义)。四轮交叉比对（203329→203750→
我方评判#1→211325→我方评判#2→反馈）已收敛的核心裁定：

    生成元完成一次闭合 χ ≠ 自然单位本身 𝔫

即本模块只交付"一次可辨识、可计数、带三边界的发生"，**不**冻结任何无量纲
测度/相位/占比字段——那是 P2-B 才需要验证的问题（见反馈 §5.3 禁止清单）。

RULES.md 强制三问：

  Q1 生物对应物：
    触发—退出—重新武装（trigger/exit/rearm）迟滞是标准的施密特触发器式
    去抖动模式，生物对应是感觉神经元的阈值调适（threshold accommodation）/
    不应期（refractory period）——持续刺激不产生无限次发放，短暂阈值附近
    抖动不被重复计数。这是通用生理学机制，不特定于某一受体。

  Q2 物理结构：
    本模块**不**新建 SynapticBundle 或 Neuron——它是纯粹读取既有
    `collector.pre_trace`（已由 `_init_quantum_thermal_pathways` 构造好的
    AND 门 collector 神经元产生）的状态机记账层。判断"是否新增结构"的标准
    （CLAUDE.md 结构构建原则）只约束"用 if/数学公式替代电路行为"——这里的
    if/else 是对**测量边界**的记账（何时算一次发生开始/结束），不是决定
    电路该如何响应输入，电路本身的响应完全由既有 SynapticBundle.propagate()
    + Neuron.step() 产生，本模块只在事后读数。

  Q3 参数依据：
    - `theta_up=0.01`：复用 `test_basegen_thermal_t1_real_occurrence.py:64`
      已验证的 `OCCURRENCE_THRESHOLD` 经验值（EXP-T1 沿用，非新造）。
    - `theta_down`：仓库中**没有任何已验证的迟滞下限值**——不能虚构。本轮
      设为 `0.1 * theta_up` 的保守占位（# EXP-P2A-001-PROVISIONAL），
      显式标记为**待标定**，必须由 P2-A1 输入工作区间扫描（u_on/u_work/
      u_sat 与 t_recovery 测量）替换，不是"调到能通过测试"的结论。
    - `rearm_min_steps=0`：本轮不引入额外不应期计时器（# EXP-P2A-002-
      PROVISIONAL）——迟滞带 [theta_down, theta_up] 本身已提供去抖动，
      是否需要额外的固定步数不应期，同样留给 P2-A1 标定后再决定，避免
      现在编造一个没有实验依据的整数。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional

from ..components.structural_address import GeneratedAddress

# EXP-T1 沿用：test_basegen_thermal_t1_real_occurrence.py:64 的 OCCURRENCE_THRESHOLD
_DEFAULT_THETA_UP = 0.01
# EXP-P2A-001-PROVISIONAL：待 P2-A1 工作区间扫描替换，此值只保证 theta_down < theta_up
_DEFAULT_THETA_DOWN = 0.1 * _DEFAULT_THETA_UP
# EXP-P2A-002-PROVISIONAL：不引入额外不应期计时器，待 P2-A1 后再评估是否需要
_DEFAULT_REARM_MIN_STEPS = 0


@dataclass(frozen=True)
class Occurrence:
    """χ_i^k = (t_up, t_down, t_rearm)：一次完整发生的三边界记录。

    这是"(计数=1, α)"最小组织记录（Λ^org 的最低候选，见反馈 §5.2），
    **不是**自然单位 𝔫——`count` 恒为 1，`address` 只携带生成谱系，不携带
    任何无量纲测度/相位/内部占比。P2-B 才会对 χ 施加测度映射 𝒩: χ ↦ 𝔫。

    字段：
      t_up:    触发时刻（进入有效发生的 step_index）
      t_down:  活动退出时刻（跌破 theta_down 的 step_index）
      t_rearm: 重新具备下一次触发资格的 step_index（本轮 == t_down，
               因 rearm_min_steps=0，见模块 Q3）
      count:   恒为 1，表示"一次有效发生"，不表示焦耳/脉冲/秒等物理量
      address: 生成地址（挂在 GeneratedAddress 上的谱系，父地址回指皮肤支撑）
    """
    t_up: int
    t_down: int
    t_rearm: int
    address: GeneratedAddress
    count: int = 1

    def __post_init__(self):
        if not (self.t_up <= self.t_down <= self.t_rearm):
            raise ValueError(
                f"Occurrence: boundaries must satisfy t_up<=t_down<=t_rearm, "
                f"got ({self.t_up}, {self.t_down}, {self.t_rearm})")


class _ClosurePhase(Enum):
    ARMED = auto()        # 可再次触发
    ACTIVE = auto()       # 已触发，等待跌破 theta_down
    REFRACTORY = auto()   # 已退出，等待 rearm_min_steps 后重新武装


@dataclass
class OccurrenceClosure:
    """触发—退出—重新武装迟滞状态机，读一个标量信号流（collector.pre_trace）。

    用法：每步调用一次 `update(value, t_step)`；跨越 theta_up 记 t_up，跌破
    theta_down 记 t_down，经 rearm_min_steps 后记 t_rearm 并 emit 一个
    `Occurrence`（返回值非 None）。

    行为对齐反馈 §四 指出的两种错误：
      - 长期饱和（持续 >= theta_up 不回落）：ACTIVE 阶段不重复触发，直到
        真正跌破 theta_down 才计一次发生——不会被计成"无限发生"。
      - 阈值附近抖动：迟滞带 [theta_down, theta_up]（theta_down < theta_up）
        吸收小幅抖动，只要信号不完整跌破 theta_down 就不会被计成多次发生。
    """
    address: GeneratedAddress
    theta_up: float = _DEFAULT_THETA_UP
    theta_down: float = _DEFAULT_THETA_DOWN
    rearm_min_steps: int = _DEFAULT_REARM_MIN_STEPS

    _phase: _ClosurePhase = field(default=_ClosurePhase.ARMED, repr=False)
    _t_up: Optional[int] = field(default=None, repr=False)
    _t_down: Optional[int] = field(default=None, repr=False)
    events: List[Occurrence] = field(default_factory=list)

    def __post_init__(self):
        if not (0.0 <= self.theta_down < self.theta_up):
            raise ValueError(
                f"OccurrenceClosure: require 0 <= theta_down < theta_up, "
                f"got theta_down={self.theta_down}, theta_up={self.theta_up}")
        if self.rearm_min_steps < 0:
            raise ValueError("OccurrenceClosure: rearm_min_steps must be >= 0")

    def update(self, value: float, t_step: int) -> Optional[Occurrence]:
        """喂入本步的信号值（如 collector.pre_trace），推进状态机。

        返回本步是否完成了一次闭合（emit Occurrence），否则 None。
        """
        if self._phase is _ClosurePhase.ARMED:
            if value >= self.theta_up:
                self._t_up = t_step
                self._phase = _ClosurePhase.ACTIVE
            return None

        if self._phase is _ClosurePhase.ACTIVE:
            if value <= self.theta_down:
                self._t_down = t_step
                self._phase = _ClosurePhase.REFRACTORY
                # 有意落入下面的 REFRACTORY 分支同步判断（而不是 return None
                # 后等下一次 update() 才检查）：当 rearm_min_steps=0 时，
                # t_down 与 t_rearm 应在同一步完成，不应凭空多等一步。
            else:
                return None

        if self._phase is _ClosurePhase.REFRACTORY:
            if t_step - self._t_down >= self.rearm_min_steps:
                ev = Occurrence(
                    t_up=self._t_up, t_down=self._t_down, t_rearm=t_step,
                    address=self.address,
                )
                self.events.append(ev)
                self._t_up = None
                self._t_down = None
                self._phase = _ClosurePhase.ARMED
                return ev
            return None

        raise AssertionError(f"unreachable closure phase {self._phase!r}")

    @property
    def is_active(self) -> bool:
        """当前是否处于 ACTIVE 或 REFRACTORY 阶段（即窗口 W=[t_up, t_rearm) 内）。"""
        return self._phase is not _ClosurePhase.ARMED

    @property
    def occurrence_count(self) -> int:
        return len(self.events)
