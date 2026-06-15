# 影子层与小环流假设 — 建模分析

## 当前系统中"影子"类结构的实际状态

300 tick 运行后的盘点：

| 结构 | 设计意图 | 实际状态 | 活跃? |
|------|---------|---------|-------|
| **Ghost bundles** | 被剪枝 bundle 的残留"记忆" | 0 个 | ❌ 从未产生 |
| **Dormant fruits** | 张力持续时的影子果实 | 0 个 | ❌ 从未产生 |
| **Convergence nodes** | z_t 维度的共激活结构 | 21 个, 但 strength ≈ 0.00003 | ⚠️ 存在但极弱 |
| **P/R circulation** | 主/副环流 | P=R (退化) | ⚠️ 无竞争 |
| **Sediment inbox** | z_t 快照的沉积缓冲 | 0 项 | ❌ 从未填充 |
| **Practice cortex** | 运动-前庭分化 | 不在 layers dict 中 | ❌ 未创建 |

### 关键诊断

**P = R** — 主环流和副环流退化为同一条路径。

```
P = ['bundle_bacdb370', 'bundle_d31dd9f0']
R = ['bundle_bacdb370', 'bundle_d31dd9f0']
```

这意味着：系统中**只有一条闭合路径**，没有竞争。
P/R 的设计意图是 "winner-take-most"，但只有一个候选人 → 无需竞争。

**Convergence nodes 强度 ≈ 0.00003** — 存在但没有被强化。

每 tick decay × 0.99 → 100 tick 后 strength = 0.99^100 = 0.366×
但初始增长 << decay → 强度收敛到极小值。

---

## 你的假设：影子层沉积 + 环流耦合

按我理解，你的构想是：

```
  encoding 处理信号
       │
       ├── 正向: → column → motor (主通路)
       │
       └── 副本: → 影子层 (沉积)
                    │
                    ├── 行为 A 的副本
                    ├── 行为 B 的副本
                    └── 行为 C 的副本
                         │
                         ▼
                    耦合/竞争 → 产生新模式
                    (小环流在影子层中形成)
```

### 这对应 Maxwell 妖循环的哪一步？

```
观察 → 记住 → 行动 → 擦除
  │       │       │       │
  │       │       │       └── 影子层: 用完的副本被选择性清除
  │       │       └── 耦合后的新模式驱动 motor
  │       └── 副本沉积到影子层
  └── encoding 接收信号
```

**影子层恰好可以充当 Szilard 引擎的"记忆寄存器"：**
- 沉积 = 存储观察结果
- 耦合 = 利用存储的信息做决策
- 衰减 = Landauer 擦除 (每次擦除 ≥ kT ln2 热)

---

## 建模：影子层假设的可行性分析

### 问题 1：副本从哪来？

当前系统中，encoding → column 的信号通过 **inter_layer_bundle** 传递。
副本意味着同一信号到达两个目的地：column 和 shadow。

**实现方式**：inter_layer_bundle 的输出分叉：

```
encoding → [inter_layer_bundle] → column  (主)
                              └→ shadow  (副本)
```

这在超图拓扑中就是：同一个超边连接 3 个节点而非 2 个。
**不需要新的 bundle 类型**，只需要现有 bundle 多一个 target。

### 问题 2：影子层内的耦合机制

副本 A、B、C 在影子层中共存。
"耦合"是什么意思？——**不同行为副本之间的干涉/竞争**。

物理类比：这像**全息存储器**——不同记忆叠加在同一基底上，
通过相位匹配（余弦相似度）来提取。

建模为：

```
shadow_activation[i] = Σ_k  copy_k[i] × strength_k

当两个副本 A、B 在同一个 shadow neuron i 上叠加时：
  如果 A[i] 和 B[i] 同号 → 增强 (建设性干涉)
  如果异号 → 抑制 (破坏性干涉)

net_pattern = 干涉后的残余模式
```

**这正是 convergence_node 设计的原始意图** — 共激活检测。
只是当前实现太弱 (strength ≈ 0.00003)。

### 问题 3：耦合后如何驱动 motor？

影子层的耦合输出需要一条路径到达 motor 层：

```
shadow → [shadow_motor_bundle] → motor
```

这条路径不存在于当前系统中。

### 问题 4：擦除如何发生？

影子层中"用完"的副本需要被清除。
"用完"的判据：**副本已被耦合并传递给 motor 后，不再需要**。

这对应于 ghost_bundle 的设计——被剪枝的 bundle 留下 ghost 残留，
ghost 强度以 0.995/tick 衰减 → 最终消失 = 擦除。

**但当前 ghost 从未产生**（因为 bundle 从未被剪枝）。

---

## 可行性裁决

| 条件 | 现状 | 可行? |
|------|------|-------|
| 信号副本分叉 | inter_layer 只连 column | ⚠️ 需要加 target |
| 影子层存在 | 无独立 shadow layer | ❌ 需要创建 |
| 层内耦合机制 | convergence_nodes 存在但极弱 | ⚠️ 机制在，强度不够 |
| shadow → motor 通路 | 不存在 | ❌ 需要创建 |
| 选择性擦除 | ghost 机制从未触发 | ⚠️ 代码在，条件不满足 |

### 假设的理论预测

如果影子层假设成立，应该观察到：

| 预测 | 可测量 | 含义 |
|------|--------|------|
| **S1**: 影子层积累多模式叠加 | S_shadow > S_encoding | 信息在影子层中叠加 |
| **S2**: 耦合后产生新模式 | cos(shadow_output, 任何单一 copy) < 1 | 干涉产生了原始输入中不存在的模式 |
| **S3**: motor 在耦合后被激活 | motor 层 activation > 0 | 信息 → 行动的闭环 |
| **S4**: ghost 产生速率与 motor 输出相关 | corr(ghost_rate, motor_act) > 0 | 行动后擦除（Szilard 完成） |
| **S5**: 系统信息积累效率提升 | η_Szilard > 0 | 闭环比开环更高效 |

> [!IMPORTANT]
> **S2 是最关键的预测。**
> 如果影子层只是简单复制+衰减，那它就是个冗余存储——没有价值。
> 只有当**耦合产生了输入中不存在的新模式**时，影子层才有信息论意义。
> 这对应于：系统从多个行为的**叠加**中提取了**任何单个行为都不包含**的结构。

### 与当前系统的关系

影子层假设实际上是在说：**convergence_node 不应该只是一个计数器，
它应该是一个有独立激活、独立权重的 neuron/layer**。

当前：
```
convergence_node = {strength: float}  ← 只是一个数字
```

假设中的影子层：
```
shadow_neuron = MetaNeuron(...)       ← 有激活、阈值、能量
shadow_bundle = bundle 到 motor       ← 可以驱动输出
```

**convergence_node 是影子层的退化形式** — 去掉了激活、权重、输出，只留了一个强度计数器。

---

## 结论

> [!IMPORTANT]
> **影子层假设在理论上是可行的**，它恰好填补了 Szilard 循环的缺口：
> 
> 1. 沉积 = Szilard 的"记忆写入"
> 2. 耦合 = "利用记忆做功" 
> 3. 选择性擦除 = "Landauer 擦除"
> 4. motor 输出 = "提取的功"
> 
> 但在当前系统中，5 个前置条件中有 2 个完全不存在 (shadow layer, shadow→motor)，
> 2 个存在但未激活 (convergence, ghost)。
> 
> **不建议立即实现** — 先验证 S2 (耦合是否产生新模式) 的数学可行性。
> 如果两个模式 A、B 的叠加不能产生新结构，整个假设就不成立。
