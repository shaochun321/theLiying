# Neuron — RC膜 + MOSFET阈值 + 双模式

## 物理对应

- **BIO**: 神经元膜电位 + 动作电位
- **EE**: RC 电路 + MOSFET 阈值开关 + FatigueCapacitor

## 文件

[neuron.py](../../components/neuron.py)

## 功能

系统中所有神经元的统一实现。通过 NeuronConfig 参数化为不同层级：
- MET/HC: continuous, τ_m=0.25
- Aff: spiking, τ_m=0.5, CRI
- Encoding: continuous, τ_m=0.25
- Column: continuous, τ_m=0.25
- Motor: spiking, τ_m=0.25, FatigueCapacitor

## 关键类

| 类 | 功能 |
|---|---|
| NeuronConfig | 参数化配置 |
| Neuron | 统一神经元 |
| CRI (CalciumRateIntegrator) | Ca²⁺ 积分器 (Aff 用) |
| FatigueCapacitor | 疲劳电容 (Motor 用) |

## 关键参数

| 参数 | 含义 | 典型值 |
|---|---|---|
| tau_m | RC 时间常数 | 0.25-0.5 |
| v_threshold | MOSFET 开启电压 | 0.1-0.35 |
| alpha_ema | 激活 EMA 平滑系数 | 0.01 |
| spiking | 是否脉冲模式 | true/false |

## 理论

- T001: 能量守恒 (E_in = I×V, E_leak = V²/R)
- T002: pre_trace/post_trace 提供 STDP 信号

## 修改历史

| 版本 | 变更 |
|---|---|
| v1.0 | 基础 RC+MOSFET |
| v1.3 | 添加 CRI |
| v1.5 | 添加 FatigueCapacitor |
| v1.6 | 编码 bias 和阈值调整 (C2 fix) |
