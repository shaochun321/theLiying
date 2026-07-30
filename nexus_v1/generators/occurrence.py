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
      （见该脚本判据4）。

    - **P2-A1b-3R 修复（`phys_support` 传入门控，见 `update()` 参数
      文档）**：上面记录的长尾自持振荡（900驱动+15000撤去观测实测产生
      14次伪occurrence，最后一次伪发生在t=13359、此时皮肤温度已精确为
      0）经逐层定位，源头在 HC 热觉毛细胞自身的通道慢态（K+适应/Ca²⁺
      释放子系统，`transducer_neurons.py:_thermo_haircell_config` 的
      docstring 自行标注为 ms→s 尺度未校准的 TODO-CALIBRATE 占位值），
      不在 ensemble/collector 本身、也不在任何反馈边（该通路是严格
      前馈：L1→HC→ensemble→collector，`_step_quantum_thermal_pathways`
      不含 collector→ensemble 回边）。直接改 HC 的通道时间常数需要
      生物文献推导具体秒级数值（Q3 暂答不全，见该 config 的 REF），
      本轮不裸调；改用 ARMED→ACTIVE 层的传入门控——中枢自发（HC残留
      慢态驱动 ensemble/collector 穿阈）不再单独计为一次新 occurrence，
      必须同时有外周（L1）活动在场（`l1.activation>0`，L1 已实测精确
      跟随 dT_raw，无自身残留）。

      **根因裁定措辞修正**：HC 慢态时间常数不是纯代码 bug（K+/Ca²⁺ 慢态
      本身可能具有合理生物物理意义），准确表述是"D0 生物物理参数未校准
      导致的时间尺度错配"——当前参数来自前庭毛细胞占位值，尚未证明
      适合热觉通路。登记为独立 D0 债务，留待有文献依据时再校准（不
      阻塞本轮工程）。

    - **P2-A1b-3R 二轮修正（电平门控→epoch/token门控，见`update()`参数
      文档 `_prev_support`/`_epoch_consumed` 机制）**：第一轮的
      `phys_support` 是电平门控（只看当前是否有外周活动），仍允许同一
      次连续物理支撑期内重复触发——3000步短间隔重测实测 emitted=3
      （应为2），此前误判为"HC残留未退尽的边界情况"，实际是电平门控
      本身的语义缺陷（`N_χ(E_phys)≤1`契约未被真正满足，只是延长间隔到
      15000步后碰巧生效）。本轮升级为 epoch/token 门控：物理支撑上升沿
      开启新 epoch，本 epoch 内最多消费一次候选闭合名额（在触发时刻
      `t_up`消费，允许候选闭合在支撑跌落之后自然完成/emit）。这是 D1
      修复（本轮完成），与 D0（HC参数校准债务）分离——不用 D1 门控掩盖
      D0 参数问题，也不让 D0 债务阻塞工程。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple

