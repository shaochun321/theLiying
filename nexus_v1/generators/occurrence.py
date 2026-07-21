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
      P2-A1b-3 用真实`tick_from_skin()`+`build_three_point_skin()`轨迹
      验证仍然有效——collector.pre_trace 在真实映射输入下确实能越过
      0.01（实测峰值可达~1.0），故本轮**不改动**该值。
    - `theta_down=0.001`（# EXP-P2A1b3-CALIBRATED，替换原
      `# EXP-P2A-001-PROVISIONAL`）：用`exp_P2A1b_3_closure_calibration.py`
      在真实映射轨迹下验证——原占位值 `0.1*theta_up=0.001` 本身已经是
      合理的迟滞下限（撤去刺激后pre_trace能在~77~2000步量级内跌破，
      不需要改动数值本身），保留不变，只是标注从占位改为已验证。
    - `rearm_min_steps=500`（# EXP-P2A1b3-CALIBRATED，替换原
      `# EXP-P2A-002-PROVISIONAL`的占位值0）：用真实映射轨迹实测发现
      ensemble/collector 下游通路对任意一次阈值穿越都会产生短时重复
      振荡（3000步持续驱动期间原0值下产生3次伪发生，间隔约150~314步），
      用`exp_P2A1b_3_closure_calibration.py`对
      rearm_min_steps∈{0,200,500,1000,2000}做扫描，确认500（略大于
      实测最大相邻爆发间隔~314步，留有余量）能把同一场景下的伪发生
      收敛为1次（真实的那一次），且不过度延迟真正独立的二次刺激重整
      （见该脚本判据4）。**已知限制（如实登记，非本轮修复范围）**：
      在远超本项目现有参考场景规模的长观测窗口（万步量级）下，该下游
      通路会表现出与外部输入基本脱耦的长尾自持振荡（实测：皮肤本身
      温度已衰减至0，pre_trace仍振荡长达10000+步），本轮标定只针对
      与现有参考场景（≤300~1000步）同数量级的代表性观测预算，未完全
      压制这个长尾现象——留待 P2-A3（成对时序分辨率标定）处理。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional

from ..components.structural_address import GeneratedAddress

# EXP-T1 沿用：test_basegen_thermal_t1_real_occurrence.py:64 的 OCCURRENCE_THRESHOLD
# P2-A1b-3 用真实映射轨迹重新验证，仍然有效（见模块 docstring Q3），不改动。
_DEFAULT_THETA_UP = 0.01
# EXP-P2A1b3-CALIBRATED：P2-A1b-3 用真实映射轨迹验证，数值本身不变
# （原 0.1*theta_up 占位恰好合理），只是标注从占位改为已验证（见 Q3）。
_DEFAULT_THETA_DOWN = 0.1 * _DEFAULT_THETA_UP
# EXP-P2A1b3-CALIBRATED：替换原 0 占位值。用
# exp_P2A1b_3_closure_calibration.py 对真实映射轨迹下的短时重复振荡做
# rearm_min_steps 扫描标定得出（见模块 docstring Q3 完整推导与已知限制）。
_DEFAULT_REARM_MIN_STEPS = 500


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
