---
tags: [专题分析, TSI, 三角约束, Landauer, Noether, 统一度量, 500k, 相变]
concepts: [TSI, T-S-I, Landauer界, Bekenstein界, 统一度量, 功率量纲, 耦合常数, 相变条件, 结构容量, Xin稳态, 500k实证, DA饥饿墙, 热力学时间, 代谢率, FEP]
type: 专题分析
date: 2026-06-17
aliases: [TSI理论, TSI约束, 三角约束, tsi-constraint]
---
# T·S·I 三角约束：理论 · 统一 · 实证 · 修正

> **核心概念**: T·S·I 是系统的一个单一约束的**三个投影面**，不是三个独立系统。
> **当前状态**: 度量已统一（功率量纲），实证已运行（500k 步），P×H 守恒被推翻，Landauer 界重新定标。
> **数据来源**: 9 份核心文档（理论、数学、实证、论文）

---

## 一、T·S·I 的定义

### 核心方程

$$T \cdot S \cdot I \leq P_{input}$$

或等价的:

$$N_{eff} \cdot \Delta w \cdot f_{osc} \cdot \text{mean}(\xi_{vest}) \leq P_{input}$$

其中:

| 量 | 含义 | 物理对应 | 量纲 (统一前) | 量纲 (统一后) |
|----|------|----------|------------|------------|
| **T** | 拓扑结构/能量框架 | 时间常数 (τ=RC)、能量 (E=½CV²) | [energy] | **[power] = dE_T/dt** |
| **S** | 结构动力学/权重矩阵 | 权重熵 (H_struct)、重塑代价 (κ·\|ΔW\|) | [dimensionless] | **[power] = dE_S/dt** |
| **I** | 输入通量/信息张力 | Xin=\|P-R\|、ξ_i | [V] | **[power] = dE_I/dt** |

---

## 二、度量统一：一切皆功率

> 来源: [[2026-06/analysis_TSI_metric_unification.2026.6.5]] · [[docs/theory/T005_TSI]]

### 核心洞察

T·S·I 的三个分量之前混合了三种不兼容的量纲（能量/无量纲/电压）。统一方案将三者归约为单一的**能量耗散率 [功率] = dE/dt**:

```
T (时间/能量):
  dE_T/dt = I²_membrane × R_leak + I²_supply × R_internal + basal_cost
  [power] ✓

S (结构/权重):
  dE_S/dt = κ × |ΔW/Δt|
  [power] ✓

I (信息/预测误差):
  dE_I/dt = Σ (ξ_i² × G_i²) / R_membrane
  [power] ✓
```

### 耦合常数（由硬件决定，非自由参数）

| 耦合 | 名称 | 公式 | 当前值 |
|------|------|------|--------|
| **T ↔ I** | Landauer 界 | α_TI = kT_system × ln2 | ≈ 0.07 |
| **T ↔ S** | 重塑代价 | α_TS = remodel_cost_kappa | 0.001 ~ 0.002 |
| **S ↔ I** | Xin 从 W 涌现 | ξ_i = \|Σ_j w_ij·a_j - a_target\| | 函数关系 |

### 统一耦合方程

```
dE_total/dt = dE_T/dt + α_TS × dE_S/dt + α_TI × dE_I/dt

Noether 守恒:
  E_in(vascular) = dE_T/dt + α_TS×|ΔW/Δt| + α_TI×|ΔH/Δt| + Q_waste
```

每一项都是 [power] ✓

---

## 三、ds²/ν 的热力学含义

> 来源: [[2026-06/analysis_TSI_metric_unification.2026.6.5]]

```
ds² = Σ ΔV²_i × C_i    [V² × F = J] → 微分能量（系统的储能变化）
ν   = Σ I²_j × R_j    [A² × Ω = W] → 耗散功率（系统的即时功耗）
ds²/ν                   [J/W = s]  → 热力学时间
```

**ds²/ν 的物理意义**:

