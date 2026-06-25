# Noether 严格化分析 (B1)

## 当前状态

NoetherProbe 有 4 个检查，但多数是**宽容近似**而非严格守恒：

| # | 守恒律 | 当前 | 问题 | 严格性 |
|---|---|---|---|---|
| 1 | 能量守恒 | E(t)+Q=E(0)+E_in | ⚠️ 遗漏多项 | 松 |
| 2 | 权重平衡 | ΔW 不应突跳 | ❌ 无分项审计 | 松 |
| 3 | Xin 账本 | total < bound | ❌ 不是守恒 | 弱 |
| 4 | Landauer | Q/bit > min | ⚠️ 粗估 | 中 |

## 严格化方案

### 1. 能量守恒 — 遗漏项

当前只追踪 `neuron.energy` + `body_kinetic` + `ecm_thermal`。

**遗漏**：
- **TemporalCoupler 电荷能量**: E_coupler = 0.5 × C × V²（6个 coupler，每个存储能量）
- **Binding→Motor 注入**: 直接 `membrane.inject()` 不经过 energy accounting
- **DA neuron→Column 注入**: `col._membrane.inject(da_current, dt)` 无能量追踪
- **VoltageRegulator 注入**: VR 注入电流但不扣 `neuron.energy`
- **EnergyStore**: 外部能量储存未计入

**修复**: 
- `TemporalCoupler` 加 `stored_energy` 属性
- 所有 `membrane.inject()` 旁路必须通过 `neuron.energy` 会计
- 或者：NoetherProbe 追踪 coupler 能量

### 2. 权重平衡 — 分项审计

当前只检查 ΔW 突跳，但不知道 ΔW 来自 LTP 还是 LTD 还是 decay。

**严格形式**: 
```
W(t) = W(0) + Σ_LTP - Σ_LTD - Σ_decay + Σ_sprout - Σ_prune
```

**修复**: Memristor 记录 `_cumulative_ltp`, `_cumulative_ltd`, `_cumulative_decay`

### 3. Xin — 从 bound 到守恒

当前：`total < bound`（bound 增长的）→ 永远通过。

**严格形式**: 
```
Xin_produced(0→t) = Xin_consumed(0→t) + Xin_remaining(t) - Xin_remaining(0)
```

**修复**: Bundle 已有 `_xin_consumed`。只需在 `compute_xin()` 中记录 `_xin_produced`。

### 4. Landauer — 信息论追踪

当前：粗估 "每次显著 dw > 0.001 = 1 bit"。

**改进**: 使用 Shannon 熵 `H = -Σp log p` of weight distribution。ΔH < 0 = bit erased。

### 5. 新增：电荷守恒

目前完全没有追踪膜电荷守恒：

```
Q_in(inject) = Q_out(leak + spike_reset) + Q_stored(membrane)
```

**修复**: `Membrane` 追踪 `_cumulative_charge_in` 和 `_cumulative_charge_out`。

---

## 优先级

> [!IMPORTANT]
> 最关键的缺口是 **coupler 能量** 和 **旁路注入**。这些能量"凭空出现"绕过了 accounting。

建议实施顺序：
1. TemporalCoupler.stored_energy 属性 + NoetherProbe 纳入
2. 旁路注入能量追踪（binding、DA、VR）
3. Xin 从 bound→strict
4. Weight 分项审计
5. Landauer 信息论
