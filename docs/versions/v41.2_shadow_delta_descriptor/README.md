# 影子层的哲学与压缩机制

## 日期
2026-05-19

## 背景（用户提出）

影子层（dormant fruit）不只是"错误记录"。它承载着**历史时空-信息轨迹**的残影。

> 真实的时空-信息轨迹本身就不可能完全相同，
> 所以必然会出现一些属于高确定性轨迹的副本。
> 将来面对真实世界，项目可能不记得副本的具体细节（已被修剪），
> 但至少会记得"不一样"。

## 核心洞见

影子 ≠ 错误。影子 = **差异的最小描述**。

当一个时空-信息轨迹与主环流(circulation)相似但不完全相同时：
- 完整保存：不切实际（内存/复杂性）
- 完全丢弃：丢失了"曾经有差异"的信息
- **压缩保存**：用项目自身的语言（运动势、时空测度）描述"怎样不一样"

## 影子的三种命运

```
                    主环流（高确定性轨迹）
                         ║
      ┌──────────────────╬───────────────────┐
      │                  ║                   │
   一致→合并          微偏差→影子          大偏差→修剪
   (no fruit)       (dormant fruit)        (pruned)
                         │
                         ▼
              ┌──────────────────────┐
              │  最小差异描述符       │
              │  (Δ-descriptor)      │
              │                      │
              │  δ_momentum: +0.03   │  ← 运动势差异
              │  δ_phase: -0.12      │  ← CPG 相位差异
              │  δ_gate: SHUT→OPEN   │  ← 门控状态差异
              │  δ_channel: aco>lum  │  ← 通道配比差异
              │  coherence: 0.7      │  ← 与主环流的相干度
              │  age: 230 ticks      │  ← 存活时长
              └──────────────────────┘
```

## Δ-descriptor 的设计

### 用项目自身的语言

| 描述符 | 来源 | 含义 |
|--------|------|------|
| `δ_momentum` | `xin_tension` | 预测残差的方向——"这条轨迹比主环流动量大/小多少" |
| `δ_phase` | `col_phase_*` - CPG phase | 影子创建时的 CPG 相位 vs 主环流相位——"在不同的时间窗口" |
| `δ_channel` | gated signal ratio | 哪个通道在影子创建时更强——"看到的世界不一样" |
| `δ_circulation` | circulation measure | 影子所在的 sig→z_t→sig 环路有多强——"这条替代路径的活力" |
| `coherence` | ST coherence | 影子与主环流的时序一致性——"有多像" |
| `age` | tick count | 影子存活了多久——"这种差异有多持久" |

### 关键原则

1. **描述符不存储原始激活值** — 只存储与主环流的**差值**
2. **差值用项目已有的物理量表达** — momentum, phase, channel ratio
3. **年龄(age)和相干度(coherence)决定修剪优先级** — 老+低相干→先修剪
4. **高相干的影子可以"回归"** — 如果主环流发生变化，相干的影子可以被激活

## 实施方案

### 修改 `xin_dormant_fruit` 数据结构

```python
# 当前：
xin_dormant_fruit = {
    "tension_at_creation": 1.44,      # 只有一个标量
    "bundle_id": "bundle_xxx",
    "state": "dormant",
    "trace_strength": 0.998,          # 化学衰减
    "trace_decay": 0.995,
}

# 新增 Δ-descriptor：
xin_dormant_fruit = {
    "tension_at_creation": 1.44,
    "bundle_id": "bundle_xxx",
    "state": "dormant",
    "trace_strength": 0.998,
    "trace_decay": 0.995,
    # v41.2: Δ-descriptor（最小差异描述）
    "delta": {
        "d_momentum": +0.03,          # 与主环流的动量差
        "d_phase": -0.12,             # 创建时 CPG 相位偏移
        "d_gate_state": 0.15,         # 创建时的门控值
        "d_channel_ratio": [0.87, 0.49, 0.002],  # 创建时通道信号
        "d_circulation": 1.77,        # 创建时环流强度
        "coherence_with_main": 0.0,   # 与主环流的相干度（初始未计算）
    },
    "created_tick": 342,
}
```

### 修改 `_column_forward_step()` — Column 读取影子

```python
# Column 读取高张力影子的 Δ-descriptor
# 如果影子的 d_phase 与当前 CPG phase 接近：
#   → 这条"替代轨迹"在当前相位是活跃的
#   → Column 可以用它来调整 phase reset 强度
```

### 修改 `_detect_practice_convergence()` — 影子参与结晶

```python
# 如果一个影子与主环流的 coherence > 0.8 且 age > 200：
#   → 这不是错误，是一条"几乎一样但有细微差异"的轨迹
#   → 它可以参与 practice_cortex 的结晶
#   → 结晶体记住了"主要这样做，但有时也那样做"
```

## 与用户愿景的对齐

用户说的核心点：

> "至少会记得'不一样'"

这正是 Δ-descriptor 的设计目标。当一个影子被修剪时：
- ❌ 不丢弃所有信息
- ✅ 保留 Δ-descriptor 的摘要到一个全局 `shadow_memory` 列表
- 这个列表是**系统对自身历史差异的记忆**

```python
# 修剪时不是删除，是压缩
def prune_dormant_fruit(self):
    if self.xin_dormant_fruit is not None:
        delta = self.xin_dormant_fruit.get("delta", {})
        self._shadow_memory.append({
            "d_momentum": delta.get("d_momentum", 0),
            "d_phase": delta.get("d_phase", 0),
            "age_at_death": current_tick - delta.get("created_tick", 0),
            "coherence": delta.get("coherence_with_main", 0),
        })
        self.xin_dormant_fruit = None
```

## 生物学映射

| Morphosphere 影子层 | 生物学 |
|---------------------|--------|
| dormant fruit | **海马体记忆痕迹**：经历→编码→巩固/遗忘 |
| Δ-descriptor | **神经重放（replay）时的变异**：睡眠中重放不是精确复制 |
| shadow_memory（修剪后） | **语义记忆**：不记得具体细节，但记得"那次不一样" |
| coherence 决定存亡 | **记忆竞争**：与当前理解一致的记忆更持久 |
| 影子回归 | **创伤后闪回**：被压抑的记忆因相似情境被激活 |
