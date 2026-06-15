> **导航**: [[00_Dashboard/核心词条索引]] · [[00_Dashboard/理念架构图]]

# 损伤影响机制：架构设计探讨

---

## 〇、议题总览

| # | 议题 | 性质 |
|---|------|------|
| 1 | 热源路线选择：梯度统一体 vs 分离对象 | 架构决策 |
| 2 | 第二主体构建方法论：染色标注体系 | 元层框架 |
| 3 | 脊髓反射的皮层抑制占位链路 | 未来预建 |
| 4 | 环境温度→ECM的简化桥接 | 物理捷径 |
| 5 | 具体实现方案 | 工程计划 |

---

## 一、热源路线选择

### 路线1：梯度统一体（推荐）

```
           HeatSource
        (单一物理对象)
              │
    ┌─────────┼─────────┐
    │         │         │
   远端     中端      近端
  (温暖)   (适宜)   (灼伤)
   │         │         │
  感知     进食     损伤
```

**物理根据**：深海热液喷口就是同一个对象。距离远时是温暖的引导信号，距离近时是致死的高温区域。没有两种不同的"热泉"——有的只是温度梯度的不同区间。

**当前代码已内置此结构**：

```python
# world.py L374-375：线性衰减场
T += src.effective_temperature() * (1.0 - d / src.radius)
```

距离 d=0 时 T = T_effective（最高温，潜在灼伤区）。距离 d≈radius 时 T≈0（微弱感知区）。中间是连续梯度。

**需要做的唯一改变**：当前 `temperature` 参数范围是 2.5~6.0。SkinPatch 的 `damage_threshold` = 3.0。这意味着只有在**非常接近**高温源（d < r × (1 - 3.0/T_eff)）时才触发损伤。这个关系已经是内蕴的——不需要新对象类型。

**优势**：
- 最小改动，不需要新类
- 保持 World 的物理统一性（一个温度场，一组方程）
- Consume_nearby 的接近度曲线自然与损伤曲线重叠（越近→进食效率越高，但同时损伤越大）
- **这就是生物面临的真实权衡**：嗜热菌必须在热效率最优点与组织损伤阈值之间找到平衡

### 路线2：分离对象

```
   FoodSource ────── DangerSource
    (可食用)          (纯危险)
```

**缺点**：
- 需要新类 `DangerSource`，修改 World 的温度场叠加逻辑
- 学习问题：两种完全不同的物理对象需要系统学会在感知层面区分它们——但目前只有 **标量温度传感器**（ThermalMembrane + SkinPatch），无法区分 "来自食物的温暖" 和 "来自危险的温暖"
- 违背了"同一物理现象的不同区间"这个更朴素的自然原则
- 如果走这条路，等于在 World 层面引入了一个**语义标签**（这是食物/这是危险），而非让系统从梯度中自行发现

> [!IMPORTANT]
> **结论：推荐路线1**。梯度统一体完全不需要新的对象类型。SkinPatch.damage_threshold 已经隐式地将温度场划分为了安全区和损伤区。缺失的不是感知划分，而是**损伤到体征的闭合反馈**。

---

## 二、第二主体构建方法论：染色标注

### 三层主体分类

你提出的区分极为关键。我将它形式化为三层：

| 层 | 名称 | 性质 | 来源 | 代码标注 |
|----|------|------|------|----------|
| L0 | 物理层 | 热力学、牛顿力学 | 自然法则 | 无标注（默认） |
| L1 | 第一主体 | 自发运动、环流 | 物理组件组装后涌现 | `# L1:EMERGENT` |
| L2 | 第二主体 | 损伤回避、觅食优化 | **人工进化选择**（设计者注入的约束） | `# L2:SELECTION` |

**L2 的本质**：

在生物体中，"烫了就跑"是亿万年自然选择固化下来的——把 TRPV1→脊髓→运动神经元的突触权重"焊死"到了基因组中。我们没有亿万年。我们做的是**人工进化选择**：

