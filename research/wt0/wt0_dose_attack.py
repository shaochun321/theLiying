"""wt0_dose_attack.py — 外部剂量攻击仓内复现（WT0 §7，裁定 R-4）。

TYPE:INFRA（research/ 观测层；G0 只运行不修改，§21 READ_ONLY 纪律）

依据：外部《WT0 方案》§7 声称（未附脚本，R-4 裁定：仓内复现吻合后方可
冻结 W0_E_TRANSDUCTION_BOTTLENECK=CONFIRMED）：

  drive 0.01–0.50 → q_max ≈ 0.76–37.96 → u≡0 → occurrence=0
  drive 1.25 → q_max ≈ 94.91；drive 50 → q_max ≈ 3796.27
  强输入均大量进入 u=0.04；G0 各只 1 次 occurrence，duration≈390 步

## 协议（先冻结；外部未给时长，按 q_max/amp≈75.93 反推为近稳态持续驱动）

  三点皮肤 TEST 档；node0 持续恒流 amp，t∈[0,2000)；撤去观测 2000 步；
  G0 = exp_P2A1b_3 fresh_generator 模板（rearm=500 标定值）；
  amp ∈ {0.01, 0.1, 0.25, 0.5, 1.25, 5, 50}。

## 记录（每 amp）

  q_max；u 占用率（floor u_lin≤0 / ceiling u_lin≥0.04 / interior
  [0.005,0.03]，驱动窗内）；occurrence 次数/起止/duration 字段。

已知背景（解释计数用，非本轮修改对象）：collector 撤源后存在 ~600-700
步自持振荡（exp_P2A1b_3 已登记）；rearm=500 是在代表性预算内把伪发生
收敛为 1 次的标定值。

输出：data/wt0_dose_attack.json
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..')))

from nexus_v1.circuit.variant_adapter import VariantCircuit  # noqa: E402
from nexus_v1.components.structural_address import AddressRegistry  # noqa: E402
from nexus_v1.components.skin_three_point import (  # noqa: E402
    TEST_KAPPA_THREE_POINT, TEST_R_LEAK_AMBIENT_THREE_POINT,
    build_three_point_skin)
from tss.generators import (  # noqa: E402
    wrap_base_generator, REFERENCE_TRANSDUCTION_CONFIG)
from tss.relations import FROZEN_THERMAL_SITES  # noqa: E402

DATA_DIR = os.path.join(_HERE, 'data')
DT = 0.001
SITE_INDEX = FROZEN_THERMAL_SITES["t1_pair"]["a"]
CFG = REFERENCE_TRANSDUCTION_CONFIG
T_DRIVE, T_DECAY = 2000, 2000
AMPS = [0.01, 0.1, 0.25, 0.5, 1.25, 5.0, 50.0]
U_INTERIOR = (0.005, 0.03)

EXTERNAL_CLAIMS = {  # WT0 §7 原文数值（q_max）
    0.01: 0.76, 0.5: 37.96, 1.25: 94.91, 50.0: 3796.27}


def fresh_generator():
    circuit = VariantCircuit()
    registry = AddressRegistry()
    handle = wrap_base_generator(circuit, SITE_INDEX, registry,
                                 polarity="warm", theta_down=0.001)
    handle.closure.rearm_min_steps = 500
    return handle


def ev_dict(ev):
    return {k: v for k, v in vars(ev).items()
            if isinstance(v, (int, float, str, bool, type(None)))}


def run_amp(amp: float):
    g = build_three_point_skin(kappa=TEST_KAPPA_THREE_POINT,
                               r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)
    handle = fresh_generator()
    q_max = 0.0
    floor = ceil_ = interior = 0
    events = []
    for t in range(T_DRIVE + T_DECAY):
        g.step(dt=1.0, external_injections=(
            {0: amp} if t < T_DRIVE else {}))
        q = g.cells[0].temperature
        q_max = max(q_max, q)
        if t < T_DRIVE:  # 占用率只统计驱动窗
            u_lin = CFG.kappa_i * (q - CFG.q_i0) + CFG.b_i
            if u_lin <= CFG.u_clip_min:
                floor += 1
            elif u_lin >= CFG.u_clip_max:
                ceil_ += 1
            u = max(CFG.u_clip_min, min(CFG.u_clip_max, u_lin))
            if U_INTERIOR[0] <= u <= U_INTERIOR[1]:
                interior += 1
        ev = handle.tick_from_skin(q, CFG, DT, t)
        if ev is not None:
            events.append({"t": t, **ev_dict(ev)})
    return {"amp": amp, "q_max": q_max,
            "floor_frac": floor / T_DRIVE, "ceil_frac": ceil_ / T_DRIVE,
            "interior_frac": interior / T_DRIVE,
            "n_occurrence": len(events), "events": events}


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 78)
    print("WT0 §7 — 剂量攻击仓内复现（R-4）：amp 扫描 × G0 occurrence")
    print("=" * 78)
    rows = []
    for amp in AMPS:
        r = run_amp(amp)
        rows.append(r)
        ext = EXTERNAL_CLAIMS.get(amp)
        ext_s = f" | 外部声称 q_max≈{ext}" if ext is not None else ""
        print(f"amp={amp:>6g}: q_max={r['q_max']:>9.2f}  "
              f"fl/ce/int={r['floor_frac']:.3f}/{r['ceil_frac']:.3f}/"
              f"{r['interior_frac']:.3f}  occ={r['n_occurrence']}{ext_s}")
        for e in r["events"]:
            print(f"          event@t={e['t']}: "
                  + ", ".join(f"{k}={v}" for k, v in e.items() if k != 't'))
    # 线性自洽：q_max/amp 恒定性
    ratios = [r["q_max"] / r["amp"] for r in rows]
    lin_dev = (max(ratios) - min(ratios)) / max(ratios)
    print(f"\n线性自洽 q_max/amp: {ratios[0]:.4f}~{ratios[-1]:.4f} "
          f"max_rel_dev={lin_dev:.3e}")
    # 与外部数值比对
    cmp = {}
    for amp, ext in EXTERNAL_CLAIMS.items():
        mine = next(r["q_max"] for r in rows if r["amp"] == amp)
        cmp[str(amp)] = {"external": ext, "measured": mine,
                         "rel_diff": abs(mine - ext) / ext}
    out = {"protocol": {"t_drive": T_DRIVE, "t_decay": T_DECAY,
                        "drive_node": 0, "site_index": SITE_INDEX,
                        "rearm_min_steps": 500, "amps": AMPS},
           "rows": rows, "qmax_per_amp_lin_dev": lin_dev,
           "external_comparison": cmp}
    path = os.path.join(DATA_DIR, "wt0_dose_attack.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"落盘: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
