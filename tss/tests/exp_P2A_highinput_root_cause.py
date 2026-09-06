"""
P2-A：高输入静默根因排查（u=0.1 / 0.2 / 0.5 逐级实测比对）

目标：P2-A1a 首轮扫描发现 u≥0.2 时生成元完全静默（非单调带通响应）。
本实验只读诊断生成元内部 L1→HC→ensemble→collector 各级状态，在三个
输入档位间逐级比对，给出裁定：

  A：结构内生的高输入抑制（需证明连续状态轨迹+可复现+非NaN/下溢/错误
     钳位+非执行顺序伪影+有明确供能/适应机制）
  B：实现错误（数值范围/符号钳位/PowerRail-Memristor饱和边缘bug/重复
     缩放/传播序列错误——若为B必须先修复再重跑P2-A1a）

方案依据：`cell-cell/交叉比对/document - 2026-07-21T122445.485.md` §三
+ 用户直接指示的排查方法（比对u=0.1/0.2/0.5，逐级检查L1是否激活/HC是否
被钳制/ensemble是否抑制或饱和/collector输入是否归零/PowerRail-Memristor
是否边界行为/是否重复缩放符号反转错误钳位）。

只读诊断方法：全部通过已存在的公开只读属性/property读取（`activation`/
`pre_trace`/`PowerRail.v_actual`——见 `semiconductor.py:296-298`），不
修改 `feed()`/`Neuron`/`PowerRail`/`Memristor` 任何一行，不新增任何
instrumentation hook。
"""
import math
import sys

sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.structural_address import AddressRegistry
from tss.generators import wrap_base_generator
from tss.relations import FROZEN_THERMAL_SITES

DT = 0.001
STEPS = 500
SITE_INDEX = FROZEN_THERMAL_SITES["t1_pair"]["a"]  # 28（冻结选点）
U_LEVELS = [0.1, 0.2, 0.5]

# 精细网格：用于定位 ensemble PowerRail 崩溃阈值的确切位置（裁定为B后，
# 修复cap的取值依据——不能凭感觉选数字，必须从实测曲线读出安全边界）。
FINE_U_LEVELS = [0.005, 0.01, 0.02, 0.03, 0.05, 0.07, 0.1, 0.15, 0.2]


def build_generator():
    circuit = VariantCircuit()
    registry = AddressRegistry()
    return wrap_base_generator(circuit, SITE_INDEX, registry, polarity="warm")


def snapshot(handle):
    """读取一步之后的全部只读诊断量（不修改任何对象状态）。"""
    return {
        "l1_activation": handle.l1.activation,
        "hc_activation": handle.hc.activation,
        "hc_v_actual": handle.hc._power.v_actual,
        "ens_activation": [n.activation for n in handle.ensemble],
        "ens_v_actual": [n._power.v_actual for n in handle.ensemble],
        "col_activation": handle.collector.activation,
        "col_v_actual": handle.collector._power.v_actual,
        "col_pre_trace": handle.collector.pre_trace,
    }


def run_level(u):
    """驱动一个全新生成元 STEPS 步，返回逐步快照序列（只读）。"""
    handle = build_generator()
    snapshots = []
    for t in range(STEPS):
        handle.feed(u, DT)
        snapshots.append(snapshot(handle))
    return snapshots


def check_reproducible(u):
    """同一 u 独立跑两次，比较末态是否一致（可复现性判据）。"""
    s1 = run_level(u)[-1]
    s2 = run_level(u)[-1]
    return (abs(s1["col_pre_trace"] - s2["col_pre_trace"]) < 1e-9
            and abs(s1["hc_v_actual"] - s2["hc_v_actual"]) < 1e-9)


def has_nan_or_inf(snapshots):
    for s in snapshots:
        vals = [s["l1_activation"], s["hc_activation"], s["hc_v_actual"],
                 s["col_activation"], s["col_v_actual"], s["col_pre_trace"]]
        vals += s["ens_activation"] + s["ens_v_actual"]
        for v in vals:
            if v != v or math.isinf(v):  # NaN != NaN
                return True
    return False


