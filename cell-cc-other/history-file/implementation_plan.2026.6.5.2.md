# 母本分化 + 引导性构建：实施计划

> 用户指令：为特定模块做母本分化，创建专属元组件。将引导性构建写入总纲和熵账本。

---

## 核心原则

**反模式**：用全局修改服务局部需求（Zener 钳位所有 shadow neurons、Xin 归一化所有 bundles）

**正确模式**：每种特殊结构有专属分化元组件，就像生物中：
- 毛细胞有 **Ca²⁺ 系统**（已实现）—— 只存在于 hair cell
- Motor 有 **FatigueCapacitor**（已实现）—— 只存在于 motor
- Shadow col → DA 需要 **Spike Rate Integrator** —— 只存在于 spiking 投射神经元
- DA 神经元需要 **D2 Autoreceptor** —— 只存在于多巴胺神经元
- Shadow enc 需要 **Divisive Normalization** —— 只存在于感觉输入接收层

已有分化组件一览（NeuronConfig 中）：

| 组件 | 配置项 | 存在于 |
|------|--------|--------|
| VoltageRegulator | `use_voltage_regulator` | 大部分 |
| DecouplingCapacitor | `use_decoupling_cap` | 需要时 |
| BiasCurrentSource | `use_bias_current` | 有自发活动的 |
| AutomaticGainControl | `use_agc` | 需要增益适应的 |
| FatigueCapacitor | `use_fatigue` | Motor（spike-rate 自限）|
| Ca²⁺ subsystem | `ca_capacitance > 0` | 只 hair cell |

---

## 新增分化组件

### H. CalciumRateIntegrator（钙指示器速率积分器）

**只存在于：spiking 投射神经元（shadow col → DA 通路的源）**

**问题**：spiking 神经元的 activation = 0/1（瞬时），大部分时间 = 0。
下游 bundle（shadow→DA）看到的 pre-synaptic 信号几乎一直为 0，BCM 持续削弱权重。

**生物学**：树突棘中的 CaMKII（钙调蛋白激酶II）整合 Ca²⁺ influx：
- 每个 spike → Ca²⁺ influx → CaMKII 自磷酸化
- CaMKII 浓度反映 **窗口内平均发放率**
- 下游突触读取 CaMKII 浓度，而非单个 spike
- τ_CaMKII ≈ 10-100 ms（fast: 突触可塑性；slow: 基因表达）

**REF**: Lisman et al. 2012 (CaMKII as molecular memory); Bhatt et al. 2009

**实现**：

```python
# In NeuronConfig:
use_calcium_rate_integrator: bool = False
cri_tau: float = 50.0          # integration time constant (ms)
cri_spike_charge: float = 0.2  # Ca²⁺ per spike
cri_decay_rate: float = 0.01   # passive leak

# In Neuron.__init__:
if config.use_calcium_rate_integrator:
    self._cri_cap = Capacitor(capacitance=1.0)  # Ca²⁺ pool
    self._cri_leak_r = config.cri_tau            # τ = C × R

# In Neuron.step():
if self._cri_cap is not None:
    if self._spiked_this_step:
        self._cri_cap.inject(config.cri_spike_charge, dt)
    self._cri_cap.leak(self._cri_leak_r, dt)
    # CRI voltage = integrated spike rate (continuous, bounded)
    self.calcium_rate = min(self._cri_cap.voltage, 1.0)  # Zener on CRI

# In bundle.propagate():
# Source activation for bundles tagged "use_cri":
# pre = src.calcium_rate (if available) else src.activation
```

**关键**：Zener 钳位只在 CRI 的 Ca²⁺ Capacitor 上，不在膜电压上。
CRI 钳位是**元组件内部的**，不是全局的。

#### [NEW] `compensation.py` 新增 `CalciumRateIntegrator` 类
#### [MODIFY] `neuron.py` 新增 H 段配置和实例化

---

### I. DivisiveNormalizationReceptor（除法归一化受体）

**只存在于：影子 encoding 神经元（接收多源 Xin 输入的感觉层）**

**问题**：vestibular chain Xin 绝对值很大（5~20），直接灌入 enc → V_ss 无界。

**生物学**：视觉皮层 V1 的 divisive normalization：
- 每个神经元的响应 R_i = L_i^n / (σ^n + Σ L_j^n)
- 实现：GABA interneuron pool activity → shunting inhibition conductance
- 物理基础：并联的抑制性电导与兴奋性输入形成**分压器**
- REF: Carandini & Heeger 2012, Nature Reviews Neuroscience

**实现**：

```python
# In NeuronConfig:
use_divisive_norm: bool = False
dn_sigma: float = 1.0       # half-saturation constant
dn_exponent: float = 2.0    # Hill coefficient

# In Neuron.__init__:
if config.use_divisive_norm:
    self._dn_pool_cap = Capacitor(capacitance=5.0)  # pool activity integrator

# In Neuron.step():
# Called BEFORE membrane injection. Requires pool_input (sum of all Xin).
if self._dn_pool_cap is not None:
    # Pool activity = EMA of total input
    self._dn_pool_cap.inject(abs(input_current), dt)
    self._dn_pool_cap.leak(5.0, dt)  # τ_pool = 5 × 5 = 25
    pool = self._dn_pool_cap.voltage
    # Divisive normalization: I_eff = I / (σ + pool)
    dn_factor = config.dn_sigma / (config.dn_sigma + pool)
    input_current *= dn_factor
```

**关键**：归一化发生在**每个 enc 神经元内部**，用自身的 pool Capacitor。
不需要全局的 max(Xin) 计算。每个 enc 独立适应自己的输入范围。

