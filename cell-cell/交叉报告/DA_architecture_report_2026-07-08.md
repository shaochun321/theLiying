# DA 架构分析报告：DA 是什么、DA 如何实现

**日期**: 2026-07-08
**目的**: 为 DA 重构提供完整的架构理解

---

## 1. DA 不是单一元件，是三层系统

```
┌─────────────────────────────────────────────────────────┐
│ 第 3 层：10 条输入通路（谁在驱动 DA？）                    │
│   shadow col → DA    │  Xin relay → DA                   │
│   relay → proj → DA  │  CPG → DA    │  ThermoDelta → DA │
│   shadow ν → DA      │  hunger → DA │  satiety → DA     │
│   intake → DA        │  RPE 直注                         │
├─────────────────────────────────────────────────────────┤
│ 第 2 层：DA 神经元池（VTA 电路，激活 → 浓度）              │
│   3 个非脉冲神经元 (da_vta_0/1/2)                        │
│   D2 自受体负反馈  │  VoltageRegulator  │  bc_current    │
├─────────────────────────────────────────────────────────┤
│ 第 1 层：Neuromodulator 容器（只存浓度值）                 │
│   _concentration: float                                  │
│   concentration: @property (只读)                        │
│   dopamine.step() 从未被调用                              │
└─────────────────────────────────────────────────────────┘
```

**结论**: DA 是一个**完整的神经调制子系统**，包含容器层、神经计算层、输入通路层。不是 "一个参数" 或 "一个元件"。

---

## 2. 第 1 层：Neuromodulator 容器

**文件**: `components/modulator.py:74-210`

`Neuromodulator` 是一个 `@dataclass`。它的职责极其简单：**存储并暴露浓度值**。

```python
@dataclass
class Neuromodulator:
    name: str = "modulator"
    tau_decay: float = 2.0        # 浓度衰减 τ（未使用）
    tau_release: float = 0.5      # 释放平滑 τ（未使用）
    baseline: float = 0.1         # 基线浓度
    max_concentration: float = 1.0

    alpha_gain: float = 0.5       # 增益调制系数
    alpha_lr: float = 1.0         # 学习率调制系数

    _concentration: float = 0.1   # ← 唯一重要的内部状态

    @property
    def concentration(self) -> float:   # 只读属性
        return self._concentration
```

**关键事实**:
- `dopamine.step()` 从未被调用（`variant_adapter.py:2226` 明确注释）
- 浓度不是通过 ODE 计算出来的，而是**直接从 DA 神经元的平均激活值赋值**
- `tau_decay`、`tau_release` 参数**形同虚设**
- `gain_factor()`、`lr_factor()` 等 effect 方法**在其他地方**被使用（propagate_bundles 中的突触增益调制），但与"DA 浓度怎么来的"无关

**`create_dopamine()` 预设** (`modulator.py:215-230`):
```python
Neuromodulator(
    name="dopamine", baseline=0.1, max_concentration=1.0,
    alpha_gain=1.5, alpha_lr=2.0,
    tau_decay=2.0, tau_release=0.2,
)
```

### 浓度读出的所有位置

| 文件 | 行号 | 用途 |
|------|------|------|
| `variant_adapter.py` | 1336 | 传入 `motor_decision.process()` |
| `variant_adapter.py` | 2216 | 传入 D2 自受体 (`da_concentration_input`) |
| `variant_adapter.py` | 2231 | 传入 `bundle.learn()` (relay_to_da 等 3 组束) |
| `variant_adapter.py` | 2247 | 传入 `bundle.learn()` (relay_to_enc) |
| `variant_adapter.py` | 2308 | 传入 `update_fruit()` (maturation 门控) |
| `variant_adapter.py` | 2428 | 传入 `ecm.degrade_pnn()` |
| `variant_adapter.py` | 2483 | `gain_factor()` 调制 Enc→Col 突触电流 |
| `variant_adapter.py` | 2686 | `gain_factor()` 调制 plasticity_gate |
| `gain_mod_adapter.py` | 46 | 传入 `gated_arc.step()` → `bundle.learn()` |
| `decision_adapter.py` | 326-329 | `gain_factor()` + `bundle.learn()` |
| `ledger/toprxin.py` | 100 | `gain_factor()` 记入 ledger snapshot |

**注意**: `gain_factor()` 被用于两个完全不同的目的：
1. 调制突触电流（propagate 阶段）
2. 调制学习速率（learn 阶段）

这两个用途的语义完全不同，但用的是同一个系数。

---

## 3. 第 2 层：DA 神经元池（VTA 电路）

