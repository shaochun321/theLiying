# VitalOscillator 实现方案 — 体征搏动器

## 目标

为系统注入**物理驱动的基底运动**，替代人工高斯噪声。
体征搏动器是能量耗散结构的自持振荡，由 EnergyStore 驱动，
输出耦合到 Motor 层产生基底随机游走。

解决 EXP-015 三大瓶颈中的第二个（无基底运动），
同时为第一个（Shadow 饱和/DA 崩溃）提供时变信号。

---

## 已有原型分析

### 已有组件

| 组件 | 位置 | 可复用性 |
|------|------|----------|
| [ResonantOscillator](file:///d:/cell-cc/nexus_v1/components/oscillator.py#L66) | `components/oscillator.py` | ✅ 核心 VdP + RK4，直接复用 |
| [EnergyStore](file:///d:/cell-cc/nexus_v1/components/energy_store.py#L68) | `components/energy_store.py` | ✅ 已有 `withdraw()` + Noether 审计 |
| [BiasCurrentSource](file:///d:/cell-cc/nexus_v1/components/compensation.py#L124) | `components/compensation.py` | ❌ 恒定电流，无振荡性 |
| [Capacitor](file:///d:/cell-cc/nexus_v1/components/semiconductor.py#L39) | `components/semiconductor.py` | ✅ KCL 审计已就位 |

### 现有 oscillator 用法

当前 `ResonantOscillator` 在 [variant_adapter.py L126-137](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py#L126-L137) 中用于**前庭 ISI 同步**:
```python
self.oscillators[axis] = ResonantOscillator(
    frequency=50.0, mu=1.0, amplitude=0.15)
```
它调制 Aff 膜电位增益，但**不消耗能量，不连接 EnergyStore**。

---

## 数理对齐

### 核心方程: VdP → 能量耗散

Van der Pol 振荡器的瞬时功率:

$$P_{osc}(t) = \mu \cdot (x^2 - 1) \cdot y^2$$

其中 $x$ 是归一化电压，$y$ 是归一化电流。

在 limit cycle 上，**平均耗散**:

$$\langle P \rangle = \frac{\mu \cdot A^2}{2 \cdot R_{eff}}$$

$A$ = 振幅 scaling，$R_{eff}$ = 等效耗散电阻。

### 能量-振幅耦合

搏动器振幅 ∝ EnergyStore 填充水平:

$$A_{vital}(t) = A_{base} \cdot f_{fill}(t)$$

其中 $f_{fill} = E_{level} / E_{capacity}$ ∈ [0, 1]。

- 能量充足 ($f_{fill} > 0.3$): $A_{vital} ≈ A_{base}$ → 正常搏动
- 能量匮乏 ($f_{fill} < 0.1$): $A_{vital} → 0$ → 搏动停止 → 死亡

**每次搏动的能量消耗**:

$$\Delta E_{beat} = P_{osc} \cdot dt = \text{vital\_energy\_cost} \cdot |x(t)| \cdot dt$$

通过 `EnergyStore.withdraw()` 结算 → 自动进入 Noether 会计。

### 时间常数匹配

| 参数 | 值 | 依据 |
|------|-----|------|
| 频率 f₀ | 2 Hz | BIO: 心跳 ~1-2 Hz; 工程: ~2000 步/周期 (dt=0.001) |
| μ | 2.0 | 弛豫振荡 → 近方波 → 清晰的搏动脉冲 |
| 基底振幅 A_base | 0.005 | 需 << 运动信号 (~0.01)，仅产生微弱颤动 |
| 能量消耗/步 | ~0.0002 | 约等于 basal_drain，可维持 ~50k 步 |

---

## 链路连通设计

### 信号流

```
EnergyStore.fill_fraction ──────────────┐
                                         ↓ 振幅调制
ResonantOscillator(f=2Hz, μ=2.0) ──→ output(t) = x(t) × A_base × f_fill
        │                                    │
        │ 能量结算:                           │ 三路输出:
        │ E.withdraw(cost)                   │
        │                                    ├─→ Motor 膜电位注入 (基底驱动)
        │                                    ├─→ 内感受 Enc 输入 (体征信号)
        │                                    └─→ MotionState.vital_pulse (诊断)
        │
        └─→ Noether: EnergyStore._total_withdrawn 增加
```

### 路径 1: Motor 基底驱动

搏动输出注入所有 Motor 神经元膜电位:

```python
# 在 variant_adapter.step() 中:
vital_out = self.vital_oscillator.step(dt) * self.energy_store.fill_fraction
# 注入 motor 膜电位 (不同轴加微弱相位差)
for i, (key, mot) in enumerate(self.motor_neurons.items()):
    phase_shift = i * 0.3  # 轴间相位差 → 不同轴不同步
    mot._membrane.inject(vital_out * math.cos(phase_shift), dt)
```

效果: 身体产生微弱的、不规则的颤动 → 打破空间对称 → dT/dt 非零。

> [!IMPORTANT]
> 注入量级必须远小于正常运动信号。A_base = 0.005 使得搏动产生的 Motor activation << 前庭驱动的 ~0.01。这不是噪声——是能量驱动的物理振荡。

### 路径 2: 内感受信号 (可选，Phase 2)

搏动输出可作为一个额外的 encoding 轴:

```python
# 未来: 内感受编码
mechanical_inputs['vital'] = vital_out
```

这使得 Shadow 层可以预测"自己的心跳" → 当心率因能量变化改变时 → 产生预测误差 → DA。但这是 Phase 2，当前不实现。

### 路径 3: MotionState 诊断

```python
ms.vital_pulse = vital_out
ms.vital_amplitude = abs(vital_out)
```

---

## 提案变更

### [NEW] `components/vital_oscillator.py`

```
VitalOscillator: 包装 ResonantOscillator + EnergyStore 耦合
  - 持有一个 ResonantOscillator(f=2.0, mu=2.0)
  - step(energy_fill, dt) → output
  - 每步从 EnergyStore 取能量 (withdraw)
  - 振幅 = base × energy_fill
  - 返回搏动电压
  - heat_output 属性用于 Noether 审计
```

> [!NOTE]
> **不修改** `ResonantOscillator` 本身。`VitalOscillator` 是一个包装层，
> 在 VdP 核心外增加能量耦合和 Noether 会计。

### [MODIFY] [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)

1. `__init__`: 创建 `self.vital_oscillator = VitalOscillator()`
2. `step()`: 在 Phase 0 (body integration) 之前:
   - 推进 vital oscillator
   - 从 EnergyStore 扣除能量
   - 注入 Motor 膜电位
   - 记录到 MotionState

### [MODIFY] [motor_decision.py](file:///d:/cell-cc/nexus_v1/circuit/motor_decision.py) — MotionState

添加 `vital_pulse` 和 `vital_amplitude` 字段。

---

## Noether 能量会计

```
每步结算:

  EnergyStore
    deposit()  ← World.consume_nearby()     [进入]
    withdraw() ← vital_energy_cost          [搏动消耗, 新增]
    withdraw() ← Vascular delivery          [神经元供能]
    tick()     ← basal_drain                [基础代谢]

  balance: total_deposited = total_withdrawn + total_basal + current_level - initial
  (已有 Noether check，新增 withdraw 自动计入)
```

搏动消耗通过 `EnergyStore.withdraw()` 结算:

```python
vital_cost = abs(vital_out) * self.vital_oscillator.energy_cost_per_unit * dt
self.energy_store.withdraw(vital_cost)
```

**不需要新的 Noether 账目** — `withdraw()` 已自动追踪到 `_total_withdrawn`。

---

## 验证计划

### 自动测试

1. **单元测试**: VitalOscillator 在不同 energy_fill 下的输出幅度
2. **能量守恒**: 运行 10k 步，验证 Noether balance ≈ 0
3. **回归测试**: 现有 21 项回归测试全通

### 行为验证

4. **EXP-016**: 150k 步热趋性重测
   - 设置: 与 EXP-015 相同（零外部前庭输入）
   - 预期: 搏动 → 微弱运动 → dT/dt ≠ 0 → Thermo AC → Shadow 预测误差 → DA → 行为
   - 成功标准: body speed > 0.001 均值, distance 变化 > 2.0

---

## Open Questions

> [!IMPORTANT]
> **Q1: 搏动频率 2 Hz 是否合适？**
> 
> 2 Hz = 2000 步/周期。太快（50 Hz）会被膜电位时间常数吃掉；太慢（0.1 Hz）运动反应太慢。2 Hz 是心跳频段，物理上合理。但你是否有不同偏好？

> [!IMPORTANT]
> **Q2: 内感受轴（路径 2）是否在 Phase 1 一起实现？**
> 
> 当前方案只实现 Motor 注入。内感受编码（将搏动作为 encoding 输入轴）会增加复杂度但提供体征→Shadow→DA 的完整闭环。是否现在一起做？

> [!IMPORTANT]  
> **Q3: 轴间相位差的物理来源？**
> 
> 当前用 `cos(i * 0.3)` 给不同 Motor 轴加相位差，使运动不完全同步。这是一个简化。是否需要用 `CoupledOscillatorArray` 实现更物理的多轴耦合？
