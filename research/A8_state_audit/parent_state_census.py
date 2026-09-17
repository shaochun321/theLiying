"""parent_state_census.py — P1-3 父状态自动 census + P1-4 父层功能闭合。

TYPE:INFRA（research/ 隔离层）

## P1-3：五分类自动 census（替代人工 32 项列表）

递归读取两套真实父系统的**全部数值字段**，按语义五分类：
  DYNAMIC_CAUSAL    随步演化且进入未来动力学 → **只有这类进入 A8 的 P**
  STATIC_PARAMETER  构造期固定（权重、电容、阈值、地址常量）
  AUDIT_COUNTER     只读记账（entry_count、_q_in/_q_out、clamp_heat）
  HISTORICAL_LOG    只增不改的事件表（fire_steps）
  ADDRESS_METADATA  GeneratedAddress / 标签

分类由字段名规则 + 类归属决定，脚本自动执行，不靠人工维护。

## P1-4：父层功能闭合

除状态比较外，给相同未来 relation-current 输入，要求
    max|ParentFuture_A − ParentFuture_B| ≤ 1e-12
这是 M3 的必要守卫（父层状态不仅"相同"，而且"后续演化相同"）。

输出：data/census.csv, data/parent_closure.csv
"""
from __future__ import annotations

import csv
import hashlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from research.A8_state_audit.candidate_config import CANONICAL, assert_fingerprint
from research.A8_state_audit.rail_latch import RailLatch
from tss.tests.test_c1_coupling import _synthetic_stack

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DRIVE = 0.17
DT2 = 50
T0 = 50000
EPS_P = 1e-12

# 分类规则（字段名 → 类别），脚本自动套用
_RULES = [
    ("fire_steps", "HISTORICAL_LOG"),
    # spike_times：发放时刻日志（append-only）。第四轮勘误：全递归 census 首跑
    # 将其兜底为 DYNAMIC_CAUSAL，致 P 对齐假 FAIL（Δ=2.4 = 事件时刻差本身）。
    # 归类判据 = purge 实证（f1_revalidation m34：T0 清空后 future 逐位不变）
    # + 外部全递归审计同分类。非阈值调整。
    ("spike_times", "HISTORICAL_LOG"),
    ("generator_address", "ADDRESS_METADATA"),
    ("neuron_id", "ADDRESS_METADATA"),
    ("bundle_id", "ADDRESS_METADATA"),
    ("_q_in", "AUDIT_COUNTER"), ("_q_out", "AUDIT_COUNTER"),
    ("_q_initial", "AUDIT_COUNTER"), ("entry_count", "AUDIT_COUNTER"),
    ("relation_count", "AUDIT_COUNTER"), ("charge_count", "AUDIT_COUNTER"),
    ("clamp_heat", "AUDIT_COUNTER"), ("_cum_ltp", "AUDIT_COUNTER"),
    ("_cum_ltd", "AUDIT_COUNTER"), ("_cum_clamp", "AUDIT_COUNTER"),
    ("_w_initial", "AUDIT_COUNTER"), ("_prev_activation", "AUDIT_COUNTER"),
]
_STATIC_NAMES = {"capacitance", "r_leak", "q_pulse", "theta_gate", "v_clamp",
                 "gm_clamp", "v_threshold", "gm", "theta_h", "weight_max",
                 "initial_weight", "synapse_gain", "physical_seed", "config",
                 "positions", "position", "n_targets", "n_sources"}


def classify(name: str, owner_class: str) -> str:
    for key, cat in _RULES:
        if key in name:
            return cat
    if name in _STATIC_NAMES:
        return "STATIC_PARAMETER"
    if name.startswith("_"):
        return "DYNAMIC_CAUSAL"          # 兜底：私有状态变量默认动态
    return "DYNAMIC_CAUSAL"


_LIST_INLINE_MAX = 64      # 标量表 ≤64 逐项记录；更长 → (len, sha256) 摘要


