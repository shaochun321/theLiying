# DopamineModulator — 多巴胺调制系统

## 物理对应

- **BIO**: VTA/SNc DA 系统 → 奖赏信号 → 第三因子学习
- **EE**: RC 积分器 + 衰减 → 浓度信号

## 文件

[modulator.py](../../components/modulator.py)

## 功能

- DA 浓度 = 3 个 VTA DA 神经元的平均激活值
- 输入来源:
  - Shadow→DA bundles (柱状预测信号)
  - Xin→DA bundles (预测误差变化率)
  - C3' deviation 电流 (体征偏激)
- 输出: `gain_factor()` → 柱层增益调制
- D2R 自受体: 防止 DA 饱和 (GIRK 负反馈)

## DA 神经元结构

```
Shadow Col neurons → [Bundle STDP] → DA neuron (τ=2s)
Xin integrator → relay → [Bundle STDP] → DA neuron
DA neuron activation → dopamine.concentration (体积传输)
```

## 关键参数

| 参数 | 值 | 物理意义 |
|---|---|---|
| DA baseline | 0.1 | bc_current × R_leak |
| DA_MATURE_THRESHOLD | 0.15 | Fruit 成熟所需 DA 水平 |
| D2 conductance | 0.5 | GIRK 通道电导 |
| D2 EC50 | 0.3 | D2R 半激活浓度 |
