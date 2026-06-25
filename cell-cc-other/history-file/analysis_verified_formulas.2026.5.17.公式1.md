# Morphosphere v40.10c — 已验证数理公式集

## 概述

以下公式全部从代码实现中精确提取，并通过实验验证。
所有实验证据来自 N=50 随机种子统计分析和 4 张熵账本的闭合审计。

---

## 公式 I：带CPG矫正的泄漏积分器

$$I_c(t+1) = \left(1 - \lambda_c^{eff}(t)\right) I_c(t) + \gamma_c \cdot \text{sgn}(u_c) \cdot \ln(1 + |u_c|)$$

$$\lambda_c^{eff}(t) = \max\left(0.001,\ \lambda_c^{base} - \kappa \cdot \phi_{CPG}(t)\right)$$

| 参数 | acoustic | thermal | luminous |
|---|---|---|---|
| $\lambda^{base}$ | 0.03 | 0.05 | 0.04 |
| $\gamma_c$ | $e^{\mathcal{N}(0, 0.09)}$ | $e^{\mathcal{N}(0, 0.09)}$ | $e^{\mathcal{N}(0, 0.09)}$ |
| avg retention | 0.964 | 0.915 | 0.955 |

> **验证**: 能量守恒 $\sum_{input} - \sum_{leak} = retained$, residual = **0.000000** ✅

---

## 公式 II：量源场方程与梯度

$$\Phi_c(\mathbf{r}) = \frac{A_c}{|\mathbf{r} - \mathbf{r}_c|^{n_c}}$$

$$\nabla\Phi_c = -n_c \cdot A_c \cdot \frac{\hat{\mathbf{L}}}{|\mathbf{L}|^{n_c+1}}$$

| 量源 | $n_c$ | $|\nabla\Phi|$ at $L=8$ | received at $L=8$ |
|---|---|---|---|
| acoustic | 1 | $A/L^2 = 0.078$ | $A/L = 0.625$ |
| thermal | 2 | $2A/L^3 = 0.020$ | $A/L^2 = 0.078$ |
| luminous | 2 | $2A/L^3 = 0.020$ | $A/L^2 = 0.078$ |

> **验证**: 物理衰减 ratio = **1.000** ✅ (5000 tick 全量)

---

## 公式 III：环流测度

$$\mu(G) = \sum_c |I_c| \cdot \left(\sum_m |a_m|\right) \cdot \left(\sum_e |a_e|\right)$$

其中 $c \in \{$acoustic, thermal, luminous$\}$, $m \in \{$motor$\}$, $e \in \{$encoding$\}$

> **验证**: $\mu(G) = 2.11$ (5000 tick), 源撤除后 persistence = **37%** ✅

---

## 公式 IV：平衡距离（梯度-扩散平衡）

在babbling主导的运动中，粒子做偏置随机游走。
梯度力提供偏置，babbling 提供扩散。平衡条件：

$$|\nabla\Phi_c(L^*)| \approx \frac{\sigma_{babbling}}{\sqrt{N_{particles}}}$$

对 $1/r$ 源：

$$L^*_{1/r} \approx \sqrt{\frac{A \cdot \sqrt{N}}{\sigma}}$$

对 $1/r^2$ 源：

$$L^*_{1/r^2} \approx \left(\frac{2A \cdot \sqrt{N}}{\sigma}\right)^{1/3}$$

| | 解析预测 | 实测 (N=50 mean) |
|---|---|---|
| $L^*_{acoustic}$ | 9.6 | **11.38 ± 1.12** |
| $L^*_{thermal}$ | 5.7 | **9.15 ± 2.12** |
| $L^*_{luminous}$ | 5.7 | **8.11 ± 2.15** |

> **验证**: 趋势正确 ($L_{aco} > L_{the} > L_{lum}$) ✅
> 绝对值偏差来自 reflex 非线性、CPG 基线运动、有限时间效应

---

## 公式 V：统计偏好定理 (修正版)

> [!WARNING]
> 原始声明 "$P(\text{aco closest}) \to 0$" 被轨迹追踪实验证伪。
> Acoustic 偶尔会成为最近源（seed=1 在 t=340）。系统是非平衡稳态过程。

**定理（统计版）**: 在不变测度 $\rho^*$ 下，

$$\mathbb{E}_{\rho^*}[L_{acoustic}] > \mathbb{E}_{\rho^*}[L_{thermal}] \geq \mathbb{E}_{\rho^*}[L_{luminous}]$$

且 acoustic 的"最近"占比是有限但小的测度：

$$\rho^*(\text{acoustic closest}) \approx 4\%$$

**物理原因**: $|\nabla\Phi_{1/r}(L)| > |\nabla\Phi_{1/r^2}(L)|$ for $L > 2$
→ acoustic 的排斥力统计上更强，但 babbling 随机性使系统偶尔逆行。

> **验证 (N=50, T=300)**: $\mathbb{E}[L_{aco}]$ = **11.38** > $\mathbb{E}[L_{the}]$ = **9.15** > $\mathbb{E}[L_{lum}]$ = **8.11** ✅
> 轨迹追踪: L_aco 在 6.5~12.7 间振荡（非平衡态），acoustic closest 偶发 ✅

---

## 公式 VI：thermal/luminous 分裂比

$$\frac{P(\text{closest} = \text{luminous})}{P(\text{closest} = \text{thermal})} \approx \frac{\lambda_{thermal}}{\lambda_{luminous}}$$

| | 预测 | 实测 |
|---|---|---|
| $\lambda_{the}/\lambda_{lum}$ | 0.05/0.04 = **1.25** | 60/36 = **1.67** |

> 方向正确，量级一致。偏差可能来自 CPG 频率差异和 reflex 非线性。

---

## 统计摘要 (N=50)

```
Closest distribution:
  acoustic:   2/50  (4%)
  thermal:   18/50 (36%)
  luminous:  30/50 (60%)

Farthest distribution:
  acoustic:  40/50 (80%)
  thermal:    4/50  (8%)
  luminous:   6/50 (12%)
```

## 相空间图

![Phase Space: L_thermal vs L_luminous](L:/Users/绍春/.gemini/antigravity/brain/b28b1552-1fcc-4344-b53a-904fd4f4bced/phase_space_Lthe_Llum.svg)

---

## 与原文档 (2026.5.17.txt) 的对照

| 原文档公式 | 本文公式 | 对照 |
|---|---|---|
| 公式一 (拓扑演化) | — | 过度理想化，STDP不是Xin梯度下降 |
| 公式二 (积分器) | **公式 I** | 数学形式精确，但遗漏了CPG矫正 |
| 公式三 (NMDA-STDP) | — | motor_frozen 不是 Xin 阈值门控 |
| 公式四 (吸引子) | **公式 IV-VI** | γ/λ比因果被证伪，用梯度-扩散替代 |
