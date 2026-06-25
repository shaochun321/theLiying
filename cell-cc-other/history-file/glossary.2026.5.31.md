# 术语表 — cell-cc 项目

## 结构组件

| 术语 | 中文 | 定义 | 代码位置 |
|------|------|------|---------|
| **Neuron** | 神经元 | 统一模型：膜电压+通道+代谢。可配置为简单阈值、毛细胞、脉冲神经元 | `neuron.py` |
| **Bundle** | 束 | 一组从源到靶的突触连接（Memristor 阵列）。信息传输的基本单位 | `bundle.py` |
| **Memristor** | 忆阻器 | 单个突触权重。记忆电阻器，电流=权重×输入 | `semiconductor.py` |
| **MOSFET** | 场效应管 | 阈值门控元件。当输入>阈值时导通 | `semiconductor.py` |
| **Capacitor** | 电容器 | 膜电压存储。充放电模拟膜动力学 | `semiconductor.py` |
| **PowerRail** | 电源轨 | 代谢能量供应。能量耗尽→神经元停止工作 | `semiconductor.py` |
| **ECM** | 细胞外基质 | 每层的热场+离子缓冲+PNN(围神经元网络) | `ecm.py` |

## 信号通路层次

| 术语 | 中文 | 定义 |
|------|------|------|
| **Met** (L1) | 机械转导 | 输入信号→电流（MOSFET阈值门控） |
| **HC** (L2) | 毛细胞 | 3通道放大+Ca²⁺释放 |
| **Aff** (L3) | 传入神经元 | 脉冲生成（AdEx模型），regular/irregular 双通路 |
| **Enc** (L4) | 编码神经元 | 正则+不正则编码融合 |
| **Col** (L5) | 柱状神经元 | 多源整合→决策输出 |
| **Motor** (L6) | 运动神经元 | 脉冲输出→肌肉收缩 |
| **Binding** | 绑定层 | 跨模态共激活检测（C(7,2)=21 对） |

## 生长机制

| 术语 | 中文 | 定义 | 触发条件 |
|------|------|------|---------|
| **Sprout** | 发芽 | 创建新 Bundle（新连接通路）| bundle 的 \|ξ\| > XI_SPROUT=0.3 |
| **Prune** | 修剪 | 删除弱 Bundle | 权重 < W_PRUNE=0.001 |
| **Mitosis** | 有丝分裂 | Motor 神经元分裂为母+子 | FatigueCapacitor 电压持续高于阈值 |
| **Apoptosis** | 凋亡 | 删除能量耗尽的神经元 | 能量持续低于阈值 |
| **Maturation** | 成熟 | 神经元从高可塑→低可塑的阶段转变 | 累积激活量 Φ 超过阈值 |

## 信息量

| 术语 | 中文 | 定义 | 公式 |
|------|------|------|------|
| **ξ (xi)** | 预测张力 | Bundle 的累积预测误差 | $\xi += (predicted - actual) \cdot dt$ |
| **Xin** | 信息张力 | ξ 的绝对值，驱动结构生长 | $X_{in} = \|\xi\|$ |
| **STDP** | 脉冲时序依赖可塑性 | 权重更新规则：因果方向增强，反因果减弱 | $\Delta w = \eta(pre_{t-1} \cdot post_t - pre_t \cdot post_{t-1})$ |
| **DA** | 多巴胺 | 三因子学习调制。编码 \|dξ/dt\|（惊喜信号） | DA > baseline → 加速学习 |
| **EMA** | 指数移动平均 | 脉冲序列→连续放电率的低通滤波 | $ema += \alpha \cdot (fired - ema)$ |

## 物理系统

| 术语 | 中文 | 定义 | 代码 |
|------|------|------|------|
| **Body** | 身体 | 3D 空间中的质点。位置+速度+加速度 | `world.py` |
| **World** | 世界 | 100³ 环形空间 + 热源 | `world.py` |
| **MuscleSystem** | 肌肉系统 | Motor EMA → 力（带延迟） | `muscle.py` |
| **Otolith** | 耳石 | 加速度传感器（acc × 500） | `variant_adapter.py` |
| **ThermalMembrane** | 热感膜 | 标量温度传感器 + 甲基化适应 | `thermal_membrane.py` |
| **Oscillator** | 振荡器 | 每轴一个内在振荡器，调制 Aff 膜电压 | `variant_adapter.py` |
| **Kinetic Damping** | 运动阻尼 | 速度越快→力越小: $k=1/(1+v/0.5)$ | `world.py` |

## 治理与守恒

| 术语 | 中文 | 定义 |
|------|------|------|
| **Noether Probe** | 诺特探针 | 检查能量守恒：输入=输出+存储变化 |
| **Governance** | 治理系统 | 平行监督系统：Fuse+Ledger+Modeler |
| **Fuse** | 熔断器 | 异常检测：权重越界、增益爆炸等 |
| **Ultrametric** | 超度量 | Bundle 的层次距离树（分裂历史记录） |
| **TOPRXin Ledger** | 信息账本 | 追踪全局 Xin 的产生和消耗 |

## 元概念（你的理论框架）

| 术语 | 中文 | 定义 | 当前代码状态 |
|------|------|------|------------|
| **Fruit** | 果实 | Bundle 的生命周期状态：dormant→growing→ripe→decayed | `bundle.py` fruit_state 字段 |
| **Circulation** | 环流 | 信息在结构中的循环流动（P→R→P'） | `circulation.py` 存在但效果为零 |
| **Efference Copy** | 传出副本 | 运动命令的内部预测：motor→预测的感觉反馈 | P0 修复新增 |
| **Motor Efficacy** | 运动效能 | motor 输出是否产生预期效果（0-1） | P0 修复新增 |
| **切分** | 切分 | 系统在客观时空上选取的测量尺度 | 你的哲学概念，未编码 |
| **回荡** | 回荡 | Xin 在被限制的结构中振荡不收敛 | 2M 实验中观察到 |

## 物理常数

| 常数 | 值 | 含义 |
|------|-----|------|
| dt | 0.001 | 时间步长（1ms） |
| μ (friction) | 0.5 | 粘性阻力系数 |
| mass | 1.0 | 身体质量 |
| muscle gain | 0.1 | EMA→力的转换增益 |
| oto_scale | 500 | 加速度→前庭信号的放大倍数 |
| XI_SPROUT | 0.3 | 触发发芽的 Xin 阈值 |
| MAX_MOTORS_PER_AXIS | 20 | 每轴最大 motor 数（P2 新增） |
| SPROUT_INTERVAL | 10000 | 结构生长检查间隔（10s） |
