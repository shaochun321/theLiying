# 前庭赫布超图：完整数学建模

## §0 设计意图

本文档定义**整个系统的数学结构**，包括所有变量、所有耦合方程、所有相变条件。
实施时按此文档整体落地，不逐条串行修补。

---

## §1 状态空间

### §1.1 元单元状态向量（单个 neuron）

每个元单元 $n_i$ 在时刻 $t$ 的完整状态：

$$
\mathbf{s}_i(t) = \Big( V_i,\; a_i,\; E_i,\; Q_i,\; w^{\text{adapt}}_i,\; x^{\text{pre}}_i,\; x^{\text{post}}_i,\; \text{Ca}_i,\; \Phi_i,\; M_i \Big)
$$

| 符号 | 含义 | 动力学 |
|------|------|--------|
| $V_i$ | 膜电压 | 膜方程（§2.1） |
| $a_i$ | 激活值（spike=1/0, graded=连续） | 阈值交叉 |
| $E_i$ | 能量（PowerRail 余量） | 消耗 + 恢复（§2.2） |
| $Q_i$ | 热输出（瞬时耗散功率） | $Q = \|a_i\| \cdot g_m$ |
| $w^{\text{adapt}}_i$ | 适应电流（SFA） | $\dot{w} = -w/\tau_w + b\cdot\delta(\text{spike})$ |
| $x^{\text{pre}}_i$ | STDP 前突触迹 | $\dot{x}^{\text{pre}} = -x^{\text{pre}}/\tau_{\text{pre}} + \delta(\text{input})$ |
| $x^{\text{post}}_i$ | STDP 后突触迹 | $\dot{x}^{\text{post}} = -x^{\text{post}}/\tau_{\text{post}} + \delta(\text{output})$ |
| $\text{Ca}_i$ | 钙浓度（自稳态传感器） | $\dot{\text{Ca}} = (\|a_i\| - \text{Ca})/\tau_{\text{Ca}}$ |
| $\Phi_i$ | 累积势能（potential） | $\dot{\Phi} = \|a_i\| \cdot \epsilon$ |
| $M_i$ | 成熟阶段 $\in \{0,1,2\}$ | 相变（§3） |

**成熟阶段编码**：$M=0$ (spine), $M=1$ (column), $M=2$ (area)

---

### §1.2 束状态向量（单个 bundle/超边）

每个超边 $b_k$ 连接源集 $S_k$ 到目标集 $T_k$：

$$
\mathbf{b}_k(t) = \Big( \mathbf{W}_k,\; \sigma_k,\; \mathcal{I}_k,\; \xi_k,\; \mathcal{F}_k,\; \lambda_k \Big)
$$

| 符号 | 含义 | 动力学 |
|------|------|--------|
| $\mathbf{W}_k \in [0,1]^{\|S_k\| \times \|T_k\|}$ | 权重矩阵（memristor 阵列） | 学习规则（§4） |
| $\sigma_k = \text{mean}(\mathbf{W}_k)$ | 束强度 | 从 $\mathbf{W}_k$ 导出 |
| $\mathcal{I}_k$ | 束惯性 | $\dot{\mathcal{I}} = -\eta_{\mathcal{I}} \cdot \|\Delta\mathbf{W}\|$ |
| $\xi_k$ | Xin 张力 | 预测残差积累（§6） |
| $\mathcal{F}_k$ | 果实状态 $\in \{\varnothing, \text{dormant}, \text{active}\}$ | 相变（§6.2） |
| $\lambda_k$ | 学习规则 $\in \{\text{stdp}, \text{bcm}, \text{frozen}\}$ | 成熟驱动切换（§4.4） |

---

### §1.3 层状态

每层 $L_\ell$ 有一个 ECM 场：

$$
\mathbf{e}_\ell(t) = \Big( \Theta_\ell,\; B_\ell,\; \pi_\ell \Big)
$$

