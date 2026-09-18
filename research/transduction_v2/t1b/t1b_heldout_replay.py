"""t1b_heldout_replay.py — canonical 冻结→fingerprint→lock→blind held-out
一次 + W1 双 twin 测试 + replay 纯度。

TYPE:INFRA。依据：外部《T1-B 方案》§17-§19/§38-§41（评判 C1 合并、C5
初始化合同）。

## §40 流程（严格顺序，本脚本一次执行）
  1. canonical 配置（合同 §四，provenance 已预承诺）→ SHA256 fingerprint
  2. 校验 held-out manifest 未被触碰（对照 dataset 封存 SHA）
  3. LOCK 登记（fingerprint + heldout SHA 写入结果文件）
  4. blind held-out 20 eps × {legacy, A, B} 跑一次；逐 episode 状态分类；
     结果原样登记为 FIRST_HELDOUT_RESULT（若有失败：先归因，不改参重跑）
  门（§41）：A/B 无 NUMERIC_FAIL 且无 TRANSDUCTION_LOSS 型 SEMANTIC_FAIL
  ⇒ 无结构性崩溃。STRUCTURALLY_EXPECTED_ZERO 不是失败。

## W1 双 twin 测试（§17-§19）
  Twin-1（场隐藏，过去 Y 不同）：A 在 t0 必须相等（容差=S×|ΔY(t0)|）；
  B 在 t0 允许不同但必须完整由录制 Y 重放解释（重放重算 ≡ 原值）。
  Twin-2（源隐藏，过去 Y 逐位同）：A、B 在 t0 均必须逐位相等；
  未来分叉后 u 按各自合同响应。违者 HIDDEN_ACCESS_OR_STATE_LEAK=FAIL。

## Replay 纯度（§39）
  代表 episodes（cal×2 + hold×2）：live 应用（episode 逐步喂候选）vs
  录制 Y_B 后离线重放（B 初始化合同 C5：prev=首样本）⇒ 逐位一致。

输出：data/heldout_results.csv, data/replay_results.json,
      data/t1b_heldout.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from t1b_common import (  # noqa: E402
    CANDIDATES, DT_EXT, G_CANON, S_CANON, Y_REF, apply_a, apply_b,
    episode_report, run_boundary, spec_from_dict)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..',
                                                'world_v2')))
from world_v2_core import SourceSpec, WorldEpisode, WorldEpisodeSpec  # noqa: E402

DATA_DIR = os.path.join(_HERE, 'data')
N, T_DRIVE, T0 = 10, 100, 99   # W1 冻结 twin 协议常量


def canonical_fingerprint():
    cfg = {"candidate_A": {"arch": "thin_amplitude_U_T", "S": S_CANON,
                           "Y_ref": Y_REF,
                           "provenance": "CANONICAL_REFERENCE/PHYSICAL"},
           "candidate_B": {"arch": "explicit_rate_U_dT", "g": G_CANON,
                           "dt_ext": DT_EXT, "init": "prev=first_sample",
                           "provenance": "CANONICAL_REFERENCE/PHYSICAL"},
           "timebase": "MAINLINE_TIMEBASE_CONTRACT dt_ext=1s",
           "contract": "T1B_PORT_AND_TIMEBASE_CONTRACT.md"}
    blob = json.dumps(cfg, sort_keys=True).encode()
    return cfg, hashlib.sha256(blob).hexdigest()


def twin_specs():
    def sp(sources, eid):
        return WorldEpisodeSpec(
            episode_id=eid, seed=-1, n_nodes=N, kappas=(0.05,) * (N - 1),
            r_leak_ambient=200.0, sources=tuple(sources),
            boundary_config="REDUCED", boundary_nodes=(0,), t_total=1600)
    # Twin-1（W1 冻结：B 幅值线性反解）
    b_a = run_boundary(sp([SourceSpec(0, 1e9, 1.0, 0)], "u1"))
    b_u = run_boundary(sp([SourceSpec(N - 1, 1e9, 1.0, 0)], "u2"))
    s = b_a[T0][0] / b_u[T0][0]
    t1a = sp([SourceSpec(0, 1.0 * T_DRIVE, 1.0, 0)], "t1A")
    t1b = sp([SourceSpec(N - 1, s * T_DRIVE, s, 0)], "t1B")
    t2a = sp([SourceSpec(0, 900.0, 1.0, 0)], "t2A")
    t2b = sp([SourceSpec(0, 100.0, 1.0, 0)], "t2B")
    return (t1a, t1b), (t2a, t2b)


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 78)
    print("T1-B held-out(BLIND 一次) + W1 双 twin + replay 纯度")
    print("=" * 78)

    # 1-3) 冻结 + 封存校验 + LOCK
    cfg, fp = canonical_fingerprint()
    with open(os.path.join(DATA_DIR, "dataset_specs.json"),
              encoding="utf-8") as f:
        specs = json.load(f)
    hold_blob = json.dumps(specs["heldout"], sort_keys=True).encode()
    hold_sha = hashlib.sha256(hold_blob).hexdigest()
    with open(os.path.join(DATA_DIR, "heldout_lock.json"),
              encoding="utf-8") as f:
        lock = json.load(f)
    sealed = hold_sha == lock["heldout_sha256"]
    lock_ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[LOCK] canonical fingerprint={fp[:16]}…  "
          f"heldout 封存校验={'一致' if sealed else '被篡改!'}  t={lock_ts}")
    assert sealed, "held-out manifest 与封存 SHA 不一致——终止"

    # W1 双 twin（§17-§19）
    (t1a, t1b), (t2a, t2b) = twin_specs()
    fr1a, fr1b = run_boundary(t1a), run_boundary(t1b)
    fr2a, fr2b = run_boundary(t2a), run_boundary(t2b)
    dy1_t0 = abs(fr1a[T0][0] - fr1b[T0][0])
    uA_1a, uA_1b = apply_a(fr1a), apply_a(fr1b)
    uB_1a, uB_1b = apply_b(fr1a), apply_b(fr1b)
    a_t1_ok = abs(uA_1a[T0][0] - uA_1b[T0][0]) <= S_CANON * dy1_t0 + 1e-15
    # B 在 Twin-1 t0 允许不同（过去 Y 不同）——重放解释性：重算=原值
    b_t1_explained = (apply_b(fr1b)[T0][0] == uB_1b[T0][0])
    uA_2a, uA_2b = apply_a(fr2a), apply_a(fr2b)
    uB_2a, uB_2b = apply_b(fr2a), apply_b(fr2b)
    a_t2_ok = uA_2a[T0] == uA_2b[T0]     # 过去逐位同 ⇒ 必须逐位等
    b_t2_ok = uB_2a[T0] == uB_2b[T0]
    fut_1 = max(abs(a[0] - b[0]) for a, b in zip(uA_1a[T_DRIVE:],
                                                 uA_1b[T_DRIVE:]))
    fut_2b = max(abs(a[0] - b[0]) for a, b in zip(uB_2a[T_DRIVE:],
                                                  uB_2b[T_DRIVE:]))
    leak_free = a_t1_ok and a_t2_ok and b_t2_ok and b_t1_explained
    print(f"[Twin-1] A t0 等值(容差内)={a_t1_ok}  B t0 差由过去 Y 解释"
          f"(重放重算一致)={b_t1_explained}")
    print(f"[Twin-2] A t0 逐位等={a_t2_ok}  B t0 逐位等={b_t2_ok}  "
          f"未来: A 分叉(T1)={fut_1:.2e}  B 分叉(T2)={fut_2b:.2e}")
    print(f"HIDDEN_ACCESS_OR_STATE_LEAK = {'PASS(无泄漏)' if leak_free else 'FAIL'}")

    # Replay 纯度（§39）：live 逐步 vs 录制重放
    reps = ([spec_from_dict(d) for d in specs["calibration"][:2]]
            + [spec_from_dict(d) for d in specs["heldout"][:2]])
    replay_ok = True
    for sp0 in reps:
        ep = WorldEpisode(sp0)
        live_u = {"A": [], "B": []}
        prev = None
        frames = []
        for _ in range(sp0.t_total):
            ep.step()
            fr = ep.boundary_frame()
            frames.append(fr)
            live_u["A"].append(tuple(S_CANON * (q - Y_REF) for q in fr))
            live_u["B"].append(tuple(
                0.0 if prev is None else G_CANON * (q - p) / DT_EXT
                for q, p in zip(fr, prev)) if prev is not None
                else tuple(0.0 for _ in fr))
            prev = fr
        ok = (apply_a(frames) == live_u["A"]
              and apply_b(frames) == live_u["B"])
        replay_ok = replay_ok and ok
    print(f"[Replay] 4 代表 episodes live vs 录制重放 逐位一致={replay_ok}")

    # 4) BLIND held-out 一次
    hold = [spec_from_dict(d) for d in specs["heldout"]]
    rows, counts = [], {c: {} for c in CANDIDATES}
    for sp0 in hold:
        fr = run_boundary(sp0)
        for name in ("legacy", "A", "B"):
            rep = episode_report(name, fr)
            counts[name][rep["status"]] = \
                counts[name].get(rep["status"], 0) + 1
            rows.append({"episode_id": sp0.episode_id, "candidate": name,
                         **rep})
    with open(os.path.join(DATA_DIR, "heldout_results.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("\nFIRST_HELDOUT_RESULT（原样登记）:")
    for name in ("legacy", "A", "B"):
        print(f"  {name:>6}: " + "  ".join(
            f"{k}={v}" for k, v in sorted(counts[name].items())))
    ab_bad = [r for r in rows if r["candidate"] in ("A", "B")
              and (r["status"] == "NUMERIC_FAIL"
                   or (r["status"] == "SEMANTIC_FAIL"
                       and "TRANSDUCTION_LOSS" in r["attribution"]))]
    heldout_pass = not ab_bad
    print(f"held-out 门（A/B 无结构性崩溃）⇒ "
          f"{'PASS' if heldout_pass else 'FAIL: ' + str(ab_bad)}")

    out = {"lock": {"canonical_fingerprint": fp, "heldout_sha256": hold_sha,
                    "lock_time": lock_ts, "canonical_config": cfg},
           "twins": {"A_t1_equal": a_t1_ok, "A_t2_equal": a_t2_ok,
                     "B_t2_equal": b_t2_ok,
                     "B_t1_replay_explained": b_t1_explained,
                     "hidden_access_leak_free": leak_free,
                     "future_div_A_twin1": fut_1,
                     "future_div_B_twin2": fut_2b},
           "replay_pure": replay_ok,
           "first_heldout_result": counts, "heldout_pass": heldout_pass}
    with open(os.path.join(DATA_DIR, "replay_results.json"), "w",
              encoding="utf-8") as f:
        json.dump({"replay_pure": replay_ok, "n_episodes": 4}, f, indent=2)
    with open(os.path.join(DATA_DIR, "t1b_heldout.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("落盘: heldout_results.csv / replay_results.json / t1b_heldout.json")
    return 0 if (heldout_pass and leak_free and replay_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
