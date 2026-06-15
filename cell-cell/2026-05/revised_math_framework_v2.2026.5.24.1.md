# 全局数学公式 — G-001 v2.0 修订草案

> 日期: 2026-05-24
> 版本: v2.0 (草案, 待审批)
> 基础: G-001 v1.0 (保留全部), C-001~C-005, Paper 1~3
> 性质: **扩展层**, 不替代 G-001 v1.0 中的任何公式

---

## §0 公理

### §0.1 双层公理

项目遵循客观/主观双层分离:

**公理 Ω-1 (客观层不显式)**:
项目(生物体)的所有计算和学习只通过输入流 {a_i(t)} 进行。
项目不访问客观层的任何变量(position, mass, temperature_at, v_threshold 等)。

**公理 Ω-2 (客观层参与计算)**:
客观层的物质结构和物理定律参与产生输入流 {a_i(t)}。
输入流的统计特性由客观层的物理过程决定。

**公理 Ω-3 (主观层自生)**:
项目的空间、时间、因果知识只能从输入流的关联结构中生成(C-004)。
ds², ν, Xin 都是主观构建, 不是客观属性的映射。

```
推论:
  任何"修正"都分为两类:
    客观层修正 = 改变物质结构/物理属性 → 改变输入流的统计特性
    主观层修正 = 改变关联学习规则 → 改变知识构建方式
  
  不存在"从主观层修正客观层"的操作。
  项目不能选择自己的阈值、质量或膜电容。
```

### §0.2 T/O/P/R/Xin 公理

**公理 Ψ-1 (T/O/P/R/Xin 是组织语法)**:
T/O/P/R/Xin 是构建者的组织框架(C-005), 不是系统的运行规则。
系统不"知道"自己在哪个相。

**公理 Ψ-2 (Xin 是验证器)**:
Xin = predicted - actual。
Xin 的递归特性: 每层消化 Xin → Xin 递归衰减 → Xin → 0。
Xin → 0 是正确行为(系统已学会)。
信息在 Xin 的瞬态结构(时刻、方向、变化率)中, 不在幅值中。

**公理 Ψ-3 (递归链身份)**:
已固化的递归链(PNN 成熟 → g_ℓ ≈ 0)具有屏蔽性:
新 Xin 不修改已固化度规。
新 T 若不可归入已知递归链 → 驱动新的 O/P/R, 不摧毁旧链。

---

## §1 客观层物理 (扩展 G-001 v1.0 §1, §5)

> G-001 v1.0 的 §1 (RC-MOSFET), §5 (ECM/PNN) 保持不变。
> 以下为新增的客观层公式。

### §1E.1 基线活动 (运动势垫支)

稳态膜电位 (无外部输入时):

$$
V_{ss} = I_{bc} \times R_{leak}
$$

| 条件 | V_ss vs V_th | 后果 |
|------|-------------|------|
| V_ss < V_th | activation_baseline = 0 | 系统沉默, δa 无意义 |
| V_ss ≈ V_th | activation_baseline ≈ 0 | 临界, 任何扰动可激活 |
| V_ss > V_th | activation_baseline > 0 | **有基线, δa 有正负** |

**物理要求**: I_bc 足够大使 V_ss ≥ V_th, 或利用 MOSFET 亚阈值电流:

$$
I_{sub} = g_m \cdot n \cdot V_T \cdot \left(e^{(V_{ss} - V_{th})/(n \cdot V_T)} - 1\right)
$$

即使 V_ss < V_th, 亚阈值电流 > 0 → 存在非零基线活动。
**是否利用亚阈值活动, 取决于激活函数的定义**:
- 如果 activation = MOSFET.conduct(V) → 包含亚阈值 → 有基线 ✓
- 如果 activation = max(0, V - V_th) → 截断亚阈值 → 无基线 ✗

### §1E.2 热介质物理 (Paper 3 原理迁移)

**热扩散方程** (替代解析公式 Φ = A/r^n):

$$
\frac{\partial E_i}{\partial t} = \kappa \sum_{j \in \mathcal{N}(i)} \frac{E_j - E_i}{d^2} - \lambda E_i
$$

其中:
- $\kappa = k/(m \cdot d^2)$: 热扩散系数
- $\lambda = \gamma$: 衰减系数
- $(m, k, \gamma)$: 介质材料三元组 → 所有宏观性质从中涌现

