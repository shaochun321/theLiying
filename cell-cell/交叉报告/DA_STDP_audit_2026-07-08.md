# DA-STDP 系统清查报告

**日期**: 2026-07-08
**依据**: 核查.md 四项清查清单
**前置报告**: DA架构报告、STDP冻结根因报告、T-092分析报告

---

## 一、通路清查：谁在驱动DA？谁在学习？

### 1.1 DA输入通路（10条）逐条核查

#### #1 shadow_to_da — ✅ 已控制，不饱和

- **源**: 7个 shadow col 神经元（脉冲+CRI），calcium_rate ∈ [0, 1]
- **束**: frozen, w=0.05, sg=0.1
- **Zener 钳位**: CRI 有 `cri_v_clamp=1.0, gm_clamp=10.0` — 硬钳位，calcium_rate 永不超 1.0
- **最大注入电流**: 7 × 1.0 × 0.05 × 0.1 = **0.035A**/DA神经元
- **历史**: 原始 sg=1.0 时 7×1.0×0.05×1.0=0.35A → DA饱和到1.0。T-084 fix 降到 0.1，现在最大注入只是 bc_current 的 35%
- **判定**: ✅ 已修复，不会导致 DA 饱和

#### #2 xin_to_da — ✅ 量级合理

- **源**: xin_relay 神经元（非脉冲），跟踪 Xin 积分器电压
- **束**: frozen, w=0.1, sg=0.5
- **通路**: Xin 积分器(Capacitor, C=1.0) 累加 |dξ/dt| → _xin_relay.step(V_xin × 0.5) → propagate → DA
- **最大注入**: relay.act≈0.5时: 0.5 × G(0.1) × 0.5 ≈ **0.025A**
- **判定**: ✅ 量级合理，phasic预测误差通路

#### #3 relay_to_da_{pid} (×4) — ⚠️ 唯一可塑DA输入，需关注

- **源**: lamina I proj 神经元（脉冲+CRI, v_peak=0.05, Zener clamp=1.0）
- **束**: **STDP**, use_eligibility_trace=True, w0=0.1, w_max=0.3, sg=0.2
- **两阶段**: relay → [frozen, w=0.3] → proj → [STDP] → DA
- **发放阈值**: relay_act > 0.35 才触发 proj 发放 → 身体离热源 d<12 时活跃
- **eligibility 参数**: τ=300, gain=1.0, ltd_rate=0.01, da_ema_tau=5000
- **风险**: OFF 期（12000步）proj 完全静默 → pre_trace 衰减 → E(t) 衰减殆尽 → LTP=0
- **判定**: ⚠️ 机制正常但"源端静默"导致 OFF 期学习冻结

#### #4 cpg_to_da — 🚫 化石，可安全移除

- **源**: CPGNeuron, 2Hz Van der Pol, 振幅 0.005（Phase-B 10×衰减后）
- **束**: frozen, w=0.1, sg=0.1
- **声称目的**: "保持 DA.post_trace > 0 防止 relay_to_da STDP 冻结"
- **核实结果**: relay_to_da 使用三因子 eligibility trace 路径，**不读 post_trace**
- **移除影响**: 无。DA._activation_ema 由 bc_current 维持 ~0.09，不受 CPG 移除影响
- **判定**: 🚫 **化石** — 两因子时代的残骸，当前架构下无功能

#### #5 thermo_delta_to_da (×12) — ⚠️ sg=1.0 偏高

- **源**: ThermalDeltaNeuron（12个皮肤片），half-wave rectified: max(0, dT × GAIN)
- **束**: frozen, w=0.1, sg=1.0
- **sg=1.0 是全系统最大的 DA 输入增益**
- **典型激活**: dT=0.00025/步时 → activation≈0.05 → I=0.05×G(0.1)×1.0≈**0.0056A**。但在快速趋近热源时 dT 可能更大
- **判定**: ⚠️ sg=1.0 是最大值，需要验证快速趋近热源时是否会导致 DA 短暂饱和

#### #6 shadow_nu_to_da — ⚠️ ν→DA 映射需核实

