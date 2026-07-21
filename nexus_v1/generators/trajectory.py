"""nexus_v1.generators.trajectory — 生成元轨迹记录器（P2-A 冻结前置补件）。

TYPE:INFRA — 本模块无 BIO/SEMI 对应物；它只读取 `BaseGenerator.feed()` 已经
产生的既有数值（Neuron 的 `pre_trace`）并追加到一个列表里，不新建任何
Neuron/SynapticBundle，不改变既有传播行为，类比 `structural_address.py` 的
审计/身份基础设施定位（观测工具而非物理机制本身）。

方案依据：`cell-cell/工作报告/P2-A_生成元核心_单点真实发生元构造与标定_
2026-07-20.md` §六(未完成项第4条)+ `cell-cell/交叉比对/评判_P2A核心确认与
生长机制来源存疑_2026-07-21.md` §一(P2-A 整体冻结前必须补齐窗口内原始轨迹)。

**架构澄清（本模块存在的直接原因）**：P1 基础设施 `joint_thermal_step_plan.py`
的 `JointThermalTrajectory` 只在 `apply_joint_thermal_step()`（世界-皮肤联合
调度管线）被调用时才产生记录；而 `BaseGenerator.feed()` 是刻意绕开 world/body
的"合成 dT 标定路径"（与 `circuit.step()` 互斥，见 `base_generator.py`
docstring），从不驱动那条管线——所以复用 `JointThermalTrajectory` 做窗口聚合
在 `feed()` 路径下无对象可切片。本模块不强行嫁接，而是给 `BaseGenerator`
配一个自己的、轻量级、只读的轨迹记录器，忠实反映 `feed()` 路径的真实物理
范围（标定用合成输入，不是完整世界物理管线）。

RULES.md 强制三问：

  Q1 生物对应物：
    无——纯审计/观测基础设施，同 `structural_address.py` 的 TYPE:INFRA 定位。

  Q2 物理结构：
    只读取 `BaseGenerator.ensemble` 各元素与 `collector` 已存在的 `pre_trace`
    属性（`components/neuron.py` 既有字段），不创建新 Neuron/Bundle，不修改
    `feed()`/传播逻辑本身，纯粹的事后记账。

  Q3 参数依据：
    无新物理/可调参数——只是数据结构字段。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class TrajectoryRecord:
    """单步轨迹快照：D_i^sim 输入 + 生成元核心内部逐步激活 + collector 输出。

    字段：
      step_index:          本记录对应的 step（与 `Occurrence`/`OccurrenceClosure`
                            使用同一计数源，供 `GeneratorTrajectory.window()`
                            按 `[t_up, t_rearm)` 半开区间对齐切片）。
      u_i:                 本步基础生成元输入端口量——即实际驱动
                            `_propagate()` 的值。`tick()`(MANUAL_CALIBRATION)
                            路径下等于调用方传入的合成 `dT_raw`（κ_i 隐式为1）；
                            `tick_from_skin()`(WORLD_COUPLED) 路径下等于
                            `skin_transduction.transduce(q_skin, config)` 的
                            输出（已经过κ_i/b_i/clip变换）。
      ensemble_pre_trace:   10 个 ensemble 神经元本步的 `pre_trace`（阶梯阈值
                            温度计编码，只读快照，不代表任何已确定的自然化
                            候选测度——是否可用作内部占比 ρ 的输入留给 P2-B）。
      collector_pre_trace:  collector（AND 门）本步的 `pre_trace`，即
                            `OccurrenceClosure` 用来判定 ARMED/ACTIVE/REFRACTORY
                            的同一信号。
      q_skin_raw:           P2-A1b-3新增，可选（默认None）。WORLD_COUPLED
                            路径下的原始未转导皮肤输出 `q_i^skin(t)`——转导
                            映射会把大部分数值clip压缩，若只记录`u_i`会丢失
                            原始物理轨迹，故与`u_i`一起保留（评判
                            document-2026-07-21T161711.318.md「②正式接入
                            转导映射」明确要求"不能只记录被clip后的u_i"）。
                            MANUAL_CALIBRATION 路径下保持 None（没有皮肤，
                            不适用）。
    """
    step_index: int
    u_i: float
    ensemble_pre_trace: Tuple[float, ...]
    collector_pre_trace: float
    q_skin_raw: Optional[float] = None


@dataclass
class GeneratorTrajectory:
    """`BaseGenerator` 的轨迹记录器：只追加、只读切片，不计算任何派生量。

    刻意不计算峰值/能量/相位等——那些是 P2-A1（输入工作区间扫描）与 P2-B
    （自然化候选测度检验）的工作，本组件只提供原始逐步记录，遵守"不预先
    构造下一深度候选测度"的纪律（反馈文档 §5.3：P2-A 不冻结最终自然单位）。
    """
    records: List[TrajectoryRecord] = field(default_factory=list)

    def record(
        self, step_index: int, u_i: float,
        ensemble_values: Tuple[float, ...], collector_value: float,
        q_skin_raw: Optional[float] = None,
    ) -> None:
        self.records.append(TrajectoryRecord(
            step_index=step_index, u_i=u_i,
            ensemble_pre_trace=tuple(ensemble_values),
            collector_pre_trace=collector_value,
            q_skin_raw=q_skin_raw,
        ))

    def window(self, t_start: int, t_end: int) -> List[TrajectoryRecord]:
        """按 `[t_start, t_end)` 半开区间切片——与 `Occurrence` 的
        `W_{i,k}=[t_up, t_rearm)` 窗口约定一致，供调用方以
        `trajectory.window(occ.t_up, occ.t_rearm)` 取出一次发生对应的
        全部原始记录。
        """
        return [r for r in self.records if t_start <= r.step_index < t_end]
