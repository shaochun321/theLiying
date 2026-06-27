# STDP冷启动实验 — 实现方案 批次4：补丁E（Efference Copy监控）+ 集成清单

> 依据：裁定文档 v3 D04/D05，监控项第五节
> 写作日期：2026-06-25
> 本文档是实施前的最后确认文档，包含原子提交的完整变更清单。

---

## Patch E：Efference Copy 抑制比例监控

### 性质说明

补丁E是**纯监控/诊断逻辑**，不添加新信号路径，不涉及新的 SynapticBundle，不影响任何物理计算结果。因此强制三问（Q1生物/Q2物理结构/Q3参数）**不适用**于本补丁，但需要确认 TYPE 标签。

```
TYPE:INFRA
```

### 当前 Efference Copy 结构

`variant_adapter.py:616-634`（已实现部分）：
- 追踪 `_motor_efficacy[axis]` ∈ [0,1]：Motor 实际效果与预测效果之比
- 追踪 `_efference_gain[axis]`：前向模型增益，缓慢自适应学习
- **缺失**：Binding 事件被 efficacy 抑制的比例统计

### 抑制比例的定义

```
R_supp = N_supp / N_total

N_total：当期统计窗口内 Binding 计算次数（每步×Binding Cell 数量）
N_supp ：其中因 motor_efficacy 过低（< threshold）而被抑制的次数
```

告警条件：`R_supp ≥ 0.9`（裁定文档§五）

### 实现位置

**不新建文件**。在 `variant_adapter.py` 的 Efference Copy 代码段中追加计数器。

**具体修改**（在 `variant_adapter.py` 的 `__init__` 中）：
```python
# Patch E: suppression ratio monitoring (INFRA)
self._efference_supp_count: int = 0
self._efference_total_count: int = 0
self._efference_supp_ratio: float = 0.0
self._efference_monitor_window: int = 10000  # steps per reporting window
```

**在 TemporalBindingCell 激活计算之后**（每次 Binding 事件处）：

```python
# Patch E: track how many Binding events are suppressed by low motor efficacy
for binding_cell in self._binding_cells:
    self._efference_total_count += 1
    # Suppression criterion: motor efficacy below effective threshold for this axis
    axis = binding_cell.config.motor_axis  # if binding is axis-specific
    if self._motor_efficacy.get(axis, 1.0) < self._efficacy_suppress_threshold:
        self._efference_supp_count += 1

# Report every N steps
if self._tick % self._efference_monitor_window == 0 and self._efference_total_count > 0:
    self._efference_supp_ratio = (self._efference_supp_count /
                                   self._efference_total_count)
    if self._efference_supp_ratio >= 0.9:
        import warnings
        warnings.warn(
            f"[EXP] Efference Copy suppression ratio {self._efference_supp_ratio:.2f} "
            f">= 0.9 threshold. Check efficacy_suppress_threshold.",
            RuntimeWarning
        )
    # Reset window counters
    self._efference_supp_count = 0
    self._efference_total_count = 0
```

**metrics 输出**（加入监控状态）：
```python
ms.efference_supp_ratio = self._efference_supp_ratio
```

### 实施前需确认

在 `variant_adapter.py` 中确认：
1. `self._binding_cells` 的实际属性名（存储所有 TemporalBindingCell 实例的列表）
2. Binding Cell 是否有 `motor_axis` 属性（axis-specific suppression），还是按全局统计
3. `_efficacy_suppress_threshold` 的合适值（建议初始值 0.1：efficacy < 0.1 = 运动基本无效）

---

## Phase 1：process_hunger 移除规格

### 裁定（D04）：原子级同步，与五补丁同一提交

`spinal_reflex.py` 中 `process_hunger()` 方法**不删除**（保留历史），改为返回零值并加废弃警告：

```python
def process_hunger(self, thermo_activations, fill_fraction,
                   da_concentration=0.0, gain_multiplier=1.0, dt=0.001):
    """DEPRECATED: Hardcoded thermotaxis reflex removed in STDP cold-start experiment.

    Returns zero drives. Motor now driven exclusively by Langevin noise (AGC-modulated).
    See: STDP冷启动实验方案, Phase 1.
    """
    import warnings
    warnings.warn(
        "process_hunger() called but is disabled (STDP cold-start experiment Phase 1). "
        "All drives are zero. Remove this call to silence this warning.",
        DeprecationWarning, stacklevel=2
    )
    # Return zero drives matching original return structure
    return {axis: 0.0 for axis in ['x', 'y', 'z']}
```

`variant_adapter.py` 中调用 `process_hunger()` 的代码段（`L790-796`）：
```python
# PHASE 1: process_hunger disabled — hardcoded thermotaxis removed
# hunger_drives = self.spinal_reflex.process_hunger(...)   # [REMOVED]
hunger_drives = {axis: 0.0 for axis in ['x', 'y', 'z']}  # zero, Langevin only
```

（直接注释掉旧调用，替换为零值字典，无需调用已废弃的方法）

---

## 原子提交：完整文件变更清单

裁定 D04 要求所有变更在单次提交中完成：