- **源**: shadow_nu_neuron（自由能偏差检测），非脉冲
- **束**: frozen, w=0.3, sg=1.0
- **ν 来源**: shadow sandbox 的宏观自由能变化率
- **NU_SCALE** = 1/176（ν_90th=176.2, 20k步统计校准 2026-07-04）
- **shadow_nu_neuron**: C=0.1, R=1.0 → τ=100步, v_threshold=0.9 MOSFET → ν>158 才激活
- **判定**: ⚠️ 映射关系复杂（ν→NuThresholdNeuron→bundle→DA），需要端到端验证量级

#### #7 hunger_to_da — ⚠️ 设计问题：驱动还是调制？

- **源**: hypothalamus_hunger（LH 输出），非脉冲
- **束**: frozen, w=0.04, sg=1.0
- **通路**: EnergyStore.fill → 3 ARC传感器 → average → hunger → DA
- **I_hunger**: fill=0 时 hunger≈1.2 → I=1.2×0.04≈**0.048A**
- **问题**: hunger 是 tonic 信号，持续驱动 DA 基线上升。但 hunger 的生物学角色是**调制**（调节 DA 系统的增益），而非直接驱动 DA 发放
- **判定**: ⚠️ 语义错误——hunger 应该调制 DA 系统对其他输入（如 RPE、温觉）的敏感度，而非直接注入电流

#### #8 satiety_to_da — ⚠️ 抑制能力是否足够？

- **源**: satiety_neuron（慢积分器, C=50, R=1, τ=50k步）
- **束**: frozen, w=0.3, sg=**-1.0**（唯一抑制通路）
- **最大抑制**: satiety_act=0.5 → I=-0.15A
- **对抗力量**: 所有其他 7 条兴奋通路的总和。hunger(0.048) + shadow(0.035) + xin(0.025) + relay_to_da(0.114max) + CPG(微小) + thermo_delta(可变) + intake(可变) + RPE(可变)
- **在最坏情况（所有通路同时活跃）**: 兴奋总和可远超 0.15A 的抑制能力
- **判定**: ⚠️ satiety 的单条 -1.0 束可能无法对抗多个兴奋通路同时激活

#### #9 intake_to_da_reward — ⚠️ sg=0.05 可能过弱

- **源**: intake_sensor_neuron（消化界面 deposit rate）
- **束**: frozen, w=1.0, sg=0.05（T-084 fix: 原 1.0, 导致饱和）
- **最大注入**: act=1.0 → I ≈ 1.0 × 10 × 0.05 = **0.5A** → 到 V=0.6 → DA≈0.59
- **但典型值**: deposit_rate≈2e-4 → intake_act≈0.2 → I=0.2×10×0.05=**0.1A**
- **判定**: ⚠️ fix 后最大不饱和（0.5A < 极限），但典型值 0.1A 只是 bc_current 水平。摄食奖励信号可能被淹没在基线中

#### #10 RPE直注 — ⚠️ 只有正相位，缺失负相位

- **源**: DADifferentialGate，eta_da=7.5, clip_max=5.0
- **公式**: `_rpe_da = max(0, 7.5 × Δfill/dt)`, clamp to [0, 5.0]
- **注入**: `_da_drive × DA_INJECT_SCALE(0.1)` → 最大 0.5A/DA神经元
- **经典 RPE 签名的负相位（dip below baseline）被 `max(0, ...)` 截断**
- **判定**: ⚠️ 只能发出"比预期好"的信号，不能发出"比预期差"。缺失了 Schultz 1997 的完整 RPE 曲线

### 1.2 STDP学习通路清查

| 束 | use_eligibility_trace | τ_elig | gain | da_ema_tau | 路径 |
|---|:---:|---|---|---|---|
| relay_to_da (×4) | ✅ True | 300 | 1.0 | 5000 | 三因子 |
| hunger→gain_gate | ✅ True | **500** | **1e-4** | 5000 | 三因子 |
| D1 phasic→spinal (×2) | ✅ True | 300 | 1e-5 | 5000 | 三因子 |
| D1 phasic→spinal_fwd (×2) | ✅ True | 300 | 1e-5 | 5000 | 三因子 |
| therm_z (×8) | ✅ True | 300 | **1e-5** | 5000 | 三因子 |
| relay→enc (×12) | ✅ True | 300 | 1e-5 | 5000 | 三因子 |
| 前庭/编码/柱状束 | ❌ False | — | — | — | 两因子/BCM |

