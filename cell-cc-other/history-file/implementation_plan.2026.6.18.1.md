# 反射优先架构 — 实施方案

## 问题背景

延长线（三次大步长构建）的核心策略是让热趋性从**皮层 STDP 链路**涌现：
`Aff → Enc → Col → Motor`，由 DA 调制权重。

结果：200k 步后 Δx = 0.270，离目标 5.0 差 18×。根本原因是 **thermal columns 没有 axis-specific 的 col→motor bundle**——它们只通过 cross-axis bundle（gain=0.7, w_init=0.05, w_max=0.15）到达 Motor。这是一个**拓扑盲区**，不是参数问题。

本方案走另一条路：**反射优先 + 拓扑修补**。让反射层立即提供行为能力，同时修复 STDP 链路的结构缺陷。

---

## 需用户确认的决策

> [!IMPORTANT]
> **延长线 bug fixes 是否独立合并？**
> Memristor 负电阻保护和 anti-saturation（tanh/MM）是纯粹的物理纠错，与方向选择无关。建议无论走哪条路都先合入。但如果你希望本地代码完全独立于延长线，也可以自行实现等效修复（本方案 Phase 0 包含了这些）。

> [!WARNING]
> **反射增益标定需要实验**
> Phase 1 的增益值（hunger_approach_gain, klinotaxis gains）都是理论估计。需要跑 50k-100k 步验证 Δx 改善情况。如果初始值不理想，可能需要 2-3 轮参数调整。

## 开放问题

1. **DA-反射耦合的方向**：DA 应该调制反射增益（DA↑→ approach更强），还是反射效果应该反过来驱动 DA（成功接近热源→DA reward）？两者都有生物学依据。我倾向**双向**：DA → reflex gain（短期），reflex success → DA（长期）。
2. **thermal col→motor axis-specific bundle 是否要新增？** 还是只在反射层解决 thermal→motor 的路由？如果新增 bundle，STDP 路径也会受益，但增加了系统复杂度。

---

## 提出的修改

### Phase 0: Bug Fixes（必须，与方向无关）

#### [MODIFY] [semiconductor.py](file:///D:/cell-cc/nexus_v1/components/semiconductor.py)

**Memristor 电阻安全钳位**

当前 `resistance` 属性计算 `r_min + (r_max - r_min) * (1 - w)`。如果 `w` 因数值误差或外部注入超过 1.0，`resistance` 可以变成负数，`conductance = 1/resistance` 爆炸到 1,000,000。

```python
# 当前:
@property
def resistance(self) -> float:
    return self.r_min + (self.r_max - self.r_min) * (1.0 - self.w)

# 修改为:
@property
def resistance(self) -> float:
    w_safe = max(0.0, min(1.0, self.w))  # 防御性钳位
    return self.r_min + (self.r_max - self.r_min) * (1.0 - w_safe)
```

**Anti-saturation：conductance 上限**

```python
# 当前:
@property
def conductance(self) -> float:
    return 1.0 / max(self.resistance, 1e-6)

# 修改为: 添加物理上限 (1/r_min)
@property
def conductance(self) -> float:
    g = 1.0 / max(self.resistance, self.r_min)
    return min(g, 1.0 / self.r_min)  # 不超过最大物理电导
```

---

### Phase 1: 强化现有反射层

#### [MODIFY] [spinal_reflex.py](file:///D:/cell-cc/nexus_v1/components/spinal_reflex.py)

**1a. Hunger approach 增益提升 + DA 调制**

当前 `hunger_approach_gain = 0.3`，hunger gate 只被 `fill_fraction` 控制。修改为：
- 基础增益 0.3 → 0.6（翻倍）
- 新增 `da_modulation` 参数：DA 浓度乘以反射增益
- 降低 `hunger_gate_v_threshold` 0.3 → 0.15（更容易开启）

```python
@dataclass
class SpinalReflexConfig:
    # ... existing ...
    hunger_approach_gain: float = 0.6        # was 0.3
    hunger_gate_v_threshold: float = 0.15    # was 0.3 (opens below ~85% fill)
    hunger_gate_gm: float = 1.5
    # NEW: DA modulation range [da_min_gain, da_max_gain]
    # DA=0 → gain × da_min_gain, DA=1 → gain × da_max_gain
    da_min_gain: float = 0.5                 # half gain at zero DA
    da_max_gain: float = 2.0                 # double gain at max DA
```

