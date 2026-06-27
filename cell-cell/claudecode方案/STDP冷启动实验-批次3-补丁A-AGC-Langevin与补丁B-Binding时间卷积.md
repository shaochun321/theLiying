# STDP冷启动实验 — 实现方案 批次3：补丁A（AGC→Langevin）+ 补丁B（Binding时间卷积）

> 依据：裁定文档 v3 D01/D02/D05，及 v3 补充裁定第一、二节
> 写作日期：2026-06-25

---

## 批次2量纲勘误

**YolkSac.step() 代码修正**（批次2已同步更新）：

```python
# 错误（批次2原稿）：
transfer = self.config.lambda_yolk * dt   # → 2e-6/步，差1000倍

# 正确（裁定文档§二）：
transfer = self.config.lambda_yolk        # → 0.002/步，与 basal_drain 同量纲
```

量纲说明：`lambda_yolk` 单位为"单位/步"，`step()` 内不除以/乘以 dt。与 `EnergyStore.basal_drain=0.0001`（单位/步）量纲相同。

---

## Patch A：AGC→Langevin 接入

### 三问核查

**Q1 生物对应物**
> BIO: 蓝斑-去甲肾上腺素系统（LC-NE, Locus Coeruleus - Norepinephrine）
> 饥饿/应激状态下，LC 激活使皮质神经元的基础噪声幅度（膜电位涨落）增大，
> 增强随机探索而不引入方向偏好（均值仍为零）。
> REF: Sara SJ (2009) "The locus coeruleus and noradrenergic modulation of cognition."
>      *Nature Reviews Neuroscience* 10:211-223.

**Q2 物理结构**
```
EnergyStore.fill_fraction ──→ AGC.step() ──→ AGC.gain (= 1 + G_clamped ≥ 1)
                                                       │
                                                       ▼（乘法调制）
ECM.temperature ──→ LangevinNoise.step() ──→ η(t) ──×(1 + G_agc)──→ Motor 驱动

约束：E[η × (1 + G_agc)] = E[η] × (1 + G_agc) = 0
      （G_agc 为能量状态函数，与 OU 噪声独立，均值不引入偏移）
```

**Q3 参数依据**

| 参数 | 值 | 来源 |
|------|-----|------|
| σ₀ | **0.70（不变）** | 裁定 D01：底层乘子，实际输出 σ₀√T_bath ≈ 0.07 |
| AGC.gain 范围 | [1.0, 1 + g_max] = [1.0, 5.0] | `agc.py:AGCConfig.g_max=4.0` |
| 有效 σ 范围 | [0.70, 3.50] × √T_bath | 饱食=1.0×底层，极度饥饿=5.0×底层 |

---

### 裁定附加约束：零点纯度（v3 §二）

> AGC 乘法后 OU 噪声均值必须保持为 0。
> 仅改变方差（探索幅度），不改变均值（方向分布）。

实现检查清单：
- [ ] `LangevinNoise.step()` 的 OU 过程本身为零均值（已有，OU 过程性质保证）
- [ ] AGC gain 作为**标量乘子**施加于输出，不加任何常数项
- [ ] `variant_adapter.py` 中执行乘法前后验证 3000 步样本均值 |E[η]| < 0.01

---

### 实现策略：VariantCircuit 层面的乘法（不修改 LangevinNoise）

`LangevinNoise` 是 OU 生成器，其接口完整且正确。Patch A 的修改**完全在 `variant_adapter.py` 中完成**，不触碰 `langevin_noise.py`。

**集成点（`circuit/variant_adapter.py`）：**

找到 Langevin 输出被送入 Motor 驱动的代码段，在此处插入 AGC gain 乘法。

原始模式（伪代码）：
```python
eta = self.langevin.step(self.ecm_vestibular, dt)   # [η_x, η_y, η_z]
# ... eta 随后送入 Motor
```

Patch A 修改（在 `langevin.step()` 调用之后，Motor 注入之前）：
```python
eta = self.langevin.step(self.ecm_vestibular, dt)   # [η_x, η_y, η_z]

# Patch A: AGC modulates exploration amplitude via LC-NE analogue
# BIO: Sara 2009, NRN — hunger scales noise std, not direction
agc_gain = self.agc.gain                             # 1.0 + G_clamped, ≥ 1.0
eta = [e * agc_gain for e in eta]                   # zero-mean preserved
```