**关键发现**: 所有使用 eligibility trace 的束都有 **da_ema_tau=5000**，无一例外。但 eligibility_gain 跨通路差 **100,000 倍**（1.0 → 1e-5）。

**eligibility_gain 的推导链**:
- 默认 1.0 → "导致 1-step 饱和"（hebbian.py:618）
- 降到 1e-5 → 主传感器通路的标准工作值
- gated_reflex 用 1e-4 → 需要在 100k 步内展示学习效果

**所有 gain 值都是实验调出来的，不是从生物参数推导的。**

### 1.3 CPG通路 — 确认化石

见 #4。可安全移除。所有引用 CPG 的注释均应更新。

---

## 二、数值溯源：每个关键数值的来源

### 2.1 时间常数

| 变量 | 值 | 来源 | 依据类型 | 可信度 |
|------|-----|------|------|:---:|
| `da_ema_tau` | 5000 步 | Seamans & Yang 2004（D1 级联 ~1-5s）, 映射 1ms/步 → 5000步 | **理论推导**但 T-092 证明太长 | ⚠️ |
| `eligibility_tau` | 300-500 步 | CaMKII autophosphorylation ~100ms-1s, 调参分两档（300默认, 500长程） | 生物范围 + **实验调参** | ✅ |
| `trace_tau_pre/post` | 20ms | **无注释，无生物引用，无实验扫描** | ❓不明 | ❌ |
| `_activation_ema` α | 0.01（硬编码）| **无推导，无配置入口** | ❓不明 | ❌ |
| DA 膜 τ | 2s (2000步) | C=2.0, R=1.0, 匹配原 dopamine.tau_decay=2.0 | 设计惯例 | ✅ |
| D2R τ | 1s (1000步) | d2_da_r_leak=1.0 × d2_da_capacitance=1.0 — **核实：配置值生效** | 设计惯例 | ✅ |

**最不可信的两个参数**: `trace_tau_pre/post=20ms` 和 `_activation_ema α=0.01`。两者都没有推导注释、没有实验扫描、没有配置入口。

**trace_tau_pre/post 的后果**:
- 当前 τ=20ms → `decay = exp(-dt/0.02) = 0.9512/步`
- 脉冲神经元 pre_trace 稳态: `spike_rate / (1-0.9512) = spike_rate × 20.5`
- 如果 τ=100ms: `decay = exp(-0.001/0.1) = 0.99`，稳态 `= spike_rate × 100`
- 如果 τ=5ms: `decay = exp(-0.001/0.005) = 0.819`，稳态 `= spike_rate × 5.5`
- **20ms 的选择完全不影响稳态缩放因子（总是缺 `(1-decay)` 归一化），只影响响应速度**

### 2.2 增益/权重值

| 参数 | 值 | 来源 |
|------|-----|------|
| `bc_current` (DA) | 0.1 | V_ss = 0.1 × 1.0 = 0.1V → 激活≈0.09。引用 Grace & Onn 1989（tonic 1-5Hz） |
| `synapse_gain` 各值 | 0.05~1.0 | **全部实验调参**：shadow_to_da 从 1.0→0.1（T-084 fix 防饱和），intake_to_da 从 1.0→0.05（同上），thermo_delta_to_da=1.0 源不明 |
| `initial_weight` 各值 | 0.04~1.0 | 混合：hunger_to_da=0.04（等效原 _hunger_da 贡献），satiety_to_da=0.3（需抑制能力） |
| `eligibility_gain` | 1e-5 ~ 1.0 | **全部实验调参**，从 1.0 "1步饱和" 往下调到合适值 |

**核心发现: synapse_gain 和 eligibility_gain 的所有值都是实验调出来的，无一有生物依据。** 这不是问题（工程上这是正常的），但需要文档化每个值的调参历史。

### 2.3 钳位/阈值

