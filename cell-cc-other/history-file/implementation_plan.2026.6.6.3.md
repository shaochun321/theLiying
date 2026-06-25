# C3' 实施计划：进食-运动-体征的环流耦合

> 设计文档: [design_homeostatic_circulation.2026.6.5.md](file:///D:/cell-cc/cell/design_homeostatic_circulation.2026.6.5.md)  
> 本地备份: [docs/design_homeostatic_circulation.2026.6.5.md](file:///L:/Users/%E7%BB%8D%E6%98%A5/.gemini/antigravity-ide/brain/b28b1552-1fcc-4344-b53a-904fd4f4bced/docs/design_homeostatic_circulation.2026.6.5.md)

---

## 核心理念

**奖励不是标量——奖励是环流模式回归平衡的过程。**

三个环流通道的振幅比例（ρ_homeo, ρ_motor, ρ_feed）反映系统状态。体征失衡 → ρ_homeo ↓ → DA ↑ → 运动+进食被激活 → 行动 → 回归平衡 → DA ↓。

---

## 现有基础设施审计

| 需要的 | 代码中已有 | 状态 |
|--------|-----------|------|
| 体征信号 | `ThermalMembrane` → ECM temperature | ✅ 完整 |
| 运动环流 | Motor→Body→Otolith→Aff→Enc→Col→Motor | ✅ 完整 |
| DA 释放 | `DopamineModulator.release()` | ✅ 完整 |
| 三因子学习 | `_do_learning()` PNN×DA×sync gate | ✅ 完整 |
| CirculationMeter | `circulation_meter.py` | ✅ 已存在 |
| body_speed | `world.body.speed()` | ✅ 已存在 |
| MotionState | `motor_decision.py` | ✅ 已存在 |
| 进食方向 | 热梯度 × body_velocity | ⚠️ 需要加热源位置 |

> [!IMPORTANT]
> 大部分基础设施已存在。C3' 主要是**连接和计算**工作，不是新增底层组件。

---

## Proposed Changes

### Step 1: MotionState 扩展

#### [MODIFY] [motor_decision.py](file:///d:/cell-cc/nexus_v1/circuit/motor_decision.py)

在 `MotionState` 中加入环流比例字段：

```python
homeo_amplitude: float = 0.0     # 体征环流振幅
motor_amplitude: float = 0.0     # 运动环流振幅
feed_amplitude: float = 0.0      # 进食环流振幅
rho_homeo: float = 0.7           # 归一化体征比例
rho_motor: float = 0.2           # 归一化运动比例
rho_feed: float = 0.1            # 归一化进食比例
homeo_deviation: float = 0.0     # |ρ_homeo - 0.7|
```

---

### Step 2: 三个振幅计算

#### [MODIFY] [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)

在 step() 的 MotionState 计算区域（Phase 0a-0b 附近），加入振幅计算：

```python
# ── C3': 环流振幅计算 ──

# ① 体征振幅: thermal stability 的反函数
# 稳定时 → 1.0, 失衡时 → 接近 0
# 使用 MOSFET conduct 而非数学函数 (S0)
thermal_err = abs(self.thermal_membrane._prev_T
                  - self.thermal_membrane._methylation)
homeo_amp = 1.0 / (1.0 + thermal_err * 10.0)

# ② 运动振幅: body speed + otolith Xin 张力
otolith_xin = sum(
    abs(b.config.xin_tension)
    for b in self.bundles_vest_to_enc
) * 0.01
motor_amp = self.world.body.speed() + otolith_xin

# ③ 进食振幅: 热梯度方向 × 速度方向 × thermal_err
# 正 = 向热源移动, 负/零 = 远离或静止
heat_pos = self.world.get_heat_source_position()  # 需要实现
body_pos = self.world.body.position
body_vel = self.world.body.velocity
heat_dir = normalize(heat_pos - body_pos)
vel_dir = normalize(body_vel)
feed_amp = max(0.0, dot(heat_dir, vel_dir)) * thermal_err
```

---

### Step 3: 环流比例 → DA 释放

在 step() 中 DA 相关区域加入：

```python
# ── C3': 环流偏移 → DA ──
total_amp = homeo_amp + motor_amp + feed_amp + 1e-8
rho_homeo = homeo_amp / total_amp

# 偏移量: 正常态 ρ_homeo ≈ 0.7
homeo_deviation = max(0.0, 0.7 - rho_homeo)

# DA 释放 ∝ 偏移量 (阈值 0.05 防止噪声)
if homeo_deviation > 0.05:
    self.dopamine.release(homeo_deviation * 0.5)

# 记录到 MotionState
ms.homeo_amplitude = homeo_amp
ms.motor_amplitude = motor_amp
ms.feed_amplitude = feed_amp
ms.rho_homeo = rho_homeo
ms.homeo_deviation = homeo_deviation
```

---

### Step 4: World 热源接口

#### [MODIFY] [world.py](file:///d:/cell-cc/nexus_v1/world/world.py) (或等效文件)

> [!IMPORTANT]
> 需要确认 World 类当前是否已有热源位置。如果没有，需要加一个简单的接口。

```python
def get_heat_source_position(self) -> tuple:
    """Return position of the nearest heat source."""
    # 如果 World 已有 heat sources, 返回最近的
    # 否则返回一个默认位置
```

---

### Step 5: 影子层沉积正常比例

影子层已经在观察主层——它通过 STDP 学到的权重分布自然编码了"正常态"下的信号模式。当 ρ_homeo 偏移时，影子层的预测（基于正常态权重）和实际状态产生 Xin，这个 Xin 已经在通过 C1 路径（shadow col → DA）驱动 DA 释放。

**C3' 的环流比例偏移 DA 是第二条 DA 通路**——与 C1 的 shadow Xin DA 互补：
- C1: 微观级（单 bundle Xin → DA, 快速）
- C3': 宏观级（环流比例偏移 → DA, 较慢）

> [!NOTE]
> 不需要额外修改影子层。现有的 shadow→DA 路径已经隐式实现了"正常比例沉积"。C3' 只是加了一条显式的宏观 DA 通路。

---

## Open Questions

> [!IMPORTANT]
> **热源位置接口**: World 类目前是否已经有热源位置信息？如果有 ThermalField，热源位置应该已经可获取。请确认。

> [!IMPORTANT]
> **两条 DA 通路的叠加**: C1 (shadow Xin→DA) 和 C3' (ρ_homeo→DA) 同时存在。两者的量级需要平衡。建议 C3' 的 DA 释放量较小（homeo_deviation × 0.5 中的 0.5 可能需要调参），让 C1 仍然是主要的精细调制通路。

> [!NOTE]
> **C5 (三因子 Fruit) 自然消解**: 设计文档说 C5 不再需要独立设计。Fruit 成熟条件 = standing_wave_score 稳定 + DA 低 = 体征平衡。这是否需要在 fruit 代码中加一个显式检查，还是现有机制已经隐式实现？

---

## Verification Plan

### Automated Tests
```bash
python test_circulation_coupling.py  # 50k步
```
验证项:
1. 正常态: ρ_homeo ≈ 0.7 (thermal 稳定时)
2. 失衡态: ρ_homeo ↓ 当 thermal_err ↑ (人为注入热偏差)
3. DA 响应: homeo_deviation > 0.05 时 DA 释放增加
4. 回归: 运动→接近热源→thermal_err↓→ρ_homeo↑→DA↓
5. Noether: 0 violations (新 DA 释放不破坏能量守恒)

### Manual Verification
- MotionState 中 rho_homeo 的时间序列图
- DA concentration 与 homeo_deviation 的相关性
