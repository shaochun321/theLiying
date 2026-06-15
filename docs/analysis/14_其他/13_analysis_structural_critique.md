# 结构性批判分析：三个致命缺陷与一个深层发现

## 批判 1：Column 是语义幻觉

> [!CAUTION]
> **判决：批判正确。** 当前 Column 与 Spine 的唯一区别是 `inertia` 和 `threshold_adapt_rate` 的数值变化。没有任何拓扑特权、侧向抑制作用域差异、或跨区连接能力。

### 当前代码的真相

[try_mature](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py#L170-L180) 只做了：

```python
if self.maturation == "spine" and self.potential > column_threshold:
    self.maturation = "column"
    self.inertia = max(self.inertia, 2.0)        # 数值变大
    self.threshold_adapt_rate *= 0.5              # 数值变小
```

这是**纯粹的标量调参**。Column 不能抑制邻居、不能跨区连接、不能影响 bundle 拓扑。

### 真实皮层微柱的物理特权

| 特性 | 真实微柱 | 当前 Column |
|------|---------|------------|
| **侧向抑制半径** | Column 通过 basket cell 抑制周围 ~3 个微柱距离的 Spine | ❌ 不存在 |
| **长程前馈** | 成熟柱的 L2/3 锥体细胞发出长程水平连接 | ❌ 不存在 |
| **不对称 STDP** | Column 使用不对称 STDP（加速器），Spine 使用对称 STDP（制动器）| ❌ 都用同一 STDP |
| **PRP 蛋白捕获** | Column 产生 plasticity-related proteins，可被远处 tagged Spine 捕获 | ❌ 不存在 |

> [!IMPORTANT]
> **Frégnac (2003, 2012)** 的核心论点：皮层功能不是从静态模块涌现，而是从**动态递归交互**和**不对称可塑性规则**涌现。Column 必须拥有 Spine 不拥有的**物理法则**，否则分化就是标签。

### 建议：不对称物理法则

```
Spine 物理法则:
  - 只吸收局部 Xin
  - 对称 STDP（稳定器）
  - 不影响邻居 threshold
  - 被 Column 抑制

Column 物理法则:
  - 空间扭曲权：抑制拓扑距离 ≤ 3 的 Spine 的 threshold 向上偏移
  - 不对称 STDP（加速器）：pre-before-post 增强系数 2×
  - 长程连接：可以在 inter_layer_bundles 中发起新 bundle
  - PRP 发射：calcium 超过阈值时产生 PRP 标记，可被远端 tagged Spine 捕获
```

---

## 批判 2：休眠果实没有时间反向追溯

> [!CAUTION]
> **判决：批判正确。** 当前 `xin_dormant_fruit` 只记录了 `created_at` 时间戳和 `tension_at_creation`，但**没有衰减机制**、没有跨时间的责任归因能力。

### 当前代码的真相

[accumulate_xin](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py#L362-L372):

```python
if abs(self.xin_tension) > 0.5 and self.xin_dormant_fruit is None:
    self.xin_dormant_fruit = {
        "tension_at_creation": self.xin_tension,
        "bundle_id": self.bundle_id,
        "created_at": _now(),
        "state": "dormant",
    }
```

**问题**：
1. 果实一旦创建就永远不衰减 — 第 100 帧的果实在第 5000 帧仍有完整张力
2. 如果果实被激活导致废热，没有机制追溯到创建时刻并惩罚那个时空位置
3. 这违反了热力学的「无长期记忆」原则

### 神经科学中的解决方案：三因子学习 + 突触标记捕获

| 机制 | 生物学 | 对应概念 |
|------|-------|---------|
| **Eligibility Trace** | 突触活动留下衰减残留（Ca²⁺），如果 neuromodulator（多巴胺）在残留期到达，突触被修改 | 果实应有指数衰减的 trace |
| **Synaptic Tagging & Capture** | 弱刺激产生短期 tag，强刺激产生 PRP 蛋白。只有 tag + PRP 同时存在才固化 | 果实应有 tag 阶段和 capture 阶段 |
| **Three-Factor Learning** | Δw = η · eligibility_trace · reward_signal · activity | 果实激活时的 STDP 应被 trace 强度加权 |

### 建议：化学梯度衰减（Chemical Trace）

```python
@dataclass
class DormantFruit:
    tension_at_creation: float
    bundle_id: str
    created_tick: int
    trace_strength: float = 1.0    # 指数衰减：每 tick *= decay_rate
    trace_decay: float = 0.995     # τ ≈ 200 ticks
    tag_proteins: float = 0.0      # 被 Column PRP 捕获时增加
    
    def decay_trace(self):
        self.trace_strength *= self.trace_decay
        if self.trace_strength < 0.01:
            return "expired"  # 果实自然消亡，无法再被激活
        return "alive"
    
    def activate(self, bias_signal: float) -> Optional[Dict]:
        # 激活强度 = tension × 残留 trace × tag 捕获
        effective_tension = self.tension_at_creation * self.trace_strength
        if effective_tension * bias_signal > 0 and abs(bias_signal) > 0.3:
            return {
                "original_tension": self.tension_at_creation,
                "effective_tension": effective_tension,  # 衰减后的
                "temporal_discount": self.trace_strength,
                # 废热反向归因：对创建时刻的 bundle 权重施加惩罚
                # 惩罚强度 ∝ 1 - trace_strength（越远越弱）
            }
```

---

## 批判 3 与发现：cos > 0 指向的共享子空间

> [!NOTE]
> **这不是缺陷。** cos > 0 是真实的物理现象。但当前架构没有**结构性地表征**这个共享子空间。

### 你观察到的现象的物理对应

你说的「流形往影子赫布超图深入，仿佛将流形捏出巨大的尖」——这在数学上对应的是：

```
主流形 M（7 维 z_t 空间）中存在一个低维子流形 S（2-3 维）

所有视觉刺激的 z_t 轨迹都被约束在 S 附近
cos > 0 测量的是轨迹在 S 上的投影重叠

当 P/R 递归深入时：
  - 时空窗口无穷延伸
  - P/R 轨迹在 S 上被压缩成一条线（共享基底）
  - Xin 的规模在 S 的法方向上增大（刺激特异性残差）
```

**这在你的语言中就是**：P/R 占据共享的时空基底（自然图像统计 + 能量灌注模式），Xin 在正交方向上不断具体化（「这是 movie 而非 scenes」的判别信号）。

### 大脑中的「顶层总览区域」

你问的「顶层的、代表高度抽象的、总览的区域」在大脑中确实存在：

| 区域 | 功能 | 对应你的概念 |
|------|------|------------|
| **前额叶外侧皮层 (dlPFC)** | 沿 rostral-caudal 轴组织的抽象层级：前端=抽象规则，后端=具体映射 | 从 z_t 子空间中提取「这是自然刺激」的抽象类别 |
| **前扣带皮层 (ACC)** | 监测预测误差，信号偏差 | **就是 Xin** — 检测实际与预期的偏离 |
| **海马体** | 发现和存储经验的层级结构 | 存储 P/R 循环的时序结构 |

> [!IMPORTANT]
> ACC-dlPFC 的关系就是你描述的 Xin 与主流形的关系：
> - ACC（Xin）检测到误差 → 信号发送到 dlPFC
> - dlPFC 更新抽象表征 → 改变 ACC 的预测模板
> - 这是**递归的**，且 ACC 信号的持续存在（Xin 增大）确实会「破坏」dlPFC 的稳定表征

### 稀疏张量 / GNN 的连接

你的直觉是对的——当前的 z_t 空间是**稠密的**（所有 7 个维度都参与每次计算），但实际的激活模式是**稀疏的**（每种刺激只激活 4-5 个维度）。

```
movie   : [0     .002   0     .106   0     .015  .102]  → 3 个非零
scenes  : [.003  .114   0     .089   0     .094   0  ]  → 4 个非零
gratings: [.004   0    .117   .021  .087    0    .111]  → 5 个非零
```

这天然形成一个**稀疏超图**：
- 节点 = z_t 维度
- 超边 = 刺激激活的维度子集
- 超边权重 = 激活强度

GNN 的消息传递机制（message passing）与 P/R 循环在数理上是同构的：
- **Aggregate**（聚合邻居消息）= P（transport）
- **Update**（更新节点状态）= R（recurrent refinement）
- **Readout**（全局读取）= Xin（circulation measure）

---

## 综合建议：下一步该构建什么

> [!WARNING]
> **不建议同时推进三个方向。** 按照物理优先级排序：

| 优先级 | 改什么 | 为什么先做 |
|:---:|--------|---------|
| **1** | Column 不对称物理法则 | 批判最致命 — 没有功能特权的分化是语义幻觉 |
| **2** | 果实化学梯度衰减 | 时间信用分配是物理约束 — 无长期记忆 |
| **3** | 共享子空间的显式表征 | cos > 0 的结构性意义需要被电路消化 |

优先级 1 是因为 Column 的语义幻觉会**污染后续所有分析** — 如果分化不带来真实的物理后果，那么在 Column 基础上构建的子空间表征也是虚假的。

优先级 3（你最感兴趣的那个——「将流形捏出巨大的尖」）需要 Column 的物理特权作为基础设施。只有当 Column 真的能**抑制周围 Spine**并**跨区连接**时，cos > 0 共享子空间才能被结构性地表征为一个特殊的 Column 集团。