| 操作 | 文件 | 内容 |
|------|------|------|
| **NEW** | `components/yolk_sac.py` | 补丁C：YolkSac（Capacitor，λ=0.002/步不乘dt） |
| **NEW** | `components/da_differential_gate.py` | 补丁D：DADifferentialGate（η_da=7.5，clip=5.0） |
| **NEW** | `components/binding_temporal.py` | 补丁B：TemporalBindingCell（τ_w=30，仅前庭卷积） |
| **MOD** | `components/langevin_noise.py` | 补丁A：仅加注释（σ₀=0.70是底层乘子，不改值） |
| **MOD** | `components/spinal_reflex.py` | Phase 1：process_hunger 返回零值+废弃警告 |
| **MOD** | `circuit/variant_adapter.py` | 五补丁集成 + Phase 1 调用替换（见下表） |

### variant_adapter.py 修改点汇总

| 位置 | 类型 | 内容 |
|------|------|------|
| `__init__` | ADD | `self.yolk_sac = YolkSac()` |
| `__init__` | ADD | `self.da_gate = DADifferentialGate(initial_fill=...)` |
| `__init__` | ADD | BindingCell → TemporalBindingCell 替换 |
| `__init__` | ADD | `self._efference_supp_count/total` 计数器 |
| `step()` 能量段 | ADD | `self.yolk_sac.step(self.energy_store, dt)` |
| `step()` Langevin段 | MOD | `eta = [e * self.agc.gain for e in eta]` |
| `step()` DA驱动段 | MOD | `da_drive = self.da_gate.step(fill_fraction, dt)` |
| `step()` Binding段 | ADD | Patch E 抑制比例计数 |
| `step()` L790-796 | MOD | `hunger_drives` 替换为零值字典 |
| metrics | ADD | `ms.yolk_level`, `ms.efference_supp_ratio` |

---

## 实施前完整核查清单

在写第一行代码之前，逐项确认：

### 接口核查
- [ ] 确认 `variant_adapter.py` 中 Langevin 输出送入 Motor 的具体行号（grep: `langevin.step`）
- [ ] 确认 `variant_adapter.py` 中 DA 驱动调用的具体行号（grep: `_circulation` 或 `da_current`）
- [ ] 确认 `variant_adapter.py` 中所有 `BindingCell(` 实例化位置
- [ ] 确认热感轴实际键名（grep: `therm` 在 `col_activations` 的键）
- [ ] 确认 `self._binding_cells` 的属性名（grep: `binding_cells` or `_binding`）

### 数学验证
- [ ] DADifferentialGate：在 dt=0.001 下，进食脉冲 Δfill_fraction ≈ 1.08e-4 → da_output = 7.5 × (1.08e-4 / 0.001) = 7.5 × 0.108 ≈ 0.81，clip_max=5.0 不触发 ✓
- [ ] YolkSac：100k 步 × 0.002/步 = 200单位 = yolk_initial_level ✓
- [ ] TemporalBindingCell：decay = exp(-1/30) ≈ 0.9672，3×τ_w = 90步后稳定 ✓
- [ ] AGC零点：E[η × (1+G_agc)] = 0（G_agc 与 η 统计独立，OU过程保证E[η]=0）✓

### 量纲一致性
- [ ] `lambda_yolk=0.002` 单位：能量单位/步（与 `basal_drain=0.0001` 相同量纲）
- [ ] `eta_da=7.5` 对应 `delta / dt` 形式（归一化fill_fraction差除以dt秒）
- [ ] `τ_w=30` 单位：步数（不是毫秒，dt=0.001s时 30步=30ms）

### 回归测试要求
- [ ] 五补丁+Phase 1 提交后立即运行：`python -m nexus_v1.tests.test_regression`（21/21 PASS）
- [ ] 运行熵审计：`python nexus_v1/run_audit.py`（信号深度 6/6，|V|<100，能量>0）
- [ ] 无NaN：YolkSac/DADifferentialGate/TemporalBindingCell 各加 `assert not math.isnan(output)`

---

## 阶段运行配置参考

Phase 3（1M步长程运行）的推荐配置：

```python
# 实验参数（对应裁定文档§三）
EXP_CONFIG = {
    'total_steps': 1_000_000,
    'report_interval': 10_000,
    'yolk_initial_level': 200.0,
    'lambda_yolk': 0.002,
    'tau_w': 30,
    'eta_da': 7.5,
    'sigma0': 0.70,  # base, actual = 0.70 × sqrt(T_bath)
    'tau_e': 500,    # eligibility trace
}

# 验收标准（对应§六）
SUCCESS_CRITERIA = {
    'weight_divergence': 0.02,   # max(Δw_ij) > 0.02
    'displacement_200k': 0.0,   # Δx(200k) > 0
    'fill_survival': 0.0,       # min(fill) > 0 @1M
    'supp_ratio': 0.9,          # R_supp < 0.9
}
```

---

*五个批次文档至此完整。可进入代码实施阶段。*
*实施顺序建议：C→D→B（新文件）→ A+E（variant_adapter修改）→ Phase 1（process_hunger禁用）→ 原子提交。*
