"""tss.adapters.relation_occurrence_port_v1 — 关系发生 χ_ρ^(1) 的递归
消费接口（D2-1/P2-C 方案 §4，评判 ADOPT with amendments 后落地）。

TYPE:INFRA — 纯记录类型：把一次已资格化的关系发生 χ_ρ^(1) 打包为下一
生成深度可直接消费的 typed 端口对象（与 OccurrencePortV2 同族、同访问
纪律）。不新建任何电路/状态机——全部字段来自 D2-0 冻结产物
（relation_occurrence_candidates.csv + 重放重建的 raw relation track）。

## 访问纪律（方案 §5，OCC 合同硬边界的 depth-1 延伸）

**下一级不允许回头直接读取 RelationCell 微观内部态**——递归消费只读
本端口暴露的已资格化 occurrence 轨迹与谱系。禁止：read membrane charge
directly / read RelationInputNeuron internal state / read frozen bundle
trace（DIAGNOSTIC_INTERVENTION 实验除外，运行接口与研究诊断分开）。

## 字段（方案 §4 最低清单逐项；含步域三边界供 replay 驱动展开）

  occurrence_id         : 实例身份 "{rho_uid}#e{epoch_id}"（实例=谱系地址
                          +epoch，P2-B1X 裁定沿用）
  generation_depth      : 恒 1（关系发生；深度 0 属 OccurrencePortV2，
                          深度 2 的 χ_ρ₂^(2) 若产生属 D2-1 产物，不在本类）
  relation_lineage      : 关系谱系地址 uid（AddressRegistry 单一事实来源，
                          DOMAIN_RELATION_RHO，可回溯至双父生成元地址）
  parent_occurrence_ids : 构成本关系发生的父 occurrence 实例 id 元组
                          （物理支撑回指，如 "occ.thermal:thermpt28_warm#e1"）
  t_up/t_down/t_rearm         : 三边界（relation 积分步域，dt 同 G0）
  t_up_s/t_down_s/t_rearm_s   : 三边界物理秒
  dt                    : 积分步（canonical 0.001 s，G0-R0 状态A）
  raw_relation_track_ref: x_ρ(t) 原始轨迹引用（重放重建的 IMMUTABLE 缓存
                          文件路径——端口存引用不内嵌轨迹；E-1 教训：无
                          raw track 则活动类自然化候选不可计算）
  typed_input_provenance: 本次关系发生消费过的 typed 输入标签元组
                          （如 ("N1_phase",)——REPLAY_REFERENCE_ONLY 谱系）
  resource_ref          : 能量/资源账本引用（重建 replay 的 ledger 行）

禁止字段（方案 §4）：is_order / is_direction / relation_type /
semantic_label——语义标签不得进入端口（D2-M6 label-promotion 纪律）。

步域 t_up/t_rearm 使本端口可被 relation_replay_adapter.build_phase_drive
直接消费（duck-type 同 OccurrencePortV2）——RC-1 typed acceptance 的
机器兑现点：递归消费与基础消费走同一驱动展开函数，无手工解包。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class RelationOccurrencePortV1:
    occurrence_id: str
    relation_lineage: str
    parent_occurrence_ids: Tuple[str, ...]
    t_up: int
    t_down: int
    t_rearm: int
    t_up_s: float
    t_down_s: float
    t_rearm_s: float
    dt: float
    raw_relation_track_ref: str
    typed_input_provenance: Tuple[str, ...]
    resource_ref: str
    generation_depth: int = 1


def build_port(rho_uid: str, epoch_id: int,
               parent_occurrence_ids: Tuple[str, ...],
               t_up: int, t_down: int, t_rearm: int, dt: float,
               raw_relation_track_ref: str,
               typed_input_provenance: Tuple[str, ...],
               resource_ref: str) -> RelationOccurrencePortV1:
    """从 D2-0 冻结候选字段打包端口对象（零新信息，纯重排）。"""
    return RelationOccurrencePortV1(
        occurrence_id=f"{rho_uid}#e{epoch_id}",
        relation_lineage=rho_uid,
        parent_occurrence_ids=tuple(parent_occurrence_ids),
        t_up=t_up, t_down=t_down, t_rearm=t_rearm,
        t_up_s=t_up * dt, t_down_s=t_down * dt, t_rearm_s=t_rearm * dt,
        dt=dt, raw_relation_track_ref=raw_relation_track_ref,
        typed_input_provenance=tuple(typed_input_provenance),
        resource_ref=resource_ref)
