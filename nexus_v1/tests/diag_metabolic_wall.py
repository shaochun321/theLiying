"""diag_metabolic_wall.py — 代谢壁诊断脚本

目标：精确测量 EnergyStore 的收支，确定 fill 在 100k 步耗尽的根本原因。

方法：
1. 运行 5000 步，记录每步的 deposit/withdraw/basal/fill
2. 在 1k/5k/10k/50k/100k 关键点打印收支快照
3. 计算稳态 P_in（进入率）vs P_out（消耗率）
4. 输出净预算缺口和耗尽预测时间
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from nexus_v1.circuit.variant_adapter import VariantCircuit

# ─── 构建电路 ───
c = VariantCircuit()
store = c.energy_store

# ─── 监控数据 ───
history = {
    'step': [],
    'fill': [],
    'deposited_delta': [],
    'withdrawn_delta': [],
    'basal_delta': [],
    'net_per_step': [],
}

prev_dep = store._total_deposited
prev_with = store._total_withdrawn
prev_basal = store._total_basal_drain

SAMPLE_INTERVAL = 100   # 每 100 步采样一次
RUN_STEPS = 5000        # 快速诊断：5000 步足够看出稳态

print("=== 代谢壁诊断 — 开始运行 ===")
print(f"EnergyStore: capacity={store.config.capacity}, initial={store.config.initial_fill*store.config.capacity:.1f}")
print(f"  max_deposit_per_step={store.config.max_deposit_per_step}")
print(f"  deposit_efficiency={store.config.deposit_efficiency}")
print(f"  basal_drain={store.config.basal_drain}")
print()

snapshot_steps = {100, 500, 1000, 2000, 5000}

for step in range(1, RUN_STEPS + 1):
    c.step({'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0}, dt=1.0)

    if step % SAMPLE_INTERVAL == 0 or step in snapshot_steps:
        dep_now = store._total_deposited
        with_now = store._total_withdrawn
        basal_now = store._total_basal_drain

        d_dep   = dep_now   - prev_dep
        d_with  = with_now  - prev_with
        d_basal = basal_now - prev_basal

        steps_elapsed = SAMPLE_INTERVAL if step % SAMPLE_INTERVAL == 0 else (step % SAMPLE_INTERVAL or SAMPLE_INTERVAL)

        rate_in   = d_dep   / steps_elapsed
        rate_out  = (d_with + d_basal) / steps_elapsed
        net_rate  = rate_in - rate_out

        history['step'].append(step)
        history['fill'].append(store.fill_fraction)
        history['deposited_delta'].append(d_dep)
        history['withdrawn_delta'].append(d_with)
        history['basal_delta'].append(d_basal)
        history['net_per_step'].append(net_rate)

        prev_dep   = dep_now
        prev_with  = with_now
        prev_basal = basal_now

        if step in snapshot_steps:
            fill = store.fill_fraction
            level = store.level
            print(f"  [step={step:6d}] fill={fill:.4f} level={level:.2f}")
            print(f"    P_in={rate_in:.5f}/step  P_out={rate_out:.5f}/step  net={net_rate:+.5f}/step")
            if net_rate < 0:
                steps_to_empty = level / abs(net_rate) if abs(net_rate) > 1e-10 else float('inf')
                print(f"    [!] net NEGATIVE -- fill=0 in ~{steps_to_empty:.0f} steps")
            else:
                print(f"    [OK] net positive")
            print()

# ─── 全局收支汇总 ───
print("=== 全程收支汇总 ===")
total_in  = store._total_deposited
total_out = store._total_withdrawn + store._total_basal_drain
total_net = total_in - total_out
level_change = store.level - (store.config.capacity * store.config.initial_fill)

print(f"  总步数          : {RUN_STEPS}")
print(f"  EnergyStore 最终level: {store.level:.4f} (initial: {store.config.capacity * store.config.initial_fill:.1f})")
print(f"  总注入 (deposit): {total_in:.4f}")
print(f"  总消耗 (withdraw): {store._total_withdrawn:.4f}")
print(f"  总基础代谢 (basal): {store._total_basal_drain:.4f}")
print(f"  总净变化         : {total_net:.4f}")
print(f"  实际 level 变化  : {level_change:.4f}")
print(f"  Noether 守恒检查  : {store.summary()['noether_balance']:.6f} (应≈0)")
print()

# ─── 各消耗源分解 ───
print("=== P_out 分解分析（每步平均）===")
avg_dep   = store._total_deposited   / RUN_STEPS
avg_with  = store._total_withdrawn   / RUN_STEPS
avg_basal = store._total_basal_drain / RUN_STEPS
avg_net   = (store._total_deposited - store._total_withdrawn - store._total_basal_drain) / RUN_STEPS

print(f"  P_deposit  (平均/步): {avg_dep:.6f}  (上限: {store.config.max_deposit_per_step:.6f})")
print(f"  P_withdraw (平均/步): {avg_with:.6f}  (各子系统合计)")
print(f"  P_basal    (平均/步): {avg_basal:.6f}  (tick 基础代谢)")
print(f"  P_net      (平均/步): {avg_net:+.6f}")
print()

deposit_utilization = avg_dep / store.config.max_deposit_per_step * 100
print(f"  deposit 利用率: {deposit_utilization:.1f}% (100% = 上限被触及, <100% = 进食不足)")
print()

# ─── 预测 100k 步的 fill ───
print("=== 预测分析 ===")
if avg_net < 0:
    steps_to_zero = store.level / abs(avg_net)
    print(f"  净负平衡：{avg_net:+.6f}/步")
    print(f"  当前 level={store.level:.2f}, 预计 {steps_to_zero:.0f} 步后耗尽")
    print(f"  (从头开始: initial={store.config.capacity * store.config.initial_fill:.1f}, 预计 {(store.config.capacity * store.config.initial_fill)/abs(avg_net):.0f} 步耗尽)")
    print()
    print("  修复方向候选：")
    gap = avg_with + avg_basal - avg_dep
    print(f"    方案A: 提高 max_deposit_per_step {store.config.max_deposit_per_step:.4f} → {store.config.max_deposit_per_step + gap * 1.2:.4f} (+20% 余量)")
    print(f"    方案B: 降低 basal_drain {store.config.basal_drain:.6f} → {max(0, store.config.basal_drain - gap * 0.5):.6f}")
    print(f"    方案C: 提高 consume_nearby 产出（世界参数）")
else:
    print(f"  净正平衡：{avg_net:+.6f}/步 — fill 应稳定增长")
    print(f"  若实验中 fill 仍耗尽，说明早期（启动阶段）消耗过高。")