> 它是系统的"**热力学时间**"——不是钟表时间，而是"以当前耗散速率，系统的储能能维持多久"。
> 对应生物学的**代谢率**（metabolic rate = 功率 → 决定生物时间尺度）。
> 小鼠代谢快 → ds²/ν 小 → 生物时间快。大象代谢慢 → ds²/ν 大 → 生物时间慢。
> **REF: Kleiber's Law (1932): P ∝ M^{3/4}**

---

## 四、P×H 守恒的推翻

> 来源: [[docs/theory/T005_TSI]]

### 原始假说

$$P_ν \times H_{flow} = \text{const}$$

### 三对照实验 (v1.6.0) — 全部否定

1. **随机权重**: 仍然"守恒" → **统计伪发现**（不是结构导致的）
2. **冻结权重**: 仍然"守恒" → **不依赖学习**（不是 STDP 导致的）
3. **零输入**: 趋向常数 → **初始条件决定**（不是动力学导致的）

**结论**: P_ν × H_flow 的稳定性是 EMA 平滑 + 有界变量的数学必然，**不是物理守恒**。

### T·S·I 不因 P×H 失败而失败

P×H 只是 T·S·I 的**一个候选代理变量组合**。这个组合失败了，但 T·S·I 的三个基本面 (T 能量/S 结构/I 信息) 仍然是系统的三个相互耦合的保值方向。

**500k 实测中的真正不变量**:

- `I_norm ≈ 0.664` (Xin 分布均匀性) — **在 N 变化时不变** → 结构生长保持了信息分配公平性

---

## 五、500k 实证：DA 饥饿墙

> 来源: [[2026-06/analysis_P23_metabolic_constraint.P2.3-T·S·I-代谢约束-500k数据分析]]

### 核心发现

```
deposited  = 1108.8  (500k 步总入)
withdrawn  = 1571.1  (500k 步总出)  
deficit    = -462.3  (来自 initial fill 500)
Noether    = 0.0 (完美守恒)
```

**系统从未达到能量自给自足。**

### 每步功率分解

| 项目 | 值/step | 占消耗比 |
|------|---------|----------|
| P_deposit | 0.002218 | — |
| P_DA refill | 0.003000 | 95.6% |
| P_ES basal drain | 0.000100 | 3.2% |
| P_bundle basal | 0.000034 | 1.1% |
| **P_net** | **-0.000882** | — |

> DA 消耗 > 世界总产能。Bundle basal cost 仅占 1.1%。
> P2.1 的热力学天花板本意是 bundle 代谢墙，但实际是 **DA 饥饿墙**。

### P_deposit 为何这么低

```
max_deposit_per_step = 0.05   (设计值)
actual deposit rate   = 0.002 (实测，仅 4.4%)
```

原因: body 大部分时间远离热源 (distance > 30)，`energy ∝ 1/distance²` → 距离远时几乎无收入。

### N_max 重新推导

$$N_{max} = \frac{E_0}{(\sum P_{drain} - P_{deposit}) \times \Delta t_{growth}}$$

当前 N_max ≈ 60（由初始 reserve E₀=500 决定，不是由稳态 power inflow 决定）。

### 四个修正方案

| 方案 | 做法 | T·S·I 含义 |
|------|------|-----------|
| A: 提高世界产能 | CONSUME_RATE↑ | 治标——掩盖了"系统无法自给"的根本问题 |
| B: 降低 DA 消耗 | DA_REFILL_RATE↓ | 治标——改变了 T·S·I 中 T 分量的基线 |
| C: DA 按需 refill | 仅在 DA < 阈值时 refill | 减少浪费——但未解决根本动力问题 |
| **D: 接受暂态 ✓** | 设计"进食行为"增加 P_deposit | **热趋性闭环**——这才是 T·S·I 的正确应用 |

---

## 六、理论锚点

> 来源: [[docs/theory/T006_theoretical_anchors]]

T·S·I 所在的四个外部理论框架:

### 1. Landauer 原理 → T ↔ I 换算率

$$\Delta E \geq kT \ln 2 \cdot |\Delta H|$$

消除 Xin 误差 = 信息擦除 → 必须消耗能量。metabolic_tax: κ × |ΔW/Δt| = Landauer 代价的电路实现。NoetherProbe T1.3 持续通过 (21/21)。

