# T·S·I 度量统一 + 分化组件的参数关系方程

> 2026-06-05 — 回答：度量不统一解决了吗？

---

## 1. 度量不统一的问题本质

之前的 T·S·I 方程混合了三个量纲：

```
T: E = ½CV²                   [energy] = C·V² = Q·V
S: W ∈ [0,1]                  [dimensionless]
I: ξ = |predicted - actual|    [voltage difference]
```

三者不能直接相加。但它们共享**同一套硬件原语**：

| 硬件原语 | 物理量 | 量纲 |
|----------|--------|------|
| Capacitor | Q = CV, E = ½CV² | [charge], [energy] |
| MOSFET | I = gm × (V - V_th) | [current] |
| Memristor | R = f(w), I = V/R | [resistance], [current] |
| PowerRail | P = I²R | [power] |

关键洞察：**所有量最终可以归约为两个基本量——电压 [V] 和电荷 [Q]**。

```
能量 E = Q × V = ½CV²        [Q·V]
功率 P = I²R = (Q/t)² × R    [Q²·R/t²]
时间常数 τ = R × C           [t]
```

---

## 2. 统一度量：一切皆能量耗散率

T·S·I 在 ds²/ν 框架下的统一量纲是 **能量耗散率 [power]**：

```
T（时间/能量）:
  dE_T/dt = I²_membrane × R_leak + I²_supply × R_internal + basal_cost
  [power] = [A²·Ω] ✓

S（结构/权重）:
  dE_S/dt = κ × |ΔW/Δt| = remodel_cost_kappa × (STDP_rate)
  [power] = [1/t × energy/change] = [power] ✓
  
  注: κ (remodel_cost_kappa) 的量纲是 [energy/weight_change]
  代码中: κ = 0.001~0.002, |ΔW| ≈ 0.001/step
  E_remodel = κ × |ΔW| = 0.001 × 0.001 = 0.000001 [energy/step]

I（信息/预测误差）:
  dE_I/dt = Σ (ξ_i² × G_i²) / R_membrane
  [power] = [V² × dimensionless² / Ω] = [V²/Ω] = [A·V] ✓
  
  注: Xin tension 的量纲是电压差 [V]
  G = synapse_gain [dimensionless]
  ξ² × G² / R = 预测误差驱动的功耗
```

> [!IMPORTANT]
> **统一度量 = 功率 [W] = dE/dt。**
> T、S、I 都可以表示为系统功率耗散的不同分量。
> ds²/ν 本身的量纲就是 [功率]：
> ```
> ds² = Σ ΔV_i² × C_i    [V² × F = V × Q = J]    → 微分能量
> ν = Σ I_j² × R_j        [A² × Ω = W]            → 耗散功率
> ds²/ν                    [J/W = s]                → 时间！
> ```

---

## 3. Landauer-Noether 桥：耦合常数

三个分量的耦合常数不是自由参数——它们由硬件决定：

### 3.1 T ↔ I 耦合：Landauer 界

```
学习（减少信息熵 ΔH < 0）必须付出能量代价：

  ΔE_T ≥ kT_system × ln2 × |ΔH|

代码中：
  WeightEntropyProbe.measure():
    landauer_bound = math.log(2) * abs(snap.delta_entropy)
    snap.landauer_satisfied = snap.q_dissipated >= landauer_bound * 0.01

耦合常数：
  α_{TI} = kT_system × ln2
  
  其中 kT_system = ECM.temperature × (scale_factor)
  当前 ECM temperature ≈ 0.1~0.5
  → α_{TI} ≈ 0.1 × 0.693 ≈ 0.07
```

### 3.2 T ↔ S 耦合：重塑代价

```
权重变化的能量代价 = remodel_cost_kappa × |ΔW|

代码中：
  bundle.learn(): 
    E_remodel = config.remodel_cost_kappa × sum(|Δw_ij|)
    neuron.energy -= E_remodel

耦合常数：
  α_{TS} = remodel_cost_kappa
  
  当前：κ ∈ {0.001, 0.002}（取决于 bundle 类型）
```

### 3.3 S ↔ I 耦合：Xin 从权重涌现

```
预测误差 = 权重矩阵的预测输出与实际输出之差：

  ξ_i = |Σ_j w_ij × a_j - a_target_i|

这不是耦合常数，而是函数关系：
  I = f(S, input)  →  I 不独立于 S
  
  偏导数：
  ∂ξ/∂w = a_j (pre-synaptic activity)
  → 权重每变化 1 单位，ξ 变化 a_j 单位
```

### 3.4 统一耦合方程

```
dE_total/dt = dE_T/dt + α_{TS} × dE_S/dt + α_{TI} × dE_I/dt

Noether 守恒：
  E_in(vascular) = dE_T/dt + α_{TS} × |ΔW/Δt| + α_{TI} × |ΔH/Δt| + Q_waste

展开到硬件：
  E_vasc = Σ_n I²_n R_n + Σ_b κ_b |ΔW_b| + Σ_b kT·ln2·|ΔH_b| + Q_ecm

每一项都是 [power]。度量统一。✓
```

---

## 4. 分化组件在统一度量下的参数

### 4.1 硬件参数注册表

每个分化组件使用相同的原语，自动继承统一量纲：

| 组件 | 原语 | 参数 | 量纲 | ds²/ν 贡献 |
|------|------|------|------|-----------|
| **CRI** | Capacitor(1.0) | C_cri, R_cri=τ_cri | [F], [Ω] | ds² += ΔV²_cri × C_cri |
| | MOSFET(1.0, 10) | V_th=1.0, gm=10 | [V], [S] | ν += I²_clamp × R_clamp |
| **DN** | Capacitor(5.0) | C_pool, R_pool=5.0 | [F], [Ω] | ds² += ΔV²_pool × C_pool |
| **D2R** | MOSFET(ec50, g_D2) | V_th, gm | [V], [S] | ν += I²_girk × R_membrane |
| | Capacitor(1.0) | C_da, R_da=τ_D2 | [F], [Ω] | ds² += ΔV²_da × C_da |

