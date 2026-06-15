# HebbianCircuit — 赫布回路基础

## 物理对应

- **BIO**: 前庭核→运动核 (层级化赫布回路)
- **EE**: 多层 SNN with STDP/BCM 学习

## 文件

[hebbian.py](../../circuit/hebbian.py)

## 功能

构建并管理完整的层级电路：
- 前庭链 → Encoding (14) → Column (7) → Motor (3+)
- Bundle 创建与拓扑管理
- 结构生长 (Sprout/Prune, 每 10k 步)
- 代谢税 (每 100 步)
- Metabolic tax → EnergyStore 扣除 (P2.1)

## 结构生长 (P2.1)

```
门控条件:
  1. !energy_store.is_starving  (EnergyStore 非饥饿)
  2. |ξ| > XI_SPROUT = 0.3      (预测误差足够大)
  3. source.energy > SPROUT_COST (源神经元有能量)
  4. sprout_count < 3            (每次最多 3 个)

容量上限:
  热力学涌现 — N × P_basal ≈ P_inflow 时自然冻结
  无硬编码 MAX_BUNDLES (P2.1 移除)
```

## 关键参数

| 参数 | 值 | 物理意义 |
|---|---|---|
| `SPROUT_INTERVAL` | 10000 | 结构检查周期 (steps) |
| `XI_SPROUT` | 0.3 | Xin 发芽阈值 |
| `BUNDLE_BASAL_COST` | 0.0005 | 每束每税检基底漏电 |
| `SPROUT_ENERGY_COST` | 0.1 | 发芽能量消耗 |