**文件**: `variant_adapter.py:614-661`（创建）, `2198-2225`（步进）

### 3.1 神经元配置

3 个相同的非脉冲神经元：

```python
NeuronConfig(
    neuron_id="da_vta_0",   # (同样配置 ×3: _0, _1, _2)
    capacitance=2.0,        # τ_membrane = C×R = 2.0×1.0 = 2.0s
    r_leak=1.0,
    v_rest=0.0,
    channels=[ChannelConfig(v_threshold=0.01, gm=1.0)],  # 单通道，近线性
    spiking=False,           # 连续模式 (Grace & Onn 1989)
    use_bias_current=True,   # bc_current=0.1 → V_ss=0.1V → 基线激活≈0.09
    bc_current=0.1,
    maturation_stage=0,      # spine — 允许输入束做 STDP
    trace_tau_pre=20.0,
    trace_tau_post=20.0,
    # 代谢
    use_voltage_regulator=True,
    vr_base_rate=0.5, vr_activity_coeff=1.0, vr_max_rate=5.0,
    # D2 自受体（DA 特异性）
    use_d2_autoreceptor=True,
    d2_conductance=0.5,      # GIRK 最大电导
    d2_ec50=0.3,             # D2R 激活阈值
    d2_da_capacitance=1.0,   # 局部 [DA] 积分器 C
    d2_da_r_leak=1.0,        # 局部 [DA] 积分器 R → τ_D2=1s
)
```

### 3.2 激活计算流程（每步）

```
输入准备:
  10 条通路逐个 propagate() → 累加到 da_input_currents[nid]

DA 神经元 step (每个 da_vta_N):
  1. refill 能量: 从 EnergyStore 提取最多 0.001
  2. 读 dopamine.concentration → da_concentration_input (D2R 用)
  3. neuron.step(total_current, dt):
     a. total_input = bundle电流 + bc_current(0.1)
     b. D2R: i_girk = compute_girk(da_concentration_input) → 加入 total_input
     c. AGC/V_regulator/DecouplingCapacitor（本系统中基本旁路）
     d. 膜注: membrane.inject(total_input × ..., dt)
     e. 激活: gate.gated_conduct(Vm) → activation ∈ [-10, 10]
     f. 更新 pre_trace = |activation|, post_trace = |d(activation)/dt|
  4. 浓度: mean_da = mean(3个activation), clamp(0, 1) → dopamine._concentration
```

### 3.3 D2 自受体机制

**文件**: `components/compensation.py:368-454`, class `D2Autoreceptor`

```
_da_local 积分器:
  _da_local += da_concentration × dt / C_da
  _da_local *= exp(-dt / τ_D2)    // τ_D2 = C_da × R_da = 1.0 × 1.0 = 1.0s

GIRK 输出:
  if _da_local ≥ ec50(0.3):
    i_girk = -conductance × (_da_local - 0.3)        // 超阈值线性
  else:
    i_girk = -conductance × nVT × (exp(ΔV/nVT) - 1)  // 亚阈值指数
    （负值 → 超极化 → 降低 activation）
```

**BUG 风险**: D2Autoreceptor 类的 `da_r_leak` 默认值是 `100.0`，但 DA 神经元配置中 `d2_da_r_leak=1.0`。需要确认 `neuron.py` 中 D2Autoreceptor 实例化时是否正确读取了配置值。如果读的是类默认值 100.0，τ_D2 = 100s，D2R 几乎不工作。

---

## 4. 第 3 层：10 条输入通路

**初始化**: `_init_da_circuit()` (`variant_adapter.py:2861-3192`)，lazy 调用（第一步触发）

### 完整通路表

| # | bundle_id | 源神经元 | 学习规则 | w | sg | 生物学依据 |
|---|-----------|----------|----------|-----|-----|-----------|
| 1 | `shadow_to_da` | shadow col (7个) | frozen | 0.05 | 0.1 | 预测误差 tonic |
| 2 | `xin_to_da` | xin_relay (1个) | frozen | 0.1 | 0.5 | 预测误差 phasic |
| 3 | `relay_to_da_{pid}` (×4) | lamina I proj (4个) | **STDP** | 0.1 | 0.2 | 方向性热觉学习 |
| 4 | `cpg_to_da` | CPG 振荡器 (1个) | frozen | 0.1 | 0.1 | 2Hz 起搏器 |
| 5 | `thermo_delta_to_da_{pid}` (×12) | ThermalDelta (12个) | frozen | 0.1 | 1.0 | 温觉起始 (LPB→VTA) |
| 6 | `shadow_nu_to_da` | shadow_nu (1个) | frozen | 0.3 | 1.0 | 自由能门控 |
| 7 | `hunger_to_da` | hypothalamus_hunger (1个) | frozen | 0.04 | 1.0 | 饥饿 tonic (ARC→LH→VTA) |
| 8 | `satiety_to_da` | satiety_neuron (1个) | frozen | 0.3 | **-1.0** | 饱腹抑制 (POMC→VTA) |
| 9 | `intake_to_da_reward` | intake_sensor (1个) | frozen | 1.0 | 0.05 | 摄食奖励 (CCK/GLP-1) |
| 10 | _(RPE 直注)_ | DADifferentialGate | — | — | 0.1 | d(fill)/dt 奖励预测误差 |

