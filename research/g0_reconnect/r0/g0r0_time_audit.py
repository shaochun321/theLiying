"""g0r0_time_audit.py — 生产代码时间语义普查（§3-§5/§14/§21）。

TYPE:INFRA（只读消费 production；§4 纪律：不靠变量名，用**行为实验**判定）

## 经验判定法（每项跑两档 dt、同一物理时长，测物理量是否不变）

  E1 Capacitor.leak    ：同 T_phys 下 dt∈{1e-3,5e-4} 衰减终值相等 ⇒ PHYSICAL
  E2 Capacitor.inject  ：恒流同 T_phys 总电荷相等 ⇒ PHYSICAL（无剂量复制）
  E3 Neuron 基类 trace ：恒定激活驱动后撤，pre_trace 衰减 τ[s] 拟合不随
                         dt 漂移 ⇒ PHYSICAL（exp(-dt/τ)+ms→s 换算）
  E4 ThermalDeltaNeuron trace：同法——预判 τ[s] 随 dt 减半而减半
                         （_TRACE_DECAY=0.99 每步）⇒ DISCRETE_COUNTER
  E5 SynapticBundle.delay_steps：代码级（bundle.py:46-49 int 步数常量）
                         ⇒ DISCRETE_COUNTER（G0 核心链 delay=0 未行使；
                         DA 路径 100-500 steps 为隐性耦合，登记）
  E6 DelayedBundle     ：代码级（bundle_v2.py:118 τ_steps=round(τ_ms/dt_ms)）
                         ⇒ PHYSICAL_TIME（dt-aware 正确先例）
  E7 OccurrenceClosure ：代码级（occurrence.py:135 t_up=step_index；
                         rearm_min_steps=500 步数）⇒ DISCRETE_COUNTER
                         （by design；§22 需 n→t_phys 映射，本轮不改）

## §14 终裁（预登记判据）：E1-E3 全 PHYSICAL ⇒ 状态 A
   （GENERATOR_DT = PHYSICAL_INTEGRATION_STEP = 0.001 s）+ 例外清单。

输出：data/time_semantics_census.csv, data/g0r0_time_audit.json
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..', '..')))

from nexus_v1.components.semiconductor import Capacitor  # noqa: E402
from nexus_v1.components.neuron import Neuron, NeuronConfig  # noqa: E402
from nexus_v1.somatosensory.transducer_neurons import (  # noqa: E402
    ThermalDeltaNeuron)

DATA_DIR = os.path.join(_HERE, 'data')
T_PHYS = 0.2   # 秒（远大于被测 τ 量级即可）


def e1_leak():
    res = {}
    for dt in (1e-3, 5e-4):
        c = Capacitor(capacitance=1.0)
        c.charge = 1.0
        for _ in range(int(T_PHYS / dt)):
            c.leak(0.05, dt)     # τ=0.05 s
        res[dt] = c.charge
    inv = abs(res[1e-3] - res[5e-4]) / res[5e-4] < 0.02
    return res, inv


def e2_inject():
    res = {}
    for dt in (1e-3, 5e-4):
        c = Capacitor(capacitance=1.0)
        for _ in range(int(T_PHYS / dt)):
            c.inject(1.0, dt)    # 恒流 1
        res[dt] = c.charge
    inv = abs(res[1e-3] - res[5e-4]) / res[5e-4] < 1e-9
    return res, inv


def fit_tau_seconds(vals, dt, i1, i2):
    a, b = vals[i1], vals[i2]
    if a <= 0 or b <= 0 or a == b:
        return float("inf")
    return (i2 - i1) * dt / math.log(a / b)


def e3_neuron_trace():
    """直接测 decay 路径：置 pre_trace=1.0 后零输入步进拟合 τ[s]
    （trace_tau_pre=20 ms ⇒ 预期 τ≈0.02 s 且两档 dt 不变）。"""
    res = {}
    for dt in (1e-3, 5e-4):
        n = Neuron(NeuronConfig(neuron_id="audit", position=(0, 0, 0)))
        n.pre_trace = 1.0
        vals = []
        for _ in range(int(0.06 / dt)):      # 观测 60 ms（3τ）
            n.step(0.0, dt)
            vals.append(n.pre_trace)
        res[dt] = fit_tau_seconds(vals, dt, int(0.005 / dt),
                                  int(0.03 / dt))
    inv = abs(res[1e-3] - res[5e-4]) / res[5e-4] < 0.05
    return res, inv


def e4_l1_trace():
    res = {}
    for dt in (1e-3, 5e-4):
        l1 = ThermalDeltaNeuron("audit")
        for _ in range(int(0.05 / dt)):
            l1.step(0.05, dt)
        vals = []
        for _ in range(int(0.3 / dt)):
            l1.step(0.0, dt)
            vals.append(l1.pre_trace)
        res[dt] = fit_tau_seconds(vals, dt, int(0.05 / dt), int(0.15 / dt))
    drift = res[5e-4] / res[1e-3]           # 预判 ≈0.5（每步衰减）
    coupled = abs(drift - 0.5) < 0.1
    return res, drift, coupled


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 78)
    print("G0-R0 时间语义普查（行为实验判定，§4 纪律）")
    print("=" * 78)
    r1, i1 = e1_leak()
    print(f"[E1 Capacitor.leak]   dt两档终值 {r1[1e-3]:.5f}/{r1[5e-4]:.5f} "
          f"⇒ {'PHYSICAL ✓' if i1 else 'DRIFT'}")
    r2, i2 = e2_inject()
    print(f"[E2 Capacitor.inject] 总电荷 {r2[1e-3]:.5f}/{r2[5e-4]:.5f} "
          f"⇒ {'PHYSICAL ✓（无剂量复制）' if i2 else 'DOSE_FAIL'}")
    r3, i3 = e3_neuron_trace()
    print(f"[E3 Neuron trace]     τ[s]={r3[1e-3]:.4f}/{r3[5e-4]:.4f} "
          f"⇒ {'PHYSICAL ✓' if i3 else 'DRIFT'}")
    r4, drift4, c4 = e4_l1_trace()
    print(f"[E4 L1 trace]         τ[s]={r4[1e-3]:.4f}/{r4[5e-4]:.4f} "
          f"(比={drift4:.3f}) ⇒ "
          f"{'DISCRETE_COUNTER（预判确认：τ 随 dt 漂移）' if c4 else '意外'}")

    census = [
        {"module": "World/Boundary (ThermalFieldGraph)", "dt": 1.0,
         "semantics": "PHYSICAL_TIME [s]", "evidence": "W1 dt 收敛+本轮 E1/E2 同族",
         "g0r0_action": "保留"},
        {"module": "Capacitor.inject/leak", "dt": "调用方", "semantics":
         "PHYSICAL_TIME", "evidence": "E1/E2 实验 + semiconductor.py:64/74",
         "g0r0_action": "保留（状态 A 基石）"},
        {"module": "Neuron 基类(膜RC/traces/适应)", "dt": 0.001,
         "semantics": "PHYSICAL_TIME [s]", "evidence":
         "E3 实验 + neuron.py:527/537/587-588(ms→s 显式换算)",
         "g0r0_action": "保留"},
        {"module": "ThermalDeltaNeuron.pre_trace", "dt": 0.001,
         "semantics": "DISCRETE_COUNTER", "evidence":
         "E4 实验(τ 比=%.3f) + _TRACE_DECAY=0.99 每步" % drift4,
         "g0r0_action": "登记 G0_DT_COUPLED_PHYSICS(定点)；修复属 G0-R1"},
        {"module": "SynapticBundle.delay_steps", "dt": "-", "semantics":
         "DISCRETE_COUNTER", "evidence": "bundle.py:46-49 int 步数常量"
         "(G0 核心链 delay=0 未行使；DA 路径 100-500 steps 隐性耦合)",
         "g0r0_action": "登记 DELAY_STEP_COUPLING(隐性)；修复属 G0-R1"},
        {"module": "DelayedBundle(bundle_v2)", "dt": "-", "semantics":
         "PHYSICAL_TIME", "evidence": "bundle_v2.py:118 "
         "τ_steps=round(τ_ms/dt_ms) dt-aware", "g0r0_action": "保留（正确先例）"},
        {"module": "SynapticBundle.da_ema β", "dt": "动态", "semantics":
         "PHYSICAL_TIME", "evidence": "bundle.py:125-127 β=dt/(dt+τ) 动态"
         "（Phase B P1 陷阱教训已制度化）", "g0r0_action": "保留"},
        {"module": "OccurrenceClosure(t_up/t_down/t_rearm/rearm=500)",
         "dt": "-", "semantics": "DISCRETE_COUNTER (by design)",
         "evidence": "occurrence.py:135 t_up=step_index；rearm 步数标定",
         "g0r0_action": "§22 n→t_phys 映射（G0-R1 实施）；本轮不改阈值(§20)"},
        {"module": "SkinPatch(体感)", "dt": 1.0, "semantics":
         "PHYSICAL_TIME [s]", "evidence": "world.py step_thermal RC+τ=5s "
         "约定；dT=每步差分未除 dt（T1-A D2 已登记，速率语义靠 dt 恒定）",
         "g0r0_action": "保留+登记 dT 未归一约束"},
    ]
    with open(os.path.join(DATA_DIR, "time_semantics_census.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(census[0].keys()))
        w.writeheader()
        w.writerows(census)

    state_a = i1 and i2 and i3
    exceptions = ["ThermalDeltaNeuron.pre_trace",
                  "SynapticBundle.delay_steps(隐性)",
                  "OccurrenceClosure counters(by design,需映射)"]
    print(f"\n§14 终裁: {'状态 A — GENERATOR_DT=PHYSICAL_INTEGRATION_STEP'
          '=0.001 s' if state_a else '状态冲突'}")
    print(f"例外清单（定点登记，修复属 G0-R1）: {exceptions}")
    out = {"E1_leak": {"vals": {str(k): v for k, v in r1.items()},
                       "physical": i1},
           "E2_inject": {"vals": {str(k): v for k, v in r2.items()},
                         "physical": i2},
           "E3_neuron_trace_tau_s": {str(k): v for k, v in r3.items()},
           "E3_physical": i3,
           "E4_l1_trace_tau_s": {str(k): v for k, v in r4.items()},
           "E4_drift_ratio": drift4, "E4_discrete_counter": c4,
           "ruling": "STATE_A" if state_a else "STATE_CONFLICT",
           "exceptions": exceptions}
    with open(os.path.join(DATA_DIR, "g0r0_time_audit.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("落盘: time_semantics_census.csv / g0r0_time_audit.json")
    return 0 if state_a else 1


if __name__ == "__main__":
    sys.exit(main())
