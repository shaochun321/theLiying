# 感觉运动闭环：逐步详解

## 总览

每个 `step(dt=0.001)` 中，系统执行一个完整的闭环：

```
               ┌──────────────────────────────────────────────┐
               │                                              │
  Motor Spike  │  ① EMA  →  ② Muscle  →  ③ Body  →  ④ Oto   │
       ↑       │                           │  │               │
       │       │                           │  └──→ ⑤ Therm   │
       │       │                           │                  │
  Col←Enc←Aff  │  ⑧ Xin ← ⑦ STDP ← ⑥ Osc×Signal           │
               │                                              │
               └──────────────────────────────────────────────┘
```

---

## ① Motor Spike → EMA（放电率估计）

Motor 是脉冲神经元。当膜电压 $V_m > V_{peak}$ 时放电。但肌肉不能用离散脉冲驱动——需要**平滑的力**。

**EMA（指数移动平均）** 将离散脉冲转换为连续激活率：

$$\text{ema}(t) = \text{ema}(t-1) \times (1 - \alpha) + \text{fired}(t) \times \alpha$$

其中 $\alpha = dt / \tau_{ema}$，$\tau_{ema} = 0.02$s（20ms），$\text{fired}(t) \in \{0, 1\}$。

**物理含义**：这是一个 RC 低通滤波器，将高频脉冲序列转换为缓慢变化的"放电率"。放电越频繁，ema 越高。

**Mitosis（有丝分裂）后**：一个轴上可能有多个 motor（500k 后 move_y 有 ~25 个后代），它们的 ema 被**求和**：

```python
axis_acts = [0.0, 0.0, 0.0]
for key, mot in self.motor_neurons.items():
    if 'move_y' in key:
        axis_acts[1] += mot._activation_ema  # 所有 y 轴 motor 的贡献叠加
```

---

## ② Muscle：EMA → 力

肌肉系统将 ema 转换为力，有两个关键操作：

### A. 运动阻尼（Golgi 腱器官反馈）

$$k_{damp} = \frac{1}{1 + |\mathbf{v}| / v_{ref}}, \quad v_{ref} = 0.5$$

速度越快 → 阻尼越大 → 力越小。这防止了失控加速。

### B. 肌肉收缩（带延迟）

$$F_i = \text{ema}_i \times g_{muscle} \times k_{damp}$$

其中 $g_{muscle} = 0.1$，且有 2 步的传导延迟（FIFO 缓冲）。

**数值例子**：
- ema_y = 0.05（move_y 的放电率）
- v = 0（静止）→ k_damp = 1.0
- F_y = 0.05 × 0.1 × 1.0 = 0.005 N

---

## ③ Body：力 → 加速度 → 位移

牛顿第二定律 + 粘性阻力：

$$a_i = \frac{F_i - \mu \cdot v_i}{m}, \quad \mu = 0.5, \quad m = 1.0$$

$$v_i(t+dt) = v_i(t) + a_i \cdot dt$$

$$x_i(t+dt) = x_i(t) + v_i \cdot dt$$

**数值例子**（续上）：
- F_y = 0.005, v_y = 0, μ = 0.5, m = 1.0
- a_y = (0.005 - 0.5×0) / 1.0 = 0.005 m/s²
- v_y(next) = 0 + 0.005 × 0.001 = 0.000005 m/s
- x_y(next) = 50.0 + 0.000005 = 50.000005

**关键**：body 在 [0, 100]³ 空间中运动，碰到边界**弹回**（速度反向 ×0.5）。

---

## ④ Otolith：加速度 → 前庭输入

加速度被放大并注入前庭通路：

$$\text{oto}_i = a_i \times 500$$

**数值例子**：
- a_y = 0.005 → oto_y = 0.005 × 500 = 2.5

这个值作为 `mechanical_inputs['oto_y']` 注入，经过阻抗匹配后进入增益链：

$$\text{oto}_{matched} = \text{oto} \times T_{impedance}$$

$$T_{impedance} = \min\left(1.0, \frac{2 Z_{body}}{Z_{body} + Z_{medium}}\right) = \min(1.0, \frac{2 \times 1.0}{1.0 + 1.0}) = 1.0$$

### Otolith 的因果闭环

```
Motor spike → 力 → 加速度 a_y = 0.005
                          ↓
           oto_y = a_y × 500 = 2.5
                          ↓
       Met→HC→Aff→Enc→Col → Motor spike（下一个周期）
```

**这就是为什么 otolith 的 Xin 永远不为零**：
- Motor 放一个 spike → 加速度脉冲 → oto 得到一个巨大的瞬态信号
- 预测器试图用上一步的信号预测这一步的 oto → 但 oto 是**自己引起的脉冲**
- 预测误差 = 脉冲的不可预测部分 → Xin 持续累积

---

## ⑤ Therm：体位 → 温度 → 热信号

Body 移动到新位置后，热感膜测量新的温度：

$$T_{raw} = T_{ambient} + \sum_{src} T_{src} \times \max\left(0, 1 - \frac{d(body, src)}{r_{src}}\right)$$

其中 $T_{ambient} = 0.1$，热源在 [70, 50, 50]，$r = 20$。

