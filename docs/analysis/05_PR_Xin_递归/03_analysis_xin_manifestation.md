# Xin 的结构表现 — 从波动到节点

## 项目中已有的 Xin 生命周期

代码中已经实现了 Xin 的**完整生命阶段**，只是这些阶段之间的连接断裂了：

```
阶段 1: 波动 (fluctuation)
  L737: xin_tension += (predicted - actual)
  → 每 tick 都在发生，大部分时候互相抵消

阶段 2: 标记 (tagging) — 当 |xin_tension| > 0.5
  L739-755: 创建 dormant_fruit
    → 记录了张力大小、来源/目标神经元、创建时间
    → 带有 Ca²⁺ trace (trace_decay = 0.995)
  这是 Xin 从"波动"凝结为"结构"的瞬间

阶段 3a: 激活 (capture) — 当 bias_signal 与 tension 同向
  L774-800: try_activate_fruit()
    → fruit 状态变为 "activated"
    → xin_tension 归零
  这对应 Frey & Morris 的 "synaptic tagging and capture"

阶段 3b: 衰减 (dissolution) — 当 trace < 0.01
  L757-772: decay_fruit_trace()
    → trace *= 0.995 每 tick
    → 约 920 ticks 后完全衰减
    → fruit 消失，注释说 "compressed into shadow_memory"
  但 shadow_memory 不存在 → Xin 被彻底丢弃

阶段 4: 幽灵 (ghost) — 被剪枝的 bundle
  L1365-1399: ghost_bundles
    → 剪枝后的 bundle 留下 ghost_strength ≈ 0.001
    → 参与 P/R circulation 的计算
  这是 Xin 的"不死残余"
```

### 当前的断裂点

```
波动 ──→ 标记 ──→ ??? ──→ 消失
              │
              └──→ 激活 ──→ ???  ← 激活后怎么办？无人处理
```

**标记后要么衰减消失，要么被激活——但激活后的果实去了哪里？**
代码中 `try_activate_fruit()` 返回一个 dict，但调用者只是把它存进 audit log。
**没有任何代码用这个 activated fruit 做任何事。**

---

## Xin 的相变特性

你的直觉——"积累形成节点"——对应物理学中的**成核 (nucleation)**：

```
                 临界阈值 |Xin| = 0.5
                        │
    波动区               │         结构区
    (subcritical)        │        (supercritical)
                        │
  Xin < 0.5:           │       Xin > 0.5:
  · 互相抵消             │       · 凝结成 dormant_fruit
  · 被 P 消解            │       · 带有衰减的 trace
  · 不留痕迹             │       · 可能被 capture 或消失
                        │
                    ────┼──── 相变
```

这和物理系统中的成核完全对应：

| 物理成核 | Xin 成核 |
|---------|---------|
| 过饱和溶液中的随机聚集 | xin_tension 的累积 |
| 临界核半径 | 阈值 0.5 |
| 低于临界半径 → 溶解 | \|Xin\| < 0.5 → 被抵消 |
| 高于临界半径 → 生长 | \|Xin\| > 0.5 → 产生 fruit |
| 生长需要持续供应 | fruit 需要 bias_signal 来 capture |
| 无供应 → Ostwald 熟化 → 消失 | 无 bias → trace 衰减 → 消失 |

---

## "直到被固定，但又不能被 P/R 化"

这是你描述中最深刻的部分。让我追踪 Xin 的所有可能结局：

```
Xin 波动
  │
  ├── 路径 A: 被 P 消解 → 消失 (正常运行)
  │
  ├── 路径 B: 累积 → 标记(fruit) → 衰减 → 消失
  │   (当前系统的实际行为 — 所有 fruit 最终都消失)
  │
  ├── 路径 C: 累积 → 标记 → capture → 成为结构
  │   (设计意图，但 capture 后无人处理)
  │
  ├── 路径 D: 被固定 → 不能被 P/R 化 → 越过 O → 到达 T
  │   (你描述的行为 — 目前不存在)
  │
  └── 路径 E: 直接越过到 T → 成为外部可观测
      (你说的 "到 T 甚至更外" — 目前不存在)
```

### 路径 D 和 E 在物理学中的对应

