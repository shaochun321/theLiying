# 超边耦合面、影子递归与变分内核的数学统一

> [!CAUTION]
> **本文档为 DEGRADED 目标定义**
>
> 以下理论框架（双重度规→层级自由能→运动势涌现）尚未经数学验证，当前项目**不实现**。
> 当前正式定义见 `modeling_hypergraph_math.md`（结构约束动态 + 下葬/衰减/共振影子层）。
> 本文档保留为日后突破时的理论参考。
>
> `status = "degraded_target"`

## §0 问题

三个构想之间的关系：

1. **超边** ← 不是简单的 AND 门，而是各向异性激活在不同时空窗口中形成的流形之间的**局部耦合面**
2. **影子层** ← 不是墓地，而是主系统的**副本沙盒**，在同调递归中提取时空测度与运动深度势的耦合
3. **递归结果** ← 可能与超边关联，作为运动势的垫支，可能符合变分自由能内核

本文推导它们如何统一。

---

## §1 流形与时空窗口切片

### §1.1 各向激活流形

设神经系统状态为 $\mathbf{x}(t) \in \mathbb{R}^d$（$d$ = 总神经元数）。

当轴 $\alpha$（例如 yaw）以强度 $I_\alpha$ 激活时，系统在时空窗口 $W = [t_0, t_0+T]$ 内的轨迹：

$$\gamma_\alpha: W \to \mathbb{R}^d, \quad t \mapsto \mathbf{x}(t \mid I_\alpha > 0, \; I_{\beta \neq \alpha} = 0)$$

**窗口切片**：固定窗口 $W$ 和强度 $I_\alpha$，轨迹 $\gamma_\alpha$ 扫过状态空间的一条曲线。

**可达集**：遍历所有强度 $I_\alpha \in [0, I_{\max}]$ 和所有窗口 $W$，可达集：

$$\mathcal{M}_\alpha = \bigcup_{I_\alpha, W} \text{Im}(\gamma_\alpha(I_\alpha, W)) \subset \mathbb{R}^d$$

$\mathcal{M}_\alpha$ 是一个低维子流形——轴 $\alpha$ 单独能驱动系统到达的全部状态。

### §1.2 六轴 → 六个流形

$$\mathcal{M}_1(\text{yaw}), \; \mathcal{M}_2(\text{pitch}), \; \ldots, \; \mathcal{M}_6(\text{saccular-z})$$

每个 $\mathcal{M}_\alpha$ 嵌入在 $\mathbb{R}^d$ 中，维度远低于 $d$（可能 2-3 维——强度 + 时间 + 适应状态）。

**当前实验已证**：$\cos(\Delta\mathbf{w}_\text{yaw}, \Delta\mathbf{w}_\text{pitch}) \approx 0$，意味着 $\mathcal{M}_1 \perp \mathcal{M}_2$——两个流形在权重空间中正交。

---

## §2 超边作为耦合面

### §2.1 联合激活的新流形

当轴 $\alpha, \beta$ 同时激活：

$$\gamma_{\alpha\beta}: W \to \mathbb{R}^d, \quad t \mapsto \mathbf{x}(t \mid I_\alpha > 0, \; I_\beta > 0)$$

关键问题：$\text{Im}(\gamma_{\alpha\beta})$ 是否在 $\mathcal{M}_\alpha \cup \mathcal{M}_\beta$ 内？

**如果是线性系统**：$\gamma_{\alpha\beta} = \gamma_\alpha + \gamma_\beta$，联合轨迹完全在 $\mathcal{M}_\alpha \oplus \mathcal{M}_\beta$ 的直和中。没有新信息。

**如果是非线性系统**（真实情况）：$\gamma_{\alpha\beta} \neq \gamma_\alpha + \gamma_\beta$。存在一个**剩余分量**：

$$\delta_{\alpha\beta}(t) = \gamma_{\alpha\beta}(t) - \big[\gamma_\alpha(t) + \gamma_\beta(t)\big]$$

$\delta_{\alpha\beta}$ 的像集 = **耦合面**：

$$\Sigma_{\alpha\beta} = \text{Im}(\delta_{\alpha\beta}) \subset \mathbb{R}^d$$

### §2.2 超边 = 耦合面的探测器

