# Nexus v1 阶段性审计报告

> 2026-06-25 — 基于 EXP-023（500k 步长期验证）全程数据

---

## 一、已证明的事实

### 1.1 趋热行为存在

生物体确实能朝热源移动。Run3 数据中 `dist`（到最近热源的距离）呈现反复接近-远离的振荡模式，而非随机漫步：

| 步段 | dist | 行为 |
|------|------|------|
| 10k | 7.8 | 接近热源 |
| 20k | 37.4 | 远离 |
| 80k | 13.0 | 再次接近 |
| 230k | 15.3 | 接近 |

但需要注意：**这不是从 L1 涌现的**。趋热性的主要驱动是 L2 硬编码的 `spinal_reflex.process_hunger()`（[variant_adapter.py:790-796](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py#L790-L796)），它直接读取 thermoreceptor 空间对比度并注入 motor 电流，由 hunger（fill_fraction）门控。

### 1.2 STDP 权重分化

Col→Motor 突触束在 500k 步中发生了可测量的权重变化：

```
col_pitch_to_move_y: 0.50 → 0.44  (Δ = -0.06)
col_roll_to_move_z:  0.50 → 0.32  (Δ = -0.18)
col_yaw_to_move_x:   0.50 → 0.44  (Δ = -0.06)
```

学习确实在发生，束之间的权重分化超过了 C4 标准（max Δw > 0.05）。

### 1.3 DA 系统运作

结构化 VTA 回路（3 个 DA 神经元 + D2 自受体）正常运作：
- DA 从初始的 1.0 冷启动值衰减到稳态 ~0.025
- D2 自受体负反馈防止了 DA 饱和
- DA 浓度对运动和学习有可测量的调节作用

### 1.4 AGC 响应

自动增益控制在能量不足时激活（AGC peak = 5.0），表明 homeostatic 回路能检测到生理赤字并做出响应。

---

## 二、未证明的事实

### 2.1 代谢自持性 ❌

**C1（fill > 0 throughout）从未通过。** 三次 500k 运行：

| Run | max_deposit | fill=0 次数 | 结局 |
|-----|-------------|-------------|------|
| Run1 | 0.05 | 持续下降 | fill 0.50→0.155，P_net=-6.9e-4 |
| Run2 | 0.08 | ≥1 次 | fill=0 @350k |
| Run3 | 0.12 | ≥2 次 | fill=0 @60k, 170k；@270k 再次危机 |

提高 max_deposit 没有解决问题。

### 2.2 L1 涌现的趋热性 ❌

当前的趋热行为依赖 L2 硬编码反射弧。L1 层面的 STDP 学习虽然在发生，但：
- 权重变化方向是否合理（向趋热方向分化）未经验证
- 如果移除 L2 hunger reflex，纯靠 STDP 权重能否产生趋热行为——未测试

### 2.3 长期正能量平衡 ❌

全局 P_net 在不同时间窗口表现不一致：
- 正常时段：P_net ≈ +0.03-0.07/step（健康）
- 烧伤时段：P_net ≈ -0.05 到 -0.10/step（崩溃）

系统在"安全进食区"和"烧伤区"之间振荡，无法稳定在正平衡。

---

## 三、根因分析 — Metabolic Wall 的确切原因

### 3.1 方法

通过 **仪器化追踪** `EnergyStore.withdraw()` 的每一个调用站点，将能量消耗精确归因到子系统。

### 3.2 发现

| 消耗源 | 代码位置 | 正常/step | **危机/step** |
|--------|---------|-----------|-------------|
| 🔴 **组织修复 (Loop B)** | [variant_adapter.py:739](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py#L737-L739) | 0.001 | **0.095** |
| Vascular delivery | [variant_adapter.py:1311](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py#L1311) | 0.004 | 0.004 |
| Vital oscillator | vital_oscillator.py:195 | 0.003 | 0.003 |
| DA neuron refill | [variant_adapter.py:1088](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py#L1088) | 0.003 | 0.003 |
| Basal drain | energy_store.py tick() | 0.0001 | 0.0001 |

> [!CAUTION]
> **Loop B 修复代价在危机时占总消耗的 90%+**，达到 0.095/step，而整个系统的最大进食速率仅 0.054/step（平均）、0.12/step（理论上限）。

### 3.3 物理矛盾

```
进食需要靠近热源 → d < 30（热源半径）
安全距离:    d > 12.6  → T_skin < 3.0（damage_threshold），无烧伤
进食效率:    d ↓ → T_local ↑ → deposit ↑
烧伤代价:    d < 12.6 → repair_cost > deposit → 净亏损
```

生物体必须在 **d ∈ (12.6, 30.0)** 的窄带中进食，但缺乏精确维持这个距离的行为机制。任何进入 d<12.6 的偏移都触发修复代价 > 进食收入的死亡螺旋。

### 3.4 之前的误判

之前三次调整 `max_deposit_per_step`（0.05→0.08→0.12）都基于错误假设："进食速率上限太低"。实际上：

- **deposit 利用率仅 45%**：实际 deposit 平均 0.054/step，远低于上限 0.12
- **上限从未被触及**：不是上限低，是 T_local（距离决定）本身不够大
- **即使上限无穷大**，repair 暴击时的 0.095/step 仍然 > deposit 实际值

---

## 四、系统性问题

### 4.1 复杂度积累

[variant_adapter.py](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py) 已达 **1824 行**，包含：

- 4 个 L2 反馈回路（Loop A/B/C/D）
- AGC、DA 系统、Vital Oscillator
- Spinal reflex（撤退 + 趋热）
- Binding layer、Lateral inhibition
- Impedance matching、Langevin noise
- Efference copy、Circulation proportion
- Entropy ledger、Noether probe
- Governance system

这些子系统通过共享的 `EnergyStore`、`Dopamine`、`MotionState` 紧密耦合，参数之间存在大量隐式依赖。

### 4.2 无穷回归模式

```
修 max_deposit → 暴露 Loop B repair cost 失控
修 repair cost → 可能暴露 vascular delivery 不平衡
修 vascular → 可能暴露 DA/AGC 工作点漂移
修 DA/AGC → 可能暴露 STDP 学习速率失调
...
```

每个修复改变了其他回路的工作点，导致新的失衡。这不是 bug，是 **缺乏全局热力学自洽约束** 的结构性问题。

### 4.3 手动参数调优的极限

当前系统至少有 50+ 个可调参数（来自各子系统的 config），它们之间的交互空间是组合爆炸的。没有解析的稳定性条件来指导参数选择，只能靠 500k 步实验反复试错。

---

## 五、事实摘要

| 问题 | 回答 |
|------|------|
| 趋热行为存在吗？ | ✅ 存在，但主要是 L2 硬编码，非 L1 涌现 |
| STDP 学习在工作吗？ | ✅ 权重分化可测量 |
| 系统能代谢自持吗？ | ❌ 三次 500k 均失败 |
| max_deposit 是瓶颈吗？ | ❌ 利用率仅 45%，从非瓶颈 |
| 真正的 killer 是什么？ | Loop B 修复代价（0.095/step vs 0.054 avg intake） |
| 继续参数调优能解决吗？ | 可能修好这一个，但大概率暴露下一个 |