**1b. `process_hunger()` 接受 DA 参数**

```python
def process_hunger(self, thermo_activations, fill_fraction,
                   da_concentration: float = 0.5, dt: float = 1.0):
    # ... existing spatial contrast logic ...
    
    # DA modulation: lerp between da_min_gain and da_max_gain
    da_factor = (self.config.da_min_gain + 
                 da_concentration * (self.config.da_max_gain - self.config.da_min_gain))
    
    raw_x = delta_x * self.config.hunger_approach_gain * da_factor
    raw_y = delta_y * self.config.hunger_approach_gain * da_factor
    
    # ... existing hunger gate logic ...
```

#### [MODIFY] [variant_adapter.py](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py)

**1c. 传递 DA 浓度给 hunger reflex**

```python
# 现有 (line ~768):
hunger_drives = self.spinal_reflex.process_hunger(
    thermo_activations, self.energy_store.fill_fraction, dt)

# 修改为:
hunger_drives = self.spinal_reflex.process_hunger(
    thermo_activations, self.energy_store.fill_fraction,
    da_concentration=self.dopamine.concentration, dt=dt)
```

---

### Phase 2: 新增 Klinotaxis 模块

#### [NEW] [thermal_klinotaxis.py](file:///D:/cell-cc/nexus_v1/components/thermal_klinotaxis.py)

**C. elegans 式偏置随机游走**

这是一个全新的组件，实现 klinokinesis（运动速率调制）+ klinotaxis（方向偏置）。不需要 STDP 学习，不需要 200k 步权重成熟——它是**物理级**的梯度追踪。

**物理原理**：
- 记录过去 N 步的 dT/dt（温度变化率）
- dT/dt > 0（越来越暖）→ 保持当前运动方向（减少转向）
- dT/dt < 0（越来越冷）→ 增加转向频率（pirouette）
- 使用 Capacitor 做 EMA 平滑（S0 合规，无 magic 常数）

```
┌─────────────────────────────────────────────┐
│           ThermalKlinotaxis                 │
│                                             │
│  T_mean (4 patches) ──→ [Capacitor: EMA]    │
│                              ↓              │
│                     dT_ema = V_new - V_old   │
│                              ↓              │
│              ┌──────────────┴──────────────┐│
│   dT > 0:    │ run_bias = gain × dT_ema   ││
│              │ (在当前运动方向加速)          ││
│   dT < 0:    │ turn_drive = gain × |dT|    ││
│              │ (注入横向随机电流)            ││
│              └─────────────────────────────┘│
│                              ↓              │
│  output: {move_x: ..., move_y: ..., ...}    │
└─────────────────────────────────────────────┘
```

关键参数：
- `ema_capacitance`: 控制温度记忆时间（τ = C × R）
- `run_gain`: dT>0 时的加速增益
- `turn_gain`: dT<0 时的转向增益
- 使用 `body.velocity` 方向作为"当前运动方向"

#### [MODIFY] [variant_adapter.py](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py)

**2b. 集成 klinotaxis 到 step() 循环**

在 hunger reflex 之后、STDP 链路之前注入 klinotaxis 电流：

```python
# After hunger reflex (line ~772), add:
klinotaxis_drives = self.klinotaxis.process(
    patch_temps, self.world.body.velocity, 
    fill_fraction=self.energy_store.fill_fraction,
    da_concentration=self.dopamine.concentration, dt=dt)
for mkey, drive in klinotaxis_drives.items():
    if drive != 0.0 and mkey in self.motor_neurons:
        self.motor_neurons[mkey]._membrane.inject(drive, dt)
```

---

### Phase 3: 拓扑修复 — Thermal Col → Motor 直接通路

#### [MODIFY] [hebbian.py](file:///D:/cell-cc/nexus_v1/circuit/hebbian.py)

**当前拓扑缺陷**：`all_axes` 包含 `therm_front/back/left/right`，但 `axis_motor_map` 只映射了 `yaw→move_x, pitch→move_y, roll→move_z`。**所有 thermal columns 只能通过 cross-axis 束**（gain=0.7, w_max=0.15）到达 Motor。

