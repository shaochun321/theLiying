---
tags: [MOC, 导航, AI编程, 自足文档, 执行]
concepts: [B06, nu_th, C3, 环流耦合, 热趋性, SpatialNavigator, DA, 抗饱和, 编程指令, 参数速查]
type: MOC
date: 2026-06-14
aliases: [AI编程, 编程文档, ai-prompt, programming-brief]
---
# AI 编程自足文档：Cell-CC 项目 v0.9.0 → v1.0 路线

> **大模型用户**: 此为最小可行自足文档。无需读取 vault 中的任何其他文件即可开始编码。
> **当需要深入了解某概念时**: 使用本文件末尾的"查询清单"查找对应的源文件。

---

## 一、项目定位

**代码位置**: `d:/cell-cc/nexus_v1/`（本项目 J:\cell-cc\cell-cell\ 为文档存档，无 Python 代码）

**当前版本**: v0.9.0 (2026-06-06)
**终极目标**: **热趋性闭环 (1.1)** — 系统自发朝热源移动并维持在该区域。
**当前状态**: 信号链 6/6 通过 (EXP-014)。行为**未涌现** (EXP-015)。20/21 回归通过 (T4.3 Motor diff 边界抖动: 0.0009 vs 阈值 0.001)。

```text
项目哲学:
  - 无语义原则: 系统内部只有数值——没有"食物""危险""方向"等语义标签
  - 结构=过程的化石: Xin(时间域) → sprout(结构变化) → 存活连接=过程的永久痕迹
  - 时空内生: ds² 和 ν 不由外部坐标定义——从信号延迟/衰减/环流中涌现
  - 回报≠标量: 回报是环流模式回到平衡的过程 (ρ 向量替换标量回报)
```

---

## 二、当前执行顺序 (P0 → P1)

```
步骤 1         步骤 2        步骤 3        步骤 4        步骤 5
B.06 ν_th  →  基底噪声  →  抗饱和  →  C3' 环流  →  L2 反馈修复
(热梯度→DA)   (随机游走)    (DA 防崩塌)   (环流回报)    (空间记忆)
```

---

### 步骤 1: B.06 — 热势 ν_th = dE_thermal/dt【最关键缺失】

**状态**: ❌ 未实现。**这是项目关键路径阻塞点。**

**含义**: 类比已有的运动势 ν=dK/dt（动能变化率驱动运动-DA 耦合），用热能变化率驱动热-DA 耦合。

**数学**:
```
ν_th = dE_thermal/dt = (T_skin[t] - T_skin[t-1]) / dt

关键关联:
  ν_th × ΔT > 0  →  朝热源移动，皮温升高 → DA↑ → 强化当前方向
  ν_th × ΔT < 0  →  远离热源，皮温降低 → DA↓ → 促进转向
```
这是 **klinokinesis**（细菌趋化性核心机制）。

**需要新增的代码**:
1. `MotionState` (motor_decision.py) 新增字段:
   ```python
   thermal_gradient: list[float]  # [T_front - T_back, T_left - T_right]
   thermal_potential: float       # d(energy_absorbed)/dt
   ```
2. 热感信号链中计算 `thermal_potential`:
   ```python
   thermal_potential = (current_skin_temp - previous_skin_temp) / dt
   ```
3. DA 释放逻辑中使用:
   ```python
   if thermal_potential * thermal_gradient_dot_velocity > 0:
       dopamine.release(abs(thermal_potential) * DA_THERMAL_GAIN)
   ```

---

### 步骤 2: 基底噪声 — 无前庭输入时的随机游走

**状态**: ❌ 未实现

**含义**: 无前庭输入 → 身体静止 → 热梯度静态 → 无时变信号。需要基线运动。

**方案**: 在 `variant_adapter.py` 的 otolith 输入路径上叠加弱自发活动:
```python
# 当前 (line ~642):
OTOLITH_GAIN = 500.0
mechanical_inputs['oto_x'] = acc[0] * OTOLITH_GAIN

# 修改为:
BASELINE_OTOLITH_NOISE = 0.01  # 弱自发活动
mechanical_inputs['oto_x'] = (acc[0] + random.normal(0, BASELINE_OTOLITH_NOISE)) * OTOLITH_GAIN
```
或在 Motor 层增加自发噪声机制。

---

### 步骤 3: 抗饱和 — Shadow col calcium_rate 防饱和

**状态**: ❌ 未实现

**含义**: Shadow 层 calcium_rate 在 ~20k 步饱和到 0.97+ → Xin 残差→0 → DA 永久沉默。

**三个对策**:
1. **硬上限**: `calcium_rate = min(calcium_rate, 0.8)` (shadow_sandbox.py)
2. **BCM 滑动阈值扩展到影子层** (当前 BCM 只在主线)
3. **Shadow STDP 衰减加速**: 调整 `w_decay` 参数

