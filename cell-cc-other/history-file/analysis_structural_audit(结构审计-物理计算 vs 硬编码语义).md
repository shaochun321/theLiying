# 结构审计：物理计算 vs 硬编码语义

> 审计标准：每个构建按 5 级量表评估
> - ⬛ **纯物理**：动力学方程+结构拓扑决定行为，无语义标签
> - 🟩 **结构约束**：拓扑选择是 L2 决策，但运行时行为由物理驱动
> - 🟨 **参数选择**：物理机制正确，但关键参数是手工校准而非导出
> - 🟧 **混合**：物理计算框架包裹硬编码语义判断
> - 🟥 **硬编码**：直接用 if/else 或字符串标签决定行为

---

## 1. 半导体原语层

### Capacitor — `dQ/dt = I`, `V = Q/C`, `leak = exp(-dt/RC)`
**评级：⬛ 纯物理**

全部基于 KVL/KCL。`inject()` = 电流→电荷积累，`leak()` = RC 放电。
KCL 审计追踪 (`_q_in`, `_q_out`)。**零硬编码**。

→ [semiconductor.py:L39-L109](file:///D:/cell-cc/nexus_v1/components/semiconductor.py#L39-L109)

### MOSFET — `I = gm × (Vgs - Vth)` + 亚阈值指数
**评级：⬛ 纯物理**

超阈值线性 + 亚阈值指数。`update_gate()` = HH 一阶门控动力学。
`gated_conduct()` = `m × gm × f(V)`。`adapt_threshold()` = NBTI 偏移。
**零硬编码**。

→ [semiconductor.py:L116-L190](file:///D:/cell-cc/nexus_v1/components/semiconductor.py#L116-L190)

### Memristor — `I = V × G`, `G = 1/R`, `R = R_min + ΔR(1-w)`
**评级：⬛ 纯物理**

欧姆定律 + 可变电阻。`apply_dw()` 有 Noether 审计追踪。
权重变化的 *来源* 由外部 STDP/BCM 规则决定，Memristor 本身只是被动器件。
**零硬编码**。

→ [semiconductor.py:L198-L268](file:///D:/cell-cc/nexus_v1/components/semiconductor.py#L198-L268)

---

## 2. 学习规则层

### STDP — `dw = η × dt × (pre_trace × post_trace - λ × w) × soft_bounds`
**评级：🟩 结构约束**

物理机制：pre_trace（突触前指数衰减）× post_trace（突触后）= 时间相关性。
乘性软边界 `(w_max - w)` 和 `(w - w_min)` 是自然饱和。
decay 项 `λ × w` 是物理耗散。

> **唯一的 L2 选择**：使用 STDP 而非 BCM 是根据 `max_maturation` 决定的。
> 但 `maturation_stage` 本身是结构状态（PNN 依赖），不是语义标签。

→ [bundle.py:L313-L328](file:///D:/cell-cc/nexus_v1/circuit/bundle.py#L313-L328)

### BCM — `dw = η × pre × post × (post - θ)`, `dθ/dt = (a² - θ)/τ`
**评级：🟩 结构约束**

滑动阈值 θ 是物理计算（均值平方的低通滤波）。
BCM 规则本身是 Bienenstock-Cooper-Munro 理论的标准形式。

> **注意**：`getattr(tgt.config, 'theta_m', post)` — 用 getattr 回退是防御性的，
> 但 `theta_m` 作为 config 属性而非动力学状态有些奇怪。

→ [bundle.py:L330-L353](file:///D:/cell-cc/nexus_v1/circuit/bundle.py#L330-L353)

### 学习规则选择逻辑
**评级：🟧 混合**

```python
if self.config.bundle_role == "cross_axis":
    effective_rule = "hebbian_decay"
else:
    effective_rule = "stdp" if max_maturation == 0 else "bcm"
```

> **⚠ 这是字符串标签路由**。`bundle_role == "cross_axis"` 是语义判断，
> 不是物理量。理想情况下，规则选择应由结构属性（如突触时间常数、
> 输入统计量的自相关时间）自然涌现。
>
> 同样，`max_maturation == 0 → STDP, == 1 → BCM, == 2 → frozen`
> 是离散语义分支，而非连续物理转变。
>
> **现实评估**：这是文献标准做法（多数神经网络模型都这样做），
> 但在"拒绝语义标签"的标准下，**这是最显著的硬编码点之一**。

→ [bundle.py:L288-L297](file:///D:/cell-cc/nexus_v1/circuit/bundle.py#L288-L297)

---

## 3. 差分对拓扑

### thermal_differential_map
**评级：🟩 结构约束（L2 选择正确标注）**

```python
thermal_differential_map = [
    ('therm_front', 'move_x', +10.0),   # front heat → excite move_x
    ('therm_back',  'move_x', -10.0),   # back heat  → inhibit move_x
    ...
]
```

**接线拓扑（谁连谁）** = L2 进化选择 ✅ 正确。
**增益符号（+10/-10）** = 结构约束：差分对的本质是 ±1 符号。
运行时行为由 STDP 权重演化决定，增益只是放大器。

> **⚠ 增益幅度 10.0 是手工校准的**。物理上应由阻抗匹配或
> 层间增益平衡推导。但符号和拓扑结构是正确的。

→ [hebbian.py:L532-L564](file:///D:/cell-cc/nexus_v1/circuit/hebbian.py#L532-L564)

---

## 4. Phase 2 冬眠护盾

### `energy_plasticity_scale = min(1.0, fill / 0.10)`
**评级：🟩 结构约束 + 🟨 参数选择**

**机制是物理的**：ATP 耗竭 → LTP/LTD 所需蛋白合成停止 → 突触冻结。
`fill_fraction` 从 EnergyStore（电容器）直接传入，是物理量。
对称冻结（v2）是实验验证的正确选择。

> **⚠ 阈值 0.10 是手工选择的**。应由 ATP→蛋白合成→AMPA 运输的
> 代谢链自然决定。但作为一阶近似，线性斜坡是合理的。

→ [bundle.py:L236-L307](file:///D:/cell-cc/nexus_v1/circuit/bundle.py#L236-L307)

---

## 5. EnergyStore

### 电容器模型：deposit / withdraw / basal_drain
**评级：⬛ 纯物理 + 🟨 参数选择**

**模型是纯物理的**：有限容量电容器 + 恒流源上限 + 漏电。
Noether 审计 (`total_deposited = withdrawn + basal + current`)。

> **⚠ 参数问题**：
> - `capacity = 1000`、`initial_fill = 0.5`、`basal_drain = 0.0001` — 全是手工调参
> - `delivery_factor()` 中的 0.3 阈值是硬编码断点
> - 但这些都是**标度参数**，不影响物理机制的正确性

→ [energy_store.py:L68-L190](file:///D:/cell-cc/nexus_v1/components/energy_store.py#L68-L190)

---

## 6. ECM / PNN 临界期门控

### `plasticity_gate = 1.0 - pnn_maturity`
**评级：🟩 结构约束**

**PNN 成熟动力学**：`d_pnn = (target - pnn) / τ`（一阶松弛）。
**DA 降解**：`d_degrade = K × (DA - baseline) × pnn`（活性依赖重塑）。
**Q10 温度校正**：`q10^(ΔT/10)`（HH 标准）。

> **物理正确**：PNN 成熟是连续物理过程，不是离散阶段切换。
> `plasticity_gate` 作为乘法因子平滑调制学习率。
> DA 降解提供了负反馈（新颖→DA↑→PNN 降解→可塑性恢复）。

→ [ecm.py:L148-L238](file:///D:/cell-cc/nexus_v1/components/ecm.py#L148-L238)

---

## 7. 脊髓反射弧

### `delta_x = back - front`, `output = delta × gain × gate`
**评级：🟩 结构约束（L2 选择正确标注）**

**退缩方向** = L2 硬连线 ✅（文件开头大字标注 `L2:SELECTION`）。
**MOSFET 门控** = 物理器件（皮层可覆写的模拟门）。
**空间对比** = 物理计算（不同皮肤 patch 的激活差分）。

> **⚠ `reflex_gain = 0.5` 是手工校准的**。
> **⚠ `hunger_approach_gain = 2.0` 经过 EXP-018 校准** — 虽然手工，但有实验依据。
> DA 调制 (`da_factor`) 通过乘法因子注入，是物理的。

→ [spinal_reflex.py:L118-L291](file:///D:/cell-cc/nexus_v1/components/spinal_reflex.py#L118-L291)

---

## 8. DA 神经元池

### 真实 Neuron 替代 Neuromodulator.release()
**评级：🟩 结构约束**

DA 神经元是真实 `Neuron` 实例（τ=2s, R=1Ω, bc=0.1），不是硬编码释放函数。
D2 自受体 = MOSFET 负反馈（`gm=0.5, ec50=0.3`）。
DA 浓度 = 神经元激活（自然涌现，不是手动设置）。

> **✅ 从硬编码 `release()` 函数升级为结构计算** — 这是正确的方向。
> **⚠ `bc_current = 0.1` 和 `d2_ec50 = 0.3` 是参数选择**。

→ [variant_adapter.py:L410-L468](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py#L410-L468)

---

## 9. 侧抑制

### `InhibitorySynapse` + `NDRElement`
**评级：🟩 结构约束**

NDR (Negative Differential Resistance) 元件 = 物理非线性器件。
连接矩阵 = L2 拓扑选择。增益 = 物理参数。
Motor 交叉抑制 (`gain=0.15`) = 前庭脊髓推挽。

> **连接拓扑是手动指定的**（all-to-all），但 NDR 动力学是物理的。

→ [variant_adapter.py:L195-L217](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py#L195-L217)

---

## 综合评分

| 构建 | 评级 | 主要问题 |
|------|------|----------|
| Capacitor / MOSFET / Memristor | ⬛ 纯物理 | — |
| EnergyStore | ⬛+🟨 | 标度参数手工选择 |
| ECM / PNN 门控 | 🟩 | — |
| STDP / BCM 规则本体 | 🟩 | — |
| **学习规则选择逻辑** | **🟧 混合** | **字符串标签路由** |
| 差分对拓扑 + 增益符号 | 🟩+🟨 | 增益幅度手工校准 |
| Phase 2 冬眠护盾 | 🟩+🟨 | 阈值 0.10 手工选择 |
| 脊髓反射弧 | 🟩 | L2 选择正确标注 |
| DA 神经元池 | 🟩 | 参数手工选择 |
| 侧抑制 | 🟩 | — |

---

## 🔴 最大硬编码点：学习规则选择

```python
# bundle.py L288-292 — 最显著的语义路由
if self.config.bundle_role == "cross_axis":   # ← 字符串标签
    effective_rule = "hebbian_decay"           # ← 语义选择
else:
    effective_rule = "stdp" if max_maturation == 0 else "bcm"
```

**这违反了"拒绝语义标签"原则。** 理想替代方案：

1. **统一规则**：所有突触使用同一规则（如广义 STDP），
   参数（τ_pre, τ_post, decay_rate）根据突触类型自动不同
2. **连续过渡**：`maturation → 0-1` 连续插值 STDP↔BCM，
   而非离散 if/else 切换
3. **结构推导**：cross-axis 使用 hebbian_decay 是因为 BCM θ
   被 intra-axis 活动主导——这应该由计算自然发现，
   而非预先标注 `bundle_role`

> [!IMPORTANT]
> 这不是当前要修的 bug——系统工作正常。但在"物理计算"的美学标准下，
> 这是**需要最终解决的最大结构债务**。
>
> 所有其他构建（包括 Phase 2 冬眠护盾）都遵循了结构原则。

---

## 🟢 最优秀的构建

1. **半导体原语层**（Capacitor/MOSFET/Memristor）— 纯 KVL/KCL 物理
2. **ECM PNN 门控** — 连续成熟动力学 + DA 负反馈 + Q10 温度校正
3. **DA 神经元池** — 从硬编码函数升级为真实 Neuron 实例

这三个构建完全没有语义标签，行为完全由结构+物理方程决定。