| 符号 | 含义 | 动力学 |
|------|------|--------|
| $\Theta_\ell$ | 局部温度 | $\dot{\Theta} = (Q_{\text{in}} - G \cdot \Theta) / C$ |
| $B_\ell$ | 离子缓冲量 | $\dot{B} = r_{\text{abs}} \cdot Q_{\text{in}} - B/\tau_B$ |
| $\pi_\ell$ | PNN 成熟度 $\in [0,1]$ | $\dot{\pi} = (\pi^* - \pi)/\tau_{\pi}$ |

**可塑性门**（从 PNN 导出）：

$$
g_\ell = 1 - \pi_\ell
$$

---

### §1.4 全系统状态

$$
\mathcal{S}(t) = \Big\{ \{\mathbf{s}_i\}_{i=1}^{N},\; \{\mathbf{b}_k\}_{k=1}^{K},\; \{\mathbf{e}_\ell\}_{\ell=1}^{L},\; \mu(t),\; \boldsymbol{\rho}(t) \Big\}
$$

其中 $\mu(t)$ 是环流测度，$\boldsymbol{\rho}(t)$ 是 ρ 观测向量。

---

## §2 单步动力学（T 相：传输）

### §2.1 膜方程

**Spiking neuron**（AdEx-LIF）：

$$
C_i \frac{dV_i}{dt} = -g_L(V_i - V_{\text{rest}}) + I_{\text{syn},i} - w^{\text{adapt}}_i + I_{\text{noise}}
$$

$$
I_{\text{syn},i} = \sum_{k: i \in T_k} \sum_{j \in S_k} W_{k,ji} \cdot r_j \cdot G_k
$$

其中 $r_j$ 是源神经元 $j$ 的 release rate，$G_k$ 是突触增益。

**Spike 条件**：$V_i > V_{\text{peak}} \Rightarrow$ spike, $V_i \leftarrow V_{\text{reset}}$

**Graded neuron**（连续）：

$$
\frac{da_i}{dt} = \frac{1}{\tau_a}\Big(-a_i + f(I_{\text{syn},i})\Big)
$$

其中 $f$ 是 sigmoid 或 ReLU。

### §2.2 能量动力学

$$
\frac{dE_i}{dt} = R_{\text{supply}} \cdot (V_{dd} - E_i) - |a_i| \cdot g_m
$$

当 $E_i < E_{\text{min}}$ 时，$I_{\text{syn}} \leftarrow I_{\text{syn}} \cdot (E_i / E_{\text{min}})$（欠压保护）。

### §2.3 横向抑制（Column 层 IPSP）

$$
a_i^{\text{col}} \leftarrow \max\Big(0,\; a_i^{\text{col}} + h_i\Big)
$$

$$
h_i = -\alpha \sum_{j \neq i} \max(0, a_j^{\text{col}} - a_i^{\text{col}}) \cdot \kappa_{ij}
$$

$\kappa_{ij}$ 是抑制核（当前全连接 $\kappa=1$；area 成熟后 $\kappa$ 可稀疏化）。

### §2.4 反馈连接（Efference Copy）

Motor→Column 的抑制性反馈用 EMA 迹：

$$
\dot{f}_m = \frac{1}{\tau_f}\big(-f_m + \mathbb{1}[\text{spike}_m]\big)
$$

$$
a_i^{\text{col}} \leftarrow \max\Big(0,\; a_i^{\text{col}} - \beta \sum_m f_m\Big)
$$

---

## §3 成熟相变（spine → column → area）

### §3.1 转移条件

$$
M_i: 0 \xrightarrow{\pi_\ell > \theta_1 \;\wedge\; \Phi_i > \Phi_1} 1 \xrightarrow{\pi_\ell > \theta_2 \;\wedge\; \Phi_i > \Phi_2} 2
$$

| 参数 | spine→column | column→area |
|------|-------------|-------------|
| $\theta$ (PNN 阈值) | 0.3 | 0.7 |
| $\Phi$ (势能阈值) | 50 | 500 |

