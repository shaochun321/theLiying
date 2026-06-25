# v40.10c Walkthrough — 完整实践层 + Origin×环流耦合

## 架构总览

```
量源(物理) ←─── 衰减律 1/r^n
     ↓
前庭层 (10 neurons)
  lever/dlever/integ × 3 + angular_vel
     ↓
IntegratorColumn (leaky + log + CPG矫正)
     ↓
Origin×Circulation 耦合
  origin_score = confidence × μ(G)
  bandwidth ← 1.0 + 0.1·μ(G)
     ↓
Practice Cortex (px_ 结晶, 环流门控)
  px_dlev_inte → act=-0.899
  px_inte_move → act=-0.880
  px_inte_inte → act=-0.021
     ↓  ↗motor (强化运动模式)
     → ↘encoding (运动→感知)
     ↓
Circuit propagation → STDP → maintain
     ↓
下一tick物理 → lever arm → 前庭 → ...
```

## 关键指标

| 指标 | 500 tick | 1000 tick |
|---|---|---|
| μ(G) circuit | 0.972 | 1.014 |
| μ(G) origin | 4.21 | — |
| px_ neurons | 3 | 3 |
| px_ max act | -0.899 | -0.899 |
| origin_score max | 3.637 | — |
| crystallizable | 11.4% | — |
| bandwidth | 1.253 | — |
| Discrimination | ✅ YES | ✅ YES |

## Origin×环流耦合

```python
origin_score = confidence × min(μ(G), 5.0)
balance = 1 / (1 + Σ|integ_state|/N)
bandwidth += 0.01 × (1 + 0.1 × μ(G))

crystallizable = (
    confidence > 0.3 AND
    μ(G) > 0.5 AND
    balance > 0.3
)
```

## 降级记录 (15项)

| # | 完整版 | 降级版 |
|---|---|---|
| 1 | 具身身体 | 粒子力代理 |
| 2 | 连续PDE场 | 点源 1/r^n |
| 3 | 6轴IMU | 标量力臂率 |
| 4 | Einstein 等价 | 忽略 |
| 5 | 小脑坐标变换 | 恒等映射 |
| 6 | 连续吸引子 | 阈值检测 |
| 7 | 完整波方程 | 静态衰减 |
| 8 | 推迟势 | 即时 |
| 9 | 刚体质心 | 粒子平均 |
| 10 | 分布式NPH/MVN | 单标量积分 |
| 11 | 群体lognormal | 单样本 |
| 12 | SMA→M1→脊髓 | 单层px_ |
| 13 | 6层皮层柱 | 单px_神经元 |
| 14 | 基底节门控 | 环流阈值 |
| 15 | 分布式皮层自我模型 | 标量score |

## 熵账本 (4表)

- `v40_quantity_source_ledger`: 力臂/速率/接收/梯度/做功
- `v40_integrator_ledger`: 状态/λ/gain/累积/保留/峰值
- `v40_signal_entropy_ledger`: 7通道信号熵
- `v40_origin_circulation_ledger`: 原点位置/置信/带宽/环流/得分/平衡/可结晶
