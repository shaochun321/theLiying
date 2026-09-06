"""T-RLI-DEDUP：P2-B1X1e 去重防线验证（2026-07-31）。

方案依据：`cell-cell/交叉比对/document - 2026-07-31T203403.976.md`评判——
调试P2-B1X1d时发现，连续（非脈冲）驱动下同一对父occurrence可能在残余振荡
下让relation collector产生第二次上升沿，若不加防线会重复登记两份
RelationOccurrence。

本测试**不跑完整3000步物理仿真**（避免重演P2-B1X1d标定阶段的暴力网格
搜索开销）——去重逻辑本身只依赖tap.address/tap.closure.epoch_id/
tap.last_transitions/relation_collector.pre_trace 这几个读出量，用最小
fake对象直接驱动`RelationFinalizer.step()`即可验证，不需要真实神经元/
World物理链路。

三个测试：
  T-RLI-DEDUP-1：同一父实例对，collector两次上升沿（模拟残余复发）——
                 只应产生1个RelationOccurrence，不是2个
  T-RLI-DEDUP-2：真正新epoch（父occurrence进入下一次发生）——应允许
                 产生第二个RelationOccurrence（去重键随epoch变化）
  T-RLI-DEDUP-3：两次上升沿之间存在OPEN但未闭合的draft时不重复创建
                 （去重同样防止"重复挂起"，不止是防止"重复闭合"）
"""
import sys

sys.path.insert(0, '.')

from dataclasses import dataclass, field
from typing import List, Tuple

from nexus_v1.components.structural_address import (
    DOMAIN_OCC_THERMAL, GeneratedAddress, StructuralAddress,
)
from tss.generators.occurrence import Occurrence, OccurrenceInstanceId, TransitionEvent
from tss.generators.occurrence_identity import OccurrenceIdentityRegistry
from tss.relations.relation_occurrence import (
    RelationFinalizer, RELATION_TYPE_A_PREC_B_FAST, DRAFT_STATUS_OPEN,
)

_SKIN_A = StructuralAddress(domain="skin.patch", uid="skin.patch:thermpt28")
_SKIN_B = StructuralAddress(domain="skin.patch", uid="skin.patch:thermpt31")
_ADDR_A = GeneratedAddress(domain=DOMAIN_OCC_THERMAL, uid="occ.thermal:thermpt28_warm",
                            parent_addresses=(_SKIN_A,), generation_depth=1)
_ADDR_B = GeneratedAddress(domain=DOMAIN_OCC_THERMAL, uid="occ.thermal:thermpt31_warm",
                            parent_addresses=(_SKIN_B,), generation_depth=1)
_COL_ADDR = StructuralAddress(domain="neuron.collector", uid="rprec_collector_a_prec_b_fast")


@dataclass
class _FakeCollector:
    """relation_collector 的最小替身：finalizer 只读 .pre_trace。"""
    pre_trace: float = 0.0


@dataclass
class _FakeClosure:
    """OccurrenceClosure 的最小替身：finalizer 只读 .epoch_id/.events。"""
    epoch_id: int = 1
    events: List[Occurrence] = field(default_factory=list)


@dataclass
class _FakeTap:
    """CollectorOccurrenceTap 的最小替身：finalizer 只读
    .address/.closure/.last_transitions。"""
    address: GeneratedAddress
    closure: _FakeClosure = field(default_factory=_FakeClosure)
    last_transitions: Tuple[TransitionEvent, ...] = field(default_factory=tuple)

    def emit_rearm(self, t_step: int, occ: Occurrence):
        """模拟一次真实rearm：closure.events追加occurrence，
        last_transitions暴露对应的rearm事件（finalizer.step()第1步靠这个
        把occurrence登记进registry）。"""
        self.closure.events.append(occ)
        self.last_transitions = (
            TransitionEvent(generator_address=self.address, epoch_id=self.closure.epoch_id,
                             kind="rearm", t_step=t_step),
        )

    def clear_transitions(self):
        self.last_transitions = ()


def _make_finalizer(tap_a, tap_b):
    registry = OccurrenceIdentityRegistry()
    collector = _FakeCollector()
    finalizer = RelationFinalizer(
        tap_a=tap_a, tap_b=tap_b, registry=registry,
        relation_collector=collector,
        collector_address=_COL_ADDR,
        relation_type=RELATION_TYPE_A_PREC_B_FAST,
        trace_scale="fast",
    )
    return finalizer, collector


def test_rli_dedup_1_residual_recurrence_not_duplicated():
    """T-RLI-DEDUP-1：同一对父occurrence，collector两次上升沿——只应
    产生1个RelationOccurrence（模拟P2-B1X1d发现的残余复发场景）。"""
    tap_a = _FakeTap(address=_ADDR_A)
    tap_b = _FakeTap(address=_ADDR_B)
    finalizer, collector = _make_finalizer(tap_a, tap_b)

    # t=0: A/B父occurrence真实完成rearm（epoch_id=1，两者相同）
    occ_a = Occurrence(t_up=100, t_down=150, t_rearm=200, address=_ADDR_A, epoch_id=1)
    occ_b = Occurrence(t_up=90, t_down=140, t_rearm=190, address=_ADDR_B, epoch_id=1)
    tap_a.emit_rearm(0, occ_a)
    tap_b.emit_rearm(0, occ_b)

    completed = []

    # t=1: collector第一次上升沿
    collector.pre_trace = 0.5
    ro = finalizer.step(1)
    if ro is not None:
        completed.append(ro)
    tap_a.clear_transitions()
    tap_b.clear_transitions()

    # t=2: collector跌落（模拟脈冲结束）
    collector.pre_trace = 0.0
    ro = finalizer.step(2)
    if ro is not None:
        completed.append(ro)

    # t=3: collector残余振荡，第二次上升沿——父occurrence仍是同一对
    # (epoch_id都还是1，因为A/B都没有新的真实发生)
    collector.pre_trace = 0.5
    ro = finalizer.step(3)
    if ro is not None:
        completed.append(ro)

    print(f"T-RLI-DEDUP-1: completed={len(completed)}, "
          f"finalizer.completed_relations={len(finalizer.completed_relations)}")
    assert len(finalizer.completed_relations) == 1, (
        f"同一对父occurrence(epoch_id相同)在残余复发下应只产生1个"
        f"RelationOccurrence，实际={len(finalizer.completed_relations)}")
    print("✓ T-RLI-DEDUP-1 PASS: 残余复发未产生重复RelationOccurrence")