### §3.2 成熟效应

成熟改变**四个参数族**，用 $M$ 索引：

$$
\begin{aligned}
\text{plasticity}(M) &= \{0.18,\; 0.01,\; 0.001\} \\
\text{decay\_rate}(M) &= \{0.025,\; 0.005,\; 0.001\} \\
\text{lateral\_range}(M) &= \{0,\; 3,\; 5\} \\
\text{inertia\_floor}(M) &= \{1.0,\; 2.0,\; 5.0\}
\end{aligned}
$$

### §3.3 成熟驱动学习规则切换

$$
\lambda_k = \begin{cases}
\text{stdp} & \text{if } \max_{j \in T_k} M_j = 0 \text{ (target is spine)} \\
\text{bcm} & \text{if } \max_{j \in T_k} M_j = 1 \text{ (target is column)} \\
\text{frozen} & \text{if } \max_{j \in T_k} M_j = 2 \text{ (target is area)}
\end{cases}
$$

> [!IMPORTANT]
> 学习规则不是手动指定——它**从目标神经元的成熟度涌现**。spine 阶段用 STDP 快速学习，column 阶段用 BCM 竞争精炼，area 阶段冻结。

---

## §4 学习规则

### §4.1 STDP（spine 阶段）

$$
\Delta W_{ij} = \eta \cdot g_\ell \cdot \text{plasticity}(M_j) \cdot \Big( A^+ x^{\text{pre}}_i \cdot |a_j| - A^- x^{\text{post}}_j \cdot |a_i| \Big)
$$

乘法边界（soft bounds）：

$$
\Delta W_{ij} \leftarrow \begin{cases}
\Delta W_{ij} \cdot (1 - W_{ij}) & \text{if } \Delta W > 0 \\
\Delta W_{ij} \cdot W_{ij} & \text{if } \Delta W < 0
\end{cases}
$$

### §4.2 BCM（column 阶段）

$$
\Delta W_{ij} = \eta \cdot g_\ell \cdot \text{plasticity}(M_j) \cdot a_j \cdot (a_j - \theta_M^{(j)}) \cdot a_i
$$

滑动阈值：

$$
\dot{\theta}_M^{(j)} = \frac{1}{\tau_\theta}\Big(a_j^2 - \theta_M^{(j)}\Big)
$$

BCM 的关键：$a_j > \theta_M$ → 增强（强者更强），$a_j < \theta_M$ → 减弱（弱者被淘汰）。

### §4.3 Frozen（area 阶段）

$$
\Delta W_{ij} = 0 \qquad \forall i,j
$$

### §4.4 统一学习方程

$$
\Delta W_{ij} = g_\ell \cdot \text{plasticity}(M_j) \cdot \begin{cases}
\eta_S \cdot \text{STDP}(x^{\text{pre}}_i, x^{\text{post}}_j, a_i, a_j) & M_j = 0 \\
\eta_B \cdot \text{BCM}(a_i, a_j, \theta_M^{(j)}) & M_j = 1 \\
0 & M_j = 2
\end{cases}
$$

所有三条规则通过**同一个方程**调度，切换条件是 $M_j$（目标成熟度）。PNN 门 $g_\ell$ 在所有规则上乘法调制。

---

## §5 Binding Layer（超边层）

### §5.1 超边定义

一个超边（binding cell）$\beta_p$ 绑定一组列神经元：

$$
\beta_p = (\mathcal{A}_p, \; \theta_p, \; G_p, \; a_p)
$$

其中 $\mathcal{A}_p \subseteq \{1, \ldots, 6\}$ 是源轴集合（例如 $\{$yaw, pitch$\}$），$\theta_p$ 是共激活阈值。

### §5.2 超边激活函数（AND 语义）

$$
a_p = G_p \cdot \prod_{i \in \mathcal{A}_p} \text{ReLU}\Big(\frac{a_i^{\text{col}} - \theta_p}{\theta_p}\Big)
$$

