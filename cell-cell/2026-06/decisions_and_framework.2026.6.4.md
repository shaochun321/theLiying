> **导航**: [[00_Dashboard/核心词条索引]] · [[00_Dashboard/理念架构图]]

# 待决定的方向 + 数理体系全貌

*2026.6.4*

---

# 第一部分：待你决定的方向

## 决定 1：影子层的角色

影子层已经建好、在运行、在学习——但输出（κ, ν, ds²）无人读取。

| 选项 | 含义 | 后果 |
|------|------|------|
| A. **影子层→主层反传播** | κ 或 ν 超阈值 → 主层 sprout | 时间环流触发空间生长成为可能 |
| B. **影子层→DA 调制** | ν（运动势）调制 DA → 影响学习率 | 影子层变成"情绪系统"，控制主层学多快 |
| C. **暂不连线** | 继续观察，积累影子层自身的数据 | 安全但不推进 |

> **你需要决定**：影子层应该通过什么渠道影响主层？还是你认为影子层的角色需要重新定义？

---

## 决定 2：Motor 分化的路径

20 个克隆 motor（$N_{eff}=1$）是当前最大的结构缺陷。

| 选项 | 原理 | 改动量 | 与 T/O/P/R/Xin 的关系 |
|------|------|--------|---------------------|
| A. **Mitosis 噪声** | 分裂时子代权重加随机扰动 | 3 行代码 | 打破 T 的对称性 |
| B. **CPG 相位锁定** | 每个 motor 分配到 CPG 不同相位 | 中等 | O 的差异化驱动 T 的差异化 |
| C. **竞争排斥** | motor 之间加抑制连接 | 较大 | 新的 T（抑制 bundle）产生新的 P/R |

> **你需要决定**：哪条路径更符合你的理论直觉？A 是最小侵入，C 最接近生物学，B 借用已有 CPG。

---

## 决定 3：P 的精确定义

你修正了 P 的含义——P 不是猜测，而是历史 R 在当前 R 上的投影。

| 选项 | 形式 | 后果 |
|------|------|------|
| A. **保持现状** | $P = W \times pre\_activation$ | 代码不变，理论文档中修正描述 |
| B. **显式化时空窗口** | $P = W_{\tau \in [t-\Delta, t]} \times activation$ | 给 P 加一个有限记忆窗口 |
| C. **P 分解为 P_t 和 P_s** | $P_t$（时间预测）+ $P_s$（空间预测）分开计算 | 时空偏振在 P 层面显式化 |

> **你需要决定**：P 需要在代码中显式区分时间/空间分量吗？还是让这个区分留在 Aff reg/irr 层面就够了？

---

## 决定 4：切分定理的编码化

"系统不生成时空，只生成时空的切分"——目前是哲学声明，不是代码约束。

| 选项 | 含义 |
|------|------|
| A. **加入 RULES 文件** | 写入 `RULES_STRUCTURAL_COMPUTATION.py`，与 Noether 守恒律并列 |
| B. **加入 Governance Fuse** | 如果系统试图"生成"连续坐标 → 熔断 |
| C. **理论层面保留** | 不编码，只作为设计指导 |

> **你需要决定**：这条定理应该被强制执行（如何检测违反？），还是作为设计准则？

---

## 决定 5：震荡验证的实验

回荡是否有周期性？T·S·I 是否有稳定关系？需要实验验证。

| 实验 | 测什么 | 预期 |
|------|--------|------|
| A. **Xin 自相关** | $C(\delta)$ 是否有周期峰 | 验证周期性 |
| B. **改变输入功率** | 减半/加倍振荡幅值，观察 Xin·Vest·$N_{eff}$ | 验证 T·S·I 约束 |
| C. **开启分化后对比** | 分化前后回荡振幅是否按 $1/N_{eff}$ 衰减 | 验证回荡下界公式 |

> **你需要决定**：先跑哪个实验？还是先把架构改完再实验？

---

## 决定 6：T/O/P/R/Xin 的递归深度