| 参数 | 值 | 来源 |
|------|-----|------|
| DA 浓度钳位 | [0, 1] | `max(0.0, min(1.0, mean_da))` — 1.0 来自 Neuromodulator.max_concentration=1.0 |
| D2R ec50 | 0.3 | 注释: "D2R activates at [DA] > 0.3" — **无生物引用**。典型 VTA DA 神经元 D2R EC50 ≈ 0.1-0.5μM（Ford 2014），0.3 在范围内但不是精确匹配 |
| Proj v_peak | 0.05 | 注释: "fires when relay.act > 0.05/G(0.3)=0.35, i.e., d<12 from heat" — 推导自 relay 激活值和期望发放距离 |

---

## 三、机制核查：代码是否按设计工作？

### 3.1 pre_trace 公式 — 🔴 BUG

**当前**（`neuron.py:589`）:
```python
self.pre_trace = self.pre_trace * decay_pre + abs(self.activation)
```

**问题**: 缺少 `(1-decay)` 归一化因子。这是**标度错误**。

**证据**:
1. 标准 EMA 公式: `new = old × decay + input × (1-decay)`
2. 当前公式稳态: `pre_trace_ss = |act| / (1-decay)` — 放大 20.5 倍（当 decay=0.9512）
3. 脉冲神经元（activation ∈ {0,1}）稳态: `spike_rate × 20.5`
4. 如果 proj 以 0.05 发放率（20步/次）发放，pre_trace≈1.02。如果是 0.1 发放率，pre_trace≈2.05。如果 0.5，直接 clamp 到 10.0

**影响**:
- E(t) 充电速率放大 20.5×
- LTP 放大 20.5×
- 这解释了为什么 `eligibility_gain` 需要被调到 1e-5 —— 它在补偿 pre_trace 的放大！

**判定**: 🔴 **这是 bug，不是设计。** 修正公式为 `pre_trace × decay + abs(activation) × (1-decay)` 后，eligibility_gain 需要重新校准（会上调约 20×）。

### 3.2 DA 浓度赋值 — 🟡 设计取舍

**当前**（`variant_adapter.py:2224-2225`）:
```python
mean_da = sum(n.activation for n in self.da_neurons.values()) / len(...)
self.dopamine._concentration = max(0.0, min(1.0, mean_da))
# dopamine.step() 永不调用
```

**问题**: Neuromodulator 的 ODE（`tau_decay=2.0`, `tau_release=0.2`）形同虚设。

**但这可能不是 bug — 这是架构选择**:
- DA 浓度通过 DA 神经元的膜动力学自然衰减（τ=2s），不需要额外的 `dopamine.step()` ODE
- D2R 自受体提供 DA 特异性的额外衰减
- `dopamine.step()` 是 Neuromodulator 独立使用时的机制，但在 VTA 电路架构下被 DA 神经元替代

**判定**: 🟡 不是 bug，但需要决策：要么删除 `dopamine.step()` 和相关参数，要么让它作为 DA 神经元之外的额外衰减层工作。

### 3.3 D2 自受体参数 — ✅ 配置值生效

**核实**: 在 `neuron.py:368` 中，`D2Autoreceptor` 的实例化使用 `self.config.d2_*` 值：
- `d2_conductance` = 0.5 ✅
- `d2_ec50` = 0.3 ✅
- `d2_da_capacitance` = 1.0 ✅
- `d2_da_r_leak` = **1.0** ✅（不是类默认的 100.0）

τ_D2 = 1.0 × 1.0 = 1.0s。类默认 100.0 从未被使用。

**判定**: ✅ 配置值正确生效，τ_D2=1s 合理。

### 3.4 gain_factor() 双重角色 — 🔴 语义混淆

**同一函数在两个不同地方做两件不同的事**:

| 使用点 | 文件:行 | 做什么 | DA=0.2 时值 | DA=0.5 时值 |
|--------|---------|--------|------------|------------|
| 突触电流调制 | `variant_adapter.py:2483` | 缩放 Enc→Col 等束的 propagate 电流 | 1.15 | 1.60 |
| 学习速率调制 | `variant_adapter.py:2686` | 缩放 plasticity_gate | 1.15 | 1.60 |

**语义混淆**:
- 突触电流调制 = D1 受体效应（cAMP/PKA，快速，在线）
- 学习速率调制 = 三因子学习规则（MAPK/ERK，慢速，离线）

