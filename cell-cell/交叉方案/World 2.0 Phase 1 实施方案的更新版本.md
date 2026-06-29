## 确认：三处修正必须接受

三处修正均成立，必须纳入实施。其中前两处为热力学守恒问题，第三处为数值稳定性问题。

---

### 修正 3：热源扣费必须扣除总热通量

**问题所在**：

当前实现：
```python
energy_intake = conductance * area * eta * delta_T * dt   # 仅 2%
src.absorb(energy_intake)                                 # 只扣了 ATP 转化部分
```

环境热量是 `conductance * area * delta_T * dt`，其中 `eta=0.02` 仅转化了 2%，98% 的废热通过口器表面散失到环境中。但这 98% 仍然来自热源，环境是一个开放系统——废热一旦散失，仍会通过热传导影响周围的温度场。如果不扣除这部分，热源的能量余额将被非法延长，因为按当前逻辑，口器每吸收 100 单位热量，只有 2 单位从热源扣除，98 单位凭空产生。

**修正后**：

```python
total_heat_flux = conductance * area * delta_T * dt       # 总热通量
energy_intake = eta * total_heat_flux                     # 进入 EnergyStore 的部分
src.absorb(total_heat_flux)                               # 从热源扣除全部
```

这样 `eta` 仍控制着转化效率，但热源扣除的是全部提取的热量，维持能量守恒。

---

### 修正 4：T_body 必须绑定到 ECM 温度

**问题所在**：

`T_body = 0.15` 是恒定死常数。口器向身体的散热去向不明——热量既没有用于加热身体，也没有被 Noether 审计追踪。这违反了热力学第一定律。

**修正后**：

```python
# 在 ThermalMouth.step() 中
T_body = world.ecm.temperature  # 或 body.ecm_temperature
```

这样：
- 口器散热会加热 ECM
- ECM 温度升高后，口器散热效率降低（“发烧食欲不振”的自然涌现）
- Noether 审计可追踪这部分热量转移

---

### 修正 5：Z 轴锁定（Phase 1 平面近似）

**问题所在**：

圆柱碰撞检测仅处理 XY 平面。当 body 从圆柱正上方降落时，`within_height` 从 False 变为 True，body 会被水平方向弹射，产生非物理位移。

**修正后**：

在 Body.step() 或位置更新结束时：
```python
# Phase 1: 固定 Z 轴平面运动
self.position[2] = 25.0  # 固定高度（根据热源位置调整）
self.velocity[2] = 0.0
```

**在实施方案中新增说明**：

> Phase 1 中，所有 body 运动被约束在 Z=25 的平面上。热源柱体的高度覆盖该平面，碰撞仅发生在 XY 平面。Z 轴的锁定是 Phase 1 的平面近似，后续版本可扩展为完整 3D。

---

### 与 P2 技术债的关系

V-03（Deviation Reflex结构化）、V-04（Xin Relay Bundle化）、Shadow K_ema发散（I-05a）、xin_conservation违规（I-05b）均为 P2 技术债，不阻塞 World 2.0 Phase 1 的实施。我将在更新后的 World 2.0 Phase 1 方案末尾添加一条说明，将这些项标记为独立工作流，与 Phase 1 并行推进即可。

---

## World 2.0 Phase 1 实施方案更新（v2.1）

### 新增修正项：Step 4 补充（热源扣费、T_body绑定）

**文件：** `components/thermal_mouth.py`

在 `step()` 中修改：
```python
def step(self, world, body, energy_store, dt: float = 0.001):
    pos = self.world_position(body)
    T_env = world.temperature_at(pos)

    # Thermal dynamics
    dT = ((T_env - self.temperature) / self.tau_heat
          - (self.temperature - self.T_body) / self.tau_cool)
    self.temperature += dT * dt

    # Energy intake
    delta_T = max(0.0, T_env - self.temperature)
    # FIX-PHASE1-001: total_heat_flux vs energy_intake
    total_heat_flux = self.conductance * self.area * delta_T * dt
    energy_intake = self.eta * total_heat_flux
    self.energy_intake = energy_intake

    if self.energy_intake > 0:
        energy_store.deposit(self.energy_intake)
        # FIX-PHASE1-001: deduct total heat flux, not just converted ATP
        for src in getattr(world, 'cylindrical_sources', []):
            if src.alive:
                src.absorb(total_heat_flux)  # ← 扣除全部，不是仅 energy_intake
                break

    return self.energy_intake
```

### 新增修正项：T_body 动态绑定

在 `ThermalMouth.__init__` 中移除固定 `T_body`，改为在 `step()` 中从 world 获取：
```python
# 在 step() 中
self.T_body = getattr(world, 'ecm_temperature', 0.15)  # 默认值作为备选
```

### 新增修正项：Z 轴锁定（Step 5 集成）

