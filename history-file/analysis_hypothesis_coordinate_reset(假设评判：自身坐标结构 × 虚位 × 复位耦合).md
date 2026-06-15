# 假设评判：自身坐标结构 × 虚位 × 复位耦合

> 日期: 2026-06-13
> 背景: L2.09 三重死亡拷问（26/26 存活）暴露了 L2 反馈环的系统性失效

---

## 1. 假设的生物学对标

你的假设中的每个结构概念，都能在成熟的神经科学理论中找到精确的对应物：

| 你的概念 | 生物学对应 | 核心文献 |
|---------|-----------|---------|
| **自身坐标结构** | Body-centered reference frame (egocentric frame) | Colby & Goldberg 1999, parietal cortex |
| **小结构存储虚位** | Path integration / dead reckoning | O'Keefe & Nadel 1978; Hafting et al. 2005 (grid cells) |
| **运动反射脉冲 (逆向补偿)** | Efference copy / corollary discharge | von Holst & Mittelstaedt 1950; Sperry 1950 |
| **主动/被动不可区分** | Equivalence principle (inertial frame) | Einstein 1907; 前庭物理学（耳石不区分加速度来源） |
| **虚位对易脉冲** | VOR (vestibulo-ocular reflex) | Lorente de Nó 1933; Robinson 1981 |
| **生存耦合到复位** | Allostasis (通过变化维持稳定) | Sterling 2012; McEwen 1998 |
| **多层过滤** | Hierarchical motor control | Bernstein 1967; Sherrington 1906 |
| **反证/屏蔽（散度比对）** | Predictive processing / free energy | Friston 2010; Rao & Ballard 1999 |

> [!NOTE]
> 关键观察：你描述的"小结构存储虚位"与内嗅皮层的**网格细胞**（grid cells）功能惊人吻合。
> 网格细胞通过积分自体运动信号（前庭 + proprioception）来维护一个持续更新的位移估计。
> 当这个估计与实际感觉输入不匹配时，系统产生"重定位"信号——这正是你说的"反证"结构。

---

## 2. 与项目代码的缺口映射

### 2.1 已存在但为空壳的结构

```
motor_decision.py:

class SpatialNavigator:        ← 你的"自身坐标结构"
    """Path integration / spatial memory.
    BIO: hippocampal place cells + entorhinal grid cells.
    Current: PASSTHROUGH — does not track position."""
    
    def update(self, state, dt):
        pass  # ← 完全空的！
```