1. 我们**选择**了 `damage_threshold = 3.0`（等价于选择了一个"有害"的物理定义）
2. 我们**设计**了 damage → 体征衰退的因果链（等价于自然选择固化了反射弧）
3. 我们**预设**了这条链路的增益和时间常数（等价于自然选择调谐了通道蛋白参数）

这些是**带价值判断的设计决策**——它们定义了"什么对有机体是有害的"。这不是L1层能涌现出来的，因为在没有物理后果的情况下，系统不知道高温是"坏的"。

### Prigogine 耗散结构等价

```
生物进化:  随机突变 → 自然选择 → 固化(基因组)
           ↓
           耗散结构: 远离平衡态 → 分岔 → 有序化

项目设计:  架构探索 → 人工选择 → 固化(代码硬连线)
           ↓
           等价结构: 设计者注入约束 → 系统在约束下涌现行为
```

关键洞见：**L2 是L1的"进化压力"**。我们不直接编码"逃跑"行为（那是L1层的语义注入），而是注入**物理后果**（damage → 心跳减弱、代谢增加），让L1层的环流耦合学习机制在这些约束下涌现出回避行为。

### 代码染色约定

```python
# L2:SELECTION — Damage threshold (artificial evolutionary choice)
# BIO: TRPV1 activation at 43°C (evolved, not learned)
# DESIGN: We choose 3.0 as the harm boundary in normalized thermal units.
# This is a VALUE JUDGMENT encoded as a physical parameter.
damage_threshold: float = 3.0
```

```python
# L2:SELECTION — Damage → metabolic cost (artificial evolutionary wiring)
# BIO: tissue repair requires ATP (thermodynamic necessity)
# DESIGN: We wire damage_integral into EnergyStore.basal_drain.
# This forces the circulation to "discover" that staying near high-T = costly.
# The avoidance behavior itself is NOT designed — it must EMERGE from L1.
damage_drain_rate: float = 0.005
```

> [!TIP]
> 每个 `L2:SELECTION` 标注应包含：
> 1. **BIO**: 对应的生物学机制
> 2. **DESIGN**: 设计者做出的选择是什么
> 3. **EMERGE**: 期望从L1涌现的行为是什么

### 对未来主体构建的意义

L2标注体系的价值不仅是文档化。它建立了一个**元模式**：

```
[新模态/新主体的构建步骤]
1. 定义物理后果（L2:SELECTION）
   → 什么是"有害的"？什么参数被消耗/衰退？
2. 硬连线到体征层（L2:SELECTION）  
   → 有害的后果如何影响核心循环？
3. 观察涌现行为（L1:EMERGENT）
   → 系统是否学会了回避？学会了多快？鲁棒吗？
4. 迭代调谐（L2:SELECTION参数调整）
   → 阈值、增益、时间常数是否合适？
```

这个模式对任何未来模态（光感、化学梯度、社交信号……）都是通用的。

---

## 三、脊髓反射的皮层抑制占位链路

### 生物学原型

```
[感觉输入] ──→ [脊髓中间神经元] ──→ [运动神经元] ──→ 肌肉收缩
                      │                                (反射)
                      │
               [下行皮层纤维] ←── [前额叶/运动皮层]
                      │
                   抑制性调制
              (我知道是热的，但我要拿)
```

Gate Control Theory (Melzack & Wall, 1965)：脊髓背角的闸门神经元可以被高级中枢调制，选择性地抑制或增强伤害感受信号的传递。

### 项目中的占位设计

```python
# 反射路径（现在激活）：
noci_signal ──→ [REFLEX_GATE] ──→ Motor直接注入
                    │
               gate_voltage ← 默认: VDD (全开)
                    │
               [未来: 皮层信号注入点]
                    ↓
               MOSFET.conduct(noci, gate=gate_voltage)

# 等价电路：
#   noci ──→ MOSFET(gate=cortex_inhibition) ──→ Motor
#
#   当 cortex_inhibition = VDD → gate全开 → 反射正常工作
#   当 cortex_inhibition = 0   → gate关闭 → 反射被抑制
#   中间值 → 部分抑制（"忍痛"）
```

**实现**：使用一个 MOSFET 作为闸门。默认 gate=VDD（全开放），反射正常执行。预留一个 `cortical_inhibition` 注入接口，未来的皮层模块可以向 gate 注入负电流来关闭反射。

