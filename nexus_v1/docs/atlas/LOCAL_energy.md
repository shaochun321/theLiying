# LOCAL: 能量系统 — EnergyStore + 代谢

> **Version**: v1.7.2 | **Files**: [energy_store.py](../../components/energy_store.py), [hebbian.py](../../circuit/hebbian.py), [variant_adapter.py](../../circuit/variant_adapter.py)

---

## 能量流全图

```
World.consume_nearby()          ← 热源吸收 (CONSUME_RATE=0.15)
  │ × distance_decay
  ▼
EnergyStore.deposit(energy)     ← cap: max_deposit_per_step=0.05
  │ × deposit_efficiency=0.9
  │ capacity=1000, initial=500
  │
  ├─→ EnergyStore.tick(dt)      ← basal_drain=0.0001/step (存在代价)
  │
  ├─→ DA neuron refill          ← 0.001/neuron/step × 3 = 0.003/step
  │     energy_store.withdraw(needed)
  │
  ├─→ Vascular delivery        ← delivery_factor × requested
  │     energy_store.withdraw(requested_total)
  │     → neuron.energy refill
  │
  └─→ Bundle basal cost        ← 0.0005/bundle/tax (每100步)
        energy_store.withdraw(BUNDLE_BASAL_COST)
```

## 消耗预算 (per step, N=50)

| 消耗项 | 量/step | 占比 |
|---|---|---|
| DA refill | 0.003 | ~60% |
| Bundle basal | 0.00025 | ~5% |
| Basal drain | 0.0001 | ~2% |
| Vascular | ~0.0015 | ~30% |
| Sprout event | 0.1 (one-time) | — |
| **总计** | ~0.005 | |

## 能量约束机制

```
P_inflow (world income)
  - N × P_basal (per-bundle drain, 线性)
  - P_DA (DA neuron refill, 常数)
  - P_vascular (vascular delivery, 变量)
  = P_net (剩余可用)

当 P_net → 0:
  EnergyStore → 0
  → is_starving = True (fill < 10%)
  → delivery_factor → 0
  → neurons starve → weight decay
  → sprout frozen (gate: !is_starving)
  → T_recovery → ∞ (临界期关闭)
```

## Noether 审计

```
EnergyStore.summary().noether_balance:
  deposited - withdrawn - basal_drain - level + initial = 0
  (每步检查, 500k 步 0 violations)
```

## 版本历史

| 版本 | 变更 |
|---|---|
| v0.10.1 | EnergyStore 初版 |
| v1.7.2 | P2.1: max_deposit_per_step, BUNDLE_BASAL_COST, DA_REFILL 校准 |
