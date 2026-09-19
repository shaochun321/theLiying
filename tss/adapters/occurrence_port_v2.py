"""tss.adapters.occurrence_port_v2 — D2 消费接口概念合同（G0-R1 §19）。

TYPE:INFRA — 纯记录类型（概念合同，名称可在 D2-0 落地时调整）：把一次
基础发生 χ_i^(0) 打包为下一生成深度可直接消费的 typed 端口对象。
不新建任何电路/状态机——全部字段来自既有对象（`Occurrence` /
`GeneratedAddress` / typed_ports 标签）。

## D2 访问纪律（§19 末句，OCC 合同的硬边界）

**D2 不允许回头直接读取 G0 内部 neuron state**——关系层/自然化层只消费
本端口暴露的字段。研究观察面（O(t)：能量/隐藏态诊断）留在 research/
账本（R-2 裁定审计面），不进入本端口；`hidden_state=True` 之类研究者
语义标签禁止出现（§12）。

字段（§19 清单逐项）：
  occurrence_id     : 实例身份字符串（= OccurrenceInstanceId 的稳定序列化
                      "{address.uid}#e{epoch_id}"——实例身份=生成元地址+
                      epoch，P2-B1X 裁定，非站点身份）
  generation_depth  : 恒 0（基础发生；χ_ρ^(1) 属 D2 产物，不在本类）
  lineage_uid       : 生成元地址 uid（父谱系经 AddressRegistry 可回溯——
                      不复制整棵谱系树，地址系统是单一事实来源）
  parent_uids       : 直接父地址 uid 元组（物理支撑回指）
  t_up/t_down/t_rearm        : 三边界（generator step_index，by design）
  t_up_s/t_down_s/t_rearm_s  : 三边界物理秒（= Occurrence.to_physical(dt)）
  dt                : 生成元积分步（canonical 0.001 s，G0-R0 状态A）
  raw_track_ref     : Λ^phys 原始轨迹引用（文件路径/数据集键——端口存
                      引用不内嵌轨迹，raw track 本身在研究区数据交付）
  typed_input_ports : 本次发生消费过的 typed 端口标签元组（如 ("U_dotT",)）
                      ——D2 的 typed relation input candidates 来源
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from tss.generators.occurrence import Occurrence


@dataclass(frozen=True)
class OccurrencePortV2:
    occurrence_id: str
    lineage_uid: str
    parent_uids: Tuple[str, ...]
    t_up: int
    t_down: int
    t_rearm: int
    t_up_s: float
    t_down_s: float
    t_rearm_s: float
    dt: float
    raw_track_ref: str
    typed_input_ports: Tuple[str, ...]
    generation_depth: int = 0


def from_occurrence(ev: Occurrence, dt: float, raw_track_ref: str,
                    typed_input_ports: Tuple[str, ...]) -> OccurrencePortV2:
    """把既有 `Occurrence` 打包为 D2 端口对象（零新信息，纯重排）。"""
    t_up_s, t_down_s, t_rearm_s = ev.to_physical(dt)
    parents = tuple(getattr(p, "uid", str(p))
                    for p in ev.address.parent_addresses)
    return OccurrencePortV2(
        occurrence_id=f"{ev.address.uid}#e{ev.epoch_id}",
        lineage_uid=ev.address.uid,
        parent_uids=parents,
        t_up=ev.t_up, t_down=ev.t_down, t_rearm=ev.t_rearm,
        t_up_s=t_up_s, t_down_s=t_down_s, t_rearm_s=t_rearm_s,
        dt=dt, raw_track_ref=raw_track_ref,
        typed_input_ports=typed_input_ports)