主层 = 第 0 层，影子层 = 第 1 层。

| 选项 | 含义 |
|------|------|
| A. **止于两层** | 主层 + 影子层 = 完整系统 |
| B. **允许 N 层** | 影子层可以有自己的影子层 → 递归 T/O/P/R/Xin |
| C. **理论上允许，代码上两层** | 保持两层实现，但理论框架支持 N 层 |

> **你需要决定**：两层够吗？还是需要更深的递归？

---

## 决定 7：运动势的定义

目前 motion_potential = Σ|Col.activation|。你提出过另一个定义：主层-影子层的差值。

| 选项 | 定义 | 含义 |
|------|------|------|
| A. **主层信号强度** | $\nu = \Sigma \|Col_i\|$ | "我在动多少"（一阶） |
| B. **主层-影子层差** | $\nu = \Sigma \|Col_i\| - \Sigma \|s\_Col_i\|$ | "我的运动状态与影子层的预期差多少"（二阶） |
| C. **影子层的 dK/dt** | $\nu = \frac{d}{dt}\Sigma \xi_i^2$ | "自由能在增还是在减"（三阶） |

> **你需要决定**：运动势应该是哪个层次的量？

---

# 第二部分：数理体系全貌

## 公理层

### 公理 0（切分定理）

> 系统不生成时间和空间。系统生成对客观时空的切分尺度。

推论：系统内部的"时间"= ISI（脉冲间隔）= 对客观时间的离散采样。系统内部的"空间"= W 矩阵的拓扑 = 对可能连接空间的选择性保留。

### 公理 1（T/O/P/R/Xin 递归）

系统的每个层次都是一个 T/O/P/R/Xin 五元组：

$$\mathcal{L}_n = (T_n, O_n, P_n, R_n, Xin_n)$$

层间关系：

$$R_{n+1} = f(Xin_n) \qquad \text{（上层的预测误差是下层的输入实在）}$$

$$Xin_n > \theta \implies T_n' = T_n \cup \Delta T \qquad \text{（预测误差驱动结构生长）}$$

### 公理 2（Noether 守恒）

$$\sum_{bundles} E_{in} = \sum_{bundles} E_{out} + \Delta E_{stored}$$

每步能量守恒。结构生长消耗能量。

---

## 结构层

### 超图 $\mathcal{H} = (V, \mathcal{E})$

- 顶点 $V$ = 所有 Neuron（~105 个主层 + 24 个影子层）
- 超边 $e \in \mathcal{E}$ = 每个 Bundle（连接多源多靶）
- 超边权重 $w_e$ = Bundle 的 Memristor 矩阵
- 超边状态 $fruit_e \in$ {dormant, growing, ripe, decayed}

### 超度量 $d_U: V \times V \to \mathbb{R}_{\geq 0}$

由 Mitosis 谱系定义：

$$d_U(i, j) = \text{最近公共祖先的分裂深度}$$

满足超度量不等式：$d_U(i,k) \leq \max(d_U(i,j), d_U(j,k))$

### 隐式度量 $d_W: V \times V \to \mathbb{R}_{\geq 0}$

由权重矩阵诱导：

$$d_W(i,j) = \frac{1}{w_{ij} + \epsilon} \quad \text{（连接越强，距离越近）}$$

---

## 动力学层

### 信号传播（O）

$$I_{j}(t) = \sum_{e: j \in targets(e)} \sum_{i \in sources(e)} w_{e,ij} \cdot a_i(t)$$

$$\frac{dV_j}{dt} = \frac{I_j - g_{leak} \cdot V_j}{C_j}$$

$$a_j(t) = \begin{cases} 1 & \text{if } V_j > V_{th} \text{ (spike)} \\ 0 & \text{otherwise} \end{cases}$$

### 学习（STDP → W 更新）

$$\Delta w_{ij} = \eta \cdot (a_i(t-1) \cdot a_j(t) - a_i(t) \cdot a_j(t-1)) \cdot DA$$

