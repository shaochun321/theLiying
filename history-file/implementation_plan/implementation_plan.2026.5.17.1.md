# 修正计划 v2：量源-力臂-前庭-环流

## 关于"时空力臂"的批判修正

"时空力臂"不是标准物理术语，但你的直觉指向了真实的物理结构。
经查阅，最接近的精确表述：

### 你的概念映射到什么？

```
经典力学中：
  力臂 (moment arm) = 从旋转轴到力的作用线的垂直距离
  力矩 τ = r × F    （力臂 × 力 = 旋转效果）

你所描述的：
  系统主体 O 与量源 S 之间的"力臂" L = S - O
  运动改变 L → 改变接收到的量
  
  这对应的是 "广义力矩"（generalized moment）：
  M = L × (received_quantity_gradient)
  
  即：力臂不仅有长度，还有方向。
  运动不仅改变距离，还改变角度。
  角度变化产生的效应 ≠ 距离变化产生的效应。
```

### 更精确的物理表述

```
量源 S 在位置 xs 辐射场 Φ(r, t)

观测者 O 在位置 xo，以速度 v 运动

接收到的场值：
  Φ_received = Φ(|xs - xo|, t - |xs - xo|/c_signal)
                                    ↑ 传播延迟（retardation）

场对观测者运动的响应：
  dΦ/dt = ∂Φ/∂r · dr/dt + ∂Φ/∂t
         = (空间梯度 · 运动速度) + (场的本征时间变化)
         = 运动贡献 + 源变化贡献

  其中 ∂Φ/∂r · dr/dt 就是你说的"力臂变化所导致的量变化"
  它包含两部分：
    径向：d|L|/dt × ∂Φ/∂r    （靠近/远离 → 场强增减）
    切向：|L| × dθ/dt × ∂Φ/∂θ （绕着转 → 角度依赖的场变化）
```

### 修正建议

| 你的表述 | 更精确的物理表述 | 是否需要修改？ |
|---|---|---|
| "时空力臂" | "广义力矩"或"观测者-源相对位置矢量" | 用"相对位置矢量 L"更准确 |
| "力臂变化" | dL/dt = 相对速度 | ✓ 正确 |
| "内化为前庭" | 前庭 = 惯性测量 = d²L/dt²（加速度） | ✓ 正确，但应是二阶导 |

> [!NOTE]
> 你的表述在概念上是正确的。"力臂"这个词稍有误导（暗示了旋转），
> 但本质是对的：系统通过运动改变与量源的**几何关系**（距离+角度），
> 这个几何变化率被前庭系统编码为运动信号。

---

## 前庭 vs Origin — 确实是两种东西

```
前庭（Vestibular）：
  - 惯性测量单元（IMU）
  - 感知：线加速度、角加速度、重力方向
  - 类比：陀螺仪 + 加速度计
  - 在我们的系统中：d²L/dt² 的编码
  - 它是一个传感器层

Origin：
  - 概率收敛点
  - 不是传感器，是从数据中涌现的数学结构
  - 定义：运动因果效力的散度 → 1 的点
  - 它是一个统计量

两者的关系：
  前庭数据 ─┐
  运动数据 ─┤→ Origin Tracker → 概率收敛
  CPG数据  ─┘
  
  前庭提供数据，origin 从数据中涌现。
  就像耳朵提供声音信号，但"音乐"是从信号中涌现的结构。
```

### 真实前庭系统的关键特性

从文献中：

1. **倾斜-平移歧义**（Einstein 等价原理）：
   耳石器不能区分"头在加速"和"头在倾斜"。
   大脑用**半规管的角速度信号**来消歧。
   → 我们的前庭层需要**至少两种传感器**的交叉验证。

2. **参考系变换**：
   前庭信号最初在头坐标系中。要用于运动控制，
   必须变换到身体坐标系。小脑负责这个变换。
   → 我们的前庭层输出需要经过"坐标变换"才能到达 encoding。

3. **主动 vs 被动**：
   前庭系统能区分自己主动产生的运动和被动承受的运动。
   机制：**传出拷贝**（efference copy）。
   运动皮层发出命令的同时，发一份拷贝给前庭核，
   "我正在主动转头，所以预期会有角速度信号 — 忽略它。"
   → motor → vestibular 的 efference copy 束已经在计划中。

---

## 环流（Circulation）的定义

你说"环流的定义一直未跟你探讨"。让我尝试形式化：

### 在赫布超图中，环流是什么？

