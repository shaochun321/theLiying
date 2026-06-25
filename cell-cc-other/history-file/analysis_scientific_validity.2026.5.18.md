# 科学发现真实性审计

## 一、审计方法

对每项"发现"，问三个问题：
1. **这是不是参数的直接后果？** (如果换参数就消失 → 不是发现)
2. **这是不是非平凡的？** (需要运行模拟才知道，不能从公式直接推 → 是发现)
3. **这对理解现实系统有没有预测力？** (能否设计实验验证 → 有价值)

---

## 二、逐项审计

### 发现 1: DERC 阶梯效应

**声称**: n≤1 时 E[L] 恒定，n>1 时急降。

**审计**:
```python
injection_scale = 1.0 / (spacing ** max(0, n - 1))
# spacing = 2.0
# n=0.5: scale = 1/(2^(-0.5)) = √2 ≈ 1.41
# n=1.0: scale = 1/(2^0) = 1.0
# n=1.5: scale = 1/(2^0.5) = 0.71
# n=2.0: scale = 1/(2^1) = 0.5
```

> [!WARNING]
> **部分循环**。阶梯的位置 n_c=1 是 `spacing^(n-1)` 公式中 n=1 时
> scale=1 的直接后果。如果我们选 spacing=1，阶梯消失（所有 n 的
> scale 都等于 1）。如果 spacing=3，阶梯更陡。
>
> 阶梯的**存在**是非平凡的（离散晶格 + 注入公式的交互），
> 但阶梯的**位置**是参数选择的结果。

**判定**: ⚠️ **半有效** — 离散化本身产生阈值效应是真的，但 n_c=1 不是普遍物理规律。

---

### 发现 2: 热觉近场 L_pen = 0.71

**声称**: 从材料三元组 (m=5, k=0.2, γ=0.02) 自动涌现。

**审计**:
```python
κ = k / (m * d²) = 0.2 / (5 * 4) = 0.01
L_pen = √(κ/γ) = √(0.01/0.02) = √0.5 = 0.707
```

> [!CAUTION]
> **循环**。我们选了 m=5, k=0.2, γ=0.02 **然后** 说 L_pen=0.71
> "正确反映了热觉近场"。但这些参数不是从第一性原理推导的 ——
> 它们是人为设定的。如果选 k=2.0，L_pen 就是 2.24，"热觉"
> 就变成了中场感知。
>
> 参数的选择没有独立于结论。

**判定**: ❌ **循环论证** — 结论预设在参数中。

---

### 发现 3: 反弹消失

**声称**: 介质传播消除了 n>2.5 的反弹。

**审计**:
分析模型中反弹的来源：当 n 大时，∇Φ = -nA/r^(n+1) 在近场
极大。agent 被强力推出。

介质模型中：晶格传播天然平滑了近场梯度（离散化效应）。

> [!NOTE]
> **有效但平凡**。任何空间离散化都会平滑极端梯度。
> 这不是介质物理的特殊性质 —— 它是 "有限网格分辨率" 的
> 一般性质。如果我们把解析场也做网格平滑（moving average），
> 反弹同样会消失。

**判定**: ⚠️ **有效但不惊人** — 是数值方法的已知性质。

---

### 发现 4: HH 动力学

**声称**: AP 幅度 90.5 mV，阈值 I=7 μA/cm²。

**审计**: HH 方程是 1952 年的经典物理模型。我们正确实现了它。这不是"发现"，是"实现"。

**判定**: ✅ **正确实现** — 但不是发现。

---

### 发现 5: 前庭 6 轴

**声称**: 从粒子运动中涌现出 angular velocity 和 linear acceleration。

**审计**: 角动量 L = Σ r×p 和 COM 加速度 Δv/Δt 是经典力学公式。
我们只是计算了它们。

**判定**: ✅ **正确计算** — 但不是发现。是工程实现。

---

### 发现 6: 本体感觉

**声称**: 148 个关节角度、spindle Ia/II、Golgi tendon。

**审计**: 这些是从弹簧网络拓扑计算的几何量。正确，但不惊人。

**判定**: ✅ **正确计算** — 工程实现，不是发现。

---

## 三、什么是真的？

### 真正有价值的东西

上述"发现"大部分是**实现**，不是**发现**。但项目的真正价值不在这些数字上。

**项目的真正贡献是架构本身**：

