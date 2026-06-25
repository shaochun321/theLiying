# VariantCircuit — 完整前庭-运动系统

## 物理对应

- **BIO**: 前庭核+运动核+调制系统 的完整集成
- **EE**: 全系统集成器

## 文件

[variant_adapter.py](../../circuit/variant_adapter.py)

## 功能

继承 HebbianCircuit，添加：
- DA 调制 (第三因子)
- PNN 可塑性门控
- A7 运动势 (ν=dK/dt)
- 熵账本 pre/post step
- 影子层集成
- 运动决策 (CPG + force + muscle + body)
- EnergyStore 能量预算 (P2.1: 热力学容量上限)

## step() 执行顺序

```
1.  前庭链 step
2.  Afferent → Encoding 传播
3.  Extra axes 直接注入
4.  Encoding → Column 传播  
5.  Column → Motor 传播
6.  Sprouted bundles 传播
7.  PowerRail 竞争
8.  Learning (DA + PNN gated)
9.  Metabolic tax (每100步, 从 EnergyStore 扣除)
10. Structural growth (每10k步, EnergyStore 门控)
11. Motor homeostasis
12. Mitosis check
13. 影子层 step
14. Fruit lifecycle (每100步)
15. 运动决策 (CPG → force → muscle → body)
16. A7 运动势计算
17. Noether probe audit
18. Entropy ledger post_step
```

## 能量预算 (P2.1)

```
收入: World.consume_nearby() → EnergyStore.deposit()
      恒定上限: max_deposit_per_step = 0.05 (P_inflow)

支出:
  - Bundle 基底漏电: 0.0005/bundle/tax (每100步)
  - DA neuron refill: 0.001/neuron/step × 3
  - EnergyStore.tick: 0.0001/step (基础代谢)

容量上限: 热力学涌现 (无硬编码)
  N_max ≈ 当 P_drain > P_income 时, EnergyStore 枯竭 → sprout 冻结
  实测: N=37→61 (80k), ES fill 50%→21%, 减速 1.5×
```

## 理论

- T001: Noether probe 审计
- T002: 学习门控 (DA × PNN × sync)
- T003: Fruit 生命周期调度
- T005: A7 运动势
- T006: 理论锚点 (Landauer/FEP/建构定律/Margolus-Levitin)

## 修改历史

| 版本 | 变更 |
|---|---|
| v1.0 | 基础 variant 覆盖 |
| v1.5 | 添加运动决策、影子层、Noether probe |
| v1.6 | A7 运动势、C2 修复、熵探针扩展 |
| v1.7 | ν EMA 平滑 |
| v1.7.1 | P2.1: 废除 MAX_BUNDLES=80, 热力学能量墙 |
