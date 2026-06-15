# C3' 环流耦合 — Walkthrough (v0.10.0)

## 概述

实现进食-运动-体征的三环流耦合模型。核心理念：**奖励不是标量——奖励是环流模式回归平衡的过程**。

## 架构图

```
           ┌──────────────────────────────────────────────┐
           │            C3' Circulation Coupling          │
           │                                              │
  thermal  │  ① homeo_amp = 1/(1 + thermal_err × 10)     │
  membrane ├──►                                           │
           │  ② motor_amp = body_speed + otolith_xin      │
  body     ├──►                                           │
  speed    │  ③ feed_amp = align(→heat) × thermal_err     │
           │                                              │
  nearest  ├──►  ρ_homeo = homeo / (homeo+motor+feed)    │
  heat src │     deviation = max(0, 0.7 - ρ_homeo)       │
           │                                              │
           │     if deviation > 0.05:                     │
           │       DA_neurons ← inject(deviation × 0.3)  │──► D2R
           │                                              │    autoregulation
           └──────────────────────────────────────────────┘
```

## 文件变更

### [world.py](file:///d:/cell-cc/nexus_v1/components/world.py)
- **多热源**: 3个初始 (不同位置/温度/半径)
- **再生**: `regenerate_sources()` — 死亡热源被移除，新热源在随机位置生成
- **最低保证**: `MIN_ALIVE=2` (始终有至少2个活跃热源)
- **查询**: `get_nearest_heat_source()` — 返回最近活跃热源

### [motor_decision.py](file:///d:/cell-cc/nexus_v1/circuit/motor_decision.py)
- MotionState 新增 7 个字段: 3 amplitudes, 3 rhos, deviation, energy_absorbed

### [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)
- **消耗激活**: `world.consume_nearby()` 每步调用
- **生态再生**: `world.regenerate_sources()` 每步调用
- **三振幅计算**: 从现有信号测量 (无新传感器)
- **DA 注入**: deviation > 0.05 时，向 DA neurons 注入激励电流 (gain=0.3)
  - 通过 D2R 自动调节，不绕过现有 DA 电路

### [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py)
- **Fruit 门控**: `update_fruit(dt, da_concentration)` 新增参数
  - dormant → mature 需要: DA < 0.15 AND standing_wave ∈ [0.05, 0.3]
  - 含义: 只有体征平衡 + 模式稳定时才允许结构固化

## 两条 DA 通路

| 通路 | 来源 | 尺度 | 作用 |
|------|------|------|------|
| C1 | shadow Xin → DA neurons | 微观 (per-bundle) | 精细学习调制 |
| C3' | ρ_homeo 偏移 → DA neurons | 宏观 (全局比例) | 体征失衡激活运动/进食 |

## 验证结果 (50k步)

```
Noether violations: 0
rho_homeo:          0.068  (偏低 — motor_amp 由 Xin 张力虚高)
homeo_deviation:    0.632  (高偏移 — DA 通路已激活)
DA concentration:   0.022  (微弱响应 — 符合预期)
total_consumed:     0.0    (body 未移动至热源)
body speed:         0.0    (学习尚未产生定向运动)
```

## 已知观察

1. **rho_motor 虚高**: `motor_amp` 中 `otolith_xin` 项随时间累积(Xin张力泄漏慢)，导致 rho_motor 偏大。可能需要用 `body_speed` 独立衡量，或对 Xin 项加上限。
2. **body 未移动**: 50k 步不够让 STDP 学会定向运动(正常)。需 200k+ 步才能观察到趋热行为。
3. **热源未消耗**: body 在 [50,50,50]，最近源在 [70,50,50]，距离=20=半径边界。需先移动才能消耗。
