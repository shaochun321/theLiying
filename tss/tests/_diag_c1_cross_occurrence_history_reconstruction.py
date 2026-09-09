"""_diag_c1_cross_occurrence_history_reconstruction — 跨 occurrence 历史可重构诊断（EXT-2 P1-5）。

TYPE:INFRA（diagnostic，不被 pytest 收集）

审计依据：《TSS C1 理论资格复审后的代码修改清单》P1-5（2026-09-09/10 外部
数值复审）。外部重复 relation-pair 实验发现：第二次相同 pair 的输出会因
上一 occurrence 的 level-2 H_τ 残留而增强；但整个效应仍可由**已有 H_τ
指数历史叠加**重构到约 5e-15。

## 两层重构（都必须成立）

  1. 父层同型栈重构（同 T-C1-6b 方法）：同类默认参数三件套喂相同二值
     事件时刻 → 第二次 c_ro 逐步等价（isclose 1e-12）
  2. 解析指数叠加：h(t) = Σ_k e^{-(t-t_k)·dt/τ}（history_kernel 文档承诺
     的纯叠加形式，Capacitor.leak 为精确指数）→ 第二次发放步的 h 与
     同型栈读出一致（rel_tol 1e-9，报告实测残差）

## 结论措辞纪律（清单原文，禁止改写）

  cross-occurrence history dependence EXISTS
  but
  independent organization state NOT ESTABLISHED

不得把历史增强写成"跨 occurrence 组织持续性"。

入口：PYTHONIOENCODING=utf-8 python -m tss.tests._diag_c1_cross_occurrence_history_reconstruction
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import math

from tss.tests.test_c1_coupling import (
    DT, _run_synthetic_recording, _reconstruct_from_binary_events,
)

# epoch gap 扫描（清单指定；1204 = ℰ↑ t_open，是 level-2 门重新开门的下界）
GAPS = (1204, 1300, 1500, 2000, 2500, 3000, 4000, 5000)
T_A, DT2 = 100, 50             # 每个 occurrence 内：A@t0, B@t0+50
TAU_STEPS = 600.0              # H_τ（history_kernel Q3，本诊断只读不改）


def main() -> int:
    print("=" * 68)
    print("EXT-2 P1-5: 跨 occurrence 历史可重构诊断")
    print("=" * 68)
    max_stack_residual, max_analytic_rel = 0.0, 0.0
    enhanced = []

    for gap in GAPS:
        n = T_A + gap + DT2 + 200
        r_a = {T_A, T_A + gap}
        r_b = {T_A + DT2, T_A + gap + DT2}
        spikes_x, spikes_y, actual = _run_synthetic_recording(r_a, r_b, n)
        fires = [t for t, c in enumerate(actual) if c > 0.0]

        # 1) 父层同型栈重构（逐步）
        recon = _reconstruct_from_binary_events(spikes_x, spikes_y, n)
        for t, (a, r) in enumerate(zip(actual, recon)):
            assert math.isclose(a, r, rel_tol=1e-12, abs_tol=1e-12), (
                f"gap={gap} step={t}: 同型栈重构失败 actual={a!r} recon={r!r}")
            max_stack_residual = max(max_stack_residual, abs(a - r))

        first_c = actual[T_A + DT2]
        second_t = T_A + gap + DT2
        second_c = actual[second_t]
        if second_c > 0.0 and first_c > 0.0:
            # 2) 解析指数叠加：第二次发放步的 h（充电时刻 = level-2 gate 放行
            #    的 b^↑ 步 = adapter spike 步；读出在充电前 → 只含更早的项）
            h_analytic = sum(
                math.exp(-(second_t - tk) * DT * 1000.0 / TAU_STEPS)
                for tk in spikes_x if tk < second_t)
            # c = conduct(h)·conduct(b)：second/first 之比 = 各自 h 的导通比。
            # 用比值消去 MOSFET 常数：h_first 解析 = e^{-Δt₂/τ}
            h_first = math.exp(-DT2 * DT * 1000.0 / TAU_STEPS)
            ratio_actual = second_c / first_c
            # conduct 阈上线性（gm·(V-θ) 或 gm·V——两种实现都用差分比对消）
            # 直接对比：同型栈重构已证等价，此处只验证 h 的解析可加性：
            # second_c/first_c 应等于以解析 h 喂入同一比较器的输出比。
            from tss.relations.theta_comparator import PhysicalThetaComparator
            from tss.tests.test_c1_coupling import _make_l1_address
            from nexus_v1.components.structural_address import AddressRegistry
            reg = AddressRegistry()
            comp = PhysicalThetaComparator(
                address_i=_make_l1_address(reg, 24),
                address_j=_make_l1_address(reg, 21))
            c_pred_second = comp.step(h_analytic, 1.0, DT)
            c_pred_first = comp.step(h_first, 1.0, DT)
            rel = abs(c_pred_second - second_c) / second_c
            max_analytic_rel = max(max_analytic_rel, rel)
            enhanced.append(gap)
            print(f"  gap={gap:5d}: first={first_c:.9f} second={second_c:.9f} "
                  f"(×{ratio_actual:.4f}) 解析h叠加残差 rel={rel:.3e}")
            assert second_c > first_c, (
                f"gap={gap}: 第二次输出未增强——与外部实测矛盾，须重查")
            assert rel < 1e-9, (
                f"gap={gap}: 解析 H_τ 叠加不能解释第二次输出 rel={rel:.3e}"
                "——可能出现独立状态变量，单独开启理论审查（不要修本诊断）")
        else:
            print(f"  gap={gap:5d}: 第二次未产生 (fires={fires})——"
                  f"ℰ↑ t_open 边界效应，登记为边界观察")

    print(f"\n  同型栈重构最大残差 = {max_stack_residual:.3e}（外部实测≈5e-15）")
    print(f"  解析 H_τ 叠加最大相对残差 = {max_analytic_rel:.3e}")
    print(f"  历史增强复现于 {len(enhanced)}/{len(GAPS)} 个 gap: {enhanced}")

    print("\n" + "=" * 68)
    print("结论（措辞冻结，清单原文）：")
    print("  cross-occurrence history dependence EXISTS")
    print("  but")
    print("  independent organization state NOT ESTABLISHED")
    print("=" * 68)
    print("exit 0 语义：历史增强已由既有 H_τ 指数叠加完全解释并登记；"
          "不构成\"跨 occurrence 组织持续性\"。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