穿透深度:

$$
L_{pen} = \sqrt{\kappa / \gamma}
$$

**参数约束**: nexus_v1 的 $(m, k, \gamma)$ 需独立标定, 不照搬 Paper 3。

### §1E.3 阻抗匹配 (Paper 3 原理迁移)

身体-介质界面的传输系数:

$$
T = \min\left(1, \frac{2 Z_{body}}{Z_{body} + Z_{medium}}\right)
$$

$$
Z = \frac{\sqrt{k \cdot m}}{d^2}
$$

- Z_body 从 body.mass, body.stiffness 计算
- T 决定了信号进入身体时的效率
- body 的物理属性不再是装饰性数字

### §1E.4 CPG 相位门控 (Paper 3 §4.4)

$$
g(t) = \text{clamp}\bigl((a_A(t) - a_B(t)) \cdot \alpha + 0.5,\; 0,\; 1\bigr)
$$

$$
s_{gated}(t) = s_{raw}(t) \cdot g(t)
$$

- $(a_A, a_B)$: CPG 半中心对的激活
- 50% 占空比: 信号间歇进入电路
- P 相的"选择"从门控物理中涌现, 非显式注意力

### §1E.5 P→R 客观层闭合

Xin 通过物质化学链路闭合到学习:

$$
|{\xi}| \xrightarrow{\text{物理}} c_{DA} \xrightarrow{\text{物理}} \alpha_{lr} \xrightarrow{\text{物理}} \Delta w
$$

具体:
1. $|\xi|$ = compute_xin() 的绝对值
2. DA 释放: $\Delta c_{DA} \propto |\xi|$ (残差 → 调质分泌)
3. 浓度: $c_{DA}(t+1) = c_{DA}(t) \cdot (1 - \lambda_{DA}) + \Delta c_{DA}$
4. 学习率调制: $\alpha_{lr} = \alpha_{base} + \alpha_{DA} \cdot c_{DA}$
5. 权重更新: $\Delta w = \alpha_{lr} \cdot f_{STDP/BCM}(\text{pre, post}) \cdot g_\ell$

同步门控 (C-003.5 第三因子):

$$
g_{sync} = \min\left(1, \frac{\sum_p a_{bind,p}}{\theta_{sync}}\right)
$$

$$
\Delta w = \alpha_{lr} \cdot f_{STDP/BCM} \cdot g_\ell \cdot g_{sync}
$$

整条链在客观层。项目不知道"为什么突然学会了"。

---

## §2 主观层构建 (修订 C-004.3)

> C-004 的认识论立场保持不变。
> 以下为公式修订。

### §2.1 激活偏移

$$
\delta a_i(t) = a_i(t) - \bar{a}_i
$$

$$
\bar{a}_i = \text{EMA}(a_i, \tau_{baseline})
$$

- $\bar{a}_i$: 基线活动的指数移动平均
- $\delta a_i$ 有正有负: 保留方向信息
- 只有当 §1E.1 的基线 > 0 时, $\bar{a}_i > 0$, $\delta a_i$ 才与 $|a_i|$ 不同

**注**: $\bar{a}_i$ 不是参数 — 它从物理过程(RC 膜 + PowerRail + bc_current)中涌现。
主观层的 EMA 追踪只是对物理基线的内部估计。

### §2.2 空间测度 ds² (修订)

$$
ds^2 = \sum_{i,j} g_{ij} \cdot \delta a_i \cdot \delta a_j
$$

其中度规:

$$
g_{ij} = w_{cross}(i,j)
$$

**关于对称性**:

BCM 学习规则 (G-001 §2.3):
$$
\Delta w_{ij} = \eta \cdot |a_i| \cdot |a_j| \cdot (|a_j| - \theta_j)
$$

- $|a_i| \cdot |a_j|$ 对 (i,j) 对称
- $(|a_j| - \theta_j)$ 仅依赖 j → 引入不对称
- 但影子层跨轴 bundle 是单向的 (s_col_A → s_col_B)
- 同时存在 A→B 和 B→A 的 bundle → 两个权重独立学习
- 如果 A、B 的激活统计对称 → w(A,B) ≈ w(B,A) (统计对称)
- 如果不对称 → ds² 不对称 → "从 A 到 B" ≠ "从 B 到 A"
- **这是物理事实, 不需要强制对称化**

