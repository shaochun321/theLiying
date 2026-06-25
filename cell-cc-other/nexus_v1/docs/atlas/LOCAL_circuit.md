# LOCAL: Hebbian 电路 — 层级结构与学习

> **Version**: v1.7.2 | **File**: [hebbian.py](../../circuit/hebbian.py)

---

## 层级拓扑

```
         Aff_reg ×6 ─┐
                     ├─→ Bundle aff→enc (12 bundles, gain=2)
         Aff_irr ×6 ─┘          │
                                ▼
                        Encoding ×14 (2×7轴, continuous)
                                │
                        Bundle enc→col (7 bundles, gain=3)
                                │
                                ▼
                         Column ×7 (6前庭+1热, continuous)
                                │
                    ┌───────────┼───────────┐
                    │           │           │
              axis bundles  cross bundle  sprouted bundles
              (3×1×1,       (1×7×3,       (动态, 0-∞)
               gain=5,      gain=0.7,
               w=0.4)       w=0.05)
                    │           │           │
                    ▼           ▼           ▼
                        Motor ×3+ (spiking, xyz)
```

## Bundle 类型与计数 (v1.7.2)

| 层 | 类型 | 初始数 | w_init | gain | coupler |
|---|---|---|---|---|---|
| met→hc | feedforward | 6 | 0.5 | 1.0 | ✗ |
| hc→aff | feedforward | 6 | 0.8 | 1.0 | ✗ |
| aff→enc | feedforward | 12 | 0.2 | 2.0 | ✓ |
| enc→col | feedforward | 7 | 0.15 | 3.0 | ✓ |
| col→mot (axis) | axis-specific | 3 | 0.4 | 5.0 | ✓ |
| col→mot (cross) | cross-axis | 1 | 0.05 | 0.7 | ✓ |
| **初始合计** | | **35** | | | |
| sprouted | 动态 | 0→∞ | 1e-4 | inherit | ✓ |

## 学习规则

```
learn(dt, gate=1.0):
  STDP: Δw = lr × (A+ × pre × Δpost - A- × post × Δpre)
  BCM:  θ_BCM = EMA(post², τ=5s)
        if post < θ_BCM: Δw *= -1 (LTD)
  Hebbian decay: Δw -= decay_rate × w
  Gate: Δw *= gate × (1 - PNN_fraction)
  Boundary: multiplicative soft boundary
```

## 代谢税 (每 100 步)

```
P2.1 (v1.7.2):
  每 bundle → EnergyStore.withdraw(BUNDLE_BASAL_COST=0.0005)
  低能量时 → 权重衰减 (deficit × 0.002 × w)
```

## 结构生长 (每 10k 步)

```
Phase 1 - Sprouting:
  if !energy_store.is_starving:      ← P2.1 门控
    for each candidate bundle:
      if |ξ| > XI_SPROUT (0.3):
        if sources have energy:
          sprout(child, expand_boost=30%)
          
Phase 2 - Pruning:
  if age > grace_period (5000):
    if ξ < -threshold AND ZCR is low:
      prune(bundle)
```

## 版本历史

| 版本 | 结构变更 |
|---|---|
| v1.5.0 | axis/cross 拓扑分化 |
| v1.7.0 | 回归测试套件 |
| v1.7.1 | Xin fan-in 归一化 |
| v1.7.2 | MAX_BUNDLES 移除, EnergyStore 门控 |