**性质**：
- 若任一 $a_i < \theta_p$ → 乘积含零 → $a_p = 0$（AND 门）
- 当所有源轴都活跃 → $a_p > 0$（联合模式检测）
- 输出幅度 = 最弱源的归一化偏差

### §5.3 超边集合

初始集合：所有 $C(6,2) = 15$ 个二元组合，在 `build_circuit()` 时**结构性创建**。

$$
\mathcal{B} = \big\{ \beta_{\{i,j\}} \;:\; 1 \le i < j \le 6 \big\}
$$

初始权重极低（$W^{\text{bind}} \approx 0.001$），超边存在但几乎沉默。动力学（STDP/BCM）决定哪些被激活——结构提供可能性，物理计算选择哪些实现。

> [!IMPORTANT]
> **结构约束动态原则（正式定义）**：超边集合 $\mathcal{B}$ 由结构给定，不由影子层决定。影子层可以利用已有超边（通过度规收缩揭示哪些超边重要），但不能创建新的超边。影子层 = 探照灯，不是建筑工。

> [!NOTE]
> **未来升级路径 — DEGRADED 目标定义**
>
> 以下是日后可能替代当前定义的**未验证理论框架**，标记为降级（不实现）：
>
> 真实神经系统比集成电路更复杂：
> - **轴突出芽**（axonal sprouting）：损伤后神经元可以长出新的轴突分支
> - **突触新生**（synaptogenesis）：成年期仍可形成全新的突触连接
> - **神经发生**（neurogenesis）：海马齿状回可产生新神经元
> - **胶质引导**（glial guidance）：星形胶质细胞可引导新连接的方向
>
> 在生物学中，慢时间尺度的结构变化可以由动态驱动——影子层的持续压力或许真的能"长出"新的超边（神经链路）。
> 若实现，路径为：双重度规收缩 → 层级自由能 $\mathcal{K}$ → 运动势 $\nu = \nabla_z \mathcal{K}$ →
> 影子层 Xin 持续高张力 + 果实激活 → 触发 LiquidMetalRouter 创建新 bundle。
>
> 该框架的收敛性、稳定性、与 Xin 守恒的兼容性均未经验证，因此降级。
>
> `degraded_target = "dynamic_structural_plasticity_via_shadow"`
> `degraded_reason = "双重度规→层级自由能→运动势涌现 的完整链路尚未验证"`
> `refs = ["modeling_coupling_recursion_vfe.md", "modeling_hierarchical_prxin.md", "modeling_shadow_dual_metric.md"]`

### §5.4 Binding→Motor 连接

$$
I_{\text{bind},m} = \sum_p W^{\text{bind}}_{pm} \cdot a_p
$$

这与直通路 Col→Motor 并行：

$$
I_{\text{total},m} = \underbrace{\sum_i W^{\text{col}}_{im} \cdot a_i^{\text{col}}}_{\text{直通路（已有）}} + \underbrace{\sum_p W^{\text{bind}}_{pm} \cdot a_p}_{\text{旁路（超边）}}
$$

**关键**：两条路径独立学习。直通路记录"哪个单轴在动"，旁路记录"哪些轴同时动"。

---

## §6 P/R/Xin 环流

### §6.1 闭合回路

加入 Binding Layer 后，系统有闭合回路：

$$
\text{Col}_i \xrightarrow{W^{\text{bind}}} \beta_p \xrightarrow{W^{\text{bind-mot}}} \text{Mot}_m \xrightarrow{f_m} \text{Col}_i
$$

每条闭合路径 $\gamma$ 的流量：

$$
\phi(\gamma) = \prod_{k \in \gamma} \sigma_k
$$

其中 $\sigma_k$ 是路径上每个束的强度。

### §6.2 环流测度

$$
\mu(\mathcal{G}) = \sum_{\gamma \in \text{cycles}} \phi(\gamma)
$$