### 通路 3 特别说明（唯一可塑的 DA 输入）

`relay_to_da` 是**唯一**使用 STDP + eligibility trace 的 DA 输入束：

```python
BundleConfig(
    learning_rule="stdp", use_eligibility_trace=True,
    eligibility_tau=300.0, eligibility_gain=1.0,
    eligibility_ltd_rate=0.01, da_ema_tau=5000.0,
    initial_weight=0.1, weight_max=0.3, stdp_lr=0.005,
    synapse_gain=0.2,
)
```

两阶段结构：
```
relay (lamina V WDR) → [frozen, w=0.3] → proj (lamina I, spiking+CRI) → [STDP] → DA neurons
```

### 为什么有 10 条通路？

从架构角度，这些通路分 4 类：

| 类别 | 通路 | 作用 |
|------|------|------|
| **预测误差** | shadow, xin, shadow_nu | 把预测误差转为 DA |
| **能量/代谢** | hunger, satiety, intake, RPE | 把能量状态转为 DA |
| **感觉** | relay_to_da, thermo_delta | 把热觉信号转为 DA |
| **节律** | CPG | 保持 DA.post_trace > 0（防止 relay_to_da STDP 冻结） |

**问题**: 这些通路之间没有明确的优先级或权重协调。hunger (w=0.04) 和 satiety (w=0.3, sg=-1.0) 互相拮抗但没有设计上的保证。CPG 只是为了"防止 STDP 冻结"而存在的——这是一个补丁，暴露了 STDP 机制需要持续 post_trace 活动才能工作的设计缺陷。

---

## 5. DA 浓度 → STDP 学习：完整数据流

```
                               ┌─────────────────────┐
                               │  10 条输入通路        │
                               │  propagate() 每步     │
                               └─────────┬───────────┘
                                         │ da_input_currents
                                         ▼
┌──────────────────────────────────────────────────────────────┐
│  3 个 DA 神经元 (da_vta_0/1/2)                               │
│                                                              │
│  neuron.step(total_current):                                 │
│    total_input = Σbundle_I + bc_current + i_girk(D2R)       │
│    ┌─ membrane.inject ─→ Vm ─→ gate.conduct ─→ activation  │
│    └─ D2R: _da_local ← 上一步的 dopamine.concentration      │
│            if _da_local > 0.3: i_girk < 0 (超极化)           │
│                                                              │
│  dopamine._concentration = clamp(mean(activation), 0, 1)    │
└──────────────────────────┬───────────────────────────────────┘
                           │ dopamine.concentration
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  使用点 1: GainModCircuit → GatedReflexArc → bundle.learn() │
│                                                              │
│  gated_arc.step(da_concentration, dt):                       │
│    _da_ema = β×DA + (1-β)×_da_ema     (β=0.0002, τ=5000)   │
│    LTP = 1e-4 × E(t) × _da_ema                              │
│    LTD_active = 0.01 × pre × post × _da_ema                 │
│    decay = 1e-6 × w                                         │
│    dw = (LTP - LTD_active - decay) × 软边界                  │
│                                                              │
│  β = dt/(dt + 5000) = 0.0002                                │
│  → _da_ema 跟踪的是 5000 步 (~5s) 尺度的 DA 均值             │
│  → 不跟踪单次奖励事件的时间信息                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. 当前架构的核心问题

### 6.1 结构性问题

**a) DA 从不归零。**
- bc_current=0.1 就贡献了基线 ~0.09 的浓度
- 10 条通路中 8 条是兴奋性的，只有 1 条抑制（satiety）
- 真实 DA 范围 ≈ [0.02, 0.30] — 永远 > 0
- `LTP = η × E × DA_ema` — DA_ema > 0 意味着 LTP 始终部分活跃
- Gate 不是"开关"，是"旋钮"（只能调快慢，不能关断）

**b) 无基线减法。**
```python
# 当前:
LTP = eligibility_gain × E(t) × DA_ema

