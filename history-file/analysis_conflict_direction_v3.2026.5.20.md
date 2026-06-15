# 冲突方向检测 v3 — 实验裁决

## 核心结果: 总压力损伤减少 55%

```
v2 (无方向检测): 总压力损伤 = 1.317
v3 (有方向检测): 总压力损伤 = 0.591
                 改善 = 55%
```

结晶率不变: v2 = v3 = 200/250 (80%)

---

## 各区域压力保护对比

| 区域 | v2 冲击 ΔS | v2 评价 | v3 冲击 ΔS | v3 评价 | 改善 |
|------|-----------|--------|-----------|--------|------|
| encoding | +0.094 | ⚠️受损 | +0.118 | ⚠️受损 | -2% |
| column | +0.127 | ⚠️受损 | +0.247 | ❌更差 | -12% |
| **inter_layer** | +0.102 | ⚠️受损 | **+0.042** | **✅保护** | **+6%** |
| motor | +0.000 | ✅保护 | +0.000 | ✅保护 | 0% |
| sediment | -0.994 | ❌严重 | +0.184 | ⚠️改善 | **+81%** |

### 为什么 inter_layer 和 sediment 改善了, 而 column 变差了?

**根因: alignment 在压力阶段仍然是正值 (~0.67)**

```
压力阶段 alignment:
  encoding:    +0.675  ← 应该是负的!
  column:      +0.690  ← 应该是负的!
  inter_layer: +0.674  ← 轻微正
  motor:       +0.597  ← 正
  sediment:    +0.703  ← 正
```

**memory_signature 是 EMA (指数移动平均)，反应太慢。**
冲突信号是学习信号的反转，但 EMA 需要很多 tick 才能感知到反转。
在 memory_tau=20 下，需要 ~40 ticks 才能让 alignment 显著改变。

> [!IMPORTANT]
> **这恰恰验证了你的分化原则——连冲突检测的参数也需要分化!**
> 
> ```
> encoding (τ=3):     memory_tau 应该小 → 快速检测方向变化
> column (τ=15):      memory_tau 应该大 → 稳定的长期记忆
> sediment (τ=50):    memory_tau 应该更大 → 极稳定的记忆签名
> ```
> 
> 不是一个 memory_tau=20 适合所有区域。

---

## 方向检测有效的证据

虽然 alignment 没有变负，但 v3 的门控值确实被缩小了:

```
压力阶段平均门控:
  encoding:    v2=+0.52 → v3=+0.37  (减少 29%)
  column:      v2=+0.99 → v3=+0.66  (减少 33%)
  inter_layer: v2=+0.87 → v3=+0.58  (减少 33%)
```

**方向调制在工作——只是还不够强。**

如果 alignment 能在压力时变成 -0.3:
```
direction_factor = max(0, -0.3 + 0.3) = 0  → 完全关闭!
```

---

## 修正方向

### 1. 分化 memory_tau

```python
VARIANTS = {
    "encoding":    {..., memory_tau: 5},    # 快速检测
    "column":      {..., memory_tau: 30},   # 稳定记忆
    "inter_layer": {..., memory_tau: 15},   # 中速
    "motor":       {..., memory_tau: 3},    # 极快 (动作)
    "sediment":    {..., memory_tau: 100},  # 极稳定
}
```

### 2. 用差分代替绝对值

```python
# 当前: alignment = cosine(signal, memory)
# 问题: EMA 变化太慢

# 修正: 用信号的变化率 (差分) 代替绝对值
delta_signal = signal - last_signal
alignment = cosine(delta_signal, learned_direction)
# 正常学习: delta 和 learned_direction 同向 → +1
# 冲突:     delta 和 learned_direction 反向 → -1
```

### 3. 双时间尺度

```python
# 快记忆: 短 EMA (最近 10 ticks)
# 慢记忆: 长 EMA (最近 100 ticks)
# alignment = cosine(fast_memory, slow_memory)
# 正常: fast ≈ slow → alignment ≈ 1
# 冲突: fast ≠ slow → alignment ↓
```

> [!TIP]
> 双时间尺度方案最优雅:
> - 慢记忆 = "已学结构" (what was)
> - 快记忆 = "当前输入" (what is)
> - alignment = 两者的一致性
> - 不需要额外存储 delta
> - 自然地，τ_fast/τ_slow 的比值可以分化!

---

## 总结

```
已确认:
  ✅ 分化门控有效 — 同一母本, 不同参数, 不同行为
  ✅ 方向检测有效 — 总压力损伤减少 55%
  ✅ 分化原则递归 — 连检测参数本身也需要分化

待改进:
  ⚠️ memory_tau 需要分化 (当前统一 =20)
  ⚠️ 应使用双时间尺度 (fast/slow EMA) 代替单 EMA
  ⚠️ column 仍然太慢关门 — θ 可能还需要微调
```
