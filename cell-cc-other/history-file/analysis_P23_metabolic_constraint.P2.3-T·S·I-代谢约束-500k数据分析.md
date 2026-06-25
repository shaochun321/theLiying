# P2.3 T·S·I 代谢约束 — 500k 数据分析

> **Date**: 2026-06-08 | **Data**: EXP-007 500k P2.1 | **Status**: ✅ 完成

---

## 核心发现

> [!CAUTION]
> **系统从未达到能量自给自足。**
> DA refill (0.003/step) > 世界总产能 (0.002/step)。
> 增长完全靠初始储备 (E₀=500) 维持。

---

## §1 能量预算审计

### 500k 实测值

```
deposited  = 1108.8  (500k 步总入)
withdrawn  = 1571.1  (500k 步总出)
deficit    = -462.3  (来自 initial fill 500)
Noether    = 0.0     (完美守恒)
```

### 每步功率

| 项目 | 值/step | 占消耗比 |
|---|---|---|
| P_deposit (实际) | 0.002218 | — |
| P_DA refill (3 neurons) | 0.003000 | 95.6% |
| P_ES basal drain | 0.000100 | 3.2% |
| P_bundle basal (N=67) | 0.000034 | 1.1% |
| **P_net** | **-0.000882** | — |

> **DA 消耗 > 世界总产能。** Bundle basal cost 仅占 1.1%。
> P2.1 的热力学天花板本意是 bundle 代谢墙，但实际是 **DA 饥饿墙**。

### P_deposit 为什么这么低？

```
max_deposit_per_step = 0.05  (设计值)
actual deposit rate  = 0.002 (实测，仅 4.4%)
```

原因: `world.consume_nearby(position, CONSUME_RATE=0.15, dt=0.001)` 
- body 大部分时间**远离热源** (distance > 30)
- `energy ∝ 1/distance²` → 距离远时几乎无收入
- 初始距离 20 → 一些收入；漂移远离 → 收入 → 0

---

## §2 T·S·I 约束简化

### 原始提案 (Phase 1)

$$T \cdot S \cdot I \leq P_{input}$$

### 500k 数据验证

| T (recovery) | S (structure) | I (information) | Product |
|---|---|---|---|
| 不可定义 | N | mean_xi | — |

**问题**: T_recovery = E_sprout / P_net，但 P_net < 0 → T = ∞。
系统从来不"恢复"，而是持续消耗储备直到枯竭。

### 正确表述

$$N_{max} = \frac{E_0}{(\sum P_{drain} - P_{deposit}) \times \Delta t_{growth}}$$

其中:
- E₀ = 初始储备 = 500
- ΣP_drain ≈ P_DA + P_basal + N·P_bundle
- P_deposit ≈ 0.002 (取决于距离)
- Δt_growth = 25000 (sprout interval)

代入:
```
P_drain(N=67) = 0.003 + 0.0001 + 67×5e-6 = 0.003435
P_net = 0.002218 - 0.003435 = -0.001217
E_consumed at step 125k = 125000 × 0.001217 ≈ 152
E_initial = 500
→ 500 - 152 = 348 已消耗 (实测 ES=66, 约=500-434)
```

偏差说明 DA refill 不是每步都消耗 0.003（有 delivered < requested 的情况）。

---

## §3 对 T·S·I 理论的影响

### 三个结论

1. **T·S·I 的 T 不是"恢复时间"** — 在能量亏损状态下无恢复可言。
   正确理解: T = 储备续航时间 = E₀/|P_net|

2. **S 的增长受限于储备深度，非稳态能量流** — 
   这是一个**暂态**系统，不是稳态系统。
   数字生命体在"消耗遗产"，没有可持续收入。

3. **I_norm ≈ 0.664 (此前发现) 的物理意义** — 
   Xin 分布均匀性在 N 变化时不变，说明**结构生长保持了信息分配公平性**。
   这可能是 T·S·I 中唯一的真正不变量。

### 修正路线

| 方案 | 做法 | 效果 |
|---|---|---|
| A: 提高世界产能 | CONSUME_RATE↑ 或热源更近 | 可能使 P_net > 0 |
| B: 降低 DA 消耗 | DA_REFILL_RATE 0.001→0.0003 | 使 P_DA < P_deposit |
| C: DA 按需 refill | 仅在 DA < threshold 时 refill | 减少浪费 |
| D: 接受暂态 | 设计"进食行为"增加 P_deposit | 热趋性闭环！|

> [!IMPORTANT]
> **方案 D 才是正确答案。** 
> 系统*应该*能量不足，这正是**热趋性行为**的驱动力。
> 如果系统能量自足就不需要"吃东西"了。
> 
> 问题不是 P_net < 0，而是系统**有没有学会向热源移动以增加 P_deposit**。
> → 这正是 EXP-009 (1.1 thermotaxis) 测试的内容。

---

## §4 预测

如果热趋性存在 (EXP-009 positive):
- P_deposit 将随距离减小而增加
- P_net 可能翻正 → 真正的稳态
- N_max 将由稳态 P_net 决定 → T·S·I 框架重新成立

如果热趋性不存在 (EXP-009 negative):
- 系统永远是暂态
- 需要 C3' 进食-运动耦合 (deviation→DA→motor→approach)
- 或需要提高 CONSUME_RATE / 降低 DA_REFILL_RATE