def test_rli_dedup_2_new_epoch_allows_new_relation():
    """T-RLI-DEDUP-2：父occurrence真正进入新epoch（新的真实发生）——
    去重键随epoch变化，应允许产生第二个RelationOccurrence。"""
    tap_a = _FakeTap(address=_ADDR_A)
    tap_b = _FakeTap(address=_ADDR_B)
    finalizer, collector = _make_finalizer(tap_a, tap_b)

    occ_a1 = Occurrence(t_up=100, t_down=150, t_rearm=200, address=_ADDR_A, epoch_id=1)
    occ_b1 = Occurrence(t_up=90, t_down=140, t_rearm=190, address=_ADDR_B, epoch_id=1)
    tap_a.emit_rearm(0, occ_a1)
    tap_b.emit_rearm(0, occ_b1)

    collector.pre_trace = 0.5
    finalizer.step(1)
    tap_a.clear_transitions()
    tap_b.clear_transitions()
    collector.pre_trace = 0.0
    finalizer.step(2)

    assert len(finalizer.completed_relations) == 1

    # 父occurrence进入新epoch=2（真正的第二次A/B发生）
    tap_a.closure.epoch_id = 2
    tap_b.closure.epoch_id = 2
    occ_a2 = Occurrence(t_up=1100, t_down=1150, t_rearm=1200, address=_ADDR_A, epoch_id=2)
    occ_b2 = Occurrence(t_up=1090, t_down=1140, t_rearm=1190, address=_ADDR_B, epoch_id=2)
    tap_a.emit_rearm(3, occ_a2)
    tap_b.emit_rearm(3, occ_b2)

    collector.pre_trace = 0.5
    finalizer.step(4)

    print(f"T-RLI-DEDUP-2: completed_relations={len(finalizer.completed_relations)}")
    assert len(finalizer.completed_relations) == 2, (
        f"新epoch的父occurrence应允许产生新的RelationOccurrence，"
        f"实际={len(finalizer.completed_relations)}")
    ids = {(r.parent_a_instance_id.epoch_id, r.parent_b_instance_id.epoch_id)
           for r in finalizer.completed_relations}
    assert ids == {(1, 1), (2, 2)}, f"两次关系应分别对应epoch(1,1)和(2,2)，实际={ids}"
    print("✓ T-RLI-DEDUP-2 PASS: 新epoch正确产生新的RelationOccurrence，去重键随epoch变化")


def test_rli_dedup_3_open_draft_not_duplicated():
    """T-RLI-DEDUP-3：collector上升沿后父occurrence尚未完成rearm
    （draft仍是OPEN），此时若collector再次上升沿，不应创建第二份OPEN
    draft——去重同样防止"重复挂起"，不止是防止"重复闭合"。"""
    tap_a = _FakeTap(address=_ADDR_A)
    tap_b = _FakeTap(address=_ADDR_B)
    finalizer, collector = _make_finalizer(tap_a, tap_b)

    # 手动预置tap的epoch_id=1，但不emit rearm——模拟父occurrence还在
    # ACTIVE/REFRACTORY阶段、尚未完成闭合（registry里查不到）。
    tap_a.closure.epoch_id = 1
    tap_b.closure.epoch_id = 1

    collector.pre_trace = 0.5
    finalizer.step(1)  # 第一次上升沿：创建OPEN draft（父occurrence未就绪，不会闭合）
    collector.pre_trace = 0.0
    finalizer.step(2)  # 跌落
    collector.pre_trace = 0.5
    finalizer.step(3)  # 第二次上升沿：同一对父实例仍未就绪，不应重复创建draft

    open_drafts = [d for d in finalizer._open_drafts if d.status == DRAFT_STATUS_OPEN]
    print(f"T-RLI-DEDUP-3: open_drafts={len(open_drafts)}, "
          f"completed_relations={len(finalizer.completed_relations)}")
    assert len(open_drafts) == 1, (
        f"同一对父实例在未就绪期间的重复上升沿不应产生第二份OPEN draft，"
        f"实际open_drafts={len(open_drafts)}")
    print("✓ T-RLI-DEDUP-3 PASS: 未就绪期间的重复上升沿未产生重复draft")


def run():
    test_rli_dedup_1_residual_recurrence_not_duplicated()
    test_rli_dedup_2_new_epoch_allows_new_relation()
    test_rli_dedup_3_open_draft_not_duplicated()
    print()
    print("=" * 60)
    print("T-RLI-DEDUP-1~3 ALL PASS")
    print("=" * 60)


if __name__ == "__main__":
    run()