### 4.2 组件间关系方程

```
── CRI ↔ 主回路 ──
τ_CRI = C_cri × R_cri                              ... 积分时间常数
E_CRI = ½ × C_cri × V²_CRI                         ... 钙池能量
V_CRI_ss = (f_spike × Q_spike × R_cri) / (1 + ε)   ... 稳态钙电压
  where f_spike = 发放率, Q_spike = 每 spike 电荷注入
  约束: V_CRI_ss ≤ V_clamp (MOSFET Zener)
  → f_spike × Q_spike × R_cri ≤ V_clamp (有界条件)

── DN ↔ Xin 输入 ──
τ_DN = C_pool × R_pool                              ... 归一化时间窗口
I_eff = I_raw × σ / (σ + V_pool)                    ... 除法归一化
V_pool_ss = I_total × R_pool                         ... 池活动稳态
  约束: V_pool → I_total_avg × R_pool (跟踪输入均值)
  → I_eff → I_raw × σ / (σ + I_total × R_pool)
  → 当 I_total >> σ/R_pool 时, I_eff → I_raw × σ/(I_total × R_pool)
  → I_eff ∝ I_raw / I_total (相对归一化) ✓

── D2R ↔ DA 浓度 ──
τ_D2 = C_da × R_da                                  ... DA 积分时间窗口
I_girk = -gm_D2 × max(0, V_da_local - ec50)         ... GIRK 抑制电流
V_da_local_ss = [DA] × R_da / (1 + VR_leak)         ... 局部 DA 稳态
  约束: I_girk ∝ [DA] → DA 升高 → 超极化 → DA 降低 (负反馈)
  稳态: [DA]* 使得 I_girk + I_excitatory = I_baseline
  → gm_D2 × ([DA]*×R_da - ec50) = I_exc - I_base
  → [DA]* = (I_exc - I_base)/(gm_D2 × R_da) + ec50/R_da

── 三组件的 T·S·I 映射 ──
T: E_total_new = E_CRI + E_DN + E_D2                ... 新增能量项
S: W_new = {CRI 不含 Memristor; DN, D2R 不含}       ... 无新权重（0 贡献）
I: H_new = CRI 的 V_cri 编码 spike rate → 信息       ... CRI 是 I 的载体
   ξ_CRI = |V_CRI - V_CRI_expected|                 ... CRI 本身可以有 Xin
```

### 4.3 组件间的递归关系

```
影子 enc 输入
  → DN 归一化 → 有界输入
  → 影子 enc 激活
  → enc→col bundle (STDP)
  → 影子 col 激活 (spiking)
  → CRI 积分 spike rate → calcium_rate
  → shadow→DA bundle (reads calcium_rate)
  → DA neuron 激活
  → D2R 负反馈 → DA 稳态
  → dopamine.concentration
  → 调节主层 STDP gain

每一步的 T/O/P/R/Xin：
  DN: T(归一化传输) → O(观测输入范围)
  CRI: O(观测 spike) → P(预测发放率)
  D2R: P(预测 DA) → R(调节自身活动) → Xin(如果偏差持续)
```

---

## 5. 熵账本如何审计新组件

### 5.1 Noether 能量守恒

```python
# 每个新组件的能量已包含在 neuron.heat_output 中：
# CRI: spike 注入和 leak 的能量 → 自动计入 neuron.energy
# DN: pool 充放电的能量 → 自动计入
# D2R: GIRK 电流的功耗 → 自动计入
# → Noether probe 的 get_all_neurons() 自动覆盖 ✓
```

### 5.2 Landauer 信息界

```python
# CRI 的信息内容 = log₂(V_CRI 的可能状态数)
# 学习（改变 CRI 的稳态）需要耗散 kT × ln2 的能量
# → WeightEntropyProbe 不直接测量 CRI，但 CRI 的能量代价
#   已包含在 neuron.heat_output 中 → 间接满足 Landauer ✓
```

### 5.3 TOPRXin 账本

```python
# 新增 bundle (shadow→DA) 已注册在 get_all_bundles() 中
# TOPRXinLedger.measure() 自动覆盖
# 新增 neurons (DA, xin_relay) 已注册在 get_all_neurons() 中
# → TOPR intensity 自动包含新组件的贡献 ✓
```

---

## 6. 总结：度量统一的回答

| 问题 | 回答 |
|------|------|
| T·S·I 度量统一了吗？ | **是的**——统一量纲 = **功率 [dE/dt]** |
| 统一的基础是什么？ | 硬件原语同质性（所有组件用 Capacitor/MOSFET/Memristor） |
| 耦合常数是什么？ | α_{TI} = kT·ln2（Landauer），α_{TS} = κ（remodel cost） |
| 新组件如何融入？ | 使用相同原语 → 自动继承量纲 → ds²/ν 自动包含 |
| ds²/ν 的量纲是什么？ | [J/W] = [s] = **时间**（系统在当前耗散率下消耗当前能量的时间） |

> [!IMPORTANT]
> **ds²/ν 的物理意义 = 系统的"热力学时间"**。
> 它不是钟表时间，而是"以当前耗散速率计，系统储能能维持多久"。
> 这与生物学中的**代谢率**直接对应（metabolic rate = 功率 → 决定生物时间尺度）。
> 小鼠代谢快 → ds²/ν 小 → 生物时间快。
> 大象代谢慢 → ds²/ν 大 → 生物时间慢。
> REF: Kleiber's Law (1932): P ∝ M^{3/4}
