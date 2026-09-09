"""_diag_c1_parent_amplitude_information_loss — 关系幅度信息损失诊断（EXT-2 P1-4）。

TYPE:INFRA（diagnostic，不被 pytest 收集，**只诊断不判 bug**）

审计依据：《TSS C1 理论资格复审后的代码修改清单》P1-4（2026-09-09/10 外部
数值复审）。外部实测：固定 Δt₂=50，两条父 relation current 从 0.002~0.36
大幅改变，只要两边都超过 adapter 发放阈值，最终 c_ro 完全相同
（49 个有效组合实测均为 0.4340310902405273）。

## 说明

当前 graded relation current → binary relation event 的二值化会**主动删除
父关系幅度信息**：level-2 消费的是"关系是否发生 + 发生时间"，而不是完整
父关系幅度。这是设计现状的定量登记，不是 bug（清单硬禁 8：不修改
RelationEventAdapter 阈值来保留 amplitude）。

## 记录三件事（清单要求）

  1. adapter threshold（发放阈值实测二分）
  2. above-threshold amplitude equivalence（越阈幅度等价）
  3. fixed Δt₂ output equality（固定 Δt₂ 输出全等）

入口：PYTHONIOENCODING=utf-8 python -m tss.tests._diag_c1_parent_amplitude_information_loss
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tss.tests.test_c1_coupling import DT, _synthetic_stack

DT2 = 50                       # 固定 Δt₂（清单指定）
T_A = 100
# 扫描幅度：覆盖 EXP-C0-02 实测域 [0.0026, 0.3660]（清单：0.002~0.36）
AMPLITUDES = (0.002, 0.005, 0.01, 0.05, 0.1, 0.2, 0.36)


def _adapter_fires_at(amp: float) -> bool:
    """单脉冲幅度 amp 是否触发 adapter 发放（独立栈，无历史污染）。"""
    ad_x, _, _ = _synthetic_stack()
    fired = False
    for t in range(20):
        s = ad_x.step(amp if t == 5 else 0.0, DT)
        fired = fired or s > 0.5
    return fired


def main() -> int:
    print("=" * 68)
    print("EXT-2 P1-4: relation amplitude 信息损失诊断（固定 Δt₂=50）")
    print("=" * 68)

    # ── 1. adapter 发放阈值实测（二分 20 轮）──
    lo, hi = 0.0, 0.0026        # EXP-C0-02 实测 r 下界处已必发放（2× 裕量设计点）
    assert _adapter_fires_at(hi), "r_min=0.0026 应必发放（EXP-C1-01 设计点）"
    for _ in range(20):
        mid = (lo + hi) / 2.0
        if _adapter_fires_at(mid):
            hi = mid
        else:
            lo = mid
    print(f"\n[1] adapter threshold 实测 ≈ {hi:.6e}（单步脉冲发放下界；"
          f"设计点 r_min=0.0026 为其 {0.0026 / hi:.2f}×）")

    # ── 2/3. 越阈幅度 7×7 全组合：固定 Δt₂ → 输出全等 ──
    # （两父幅度不同，_run_synthetic_recording 的标量 r_amp 不适用，手工馈入）
    results = {}
    for a in AMPLITUDES:
        for b in AMPLITUDES:
            ad_x, ad_y, st = _synthetic_stack()
            fires, c_vals = [], []
            for t in range(T_A + DT2 + 200):
                ad_x.step(a if t == T_A else 0.0, DT)
                ad_y.step(b if t == T_A + DT2 else 0.0, DT)
                c = st.step(t, DT)
                if c > 0.0:
                    fires.append(t)
                    c_vals.append(c)
            results[(a, b)] = (tuple(fires), tuple(c_vals),
                               st.downstream.voltage)

    distinct = set(results.values())
    ref = results[(AMPLITUDES[0], AMPLITUDES[0])]
    print(f"\n[2] 越阈幅度组合 {len(results)} 个（{len(AMPLITUDES)}×"
          f"{len(AMPLITUDES)}，覆盖实测域 [0.0026,0.3660]）")
    print(f"[3] 输出等价类数 = {len(distinct)}（期望 1）")
    print(f"    参考输出: fires={ref[0]} c_ro={ref[1][0]!r} 下游v={ref[2]!r}")
    assert len(distinct) == 1, (
        f"越阈组合输出不全等（{len(distinct)} 类）——与外部实测矛盾，须重查")

    print("\n" + "=" * 68)
    print("结论（登记，不判 bug）：")
    print("  above-threshold amplitude equivalence 成立——")
    print("  graded relation current → binary relation event 主动删除父关系")
    print("  幅度信息；level-2 当前消费的是\"关系是否发生 + 发生时间\"，")
    print("  而不是完整父关系幅度。")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
