# 有害热源 → 体征 → 环流：因果链路完整追踪

---

## 一、真实生物的链路（对比基线）

```
有害热源 → 组织温度升高 → 蛋白质变性 → 伤害感受器放电 → 脊髓反射 → 逃跑
                              ↓                                  ↓
                        代谢紊乱/炎症           同时: 丘脑→皮层→痛觉
                              ↓
                        心率↑, 呼吸↑, 交感激活 (体征改变)
                              ↓
                        应激激素(肾上腺素/皮质醇)→ 全身代谢重分配
```

关键特征：
1. **组织损伤是物理过程** — 蛋白质在43°C开始变性（Arrhenius动力学）
2. **伤害感受与温度感受是不同通道** — C纤维/Aδ纤维 vs TRPM8
3. **反射回路是硬连线的** — 不需要学习即可逃跑
4. **体征受应激影响** — 心率、代谢率、激素水平都改变

---

## 二、项目中的实际链路（源码追踪）

### 链路1：环境温度 → SkinPatch 物理热动力学

```
World.temperature_at(pos) ─→ T_env
        ↓
SkinPatch.step_thermal()
    q_dot = conductance × (T_env - T_skin)      ← Fourier热传导
    dT_skin = q_dot / C_thermal × dt
    T_skin 更新                                   ← 有惯性，不是瞬时
        ↓
    if T_skin > damage_threshold(3.0):
        damage_integral += (T_skin - 3.0) × dt   ← Arrhenius组织损伤累积
    else:
        damage_integral -= heal_rate × dt         ← 慢修复
```

> [!IMPORTANT]
> **SkinPatch 是物理热质量**，不是理想温度计。τ_skin = C/k = 10/2 = 5步。快速通过热源几乎不升温（热惯性），持续暴露才累积损伤。这是正确的。

