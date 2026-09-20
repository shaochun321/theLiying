"""d21_common.py — D2-1/P2-C 共享层：D2-0 冻结产物加载、site23 轨迹
缓存、relation track 重放重建（IMMUTABLE 缓存）、RelationOccurrencePortV1
组装。

TYPE:INFRA（research/ 层；production READ_ONLY——G0/D2-0 结构只运行
不修改）。

依据：外部《MAINLINE V2 — D2-1/P2-C》方案 37 节 + 评判 ADOPT with
amendments（BACKLOG 2026-09-20 登记：StepB=RelationOccurrencePortV1+
relation track 重放重建缓存+新 site23 轨迹≤8+hold6 封存；E2 功能面判据）。

## 冻结事实（全部只读 D2-0 产物，本轮禁止重标定 §0）

  g_rel        = 0.25      # D2-0 canonical（relation_calibration.json）
  theta_up_ρ   = 2.6164    # = u_work/2（D2-0 Step5 新鲜推导，运行时重读）
  rearm_ρ      = 456 步    # = round(τ_decay/dt)
  ρ 谱系       = relation.r_rho:d2_rho0（depth=1，父=site28/31 生成元地址）
  候选 χ_ρ^(1) = relation_occurrence_candidates.csv ×9（双父 cal 轨迹各 1）

## 主 parent 选择（方案 §9：固定一个已资格化 relation occurrence）

  RHO_MAIN_TRAJ = cal_C3_m —— A→B 中档时距代表（D2-0 NC4/C6 工作轨迹），
  关系窗 [2617, 3971)。配 χ_23^(0)（第三支撑 site23）避免新关系只是
  重复消费 ρ_a 自身的 site28/31 父。

## relation track 重放重建（评判修正兑现点）

  D2-0 只冻结了 χ_ρ^(1) 边界（candidates.csv），未存 x_ρ(t) 原始轨迹——
  RelationOccurrencePortV1 的 raw_relation_track_ref 字段无所指（E-1
  同型缺口：无 raw track 则活动类自然化候选不可计算）。本层以 D2-0
  冻结参数确定性重放 stage-1（parent ports → 𝒩 → RelationCell），
  **逐位核对**重建闭合边界与冻结候选一致后写 IMMUTABLE 缓存。
  重建 ≠ 重标定：参数只读，任何不一致=阻断性失败（不回调）。

复现入口：见 dataset_builder.py。
"""
from __future__ import annotations

