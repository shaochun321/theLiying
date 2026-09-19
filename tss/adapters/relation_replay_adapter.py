"""tss.adapters.relation_replay_adapter — OccurrencePortV2/RawOccurrenceTrack
→ 关系结构的 replay 驱动序列（D2-0 E-2 接口缺口的最小填补）。

TYPE:INFRA — 反馈 §3.1 指名的 production 侧唯一新增 adapter。旧 tss
relation primitive 是 live circuit coupled（消费 l1/collector 对象引用）；
D2-0 是 qualified occurrence replay coupled——本模块把已资格化 occurrence
的 typed 端口转为逐子步驱动样本，供关系结构以 replay 消费，**不回读 G0
内部 neuron state**（方案 §3 纪律：允许字段仅 port 六项+raw track 引用）。

驱动量 = N1 局部相位 ϑ_i(t)=(t−t↑)/(t_rearm−t↑)∈[0,1]（Step2 资格
QUALIFIED_REFERENCE）。**REPLAY_REFERENCE_ONLY**：分母含 t_rearm，只在
occurrence 完成后可知——live 端到端前须因果变体
（CAUSAL_VARIANT_REQUIRED_BEFORE_LIVE_D2，反馈 §五登记）。

parent_support 语义（E-5/反馈 §六）：= 该 parent 存在活跃 occurrence 窗
[t_up, t_rearm)。关系 closure 的 epoch/token 门控消费此标志——关系结构
内部振荡在无父支撑时不得产生新的物理确认（ΔC_phys=0）。

依赖方向：仅 stdlib + 同包 occurrence_port_v2（tss→nexus_v1 单向铁律
不受影响；本模块不 import nexus_v1 电路对象——驱动样本是纯数据）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from tss.adapters.occurrence_port_v2 import OccurrencePortV2


@dataclass(frozen=True)
class RelayDriveSample:
    """一个子步的关系驱动样本（单 parent 通道）。"""
    t_phys: float
    value: float           # ϑ(t)∈[0,1]，窗外=0
    parent_support: bool   # 是否处于某 parent occurrence 窗内
    parent_epoch: int      # 支撑窗序号（第 n 个 occurrence，无支撑=0）


def build_phase_drive(t_total_steps: int, dt: float,
                      ports: Sequence[OccurrencePortV2]
                      ) -> List[RelayDriveSample]:
    """把一个 parent 的 occurrence 端口序列展开为逐子步驱动序列。

    REPLAY_REFERENCE_ONLY（见模块 docstring）。多个 occurrence 窗按
    时间不重叠（G0 closure 状态机保证 rearm 之前不重触发）。
    """
    windows = sorted(
        ((p.t_up, p.t_rearm) for p in ports), key=lambda w: w[0])
    out: List[RelayDriveSample] = []
    wi = 0
    for k in range(t_total_steps):
        value, support, epoch = 0.0, False, 0
        while wi < len(windows) and k >= windows[wi][1]:
            wi += 1
        if wi < len(windows):
            t_up, t_rearm = windows[wi]
            if t_up <= k < t_rearm:
                value = (k - t_up) / (t_rearm - t_up)
                support = True
                epoch = wi + 1
        out.append(RelayDriveSample(t_phys=k * dt, value=value,
                                    parent_support=support,
                                    parent_epoch=epoch))
    return out