**源码**：[world.py SkinPatch](file:///d:/cell-cc/nexus_v1/components/world.py#L69-L197)

---

### 链路2：SkinPatch → 体感链 → 神经信号

```
Body.sample_skin() → {patch_id: (T_skin, dT_skin, damage_integral)}
        ↓
SomatosensoryChain.step(patch_temps)
        ↓
    ┌─ Thermoreceptor ← T_skin (DC/tonic，慢积分，τ=100ms)
    │       BIO: TRPV3/TRPM8
    │
    ├─ Nociceptor ← |dT| × NOCI_DT_GAIN(200) + damage × 10.0 (AC/phasic，τ=1ms)
    │       BIO: TRPV1 C-fibers，裸神经差分器
    │       v_peak=0.01 → 极低阈值，能从搏动微运动产生的dT/dt放电
    │
    └─ Relay ← Thermo + Noci - 侧向抑制 (相邻patch互抑)
            BIO: 脊髓背角WDR神经元
```

> [!NOTE]
> Nociceptor 有**双通道输入**：
> - **通道A**（dT/dt）：热梯度的时间变化率 → 接近热源时就放电（无需组织损伤）
> - **通道B**（damage_integral）：累积组织损伤 → 只有T_skin > 3.0后才有
>
> 这是EXP-016的修复：原来只用damage_integral（在安全距离=0），导致nociceptor永远沉默 → DA塌陷 → "温水煮蛙"。

**源码**：[somatosensory/chain.py L288-333](file:///d:/cell-cc/nexus_v1/somatosensory/chain.py#L288-L333)

---

### 链路3：体感输出 → 主回路 → 环流

```
SomatosensoryChain.get_mechanical_inputs()
    → { therm_front: relay.ema, dtherm_front: noci.ema, ... }
        ↓
mechanical_inputs[key] = val    ← 注入到Hebbian的extra_axes
        ↓
VestibularChain + extra_axes → Met → HC → Aff → Enc → Col → Motor
                                                        ↓
                                              Col.ema → BindingCell
                                                        ↓
                                              Bind → Motor → FBCap → Col (环流)
```

**体感信号如何影响环流**：体感relay的activation进入Encoding层，通过 Enc→Col 的STDP束传播到Column层。Column层的ema参与**大环流路径**：

```
Col.ema → BindingLayer → Motor → FBCap → Col (负反馈)
```

> [!WARNING]
> 体感信号对环流的影响是**间接的、学习依赖的**。它必须通过Enc→Col的权重才能影响Col激活，进而影响环流流量。如果这些权重还没学好，热信号对环流的影响为零。

---

### 链路4：温度 → CirculationProportion → DA → 学习

```
ThermalMembrane._prev_T - ThermalMembrane._methylation
    = thermal_err
        ↓
thermal_stability = 1.0 / (1 + thermal_err × 10)     ← 热稳定性指标
        ↓                                                 高稳定=安静，低=偏离
CirculationProportionCircuit.step(thermal_stability, body_speed, feed_alignment)
    Cap_homeo.inject(thermal_stability)               ← 积分到电容
    Cap_motor.inject(body_speed)
    Cap_feed.inject(feed_alignment)
        ↓
    ρ_homeo = V_homeo / V_total                       ← 三比例
    deviation = |0.7 - ρ_homeo|                       ← 偏差
        ↓
    da_current = MOSFET.conduct(deviation)            ← 超过阈值→DA电流
        ↓
    DA neurons ← inject(da_current)                   ← 直接注入DA膜
        ↓
    dopamine.concentration ↑                          ← 影响全局学习率
```

> [!IMPORTANT]
> **热源通过thermal_stability影响的是环流比例的"稳态通道"(ρ_homeo)，不是体征本身**。
>
> 这里的逻辑是：
> - 热源附近 → `thermal_err`大 → `thermal_stability`低 → `ρ_homeo`下降
> - `ρ_homeo`下降 → deviation↑ → DA↑ → 学习率增强
> - 同时 deviation > 0.1 → 直接注入Motor膜电流 → 运动

**源码**：[variant_adapter.py L662-722](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py#L662-L722)

---

### 链路5：热源 → ECM温度 → 通道动力学（内部代谢热）

```
Σ neuron.heat_output → ECM.step(heat_inputs)
    dT_ecm = (Q_neural - G×ΔT) / C_thermal           ← 内部产热
        ↓
ECM.temperature_effect_on_tau(τ_base)
    τ_corrected = τ_base / Q10^(ΔT/10)               ← Q10效应
        ↓
    温度↑ → τ↓ → 通道加速 → 放电加快 → 更多产热 → 正反馈?
        ↓
VascularCooling.step(tissue_temp) → 散热                ← 负反馈闭环
```

> [!NOTE]
> ECM温度来自**神经元自身活动的产热**，不是直接来自World的环境温度。环境温度通过SkinPatch→神经信号→活动→产热的**间接路径**才到达ECM。

---

## 三、关键缺口分析

### ❌ 缺口1：组织损伤(damage_integral)没有回到体征/环流

```
SkinPatch.damage_integral → Nociceptor (通道B, gain=10.0)
                          → 然后... 就没了
```

在生物体中，组织损伤会引起：
- 心率增加（交感激活）→ **项目的VitalOscillator没有受damage影响**
- 代谢增加（应激反应）→ **EnergyStore的基础代谢率是常数**
- 炎症（PGE2等）→ **ECM没有炎症机制**

**damage_integral 只影响nociceptor的输入**，不影响：
- VitalOscillator（搏动频率/幅度不变）
- EnergyStore（代谢消耗不变）
- ECM（无炎症/肿胀效应）
- CirculationProportion（无组织应激通道）

### ❌ 缺口2：没有硬连线的撤退反射

生物的伤害回避是**脊髓级反射**——不需要经过大脑、不需要学习。手碰到热锅，在感到痛之前手已经缩回来了。

项目中，Motor的运动必须通过：
```
Noci → Relay → extra_axes → Enc → Col → Motor (via STDP bundles)
```
这是一条**需要学习的路径**。初始权重下，nociceptor的放电不一定能驱动有效运动。

唯一的"非学习"路径是 C.04 deviation → Motor direct activation：
```python
if deviation > 0.1:
    motor_drive = (deviation - 0.1) * DEVIATION_MOTOR_GAIN
    for mot in self.motor_neurons.values():
        mot._membrane.inject(motor_drive, dt)
```
但这个路径**不区分方向**——它只是增大所有motor的膜电压，不能产生"远离热源"的定向运动。

### ❌ 缺口3：环境温度不直接作用于ECM

ECM温度来源是 `neuron.heat_output`（内部代谢热），而不是环境热源。生物体中，如果整个身体泡在热水里，组织温度直接上升，离子通道加速，可能导致离子失衡甚至癫痫。

项目中的链路是：
```
环境热 → SkinPatch.T_skin → 神经信号 → 活动 → heat_output → ECM温度
```
中间隔了好几个间接步骤。

### ✅ 正确的部分

| 机制 | 状态 | 说明 |
|------|------|------|
| SkinPatch Fourier热传导 | ✅ | 有热惯性、有时间延迟 |
| Nociceptor双通道(dT/dt + damage) | ✅ | EXP-016修复后能探测热梯度 |
| ThermalMembrane甲基化适应 | ✅ | 只检测变化，不检测绝对温度 |
| CirculationProportion热稳定性 | ✅ | 偏差→DA→学习调制 |
| C.04 Deviation→Motor | ✅ | 非学习的直接运动驱动 |
| SkinPatch damage_integral | ✅ | Arrhenius累积 + 自修复 |

---

## 四、总结：项目中的"有害热源"因果链

```
                    World.heat_source (高温区域)
                            │
                ┌───────────┼───────────┐
                ↓           ↓           ↓
         SkinPatch     ThermalMembrane  Body.position
          (物理热传导)    (甲基化适应)     (距离决定温度)
                │           │
        ┌───────┴──────┐    │
        ↓              ↓    ↓
  Thermoreceptor   Nociceptor   thermal_stability
   (DC tonic)      (AC phasic)      │
        │              │            │
        └──────┬───────┘     CirculationProportion
               ↓                    │
           SomaRelay          ┌─────┴──────┐
               │              ↓            ↓
         extra_axes     deviation     ρ_homeo↓
               │         > 0.1         → DA↑
         Enc → Col    Motor直接        → lr↑
               ↓       注入(无方向)
            大环流
       Col→Bind→Mot→FB→Col

    ═══════════════════════════════════════════
              体征影响 = 零
         VitalOsc: ❌ 频率/幅度不受损伤影响
         EnergyStore: ❌ 代谢率不受损伤影响
         ECM: ❌ 无炎症/无环境热直接传入
    ═══════════════════════════════════════════
```

## 五、本质问题

项目把热源同时定义为**食物和危险**。在当前设计中：

- **热源=食物**的路径是完整的：`consume_nearby → EnergyStore → VitalOsc → 生存`
- **热源=危险**的路径是**残缺的**：只有感知层（SkinPatch、Nociceptor）存在，但从感知到**体征改变**和**定向回避**的链路没有闭合。

生物的解决方案是**进化固化的反射弧** + **应激轴**（HPA axis）。项目没有这两者的等价物。

> [!CAUTION]
> 当前的有机体不是"害怕高温然后逃跑"——它是一个**嗜热菌**，靠近热源是为了吃东西。"逃跑"必须从**环流耦合学习**中涌现：在热源附近停留太久 → 某种负面信号 → 学到"过度接近=不好"。
>
> 但这个负面信号是什么？目前唯一的候选是：
> - `thermal_stability↓ → deviation↑ → DA↑` （但DA是学习增强信号，不是惩罚信号）
> - `damage_integral↑ → noci放电↑ → ...` （但这条路径不闭合到体征）
>
> 也就是说：**有害热源在当前系统中没有"有害"的物理后果**。它只是让thermal_stability下降、DA上升。

如果要让"过度接近热源=有害"成为系统能自主学到的东西，需要 damage_integral → 体征的物理闭合链路，例如：

1. `damage_integral → VitalOsc.amplitude 衰减` （组织受损→心功能下降）
2. `damage_integral → EnergyStore.basal_drain 增加` （修复组织需要能量）
3. `damage_integral → ECM.temperature 直接注入` （炎症产热）

这些都是**物理的、非语义的**反馈，符合"拒绝语义标签，坚守热力学锚定"的原则。
