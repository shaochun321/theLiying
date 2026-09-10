"""exp_A8_new_02_reconstruct.py — EXP-A8-NEW-02 父层同类重构攻击（§E）。

TYPE:INFRA（research/ 隔离层）

## 协议（方案修订稿 §A.2 / §6 原方案）

对每个候选，用**完整 r(t)**（不是二值事件）做 𝒜⁺ 最优拟合，报告：
    R_Z(t) = Z_actual(t) − Ẑ(t)
    residual / rel / abs_max / scale

判定（§E）：
    若 ‖R_Z‖ ≤ max(20·floor_null, 1e-12) 或 δ=0.01 washout 下消失
    → 父层同类算子可重构，候选淘汰。

floor_null = C-null-3 上（已知 ∈ 𝒜⁺ 的线性控制件）的重构残差，
             即重构器自身的浮点地板。

## 与 EXP-01 的分工

EXP-01 用**行为差分**（twin effect）判断"状态是否有可见作用"；
EXP-02 用**拟合残差**判断"状态是否超出 𝒜⁺ 的表达能力"。
两者都通过才允许进入 A8_CANDIDATE（§A.2 + §E）。

入口：PYTHONIOENCODING=utf-8 python research/A8_candidate/exp_A8_new_02_reconstruct.py
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from research.A8_candidate.candidate_z import (
    ZLinearRC, ZSaturating, ZMemristive)
from research.A8_candidate.reconstructor import reconstruct

DT = 0.001
PROBE = 0.17
FORM_STEPS = 3000
WASHOUT = 20000
PROBE_STEPS = 4000
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# formation 驱动：区分"低支"与"高支"（memristor 分岔区）
FORM_DRIVE_LOW = 0.40
FORM_DRIVE_HIGH = 0.50


def _run(z, drive_form, nform=FORM_STEPS, nwash=WASHOUT,
         nprobe=PROBE_STEPS, probe=PROBE):
    for _ in range(nform):
        z.step(drive_form, 0.0, DT)
    for _ in range(nwash):
        z.step(0.0, 0.0, DT)
    return [z.step(probe, 0.0, DT) for _ in range(nprobe)]


def _probe_r(n=PROBE_STEPS, probe=PROBE):
    return [probe] * n


def attack(cls, tag, drive_form):
    z = cls()
    out = _run(z, drive_form)
    rec = reconstruct(out, _probe_r(), DT)
    return {
        "tag": tag,
        "drive_form": drive_form,
        "w_final": getattr(z, "weight", None),
        "residual": rec["residual"],
        "rel": rec["rel"],
        "abs_max": rec["abs_max"],
        "scale": rec["scale"],
    }


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 70)
    print("EXP-A8-NEW-02 父层同类重构攻击（𝒜⁺ 最优拟合，完整 r(t)）")
    print("=" * 70)

    # ── floor_null：C-null-3（已知 ∈ 𝒜⁺ 的线性控制件）──
    ctrl = attack(ZLinearRC, "ZLinearRC", FORM_DRIVE_HIGH)
    floor_null = ctrl["rel"]
    print(f"\n[floor] C-null-3（ZLinearRC，已知 ∈ 𝒜⁺）rel = {floor_null:.6e}")
    print(f"        绝对残差 {ctrl['residual']:.6e} / 尺度 {ctrl['scale']:.6e}")

    rows = [ctrl]
    print("\n候选重构残差（完整 r(t) 攻击）：")
    print(f"  {'候选':<18}{'rel':>14}{'abs_max':>14}{'w_final':>10}")
    for cls, tag, drive in (
        (ZSaturating, "ZSaturating/lo", FORM_DRIVE_LOW),
        (ZSaturating, "ZSaturating/hi", FORM_DRIVE_HIGH),
        (ZMemristive, "ZMemristive/lo", FORM_DRIVE_LOW),
        (ZMemristive, "ZMemristive/hi", FORM_DRIVE_HIGH),
    ):
        r = attack(cls, tag, drive)
        rows.append(r)
        wf = "—" if r["w_final"] is None else f"{r['w_final']:.4f}"
        print(f"  {tag:<18}{r['rel']:>14.3e}{r['abs_max']:>14.3e}{wf:>10}")

    # ── 判定（§E）──
    print("\n" + "-" * 70)
    print("[判定] §E：‖R_Z‖ ≤ max(20·floor, 1e-12) ⟹ 可重构，淘汰")
    thr = max(20.0 * floor_null, 1e-12)
    print(f"  阈值 = max(20×{floor_null:.3e}, 1e-12) = {thr:.3e}")
    verdicts = {}
    for r in rows[1:]:
        # 注意：ZMemristive 的 rel 大是因为其输出尺度极小（scale→0），
        # 需同时看绝对残差与尺度，避免"除以零"造成的伪判定。
        reconstructible = (r["residual"] <= thr) or (r["scale"] < 1e-12)
        verdict = "reconstructible" if reconstructible else "A8_CANDIDATE?"
        verdicts[r["tag"]] = verdict
        note = "  (scale≈0：输出恒零，残差无判别意义)" if r["scale"] < 1e-12 else ""
        print(f"  {r['tag']:<18}{verdict}{note}")

    out = {
        "floor_null_rel": floor_null,
        "floor_null_abs": ctrl["residual"],
        "threshold": thr,
        "rows": rows,
        "verdicts": verdicts,
    }
    with open(os.path.join(DATA_DIR, "exp02_reconstruct.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n数据落盘: {os.path.join(DATA_DIR, 'exp02_reconstruct.json')}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