```python
class SpinalReflexArc:
    """L2:SELECTION — Nociceptor-to-Motor reflex pathway.
    
    Hardwired (not learned) pathway from nociception to motor activation.
    BIO: Aδ-fiber → spinal interneuron → α-motor neuron.
    
    The gate MOSFET provides a future injection point for cortical
    inhibition (Gate Control, Melzack & Wall 1965).
    Currently: gate = VDD (fully open, reflex always executes).
    Future: cortical module injects negative current → gate closes.
    """
    def __init__(self):
        self._gate = MOSFET(v_threshold=0.1, gm=2.0)  # reflex amplifier
        self._gate_voltage = 1.0   # default: VDD = fully open
        # ↑ PLACEHOLDER: cortical module will modulate this
    
    def process(self, noci_signals: dict, dt: float) -> dict:
        """Convert nociceptor activations to directional motor drive.
        
        Returns per-axis motor current (signed, directional).
        """
        # Gate modulation (future cortical override)
        gated_gain = self._gate.conduct(self._gate_voltage)
        
        # Directional computation from spatial nociceptor pattern
        # front_noci > back_noci → flee backward (negative x)
        # left_noci > right_noci → flee right (negative y)
        ...
        
        return motor_drives
```

> [!NOTE]
> 这个设计的关键是**物理的**：MOSFET的gate电压是一个真实的模拟量，不是布尔开关。皮层可以"部分抑制"反射（忍痛），而不仅仅是全开/全关。这符合生物现实。

---

## 四、环境温度 → ECM 的简化桥接

### 完整物理链路（不建议实现）

```
环境热源 → 流体介质(水) → 体表(SkinPatch) → 组织(结缔组织) 
    → 细胞间液(ECM) → 细胞膜 → 离子通道动力学改变
```

要完整建模这条链路需要：流体动力学（Navier-Stokes）、热扩散方程（∂T/∂t = α∇²T）、多层组织模型。**远超项目范围**。

### 推荐捷径：damage_integral 作为屏障突破代理

```
SkinPatch.damage_integral > 0
         ↓
    "皮肤屏障已被热穿透"
         ↓
    ECM._temperature += f(damage_integral) × dt
```

**物理理据**：
- SkinPatch 的 damage_integral 是组织蛋白质变性的Arrhenius累积
- 蛋白质变性 = 组织结构被破坏 = 屏障失效
- 屏障失效 → 环境热量直接渗入深层组织
- 这是一个合理的简化：只有当损伤发生时，外部热才能穿透到内部

**等价模型**：

```python
# L2:SELECTION — Environmental heat breach via tissue damage
# BIO: Burns destroy dermal barrier → deep tissue thermal injury
# PHYS: Damaged insulator → thermal resistance drops → heat flows in
# DESIGN: damage_integral acts as inverse thermal resistance.
# No damage → ECM fully insulated from environment.
# High damage → ECM directly exposed to environment temperature.

breach_factor = damage_integral / (damage_integral + K_BARRIER)
# K_BARRIER: half-saturation constant. At damage=K, 50% of env heat reaches ECM.
# Michaelis-Menten form ensures bounded response (never > 1.0).

heat_breach = breach_factor * (T_skin - ecm.temperature) * BREACH_CONDUCTANCE
ecm._temperature += heat_breach * dt
```

这个简化满足：
1. **无损伤时完全隔离**（breach_factor → 0）
2. **损伤越大穿透越多**（单调递增）
3. **饱和行为**（不会无限穿透）
4. **热力学方向正确**（热从高温流向低温）
5. **不需要流体力学**

---

## 五、具体实现方案

### 总体架构：三条反馈闭环

```
                    SkinPatch.damage_integral
                            │
              ┌─────────────┼─────────────┐
              ↓             ↓             ↓
        [反馈环A]      [反馈环B]      [反馈环C]
         心跳衰减      代谢消耗       脊髓反射
              │             │             │
    VitalOsc.amplitude  EnergyStore    Motor直接驱动
         衰减因子       额外drain      (带方向)
              │             │             │
    搏动减弱→体征    能量下降→        ← [REFLEX_GATE]
    环流受影响        饥饿→体征变化      ↑ (皮层占位)
```

