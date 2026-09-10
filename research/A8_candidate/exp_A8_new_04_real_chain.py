"""exp_A8_new_04_real_chain.py — 真实父层链路双胞胎（最强 A8 检验）。

TYPE:INFRA（research/ 隔离层）

## 为什么需要这一项

EXP-01/02/03 用的是**手工馈入的 r(t)**。本项改用**真实 C1 链路**
（AddressRegistry → RelationEventAdapter → PhysicalEntryGate →
PhysicalHistoryKernel → PhysicalThetaComparator），即父层算子 𝒜 的
真实实例，检验：

    在两个 twin 的父层可观测状态被 washout 对齐之后，
    候选 Z 能否凭内部状态在相同 probe 下给出不同输出？

## 与 T-C1-6b 的关系

T-C1-6b（EXT-2，已冻结）证明的是：**c_ro 可被父层同型栈 bit-exact 重构**
（残差 0.0）⇒ A8 NOT_MET。
本项在同一真实链路上追加候选 Z，检验"追加候选后 A8 是否仍 NOT_MET"。
若候选只是父层状态的函数，结论必然与 6b 一致（A8 仍 NOT_MET）。

## 输入通道（诚实声明）

真实链路的 relation current 由 PhysicalThetaComparator 产生；
本项把该比较器的输出**同时**喂给父层栈（保持 6b 语义）与候选 Z，
从而使候选与父层**共享完全相同的 r(t)**——这是最强攻击。

入口：PYTHONIOENCODING=utf-8 python research/A8_candidate/exp_A8_new_04_real_chain.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from research.A8_candidate.candidate_z import ZMemristive
from tss.tests.test_c1_coupling import _synthetic_stack, DT
from research.A8_candidate.reconstructor import reconstruct

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

FORM_DRIVE = 0.17
WASHOUT = 20000
PROBE_STEPS = 4000


def _drive_pair(form_on_x: bool, nform: int = 3000):
    """真实链路 + 候选：formation 期 A 驱动 X 通道 / B 驱动 Y 通道。

    返回 (candidate, parent_trace, candidate_trace)。
    """
    ad_x, ad_y, st = _synthetic_stack()
    z = ZMemristive()
    parent_trace, cand_trace = [], []

    for t in range(nform):
        rx = FORM_DRIVE if form_on_x else 0.0
        ry = 0.0 if form_on_x else FORM_DRIVE
        ad_x.step(rx, DT)
        ad_y.step(ry, DT)
        c = st.step(t, DT)
        parent_trace.append(c)
        # 候选消费同一个 r（此处用父层实际输出的关系电流）
        cand_trace.append(z.step(c, 0.0, DT))
    return z, ad_x, ad_y, st, parent_trace, cand_trace


def _probe(z, ad_x, ad_y, st, t_offset, nprobe=PROBE_STEPS):
    """probe：父层与候选都喂**完全相同**的输入序列。"""
    parent, cand = [], []
    for k in range(nprobe):
        ad_x.step(FORM_DRIVE, DT)
        ad_y.step(FORM_DRIVE, DT)
        c = st.step(t_offset + k, DT)
        parent.append(c)
        cand.append(z.step(c, 0.0, DT))
    return parent, cand


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 70)
    print("EXP-A8-NEW-04 真实父层链路双胞胎（𝒜 的真实实例）")
    print("=" * 70)

    # ── twin A：formation 驱动 X 通道 ──
    zA, axA, ayA, stA, pA, cA = _drive_pair(True)
    for _ in range(WASHOUT):                      # washout
        zA.step(0.0, 0.0, DT)
    wA = zA.weight
    pA_probe, cA_probe = _probe(zA, axA, ayA, stA, 3000)

    # ── twin B：formation 驱动 Y 通道 ──
    zB, axB, ayB, stB, pB, cB = _drive_pair(False)
    for _ in range(WASHOUT):
        zB.step(0.0, 0.0, DT)
    wB = zB.weight
    pB_probe, cB_probe = _probe(zB, axB, ayB, stB, 3000)

    print(f"\n  formation: A=X通道  B=Y通道")
    print(f"  washout 后候选权重: w_A={wA:.6f}  w_B={wB:.6f}  Δw={abs(wA-wB):.3e}")

    # ── 父层可观测状态是否已对齐（§5 washout 要求）──
    p_diff = max((abs(a - b) for a, b in zip(pA_probe, pB_probe)), default=0.0)
    print(f"  probe 期父层输出差分   = {p_diff:.3e}  （应≈0：父层状态已对齐）")

    # ── 候选输出差分 ──
    c_diff = max((abs(a - b) for a, b in zip(cA_probe, cB_probe)), default=0.0)
    c_l2 = sum((a - b) ** 2 for a, b in zip(cA_probe, cB_probe)) ** 0.5
    print(f"  probe 期候选输出差分   = {c_diff:.3e} (L2={c_l2:.3e})")

    # ── 重构攻击：完整 r(t) 拟合候选 ──
    r_series = [FORM_DRIVE] * PROBE_STEPS
    recA = reconstruct(cA_probe, r_series, DT)
    recB = reconstruct(cB_probe, r_series, DT)
    print(f"  候选重构残差           = A {recA['rel']:.3e} / B {recB['rel']:.3e}")

    # ── 判定（§A.2 + §E）──
    print("\n" + "-" * 70)
    if p_diff > 1e-9:
        verdict = "INVALID: 父层状态未对齐，washout 不足"
    elif c_diff <= 1e-9:
        verdict = "A8 仍 NOT_MET（候选未产生可分辨差分）"
    else:
        verdict = "A8_CANDIDATE?（需跨 seed 复核）"
    print(f"  判定: {verdict}")

    out = {"w_A": wA, "w_B": wB, "dw": abs(wA - wB),
           "parent_probe_diff": p_diff,
           "cand_probe_diff": c_diff, "cand_l2": c_l2,
           "recon_A": recA["rel"], "recon_B": recB["rel"],
           "verdict": verdict}
    with open(os.path.join(DATA_DIR, "exp04_real_chain.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n数据落盘: {os.path.join(DATA_DIR, 'exp04_real_chain.json')}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
