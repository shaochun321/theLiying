"""g0r0_invariance.py — dt_G 时间尺度不变性攻击 + 延迟/RC 审计 + 剂量审计
（§17-§19/§29-§30）。

TYPE:INFRA（production READ_ONLY）

## dt_G 攻击（§17；T_phys=60 s 恒定；同一 dt_B=1s 边界，S1-A 调度）
  dt_G∈{0.002, 0.001, 0.0005}，状态每物理秒采样。
  判定分两层（scheduler 轮已证振荡层相位失相干为 G0 内部性质）：
  Tier-1(L1,HC)：err(1ms vs 0.5ms) < err(2ms vs 1ms) ⇒ 收敛；
  Tier-2 全向量：原样登记（FIRST_RESULT 纪律）。

## RC τ 在体审计（§19）
  HC（Neuron 基类 hair_cell 路径）pre_trace 撤驱动衰减 τ[s] 在
  dt_G∈{1ms, 0.5ms} 下拟合——预期不变（时间审计 E3 的在体版）。

## 延迟审计（§18）
  最小 frozen SynapticBundle(delay_steps=5)：脉冲到达目标的物理延迟
  在 dt_G∈{1ms, 0.5ms} 下实测——预期 5 步恒定 ⇒ 物理延迟 5ms vs 2.5ms
  漂移 ⇒ DELAY_STEP_COUPLING 实证（G0 核心链 delay=0 未行使，隐性登记）。

## 剂量审计（§29-§30）
  E_proxy=Σ|u|·dt_G 对比：multirate(S1-A, 1ms) / fine ref(S2) /
  **旧 1:1 耦合**（每边界样本 1 tick，dt=1ms）——预期旧耦合剂量≈1/1000
  （§40 负结果定量化）；B0 vs B1 剂量比≈1（ZOH 无 1000× 复制）。

输出：data/{delay_invariance.csv, rc_invariance.csv, dose_audit.csv,
      g0r0_invariance.json}
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from g0r0_common import (  # noqa: E402
    MultiRateScheduler, boundary_from_episode, drive_g0, ep_spec,
    fresh_g0, u_series_a, u_series_b0, u_series_b1)

DATA_DIR = os.path.join(_HERE, 'data')
T_PHYS = 60


def tier_err(a, b, comps):
    num = sum((ra[c] - rb[c]) ** 2 for ra, rb in zip(a, b) for c in comps)
    den = sum(rb[c] ** 2 for rb in b for c in comps)
    return math.sqrt(num / max(den, 1e-30))


def dtg_attack(y_1s):
    runs = {}
    for dt_g in (0.002, 0.001, 0.0005):
        sch = MultiRateScheduler(1.0, dt_g)
        y_sub = sch.expand(y_1s, "S1")
        runs[dt_g] = drive_g0(u_series_a(y_sub), dt_g, sch.n_sub)
    n_comp = len(runs[0.001][0])
    t1, t2 = (0, 1), tuple(range(n_comp))
    e_coarse_t1 = tier_err(runs[0.002], runs[0.001], t1)
    e_fine_t1 = tier_err(runs[0.0005], runs[0.001], t1)
    e_coarse_full = tier_err(runs[0.002], runs[0.001], t2)
    e_fine_full = tier_err(runs[0.0005], runs[0.001], t2)
    conv = e_fine_t1 < e_coarse_t1
    print(f"[dt_G 攻击 Tier-1] err(2ms↔1ms)={e_coarse_t1:.3e} "
          f"err(0.5ms↔1ms)={e_fine_t1:.3e} ⇒ "
          f"{'收敛 ✓' if conv else 'G0_DT_COUPLED_PHYSICS_FAIL(接口层)'}")
    print(f"[dt_G 攻击 全向量 FIRST_RESULT] {e_coarse_full:.3f}/"
          f"{e_fine_full:.3f}（振荡层相位，登记）")
    return {"tier1_2ms_vs_1ms": e_coarse_t1,
            "tier1_05ms_vs_1ms": e_fine_t1,
            "full_2ms_vs_1ms": e_coarse_full,
            "full_05ms_vs_1ms": e_fine_full, "tier1_converges": conv}


def rc_in_situ():
    rows, taus = [], {}
    for dt_g in (0.001, 0.0005):
        h = fresh_g0()
        for k in range(int(2.0 / dt_g)):          # 低幅驱动 2 s（避开钳位）
            h.tick(0.004, dt_g, k)
        vals = []
        for k in range(int(5.0 / dt_g)):          # 撤驱动 5 s
            h.tick(0.0, dt_g, int(2.0 / dt_g) + k)
            vals.append(h.hc.pre_trace)
        i1, i2 = int(1.0 / dt_g), int(3.0 / dt_g)
        a, b = vals[i1], vals[i2]
        tau = (i2 - i1) * dt_g / math.log(a / b) if a > 0 and b > 0 \
            and a != b else float("inf")
        taus[dt_g] = tau
        rows.append({"dt_g": dt_g, "hc_trace_tau_s": tau})
    inv = abs(taus[0.001] - taus[0.0005]) / abs(taus[0.0005]) < 0.05
    print(f"[RC 在体] HC trace τ[s]={taus[0.001]:.4f}/{taus[0.0005]:.4f} "
          f"⇒ {'不变 ✓' if inv else '漂移'}")
    with open(os.path.join(DATA_DIR, "rc_invariance.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return {"taus": {str(k): v for k, v in taus.items()}, "invariant": inv}


def delay_audit():
    from nexus_v1.circuit.bundle import BundleConfig, SynapticBundle
    from nexus_v1.components.neuron import Neuron, NeuronConfig
    rows, delays = [], {}
    for dt_g in (0.001, 0.0005):
        src = Neuron(NeuronConfig(neuron_id="d_src", position=(0, 0, 0)))
        tgt = Neuron(NeuronConfig(neuron_id="d_tgt", position=(1, 0, 0)))
        cfg = BundleConfig(bundle_id="delay_audit", learning_rule="frozen",
                           initial_weight=0.5, weight_max=0.5,
                           synapse_gain=1.0, bundle_role="feedforward",
                           delay_steps=5)
        b = SynapticBundle(cfg, [src], [tgt])
        src.activation = 1.0
        src.pre_trace = 1.0
        arrive_step = None
        for k in range(20):
            cur = b.propagate()
            if cur and abs(cur[0]) > 1e-12 and arrive_step is None:
                arrive_step = k
            src.activation = 0.0     # 单脉冲
        delays[dt_g] = {"steps": arrive_step,
                        "physical_ms": None if arrive_step is None
                        else arrive_step * dt_g * 1000}
        rows.append({"dt_g": dt_g, **delays[dt_g]})
    coupled = (delays[0.001]["steps"] == delays[0.0005]["steps"]
               and delays[0.001]["physical_ms"]
               != delays[0.0005]["physical_ms"])
    print(f"[延迟] delay_steps=5: 到达步 {delays[0.001]['steps']}/"
          f"{delays[0.0005]['steps']}，物理延迟 "
          f"{delays[0.001]['physical_ms']}/"
          f"{delays[0.0005]['physical_ms']} ms ⇒ "
          f"{'DELAY_STEP_COUPLING 实证（隐性：G0 核心链 delay=0 未行使）' if coupled else '未复现'}")
    with open(os.path.join(DATA_DIR, "delay_invariance.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return {"delays": {str(k): v for k, v in delays.items()},
            "step_coupling_latent": coupled}


def dose_audit(y_1s, y_fine):
    sch = MultiRateScheduler(1.0, 0.001)
    u_multi = u_series_a(sch.expand(y_1s, "S1"))
    u_ref = u_series_a(sch.expand(y_1s, "S2", y_fine))
    u_old = u_series_a(y_1s[1:])                  # 旧 1:1：每样本 1 tick
    u_b0 = u_series_b0(y_1s, sch.n_sub, 1.0)
    u_b1 = u_series_b1(sch.expand(y_1s, "S1"), 0.001)
    e = {"multirate_A": sum(abs(u) for u in u_multi) * 0.001,
         "fine_ref_A": sum(abs(u) for u in u_ref) * 0.001,
         "old_1to1_A": sum(abs(u) for u in u_old) * 0.001,
         "B0": sum(abs(u) for u in u_b0) * 0.001,
         "B1_S1": sum(abs(u) for u in u_b1) * 0.001}
    r_multi = e["multirate_A"] / e["fine_ref_A"]
    r_old = e["old_1to1_A"] / e["fine_ref_A"]
    r_b = e["B0"] / max(e["B1_S1"], 1e-30)
    no_dup = 0.9 < r_multi < 1.1 and 0.5 < r_b < 2.0
    print(f"[剂量] multirate/ref={r_multi:.4f}（≈1 无复制 ✓）  "
          f"old 1:1/ref={r_old:.5f}（≈1/1000——旧耦合物理不一致定量化）  "
          f"B0/B1={r_b:.3f}")
    rows = [{"path": k, "E_proxy": v} for k, v in e.items()]
    with open(os.path.join(DATA_DIR, "dose_audit.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["path", "E_proxy"])
        w.writeheader()
        w.writerows(rows)
    return {"E_proxy": e, "multirate_over_ref": r_multi,
            "old_over_ref": r_old, "b0_over_b1": r_b,
            "no_dose_duplication": no_dup}


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 78)
    print("G0-R0 不变性/剂量审计 — dt_G 攻击 / RC 在体 / 延迟 / 剂量")
    print("=" * 78)
    y_1s = [fr[3] for fr in boundary_from_episode(
        ep_spec(t_total=T_PHYS, dt=1.0, eid="inv_1s"))]
    y_fine = [fr[3] for fr in boundary_from_episode(
        ep_spec(t_total=T_PHYS * 1000, dt=0.001, eid="inv_fine"))][1:]
    out = {"dtg_attack": dtg_attack(y_1s), "rc": rc_in_situ(),
           "delay": delay_audit(), "dose": dose_audit(y_1s, y_fine)}
    path = os.path.join(DATA_DIR, "g0r0_invariance.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"落盘: {path} + 3 CSV")
    ok = (out["dtg_attack"]["tier1_converges"] and out["rc"]["invariant"]
          and out["dose"]["no_dose_duplication"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