**最小改动**: 方案 1 (硬上限) 1 行代码，先验证效果，再考虑方案 2/3。

---

### 步骤 4: C3' — 摄食-运动-体征环流耦合

**状态**: 6/6 实现步骤完成，50k 步 0 违规。**依赖 B.06 完成。**

**含义**: 替代旧 C3(热源→DA)和 C5(三因子 Fruit)。"回报不是标量——回报是环流模式回到平衡的过程。"

**已实现的 MotionState 字段** (motor_decision.py):
```python
homeo_amplitude: float       # 体征稳定度反比
motor_amplitude: float       # body_speed + otolith Xin
feed_amplitude: float        # heat_dir dot vel_dir * thermal_err
rho_homeo/motor/feed         # 归一化环流比例
homeo_deviation              # |rho - 1/3|
```

**DA 释放**: `dopamine.release(homeo_deviation * 0.5)` when `homeo_deviation > 0.05`

**正常/失衡态**:
```
正常: ρ_homeo≈0.7, ρ_motor≈0.2, ρ_feed≈0.1 → DA 低 → 维持
失衡: ρ_homeo↓, ρ_motor↑, ρ_feed↑ → DA 高 → 学习
```

---

### 步骤 5: L2 反馈修复 — 空间记忆

**状态**: 规划阶段。**依赖 C3' 完成。**

**L2.09 发现**: 26 参数组合 → **0 死亡**。L2.08 的"4/4 FULL PASS"是假阳性。
**根因**: 机体是"无记忆布朗运动代理"——它不知道自己从哪里来，不区分主动运动/被动位移。

**需要填充的空壳**:
| 结构 | 文件 | 现有状态 | 需要实现 |
|------|------|---------|----------|
| `SpatialNavigator` | motor_decision.py:256-284 | `update()` is `pass` | 路径积分: 积分 otolith 加速度→位移估计 |
| Efference copy | 不存在 (grep 零结果) | — | Motor 输出副本→比较器输入 |
| 复位脉冲生成器 | 不存在 | — | 散度>阈值→VOR 反向脉冲 |
| 散度比对 | Shadow 有但无行为输出 | — | 连接 Shadow Xin 比较→Motor 决策 |

---

## 三、当前代码基座 (v0.9.0 架构总览)

```
VariantCircuit (主系统)
├── VestibularChain (6 层 x N 轴 + 4 热补丁)
│   ├── Met(L1) → HC(L2) → Aff(L3) → Enc(L4) → Col(L5) → Motor(L6)
│   └── SomatosensoryChain (Thermo + Noci) [6.11 新增]
├── HebbianCircuit
│   ├── Encoding x4, Column x4, Motor 3(+mitosis), Bundles + 结构操作
│   └── ShadowSandbox (24 神经元, DN + CRI + spiking)
├── DA Circuit (3 神经元, D2Autoreceptor, gm=8.0, bias_current)
├── Entropy Ledger (Phase 0 前置, _structural_freeze 门控)
├── ECM + Vascular + Thermal
├── Oscillators (VitalOscillator: 3 失谐 VdP, f≈2Hz, 振幅∝EnergyStore)
├── LiquidMetalRouters, LateralInhibition
└── CirculationMeter (开环传感器, 非环流本身)
```

**新增文件清单** (步骤 1-5 执行后预计):
- NEW: `somatosensory/chain.py`, `self_origin.py`, `components/spinal_reflex.py`
- MODIFY: `world.py`, `shadow_sandbox.py`, `hebbian.py`, `variant_adapter.py`, `motor_decision.py`

---

## 四、回归测试基线

**当前**: 20/21 PASS。失败: T4.3 Motor diff = 0.0009 < 阈值 0.001（边界抖动）。

**测试文件**:
- `tests/test_regression.py` — 主回归套件
- `tests/test_phase3_da_loop.py` — Gate 3 (已修复使用 calcium_rate)
- `tests/test_thermotaxis_v2.py` — EXP-015 热趋性

**性能约束**: 10k 步 ≈ 28.8s, 100k 步 ≈ 合理范围。50k 步 = 标准验证。

---

## 五、开放退化项 (需在步骤 1-5 后处理)

| ID | 问题 | 优先级 |
|----|------|--------|
| DEG-004 | Afferent 发放率太低 (12.5Hz vs 目标 50-100Hz) | 中 |
| DEG-007 | STDP 权重未演化 | 高 (阻塞学习) |
| DEG-008 | Motor bias 自发 82% | 中 |
| DEG-011/012 | MET/HairCell 能量耗尽 (0.001 → 合约要求 0.5) | 中 |

