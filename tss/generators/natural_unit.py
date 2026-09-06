"""tss.generators.natural_unit — P2-B0：单 occurrence 自然化接口。

TYPE:INFRA — 本模块无 BIO/SEMI 对应物本身；它是"感受野输出到共同无量纲
组织接口"的标准换能器读出范式（同 `评判_反馈自然单位概念修正_2026-07-20.md`
§三"使不同类型生成元在不直接比较原始量纲的情况下进入共同关系耦合"目的），
只组合既有对象产出一个新 dataclass，不新建 Neuron/SynapticBundle。

方案依据：
  - `cell-cell/交叉比对/评判_反馈自然单位概念修正_2026-07-20.md`：核心裁定
    `χ ≠ 𝔫`，`𝒩_i: χ_i^k ↦ 𝔫_i^k`（测度映射，非物理量替换）。当前唯一已
    验证的最低测度候选：`Λ^org = (C_i(χ)=1, α_i)`——"1"只表示"一次有效
    发生"，禁止冒充焦耳/脉冲/秒等物理量。双轨账本：`Λ^phys`（物理-运行轨）
    + `Λ^org=(1,α)`（组织-无量纲轨）。P2-A/本模块**不冻结最终 NaturalUnit
    实体**，只交付可被 P2-B 验证的候选结构。
  - `cell-cell/交叉比对/document - 2026-07-28T183325.248.md`（正式放行
    P2-B0）：候选自然单位元组
    `𝔲_{i,k}^(1) = (Ĝ_i, S_in,i, S_out,i, Port_i, W_{i,k}, ℒ_{i,k}, Addr_{i,k})`，
    量纲恢复公式 `𝒢_i = S_out,i · Ĝ_i · S_in,i^{-1}`。

四个必答问题（该评判文档要求）与本模块的回答：

  Q1 哪个量是自然化输出？
    不宣称单一"the"自然单位。交付两个明确标注、彼此不混淆的候选测度：
    `count_measure=1`（Λ^org 的 C_i(χ)，07-20 已验证唯一合法的当前候选，
    纯计数，不代表任何物理量）与 `duration_raw_steps`/`duration_seconds`
    （**明确标注为未经 P2-B 验证的候选**——"持续时间是否是合适的自然单位"
    正是 07-20 裁定要留给 P2-B 验证的问题）。

  Q2 量纲如何恢复？`𝒢_i = S_out,i · Ĝ_i · S_in,i^{-1}`：
    count 测度：`Ĝ_i=1`, `S_in=S_out=1`（恒等，计数本身无量纲）。
    duration 测度：`Ĝ_i=duration_raw_steps`（生成元内部"步"单位），
    `S_out_i=dt`（仿真步长，转成秒），`S_in_i=1`（duration 不经过转导映射链，
    input-side scaling 不适用）。

  Q3 站点固有偏置如何保留？
    不把 `δ_ij^{0|W}` 当全局常数吸收/删除。`SiteCalibration`（可选字段）只
    携带指针，不自动做偏置校正——`count_measure`/`duration_*` 本身是未校正
    的原始读数，消费方自己决定是否应用。

  Q4 自然化是否保持父物理支撑谱系？
    `address: GeneratedAddress`（= `Occurrence.address`本身，已含
    `parent_addresses` 回指皮肤支撑）是必填字段，不允许自然化后只剩裸数字。

RULES.md 强制三问：
  Q1 生物对应物：同上——跨模态无量纲组织接口的标准读出范式，非新生物机制。
  Q2 物理结构：只读取已有 `Occurrence`/`GeneratorTrajectory`/
    `GeneratedAddress` 字段组装新 dataclass，不新建 Neuron/SynapticBundle，
    不修改 `occurrence.py`/`base_generator.py`/`trajectory.py` 本身。
  Q3 参数依据：零新增物理参数，`dt` 复用既有仿真步长约定
    （`BaseGenerator.tick()`/`tick_from_skin()` 同一 `dt` 语义）。

P2-B0 冻结契约（评判`document - 2026-07-28T185716.294.md`，精简记录，取代
长篇报告）——本模块的边界与不变量：

  边界：P2-B0 只负责"把一个已经合格的 D1 occurrence 包装成类型化自然接口"。
    不负责：关系生成、STDP/DA 学习、两个 occurrence 的比较、事件语义、
    Xin/旋转/组织生长——这些都是 P2-B1 及以后的工作，本模块不涉及。

  不变量（六条，均已被 `test_natural_unit.py` T-NU-1~5 验证）：
    1. `NaturalUnit` 必须携带 `GeneratedAddress`（Q4）。
    2. 自然化不得删除父物理支撑谱系（`address.parent_addresses` 非空）。
    3. 原始测量值不得被站点偏置自动修改（`SiteCalibration` 只携带指针，
       见 Q3）。
    4. 校准信息必须带作用域 `W`（`SiteCalibration.w_init_description`，
       不允许脱离作用域裸用 `δ_ij^0`）。
    5. `physical_ledger` 必须来自实际 `trajectory.window()` 切片，不是
       伪造/重新计算的数据。
    6. 非法 `occurrence.count`（≠1）不得进入接口——`__post_init__` 直接
       拒绝。

  当前留白（非阻塞，登记供 P2-B1+ 参考）：
    - duration 是否具有关系层资格（尚未验证）；
    - count 与 duration 是否需要联合自然化（尚未设计）；
    - `SiteCalibration` 在未来 D2 关系回路中怎样参与跨站点比较（尚未设计）。

  **命名澄清（避免误读）**：类名 `NaturalUnit` 不代表"已经找到了项目唯一的
  自然单位"。准确说法是——本模块建立了 D1 occurrence 的自然单位**接口容器**，
  其中 `count_measure` 是当前唯一已取得资格的自然化测度，`duration_*` 是
  未经 P2-B 验证的候选测度，两者资格不同，不应混为一谈。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

from nexus_v1.components.structural_address import GeneratedAddress
from .occurrence import Occurrence, OccurrenceInstanceId
from .skin_transduction import TransductionConfig
from .trajectory import TrajectoryRecord


@dataclass(frozen=True)
class SiteCalibration:
    """P2-A3 冻结的成对标定引用（评判`document - 2026-07-28T170247.644.md`
    「三轮措辞收口」正式冻结的 `𝔗_ij^(1)` 元组的一部分）——只在某个站点确实
    做过成对时序标定时才附加，多数站点当前没有，默认 `None`。

    本类只**携带**标定值，不做任何自动校正——校正与否由消费方决定（Q3）。

    字段：
      delta_0: 站点固有启动偏置 `δ_ij^{0|W}`（步）。
      eta: 该作用域下的不确定度预算 `η_ij^{|W}`（步）。
      w_init_description: 标定作用域 `W_init` 的文字描述（预热步数/平台检查
        范围/站点对/参数与输入条件），不是自由数值——避免脱离作用域裸用。
    """
    delta_0: float
    eta: float
    w_init_description: str


@dataclass(frozen=True)
class NaturalUnit:
    """𝔲_{i,k}^(1)：单个已完成 `Occurrence` 的自然化接口（P2-B0 首版）。

    字段对应候选元组 `(Ĝ_i, S_in,i, S_out,i, Port_i, W_{i,k}, ℒ_{i,k},
    Addr_{i,k})`——`Ĝ_i`/`S_in,i`/`S_out,i` 因为需要同时承载两个候选测度
    （count/duration），拆成各自独立的字段而非单一标量，见模块文档 Q1/Q2。

    字段：
      address:         Addr_{i,k}，= `occurrence.address`（父物理支撑谱系，Q4）。
      port:            Port_i，= `(site_index, polarity)`，标识产生这次发生
                        的具体生成元实例。
      window:          W_{i,k}，= `(t_up, t_rearm)`（半开区间边界，与
                        `GeneratorTrajectory.window()` 的切片约定一致）。
      count_measure:    Λ^org 的 `C_i(χ)`，恒为 1——只表示"一次有效发生"，
                        不表示任何物理量（07-20 文档明确禁止的冒充行为）。
      duration_raw_steps: `t_rearm - t_up`，生成元内部"步"单位下的候选
                        测度（Ĝ_i 的 duration 候选，未经 P2-B 验证）。
      duration_seconds: `duration_raw_steps * dt`（量纲恢复：S_out_i=dt,
                        S_in_i=1，见模块文档 Q2）。
      physical_ledger:  ℒ_{i,k} 的 Λ^phys 部分——若生成元句柄挂载了
                        `GeneratorTrajectory`，则是 `trajectory.window(t_up,
                        t_rearm)` 的原始切片（窗口内 ensemble 逐步激活/
                        u_i/collector 读数，满足 07-20 文档 §五对"ensemble
                        逐步激活轨"的补充要求）；否则为空 tuple（不报错，
                        因为 `record_trajectory` 默认 False，向后兼容）。
      input_scale:      S_in,i——WORLD_COUPLED 模式下驱动该生成元的
                        `TransductionConfig`（若适用），MANUAL_CALIBRATION
                        模式或未提供时为 `None`。
      site_calibration: 可选的 `SiteCalibration` 引用（Q3），默认 `None`。
      source_occurrence_instance_id: 评判修正（`document -
                        2026-07-30T113327.179.md`）新增字段——来源
                        `Occurrence.instance_id`（= `(generator_address,
                        epoch_id)`）。此前 `NaturalUnit` 只携带 `address`
                        （生成元地址，多个 occurrence 共享），无法区分
                        `u_{A,17}^(1)` 与 `u_{A,18}^(1)`。默认值 `None`
                        只是为了兼容 T-NU-5 等直接手工构造 `NaturalUnit`
                        （不经过 `naturalize()`）的既有测试——`naturalize()`
                        本身总是传入真实值，不允许为 None（见其函数体）。
    """
    address: GeneratedAddress
    port: Tuple[int, str]
    window: Tuple[int, int]
    count_measure: int
    duration_raw_steps: int
    duration_seconds: float
    physical_ledger: Tuple[TrajectoryRecord, ...] = field(default_factory=tuple)
    input_scale: Optional[TransductionConfig] = None
    site_calibration: Optional[SiteCalibration] = None
    source_occurrence_instance_id: Optional[OccurrenceInstanceId] = None

    def __post_init__(self):
        if self.count_measure != 1:
            raise ValueError(
                f"NaturalUnit: count_measure must be 1 (one valid occurrence, "
                f"not a physical quantity), got {self.count_measure}")
        t_up, t_rearm = self.window
        if not (t_up <= t_rearm):
            raise ValueError(
                f"NaturalUnit: window must satisfy t_up<=t_rearm, got {self.window}")
        if self.duration_raw_steps != t_rearm - t_up:
            raise ValueError(
                f"NaturalUnit: duration_raw_steps must equal t_rearm-t_up "
                f"({t_rearm - t_up}), got {self.duration_raw_steps}")


def naturalize(
    handle, occurrence: Occurrence, dt: float, *,
    transduction_config: Optional[TransductionConfig] = None,
    site_calibration: Optional[SiteCalibration] = None,
) -> NaturalUnit:
    """把一个已完成的 `Occurrence` 包装成 `NaturalUnit`（P2-B0 首版 𝒩_i^(0)）。

    纯函数，不修改 `handle`/`occurrence` 本身。`handle` 是产生该 occurrence
    的 `BaseGenerator` 句柄（用其 `site_index`/`polarity`/`trajectory`，
    这里不做类型注解绑定到 `BaseGenerator` 以避免循环导入——`base_generator.py`
    未来若需要调用本模块，不会与本模块导入 `BaseGenerator` 类型产生环）。

    Args:
      handle: 拥有 `site_index`/`polarity`/`trajectory` 属性的生成元句柄
        （即 `BaseGenerator` 实例）。
      occurrence: 已完成的 `Occurrence`（来自 `OccurrenceClosure.update()`
        的非 None 返回值）。
      dt: 仿真步长（与驱动该生成元时使用的 `dt` 相同语义）。
      transduction_config: 若该生成元由 `feed_from_skin()`/`tick_from_skin()`
        驱动（WORLD_COUPLED 模式），传入其使用的 `TransductionConfig` 作为
        `S_in,i`；否则为 `None`。
      site_calibration: 可选的 `SiteCalibration` 引用（Q3），默认 `None`。

    Returns:
      组装好的 `NaturalUnit`。
    """
    window = (occurrence.t_up, occurrence.t_rearm)
    duration_raw_steps = occurrence.t_rearm - occurrence.t_up
    duration_seconds = duration_raw_steps * dt

    trajectory = getattr(handle, "trajectory", None)
    physical_ledger: Tuple[TrajectoryRecord, ...] = (
        tuple(trajectory.window(occurrence.t_up, occurrence.t_rearm))
        if trajectory is not None else ()
    )

    return NaturalUnit(
        address=occurrence.address,
        port=(handle.site_index, handle.polarity),
        window=window,
        count_measure=occurrence.count,
        duration_raw_steps=duration_raw_steps,
        duration_seconds=duration_seconds,
        physical_ledger=physical_ledger,
        input_scale=transduction_config,
        site_calibration=site_calibration,
        # 评判修正（2026-07-30T113327.179.md）：生产路径必须携带来源
        # occurrence 的实例身份，不能只有共享的生成元地址。
        source_occurrence_instance_id=occurrence.instance_id,
    )
