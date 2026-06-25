# 多参数测试结果分析

> 2026-06-05 — T7 + T1/T3/T4 测试结果

---

## 核心发现：推翻了三个假设

### ❌ 假设 1："Xin 总量线性增长"——错误

```
Step    Xin_total   N_bundles   Delta
10k      87.97        33       +88.0 (初始)
50k     132.65        38        +3.6 (趋缓)
60k      78.78        38       -53.9 (大幅下跌!)
90k      87.28        38        +2.1 (稳定)
```

Xin 总量在 50k 达到峰值后**回落并稳定**在 ~87。不是线性增长。

### ❌ 假设 2："synapse_gain 是增长因子"——错误

| synapse_gain | @20k col max |
|-------------|-------------|
| 10.0 | 6.948 |
| 3.0 | 6.948 |
| 1.0 | 6.948 |

**synapse_gain 从 10 降到 1，对影子 col 激活值零影响。**

这意味着：影子 col 的激活**不是由 bundle 传播（STDP 权重 × gain）驱动的**，
而是由 **Xin 直接输入**驱动的。

### ✅ 假设 3（部分）："XIN_GAIN 是主因"——确认

| XIN_GAIN | @20k col max | 相对 baseline |
|----------|-------------|--------------|
| 3.0 | 6.948 | 100% |
| 1.0 | 5.976 | 86% |
| 0.3 | 4.615 | 66% |

XIN_GAIN 有显著效果，但即使降到 0.3，col 最大激活仍然 4.6。

---

## 真正的信号链

测试揭示了影子 col 增长的真正路径：

```
主层前庭链 Xin（met→hc: 5.2, hc→aff: 9.7）
  ↓ × XIN_GAIN = 3.0
  ↓ = 15.6 ~ 29.1 输入电流  ← 这是关键!
  ↓
影子 enc 神经元（non-spiking, C=3, R=5）
  V_ss = I × R / (1 + VR) ≈ 29 × 5 / 6 ≈ 24
  activation = gm × (V - 0.01) ≈ 24
  ↓
影子 enc→col bundle（synapse_gain doesn't matter）
  ↓  影子 enc 的高激活值本身就足以驱动 col
  ↓
影子 col 神经元
  activation = 6.95
```

> [!IMPORTANT]
> **根因不是 Xin 增长，不是 synapse_gain，而是：**
> **前庭链 Xin 本身就很大（5~20），乘以 XIN_GAIN=3 后直接灌入 non-spiking 影子 enc，无硬上界。**

---

## Xin 的分布不均匀

| Bundle 类型 | Xin 平均值 | 占总 Xin % |
|------------|-----------|-----------|
| hc→aff | 9.71 | **66%** |
| met→hc | 5.20 | **35%** |
| col→mot | 0.47 | 3% |
| enc→col | 0.18 | 1% |
| aff→enc | 0.14 | 1% |

前庭链（met→hc + hc→aff）占主层 Xin 总量的 **95%**。

> [!NOTE]
> 这说明前庭链的预测误差天然就大。
> BIO 验证：前庭系统的 adaptation 确实比高层慢（前庭核的 time constant ~20s）。
> 前庭 Xin 大 ≠ 系统异常。这是预期的。

---

## shadow→DA bundle 自身的 Xin 异常

```
shad→DA: Xin_avg = 105.5  (是 hc→aff 的 10 倍!)
```

shadow→DA bundle 的 Xin 极大，因为：
- pre = shadow col activation ≈ 7.0（高）
- post = DA neuron activation ≈ 0（差分对导致）
- STDP 判定预测误差 = 7 - 0 = 7 → Xin 积累

如果 DA 从差分对恢复为单通路，DA 有活动后，shadow→DA 的 Xin 会正常化。

---

## 修订的根因排序

| 排名 | 根因 | 证据 | 修复方向 |
|------|------|------|---------|
| 1 | **Non-spiking 无硬上界** | gain=1/3/10 结果相同 → VR 和增益无法限制 | 影子层引入 spiking 或硬 clamp |
| 2 | **前庭链 Xin 天然大** | met→hc=5.2, hc→aff=9.7 | 不应修改（BIO 正确），但 XIN_GAIN 需适配 |
| 3 | **XIN_GAIN=3.0 对大 Xin 过高** | xin=0.3 → col=4.6 vs xin=3.0 → col=7.0 | 归一化 Xin（除以 bundle Xin 的 max/mean）|
| 4 | **差分对完全对消** | DA=0（当前代码状态） | 恢复单通路或重新设计 |

---

## 修复候选方案（修订版）

### 方案 A：影子 col 引入 Spiking

```python
# shadow col config:
spiking=True,
v_peak=0.5,    # 硬上界
v_reset=0.1,
```

**效果**：activation ≤ firing_rate_max。无论输入多大，col 激活有硬上界。
**风险**：影子层原本设计为连续（rate coding），引入 spiking 改变了信息编码方式。
STDP 从 BCM（rate-based）变成 spike-timing-based，这可能影响权重收敛。

### 方案 B：Xin 归一化输入

```python
# 在 shadow observe 中，归一化 Xin：
xin_values = [abs(b.config.xin_tension) for b in circuit.get_all_bundles()]
xin_max = max(xin_values) if xin_values else 1.0
for b in circuit.get_all_bundles():
    xi_normalized = abs(b.config.xin_tension) / max(xin_max, 0.01)
    # xi_normalized ∈ [0, 1]，无论 Xin 绝对值多大
```

**效果**：影子 enc 输入 ∈ [0, XIN_GAIN]，有界。
**风险**：丢失 Xin 绝对值信息（10 和 0.1 都被归一化到相同范围）。

### 方案 C：影子层 VR 参数匹配主层

当前影子 VR = 0.01（主层 = 0.05~0.5）。
如果匹配到主层水平（vr_base_rate=0.5），VR 能更有效抑制。

但 T3 结果表明 gain 无效 → VR 也可能无效（同样原因：输入太大，
VR max_rate=5.0 远小于输入电流）。

### 方案 D：组合（推荐）

1. Xin 归一化（方案 B）—— 解决输入有界性
2. 影子 col spiking（方案 A）—— 解决输出有界性  
3. 恢复 DA 单通路 —— 用 VR 做慢适应

三者组合提供**输入有界 + 输出有界 + 新奇检测**。

---

## 下一步

等待你对方案 A/B/C/D 的选择或修改意见。
不会在没有你确认的情况下修改代码。