---

## 六、关键参数速查表

| 参数 | 当前值 | 位置 | 说明 |
|------|--------|------|------|
| `OTOLITH_GAIN` | 500.0 | variant_adapter.py:642 | 前庭放大 |
| `XI_SPROUT` | 0.3 (glossary) / 2.0 (旧 plan) | — | **矛盾**，确认实际值 |
| `MAX_MOTORS_PER_AXIS` | 20 | glossary | Motor 轴上限 |
| DA gm | 8.0 | variant_adapter.py | DA 增益 |
| DA bias_current | 已添加 (v0.9.0) | variant_adapter.py | 防止 V_m=0 |
| DA release threshold | 0.05 | variant_adapter.py | C3' 环流偏差激活阈值 |
| Motor bc_current | 0.01 | circuit config | 导致 82% 自发 (DEG-008) |
| Shadow calcium_rate saturation | 0.97+ | shadow_sandbox.py | **需要硬上限 0.8** |
| Noci tau | 4ms (C=0.5,R=8.0) | 设计规范 | 未硬编码 |
| Thermo tau | 100ms (C=5.0,R=20.0) | 设计规范 | 未硬编码 |

---

## 七、九个待决设计决策 (执行线之后)

| # | 决策 | 推荐 | 触发条件 |
|---|------|------|----------|
| D1 | 影子层输出 → ? | B: nu→DA | B.06 后 |
| D2 | Motor 分化路径 | C: 竞争抑制 | 步骤 5 后 |
| D3 | P 精度 | A: 保持现状 | — |
| D5 | 振荡验证实验 | B: 改变输入功率 | 执行线后 |
| D7 | 运动势定义 | C: dK/dt | ν 接线修复后 |
| D8 | 影子 4D 容积 | 抽象先→4D 后 | 执行线后 |
| D9 | 影子生长模式 | 不生→Scout 后 | 执行线后 |

---

## 八、三环流周期参考

```
ρ_homeo (稳态):  ~100 步 (0.1s) — Thermal → ECM → Enc → Col
ρ_motor (运动):  ~500 步 (0.5s) — Motor → Body → Oto → Aff → Enc → Col → Motor
ρ_feed  (摄食):  ~5000 步 (5s)  — Thermal → Col → Motor → Body → 位移 → Thermal
```

---

## 九、T·S·I 约束 (基础不变量)

```
N_eff · Δw · f_osc · mean_ξ_vest ≤ P_input

相变条件: 结构容量满 + 振荡频率↑ → 空间度量坍缩 → 失去空间分辨率 → 相变
相变后: 新生 T' (sprout/mitosis) → 容量↑ → 新稳态
可检验预测: 改变输入功率 → T·S·I 保持恒定 (±15%)
```

---

## 十、查询清单

> 当需要深入了解某一主题时，到 vault 中查阅对应文件。

### 🔴 当前执行线相关文档

| 主题 | 查询文档 |
|------|---------|
| B.06 ν_th 详细方案 | `J:\cell-cc\cell-cell\01_工程执行\implementation_plan.实施计划-第二主体（热）构建.md` |
| 热感知架构设计 | `J:\cell-cc\cell-cell\2026-06-continued\analysis_body_sensing_architecture.方向性文档-外皮感受机制的架构设计.md` |
| 皮肤→神经元数学模型 | `J:\cell-cc\cell-cell\2026-06-continued\analysis_skin_neuron_modeling.分析-第二主体（热）的皮肤-神经元建模.md` |
| 6.11 状态报告 (EXP-014/015) | `J:\cell-cc\cell-cell\2026-06-continued\status_report_0611.项目状态报告-2026-06-11.md` |
| L2.09 根因 + 空间记忆方案 | `J:\cell-cc\cell-cell\2026-06-continued\analysis_hypothesis_coordinate_reset(假设评判：自身坐标结构 × 虚位 × 复位耦合).md` |
| C3' 环流耦合完整设计 | `J:\cell-cc\cell-cell\archive\undated\design_homeostatic_circulation.C3-设计-进食-运动-体征的环流耦合.md` |
| C3' 任务清单 (已完成) | `J:\cell-cc\cell-cell\01_工程执行\task.环流耦合实施任务.md` |

### 🔵 架构与决策

| 主题 | 查询文档 |
|------|---------|
| 9 项待决设计决策 | `J:\cell-cc\cell-cell\2026-06\decisions_and_framework.2026.6.4.md` + `decisions_and_framework_cont.2026.6.4.md` |
| v0.9.0 系统全景 | `J:\cell-cc\cell-cell\2026-06\system_state_v0.9.0.2026.6.6.md` |
| v0.9.0 变更日志 | `J:\cell-cc\cell-cell\2026-06\CHANGELOG.2026.6.6.md` |
| 实现审计 (误报修正) | `J:\cell-cc\cell-cell\docs\AUDIT_v1.0.md` |
| 路线图 v1.7.2 | `J:\cell-cc\cell-cell\docs\ROADMAP_v1.7.2.md` |
| 72 项追踪表 | `J:\cell-cc\cell-cell\docs\TRACKER_v1.0.md` |

