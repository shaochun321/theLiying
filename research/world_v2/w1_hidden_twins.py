"""w1_hidden_twins.py — W1 隐藏动力学孪生对（M6 核心门 + §26/§27/§28/§41）。

TYPE:INFRA（research/ 层，production 零改动）

## 预登记阈值（§26 纪律：写死后不得改；依据=W1 方案评判 B2，
## 数值尺度取自 World v1 正对照实测 ~1e-5/~1.5/~0.5）

  ε_B: ‖Y_A(t0)−Y_B(t0)‖/RMS(Y) < 1e-2     （t0 边界不可区分）
  ε_X: ‖X_A(t0)−X_B(t0)‖/RMS(X) > 0.2      （t0 完整态可区分；X_W 含
                                              场节点+源剩余能量，§2 定义）
  ε_F: max_{τ>0}‖Y_A−Y_B‖/RMS(Y) > 5e-2    （未来边界分叉）

## Twin-1 Field-hidden（§26 一般化版）
  N=10 链（均匀 κ=0.05, r_leak=200），Y_B=node0（REDUCED）。
  Γ_A: node0@1.0×100 步；Γ_B: node9@s×100 步，s 由线性叠加原理反解使
  Y_B(t0=99) 相等（v1 正对照同法，场线性 T0 已证 dev~1e-16）。
  隐藏态=远端节点温度分布。撤驱动自由演化 1500 步测分叉。

## Twin-2 Source-hidden（§27）
  同一驱动历史（node0@P=1.0, t∈[0,100)），源剩余能量不同：
  E_A=900（t0 后还能烧 800 步）vs E_B=100（t0 恰好耗尽）。
  t0=99 时场态逐位相同、边界逐位相同；X_W 差全在 E_source。
  证明隐藏动力学可来自环境对象未来因果状态（非场节点）。

## 因果阻断（§28）
  Twin-2: intact(A) vs causal-block(A@t0 置 energy_remaining=0)。
  若阻断后未来边界差消失（A_blocked ≡ B 逐位）⇒
  HIDDEN_STATE_CAUSALLY_SUPPORTED。
  Twin-1: 干预=t0 把 B 的全场态覆写为 A 的全场态（研究层状态手术，
  合法因果干预）⇒ 未来应逐位重合 ⇒ 场隐藏态因果支撑成立。

## Full vs Reduced 对照（§41/NC4/NC5）
  Twin-1 在 BOUNDARY_FULL 下 t0 即可区分（ΔX 可见）⇒
  "same-current/different-future" 只在 REDUCED 出现 ⇒ 隐藏动力学
  确系有限观察产物而非算法黑箱。

输出：data/hidden_twin_pairs.csv, data/w1_hidden_twins.json
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from world_v2_core import (  # noqa: E402
    SourceSpec, WorldEpisode, WorldEpisodeSpec)

DATA_DIR = os.path.join(_HERE, 'data')
EPS_B, EPS_X, EPS_F = 1e-2, 0.2, 5e-2
N = 10
T_DRIVE, T0, T_FREE = 100, 99, 1500


def spec(sources, boundary=("REDUCED", (0,)), t_total=T_DRIVE + T_FREE,
         eid="twin"):
    return WorldEpisodeSpec(
        episode_id=eid, seed=-1, n_nodes=N,
        kappas=tuple([0.05] * (N - 1)), r_leak_ambient=200.0,
        sources=tuple(sources), boundary_config=boundary[0],
        boundary_nodes=boundary[1], t_total=t_total)


def run_ep(sp, surgery=None):
    """跑完整 episode；surgery=(t, fn(ep)) 在步 t 之后施加干预。返回
    (boundary_traj, full_traj, src_energy_traj)。"""
    ep = WorldEpisode(sp)
    b_traj, f_traj, e_traj = [], [], []
    for t in range(sp.t_total):
        ep.step()
        if surgery and t == surgery[0]:
            surgery[1](ep)
        b_traj.append(ep.boundary_frame())
        f_traj.append(ep.full_state())
        e_traj.append(sum(s.energy_remaining for s in ep.sources))
    return b_traj, f_traj, e_traj


def rel(vec_a, vec_b, ref_rms):
    d = math.sqrt(sum((a - b) ** 2 for a, b in zip(vec_a, vec_b))
                  / len(vec_a))
    return d / max(ref_rms, 1e-30)


def rms_traj(traj):
    return math.sqrt(sum(v * v for row in traj for v in row)
                     / (len(traj) * len(traj[0])))


def eval_twin(name, bA, fA, eA, bB, fB, eB):
    rms_y = max(rms_traj(bA), rms_traj(bB))
    rms_x = max(rms_traj(fA), rms_traj(fB))
    d_b_t0 = rel(bA[T0], bB[T0], rms_y)
    # X_W 含场节点 + 源剩余能量（§2）
    xA = list(fA[T0]) + [eA[T0]]
    xB = list(fB[T0]) + [eB[T0]]
    rms_x_ext = max(rms_x, abs(eA[T0]), abs(eB[T0]), 1e-30)
    d_x_t0 = math.sqrt(sum((a - b) ** 2 for a, b in zip(xA, xB))
                       / len(xA)) / rms_x_ext
    d_f = max(rel(a, b, rms_y) for a, b in zip(bA[T_DRIVE:], bB[T_DRIVE:]))
    g1, g2, g3 = d_b_t0 < EPS_B, d_x_t0 > EPS_X, d_f > EPS_F
    ok = g1 and g2 and g3
    print(f"[{name}] ΔY(t0)/RMS={d_b_t0:.2e} [{'PASS' if g1 else 'FAIL'}]  "
          f"ΔX(t0)/RMS={d_x_t0:.3f} [{'PASS' if g2 else 'FAIL'}]  "
          f"maxΔY⁺/RMS={d_f:.3f} [{'PASS' if g3 else 'FAIL'}]  "
          f"⇒ {'ESTABLISHED' if ok else 'NOT_ESTABLISHED'}")
    return {"d_boundary_t0": d_b_t0, "d_x_t0": d_x_t0,
            "d_future_max": d_f, "gates": [g1, g2, g3], "pass": ok}


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 78)
    print("W1 隐藏孪生 — M6（Twin-1 场隐藏 / Twin-2 源隐藏 / 因果阻断 / "
          "Full-vs-Reduced）")
    print("=" * 78)
    print(f"预登记阈值: eps_B<{EPS_B} eps_X>{EPS_X} eps_F>{EPS_F}")
    out = {"thresholds": {"eps_B": EPS_B, "eps_X": EPS_X, "eps_F": EPS_F}}
    rows = []

    # ── Twin-1 Field-hidden ─────────────────────────────────────────────
    bA, fA, eA = run_ep(spec([SourceSpec(0, 1e9, 1.0, 0)], eid="t1A",
                             t_total=T_DRIVE))
    b_unit, _, _ = run_ep(spec([SourceSpec(N - 1, 1e9, 1.0, 0)], eid="t1u",
                               t_total=T_DRIVE))
    s = bA[T0][0] / b_unit[T0][0]  # 线性反解幅值（v1 正对照同法）
    # 注意：t_total 内源恒燃会掩盖撤驱动——用 energy=P*T_DRIVE 精确燃 100 步
    src_a = SourceSpec(0, 1.0 * T_DRIVE, 1.0, 0)
    src_b = SourceSpec(N - 1, s * T_DRIVE, s, 0)
    bA, fA, eA = run_ep(spec([src_a], eid="t1A_full"))
    bB, fB, eB = run_ep(spec([src_b], eid="t1B_full"))
    out["twin1_field_hidden"] = eval_twin("Twin-1", bA, fA, eA, bB, fB, eB)
    out["twin1_scale_b"] = s
    rows.append({"twin": "T1_field", **out["twin1_field_hidden"]})

    # Twin-1 因果阻断：t0 把 B 全场态覆写为 A 场态（源已同为耗尽）
    fA_t0 = fA[T0]

    def surgery_copy_field(ep):
        for i in range(N):
            ep.graph.cells[i].capacitor.charge = fA_t0[i]

    bB_blk, _, _ = run_ep(spec([src_b], eid="t1B_blocked"),
                          surgery=(T0, surgery_copy_field))
    rms_y = max(rms_traj(bA), rms_traj(bB_blk))
    resid = max(rel(a, b, rms_y)
                for a, b in zip(bA[T_DRIVE:], bB_blk[T_DRIVE:]))
    t1_causal = resid < 1e-9
    print(f"[Twin-1 causal-block] 覆写场态后未来边界残差={resid:.2e} ⇒ "
          f"{'HIDDEN_STATE_CAUSALLY_SUPPORTED' if t1_causal else 'CORRELATIONAL_ONLY'}")
    out["twin1_causal_block"] = {"future_residual": resid,
                                 "causally_supported": t1_causal}

    # ── Twin-2 Source-hidden（§27）────────────────────────────────────
    bA2, fA2, eA2 = run_ep(spec([SourceSpec(0, 900.0, 1.0, 0)], eid="t2A"))
    bB2, fB2, eB2 = run_ep(spec([SourceSpec(0, 100.0, 1.0, 0)], eid="t2B"))
    field_same_t0 = fA2[T0] == fB2[T0]
    print(f"[Twin-2] t0 场态逐位相同={field_same_t0}  "
          f"E_src(t0): A={eA2[T0]:.1f} vs B={eB2[T0]:.1f}")
    out["twin2_source_hidden"] = eval_twin("Twin-2", bA2, fA2, eA2,
                                           bB2, fB2, eB2)
    out["twin2_field_identical_t0"] = field_same_t0
    rows.append({"twin": "T2_source", **out["twin2_source_hidden"]})

    # Twin-2 因果阻断：intact(A) vs A@t0 源置零
    def surgery_kill_source(ep):
        for src in ep.sources:
            src.energy_remaining = 0.0

    bA2_blk, _, _ = run_ep(spec([SourceSpec(0, 900.0, 1.0, 0)],
                                eid="t2A_blocked"),
                           surgery=(T0, surgery_kill_source))
    rms_y2 = max(rms_traj(bA2_blk), rms_traj(bB2))
    resid2 = max(rel(a, b, rms_y2)
                 for a, b in zip(bA2_blk[T_DRIVE:], bB2[T_DRIVE:]))
    t2_causal = resid2 < 1e-9
    print(f"[Twin-2 causal-block] 阻断源后 A_blocked≡B 残差={resid2:.2e} ⇒ "
          f"{'HIDDEN_STATE_CAUSALLY_SUPPORTED' if t2_causal else 'CORRELATIONAL_ONLY'}")
    out["twin2_causal_block"] = {"future_residual": resid2,
                                 "causally_supported": t2_causal}

    # ── Full vs Reduced（§41）────────────────────────────────────────
    bAf, _, _ = run_ep(spec([src_a], boundary=("FULL", tuple(range(N))),
                            eid="t1A_fullbnd"))
    bBf, _, _ = run_ep(spec([src_b], boundary=("FULL", tuple(range(N))),
                            eid="t1B_fullbnd"))
    rms_full = max(rms_traj(bAf), rms_traj(bBf))
    d_full_t0 = rel(bAf[T0], bBf[T0], rms_full)
    full_distinguishes = d_full_t0 > EPS_B
    print(f"[Full-vs-Reduced] FULL 边界 t0 差={d_full_t0:.3f}"
          f"（REDUCED 为 {out['twin1_field_hidden']['d_boundary_t0']:.2e}）"
          f" ⇒ 隐藏动力学{'确系有限观察产物' if full_distinguishes else '异常'}")
    out["full_vs_reduced"] = {"d_full_t0": d_full_t0,
                              "partial_observation_confirmed": full_distinguishes}

    m6 = (out["twin1_field_hidden"]["pass"]
          and out["twin2_source_hidden"]["pass"]
          and t1_causal and t2_causal and full_distinguishes)
    out["M6_pass"] = m6
    print(f"\nM6 隐藏因果动力学 ⇒ {'PASS' if m6 else 'FAIL'}")

    with open(os.path.join(DATA_DIR, "hidden_twin_pairs.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    path = os.path.join(DATA_DIR, "w1_hidden_twins.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"落盘: {path}")
    return 0 if m6 else 1


if __name__ == "__main__":
    sys.exit(main())