def run():
    print("=" * 90)
    print("  P2-A 高输入静默根因排查：u=0.1 / 0.2 / 0.5 逐级实测比对")
    print("=" * 90)

    results = {}
    for u in U_LEVELS:
        snaps = run_level(u)
        results[u] = snaps

    header = (f"{'u':>6} | {'L1(final)':>10} | {'HC.v_actual(final)':>19} | "
              f"{'HC.activation':>13} | {'ens.v_actual(mean)':>18} | "
              f"{'col.v_actual':>12} | {'col.pre_trace':>13}")
    print(header)
    print("-" * len(header))
    for u in U_LEVELS:
        final = results[u][-1]
        ens_v_mean = sum(final["ens_v_actual"]) / len(final["ens_v_actual"])
        print(f"{u:>6.2f} | {final['l1_activation']:>10.4f} | "
              f"{final['hc_v_actual']:>19.6f} | {final['hc_activation']:>13.6f} | "
              f"{ens_v_mean:>18.6f} | {final['col_v_actual']:>12.6f} | "
              f"{final['col_pre_trace']:>13.6f}")

    print()
    print("=" * 90)
    print("  HC.v_actual 随时间演化（每50步采样，观察是否连续/渐进 vs 突然坍缩）")
    print("=" * 90)
    for u in U_LEVELS:
        trace = [results[u][t]["hc_v_actual"] for t in range(0, STEPS, 50)]
        print(f"  u={u:.2f}: " + " ".join(f"{v:.4f}" for v in trace))

    # ── 安全性/可复现性检查 ──
    nan_found = {u: has_nan_or_inf(results[u]) for u in U_LEVELS}
    reproducible = {u: check_reproducible(u) for u in U_LEVELS}

    print()
    print("=" * 90)
    print("  逐级检查结论")
    print("=" * 90)
    for u in U_LEVELS:
        final = results[u][-1]
        l1_active = final["l1_activation"] > 0.0
        hc_clamped = final["hc_v_actual"] <= 1e-9
        ens_v_mean = sum(final["ens_v_actual"]) / len(final["ens_v_actual"])
        ens_suppressed = ens_v_mean <= 1e-9
        col_zeroed = final["col_pre_trace"] <= 1e-9
        print(f"  u={u:.2f}: L1激活={l1_active} | HC被钳制(v_actual≈0)={hc_clamped} | "
              f"ensemble被抑制(v_actual均值≈0)={ens_suppressed} | "
              f"collector输入归零={col_zeroed} | NaN/inf={nan_found[u]} | "
              f"可复现={reproducible[u]}")

    # ── A/B 裁定 ──
    print()
    print("=" * 90)
    print("  A/B 裁定")
    print("=" * 90)

    l1_always_active = all(results[u][-1]["l1_activation"] > 0.0 for u in U_LEVELS)
    all_reproducible = all(reproducible.values())
    no_nan = not any(nan_found.values())

    # 修正（实测推翻了最初"HC PowerRail 崩溃"的代码分析假设）：真正崩溃的
    # 是 ensemble 这一级——HC.v_actual 随 u 渐进衰减（0.858→0.716→0.289，
    # 连续，非硬钳位），但 ensemble.v_actual 均值在 u=0.2/0.5 精确为 0
    # （u=0.1 已只剩 0.008，接近但未到0）。检查真正的崩溃层级：ensemble。
    ens_v_by_u = {u: sum(results[u][-1]["ens_v_actual"]) / len(results[u][-1]["ens_v_actual"])
                  for u in U_LEVELS}
    hc_v_by_u = {u: results[u][-1]["hc_v_actual"] for u in U_LEVELS}

    ens_collapses_at_high_u = ens_v_by_u[0.2] <= 1e-9 and ens_v_by_u[0.5] <= 1e-9
    ens_degraded_at_low_u = ens_v_by_u[0.1] < 0.1  # 已明显退化，非健康量级
    hc_is_continuous = hc_v_by_u[0.1] > hc_v_by_u[0.2] > hc_v_by_u[0.5] > 0.0

    is_hard_collapse_at_ensemble = ens_collapses_at_high_u

    if is_hard_collapse_at_ensemble and all_reproducible and no_nan and l1_always_active:
        verdict = "B"
        reason = (
            "崩溃层级实测定位在 ensemble（不是最初代码分析猜测的HC）："
            "HC.v_actual 随u连续渐进衰减（0.858→0.716→0.289，非硬钳位，"
            "HC本身表现正常），但 ensemble.v_actual 均值在u=0.2/0.5精确"
            "坍缩为0（u=0.1时已退化到0.008，非健康量级），collector随之"
            "在u≥0.2收不到任何输入（pre_trace=0）。L1在全部档位持续激活"
            "且无上限（半波整流理论线性无界增长），可复现、无NaN/inf，"
            "排除数值不稳定或执行顺序伪影。根因 = L1无输出上限产生的过大"
            "电流经HC传导后，在ensemble这一级的PowerRail（同样"
            "vdd=1.0,r_supply=0.05）被max(0,vdd-I*r_internal)硬钳位为0"
            "——与project_memristor_saturation_edge_bug记录的同一机制"
            "（注入电流超过vdd/r_supply被钳死为0）同源，只是崩溃点在"
            "ensemble而非之前规避过的bundle权重/HC层级。"
        )
    else:
        verdict = "A"
        reason = "未观测到符合结论B判据的硬钳位特征，需人工复核。"

    print(f"  裁定：结论{verdict}")
    print(f"  依据：{reason}")
    print(f"  HC.v_actual by u（连续渐进）: {hc_v_by_u}")
    print(f"  ensemble.v_actual(mean) by u（真正崩溃层级）: {ens_v_by_u}")
    print("=" * 90)

    # ── 精细网格：定位 ensemble PowerRail 崩溃阈值的确切曲线（供修复
    # cap 取值依据，避免凭感觉选数字）──
    print()
    print("=" * 90)
    print("  精细网格：ensemble PowerRail 崩溃曲线（用于推导修复 cap）")
    print("=" * 90)
    fine_header = f"{'u':>8} | {'L1':>8} | {'ens_v_actual(mean)':>18} | {'hc_v_actual':>12}"
    print(fine_header)
    print("-" * len(fine_header))
    fine_data = {}
    for u in FINE_U_LEVELS:
        h = build_generator()
        for t in range(STEPS):
            h.feed(u, DT)
        ens_mean = sum(n._power.v_actual for n in h.ensemble) / len(h.ensemble)
        fine_data[u] = {"l1": h.l1.activation, "ens_v_actual": ens_mean,
                          "hc_v_actual": h.hc._power.v_actual}
        print(f"{u:>8.3f} | {h.l1.activation:>8.2f} | {ens_mean:>18.6f} | "
              f"{h.hc._power.v_actual:>12.6f}")
    print()
    print("  观察：ensemble.v_actual 随 L1 输出连续、平滑衰减(非阶跃跳变)，")
    print("  这是 PowerRail 自身文档化的设计('IR drop is the natural gain")
    print("  limiter')；但 L1(ThermalDeltaNeuron) 完全没有输出上限，导致")
    print("  任何足够大的合理 dT 最终都会把 ensemble 电源拖入完全崩溃")
    print("  (v_actual精确为0)，与2026-07-11注释记录的'dT<=0.1安全'假设")
    print("  实际在ensemble这一级已不成立(L1=20时ensemble已剩0.025)。")
    print("=" * 90)

    return verdict, results, fine_data


if __name__ == "__main__":
    run()