# 应该:
LTP = eligibility_gain × E(t) × max(0, DA_ema - DA_baseline)
```
没有基线减法，DA 的绝对值被用作门控信号，而不是"超出基线的部分"。

**c) τ_DA_ema (5000) 和 τ_eligibility (500) 差 10 倍。**
- Eligibility trace E(t) 记得 ~500 步内的 pre-post 共现
- DA_ema 把 ~5000 步内的 DA 全混在一起
- 结果：无法把特定行为归因到特定奖励时刻

**d) Neuromodulator 的 ODE (`dopamine.step()`) 完全不参与。**
- `tau_decay=2.0` 和 `tau_release=0.2` 形同虚设
- 浓度完全由 DA 神经元平均激活决定
- 容器层本质上只是一个 `float` 包装器

**e) `gain_factor()` 身兼两职。**
- 在 `_propagate_bundles()` 中调制突触电流
- 在 `_do_learning()` 中调制学习速率
- 语义混淆：增益调制 ≠ 学习门控

### 6.2 T-092 揭示的问题

| 条件 | DA_ema | w 饱和时间 |
|------|--------|-----------|
| REAL-DA | 0.18 | ~36k 步 |
| RANDOM-DA | 0.51 | ~20k 步 |

随机 DA (均值 0.5) 比真实 DA (均值 0.18) 学习快 3 倍。
**两者都在 40k 步内饱和** → gate 不能阻止学习，只能调节速度。

### 6.3 代码质量问题

- `dopamine.step()` 存在但从不被调用（死代码）
- D2Autoreceptor 的类默认 `da_r_leak=100.0` 与配置值 `d2_da_r_leak=1.0` 不一致 — 需要核实实际生效的值
- `create_dopamine()` 中的 `tau_decay`/`tau_release` 从未被使用
- CPG 通路的存在是一个 hack（"保持 post_trace > 0 防止 STDP 冻结"）

---

## 7. 重构建议方向

### 7.1 明确 DA 的架构边界

```
当前: Neuromodulator (容器) + DA神经元池 (计算) + 10条通路 (输入)
      → 三个职责混在一起

建议: 拆分为清晰的层次
  DA 容器层: 只负责存储和暴露浓度（可以极简到一个 float）
  DA 计算层: 神经元池 → 浓度（保留 D2R 负反馈）
  DA 输入层: 通路管理（可控的优先级/权重）
```

### 7.2 修复门控语义

```
关键改动:
  LTP = η × E × max(0, DA_ema - DA_baseline)
  使 DA = baseline 时 LTP = 0（gate 真正闭合）
```

### 7.3 时间常数对齐

```
当前: τ_eligibility=500, τ_DA_ema=5000 (10×)
建议: 引入双时间尺度:
  - 快通道 (τ≈200-500): phasic DA 跟踪 → 时间信用分配
  - 慢通道 (τ≈2000-5000): tonic DA 上下文 → 动机状态调制
```

### 7.4 清理死代码

- 删除 `dopamine.step()` 或让它真正工作
- 移除未使用的 `tau_decay`/`tau_release`
- 确认 D2R 的 da_r_leak 生效值

---

## 附录：关键文件索引

| 文件 | 关键内容 |
|------|----------|
| `components/modulator.py` | `Neuromodulator` 类, `create_dopamine()` |
| `components/compensation.py:368-454` | `D2Autoreceptor` 实现 |
| `components/neuron.py:373-652` | `neuron.step()` 激活计算 |
| `circuit/variant_adapter.py:614-661` | DA 神经元创建 |
| `circuit/variant_adapter.py:2060-2225` | DA 神经元步进 + 浓度赋值 |
| `circuit/variant_adapter.py:2861-3192` | `_init_da_circuit()` 10 条通路 |
| `circuit/bundle.py:310-435` | `bundle.learn()` STDP + DA_ema |
| `circuit/bundle.py:18-131` | `BundleConfig` 参数默认值 |
| `components/gated_reflex.py:42-122` | `GatedReflexArc` — DA 如何进入学习 |
| `circuit/gain_mod_adapter.py:42-53` | `GainModCircuit.step()` — DA 桥接点 |
| `components/da_differential_gate.py` | RPE 计算 (d(fill)/dt → DA) |
| `somatosensory/transducer_neurons.py` | ThermalDeltaNeuron (温觉→DA) |
| `components/cpg_neuron.py` | CPG 振荡器 (起搏器→DA) |
