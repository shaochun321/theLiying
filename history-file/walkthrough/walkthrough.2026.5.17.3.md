# v40.10c Walkthrough — 完整实践层

## 架构总览

```
量源(物理)
  acoustic (7.5,0,0) 1/r
  thermal  (0,7.5,0) 1/r²
  luminous (0,0,7.5) 1/r²
     ↓
前庭层 (10 neurons)
  lever_X, dlever_X, integ_X × 3源 + angular_vel
     ↓
IntegratorColumn (leaky + log)
  state(t+1) = (1-λ)·state(t) + gain·log(1+|input|)
  CPG correction → λ_eff
     ↓
Practice Cortex (px_ 结晶)
  px_dlev_inte: act=-0.899 (前庭→积分模式)
  px_inte_move: act=-0.880 (积分→运动模式)
  px_inte_inte: act=-0.021 (跨模态模式)
     ↙       ↘
motor        encoding
  ↓              ↑
physics ——→ vestibular
```

## 关键指标 (1000 tick)

| 指标 | 值 |
|---|---|
| μ(G) | 1.014 (稳定) |
| px_ crystallized | 3 |
| px_ max activation | -0.899 |
| practice_cortex occ | 0.963 |
| Discrimination | ✅ YES |
| Active dimensions | exploit=3, explore=5, refine=5 |
| Inter-layer bundles | 36 |
| 物理衰减精度 | ratio=1.000 |

## 三源平衡 (t=800-999)

| 量源 | avg |L| | avg dL/dt | recv |
|---|---|---|---|
| acoustic | 11.50 | -0.002 | 0.437 |
| luminous | 7.96 | +0.011 | 0.084 |
| thermal | 8.74 | -0.004 | 0.044 |

系统趋向平衡：dL/dt → 0，积分器在零点附近振荡。

## 降级记录 (14项)

| # | 完整版 | 降级版 |
|---|---|---|
| 1 | 具身身体 | 粒子力代理 |
| 2 | 连续PDE场方程 | 点源 1/r^n |
| 3 | 6轴IMU (3+3) | 标量力臂率 |
| 4 | Einstein 倾斜-平移等价 | 忽略 |
| 5 | 小脑坐标变换 | 恒等映射 |
| 6 | 连续吸引子 | 阈值检测 |
| 7 | 完整波方程 | 静态衰减 |
| 8 | 推迟势 (retarded potential) | 即时 |
| 9 | 刚体质心 | 粒子平均 |
| 10 | 分布式 NPH/MVN 积分网络 | 单标量积分 |
| 11 | 群体 lognormal 增益 | 单样本 |
| 12 | SMA→M1→脊髓分层运动 | 单层 px_ |
| 13 | 6层皮层柱微电路 | 单 px_ 神经元 |
| 14 | 基底节选择门控 | 环流阈值门控 |

## 熵账本 (3表)

- `v40_quantity_source_ledger`: lever_arm, lever_rate, received_value, gradient_mag, work
- `v40_integrator_ledger`: state, lambda_eff, gain, cumulative_input, cumulative_leak, retention, peak
- `v40_signal_entropy_ledger`: 7-channel signal entropy per window
