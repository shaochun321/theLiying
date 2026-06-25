# 偏好不变量：最终修正

## 之前的声明（错误）

> "$P(\text{acoustic closest}) \to 0$ 当 $T \to \infty$"

## 轨迹证据

单seed连续追踪显示：**系统不收敛到固定平衡点**。

```
seed=1, L_acoustic 时间序列:
  7.53 → 12.35 → 12.20 → 6.49 → 12.71 → 9.77 → 7.47 → 12.21 → ...
  → 11.85 → 10.42 → 12.30 → 10.02 → 6.98(!) → 12.00 → 12.18
```

**L_aco 在 6.5~12.7 之间大幅振荡**，acoustic 在 t=0, t=340 两次成为最近源。

## 修正后的定理

> [!IMPORTANT]
> **定理（统计版）**: 在足够长的时间窗口 $[0, T]$ 中，
> $$\mathbb{E}[L_{acoustic}] > \mathbb{E}[L_{thermal}] \approx \mathbb{E}[L_{luminous}]$$
> 且
> $$\text{frac}(\text{acoustic closest}) < \text{frac}(\text{thermal closest}) \approx \text{frac}(\text{luminous closest})$$

这不是一个确定性的"永远不会"，而是一个**统计倾向**。

## 物理机制（修正版）

```
1. 系统进行有偏随机游走 (babbling + CPG + reflex)
2. acoustic (1/r) 有更强的长程梯度 → 更强的reflex驱动
3. 当系统靠近 acoustic → received > 0.5 → 触发avoidance → 被推走
4. 但 babbling 可以暂时把系统再推回来 → 产生振荡
5. 统计上: 被推走的时间 > 被推回来的时间 → E[L_aco] 偏大
```

## 关键区分

| 属性 | 之前声称 | 实际情况 |
|---|---|---|
| 收敛到 L* | ✅ 固定点 | ❌ 持续振荡 |
| acoustic 永不最近 | ✅ 不变量 | ❌ 偶尔最近 |
| P(aco) → 0 | ✅ 渐近 | ❌ 有限非零 |
| E[L_aco] > E[L_others] | ✅ | ✅ **唯一成立的** |
| 系统行为 | 平衡态 | **非平衡态随机过程** |

## 数学意义

这个系统不是一个梯度系统(gradient system)，而是一个**非平衡稳态过程(NESS)**。

它的长时间行为不由不动点描述，而由**不变测度(invariant measure)**描述：

$$\rho^*(L_{aco}, L_{the}, L_{lum}) \neq \delta(L - L^*)$$

不变测度在 $L_{aco}$ 方向上的均值更大、分布更宽。
这比"收敛到固定点"更丰富、更有物理意义。

## N=50 统计中的 2/50=4% 是什么？

不是"4% 的 seed 产生了异常"。
而是"所有 seed 在 T=300 这个特定时刻的快照"。
如果对同一个 seed 的不同时刻取快照，acoustic 也会偶尔成为最近。

**4% 是不变测度在 "acoustic closest" 区域的测度。**
