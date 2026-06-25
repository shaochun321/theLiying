# LOCAL: 熵账本 + Noether 审计系统

> **Version**: v1.7.2 | **Files**: [entropy_ledger.py](../../components/entropy_ledger.py), [noether_probe.py](../../circuit/noether_probe.py), [toprxin_ledger.py](../../circuit/toprxin_ledger.py)

---

## 三层审计架构

```
┌──────────────────────────────────────────────┐
│ Layer 1: Noether Probe (每步)                 │
│   能量守恒: E_in = E_out + E_stored + E_leak │
│   电荷 KCL:  ΣI_in = ΣI_out (per Capacitor) │
│   Landauer:  Q/bit ≥ kT ln2                  │
│   权重稳定:  |mean(dw)| < 0.01/step          │
│                                              │
│   违规 → _structural_freeze = True           │
└──────────────────┬───────────────────────────┘
                   │
┌──────────────────▼───────────────────────────┐
│ Layer 2: Entropy Ledger (每步 pre/post)       │
│   pre_step:  检查守恒不变量                    │
│   post_step: 记录结构事件                      │
│   事件:                                       │
│     SPROUT (parent, child, xi, N)             │
│     PRUNE  (bundle, reason)                   │
│     MITOSIS (parent, child, axis)             │
│     MATURATION (neuron, stage_old, stage_new) │
│     E1_EVAL (N_before, N_after, ratio)        │
│                                              │
│   冻结条件:                                    │
│     Noether violation detected                │
│     energy_balance > threshold                │
└──────────────────┬───────────────────────────┘
                   │
┌──────────────────▼───────────────────────────┐
│ Layer 3: TOPRXin Ledger (慢尺度)              │
│   每 1000 步:                                 │
│     T = 拓扑快照 (N_bundles, connections)      │
│     O = 振荡器状态 (freq, phase)               │
│     P = 功率分布 (per-layer power)             │
│     R = 运动势 (ν, P_ν)                       │
│     Xin = 预测误差分布                         │
│                                              │
│   输出: 权重 Shannon 熵 (A3 Landauer 探针)    │
│   交叉引用: registry.json                     │
└──────────────────────────────────────────────┘
```

## 时序

```
VariantCircuit.step():
  _entropy_ledger_pre_step()   ← Layer 2 前置检查
  ... (全部计算) ...
  _noether_probe.audit()       ← Layer 1 守恒审计
  _entropy_ledger_post_step()  ← Layer 2 后置记录
```

## P2.1 后新增审计

- **E1 系统级评估**: 每次 N 变化后，比较 mean_xi 变化率
- **EnergyStore Noether**: deposited - withdrawn - basal - level + initial = 0
- **Bundle basal drain**: 从 EnergyStore 扣除记账

## 回归测试覆盖

| 审计项 | 测试 ID | 阈值 |
|---|---|---|
| Noether violations | T1.1 | == 0 |
| Energy balance | T1.2 | < 0.01 |
| Landauer bound | T1.3 | True |
| Structural entropy | T8.1, T8.2 | > 0 |
| Fan-in fairness | T9.1 | < 2.0× |

## 版本历史

| 版本 | 变更 |
|---|---|
| v1.5.0 | NoetherProbe 初版 |
| v1.6.0 | TOPRXin Ledger, 结构熵 |
| v1.7.0 | 回归测试套件集成 |
| v1.7.1 | T9 fan-in 测试 |
| v1.7.2 | E1 评估, EnergyStore Noether |