**路径 D**: Xin 被"固定"但不能被 P/R 吸收 = **拓扑缺陷 (topological defect)**

```
在凝聚态物理中:
  · 涡旋 (vortex) 是无法被连续形变消除的
  · 它必须与另一个反涡旋湮灭，或者永远存在
  · 它会影响周围的流动模式

在超图中:
  · 被固定的 Xin 是一个不能被 P/R 环流吸收的"结节"
  · 它会永久改变周围 bundle 的流向
  · 这就是 crystal neuron 的本质!
```

**路径 E**: Xin 越过 O/P/R 到达 T = **对称性破缺 (symmetry breaking)**

```
当 Xin 足够强且无法被本层消解时:
  · 它不走 P/R (因为 P/R 没有容量)
  · 它直接改变了 T (传递结构本身)
  · 这等价于: spine → column 的 maturation!
```

看代码 L270-307:

```python
# spine → column 的条件:
#   potential > threshold  AND  activation_count > 20
# 这就是: Xin 累积到 potential 超过阈值 → 结构突变
```

**Maturation = Xin 越过 O/P/R 直接到 T 的代码实现。**

---

## 用项目语言定位

### 时空测度 (spatiotemporal measure)

```
Xin 在时空中的分布:
  空间: 哪些 bundle/neuron 上的 Xin 最大? → 结构热点
  时间: Xin 在多长的窗口内持续? → 决定它到达哪一层

时空测度 μ(Xin) = ∫∫ |Xin(x,t)| dx dt
  小 → 局部波动，被底层消解
  大 → 全局偏差，到达高层
```

### 运动势 (motion_potential)

```
Xin 是运动势的来源:
  motion_potential = Σ c_i × feature_i  (在 _common.py L127)
  
  如果 Xin 被固定成结构:
    → 它贡献到 c4 (motion_potential_displacement, weight=1.2)
    → 它是系统中最重的分量!
  
  所以: Xin 固定 → 运动势最大分量改变 → 系统行为改变
```

### 结构计算/物理计算

```
Xin 的物理含义:
  · 在突触级: 预测误差 (信息论)
  · 在 bundle 级: 张力 (弹性力学)
  · 在层级: 失调 (热力学非平衡)
  · 在 circuit 级: 不满足 (控制论误差信号)

被固定的 Xin = 结构应力 (structural stress)
  · 像金属中的位错 (dislocation)
  · 不能通过简单退火消除
  · 会改变材料的力学性质
  · 但也可能是"强化"的来源 (加工硬化!)
```

---

## 缺失的第三因子 (third factor)

从代码 L760-764 的注释:

```
"If no neuromodulatory signal (third factor) arrives before
the trace expires, the fruit naturally dissolves"
```

**系统知道需要"第三因子"，但从未实现过。**

在 Park et al. 中，第三因子 = **CF 同步性触发的去抑制**。

```
fruit 被标记 (Xin > 0.5)
   │
   等待 ← trace 在衰减 (0.995/tick, ~920 ticks 寿命)
   │
   ├── 同步事件 (g > 0.5) 在 trace 存活时到达:
   │   → capture! → Xin 固定为结构
   │
   └── 同步事件未到达:
       → trace → 0 → fruit 消失 → Xin 被丢弃
```

**同步性就是第三因子。**

> [!IMPORTANT]
> **完整的 Xin 生命周期应该是：**
> 
> ```
> 波动 → 累积 → 标记(fruit) → [等待第三因子]
>                                    │
>                    ┌───────────────┼───────────────┐
>                    │               │               │
>               衰减消失        同步 capture      超过 P 容量
>              (路径 B)        (路径 C→固定)     (路径 D→越过到 T)
>                                    │               │
>                              结构化节点         Maturation
>                            (convergence)    (spine→column→area)
> ```
> 
> **当前系统中只有路径 B 在工作。路径 C 和 D 的代码存在但断裂。**
> 
> 你说的"无名波动"其实已经有名了 — 它是 **eligibility trace + 
> synaptic tagging**。只是 capture 的触发条件（第三因子 = 同步性）
> 从未被连接到 `try_activate_fruit()` 的调用链上。
