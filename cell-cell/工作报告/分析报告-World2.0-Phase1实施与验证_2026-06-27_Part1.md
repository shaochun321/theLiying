# 分析报告 — World 2.0 Phase 1 实施与验证
## Part 1：背景、实施内容、物理层测试

**日期：** 2026-06-27  
**版本：** v1.0  
**实验代码路径：** `J:\cell-cc\cell-cc-other\nexus_v1\`  
**关联方案：** `cell-cell/claudecode方案/World2.0-Phase1-实施方案_2026-06-27.md`（v2.1）

---

## 1. 背景与动机

### 1.1 前置阶段回顾

Phase 5 Round 4（2026-06-26）以 **5/6 PASS** 结束，首次观测到 y 轴热趋性自发涌现：
- `w_right` 从 0.106 → 0.500（饱和），`w_left` 从 0.078 → 0.006（衰减）
- DR5（方向对齐率）失败原因为指标设计问题——body 越过 y=75 热源后无停止机制，持续过冲导致 align 变负。实际学习行为正常。

该轮实验确认了"在受控 2D 热梯度下 STDP 可产生方向性权重分化"，满足进入 World 2.0 阶段的条件。

### 1.2 World 2.0 的核心动机

旧热源系统（8 个点热源，均匀覆盖 ~90% 空间）使 body **总是泡在热场里**，没有需要主动趋向的梯度结构。热趋性虽然在 Round 4 涌现，是因为外部强制了 body 在特定方向的初始偏置，而非 body 自主导航的结果。

World 2.0 目标：
1. 引入**有体积的柱状热源**（Gaussian 热场），产生空间梯度结构
2. 身体需要主动趋近才能摄食（`ThermalMouth`）
3. 物理对流浮力作为背景驱动力（不是语义规则）
4. 偏航力矩从左右温差中物理涌现（不注入方向信息）

### 1.3 合规性基础（Structure-First 三问）

**柱状热源（`CylindricalHeatSource`）：**
- Q1 BIO: 深海热液喷口（Kelley et al. 2002, *Science* 301:495）
- Q2 结构: 圆柱形热源 → Gaussian 温度场 → `World.temperature_at()` → 皮肤贴片温度
- Q3 参数: σ=25（Gaussian 扩散长，对应约 1 喷口体积半径的自然扩散）；energy=1000（有限储量，regen=0.002/步）

**热觉口器（`ThermalMouth`）：**
- Q1 BIO: 热液喷口化学合成自养生物（*Riftia pachyptila* 等，Childress & Fisher 1992）
- Q2 结构: `ThermalMouth.local_offset=[2,0,0]` → `SynapticBundle`（类比 bundles_shadow_to_da）通过 body yaw 旋转取得世界坐标 → `energy_store.deposit()`
- Q3 参数: τ_heat=13（推导：稳态方程 `T_ss = (T_env/τ_h + T_body/τ_c) / (1/τ_h + 1/τ_c) = 4.0`）；η=0.02（热→代谢转化效率）

**热流对流漂移（Buoyancy advection）：**
- Q1 BIO: 热液喷口附近流体受热密度降低，对流电流将生物被动携带趋近热源（Kelley 2002）
- Q2 结构: `world.gradient_at(body.position)` → `body.velocity += k_conv * ∇T * dt`（Newton 外力，非 if 语句）
- Q3 参数: k_conv=0.5（EXP-W2-004；理论终端速度 v_t = k_conv|∇T|/μ ≈ 0.116 units/step at σ 距离）

---

## 2. 实施内容

### 2.1 新建文件

#### `components/heat_source.py` — TYPE:BIO

```
CylindricalHeatSource:
  center=[50,50,25]  radius=6   height=16
  T_surface=5.0      T_ambient=0.15  sigma=25.0
  energy=1000.0      regeneration_rate=0.002
```

核心方法：
- `_dist_to_cylinder_surface(pos, center, r, hh)` — 精确计算点到圆柱表面最短距离（处理侧面、端面、棱角三种情况）
- `temperature_at(pos)` — Gaussian 扩散场：`T = T_a + (T_eff - T_a) * exp(-d²/2σ²)`
- `absorb(amount)` — 从能量储量中扣除热通量（Noether 守恒：摄入 = 来源消耗）
- `effective_T_surface` — 随能量比例线性衰减

#### `components/thermal_mouth.py` — TYPE:BIO

```
ThermalMouth:
  local_offset=[2,0,0]  conductance=2.0  area=1.0
  tau_heat=13.0  tau_cool=50.0  eta=0.02
