# LOCAL: 影子层 + DA 回路

> **Version**: v1.7.2 | **Files**: [shadow_sandbox.py](../../components/shadow_sandbox.py), [variant_adapter.py](../../circuit/variant_adapter.py)

---

## 影子层架构

```
主层 Column ×7
  │ (只读观测, 每 10 步)
  ▼
ShadowSandbox
  ├── shadow_cols ×7 (BCM 学习, 独立权重)
  │     W_shadow 追踪 Column 激活统计
  │     BCM θ = EMA(activation², τ)
  │
  └── 输出 → DA 回路
```

## DA 回路 (结构化 VTA)

```
                        ┌─────────────────┐
Shadow Col ×7 ──────┐   │ DA Neuron ×3     │
                    │   │ (τ=2s, bc=0.1)   │
  [shadow_to_da     ├──→│ 输入: shadow +   │──→ dopamine.concentration
   bundles, STDP]   │   │       xin relay  │    (体积传输, 均值)
                    │   │ D2R 自受体:       │
Xin integrator     │   │  GIRK 负反馈      │
  │ (Capacitor)    │   │                   │
  ▼                │   └─────────────────┘
Xin relay neuron ──┘
  [xin_to_da
   bundles, STDP]
```

## DA 输出路径

```
dopamine.concentration (0.0 ~ 1.0)
  │
  ├─→ gain_factor() → Column 增益调制
  │     da_current = (gain - 1.0) × 0.5 × col_activation
  │     inject into Column membrane
  │
  ├─→ Fruit gate: DA < 0.15 → 允许成熟 (pruning possible)
  │
  └─→ 三因子学习: gate = DA × pre × post
```

## C3' 偏激→DA 路径

```
CirculationProportionCircuit
  │ deviation = |actual_ratio - 1/3|
  │ MOSFET comparator → da_current
  ▼
DA neuron ← inject(c3_da_current, dt)
  → D2R 自然调节 (不是 bypass)
```

## 能量约束 (P2.1)

- DA neuron refill: 0.001/step/neuron from EnergyStore
- 总 DA 能量消耗: 3 × 0.001 = 0.003/step (ES 第二大消耗源)

## 未来路线

- **A8**: 影子层升级为 DC 处理器 (结构决策)
- **DC/AC 分离**: 影子层处理 DC (长期趋势), 主层处理 AC (快速信号)
- **T006 §2**: FEP 第三条路径 = 结构可塑性

## 版本历史

| 版本 | 变更 |
|---|---|
| v1.5.0 | ShadowSandbox 初版 (只读) |
| v1.6.0 | DA 神经元池 (3 VTA) |
| v1.7.0 | shadow→DA + xin→DA bundles |
| v1.7.2 | DA_REFILL_RATE 0.01→0.001 |
