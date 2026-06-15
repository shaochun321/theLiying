# nexus_v1 构建日志 — 生物参数推导与信号全通

> **日期**: 2026-05-22
> **阶段**: 从 1/6 信号深度到 6/6 全通
> **方法**: 建模先行 + 熵账本审计 + 文献溯源

---

## 信号堵因定量分析

### 堵因定位（熵账本 → Layer 3 DEAD）

```
release_rate = 0.011
bundle_weight = 0.3, memristor_G = 0.14
I_input = 0.011 × 0.14 = 0.0015
V_ss = I × R = 0.0015 × 10 = 0.015
v_peak = 0.3
V_ss / v_peak = 5% ← 只有阈值的 5%
```

### 归一化方案

```
V_norm = (V_bio + 80) / 130
E_K = 0.000, V_rest = 0.115, V_thresh_Ca = 0.308
V_thresh_K = 0.385, V_peak = 0.615, V_reset = 0.077
```

### 生物文献 → 参数

| 参数 | 文献值 | 归一化值 | 来源 |
|------|--------|---------|------|
| C_m (毛细胞) | 5 pF | 1.0 | Eatock & Songer 2011 |
| τ_m | 5 ms | r_leak=5.0 | Eatock & Songer 2011 |
| g_MET | 30 nS | 1.0 | Fettiplace & Kim 2014 |
| g_K(BK) | 20 nS | 0.67 | Eatock & Songer 2011 |
| g_Ca(CaV1.3) | 5 nS | 0.17 | Eatock & Songer 2011 |
| τ_Ca_decay | 100 ms | Ca_C×Ca_R=100 | Roberts et al. 1990 |
| Afferent 放电率 | 50-100 Hz | - | Goldberg 2000 |
| Regular τ_adapt | 200-500 ms | 300 | Goldberg 2000 |
| Irregular τ_adapt | 5-20 ms | 10 | Goldberg 2000 |
| Ribbon EPSC | 20-700 pA | weight=0.8 | Bao et al. 2003 |

## 修复清单

| 修复项 | 修改 | 效果 |
|--------|------|------|
| tau_gate 单位 | 5.0 → 0.005 | K通道正常开放 |
| Ca capacitance | 0.5 → 0.2 | Ca电压积累加速 |
| HC→Aff weight | 0.3 → 0.8 | 带状突触高效传导 |
| v_peak (afferent) | 0.3 → 0.23 | 生物推导阈值 |
| v_rest (HC) | 0 → 0.115 | 正确静息电位 |
| pre_trace/activation | 统一 pre_trace | spiking/non-spiking 分离 |
| activation clamp | 无 → ±10 | 防止正反馈爆炸 |
| synapse_gain | 1.0 → 5/80/40/20/10 | 补偿 dt=0.001 缩放 |

## 结果

```
信号深度: 1/6 → 6/6
总脉冲:   2078
耗散:     71.35 (从 4055 降至 71)
```
