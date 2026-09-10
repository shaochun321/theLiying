"""exp_A8_new_03_block_future.py — EXP-A8-NEW-03 候选阻断 / 未来探测 + 三重证伪。

TYPE:INFRA（research/ 隔离层）

## 第一部分：fail-fast 证伪（先于任何 A8 声明）

EXP-01 报出的任何 twin effect 必须先通过下列三门证伪，否则按 §13 判定：

  F-4 输入量证伪：双胞胎收到**完全相同的输入多集合**（仅时序不同）时，
      差分是否消失？消失 ⟹ 差分来自输入量而非内部状态 ⟹ 命中 FAIL-4。
  F-6 初值证伪：完全相同输入序列下，不同初始状态是否收敛到同一点？
      收敛 ⟹ 初始条件被形成期抹掉 ⟹ 状态 = 输入历史的确定性函数。
  F-7 确定性证伪：同输入同初值是否逐位相同（差=0）？
      是 ⟹ 任何确定性重构器（已知初值+完整输入）必然复现 ⟹ 不可约不成立。

## 第二部分：K-07 未来可达作用（§8 原方案）

  baseline       : formation → Z → future_probe
  candidate block: formation → 物理阻断 Z → future_probe
  parent-only    : 相同 parent 历史 → 不允许 Z 建立 → future_probe
  要求 Future_Z ≠ Future_blocked 且 Future_Z ≠ Future_parent-only。
  ★ 但仅当第一部分三门证伪全部通过，K-07 才有意义（§8："只有
    A8_CANDIDATE 才能进入 K-07"）。本脚本同样执行这层守卫。

入口：PYTHONIOENCODING=utf-8 python research/A8_candidate/exp_A8_new_03_block_future.py
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from research.A8_candidate.candidate_z import ZMemristive

DT = 0.001
PROBE = 0.17
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def _run(z, seq, nwash=20000, nprobe=4000, probe=PROBE):
    for r in seq:
        z.step(r, 0.0, DT)
    for _ in range(nwash):
        z.step(0.0, 0.0, DT)
    return [z.step(probe, 0.0, DT) for _ in range(nprobe)]


def _maxdiff(a, b):
    n = min(len(a), len(b))
    return max((abs(a[i] - b[i]) for i in range(n)), default=0.0)


# ─────────────────────────────────────────────────────────────────────
# 第一部分：三重证伪
# ─────────────────────────────────────────────────────────────────────

def falsify_order_independence() -> dict:
    """F-4：相同输入多集合、仅时序不同 → 差分是否消失。"""
    seq_hi_first = [0.5] * 500 + [0.0] * 2500
    seq_lo_first = [0.0] * 2500 + [0.5] * 500
    za, zb = ZMemristive(), ZMemristive()
    A = _run(za, seq_hi_first)
    B = _run(zb, seq_lo_first)
    return {"w_A": za.weight, "w_B": zb.weight,
            "dw": abs(za.weight - zb.weight),
            "probe_maxdiff": _maxdiff(A, B),
            "passed": _maxdiff(A, B) < 1e-9}


def falsify_initial_condition() -> dict:
    """F-6：相同输入序列、不同初始 w → 是否收敛到同一点。"""
    seq = [0.5] * 500 + [0.0] * 2500
    wf = {}
    for w0 in (0.2, 0.5, 0.8):
        z = ZMemristive()
        z._mem = type(z._mem)(w=w0)
        for r in seq:
            z.step(r, 0.0, DT)
        wf[w0] = z.weight
    spread = max(wf.values()) - min(wf.values())
    return {"w_final": wf, "spread": spread,
            "passed": spread < 1e-9,
            "note": "收敛(散度≈0) ⟹ 形成期抹掉初始条件 ⟹ 状态=输入历史的函数"}


def falsify_determinism() -> dict:
    """F-7：同输入同初值是否逐位相同。"""
    seq = [0.5] * 500 + [0.0] * 2500
    za, zb = ZMemristive(), ZMemristive()
    for r in seq:
        za.step(r, 0.0, DT)
        zb.step(r, 0.0, DT)
    d = abs(za.weight - zb.weight)
    return {"dw": d, "passed": d == 0.0,
            "note": "逐位相同 ⟹ 确定性 ⟹ 已知初值+完整输入的重构器必然复现"}


# ─────────────────────────────────────────────────────────────────────
# 第二部分：K-07（仅在 A8_CANDIDATE 时执行）
# ─────────────────────────────────────────────────────────────────────

def k07_probe() -> dict:
    """K-07 三组：baseline / candidate-blocked / parent-only。"""
    form = [0.5] * 500 + [0.0] * 2500

    # baseline：正常形成 Z
    base = _run(ZMemristive(), form)

    # candidate blocked：物理阻断——把 memristor 替换为短路（电导固定在后天值，
    # 不允许状态演化）。物理上对应"切断 memristor 的离子漂移路径"。
    z_blk = ZMemristive()
    for r in form:
        z_blk.step(r, 0.0, DT)
    w_after = z_blk.weight
    z_blk2 = ZMemristive()
    z_blk2._mem = type(z_blk2._mem)(w=w_after)
    # 阻断：每步强制恢复权重（切断状态演化路径）
    for r in form:
        z_blk2.step(r, 0.0, DT)
        z_blk2._mem.w = w_after
    blocked = _run(z_blk2, [0.0] * 3000)

    # parent-only：不允许 Z 建立（无 formation），只走父层历史
    parent_only = _run(ZMemristive(), [0.0] * 3000)

    return {
        "baseline": {"last": base[-1], "max": max(base)},
        "blocked": {"last": blocked[-1], "max": max(blocked)},
        "parent_only": {"last": parent_only[-1], "max": max(parent_only)},
        "diff_base_blocked": _maxdiff(base, blocked),
        "diff_base_parent": _maxdiff(base, parent_only),
    }


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 70)
    print("EXP-A8-NEW-03 候选阻断/未来探测 + 三重证伪（fail-fast）")
    print("=" * 70)

    print("\n[第一部分] 三重证伪（任一失败 ⟹ A8 不成立）")
    f4 = falsify_order_independence()
    f6 = falsify_initial_condition()
    f7 = falsify_determinism()

    print(f"\n  F-4 输入量证伪（相同多集合、仅时序不同）")
    print(f"      w_A={f4['w_A']:.6f}  w_B={f4['w_B']:.6f}  Δw={f4['dw']:.3e}")
    print(f"      probe maxdiff={f4['probe_maxdiff']:.3e}  → "
          f"{'差分消失：命中 FAIL-4' if f4['passed'] else '差分保留'}")

    print(f"\n  F-6 初值证伪（相同输入、不同初始 w）")
    for w0, wf in f6["w_final"].items():
        print(f"      w0={w0} → w_final={wf:.6f}")
    print(f"      散度={f6['spread']:.3e} → "
          f"{'收敛：命中 FAIL-6' if f6['passed'] else '保留初值依赖'}")

    print(f"\n  F-7 确定性证伪（同输入同初值）")
    print(f"      最终 w 差={f7['dw']:.3e} → "
          f"{'逐位相同：确定性成立' if f7['passed'] else '非确定性'}")

    all_passed = f4["passed"] and f6["passed"] and f7["passed"]
    a8_viable = not all_passed      # 三门全过 ⟹ 证伪成功 ⟹ A8 不成立
    print(f"\n  综合：三门证伪 {'全部通过' if all_passed else '未全过'}"
          f" ⟹ A8 {'不成立（候选被证伪）' if all_passed else '仍待议'}")

    out = {"falsify_order": f4, "falsify_init": f6, "falsify_det": f7,
           "a8_viable": a8_viable}

    print("\n[第二部分] K-07 未来可达作用")
    if not a8_viable:
        print("  ⏹ 守卫触发：§8 规定只有 A8_CANDIDATE 才能进入 K-07。")
        print("     三门证伪已通过 ⟹ 候选不是 A8_CANDIDATE ⟹ K-07 = NOT_APPLICABLE。")
        out["k07"] = {"status": "NOT_APPLICABLE",
                      "reason": "A8 未成立，K-07 前置条件不满足"}
    else:
        k = k07_probe()
        print(f"  baseline      last={k['baseline']['last']:.6e}")
        print(f"  blocked       last={k['blocked']['last']:.6e}")
        print(f"  parent-only   last={k['parent_only']['last']:.6e}")
        print(f"  Δ(base,blocked) = {k['diff_base_blocked']:.3e}")
        print(f"  Δ(base,parent)  = {k['diff_base_parent']:.3e}")
        out["k07"] = k

    with open(os.path.join(DATA_DIR, "exp03_falsify.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n数据落盘: {os.path.join(DATA_DIR, 'exp03_falsify.json')}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