在 `variant_adapter.step()` 的位置更新之后、碰撞检测之前：
```python
# Phase 1: 2D planar approximation — lock Z axis
self.body.position[2] = 25.0
self.body.velocity[2] = 0.0
```

### 方案版本更新

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v2.0 | 2026-06-27 | 初始修订版（碰撞→损伤、过阻尼偏航、口器散热）|
| v2.1 | 2026-06-27 | 热源扣费修正（扣除总热通量）、T_body 绑定到 ECM、Z 轴锁定 |

### 实施检查清单（更新）

- [ ] Step 1: CylindricalHeatSource + temperature_at()
- [ ] Step 2: Body.yaw + SkinPatch.world_position()
- [ ] Step 3: 碰撞检测 + damage 注入（同时锁定Z轴）
- [ ] Step 4: ThermalMouth（含总热通量扣费 + T_body动态绑定）
- [ ] Step 5: variant_adapter.py 集成（含Z轴锁定）
- [ ] Step 6: diag_world2_physics.py 单元测试
- [ ] Step 7: exp_world2_phase1.py 探测实验


## 确认分析：World 2.0 Phase 1 的结构构建与物理计算合规性

### 一、三处修正的合规性分析

| 修正 | 性质 | 符合结构构建？ | 符合物理计算？ | 说明 |
|------|------|--------------|---------------|------|
| **热源扣费（总热通量）** | 热力学守恒修正 | ✅ 是 | ✅ 是 | 热源扣除全部提取热量，无论转化效率如何。能量守恒是物理计算的底层要求，不是语义规则 |
| **T_body绑定ECM** | 热力学路径修正 | ✅ 是 | ✅ 是 | 口器散热去向变为可追踪的物理路径（ECM温度），而非凭空消失。这使“发烧→食欲不振”成为涌现行为 |
| **Z轴锁定** | 工程简化 | ⚠️ 条件性 | ⚠️ 条件性 | Phase 1 平面近似，非最终物理设计。需要在文档中明确标注为临时简化，后续版本需取消锁定 |

**整体评估**：World 2.0 Phase 1 构建符合“结构构建”和“物理计算”原则：

- 物理计算：温度场通过高斯扩散定义，碰撞通过速度/位置更新实现，热交换通过温差驱动——全部是物理量之间的相互作用
- 结构构建：口器通过温差热交换获得能量，碰撞通过损伤路径间接影响能量预算——行为从物理结构中涌现，而非从 `if-else` 逻辑中产生

**Z轴锁定的定位**：它是一个清晰的工程决策——在 Phase 1 中为了简化验证而固定 Z 轴，不意味着最终系统没有 Z 轴运动。需要在 Phase 1 验证通过后将其作为“遗留项”处理。

### 二、与 P2 技术债的关系

P2 技术债（V-03 Deviation Reflex结构化、V-04 Xin Relay Bundle化、Shadow K_ema发散、xin_conservation违规）的修复方式与 World 2.0 Phase 1 的构建遵循相同原则：

| 技术债 | 修复方式 | 符合结构构建？ | 说明 |
|--------|----------|--------------|------|
| V-03 Deviation Reflex | 创建 DeviationRelayNeuron + STDP束 | ✅ 是 | 将语义硬编码替换为物理神经元通路 |
| V-04 Xin Relay Bundle化 | XinIntegratorNeuron适配器 + Bundle | ✅ 是 | 电容→神经元→Bundle的物理信号链 |
| Shadow K_ema发散 | 检查并添加指数衰减项 | ✅ 是 | 自由能应有物理衰减机制 |
| xin_conservation违规 | 检查 Memristor.apply_dw 是否被绕过 | ✅ 是 | 权重变化必须经过 KCL 追踪的原子操作 |

**确认**：P2 技术债的全部修复方向与项目原则一致，不阻塞 World 2.0 Phase 1。

### 三、World 2.0 Phase 1 需在方案中补充的说明

基于上述分析，需要在实施方案中增加以下说明：

1. **Z轴锁定标注**：
   > “Phase 1 采用 Z=25 平面近似，所有运动被约束在二维平面。该约束是工程简化，用于在 World 2.0 的早期阶段验证核心机制（温差热交换、偏航、粘性碰撞），不构成最终物理设计。Phase 2 将解除 Z 轴锁定。”

2. **热源扣费说明**：
   > “`src.absorb()` 扣除总热通量 `total_heat_flux`，而非仅 `energy_intake`。口器转化的 2% 热量进入 EnergyStore，98% 废热散失到环境并被热源能量余额吸收。这符合热力学第一定律——环境与热源的热交换是一个开放的物理过程，废热仍通过环境介质的温度场重新分布。”

3. **T_body 说明**：
   > “`T_body` 从 ECM 温度读取，使口器散热路径可被 Noether 审计追踪。此路径使‘ECM 温度升高→口器散热效率降低→进食功率下降’成为涌现行为，形成物理闭环。”