# 关键发现：论文结论被推翻

> [!CAUTION]
> **论文的核心声明——"衰减律指数决定偏好"——完全错误。**

## 实验证据

```
Position (no sources):   (-4.16, -3.96, 2.75)
Position (with sources): (-4.16, -3.96, 2.75)
Position difference: 0.000000
```

**去除所有量源后，轨迹完全一致。**

交换衰减律、改变振幅、改变leak——结果都一样。

## 根本原因

```
量源 → received_at() → vestibular sensory dict → 返回给 circuit
                                                      ↓
                          但 circuit_motor 在实验中 = {0, 0, 0}！
                                                      ↓
       motor_final = CPG + 0 + reflex(PARTICLE energy, 不是源) + babbling
```

1. **reflex 不使用量源数据**。它使用粒子系统内部的 `energy_H` 和 `spectral_H`
2. **circuit_motor 始终为零**。量源信息返回给 circuit，但 circuit 的输出在实验中被短路了
3. **量源只是被动测量**。它们不影响物理，只提供 lever arm 数据用于记录

## "偏好"的真实来源

"偏好"不是来自衰减律，而是来自：

| 因素 | 效应 |
|---|---|
| **CPG 方向不对称** | x: sin(0.2), y: cos(0.1), z: sin(0.05) — z 振幅最小 |
| **源位置不对称** | acoustic=(7.5,0,0), thermal=(0,7.5,0), luminous=(0,0,7.5) |
| **seed** | 初始粒子位置 + babbling 序列 |

CPG 在 z 方向振幅最小 (0.05)，luminous 在 z 轴。
CPG 在 x 方向振幅最大 (0.2)，acoustic 在 x 轴。
→ 系统在 x 方向移动最多 → 离 acoustic 最远。
→ 系统在 z 方向移动最少 → 离 luminous 最近。

**"偏好"不过是 CPG 各轴振幅的投影。**

## 对论文的影响

| 论文声明 | 实际状态 | 判定 |
|---|---|---|
| n 决定偏好排序 | n 无效 | ❌ **错误** |
| $L^* \sim (nA\sqrt{N}/\sigma)^{1/(n+1)}$ | L* 由 CPG+seed 决定 | ❌ **公式无意义** |
| 系统是 NESS | 确实是非平衡 | ⚠️ 正确但原因不对 |
| 环流自持 37% | CPG+babbling 维持 | ⚠️ 正确但与源无关 |
| 能量守恒 residual=0 | 正确 | ✅ |
| thermal/luminous 分裂 ≈ λ比 | CPG y>z 轴振幅差 | ❌ **错误归因** |

## 修正方向

要使量源真正影响行为，需要：

1. **reflex 使用量源梯度** — 让 avoidance/orienting 响应源强度
2. **或者 circuit_motor 非零** — 使用完整的 hebbian circuit 闭环

目前系统的实验方式（circuit_motor=0）等于切断了感知-动作环的一半。

## 诚实的结论

**在当前实验条件下，项目能发表的是：**
1. 积分器数学精确，能量守恒完美 ✅
2. 59 项降级的系统工程文档 ✅
3. CPG+babbling 产生的随机游走统计特征 ✅

**不能发表的：**
- ~~衰减律→偏好的映射~~ (量源无效)
- ~~梯度-扩散平衡~~ (没有梯度力作用于粒子)
- ~~不变测度由n决定~~ (由CPG轴向决定)
