# 平行构建批判分析：p3g_dynamic_ecology

## 概览

| 维度 | 主项目 (cell-cc) | 平行构建 (p3g) |
|---|---|---|
| variant_adapter.py | 76KB / 1,600 行 | 109KB / 2,159 行 |
| 总 .py 文件数 | 82 | 136 |
| 声称阶段 | DA 乘法调制 (结构计算) | P3-G 动态生态生存 |
| P3g 验证 | 未到达 | ✅ PASS_DYNAMIC_SURVIVAL |

---

## 1. DA→Motor 调制：两种实现对比

### 平行构建 (line 1653-1683)
```python
def _propagate_bundles(self, bundles, dt):
    da_gain = max(0.05, min(3.0, self.dopamine.gain_factor()))
    for bundle in bundles:
        currents = bundle.propagate()
        if self._da_modulates_bundle(bundle):
            currents = [c * da_gain for c in currents]
        bundle.apply_to_targets(currents, dt)
```

### 主项目 (我们的实现)
```python
def _propagate_bundles(self, dt):
    da_level = self._get_da_concentration()
    gain_factor = 1.0 + self.da_modulator.alpha_gain * da_level
    for bundle in [enc→col, col→motor, sprouted]:
        currents = bundle.propagate()
        currents = [c * gain_factor for c in currents]  # motor-bound only
        bundle.apply_to_targets(currents, dt)
```

> [!NOTE]
> 两者本质相同——乘法缩放。但平行构建的 `_da_modulates_bundle()` 用字符串匹配 (`'move_'`, `'col_to_motor'`) 做路由选择，这是**语义检查**。我们的实现按 bundle 列表的结构位置分派（enc→col 和 col→motor 分开循环），是纯结构路由。

**判决：平行构建的 DA 实现物理上等价，但路由逻辑含轻度语义残留。**

---

## 2. DirectionSelector：核心架构分歧

这是平行构建"领先"的关键机制。细看 `motor_decision.py` line 526-602:

```python
class DirectionSelector:
    def select(self, motor_acts, state, da=0.1):
        noc_grad = state.body_frame_nociceptive_gradient
        food_grad = state.body_frame_nutritive_gradient
        
        # Escape: move away from nociception
        escape_x = -gain * adaptive_gain * urgency * front_hazard
        
        # Feed: move toward food
        feed_x = feed_gain * food_gate * satiation * food_grad[0]
        
        # Combine
        out[0] = clip(motor_acts[0] + escape_x + feed_x)
```

> [!WARNING]
> **这是加法电流注入的伪装形式。**
> 
> `DirectionSelector.select()` 直接对 motor_acts 做 `+= bias`。虽然注释说"not a semantic escape command"，但实际上：
> 
> 1. `body_frame_nociceptive_gradient` → `escape_x` 是一个**硬编码的 gradient→force 映射**
> 2. `body_frame_nutritive_gradient` → `feed_x` 是一个**硬编码的 food→approach 映射**
> 3. "有害=逃跑，营养=靠近"这个语义**没有从任何物理过程中涌现**——它被直接编码在代码里
> 
> 生物等价：这不是小脑的前向模型，而是一个**预编程的反射弧** (hardwired reflex)。真正的热趋性应该通过 DA 奖赏信号 + STDP 学习涌现方向偏好，而不是直接注入梯度力。

**判决：DirectionSelector 是显式语义内置。它违反了"structure constrains dynamics"原则——行为不是从结构约束中涌现的，而是被编码到 force bias 计算中。**

---

## 3. MotionState 数据类：信息臃肿

`MotionState` dataclass 有 **139 行，50+ 字段**（line 36-150）。包括：

- `body_frame_nutritive_gradient`
- `harmful_heat_behavior_status: str = "unassessed"` 
- `mixed_ecology_status: str = "unassessed"`
- `dynamic_ecology_status: str = "unassessed"`
- `escape_amplitude`, `escape_success`
- `feed_escape_balance`

