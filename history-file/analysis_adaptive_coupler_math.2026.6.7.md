# 自适应时间耦合器 — 建模分析

## 1. 问题定义

TemporalCoupler 桥接了不同时间尺度的层（τ_src, τ_tgt, dt）。  
当前使用**固定** τ_couple = 2.0，导致所有 spiking 神经元 100% 饱和。

**目标**：τ_couple 自适应，由前后端环流状态决定，收敛到不饱和的平衡点（吸引子）。

---

## 2. 固定 Coupler 的传递函数

Coupler 本质是离散时间低通滤波器：

```
V(n+1) = [V(n) + I_in × dt] × α      where α = exp(-dt/τ)
```

稳态电压（常数输入 I_in）：

```
V_ss = I_in × dt × α / [(1 - α) × C_couple]
```

截止频率：

```
f_c = 1 / (2π × τ_couple)
```

### 当前参数实测

| τ_couple | 每步保留 α | V_ss (I=0.35) | 结果 |
|---|---|---|---|
| 0.5 | 13.5% | 0.055 | 太小：信号被滤掉 |
| **0.48** | **12.5%** | **0.050** | **平衡点：V_ss × gain ≈ v_peak** |
| 1.0 | 36.8% | 0.204 | 轻微过驱动 |
| **2.0** | **60.7%** | **0.540** | **当前值：严重饱和** |
| 5.0 | 81.9% | 1.581 | 灾难性饱和 |

> [!WARNING]
> 当前 τ=2.0 → V_ss=0.54 → 经过 gain=3.0 → Column 输入 = 1.62 >> v_peak=0.15  
> 这就是 100% 饱和的原因。

---

## 3. 平衡态 τ_eq 的推导

**条件**：coupler 输出的平均电流恰好让下游神经元以 **目标频率 f\*** 发放。

对于 spiking 神经元：
- 每次 spike 需要 Vm 从 v_reset 升到 v_peak
- 所需电压增量：ΔV = v_peak − v_reset
- 所需电荷：ΔQ = ΔV × C_neuron
- 在 ISI = 1/f\* 步内提供这些电荷：I_need = ΔQ / (ISI × dt)

Coupler 必须输出 I_need：

```
V_ss_couple × gain = I_need

V_ss_couple = I_need / gain = (v_peak - v_reset) × C_neuron × f* / gain
```

从 V_ss 方程反解 τ_eq：

```
V_target = I_need / gain
α_eq = V_target / (V_target + I_in × dt)
τ_eq = -dt / ln(α_eq)
```

### Column (Enc→Col coupler) 数值解

```
v_peak = 0.15, v_reset = 0.02, C_n = 0.05, gain = 3.0
目标频率 f* = 0.1 (每 10 步 spike 一次, ~10% duty)

I_need = (0.15 - 0.02) × 0.05 × 0.1 = 6.5e-4
V_target = 6.5e-4 / 3.0 = 2.17e-4
α_eq = 2.17e-4 / (2.17e-4 + 0.35) ≈ 6.2e-4
τ_eq = -1.0 / ln(6.2e-4) ≈ 0.135
```

### Motor (Col→Motor coupler) 数值解

```
v_peak = 0.2, v_reset = 0.0, C_n = 0.01, gain = 5.0
目标频率 f* = 0.05 (每 20 步 spike 一次)

I_need = 0.2 × 0.01 × 0.05 = 1.0e-4
V_target = 1.0e-4 / 5.0 = 2.0e-5
τ_eq ≈ 0.092
```

> [!IMPORTANT]  
> 平衡 τ_eq 远小于当前的 2.0！  
> 固定 τ=2.0 → 输出比需要大 ~1000 倍 → 100% 饱和。

---

## 4. 震荡 → 结构 → 驻波 的数学链

### 4.1 RC 电路 = 振荡器

每个 spiking 神经元是一个 **张弛振荡器** (relaxation oscillator)：

```
充电阶段:  dV/dt = I/C                (线性上升)
放电阶段:  V → v_reset               (瞬间跳变)
周期:      T = C × (v_peak - v_reset) / I
频率:      f = I / [C × (v_peak - v_reset)]
```

调节 C、R（通过 coupler τ）改变的是这个振荡器的**固有频率**。

### 4.2 Coupler = 共鸣腔 / 频率选择器

Coupler 的低通特性意味着：
- f > f_c 的快震荡被平均掉（积分器行为）
- f < f_c 的慢震荡通过（直通行为）
- f ≈ f_c 的震荡被最大传递（共振区）

τ_couple 决定了这个共鸣腔的**共振频率**。

### 4.3 驻波条件

两端振荡器通过 coupler 耦合，形成驻波的条件：

```
前端频率 f₁  ←→  [coupler τ]  ←→  后端频率 f₂

驻波条件: f₁ / f₂ = 整数比 (m/n)
```

当 coupler 的 τ 恰好让两端的功率传输最大化时（阻抗匹配），驻波最稳定。

