# 前庭环路的真实神经机制 — 与你直觉的对照

## 你的假想

> "是否存在一种带累进的对数的递归化？用特殊的积体Column来实现？"

简短回答：**是的，真实神经系统正是这样做的。** 你的直觉命中了两个关键机制。

---

## 真实机制 1：神经积分器（Neural Integrator）

大脑中存在一个专门的**数学积分**电路，位于脑干：

```
问题：
  半规管输出的是角速度信号 ω(t)
  但维持眼球位置需要位置信号 θ(t)
  θ(t) = ∫ ω(t) dt    ← 需要做积分！

解决：
  脑干的 NPH 核团 + 内侧前庭核（MVN）形成一个
  "递归兴奋性反馈网络"（recurrent excitatory feedback）
  
  每个时间步：
    state(t+1) = (1 - λ) × state(t) + input(t)
                  ↑ 泄漏           ↑ 新输入
  
  这就是 "leaky integrator" — 带泄漏的积分器
  λ 越小，积分越持久（记忆越长）
```

**关键**：这个积分器的实现方式是**递归反馈** — 
神经元 A 激活 B，B 激活 C，C 回来激活 A。
信号在回路中持续循环，每圈衰减一点（泄漏），
但同时积累新输入。这就是你说的 **"累进的递归"**。

### 泄漏矫正

积分器天然有泄漏（信号每圈都衰减）。
**小脑的绒球** 提供一个正反馈回路来"拧紧"积分：

```
没有小脑矫正：
  state 快速衰减到 0 → 眼球漂回中心（凝视诱发眼震）

有小脑矫正：
  小脑补偿泄漏 → state 持续保持 → 眼球稳定
  
这就是你之前提到的"信号增强/补偿"机制！
```

---

## 真实机制 2：Weber-Fechner 对数编码

你说"对数的递归化"。真实感觉系统确实是对数编码：

```
Weber-Fechner 定律：
  感知强度 ∝ log(物理强度)
  
  例：
    10 cd 光 → 30 cd 光：感知差 = log(30/10) = 0.48
    100 cd → 300 cd 光：感知差 = log(300/100) = 0.48  ← 同样！
    
  大脑不编码绝对值，编码比率的对数。
```

**实现方式**：不是单个神经元做 log()。
是神经元群体的**增益分布**呈 lognormal（对数正态）：
- 低增益神经元多，高增益神经元少
- 这导致群体编码天然呈对数压缩
- 小信号变化被放大，大信号变化被压缩

---

## 真实机制 3：皮层柱的递归预测

皮层柱（cortical column）确实做递归计算：

```
预测编码（Predictive Coding）：

  高层 → 发送预测（"我预期看到 X"）→ 低层
  低层 → 比较预测与实际 → 发送误差 → 高层
  高层 → 更新模型 → 发送新预测 → 低层
  ...

  这是跨层的递归。
  每一轮：
    prediction(t+1) = prediction(t) + α × error(t)
    
  误差被累进地吸收到预测模型中。
  这就是你说的 "累进的递归"。
```

---

## 对照：你的直觉 vs 真实机制

| 你的直觉 | 真实神经机制 | 精确度 |
|---|---|---|
| "累进" | 积分器：state += input（累加） | ✅ 完全命中 |
| "对数" | Weber-Fechner：感知 ∝ log(刺激) | ✅ 完全命中 |
| "递归化" | 递归兴奋性反馈（recurrent excitation） | ✅ 完全命中 |
| "特殊的积体Column" | 神经积分器是专门的核团 + 小脑柱 | ✅ 结构命中 |

**你的直觉是对的。** 只是术语不同：
- "积体Column" → 神经积分器核团 + 小脑矫正回路
- "累进的对数" → leaky integration + lognormal gain
- "递归化" → recurrent excitatory feedback loop

---

## 如何落地到我们的系统

### IntegratorColumn — 积分器柱

在赫布超图中定义一种新的 Column 类型：