> [!CAUTION]
> 这些字段大量包含**语义标签**（"nutritive", "harmful", "escape", "feed"）。一个物理系统不应该"知道"什么是食物，什么是危害——它只应该感受到温度梯度、nociceptive 信号、能量变化，然后通过学习产生行为偏好。
> 
> 对比我们的 `HebbianCircuit`：没有 `harmful_heat_behavior_status` 字段，因为系统不评估自己的行为是否"正确"——它只是按物理规则运行。

---

## 4. 实验验证的宽松度

P3g 实验 (`p3g_dynamic_multisource_ecology_validate.py`) 的 checks：

```python
"feed_bias_present": max(feed_bias) > 1e-4,      # 极低阈值
"escape_bias_present": max(escape_bias) > 0.01,   # 极低阈值
"survival_margin_positive": final_store > 0.10,    # 仅要求 10%
```

> [!NOTE]
> 这些验证条件非常宽松。`feed_bias > 1e-4` 只要 DirectionSelector 在任何一步产生了微弱偏差就通过——不验证**方向是否正确**。这意味着即使 agent 随机漂移但恰好碰到了食物（1800 步只需碰一次），也能 PASS。

---

## 5. 代码健康度

### ✅ 正面发现

| 优点 | 说明 |
|---|---|
| `_propagate_bundles` 钩子 | 与我们的设计一致（override 模式） |
| `SurfaceInteractionLedger` | 结构化的表面交互记录 |
| `NoetherProbe` 独立模块 | 20KB 的守恒验证，比我们的更全面 |
| `EcologicalScenarioConfig` | 参数化的生态配置 |
| `SelfOriginForwardModel` | 前向模型概念良好 |

### ❌ 架构风险

| 风险 | 严重性 | 说明 |
|---|---|---|
| variant_adapter 109KB | 🔴 高 | 单文件 2159 行，违反模块化原则 |
| `DirectionSelector` 硬编码梯度力 | 🔴 高 | 行为不涌现，被注入 |
| `_da_modulates_bundle` 字符串匹配 | 🟡 中 | 语义路由 |
| `MotionState` 50+ 字段 | 🟡 中 | 信息臃肿，语义标签泛滥 |
| `self_test_drive` 注入电流到 motor | 🟡 中 | 绕过正常信号链 |
| `NutritiveThermalSource` vs `ThermalStimulusSource` | 🔴 高 | 源类型编码"食物/有害"语义 |

---

## 6. 核心判决

> **平行构建通过在 MotorDecisionLayer 中内置方向偏好（DirectionSelector），跳过了"行为从物理约束中涌现"的核心挑战。**
> 
> P3g 的 PASS_DYNAMIC_SURVIVAL 不是热趋性涌现的证据——它是 `escape_x = -gain * noc_gradient` 的直接后果。
> 
> 这等价于在生物学中给虫子预装一个"看到火就跑"的基因——有效，但不是学习。

### 可借鉴的部分

| 组件 | 可借鉴性 | 条件 |
|---|---|---|
| `SurfaceInteractionLedger` | ✅ 高 | 剥离语义标签后 |
| `NoetherProbe` 独立化 | ✅ 高 | 设计理念良好 |
| `EcologicalScenarioConfig` | ✅ 高 | 纯参数化 |
| `BodySurface` 热通量模型 | ✅ 中 | 物理部分有价值 |
| `DirectionSelector` | ❌ 不可借鉴 | 违反涌现原则 |
| `NutritiveThermalSource` | ⚠️ 有条件 | 需删除语义分类 |

### 建议

1. **不追赶**。平行构建的"领先"是通过降低涌现标准实现的
2. **选择性吸收**：Noether Probe 独立化、SurfaceInteractionLedger 的分层记录结构
3. **坚持主线**：DA 乘法调制 → STDP 学出方向偏好 → 真正的热趋性涌现
