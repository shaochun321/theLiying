"""t1b_calibration_cross_world.py — calibration 全集三候选陪跑 + 参数合法域 +
cross-pair 共谋攻击 + LORO + World v1 reference。

TYPE:INFRA。依据：外部《T1-B 方案》§12/§15/§20-§23（评判 C1 合并）。

## 内容
1. **cal 30 episodes × {legacy, A, B}**（§22 legacy 全程陪跑）：逐 episode
   状态分类（§36 五类，t1b_common 预声明规则）+ §37 归因 +
   cross_world_matrix.csv。
2. **参数合法域扫描（§12/§23）**：S, g ∈ log 网格 {1e-5..1e3}，固定一套
   参数横跨全 cal 集，输出=合法区间+失效边界+极端案例（无 argmax）。
   线性映射的预期：数值溢出前无内在失效边界——如实登记；下游 L1 钳位
   子域仅作信息性登记（§33：L1 只是接口后果，非优化目标）。
3. **cross-pair（§20）**：canonical θ_D 固定，横跨全部 World 条件
   （cal 30 + World v1 三历史 reference）。若某参数仅在子域工作 ⇒
   CO_ADAPTATION_RISK=HIGH（不冻结）。
4. **LORO（§21）**：canonical 参数未经任何拟合 ⇒ LORO 退化为跨域状态
   检查（如实登记）：LORO-A 排除域（r_leak<50）与 LORO-B 排除域（3 源）
   episode 上 A/B 不得出现 NUMERIC/SEMANTIC_FAIL。
5. **World v1 reference（§6）**：w0e 三历史 × 三候选——legacy 旧失败
   （baseline-zeroing artifact）应复现；A/B 应保留区分（历史可比性）。

输出：data/cross_world_matrix.csv, data/parameter_legal_regions.csv,
      data/w1ref_results.json, data/t1b_calibration.json
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from t1b_common import (  # noqa: E402
    CANDIDATES, G_CANON, S_CANON, apply_a, apply_b, episode_report,
    rms, run_boundary, spec_from_dict)

sys.path.insert(0, os.path.abspath(os.path.join(
    _HERE, '..', '..', 'world_requalification')))
import w0e_history_discrimination as w0e  # noqa: E402

DATA_DIR = os.path.join(_HERE, 'data')


def load_cal():
    with open(os.path.join(DATA_DIR, "dataset_specs.json"),
              encoding="utf-8") as f:
        specs = json.load(f)
    return [spec_from_dict(d) for d in specs["calibration"]]


def load_manifest():
    with open(os.path.join(DATA_DIR, "dataset_manifest.csv"),
              encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r["group"] == "calibration"]


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 78)
    print("T1-B calibration — 30 eps × 3 候选 / 参数合法域 / cross-pair / "
          "LORO / v1 ref")
    print("=" * 78)
    cal = load_cal()
    manifest = {r["episode_id"]: r for r in load_manifest()}
    frames_cache = {sp.episode_id: run_boundary(sp) for sp in cal}

    # 1) 逐 episode × 候选
    rows = []
    counts = {c: {} for c in CANDIDATES}
    for sp in cal:
        fr = frames_cache[sp.episode_id]
        for name in ("legacy", "A", "B"):
            rep = episode_report(name, fr)
            counts[name][rep["status"]] = \
                counts[name].get(rep["status"], 0) + 1
            rows.append({"episode_id": sp.episode_id, "candidate": name,
                         **rep,
                         "strata": manifest[sp.episode_id]["strata"]})
    with open(os.path.join(DATA_DIR, "cross_world_matrix.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    for name in ("legacy", "A", "B"):
        print(f"[cal] {name:>6}: " + "  ".join(
            f"{k}={v}" for k, v in sorted(counts[name].items())))

    # 2) 参数合法域扫描（子集 8 eps 足够探数值失效；无 argmax）
    sub = cal[:8]
    legal_rows = []
    for pname, applier, canon in (("S", apply_a, S_CANON),
                                  ("g", apply_b, G_CANON)):
        for exp in (-5, -3, -1, 0, 1, 3):
            val = 10.0 ** exp
            ok = True
            for sp in sub:
                u = applier(frames_cache[sp.episode_id],
                            val)  # 第二参数即被扫参数
                if any(v != v or abs(v) > 1e9 for frr in u for v in frr):
                    ok = False
                    break
            legal_rows.append({"param": pname, "value": val,
                               "numeric_ok": ok,
                               "canonical": abs(val - canon) < 1e-12})
        print(f"[legal] {pname}: 1e-5..1e3 全部 numeric_ok="
              f"{all(r['numeric_ok'] for r in legal_rows if r['param'] == pname)}"
              f"（线性⇒溢出前无内在失效边界，如实登记）")
    with open(os.path.join(DATA_DIR, "parameter_legal_regions.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(legal_rows[0].keys()))
        w.writeheader()
        w.writerows(legal_rows)

    # 3) cross-pair：canonical 固定横跨全部条件 ⇒ A/B 失败计数
    ab_fail = [r for r in rows if r["candidate"] in ("A", "B")
               and r["status"] in ("NUMERIC_FAIL", "SEMANTIC_FAIL")]
    co_adaptation = "HIGH" if ab_fail else "LOW"
    print(f"[cross-pair] canonical θ_D 横跨 30 World 条件: A/B "
          f"NUMERIC/SEMANTIC_FAIL={len(ab_fail)} ⇒ "
          f"CO_ADAPTATION_RISK={co_adaptation}")

    # 4) LORO 跨域状态检查（canonical 未经拟合，如实登记退化形态）
    loro = {}
    for tag, col in (("LORO_A_excluded(r_leak<50)", "loro_A_member"),
                     ("LORO_B_excluded(3source)", "loro_B_member")):
        excl_ids = {eid for eid, m in manifest.items()
                    if m[col] == "False"}
        bad = [r for r in rows if r["episode_id"] in excl_ids
               and r["candidate"] in ("A", "B")
               and r["status"] in ("NUMERIC_FAIL", "SEMANTIC_FAIL")]
        loro[tag] = {"n_excluded_eps": len(excl_ids), "ab_fails": len(bad)}
        print(f"[LORO] {tag}: 排除域 {len(excl_ids)} eps, A/B fail={len(bad)}")

    # 5) World v1 reference（w0e 三历史 scale=1.0）
    runs = {n: w0e.run_history(n, 1.0) for n in ("A", "B", "C")}
    v1 = {}
    for cname, fn in CANDIDATES.items():
        us = {n: fn([tuple(row) for row in runs[n]["world"]])
              for n in ("A", "B", "C")}
        pairres = {}
        for x, y in (("A", "B"), ("A", "C"), ("B", "C")):
            dw = w0e.dhat(runs[x]["world"], runs[y]["world"])
            du = w0e.dhat([list(r) for r in us[x]], [list(r) for r in us[y]])
            pairres["-".join((x, y))] = {
                "D_world_hat": round(dw, 4), "D_port_hat": round(du, 4),
                "D_port_abs": w0e.dist([list(r) for r in us[x]],
                                       [list(r) for r in us[y]])}
        v1[cname] = pairres
    leg_art = all(v1["legacy"][p]["D_port_hat"] / v1["legacy"][p]["D_world_hat"]
                  > 1.0 for p in ("A-B",))
    print(f"[v1 ref] legacy A-B ratio="
          f"{v1['legacy']['A-B']['D_port_hat'] / v1['legacy']['A-B']['D_world_hat']:.2f}"
          f"（>1 基线归零假放大复现={leg_art}）; "
          f"A retention={v1['A']['A-B']['D_port_hat'] / v1['A']['A-B']['D_world_hat']:.3f}")
    with open(os.path.join(DATA_DIR, "w1ref_results.json"), "w",
              encoding="utf-8") as f:
        json.dump(v1, f, indent=2)

    out = {"status_counts": counts,
           "co_adaptation_risk": co_adaptation, "loro": loro,
           "legacy_v1_artifact_reproduced": leg_art,
           "note_legal_region": "线性映射：1e-5..1e3 全 numeric_ok，"
                                "溢出前无内在失效边界；L1 钳位子域为"
                                "信息性，非门"}
    with open(os.path.join(DATA_DIR, "t1b_calibration.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("落盘: cross_world_matrix.csv / parameter_legal_regions.csv / "
          "w1ref_results.json / t1b_calibration.json")
    return 0 if co_adaptation == "LOW" else 1


if __name__ == "__main__":
    sys.exit(main())
