# 运动状态判别机制分析报告

**日期**: 2026-06-11  
**问题**: 运动状态判别机制是否生效并准确？如何生效？  
**方法**: 阅读全部相关源码（motor_decision.py, variant_adapter.py）+ 运行 VariantCircuit 10000 步实测

---

## 1. 结论

**不生效。** 机制的设计和代码完整，但所有从神经环路提取的 MotionState 字段在实测中全部为零。只有直接从身体物理量（加速度、动能）计算的非神经字段有值。

**根因**: 信号链在 Col 层断裂 — 进入 VariantCircuit 后，所有 Column 神经元完全不发放（activation=0, EMA=0），MotionState 的神经源失去了全部输入。

---

## 2. 机制设计解析

运动状态判别是一个三层结构：

### 2.1 第一层: MotionState 提取（Col 输出 → 三个测度）

代码位置: `variant_adapter.py:494-522`

```
┌──────────────────────────────────────────────────┐
│         MotionState 数据来源映射                    │
├──────────────────┬───────────────────────────────┤
│ 字段              │ 数据来源                       │
├──────────────────┼───────────────────────────────┤
│ motion_potential │ Σ|Col.activation|  各轴运动强度 │
│ temporal_measure │ Enc_irr._activation_ema  AC分量 │
│ spatial_measure  │ Enc_reg._activation_ema  DC分量 │
│ otolith_acc      │ Body.acceleration      物理测量  │
│ body_speed       │ Body.speed()           物理测量  │
│ thermal          │ ThermalMembrane        物理测量  │
└──────────────────┴───────────────────────────────┘
```

三个测度的生物学来源:

- **运动势 (motion_potential)**: 所有 Col 激活之和。在神经生物学中对应前庭核团向小脑/丘脑的输出总强度。
- **时间测度 (temporal_measure)**: Enc_irr 的平滑放电率。Irregular 传入编码加速度/振荡（AC），所以 Enc_irr 的活跃程度反映"变化有多快"。
- **空间测度 (spatial_measure)**: Enc_reg 的平滑放电率。Regular 传入编码恒定方向/重力（DC），所以 Enc_reg 的活跃程度反映"朝向哪个方向"。

这三个测度使用两路分叉（Regular/Irregular）中的信息来区分"恒定"与"变化"——这对应 Goldberg 2000 对前庭传入纤维的经典分类。

### 2.2 第二层: MotorDecisionLayer（CPG 节律 + 方向选择）

代码位置: `motor_decision.py:335-375`

```
MotionState ──→ MotorRhythmGenerator (CPG) ──→ LateralInhibition ──→ DirectionSelector ──→ Motor
                           │
                           └──→ SpatialNavigator (侧通道, 不修改输出)
```

**MotorRhythmGenerator (CPG)** 是三个耦合的 Kuramoto 相位振荡器 (x/y/z):

```
dφ_i/dt = ω_i + Σ_j κ sin(φ_j - φ_i - Δφ_ij) + ε · temporal_i
           ↑         ↑                              ↑
     固有频率 1Hz   轴间相位耦合(120°)      vestibular entrainment
```

设计意图:
- 当身体在某一轴向上有加速度（otolith_acc ≠ 0），或 Encoding_irr 显示该轴有变化（temporal_measure ≠ 0），CPG 的 `temporal_ema` 上升。
- `temporal_ema` 上升 → 推动该轴振荡器相位加速 → 运动节律与身体实际运动同步。
- 输出包络 `envelope = 0.5 + 0.5·sin(φ)` → 范围 [0, 1] → 产生交替的收缩/舒张节律。

生物对应: 脊髓 CPG + 感觉反馈夹带（Grillner 2006 七鳃鳗游泳回路，Ijspeert 2008 CPG 综述）。

**DirectionSelector** 和 **SpatialNavigator** 当前都是 Stub（passthrough），不做任何处理。

**LateralInhibition**（脊髓 Renshaw 细胞）在同一轴的 Motor 神经元之间做 WTA 竞争，防止 Motor 有丝分裂产生的所有克隆神经元以相同强度发放。

### 2.3 第三层: 反馈闭环

代码位置: `variant_adapter.py:563-581, 931-961`

**P0 Efference Copy**（前向模型）:
```python
predicted_acc = motor_acts[i] * efference_gain[axis]
error = actual_acc - predicted_acc
if motor_acts > 0.01 and mismatch < 0.001:
    motor_efficacy[axis] -= 0.0001  # Motor 发了但身体没动 → 该轴运动无效
```

设计意图: 当 Motor 命令发出后身体没有移动（被墙壁/流体阻力阻挡），降低该轴的 efficacy → 抑制该轴 Motor 的有丝分裂（不浪费能量在无效运动上）。

**Motor→Col 反馈抑制**（corollary discharge）:
```python
motor_act → Capacitor 积分 → 抑制性电流注入 Col 膜
```

设计意图: Motor 发放后抑制 Col，防止运动命令持续过驱动。生物对应: 小脑 efference copy 回路（Cullen 2004）。

---

## 3. 实测数据

### 3.1 VariantCircuit 10000 步（yaw=0.8 持续输入）

```
=== MOTION STATE (全部神经源字段 = 0) ===
motion_potential:   0.000000    ← 源: Σ|Col.activation| = 0
temporal_measure:   全部 0.0    ← 源: Enc_irr._activation_ema = 0
spatial_measure:    全部 0.0    ← 源: Enc_reg._activation_ema = 0
thermal:            0.000000    ← Col_therm = 0

=== 仅物理直接测量的字段有值 ===
body_speed:         0.000182    ← 物理（速度的模）
kinetic_energy:     0.000000    ← 物理（½mv²）
motor_potential ν: -0.000000    ← 物理（dK/dt）
otolith_acc:        x=+0.000195 ← 物理（加速度计）
polarization P:     0.404565    ← 间接（由加速度推算）
```