Body 在 [50, 50, 50] → $d = 20.0$ → 刚好在热源边缘。

### 甲基化适应（时间微分）

$$M(t+dt) = M(t) + \frac{T_{raw} - M(t)}{\tau_M} \cdot dt, \quad \tau_M = 200$$

$$\text{therm} = T_{raw} - M \quad \text{（偏离基线的量）}$$

$$\text{dtherm} = \frac{T_{raw}(t) - T_{raw}(t-1)}{dt} \quad \text{（变化率）}$$

**关键因果**：
- Motor 让 body 往 [70,50,50]（热源）移动 → T_raw 升高 → therm > 0 → "变暖了"
- Motor 让 body 往 [30,50,50]（远离热源）移动 → T_raw 降低 → therm < 0 → "变冷了"
- 如果 body 静止 → M 慢慢适应 → therm → 0 → 静默

**这是空间信号**：热感不知道方向（只有一个标量传感器），但通过与 vestibular 的跨模态 Hebbian 学习，系统可以学到"往 +x 走就变暖"。

---

## ⑥ Oscillator × Signal：时间调制

每个前庭轴有一个振荡器，产生调制信号：

$$\text{osc}(t) = A \sin(2\pi f \cdot t + \phi)$$

默认 $A = 0.01$（很小），$f$ 随轴不同。

调制施加在 Afferent 膜电压上：

$$V_{aff}' = V_{rest} + (V_{aff} - V_{rest}) \times \max(0, 1 + \text{osc}(t))$$

**数值例子**：
- V_aff = 0.15（正在充电）, V_rest = 0
- osc = 0.01 × sin(ωt) ≈ 0.005
- V_aff' = 0.15 × 1.005 = 0.15075（微小调制）

### 拍频效应

如果输入是 $f_{in} = 1.0$ Hz 的正弦波，振荡器是 $f_{osc} = 1.03$ Hz：

$$V_{aff}(t) \propto \sin(2\pi \times 1.0 \times t) \times [1 + 0.01 \sin(2\pi \times 1.03 \times t)]$$

展开包含 $\sin(2\pi \times 0.03 \times t)$（拍频 0.03 Hz，周期 ~33 秒）。

**这个超低频调制对 bundle 的预测器来说是"不可预测的"**——因为预测器只看到前一步的信号，无法捕捉到这个 33 秒周期的包络。

但目前 $A = 0.01$，效果微弱。

---

## ⑦ STDP：信号 → 权重变化

所有信号（oto + therm + yaw/pitch/roll）经过 Met→HC→Aff→Enc→Col 的增益链后，STDP 调整权重：

$$\Delta w = \eta \times [\text{pre}(t-1) \times \text{post}(t) - \text{pre}(t) \times \text{post}(t-1)]$$

**前后因果**：如果源在靶之前活跃（因果方向），权重增加；反之减少。

DA 调制学习率（三因子学习规则）：

$$\eta_{eff} = \eta_{base} \times (1 + \alpha_{lr} \times (DA - DA_{baseline}))$$

现在 DA = 0.1 = baseline → $\eta_{eff} = \eta_{base}$（没有调制）。

---

## ⑧ Xin：预测 vs 实际

每个 bundle 在每步计算预测残差：

$$\hat{a}_j = \sum_i W_{ij} \cdot a_i^{prev}$$

$$\xi += \sum_j (\hat{a}_j - a_j^{actual}) \cdot dt$$

**三个闭环各自产生 Xin**：

| 闭环 | 信号路径 | 不可预测性来源 | Xin 量级 |
|------|---------|---------------|---------|
| Otolith | Motor→Body→acc→oto | 自身运动引起的加速度脉冲 | **大** (xi≈10-25) |
| Thermal | Motor→Body→position→T→therm | 位移导致的温度变化 | **中** (xi≈0.2) |
| Oscillator | 内在振荡 × 外部信号 | 拍频（两个频率不匹配） | **小** (xi≈0.01) |

---

## 三个闭环如何纠缠

它们不是独立的——**共享 body 状态**：

```
Motor spike (t)
    ↓
  body.step(forces)  ← 改变了 body 的 position + velocity + acceleration
    ↓                    ↓                          ↓
  Thermal:             Otolith:                   Kinetic damping:
  T(pos_new)           acc × 500                  1/(1+v/0.5)
  不同于 T(pos_old)    不同于 acc_old              下一步的 Force 更小
    ↓                    ↓                          ↓
  therm 信号变化        oto 信号变化               motor 的 EMA→Force 被压制
    ↓                    ↓                          ↓
  enc_therm 放电变化    enc_oto 放电变化           motor 放电变化
    ↓                    ↓                          ↓
  col→motor 权重变化    col→motor 权重变化         下一步的加速度变化
         ↘                  ↓                    ↙
           ────→ Motor spike (t+1) ←────
```

**一个 motor spike 同时改变了三个感觉通道的输入**，这三个通道又通过不同的时间常数回馈到同一组 motor。

因此：
- 单看每个通道是简单的（正弦波、脉冲、渐变）
- 但三个通道的**联合轨迹**在时间上不可预测
- 这就是复杂输入的来源——不是外部注入的，而是**闭环自己制造的**