**P 环流** = $\arg\max_\gamma \phi(\gamma)$
**R 环流** = $\arg\max_{\gamma \neq P} \phi(\gamma)$

### §6.3 ρ 向量（外部观测）

$$
\boldsymbol{\rho} = (p_c, \; p_b, \; r_c, \; r_b, \; m_b, \; x, \; u) \in \Delta^6
$$

| 分量 | 含义 | 计算 |
|------|------|------|
| $p_c$ | P 路径中稳定（crystallized）部分 | $\phi(P) \cdot \mathbb{1}[\text{P bundles crystallized}] / Z$ |
| $p_b$ | P 路径中带宽（learning）部分 | $\phi(P) \cdot (1 - p_c\text{frac}) / Z$ |
| $r_c$ | R 稳定部分 | 同上类推 |
| $r_b$ | R 带宽部分 | |
| $m_b$ | masking（被抑制环路的贡献） | $\sum_{\gamma \notin \{P,R\}} \phi(\gamma) / Z$ |
| $x$ | Xin 张力总量 | $\sum_k |\xi_k| / Z$ |
| $u$ | 未解析残差 | $1 - p_c - p_b - r_c - r_b - m_b - x$ |

归一化：$Z = \mu(\mathcal{G}) + \sum_k |\xi_k| + \epsilon$，使 $\|\boldsymbol{\rho}\|_1 = 1$。

---

## §7 Xin 张力与果实

### §7.1 预测

每个束 $b_k$ 维护一个**预测信号**：

$$
\hat{a}_{k,j}(t) = \sum_{i \in S_k} W_{k,ij} \cdot a_i(t-\delta t)
$$

即用**上一步**的源激活和**当前**的权重预测目标激活。

### §7.2 Xin 张力积累

$$
\xi_k(t) = \xi_k(t-\delta t) + \sum_{j \in T_k} \big(\hat{a}_{k,j} - a_j\big) \cdot \delta t
$$

**Xin 守恒铁律**：张力的总变化必须可追溯。

$$
\frac{d}{dt}\sum_k \xi_k = \underbrace{\text{新增张力}}_{\text{预测误差}} - \underbrace{\text{被吸收}}_{\text{果实激活}} - \underbrace{\text{被耗散}}_{\text{束剪枝}}
$$

三个通道都必须在熵账本中记录。无记录的消失 = **守恒违规**。

### §7.3 果实生命周期

$$
\mathcal{F}_k: \varnothing \xrightarrow{|\xi_k| > \xi^*} \text{dormant} \xrightarrow{\xi_k \cdot \text{bias} > 0 \;\wedge\; |\text{bias}| > 0.3} \text{active} \xrightarrow{\text{consumed}} \varnothing
$$

**dormant**: 果实存储 $\xi_k^{\text{birth}}$ = 创建时的张力值。

**active**: 果实释放能量 → 可执行的结构操作：
- 增强对应 bundle 权重 $\Delta W = \eta_F \cdot \xi_k^{\text{birth}}$
- 或触发新束创建（LiquidMetalRouter 开新通路）

**consumed**: 果实的张力值转入熵账本的 "Xin 已消费" 栏。

---

## §8 结晶

### §8.1 结晶检测条件

Bundle $b_k$ 被标记为结晶当且仅当：

$$
\text{crystallized}(b_k) \iff \begin{cases}
\max_{j \in T_k} M_j = 2 & \text{(目标已 area)} \\
\text{Var}(\mathbf{W}_k) < \sigma^2_{\text{cry}} & \text{(权重方差小)} \\
|\dot{W}_{ij}| < \epsilon_{\text{cry}}\; \forall i,j & \text{(权重不再变化)}
\end{cases}
$$

$\sigma^2_{\text{cry}} = 0.01$，$\epsilon_{\text{cry}} = 10^{-4}$

### §8.2 结晶保护

结晶的束不参与 Xin 张力积累（预测已精确，残差为零）。如果外部扰动导致 $|\xi_k| > 0$，这是结晶破裂的信号 → 进入影子层。