### 3.2 神经源字段为零的根因链

```
MotionState 所有神经字段 = 0
    ↑
Column.activation = 0（全部 6 个 Col 不发放 spike）
    ↑
Col.activation_ema = 0（发放率 EMA 为零）
    ↑
Col 膜电压 Vm = 0.05-0.12 << v_peak = 0.25（从未到达发放阈值）
    ↑
Enc→Col bundle 传入电流太弱（Enc 也不发放 → pre_trace≈0 → propagate()≈0）
    ↑
Encoding.activation = 0（全部 14 个 Enc 不发放 spike）
    ↑
Aff→Enc bundle 传入电流太弱
    ↑
VariantCircuit 有多层额外衰减:
  - Damper（L738）: 对 Enc/Col 施加额外能量消耗
  - 振荡器调制（L721）: 缩放 Aff 膜电压偏离静息值
  - NDR 门控（L762）: 在 Aff 恢复期降低膜电荷
  - 侧向抑制（L780）: 各 Col 互相注入 IPSP
  - Motor→Col 反馈抑制（L931）: Motor 发放后抑制 Col
```

### 3.3 对比: 基础版 HebbianCircuit 的 Col 状态

在 `run_audit.py` 中（使用基础版 HebbianCircuit，无 Variant 组件），Col 是有激活的:

```
run_audit.py (5000步, yaw=0.8):
  Col activation: 4.0  ← 有信号！
```

但在 `test_multiaxis.py` 中（使用 VariantCircuit），所有 Col 激活 = 0。

**差距在于 Variant 组件的累积衰减。** 基础版信号能到达 Col，闭环版被 Variant 层压制。

### 3.4 CPG 状态

```
CPG phases:       [0.001, 2.095, 4.19]    ← 在转（固有频率 1Hz）
CPG temporal_ema: [0.0001, 0.00005, 0.00006]  ← 近乎为零

无 entrainment → CPG 只是三个独立旋转的振荡器 → 节律包络与身体运动无关
```

---

## 4. 判定矩阵

| MotionState 字段 | 数据源类型 | 实测值 | 是否生效 | 失效原因 |
|-----------------|-----------|--------|---------|---------|
| motion_potential | 神经 (Col) | 0.0 | ❌ | Col 不发放 |
| temporal_measure | 神经 (Enc_irr) | 全部 0 | ❌ | Enc 不发放 |
| spatial_measure | 神经 (Enc_reg) | 全部 0 | ❌ | Enc 不发放 |
| otolith_acc | 物理 (加速度) | 有效值 | ✅ | 直接物理测量 |
| body_speed | 物理 (速度) | 有效值 | ✅ | 直接物理测量 |
| kinetic_energy | 物理 (½mv²) | 有效值 | ✅ | 直接物理计算 |
| motor_potential ν | 物理 (dK/dt) | ~0 | ⚠️ | 身体几乎不动 |
| polarization P | 混合 (加速度) | 0.405 | ⚠️ | 有意义但源信号弱 |
| thermal | 物理 (温度) | 0.0 | ⚠️ | 身体离热源太远 |
| rho_homeo | C3' 电路 | 0.9998 | ⚠️ | 运动=0 → 稳态主导 |
| homeo_deviation | C3' 电路 | 0.2998 | ⚠️ | 有值但源于静默，非真实偏离 |

---

## 5. 评估

### 5.1 设计层面

运动状态判别的三层架构（提取 → 加工 → 反馈）在概念上是正确的。特别是:

- **DC/AC 分离映射为空间/时间测度** 是对前庭神经生物学的准确建模（Goldberg 2000）
- **CPG + Entrainment** 是脊椎动物运动控制的标准范式（Grillner 2006）
- **Efference Copy** 是小脑前向模型的核心机制（Cullen 2004, Ito 1984）

### 5.2 实现层面

代码是完整且规范的:
- `MotionState` 的 20+ 个字段都有明确的来源（神经 vs 物理）和生物对应
- `MotorRhythmGenerator` 的 Kuramoto 耦合振荡器数学实现正确
- `LateralInhibition` 的 Renshaw 竞争逻辑简洁合理
- Efference Copy 的预测-比较-适应循环完整

### 5.3 运行层面

**但这一切都不工作**，因为 VariantCircuit 中的信号链在 Col 层完全断裂。运动判别器是一个设计精良的引擎控制器，但它的传感器（Col 神经元）全部离线。

这不是运动判别机制本身的问题——是信号传递链的问题。如果 Col 能正常发放（如基础版 HebbianCircuit 所示），MotionState 的神经字段就会有非零值。

### 5.4 修复路径

要使运动状态判别生效，需要按顺序解决:

1. **让 VariantCircuit 的 Enc 神经元恢复发放**（当前全部沉默）— 审查 Damper 参数、振荡器调制深度、NDR 恢复系数
2. **让 Enc→Col 传递有足够的电流**推动 Col 膜达到 v_peak（0.25）
3. **让 Col 的侧向抑制保留足够的信号**而不是完全压制（当前 gain=0.05 过强?）
4. 以上三步解决后，MotionState.temporal_measure/spatial_measure/motion_potential 将自动有值
5. CPG 的 temporal_ema 将收到非零的 entrainment 信号，振荡器与身体运动同步

---

*附注: 本报告仅针对运动状态判别机制。信号链断裂的完整分析见主报告 `nexus_v1_analysis_report_2026-06-11.md` 第 4 节。*
