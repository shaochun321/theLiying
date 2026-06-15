# T003: Fruit 生命周期 — 结构事件触发

> 状态: ✅ 首次验证 v1.7.0 (38 matured, 9 expand, 26 contract)

## 核心概念

Fruit 是将**持续的 Xin 张力**转化为**结构决策**的机制。
不修改权重——只触发 sprout/prune 候选。

BIO: 皮层地图重组 (Merzenich 1984)

## 状态机

```
∅ ──[|ξ| > 0.5]──→ dormant ──[age≥500, DA<0.15]──→ mature
                      │                                │
                      │ [tension reversal]              ├─[ξ>0]→ expand
                      ↓                                 └─[ξ<0]→ contract
                   consumed                                    │
                                                               ↓
                                                expand: sprout_threshold × 0.5
                                                contract: force prune
```

## 双因子门控

| 因子 | 阈值 | 含义 |
|---|---|---|
| DA concentration | < 0.15 | 身体不在主动探索 |
| Sustained tension | age ≥ 500 ticks (50k步) | 预测误差持续存在 |

> **注意**: Standing wave gate 在 v1.7.0 被移除。
> 原因: ZCR 双峰分布 (0.000 或 1.000)，永远不在 [0.05, 0.3] 范围内。
> 果实在整个项目历史中从未成熟过，直到此修复。

## Xin 张力计算 (§7.2)

$$\hat{y}_j = \sum_i W_{ij} \cdot a_i(t-1) \quad \text{(prediction)}$$
$$\xi \mathrel{+}= \sum_j (\hat{y}_j - a_j(t)) \cdot dt \quad \text{(residual)}$$
$$\xi(t+1) = \xi(t) \cdot e^{-dt/\tau_{leak}} + \text{residual} \quad (\tau_{leak}=1000s)$$

## 代码位置

| 文件 | 行 | 功能 |
|---|---|---|
| circuit/bundle.py | L375-434 | compute_xin() |
| circuit/bundle.py | L436-533 | update_fruit() |
| circuit/hebbian.py | L648-650 | expand consumer |
| circuit/hebbian.py | L716-718 | contract consumer |
| circuit/variant_adapter.py | L977-980 | fruit update 调度 (每100步) |

## 实验结果 (v1.7.0, 60k步)

| 通道 | Xin 方向 | 动作 | 含义 |
|---|---|---|---|
| hc_to_aff_oto_x/y/z | +15000 | expand | 活跃轴欠预测 → 需扩容 |
| enc_to_col_* | 正 | expand | 列层需要更多处理 |
| met_to_hc_* | -9900 | contract | 上游过预测 → 裁减 |
| aff_to_enc_* | 负 | contract | 编码层过剩 |

## 修改历史

| 版本 | 变更 |
|---|---|
| v1.5.0 | Fruit 状态机初始实现 |
| v1.5.0 | 三因子门控: DA + SW + sustained tension |
| v1.7.0 | **移除 SW gate** (ZCR 双峰, 永远不在范围内) |
| v1.7.0 | 首次完整运行: 38 matured |