**执行顺序约束**：`self.agc.step()` 必须在此之前已被调用（当前 `variant_adapter.py:836` 已满足）。

---

### `langevin_noise.py` 的仅注释修改

`langevin_noise.py:64` 不改动数值，仅补充注释说明 σ₀ 的物理含义（裁定 D01 要求）：

```python
# sigma0=0.70 is the fluctuation-dissipation base multiplier.
# Actual output std = sigma0 * sqrt(T_bath) ≈ 0.07 at T_bath=0.01.
# Do NOT change this value; modulate via AGC gain in variant_adapter.
sigma0: float = 0.70
```

---

## Patch B：TemporalBindingCell（时间卷积窗口）

### 三问核查

**Q1 生物对应物**
> BIO: 突触前钙残余（presynaptic calcium remnant）介导的短时程易化（STF）快成分。
> 前庭信号触发突触前 Ca²⁺ 内流，部分 Ca²⁺ 在 τ_STF 内滞留于突触前终末。
> 滞留的 Ca²⁺ 使后续释放概率增大，等效于前庭信号在 Binding 突触处短时"记忆"。
> 热感信号到达时，与被滞留的前庭信号配对，实现跨时序的因果 AND 检测。
> REF: Zucker RS & Regehr WG (2002) "Short-term synaptic plasticity."
>      *Annual Review of Physiology* 64:355-405. （τ_STF 快成分 20-50ms）

**Q2 物理结构**
```
vestibular Column激活 V_i(t)
    ↓
Capacitor（τ_w = 30步，RC积分器）
    ↓ Ṽ_i(t) = Σ V_i(t-s) × exp(-s/τ_w)   [s=0..τ_w]
    ↓（离散：Ṽ_i[t] = decay×Ṽ_i[t-1] + update×V_i[t]）
    ↓
AND 门（乘积，与母类相同）× T_j(t)  ← 热感信号：瞬时，不经卷积
    ↓
B_ij(t)（Binding 激活）
```

**因果非对称性约束（v3 §一）：**
> 仅前庭信号 V_i(t) 通过卷积展宽，热感信号 T_j(t) 保持瞬时。
> 若双端都展宽，因果方向不可区分（系统无法区分"运动→热变化"与"热变化→运动"）。

**Q3 参数依据**

| 参数 | 值 | 来源 |
|------|-----|------|
| τ_w | 30 步（30ms@dt=1ms） | 裁定 D02：STF 快成分 20-50ms 区间中值，Zucker & Regehr 2002 |
| decay | exp(-1/30) ≈ 0.9672 | 离散化：每步衰减因子 |
| update | 1 - exp(-1/30) ≈ 0.0328 | 离散化：每步注入权重 |

---

### 文件位置

**新建文件**：`cell-cc-other/nexus_v1/components/binding_temporal.py`

**不修改** `components/binding.py`（母类）。

---

### 接口规格

