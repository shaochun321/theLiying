# 全局数学公式 — G-001

> 日期: 2026-05-24
> 版本: v1.0 (初版)
> 关联: concept_C001~C003, layer_contracts, modeling_016~017

---

## §1 神经元膜方程 (RC-MOSFET)

> 代码: [neuron.py](file:///d:/cell-cc/nexus_v1/components/neuron.py)

### §1.1 膜电位

$$
C \frac{dV}{dt} = -\frac{V - V_{\text{rest}}}{R} + I_{\text{ext}} - w
$$

| 参数 | 符号 | 默认值 | 说明 |
|------|------|--------|------|
| 电容 | C | 1.0 (主), 3.0 (影子) | RC 时间常数 τ = RC |
| 泄漏电阻 | R | 5.0 | 决定稳态 V_ss = I × R |
| 静息电位 | V_rest | 0.0 | |
| 适应电流 | w | 自适应 | 负反馈 |

### §1.2 MOSFET 激活函数

$$
a = \max(0, V - V_{\text{th}})
$$

- V_th = 0.3（固定阈值）
- 等效半导体 FET 门控，不是生物意义的"阈值"

### §1.3 适应电流 (w_adapt)

$$
\frac{dw}{dt} = \frac{a_w(V - V_{\text{rest}}) - w}{\tau_w}
$$

- a_w = 0.01 (编码), 0.005 (运动)
- τ_w = 100

### §1.4 脉冲检测 (仅脉冲神经元)

$$
V > V_{\text{th}} \implies \text{spike}, \quad V \leftarrow V_{\text{rest}}, \quad w \leftarrow w + b
$$

- b = 0.05 (脉冲后适应增量)

### §1.5 能量与热

$$
E_{\text{heat}} = \frac{I^2}{R} \cdot dt \qquad (\text{I²R 焦耳热})
$$

$$
E_{\text{new}} = \max(0, E - E_{\text{heat}})
$$

---

## §2 突触束 (SynapticBundle + Memristor)

> 代码: [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py)

### §2.1 传播

$$
I_j = \text{gain} \times \sum_i a_i \times w_{ij}
$$

| 参数 | 默认值 |
|------|--------|
| gain (synapse_gain) | 10.0 |
| w_{ij} 初始值 | 0.1~0.5 (层依赖) |

### §2.2 STDP 学习 (M=0, Spine 阶段)

$$
\Delta w_{ij}^{\text{raw}} = \eta \cdot dt \cdot (\underbrace{x_i^{\text{pre}} \cdot x_j^{\text{post}}}_{\text{LTP}} - \underbrace{\lambda \cdot w_{ij}}_{\text{衰减}})
$$

乘性软边界：
$$
\Delta w = \begin{cases}
\Delta w^{\text{raw}} \cdot (w_{\max} - w) & \text{if } \Delta w^{\text{raw}} > 0 \\
\Delta w^{\text{raw}} \cdot (w - w_{\min}) & \text{if } \Delta w^{\text{raw}} < 0
\end{cases}
$$

最终：
$$
w \leftarrow \text{clip}(w + \Delta w \cdot g_{\ell} \cdot p_s, \; w_{\min}, \; w_{\max})
$$

| 参数 | 符号 | 默认值 |
|------|------|--------|
| 学习率 | η (stdp_lr) | 0.01 |
| 衰减 | λ | 0.001 |
| PNN 门控 | g_ℓ | [0,1] |
| 成熟率 | p_s | [0.18, 0.01, 0.001] |

### §2.3 BCM 学习 (M=1, Column 阶段 / 影子层)

$$
\Delta w_{ij} = \eta \cdot dt \cdot |a_i| \cdot |a_j| \cdot (|a_j| - \theta_j) \cdot g_{\ell} \cdot p_s
$$

滑动阈值更新：
$$
\frac{d\theta_j}{dt} = \frac{a_j^2 - \theta_j}{\tau_\theta}
$$

- τ_θ = 100
- 影子层非脉冲神经元使用 BCM（STDP trace 对非脉冲无效）

### §2.4 E_remodel 能量消耗

$$
E_{\text{remodel}} = \kappa \cdot |\Delta w|
$$

- κ = 0.1 (默认)

### §2.5 Xin 张力

$$
X_{\text{in}} = \frac{\text{predicted} - \text{actual}}{\tau_{\text{xin}}}
$$

- predicted = 上一步权重加权和
- actual = 当前突触后激活

---

## §3 环流测量

> 代码: [circulation.py](file:///d:/cell-cc/nexus_v1/circuit/circulation.py)

### §3.1 路径流量

$$
\mu_p = a_{\text{col}} \times a_{\text{bind}} \times w_{\text{bind→mot}} \times f_{\text{feedback}}
$$

- MIN_FLOW = 1e-5（低于此值忽略）

### §3.2 总流量

$$
\mu_{\text{total}} = \sum_p \mu_p
$$

### §3.3 运动势 (ν)

$$
\nu_p = \frac{d\rho_p}{dt} = \frac{\rho_p(t) - \rho_p(t-1)}{dt}
$$

$$
\rho_p = \frac{\mu_p}{\mu_{\text{total}}}
$$

### §3.4 Noether 异常

$$
A = \frac{|d\mu/dt|}{J}
$$

- A 递减 → 系统在收敛
- A 趋零 → 动态对称性恢复

---

## §4 影子层

> 代码: [shadow_sandbox.py](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py)

### §4.1 影子层输入

$$
I_{\text{shadow}} = |X_{\text{in}}| \times K_{\text{xin}}
$$

- K_xin = XIN_GAIN（abs 是因为影子层只关心误差大小）

### §4.2 收缩度

$$
\kappa(t) = \frac{\sum_i \sum_j w_{ij}^{\text{cross}} \cdot |a_i| \cdot |a_j|}{\sum_i |a_i| \cdot \sum_j |a_j|}
$$

### §4.3 施工供电（临时）

$$
E_n \leftarrow \max(E_n, 5.0) \quad \forall n \in \text{shadow neurons}
$$

- `_construction_power = True` 时生效
- 验证完成后关闭

---

## §5 热力学

> 代码: [ecm.py](file:///d:/cell-cc/nexus_v1/components/ecm.py), [vascular.py](file:///d:/cell-cc/nexus_v1/components/vascular.py)

### §5.1 ECM 温度场

$$
\frac{dT}{dt} = \frac{Q_{\text{neural}} - Q_{\text{dissipated}}}{C_{\text{thermal}}}
$$

### §5.2 PNN 成熟

$$
\frac{d\text{PNN}}{dt} = \frac{\text{target} - \text{PNN}}{\tau_{\text{pnn}}}
$$

$$
g_{\ell} = 1 - \text{PNN} \quad (\text{可塑性门控})
$$

### §5.3 血管冷却 (NVC)

$$
Q_{\text{removed}} = \text{flow} \times (T - T_{\text{blood}}) \times c_p
$$

### §5.4 能量输入 (VR)

$$
\frac{dE}{dt} = r_{\text{base}} + r_{\text{act}} \times |a| \quad (\text{活动依赖恢复})
$$

---

## §6 参数速查表

| 层 | w_init | gain | C | R | τ=RC | spiking | 学习规则 |
|----|--------|------|---|---|------|---------|---------|
| vest→enc (aff→enc) | 0.2 | 10 | 1.0 | 5.0 | 5 | ✓ | STDP |
| enc→col | 0.15 | 10 | 1.0 | 5.0 | 5 | ✗ | STDP |
| col→mot | 0.1 | 10 | 1.0 | 5.0 | 5 | ✓ | STDP |
| s_enc→col | 0.1 | 10 | 3.0 | 5.0 | 15 | ✗ | BCM |
| s_col→mot | 0.05 | 10 | 3.0 | 5.0 | 15 | ✗ | BCM |
| s_cross | 0.001 | 10 | 3.0 | 5.0 | 15 | ✗ | BCM |
| HC→Aff | 0.8 | — | — | — | — | — | — |
| MET→HC | 0.5 | — | — | — | — | — | — |
