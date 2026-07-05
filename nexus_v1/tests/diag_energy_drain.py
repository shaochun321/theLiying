"""
能量收支精细诊断：禁用 consume_nearby，追踪每步 deposit / withdraw 差额。
目标：找出 fill 无法恢复的根因（drain 来自何处？）

运行：
  PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.diag_energy_drain
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit

N_STEPS = 3000
PRINT_EVERY = 500

def run():
    print("=== 能量收支精细诊断（consume_nearby 禁用，eta=0.06）===\n")
    c = VariantCircuit()

    # 禁用 consume_nearby
    c.world.consume_nearby = lambda pos, rate, dt: 0.0

    # 记录 EnergyStore 内部状态
    es = c.energy_store

    print(f"  初始 fill: {es.fill_fraction:.4f} | charge: {es._cap.charge:.2f}")
    print()

    # 保存上一步的 Noether 计数
    prev_dep  = es._total_deposited
    prev_with = es._total_withdrawn
    prev_base = es._total_basal_drain

    header = f"{'Step':>6} {'fill':>7} {'charge':>8} {'dep_Δ':>8} {'with_Δ':>8} {'base_Δ':>8} {'net':>8}"
    print(header)
    print("-" * len(header))

    for step in range(1, N_STEPS + 1):
        c.step({}, dt=1.0)

        dep_d  = es._total_deposited  - prev_dep
        with_d = es._total_withdrawn  - prev_with
        base_d = es._total_basal_drain - prev_base
        net    = dep_d - with_d - base_d

        prev_dep  = es._total_deposited
        prev_with = es._total_withdrawn
        prev_base = es._total_basal_drain

        if step % PRINT_EVERY == 0:
            print(f"{step:>6} {es.fill_fraction:>7.4f} {es._cap.charge:>8.3f} "
                  f"{dep_d:>8.4f} {with_d:>8.4f} {base_d:>8.6f} {net:>8.4f}")

    print()
    print("== 累计总结 ==")
    print(f"  total_deposited:   {es._total_deposited:.3f}")
    print(f"  total_withdrawn:   {es._total_withdrawn:.3f}")
    print(f"  total_basal_drain: {es._total_basal_drain:.6f}")
    net_total = es._total_deposited - es._total_withdrawn - es._total_basal_drain
    print(f"  net (dep-with-base): {net_total:.3f}")
    print(f"  actual level change: {es._cap.charge - 500:.3f} (started at 500)")
    print()
    imbalance = net_total - (es._cap.charge - 500)
    print(f"  Noether balance error: {imbalance:.6f}  (should be ~0)")

if __name__ == '__main__':
    run()