import csv
import json
import os
import sys
from typing import Dict, List, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
_D20 = os.path.abspath(os.path.join(_HERE, '..', 'd2_relation_v0'))
for _p in (_ROOT, _D20, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from d2_common import DATA as D20_DATA, DT_G  # noqa: E402
from relation_physical_impl import (  # noqa: E402
    build_relation, drives_for, load_port_windows, step_relation)
from tss.adapters.relation_occurrence_port_v1 import (  # noqa: E402
    RelationOccurrencePortV1, build_port)

DATA = os.path.join(_HERE, 'data')
S23_TRACES = os.path.join(DATA, 'site23_traces')
REL_TRACES = os.path.join(DATA, 'relation_traces')

RHO_MAIN_TRAJ = "cal_C3_m"
# StepB 重建集：主 parent + hold6 消费的三条（H1 未见时长/H4 弱/H5 强）
REBUILD_TRAJS = ("cal_C3_m", "cal_C2_sim", "cal_C5_weak", "cal_C5_strong")
TYPED_PROVENANCE = ("N1_phase",)   # REPLAY_REFERENCE_ONLY 谱系（D2-0 N1）


# ── D2-0 冻结产物只读加载 ──

def frozen_relation_params() -> Tuple[float, float, int]:
    """(g_rel, theta_up_ρ, rearm_ρ) —— 与 D2-0 Step5 同一推导规则重读，
    禁止本轮重标定（方案 §0）。"""
    with open(os.path.join(D20_DATA, 'relation_calibration.json'),
              encoding='utf-8') as f:
        c = json.load(f)
    g = c["canonical_reference"]["g_rel"]
    theta_up = c["measured"]["u_work"] / 2.0
    rearm = round(c["measured"]["tau_decay_s"] / DT_G)
    return g, theta_up, rearm


def frozen_candidates() -> Dict[str, dict]:
    """{traj: 冻结候选行}（每条双父 cal 轨迹恰 1 个 χ_ρ^(1)）。"""
    out = {}
    with open(os.path.join(D20_DATA, 'relation_occurrence_candidates.csv'),
              newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            assert r["traj"] not in out, "候选唯一性假设破坏"
            out[r["traj"]] = r
    return out


def parent_instance_ids(traj: str) -> Tuple[str, ...]:
    """该轨迹构成关系发生的父 occurrence 实例 id（parent manifest 回指）。"""
    ids = []
    with open(os.path.join(D20_DATA, 'occurrence_parent_manifest.csv'),
              newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r["traj"] == traj:
                ids.append(r["occurrence_id"])
    return tuple(ids)


# ── 轨迹缓存（site23 / relation 各自独立 IMMUTABLE 目录）──

def write_immutable(directory: str, tid: str, rows: List[dict]) -> str:
    """写 IMMUTABLE 缓存（UTF-8）；已存在则拒绝覆盖（D2-0 纪律沿用）。"""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{tid}.csv")
    if os.path.exists(path):
        raise FileExistsError(
            f"IMMUTABLE 缓存已存在，禁止覆盖：{path}"
            "（如需重生成，删除旧缓存并在报告登记）")
    fieldnames: List[str] = []
    for r in rows:
        for k in r:
            if k not in fieldnames:
                fieldnames.append(k)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return path


def rebuild_relation_track(traj: str, g: float, theta_up: float,
                           rearm: int, rho_addr, windows=None):
    """stage-1 确定性重放 + 闭合重建 + 录制 x_ρ(t) 轨迹。

    返回 (rows, events, ledger)。计入 depth-1 relation replay 预算 1 次。
    重放路径与 D2-0 run_relation/_run_closure 完全同构（同 build_relation/
    step_relation/OccurrenceClosure 调用序），确定性已由 D2-M5 逐位门证实。
    """
    from tss.generators.occurrence import OccurrenceClosure
    if windows is None:
        windows = load_port_windows()
    da, db = drives_for(traj, windows)
    p = build_relation(g)
    cl = OccurrenceClosure(address=rho_addr, theta_up=theta_up,
                           theta_down=0.1 * theta_up,
                           rearm_min_steps=rearm, dt=DT_G)
    neurons = (p.tin_a, p.tin_b, p.cell)
    e0 = sum(n.energy for n in neurons)
    rows = []
    for k, (sa, sb) in enumerate(zip(da, db)):
        x = step_relation(p, sa.value, sb.value)
        sup = sa.parent_support or sb.parent_support
        cl.update(x, k, phys_support=sup)
        row = {"k": k, "t_phys": k * DT_G, "theta_A": sa.value,
               "theta_B": sb.value, "sup": int(sup), "x_rho": x}
        if k % 100 == 0:
            row["energy"] = sum(n.energy for n in neurons)
        rows.append(row)
    e1 = sum(n.energy for n in neurons)
    ledger = {"traj": traj, "g_rel": g,
              "x_peak": max(r["x_rho"] for r in rows),
              "e_start": e0, "e_end": e1, "energy_drop": e0 - e1,
              "transport_cost": p.bundle_a.transport_cost
              + p.bundle_b.transport_cost}
    return rows, cl.events, ledger


def relation_address():
    """重建 ρ 谱系地址（与 D2-0 Step5 同一注册调用；无物理步进）。"""
    from d2_common import SITE_A, SITE_B, build_parents
    from nexus_v1.components.structural_address import (
        AddressRegistry, DOMAIN_RELATION_RHO)
    _circuit, handles = build_parents({"A": SITE_A, "B": SITE_B})
    addr_a = handles["A"].closure.address
    addr_b = handles["B"].closure.address
    reg = AddressRegistry()
    rho = reg.register_generated(DOMAIN_RELATION_RHO, "d2_rho0",
                                 (addr_a, addr_b), generation_depth=1)
    return rho


def relation2_address():
    """χ_ρ₂ 谱系地址：depth=2，父=(ρ 地址 depth1, site23 生成元地址 depth0)。

    真实 AddressRegistry 注册（谱系单一事实来源）；返回 (rho2, rho, c)。
    """
    from d2_common import SITE_A, SITE_B, SITE_C, build_parents
    from nexus_v1.components.structural_address import (
        AddressRegistry, DOMAIN_RELATION_RHO)
    _circuit, handles = build_parents({"A": SITE_A, "B": SITE_B,
                                       "C": SITE_C})
    addr_a = handles["A"].closure.address
    addr_b = handles["B"].closure.address
    addr_c = handles["C"].closure.address
    reg = AddressRegistry()
    rho = reg.register_generated(DOMAIN_RELATION_RHO, "d2_rho0",
                                 (addr_a, addr_b), generation_depth=1)
    rho2 = reg.register_generated(DOMAIN_RELATION_RHO, "d21_rho2",
                                  (rho, addr_c), generation_depth=2)
    return rho2, rho, addr_c


def frozen_relation2_params() -> Tuple[float, float, int]:
    """(g_rel2, theta_up_ρ2, rearm_ρ2) —— StepC 实测的新鲜推导
    （同一规则族：θ=u_work/2，rearm=round(τ_decay/dt)；数值非抄用）。"""
    with open(os.path.join(DATA, 'relation2_calibration.json'),
              encoding='utf-8') as f:
        c = json.load(f)
    g = c["canonical_reference"]["g_rel2"]
    theta_up = c["measured"]["u_work"] / 2.0
    rearm = round(c["measured"]["tau_decay2_s"] / DT_G)
    return g, theta_up, rearm


# ── RelationOccurrencePortV1 manifest ──

def load_relation_ports() -> Dict[str, RelationOccurrencePortV1]:
    """{traj: port} —— 消费 StepB 产物 relation_occurrence_manifest.csv。"""
    out = {}
    with open(os.path.join(DATA, 'relation_occurrence_manifest.csv'),
              newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            out[r["traj"]] = RelationOccurrencePortV1(
                occurrence_id=r["occurrence_id"],
                relation_lineage=r["relation_lineage"],
                parent_occurrence_ids=tuple(
                    r["parent_occurrence_ids"].split("|")),
                t_up=int(r["t_up"]), t_down=int(r["t_down"]),
                t_rearm=int(r["t_rearm"]),
                t_up_s=float(r["t_up_s"]), t_down_s=float(r["t_down_s"]),
                t_rearm_s=float(r["t_rearm_s"]), dt=float(r["dt"]),
                raw_relation_track_ref=r["raw_relation_track_ref"],
                typed_input_provenance=tuple(
                    r["typed_input_provenance"].split("|")),
                resource_ref=r["resource_ref"],
                generation_depth=int(r["generation_depth"]))
    return out


def load_site23_windows() -> Dict[str, list]:
    """{tid: [PortWindow…]} —— 消费 StepB 产物 site23 occurrence manifest。"""
    from relation_physical_impl import PortWindow
    out: Dict[str, list] = {}
    with open(os.path.join(DATA, 'site23_occurrence_manifest.csv'),
              newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            out.setdefault(r["traj"], []).append(
                PortWindow(int(r["t_up"]), int(r["t_rearm"]),
                           r["occurrence_id"]))
    return out
