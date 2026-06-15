# v40.10b Walkthrough — IntegratorColumn + 环路闭合

## 核心变更

### IntegratorColumn (practice_engine.py)

```python
state(t+1) = (1 - λ_eff) × state(t) + gain × log(1+|input|) × sign(input)
λ_eff = max(0.001, λ_base - CPG_correction)
gain ~ lognormal(μ=0, σ=0.3)
```

| 降级 | 完整版 | 当前版 |
|---|---|---|
| 分布式积分器 | NPH/MVN 神经网络 | 单标量 leaky integrator |
| 群体 lognormal 增益 | N个神经元的增益分布 | 单 lognormal 采样 |

### 环路闭合 (circuit bundles)

```
integ_acoustic/thermal/luminous → move_x/y/z  (w=0.08, 环路闭合束)
integ_acoustic/thermal/luminous → xin_residual/gamma_desync/magnitude  (w=0.04)
```

完整回路：
```
vestibular(dlever) → IntegratorColumn(积分) → integ neuron(持续)
    → motor(束传播) → physics(物理) → lever arm(变化) → vestibular
```

## 结果

### 分辨力突破

| 指标 | 300 ticks (无积分器) | 500 ticks (有积分器) |
|---|---|---|
| Circuit cos | 0.9996 | **-0.333** |
| Improvement | -0.0002 | **+1.333** |
| Discrimination | ❌ NO | **✅ YES** |
| Active dimensions | explore=5, refine=5 | **exploit=5**, explore=3, refine=5 |

### 涌现导航行为

光源力臂轨迹（系统自主靠近了光源）：

```
t=[  0- 99]: luminous avg_L = 9.25  (远)
t=[100-199]: luminous avg_L = 11.1  (更远)
t=[200-299]: luminous avg_L = 3.91  (大幅靠近！)
t=[300-499]: luminous avg_L ≈ 3.8   (稳定在光源附近)
```

接收值从 0.069 → 0.310（靠近后 1/r² 信号增强 4.5x）

### 积分器熵账本

```
acoustic : state=+1.557  ret=0.947  peak=3.61  gain=0.958
thermal  : state=+1.390  ret=0.871  peak=4.89  gain=1.568
luminous : state=+0.004  ret=0.921  peak=3.28  gain=0.730
                   ↑ ≈0 因为已到达目标（平衡点）
```

## 降级记录汇总

| # | 组件 | 完整版 | 降级版 |
|---|---|---|---|
| 1 | 感觉运动 | 具身身体 | 粒子力代理 |
| 2 | 场方程 | 连续PDE | 点源 1/r^n |
| 3 | 前庭 | 6轴IMU | 标量力臂率 |
| 4 | 倾斜-平移消歧 | Einstein 等价 | 忽略 |
| 5 | 参考系变换 | 小脑坐标变换 | 恒等映射 |
| 6 | 环流检测 | 连续吸引子 | 阈值检测 |
| 7 | 波传播 | 完整波方程 | 静态衰减 |
| 8 | 传播延迟 | 推迟势 | 即时 |
| 9 | 观测者质心 | 刚体质心 | 粒子平均 |
| 10 | 分布式积分器 | NPH/MVN网络 | 单标量积分 |
| 11 | 群体增益 | lognormal分布 | 单样本 |

## 熵账本表

- `v40_quantity_source_ledger`: lever_arm, lever_rate, received_value, gradient_mag, work_against_gradient
- `v40_integrator_ledger`: state, lambda_eff, gain, cumulative_input, cumulative_leak, retention_ratio, peak_state