```python
# TYPE:BIO
# Short-term facilitation window for vestibular-thermal coincidence detection.
# Only vestibular axes are convolved; thermal axis remains instantaneous.
# BIO: Presynaptic Ca2+ remnant (STF fast component), Zucker & Regehr 2002.

from dataclasses import dataclass, field
from typing import Dict, Set
import math

from nexus_v1.components.binding import BindingCell, BindingConfig

@dataclass
class TemporalBindingConfig(BindingConfig):
    tau_w: int = 30                        # BIO: STF fast component ~20-50ms, Zucker 2002
    thermal_axes: Set[str] = field(
        default_factory=lambda: {'therm'}  # axes kept instantaneous (causal asymmetry)
    )


class TemporalBindingCell(BindingCell):
    """TYPE:BIO — Vestibular-thermal coincidence detector with STF temporal window.

    Extends BindingCell by applying an exponential moving average (Capacitor)
    to vestibular axes only. Thermal axes remain instantaneous.

    Causal asymmetry: V_i(t) -> convolved; T_j(t) -> instantaneous.
    This ensures STDP learns "motion caused thermal change", not the reverse.

    BIO: Presynaptic Ca2+ remnant drives STF, tau_STF fast ~20-50ms.
    REF: Zucker & Regehr 2002, Annu Rev Physiol 64:355-405.
    """

    def __init__(self, config: TemporalBindingConfig):
        super().__init__(config)
        self._tau_config: TemporalBindingConfig = config
        self._decay = math.exp(-1.0 / config.tau_w)   # per-step decay
        self._update = 1.0 - self._decay               # per-step injection weight
        # Leaky integrator state for each vestibular axis (Capacitor analogue)
        self._v_tilde: Dict[str, float] = {
            ax: 0.0 for ax in config.source_axes
            if ax not in config.thermal_axes
        }

    def compute(self, col_activations: Dict[str, float]) -> float:
        """Override: convolve vestibular axes, pass thermal axes instantaneously."""
        # Step 1: update leaky integrators for vestibular axes
        for ax in self._v_tilde:
            v_now = col_activations.get(ax, 0.0)
            self._v_tilde[ax] = self._decay * self._v_tilde[ax] + self._update * v_now

        # Step 2: build effective activation dict for parent AND gate
        effective = {}
        for ax in self._tau_config.source_axes:
            if ax in self._tau_config.thermal_axes:
                effective[ax] = col_activations.get(ax, 0.0)   # instantaneous
            else:
                effective[ax] = self._v_tilde[ax]               # time-convolved

        # Step 3: delegate to parent product AND gate
        return super().compute(effective)

    def reset_integrators(self):
        """Reset leaky integrators (e.g., between trials)."""
        for ax in self._v_tilde:
            self._v_tilde[ax] = 0.0
```

---

### VariantCircuit 集成点

`TemporalBindingCell` 替换 VariantCircuit 中所有 `BindingCell` 实例化。

**`__init__` 中的替换（查找现有 BindingCell 实例化位置）：**

```python
from nexus_v1.components.binding_temporal import TemporalBindingCell, TemporalBindingConfig

# 替换模式：将现有 BindingCell(BindingConfig(...)) 替换为：
TemporalBindingCell(TemporalBindingConfig(
    binding_id=...,
    source_axes=...,           # 保持原有配置
    co_activation_threshold=...,
    gain=...,
    tau_w=30,                  # BIO: STF, Zucker 2002
    thermal_axes={'therm'},    # 热感轴保持瞬时
))
```

**需要实施前确认**：在 `variant_adapter.py` 中 `grep -n "BindingCell\|BindingConfig"` 确认所有实例化位置，逐一替换。

---

### 边界条件与已知风险

**冷启动积分器状态**
- 系统启动时 `_v_tilde` 全为 0.0
- 前庭信号需要约 3×τ_w ≈ 90 步才能在积分器中建立稳定响应（约 3 个时间常数）
- 影响：前 90 步 Binding 激活率低于稳态，但不影响长期行为

**τ_w 对 STDP 时间窗口的影响**
- τ_w=30 步 < τ_e=500 步（适格迹时间常数），两者量级匹配
- 若τ_w 过小（<10步），前庭信号在热感信号到达前已衰减，Binding=0，STDP 无因果配对
- 若τ_w 过大（>100步），积分器记住多次运动，因果配对信噪比下降

**thermal_axes 配置的重要性**
- 若误将 `therm` 加入卷积轴，双端展宽消除因果方向性
- `thermal_axes={'therm'}` 必须与实际热感轴名称完全匹配
- 实施前确认：`grep -n "therm" variant_adapter.py` 检查热感轴实际键名

---

## 两项补丁的组合效应验证

Patch A + B 共同保证 STDP 的"探索-配对"循环：

```
饥饿时 AGC.gain↑
    → Langevin σ_eff↑
    → 运动幅度增大（Patch A）
    → 前庭 Column 激活增大 V_i(t)
    → TemporalBindingCell 积分器充电 Ṽ_i↑
    → 热感到达时 B_ij = Ṽ_i × T_j > 0（Patch B）
    → STDP 适格迹 E_ij 开始累积
    → DA 释放时 Δw = η × E_ij × DA > 0（补丁D）
    → 方向性权重涌现
```

Patch A 提供"足够大的探索信号使 Binding 激活"，Patch B 提供"足够长的时间窗口使因果配对成立"。二者缺一不可。

---

*下一批次：批次4 — 补丁E（Efference Copy监控）+ Phase 1（process_hunger 移除规格）+ 集成检查清单 + 单次提交文件变更清单。*
