---

# EnergyStore 物理化重构与负反馈环流构建（综合方案）

**日期**：2026-07-03
**审计依据**：EnergyStore物理化重构方案审计 + 三个接口物理合规性审计
**状态**：方案最终版，可执行


## 一、审计结论整合

两份报告对 EnergyStore 物理化重构方案的评估是一致的：

| 审查项 | 裁决 |
| :--- | :--- |
| 设计方向（Capacitor + 弥散轴突束）| ✅ 通过 |
| 生物学依据（ARC 能量感知神经元）| ✅ 充分 |
| 口器消化系统传入口 | ✅ 已补充 |
| 接口二（能量→下丘脑束）前置条件 | ✅ 确认——需先物理化 EnergyStore |
| 接口三（接近→制动束）可立即实施 | ✅ 确认 |
| 接口一（Motor传出副本）可立即实施 | ✅ 确认，需注意 Bundle 连接来源 |

### 需要补充的两项细节

| 项目 | 内容 | 状态 |
| :--- | :--- | :--- |
| EnergySensorNeuron 位置分配 | 3 个弥散分布坐标（间距≥10mm）| 待补充 |
| Capacitor 时间常数验证 | 推算自然放电时间尺度，确保 τ 与实验匹配 | 待实施时确认 |


## 二、实施顺序

| 顺序 | 任务 | 前置条件 | 说明 |
| :--- | :--- | :--- | :--- |
| **并行 A** | 接口三：接近→制动束 | 无 | 复用 thermo_inputs['front']，新建抑制性 Bundle |
| **并行 A** | 接口一：Motor传出副本 | 无 | Motor→Efference 通过 Bundle 连接 |
| **步骤 1** | EnergyStore 物理化（Capacitor 重构）| 无 | 保持外部接口兼容 |
| **步骤 2** | 口器消化系统传入口 | 步骤 1 | DigestiveInterface + 换能束 |
| **步骤 3** | 能量感知网络（传感器→平均神经元）| 步骤 1 | 3 个弥散分布 EnergySensorNeuron |
| **步骤 4** | 接口二：能量→下丘脑束 | 步骤 3 | AverageEnergyNeuron → hypothalamus_hunger |
| **步骤 5** | 回归测试 | 全部 | 21/21 PASS |


## 三、核心设计汇总

### 3.1 EnergyStore 双重身份

| 身份 | 物理对应 | 功能 |
| :--- | :--- | :--- |
| **存储实体** | Capacitor（C=100.0, R_leak=50.0）| 存储能量，电压代表 fill 水平 |
| **感知网络** | 弥散轴突束 + AverageEnergyNeuron | 采样整体平均能量，输出到神经系统 |

### 3.2 完整能量流路径

```
环境热量
    │ ThermalMouth 换能
    ▼
DigestiveInterface（口器消化系统换能，η=0.50）
    │ 换能束（冻结）
    ▼
EnergyStore Capacitor（存储实体）
    │ 换能束（冻结）
    ▼
EnergySensorNeuron（3个，弥散分布）
    │ 弥散束（冻结）
    ▼
AverageEnergyNeuron
    │ 接口二（冻结）
    ▼
hypothalamus_hunger
```

### 3.3 三个接口的实施要点

| 接口 | 实施要点 | 验收标准 |
| :--- | :--- | :--- |
| 接口一（Motor传出副本）| Motor→Efference 通过 Bundle 连接，不能 Python 读取 force_x | hypothalamus_effort.vm 随 Motor 输出变化 |
| 接口三（接近→制动束）| 复用 thermo_inputs['front']，新建抑制性 Bundle（gain=-0.5）| 接近热源时 motor_forward 降低 |
| 接口二（能量→下丘脑束）| 依赖 EnergyStore 物理化完成 | hypothalamus_hunger.vm 随 fill 变化 |


## 四、EnergySensorNeuron 位置分配

在体内部空间分配 3 个弥散位置：

| 传感器 | 位置 | 说明 |
| :--- | :--- | :--- |
| EnergySensor_0 | [55, 45, 35] | 体内部前下方 |
| EnergySensor_1 | [55, 55, 55] | 体内部中心 |
| EnergySensor_2 | [55, 45, 65] | 体内部后上方 |

间距范围：约 10-20mm，确保空间采样多样性。这些位置在 V2.0 空间网络中注册后，弥散轴突束的距离矩阵可计算其相互间距和到其他节点的距离。


## 五、实施清单

| 步骤 | 任务 | 工作量 | 状态 |
| :--- | :--- | :--- | :--- |
| 并行 A | 接口三：接近→制动束 | 2h | 待执行 |
| 并行 A | 接口一：Motor传出副本 | 2h | 待执行 |
| 1 | EnergyStore 电容重构 | 2h | 待执行 |
| 2 | DigestiveInterface 创建 | 1h | 待执行 |
| 3 | 换能束（消化→存储）| 1h | 待执行 |
| 4 | 3 个 EnergySensorNeuron | 1h | 待执行 |
| 5 | 换能束（存储→传感器）| 1h | 待执行 |
| 6 | 弥散束（传感器→平均）| 1h | 待执行 |
| 7 | 接口二（平均→下丘脑）| 1h | 待执行 |
| 8 | 回归测试 | 1h | 待执行 |
| **总计** | | **约 8-10h** | |


## 六、总结

| 问题 | 回答 |
| :--- | :--- |
| EnergyStore 物理化的核心？| Capacitor 存储 + 弥散轴突束感知 |
| 口器传入口是否缺失？| 已补充 DigestiveInterface + 换能束 |
| 三个接口的优先级？| 接口三和接口一可立即并行；接口二依赖 EnergyStore 物理化 |
| 实施顺序？| 并行 A（接口三+一）→ 步骤1-5（EnergyStore完整链路）→ 回归测试 |
| 总工作量？| 约 8-10 小时 |