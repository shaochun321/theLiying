# 结构参数 ↔ T/O/P/R/Xin 递归架构：方程推导

> 2026-06-05 — 理论分析

---

## 1. 参数注册表与约束方程

### 1.1 四类结构参数

| 类别 | 参数 | 符号 | 约束来源 |
|------|------|------|---------|
| **时间常数** | C, R_leak, τ_RC | τ = C·R | T (Topology 时间结构) |
| **增益链** | synapse_gain, XIN_GAIN, gm | G | O (Operator 算子增益) |
| **阈值** | v_threshold, v_peak, silence_threshold | θ | P (Polarization 极化边界) |
| **学习率** | stdp_lr, remodel_cost_κ, vr_base_rate | η | R (Remodel 重塑速率) |

**Xin** 不是参数——它是以上四类参数相互作用的**涌现结果**：
```
Xin_i = f(τ_pre, τ_post, G, θ, η, input_i)
```

### 1.2 有界性约束方程

T7+T1/T3/T4 测试揭示的核心约束：

**约束 1：非脉冲神经元的稳态方程**

```
V_ss = I_total × R_leak / (1 + VR_eff)

其中：
  I_total = Σ_j (a_j × w_j × G) + I_bc           ... 输入电流
  VR_eff = min(r_base + r_coeff × V_ss, r_max)    ... VR 有效速率

稳态条件：
  V_ss(1 + VR_eff) = I_total × R_leak
  V_ss(1 + min(r_base + r_coeff × V_ss, r_max)) = I_total × R_leak
```

当 `VR_eff → r_max`（饱和）：
```
  V_ss = I_total × R_leak / (1 + r_max)
```

**如果 I_total 无界，V_ss 无界。** VR 只提供有限衰减，不是硬上界。

**约束 2：脉冲神经元的硬上界**

```
activation ≤ 1 / τ_ref     (受不应期限制)
V_m ∈ [v_reset, v_peak]    (电压硬裁剪)
```

脉冲 = 唯一的结构性硬上界。这是 Plan D 引入 spiking 的数理理由。

**约束 3：输入有界条件（divisive normalization）**

```
I_normalized = |ξ_i| / max_j(|ξ_j|) × G_xin ∈ [0, G_xin]
```

无论 Xin 绝对值如何增长，归一化后的输入始终 ∈ [0, G_xin]。

### 1.3 T/O/P/R/Xin 与参数的映射方程

```
T (Topology):
  τ_layer = C × R_leak
  τ_system = max(τ_layer_i)  →  系统最慢时间尺度
  约束: τ_shadow / τ_main ≈ 3  (设计选择)
  方程: τ_shadow_col = 3.0 × 5.0 = 15 ms
        τ_main_col   = 0.05 × 5.0 = 0.25 ms

O (Operator):
  G_total = Π_k G_k  (增益链乘积)
  影子链: G = XIN_GAIN × syn_gain = 3.0 × 10.0 = 30 (原始)
  Plan D: G = 3.0 × 1.0 (归一化后) ∈ [0, 3.0]
  约束: G_total × a_max ≤ V_peak / R_leak  (输出不超过 spike 阈值)

P (Polarization):  
  θ_net = v_threshold + silence_threshold + maturation_gate
  约束: θ_net < V_ss_baseline  (baseline 不被门控)
  方程: 0.01 + 0.0005 < 0.005 × 5.0 = 0.025  ✓

R (Remodel):
  η_eff = stdp_lr × (1 - crystallization) × DA_gain
  约束: η_eff → 0 as t → ∞  (收敛)
  方程: 0.005 × (1 - PNN) × da_factor → 0 当 PNN → 1

Xin (涌现):
  Xin_i = |predicted_i - actual_i|  
         = |Σ_j(w_ij × a_j) - a_target_i|
  约束: Σ Xin_i → const (T7 验证: 稳定在 ~87)
  约束: Xin 与 T/O/P/R 的关系:
        ∂Xin/∂τ < 0  (更慢 → 更多预测误差)
        ∂Xin/∂G < 0  (更高增益 → 更快收敛 → 更少 Xin)
        ∂Xin/∂θ > 0  (更高阈值 → 更少通过 → 更多 Xin)
        ∂Xin/∂η < 0  (更快学习 → 更快收敛 → 更少 Xin)
```

---

## 2. T·S·I 约束：同一架构的三个面

### 2.1 T·S·I 不是并行系统，而是同一动力学的三个守恒量

| 约束 | 物理量 | 守恒方程 | Noether 对称性 |
|------|--------|---------|---------------|
| **T** (Time) | 能量 E | dE/dt = E_in - E_dissipated - E_stored | 时间平移不变 |
| **S** (Structure) | 权重 W | dW/dt = STDP - crystallization - prune | 拓扑不变性 |
| **I** (Information) | Xin ξ | dξ/dt = prediction_error - adaptation | 信息处理不变 |

```
T·S·I 耦合方程：

  E_stored = ½ C V² + Σ E_remodel(w_ij)    ... T 包含 S 的重塑代价
  dW/dt = η(E) × STDP(V_pre, V_post)        ... S 的学习速率依赖 T 的能量
  ξ = f(W, V)                                ... I 是 S 和 T 的函数
  
  ∴ T·S·I 不可分离
```

