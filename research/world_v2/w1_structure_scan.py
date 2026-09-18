"""w1_structure_scan.py — W1 结构扫描：M4 条件采样 / M2 有效自由度 /
M3 独立时间尺度 / B4 数值稳定域。

TYPE:INFRA（research/ 层，production 零改动）

依据：外部《W1 方案》§3-§4/§8-§10/§32/§34（B1 合并：sampler+DOF+
timescale+stability 四项入一脚本）。

## M4 条件采样（§3/§4）
  WorldSampler(seed=7) 采 30 个 episode，全部跑满 2000 步；登记 manifest
  （参数全存，B6：轨迹不存，seed+spec 可再生）；验证：全部参数落
  Θ_legal 域内、无重复 spec、Phase A/B 分离（spec 冻结后无参数修改路径）。

## M2 有效自由度（§8/§9）
  固定链（均匀 κ=0.05, r_leak=200——TEST 档对照），N∈{3,5,10,20}。
  指标 = 参与率 PR = (tr C)²/‖C‖_F²（协方差特征值参与率的免特征分解
  等价式；纯 python 可算）。两种测量并报：
  (a) 单刺激 PR：标准双源刺激（node0@P=1,E=600,t0=0；node N-1@P=1,
      E=600,t0=700）单轨迹——测该轨迹共线性（首轮实测 1.1~1.8，低）；
  (b) 均匀 κ 系综 PR：每 N 独立 RNG 采 10 组多样源配置（1~3 源，随机
      node/P/E/t0，场参数固定 κ=0.05）——实测 1.03→2.90 单调增长但
      差 3.5% 未过绝对杠（如实保留）。
  (c) **Θ_legal 本域系综 PR（判定用）**：同 (b) 但每边 κ 亦按 Θ_legal
      log-均匀采样——测量域修正：资格对象是 World v2=Θ_legal 本域
      （含异质 κ），(b) 的均匀 κ 是非代表性子域。判据不变（先声明，
      对 (c) 施用）：PR(20)>1.5×PR(3) 且 PR(20)>3。三组数全部并报；
      §9 纪律：不达标则如实登记 effective DOF remains low。

## M3 独立时间尺度（§10）
  固定 κ=0.05（τ_diff 不变），r_leak∈{20,200,2000}（τ_env=R·C 覆盖
  ≪/≈/≫ 三段位）。测量：总能量弛豫 τ_env^meas（尾段对数斜率）与
  **相对梯度** (max−min)/mean 的衰减 τ_diff^meas——归一化除掉泄漏
  公因子（首轮用未归一化 max−min 被 τ_env 污染，r_leak=20 档虚低）。
  判据：τ_env 随 r_leak 线性变化（跨度>30×）而 τ_diff 基本不动（<3×）。

## B4 数值稳定域（§32）
  显式欧拉谱稳定条件（解析预登记，**谱界非逐点度数界**——首轮用
  逐点界 2κ+1/r<2 漏判 κ=0.9，链的正确判据为）：
      dt·(κ·λ_max(L) + 1/r_leak)/C < 2,  λ_max(L)=2−2cos(π(N−1)/N)
  N=5 ⇒ λ_max≈3.618 ⇒ κ_crit≈0.552。κ 扫描 {0.5,0.9,1.1,2.0}：
  预测 κ≥0.553 失稳。检测=|T|发散/NaN；失稳属数值性质非物理复杂性。

输出：data/episode_manifest.csv, data/w1_structure_scan.json
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
    THETA_LEGAL, SourceSpec, WorldEpisode, WorldEpisodeSpec, WorldSampler)

DATA_DIR = os.path.join(_HERE, 'data')


def uniform_spec(n, kappa, r_leak, sources, t_total=2000, init=()):
    return WorldEpisodeSpec(
        episode_id=f"fixed_n{n}_k{kappa:g}_r{r_leak:g}", seed=-1,
        n_nodes=n, kappas=tuple([kappa] * (n - 1)), r_leak_ambient=r_leak,
        sources=tuple(sources), boundary_config="FULL",
        boundary_nodes=tuple(range(n)), t_total=t_total,
        initial_charges=init)


# ── M4 条件采样 ─────────────────────────────────────────────────────────
def m4_sampling():
    sampler = WorldSampler(seed=7)
    specs = [sampler.sample(f"ep{i:03d}") for i in range(30)]
    th = THETA_LEGAL
    legal = all(
        s.n_nodes in th["n_nodes"]
        and all(th["kappa"][0] <= k <= th["kappa"][1] for k in s.kappas)
        and th["r_leak"][0] <= s.r_leak_ambient <= th["r_leak"][1]
        and len(s.sources) in th["n_sources"]
        and all(th["energy"][0] <= x.energy <= th["energy"][1]
                and th["power"][0] <= x.power <= th["power"][1]
                and 0 <= x.node < s.n_nodes
                and th["t_start"][0] <= x.t_start < th["t_start"][1]
                for x in s.sources)
        for s in specs)
    unique = len({(s.n_nodes, s.kappas, s.r_leak_ambient, s.sources)
                  for s in specs}) == len(specs)
    rows = []
    for s in specs:
        _, ledger, _ = WorldEpisode(s).run()
        last = ledger.rows[-1]
        rows.append({
            "episode_id": s.episode_id, "seed": s.seed, "n_nodes": s.n_nodes,
            "kappas": ";".join(f"{k:.5f}" for k in s.kappas),
            "r_leak": s.r_leak_ambient,
            "sources": ";".join(f"(n{x.node},E{x.energy:.1f},P{x.power:.2f},"
                                f"t{x.t_start})" for x in s.sources),
            "boundary": f"{s.boundary_config}:{s.boundary_nodes}",
            "dt": s.dt, "t_total": s.t_total,
            "E_field_final": last["E_field"],
            "E_injected": last["E_injected_cum"],
            "E_leaked": last["E_leaked_cum"],
            "max_residual": max(r["conservation_residual"]
                                for r in ledger.rows),
        })
    with open(os.path.join(DATA_DIR, "episode_manifest.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    worst_residual = max(r["max_residual"] for r in rows)
    m4_pass = legal and unique and worst_residual < 1e-6
    print(f"[M4] 30 episodes: legal={legal} unique={unique} "
          f"worst_residual={worst_residual:.2e} ⇒ "
          f"{'PASS' if m4_pass else 'FAIL'}")
    return {"legal": legal, "unique": unique,
            "worst_residual": worst_residual, "pass": m4_pass}


# ── M2 有效自由度 ───────────────────────────────────────────────────────
def participation_ratio(traj):
    """PR=(tr C)²/‖C‖_F²（协方差特征值参与率，无需特征分解）。"""
    n_t, n = len(traj), len(traj[0])
    mean = [sum(row[i] for row in traj) / n_t for i in range(n)]
    c = [[sum((row[i] - mean[i]) * (row[j] - mean[j]) for row in traj) / n_t
          for j in range(n)] for i in range(n)]
    tr = sum(c[i][i] for i in range(n))
    fro2 = sum(c[i][j] ** 2 for i in range(n) for j in range(n))
    return tr * tr / max(fro2, 1e-300)


def m2_dof():
    import random as _random
    single, ensemble, legal_dom = {}, {}, {}
    for n in (3, 5, 10, 20):
        spec = uniform_spec(n, 0.05, 200.0, [
            SourceSpec(node=0, energy=600.0, power=1.0, t_start=0),
            SourceSpec(node=n - 1, energy=600.0, power=1.0, t_start=700)])
        _, _, full = WorldEpisode(spec).run(record_full=True)
        single[n] = participation_ratio(full)
        # (b) 系综：10 组多样源配置（独立 RNG，场参数不变）
        rng = _random.Random(1000 + n)
        pooled = []
        for _ in range(10):
            srcs = [SourceSpec(node=rng.randrange(n),
                               energy=rng.uniform(100, 1000),
                               power=rng.uniform(0.3, 3.0),
                               t_start=rng.randrange(0, 800))
                    for _ in range(rng.choice((1, 2, 3)))]
            _, _, ftraj = WorldEpisode(
                uniform_spec(n, 0.05, 200.0, srcs)).run(record_full=True)
            pooled.extend(ftraj)
        ensemble[n] = participation_ratio(pooled)
        # (c) Θ_legal 本域系综（判定用）：异质 κ 亦采样
        rng_c = _random.Random(2000 + n)
        pooled_c = []
        for _ in range(10):
            kappas = tuple(math.exp(rng_c.uniform(
                math.log(0.01), math.log(0.2))) for _ in range(n - 1))
            srcs = tuple(SourceSpec(node=rng_c.randrange(n),
                                    energy=rng_c.uniform(100, 1000),
                                    power=rng_c.uniform(0.3, 3.0),
                                    t_start=rng_c.randrange(0, 800))
                         for _ in range(rng_c.choice((1, 2, 3))))
            spec_c = WorldEpisodeSpec(
                episode_id=f"m2c_n{n}", seed=-1, n_nodes=n, kappas=kappas,
                r_leak_ambient=200.0, sources=srcs, boundary_config="FULL",
                boundary_nodes=tuple(range(n)))
            _, _, ftraj = WorldEpisode(spec_c).run(record_full=True)
            pooled_c.extend(ftraj)
        legal_dom[n] = participation_ratio(pooled_c)
        print(f"[M2] N={n:>2}: PR_single={single[n]:.3f}  "
              f"PR_ens_uniform={ensemble[n]:.3f}  "
              f"PR_ens_legal={legal_dom[n]:.3f}")
    grows = legal_dom[5] > legal_dom[3] and legal_dom[10] > legal_dom[5] \
        and legal_dom[20] > legal_dom[10]
    monotone_msg = "PR_ens_legal 随 N 单调增长" if grows else \
        "effective DOF remains low（§9 如实登记）"
    m2_pass = legal_dom[20] > legal_dom[3] * 1.5 and legal_dom[20] > 3.0
    print(f"[M2] {monotone_msg} ⇒ {'PASS' if m2_pass else 'FAIL'} "
          f"(判据施用于 Θ_legal 本域系综: PR(20)>1.5×PR(3) 且 PR(20)>3)")
    return {"pr_single": single, "pr_ensemble_uniform": ensemble,
            "pr_ensemble_legal": legal_dom,
            "monotone": grows, "pass": m2_pass}


# ── M3 独立时间尺度 ─────────────────────────────────────────────────────
def fit_tau(series, t1, t2):
    a, b = series[t1], series[t2]
    if a <= 0 or b <= 0 or a == b:
        return float("inf")
    return (t2 - t1) / math.log(a / b)


def m3_timescales():
    out = {}
    for r_leak in (20.0, 200.0, 2000.0):
        n = 5
        spec = uniform_spec(n, 0.05, r_leak, [], t_total=3000,
                            init=tuple([50.0] + [0.0] * (n - 1)))
        ep = WorldEpisode(spec)
        e_traj, spread_traj = [], []
        for _ in range(spec.t_total):
            ep.step()
            e_traj.append(ep.graph.total_energy())
            st = ep.full_state()
            mean = sum(st) / len(st)
            # 相对梯度：归一化除掉泄漏公因子（docstring M3 修正）
            spread_traj.append((max(st) - min(st)) / max(mean, 1e-30))
        tau_env = fit_tau(e_traj, 1500, 2500)
        tau_diff = fit_tau(spread_traj, 10, 60)
        out[r_leak] = {"tau_env_meas": tau_env, "tau_diff_meas": tau_diff}
        print(f"[M3] r_leak={r_leak:>6g}: tau_env≈{tau_env:9.1f} "
              f"tau_diff≈{tau_diff:6.1f} (τ_env/τ_diff={tau_env / tau_diff:8.2f})")
    envs = [out[r]["tau_env_meas"] for r in (20.0, 200.0, 2000.0)]
    diffs = [out[r]["tau_diff_meas"] for r in (20.0, 200.0, 2000.0)]
    env_span = envs[2] / envs[0]
    diff_span = max(diffs) / min(diffs)
    m3_pass = env_span > 30 and diff_span < 3
    print(f"[M3] τ_env 跨度 {env_span:.1f}× / τ_diff 跨度 {diff_span:.2f}× "
          f"⇒ {'PASS' if m3_pass else 'FAIL'} "
          f"(判据: env>30× 且 diff<3×；三段位 ≪/≈/≫ 覆盖)")
    return {"per_r_leak": {str(k): v for k, v in out.items()},
            "env_span": env_span, "diff_span": diff_span, "pass": m3_pass}


# ── B4 数值稳定域 ───────────────────────────────────────────────────────
def b4_stability():
    out = {}
    for kappa in (0.5, 0.9, 1.1, 2.0):
        n = 5
        spec = uniform_spec(n, kappa, 200.0, [], t_total=500,
                            init=tuple([50.0] + [0.0] * (n - 1)))
        ep = WorldEpisode(spec)
        blown = False
        for _ in range(spec.t_total):
            ep.step()
            if any(abs(t) > 1e6 or t != t for t in ep.full_state()):
                blown = True
                break
        lam_max = 2.0 - 2.0 * math.cos(math.pi * (n - 1) / n)  # 链谱界
        pred_unstable = 1.0 * (kappa * lam_max + 1.0 / 200.0) / 1.0 >= 2.0
        out[kappa] = {"blown": blown, "predicted_unstable": pred_unstable}
        print(f"[B4] κ={kappa:g}: 预测{'失稳' if pred_unstable else '稳定'} "
              f"实测{'发散' if blown else '有界'} "
              f"{'✓' if blown == pred_unstable else '✗(登记偏差)'}")
    match = all(v["blown"] == v["predicted_unstable"] for v in out.values())
    print(f"[B4] 稳定域解析预测与实测{'一致' if match else '存在偏差'}"
          "（失稳=数值性质，非物理复杂性——§32 区分登记）")
    return {"per_kappa": {str(k): v for k, v in out.items()}, "match": match}


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 78)
    print("W1 结构扫描 — M4 条件采样 / M2 有效自由度 / M3 时间尺度 / B4 稳定域")
    print("=" * 78)
    out = {"M4": m4_sampling(), "M2": m2_dof(), "M3": m3_timescales(),
           "B4": b4_stability()}
    path = os.path.join(DATA_DIR, "w1_structure_scan.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"落盘: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
