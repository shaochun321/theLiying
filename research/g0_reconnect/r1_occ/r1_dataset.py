"""r1_dataset.py — G0-R1 Step3：G0_cal / G0_hold 数据集构建与 SHA 封存。

TYPE:INFRA（research/ 层；production READ_ONLY）。

依据：外部《G0-R1/OCC 方案》§9（评判 E-8：hold 场景清单超出 T1-B hold20
覆盖，扩集必须重新 SHA 封存并保持 held-out 纪律）。封存协议沿
t1b_dataset.py 先例：hold 清单 JSON 的 SHA256 在任何 hold 评估之前
提交入库；hold 集不参与 closure/g 任何重标（§9 末句）。

## 八类场景（§9 清单，全部 World v2 冻结条件，确定性 seed=-1 无 RNG）

  K1 normal    普通 World（单源 20E@node0）
  K2 dissip    强耗散（r_leak_ambient 200→20）
  K3 multisrc  多 Source（node0 20E + node2 12E@t20）
  K4 boundary  不同 Boundary（REDUCED 边界节点 0→1；n_nodes 5→7 变体）
  K5 twin      hidden twin（源位置 node3 vs node4，边界读数近似——
               对应 W1-M6/G0-R0 twin 家族；Step4 hidden dynamics 复用）
  K6 weak      弱输入（能量 3E、功率 0.3）
  K7 sustain   持续输入（能量 60E 覆盖整个 episode）
  K8 adjacent  相邻多 occurrence（同节点两个脉冲 5E@t0 + 5E@t30）

cal：每类 2 变体 = 16 episodes（参数扰动变体，标定/重标专用）。
hold：每类 1-2 变体 = 12 episodes（独立参数点，封存后只在
final_qualification 冻结参数下评估一次，不回调）。

复现入口：
  PYTHONIOENCODING=utf-8 python research/g0_reconnect/r1_occ/r1_dataset.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import asdict

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', 'r0')))

from g0r0_common import ep_spec  # noqa: E402
from world_v2_core import SourceSpec, WorldEpisodeSpec  # noqa: E402

DATA = os.path.join(_HERE, 'data')
os.makedirs(DATA, exist_ok=True)

T_TOTAL = 60  # 60 个 1s 边界样本 = 60k generator 子步/episode


def _spec(eid, *, n=5, kappa=0.05, r_leak=200.0, sources=None,
          bnodes=(0,)) -> WorldEpisodeSpec:
    return WorldEpisodeSpec(
        episode_id=eid, seed=-1, n_nodes=n, kappas=(kappa,) * (n - 1),
        r_leak_ambient=r_leak, sources=tuple(sources),
        boundary_config="REDUCED", boundary_nodes=bnodes,
        dt=1.0, t_total=T_TOTAL)


def build_sets():
    S = SourceSpec
    cal = {
        # K1 normal ×2
        "cal_K1a": _spec("cal_K1a", sources=[S(0, 20.0, 1.0, 0)]),
        "cal_K1b": _spec("cal_K1b", kappa=0.03, sources=[S(0, 15.0, 1.0, 5)]),
        # K2 dissip ×2
        "cal_K2a": _spec("cal_K2a", r_leak=20.0, sources=[S(0, 20.0, 1.0, 0)]),
        "cal_K2b": _spec("cal_K2b", r_leak=50.0, sources=[S(0, 20.0, 1.0, 0)]),
        # K3 multisrc ×2
        "cal_K3a": _spec("cal_K3a", sources=[S(0, 20.0, 1.0, 0),
                                             S(2, 12.0, 1.0, 20)]),
        "cal_K3b": _spec("cal_K3b", sources=[S(0, 10.0, 1.0, 0),
                                             S(4, 10.0, 1.0, 10)]),
        # K4 boundary ×2
        "cal_K4a": _spec("cal_K4a", sources=[S(0, 20.0, 1.0, 0)], bnodes=(1,)),
        "cal_K4b": _spec("cal_K4b", n=7, sources=[S(0, 20.0, 1.0, 0)]),
        # K5 twin ×2（成对：源 node3 vs node4，边界 node0）
        "cal_K5a": _spec("cal_K5a", sources=[S(3, 16.0, 1.0, 0)]),
        "cal_K5b": _spec("cal_K5b", sources=[S(4, 16.0, 1.0, 0)]),
        # K6 weak ×2
        "cal_K6a": _spec("cal_K6a", sources=[S(0, 3.0, 0.3, 0)]),
        "cal_K6b": _spec("cal_K6b", sources=[S(0, 5.0, 0.5, 0)]),
        # K7 sustain ×2
        "cal_K7a": _spec("cal_K7a", sources=[S(0, 60.0, 1.0, 0)]),
        "cal_K7b": _spec("cal_K7b", sources=[S(0, 45.0, 0.8, 0)]),
        # K8 adjacent ×2（脉冲间隔 30s ≫ rearm 0.5s）
        "cal_K8a": _spec("cal_K8a", sources=[S(0, 5.0, 1.0, 0),
                                             S(0, 5.0, 1.0, 30)]),
        "cal_K8b": _spec("cal_K8b", sources=[S(0, 4.0, 1.0, 5),
                                             S(0, 6.0, 1.0, 35)]),
    }
    hold = {
        "hold_K1": _spec("hold_K1", kappa=0.04, sources=[S(0, 18.0, 1.0, 3)]),
        "hold_K2": _spec("hold_K2", r_leak=30.0, sources=[S(0, 22.0, 1.0, 0)]),
        "hold_K3": _spec("hold_K3", sources=[S(0, 14.0, 1.0, 0),
                                             S(3, 9.0, 1.0, 25)]),
        "hold_K4": _spec("hold_K4", n=6, sources=[S(0, 20.0, 1.0, 0)],
                         bnodes=(1,)),
        "hold_K5a": _spec("hold_K5a", sources=[S(3, 14.0, 1.0, 2)]),
        "hold_K5b": _spec("hold_K5b", sources=[S(4, 14.0, 1.0, 2)]),
        "hold_K6": _spec("hold_K6", sources=[S(0, 4.0, 0.4, 0)]),
        "hold_K7": _spec("hold_K7", sources=[S(0, 55.0, 0.9, 0)]),
        "hold_K8": _spec("hold_K8", sources=[S(0, 5.0, 1.0, 2),
                                             S(0, 5.0, 1.0, 32)]),
        "hold_K1s": _spec("hold_K1s", kappa=0.06,
                          sources=[S(0, 25.0, 1.0, 0)]),
        "hold_K2s": _spec("hold_K2s", r_leak=15.0,
                          sources=[S(0, 20.0, 1.0, 0)]),
        "hold_K8s": _spec("hold_K8s", sources=[S(0, 6.0, 1.0, 0),
                                               S(0, 4.0, 1.0, 28)]),
    }
    return cal, hold


def _dump(d):
    return {k: asdict(v) for k, v in sorted(d.items())}


def main() -> int:
    cal, hold = build_sets()
    cal_j = json.dumps(_dump(cal), indent=1, sort_keys=True)
    hold_j = json.dumps(_dump(hold), indent=1, sort_keys=True)
    with open(os.path.join(DATA, 'r1_cal_manifest.json'), 'w',
              newline='\n', encoding='utf-8') as f:
        f.write(cal_j)
    with open(os.path.join(DATA, 'r1_hold_manifest.json'), 'w',
              newline='\n', encoding='utf-8') as f:
        f.write(hold_j)
    sha = hashlib.sha256(hold_j.encode('utf-8')).hexdigest()
    with open(os.path.join(DATA, 'r1_hold_seal.json'), 'w',
              newline='\n', encoding='utf-8') as f:
        json.dump({"hold_manifest_sha256": sha,
                   "sealed": "2026-09-19",
                   "discipline": "hold set MUST NOT participate in any "
                                 "closure/g recalibration (§9/E-8); evaluated "
                                 "once with frozen params in "
                                 "final_qualification only"}, f, indent=1)
    print(f"cal episodes : {len(cal)} (8 classes ×2)")
    print(f"hold episodes: {len(hold)} (SHA256={sha[:16]}…) SEALED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
