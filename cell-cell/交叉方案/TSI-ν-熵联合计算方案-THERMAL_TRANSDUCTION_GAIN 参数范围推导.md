# TSI-ν-熵联合计算方案：THERMAL_TRANSDUCTION_GAIN 参数范围推导

**日期**: 2026-07-02
**目标**: 利用 TSI 功率账本、运动势 ν 探针、熵账本三套数理工具，计算出使 relay 在 d=20 激活的 `THERMAL_TRANSDUCTION_GAIN` 有效范围，替代试探性调参
**前置条件**: NoetherProbe（已就位）、ν探针（Phase 1 已实现）、WeightEntropyProbe（已就位）、P2 诊断报告 relay.vm vs 距离映射（已有）


## 一、核心原理

三个约束联合求解参数范围：

| 约束来源 | 计算目标 | 公式 |
| :--- | :--- | :--- |
| **TSI 功率账本** | 增益上限 | `P_T(gain) ≤ P_input × 0.8` |
| **ν 运动势** | 增益下限 | `ν(gain) > 0 @ d=20`（系统进入探索态） |
| **熵账本** | 有效性验证 | `H > 0` 且 `dH/dt < 0`（信息在固化） |

三个约束联合定位出一个区间 `[gain_min, gain_max]`，在此区间内选值，单次验证。


## 二、步骤 1：实测 P_T vs relay.activation 关系

### 目的

建立 relay 激活水平与系统功率消耗之间的精确函数关系，用于 TSI 约束计算。

### 方法

运行 `nexus_v1/tests/exp_calibrate_pt_vs_relay.py`：

```
场景：body 固定在 [60, 50, 25]（d=20），热源 S1=[80, 50, 25]
扫描参数：THERMAL_TRANSDUCTION_GAIN ∈ {0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5}
每点运行：5000 步，记录末尾 2000 步平均值
测量项：P_T_total, P_T_relay_layer, relay_activation_mean, relay_vm_mean
输出：P_T vs gain 曲线
```

### 预期输出

一条增益-功率响应曲线，可直接查出任一增益值对应的 P_T 增量。


## 三、步骤 2：TSI 约束计算 — 增益上限

### 公式

```
P_T_total(gain) = P_T_baseline + ΔP_T_relay(gain)

P_T_baseline：增益=0.1 时的总传输功率（从步骤1实测）
ΔP_T_relay(gain)：relay 层随增益增加的功率增量（从步骤1曲线查得）

安全约束：P_T_total(gain_max) ≤ P_input × 0.8

P_input 取值：从 EnergyStore 最近 50k 步的平均 fill_fraction × capacity / τ_drain
保守估计：P_input ≈ 0.0032 fill/step（与 P2 诊断报告中 drain/10k 数据一致）
```

### 计算

代入步骤1的实测曲线，求解增益上限：

```
gain_max = max{gain | P_T_total(gain) ≤ P_input × 0.8}
```

### 预期输出

一个具体的增益上限值（例如 gain_max ≈ 2.0）。


## 四、步骤 3：ν 约束计算 — 增益下限

### 目的

确定使 relay 在 d=20 处开始激活的最低增益值。

### 方法

运行步骤1的扫描数据中，同时记录 ν 探针数据：

```
同一扫描实验中，每点记录：
  system_ν_ema（ν探针）
  relay_activation_mean
  charging_fraction（ν探针）

增益下限判定：
  gain_min = min{gain | relay_activation_mean > 0.01 且 ν > 0}
```

relay_activation_mean > 0.01 确认 relay 已越过噪声门槛开始激活。ν > 0 确认系统进入探索态而非随机游走。

### 预期输出

一个具体的增益下限值（例如 gain_min ≈ 1.2）。


## 五、步骤 4：熵约束验证 — 学习确认

### 目的

在计算出的增益区间内，确认参数调整确实导致学习发生，而非纯粹噪声放大。

### 方法

选择增益值 = (gain_min + gain_max) / 2（区间中值）。运行 `exp_validate_entropy.py`（50k 步，body 从 d=20 出发）：

```
每 5k 步记录：
  relay_to_enc_{pid} 各束的 Xin 张力
  WeightEntropyProbe.dH/dt（信息熵变化率）
  WeightEntropyProbe.H（当前信息熵）

判定：
  阶段1（0-25k步）：H > 0 确认（信息开始注入）
  阶段2（25-50k步）：dH/dt < 0 确认（信息在固化）
```

### 预期输出

H 时间序列呈现“先升后降”的学习特征曲线；dH/dt 在后期 < 0。


## 六、步骤 5：选定增益值，单次验证

### 原则

在 `[gain_min, gain_max]` 区间内选择一个最终值，不逐步试探。

### 策略

若区间较宽（gain_max/gain_min > 1.5）：选 70% 分位值（偏保守上限）。若区间较窄：选中值。

### 执行

运行 Phase 3 三热源实验 500k 步（使用选定增益值）。验收标准：relay_to_enc 权重在 100k 步内产生方向性分化（|Δw| > 0.02）；DR5 > 50%。


## 七、总执行流程

```
步骤 1：实测 P_T vs gain 关系
    ↓
步骤 2：计算 gain_max（TSI 上限）
步骤 3：计算 gain_min（ν 下限）
    ↓
确定有效区间 [gain_min, gain_max]
    ↓
步骤 4：在区间中值处运行熵验证（确认学习发生）
    ↓
步骤 5：选定最终增益值，单次 500k 验证
```

## 八、所需新建文件

| 文件 | 用途 |
| :--- | :--- |
| `nexus_v1/tests/exp_calibrate_pt_vs_relay.py` | 步骤1：P_T vs gain 扫描 |
| `nexus_v1/tests/exp_validate_entropy.py` | 步骤4：熵验证 |


## 九、物理意义

这套流程不是“用 TSI/ν/熵去调参”。它是在参数空间中，利用物理定律精确筛选出使系统维持物理一致性的有效区域。任何落在这个区域内的参数值都是可接受的选择——剩下的只是工程偏好（保守/激进）。从“试探性调参”到“物理约束下的参数推导”，这是项目方法论的根本升级。