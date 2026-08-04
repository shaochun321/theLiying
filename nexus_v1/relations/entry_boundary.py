"""nexus_v1.relations.entry_boundary — TSS-R1a：E^↑ 首次进入边界**实时参考检测器**。

TYPE:INFRA

## 资格边界（评判document - 2026-08-05T010306.536.md裁定，先读这段）

本模块实现的是**判定规则**，不是物理生成算子。已取得的资格：

  输入类型裁定：通过
  首次进入边界规则：通过
  实时因果方向：通过（p_α(t) → b_α^↑(t)，不反查闭合状态）
  跨站点统一参数：通过
  物理生成算子资格：**待实现**（TSS-R1b）

原因：`CollectorBoundaryPort`只暴露真实物理载体已产生的信号，可作INFRA
接口；而本模块保存ARMED/ACTIVE/REFRACTORY状态、计算无脉冲间隔、抑制同
一发生内的后续脉冲、产生新脉冲——这是一个真正的过程变换
E^↑: p_α(t) ↦ b_α^↑(t)，目前只存在于Python控制逻辑中，没有对应的物理
载体（电容泄漏时间常数/门控/不应期/锁存释放结构）。

因此：
  - 禁止宣称"E^↑生成算子已完成"。若让H_τ直接消费本模块输出并据此宣称
    统一时间算子成立，等于把主线从"由Occurrence事后重建过程"改成"由软件
    状态机实时生成过程"——因果方向对了，物理实现问题仍未解决。
  - 本模块的正确用途：**物理实现的对照标准（test oracle）**，要求
    b^↑_physical(t) ≡ b^↑_reference(t)。
  - gap_steps=500 作为仿真判定规则有实测依据（见Q3）；作为物理算子参数，
    还需回答 τ_gap = 500·Δt 由哪个物理结构保存——整数计步本身不构成物理
    载体。

方案依据：document - 2026-08-04T220649.641.md（评判裁定TSS-R1a：时间生成
算子输入事件类型裁定，冻结版本A——"28≺21"检测的是一次发生的进入边界
先后，不是活动历史的持续支撑）。

## 背景

TSS-R0建立了`CollectorBoundaryPort.spike_output`（实时二值脉冲），但
它是"collector本步是否发火"，不等于"一次持续发生的首次进入"——持续
驱动下collector会反复spike（实测site28在radius=5.0场景下ISI集中在
120~316步），若Θ_τ直接读取每次spike，会把"发生了几次/多密集"混进
"先后关系"，重演T3失败的同一失效模式（幅值/频率污染时序判断）。

版本A裁定：Θ_τ应读取一次持续发生的**首次进入边界**——同一次持续发生
内，无论collector反复spike多少次，只应产生一次"进入"事件；活动完全
停止并经过冷却期后，才能重新武装、产生下一次"进入"事件。

## 与OccurrenceClosure的关系（复用已验证状态机，不重复设计）

`occurrence.py`的`OccurrenceClosure`（ARMED→ACTIVE→REFRACTORY）已经
实现了这个锁存语义——`_epoch_consumed`在越阈瞬间锁死，同一epoch内
重复越阈不重复产生"up"事件，且判断逐步实时（不等t_down）。但它的
输入是`pre_trace`（连续量，theta_up/theta_down软阈值），本模块把
同一套三态结构改造为吃`spike_output`（二值）：

  - 二值输入不需要theta_up/theta_down迟滞带——spike本身已经是离散
    事件（0或1），不存在"阈值附近抖动"问题，ARMED→ACTIVE只需
    `spike_output > 0.5`
  - "持续发生"的活/不活判断改用**冷却期**（gap_steps）：连续
    gap_steps步无spike，才判定为ACTIVE→REFRACTORY（活动真正退出）
  - REFRACTORY→ARMED（重新武装）沿用occurrence.py同一做法：经过
    rearm_min_steps后完成

## 参数依据（Q3）

`gap_steps`/`rearm_min_steps`复用`occurrence.py._DEFAULT_REARM_MIN_STEPS
=500`——不新造标定：
  - EXP-R1A-01（2026-08-04一次性探针，已删除不留代码）：radius=5.0场景
    下28/31/21/24四站点8000步实测ISI，正常发放簇内ISI集中在120~316步，
    量级与occurrence.py Q3记录的"实测最大相邻爆发间隔~314步"完全一致
    （同一套量子元通路，同一类阵发性爆发动力学，非偶然）。
  - 该探针另测到21/24各出现一次孤立超大间隔（4257/5927步）——判定为
    Body运动导致远端站点短暂脱离HeatSource有效范围的真实退出事件，
    不是需要用更大gap_steps去"合并"的噪声。若强行取max_isi作为
    gap_steps会得到8890步这种荒谬数字，让E^↑形同瘫痪，是错误的标定
    方向。
  - 结论：直接复用occurrence.py已验证的500这个值（"略大于实测最大
    相邻爆发间隔~314步，留有余量"的推导对本场景同样适用），不新造
    独立常数。

RULES.md 强制三问：
  Q1 生物对应物：同occurrence.py Q1——触发/退出/重新武装迟滞，标准
     施密特触发器式去抖动，生物对应是感觉神经元阈值调适/不应期。
  Q2 物理结构：**尚无**。本模块不新建Neuron/SynapticBundle，只读取
     CollectorBoundaryPort.spike_output做状态机记账，不改变任何神经元
     状态。但状态机本身（相位锁存、间隔计数、冷却计时）没有物理载体
     ——这正是本模块只能作为参考检测器、Q2留空待TSS-R1b回答的原因。
  Q3 参数依据：见上，复用occurrence.py的500，不新造。作为判定规则的
     依据充分；作为物理时间常数的映射见Q2，未完成。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from ..components.structural_address import GeneratedAddress
from .boundary_process import CollectorBoundaryPort

# 复用 occurrence.py._DEFAULT_REARM_MIN_STEPS，不新造标定（见模块 Q3）。
_DEFAULT_GAP_STEPS = 500
_DEFAULT_REARM_MIN_STEPS = 500


class _EntryPhase(Enum):
    ARMED = auto()       # 可再次检测首次进入
    ACTIVE = auto()      # 已进入，持续发生窗口内（含反复spike与短暂静默）
    REFRACTORY = auto()  # 已判定真正退出，等待rearm_min_steps后重新武装


@dataclass
class EntryBoundaryDetector:
    """TYPE:INFRA — E^↑：p_α(t) ↦ b_α^↑(t)，首次进入边界检测器。

    每步调用`update(spike_output, t_step)`，推进状态机；返回True表示
    本步产生了一次"首次进入"事件（b_α^↑=1），否则False。

    六项资格（评判document-220649.641.md明确要求）：
      1. 在持续发生首次进入时输出一次脉冲——ARMED→ACTIVE跳变时return True
      2. 持续发生中的重复spike不重复输出——ACTIVE阶段内spike_output=1
         不再产生新事件，只刷新静默计数器
      3. 真实退出并重新具备资格后才能再次输出——需经历
         ACTIVE→(冷却gap_steps)→REFRACTORY→(rearm_min_steps)→ARMED
         完整闭环
      4. 实时运行，不读取完整Occurrence或事后才知道的t_down——每步
         只用当前spike_output和内部计数器判断，不依赖任何审计记录
      5. 跨站点使用同一结构和同一参数——本类不含任何站点专属字段，
         gap_steps/rearm_min_steps是构造参数，同一份数值可用于任意站点
      6. 地址名称不参与判断——generator_address只用于调用方追踪，
         update()的判断逻辑完全不读取该字段
    """
    generator_address: GeneratedAddress
    gap_steps: int = _DEFAULT_GAP_STEPS
    rearm_min_steps: int = _DEFAULT_REARM_MIN_STEPS

    # init=False：这些是内部状态记账字段，不应作为构造参数暴露——调用方
    # 不能直接传_phase=ACTIVE跳过状态机（同T-R1A-4"不依赖事后信息，纯实时
    # 判断"的封装要求，构造签名应只有generator_address/gap_steps/
    # rearm_min_steps三个真正的配置参数）。
    _phase: _EntryPhase = field(default=_EntryPhase.ARMED, repr=False, init=False)
    _silence_count: int = field(default=0, repr=False, init=False)   # ACTIVE阶段连续无spike步数
    _t_exit: Optional[int] = field(default=None, repr=False, init=False)  # 判定真正退出的时刻
    entry_count: int = field(default=0, repr=False, init=False)  # 累计首次进入次数（审计用，不参与判断）

    def __post_init__(self):
        if self.gap_steps < 0:
            raise ValueError("EntryBoundaryDetector: gap_steps must be >= 0")
        if self.rearm_min_steps < 0:
            raise ValueError("EntryBoundaryDetector: rearm_min_steps must be >= 0")

    def update(self, spike_output: float, t_step: int) -> bool:
        """喂入本步的spike_output（0.0或1.0），推进状态机。

        返回True仅当本步发生ARMED→ACTIVE跳变（首次进入边界）。
        """
        is_spike = spike_output > 0.5

        if self._phase is _EntryPhase.ARMED:
            if is_spike:
                self._phase = _EntryPhase.ACTIVE
                self._silence_count = 0
                self.entry_count += 1
                return True
            return False

        if self._phase is _EntryPhase.ACTIVE:
            if is_spike:
                self._silence_count = 0
            else:
                self._silence_count += 1
                if self._silence_count >= self.gap_steps:
                    self._phase = _EntryPhase.REFRACTORY
                    self._t_exit = t_step
            return False

        if self._phase is _EntryPhase.REFRACTORY:
            if t_step - self._t_exit >= self.rearm_min_steps:
                self._phase = _EntryPhase.ARMED
                self._t_exit = None
                self._silence_count = 0
                # 重新武装后，本步若恰好也是spike，按ARMED分支处理
                if is_spike:
                    self._phase = _EntryPhase.ACTIVE
                    self._silence_count = 0
                    self.entry_count += 1
                    return True
            return False

        raise AssertionError(f"unreachable entry phase {self._phase!r}")

    @property
    def is_active(self) -> bool:
        """当前是否处于持续发生窗口内（ACTIVE或REFRACTORY）。"""
        return self._phase is not _EntryPhase.ARMED


def make_entry_detector(port: CollectorBoundaryPort,
                        gap_steps: int = _DEFAULT_GAP_STEPS,
                        rearm_min_steps: int = _DEFAULT_REARM_MIN_STEPS
                        ) -> EntryBoundaryDetector:
    """从既有CollectorBoundaryPort构造对应的EntryBoundaryDetector。

    只复用port的generator_address做谱系追踪，不建立对port本身的引用
    ——调用方每步显式传入`port.spike_output`给`update()`，保持
    EntryBoundaryDetector与CollectorBoundaryPort完全解耦（同评判要求
    "地址只用于定位载体和谱系追踪，不决定算子是否成立"的既定边界）。
    """
    return EntryBoundaryDetector(
        generator_address=port.generator_address,
        gap_steps=gap_steps, rearm_min_steps=rearm_min_steps)
