"""t1b_common.py — T1-B 共享候选/度量/分类逻辑（被 t1b_* 脚本 import）。

TYPE:INFRA。候选定义与 canonical 参数以 `T1B_PORT_AND_TIMEBASE_CONTRACT.md`
为准（provenance 已在 held-out 锁定前预承诺，评判 C3）：

  legacy : clip[κ(q−q0)+b, 0, 0.04]                       （负控制）
  A U_T  : S·(q − Y_ref)          S=0.00137531 [u/T] CANONICAL_REFERENCE
                                  Y_ref=0 [T] PHYSICAL
  B U_Ṫ : g·(q_t − q_{t−Δt_ext})/Δt_ext                  （dt-aware，§10）
           g=0.275062 [u·s/T] CANONICAL_REFERENCE；Δt_ext=1 s PHYSICAL；
           状态初始化合同（C5）：prev=首样本 ⇒ u(0)=0，replay 逐位可复现。

逐 episode 状态分类（§36，先声明）：
  NUMERIC_FAIL   : 任一输出 NaN/inf 或 |u|>1e9
  SEMANTIC_FAIL  : legacy=动态范围塌缩（边界相对变化>5% 而 u 恒定——
                   floor/ceiling collapse）；B=衰减段无负值（符号语义违约，
                   仅当边界确有下降段）；A=无（线性无可违约项）
  STRUCTURALLY_EXPECTED_ZERO : 边界自身近静（相对变化<1%）且 u 相对变化<1%
  DEGRADED       : legacy 部分钳位（floor+ceil 占用>50% 但仍有信号）
  QUALIFIED      : 其余
§37 归因：u 无变化时看边界——边界也无变化 ⇒ WORLD_ALREADY_REDUCED；
边界有变化 ⇒ TRANSDUCTION_LOSS。
"""
from __future__ import annotations

import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..',
                                                'world_v2')))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..', '..')))

from world_v2_core import (  # noqa: E402
    SourceSpec, WorldEpisode, WorldEpisodeSpec)
from tss.generators.skin_transduction import (  # noqa: E402
    REFERENCE_TRANSDUCTION_CONFIG as LEG, transduce)

# canonical（合同 §四；CANONICAL_FOR_IMPLEMENTATION ≠ OPTIMAL）
S_CANON = 0.00137531
Y_REF = 0.0
G_CANON = 0.275062
DT_EXT = 1.0


def spec_from_dict(d: dict) -> WorldEpisodeSpec:
    return WorldEpisodeSpec(
        episode_id=d["episode_id"], seed=d["seed"], n_nodes=d["n_nodes"],
        kappas=tuple(d["kappas"]), r_leak_ambient=d["r_leak_ambient"],
        sources=tuple(SourceSpec(**x) for x in d["sources"]),
        boundary_config=d["boundary_config"],
        boundary_nodes=tuple(d["boundary_nodes"]),
        dt=d["dt"], t_total=d["t_total"])


def run_boundary(spec: WorldEpisodeSpec):
    bv, _, _ = WorldEpisode(spec).run()
    return bv.frames  # list of tuples（多边界节点=多维）


def apply_legacy(frames):
    return [tuple(transduce(q, LEG) for q in fr) for fr in frames]


def apply_a(frames, s=S_CANON, y_ref=Y_REF):
    return [tuple(s * (q - y_ref) for q in fr) for fr in frames]


def apply_b(frames, g=G_CANON, dt_ext=DT_EXT):
    out, prev = [], None
    for fr in frames:
        if prev is None:
            out.append(tuple(0.0 for _ in fr))       # C5 初始化合同
        else:
            out.append(tuple(g * (q - p) / dt_ext
                             for q, p in zip(fr, prev)))
        prev = fr
    return out


CANDIDATES = {"legacy": apply_legacy, "A": apply_a, "B": apply_b}


def rel_variation(traj):
    """相对变化：range/max(|max|, floor)——刻画信号是否'有事发生'。"""
    flat = [v for fr in traj for v in fr]
    lo, hi = min(flat), max(flat)
    return (hi - lo) / max(abs(hi), abs(lo), 1e-30)


def occupancies(u_traj, name):
    n = sum(len(fr) for fr in u_traj)
    zero = sum(1 for fr in u_traj for v in fr if abs(v) <= 1e-12) / n
    sat = (sum(1 for fr in u_traj for v in fr
               if v >= LEG.u_clip_max) / n if name == "legacy" else 0.0)
    return zero, sat


def classify(name, frames, u_traj):
    flat_u = [v for fr in u_traj for v in fr]
    if any(v != v or abs(v) > 1e9 for v in flat_u):
        return "NUMERIC_FAIL", "-"
    bnd_var = rel_variation(frames)
    u_var = rel_variation(u_traj)
    zero, sat = occupancies(u_traj, name)
    if bnd_var < 0.01 and u_var < 0.01:
        return "STRUCTURALLY_EXPECTED_ZERO", "WORLD_ALREADY_REDUCED"
    if u_var < 1e-6 and bnd_var > 0.05:
        return "SEMANTIC_FAIL", "TRANSDUCTION_LOSS"
    if name == "B" and bnd_var > 0.05:
        # 符号语义：边界存在下降段则 u 应出现负值
        has_desc = any(frames[t][i] < frames[t - 1][i] - 1e-9
                       for t in range(1, len(frames))
                       for i in range(len(frames[0])))
        has_neg = any(v < -1e-12 for v in flat_u)
        if has_desc and not has_neg:
            return "SEMANTIC_FAIL", "TRANSDUCTION_LOSS"
    if name == "legacy" and (zero + sat) > 0.5 and u_var > 1e-6:
        return "DEGRADED", "TRANSDUCTION_LOSS(partial)"
    return "QUALIFIED", "-"


def episode_report(name, frames):
    u = CANDIDATES[name](frames)
    status, attribution = classify(name, frames, u)
    zero, sat = occupancies(u, name)
    flat = [v for fr in u for v in fr]
    return {"status": status, "attribution": attribution,
            "zero_occ": round(zero, 4), "sat_occ": round(sat, 4),
            "u_min": min(flat), "u_max": max(flat),
            "boundary_rel_var": round(rel_variation(frames), 4)}


def rms(traj):
    flat = [v for fr in traj for v in fr]
    return math.sqrt(sum(v * v for v in flat) / len(flat))