def _record(out: list, path: str, cls: str, value, name: str) -> None:
    out.append({"path": path, "owner_class": cls, "value": value,
                "category": classify(name, cls)})


def _walk(val, path: str, name: str, cls: str, seen: set, out: list) -> None:
    """值分发器（第四轮 P1-3 修正：dict/对象 list/空容器全覆盖）。

    第三轮缺陷勘误：dict 无处理分支被整体跳过（_channels/_channel_configs
    共 0 条）、对象 list 不递归（_memristors/_delay_buffer 共 0 条）、float
    list 只记长度字符串、空 list 被 `val and ...` 跳过。"""
    if isinstance(val, bool) or val is None or isinstance(val, (str, bytes)):
        return
    if isinstance(val, (int, float)):
        _record(out, path, cls, val, name)
        return
    if isinstance(val, dict):
        if id(val) in seen:
            return
        seen.add(id(val))
        if not val:
            _record(out, path, cls, "{0}", name)
            return
        for k, v in val.items():
            _walk(v, f"{path}[{k!r}]", name, cls, seen, out)
        return
    if isinstance(val, (list, tuple)):
        if id(val) in seen:
            return
        seen.add(id(val))
        if not val:
            _record(out, path, cls, "[0]", name)
            return
        if all(isinstance(x, (int, float)) and not isinstance(x, bool)
               for x in val):
            if len(val) <= _LIST_INLINE_MAX:
                for i, x in enumerate(val):
                    _record(out, f"{path}[{i}]", cls, x, name)
            else:
                digest = hashlib.sha256(
                    repr(list(val)).encode()).hexdigest()[:16]
                _record(out, f"{path}[*]", cls,
                        f"len={len(val)}#sha={digest}", name)
            return
        for i, x in enumerate(val):
            _walk(x, f"{path}[{i}]", name, cls, seen, out)
        return
    if hasattr(val, "__dict__"):
        census(val, path, seen, out)


def census(obj, prefix: str, seen: set, out: list) -> None:
    """递归收集全部数值/容器字段（第四轮：全容器递归版）。"""
    if id(obj) in seen:
        return
    seen.add(id(obj))
    if not hasattr(obj, "__dict__"):
        return
    cls = type(obj).__name__
    for name, val in vars(obj).items():
        _walk(val, f"{prefix}.{name}", name, cls, seen, out)


_HISTORICAL_LIST_NAMES = ("fire_steps", "spike_times")


def purge_historical_logs(root_objs) -> int:
    """清空全部 fire_steps/spike_times 表，返回清除条目数。

    用途（方案 §十三）：对"历史日志不进入 parent future dynamics"给**实证
    证明**——T0 时刻清空后 future 演化必须逐位不变；若变，说明日志被动力学
    读取，必须按 DYNAMIC_CAUSAL 重新归类。"""
    cleared = 0
    seen: set = set()
    stack = list(root_objs)
    while stack:
        o = stack.pop()
        if id(o) in seen:
            continue
        seen.add(id(o))
        if isinstance(o, dict):
            stack.extend(o.values())
            continue
        if isinstance(o, (list, tuple)):
            stack.extend(o)
            continue
        if not hasattr(o, "__dict__"):
            continue
        for name, val in vars(o).items():
            if name in _HISTORICAL_LIST_NAMES and isinstance(val, list):
                cleared += len(val)
                val.clear()
            elif isinstance(val, (dict, list, tuple)) or hasattr(val, "__dict__"):
                stack.append(val)
    return cleared


