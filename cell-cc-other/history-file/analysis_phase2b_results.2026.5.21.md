# Phase 2b 实测结果分析

## 实验参数

```
电路: 20 neurons, 10 bundles (from Allen Brain W_signal)
运行: 120 ticks
观测: CircuitObserver 每 tick 记录 rho + Xin flow
```

---

## 关键发现 1: Xin 占据 97.8% 的信息预算

```
Average rho over 99 ticks:
  p_core:     0.004   (P 环流只占 0.4%)
  p_band:     0.004
  r_core:     0.000   (R 环流几乎为 0)
  r_band:     0.004
  masking:    0.001
  xin:        0.978   ← 97.8% 是未解决的 Xin tension
  unresolved: 0.009

趋势:
  xin: 0.958 >>> 0.998  (越来越被 Xin 主导)
  p_core: 0.008 → 0.000  (P 相对占比在缩小)
```

### 诊断

```
Xin tension 在累积, 但没有被消耗:
  tick 10:  Xin = 48
  tick 50:  Xin = 307
  tick 90:  Xin = 599

增长率 ≈ 6.7/tick, 线性增长, 没有饱和

原因:
  1. 没有果实激活 (fruit_consumed = 0)
  2. Xin 没有被 P 吸收 (absorbed 记录显示全是负的)
  3. 守恒误差 ≈ 13.6/tick (有大量未追踪的 Xin 来源)

这意味着:
  每个 tick 产生的预测误差 (predicted - actual)
  全部堆积在 bundle 上, 从未被解决
```

---

## 关键发现 2: P 环流存在且非常稳定

```
P 环流: 100/100 个 tick 都检测到 P
R 环流: 100/100 个 tick 都检测到 R
环流路径: bundle_4af26cb5 → bundle_5bb67d6b

固化候选的健康分数:
  continuity:      0.996  (极高 — 变化平滑)
  conservation:    0.982  (极高 — 能量稳定)
  phase_coherence: 0.978  (极高 — 相位一致)
  overall_health:  0.839  (可以固化)

XOR 比对:
  当前快照 vs 固化模式: distance = 0.000 (完全匹配)
  当前快照 vs 早期模式: distance = 0.000 (也完全匹配)
```

### 诊断

```
环流存在, 但它是"冻结"的:
  20 个神经元的激活模式几乎不变
  distance = 0 意味着没有动态变化

这不是真正的"运动", 而是一个静态模式
类似于前神经分析中发现的"准静止"状态

P 环流只通过 2 个 bundle (很短的环路)
整个 20 个神经元都在同一种状态
```

---

## 关键发现 3: 无成熟

```
Start: spine=20, column=0, area=0
End:   spine=20, column=0, area=0

120 个 tick 没有任何神经元从 spine 晋升到 column

这可能是因为:
  1. 成熟阈值太高
  2. calcium 积累不够
  3. 环流太弱 (只占 0.4%)
```

---

## 根本问题: 输入不够分化

```
当前输入: 6 个信号特征 → 13 个 encoding 神经元 → 7 个 column 神经元
所有神经元接收相似的信号 → 所有神经元处于相似的激活状态
→ XOR distance = 0 (全部一样)
→ 只有一种模式 (准静止)
→ Xin 累积 (预测误差不被解决)

需要: 输入分化
  不同神经元接收不同方面的信息
  才会产生不同的激活模式
  才会有真正的运动状态分离
```

---

## 下一步行动

```
选项 A: 修复输入端 (Phase 1)
  修改 _compute_sensory → 多通道分离
  让不同元单元组收到不同类型的信号
  这样才会产生可区分的激活模式

选项 B: 修复 Xin 消耗机制
  当前 Xin 只累积不消耗
  需要: fruit 激活条件放松, 或 R 消解机制
  让 Xin 有出口

选项 C: 利用已有的 VestibularSystem
  当前 vestibular_system.py 的 6 轴信号
  没有被接入 HebbianCircuit
  接入后可以提供运动类型信号分化

推荐: 先 B (修 Xin) → 然后 C (接入前庭)
  因为 B 是外部修复 (Xin 消耗策略)
  C 是利用已有模块
  都不需要大改主线
```