超边 $\beta_{\{\alpha,\beta\}}$ 的激活不应该是简单的 AND 门（$\prod \text{ReLU}$），而是：

$$a_{\text{hyper}} = \|\delta_{\alpha\beta}\| = \|\mathbf{x}_{\text{actual}} - (\mathbf{x}_{\alpha\text{-only}} + \mathbf{x}_{\beta\text{-only}})\|$$

即：超边检测的是**联合激活与各轴独立激活之和的偏差**——非线性耦合项的大小。

**与此前实验的对应**：

$$\cos(\Delta\mathbf{w}_{\text{yaw+pitch}}, \; \Delta\mathbf{w}_\text{yaw} \oplus \Delta\mathbf{w}_\text{pitch}) = 0.677 \approx \frac{1}{\sqrt{2}}$$

cos = 0.677 意味着联合轨迹与直和的夹角 ≈ 47°。这 47° 的偏差就是 $\|\delta_{\alpha\beta}\|$ 的贡献——**耦合面确实存在，但当前架构无法捕捉它**。

### §2.3 耦合面作为 T/O/P/R/Xin 中的量

| 生命周期 | 耦合面的角色 |
|---------|------------|
| **T** (传输) | 信号沿耦合面传播时，传输成本不同于沿单轴流形——耦合面有自己的度规 |
| **O** (观测) | 耦合面的"面积"（体积测度）是一个可观测量 |
| **P** (主环流) | 如果主环流穿过耦合面，环流的流量包含耦合项 |
| **Xin** (残差) | 预测误差 = $\|\delta_{\alpha\beta}\|$ 在耦合面上的分量——系统尚未学会的非线性部分 |

**关键洞察**：耦合面的 Xin 残差 $\neq$ 各轴 Xin 的和。它是一个**不可约的联合残差**，只有超边能检测到。

---

## §3 影子层作为沙盒递归

### §3.1 副本沙盒的形式化

设主系统状态为 $\mathbf{x}(t)$，影子系统状态为 $\tilde{\mathbf{x}}(t)$。

影子系统运行**同样的动力学**，但：
- 时间尺度膨胀 $\times k$（每 $k$ 步更新一次）
- 接收主系统的状态作为"观测"
- 用自己的内部模型 $g(\tilde{\mathbf{x}})$ 预测主系统

$$\dot{\tilde{\mathbf{x}}} = \underbrace{f(\tilde{\mathbf{x}})}_{\text{自身动力学}} + \underbrace{K \cdot \big(\mathbf{x} - g(\tilde{\mathbf{x}})\big)}_{\text{预测误差校正}}$$

这就是**预测编码**（Rao & Ballard 1999）的精确数学形式。

$K$ 是一个类 Kalman 增益矩阵——控制影子系统对主系统偏差的响应速度。

### §3.2 同调递归（Homological Recursion）

影子系统不止一层。定义递归层级 $n = 0, 1, 2, \ldots$：

$$\tilde{\mathbf{x}}^{(0)} = \mathbf{x} \quad (\text{主系统本身})$$

$$\dot{\tilde{\mathbf{x}}}^{(n+1)} = f^{(n)}(\tilde{\mathbf{x}}^{(n+1)}) + K^{(n)} \cdot \big(\tilde{\mathbf{x}}^{(n)} - g^{(n)}(\tilde{\mathbf{x}}^{(n+1)})\big)$$

每一层都在预测上一层，时间尺度逐层膨胀：

$$\tau^{(n)} = \tau^{(0)} \cdot k^n$$

**"同调"的含义**：每一层提取上一层的**拓扑不变量**——那些在时间尺度 $\tau^{(n)}$ 上稳定的结构特征。快变化在低层被平均掉，只有慢结构传到下一层。

### §3.3 递归收敛的三种可能

**定理（非正式）**：递归 $\tilde{\mathbf{x}}^{(n)}$ 的收敛行为取决于主系统动力学 $f$ 的结构：

#### 情况 A：收敛到少数特征

如果 $f$ 有**低维吸引子**（如前庭系统的 6 个轴 → 几个 effective DoF）：

$$\tilde{\mathbf{x}}^{(n)} \xrightarrow{n \to \infty} \mathbf{z} \in \mathbb{R}^p, \quad p \ll d$$

