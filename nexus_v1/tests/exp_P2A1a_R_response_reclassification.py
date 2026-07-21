"""
P2-A1a-R：修复后响应重分类（低端精扫 + 钳位转折附近精扫）

背景：评判(`document - 2026-07-21T133444.403.md`非阻塞一)指出，FIX-019
修复高输入静默后，`activation_L1 = min(200u, 10)`——u≥0.05 时 L1 输出
精确等于常数10，与 u=0.05 还是 5.0 无关。原报告把 `(0.0005,5.0)` 描述为
扩展后的 `u_work`，这个结论过强：只能说这段范围属于 `𝒜_resp`（能触发），
不能说全段都属于有效工作区间。

本实验产出三分类的精确边界数据：
  𝒜_resp = {u: 能够产生发生}
  𝒟_disc = {u: 输入变化仍能造成可区分输出}（预期 u<0.05）
  𝒮_cap  = {u: 受L1上限钳位而趋于等价}（预期 u>=0.05，与
           activation_L1=min(200u,10) 的解析转折点吻合）

方法：复用现有 `scan_input_envelope`/`InputEnvelopePoint`（P2-A1a-R 新增
的 `l1_activation_final` 字段直接提供 D_disc/S_cap 的判据），不新建
组件，只是两组针对性的精细网格：
  - 低端精扫：u∈[1e-5,1e-3]，寻找真实静默/启动边界（原网格下限0.0005
    已勉强触发，本轮向下探）。
  - 钳位转折精扫：u∈[0.02,0.08]，验证相邻档位间 l1_activation_final
    是否可区分——解析预测转折点精确在 u=0.05。
"""
import sys

sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.structural_address import AddressRegistry
from nexus_v1.generators import scan_input_envelope, wrap_base_generator
from nexus_v1.relations import FROZEN_THERMAL_SITES

DT = 0.001
STEPS = 5000
SITE_INDEX = FROZEN_THERMAL_SITES["t1_pair"]["a"]  # 28（冻结选点）

LOW_END_LEVELS = [1e-5, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4, 7e-4, 1e-3]
CLAMP_TRANSITION_LEVELS = [0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06, 0.07, 0.08]


def build_generator():
    circuit = VariantCircuit()
    registry = AddressRegistry()
    return wrap_base_generator(circuit, SITE_INDEX, registry, polarity="warm")


def print_table(points, title):
    print("=" * 90)
    print(f"  {title}")
    print("=" * 90)
    header = (f"{'u':>10} | {'n_occ':>6} | {'l_first':>8} | {'f_occ':>10} | "
              f"{'l1_activation_final':>20} | {'ends_active':>12}")
    print(header)
    print("-" * len(header))
    for p in points:
        l_first_str = f"{p.l_first}" if p.l_first is not None else "-"
        print(f"{p.u:>10.6f} | {p.n_occ:>6} | {l_first_str:>8} | {p.f_occ:>10.6f} | "
              f"{p.l1_activation_final:>20.6f} | {str(p.ends_active):>12}")
    print()


def run():
    print("#" * 90)
    print("  P2-A1a-R：修复后响应重分类")
    print("#" * 90)

    low_points = scan_input_envelope(build_generator, LOW_END_LEVELS, DT, STEPS)
    print_table(low_points, "低端精扫（寻找真实静默/启动边界，u∈[1e-5,1e-3]）")

    clamp_points = scan_input_envelope(build_generator, CLAMP_TRANSITION_LEVELS, DT, STEPS)
    print_table(clamp_points, "钳位转折精扫（u∈[0.02,0.08]）")

    # ── 边界分类 ──
    print("=" * 90)
    print("  三分类边界结论")
    print("=" * 90)

    # A_resp 下界：最低的产生过至少一次发生的档位。
    a_resp_candidates = [p.u for p in low_points if p.n_occ > 0]
    a_resp_lower = min(a_resp_candidates) if a_resp_candidates else None

    # D_disc / S_cap 边界：相邻档位间 l1_activation_final 是否可区分（差值>1e-6）。
    d_disc_upper = None
    s_cap_lower = None
    for i in range(len(clamp_points) - 1):
        p_cur, p_next = clamp_points[i], clamp_points[i + 1]
        discriminable = abs(p_next.l1_activation_final - p_cur.l1_activation_final) > 1e-6
        if discriminable:
            d_disc_upper = p_next.u
        elif s_cap_lower is None:
            s_cap_lower = p_cur.u

    print(f"  𝒜_resp 下界（低端精扫内最低触发档位）：{a_resp_lower}")
    print(f"  𝒟_disc 上界（相邻档位 l1_activation_final 仍可区分的最高档位）："
          f"{d_disc_upper}")
    print(f"  𝒮_cap 下界（l1_activation_final 恒定不再区分的最低档位）：{s_cap_lower}")
    print(f"  解析预测（activation_L1=min(200u,10)）：转折点应精确在 u=0.05")
    print("=" * 90)

    return low_points, clamp_points


if __name__ == "__main__":
    run()