```

核心机制（Newton 热传导 + 效率转化）：
```
dT_mouth = (T_env - T_mouth)/τ_heat - (T_mouth - T_body)/τ_cool) × dt
total_heat_flux = conductance × area × max(0, T_env - T_mouth) × dt
energy_intake = η × total_heat_flux
```

FIX-PHASE1-001：`src.absorb(total_heat_flux)` 扣除**全热通量**（非仅 η 部分），保证 Noether 热能守恒。  
FIX-PHASE1-002：`T_body = ecm_vestibular.temperature`（动态绑定，非硬编码常数）。

### 2.2 修改文件

#### `components/world.py`

| 新增内容 | 说明 |
|---------|------|
| `Body.yaw / angular_velocity / inertia / angular_friction` | 显式偏航状态（Phase 1 前使用速度方向推断，存在零速奇异性）|
| `Body.apply_yaw_torque(torque, dt)` | 指数衰减法（精确半步解 `I*dω/dt = τ - γω`），angular_friction=3.0 |
| `Body._collide_with_cylinder(src, dt)` | 法向速度反射 + 切向摩擦 + 几何推出 + damage_integral 注入（接入 Loop B）|
| `SkinPatch.world_position(body)` | 改为显式 yaw 旋转：`wx = lx*cos_y - ly*sin_y`（消除速度方向推断）|
| `World.__init__(cylindrical_sources=None)` | 接收柱状热源列表 |
| `World.temperature_at()` | Gaussian 柱热源叠加（`T += src.temperature_at(pos) - src.T_ambient`）|

#### `circuit/variant_adapter.py`

在 `VariantCircuit.__init__()` 末尾初始化柱状热源和热觉口器；在 `step()` 中新增五段逻辑（按执行顺序）：

1. **Z 轴锁定**（Phase 1 TEMP）：`position[2]=25.0; velocity[2]=0.0`
2. **偏航力矩**：`delta_T_lr = T_left - T_right; torque = delta_T_lr × YAW_GAIN(0.1)`
3. **对流漂移**（Phase 1b）：`body.velocity += k_conv(0.5) × ∇T × dt`
4. **碰撞检测 + 柱源步进**：`_collide_with_cylinder` + `_cylindrical_source.step(dt)`
5. **ThermalMouth 步进**：在 `energy_store.deposit(energy_absorbed)` 后调用

### 2.3 新建测试文件

#### `tests/diag_world2_physics.py` — 7 项物理层单元测试

| 编号 | 测试内容 | 结果 |
|------|---------|------|
| W1b | `_dist_to_cylinder_surface` 几何（内部/侧面/顶盖/棱角）| PASS |
| W1 | Gaussian 温度场（表面/σ处/3σ处/内部）| PASS |
| W1-world | `World.temperature_at()` 柱热源叠加 | PASS |
| W4 | 偏航动力学（初值/力矩/指数衰减/贴片90°位置）| PASS |
| W2/W3 | 碰撞检测（速度反射/damage注入）| PASS |
| W5/W6 | ThermalMouth 能量摄入（正值/口温升/无死锁）| PASS |
| W8 | 温差→偏航力矩方向 | PASS |

**7/7 PASS**

---

## 3. Phase 1a+1b 补丁（本次会话）

在完成基础实施后，分析 W9 原始实验（body 在轴线上，遗留热源干扰）发现两个问题，本次修复：

### 3.1 问题一：轴线对称性导致偏航力矩为零

原始配置 body 位置 `[82, 50, 25]`，热源中心 `[50, 50, 25]`，两者在同一 y 轴线上。

```
Left patch  [82, 51.3, 25]: dist_to_surface ≈ 26.03
Right patch [82, 48.7, 25]: dist_to_surface ≈ 26.03
→ T_left = T_right → delta_T_lr = 0 → yaw torque = 0
```

**修复**：body 偏轴启动 `[75.0, 35.0, 25.0]`，使左贴片比右贴片更靠近热源：
```
Left patch  [75, 37.3, 25]: dist ≈ 22 from surface → T_left ≈ 3.42
Right patch [75, 32.7, 25]: dist ≈ 24 from surface → T_right ≈ 3.18
→ delta_T_lr = +0.24 → positive yaw torque → CCW 转向热源 ✓
```

### 3.2 问题二：遗留 8 点热源制造 y 方向假梯度

原始世界包含 8 个八分区位点热源（radius=30），它们在 y 方向产生非对称信号，与柱状热源的梯度叠加产生混淆。在实验脚本中将 `circuit.world.heat_sources = []` 以隔离信号。

### 3.3 Phase 1b：热流对流漂移

在 `variant_adapter.py` 的偏航力矩段之后插入：

```python
_CONV_K = 0.5
_grad = self.world.gradient_at(self.world.body.position)
self.world.body.velocity[0] += _CONV_K * _grad[0] * dt
self.world.body.velocity[1] += _CONV_K * _grad[1] * dt
```

理论分析：
- 摩擦系数 μ=0.5，dt=0.001，系统时间常数 τ = m/μ = 1/0.5 = 2 s（物理时间），约 2000 步
- 到达终端速度：v_t = k_conv × |∇T| / μ ≈ 0.5 × 0.116 / 0.5 = 0.116 units/step
- 100k 步内预测漂移量：约 10 单位（从初始 dist=23 至 dist=13）

---

## 4. 回归验证

实施所有修改后，回归测试结果：

```
21/21 PASS（耗时 ~51s）
```

所有现有测试均无退化，物理层修改对信号传播链路透明。

---

**→ 接下文 Part 2：W9 探测实验结果与行为涌现分析**