因果方向（pre 先 → post 后）→ 增强。反因果 → 减弱。DA 调制学习速率。

### 预测与张力

$$P_e(t) = \sum_{ij \in e} w_{ij} \cdot a_i(t)$$

$$\xi_e(t+1) = \xi_e(t) + (P_e(t) - R_j(t)) \cdot dt$$

$$Xin_e = |\xi_e|$$

---

## 生长层

### Sprout（发芽）

$$Xin_e > \theta_{sprout} \implies \mathcal{E} \leftarrow \mathcal{E} \cup \{e_{new}\}$$

新超边初始权重 = 0，fruit = dormant。

### Prune（修剪）

$$\bar{w}_e < \theta_{prune} \implies \mathcal{E} \leftarrow \mathcal{E} \setminus \{e\}$$

### Mitosis（分裂）

$$V_{fat,j} > \theta_{mitosis} \text{ for } \Delta t > \tau_{mitosis} \implies V \leftarrow V \cup \{j'\}$$

$$config_{j'} = config_j, \quad E_{j'} = E_j / 2$$

约束：$|motors_{axis}| \leq N_{max} = 20$，且 $efficacy_{axis} > \theta_{eff}$。

---

## 偏振层（时空分叉）

### Aff 偏振器

$$signal_{raw} \xrightarrow{Aff_{reg}} \bar{a}_{DC} \quad \text{（空间偏振：恒定分量）}$$

$$signal_{raw} \xrightarrow{Aff_{irr}} \tilde{a}_{AC} \quad \text{（时间偏振：变化分量）}$$

### 测度提取

$$\text{时间测度} \quad \mathcal{T}_{axis} = EMA(\tilde{a}_{AC,axis})$$

$$\text{空间测度} \quad \mathcal{S}_{axis} = EMA(\bar{a}_{DC,axis})$$

$$\text{运动势} \quad \nu = \sum_{axis} |Col_{axis}.activation|$$

### 偏振耦合（跨域，在影子层中）

$$\frac{\partial W_{time}}{\partial t} \xrightarrow{\text{cross-axis STDP}} \Delta W_{space}$$

$$\frac{\partial W_{space}}{\partial t} \xrightarrow{\text{cross-axis STDP}} \Delta W_{time}$$

介质 = 影子层跨轴 bundle。静态解耦，通过变化率耦合。

---

## 重整化塔

```
尺度 5: Maturation (新兵→成熟→老兵)     窗口 ~1M 步
         ↕ 粗粒化/约束
尺度 4: Fruit (dormant→growing→ripe)     窗口 ~100k 步
         ↕ 粗粒化/约束
尺度 3: Xin (|P-R| 累积)                 窗口 ~10k 步
         ↕ 粗粒化/约束
尺度 2: EMA (spike → 放电率)             窗口 ~100 步
         ↕ 粗粒化/约束
尺度 1: Spike (离散事件)                 窗口 = 1 步 (dt=0.001s)
```

每个尺度向上：粗粒化（信息压缩）
每个尺度向下：约束（冻结可塑性、限制生长）

---

## 信息界（猜想）

### 回荡下界

$$Xin_{echo} \geq \frac{H_{input}}{N_{eff} \cdot \Delta w}$$

$N_{eff}$ = 有效独立 motor 数，$\Delta w$ = 单个 motor 的权重精度。

### T·S·I 约束（待验证）

$$N_{eff} \cdot \Delta w \cdot f_{osc} \cdot \bar{\xi}_{vest} \leq P_{input}$$

崩解条件：结构容量满 + 振荡增频 → 空间测度塌缩 → 相变。

继承条件：新 T 诞生 → 容量增 → 新稳态。

### 递归信息流

$$\mathcal{L}_0 \xrightarrow{Xin_0} \mathcal{L}_1 \xrightarrow{Xin_1} \mathcal{L}_2 \xrightarrow{\cdots}$$

每层的预测误差是下层的输入实在。信息在层间不守恒——每层都有损耗（重整化代价）。