---

### 反馈环A：damage → VitalOscillator 幅度衰减

**物理对应**：组织损伤 → 心肌功能受损 → 心输出量下降

**实现位置**：[variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) 的 vital_oscillator.step() 调用处

```python
# L2:SELECTION — Tissue damage depresses vital oscillation
# BIO: Burn injury → systemic inflammatory response → cardiac depression
#      (Horton 2003, "Hypovolemic shock in burn patients")
# DESIGN: max(damage) across all patches → amplitude suppression factor
# EMERGE: System should learn that proximity→damage→vital_drop is costly
max_damage = max(patch_temps[pid][2] for pid in patch_temps)
# Suppression: sigmoid decay. At damage=0 → factor=1.0. At damage=5 → factor≈0.27
vital_damage_factor = 1.0 / (1.0 + max_damage * 0.5)

# Apply to vital oscillator output AFTER step()
vital_outputs = [v * vital_damage_factor for v in vital_outputs]
```

**因果链**：
```
高温→damage↑ → vital_outputs↓ → Motor膜注入电流↓ → 搏动减弱
    → 运动能力下降 → 探索减少 → 进食减少 → energy↓ → 更多体征下降
```

---

### 反馈环B：damage → EnergyStore 额外代谢消耗

**物理对应**：组织修复需要ATP，损伤修复是高代谢过程

**实现位置**：[variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) 的 energy_store.tick() 调用处

```python
# L2:SELECTION — Tissue repair metabolic cost
# BIO: Wound healing consumes 20-50% additional metabolic energy
#      (Arnold & Barbul 2006, "Nutrition and Wound Healing")
# DESIGN: damage_integral → additional energy drain from EnergyStore
# This creates thermodynamic pressure: damage costs real energy.
# EMERGE: System should learn to avoid states that increase drain.
REPAIR_ENERGY_RATE = 0.005  # energy per unit damage per dt

total_damage = sum(patch_temps[pid][2] for pid in patch_temps)
repair_cost = total_damage * REPAIR_ENERGY_RATE * dt
if repair_cost > 0:
    energy_store.withdraw(repair_cost)
```

**因果链**：
```
高温→damage↑ → repair_cost↑ → energy↓ → fill_fraction↓
    → vital_amplitude↓ → 搏动减弱
    → delivery_factor↓ → 神经元能量供应↓ → 活动↓ → 学习↓
```

---

### 反馈环C：Nociceptor → 定向运动反射弧

**物理对应**：伤害感受 → 脊髓反射 → 定向撤退

**这是唯一的"硬连线"路径**——不需要学习，从第一步就能执行。

**方向性计算**：利用4个SkinPatch的nociceptor活性差异计算逃离方向。

```python
# L2:SELECTION — Spinal nociceptive withdrawal reflex
# BIO: Aδ/C-fiber → spinal interneuron → contralateral flexor motor neuron
#      Reflexive withdrawal AWAY from noxious stimulus.
#      Sherrington 1906: "flexion reflex", hardwired at birth.
# DESIGN: Spatial nociceptor contrast → directional motor current.
#         Front_noci > Back_noci → flee backward (−x motor drive).
#         Uses existing SkinPatch spatial arrangement.
# EMERGE: None — this is L2 hardwired, not learned.
#         But cortical override (future) CAN suppress it.

noci_out = self.somatosensory.get_output()
front_noci = noci_out.get("front", {}).get("noci_activation", 0.0)
back_noci  = noci_out.get("back", {}).get("noci_activation", 0.0)
left_noci  = noci_out.get("left", {}).get("noci_activation", 0.0)
right_noci = noci_out.get("right", {}).get("noci_activation", 0.0)

# Directional contrast → signed motor drive
# (flee away from higher nociception)
REFLEX_GAIN = 0.5
reflex_x = (back_noci - front_noci) * REFLEX_GAIN  # front hot → go back
reflex_y = (right_noci - left_noci) * REFLEX_GAIN   # left hot → go right

# Gate modulation (PLACEHOLDER for cortical override)
# L2:SELECTION — Default: gate fully open. Future: cortical injection.
gate_open = self._reflex_gate_voltage  # default 1.0

if 'move_x' in self.motor_neurons:
    self.motor_neurons['move_x']._membrane.inject(
        reflex_x * gate_open, dt)
if 'move_y' in self.motor_neurons:
    self.motor_neurons['move_y']._membrane.inject(
        reflex_y * gate_open, dt)
```

