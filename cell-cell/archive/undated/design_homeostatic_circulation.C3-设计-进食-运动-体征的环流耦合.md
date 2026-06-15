> **导航**: [[00_Dashboard/核心词条索引]] · [[00_Dashboard/理念架构图]]

# C3' 设计：进食-运动-体征的环流耦合

*替代原 C3（热源→DA）和 C5（三因子 Fruit）*

---

## 核心理念

奖励不是标量——奖励是**环流模式回归平衡的过程**。

```
传统设计（已废弃）：
  热源 → DA ↑ → 学习 ↑ → 简单强化

你的设计：
  体征平衡 → 环流占比稳定 → 低 DA → 慢学习（维持）
  体征失衡 → 环流占比偏移 → 运动+进食被激活 → 行动 → 回归平衡
```

---

## 三个子系统与环流通道

### 现有基础设施

| 子系统 | 代码中对应物 | 信号源 |
|--------|-----------|--------|
| **体征稳定** | `ThermalMembrane` + ECM temperature | `thermal = T_actual - T_setpoint` |
| **运动** | Motor→Body→Otolith→Vestibular→Motor | `body_speed`, `axis_acts` |
| **进食** | 热梯度→接近热源 | `world.body.position` vs `heat_source` |

### 三者的环流路径

```
① 体征环流（主环流，平时振幅最大）：
   ThermalMembrane → ECM temperature → thermal signal → Enc → Col
   → 内部稳态参考 → 偏差信号 → 回到 ThermalMembrane
   
② 运动环流（通常中等振幅）：
   Motor → Muscle → Body → Otolith → Aff → Enc → Col → Motor
   （已存在且完整）

③ 进食环流（通常小振幅）：
   thermal error → Col bias → Motor → Body move → 位置变化
   → 热源距离变化 → thermal 变化 → 回到 thermal error
```

---

## 环流比例模型

定义三个环流的振幅：

$$A_{homeo} = f(\text{thermal stability}) \quad \text{（体征越稳定，振幅越大）}$$
$$A_{motor} = f(\text{body\_speed}, \text{otolith Xin})$$
$$A_{feed}  = f(\text{thermal gradient} \times \text{body velocity toward heat})$$

归一化环流比例：

$$\rho_{homeo} = \frac{A_{homeo}}{A_{homeo} + A_{motor} + A_{feed}}$$

### 正常态

$$\rho_{homeo} \approx 0.7, \quad \rho_{motor} \approx 0.2, \quad \rho_{feed} \approx 0.1$$

体征稳定占主导。DA 低，学习慢，系统维持现状。

### 失衡态

$$\text{thermal error} > \theta_{alert} \implies$$
$$\rho_{homeo} \downarrow, \quad \rho_{motor} \uparrow, \quad \rho_{feed} \uparrow$$

体征失衡 → 环流重新分配 → 运动和进食被"推大"。

---

## 从环流偏移到行为激活

### 机制：环流偏移 → DA → 差异化学习

```
                    CirculationMeter
                         │
                    计算 ρ_homeo, ρ_motor, ρ_feed
                         │
              ┌──────────┴──────────┐
              │                     │
       ρ_homeo 下降          ρ_motor + ρ_feed 上升
              │                     │
       "体征不稳定"           "需要行动"
              │                     │
              └──────────┬──────────┘
                         │
                    DA 释放 ∝ |Δρ_homeo|
                         │
              ┌──────────┴──────────┐
              │                     │
        Motor STDP 增强        Thermal→Col 增强
        (运动学习加速)         (热源追踪学习加速)
              │                     │
              └──────────┬──────────┘
                         │
                    Body 向热源移动
                         │
                    thermal error ↓
                         │
                    ρ_homeo ↑ (回归)
                         │
                    DA ↓ (奖励完成)
```

---

## 影子层的角色

影子层沉积"正常"的环流模式：

