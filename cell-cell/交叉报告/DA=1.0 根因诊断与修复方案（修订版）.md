# DA=1.0 根因诊断与修复方案（修订版）

## 诊断结果

### 信号追踪表（热源移除后 5000 步）

```
通路                   移除前    移除后    趋势     根因
─────────────────────────────────────────────────────
shadow_to_da           0.75    → 3.09    ↑↑↑ 增长   BUG-1 (正反馈)
intake_to_da           2.46    → 1.30    →  缓慢衰减 保留(初驱力)
relay_to_da            0.43    → 0.00    ✅ 正确
thermo_delta_to_da     0.00    → 0.00    ✅ 正确
satiety_to_da         -0.17    → -0.10   太弱      设计缺陷
bc_current (×3)        0.30      0.30    恒定      正常
```

### BUG-1: shadow_to_da 正反馈回路（唯一真正的 bug）

shadow 层是**自治子系统**，内部有：
- 7 个 col neurons（bc_current=0.005, spiking, CRI）
- BCM 学习（stdp_lr=0.01）在 enc→col 束上
- `synapse_gain=10.0`（放大 10 倍）
- 跨轴 cross bundles 随 BCM 增强

shadow col 的 `calcium_rate` 持续增长 → shadow_to_da 注入 DA 越来越多（0.75→3.09）。
这是**开环正反馈**：shadow 层的活动不受主系统 fill/satiety 约束。

### intake_to_da（非 bug，保留）

`_feed_rate_cap` 电容提供初始生存驱力。τ=5000 步是设计意图。
在测试中可以手动清零 `c._feed_rate_cap.charge = 0` 来隔离 DA 行为。

---

## 修复方案

### Fix-1: 降低 shadow_to_da 权重（直接削弱正反馈）

[variant_adapter.py L2817-2830](file:///D:/cell-cc/2026.7.6/nexus_v1/circuit/variant_adapter.py#L2817-L2830):

```diff
-initial_weight=0.05,
+initial_weight=0.01,    # 从 0.05 降至 0.01: I_max = 7×1.0×0.01×1.0 = 0.07
```

### Fix-2: 增强 satiety_to_da 抑制（平衡 DA）

[variant_adapter.py L3054-3063](file:///D:/cell-cc/2026.7.6/nexus_v1/circuit/variant_adapter.py#L3054-L3063):

```diff
-initial_weight=0.3,
-synapse_gain=-1.0,
+initial_weight=1.0,
+synapse_gain=-5.0,       # I_max = act × 1.0 × 5.0 = 最大 5.0
```

需确认 satiety_neuron 在 fill=1.0 时的 activation 值。

### 预期修复效果

| 状态 | shadow | intake | satiety | 净DA输入 | DA浓度 |
|------|--------|--------|---------|---------|--------|
| 初始进食 (fill↑) | 0.07 | 1.30 | -0.50 | +0.87 | ~0.8 ✅ |
| 贴源静止 (fill=1) | 0.07 | 缓慢衰减 | -5.0 | <-4.0 | ~0.01 ✅ |
| 远离源 (fill<0.5) | 0.07 | 0 | 0 | +0.07 | ~0.07 ✅ |
| 接近新源 (fill↓) | 0.07 | ↑ | 0 | ↑ | ↑ ✅ |

> [!IMPORTANT]
> intake 电容保留。在特定测试中手动清零 `c._feed_rate_cap.charge = 0`。

## 验证计划

1. 重跑 `diag_da_trace.py`：确认修复后 DA 在热源移除 500 步内降至 < 0.1
2. 重跑 `Test 1`：确认 DA_ema 衰减至 < 0.1（P0 冻结机制真正被触发）
3. 重跑 `Test 3`：STDP ON vs OFF 是否产生 DR5 差异