---

### 反馈环D（可选）：damage → ECM 热突破

```python
# L2:SELECTION — Barrier breach: tissue damage allows environmental heat into ECM
# Only activates when damage > 0 (skin barrier compromised)
max_damage = max(patch_temps[pid][2] for pid in patch_temps)
if max_damage > 0.01:
    K_BARRIER = 2.0  # half-saturation
    breach = max_damage / (max_damage + K_BARRIER)
    # Find hottest skin patch temperature
    max_skin_T = max(patch_temps[pid][0] for pid in patch_temps)
    for ecm in [self.ecm_vestibular, self.ecm_encoding, self.ecm_column]:
        heat_in = breach * (max_skin_T - ecm.temperature) * 0.1
        if heat_in > 0:
            ecm._temperature += heat_in * dt
```

---

## 六、完整因果链（实现后）

```
         World.heat_source (距离→温度梯度)
                    │
         ┌──────────┼──────────┐
         ↓          ↓          ↓
   远端(安全)   中端(进食)   近端(灼伤)
   T < 1.0     1.0 < T < 3.0   T > 3.0
         │          │          │
    感知/学习    consume    SkinPatch.damage ↑
         │       nearby         │
    Noci(dT/dt)    │    ┌───────┼───────────┐
         │    EnergyStore   │       │           │
    extra_axes  deposit  反馈A   反馈B       反馈C
         │         │    Vital↓  Energy↓    Motor定向
    Enc→Col     搏动  心跳减弱 修复消耗     ← [GATE]
         │    输出                              ↑
    大环流                                   (皮层占位)
         │
   ╔═════════════════════════════════════════╗
   ║  体征受损 → 环流流量变化 → DA变化        ║
   ║  → 突触权重调整 → 运动模式改变           ║
   ║  → 涌现行为: 学会在安全距离进食          ║
   ║                                         ║
   ║  L1:EMERGENT (从L2约束中涌现)           ║
   ╚═════════════════════════════════════════╝
```

---

## 七、待决问题

> [!IMPORTANT]
> 1. **路线确认**：路线1（梯度统一体）是否接受？
> 2. **反馈环D（ECM热突破）**：是否在第一轮实现？还是先做A/B/C，观察涌现效果后再决定？
> 3. **REFLEX_GAIN 校准**：反射增益需要实验标定。太大→永远逃跑（无法进食），太小→反射无效。建议初始0.5，后续EXP调整。
> 4. **染色标注格式**：`# L2:SELECTION` 是否满足需要？是否需要在文档层面（TRACKER, SERIAL_DEPENDENCIES）也引入 L0/L1/L2 分类？

---

## 八、实现文件清单

| 文件 | 改动 | 性质 |
|------|------|------|
| [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) | 添加反馈环A/B/C + 反射门 | L2:SELECTION |
| [vital_oscillator.py](file:///d:/cell-cc/nexus_v1/components/vital_oscillator.py) | 添加 `damage_factor` 外部调制接口 | 接口扩展 |
| [energy_store.py](file:///d:/cell-cc/nexus_v1/components/energy_store.py) | 无改动（已有 withdraw） | — |
| [world.py](file:///d:/cell-cc/nexus_v1/components/world.py) | 无改动（SkinPatch.damage 已存在） | — |
| [ecm.py](file:///d:/cell-cc/nexus_v1/components/ecm.py) | 可选：添加 breach 注入方法 | 反馈环D |
| 新文件：`components/spinal_reflex.py` | 反射弧封装 + MOSFET闸门 | L2:SELECTION |