**SpatialNavigator** 已经存在于 [motor_decision.py](file:///d:/cell-cc/nexus_v1/circuit/motor_decision.py#L256-L284)，
且注释明确写着"future: dead reckoning via otolith integration"。
但它是一个空壳——`update()` 什么都不做。

### 2.2 假设所需但完全缺失的结构

| 假设中的结构 | 项目现状 | 影响 |
|-------------|---------|------|
| **虚位存储** | 不存在 | 有机体没有"我从哪里来"的记忆 |
| **Efference copy** | 不存在（grep 零结果） | 无法区分主动运动 vs 被动位移 |
| **复位脉冲生成器** | 不存在 | 无"回到安全位置"的驱动力 |
| **散度比对/反证** | Shadow 有 Xin 比较，但不回馈主系统 | Shadow 是只读观察者，无行为输出 |
| **稳态→复位耦合** | EnergyStore + VitalOscillator 存在，但不与空间坐标耦合 | 能量状态不影响空间决策 |

### 2.3 你的假设精确命中了 L2.09 失败的根因

L2.09 暴露：有机体是一个**无记忆的布朗运动体**。它不知道自己从哪里来，不知道"安全位置"在哪里，
不区分"我主动走开了"和"我被推开了"。

你的假设提供了**最小充分结构**让"回避"成为物理上可能：

```
当前状态:
  感受损伤 → 反馈环（微弱）→ ... → 无效（因为随机游走已逃离）

你的假设补充:
  感受损伤 → 稳态失衡 
    → 介入复位过程 
    → 复位目标 = "远离伤害源的位置"（因为虚位+损伤历史耦合）
    → 持续发送方向性脉冲（不是单发）
    → 有机体主动、持续地远离
```

---

## 3. 假设的内部一致性分析

### 3.1 强一致点

**"运动状态判断不区分主被动"** — 物理上完全正确。

前庭系统的耳石器（utricle, saccule）测量的是线性加速度，
半规管测量的是角加速度。两者都遵循等价原理：
加速度 = 加速度，无论来源是肌肉力还是外力。

项目代码也忠实反映了这一点：

```python
# variant_adapter.py L642-646
OTOLITH_GAIN = 500.0
acc = self.world.body.acceleration
mechanical_inputs['oto_x'] = acc[0] * OTOLITH_GAIN  # ← 只看加速度，不看来源
```

**"真正区分主被动的是另一个结构"** — 这就是 efference copy。

生物学中，小脑（cerebellum）接收运动指令的副本（efference copy），
与实际感觉反馈比较。匹配 = 主动运动（忽略）。不匹配 = 被动位移（报警）。
这个比较器结构是你假设中"自身坐标结构"的核心功能。

### 3.2 需要修正/澄清的点

**"左旋3s → 补充右旋3s"** — 这个表述需要区分两种情况：

1. **VOR（前庭-眼反射）式补偿**：即时的、1:1 的反向运动。
   生物学中这只存在于眼球运动（稳定视野）。
   对于身体运动，不是"补偿到原位"，而是"积分位移，更新内部坐标"。

2. **路径积分式记录**：不产生立即的反向运动，而是在内部地图上
   标记"我现在在 3s 左旋之后的位置"。只有当高阶系统决定"回去"时，
   才生成反向脉冲。

> [!IMPORTANT]
> 你后文中自己修正了这一点："这个虚位也不是一段单发的对易脉冲，
> 而是一段为达到对易状态而**持续产生**的脉冲。"
> 这个修正将概念从 VOR（即时反射）提升到路径积分（持续追踪），是正确的方向。

**"惯性力在项目中的具体表现...位移是静止的"** — 这一点目前在项目中
实际上被简化了：

```python
# world.py Body.step()
# 使用简单的 F=ma 动力学 + 粘性阻力
# 没有旋转惯性（无角动量守恒）
# "位移是静止的"在当前实现中 ≈ 阻力很快使有机体减速到零
```

制动行为（你提到的植物性反射）在生物学中对应的是：
- 前庭脊髓反射（vestibulospinal reflex）— 平衡校正
- 姿势张力维持 — 抗重力肌肉持续激活
- 这些都是"不需要学习"的 L2:SELECTION 反射，与脊髓反射同层级

### 3.3 "反证/屏蔽"结构的精确对标

你描述的"散度比对 → 缓存状态 → 调用/筛选/预测 → 学习"结构，
是 Karl Friston 的**自由能原理**（Free Energy Principle）的一个特定实现：

```
你的术语              Friston 框架
─────────────────    ─────────────────
散度比对              KL divergence minimization
缓存状态              Generative model (prior)
调用/筛选(预测)       Active inference (action selection)
停止/开始选取         Precision weighting
可学习                Belief updating
```

项目中的 **Shadow 层**本意是承担这个角色（Xin 张力 = prediction error），
但目前它是**只读的**——不回馈主系统：

```python
# shadow_sandbox.py
# STATUS: Read-only observer. Computes contraction, clustering, free energy,
# motion potential, but does NOT feed back into the main system.
```

Shadow 需要从"纯观察者"升级为"行为影响者"才能实现你描述的过滤/屏蔽功能。

---

## 4. 与 L2.09 实验数据的交叉验证

### 4.1 Flinch Test 数据支持你的假设

reflex_gain=0.0 时有机体仍然逃离——说明"逃离"来自基线游动（vital oscillator），
不来自定向反射。你的假设解释了为什么：

> 当前没有"我在哪里"的追踪 → 没有"回到安全区"的目标 →
> 反射增益无论多高都只是在随机游走上叠加微弱方向性 →
> 方向性在 7000 步后就消失了（已离开伤害区）

### 4.2 Hemorrhage Test 数据符合预期

即使 200x 代谢税，fill 只从 0.334 降到 0.288——因为暴露时间太短。
如果有了你假设中的"稳态→复位"耦合：

> 稳态失衡（fill 下降）→ 应该触发"回到高能量密度区域"的复位脉冲 →
> 但目前 EnergyStore 与空间决策**完全脱钩** →
> 有机体不知道"靠近热源 = 获取能量"

### 4.3 Fever Test 提供有趣的支持

ECM 峰值温度达到 2.53 但恢复到 0.15 — 完全可逆。
你假设中的"散度比对"结构会将这个温度脉冲记录为"状态偏移"，
但当前没有这种缓存结构，所以系统对这个经历没有任何记忆。

---

## 5. Feeding 机制完整信号链

```
┌─────────────────────────────────────────────────────────────┐
│                    FEEDING 信号链                            │
│                                                              │
│  World.heat_sources[i]                                       │
│    ├─ position: [60, 50, 50]                                │
│    ├─ radius: 20.0          ← 进食范围 = 距离 < 20          │
│    ├─ energy: 50.0          ← 热源总能量（有限，可耗尽）    │
│    └─ temperature: 5.0      ← 也是伤害来源！                │
│                                                              │
│  variant_adapter.step():                                     │
│    │                                                         │
│    ├─ CONSUME_RATE = 0.15                                   │
│    ├─ energy_absorbed = world.consume_nearby(                │
│    │      body.position, 0.15, dt=0.001)                    │
│    │                                                         │
│    │   world.consume_nearby() 内部:                         │
│    │     对每个 heat_source:                                 │
│    │       d = distance(body, source)                        │
│    │       if d < source.radius (20):                        │
│    │         proximity = 1.0 - d/20                          │
│    │         amount = 0.15 × proximity × 0.001               │
│    │         amount = min(amount, source.energy)              │
│    │         source.energy -= amount                          │
│    │         return amount                                    │
│    │                                                         │
│    │   ┌──────────────────────────────────────┐              │
│    │   │ consume_nearby 输出 vs 距离           │              │
│    │   │                                      │              │
│    │   │ d=0:  0.15 × 1.0 × 0.001 = 0.000150 │              │
│    │   │ d=5:  0.15 × 0.75 × 0.001 = 0.000113│              │
│    │   │ d=10: 0.15 × 0.5 × 0.001 = 0.000075 │              │
│    │   │ d=15: 0.15 × 0.25 × 0.001 = 0.000038│              │
│    │   │ d=19: 0.15 × 0.05 × 0.001 = 0.000008│              │
│    │   │ d≥20: 0 (超出半径)                   │              │
│    │   └──────────────────────────────────────┘              │
│    │                                                         │
│    ├─ energy_store.deposit(energy_absorbed)                  │
│    │     effective = amount × 0.9 (消化效率)                │
│    │     stored = min(effective, space, 0.05)  ← 每步上限   │
│    │                                                         │
│    └─ energy_store.tick(dt)                                  │
│          drain = 0.0001 × 0.001 = 0.0000001                 │
│          ← 基线代谢消耗                                     │
│                                                              │
│  ┌──────────────────────────────────────────────┐            │
│  │ 关键数学:                                    │            │
│  │                                              │            │
│  │ 在 d=5 处的进食收入:                         │            │
│  │   0.000113/step × 0.9效率 = ~0.000102/step   │            │
│  │                                              │            │
│  │ 基线代谢支出:                                │            │
│  │   0.0000001/step (basal_drain)               │            │
│  │   + ~0.003/step (withdraw: vascular/neural)  │            │
│  │                                              │            │
│  │ 净收支 (在热源附近):                         │            │
│  │   income ≈ 0.0001 << expense ≈ 0.003        │            │
│  │   ⟹ 进食收入 ≈ 支出的 3%                    │            │
│  │   ⟹ 即使站在热源正中心，也入不敷出！        │            │
│  │                                              │            │
│  │ 这意味着:                                    │            │
│  │   fill_fraction 的下降是不可避免的           │            │
│  │   有机体终将饿死（~160k 步后 fill→0）       │            │
│  │   接近/远离热源对 fill 的影响可忽略不计      │            │
│  └──────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

> [!CAUTION]
> **Feeding 在数学上是死代码。**
> 
> 即使有机体站在热源正中心（d=0），每步进食 = 0.000150。
> 每步支出（withdraw + basal）≈ 0.003。
> **进食收入 < 支出的 5%。**
> 
> 有机体的 fill 下降完全由 withdraw（神经代谢）驱动。
> 接近/远离热源对生存无任何影响。
> 这意味着"食物即危险"的两难困境（L2 设计的核心前提）**不存在**。

---

## 6. 综合判决

### 6.1 你的假设是正确方向

你的直觉准确地识别了项目**缺失的结构层**：

1. ✅ 自身坐标系统 (SpatialNavigator) — 存在但为空壳
2. ✅ 虚位/路径积分 — 完全缺失
3. ✅ Efference copy — 完全缺失
4. ✅ 稳态×空间耦合 — EnergyStore 与位置决策脱钩
5. ✅ 散度比对/预测 — Shadow 是只读的
6. ✅ 多层过滤 — DirectionSelector 是空壳

### 6.2 但实现之前有一个更基础的问题

> [!WARNING]
> **feeding 是死代码这个事实比任何架构缺失都更致命。**
> 
> 如果有机体的生存不取决于它在空间中的位置（因为进食收入 << 代谢支出），
> 那么无论你建了多精美的坐标系统 + 复位机制，有机体都没有**热力学动机**
> 去偏好任何位置。
> 
> 在实现你的假设之前，必须先让 feeding 成为生存的**必要条件**：
> - 调整 CONSUME_RATE 使得"在热源附近" ≈ 收支平衡
> - 调整 withdraw 或 basal 使得"远离热源" = 确定死亡
> - 只有这样，"接近热源获取能量"才成为真实的生存压力

### 6.3 用语修正建议

| 你的用词 | 建议修正 | 理由 |
|---------|---------|------|
| "对易" | **对抗/补偿** (compensatory) | "对易"暗示精确的群论对称，你描述的更接近"反向补偿" |
| "虚位" | **路径积分位移** (integrated displacement) | "虚位"可能与"虚拟位移"（virtual displacement, 拉格朗日力学）混淆 |
| "散度比对" | **预测误差** (prediction error) 或 **KL 散度** | 如果你指的是分布之间的差异，KL 散度是精确术语 |

---

## 7. 建议的实施优先级

```
优先级 0: 修复 feeding（无此则一切无意义）
  ├─ CONSUME_RATE ×10~50
  ├─ 或降低 withdraw 基线
  └─ 验证: 近源 fill 稳定，远源 fill 下降

优先级 1: 激活 SpatialNavigator（路径积分）
  ├─ 积分 otolith acceleration → 位移估计
  ├─ 维护内部坐标 [x, y, z]
  └─ 这是你假设中"自身坐标结构"的最小实现

优先级 2: 实现 efference copy
  ├─ motor_command → 小脑副本
  ├─ 比较 predicted_displacement vs actual_displacement
  └─ 差异 = exafference（外力位移）

优先级 3: 稳态 × 空间耦合
  ├─ EnergyStore.fill_fraction → 空间决策权重
  ├─ fill 低 → "回到高收入区域"压力增加
  └─ 这是你假设中"生存耦合到复位"

优先级 4: Shadow 回馈
  ├─ Shadow 预测误差 → DA → STDP 方向性调制
  └─ 这是你假设中"反证/屏蔽"的实现
```
