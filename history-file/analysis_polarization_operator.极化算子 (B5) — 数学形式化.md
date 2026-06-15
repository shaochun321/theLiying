# 极化算子 (B5) — 数学形式化

## 动机

电路中信号经过 Vest → Enc → Coupler → Col → Coupler → Motor 四层变换。
每层是一个**极化算子** — 将输入场映射为输出场，类似介质对电磁场的响应。

## 单层传递函数

### RC 膜 (Encoding / Column / Motor)

每个 spiking 神经元本质上是一个非线性 RC 滤波器 + 阈值检测器：

```
H_neuron(s) = 1/(1 + s·τ_RC)  ×  Θ(V_m - V_peak)
```

其中 τ_RC = C × R_leak，Θ 是 Heaviside 阈值函数。

离散化（dt=1.0）：

```
α = exp(-dt/τ)
V_m[n] = α · V_m[n-1] + (1-α) · I_in[n] · R
spike[n] = Θ(V_m[n] - V_peak)
```

### TemporalCoupler 传递函数

Coupler 是自适应低通滤波器。基础传递函数：

```
T_base(s) = 1/(1 + s·τ_base)     τ_base = C_couple × R_leak
```

#### C-layer 修正（快速反馈）

MOSFET 增加并联电阻 R_adapt = 1/g_adapt，当 ema > V_th：

```
g_adapt = gm × max(0, ema_down - V_th)
τ_eff = 1/(1/τ_base + g_adapt/C_couple)
T_C(s) = 1/(1 + s·τ_eff)
```

#### B-layer 修正（慢反馈）

差分比较器调制 R_leak → τ_base 漂移：

```
dV_slow/dt = gm·(ema_up - ema_down) - V_slow/(C_slow·R_slow)
R_eff = R_base × (1 + k·V_slow)
τ_base(t) = C_couple × R_eff(t)     （缓慢变化的参数）
```

**B-layer 不动点条件**：

```
dV_slow/dt = 0  ⟹  V_slow* = gm·R_slow·C_slow·(ema_up* - ema_down*)
```

当 ema_up* = ema_down* → V_slow* = 0 → R_eff = R_base（**阻抗匹配吸引子**）

## 全系统极化算子

### 线性近似（小信号分析）

```
P(ω) = H_enc(ω) × T_ec(ω) × H_col(ω) × T_cm(ω) × H_mot(ω)
```

展开：

```
P(ω) = 1/[(1+jω·τ_enc)(1+jω·τ_ec)(1+jω·τ_col)(1+jω·τ_cm)(1+jω·τ_mot)]
```

这是一个 **5 阶低通滤波器**。截止频率由最大的 τ 决定：

| 元素 | τ 值 | 截止频率 f_c = 1/(2πτ) |
|---|---|---|
| Encoding | 0.75 | 0.21 Hz |
| Coupler_ec | 2.0 (→ τ_eff ≈ 0.7) | 0.23 Hz |
| Column | 1.0 | 0.16 Hz |
| Coupler_cm | 2.0 (→ τ_eff ≈ 0.7) | 0.23 Hz |
| Motor | 1.5 | 0.11 Hz |

**总截止频率** ≈ 0.05 Hz（5 个串联 RC 的合成效应）。

### 非线性修正（大信号分析）

spiking 阈值引入非线性。用 firing rate 近似：

```
f(I) = 1/(τ_ref + τ_RC · ln(I·R/(I·R - V_peak)))    （I·R > V_peak 时）
f(I) = 0                                               （I·R ≤ V_peak 时）
```

这是一个 **f-I 曲线**（频率-电流关系），具有：
- 死区：I < V_peak/R → f = 0
- 线性区：I 稍大于阈值 → f ∝ (I - I_th)
- 饱和区：f → 1/τ_ref

### 自适应极化算子的不动点

系统的不动点满足所有 B-layer 稳定且所有神经元在 f-I 曲线的线性区：

```
ema_vest ≈ ema_enc ≈ ema_col ≈ ema_mot  （阻抗匹配）
V_slow_ec = V_slow_cm ≈ 0                （B-layer 平衡）
τ_eff ≈ τ_base                            （C-layer 无需修正）
```

这是系统的**全局吸引子**。偏离此态后，B-layer 在 ~1000 步内恢复。

## 与震荡/驻波的关系

5 阶系统在特定频率可以产生相位延迟 ≥ 180°（正反馈条件）。
如果 loop gain > 1 @ 这些频率 → **自激振荡**。

这就是之前观察到的 "调整元件引起震荡" 的数学解释：

```
Phase(ω_osc) = -180° → ΣΦ_layer = -π
|P(ω_osc)| × |G_feedback(ω_osc)| ≥ 1  → sustained oscillation
```

**驻波条件**：当电路拓扑形成闭环且满足相位匹配条件时，
Xin 的 ZCR（零交叉率）会升高 — 这正是 C4 检测到的信号。

> [!IMPORTANT]
> 驻波不是 bug — 它是结构性信息。高 ZCR 的 bundle 位于环路的"节点"，
> 低 ZCR 的位于"腹点"。这个拓扑信息可用于指导结构修剪（prune 节点 bundle）。
