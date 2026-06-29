

> **目标**：在柱体热源、连续温度场、温差热交换供能、偏航自由度、粘性碰撞的物理环境中，验证生命体在新世界中的感觉-运动闭环与能量自持能力。
> **原则**：最小侵入，不改神经网络核心学习规则，只修改环境（World/Body）和新增口器供能通路。影子层不修复，偏航用简单反射+可塑束驱动。

> **v2 修订说明**（2026-06-27）：
> - 碰撞耗散改为间接路径（碰撞→损伤→修复代谢税），不再直接扣除 ATP
> - 偏航角摩擦改为过阻尼配置（angular_friction=3.0），采用指数衰减
> - 口器热交换补充散热机制（弱连接至身体恒温池）
> - 碰撞后添加几何弹出余量（0.01），防止浮点穿模
> - 补充热源能量扣除，确保热力学守恒
> - 碰撞冲击→损伤的转换系数 `K_impact` 暂定为 0.01，Phase 1 验证中标定


## 一、Phase 1 交付范围

| 模块 | 内容 | 优先级 |
|------|------|--------|
| 柱体热源 | 具有物理体积和碰撞响应的柱体，表面向外扩散温度场 | P0 |
| 连续温度场 | 柱体表面向外高斯扩散，梯度连续，全空间有定义 | P0 |
| 粘性碰撞 | body 与柱体碰撞时速度衰减反弹，通过损伤路径间接影响能量 | P0 |
| 偏航自由度 | Body 增加 yaw 角 + 过阻尼角运动方程 | P0 |
| 口器热交换供能 | 口器贴片在温度场中通过温差获得能量，替代离散食物 | P0 |
| 硬边界世界 | 世界外壳坐标钳位 + 速度反弹 | P0 |
| 温差-偏航反射束 | 左右温差→偏航力矩的初始通路 | P0 |
| YolkSac 保留 | 初始能量储备，早期探索 | P1 |
| 短程验证 | 100k 步探测测试，验证感觉-运动闭环 | P1 |


## 二、物理层改动

### 2.1 柱体热源 + 连续温度场

**修改文件**：`nexus_v1/components/heat_source.py`（新建）、`nexus_v1/components/world.py`

**柱体属性**：
```
CylindricalHeatSource:
  - center: [x, y, z]（柱体中心）
  - radius: 6（物理碰撞半径）
  - height: 16（柱体高度）
  - T_surface: 5.0（表面温度）
  - energy: 1000（可消耗热量储量）
  - regeneration_rate: 0.002/步（可再生）
```

**温度场**（柱体表面向外扩散）：
$$T(\mathbf{x}) = T_{ambient} + \sum_{i} (T_{surface,i} - T_{ambient}) \cdot \exp\left(-\frac{d_i^2}{2\sigma_i^2}\right)$$

其中 $d_i$ = 到柱体表面的距离（柱体内部为 0），$\sigma_i$ = 扩散长度（25）

**关键特性**：
- 全空间连续可微，无边界突变
- 梯度 $\nabla T$ 在全空间有定义
- 柱体温度随能量变化：$T_{surface} = T_{base} \times (energy / energy_{initial})$
- **口器吸收的热量从 `HeatSource.energy` 中扣除**，确保热力学守恒

### 2.2 粘性碰撞（间接耗散路径）

**修改文件**：`nexus_v1/components/world.py` 中的 `Body.update_position()`

**碰撞检测**：
- 计算 body 中心到柱体表面的最短距离
- 若距离 < `body.radius + 0.01`，触发碰撞响应

**碰撞响应**：
```
碰撞发生时：
  v_normal = dot(v, normal)（法向速度）
  if v_normal < 0（正在靠近）:
    v_normal_new = -v_normal × 0.7（法向反弹 + 阻尼）
    tangential_component_new = tangential_component × 0.9（切向摩擦）
    v = v_normal_new + tangential_component_new
    position 推移到 radius + 0.01（几何弹出余量，防止浮点穿模）
    
    碰撞冲击力 → 前部皮肤损伤：
    delta_E_kinetic = 0.5 × m × (|v_before|² - |v_after|²)
    front_patch.damage_integral += K_impact × delta_E_kinetic
    K_impact = 0.01（暂定，Phase 1 验证中标定）
```

**间接能量路径**：
- 碰撞 → 损伤积累 → 触发修复代谢税（Loop B）→ `EnergyStore.withdraw(label='repair')`
- **不直接从 EnergyStore 扣除碰撞耗散**，而是通过物理损伤间接影响能量预算

