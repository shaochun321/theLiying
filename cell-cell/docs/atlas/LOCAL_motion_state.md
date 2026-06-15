# LOCAL: 运动状态识别与存储

> **Version**: v1.7.2 | **File**: [variant_adapter.py](../../circuit/variant_adapter.py)

---

## MotionState 数据结构

每步更新，记录系统的即时运动状态：

```
MotionState:
  ├── kinetic_energy    K = ½m|v|²
  ├── motor_potential   ν = EMA(dK/dt, α=0.01)
  ├── motor_potential_xyz  ν_i = EMA(m×v_i×a_i)
  ├── polarization      P = max|ν_i| / Σ|ν_i|
  ├── body_speed        |v|
  ├── temporal_measure  {axis: irr_enc EMA}  ← AC 分量
  ├── spatial_measure   {axis: reg_enc EMA}  ← DC 分量
  ├── otolith_acc       {x,y,z: body.acceleration}
  ├── thermal           T_measured - methylation
  │
  ├── homeo_amplitude   CirculationProportion v_homeo
  ├── motor_amplitude   CirculationProportion v_motor
  ├── feed_amplitude    CirculationProportion v_feed
  ├── rho_homeo/motor/feed  比例
  ├── homeo_deviation   |rho - 1/3| 偏激度
  └── energy_absorbed   本步热源吸收量
```

## 信号来源

```
                    ┌── body.acceleration × OTOLITH_GAIN
                    │
World + Body ───────┼── body.speed()
                    │
                    └── ThermalMembrane.sense()
                    
Encoding neurons ───┼── irr_* EMA → temporal_measure (AC)
                    │
                    └── reg_* EMA → spatial_measure (DC)
                    
Column neurons ─────── Σ|activation| → motion_potential

CirculationProportion ─ v_homeo/motor/feed → rho → deviation
```

## 使用者

| 消费者 | 使用字段 | 用途 |
|---|---|---|
| MotorDecision | axis_acts, da | CPG 输入 (当前 passthrough) |
| Noether Probe | kinetic_energy | 能量守恒审计 |
| Mitosis check | motor_potential | 运动神经元分裂门控 |
| C3' coupling | thermal, speed, alignment | 环流比例计算 |

## DC/AC 分离

| 成分 | 来源 | 时间尺度 | 用途 |
|---|---|---|---|
| DC (空间) | reg_enc EMA | ~100 步 | 静态位置/姿态 |
| AC (时间) | irr_enc EMA | ~10 步 | 动态运动/变化 |

**理论对接**: T006 §2 — DC 驱动结构变化, AC 驱动权重变化

## 版本历史

| 版本 | 变更 |
|---|---|
| v1.5.0 | MotionState 初版 |
| v1.6.0 | A7 ν=dK/dt, 偏振度 |
| v1.7.0 | ν EMA 平滑 |