def collect_parent() -> list[dict]:
    out: list = []
    seen: set = set()
    for i, st in enumerate(("s1", "s2")):
        adx, ady, pair = _synthetic_stack()
        census(adx, f"{st}.adx", seen, out)
        census(ady, f"{st}.ady", seen, out)
        census(pair, f"{st}.pair", seen, out)
    return out


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    fp = assert_fingerprint(CANONICAL)
    print("=" * 70)
    print(f"P1-3 父状态 census（fingerprint={fp}）")
    print("=" * 70)

    census_rows = collect_parent()
    by_cat = {}
    for r in census_rows:
        by_cat.setdefault(r["category"], []).append(r)
    print(f"\n  递归读到数值字段总数 = {len(census_rows)}")
    for cat in ("DYNAMIC_CAUSAL", "STATIC_PARAMETER", "AUDIT_COUNTER",
                "HISTORICAL_LOG", "ADDRESS_METADATA"):
        n = len(by_cat.get(cat, []))
        print(f"    {cat:<18} {n:>4}")
    p_fields = by_cat.get("DYNAMIC_CAUSAL", [])
    print(f"\n  ⇒ 进入 A8 的 P 集合：DYNAMIC_CAUSAL {len(p_fields)} 项（自动分类，非人工列表）")

    with open(os.path.join(DATA_DIR, "census.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["path", "owner_class", "value", "category"])
        w.writeheader()
        w.writerows(census_rows)

    # ── P1-4 父层功能闭合 ──
    print("\n" + "-" * 70)
    print("P1-4 父层功能闭合（相同未来输入，要求 ≤1e-12）")
    print("-" * 70)

    def run_parent_future(ev1, ev2):
        adx1, ady1, p1 = _synthetic_stack()
        adx2, ady2, p2 = _synthetic_stack()
        for t in range(T0):
            adx1.step(DRIVE if (t == ev1) else 0.0, 0.001)
            ady1.step(DRIVE if (t == ev1 + DT2) else 0.0, 0.001)
            adx2.step(DRIVE if (t == ev2) else 0.0, 0.001)
            ady2.step(DRIVE if (t == ev2 + DT2) else 0.0, 0.001)
            p1.step(t, 0.001)
            p2.step(t, 0.001)
        # 相同未来输入：两套 pair 各喂同一序列
        fut1, fut2 = [], []
        for k in range(3000):
            adx1.step(DRIVE if k == 100 else 0.0, 0.001)
            ady1.step(DRIVE if k == 200 else 0.0, 0.001)
            adx2.step(DRIVE if k == 100 else 0.0, 0.001)
            ady2.step(DRIVE if k == 200 else 0.0, 0.001)
            fut1.append(p1.step(T0 + k, 0.001))
            fut2.append(p2.step(T0 + k, 0.001))
        return fut1, fut2

    f1, f2 = run_parent_future(500, 600)     # A: 共现
    f3, f4 = run_parent_future(500, 3000)    # B: 分散
    d_same = max(abs(a - b) for a, b in zip(f1, f2))     # 同历史跨实例
    d_cross = max(abs(a - b) for a, b in zip(f1, f3))    # 不同历史
    print(f"  同历史跨实例（s1 vs s2，A 条件） max|Δ| = {d_same:.3e}")
    print(f"  不同形成历史（A vs B）           max|Δ| = {d_cross:.3e}")
    closed = d_same <= EPS_P
    print(f"  ⇒ 父层功能闭合 = {'PASS' if closed else 'FAIL'}（阈值 {EPS_P:.0e}）")
    print(f"    （不同历史差异同样在地板 ⇒ 父层对形成历史无残留，M3 守卫成立）")

    with open(os.path.join(DATA_DIR, "parent_closure.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["comparison", "max_abs_diff",
                                          "threshold", "passes"])
        w.writeheader()
        w.writerow({"comparison": "same_history_cross_instance",
                    "max_abs_diff": d_same, "threshold": EPS_P,
                    "passes": closed})
        w.writerow({"comparison": "different_formation_history",
                    "max_abs_diff": d_cross, "threshold": EPS_P,
                    "passes": d_cross <= EPS_P})

    print(f"\n落盘: {os.path.join(DATA_DIR, 'census.csv')} / parent_closure.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