### 2.3 硬边界世界

**逻辑**：
1. 更新位置后，钳位坐标到 $[0, 100]$ 范围
2. 若越界，将该轴速度分量反向 ×0.8（弹性 + 阻尼）
3. 位置置为边界值

### 2.4 偏航自由度（过阻尼配置）

**修改文件**：`nexus_v1/components/world.py` 中的 `Body` 类

**新增属性**：
- `yaw: float`（绕 z 轴旋转角，初始 0）
- `angular_velocity: float`（初始 0）
- `inertia: float = 1.0`
- `angular_friction: float = 3.0`（过阻尼，使转向沉重粘滞）

**运动方程**：
```
yaw_accel = motor_torque / inertia - angular_friction × angular_velocity
angular_velocity += yaw_accel × dt

# 角速度衰减（指数衰减，防止符号翻转）
angular_velocity *= exp(-angular_friction × dt)

yaw += angular_velocity × dt
```

**皮肤贴片世界坐标**：修改 `SkinPatch.world_position()`，应用绕 z 轴的 2D 旋转矩阵。

### 2.5 口器贴片（温差热交换）

**新增文件**：`nexus_v1/components/thermal_mouth.py`

**物理模型**：
- 口器贴片位于身体正前方 `[body_radius + 0.5, 0, 0]`，随 body 偏航旋转
- 能量流入功率（基于温差热交换）：
$$P = k \cdot A \cdot \eta \cdot \max(0, T_{env} - T_{mouth})$$

- `k`：导热系数（2.0）
- `A`：面积（1.0）
- `\eta`：热电转换效率（0.02）
- `T_{env}`：口器位置的环境温度
- `T_{mouth}`：口器贴片当前温度（通过 Fourier 热传导与环境同步）

- 每步沉积到 `EnergyStore` 的能量：$\Delta E = P \cdot dt$

**散热机制**：
- 口器贴片具有热容，温度变化受热传导方程控制
- 口器通过**身体内部恒温池的弱热连接**散热，使 $T_{mouth}$ 被压低，维持与环境温差的持续性，防止“热平衡死锁”
- 散热项：`dT_mouth/dt = (T_env - T_mouth) / τ_heat - (T_mouth - T_body) / τ_cool`
- `τ_cool` = 50（冷却时间常数），模拟血液循环带走热量

**设计约束**：口器只在比自身更热的环境中供能；远离热源时无法获得净能量。

**热源能量扣除**：口器吸收的热量从对应的 `CylindricalHeatSource.energy` 中扣除。


## 三、神经控制层改动

### 3.1 温差-偏航反射束

**修改文件**：`nexus_v1/circuit/variant_adapter.py`

**新增逻辑**：
```python
# 左右皮肤温差 → 偏航力矩
delta_T_lr = skin_temp_left - skin_temp_right
motor_torque = delta_T_lr × YAW_GAIN  # YAW_GAIN = 0.1

# 同时为可塑学习预留通路
# therm_left → rotate_yaw, therm_right → rotate_yaw（可塑束，初始权重 0.01）
```

### 3.2 口器供能集成

**修改文件**：`nexus_v1/circuit/variant_adapter.py` 的 `step()` 能量段

**逻辑**：
1. 在 `body.step()` 之后，调用 `thermal_mouth.step(world, body, dt)`
2. 获取口器供能 `mouth_energy = thermal_mouth.energy_intake`
3. 将 `mouth_energy` 沉积到 `EnergyStore`
4. 从 `HeatSource.energy` 扣除对应的热量

### 3.3 YolkSac 保留

YolkSac 初始能量 200-500 单位保留，提供早期探索预算。Phase 1 验证阶段，口器供能作为补充而非替代。


## 四、Phase 1 验收标准

| 编号 | 标准 | 测试方法 |
|------|------|----------|
| W1 | 温度场连续，柱体表面温度清晰 | 手动测试 `temperature_at()` |
| W2 | 柱体碰撞生效 | body 推向柱体，检查是否穿透、速度是否反转衰减、损伤是否积累 |
| W3 | 碰撞耗散通过损伤路径间接影响能量 | 碰撞后检查 fill 是否通过修复代谢税下降 |
| W4 | 身体可偏航，贴片坐标跟随旋转 | 输入固定力矩，检查 yaw 变化和贴片世界坐标 |
| W5 | 口器贴片在温度场中可供能 | body 置于温度场中，检查 EnergyStore 增长 |
| W6 | 口器在热源中心不会热平衡死锁 | 长时间置于热源中心，检查进食功率是否维持非零 |
| W7 | 身体越界被硬边界反弹 | 驱动 body 冲向边界，检查位置钳位和速度反弹 |
| W8 | 温差-偏航反射束工作正常 | 模拟左右温差，检查 motor_torque 输出 |
| W9 | 100k 步探测测试：fill 不归零 | 从初始位置出发，YolkSac 耗尽后口器供能维持生存 |


