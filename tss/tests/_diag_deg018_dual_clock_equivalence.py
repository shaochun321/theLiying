"""_diag_deg018_dual_clock_equivalence — DEG-018 双时钟等价性审计（EXP-DEG018-01）。

TYPE:INFRA（diagnostic，不被 pytest 收集）

审计依据：degradation_registry DEG-018 + 用户裁定 2026-09-07"审计先行——
等价性证明成立才合并二态，否则保留双时钟并把审计结论补进登记"。

## 审计问题

`OccurrenceClosure` 的 REFRACTORY 整数计步时钟（rearm_min_steps=500）相对
theta_down 迟滞时钟是否**冗余**？冗余 = 在全部消费方可见维度上
rearm=0 与 rearm=500 不可分辨。

## 三个流

  FLOW-A 真实链路：RPrecCircuitT1 site28 加热 900 步→撤热，双 oracle
         （rearm=0 / rearm=500）喂**同一** collector.pre_trace 流，比较
         事件计数 / t_up / t_down / t_rearm / epoch_id
  FLOW-B 对抗边界：合成流在 t_down 后 gap∈{100,300,499,501,1000} 步处
         开新支撑 epoch 并再越 theta_up——刻画第二时钟改变行为的精确边界
  FLOW-C 消费方可见性：rearm 事件时刻 = relation_occurrence.RelationFinalizer
         的 occurrence 登记触发点（step() 读 "rearm" transition）——
         t_rearm 的系统性偏移直接平移下游登记时刻，按 T3 实测关系窗
         （Δt₂⊂[35,319]）同数量级即为消费方可见

## 判定纪律

  等价性按维度分别判定，不合并成单一"PASS"：计数等价 ≠ 时刻等价。
  只要存在消费方可见的不可分辨性破缺，即判"非严格等价"→ 按用户裁定
  不合并二态，把定量边界补进 DEG-018 登记。

入口：PYTHONIOENCODING=utf-8 python -m tss.tests._diag_deg018_dual_clock_equivalence
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.components.structural_address import AddressRegistry, DOMAIN_SKIN_PATCH
from nexus_v1.components.world import HeatSource
from tss.generators.occurrence import OccurrenceClosure
from tss.generators.base_generator import register_occ_thermal
from tss.relations.temporal_r_prec import RPrecCircuitT1
from tss.tests.test_tss3a_theta_distance_audit import _reseed_site

DT = 0.001
SITE = 28
N_STEPS = 6000
HEAT_OFF_AT = 900          # 900 驱动 + 撤去观测（P2-A1b-3R 既有方法论）
HEAT_RADIUS = 3.0
REARM_VARIANTS = (0, 500)  # 双 oracle


def _make_closure(rearm: int):
    registry = AddressRegistry()
    parent = registry.register_physical(DOMAIN_SKIN_PATCH, f"thermpt{SITE}")
    addr = register_occ_thermal(registry, f"thermpt{SITE}_warm_r{rearm}", parent)
    return OccurrenceClosure(address=addr, rearm_min_steps=rearm)


def _drive_dual(value_stream, support_stream):
    """同一 (value, phys_support) 流喂双 oracle，返回逐 oracle 事件记录。"""
    out = {}
    for rearm in REARM_VARIANTS:
        clo = _make_closure(rearm)
        rearm_steps = []
        for t, (v, sup) in enumerate(zip(value_stream, support_stream)):
            ev = clo.update(v, t, phys_support=sup)
            if ev is not None:
                rearm_steps.append(t)
        out[rearm] = {
            "events": [(e.t_up, e.t_down, e.t_rearm, e.epoch_id)
                       for e in clo.events],
            "rearm_visible_steps": rearm_steps,
        }
    return out


def flow_a_real_chain():
    """FLOW-A：真实链路 pre_trace 流（录一次，双 oracle 共享）。"""
    circuit = RPrecCircuitT1()
    _reseed_site(circuit, SITE, None)
    patch = circuit._thermal_quantum_patches[SITE]
    pos = patch.world_position(circuit.world.body)
    circuit.world.heat_sources = [HeatSource(
        position=list(pos), energy=100000.0, temperature=300.0,
        radius=HEAT_RADIUS, _drift=[0.0, 0.0, 0.0])]
    collector = circuit.thermal_quantum_collectors[f"thermpt{SITE}_warm"]

    values, supports = [], []
    for t in range(N_STEPS):
        if t == HEAT_OFF_AT:
            circuit.world.heat_sources = []
        circuit.step({}, DT)
        values.append(collector.pre_trace)
        supports.append(t < HEAT_OFF_AT)
    return _drive_dual(values, supports), values


def flow_b_adversarial(gaps=(100, 300, 499, 501, 1000)):
    """FLOW-B：t_down 后 gap 步开新 epoch 再越阈——第二时钟的行为边界。

    合成流（状态机层，无电路）：epoch1 方波 0.02 持续 200 步→归零
    （t_down≈200），静默 gap 步后 epoch2 同样方波。
    """
    results = {}
    for gap in gaps:
        values, supports = [], []
        # epoch 1
        values += [0.02] * 200 + [0.0] * gap
        supports += [True] * 200 + [False] * gap
        # epoch 2（新物理支撑上升沿 + 再越 theta_up）
        values += [0.02] * 200 + [0.0] * 700
        supports += [True] * 200 + [False] * 700
        results[gap] = _drive_dual(values, supports)
    return results


def main():
    print("=" * 68)
    print("EXP-DEG018-01 双时钟等价性审计（rearm=0 vs rearm=500）")
    print("=" * 68)

    # ── FLOW-A ──
    dual_a, values = flow_a_real_chain()
    print("\n[FLOW-A] 真实链路（site28 加热900步→撤热，共%d步）" % N_STEPS)
    for rearm in REARM_VARIANTS:
        print(f"  rearm={rearm}: events={dual_a[rearm]['events']}")
    ev0, ev5 = dual_a[0]["events"], dual_a[500]["events"]
    a_count_eq = len(ev0) == len(ev5)
    a_updown_eq = ([(e[0], e[1]) for e in ev0] == [(e[0], e[1]) for e in ev5])
    a_rearm_shift = ([e[2] for e in ev5][0] - [e[2] for e in ev0][0]
                     if (ev0 and ev5) else None)
    print(f"  计数等价: {a_count_eq}   t_up/t_down 等价: {a_updown_eq}   "
          f"t_rearm 偏移: {a_rearm_shift}")

    # ── FLOW-B ──
    dual_b = flow_b_adversarial()
    print("\n[FLOW-B] 对抗边界（t_down 后 gap 步开新 epoch 再越阈）")
    print(f"  {'gap':>5} | {'rearm=0 计数':>10} | {'rearm=500 计数':>12} | 计数等价")
    b_boundary = {}
    for gap, d in sorted(dual_b.items()):
        n0, n5 = len(d[0]["events"]), len(d[500]["events"])
        b_boundary[gap] = (n0, n5)
        print(f"  {gap:>5} | {n0:>10} | {n5:>12} | {n0 == n5}")

    # ── FLOW-C（分析性结论，用 A 的实测偏移量化）──
    print("\n[FLOW-C] 消费方可见性")
    print("  RelationFinalizer.step() 以 'rearm' transition 为 occurrence")
    print("  登记触发点（relation_occurrence.py）——FLOW-A 实测 t_rearm 偏移"
          f" +{a_rearm_shift} 步")
    print("  对照 T3/C0 实测关系窗 Δt₂ ⊂ [35, 319] 步：同数量级 ⇒ 偏移对"
          "下游登记时刻消费方可见")

    # ── 判定 ──
    print("\n" + "=" * 68)
    print("判定（按维度分别判定，不合并单一 PASS）")
    print("=" * 68)
    diverge_gaps = [g for g, (n0, n5) in b_boundary.items() if n0 != n5]
    print(f"  1. 发生计数（真实链路）      : {'等价' if a_count_eq else '不等价'}")
    print(f"  2. t_up/t_down（真实链路）   : {'等价' if a_updown_eq else '不等价'}")
    print(f"  3. t_rearm/下游可见时刻      : 不等价（系统性 +{a_rearm_shift} 步，"
          "消费方可见）" if a_rearm_shift else "  3. t_rearm: 无事件，无法判定")
    print(f"  4. 短间隔重臂（gap<500）计数 : "
          f"{'不等价（gap=' + str(diverge_gaps) + ' 处第二时钟抑制/延迟新发生）' if diverge_gaps else '等价'}")
    strictly_equivalent = (a_count_eq and a_updown_eq
                          and a_rearm_shift in (0, None) and not diverge_gaps)
    print(f"\n  严格等价（全维度）: {strictly_equivalent}")
    if not strictly_equivalent:
        print("  ⇒ 按用户裁定（2026-09-07 审计先行）：**不合并二态**——")
        print("    第二时钟不是冗余；把上述定量边界补进 DEG-018 登记，")
        print("    降为『已定量刻画的设计决定』。")
    else:
        print("  ⇒ 全维度等价，可进入合并二态实施（迁移全部消费方+回归）。")
    return {
        "flow_a": dual_a, "flow_b_boundary": b_boundary,
        "rearm_shift": a_rearm_shift,
        "strictly_equivalent": strictly_equivalent,
    }


if __name__ == "__main__":
    main()
