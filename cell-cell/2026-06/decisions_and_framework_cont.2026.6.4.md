> **导航**: [[00_Dashboard/核心词条索引]] · [[00_Dashboard/理念架构图]]

# 待决定的方向 + 数理体系全貌（续篇）

*接续 decisions_and_framework_0604.md，2026.6.4 01:16*

---

## 新增决定

### 决定 8：影子层的本体论

影子层应该是什么？

| 选项 | 定义 | 后果 |
|------|------|------|
| A. **抽象观察者** | 无空间、无体积、纯拓扑图 | 现状，最简 |
| B. **四维积体神经组织** | 有空间坐标、有体积、有距离约束 | 需要空间分配 + 距离公式 + 密度限制 |
| C. **分阶段** | 先 A，验证垫支机制后升级为 B | 渐进式，风险低 |

如果选 B，影子层额外需要：

| 属性 | 当前 | 需要 |
|------|------|------|
| 神经元位置 | 无 | 3D 坐标 $(x_i, y_i, z_i)$ |
| 连接延迟 | 固定 2 步 | $delay = \|pos_i - pos_j\| / v_{conduct}$ |
| 体积约束 | 无 | 单位体积最大 neuron 数 $\rho_{max}$ |
| 生长方向 | sprout 随机 | sprout 偏向半径 $r$ 内的邻居 |

> **你需要决定**：影子层需要空间性吗？还是纯拓扑就够？

---

### 决定 9：影子层的生长模式

如果允许影子层生长（sprout/prune），如何约束？

| 选项 | 规则 | 自平衡机制 |
|------|------|----------|
| A. **镜像** | 主层 sprout → 影子层同步 sprout | 无独立发现能力 |
| B. **独立+容量上限** | 影子层自由生长，$\|T_1\| \leq \alpha \|T_0\|$ | 对应关系弱化 |
| C. **侦察兵** | 影子层自由生长，ripe 后反传播到主层 | 自平衡：成功→输入减少→生长减速 |
| D. **纯粗粒化** | 不生长，只在更长时间尺度上调权重 | 最保守 |

内禀约束（无论选哪个都适用）：

$$|T_1| \leq f\big(H(Xin_0)\big)$$

影子层结构规模 ≤ 主层预测误差的信息熵。主层越完美，影子层越小。

> **你需要决定**：影子层是侦察兵（C）还是粗粒化器（D）？或者先 D 后升级 C？

---

## 新增概念：垫支与驻波

### 垫支（Padding）的定义

> **垫支** = Fruit(ripe) + Maturation(area) 的联合状态。一条通路达到垫支后，其编码的 P ≈ R 模式被冻结为结构基底，不再需要逐步计算。

数学表示：

$$\text{Padding}(e, j) = \mathbb{1}[fruit_e = ripe] \cdot \mathbb{1}[stage_j \geq 2]$$

当 $\text{Padding} = 1$ 时，bundle $e$ 和 neuron $j$ 构成的通路成为**基底结构**——后续信号在此基底上叠加，而不是重新构建。

### 驻波的形成条件

正向波（外部输入 → 前庭链 → Motor → Body）与反向波（Body → Otolith → 前庭链）在 Enc→Col 层叠加。

驻波形成条件：

$$\left|\frac{f_{forward}}{f_{backward}} - \frac{p}{q}\right| < \epsilon \quad (p, q \in \mathbb{Z})$$

正反向频率比接近有理数时 → 稳定干涉 → STDP 固化为权重模式 → Fruit 从 growing → ripe。

### 多尺度内化

| 时窗 | 内化什么 | 结构对应 | 驻波类型 |
|------|---------|---------|---------|
| 短（~10k 步 / 10s） | 单信号的周期模式 | Aff→Enc 权重 | 一阶驻波 |
| 中（~100k 步 / 100s） | 信号间的关系 | 跨轴 bundle 权重 | 二阶驻波 |
| 长（~1M 步 / 1000s） | 关系的稳定性 | Maturation 冻结 | 基底固化 |

$$\text{外部信号} \xrightarrow{\text{短窗}} \text{一阶驻波} \xrightarrow{\text{中窗}} \text{二阶驻波} \xrightarrow{\text{长窗}} \text{垫支（基底）}$$

每一级驻波都是下一级的输入"地面"——这就是"垫支"的层叠。

---

## 数理体系新增部分

### 垫支算子

定义垫支算子 $\mathcal{P}$ 作用于超图 $\mathcal{H}$：

$$\mathcal{P}(\mathcal{H}) = \{e \in \mathcal{E} : Padding(e) = 1\}$$

垫支后的超图分裂为两部分：

$$\mathcal{H} = \mathcal{H}_{base} \cup \mathcal{H}_{active}$$

- $\mathcal{H}_{base} = \mathcal{P}(\mathcal{H})$：冻结的基底（ripe + area）
- $\mathcal{H}_{active} = \mathcal{H} \setminus \mathcal{P}(\mathcal{H})$：仍在学习的活跃部分

**所有新的 sprout 只在 $\mathcal{H}_{active}$ 上发生。** 基底不再变化。

### 驻波检测

$$SW_e(t) = \text{AutoCorr}(\xi_e, \delta^*) \quad \text{where } \delta^* = \arg\max_{\delta > 0} C(\delta)$$

如果 $SW_e > \theta_{SW}$（自相关峰值足够高），bundle $e$ 形成了驻波 → Fruit 可以转 ripe。

### 重整化塔（更新）

```
尺度 6: 垫支（基底固化）              窗口 ~1M+ 步
         ↕ 冻结/释放
尺度 5: Maturation (spine→column→area)  窗口 ~1M 步
         ↕ 可塑性递减
尺度 4: Fruit (dormant→growing→ripe)    窗口 ~100k 步
         ↕ 驻波检测
尺度 3: Xin (|P-R| 累积)               窗口 ~10k 步
         ↕ 结构生长
尺度 2: EMA (spike → 放电率)            窗口 ~100 步
         ↕ 时间平滑
尺度 1: Spike (离散事件)               窗口 = 1 步
```

新增的**尺度 6（垫支）**是最长时间尺度——一旦达到，结构从 active 转移到 base，成为后续所有计算的不可变地基。

### 体积约束（如果影子层成为 4D）

$$\sum_{j: \|pos_j - pos_c\| < r} 1 \leq \rho_{max} \cdot \frac{4}{3}\pi r^3$$

任意半径 $r$ 的球内，neuron 数不超过密度上限 × 体积。

sprout 距离约束：

$$P(\text{sprout } i \to j) \propto e^{-\|pos_i - pos_j\|^2 / 2\sigma^2}$$

越近越可能连接。远距离连接不是不可能，但概率指数衰减。

---

## 完整决定清单（含新增）

| # | 问题 | 状态 |
|---|------|------|
| 1 | 影子层→主层通道 | 待定 |
| 2 | Motor 分化路径 | 待定 |
| 3 | P 的精确化 | 待定 |
| 4 | 切分定理编码化 | 待定 |
| 5 | 先跑什么实验 | 待定 |
| 6 | T/O/P/R/Xin 递归深度 | 待定 |
| 7 | 运动势定义 | 待定 |
| **8** | **影子层本体论（抽象/4D/分阶段）** | **新增，待定** |
| **9** | **影子层生长模式（镜像/独立/侦察兵/粗粒化）** | **新增，待定** |
