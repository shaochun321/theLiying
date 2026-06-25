# EXP-018 诊断报告：200k 步验证结果

## 核心数据

| 指标 | 结果 | 预期 | 判定 |
|------|------|------|------|
| **Δx** | **+0.102** | > 1.0 | ❌ 未达标 |
| Thermal bundle weights | 0.097→0.091 (**-5.2%**) | 增长 | ❌ 衰减 |
| DA concentration | 0.0（80%步数） | 动态调制 | ❌ 崩塌 |
| Speed | 0.0005 | > 0.005 | ❌ 过低 |
| Skin T front-back diff | **+0.43** | — | ✅ 梯度存在 |
| Energy store | 0.50→0.15 | — | ⚠️ 持续消耗 |

**距离轨迹方向正确**（20.00→19.90），但幅度极小。

---

## 三大根因

### 根因 1：DA 崩塌 → 反射增益反被削弱

DA=0.0 占了 200k 步中 160k 步（30k-180k）。这触发了我们自己设计的 DA 调制的**反效果**：

```
DA=0 → da_factor = da_min_gain = 0.5
有效增益 = hunger_approach_gain × da_factor = 0.6 × 0.5 = 0.3
```

**改之前**的增益是 0.3，**改之后**在 DA=0 时有效增益还是 0.3。DA 调制没有帮上忙，反而在 DA 低时起了约束作用。

**为什么 DA=0？** 战役一的"DA 净空锁"（shadow_to_da 权重 1.0→0.1）大幅抑制了 DA 产生。没有足够的运动→没有足够的预测误差→DA 无法重新激活。

### 根因 2：Thermal bundle 权重衰减 — STDP 支架失效

| 时间 | move_x 权重 | move_y 权重 |
|------|------------|------------|
| 0k | 0.097 | 0.081 |
| 50k | 0.091 | 0.075 |
| 200k | 0.091 | 0.075 |

权重在前 50k 步下降后**冻结**。原因：

1. Motor 几乎不放电（speed=0.0005）→ **无 post-synaptic trace**
2. 无 post-trace → STDP 无法检测因果关系（"fire together, wire together" 的前提是 motor 要 fire）
3. `decay_rate_by_stage=(0.5, 0.1, 0.01)` 在 stage 1（权重<阈值）衰减率 0.5 → 权重被推向 0.091 然后稳定

**支架效应需要反射层先产生足够的运动**，但反射层被 DA=0 抑制了。形成了**死锁**：
```
反射弱 → motor不放电 → STDP无法学习 → 权重衰减 → 更弱
```

### 根因 3：双源 bundle 架构不区分方向

新建的 bundle 是：
```
sources=[therm_front, therm_back] → targets=[move_x]
```

两个热感柱作为**同一个 bundle 的源**，各自有独立的 memristor 权重：
- `_memristors[0][0]` = therm_front → move_x = 0.091
- `_memristors[1][0]` = therm_back → move_x = 0.091

但两个权重几乎相同（都是 0.091），所以 bundle 的净效果是：
```
I_move_x = (act_front × 0.091 + act_back × 0.091) × gain
```

这是一个**常数驱动**，不是**梯度驱动**。无论热源在前还是后，motor 收到的电流差异极小。STDP 理论上能学出差异化权重（front>back），但需要 motor 先有方向性放电——又是死锁。

---

## 修复方向

### 方向 A：解除 DA 底线约束

```python
# 当前：DA=0 → da_factor=0.5 → 削弱反射
# 修复：DA 调制只增强不削弱
da_min_gain: float = 1.0    # DA=0: 原始增益（不惩罚）
da_max_gain: float = 2.0    # DA=1: 双倍增益（奖励）
```

物理意义：反射是先天行为，不应被 DA 抑制。DA 只应该**放大**反射（正调制），不**衰减**反射。

### 方向 B：拆分 thermal bundle 为差分对

```python
# 当前：[therm_front, therm_back] → move_x (共用 bundle)
# 修复：拆成两个独立 bundle
#   therm_front → move_x (正向: 前方热→前进)
#   therm_back  → move_x (反向: 后方热→后退，或 gain 为负)
```

这样 STDP 可以独立学习每个方向的权重。

### 方向 C：提高反射层的直接驱动力（打破死锁）

当前 hunger reflex 的输出 = `delta_x × gain × da_factor × gate_factor`。如果 thermoreceptor activation 差异太小（两端都饱和在高值），delta 就很小。

需要确认 thermoreceptor activations 是否饱和。如果 `activation ≈ 10.0` 对所有 patch，则 `delta = 10.2 - 7.8 = 2.4`，这其实不小。问题可能在 gate 或 inject 后被其他力抵消。
