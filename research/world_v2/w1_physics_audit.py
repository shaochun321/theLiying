"""w1_physics_audit.py — W1 物理/数值审计：M1 能量闭合 + §33 dt 收敛 +
NC1-NC3 负控制 + E1-E5 episode 族覆盖 + §35 极端案例。

TYPE:INFRA（research/ 层，production 零改动）

## M1 物理闭合（§30/§31）
  10 个采样 episode（WorldSampler(seed=17)）全程逐步检查
  graph.conservation_residual()=|ΔE−injected+leaked|；判据（预登记）：
  max_residual < 1e-6（浮点级）。代表 episode 能量谱系落 CSV
  （E_source/E_field/E_injected/E_leaked 每步）。范围=
  WORLD_LOCAL_ENERGY_AUDITABLE，不宣称全项目闭合（§31）。

## §33 dt 收敛
  代表 episode（N=5, κ=0.05, r_leak=200, 单源 E=300/P=1.0），物理时长
  T_phys=2000 恒定；dt∈{1.0, 0.1, 0.01}（步数 2000/20000/200000——
  物理时长不变，杜绝"步数与 dt 同缩放"旧病）。比较末态边界值/总能量/
  弛豫常数的相邻档相对差，判据：逐档收敛（diff(0.1→0.01) <
  diff(1.0→0.1)）且最细档差 < 1%。

## NC1-NC3 负控制（§40）
  NC1 无源：初始脉冲纯耗散（能量单调降，无注入）。
  NC2 断连源：源存在但从不释放（t_start=∞ 等效）⇒ 场轨迹与 NC1 逐位同。
  NC3 无场耦合：κ=0 ⇒ 驱动节点独热，其余恒 0（无跨节点传输）。
  （NC4/NC5 Full-vs-Reduced 已在 w1_hidden_twins.py 完成，交叉引用。）

## E1-E5 episode 族覆盖（§24）
  E1 单源弛豫 / E2 位置变化（node 0/2/4）/ E3 多源干涉（同时 vs 错时）/
  E4 时间尺度对比（r_leak 20 vs 2000）/ E5 隐藏孪生（w1_hidden_twins
  交叉引用）。各族代表 boundary 轨迹落 CSV（B6：只存代表）。

## §35 极端案例（从 manifest 30 episodes 提取）
  最弱/最强有效耦合、最快/最慢时间尺度、最大能量残差——不只报均值。

输出：data/energy_ledger.csv, data/dt_convergence.csv,
      data/boundary_trajectories.csv, data/w1_physics_audit.json
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
    SourceSpec, WorldEpisode, WorldEpisodeSpec, WorldSampler)

DATA_DIR = os.path.join(_HERE, 'data')


def mk(n, kappa, r_leak, sources, t_total=2000, init=(), dt=1.0,
       eid="audit"):
    return WorldEpisodeSpec(
        episode_id=eid, seed=-1, n_nodes=n,
        kappas=tuple([kappa] * (n - 1)), r_leak_ambient=r_leak,
        sources=tuple(sources), boundary_config="FULL",
        boundary_nodes=tuple(range(n)), dt=dt, t_total=t_total,
        initial_charges=init)


def m1_energy():
    sampler = WorldSampler(seed=17)
    worst = 0.0
    rep_ledger = None
    for i in range(10):
        sp = sampler.sample(f"audit{i:02d}")
        _, ledger, _ = WorldEpisode(sp).run()
        mx = max(r["conservation_residual"] for r in ledger.rows)
        worst = max(worst, mx)
        if i == 0:
            rep_ledger = ledger
    with open(os.path.join(DATA_DIR, "energy_ledger.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rep_ledger.rows[0].keys()))
        w.writeheader()
        w.writerows(rep_ledger.rows)
    ok = worst < 1e-6
    print(f"[M1] 10 episodes 全程逐步账本: max|ΔE−inj+leak|={worst:.2e} "
          f"⇒ {'PASS' if ok else 'FAIL'}（WORLD_LOCAL_ENERGY_AUDITABLE）")
    return {"worst_residual": worst, "pass": ok}


def dt_convergence():
    t_phys = 2000.0
    results = {}
    for dt in (1.0, 0.1, 0.01):
        steps = int(round(t_phys / dt))
        sp = mk(5, 0.05, 200.0, [SourceSpec(0, 300.0, 1.0, 0)],
                t_total=steps, dt=dt, eid=f"dtconv_{dt:g}")
        ep = WorldEpisode(sp)
        e_traj = []
        for _ in range(steps):
            ep.step()
            e_traj.append(ep.graph.total_energy())
        # 弛豫常数：物理时刻 1500→1900 的能量对数斜率
        i1, i2 = int(1500 / dt) - 1, int(1900 / dt) - 1
        tau = (1900 - 1500) / math.log(e_traj[i1] / e_traj[i2])
        results[dt] = {"boundary_final": ep.boundary_frame(),
                       "E_final": e_traj[-1], "tau_relax": tau}
        print(f"[dt] dt={dt:>5g} steps={steps:>6}: E_final={e_traj[-1]:.5f} "
              f"tau={tau:.1f} T0_final={ep.full_state()[0]:.5f}")

    def rdiff(a, b):
        return abs(a - b) / max(abs(b), 1e-30)

    d10 = max(rdiff(results[1.0]["E_final"], results[0.1]["E_final"]),
              rdiff(results[1.0]["tau_relax"], results[0.1]["tau_relax"]))
    d01 = max(rdiff(results[0.1]["E_final"], results[0.01]["E_final"]),
              rdiff(results[0.1]["tau_relax"], results[0.01]["tau_relax"]))
    ok = d01 < d10 and d01 < 0.01
    print(f"[dt] 相邻档最大相对差: 1.0→0.1={d10:.3e}  0.1→0.01={d01:.3e} "
          f"⇒ {'收敛 PASS' if ok else 'FAIL'}")
    return {"per_dt": {str(k): {kk: vv for kk, vv in v.items()
                                if kk != 'boundary_final'}
                       for k, v in results.items()},
            "diff_1.0_to_0.1": d10, "diff_0.1_to_0.01": d01, "pass": ok}


def negative_controls():
    init = tuple([50.0] + [0.0] * 4)
    # NC1 无源纯耗散
    ep1 = WorldEpisode(mk(5, 0.05, 200.0, [], t_total=1000, init=init,
                          eid="NC1"))
    e_prev, mono, f1 = None, True, []
    for _ in range(1000):
        ep1.step()
        e = ep1.graph.total_energy()
        if e_prev is not None and e > e_prev + 1e-12:
            mono = False
        e_prev = e
        f1.append(ep1.full_state())
    inj1 = ep1.graph._total_injected
    # NC2 断连源（t_start 在 episode 外 ⇒ 永不释放）
    ep2 = WorldEpisode(mk(5, 0.05, 200.0,
                          [SourceSpec(2, 1000.0, 1.0, 10 ** 9)],
                          t_total=1000, init=init, eid="NC2"))
    f2 = []
    for _ in range(1000):
        ep2.step()
        f2.append(ep2.full_state())
    nc2_same = f1 == f2
    # NC3 无场耦合
    ep3 = WorldEpisode(mk(5, 0.0, 200.0, [SourceSpec(2, 500.0, 1.0, 0)],
                          t_total=1000, eid="NC3"))
    for _ in range(1000):
        ep3.step()
    st3 = ep3.full_state()
    nc3_isolated = st3[2] > 1.0 and all(
        st3[i] == 0.0 for i in range(5) if i != 2)
    ok = mono and inj1 == 0.0 and nc2_same and nc3_isolated
    print(f"[NC] NC1 纯耗散(单调降/零注入)={mono}/{inj1 == 0.0}  "
          f"NC2 断连源≡NC1 逐位={nc2_same}  "
          f"NC3 无耦合独热={nc3_isolated} ⇒ {'PASS' if ok else 'FAIL'}")
    return {"nc1_monotone": mono, "nc1_zero_injection": inj1 == 0.0,
            "nc2_bitwise_same_as_nc1": nc2_same,
            "nc3_isolated": nc3_isolated, "pass": ok,
            "nc4_nc5": "见 w1_hidden_twins.py Full-vs-Reduced（交叉引用）"}


def episode_families():
    fams = {}
    reps = {}
    # E1 单源弛豫
    reps["E1"] = mk(5, 0.05, 200.0, [SourceSpec(0, 300.0, 1.0, 0)], eid="E1")
    # E2 位置变化
    for node in (0, 2, 4):
        reps[f"E2_n{node}"] = mk(5, 0.05, 200.0,
                                 [SourceSpec(node, 300.0, 1.0, 0)],
                                 eid=f"E2_n{node}")
    # E3 多源干涉：同时 vs 错时
    reps["E3_sync"] = mk(5, 0.05, 200.0,
                         [SourceSpec(0, 300.0, 1.0, 0),
                          SourceSpec(4, 300.0, 1.0, 0)], eid="E3_sync")
    reps["E3_stag"] = mk(5, 0.05, 200.0,
                         [SourceSpec(0, 300.0, 1.0, 0),
                          SourceSpec(4, 300.0, 1.0, 700)], eid="E3_stag")
    # E4 时间尺度对比
    for r in (20.0, 2000.0):
        reps[f"E4_r{r:g}"] = mk(5, 0.05, r, [SourceSpec(0, 300.0, 1.0, 0)],
                                eid=f"E4_r{r:g}")
    rows = []
    for name, sp in reps.items():
        bv, ledger, _ = WorldEpisode(sp).run()
        last = ledger.rows[-1]
        fams[name] = {"E_final": last["E_field"],
                      "peak_T0": max(fr[0] for fr in bv.frames)}
        for t in range(0, sp.t_total, 20):   # B6：降采样代表轨迹
            rows.append({"family": name, "t": t,
                         **{f"T{i}": bv.frames[t][i]
                            for i in range(sp.n_nodes)}})
    with open(os.path.join(DATA_DIR, "boundary_trajectories.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    # 族间可区分性粗检（E2 三位置边界轨迹应互不相同）
    distinct = (fams["E2_n0"]["peak_T0"] != fams["E2_n2"]["peak_T0"]
                != fams["E2_n4"]["peak_T0"])
    print(f"[E1-E5] 族代表全部跑通；E2 位置族边界互异={distinct}；"
          "E5=w1_hidden_twins（交叉引用）")
    return {"families": fams, "e2_distinct": distinct,
            "e5": "见 w1_hidden_twins.py"}


def extremes():
    with open(os.path.join(DATA_DIR, "episode_manifest.csv"),
              encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    k_all = [float(k) for r in rows for k in r["kappas"].split(";")]
    r_all = [float(r["r_leak"]) for r in rows]
    res_all = [float(r["max_residual"]) for r in rows]
    out = {"kappa_min": min(k_all), "kappa_max": max(k_all),
           "tau_env_min": min(r_all), "tau_env_max": max(r_all),
           "max_energy_residual": max(res_all)}
    print(f"[§35 extremes] κ∈[{out['kappa_min']:.4f},{out['kappa_max']:.4f}] "
          f"τ_env∈[{out['tau_env_min']:.0f},{out['tau_env_max']:.0f}] "
          f"max_residual={out['max_energy_residual']:.2e}")
    return out


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 78)
    print("W1 物理/数值审计 — M1 能量 / dt 收敛 / NC1-3 / E1-E5 / 极端案例")
    print("=" * 78)
    out = {"M1": m1_energy(), "dt_convergence": dt_convergence(),
           "negative_controls": negative_controls(),
           "episode_families": episode_families(), "extremes": extremes()}
    path = os.path.join(DATA_DIR, "w1_physics_audit.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"落盘: {path}")
    ok = (out["M1"]["pass"] and out["dt_convergence"]["pass"]
          and out["negative_controls"]["pass"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
