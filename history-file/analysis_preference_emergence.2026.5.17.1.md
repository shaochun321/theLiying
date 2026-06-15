# 偏好行为涌现分析（修正版）

## 原始假设 vs 实验结果

| 假设 | 实验结果 | 结论 |
|---|---|---|
| gain 不对称是根因 | 等增益后 lever 完全不变 | ❌ **WRONG** |
| 种子改变偏好 | 8种子: thermal=4, luminous=4 | ✅ YES |
| acoustic 可以是最近 | 8/8次都不是 | ❌ **永远不会** |

## 真正的因果链

```
物理衰减律不对称 (1/r vs 1/r²)         ← 第1因 (结构)
          ↓
梯度力不对称:
  acoustic: ∇Φ ~ 1/r²  (弱引力)
  thermal:  ∇Φ ~ 1/r³  (强引力)
  luminous: ∇Φ ~ 1/r³  (强引力)
          ↓
反射模块 (reflex): 强梯度源 → 更强吸引
          ↓
acoustic 永远不被接近                   ← 不变量
          ↓
babbling RNG (seed)                    ← 第2因 (对称破缺)
          ↓
决定 thermal 还是 luminous 被接近       ← 偶然性
```

## 关键数据

**8个种子的最终力臂:**
```
seed=42:    aco=12.0  the=10.7  lum=10.8  → thermal
seed=7:     aco=11.1  the= 9.5  lum= 5.0  → luminous  
seed=123:   aco= 9.9  the= 6.2  lum= 9.6  → thermal
seed=999:   aco=11.9  the= 7.2  lum= 9.0  → thermal
seed=2026:  aco=10.8  the= 8.1  lum= 4.8  → luminous
seed=314:   aco=12.4  the=12.2  lum= 7.7  → luminous
seed=65535: aco=12.0  the= 7.2  lum=10.9  → thermal
seed=1:     aco=11.4  the= 7.2  lum= 6.7  → luminous
```

**acoustic 永远不是 closest** — 这是物理衰减律决定的不变量。

## 等增益实验证伪

```
gain=0.73 seed=42: aco=12.0 the=10.7 lum=10.8  ← 和 gain=1.57 完全相同！
gain=1.00 seed=42: aco=12.0 the=10.7 lum=10.8
gain=1.57 seed=42: aco=12.0 the=10.7 lum=10.8
```

**gain 对最终力臂零影响。** gain 只影响积分器内部状态的振幅，不影响物理轨迹。
因为积分器→motor 的权重太小 (w=0.08)，被 reflex 和 babbling 完全淹没。

## 深层含义

| 层级 | 因素 | 效应 | 可变性 |
|---|---|---|---|
| **结构** | 衰减律 1/r vs 1/r² | 决定哪类源可被接近 | 固定 |
| **偶然** | babbling 序列 (seed) | 决定具体接近哪个源 | 随机 |
| **无效** | lognormal gain | 仅影响积分器内部态 | 无物理效应 |

> **核心修正**: 偏好不是来自"身体结构的随机不对称"(gain)，
> 而是来自**物理定律的结构不对称**(1/r vs 1/r²) + **初始运动的偶然对称破缺**。
> 这更像是物理约束决定了"可能的偏好空间"，
> 随机事件从中选择了具体的偏好方向。