---

## §9 影子层

> [!IMPORTANT]
> **当前正式定义**：影子层 = 下葬 + 衰减 + 共振。三个功能，不多不少。

> [!NOTE]
> **未来升级路径 — DEGRADED 目标定义**
>
> 以下是影子层的**未验证理论框架**，标记为降级（不实现）：
>
> 完整的影子层应为主系统的**副本沙盒**，运行自己的 T/O/P/R/Xin 生命周期，通过层级变分推断提取慢流形坐标和运动深度势（见 `modeling_coupling_recursion_vfe.md` §3-§4，`modeling_hierarchical_prxin.md` §1-§5，`modeling_shadow_dual_metric.md` §1-§3）。
>
> 具体路径：
> 1. 双重度规（主度规 + 影子收缩度规）
> 2. 影子层运行自己的 $P^{(1)}/R^{(1)}/Xin^{(1)}$
> 3. 层级自由能 $\mathcal{K} = \sum_n F^{(n)}$
> 4. 运动势从 $\nabla_z \mathcal{K}$ 涌现
> 5. 影子压力可能触发新超边创建（突破“结构约束动态”）
>
> 降级原因：完整链路（双重度规 → 层级自由能 → 运动势涌现）的收敛性、稳定性均未经数学验证，且实施复杂度高。
>
> `degraded_target = "hierarchical_variational_sandbox"`
> `degraded_reason = "双重度规→层级自由能→运动势涌现 的完整链路尚未验证"`

### §9.1 下葬条件

$$
\text{inter}(b_k) \iff \sigma_k < \sigma_{\text{prune}} \;\wedge\; \dot{\sigma}_k < 0
$$

下葬时存储：$(\mathbf{W}_k^{\text{death}}, \; \xi_k^{\text{death}}, \; \mathcal{F}_k^{\text{death}}, \; \Phi^{\text{death}})$

### §9.2 影子能量衰减

$$
E^{\text{shadow}}_k(t) = E^{\text{shadow}}_k(0) \cdot (1 - \delta_s)^{t/\tau_s}
$$

当 $E^{\text{shadow}} < E_{\text{expire}}$ → 从影子层移除（necropolis）。

### §9.3 共振检测

$$
\text{cosine}(\mathbf{W}^{\text{shadow}}_k, \; \mathbf{W}^{\text{live}}_j) > \theta_{\text{echo}} \Rightarrow \text{echo}
$$

共振只**记录到熵账本**，不反写主线。

---

## §10 时间尺度分离

| 过程 | 时间尺度 | 每步执行？ |
|------|---------|-----------|
| 膜方程 | $\sim$ ms | ✅ 每 dt |
| STDP trace decay | $\sim$ 20 ms | ✅ 每 dt |
| 适应电流 | $\sim$ 2 s | ✅ 每 dt |
| 能量恢复 | $\sim$ 10 s | ✅ 每 dt |
| ECM 温度 | $\sim$ 5 s | ✅ 每 dt |
| PNN 成熟 | $\sim$ 100 s | ✅ 每 dt |
| 成熟相变 | $\sim$ 100-500 s | 检查间隔 1s |
| 学习规则切换 | 与成熟同步 | 与成熟同步 |
| 果实创建 | 事件驱动 | 当 $|\xi| > \xi^*$ |
| 影子层维护 | $\sim$ 1000 s | 周期性 |
| 环流检测 | $\sim$ 1 s | 周期性 |
| ρ 计算 | $\sim$ 1 s | 周期性 |

---

## §11 守恒律与审计

### §11.1 能量守恒（第一定律）

$$
\sum_i E_i(t) + \int_0^t \sum_i Q_i(\tau)\,d\tau = \sum_i E_i(0) + \int_0^t P_{\text{supply}}(\tau)\,d\tau
$$

熵账本每步检查误差 $< 10^{-6}$。

### §11.2 Xin 守恒

