"""t1b_dataset.py — T1-B 数据集构建：calibration(30) + held-out(20, BLIND)。

TYPE:INFRA（research/ 层；nexus_v1/tss/research/world_v2 零改动）

依据：外部《T1-B 方案》§6-§8（经评判 C4 具体化）。

## 三分集（§6）
  W_ref  = World v1（w0e 三历史，在 calibration 脚本内直接复用，不在此建）
  W_cal  = 30 episodes：WorldSampler(seed=1001) 直采（Θ_legal 域内）
  W_hold = 20 episodes：分层构建，**必含困难角**（§7）：
     r_leak<50 强耗散 ×3 / 3 源 ×3 / N=3 低 DOF ×3 / N=20 高 DOF ×3 /
     错时源(t_start>300) ×3 / REDUCED 非 node0 边界 ×3 / 随机补足 ×2
  strata 只按物理量（§8：κ/τ_env/源数/时长/能量/边界大小），无语义标签。

## BLIND 纪律（§40 前置）
  held-out manifest 建成即封存（记录 SHA256）；本脚本不对 hold 集计算
  任何转导指标；heldout 评估只允许在 canonical 冻结后运行一次。

## LORO 组（§21）
  LORO-A = cal 中 r_leak≥50 的子集（排除强耗散域，hold 专测）
  LORO-B = cal 中源数≤2 的子集（排除 3 源，hold 专测）
  登记为 manifest 列，不复制数据。

输出：data/dataset_manifest.csv（两集合+strata+LORO 列），
      data/dataset_specs.json（spec 全量可重建），
      data/heldout_lock.json（held-out 部分的 SHA256 封存）
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..',
                                                'world_v2')))
from world_v2_core import WorldSampler, WorldEpisodeSpec  # noqa: E402

DATA_DIR = os.path.join(_HERE, 'data')


def spec_to_dict(s: WorldEpisodeSpec) -> dict:
    return {"episode_id": s.episode_id, "seed": s.seed,
            "n_nodes": s.n_nodes, "kappas": list(s.kappas),
            "r_leak_ambient": s.r_leak_ambient,
            "sources": [{"node": x.node, "energy": x.energy,
                         "power": x.power, "t_start": x.t_start}
                        for x in s.sources],
            "boundary_config": s.boundary_config,
            "boundary_nodes": list(s.boundary_nodes),
            "dt": s.dt, "t_total": s.t_total}


def strata_of(s: WorldEpisodeSpec):
    tags = []
    if s.r_leak_ambient < 50:
        tags.append("strong_dissipation")
    if len(s.sources) == 3:
        tags.append("three_source")
    if s.n_nodes == 3:
        tags.append("low_dof")
    if s.n_nodes == 20:
        tags.append("high_dof")
    if any(x.t_start > 300 for x in s.sources):
        tags.append("staggered_source")
    if s.boundary_config == "REDUCED" and 0 not in s.boundary_nodes:
        tags.append("reduced_non_node0")
    return tags


def build_heldout():
    """分层构建：从大候选池按困难角配额挑选（strata 只按物理量）。"""
    sampler = WorldSampler(seed=2001)
    pool = [sampler.sample(f"hold_pool{i:03d}") for i in range(400)]
    quota = [("strong_dissipation", 3), ("three_source", 3),
             ("low_dof", 3), ("high_dof", 3),
             ("staggered_source", 3), ("reduced_non_node0", 3)]
    chosen, used = [], set()
    for tag, k in quota:
        got = 0
        for s in pool:
            if id(s) in used or got >= k:
                continue
            if tag in strata_of(s):
                chosen.append(s)
                used.add(id(s))
                got += 1
        assert got == k, f"heldout strata {tag} 不足（池 400 未覆盖）"
    for s in pool:  # 随机补足到 20
        if len(chosen) >= 20:
            break
        if id(s) not in used:
            chosen.append(s)
            used.add(id(s))
    return chosen[:20]


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 78)
    print("T1-B 数据集 — cal(30, seed=1001) + held-out(20, seed=2001 分层, BLIND)")
    print("=" * 78)
    cal_sampler = WorldSampler(seed=1001)
    cal = [cal_sampler.sample(f"cal{i:03d}") for i in range(30)]
    hold = build_heldout()

    rows, specs = [], {"calibration": [], "heldout": []}
    for group, eps in (("calibration", cal), ("heldout", hold)):
        for s in eps:
            tags = strata_of(s)
            rows.append({
                "group": group, "episode_id": s.episode_id,
                "n_nodes": s.n_nodes, "n_sources": len(s.sources),
                "r_leak": round(s.r_leak_ambient, 3),
                "kappa_mean": round(sum(s.kappas) / len(s.kappas), 5),
                "boundary": f"{s.boundary_config}:{s.boundary_nodes}",
                "strata": ";".join(tags) or "-",
                "loro_A_member": group == "calibration"
                and s.r_leak_ambient >= 50,
                "loro_B_member": group == "calibration"
                and len(s.sources) <= 2,
            })
            specs[group].append(spec_to_dict(s))

    man_path = os.path.join(DATA_DIR, "dataset_manifest.csv")
    with open(man_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    specs_path = os.path.join(DATA_DIR, "dataset_specs.json")
    with open(specs_path, "w", encoding="utf-8") as f:
        json.dump(specs, f, indent=2)

    hold_blob = json.dumps(specs["heldout"], sort_keys=True).encode()
    sha = hashlib.sha256(hold_blob).hexdigest()
    with open(os.path.join(DATA_DIR, "heldout_lock.json"), "w",
              encoding="utf-8") as f:
        json.dump({"heldout_sha256": sha, "n_heldout": len(hold),
                   "note": "BLIND：heldout 只允许在 canonical 冻结后评估一次"},
                  f, indent=2)

    n_loro_a = sum(1 for r in rows if r["loro_A_member"])
    n_loro_b = sum(1 for r in rows if r["loro_B_member"])
    hold_tags = [t for r in rows if r["group"] == "heldout"
                 for t in r["strata"].split(";") if t != "-"]
    print(f"cal=30（LORO-A={n_loro_a} / LORO-B={n_loro_b}）  hold=20")
    print(f"hold 困难角覆盖: " + ", ".join(
        f"{t}×{hold_tags.count(t)}" for t in sorted(set(hold_tags))))
    print(f"heldout SHA256={sha[:16]}…（封存）")
    print(f"落盘: {man_path}\n落盘: {specs_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