递归提取出 $p$ 个**慢变量**（slow manifold 的坐标）。

**预测**：对前庭系统，$p \approx 3\text{-}4$：
- 1 个总活动量级（能量）
- 1 个轴际偏好（哪组轴主导）
- 1 个时序相位（振荡周期位置）
- 可能的第 4 个：耦合强度（联合模式 vs 单轴模式）

#### 情况 B：收敛到稳定振荡

如果 $f$ 有**极限环**（CPG 驱动的系统天然如此）：

$$\tilde{\mathbf{x}}^{(n)} \xrightarrow{n \to \infty} \mathbf{z}(t), \quad \mathbf{z}(t + T^*) = \mathbf{z}(t)$$

递归找到一个**慢周期** $T^* \gg T_{\text{fast}}$，这就是系统的"内在节律"。

**物理意义**：这个慢振荡就是系统在 P/R 竞争中的**自然切换周期**——P 主导 → R 挑战 → 切换 → P' 主导 → ...

#### 情况 C：收敛到常数（热寂）

如果 $f$ 是**遍历的且无吸引子**：

$$\tilde{\mathbf{x}}^{(n)} \xrightarrow{n \to \infty} \bar{\mathbf{x}} = \text{const}$$

递归结果是系统的**时间均值**。这是最大熵状态——意味着主系统没有可提取的结构。

**判据**：如果系统的 Xin 守恒成立且果实全部被消费，系统趋向热平衡 → 常数。

### §3.4 最可能的结果

对前庭赫布超图，三种情况会**叠加**：

$$\tilde{\mathbf{x}}^{(\infty)} = \underbrace{\bar{\mathbf{x}}}_{\text{常数基底}} + \underbrace{\sum_{i=1}^{p} c_i \mathbf{e}_i}_{\text{少数特征}} + \underbrace{A \cos(\omega^* t + \phi)}_{\text{慢振荡}}$$

即：一个常数基底 + 少量特征方向 + 一个稳定的慢周期振荡。

---

## §4 与变分自由能的统一

### §4.1 影子递归 = 变分推断

变分自由能（Friston 2010）：

$$F[q] = \underbrace{E_q[-\ln p(\mathbf{o}, \boldsymbol{\theta})]}_{\text{内能（预测成本）}} - \underbrace{H[q(\boldsymbol{\theta})]}_{\text{熵（模型复杂度）}}$$

其中 $q(\boldsymbol{\theta})$ 是内部模型对隐变量 $\boldsymbol{\theta}$ 的近似后验。

**映射到影子系统**：

| 变分推断 | 影子递归 |
|---------|---------|
| 观测 $\mathbf{o}$ | 主系统状态 $\mathbf{x}$ |
| 隐变量 $\boldsymbol{\theta}$ | 引起 $\mathbf{x}$ 变化的隐含原因（运动模式） |
| 近似后验 $q(\boldsymbol{\theta})$ | 影子状态 $\tilde{\mathbf{x}}$ |
| 生成模型 $p(\mathbf{o} \mid \boldsymbol{\theta})$ | 影子的预测函数 $g(\tilde{\mathbf{x}})$ |
| 自由能最小化 $\nabla_q F = 0$ | 影子预测误差校正 $K \cdot (\mathbf{x} - g(\tilde{\mathbf{x}}))$ |

**因此**：影子层的同调递归 = 在层级化的时间尺度上做变分推断。

### §4.2 自由能内核

递归收敛后的 $\tilde{\mathbf{x}}^{(\infty)}$ 是什么？它是使自由能最小的**充分统计量**：

$$\tilde{\mathbf{x}}^{(\infty)} = \arg\min_{\tilde{x}} F[\tilde{x}, \mathbf{x}]$$

展开：

$$F[\tilde{x}] = \frac{1}{2}\|\mathbf{x} - g(\tilde{x})\|^2_{\Sigma_o^{-1}} + \frac{1}{2}\|\tilde{x} - \mu_p\|^2_{\Sigma_p^{-1}}$$

第一项 = 预测精度（主系统与影子预测的偏差）
第二项 = 先验约束（影子不能离先验太远）

