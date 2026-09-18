"""wt0_boundary_replay.py — Boundary Replay Test（WT0 §5）。

TYPE:INFRA（research/ 观测层；G0 只运行不修改——BaseGenerator/
OccurrenceClosure READ_ONLY 纪律，§21）

依据：外部《WT0 方案》§5：记录 Y_B(0:T)，完全移除 World 后把边界轨迹
重放给 D_i+G0，要求相同下游初态下输出逐位一致；不同 ⇒
HIDDEN_SIDE_CHANNEL = FAIL（禁止在 Replay PASS 前建设 World v2）。

## 实验设计（先冻结）

  配置 = exp_P2A1b_3 判据2 代表性预算：三点皮肤 TEST 档，node0@1.0
  驱动 900 步 + 撤去 3000 步（总 3900 步，预期 occurrence=1——闭合
  事件按标定数据出现在 ~1577 步附近，窗口必须覆盖到事件完成）；
  G0 = fresh_generator 模板（VariantCircuit + wrap_base_generator
  site=t1_pair.a, polarity=warm, theta_down=0.001, rearm=500）。

  Gate 0（自确定性基线，前置）：同配置 live 臂独立构造两次，比较逐步
  签名（q / u_i / collector pre_trace / ensemble pre_traces /
  l1.activation）与 occurrence 事件表，要求逐位一致（==，非近似）。
  不过 Gate 0 ⇒ 重放测试无意义，按检查表登记（PYTHONHASHSEED/bundle_id、
  共享 RNG、全局步数、更新顺序），**只登记不修母体**。

  Gate 1（live vs replay）：live 臂录制 q_skin(0:T)；replay 臂完全不
  构造 World（无 ThermalFieldGraph 对象），把录制序列喂给全新
  fresh_generator 的 tick_from_skin。比较同一组签名，要求逐位一致。

  判定：Gate0 PASS 且 Gate1 PASS ⇒ HIDDEN_SIDE_CHANNEL = PASS。

## 签名内容（每步）

  (q_skin, u_i, collector.pre_trace, tuple(ensemble pre_traces),
   l1.activation) + occurrence 事件字段字典列表（vars() 提取）。

输出：data/wt0_replay.json（含首个分歧步定位，若有）。
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
from tss.generators.skin_transduction import transduce  # noqa: E402
from tss.relations import FROZEN_THERMAL_SITES  # noqa: E402

DATA_DIR = os.path.join(_HERE, 'data')
DT = 0.001
SITE_INDEX = FROZEN_THERMAL_SITES["t1_pair"]["a"]
CFG = REFERENCE_TRANSDUCTION_CONFIG
T_DRIVE, T_DECAY = 900, 3000
DRIVE_NODE, DRIVE_AMP = 0, 1.0


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


def drive_generator(handle, q_source):
    """把 q 序列（迭代器）喂给生成元，返回 (逐步签名, 事件表)。"""
    sig, events = [], []
    for t, q in enumerate(q_source):
        u = transduce(q, CFG)  # 与 feed_from_skin 内部同一纯函数，仅记录用
        ev = handle.tick_from_skin(q, CFG, DT, t)
        sig.append((q, u, handle.collector.pre_trace,
                    tuple(n.pre_trace for n in handle.ensemble),
                    handle.l1.activation))
        if ev is not None:
            events.append({"t": t, **ev_dict(ev)})
    return sig, events


def live_q_trace():
    """live 臂的世界侧：三点皮肤自主演化产生 q_skin(0:T)。"""
    g = build_three_point_skin(kappa=TEST_KAPPA_THREE_POINT,
                               r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)
    qs = []
    for t in range(T_DRIVE + T_DECAY):
        g.step(dt=1.0, external_injections=(
            {DRIVE_NODE: DRIVE_AMP} if t < T_DRIVE else {}))
        qs.append(g.cells[DRIVE_NODE].temperature)
    return qs


def live_run():
    """live 臂：World 与 G0 在同一循环中交替步进。"""
    g = build_three_point_skin(kappa=TEST_KAPPA_THREE_POINT,
                               r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)
    handle = fresh_generator()
    sig, events, qs = [], [], []
    for t in range(T_DRIVE + T_DECAY):
        g.step(dt=1.0, external_injections=(
            {DRIVE_NODE: DRIVE_AMP} if t < T_DRIVE else {}))
        q = g.cells[DRIVE_NODE].temperature
        qs.append(q)
        u = transduce(q, CFG)
        ev = handle.tick_from_skin(q, CFG, DT, t)
        sig.append((q, u, handle.collector.pre_trace,
                    tuple(n.pre_trace for n in handle.ensemble),
                    handle.l1.activation))
        if ev is not None:
            events.append({"t": t, **ev_dict(ev)})
    return sig, events, qs


def first_divergence(sig_a, sig_b):
    for t, (a, b) in enumerate(zip(sig_a, sig_b)):
        if a != b:
            return t, a, b
    return None


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 68)
    print("WT0 §5 — Boundary Replay Test（Gate0 自确定性 + Gate1 live/replay）")
    print("=" * 68)

    print("\n[Gate 0] live 臂 ×2 独立构造…")
    sig1, ev1, qs1 = live_run()
    sig2, ev2, qs2 = live_run()
    div0 = first_divergence(sig1, sig2)
    g0 = div0 is None and ev1 == ev2 and qs1 == qs2
    print(f"  签名逐位一致={div0 is None}  事件表一致={ev1 == ev2}  "
          f"q轨迹一致={qs1 == qs2}  ⇒ Gate0 {'PASS' if g0 else 'FAIL'}")
    if div0 is not None:
        print(f"  首个分歧步 t={div0[0]}:\n    run1={div0[1]}\n    run2={div0[2]}")

    g1 = None
    div1 = None
    if g0:
        print("\n[Gate 1] live vs replay（replay 臂零 World 对象）…")
        sig_r, ev_r = drive_generator(fresh_generator(), qs1)
        div1 = first_divergence(sig1, sig_r)
        g1 = div1 is None and ev1 == ev_r
        print(f"  签名逐位一致={div1 is None}  事件表一致={ev1 == ev_r}  "
              f"⇒ Gate1 {'PASS' if g1 else 'FAIL'}")
        if div1 is not None:
            print(f"  首个分歧步 t={div1[0]}:\n    live  ={div1[1]}\n    replay={div1[2]}")
    else:
        print("\n[Gate 1] 跳过（Gate 0 未过，重放比较无意义）")

    verdict = "PASS" if (g0 and g1) else "FAIL"
    print(f"\noccurrence 事件（live）：{ev1}")
    print(f"HIDDEN_SIDE_CHANNEL = {verdict}"
          + ("" if verdict == "PASS" else "（⇒ WT0_SIDE_CHANNEL_FAIL，先修接口）"))
    out = {"config": {"t_drive": T_DRIVE, "t_decay": T_DECAY,
                      "drive_node": DRIVE_NODE, "drive_amp": DRIVE_AMP,
                      "site_index": SITE_INDEX, "rearm_min_steps": 500},
           "gate0_pass": g0, "gate1_pass": g1,
           "gate0_first_divergence_step": None if div0 is None else div0[0],
           "gate1_first_divergence_step": None if div1 is None else div1[0],
           "occurrences_live": ev1, "hidden_side_channel": verdict}
    path = os.path.join(DATA_DIR, "wt0_replay.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"落盘: {path}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