生物上是不同受体、不同信号通路。代码中用了同一个 `gain_factor()`。

**更糟的是**: `gain_factor()` 在 baseline (0.1) 时 = 1.0，但在 DA=0.09 时 = 0.985（略小于 1.0）。这意味着低 DA 会**抑制**突触传导和学习——这可能是期望的行为（DA 低于基线 = 抑制），但从未被明确设计。

**判定**: 🔴 应拆分为两个独立函数: `d1_gain_factor()` (突触调制) 和 `da_lr_gate()` (学习门控)。

---

## 四、汇总：设计 vs Bug vs 化石

### 🔴 Bug（行为与设计意图不符）

| # | 问题 | 严重度 | 位置 |
|---|------|:---:|------|
| B1 | **pre_trace 缺归一化** — 稳态放大 20.5×，连锁影响所有 eligibility gain 校准 | 高 | `neuron.py:589` |
| B2 | **RPE 缺失负相位** — `max(0, ...)` 截断了下调信号 | 中 | `da_differential_gate.py:69` |
| B3 | **gain_factor() 语义混淆** — 同一函数做两件生物上不同的事 | 中 | `variant_adapter.py:2483,2686` |
| B4 | **脉冲神经元 pre_trace = post_trace** — 违反注释声明的"对称性打破"设计意图 | 低 | `neuron.py:589,592` |

### 🟡 设计取舍（可争议但不一定是 bug）

| # | 问题 | 位置 |
|---|------|------|
| D1 | `da_ema_tau=5000` 太长 — T-092 证明导致时间信用分配模糊 | `bundle.py:121` |
| D2 | `dopamine.step()` 死代码 — 架构选择（DA神经元替代ODE），但参数仍在 | `modulator.py:136` |
| D3 | `_activation_ema` α=0.01 硬编码 — 无配置入口 | `neuron.py:603` |
| D4 | `trace_tau_pre/post=20ms` 无来源 — 无生物引用，无实验支撑 | `neuron.py:94-95` |
| D5 | hunger 驱动 DA 而非调制 — 语义问题 | `variant_adapter.py:3418-3430` |
| D6 | DA 永不归零 — bc_current=0.1 贡献基线 0.09 | `variant_adapter.py:631` |

### 🚫 化石（应移除）

| # | 问题 | 位置 |
|---|------|------|
| F1 | **CPG 通路** — 为两因子 STDP 设计，三因子路径不读 post_trace | `cpg_neuron.py`, `variant_adapter.py:3036-3065` |
| F2 | CPG→DA 束 `cpg_to_da` | `variant_adapter.py:3041-3065` |
| F3 | 关于 "保持 DA.post_trace>0" 的过时注释 | `variant_adapter.py:697-699, 2129, 3037-3039` |
| F4 | `Memristor.update(pre_trace, post_trace)` — 旧 STDP 方法，无调用点 | `semiconductor.py:269-271` |

---

## 五、建议修复顺序

### 第一优先：修复 pre_trace 公式（Bug B1）

```python
# neuron.py:589 — 当前:
self.pre_trace = self.pre_trace * decay_pre + abs(self.activation)

# 修正:
self.pre_trace = self.pre_trace * decay_pre + abs(self.activation) * (1.0 - decay_pre)
```

**连锁影响**: 所有 `eligibility_gain` 需要上调约 20× 重新校准。

### 第二优先：移除 CPG 通路（化石 F1-F3）

安全删除，零影响。

### 第三优先：拆分 gain_factor()（Bug B3）

```python
def d1_gain(self) -> float:  # 突触电流调制
    return 1.0 + alpha_d1 * (conc - baseline)

def da_lr_gate(self) -> float:  # 学习门控
    return max(0.0, conc - baseline) / (1.0 - baseline)
```

### 第四优先：缩短 da_ema_tau（设计 D1）

从 5000 → 200-500，匹配 eligibility τ。

### 后续

- 为 `trace_tau_pre/post` 补充生物引用或实验校准
- 为 `_activation_ema` α 添加配置入口
- 考虑 hunger 的调制角色重构