**修复**：新增 thermal-to-motor axis-specific bundles。

```python
# 新增 thermal→motor 映射:
# therm_front/back → move_x (前后温差驱动纵向运动)
# therm_left/right → move_y (左右温差驱动横向运动)
thermal_motor_map = [
    (['therm_front', 'therm_back'], 'move_x'),
    (['therm_left', 'therm_right'], 'move_y'),
]
for therm_axes, mot_name in thermal_motor_map:
    sources = [self.column_neurons[ax] for ax in therm_axes]
    b_therm = SynapticBundle(
        config=BundleConfig(
            bundle_id=f"therm_{'_'.join(therm_axes)}_to_{mot_name}",
            learning_rule="stdp",
            initial_weight=0.2,
            weight_max=0.5,
            stdp_lr=0.005,
            synapse_gain=3.0,    # moderate, not as strong as VOR
            bundle_role="feedforward",
            coupler_capacitance=1.0,
            coupler_r_leak=2.0,
            coupler_adapt_vth=0.2,
            coupler_adapt_gm=2.0,
            coupler_blayer_c_slow=100.0,
            coupler_blayer_r_slow=10.0,
            coupler_blayer_gm=0.01,
            coupler_blayer_k=2.0,
            decay_rate_by_stage=(0.5, 0.1, 0.01),
        ),
        sources=sources,
        targets=[self.motor_neurons[mot_name]],
    )
    self.bundles_col_to_motor.append(b_therm)
```

> [!NOTE]
> 这个修复**同时让 STDP 路径受益**。即使不做 Phase 1/2 的反射增强，仅修复拓扑就能让 thermal 信号通过高增益通路到达 Motor。这是延长线未发现的结构盲区。

---

## 修改清单

| Phase | 文件 | 改动类型 | 复杂度 |
|-------|------|---------|--------|
| 0 | `semiconductor.py` | 修改 2 个属性 | 低 |
| 1a | `spinal_reflex.py` | Config + process_hunger 签名 | 低 |
| 1c | `variant_adapter.py` | 传参 1 行 | 低 |
| 2 | `thermal_klinotaxis.py` | 新增 ~120 行 | 中 |
| 2b | `variant_adapter.py` | 集成 ~15 行 | 低 |
| 3 | `hebbian.py` | 新增 thermal bundles ~30 行 | 中 |

总改动量：约 200 行。无破坏性变更（全部向后兼容）。

---

## 验证计划

### 自动测试

```bash
cd d:\cell-cc
python -m pytest nexus_v1/tests/ -v
```

### 实验验证

1. **Phase 0 验证**：检查 Memristor 在边界条件下 conductance 不爆炸
2. **Phase 1+2 验证**：跑 50k 步，对比：
   - 修改前 Δx
   - Phase 1 only Δx（增强反射）
   - Phase 1+2 Δx（反射 + klinotaxis）
3. **Phase 3 验证**：跑 100k 步，观察 thermal col→motor 权重是否通过 STDP 成熟

### 核心指标

| 指标 | 修改前基线 | Phase 1 目标 | Phase 1+2 目标 |
|------|-----------|-------------|---------------|
| Δx (50k) | ~0.05 | > 0.5 | > 1.0 |
| 反射 motor drive | 0 (hunger gate未开) | > 0.01/step | > 0.05/step |
| thermal col→motor weight | 0.05 (cross only) | 0.2 (new bundles) | 0.3+ (STDP mature) |

---

## 与延长线的关系

| 延长线改动 | 本方案处理 |
|-----------|-----------|
| Memristor 负电阻 fix | ✅ Phase 0 自行实现等效 |
| Anti-saturation (tanh/MM) | ✅ Phase 0 conductance 上限 |
| K_ema 发散 fix | ⏳ 待评估（本地是否有此问题） |
| Class 1 Driver (W=2.5) | ❌ 不采用（反射层替代） |
| Langevin noise | ❌ 不采用（klinotaxis 替代） |
| 六刀参数标定 | ❌ 不采用（保留为平行分支） |
| CRI 给 Col neurons | ⏳ 值得考虑但不急（反射层不依赖 Col 放电率） |