$$
\sum_k \xi_k(t) = \sum_k \xi_k(0) + \underbrace{\sum_{\tau \le t} \Delta\xi^{\text{pred}}(\tau)}_{\text{预测误差累积}} - \underbrace{\sum_{\tau \le t} \xi^{\text{fruit}}(\tau)}_{\text{果实消费}} - \underbrace{\sum_{\tau \le t} \xi^{\text{prune}}(\tau)}_{\text{剪枝耗散}}
$$

任何不属于这三个通道的 $\xi$ 变化 = **守恒违规**。

### §11.3 信息流审计

层间传递效率：

$$
\eta_{\ell \to \ell'} = \frac{I(\mathbf{a}_\ell; \mathbf{a}_{\ell'})}{H(\mathbf{a}_\ell)}
$$

其中 $I$ 是互信息，$H$ 是熵。用 ISI 直方图近似。

---

## §12 运动势（涌现量）

$$
\boldsymbol{\nu}(t) = \frac{d\boldsymbol{\rho}}{dt}
$$

运动势**不是一个独立的变量**——它是 ρ 向量的时间导数。当系统处于稳态时 $\boldsymbol{\nu} = 0$；当运动模式切换时 $\|\boldsymbol{\nu}\|$ 峰值。

---

## §13 完整单步流程

```
input: mechanical_inputs, dt

── T 相 (传输) ──────────────────────────────────
1. 膜方程: ∀i, update V_i, a_i, w_adapt        (§2.1)
2. 能量: ∀i, update E_i, Q_i                    (§2.2)
3. STDP traces: ∀i, decay x_pre, x_post         (§1.1)
4. Calcium: ∀i, update Ca_i                      (§1.1)
5. 横向抑制: Col 层 IPSP                         (§2.3)
6. Binding: ∀p, compute a_p                      (§5.2)
7. Motor input: I_total = direct + binding       (§5.4)
8. Feedback: update f_m, apply IPSP              (§2.4)
9. ECM: update Θ, B, π                           (§1.3)

── O 相 (观测, 外部) ──────────────────────────────
10. 熵账本: record(circuit, dt)                   (外部)
11. 能量守恒检查                                    (§11.1)

── 学习 ──────────────────────────────────────────
12. ∀k, Δw = unified_learn(λ_k, g_ℓ, M_j, ...)  (§4.4)
13. Xin: ∀k, update ξ_k                          (§7.2)
14. Fruit: check dormant/active transitions       (§7.3)
15. Xin 守恒检查                                    (§11.2)

── 成熟 (慢周期) ─────────────────────────────────
16. ∀i, update Φ_i, check M transition           (§3.1)
17. 学习规则切换: ∀k, update λ_k from M_j        (§3.3)

── 环流 (慢周期) ─────────────────────────────────
18. detect P, R circulations                      (§6.2)
19. compute ρ vector                              (§6.3)
20. compute ν = dρ/dt                             (§12)

── 维护 (极慢周期) ───────────────────────────────
21. pruning: if σ_k < threshold → inter to shadow (§9.1)
22. shadow decay + resonance check                (§9.2-3)
23. crystallization check                         (§8.1)
```

---

## §14 Open Questions

1. **BCM 的 $\theta_M$ 初始值**：$\theta_M(0) = \text{target\_rate}$ 还是 $0$？
   - 建议：$\theta_M(0) = \text{Ca}(0) = \text{target\_rate}$（与自稳态一致）

2. **超边 pruning**：当一个二元组合长期不被激活时，是否剪枝？
   - 建议：是。$\sigma_p < 0.02$ 且 $a_p = 0$ 持续 1000 步 → 下葬

3. **ρ 更新频率**：每步还是每秒？
   - 建议：每秒（ρ 是宏观量，不需要 ms 分辨率）

4. **影子层最大容量**：无限制还是有上限？
   - 建议：上限 = 当前活跃束数量的 3× (影子不应比活跃结构大太多)
