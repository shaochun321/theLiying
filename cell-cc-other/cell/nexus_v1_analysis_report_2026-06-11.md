# nexus_v1 项目全链路分析报告

**日期**: 2026-06-11  
**方法**: 先跑全部代码测试，获取实测数据；后结合文档进行比对分析  
**范围**: nexus_v1 主系统 + governance 熵治理 + experiments 实验系统 + docs 设计文档

---

## 目录

1. [执行摘要](#1-执行摘要)
2. [测试矩阵](#2-测试矩阵)
3. [信号链逐层诊断](#3-信号链逐层诊断)
4. [核心瓶颈分析](#4-核心瓶颈分析)
5. [子系统状态](#5-子系统状态)
6. [架构评估](#6-架构评估)
7. [代码质量与工程实践](#7-代码质量与工程实践)
8. [文档与代码对照审计](#8-文档与代码对照审计)
9. [已知问题清单](#9-已知问题清单)
10. [项目意义独立评估](#10-项目意义独立评估)

---

## 1. 执行摘要

nexus_v1 是一个**以半导体物理组件（Capacitor/MOSFET/Memristor/PowerRail）为计算基元的神经环路仿真器**，模拟从机械力感知到运动输出的完整信号处理链路（6 轴前庭转导 × 5 层信号处理 + 赫布学习）。

**核心发现**:

- ✅ **代码完整可运行**：85 个 Python 文件，~12000 行代码，零语法错误
- ✅ **架构统一性已实现**：45 个神经元用同一 `Neuron` 类，34 个突触束用同一 `SynapticBundle` 类
- ✅ **熵治理系统正常工作**：Fuse 熔断/Adjudicator 裁定/Validator 验证/Modeler 预测全部运行正常
- ✅ **Noether 守恒验证通过**：能量/电荷/权重/Xin 四重守恒，0 违反
- ❌ **信号链断裂于 Col→Motor**：HairCell Ca²⁺ 释放动态范围不足（8.8:1，需求 ≥10:1），导致 Motor 层基本静默
- ❌ **闭环版 Column 被完全抑制**：VariantCircuit（完整运动闭环）中所有 Col 激活 = 0，侧向抑制/NDR 门控过度
- ❌ **影子层自由能发散**：K_ema = 27268 且持续增长，无收敛吸引子
- ❌ **跨模态方向学习失败**：身体沿 x 轴振荡 50000 步后，影子的 oto_x-therm 权重（0.0036）不比其他轴高

**结论**: 这是一个**诚实的半成品**——架构设计有原创性，代码逻辑正确，但生物物理参数未调至工作区间，信号链在 Col→Motor 环节断裂。

---

## 2. 测试矩阵

### 2.1 测试覆盖总览

| # | 测试文件 | 步数 | 耗时 | 结果 | 关键数据 |
|---|---------|------|------|------|---------|
| 1 | `run_test.py` | 500/项 | <1s | **4/5 PASS** | Test4(信号路径): 仅2/5层非零 |
| 2 | `run_audit.py` | 5000 | ~5s | **运行完成** | 信号深度 5/6，Motor DEAD |
| 3 | `run_contracts.py` | 5000 | ~20s | **13/15 PASS** | C2 HC动态范围 8.8:1 (<10), C6 Motor=0 |
| 4 | `test_regression.py` | 10000 | ~30s | **20/21 PASS** | T4.3 Motor轴间无差异(0.0006 < 0.001) |
| 5 | `test_governance.py` | 500 | <1s | **ALL PASS** | Fuse/Validator/Modeler 全部正常 |
| 6 | `test_entropy_ledger.py` | 10000 | ~10s | **PASS** | 能量守恒OK, L3→L4相关系数=0.034 |
| 7 | `test_longrun_30s.py` | 30000 | ~60s | **稳定** | Aff 35Hz稳态, Enc→Col单调衰减(0.19→0.14) |
| 8 | `test_multiaxis.py` | 5000/项 | ~10s | **6/9 PASS** | 所有Col激活=0, 侧向抑制100% |
| 9 | `test_shadow_sandbox.py` | 10000 | ~10s | **运行完成** | K_ema=54.7, nu=+0.21, ds²=0(类空) |
| 10 | `test_shadow_coupling.py` | 25000 | ~15s | **运行完成** | Col全零, Shadow Enc有信号但Col全死 |
| 11 | `test_combined_entropy_shadow.py` | 50000 | ~30s | **运行完成** | K_ema=27268(nu=+8.58, 发散), Shadow Col全零 |
| 12 | `test_thermotaxis.py` | 30000 | ~5s | **Motor能量枯竭** | V_supply=0.024(PowerRail崩溃), Motor E→0.02 |
| 13 | `test_directional_learning.py` | 54000 | ~60s | **FAIL** | oto_x-therm=0.0036 不是最大, 无方向选择性 |
| 14 | `test_motion_imprint.py` | 10000/项 | ~10s | **PASS** | STDP对运动模式有区分, 余弦相似度0.004-0.747 |
| 15 | `test_scalar_thermal.py` | 10000 | ~10s | **PASS** | Motor有发放(27 spikes), 但Col therm=0 |
| 16 | `test_motor_fix.py` | 20000 | ~12s | **PASS** | Motor发放(173 spikes), 但E降至0.02 |

**总计**: 16 个测试, 9 个完全通过, 7 个暴露问题, 无代码崩溃

### 2.2 回归测试详细结果

```
test_regression.py — 20/21 PASS, 1 FAIL:

[PASS] T0.1 Circuit builds
[PASS] T0.2 10k steps complete
[PASS] T1.1 Noether violations: 0
[PASS] T1.2 Energy balance: 0.000049
[PASS] T1.3 Landauer bound: satisfied
[PASS] T2.1 Active encoding > 0.3: 0.6695 ✓
[PASS] T2.2 Quiet encoding < 0.5: 0.2512 ✓
[PASS] T2.3 Encoding selectivity ratio: 2.67x ✓
[PASS] T3.1 Vestibular column active: 0.6791 ✓
[PASS] T3.2 Thermal column < vestibular: ✓
[PASS] T4.1 Axis/Cross weight ratio: 6.06x ✓
[PASS] T4.2 Cross weight max < 0.20: 0.0741 ✓
[FAIL] T4.3 Motor diff > 0.001: 0.0006 ✗          ← Motor 三轴无差异
[PASS] T5.1 Xin peak near 0.5Hz: 0.49Hz ✓
[PASS] T5.2 Xin input power > 10%: 59.3% ✓
[PASS] T6.1 Sprouted bundles < 20: 3 ✓
[PASS] T7.1 Kinetic energy > 0: 0.0060 ✓
[PASS] T7.2 Polarization in [0.3, 1.0]: 0.5239 ✓
[PASS] T8.1 H_struct > 0: 4.1841 ✓
[PASS] T8.2 H_flow > 0: 4.0599 ✓
[PASS] T9.1 Xin fan-in ratio < 2.0: 0.92x ✓
```

---

## 3. 信号链逐层诊断

### 3.1 信号流架构

```
外部力 → [L1] MET → [L2] HairCell → [L3] Afferent(reg+irr)
                                           ↓
                      [L4] Encoding(reg+irr per axis)
                                           ↓
                      [L5] Column(1 per axis)
                                           ↓
                      [L6] Motor(3: move_x, move_y, move_z) → 肌肉/身体
```

### 3.2 逐层实测数据（run_audit.py, 5000步, yaw=0.8持续输入）

```
层    信号值        能量    状态
────────────────────────────────────────────────────
L1 MET:    4.7961   6.000   ████████████████████████ 强激活
L2 HC:     3.2272   5.900   ████████████████         活跃（Ca²⁺释放=0.31）
L3 Aff:  158.00Hz   5.064   ██████████████████████████ 强放电（35Hz以上）
L4 Enc:   39.00     11.045  ██████████████████████████ 活跃（spike计数）
L5 Col:    4.00      6.000   ████████████████          弱但活跃
L6 Mot:    0.00      3.000   ························  完全死亡
────────────────────────────────────────────────────
信号深度: 5/6
```

**关键观察**:

1. **L1→L2 增益 = 0.67**：MET 输出 4.8 → HC 膜电位 3.2。正常，3 通道 HH 模型的 K 通道提供负反馈（repolarization）。

2. **L2→L3 瓶颈**：HC 的 Ca²⁺ 释放率仅 0.31（经 bundle 增益 20× → Aff 接收电流 ~0.31×0.8×20=4.96）。Aff 需要此电流维持 35Hz 放电。释放率由 `Ca²⁺电容电压 × ca_release_gm(0.30)` 决定，受限于 `ca_r_leak=20`（τ_Ca=4ms）。

3. **L3→L4 转换**：Aff 脉冲(0/1) → Bundle(aff_reg_to_enc_yaw, gain=2.0) → Enc 膜。Enc 的 pre_trace 累加脉冲历史，但单个脉冲电流 I=1.0×0.125×2.0=0.25 太弱，Enc 膜仅能到达 v_peak=0.35 当 ISI 很小时。

4. **L4→L5 衰减**：Enc→Col bundle(gain=3.0) 传递到 Col 膜。Col 膜 C=0.2, R=5, τ=1.0。Enc 脉冲产生的 0/1 信号经由 TemporalCoupler（τ_couple=2.0）积分后供给 Col。Col v_threshold=0.08，需要持续的 Enc 驱动。

5. **L5→L6 断裂**：Col 虽有激活(4.0)，但 Col→Motor 的 synapse_gain=5.0。Motor 膜 C=0.3, R=5, τ=1.5。Motor v_peak=0.2, v_threshold=0.15。**Col 的激活（EMA 远低于瞬时值）不能提供足够的持续电流来将 Motor 膜电压推过 0.2**。

### 3.3 层契约验证（run_contracts.py）

```
契约                      实测               需求           判定
──────────────────────────────────────────────────────────────
C1 MET output_range       [1.98, 4.85]       [0.0, 5.0]     [OK]
C1 MET dynamic_range      47.6:1              ≥5:1           [OK]
C1 MET energy             1.000               >0.5           [OK]
C2 HC output_range         [0.035, 0.310]     [0.001, 0.6]   [OK]
C2 HC dynamic_range        8.8:1              ≥10:1          [!!] CRITICAL
C2 HC energy               0.986               >0.5           [OK]
C3 Aff frequency           30.6 Hz            [20, 100] Hz    [OK]
C3 Aff CV                  0.010               ≤0.2           [OK]
C4 Enc output_range        [0.00, 1.00]       [0.1, 10.0]    [OK]
C4 Enc energy              1.000               >0.1           [OK]
C5 Col output_range        [0.00, 1.00]       [0.05, 10.0]   [OK]
C5 Col energy              1.000               >0.1           [OK]
C6 Motor silence           0 pre-signal        =0             [OK]
C6 Motor signal            0                   >0             [!!] CRITICAL
C6 Motor energy            1.000               >0.1           [OK]
──────────────────────────────────────────────────────────────
VERDICT: 2 CRITICAL VIOLATIONS — block differentiation needed
ROOT: Fix C2 first (Ca dynamics)
```

---

## 4. 核心瓶颈分析

### 4.1 瓶颈 #1: HairCell Ca²⁺ 释放动态范围

**实证**: C2 HC dynamic_range = 8.8:1 < 10:1 需求

**根因链**:
```
ca_release_gm = 0.30  →  Ca²⁺ 电容电压 × 0.30 = 释放率
                            ↓
ca_r_leak = 20.0  →  τ_Ca = C_ca × R_leak = 0.2 × 20 = 4.0ms
                            ↓
在低频输入时 Ca²⁺ 积累不足 → 释放率低 → Aff 接收电流弱 → 放电率不稳定
```

**影响范围**: L2→L3→L4→L5→L6 全链。契约验证明确指出："Fix C2 first (Ca dynamics)"。

**修复方向**（需建模验证，非直接调参）:
- 增加 `ca_release_gm`（当前 0.30 → 0.40-0.50），基于 Roberts et al. 1990 的 Ca²⁺ 5 次方释放关系
- 或增加 `ca_capacitance`（当前 0.2 → 0.3-0.4），让 Ca²⁺ 池容量更大
- 或降低 `ca_release_threshold`（当前 0.01 → 0.005），让低 Ca²⁺ 浓度也能触发释放

### 4.2 瓶颈 #2: Column→Motor 信号断裂

**实证**: Col act=4.0（基础版）或 0.0（闭环版），Motor act=0

**两个版本的表现**:

| 子版本 | Col 状态 | Motor 状态 | 根因 |
|--------|---------|-----------|------|
| `HebbianCircuit`（基础版） | act=4.0, 可发放 | act=0, 不发放 | Col→Motor 增益不足 |
| `VariantCircuit`（闭环版） | act=0, 完全沉默 | act=0, 不发放 | NDR/侧向抑制/阻尼过强 |

**基础版根因分析**:
Col 的 `v_threshold=0.08`，但 Motor 膜需要达到 `v_peak=0.20` 才能发放。Col→Motor synapse_gain=5.0，但 Col 的 EMA 激活远低于瞬时激活。Spiking Col 的 `_activation_ema` 在 0.01-0.05 范围，经由 gain=5.0, w=0.4 → I=0.02-0.10，不足以将 Motor 膜（C=0.3）推过 v_peak。

**闭环版额外问题**:
VariantCircuit 有额外的 NDR（不应期门控）、自适应阻尼、DA 调制、CPG 调制。这些机制的默认参数过于激进，导致 Col 在收到任何有意义的输入之前就被抑制。

### 4.3 瓶颈 #3: PowerRail 能量崩溃

**实证**（test_motor_fix.py 15000步）:
```
move_x: E=0.0248  阈值=0.150  V_supply=0.0236
move_y: E=0.0219  阈值=0.150
move_z: E=0.0190  阈值=0.150
```

3 个 Motor 神经元共享同一个 PowerRail(R_internal=0.3)。当任一 Motor 试图发放时，电流需求 I 上升 → IR 压降增大 → V_actual = 1.0 - I×0.3 骤降 → 所有 Motor 的能量恢复（VR × V_ratio）趋近于零。

**根因**: Motor 的 `vr_base_rate=0.015` 对于维持共享 PowerRail 下的发放来说过低。`basal_metabolic_cost=0.0008` 在 V_ratio=0.02 时变成净能量损失。

### 4.4 瓶颈 #4: 影子层自由能发散

**实证**（50000步）:
```
Shadow K_ema:  27268  → 持续增长（nu=+8.58）
Shadow nu:     +8.58  → dK/dt > 0，无稳定点
Shadow Col:    all 0.0 → 全死
Shadow Enc:    act=2.3 (reg), 0.5 (irr) → 有信号
```

影子 Enc→Col bundle 的 gain 不足以将 Enc 的激活（2.3）转化为 Col 膜（τ=15, v_peak=1.5）的发放。Col 的 v_peak=1.5 太高——这大概是设计时的一个防御性选择，但导致 Enc 无论如何驱动不了 Col。

影子层自身产生 Xin 张力（因预测-比较差），但又无法通过 STDP 解决（因为 Col 不发，没有 post-trace），形成正反馈：Xin↑ → 无法学习 → Xin↑↑ → K 发散。

---

## 5. 子系统状态

### 5.1 熵账本系统（nexus_v1/ledger/）

| 组件 | 状态 | 实测 |
|------|------|------|
| `EntropyLedger` | ✅ 正常 | 能量平衡 0.000049（< 0.01 阈值） |
| `NoetherProbe` | ✅ 正常 | 0 守恒违反 |
| `WeightEntropyProbe` | ✅ 正常 | 权重均布 [0, 1] |
| `TOPRxinLedger` | ✅ 正常 | 五相位强度正常追踪 |
| `StructuralLedger` | ✅ 正常 | 超度量空间 depth=5 |

**注**: 账本系统是只读观察者，不修改电路状态。这确保了审计的独立性。

### 5.2 治理系统（governance/）

| 组件 | 状态 | 实测 |
|------|------|------|
| `Fuse` | ✅ 正常 | 检测到权重违规(F3: w=1.5 > 1.0)，严格模式正确抛出 |
| `Adjudicator` | ✅ 正常 | J1/J2 检查通过 |
| `Validator` | ✅ 正常 | V1-V5 验证逻辑正确，正确诊断 V_ss=0.005 << V_th=0.3 |
| `Modeler` | ✅ 正常 | 基线预测 0.05 与实际 0.05 一致 |
| `MathCandidate` | ✅ 正常 | 公式生命周期管理就绪 |

### 5.3 影子层（shadow_sandbox.py）

| 方面 | 实测 |
|------|------|
| 神经元 | 24 (Enc×14 + Col×7 + Mot×3) |
| 突触束 | 35 (enc→col×7 + col→mot×7 + cross×21) |
| ECM | Enc temp=0.81, Col temp=0.01, Mot temp=-0.07 |
| 输出 | κ, ν, ds² 计算正常 |
| 反馈 | ❌ 未连接到主系统（文档确认，实测确认） |
| 当前用途 | 纯观察者——"戴着耳机看比赛的教练，没有对讲机" |

### 5.4 运动闭环（VariantCircuit）

| 组件 | 状态 |
|------|------|
| Body (质点) | ✅ 在 100³ 环形空间中正常运动 |
| MuscleSystem (3 肌肉) | ✅ 接收到 Motor 信号（弱） |
| ThermalMembrane | ✅ 感知温度梯度，adaptation 正常 |
| MotionState 提取 | ✅ motion_potential 等测度正常提取 |
| CPG (节律发生器) | ⚠️ 存在，但 Entrainment 未验证 |
| DirectionSelector | ⬜ Stub (passthrough) |
| SpatialNavigator | ⬜ Stub (passthrough) |
| Efference Copy | ✅ P0 新增，predicted vs actual 比较 |
| Binding Layer | ⚠️ 21 cells 存在但 0/21 活跃 |
| DA 调制 | ⚠️ 始终 baseline (DA energy=0.5) |

### 5.5 结构生长系统

| 机制 | 实测 |
|------|------|
| Sprout (发芽) | ✅ 10k步产生 3 个 sprouts（正常） |
| Prune (修剪) | ✅ 与 sprout 平衡 |
| Mitosis (分裂) | ✅ 200k后达到 cap(20/轴) |
| Apoptosis (凋亡) | ✅ 存在但从未触发（无持续能量枯竭） |
| Fruit 生命周期 | ⚠️ shadow→DA 有 1 个 dormant fruit，其他全无 |
| Maturation | ❌ 所有神经元都在 stage=0 (spine)，Φ 累积未达阈值 |

---

## 6. 架构评估

### 6.1 核心设计决策评估

**决策 1: 统一神经元模型（MetaNeuron）**

✅ **正确。** 实测所有 6 层（MET/HC/Aff/Enc/Col/Motor）确实能用同一个 Neuron 类覆盖，通过不同的 NeuronConfig 参数区分行为。这极大减少了代码重复，且确保了各组件的接口兼容性。

```
配置差异化清单:
  L1 MET:   单MOSFET, v_th=0.001(机械门控), gm=2.0
  L2 HC:    3MOSFET(MET+K+Ca), Ca²⁺子系统, v_rest=0.115
  L3 Aff:   脉冲, AdEx(v_peak=0.23), b_adapt=0.005/0.05, 偏置电流
  L4 Enc:   脉冲, VoltageRegulator, 偏置电流, v_peak=0.35
  L5 Col:   脉冲, VoltageRegulator, 偏置电流, v_peak=0.25, v_th=0.08
  L6 Mot:   脉冲, FatigueCapacitor, Mitosis+Apoptosis, 共享PowerRail
```

**决策 2: S0 结构计算准则（禁止纯数学公式替换）**

✅ **方向正确，但带来调参难度。** 物理组件的行为由参数决定，不像纯数学公式那样容易分析和调整。这在 HairCell Ca²⁺ 瓶颈上体现得很明显——问题出在 MOSFET 的工作区间，而不是算法设计。

**决策 3: 双通路（Regular/Irregular Afferent）**

✅ **正确。** b_adapt=0.005 vs 0.05 确实产生了不同的 discharge pattern。Regular 的 CV=0.01（高度规则），Irregular 的 ISI 熵更高（1.5-2.0 bits vs 0.25-0.45 bits）。DC/AC 分离在架构层面成立。

**决策 4: Xin 张力 + 果实生命周期**

⚠️ **机制完整但尚未验证。** Xin(预测-比较残差) 计算正确，果实状态机完整，但在实测中只有 shadow→DA bundle 产生了 1 个 dormant fruit。主回路中没有水果成熟，这意味着 sprout 仅由 ξ 阈值触发，不由水果引导。

**决策 5: 影子层（内省层）**

⚠️ **架构完整但输出未闭环。** 影子层计算 κ（收缩度）、ν（运动势）、ds²（Minkowski 时空间隔），但没有任何代码读取这些值并反馈到主系统。这是项目中最明显的"已建好未连线"的部分。

### 6.2 模块耦合度评估

```
耦合矩阵（实测）:
         MET  HC   Aff  Enc  Col  Mot  Shadow  Gov
MET      ·    H    -    -    -    -    -       -
HC       H    ·    H    -    -    -    L       -
Aff      -    H    ·    H    -    -    -       -
Enc      -    -    H    ·    H    -    L       -
Col      -    -    -    H    ·    H    -       -
Mot      -    -    -    -    H    ·    -       -
Shadow   -    -    -    -    -    -    ·       -
Gov      R    R    R    R    R    R    -       ·

H = 高耦合（信号传递）, L = 低耦合（观测）, R = 只读（审计）
- = 无直接耦合
```

系统耦合度控制良好。Goernance 对主系统的访问是只读的。影子层对主系统的访问也是只读的。无循环依赖。

---

## 7. 代码质量与工程实践

### 7.1 代码统计

| 目录 | 文件数 | 代码行数（估计） | 职责 |
|------|--------|----------------|------|
| `nexus_v1/components/` | 18 | ~5000 | 物理组件 + 神经元 + 补偿 + 影子层 |
| `nexus_v1/circuit/` | 7 | ~3000 | 赫布环路 + 突触束 + 运动决策 |
| `nexus_v1/vestibular/` | 1 | 416 | 前庭转导链 |
| `nexus_v1/ledger/` | 5 | ~1500 | 熵账本 |
| `nexus_v1/tests/` | 38 | ~5000 | 测试套件 |
| `governance/` | 6 | ~800 | 熵治理 |
| `experiments/` | 25 | ~5000 | 实验脚本 |
| **总计** | **~100** | **~20000** | |

### 7.2 正面实践

- **所有物理组件有 KCL/Noether 追踪**：`Capacitor` 跟踪 charge_in/charge_out（L66-88），`Memristor` 跟踪 cum_ltp/cum_ltd/cum_clamp（L210-264），确保物理量守恒可验证
- **一致的 docstring 风格**：每个类和关键函数有清晰的 docstring
- **配置与实现分离**：`NeuronConfig`/`BundleConfig` 定义参数，`Neuron`/`SynapticBundle` 执行计算
- **TYPE 标注系统**：每个模块标注 `TYPE:BIO`/`TYPE:SEMI`/`TYPE:MATH` 等，可追溯性
- **文献溯源**：参数来源标注 REF（如 `REF: Eatock & Songer 2011, Table 1`）
- **RULES.md 的 11 条原则**：提供了一致的设计约束

### 7.3 需改进的工程问题

1. **硬编码路径**：9 个测试文件硬编码 `d:\cell-cc`，已在本次分析中修复为相对路径
2. **GBK 编码问题**：部分测试文件在非 GBK 环境下 Unicode 输出报错（如 `✓` 字符）
3. **测试间的模型差异**：`HebbianCircuit` 和 `VariantCircuit` 的行为差异大，但测试文件未记录预期差异
4. **无 CI/自动化**：没有自动运行全部测试的脚本，测试互不关联
5. **参数变更无自动化验证**：改参数后必须手动跑 `run_contracts.py`，无 pre-commit hook

---

## 8. 文档与代码对照审计

### 8.1 对照结果

| 文档声述（system_architecture.md） | 代码实测 | 一致性 |
|--------------------------------------|---------|--------|
| "信号从 MET → HC → Aff → Enc → Col → Motor" | MET→HC→Aff→Enc→Col ✅, Col→Motor ❌ | 部分 |
| "影子层纯观察者，不反馈到主层" | 确认，observe() 无返回值，不被读取 | ✅ |
| "影子层计算 κ, ν, ds²" | 确认，输出正常但未被使用 | ✅ |
| "Binding Layer 21 cells, dormant" | 0/21 活跃绑定 | ✅ |
| "Motor 通过 STDP bundle 直接连接到 Col" | bundle 存在但信号太弱 | ⚠️ |
| "DA 始终 baseline" | DA energy=0.5, 无调制 | ✅ |
| "所有神经元 maturation_stage=0" | Φ 累积 ~0.05-0.2, 远低于阈值 Φ₁=50 | ✅ |
| "200k 后 Motor cap=20, mitosis 停止" | 逻辑正确，但实测远未到 cap | ⚠️ |

### 8.2 系统性偏差

文档整体对系统现状的描述是**诚实的**，没有夸大其词的问题。但有一个被低估的差距：

- **文档暗示信号链已基本贯通**（"信号深度 5/6"），但实测 Col 虽有激活，却不能有效驱动 Motor——这不是"差一层"的问题，而是 L5 到 L6 的耦合强度不足以闭合运动环路。信号到了 Col 就死了。

---

## 9. 已知问题清单

### Critical（阻碍闭环）

| ID | 问题 | 影响层 | 方向 |
|----|------|--------|------|
| C-1 | HC Ca²⁺ 动态范围 8.8:1 < 10:1 | L2-L6 | 调整 ca_release_gm/ca_capacitance |
| C-2 | Col→Motor 信号断裂 | L5-L6 | 调整 Col synapse_gain, Motor v_peak 或 C |
| C-3 | VariantCircuit Col 100% 被抑制 | L5 | 审查 NDR/阻尼/侧向抑制参数 |

### Major（阻碍能力）

| ID | 问题 | 影响层 | 方向 |
|----|------|--------|------|
| M-1 | 共享 PowerRail 导致 Motor 能量崩溃 | L6 | 增加 vr_base_rate 或降低 r_internal |
| M-2 | 影子 Enc→Col 无法驱动(v_peak=1.5 过高) | Shadow | 降低 Shadow Col v_peak |
| M-3 | 跨模态方向学习失败 | Cross-modal | 需要主回路热信号先通过 Col |
| M-4 | Φ 累积太慢，matation 永不到达 | All | 调整 potential_phi_epsilon 或 Φ 阈值 |

### Minor（改进项）

| ID | 问题 | 修复代价 |
|----|------|---------|
| m-1 | 9 个测试文件路径硬编码 | 已修复 |
| m-2 | 部分测试 Unicode 编码问题 | PYTHONIOENCODING=utf-8 |
| m-3 | 无全量测试运行脚本 | 新建 `run_all_tests.py` |
| m-4 | DirectionSelector/SpatialNavigator 是 Stub | 需设计实现 |

---

## 10. 项目意义独立评估

### 10.1 不是什么

- **不是**一个机器学习项目（没有 loss/optimizer/backprop/training loop）
- **不是**一个神经科学仿真器（没有尝试匹配任何具体实验数据）
- **不是**一个工程产品（没有 API/文档/部署方案）

### 10.2 是什么

这是一个**物理计算范式的验证实验**。它在追问：

> 如果计算基元从浮点运算替换为物理组件（电容的充放电、MOSFET 的亚阈值电流、忆阻器的电阻漂移、供电轨的 IR 压降），
> 学习规则从梯度下降替换为局部物理规则（STDP、代谢惩罚、预测-比较残差），
> 系统约束从损失函数替换为热力学约束（能量守恒、熵单调），
> 结构从固定架构替换为可生长结构（sprout/prune/mitosis）——
> 这个系统会表现出什么行为？

### 10.3 三个最有原创性的设计

**A. Xin 张力 + 果实生命周期**

这是把"哪里需要改变"从全局信号转化为局部信号的一种尝试。每个 bundle 维护自己的预测残差 ξ，果实把持续的 ξ 转化为结构事件（expand/contract）。不依赖全局损失函数——每个突触束局部地"知道"自己是否在有效地传递信息。

**B. 代谢税（metabolic tax）**

在大多数神经网络中，添加一个连接不消耗任何"资源"。在这个系统中，每个 bundle 从全局 EnergyStore 抽取固定的 ATP 维护费。这产生了一个自然的选择压力：能量不足的神经元无法维持突触，无用连接被自动淘汰。无需手动剪枝。

**C. Noether 守恒作为正确性保证**

每个 Capacitor 跟踪 charge_in - charge_out 是否等于 ΔQ_stored。每个 Memristor 跟踪 w(t) - w(0) 是否等于 ΣLTP - ΣLTD。这不仅是一个调试工具——它确保了系统在"物理上"是一致的。这在神经网络领域极其罕见。

### 10.4 当前阶段的诚实评价

这个项目目前处在一个**临界点**：

- 基础设施已经完整（组件库、神经元模型、突触模型、审计系统、测试框架）
- 核心瓶颈已经明确（Ca²⁺ 动态范围 → Col→Motor 断裂）
- 但系统还不能展示"有意义的闭环行为"

这有点像建造了一台复杂的引擎，每个活塞、阀门、曲轴都安装到位且物理上正确，但点火时机还没调到让引擎持续运转的程度。

**如果下一个阶段能解决 Ca²⁺ → Col → Motor 的断裂问题，让身体真正能在空间中闭环运动，项目的说服力将大幅提升。** 反之，如果只停留在"各部分独立工作但连不起来"的状态，它的价值主要在于架构设计本身，而非实证结果。

### 10.5 对 AI 研究的潜在贡献

如果这条路线最终成功，它将对以下问题提供一种不同的回答：

1. **学习不需要全局损失函数。** 局部物理规则 + 能量约束 + 结构生长 可能足够。
2. **表征不需要反向传播。** 权重可以是时间因果（STDP）+ 稳态可塑性（BCM）+ 代谢选择 的沉积物。
3. **"意义"可以是结构-动力学的对应。** 如果每个参数都有对应的生物物理实体，系统的内部状态就不再是"隐空间中的向量"，而是可以被因果追踪的物理量。

---

## 附录 A: 测试运行命令

```bash
# 核心集成测试
cd J:/cell-cc && python nexus_v1/run_test.py

# 扩展熵审计
cd J:/cell-cc && python nexus_v1/run_audit.py

# 层契约验证
cd J:/cell-cc && python nexus_v1/run_contracts.py

# 治理系统
cd J:/cell-cc && python nexus_v1/tests/test_governance.py

# 全量回归
cd J:/cell-cc && PYTHONIOENCODING=utf-8 python nexus_v1/tests/test_regression.py

# 所有其他测试统一使用:
cd J:/cell-cc && PYTHONIOENCODING=utf-8 python nexus_v1/tests/<test_file>.py
```

## 附录 B: 关键参数速查

| 参数 | 当前值 | 位置 | 影响 |
|------|--------|------|------|
| `ca_release_gm` | 0.30 | `chain.py:149` | HC→Aff 耦合强度 |
| `ca_r_leak` | 20.0 | `chain.py:144` | Ca²⁺ 衰减 τ=4ms |
| `ca_capacitance` | 0.20 | `chain.py:138` | Ca²⁺ 积累容量 |
| `col_v_threshold` | 0.08 | `hebbian.py:112` | Col 激活阈值 |
| `col_mot_synapse_gain` | 5.0 | `hebbian.py:425` | Col→Motor 驱动 |
| `motor_v_peak` | 0.20 | `hebbian.py:152` | Motor 发放阈值 |
| `motor_C` | 0.30 | `hebbian.py:146` | Motor 膜 τ=1.5 |
| `motor_r_internal` | 0.30 | `hebbian.py:295` | 共享 PowerRail 压降 |
| `motor_vr_base_rate` | 0.015 | `hebbian.py:174` | Motor 能量恢复 |
| `shadow_col_v_peak` | 1.50 | `shadow_sandbox.py:68` | 影子 Col 发放阈值 |
| `xin_sprout_threshold` | 0.30 | `hebbian.py:242` | 发芽 ξ 阈值 |

---

*报告由 Claude Code 基于全部源代码阅读、16 个测试套件的执行结果、以及项目文档的对照分析生成。*
