"""wt0_positive_control.py — 冻结 WORLD_HIDDEN_DYNAMICS_POSITIVE_CONTROL。

TYPE:INFRA（research/ 观测层，只读消费 nexus_v1 三点皮肤；零母体改动）

依据：外部《WT0 方案》§4 + 评判裁定（R-3：Y_B 必须显式定义）+ 评判附录一
补全协议（外部文档缺 t_drive/t0/幅值/边界定义，本脚本为完整冻结版）。

## 冻结协议（先于实验写死）

  场:        build_three_point_skin(TEST 档 κ=0.05, r_leak_ambient=200), dt=1.0
  history A: node0 恒流 I=1.0,   t∈[0,100)
  history B: node2 恒流 I=1.996, t∈[0,100)
  t0 = 99（0 起步计数，驱动末步）
  边界:      Y_B = node0 温度 —— **reduced-boundary 配置**（显式声明：
             非现行 P2-A 三节点全转导接线；三节点全可见配置下 World v1
             无隐藏态，本正对照不成立——R-3 裁定的分水岭）
  撤驱动:    t≥100 外部输入恒 0，自由演化 1000 步

## 断言门（三门全过 = 正对照成立）

  G1 t0 边界不可区分:   |q_A0(t0) − q_B0(t0)| < 0.001
  G2 t0 隐藏态可区分:   max_i |q_Ai(t0) − q_Bi(t0)| > 20   (i∈{1,2})
  G3 未来边界分叉:      max_{t>t0} |q_A0(t) − q_B0(t)| > 10 （外部/评判实测 ≈18.68）

证明命题（§4 原文）：即使完整 World 是确定动力系统，有限边界观测也可以
表现出历史依赖。**该现象属 World 层，不得改造为 TSS 的 H_τ**（§4 禁令）。

输出：data/wt0_positive_control.json
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..')))

from nexus_v1.components.skin_three_point import (  # noqa: E402
    TEST_KAPPA_THREE_POINT, TEST_R_LEAK_AMBIENT_THREE_POINT,
    build_three_point_skin)

DATA_DIR = os.path.join(_HERE, 'data')
T_DRIVE = 100
T0 = 99
T_FREE = 1000
AMP_A, NODE_A = 1.0, 0
AMP_B, NODE_B = 1.996, 2
BOUNDARY_NODE = 0  # Y_B = node0（reduced-boundary 配置，见 docstring）


def run(node: int, amp: float):
    g = build_three_point_skin(kappa=TEST_KAPPA_THREE_POINT,
                               r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)
    traj = []
    for t in range(T_DRIVE + T_FREE):
        g.step(1.0, {node: amp} if t < T_DRIVE else {})
        traj.append([g.cells[i].temperature for i in range(3)])
    return traj


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 68)
    print("WT0 §4 — WORLD_HIDDEN_DYNAMICS_POSITIVE_CONTROL（冻结协议版）")
    print("=" * 68)
    A, B = run(NODE_A, AMP_A), run(NODE_B, AMP_B)
    d_boundary_t0 = abs(A[T0][BOUNDARY_NODE] - B[T0][BOUNDARY_NODE])
    d_hidden_t0 = max(abs(A[T0][i] - B[T0][i]) for i in (1, 2))
    div_future = max(abs(a[BOUNDARY_NODE] - b[BOUNDARY_NODE])
                     for a, b in zip(A[T_DRIVE:], B[T_DRIVE:]))
    g1, g2, g3 = d_boundary_t0 < 0.001, d_hidden_t0 > 20, div_future > 10
    print(f"t0={T0}: boundary A={A[T0][0]:.5f} B={B[T0][0]:.5f} "
          f"|Δ|={d_boundary_t0:.2e}  [G1 {'PASS' if g1 else 'FAIL'}]")
    print(f"hidden A={['%.4f' % x for x in A[T0]]}")
    print(f"hidden B={['%.4f' % x for x in B[T0]]}  "
          f"max|Δ_hidden|={d_hidden_t0:.4f}  [G2 {'PASS' if g2 else 'FAIL'}]")
    print(f"撤驱动后 max|qA0−qB0|={div_future:.4f}  "
          f"[G3 {'PASS' if g3 else 'FAIL'}]（外部基准 ≈18.68）")
    verdict = "ESTABLISHED" if (g1 and g2 and g3) else "NOT_ESTABLISHED"
    print(f"\nWORLD_HIDDEN_DYNAMICS_POSITIVE_CONTROL = {verdict}")
    out = {
        "protocol": {"t_drive": T_DRIVE, "t0": T0, "t_free": T_FREE,
                     "amp_A": AMP_A, "node_A": NODE_A,
                     "amp_B": AMP_B, "node_B": NODE_B,
                     "boundary": f"node{BOUNDARY_NODE} (reduced-boundary)",
                     "kappa": TEST_KAPPA_THREE_POINT,
                     "r_leak_ambient": TEST_R_LEAK_AMBIENT_THREE_POINT},
        "boundary_t0": [A[T0][0], B[T0][0]],
        "hidden_t0": {"A": A[T0], "B": B[T0]},
        "d_boundary_t0": d_boundary_t0, "d_hidden_t0": d_hidden_t0,
        "max_future_divergence": div_future,
        "gates": {"G1": g1, "G2": g2, "G3": g3}, "verdict": verdict,
    }
    path = os.path.join(DATA_DIR, "wt0_positive_control.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"落盘: {path}")
    return 0 if (g1 and g2 and g3) else 1


if __name__ == "__main__":
    sys.exit(main())
