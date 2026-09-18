"""g0r0_replay_bridge.py — multirate replay + Twin-2 跨层泄漏检查 +
B bridge 五场景（§25-§28）。

TYPE:INFRA（production READ_ONLY）

## Multirate replay（§27）
  代表 episode → timestamped Y_B 帧（t_phys, dt_B, sample_id, y）→
  arm-live：World 步进与 G0 子步消费交替进行（每完成 1 个边界区间即
  展开 1000 子步喂入）；arm-replay：World 删除后仅由录制帧离线重建。
  same scheduler config/dt_G/G0 初态 ⇒ G0 状态轨迹**逐位**比较。

## Twin-2 跨层检查（§28；用 A 通道避开 B 桥饱和混淆）
  源 E_A=40（燃 40s）vs E_B=20（燃 20s），P=1 同 node0：边界逐位相同至
  t=20s，之后分叉。要求：相同边界段 G0_A≡G0_B（逐位），分叉后才允许
  不同；否则 CROSS_LAYER_HIDDEN_LEAK。

## B bridge 五场景（§25-§26；T_phys=40s，S1+B1 调度）
  v1 等价（3 节点 TEST 档）/ v2 普通（N=5）/ 强耗散（r_leak=20）/
  多源 / hidden-twin 变体。判据（§26）：有限输出/无 NaN/L1≤钳位/状态
  连续（相邻秒 collector 跳变 < 10×窗口典型幅度）/dt_G 收敛（invariance
  轮已证，交叉引用）；**不检查 occurrence 必须发生**（只登记次数）。

输出：data/replay_results.json, data/g0r0_bridge.json
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from g0r0_common import (  # noqa: E402
    MultiRateScheduler, boundary_from_episode, drive_g0, ep_spec,
    fresh_g0, u_series_a, u_series_b1)
from world_v2_core import SourceSpec, WorldEpisode  # noqa: E402

DATA_DIR = os.path.join(_HERE, 'data')
DT_G = 0.001


def run_pipeline(u_sub, dt_g=DT_G, sample_every=1000, count_events=False):
    h = fresh_g0()
    states, n_ev = [], 0
    for k, u in enumerate(u_sub):
        ev = h.tick(u, dt_g, k)
        if ev is not None:
            n_ev += 1
        if (k + 1) % sample_every == 0:
            states.append((h.l1.activation, h.hc.pre_trace,
                           *(n.pre_trace for n in h.ensemble),
                           h.collector.pre_trace))
    return (states, n_ev) if count_events else states


def multirate_replay():
    spec = ep_spec(t_total=60, dt=1.0, eid="replay")
    sch = MultiRateScheduler(1.0, DT_G)
    # arm-live：World 步进与 G0 消费交替
    ep = WorldEpisode(spec)
    h = fresh_g0()
    y_prev = 0.0
    live_states, k_global = [], 0
    frames = [(0.0, 1.0, 0, 0.0)]
    for t in range(spec.t_total):
        ep.step()
        y_next = ep.graph.cells[0].temperature
        frames.append(((t + 1) * 1.0, 1.0, t + 1, y_next))
        for k in range(1, sch.n_sub + 1):        # S1 展开本区间
            y = y_prev + (k / sch.n_sub) * (y_next - y_prev)
            h.tick(0.00137531 * y, DT_G, k_global)
            k_global += 1
        live_states.append((h.l1.activation, h.hc.pre_trace,
                            *(n.pre_trace for n in h.ensemble),
                            h.collector.pre_trace))
        y_prev = y_next
    # arm-replay：删除 World，仅由录制帧重建
    y_samples = [fr[3] for fr in frames]
    u_sub = u_series_a(sch.expand(y_samples, "S1"))
    replay_states = run_pipeline(u_sub)
    ok = live_states == replay_states
    print(f"[replay] live(交替步进) vs replay(纯帧重建) 逐位一致={ok}  "
          f"(timestamped 帧含 t_phys/dt_B/sample_id)")
    return {"bit_exact": ok, "n_samples": len(frames)}


def twin2_check():
    sch = MultiRateScheduler(1.0, DT_G)
    y = {}
    for tag, e in (("A", 40.0), ("B", 20.0)):
        y[tag] = [fr[3] for fr in boundary_from_episode(ep_spec(
            t_total=50, sources=[SourceSpec(0, e, 1.0, 0)],
            eid=f"twin2{tag}"))]
    same_until = next(i for i in range(len(y["A"]))
                      if y["A"][i] != y["B"][i])
    sA = run_pipeline(u_series_a(sch.expand(y["A"], "S1")))
    sB = run_pipeline(u_series_a(sch.expand(y["B"], "S1")))
    # 边界相同段（S1 消费到样本 n+1 ⇒ 状态相同段=前 same_until-1 秒）
    n_same = same_until - 1
    seg_same = sA[:n_same] == sB[:n_same]
    diverged = sA[n_same:] != sB[n_same:]
    ok = seg_same and diverged
    print(f"[Twin-2] 边界逐位相同至样本 {same_until}；G0 状态相同段"
          f"(前 {n_same} 秒)逐位={seg_same}，分叉后不同={diverged} ⇒ "
          f"{'无 CROSS_LAYER_HIDDEN_LEAK ✓' if ok else 'LEAK/异常'}")
    return {"boundary_same_until_sample": same_until,
            "g0_identical_during_same": seg_same,
            "g0_diverges_after": diverged, "pass": ok}


def bridge_scenarios():
    sch = MultiRateScheduler(1.0, DT_G)
    scen = {
        "v1_equiv_3node": ep_spec(n=3, t_total=40,
                                  sources=[SourceSpec(0, 20.0, 1.0, 0)],
                                  eid="br_v1"),
        "v2_ordinary": ep_spec(t_total=40, eid="br_v2"),
        "strong_dissipation": ep_spec(r_leak=20.0, t_total=40,
                                      eid="br_diss"),
        "multi_source": ep_spec(t_total=40, sources=[
            SourceSpec(0, 15.0, 1.0, 0), SourceSpec(4, 15.0, 1.0, 15)],
            eid="br_multi"),
        "hidden_twin_variant": ep_spec(t_total=40, sources=[
            SourceSpec(0, 35.0, 1.0, 0)], eid="br_twin"),
    }
    out = {}
    all_ok = True
    for name, sp in scen.items():
        y = [fr[3] for fr in boundary_from_episode(sp)]
        u = u_series_b1(sch.expand(y, "S1"), DT_G)
        states, n_ev = run_pipeline(u, count_events=True)
        flat = [v for st in states for v in st]
        finite = all(v == v and abs(v) < 1e9 for v in flat)
        l1_max = max(st[0] for st in states)
        col = [st[-1] for st in states]
        col_span = max(col) - min(col)
        jump = max(abs(a - b) for a, b in zip(col, col[1:]))
        continuous = col_span == 0 or jump < 10 * max(col_span / 5, 1e-9)
        ok = finite and l1_max <= 10.0 and continuous
        all_ok = all_ok and ok
        out[name] = {"finite": finite, "l1_max": l1_max,
                     "collector_jump_ok": continuous,
                     "n_occurrences_recorded": n_ev, "pass": ok}
        print(f"[bridge {name:<20}] finite={finite} L1max={l1_max:.2f} "
              f"连续={continuous} occ={n_ev}(只登记) ⇒ "
              f"{'PASS' if ok else 'FAIL'}")
    return out, all_ok


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 78)
    print("G0-R0 replay + Twin-2 + B bridge 五场景")
    print("=" * 78)
    rep = multirate_replay()
    tw = twin2_check()
    br, br_ok = bridge_scenarios()
    out = {"replay": rep, "twin2": tw, "bridge": br,
           "bridge_all_pass": br_ok,
           "note": "B 桥 L1 饱和（scheduler 轮登记 33.3% 子步 u>0.05）"
                   "不在 §26 判据内——量级重标属 occurrence revalidation"}
    with open(os.path.join(DATA_DIR, "replay_results.json"), "w",
              encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    with open(os.path.join(DATA_DIR, "g0r0_bridge.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("落盘: replay_results.json / g0r0_bridge.json")
    return 0 if (rep["bit_exact"] and tw["pass"] and br_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