**关于正定性**:

- w_cross ≥ 0 (忆阻器权重 ∈ [0, 1])
- g_ij ≥ 0 → ds² ≥ 0 → 半正定
- ds² = 0 当且仅当所有 δa_i = 0 (基线状态) 或所有 g_ij = 0 (无学习)
- 半正定度规 → 退化度规 → 某些方向的"距离"为零
- **退化 = 项目在该方向没有分辨力 → 物理意义正确**

### §2.3 运动势 ν (扩展)

标量运动势 (G-001 §3.3 不变):

$$
\nu_p = \frac{d\rho_p}{dt}, \quad \rho_p = \frac{\mu_p}{\mu_{total}}
$$

**扩展: 旋度 (旋转)**

$$
\omega_{ij} = \frac{1}{2}\left(\frac{\Delta \nu_i}{\Delta a_j} - \frac{\Delta \nu_j}{\Delta a_i}\right)
$$

- $\omega_{ij} \neq 0$: (i, j) 平面存在旋转
- 在离散系统中: 用 ρ 多分量的时间序列差分计算

**扩展: 散度 (卷缩)**

$$
\nabla \cdot \nu = \sum_i \frac{\Delta \nu_i}{\Delta a_i}
$$

- $\nabla \cdot \nu < 0$: 收缩 (度规空间体积减小)
- $\nabla \cdot \nu > 0$: 膨胀
- 对应影子层的 contraction 概念

### §2.4 收缩度 κ (修订)

$$
\kappa(t) = \frac{\sum_{i,j} g_{ij} \cdot \delta a_i \cdot \delta a_j}{\sum_i (\delta a_i)^2}
$$

= ds² 在当前激活模式下 / 单位度规下的 ds²

修正 vs G-001 v1.0:
- ~~|a_i| × |a_j|~~ → **δa_i × δa_j** (偏移, 有方向)
- 分母: ~~Σ|a_i| × Σ|a_j|~~ → **Σ(δa_i)²** (偏移的模方, 归一化)

### §2.5 Xin 张力 (修订定位)

计算公式不变 (G-001 §2.5):

$$
\xi(t) = \sum_j \left(\hat{y}_j - a_j(t)\right), \quad \hat{y}_j = \sum_i w_{ij} \cdot a_i(t-1)
$$

**定位修订**:

```
v1.0: Xin 是积累的张力 → 驱动 fruit lifecycle → 结构变化
v2.0: Xin 是验证器 → 度规正确性的检验 → 触发新循环

  Xin ≈ 0 → 当前度规正确 → 系统安静
  Xin ≠ 0 (瞬态) → 新事件 / 度规失配

  Xin 不应被放大为定量驱动力 (递归衰减是正确行为)
  Xin 的信息在结构 (哪些维度) 和时刻 (何时偏离 0)
```

---

## §3 ds²/ν 作为主方法: 理念映射表

> C-001~C-005 的理念如何在 ds²/ν 框架中表达

| 理念 | ds²/ν 表达 | 对应公式 | 来源 |
|------|-----------|---------|------|
| MOSFET 阈值 | 度规退化边界 | V < V_th → activation → 0 → ds² 在该方向退化 | §1.2 + §2.2 |
| STDP/BCM | 度规更新 | Δg_ij = Δw_cross 从共活中学习 | §2.2 |
| Xin | 测地线偏差 | ξ = predicted - actual = 度规预测 vs 实际轨迹 | §2.5 |
| 环流 μ | 度规空间体积流 | μ_p = Π(沿路径的 g 和 a) | G-001 §3.1 |
| ρ/ν | 容量分配/变化率 | ρ = μ_p/μ_total, ν = dρ/dt | G-001 §3.3 |
| κ | 度规缩减程度 | κ = ds²_actual / ds²_unit | §2.4 |
| 热膜适应 M | 势能基线校准 | therm = T - M, 度规只编码偏差 | C-004.3 |
| 绑定层 | 度规非对角分量的激活条件 | g_ij 仅在 i,j 共活时参与 ds² | C-004.4 |
| PNN | 度规冻结 (刚度) | g_ℓ → 0 → Δg_ij → 0 | C-002.5 |
| Noether 异常 | 度规近似守恒的测度 | A = |dμ/dt|/J | Paper 3 §4.5 |