**结构推论**: 废除 MAX_BUNDLES 硬上限后，Landauer 原理自动提供容量上限: 每个 bundle 维持其信息状态的最小功耗 ≥ kT ln2 × 信息位数。当 N_b × P_maintain > P_input 时，系统在物理上被绝对逼停。

### 2. 自由能原理 (FEP) → I 驱动 S 与 T

$$\Xi = |P - R| = \text{FEP 的 Surprise（电路版）}$$

T·S·I 约束 = Free Energy 最小化的三个梯度方向:
- perception: 更新 q(s) → 对应 T
- learning: 更新 θ (params) → 对应 S
- action: 更新 a → 对应 I (减少预测误差)

### 3. 构造定律 (Constructal Law) → S ↔ I 流网络

系统倾向于发展出使信息/能量流更好地穿过系统的结构。

### 4. Merzenich (1984) 皮层重组 → 在 T·S·I 中的浮现

> 来源: [[docs/theory/PAPER_structural_reorganization]]

Merzenich 的核心发现: 活跃皮层区域扩张，闲置区域收缩。

在 T·S·I 框架下:
- 高 Xin 束 = "活跃" 的代谢/信息通路 → 吸引更多 Sprout
- 低 Xin 束 = "闲置" → 被 Prune
- **预测误差 (I) 驱动的结构重组 (S) 在能量约束 (T) 下自动产生 Merzenich 行为**

500k 步验证: 9 个真正的活动依赖扩张事件 + 579 个收缩事件。

---

## 七、结构容量极限与相变条件

> 来源: [[2026-06/analysis_TSI_parameter_equations.2026.6.5]] · [[交叉比对/影子层稳态重建与宏观行为涌现 —— 结构容量极限、动力学软平权与热趋性大一统方案]] §3

### 颅骨闭合条件

$$\frac{dN_{bundle}}{dt} = \kappa_{sprout} \cdot \Theta(\Xi_{local} - \Xi_{thresh}) \cdot \Theta(C_{max} - N_{bundle})$$

当 N_bundle → C_max=20 时，第二项阶跃归零 → dN_bundle/dt ≡ 0。**拓扑形态发生学遭到绝对物理冻结。**

### 相变条件

```
结构容量满 (N → C_max) + 振荡频率 ↑ → 空间度量坍缩 → 失去空间分辨率 → 相变
```

**相变前**: 体系通过增加结构 (sprout) 来吸收惊奇 (Xin)。

**相变后**: 体系无法再增加结构 → 惊奇必须通过**行为输出**来消除。**必须移动**。

**阻挫驻波 (Reverberation) = 健康的生存压力**:

$$\lim_{t \to \infty} \Xi_{total}(t) = \Xi_{base\_noise} + \Xi_{reverb} \approx \text{Const}$$

50k 步后 Xin 稳定在 ~87 的本源正在于此。**绝对禁止修改 C_max。** 容量极限不是缺陷，是系统诞生宏观自我意志的刻刀。

### 可检验预测

改变输入功率 (Decision 5 — 系统辨识标准方法):
- 设置 3 个功率水平 (0.5× / 1× / 2×)，各跑 50k 步
- 预测: **T·S·I 保持恒定 (±15%)**

---

## 八、T·S·I 与环流记忆的定点关系

> 来源: [[2026-06/analysis_TSI_parameter_equations.2026.6.5]]

环流 = T·S·I 动力学的**不动点**:

```
环流 = {V*, W*, ξ*} 使得:
  dV*/dt = 0  (热力学平衡)
  dW*/dt = 0  (权重收敛)
  dξ*/dt = 0  (预测误差稳定)

当 input 改变时:
  系统离开 {V*, W*, ξ*}
  T·S·I 驱动系统 → 新的不动点 {V**, W**, ξ**}
  回归轨迹 = 环流的"记忆"
```

"环流记忆落地" = 系统能稳定到不动点 + 能从扰动中恢复。

---

## 九、约束流形

> 来源: [[2026-06/analysis_TSI_parameter_equations.2026.6.5]]