## 五、参数总览

| 参数 | 值 | 说明 |
|------|-----|------|
| 柱体半径 | 6 | 碰撞半径 |
| 柱体高度 | 16 | 柱体垂直范围 |
| T_surface | 5.0 | 柱体表面温度 |
| 扩散长度 σ | 25 | 温度场衰减尺度 |
| 背景温度 | 0.15 | 环境基线 |
| 口器导热系数 k | 2.0 | 与皮肤一致 |
| 口器面积 A | 1.0 | 热交换面积 |
| 热电转换效率 η | 0.02 | 热能→代谢能 |
| 口器冷却时间常数 τ_cool | 50 | 散热速度（步）|
| 转动惯量 I | 1.0 | 归一化 |
| 角摩擦系数 | 3.0 | 过阻尼配置 |
| 法向阻尼 | 0.7 | 碰撞后法向速度损失 |
| 切向阻尼 | 0.9 | 碰撞后切向速度损失 |
| 几何弹出余量 | 0.01 | 防止浮点穿模 |
| 冲击-损伤系数 K_impact | 0.01（暂定）| Phase 1 中标定 |
| YAW_GAIN | 0.1 | 温差→力矩的初始增益 |
| YolkSac 初始量 | 200 | 早期探索 |
| 世界尺寸 | 100×100×100 | 硬边界 |


## 六、文件变更清单

| 文件 | 操作 | 内容 |
|------|------|------|
| `nexus_v1/components/heat_source.py` | 新建 | `CylindricalHeatSource` 类 |
| `nexus_v1/components/thermal_mouth.py` | 新建 | `ThermalMouth(SkinPatch)` 类 |
| `nexus_v1/components/world.py` | 修改 | 集成柱体热源、`temperature_at()` 高斯场；`Body` 增加 yaw、过阻尼偏航、粘性碰撞（含损伤路径）、硬边界 |
| `nexus_v1/circuit/variant_adapter.py` | 修改 | 口器供能集成，偏航力矩计算，可塑束预留 |
| `nexus_v1/tests/exp_world2_phase1.py` | 新建 | Phase 1 100k 步探测测试脚本 |
| `nexus_v1/tests/diag_world2_physics.py` | 新建 | 物理层单元测试（温度场、碰撞、偏航）|


## 七、与原有 World 1.0 的关系

| 特征 | World 1.0 | World 2.0 |
|------|-----------|-----------|
| 热源几何 | 点 | 柱体 |
| 温度场 | 离散点源叠加 | 柱体表面高斯扩散 |
| 进食机制 | 半径内 360° 吸能 | 温差热交换（口器在温度场中）|
| 碰撞响应 | 无 | 粘性碰撞（通过损伤间接耗能）|
| 碰撞耗散路径 | — | 碰撞→损伤→修复代谢税→EnergyStore |
| 偏航 | 无 | 有（过阻尼）|
| 影子层 | 热觉轴循环依赖 | 验证通过后再处理 |
| 硬边界 | 有 | 有 |


## 八、下一步规划（后续阶段）

- **Phase 2（生命体适配）**：完全移除 YolkSac，让口器供能成为唯一能量来源；让偏航可塑束参与 STDP 学习；修复影子层内部通路
- **Phase 3（学习验证）**：运行长程实验（500k 步），验证涌现行为（巡航热源、能量自持）

## 九、 备忘录

- 方案中有一个参数需要在实验中标定：K_impact = 0.01（碰撞冲击→损伤的转换系数）。这个值决定了碰撞对生存的影响程度——太小则碰撞无关紧要，太大则轻微碰撞就会产生严重损伤。Phase 1的验证实验需要确认这个值是否落在合理范围内：碰撞应该产生可感知但非致命的损伤代价。

- 口器散热速率（τ_cool=50）的设定缺乏直接的生物物理依据。如果散热过快，口器永远无法达到与环境的热平衡，进食效率极低。如果散热过慢，口器在热源中心迅速达到热平衡，进食停止。这个参数需要在Phase 1实验中作为重点监控对象。