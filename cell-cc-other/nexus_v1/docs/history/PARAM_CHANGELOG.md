# 参数变更日志 — nexus_v1

> 记录所有关键参数的变更历史。每条记录包含：旧值→新值、变更原因、影响范围。
> 
> 格式: `[版本] 文件 > 参数: 旧值 → 新值 (原因)`

---

## v1.7.2 (2026-06-08) — P2.1 能量预算重构

### hebbian.py

| 参数 | 旧值 | 新值 | 原因 |
|---|---|---|---|
| `MAX_TOTAL_BUNDLES` | 80 | **删除** | P2.1: 热力学能量墙替代硬编码 |
| `TAX_PER_BUNDLE` | 5e-5 (from neuron) | `BUNDLE_BASAL_COST = 0.0005` (from EnergyStore) | P2.1: 局部常数漏电, 符合 S0 |

### variant_adapter.py

| 参数 | 旧值 | 新值 | 原因 |
|---|---|---|---|
| `CONSUME_RATE` | 0.05 | 0.15 | P2.1: 世界产能太低, ES 15k 步即枯竭 |
| `DA_REFILL_RATE` | 0.01 | 0.001 | P2.1: DA 占 60% 总消耗, 过高 |

### energy_store.py

| 参数 | 旧值 | 新值 | 原因 |
|---|---|---|---|
| `max_deposit_per_step` | *(不存在)* | 0.05 | P2.1: 恒定 P_inflow 上限 |

### bundle.py

| 参数 | 旧值 | 新值 | 原因 |
|---|---|---|---|
| `EXPAND_BOOST_RATIO` | *(不存在)* | 0.3 | sprout 继承 30% 父本权重 |

---

## v1.7.1 (2026-06-07) — Xin 归一化 + Fruit 修复

### bundle.py

| 参数 | 旧值 | 新值 | 原因 |
|---|---|---|---|
| `total_residual /= N_t` | 无归一化 | `/ max(len(targets), 1)` | fan-in 偏差: 7×3 bundle Xin 累积 21× 快于 1×1 |
| `standing_wave_gate` | [0.05, 0.3] | **移除** | ZCR 双峰 (0.000 或 1.000), 无 bundle 落在范围内 |

### variant_adapter.py

| 参数 | 旧值 | 新值 | 原因 |
|---|---|---|---|
| `DA_MATURE_THRESHOLD` | 0.15 | 保持 | 与 SW gate 移除后 DA-only 门控匹配 |

---

## v1.7.0 (2026-06-07) — ν 平滑 + 回归套件

### variant_adapter.py

| 参数 | 旧值 | 新值 | 原因 |
|---|---|---|---|
| `NU_ALPHA` | *(raw Δ)* | 0.01 | raw ν 是宽带噪声, EMA 恢复输入频率 |

---

## v1.6.0 (2026-06-06) — 运动势

### variant_adapter.py

| 参数 | 旧值 | 新值 | 原因 |
|---|---|---|---|
| `OTOLITH_GAIN` | 500.0 | 保持 | 校准: acc → vestibular input range |

### hebbian.py

| 参数 | 旧值 | 新值 | 原因 |
|---|---|---|---|
| `XI_SPROUT` | 0.3 | 保持 | 从 100k 运行校准 |
| `SPROUT_INTERVAL` | 10000 | 保持 | 10k 步 = 10s 物理时间 |

---

## v1.5.0 (2026-06-05) — 运动分化

### hebbian.py

| 参数 | 旧值 | 新值 | 原因 |
|---|---|---|---|
| `cross_weight_ceiling` | *(无)* | 0.2 | 防止 cross-axis 权重追赶 axis |
| `MAX_MOTORS_PER_AXIS` | *(无)* | 20 | 头骨物理约束 |

---

## 参数索引 (当前值速查)

### 结构常数 (hebbian.py)

| 参数 | 当前值 | 单位 | 物理意义 |
|---|---|---|---|
| `SPROUT_INTERVAL` | 10000 | steps | 结构检查周期 |
| `XI_SPROUT` | 0.3 | V·s | Xin 发芽阈值 |
| `MAX_SPROUTS_PER_INTERVAL` | 3 | count | 每次检查最大发芽数 |
| `SPROUT_ENERGY_COST` | 0.1 | energy | 发芽能量消耗 |
| `BUNDLE_BASAL_COST` | 0.0005 | energy/tax | 每束每次税检基底漏电 |
| `MAX_MOTORS_PER_AXIS` | 20 | count | 每轴最大运动神经元 |

### 能量参数 (energy_store.py)

| 参数 | 当前值 | 单位 | 物理意义 |
|---|---|---|---|
| `capacity` | 1000.0 | energy | 最大储能 |
| `initial_fill` | 0.5 | fraction | 初始充能比例 |
| `basal_drain` | 0.0001 | energy/step | 基础代谢漏电 |
| `max_deposit_per_step` | 0.05 | energy/step | P_inflow 恒定上限 |
| `deposit_efficiency` | 0.9 | fraction | 消化效率 |
| `starvation_threshold` | 0.1 | fraction | 饥饿阈值 |

### 世界参数 (variant_adapter.py)

| 参数 | 当前值 | 单位 | 物理意义 |
|---|---|---|---|
| `CONSUME_RATE` | 0.15 | energy/step | 热源吸收速率 |
| `DA_REFILL_RATE` | 0.001 | energy/step/neuron | DA 神经元补能速率 |
| `OTOLITH_GAIN` | 500.0 | - | 加速度→前庭输入增益 |