**自由能内核 $\mathcal{K}$**：当 $n \to \infty$，自由能达到最小值：

$$\mathcal{K} = F[\tilde{\mathbf{x}}^{(\infty)}] = F_{\min}$$

$\mathcal{K}$ 是一个**标量**——系统的**不可约预测误差**。它度量的是：即使影子层做了最优推断，主系统中仍有多少"不可预测"的成分。

### §4.3 超边耦合面 = 自由能地形中的鞍点

将自由能看作状态空间上的地形 $F: \mathbb{R}^d \to \mathbb{R}$。

在**单轴流形** $\mathcal{M}_\alpha$ 上，自由能沿着一条谷底（学到的预测模型好 → F 低）。

在**耦合面** $\Sigma_{\alpha\beta}$ 上：

$$F\big|_{\Sigma_{\alpha\beta}} = F\big|_{\mathcal{M}_\alpha} + F\big|_{\mathcal{M}_\beta} + \underbrace{F_{\text{coupling}}}_{\text{耦合项}}$$

$F_{\text{coupling}}$ 就是 $\|\delta_{\alpha\beta}\|^2$——联合激活时的额外预测误差。

**超边的学习 = 减小 $F_{\text{coupling}}$**：

$$\frac{\partial}{\partial \mathbf{W}^{\text{hyper}}} F_{\text{coupling}} < 0$$

超边权重的 STDP 更新正是在沿着这个梯度下降。当超边学好后：

$$F_{\text{coupling}} \to 0$$

耦合面从自由能的"山脊"变成"谷底"——联合运动模式变得和单轴一样可预测。

---

## §5 三者统一

### §5.1 因果链

```
各向激活 → 流形 M_α
                ↓
联合激活 → 耦合面 Σ_αβ = 自由能地形的高处
                ↓
超边学习 → 降低 F_coupling → 耦合面 → 谷底
                ↓
影子递归 → 在慢时间尺度上提取 F_min
                ↓
递归收敛 → 自由能内核 K + 慢流形坐标 z
                ↓
运动势 = ∇_z K → 信息在慢流形上的倾向
```

### §5.2 每个概念的位置

```
                    ┌─────────────────────────────────────────┐
                    │           快时间尺度 (τ₀)              │
                    │                                         │
                    │  M₁(yaw) ⊥ M₂(pitch) ⊥ ... ⊥ M₆      │
                    │       ↘        ↓        ↙               │
                    │         Σ₁₂   Σ₁₃   ...  ← 耦合面     │
                    │           ↓                             │
                    │      超边 β_{12} 学习                   │
                    │      → F_coupling ↓                     │
                    ├─────────────────────────────────────────┤
                    │           中间时间尺度 (τ₁ = kτ₀)       │
                    │                                         │
                    │    影子层 x̃⁽¹⁾ ← 预测 x⁽⁰⁾            │
                    │    提取: 哪些耦合面稳定？               │
                    │          哪些是噪声？                   │
                    ├─────────────────────────────────────────┤
                    │           慢时间尺度 (τ₂ = k²τ₀)        │
                    │                                         │
                    │    影子层 x̃⁽²⁾ ← 预测 x̃⁽¹⁾            │
                    │    提取: 慢流形坐标 z ∈ R^p             │
                    ├─────────────────────────────────────────┤
                    │           极慢尺度 (τ_∞)                │
                    │                                         │
                    │    K = F_min = 不可约残差 (标量)        │
                    │    ν = ∇_z K = 运动势                   │
                    │    超边垫支 = z 空间中的稳定方向         │
                    └─────────────────────────────────────────┘
```

### §5.3 回答你的三个问题

**Q1: 递归会导致怎样的结果？**

最可能的结果是 **情况 A+B 的叠加**：
$$\tilde{\mathbf{x}}^{(\infty)} = \bar{x} + \sum_{i=1}^{3\sim4} c_i \mathbf{e}_i + A\cos(\omega^* t)$$
- 常数基底 $\bar{x}$ = 系统的时间均值（热力学平衡态）
- 3-4 个特征方向 $\mathbf{e}_i$ = 慢流形的坐标轴
- 一个慢振荡 $\omega^*$ = P/R 竞争的内在周期

