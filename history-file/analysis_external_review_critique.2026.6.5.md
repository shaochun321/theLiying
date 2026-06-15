# 外部审查文档批判性评估

> 对 [2026.6.5.txt](file:///D:/cell-cc/cell/2026.6.5.txt) 和 [2026.6.5.1.txt](file:///D:/cell-cc/cell/2026.6.5.1.txt) 的逐条代码验证

---

## 文档一（2026.6.5.txt）：工程可行性审计

### 灾难一：刚性系统（Stiff ODEs）数值爆炸

> **声称**：如果使用显式欧拉法（`V += (V_ss - V) * dt / tau`），当 τ < dt 时会发散。
> 必须改用精确指数积分法 `V(t+dt) = V_ss + (V(t) - V_ss) × e^{-dt/τ}`。

**判定：❌ 已解决（审查者未看到代码）**

实际代码（[semiconductor.py L56-62](file:///d:/cell-cc/nexus_v1/components/semiconductor.py#L56-L62)）：

```python
def leak(self, resistance, dt=1.0):
    tau = resistance * self.capacitance
    decay = math.exp(-dt / max(tau, 0.01))   # ← 精确指数积分
    self.charge *= decay
```

Capacitor.leak() **已经使用精确指数衰减**，不是欧拉法。
`charge *= exp(-dt/τ)` 精确等价于审查者建议的公式。
且 τ 有下限 `max(tau, 0.01)` 防止极端情况。

**结论**：这个"灾难"不存在。Capacitor 是所有组件（CRI/DN/D2R）的基础原语，
新组件使用同一个 `Capacitor.leak()` 方法，自动继承数值稳定性。

---

### 灾难二：D2R 负反馈的锯齿震荡

> **声称**：`max(0, V-ec50)` 的硬折线在离散步进中会造成锯齿震荡。
> 建议改用 Softplus 函数。

**判定：⚠️ 部分有效**

MOSFET.conduct()（[semiconductor.py L99-117](file:///d:/cell-cc/nexus_v1/components/semiconductor.py#L99-L117)）实际实现：

```python
def conduct(self, v_gate):
    if v_gate >= self.v_threshold:
        return self.gm * (v_gate - self.v_threshold)       # 超阈值: 线性
    else:
        nVT = self.n_slope * max(self.v_thermal, 0.001)
        exponent = (v_gate - self.v_threshold) / nVT
        return max(0.0, self.gm * nVT * (math.exp(exponent) - 1.0))  # 亚阈值: 指数
```

**关键事实**：MOSFET **已有亚阈值指数过渡区**。
在 V ≈ V_th 附近，不是硬折线而是平滑的指数曲线。
亚阈值电流 ∝ exp((V-V_th)/(n·V_T))，这本质上就是 Softplus 的物理版本。

**但审查者的担忧有合理性**：D2R 的负反馈**延迟环路**（DA → Capacitor积分 → MOSFET → 膜电流）
确实可能在某些参数组合下产生振荡。这不是数值问题（MOSFET已平滑），
而是**控制论问题**（闭环稳定性取决于 τ_D2 vs τ_membrane）。

**行动**：实现时需要验证 D2R 环路的 Bode 图/相位裕量，或通过测试确认不振荡。
参数选择约束：τ_D2 >> τ_membrane（慢反馈更稳定）。

---

### 灾难三：DN 归一化的除零奇点

> **声称**：当输入静默时分母可能趋近 0。

**判定：⚠️ 部分有效，但严重性被夸大**

DN 的公式中 σ > 0 是常数（半饱和电压），所以分母 = σ + V_pool ≥ σ > 0。
只要 σ ≠ 0 且 V_pool ≥ 0（Capacitor 电压非负），不可能除零。

**但审查者提到的"浮点负向下冲"有道理**：如果 V_pool 出现微小负值
（因为 Capacitor.charge 理论上可以变负，虽然不应该），
分母可能 < σ 但仍然 > 0。不过不会是 NaN。

**行动**：在 DN 实现中加 `max(sigma + V_pool, sigma * 0.01)` 作为防御。成本为零。

---

### 灾难四：Landauer 加法的浮点吞噬

> **声称**：E_remodel（~10⁻⁶）加到膜功耗（~10⁰）时会被 float64 吞噬。

**判定：❌ 不是真实问题**

Float64 有 52-bit 尾数，相对精度 ~2.2×10⁻¹⁶。
10⁻⁶ 加到 10⁰ 的相对误差 = 10⁻⁶ / 10⁰ = 10⁻⁶ >> 10⁻¹⁶。
完全在 float64 精度范围内。

灾难性抵消（catastrophic cancellation）发生在**两个近似相等的大数相减**时，
而非大小数相加时。相加只丢失小数的低位精度（这里完全可接受）。

**结论**：浮点精度不是问题。审查者混淆了 cancellation 和 swamping。

---

## 文档二（2026.6.5.1.txt）：理论审计

### 1. α_{TS} 重复乘法

> **声称**：如果 dE_S/dt 已含 κ，则 α_{TS} × dE_S/dt = κ² × |ΔW/Δt|。

**判定：✅ 完全正确——这是我的错误**

实施计划中：
- dE_S/dt = κ × |ΔW/Δt|（已含代价）
- 统一方程又乘了 α_{TS} = κ

确实变成了 κ²。必须修正。采用审查者建议的**方案1**：
```
dE_S/dt = |ΔW/Δt|（原始变化率，无量纲/时间）
统一方程: dE_total/dt = P_T + κ × |ΔW/Δt| + P_Landauer
```

---

### 2. α_{TI} 量纲错配（严重）

> **声称**：α_{TI} = kT·ln2 量纲是 [能量]，乘以 dE_I/dt [功率] 得到 [J²/s]，不是功率。
> 且 dE_I/dt 被定义为欧姆功耗 Σξ²G²/R，这属于 T 的信号功耗，不是信息擦除代价。

**判定：✅ 完全正确——这是核心理论漏洞**

审查者精确诊断了两个混淆：

**混淆 1**：Σξ²G²/R 是信号传输的焦耳热，属于 P_T（膜电流功耗），不是 P_I。

**混淆 2**：Landauer 功率的正确定义是：
```
P_Landauer = kT_system × ln2 × dH/dt
           = [能量/bit] × [bit/时间]
           = [功率] ✓

而不是：
α_{TI} × (Σξ²G²/R)
= [能量] × [功率]  
= [J²/s] ✗
```

**修正**：
1. P_I 应定义为 P_Landauer = kT·ln2 × |dH/dt|（信息熵变化率来自 WeightEntropyProbe）
2. Σξ²G²/R 归入 P_T
3. 统一方程: dE/dt = P_T + κ×|ΔW/Δt| + kT·ln2×|dH/dt|

代码中 NoetherProbe 已有类似实现（[noether_probe.py L197](file:///d:/cell-cc/nexus_v1/circuit/noether_probe.py#L197)）：
```python
K_LANDAUER = 0.693 * self.LANDAUER_TEMP  # kT ln2
```
LANDAUER_TEMP = 1.0，所以 K_LANDAUER = 0.693。
但 WeightEntropyProbe 中的 landauer_bound 计算（[toprxin_ledger.py L122](file:///d:/cell-cc/nexus_v1/circuit/toprxin_ledger.py#L122)）：
```python
landauer_bound = math.log(2) * abs(snap.delta_entropy)
snap.landauer_satisfied = snap.q_dissipated >= landauer_bound * 0.01
```
**确实没有乘 kT**。`math.log(2)` 只是 ln2，缺少温度项。

---

### 3. ds²/ν 与 Noether 守恒的接榫

> **声称**：ds²/ν 与 T·S·I 功率框架之间缺少显式连接。建议 ν ≡ dE_total/dt。

**判定：✅ 方向正确，但需要细化**

审查者建议的接榫方式合理：
```
ν(t) = Σ heat_output(t) / dt = 瞬时总耗散功率
ds²(t) = |ΔE_stored(t)| = 储能变化绝对值
ds²/ν = 储能变化 / 耗散功率 = 热力学时间常数
```

NoetherProbe 已经在计算 `e_stored`、`q_dissipated`、`e_input`，
只需要将这些量桥接到 ds²/ν 的更新方程中。

---

### 4. CRI/DN/D2R 方程的中间变量

> **声称**：V_CRI_ss 中 Q_spike 的量纲需要明确（电荷注入 vs 电流脉冲）。

**判定：⚠️ 有效，需要在实现时明确**

在 Capacitor.inject() 中，参数是 `current`（电流），`ΔQ = I·dt`。
如果 spike 注入是直接加电荷（bypass inject()），则是电荷注入。
如果通过 inject() 加电流脉冲，则 Q_actual = I_spike × dt_spike。
实现时需要选择一种并明确标注。

---

### 5. 代码审计覆盖问题

> **声称**：如果新组件的电流没有通过 neuron.step() 的标准路径，则不会进入能量账户。

**判定：✅ 关键约束——必须在实现中遵守**

neuron.heat_output 的计算（[neuron.py L494-502](file:///d:/cell-cc/nexus_v1/components/neuron.py#L494-L502)）：
```python
self.heat_output = (clamped_current ** 2 * self._power.r_internal
                    + self._spike_heat
                    + self.config.basal_metabolic_cost)
self.energy = max(0.0, self.energy - self.heat_output)
```

只有通过 `scaled_current` 路径的电流才计入 I²R 热耗。
如果 CRI/D2R 的电流在 step() 外部注入（如 shadow_sandbox 的 Zener clamp），
则**不进入能量账户**。

**硬约束**：所有新组件的电流**必须在 neuron.step() 内部**处理，
通过标准的膜电流路径影响 V_m，从而自动进入 heat_output 计算。

---

## 总结评分

| 批评 | 判定 | 严重性 | 行动 |
|------|------|--------|------|
| 灾难一: 刚性 ODE | ❌ 已解决 | — | 无需行动 |
| 灾难二: D2R 锯齿 | ⚠️ 部分有效 | 低 | MOSFET 已平滑，但需验证闭环稳定性 |
| 灾难三: DN 除零 | ⚠️ 部分有效 | 低 | 加防御性 max()，成本为零 |
| 灾难四: 浮点吞噬 | ❌ 不存在 | — | 无需行动 |
| α_{TS} 重复 | ✅ 正确 | 中 | 采用方案1修正 |
| **α_{TI} 量纲错配** | **✅ 正确** | **高** | **拆分信号功耗与信息功耗** |
| ds²/ν 接榫缺失 | ✅ 正确 | 中 | 绑定 Noether 输出 |
| CRI Q_spike 量纲 | ⚠️ 有效 | 低 | 实现时明确 |
| 能量审计覆盖 | ✅ 关键 | 高 | 新组件必须在 step() 内部 |

> [!IMPORTANT]
> **两份文档中最有价值的洞察**：
> 1. **信号功耗 ≠ 信息功耗**（ξ²G²/R 是焦耳热，不是 Landauer 代价）
> 2. **新组件必须通过 step() 标准路径接入能量账户**（否则度量统一只存在于文档中）
>
> 两份文档的**局限性**：
> - 未看到 semiconductor.py 的实际代码（所以误判了灾难一和灾难四）
> - 未了解 MOSFET 的亚阈值特性（所以高估了灾难二）
> - 对项目的理解基于理论文档，不是代码（所以部分担忧的前提不成立）