已有结构对应：[bundle.py C4 ZCR](file:///d:/cell-cc/nexus_v1/circuit/bundle.py#L63-L71)

---

## 5. 自适应机制候选方案

### 方案 A：误差积分器 (Error Integrator)

```
                    ┌─────────────────────┐
f_downstream ──→ [MOSFET: 阈值=f*] ──→ 误差电流 ──→ [C_adapt] ──→ V_adapt
                    └─────────────────────┘               ↓
                                              τ_eff = τ_base + k × V_adapt
```

- 下游频率 > f\*：MOSFET 导通 → 正电流 → V_adapt 上升 → τ 减小 → 传递更少
- 下游频率 < f\*：MOSFET 截止 → V_adapt 通过 leak 下降 → τ 增大 → 传递更多

**问题**：f\* 是什么？如果是固定值 → 软件常数，违反 S0。

### 方案 B：环流比例反馈 (Circulation Feedback)

```
ρ_upstream ──→ [差分: ρ_up - ρ_down] ──→ [C_adapt] ──→ τ_eff
ρ_downstream ──→ ──────────┘
```

- 当 ρ_up > ρ_down（上游更活跃）→ 正误差 → τ 增大 → 传更多
- 当 ρ_up < ρ_down（下游更活跃）→ 负误差 → τ 减小 → 传更少
- **吸引子：ρ_up ≈ ρ_down**（阻抗匹配）

**优势**：无固定目标值，平衡点由系统自洽决定。  
**问题**：ρ 的结构载体 (CirculationProportionCircuit) 已存在，但 rho 值如何映射到 coupler？

### 方案 C：直接膜电压反馈 (Vm Feedback)

```
V_downstream_ema ──→ [MOSFET: 阈值 = v_peak/2] ──→ [C_adapt]
                         ↓
              导通时: 增加 coupler leak → τ 减小 → 输出降低
              截止时: coupler leak 自然恢复 → τ 增大
```

- 当下游 Vm 持续高（接近饱和）→ MOSFET 导通 → coupler 加速泄漏 → 输出降低
- 当下游 Vm 低 → MOSFET 截止 → coupler 正常积分

**优势**：完全结构化（Capacitor + MOSFET），无软件数学。  
**优势**：直接在 coupler 内部实现，不依赖外部环流测量。  
**生物对应**：突触后电位反馈到突触前 → 逆行信使 (retrograde messenger, 如 NO, endocannabinoids)。

---

## 6. 方案评估

| 维度 | A (误差积分) | B (环流反馈) | C (Vm反馈) |
|---|---|---|---|
| S0 合规 | ⚠️ f\* 是常数 | ✅ 全结构化 | ✅ 全结构化 |
| 生物对应 | 突触缩放 | 血管-神经耦合 | **逆行信使** |
| 闭环 | ✅ | ✅ | ✅ |
| 自洽吸引子 | ✅ (f→f\*) | ✅ (ρ_up→ρ_down) | ✅ (Vm→v_peak/2) |
| 实现复杂度 | 中 | 高（需跨层引用） | **低** |
| 与驻波关系 | 间接 | 间接 | **直接**（Vm 是振荡的瞬时状态） |

> [!TIP]
> **推荐方案 C**：最简单、最结构化、最直接。  
> Coupler 内部增加一个 MOSFET 读取下游 Vm，自动调节 leak。  
> 可以后续叠加方案 B（环流反馈）作为慢时间尺度的第二层调节。

---

## 7. 方案 C 详细设计

### 结构

```
                  TemporalCoupler (adaptive)
  ┌─────────────────────────────────────────────┐
  │                                             │
  │  [C_couple: 积分电容]                       │
  │       ↑ inject(I_upstream)                  │
  │       ↓ leak(R_base)          ← 基础 leak   │
  │       ↓ leak(R_adapt)         ← 自适应 leak  │
  │                                             │
  │  [MOSFET_adapt]                             │
  │    gate = V_downstream (下游膜电压)          │
  │    V_th = v_peak / 2                        │
  │    gm = k_adapt                             │
  │       ↓                                     │
  │  R_adapt = R_base / (1 + gm × (Vm - Vth))  │
  │                                             │
  │  output = C_couple.voltage                  │
  └─────────────────────────────────────────────┘
```

### 动力学

```
dV_couple/dt = I_upstream/C - V_couple × [1/τ_base + g_adapt(Vm_down)]

其中 g_adapt(Vm) = gm × max(0, Vm - V_th)

平衡点: V_couple_ss = I_upstream / [1/τ_base + g_adapt(Vm_down)]
```

当 Vm_down 高（饱和）→ g_adapt 大 → V_couple 低 → 输出少 → Vm_down 降  
当 Vm_down 低（欠驱动）→ g_adapt ≈ 0 → V_couple 正常 → 输出多 → Vm_down 升

**吸引子**：Vm_down ≈ V_th = v_peak/2（半饱和状态）

### 与驻波的关系

当两端都在吸引子附近时：
- 前端以某频率 f₁ 提供脉冲
- Coupler 以 τ_eff 积分
- 后端以 f₂ 读取
- f₁、f₂、τ_eff 三者形成**共振三角**
- 如果 f₁/f₂ 趋近有理比值 → 驻波形成