#### [MODIFY] `compensation.py` 新增 `DivisiveNormalizationReceptor` 类
#### [MODIFY] `neuron.py` 新增 I 段配置和实例化

---

### J. D2Autoreceptor（D2 自受体）

**只存在于：DA 神经元**

**问题**：DA 饱和后无法恢复（VR 太慢，且是通用机制不了解 DA 特性）。

**生物学**：VTA DA 神经元的 D2 autoreceptor：
- DA 释放 → 扩散到突触间隙 → 结合 soma 上的 D2R
- D2R 激活 → 打开 GIRK K+ 通道 → 超极化 → 降低发放率
- 这是 DA 特有的**负反馈回路**，不存在于其他神经元
- τ_D2 ≈ 100-500 ms（比 VR 的 metabolic 恢复快）
- REF: Lacey et al. 1987; Ford 2014, Pharmacological Reviews

**实现**：

```python
# In NeuronConfig:
use_d2_autoreceptor: bool = False
d2_conductance: float = 0.5     # max GIRK conductance
d2_tau: float = 100.0           # D2R desensitization time constant
d2_ec50: float = 0.3            # half-activation DA concentration

# In Neuron.__init__:
if config.use_d2_autoreceptor:
    self._d2_receptor = MOSFET(v_threshold=config.d2_ec50, gm=config.d2_conductance)
    self._d2_da_cap = Capacitor(capacitance=1.0)  # local [DA] integrator

# In Neuron.step():
# Requires da_concentration input (from dopamine.concentration)
if self._d2_receptor is not None:
    # Integrate local DA concentration
    self._d2_da_cap.inject(da_concentration, dt)
    self._d2_da_cap.leak(config.d2_tau, dt)
    da_local = self._d2_da_cap.voltage
    # D2R activation → hyperpolarizing current
    i_girk = -self._d2_receptor.conduct(da_local)
    self._membrane.inject(i_girk, dt)
```

**关键**：D2R 创建了 DA 特有的**自抑制**。其他神经元不受影响。
DA → D2R → GIRK → 超极化 → 降低 DA，是 DA 浓度的天然稳定器。

#### [MODIFY] `compensation.py` 新增 `D2Autoreceptor` 类
#### [MODIFY] `neuron.py` 新增 J 段配置和实例化

---

## 引导性构建规则（写入熵账本）

### 新增 Section 7: GuidedConstructionAuditor

**原则**：当对同一结构的串行参数修改超过 N 次仍无效时（过渡自限），
强制进入引导性构建模式 —— 创建新的分化组件而非继续调参。

```python
@dataclass 
class SerialModificationLog:
    """Track serial modifications to the same structural pathway."""
    pathway_id: str          # e.g. "shadow_col_to_da"
    modifications: List[dict]  # [{tick, param, old, new, result}]
    
    def is_self_limiting(self, threshold: int = 3) -> bool:
        """过渡自限：连续 N 次修改未改善 → 需要引导性构建."""
        if len(self.modifications) < threshold:
            return False
        # Check if last N modifications all failed to improve
        recent = self.modifications[-threshold:]
        return all(m.get('result') == 'no_improvement' for m in recent)

class GuidedConstructionAuditor:
    """Entropy ledger Section 7: 引导性构建审计.
    
    Rules:
    1. DIFFERENTIATION_REQUIRED: When serial modifications hit self-limit,
       flag that a new differentiated component is needed.
    2. COMPONENT_LOCALITY: Each structural modification must be scoped
       to a specific component, not applied globally.
    3. ANCESTRY_TRACKING: New components must declare which neuron types
       they apply to (via NeuronConfig flags).
    """
```

#### [MODIFY] `toprxin_ledger.py` 新增 Section 7

---

## 回退清单（移除全局补丁）

1. ❌ 移除 `shadow_sandbox.py` 中的 Zener voltage clamp（全局）
2. ❌ 移除 `shadow_sandbox.py` 中的 Xin 全局归一化
3. ✅ 保留 shadow→DA 单通路（正确的结构）
4. ✅ 保留 DA neuron VR（通用组件，正确使用）

---

## 文件变更总结

### [MODIFY] [compensation.py](file:///d:/cell-cc/nexus_v1/components/compensation.py)
- 新增 `CalciumRateIntegrator` 类（H）
- 新增 `DivisiveNormalizationReceptor` 类（I）

### [MODIFY] [neuron.py](file:///d:/cell-cc/nexus_v1/components/neuron.py)
- NeuronConfig 新增 H/I/J 配置项
- Neuron.__init__ 新增 H/I/J 实例化
- Neuron.step() 新增 H/I/J 计算步骤

### [MODIFY] [shadow_sandbox.py](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py)
- shadow col config: 启用 `use_calcium_rate_integrator=True`
- shadow enc config: 启用 `use_divisive_norm=True`
- 移除 Zener clamp 和 Xin 全局归一化

### [MODIFY] [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)
- DA neuron config: 启用 `use_d2_autoreceptor=True`
- shadow→DA bundle: 使用 `calcium_rate` 作为 pre-synaptic signal

### [MODIFY] [toprxin_ledger.py](file:///d:/cell-cc/nexus_v1/circuit/toprxin_ledger.py)
- 新增 Section 7: GuidedConstructionAuditor

---

## 验证计划

### 自动化测试
```bash
python test_plan_D.py  # 50k 步验证 DA 动态
```

### 验证项
1. Shadow enc activation **自动** bounded（by DN receptor）
2. Shadow col → DA **持续** 有信号（by CRI）
3. DA **不饱和** 且有动态范围（by D2R）
4. Noether ALL PASSED
5. 每个新组件**只存在于**指定神经元类型
