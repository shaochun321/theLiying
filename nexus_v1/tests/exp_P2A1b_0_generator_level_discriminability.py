"""
P2-A1b-0：生成元级可区分度测量（𝒟_disc^G vs 𝒟_disc^L1）

背景：评判(`document - 2026-07-21T140903.110.md`非阻塞一)指出
P2-A1a-R报告的`𝒟_disc=u<0.05`只是L1自己的输出可区分区（`l1_activation_
final=min(200u,10)`的解析推论，不需要实测就该知道），从未验证HC→
ensemble→collector→闭合状态机这条链条是否也保留了这个可区分性——下游
可能因非线性响应（如10个ensemble神经元的bc_current阶梯偏置）再次压缩
差异。

本实验复用现有 `wrap_base_generator(..., record_trajectory=True)` +
`GeneratorTrajectory`（不新建组件），对P2-A1a-R已用的钳位转折精细网格
`u∈[0.02,0.08]`逐档记录完整`R_G(u)=(L_first,f_occ,mean_t_active,
ensemble逐步激活向量)`，验证相邻档位间生成元整体是否仍可区分，产出真正
的`𝒟_disc^G`边界（可能与`𝒟_disc^L1=u<0.05`不同，本实验不预设结论）。

固定`PYTHONHASHSEED`保证跨u档位可比（否则Memristor±25%扰动的逐进程
随机性会混淆"u的真实效应"与"进程间噪声"两种来源的差异）。
"""
import os
import sys

# 固定随机性以保证跨u档位可比——同一进程内所有u共享同一次hash()随机化，
# 但为了让这份实验本身也可复现（供未来重跑核对），显式设置。
if os.environ.get("PYTHONHASHSEED") != "0":
    os.execvpe(sys.executable, [sys.executable] + sys.argv,
               {**os.environ, "PYTHONHASHSEED": "0"})

sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.structural_address import AddressRegistry
from nexus_v1.generators import wrap_base_generator
from nexus_v1.relations import FROZEN_THERMAL_SITES

DT = 0.001
STEPS = 5000
SITE_INDEX = FROZEN_THERMAL_SITES["t1_pair"]["a"]

# 与 P2-A1a-R 钳位转折精扫相同的网格，便于直接对照。
U_LEVELS = [0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06, 0.07, 0.08]


def build_generator():
    circuit = VariantCircuit()
    registry = AddressRegistry()
    return wrap_base_generator(
        circuit, SITE_INDEX, registry, polarity="warm", record_trajectory=True)


def run_level(u):
    handle = build_generator()
    for t in range(STEPS):
        handle.tick(u, DT, t)

    events = handle.closure.events
    n_occ = len(events)
    l_first = events[0].t_up if events else None
    mean_t_active = (sum(e.t_down - e.t_up for e in events) / n_occ) if n_occ else None
    f_occ = n_occ / STEPS

    # 生成元级可区分度证据：10个ensemble神经元pre_trace在整个观测窗内的
    # 峰值向量（不是末态快照——发生次数少(2~7次)且集中在窗口早期，末态
    # 早已衰减回静息，只采样末态会得到全零的假阴性；复用本项目已建立的
    # "峰值而非终态"方法论，同`relations/probes.py`的`PeakDecayRestProbe.
    # peak`、`input_envelope.py`的`peak_pre_trace`）。
    n_ensemble = len(handle.ensemble)
    peak_ensemble_pre_trace = [0.0] * n_ensemble
    for rec in handle.trajectory.records:
        for i, v in enumerate(rec.ensemble_pre_trace):
            if v > peak_ensemble_pre_trace[i]:
                peak_ensemble_pre_trace[i] = v
    peak_ensemble_pre_trace = tuple(peak_ensemble_pre_trace)

    return {
        "u": u, "n_occ": n_occ, "l_first": l_first, "f_occ": f_occ,
        "mean_t_active": mean_t_active,
        "l1_activation_final": handle.l1.activation,
        "ensemble_pre_trace_peak": peak_ensemble_pre_trace,
    }


def vector_distinguishable(v1, v2, tol=1e-6):
    return any(abs(a - b) >= tol for a, b in zip(v1, v2))


def run():
    print("=" * 100)
    print("  P2-A1b-0：生成元级可区分度测量 R_G(u)（PYTHONHASHSEED=0 固定）")
    print("=" * 100)

    results = [run_level(u) for u in U_LEVELS]

    header = (f"{'u':>8} | {'n_occ':>6} | {'l_first':>8} | {'f_occ':>10} | "
              f"{'mean_t_active':>14} | {'l1_act_final':>13}")
    print(header)
    print("-" * len(header))
    for r in results:
        l_first_str = f"{r['l_first']}" if r['l_first'] is not None else "-"
        mta_str = f"{r['mean_t_active']:.2f}" if r['mean_t_active'] is not None else "-"
        print(f"{r['u']:>8.3f} | {r['n_occ']:>6} | {l_first_str:>8} | {r['f_occ']:>10.6f} | "
              f"{mta_str:>14} | {r['l1_activation_final']:>13.4f}")

    print()
    print("  ensemble_pre_trace 向量（整个观测窗内10个神经元各自的峰值）：")
    for r in results:
        vec_str = ",".join(f"{v:.4f}" for v in r["ensemble_pre_trace_peak"])
        print(f"    u={r['u']:.3f}: [{vec_str}]")

    # ── 生成元级可区分度判定：相邻档位的 (l_first,f_occ,mean_t_active,
    #    ensemble_pre_trace向量) 组合是否可区分，而不只看l1_activation_final ──
    print()
    print("=" * 100)
    print("  相邻档位生成元级可区分度判定")
    print("=" * 100)
    d_disc_g_upper = None
    for i in range(len(results) - 1):
        r_cur, r_next = results[i], results[i + 1]
        l1_diff = abs(r_next["l1_activation_final"] - r_cur["l1_activation_final"]) > 1e-6
        ensemble_diff = vector_distinguishable(
            r_cur["ensemble_pre_trace_peak"], r_next["ensemble_pre_trace_peak"])
        scalar_diff = (r_cur["n_occ"] != r_next["n_occ"]
                       or r_cur["l_first"] != r_next["l_first"]
                       or abs(r_cur["f_occ"] - r_next["f_occ"]) > 1e-9)
        generator_discriminable = ensemble_diff or scalar_diff
        print(f"  u={r_cur['u']:.3f}→{r_next['u']:.3f}: L1可区分={l1_diff}, "
              f"ensemble向量可区分={ensemble_diff}, 标量指标可区分={scalar_diff}, "
              f"生成元整体可区分={generator_discriminable}")
        if generator_discriminable:
            d_disc_g_upper = r_next["u"]

    print()
    print(f"  𝒟_disc^L1 上界（解析预测）：u<0.05")
    print(f"  𝒟_disc^G 上界（本轮实测，相邻档位生成元整体仍可区分的最高u）：{d_disc_g_upper}")
    print("=" * 100)

    return results


if __name__ == "__main__":
    run()