**不是纯常数**（因为前庭系统有 CPG 驱动的内禀振荡），也不会是高维特征集（因为维度远低于自由度）。

**Q2: 递归结果与超边的关系？**

超边耦合面是 $\mathbf{e}_i$ 的**来源**。影子递归提取出的 3-4 个特征方向中，至少 1 个是耦合方向——即 $\delta_{\alpha\beta}$ 的主成分。

因此：$z$ 空间中的坐标 = 单轴方向 + 耦合方向。运动势 $\nu = \nabla_z \mathcal{K}$ 在耦合方向上的分量就是超边提供的"垫支"——没有超边，运动势在这个方向上没有定义（因为没有对应的自由度）。

**Q3: 是否符合变分自由能内核？**

是的。$\mathcal{K} = F_{\min}$ 就是变分自由能的最优下界：

$$\mathcal{K} = -\ln p(\mathbf{x}) + D_{KL}[q^* \| p(\boldsymbol{\theta} | \mathbf{x})]$$

当 $q^* = p(\boldsymbol{\theta} | \mathbf{x})$（完美推断）时，$D_{KL} = 0$，$\mathcal{K} = -\ln p(\mathbf{x})$ = 惊讶度。

影子递归的极限就是在逼近这个下界。超边让 $g(\tilde{x})$ 能够捕捉耦合项，从而降低 $\mathcal{K}$。

---

## §6 对数学建模的修正

基于以上分析，§2（完整数学建模）的 §5 和 §9 需要重写：

### §5 Binding Layer → 耦合面探测器

原来：$a_p = G_p \cdot \prod \text{ReLU}(\cdot)$（AND 门）

修正为：

$$a_p = \Big\| \mathbf{x}^{\text{col}} - \sum_{\alpha \in \mathcal{A}_p} \Pi_\alpha \mathbf{x}^{\text{col}} \Big\|$$

其中 $\Pi_\alpha$ 是向 $\mathcal{M}_\alpha$ 的投影。$a_p$ 度量的是**联合状态偏离各轴直和的程度**。

实际实现中，$\Pi_\alpha$ 不需要显式计算——由影子系统在单轴训练中自动学到（$g_\alpha(\tilde{x}) \approx \Pi_\alpha \mathbf{x}$）。

### §9 Shadow Layer → 层级变分沙盒

原来：下葬 + 衰减 + 共振

修正为：

$$\dot{\tilde{\mathbf{x}}}^{(n+1)} = f^{(n)}(\tilde{\mathbf{x}}^{(n+1)}) + K^{(n)} \cdot (\tilde{\mathbf{x}}^{(n)} - g^{(n)}(\tilde{\mathbf{x}}^{(n+1)}))$$

每层时间膨胀 $\times k$，递归深度 $N$ 由以下条件确定：

$$\|\tilde{\mathbf{x}}^{(N)} - \tilde{\mathbf{x}}^{(N-1)}\| < \epsilon \quad \text{(收敛判据)}$$

---

## §7 Open Questions

1. **$k$ 的值**：时间膨胀因子。如果 $k = 20$（v41.3 的设定），两层递归覆盖 $\tau_2 = 400 \tau_0$。这够提取慢流形吗？可能需要 $k = 5$、$N = 4$ 层更合理。

2. **$K$ 的学习**：Kalman 增益是固定的还是自适应的？如果自适应，用什么更新规则？
   - 候选：$K$ 本身用 STDP 学习 → 影子层的连接权重就是 $K$

3. **投影 $\Pi_\alpha$ 如何获取**：影子系统需要知道"单轴激活时的预测"。这需要主系统做过单轴训练。
   - 可行方案：在 spine 阶段（各轴独立训练），影子系统同步学习 $g_\alpha$
   - column 阶段开始联合激活时，$\Pi_\alpha$ 已经就位

4. **递归是否会发散**：如果 $K$ 太大或 $f$ 不稳定。
   - 需要证明或验证：收缩映射条件 $\|f' + K g'\| < 1$

5. **慢振荡 $\omega^*$ 是否与 CPG 相关**：如果是，影子提取到的其实就是 CPG 的基频。如果不是，那是一个新的涌现周期——可能对应 P/R 竞争的自然频率。