```
影子层 STDP 学习到：
  "正常态 = ρ_homeo ≈ 0.7"

当主层实际 ρ_homeo = 0.4 时：
  影子层 Xin₁ = |预期 0.7 - 实际 0.4| = 0.3
  影子层 ν = dXin₁/dt > 0
  → DA 释放（C1 已实现的路径）
  → 运动+进食被激活
  → 行动 → 回归 → 影子层 Xin₁ → 0 → DA 回落
```

**这就是 C1 已经在做的事情的正确解读**——影子层 ν→DA 不只是"误差驱动学习率"，它是**体征失衡驱动行为的完整机制**。

---

## 实现方案

### 步骤 1：在 MotionState 中加入环流比例

```python
# motor_decision.py MotionState
homeo_amplitude: float = 0.0   # 体征环流振幅
motor_amplitude: float = 0.0   # 运动环流振幅  
feed_amplitude: float = 0.0    # 进食环流振幅
circulation_balance: float = 1.0  # ρ_homeo (1.0=完全平衡)
```

### 步骤 2：在 variant_adapter 中计算三个振幅

```python
# 体征振幅：thermal stability 的反函数
thermal_err = abs(self.thermal_membrane._prev_T 
                  - self.thermal_membrane._methylation)
homeo_amp = 1.0 / (1.0 + thermal_err * 10)  # 稳定时→1，失衡时→0

# 运动振幅：body speed + otolith Xin
motor_amp = body_speed + sum(
    abs(b.config.xin_tension) for b in oto_bundles) * 0.01

# 进食振幅：热梯度方向 × 速度方向（正=向热源，负=远离）
heat_dir = normalize(heat_pos - body_pos)
vel_dir = normalize(body_velocity)
feed_amp = max(0, dot(heat_dir, vel_dir)) * thermal_err
```

### 步骤 3：环流偏移 → DA

```python
# 归一化比例
total = homeo_amp + motor_amp + feed_amp + 1e-8
rho_homeo = homeo_amp / total

# 偏移量 = |当前比例 - 正常比例|
homeo_deviation = max(0, 0.7 - rho_homeo)  # 0.7 是"正常"比例

# DA 释放 ∝ 偏移量
if homeo_deviation > 0.05:
    self.dopamine.release(homeo_deviation * 0.5)
```

### 步骤 4：DA 差异化影响运动 vs 进食

当 DA 升高时，Col→Motor 的 STDP 增强（运动学习），
同时 Thermal→Enc 的 cross-axis STDP 增强（热源追踪学习）。

**这已经由现有的三因子学习规则自动实现**——DA 全局调制所有 STDP。

---

## 与震荡的联系

每个子系统有自己的环流周期（传播延迟决定）：

| 子系统 | 环流路径长度 | 估计周期 |
|--------|-----------|---------|
| 体征 | Thermal→ECM→Enc→Col (短) | ~100 步 = 0.1s |
| 运动 | Motor→Body→Oto→Aff→Enc→Col→Motor (长) | ~500 步 = 0.5s |
| 进食 | Thermal→Col→Motor→Body→位移→Thermal (最长) | ~5000 步 = 5s |

三个周期的**叠加**产生复合震荡。正常态下体征的短周期占主导；失衡时长周期（运动/进食）被激活。

**C4 的 standing_wave_score 可以检测哪个周期占主导**——从 ZCR 的变化判断环流是否从体征主导转向了运动/进食主导。

---

## 与 Fruit/DA 三因子的关系

**C5（三因子 Fruit）不再需要独立设计**。

在这个模型中：
- Fruit growing→ripe 的条件 = standing_wave_score 稳定 + DA 低（体征平衡）
- 如果 DA 持续高（体征失衡），Fruit 不会成熟 → 系统保持可塑
- 只有当环流回归平衡时，DA 下降，Fruit 才能成熟 → **垫支**

这就是"三者依靠影子层沉积"的实现——只有体征平衡时，结构才固化。
