# 增益链零信号 — 修正诊断与方案

> [!CAUTION]
> 之前的诊断有误：**Enc/Col 是非脉冲神经元** (`spiking=False`)。v_peak 对它们无效。问题不是 spike 阈值，而是**信号逐层衰减**。

## 信号追踪（实测数据 5000 步）

```
Aff pitch (spiking)
  pre_trace = 0.643
  ↓ vest_to_enc bundle: gain=1.0, w=0.21
  ↓ I_in = 0.643 × 0.21 × 1.0 × conduct = ~0.13

Enc pitch (NON-spiking)
  Vm = 0.374 → activation = gated_conduct(0.374) = 0.119
  ↓ enc_to_col bundle: gain=1.0, w=0.14
  ↓ I_in = 0.119 × 0.14 × 1.0 × conduct = ~0.029

Col pitch (NON-spiking, C=2.0)
  Vm = 0.033 → activation = 0.8 × (0.033-0.01) = 0.018
  ↓ col_to_motor bundle: gain=5.0, w=0.20
  ↓ I_in = 0.018 × 0.20 × 5.0 = ~0.018

Mot (spiking, v_peak=0.2)
  bc_current = 0.032 → V_ss_bc = 0.16
  signal_current = 0.018 → V_ss_signal = 0.018 × 5 = 0.09
  >>> bc_current (0.16V) >> signal (0.09V)
  >>> Motor fires from bc noise, not from signal
```

## 衰减分析

| 段 | 输入 | 输出 | 衰减 | 原因 |
|----|------|------|------|------|
| Aff→Enc | 0.643 | 0.119 | **×0.19** | gain=1.0, w=0.21, memristor conduct |
| Enc→Col | 0.119 | 0.018 | **×0.15** | gain=1.0, w=0.14, C=2.0 拖慢充电 |
| Col→Mot | 0.018 | 0.018 | ×1.0 | gain=5.0 补偿了 w=0.2 |
| **总** | **0.643** | **0.018** | **×0.028** | 信号衰减到 2.8% |

Motor 的 bc=0.032 产生 V=0.16，信号只有 0.09V — 信号被偏置电流淹没。

## 修复方案（修正版）

目标：让信号在 Motor 上超过 bc 基线贡献。

### 改动 1：提高 Enc→Col synapse_gain

当前 gain=1.0，需要至少 ×3 让 Col Vm 从 0.033 上升到 ~0.10：

```python
# enc_to_col bundle
synapse_gain = 1.0 → 3.0  
```

Col Vm_new ≈ 0.029 × 3 × 5 = 0.435 → activation ≈ 0.8 × 0.425 = 0.34

### 改动 2：降低 Col 电容

C=2.0 → 1.0。τ 从 10ms 降到 5ms，充电更快。

```python
# _column_config
capacitance = 2.0 → 1.0
```

### 改动 3：提高 Aff→Enc synapse_gain  

当前 gain=1.0，Afferent pre_trace=0.64 但到 Enc 只剩 0.13。提高到 2.0：

```python
# vest_to_enc bundles
synapse_gain = 1.0 → 2.0
```

### 不改动

- Enc/Col 的 v_peak：**不动**，它们是非脉冲，v_peak 无关
- Motor 的 bc_current：**不动**，baseline firing 是设计需要
- col_to_motor gain=5.0：**不动**，已经合理

### 预期效果

```
信号链修复后:
  Aff pre_trace = 0.64
  → Enc: gain=2.0 → I=0.26 → Vm≈1.3 → act≈1.0 (saturation)
  → Col: gain=3.0, C=1.0 → I=1.0×0.14×3.0=0.42 → Vm=2.1 → act=0.8×2.09=1.67
  → Mot: gain=5.0 → I=1.67×0.2×5.0=1.67 → V_signal >> V_bc
```

太大了，需要平衡。让我用更保守的值：
- vest_to_enc: gain 1.0 → 2.0
- enc_to_col: gain 1.0 → 3.0  
- Col C: 2.0 → 1.0

实际需要用诊断脚本调到 Motor V_signal ≈ 2-3× V_bc。

## 验证计划

1. 改参数 → 5000 步诊断 → 确认每层信号非零
2. Governance 测试 → 确认不 trip
3. 50k 验证 → 增益链数值、Noether、权重