from ..components.structural_address import GeneratedAddress, StructuralAddress

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
class OccurrenceInstanceId:
    """D1实例身份键：(生成元地址, epoch序号)。

    评判修正（`document - 2026-07-30T113327.179.md`）：`Occurrence.address`
    单独存在时只是"生成元地址"（同一生成元反复产生的所有 occurrence 共享
    同一个 address），不能被当作"这一次发生"的实例地址。**D1实例身份是
    "生成元地址＋epoch"，不是生成元地址本身**——两者组合才能唯一区分
    `u_{A,17}^(1)` 与 `u_{A,18}^(1)`。

    本类不新造字段来源——`generator_address`/`epoch_id` 都已存在于
    `Occurrence`（见 `Occurrence.instance_id` 属性），只是把它们包装成
    一个有类型、可哈希、可作 dict key 的复合身份对象，而不是让调用方各自
    拼字符串（如 `f"{addr.uid}_epoch_{epoch}"`）模拟这个概念。
    """
    generator_address: GeneratedAddress
    epoch_id: int


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
      address: 生成地址（挂在 GeneratedAddress 上的谱系，父地址回指皮肤支撑）。
               **注意**：同一生成元反复产生的所有 Occurrence 共享同一个
               `address`（它是生成元自身的地址，不是逐次发生的实例地址）。
               要区分"这一次"和"上一次"发生，须用 `(address, epoch_id)` 组合，
               不能只用 `address`（见 P2-B1X1 评判
               `document - 2026-07-29T200523.988.md` 对跨 epoch 错配的要求）。
      epoch_id: 本次发生所属的父物理支撑 epoch 序号（= `TransitionEvent.
               epoch_id`，从 `OccurrenceClosure._epoch_id` 直接继承，见
               `update()`）。P2-B1X1 新增字段——此前只存在于 `TransitionEvent`，
               未进入 `Occurrence` 本身，导致下游（如关系实例绑定）无法区分
               同一生成元的不同发生实例，只能靠测试手写字符串模拟。
      count:   恒为 1，表示"一次有效发生"，不表示焦耳/脉冲/秒等物理量
    """
    t_up: int
    t_down: int
    t_rearm: int
    address: GeneratedAddress
    epoch_id: int
    count: int = 1

    def __post_init__(self):
        if not (self.t_up <= self.t_down <= self.t_rearm):
            raise ValueError(
                f"Occurrence: boundaries must satisfy t_up<=t_down<=t_rearm, "
                f"got ({self.t_up}, {self.t_down}, {self.t_rearm})")

    @property
    def instance_id(self) -> "OccurrenceInstanceId":
        """D1实例身份（评判要求，见 `OccurrenceInstanceId` 文档）。用
        `@property` 组合既有字段，不重构现有构造签名/不新增独立传参——
        `generator_address`/`epoch_id` 已经是本对象的既定字段。"""
        return OccurrenceInstanceId(generator_address=self.address, epoch_id=self.epoch_id)


@dataclass(frozen=True)
class TransitionEvent:
    """审查点2「D1 在线转换流类型化」（评判`document - 2026-07-28T170247.680.md`
    「一个非阻塞接口问题」）：把 P2-A3 首轮的裸元组 `("up", t)` 升级为带完整
    上下文的转换记录，回答"来自哪个生成元/属于哪个父物理epoch/是哪种转换/
    回指哪个物理支撑"四个问题，供 P2-B0 直接消费，不再依赖调用方自行从外部
    对象拼接这些信息。

    字段：
      generator_address: 触发本次转换的生成元自身地址（= `OccurrenceClosure.
        address`，含 `parent_addresses` 谱系，不新建平行身份系统）。
      epoch_id: 本次转换所属的父物理支撑 epoch 序号（从1开始，每次 phys_support
        的 False→True 上升沿递增；同一 epoch 内的 up/down/rearm 共享同一
        epoch_id，即使 down/rearm 发生在支撑已跌落之后——见 update() 文档，
        消费判定发生在触发时刻而非支撑状态本身）。
      kind: "up"/"down"/"rearm"，对应 ξ↑/ξ↓/ξ_rearm。
      t_step: 转换发生的 step_index（与 Occurrence 的 t_up/t_down/t_rearm
        同一时间基准）。
      phys_support_address: 回指的物理支撑地址（= `generator_address.
        parent_addresses[0]`，若存在；本模块不新增地址系统，只读取既有
        `GeneratedAddress.parent_addresses` 谱系的第一个元素）。
    """
    generator_address: GeneratedAddress
    epoch_id: int
    kind: str
    t_step: int
    phys_support_address: Optional[StructuralAddress] = None


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

    # P2-A1b-3R 二轮修正（评判`document - 2026-07-28T115051.644.md`）：从
    # 电平门控升级为 epoch/token 门控，见 update() 文档。
    _prev_support: bool = field(default=False, repr=False)
    _epoch_consumed: bool = field(default=False, repr=False)

    # P2-A3（评判`document - 2026-07-28T120854.728.md`「1. 建立在线转换流」）：
    # 每步转换事件的实时暴露，见 update() 文档与 last_transitions 属性。
    # 审查点2（评判`document - 2026-07-28T170247.680.md`）升级为类型化
    # `TransitionEvent`（原裸元组 `(kind, t_step)`），见该类文档。
    _last_transitions: List[TransitionEvent] = field(default_factory=list, repr=False)
    # epoch 序号计数器：每次 phys_support False→True 上升沿递增（从0开始，
    # 第一次上升沿变为1）。与 `_epoch_consumed`（是否已消费本epoch名额）
    # 是两个独立字段——前者是给外部可读的序号标识，后者是内部门控状态。
    _epoch_id: int = field(default=0, repr=False)

    def __post_init__(self):
        if not (0.0 <= self.theta_down < self.theta_up):
            raise ValueError(
                f"OccurrenceClosure: require 0 <= theta_down < theta_up, "
                f"got theta_down={self.theta_down}, theta_up={self.theta_up}")
        if self.rearm_min_steps < 0:
            raise ValueError("OccurrenceClosure: rearm_min_steps must be >= 0")

    def update(self, value: float, t_step: int, phys_support: bool = True) -> Optional[Occurrence]:
        """喂入本步的信号值（如 collector.pre_trace），推进状态机。

        P2-A1b-3R 传入门控（第一轮，评判`document - 2026-07-28T111507.473.md`）
        新增 `phys_support`：ARMED→ACTIVE 除了 value 越过 theta_up，还要求
        本步存在真实外周传入活动——这解决了"外周已静息、纯内部残留触发"
        的长尾自持振荡问题（900 驱动+15000 撤去观测实测 14→1）。

        P2-A1b-3R 二轮修正（评判`document - 2026-07-28T115051.644.md`）：
        第一轮是**电平门控**（只看当前是否有外周活动），仍允许同一次连续
        物理支撑期内重复触发——3000 步短间隔重测实测 emitted=3（应为2）
        坐实了这个缺陷：第二次真实驱动期间 phys_support 全程为真，但
        collector 在同一个驱动窗口内越阈两次，两次都满足电平门控。

        本轮升级为 **epoch/token 门控**：`_prev_support`/`_epoch_consumed`
        跟踪"物理支撑上升沿→开启新 epoch→本 epoch 最多消费一次候选闭合
        名额"。消费发生在 ARMED→ACTIVE 的**触发时刻**（t_up），而非实际
        emit 时刻——这样候选闭合即使在 phys_support 已经跌落之后才自然
        完成/emit（生理响应滞后于外周刺激是合法的，如实测 t_up=673 但
        t_rearm=3328、此时外周输入早在 t=900 就已结束），仍允许它完成；
        只是同一个连续支撑期内不能开启第二个候选。`phys_support` 保持
        默认 True——不传该参数的既有调用点（本模块状态机层面的测试）
        行为不变（持续 True 意味着只在第一次上升沿开一次 epoch，此后
        `_epoch_consumed` 逻辑等效于原来的"ACTIVE 阶段不重复触发"行为，
        不产生额外差异）。

        返回本步是否完成了一次闭合（emit Occurrence），否则 None。

        P2-A3 在线转换流（评判`document - 2026-07-28T120854.728.md`「1. 建立
        在线转换流」要求的 ξ↑/ξ↓/ξ_rearm）：本次调用触发的转换事件同时记入
        `self._last_transitions`（通过 `last_transitions` 属性读取），不改变
        本方法既有的 `Optional[Occurrence]` 返回值契约——只有真正完成一次
        闭合（rearm）时才返回非 None，向后兼容全部既有调用点。`t_down` 与
        `t_rearm` 可能在同一步同时发生（`rearm_min_steps=0` 时），故
        `last_transitions` 是列表，单步可含多个事件。
        """
        self._last_transitions = []

        if phys_support and not self._prev_support:
            # 物理支撑上升沿：开启新 epoch，重置本 epoch 的消费名额，
            # epoch 序号递增（供 TransitionEvent.epoch_id 使用）。
            self._epoch_consumed = False
            self._epoch_id += 1
        self._prev_support = phys_support

        phys_support_addr = (
            self.address.parent_addresses[0] if self.address.parent_addresses else None
        )

        if self._phase is _ClosurePhase.ARMED:
            if value >= self.theta_up and phys_support and not self._epoch_consumed:
                self._t_up = t_step
                self._phase = _ClosurePhase.ACTIVE
                self._epoch_consumed = True
                self._last_transitions.append(TransitionEvent(
                    generator_address=self.address, epoch_id=self._epoch_id,
                    kind="up", t_step=t_step, phys_support_address=phys_support_addr,
                ))
            return None

        if self._phase is _ClosurePhase.ACTIVE:
            if value <= self.theta_down:
                self._t_down = t_step
                self._phase = _ClosurePhase.REFRACTORY
                self._last_transitions.append(TransitionEvent(
                    generator_address=self.address, epoch_id=self._epoch_id,
                    kind="down", t_step=t_step, phys_support_address=phys_support_addr,
                ))
                # 有意落入下面的 REFRACTORY 分支同步判断（而不是 return None
                # 后等下一次 update() 才检查）：当 rearm_min_steps=0 时，
                # t_down 与 t_rearm 应在同一步完成，不应凭空多等一步。
            else:
                return None

        if self._phase is _ClosurePhase.REFRACTORY:
            if t_step - self._t_down >= self.rearm_min_steps:
                ev = Occurrence(
                    t_up=self._t_up, t_down=self._t_down, t_rearm=t_step,
                    address=self.address, epoch_id=self._epoch_id,
                )
                self.events.append(ev)
                self._t_up = None
                self._t_down = None
                self._phase = _ClosurePhase.ARMED
                self._last_transitions.append(TransitionEvent(
                    generator_address=self.address, epoch_id=self._epoch_id,
                    kind="rearm", t_step=t_step, phys_support_address=phys_support_addr,
                ))
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

    @property
    def last_transitions(self) -> Tuple[TransitionEvent, ...]:
        """本次 `update()` 调用触发的转换事件列表，元素为类型化的
        `TransitionEvent`（`kind` ∈ {"up", "down", "rearm"}，对应
        ξ↑/ξ↓/ξ_rearm，见该类文档）。多数步为空元组；`rearm_min_steps=0`
        时单步可能同时含 "down" 与 "rearm" 两条记录。

        审查点2升级（评判`document - 2026-07-28T170247.680.md`）：从裸元组
        `(kind, t_step)` 升级为携带 `generator_address`/`epoch_id`/
        `phys_support_address` 的完整记录，不再需要调用方从外部对象上下文
        隐含拼接这些信息。"""
        return tuple(self._last_transitions)