| 贡献 | 性质 | 价值 |
|---|---|---|
| T/O/P/R/Xin 生命周期 | 框架 | 提供了一种描述神经结构动力学的语言 |
| DEGRADED/RECOVERED 标注 | 方法论 | 系统化的简化追踪，科学上很有价值 |
| 结构动力学不变量 | 设计原则 | 确保每个字段有生成/衰减/耦合 |
| 物理引擎→感知管道 | 工程 | 59 通道的闭环感知系统 |
| 熵账本代理 | 架构 | 将热力学约束注入计算 |

### 赫布超图的真实状态

```
HebbianCircuit 内部:
  MetaNeuron: activation + STDP traces + calcium + threshold + energy
  MetaSynapticBundle: weights + transport cost + dorman fruit
  CircuitLayer: lateral inhibition (divisive normalization)
  T/O/P/R/Xin: transport → observe → circulation → residual
  
  这是一个完整的、自洽的信号处理框架 ✅
```

但关键问题：

```
PracticeEngine.step():
  sensory = {...59 channels...}
  return sensory  ← 返回给谁？

调用者 (runner) 应该做:
  motor = circuit.transport(sensory, "input_layer")
  sensory = engine.step(motor)
  
  这个循环是否畅通？
```

---

## 四、信息管道审计

### 当前的管道

```
         HebbianCircuit
         ┌──────────────────┐
sensory →│ transport()       │→ motor
  59ch   │ observe()         │  3ch
         │ detect_circul()   │
         │ resolve_xin()     │
         └──────────────────┘
              ↑
              │ 但: practice_engine 
              │ 不直接调用 circuit!
              │ 它只产生 sensory dict
              │ 并接收 circuit_motor
              │
              │ runner 负责连接:
              │ runner.py:
              │   sensory = engine.step(motor)
              │   motor = circuit.transport(sensory)
              │   ...
              ↓
```

### 管道断点

| 环节 | 状态 | 问题 |
|---|---|---|
| 源→介质→梯度 | ✅ 畅通 | Medium3D 正确传播 |
| 梯度→反射→motor | ✅ 畅通 | compute_reflex() 硬编码 |
| 物理→sensory | ✅ 畅通 | 59 通道 |
| sensory→HebbianCircuit | ⚠️ **依赖 runner** | engine 不管 circuit |
| HebbianCircuit→motor | ⚠️ **依赖 runner** | circuit output → engine input |
| HH spike→任何决策 | ❌ **断开** | spike 只在体内传播 |
| 前庭/本体→任何决策 | ❌ **断开** | 输出到 sensory 后无人读取 |

### 真正需要畅通的管道

```
Phase 5 的正确目标不是 STDP —— 是管道畅通:

1. 确保 sensory 59 通道 → HebbianCircuit.transport() 正确映射
2. 确保 circuit motor output → engine step() 有实际效果
3. 确保 T/O/P/R/Xin 周期在 59 通道输入下正常运转
4. 确保 circuit 的 weight 更新（已有 STDP trace!）在闭环中收敛
```

---

## 五、关于"粒子分化"

> 用户说: "粒子分化我看不太懂"

放弃粒子分化方案。原因：

1. HebbianCircuit 的 MetaNeuron **已经有** STDP trace, calcium, 
   threshold adaptation —— 这些都比 HH 粒子的 spike 更适合
   做"认知层"的可塑性。

2. 正确的架构是 **两层分离**:
   - 下层: ParticleSystem3D + HH → 产生 sensory（身体）
   - 上层: HebbianCircuit + T/O/P/R/Xin → 处理 sensory，输出 motor（脑）
   
3. STDP 应该发生在 **HebbianCircuit 层**（MetaNeuron 已经有
   pre_trace/post_trace），不是在 HH 粒子层。

---

## 六、结论

> [!IMPORTANT]
> **项目获得的不是"科学发现"——是一个正确构建的物理-认知框架。**
>
> T/O/P/R/Xin + HebbianCircuit 的价值在于它提供了一种
> **结构化的降级追踪方法**。这个方法论本身就是贡献。
>
> "科学发现"需要等到管道畅通后、agent 在闭环中展现出
> 不可从参数直接推导的行为时才能声称。

### 下一步应该做什么

不是 STDP。是**管道畅通**：

```
Step 1: 写一个完整的 runner，将 engine + circuit 闭环
Step 2: 确认 59 通道正确映射到 circuit neurons
Step 3: 确认 circuit motor 输出有实际行为效应
Step 4: 跑 1000 ticks，观察 T/O/P/R/Xin 是否正常循环
Step 5: 然后才讨论 STDP / 涌现 / 科学发现
```
