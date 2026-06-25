# MotionState — 运动状态

## 物理对应

- **BIO**: 本体感觉 (前庭 + 肌梭 + 关节感受器)
- **EE**: 动力学积分器: ν=dK/dt, 偏振度 P_ν

## 文件

[variant_adapter.py](../../circuit/variant_adapter.py) (内嵌类)

## 功能

每步更新的运动状态数据:

| 属性 | 公式 | 物理意义 |
|---|---|---|
| `kinetic_energy` | ½m\|v\|² | 动能 |
| `motor_potential` | EMA(dK/dt, α=0.01) | 运动势 |
| `motor_potential_xyz` | EMA(m×v_i×a_i) | 分轴运动势 |
| `polarization` | max(\|ν_i\|) / Σ\|ν_i\| | 偏振度 [0.33, 1.0] |
| `body_speed` | \|v\| | 体速 |
| `temporal_measure` | irr afferent EMA | AC 时间分量 |
| `spatial_measure` | reg afferent EMA | DC 空间分量 |
| `otolith_acc` | body acceleration | 耳石加速度 |

## 关键参数

| 参数 | 值 | 物理意义 |
|---|---|---|
| `NU_ALPHA` | 0.01 | EMA 平滑系数 (~100 步窗口) |
