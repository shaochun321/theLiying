"""_diag_c1_runtime_lineage_collision — A9 运行时实例谱系缺口登记（EXT-2 P1-2）。

TYPE:INFRA（diagnostic，不被 pytest 收集）

审计依据：《TSS C1 理论资格复审后的代码修改清单》P1-2（2026-09-09/10 外部
数值复审）。本脚本**只登记缺口，不实现 binder**（P1-3：禁止把 Python/INFRA
身份判断放进 BIO/SEMI 物理发放条件；正式修复须待理论裁定，方向是独立的
lineage audit/binding sidecar，且 sidecar 不得改变 spike/Θ/gate）。

## 审计问题

`RelationEventAdapter.step(self, r_current, dt)` 的物理接口只消费
r_current 与 dt，不消费 RelationOccurrence / parent occurrence instance
IDs / relation window / ledger snapshot / runtime epoch identity。

因此两个不同 relation instance（Relation A/Epoch1 vs Relation A/Epoch2）
只要产生完全相同的 r_current(t)，adapter 与 C1 后续物理路径无法区分。

## 实验（清单原文两 case）

  case A: relation instance lineage = Epoch1/Epoch1, physical r traces = X
  case B: relation instance lineage = Epoch1/Epoch2, physical r traces = X

lineage 只能以 INFRA 元数据形式声明（物理路径根本没有可传入的端口——
这正是缺口本身）。确认：adapter pulses identical，c_ro identical。

## 判定纪律

exit 0 表示：**已正确复现并登记缺口（A9_RUNTIME_INSTANCE_LINEAGE = GAP）**。
不是：A9 PASS。

入口：PYTHONIOENCODING=utf-8 python -m tss.tests._diag_c1_runtime_lineage_collision
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import inspect

from tss.relations.relation_event_adapter import RelationEventAdapter
from tss.tests.test_c1_coupling import DT, _run_synthetic_recording

N = 900
R_TRACE_X = ({100}, {400})     # 同一条物理 r trace X：父A@100 / 父B@400


def _run_case(lineage_tag_x: str, lineage_tag_y: str):
    """跑一遍合成 C1 栈。lineage 仅为 INFRA 声明——物理接口无端口可消费它。"""
    lineage = {"parent_x_instance": lineage_tag_x,
               "parent_y_instance": lineage_tag_y}   # 声明即全部：无处可传入
    spikes_x, spikes_y, c_trace = _run_synthetic_recording(
        R_TRACE_X[0], R_TRACE_X[1], N)
    return lineage, spikes_x, spikes_y, c_trace


def main() -> int:
    print("=" * 68)
    print("EXT-2 P1-2: A9 运行时 relation-instance 谱系缺口登记")
    print("=" * 68)

    # ── 接口审计：物理签名没有 instance 身份端口 ──
    sig = inspect.signature(RelationEventAdapter.step)
    params = list(sig.parameters)
    print(f"\n[接口] RelationEventAdapter.step 参数 = {params}")
    assert params == ["self", "r_current", "dt"], (
        "接口已变化——本诊断的缺口描述需要重新审计")
    for forbidden in ("occurrence", "epoch", "instance", "window", "ledger"):
        assert all(forbidden not in p.lower() for p in params)
    print("[接口] 无 RelationOccurrence/instance ID/window/ledger/epoch 端口"
          "——运行时身份在物理路径上不存在")

    # ── 行为审计：不同 lineage 声明 + 相同 r trace → 完全相同输出 ──
    lin_a, sx_a, sy_a, c_a = _run_case("RelA/Epoch1", "RelB/Epoch1")
    lin_b, sx_b, sy_b, c_b = _run_case("RelA/Epoch1", "RelB/Epoch2")
    print(f"\n[case A] lineage={lin_a} pulses X={sx_a} Y={sy_a}")
    print(f"[case B] lineage={lin_b} pulses X={sx_b} Y={sy_b}")
    assert sx_a == sx_b and sy_a == sy_b, "adapter pulses 应逐位相同"
    assert c_a == c_b, "c_ro trace 应逐位相同"
    fires = [t for t, c in enumerate(c_a) if c > 0.0]
    print(f"[结论] adapter pulses identical; c_ro identical (fires={fires})"
          "——不同 relation instance 谱系在 C1 物理路径上不可区分")

    print("\n" + "=" * 68)
    print("A9_RUNTIME_INSTANCE_LINEAGE = GAP")
    print("=" * 68)
    print("exit 0 语义：缺口已正确复现并登记；不是 A9 PASS。")
    print("本轮不实现 binder（P1-3）；未来修复方向 = 物理路径原样 + 独立"
          "lineage audit/binding sidecar（不得改变 spike/Θ/gate），待理论裁定。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