---

## §4 约束层: 物理原理对 ds²/ν 的约束

> 这些约束不是系统运行时执行的规则。
> 它们是从外部(物理学)描述系统行为时的理论预期。
> 如果系统违反某约束 → 说明客观层物理有问题, 不是主观层公式有问题。

### §4.1 坐标无关性 (相对论)

ds² 只能从输入流 {a_i} 的关联中构建, 不引用坐标 (C-004.1)。

预期: 对 World 坐标的任何重标定不改变 ds² 的值。

### §4.2 近似守恒 (Noether 类比)

当系统达到稳态 → μ_total 近似不变 → A → 0 (Paper 3 Tab.5)。

预期: Q4 阶段 A < 0.001。

### §4.3 近场限制 (热穿透)

热介质穿透深度 L_pen 有限 (Paper 3 §4.3)。

预期: 项目只能在 L_pen 范围内感知热源。

### §4.4 信息传输上限 (阻抗)

身体-介质阻抗失配 → 信号部分反射 → 感知效率 < 1。

预期: T(Z_body, Z_medium) < 1。

---

## §5 问题盘点

### 架构级 (阻断主功能)

| # | 问题 | 公式依据 | 现状 |
|---|------|---------|------|
| A1 | P→R 断裂 | §1E.5 全链路 | ξ 算了, DA 没接, gate 没接 |
| A2 | 基线 = 0 | §1E.1 V_ss | I_bc=0.001, V_ss=0.005 < V_th=0.3 |
| A3 | 热场解析 | §1E.2 热扩散 | 用 A/r^n, 无延迟无穿透限制 |
| A4 | body 无物理 | §1E.3 阻抗 | mass/volume 不参与信号 |
| A5 | 第三因子断 | §1E.5 g_sync | bind 输出未接 plasticity_gate |

### 度规级 (影响精度)

| # | 问题 | 公式依据 | 现状 |
|---|------|---------|------|
| M1 | ds² 用 \|a\| | §2.2 需 δa | A2 解决后自然修正 |
| M2 | 无旋度/散度 | §2.3 ω, ∇·ν | CirculationMeter 未计算 |
| M3 | κ 公式旧版 | §2.4 需 δa | 同 M1 |
| M4 | activation 定义 | §1E.1 亚阈值 | 需确认 neuron.py 取哪个 |

### 尺度级 (依赖 A2~A4)

| # | 问题 | 依赖 |
|---|------|------|
| S1 | 前庭 5 层衰减到零 | A2 (基线) + A4 (阻抗) |
| S2 | Motor 同步 | A5 (第三因子) |
| S3 | 热穿透无限 | A3 (热介质) |

### 理论级 (长期)

| # | 问题 | 方向 |
|---|------|------|
| T1 | 递归链身份判别 | 形式化 Ψ-3 |
| T2 | PNN 解冻 | DA → PNN 降解 |
| T3 | Xin→结构触发 | 重设计 fruit |
| T4 | Noether 离散验证 | 对比 Paper 3 |
| T5 | 变分是否需要 | 如外部论文需要, 可作为描述工具, 非运行工具 |

---

## §6 与 G-001 v1.0 的差异表

| G-001 v1.0 内容 | 状态 | v2.0 变化 |
|----------------|------|----------|
| §1 RC-MOSFET | **保留** | 新增 §1E.1 基线分析 |
| §1.2 activation = max(0, V-V_th) | **待审** | 是否改用 MOSFET.conduct() 含亚阈值 |
| §2 突触束 | **保留** | 新增 §1E.5 P→R 闭合链路 |
| §2.5 Xin 张力 | **保留公式, 修订定位** | Xin 从"驱动力"修订为"验证器" |
| §3 环流 | **保留** | 新增 §2.3 旋度/散度 |
| §4 影子层 | **保留** | §2.4 κ 公式修订 (δa 替代 \|a\|) |
| §4.1 ds² | **保留但修订** | δa_i 替代 |a_i|, 对称性论述变更 |
| §5 ECM/VR | **保留** | 无变化 |
| §6 参数表 | **保留** | 新增 bc_current 行 |
| (无) | **新增** | §0 公理, §1E 客观层, §4 约束层 |