### 🟢 数理与理论基础

| 主题 | 查询文档 |
|------|---------|
| 完整数学公式 (RC-MOSFET/STDP/Xin/ECM) | `J:\cell-cc\cell-cell\docs\global_G001_math_formulas.md` |
| 系统全景架构图 (ASCII) | `J:\cell-cc\cell-cell\docs\global_G002_architecture.md` |
| 超图数学 (10 维状态空间) | `J:\cell-cc\cell-cell\2026-05\modeling_hypergraph_math.2026.5.22.md` |
| ds²/ν 统一框架 | `J:\cell-cc\cell-cell\2026-05\analysis_unified_master_method.2026.5.24.md` |
| T·S·I 维度统一 | `J:\cell-cc\cell-cell\2026-06\analysis_TSI_metric_unification.2026.6.5.md` |
| 环流架构概念 | `J:\cell-cc\cell-cell\docs\concept_C001_circulation_architecture.md` |
| 内生时空认识论 | `J:\cell-cc\cell-cell\docs\concept_C004_autogenous_spacetime.md` |
| 概念变迁总册 (兼容性矩阵) | `J:\cell-cc\cell-cell\2026-05\analysis_concept_evolution.2026.5.21.md` |

### 🟡 缺陷与追踪

| 主题 | 查询文档 |
|------|---------|
| 14 项退化注册表 | `J:\cell-cc\cell-cell\docs\degradation_registry.md` |
| 18 项修复注册表 | `J:\cell-cc\cell-cell\docs\fix_registry.md` |
| 6 项涌现发现 | `J:\cell-cc\cell-cell\docs\discovery_log.md` |
| 5 条阻塞链 | `J:\cell-cc\cell-cell\docs\SERIAL_DEPENDENCIES_v1.5.md` |
| 矛盾·遗留·生长点 (全量) | `J:\cell-cc\cell-cell\00_Dashboard\矛盾·遗留·生长点.md` |

### 🟣 工程执行过程

| 主题 | 查询文档 |
|------|---------|
| Plan/Walkthrough/Analysis 三角映射 | `J:\cell-cc\cell-cell\00_Dashboard\Plan-Walkthrough-Analysis三角映射.md` |
| 所有 implementation_plan | `J:\cell-cc\cell-cell\01_工程执行\implementation_plan.*.md` |
| 所有 walkthrough | `J:\cell-cc\cell-cell\01_工程执行\walkthrough.*.md` |
| AI 对话日志 (6.9-6.13 实现会话) | `J:\cell-cc\cell-cell\02_AI对话日志\Refactoring Neural Hypergraph Physics.2026.6.1*.md` |

### 🟠 系统基础

| 主题 | 查询文档 |
|------|---------|
| 术语表 | `J:\cell-cc\cell-cell\2026-05\glossary.2026.5.31.md` |
| 系统叙事 | `J:\cell-cc\cell-cell\2026-05\system_narrative.2026.5.31.md` |
| 前庭链解剖 | `J:\cell-cc\cell-cell\2026-05\nexus_v1_chain_anatomy.2026.5.22.md` |
| 机制总档案 (40+ 机制) | `J:\cell-cc\cell-cell\2026-06-continued\mechanism_archive.nexus_v1 机制总档案.md` |
| 生物对应表 | `J:\cell-cc\cell-cell\2026-06\bio_correspondences.2026.6.4.md` |

---

## 📂 Vault 导航 (如需要)

| 文件 | 作用 |
|------|------|
| `00_Dashboard\核心词条索引.md` | 概念定义字典 |
| `00_Dashboard\理念架构图.md` | 概念层级关系 (ASCII 图示) |
| `00_Dashboard\概念演化链.md` | 概念时间线 (诞生→修正→结晶) |
| `00_Dashboard\概念演化链.canvas` | 概念演化交互式 Canvas |
| `00_Dashboard\架构演化树.canvas` | 决策/降级/未完成 Canvas |
| `00_Dashboard\矛盾·遗留·生长点.md` | 全量矛盾13+遗留37+生长28 |
| `00_Dashboard\Plan-Walkthrough-Analysis三角映射.md` | 319 文件 Plan→Build→Reflect 对应关系 |
| `00_Dashboard\当前方向与缺口追踪.md` | 人类可读的执行优先级 |
