"""exp_A8_new_01_twins.py — EXP-A8-NEW-01 历史匹配双胞胎实验（含 §B/§C）。

TYPE:INFRA（research/ 隔离层）

方案：cell-cell/claudecode方案/A8-A9-K-06时间方向组织候选_执行方案修订_2026-09-10.md
      §5（原方案）+ §B（ε_H 标定）+ §C（control-null 三组基线）

## 实验分组（每组 2 个 twin A/B）

  formation  : A 驱动 r1 通道 / B 驱动 r2 通道（不同 formation history）
  washout    : 双方 r=0，等 T_w —— §B：T_w 由物理上界反推，并扫 δ 敏感度
  probe      : 双方喂**完全相同**的 r(t)，比较读出

  C-null-1  同输入双胞胎：A、B formation 相同 → σ_null 噪声地板
  C-null-2  无形成双胞胎：A、B 直接进 washout
  C-null-3  可重构性标定：伪候选 = ZLinearRC（已知 ∈ 𝒜⁺）→ 必须 R ≈ 0

## ε_H 标定（§B）

  h(T_w) = h_max · e^{−T_w/τ_h}，h_max = 1.155（history_kernel.py:38）
  S = |∂Z/∂H_τ|（有限差分实测）
  ε_H 取使 S·h(T_w) ≤ δ·σ_null，δ = 0.1
  ⇒ T_w = τ_h · ln(S·h_max / (δ·σ_null))

  报告同时给 δ = 0.1 / 0.01 两档（§B 要求敏感度曲线）。

入口：PYTHONIOENCODING=utf-8 python -m research.A8_candidate.exp_A8_new_01_twins
      或 python research/A8_candidate/exp_A8_new_01_twins.py
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
TAU_H = 600.0          # history_kernel _DEFAULT_R_LEAK × C = 600 步
H_MAX = 1.155          # history_kernel.py:38 几何级数上界

FORM_STEPS = 3000      # formation 期
PROBE_STEPS = 4000     # probe 期
DRIVE = 0.17           # EXP-C0-02 实测域内的 relation current
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


# ─────────────────────────────────────────────────────────────────────
# 通用运行器
# ─────────────────────────────────────────────────────────────────────

def _run(z, r1_seq, r2_seq, dt=DT):
    """把 (r1, r2) 序列喂给候选，返回每步读出。"""
    out = []
    for r1, r2 in zip(r1_seq, r2_seq):
        out.append(z.step(r1, r2, dt))
    return out


def _seq(steps, **channels):
    """构造 (r1, r2) 序列。channels: r1=[(start, stop, amp)], ..."""
    r1 = [0.0] * steps
    r2 = [0.0] * steps
    for (a, b, amp) in channels.get("r1", []):
        for t in range(a, min(b, steps)):
            r1[t] = amp
    for (a, b, amp) in channels.get("r2", []):
        for t in range(a, min(b, steps)):
            r2[t] = amp
    return r1, r2


def twin_experiment(cls, formation_side: int, washout: int,
                    probe_seq: tuple, dt=DT):
    """单个 twin 对：formation（A 驱动 1 侧 / B 驱动 2 侧）→ washout → probe。"""
    results = {}
    for tag, side in (("A", 1), ("B", 2)):
        z = cls()
        if formation_side == 0:                       # 无形成（C-null-2）
            pass
        elif formation_side == 1:                     # 不同 formation（主实验）
            fseq = _seq(FORM_STEPS,
                        r1=[(0, FORM_STEPS, DRIVE)] if side == 1 else [],
                        r2=[(0, FORM_STEPS, DRIVE)] if side == 2 else [])
            _run(z, *fseq, dt=dt)
        elif formation_side == 2:                     # 相同 formation（C-null-1）
            fseq = _seq(FORM_STEPS, r1=[(0, FORM_STEPS, DRIVE)])
            _run(z, *fseq, dt=dt)

        for _ in range(washout):                      # washout
            z.step(0.0, 0.0, dt)

        probe_out = _run(z, *probe_seq, dt=dt)
        results[tag] = {
            "out": probe_out,
            "final": probe_out[-1] if probe_out else 0.0,
            "post_washout": z.state if hasattr(z, "state") else None,
        }
    return results


def _effect(res):
    a, b = res["A"]["out"], res["B"]["out"]
    n = min(len(a), len(b))
    d = [a[i] - b[i] for i in range(n)]
    l2 = math.sqrt(sum(x * x for x in d))
    scale = max(math.sqrt(sum(x * x for x in a[:n])),
                math.sqrt(sum(x * x for x in b[:n])), 1e-15)
    return l2, l2 / scale, max((abs(x) for x in d), default=0.0)


def _reconstruct_pair(res, probe_seq, dt=DT):
    """把 A、B 的 probe 段读出各自做 𝒜⁺ 最优拟合，返回残差对比。"""
    r_series = list(probe_seq[0])          # probe 期的 r1 序列（重构器输入）
    out = {}
    for tag in ("A", "B"):
        z = res[tag]["out"]
        out[tag] = reconstruct(z, r_series, dt)
    return out


# ─────────────────────────────────────────────────────────────────────
# 各分组
# ─────────────────────────────────────────────────────────────────────

def run_C_null_1(probe_seq, washout, dt=DT):
    """C-null-1：相同 formation 的双胞胎（噪声地板 σ_null）。"""
    return twin_experiment(ZMemristive, 2, washout, probe_seq, dt)


def run_C_null_2(probe_seq, washout, dt=DT):
    """C-null-2：无 formation 的双胞胎。"""
    return twin_experiment(ZMemristive, 0, washout, probe_seq, dt)


def run_C_null_3(washout, dt=DT):
    """C-null-3：可重构性标定——伪候选 ZLinearRC（已知 ∈ 𝒜⁺）。"""
    probe = _seq(PROBE_STEPS, r1=[(0, PROBE_STEPS, DRIVE)])
    res = twin_experiment(ZLinearRC, 1, washout, probe, dt)
    rec = _reconstruct_pair(res, probe, dt)
    return res, rec


def run_main(cls, washout, dt=DT):
    """主实验：不同 formation（A 驱动 1 侧 / B 驱动 2 侧）→ washout → 相同 probe。"""
    probe = _seq(PROBE_STEPS, r1=[(0, PROBE_STEPS, DRIVE)])
    res = twin_experiment(cls, 1, washout, probe, dt)
    rec = _reconstruct_pair(res, probe, dt)
    return res, rec


def washout_sweep(cls, deltas=(0.1, 0.01), dt=DT):
    """§B：ε_H 标定与 washout 敏感度曲线。

    S = |∂Z/∂H_τ| 有限差分实测：在探测点把父层残余历史 H_τ 当作
    额外输入偏置，测候选读出的变化。
    """
    probe = _seq(PROBE_STEPS, r1=[(0, PROBE_STEPS, DRIVE)])

    # 1. 实测 S：在 probe 起点叠加微量 H_τ 型偏置，看读出差
    base = twin_experiment(cls, 1, 0, probe, dt)["A"]["out"]
    eps_h = 1e-3
    bias_seq = _seq(PROBE_STEPS, r1=[(0, PROBE_STEPS, DRIVE + eps_h / DT)])
    biased = twin_experiment(cls, 1, 0, bias_seq, dt)["A"]["out"]
    n = min(len(base), len(biased))
    dmax = max(abs(base[i] - biased[i]) for i in range(n)) if n else 0.0
    S = dmax / eps_h if eps_h > 0 else 0.0

    # 2. 由物理上界反推 T_w（§B 公式）
    rows = []
    for delta in deltas:
        sigma_ref = 1e-6                        # 零效应参考尺度（保守下限）
        arg = max(S * H_MAX / max(delta * sigma_ref, 1e-300), 1e-300)
        if S > 0.0:
            tw = TAU_H * math.log(arg)
            tw_steps = int(max(tw / DT, 0))
        else:
            tw_steps = 0
        rows.append({"delta": delta, "S": S, "T_w_steps": tw_steps,
                     "h_residual": H_MAX * math.exp(-tw_steps * DT / TAU_H)})
    return {"S": S, "rows": rows}


# ─────────────────────────────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────────────────────────────

def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 70)
    print("EXP-A8-NEW-01 历史匹配双胞胎（含 §B  washout 标定 / §C 三组基线）")
    print("=" * 70)

    washout = 20000
    probe = _seq(PROBE_STEPS, r1=[(0, PROBE_STEPS, DRIVE)])
    report = {}

    # ── §C 三组基线 ──
    res1 = run_C_null_1(probe, washout)
    l2_1, rel_1, mx_1 = _effect(res1)
    print(f"\n[C-null-1] 相同 formation：effect L2={l2_1:.6e} rel={rel_1:.3e} max={mx_1:.3e}")

    res2 = run_C_null_2(probe, washout)
    l2_2, rel_2, mx_2 = _effect(res2)
    print(f"[C-null-2] 无 formation  ：effect L2={l2_2:.6e} rel={rel_2:.3e} max={mx_2:.3e}")

    res3, rec3 = run_C_null_3(washout)
    l2_3, rel_3, mx_3 = _effect(res3)
    print(f"[C-null-3] 线性控制件   ：effect L2={l2_3:.6e} rel={rel_3:.3e} max={mx_3:.3e}")
    print(f"           𝒜⁺ 重构残差 = {rec3['A']['rel']:.3e} (A) / "
          f"{rec3['B']['rel']:.3e} (B)  ← 必须 ≈ 0")

    sigma_null = max(rel_1, rel_2, 1e-15)
    floor = max(rec3["A"]["rel"], rec3["B"]["rel"], 1e-15)
    print(f"\n  σ_null（噪声地板）= {sigma_null:.3e}")
    print(f"  重构器地板（C-null-3）= {floor:.3e}")

    # ── §B washout 标定 ──
    print("\n" + "-" * 70)
    print("[§B] ε_H 标定与 washout 敏感度")
    sw = washout_sweep(ZMemristive)
    print(f"  S = |∂Z/∂H_τ| = {sw['S']:.6e}")
    for row in sw["rows"]:
        print(f"  δ={row['delta']:<5} → T_w≈{row['T_w_steps']} 步 "
              f"(h_residual={row['h_residual']:.3e})")

    # ── 主实验：三个候选 ──
    print("\n" + "-" * 70)
    print("[主实验] 不同 formation → washout=20000 → 相同 probe")
    candidates = {
        "C0-ZLinearRC": ZLinearRC,
        "C0-ZSaturating": ZSaturating,
        "C1-ZMemristive": ZMemristive,
    }
    for name, cls in candidates.items():
        res, rec = run_main(cls, washout)
        l2, rel, mx = _effect(res)
        ra = rec["A"]["rel"]
        rb = rec["B"]["rel"]
        verdict = "A8_CANDIDATE" if (rel > max(3 * sigma_null, 10 * floor)
                                     and rel > 1e-9) else "reconstructible"
        print(f"\n  {name}")
        print(f"    twin effect : L2={l2:.6e}  rel={rel:.3e}  max={mx:.3e}")
        print(f"    重构残差    : A={ra:.3e}  B={rb:.3e}")
        print(f"    判定        : {verdict}")
        report[name] = {"effect_rel": rel, "effect_l2": l2, "effect_max": mx,
                        "recon_A": ra, "recon_B": rb, "verdict": verdict}

    out = {
        "sigma_null": sigma_null, "recon_floor": floor,
        "cn1": {"l2": l2_1, "rel": rel_1, "max": mx_1},
        "cn2": {"l2": l2_2, "rel": rel_2, "max": mx_2},
        "cn3": {"l2": l2_3, "rel": rel_3, "max": mx_3,
                "recon_A": rec3["A"]["rel"], "recon_B": rec3["B"]["rel"]},
        "washout_sweep": sw,
        "candidates": report,
    }
    with open(os.path.join(DATA_DIR, "exp01_twins.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"数据落盘: {os.path.join(DATA_DIR, 'exp01_twins.json')}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