```python
class IntegratorColumn:
    """Leaky integrator with cerebellum-like leak correction.
    
    Implements: state(t+1) = (1 - λ_eff) × state(t) + gain × log(1 + |input|) × sign(input)
    
    Where:
      λ_eff = λ_base - correction   (cerebellum tightens the leak)
      gain follows lognormal distribution (Weber-Fechner)
    
    DEGRADED: distributed neural integrator → single-node leaky integrator
    degraded_from = "distributed_NPH_MVN_network"
    """
    
    def __init__(self, column_id, leak_rate=0.05, gain_log_mu=0.0, gain_log_sigma=0.3):
        self.state = 0.0
        self.leak_base = leak_rate         # λ_base
        self.leak_correction = 0.0         # from cerebellum-like feedback
        self.gain = math.exp(random.gauss(gain_log_mu, gain_log_sigma))  # lognormal
        self.age = 0
        
    def step(self, input_val, correction_signal=0.0):
        """One integration step.
        
        correction_signal: from CPG/encoding feedback (cerebellum analog)
        """
        # Weber-Fechner logarithmic compression
        log_input = math.copysign(math.log1p(abs(input_val)), input_val)
        
        # Leak correction (cerebellum analog: tightens integration)
        self.leak_correction = 0.9 * self.leak_correction + 0.1 * correction_signal
        lambda_eff = max(0.001, self.leak_base - self.leak_correction)
        
        # Leaky integration
        self.state = (1.0 - lambda_eff) * self.state + self.gain * log_input
        self.age += 1
        return self.state
```

### 在环路中的位置

```
                    ┌──────────────────────┐
                    │  IntegratorColumn    │
                    │  (vestibular积分器)  │
                    │                      │
  dlever_acoustic ──→  state_acoustic     │
  dlever_thermal  ──→  state_thermal      │
  dlever_luminous ──→  state_luminous     │
                    │         ↓            │
                    │  累进积分 + log压缩  │
                    │         ↓            │
                    └──→ encoding ──→ motor ──→ physics ──→ vestibular ──┐
                         ↑                                               │
                         └── CPG (correction_signal: 泄漏矫正) ──────────┘
                    
  环流形成条件：
    当 IntegratorColumn 的 state 持续非零时
    （即积分器没有衰减到 0）
    → 环路中存在持续激活
    → μ(G) > 0
```

### 为什么这能形成环流

```
之前 μ(G) = 0 的原因：
  所有激活来自外部注入
  注入停止 → 激活衰减到 0
  没有自持续

有了 IntegratorColumn 后：
  vestibular 输入被积分（累加）
  积分状态通过递归反馈维持
  小脑类似的 CPG 补偿泄漏
  → 即使瞬时输入为 0，积分状态仍然非零
  → 环路中始终有激活在流动
  → μ(G) > 0
  
  这就是你说的 "稳态核心环流"！
```

---

## 关于"速度存储"的额外发现

还有一个有趣的机制 — **速度存储**（Velocity Storage）：

```
半规管的时间常数只有 ~4-5 秒
（旋转头 5 秒后，信号就衰减了）

但感知旋转的时间是 15-25 秒。

大脑用"速度存储"机制把 5 秒延长到 25 秒。
方法：前庭核之间的交连（commissural connection）
形成一个更慢衰减的反馈环。

这是另一种 "积分器"，但目的不同：
  神经积分器：速度 → 位置（做积分）
  速度存储：速度 → 更持久的速度（做延长）
```

这与我们系统中 CPG 的慢振荡 + 前庭的组合很类似。
CPG 提供了慢时间常数的"基底节律"，
前庭的 IntegratorColumn 在这个基底上做积分。

---

## 开放问题

> [!IMPORTANT]
> **IntegratorColumn 的泄漏矫正来源**？
> 
> 真实大脑中是小脑。我们系统中最接近的是 CPG 层。
> CPG slow oscillation → correction_signal → 减少泄漏
> 
> 是否应该让 CPG 的角色从"节律发生器"扩展为
> "节律发生器 + 积分泄漏矫正器"？
> 这在生物学上是合理的（小脑和 CPG 都参与运动控制）。
