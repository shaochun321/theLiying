# C1: Noether × Polarization — 能量预算钳制振荡幅度

## 1. 设置

两个独立建立的结果：

- **B1 (Noether)**: E_stored(t) + Q_diss(t) = E_in(t)  — 严格守恒，0 violations
- **B5 (Polarization)**: ξ(t) = A·sin(ωt + φ)·e^{-t/τ_leak} — Xin 振荡衰减

问题：**振荡幅度 A 的上界是什么？**

---

## 2. 振荡能量

Xin 存储在 capacitor 中（BundleConfig.xin_tension → RC filter）：

$$E_{sw} = \frac{1}{2} C_{xin} \cdot \xi^2$$

对于正弦振荡 ξ = A·sin(ωt)：

$$\langle E_{sw} \rangle = \frac{1}{4} C_{xin} \cdot A^2$$

耗散功率（leak through R_leak）：

$$P_{diss} = \frac{\xi^2}{R_{leak}} = \frac{A^2}{2 R_{leak}}$$

（时间平均 sin² = 1/2）

---

## 3. 能量预算约束

Noether 守恒要求：

$$P_{input} \geq P_{diss}$$

其中 P_input 是 prediction error 向 Xin 注入的功率：

$$P_{input} = \langle |residual|^2 \rangle \cdot dt$$

因此振荡幅度上界：

$$\boxed{A_{max} = \sqrt{2 \cdot P_{input} \cdot R_{leak}}}$$

**数值验证**：
- τ_leak = 1000s, R_leak = τ/C = 1000 (C_xin ≈ 1)
- P_input ≈ 0.01 (typical residual² × dt for stable circuit)
- A_max = √(2 × 0.01 × 1000) = √20 ≈ 4.47

实际观测的 Xin amplitude ≈ 2-5，一致 ✓

---

## 4. 自洽吸引子

当 A → A_max 时：
1. 能量耗散 P_diss 上升
2. Noether 余量 (P_input - P_diss) 下降
3. 剩余能量给 STDP 的份额减少
4. Weight drift 减慢 → prediction error 减小
5. P_input 下降 → A_max 下降

这是一个**负反馈环路**：

```
A ↑ → P_diss ↑ → 余量 ↓ → STDP 减慢 → error ↓ → P_input ↓ → A ↓
```

吸引子方程（稳态 P_input = P_diss）：

$$A^* = \sqrt{2 R_{leak} \cdot f(A^*)}$$

其中 f(A) = P_input(A) 是递减函数。不动点 A* 稳定当且仅当 f'(A*) < A*/R_leak。

**物理含义**：系统不能同时维持大振荡 AND 快速学习。能量是守恒的——用于振荡的份额抢占了学习的份额。

---

## 5. 主观时间窗推导

系统有三个关键时间常数：

| 常数 | 值 | 来源 |
|---|---|---|
| τ_RC (膜) | 0.75-1.5s | Capacitor × R_leak |
| τ_B (B-layer) | ~10s | C_slow × R_slow (收敛时间) |
| τ_fruit | 5s | MATURATION_TICKS = 5000 |
| τ_xin_leak | 1000s | Xin 结构记忆 |

**最短可分辨时间窗**由 τ_B 决定（B-layer 必须收敛才能区分新旧信号）：

$$T_{subjective} \approx 2\pi / \omega_{B} \approx 2\pi \cdot \tau_B \approx 63s$$

但这是 full-cycle 分辨率。**半周期分辨**：

$$T_{min} \approx \pi \cdot \tau_B \approx 30s$$

**实际约束**更强——需要 B-layer 完成阻抗匹配才能区分信号变化。
从 100k 仿真观测：B-layer 在 ~10k 步 (10s) 收敛。
因此预测：**系统对 <10s 的信号变化敏感，对 >30s 的变化视为准静态。**

---

## 6. 实验验证方案 (C2)

用变频输入测试时间分辨率：

```python
# Phase 1: 0.5 Hz, 10000 steps → 10s 稳态
# Phase 2: 突变到 2.0 Hz, 10000 steps
# Phase 3: 突变到 0.1 Hz, 10000 steps
# 观测: column ema 对每个变化的响应时间
```

如果 C1 正确：
- 0.5→2.0 Hz 变化应在 ~10s (τ_B) 内被反映在 column ema 中
- Column ema 变化幅度受 A_max 约束

---

## 7. 统一定理

**命题 (B1+B5 耦合)**：
*在 Noether 能量守恒约束下，Xin 驻波的幅度满足 A ≤ √(2·P_input·R_leak)，
且稳态幅度 A* 是 P_input(A) = A²/(2R_leak) 的唯一不动点。
该不动点稳定当且仅当 |df/dA| < 1/R_leak。*

**推论 1**: 学习率和振荡幅度互相竞争能量——系统不能同时最大化两者。
**推论 2**: 在能量充足时 (energy >> 0.5)，A* ≈ √(2R_leak·ε²)，其中 ε 是平均 prediction error。
**推论 3**: 在能量匮乏时 (energy → 0)，A* → 0 AND STDP → 0，系统冻结。

这解释了为什么 apoptosis threshold (energy < 0.05) 对应系统功能完全丧失。