以下约束形成一个**耦合流形**——参数的任何合法组合必须落在上面:

```
输入有界:     ∀i: I_i ∈ [0, G_xin]                         ← divisive normalization
输出有界:     ∀n: a_n ≤ 1/τ_ref (spiking)                    ← spike upper bound
能量守恒:     E_total(t+1) = E_total(t) + δ ± ε              ← Noether T
权重守恒:     |ΔW_total/Δt| < ε_w                             ← Noether S
Xin 稳定:     lim(t→∞) Σ|ξ_i(t)| = const                     ← 500k 实证 (稳定在 ~87)

耦合约束:
  τ × G × a_max ≤ V_peak × (1 + VR_max)                     ← 稳态不溢出
  η × f(DA) → 0 as PNN → 1                                   ← 结晶化停止学习
  Xin(W, τ, G, θ) = Σ_i |Σ_j w_ij a_j - a_target_i|          ← Xin 依赖全部参数
```

---

## 十、与项目其他三根主轴的关系

| 主轴 | T·S·I 中的作用 |
|------|--------------|
| **Xin → 规模生长** | Xin = I 分量。高 Xin → 消耗更多能量 (T) + 触发 sprout (S) |
| **母本分化** | 新增分化组件 = 新增 T/E/I 分量 → 自动继承统一功率量纲 |
| **熵账本** | 审计 T·S·I 的四个守恒不变量。Landauer 界 = T↔I 耦合常数 |
| **搏动/VitalOscillator** | 基底 T 消耗（心脏耗能）+ 创造 I 时变信号 (dT/dt) |

---

## 十一、当前理论状态

| 问题 | 状态 | 备注 |
|------|------|------|
| T·S·I 度量统一了吗？ | ✅ 统一到功率 [dE/dt] | 基于硬件原语同质性 |
| P×H 守恒成立吗？ | ❌ 否定 | 统计伪发现，不是物理守恒 |
| Landauer 界在代码中正确吗？ | ⚠️ 部分正确 | 缺 kT 乘子（已知 bug） |
| N_max 有物理上限吗？ | ✅ 由储备深度决定，非稳态 | 暂态系统 |
| Merzenich 行为涌现了吗？ | ✅ 500k 步确认 | 9 扩张 + 579 收缩 |
| 环流记忆 = T·S·I 的不动点？ | ⚠️ 理论推导，待实证 | 需要 {V*,W*,ξ*} 三者同时稳定 |
| T·S·I 恒定预测可检验吗？ | ⏳ 待实验 | Decision 5: 改变输入功率 |

---

## 📂 关键文件索引

### 理论核心
- [[docs/theory/T005_TSI]] — T005: T·S·I 框架（P×H 否定后的状态）
- [[docs/theory/T006_theoretical_anchors]] — T006: 理论锚点（Landauer + FEP + 构造定律 + Margolus-Levitin）
- [[docs/theory/PAPER_structural_reorganization]] — Merzenich 皮层重组在 T·S·I 中的浮现

### 数学统一
- [[2026-06/analysis_TSI_metric_unification.2026.6.5]] — **度量统一**: 一切归约为功率
- [[2026-06/analysis_TSI_parameter_equations.2026.6.5]] — **参数方程**: T/O/P/R/Xin 与四类结构参数的映射

### 500k 实证
- [[2026-06/analysis_P23_metabolic_constraint.P2.3-T·S·I-代谢约束-500k数据分析]] — DA 饥饿墙 + N_max 重新推导

### 大一统应用
- [[交叉比对/影子层稳态重建与宏观行为涌现 —— 结构容量极限、动力学软平权与热趋性大一统方案]] §3 — 颅骨闭合 + 阻挫驻波

### 项目主轴中的 T·S·I
- [[专题分析/Xin驱动规模生长-机制与实测]] — Xin = I 分量
- [[专题分析/熵账本构建规范-约束与纪律]] — 熵账本审计 T·S·I 守恒
- [[专题分析/母本分化与元件构建原则-融合版]] — 新分化组件 = 新增 T/E/I 分量