```
图 G 中的一个环流 C 是一组有向边 {e1, e2, ..., en}，
满足：
  1. 它们形成一个闭合回路（cycle）：
     target(e_i) = source(e_{i+1})  且  target(e_n) = source(e_1)
  
  2. 稳态条件（divergence-free）：
     每个节点的流入 = 流出
     Σ(incoming_activation) ≈ Σ(outgoing_activation)
  
  3. 自持续（self-sustaining）：
     即使外部输入为 0，环流仍然维持
     → 不需要外部驱动也能存在的激活回路
```

### 当前系统中的 μ(G) = 0.000 意味着什么

```
现在的系统没有满足条件(3)的回路。
所有激活都来自外部输入（signal entropy 或 CPG）。
一旦输入停止，所有激活衰减到 0。

需要的："核心环流" = 一个自持续的激活回路，
它在前庭-运动-CPG 之间形成闭环：

  前庭感知运动 → encoding → motor 发出命令 →
  physics 改变 → 力臂变化 → 前庭感知变化 →
  （回到开头）

如果这个回路的增益 > 衰减，它就会自持续。
它的稳态流就是"核心环流"。
```

### 核心环流与运动势共域

```
不同量源产生不同的"运动势"：
  Φ_acoustic(L) = A / |L|          （声场势）
  Φ_thermal(L) = B / |L|²          （热场势）
  Φ_luminous(L) = C / |L|²         （光场势）

每个势都定义了一个梯度场 → 运动倾向。
系统在这些势场的叠加中运动。

"运动势共域" = 所有势场在系统位置处的叠加：
  Φ_total(xo) = Σ Φ_i(|S_i - xo|)

核心环流在这个共域的稳态点附近形成。
稳态点是 ∇Φ_total = 0 的位置 — 
所有势的梯度平衡的地方。

核心环流 = 围绕这个稳态点的循环：
  motor 推 → 偏离稳态 → 梯度恢复力 → 前庭感知恢复 → motor 调整
  这就是 "不同运动势共域的稳态核心环流"。
```

---

## 实现方案

### Phase 1: 前庭层（独立于 origin）

```python
# 在 run_v40_integrated.py 的 build_signal_entropy_circuit() 中
vestibular_layer = CircuitLayer(layer_id="vestibular")
# 每个量源 2 个神经元：距离 + 变化率
for src in ["acoustic", "thermal", "luminous"]:
    vestibular_layer.add_neuron(f"lever_{src}")      # |L_i|
    vestibular_layer.add_neuron(f"dlever_{src}")     # d|L_i|/dt
vestibular_layer.add_neuron("angular_vel")            # dθ/dt（综合）

# 传入束
motor → vestibular   (efference copy)
vestibular → encoding (运动信号 → 感知调制)
```

### Phase 2: 量源和力臂计算

```python
# 在 practice_engine.py 中
class QuantitySource:
    pos: Tuple[float, float, float]   # 固定位置
    source_type: str                   # acoustic/thermal/luminous
    amplitude: float
    decay_law: str                     # "1/r" or "1/r2"
    
    def received_at(self, observer_pos, t):
        r = distance(self.pos, observer_pos)
        if self.decay_law == "1/r":
            return self.amplitude / (r + 0.01)
        else:
            return self.amplitude / (r*r + 0.01)

# 力臂计算
lever_arm = source.pos - observer_pos          # 矢量
lever_length = |lever_arm|                      # 标量
lever_rate = (lever_length - prev_lever) / dt   # d|L|/dt
```

### Phase 3: 量源熵账本

```sql
CREATE TABLE v40_quantity_source_ledger (
    run_id TEXT, tick INTEGER, source_type TEXT,
    received_value REAL,
    lever_arm_length REAL, lever_arm_rate REAL,
    entropy_contribution REAL,
    work_against_gradient REAL
);
```

### Phase 4: 环流检测

在 circuit.maintain() 中检测自持续回路：

```python
def detect_circulation(circuit):
    """Find self-sustaining cycles in the Hebbian graph."""
    # BFS/DFS 找所有闭合回路
    # 检查每个回路的净增益 vs 衰减
    # 如果 gain > decay → 标记为 active circulation
    # μ(G) = Σ(circulation_strength)
```

---

## 开放问题

> [!IMPORTANT]
> **环流的定义**：上面的形式化是否符合你的想法？
> 还是你有不同的/更精确的定义？
> 这会直接影响 `detect_circulation()` 的实现。