> [!IMPORTANT]  
> **T·S·I 是一个单一约束系统的三个投影，不是三个独立系统。**
> 修改任何一个（如改变时间常数 τ）必然影响另外两个（权重收敛速率、Xin 动态）。
> 这就是为什么"只调一个参数"的方法总是失败。

### 2.2 环流记忆 = T·S·I 的定点

环流（Circulation）是 T·S·I 动力学的**不动点**：

```
环流 = {V*, W*, ξ*} 使得：
  dV*/dt = 0  (热力学平衡)
  dW*/dt = 0  (权重收敛)
  dξ*/dt = 0  (预测误差稳定)

当 input 改变时：
  系统离开 {V*, W*, ξ*}
  T·S·I 驱动系统回到新的不动点 {V**, W**, ξ**}
  回归轨迹 = 环流的"记忆"
```

"环流记忆落地"= 系统能稳定到不动点 + 能从扰动中恢复。
Plan D 的三个改变正是确保不动点存在（有界性）和稳定（VR 适应）。

---

## 3. 生物学对应

### 3.1 Divisive Normalization（除法归一化）

**来源**：Carandini & Heeger (2012), Nature Reviews Neuroscience

V1 视觉皮层的经典发现：每个神经元的响应除以周围神经元池的总活动。

```
R_i = L_i^n / (σ^n + Σ_j L_j^n)
```

在本项目中：
```
xi_normalized = |xi_i| / max_j(|xi_j|)
```

这是 divisive normalization 的最简形式（max 而非 sum）。

**BIO 意义**：感觉系统在所有层级都使用 divisive normalization。
这不是一个"工程技巧"——它是神经系统处理多尺度输入的基本机制。

### 3.2 Spiking as Bounded Representation

**来源**：Dayan & Abbott (2001), Theoretical Neuroscience

脉冲编码天然提供上界：
```
f_max = 1 / (τ_ref + τ_abs) ≈ 500 Hz (理论)
实际: f_max ≈ 100-300 Hz (考虑适应)
```

影子层 col 从 non-spiking 改为 spiking = 从模拟信号改为数字信号。
**BIO**：大脑中没有长距离的模拟（rate-coded）投射。
所有长距离通信都是脉冲编码的。影子 col → DA 是"长距离投射"，
所以 col 应该用脉冲编码。

### 3.3 VTA DA Neurons as Adaptive Homeostats

**来源**：Schultz (1997, 2016), Neuron

VTA DA 神经元的核心特性：
1. **基线发放** ~5 Hz（bc_current = 0.1 → V_ss ≈ 0.1）
2. **相位性爆发** 响应新奇刺激（突触输入增加 → 暂时偏离基线）
3. **适应** 对持续刺激（VR 效应 → 回到基线）
4. **D2 自调节**（VR activity_coeff → 高活动 → 更多抑制）

DA neuron 的 VR 参数直接对应 D2 autoreceptor 动态：
```
VR_rate = base + coeff × activation
      ↔  D2_activation = baseline + gain × [DA]_extracellular
```

### 3.4 Free Energy Principle 与 T·S·I

**来源**：Friston (2010), Nature Reviews Neuroscience

自由能原理统一了感知、行动、学习：
```
F = E_q[ln q(s) - ln p(o,s)]   (变分自由能)
  = complexity - accuracy

最小化 F：
  perception: 更新 q(s)      → 对应 T (能量状态更新)
  learning:   更新 θ (params) → 对应 S (权重更新)
  action:     更新 a          → 对应 I (减少预测误差)
```

T·S·I 约束 = Free Energy 最小化的三个梯度方向。

---

## 4. 方程总结：结构参数约束集

```
输入有界:     ∀i: I_i ∈ [0, G_xin]               ... divisive normalization
输出有界:     ∀n: a_n ≤ 1/τ_ref (spiking)          ... spike upper bound
能量守恒:     E_total(t+1) = E_total(t) + δ ± ε   ... Noether T
权重守恒:     |ΔW_total/Δt| < ε_w                  ... Noether S  
Xin 稳定:     lim(t→∞) Σ|ξ_i(t)| = const           ... empirical (T7)

耦合约束:
  τ × G × a_max ≤ V_peak × (1 + VR_max)           ... 稳态不溢出
  η × f(DA) → 0 as PNN → 1                         ... 结晶化停止学习
  Xin(W, τ, G, θ) = Σ_i |Σ_j w_ij a_j - a_target_i|  ... Xin 依赖全部参数
```

这组方程不是独立的——它们通过 T·S·I 耦合形成一个约束流形。
参数的任何合法组合必须落在这个流形上。

---

## 5. 待 Plan D 测试结果验证的预测

1. 影子 col 激活 ≤ ~3.0（spike-bounded）
2. DA ∈ [0.08, 0.4]（有动态范围）
3. DA 在 CHANGED 相上升（VR lag → novelty detection）
4. Noether ALL PASSED
5. shadow→DA Xin 不再异常（shadow col 有界 → Xin 有界）
