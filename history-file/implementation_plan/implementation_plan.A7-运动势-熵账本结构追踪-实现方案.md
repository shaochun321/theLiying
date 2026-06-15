# A7 运动势 + 熵账本结构追踪 — 实现方案

## 1. A7 运动势 ν = dK/dt

### 数学定义

动能:
```
K(t) = ½ m v²(t)
```

运动势:
```
ν(t) = dK/dt = m v · a = F_muscle · v
```

离散化 (per step):
```
ν_k = (K_k - K_{k-1}) / dt
    = ½m(v_k² - v_{k-1}²) / dt
```

### 与 coupler 电压的关系

C2 修复后, coupler 电压比 10-114:1 表示**瞬时轴选择性**。
定义**轴运动势分量**:

```
ν_x(t) = m · v_x · a_x = F_x · v_x
ν_y(t) = m · v_y · a_y = F_y · v_y  
ν_z(t) = m · v_z · a_z = F_z · v_z

ν_total = ν_x + ν_y + ν_z
```

**运动势极化度** (类比光偏振):
```
P_ν = max(|ν_i|) / (|ν_x| + |ν_y| + |ν_z|)
```
- P_ν → 1: 单轴运动 (偏振光)
- P_ν → 1/3: 均匀运动 (非偏振光)

### 实现位置

在 `variant_adapter.py` 的 `MotionState` 中添加:
- `kinetic_energy`: K(t)
- `motor_potential`: ν(t) = dK/dt  
- `motor_potential_components`: [ν_x, ν_y, ν_z]
- `polarization`: P_ν

---

## 2. 熵账本: 结构/流程/规模追踪

### 新增 Noether Probe 追踪维度

#### [5] 结构熵 H_struct (拓扑复杂度)

```
H_struct = -Σ (n_i/N) log₂(n_i/N)
```
where n_i = bundle i 的突触数, N = 总突触数。

- H_struct 高 → 突触均匀分布 (无结构偏好)
- H_struct 低 → 少数 bundle 占主导 (结构特化)

**与 C2 的关系**: sprouting 增加 H_struct (更多 bundle);
pruning 降低 H_struct (去除弱 bundle)。
健康系统应该有 H_struct 先升后降的轨迹。

#### [6] 流程熵 H_flow (信号流方向性)

```
H_flow = -Σ (f_i/F) log₂(f_i/F)
```
where f_i = bundle i 的 coupler 电压积分, F = 总流量。

- H_flow 高 → 信号均匀流向所有路径
- H_flow 低 → 信号集中在少数路径 (路由特化)

**与 A7 的关系**: 高 P_ν (运动偏振) 对应低 H_flow (信号集中)。
数理基因: **P_ν × H_flow ≈ const** ?

#### [7] 规模参数 Ω (系统复杂度)

```
Ω = N_neurons × N_bundles × N_sprouted
```

追踪 Ω 的增长率 dΩ/dt。
健康系统: dΩ/dt → 0 (结构稳定)。
病态系统: dΩ/dt > 0 持续 (癌变生长)。

### 数理基因候选

如果以下关系成立, 它就是"基因":

```
P_ν × H_flow ≈ C₁        (运动-信息耦合)
H_struct + H_flow ≈ C₂    (结构-流程互补)
dΩ/dt ∝ (H_struct - H₀)  (结构趋稳)
```

---

## 3. 实现方案

### 文件修改

#### [MODIFY] [noether_probe.py](file:///d:/cell-cc/nexus_v1/circuit/noether_probe.py)
- 新增 `_check_structural_entropy()` — H_struct 计算
- 新增 `_check_flow_entropy()` — H_flow 计算
- 新增 `_check_scale_parameter()` — Ω 追踪
- 扩展 `summary()` 和 `print_report()`

#### [MODIFY] [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)
- `MotionState` 添加 ν, P_ν 字段
- 在 body integration 后计算 K, dK/dt
- 记录轴分量 ν_x, ν_y, ν_z

### 验证计划

1. 20k 运行 + 打印 ν(t) 和 P_ν 趋势
2. 检查 P_ν × H_flow 是否近似常数
3. Noether 仍然 0 violations
