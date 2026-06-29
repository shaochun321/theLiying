# World 2.0 Phase 1 实施方案（v2.1）

**日期：** 2026-06-27  
**基础方案：** `J:\cell-cc\cell-cell\交叉方案\World 2.0-Phase 1 实施方案（修订版 v2）.md`  
**更新版本：** `J:\cell-cc\cell-cell\交叉方案\World 2.0 Phase 1 实施方案的更新版本.md`  
**可行性分析：** 本次会话（2026-06-27）  
**目标 repo：** `J:\cell-cc\cell-cc-other\nexus_v1\`

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v2.0 | 2026-06-27 | Loop B 确认、偏航方程修正、τ_heat 推导 |
| **v2.1** | **2026-06-27** | **热源扣费修正（总热通量）、T_body 绑定 ECM、Z 轴锁定** |

---

## 一、可行性确认结论

### Loop B（W3 关键依赖）✅ 已存在

`variant_adapter.py` 第 784-793 行：

```python
# ── Feedback Loop B: damage → EnergyStore repair metabolic cost ──
repair_cost = _total_damage * self.repair_energy_rate * dt
if repair_cost > 0:
    self.energy_store.withdraw(repair_cost)
```

`_total_damage = sum(patch_temps[pid][2] for pid in patch_temps)` — 汇总所有皮肤贴片的 `damage_integral`。

**结论：** 碰撞只需向 `front_patch.damage_integral` 追加 `K_impact × delta_E_kinetic`，Loop B 会自动转换为 `EnergyStore.withdraw()`。W3 无需额外实现。

### 其他已确认事项

| 项目 | 确认结果 |
|------|---------|
| `SkinPatch.world_position()` | 已存在，当前用速度向量推算朝向；World 2.0 改为用显式 `body.yaw` |
| `Body.effective_radius` | `(3×9/4π)^(1/3) ≈ 1.30` 单位，皮肤贴片放置于此半径处 |
| `temperature_at()` | 已存在（线性锥形场），World 2.0 替换为高斯柱体场 |
| 现有 `HeatSource` | 点源 + 线性衰减，World 2.0 保留接口但新建 `CylindricalHeatSource` |

---

## 二、方案 v2 的两处修正（实施前必读）

### 修正 1：偏航运动方程双重阻尼 Bug

**v2 原文有 bug**：`yaw_accel` 已包含线性摩擦，再乘以 `exp(-angular_friction×dt)` 等于施加两次阻尼，实际阻尼强度超出设计值数倍。

**正确实现（指数衰减法，推荐）：**

```python
# BIO: overdamped angular dynamics, viscous coupling to fluid medium
# τ = 1/angular_friction = 1/3.0 ≈ 0.33s at dt=0.001
angular_velocity = (
    angular_velocity + motor_torque / body.inertia * dt
) * math.exp(-body.angular_friction * dt)
body.yaw += angular_velocity * dt
```

此公式是阻尼简谐运动的精确半步长解，在 angular_friction=3.0、dt=0.001 下数值稳定（`exp(-3.0×0.001) ≈ 0.997`，每步衰减 0.3%）。

### 修正 2：口器 τ_heat 补全

**v2 原文缺失 `τ_heat`。** 推导：

目标：在柱体表面（T_env=5.0，T_body=0.15）口器稳态温度 ≈ 4.0（保留 20% 温差以维持持续供能）。

稳态方程：`T_ss × (1/τ_heat + 1/τ_cool) = T_env/τ_heat + T_body/τ_cool`

代入 T_ss=4.0，T_env=5.0，T_body=0.15，τ_cool=50 → **τ_heat ≈ 13 步**

验证：`T_ss = (5.0×50 + 0.15×13) / (50+13) = 251.95/63 ≈ 4.0` ✓

**口器完整温度方程：**
```python
dT_mouth = (T_env - mouth.temperature) / tau_heat - (mouth.temperature - T_body) / tau_cool
mouth.temperature += dT_mouth * dt
# tau_heat = 13, tau_cool = 50, T_body = 0.15
```

---

## 三、实施顺序与依赖关系

```
Step 1: CylindricalHeatSource + World.temperature_at()        → 解锁 W1、W5
Step 2: Body.yaw + SkinPatch.world_position()                 → 解锁 W4、W8
Step 3: 碰撞检测 + damage 注入                                → 解锁 W2、W3
Step 4: ThermalMouth（含总热通量扣费 + T_body→ECM 绑定）     → 解锁 W5、W6
Step 5: variant_adapter.py 集成（含 Z 轴锁定）               → 解锁 W8
Step 6: diag_world2_physics.py                                → 验证 W1-W8
Step 7: exp_world2_phase1.py                                  → 验证 W9
```

### 实施检查清单

- [ ] Step 1: CylindricalHeatSource + `temperature_at()` 高斯场
- [ ] Step 2: `Body.yaw/angular_velocity` + `SkinPatch.world_position()` 显式 yaw
- [ ] Step 3: 碰撞检测 + `front_patch.damage_integral` 注入
- [ ] Step 4: `ThermalMouth`（`total_heat_flux` 扣费 + `T_body = world.ecm_temperature`）
- [ ] Step 5: `variant_adapter.py` 集成（Z 轴锁定 `position[2]=25, velocity[2]=0`）
- [ ] Step 6: `diag_world2_physics.py` 8 项单元测试（W1-W8）
- [ ] Step 7: `exp_world2_phase1.py` 100k 步探测实验（W9）
- [ ] 回归：`python -m nexus_v1.tests.test_regression` → 21/21 PASS

---

## 四、Step 1：CylindricalHeatSource（新建文件）

**文件：** `nexus_v1/components/heat_source.py`

```python
"""nexus_v1.components.heat_source — Cylindrical heat source with Gaussian field.

TYPE:BIO — Analogous to hydrothermal vent: physical volume, finite energy,
Gaussian thermal diffusion from surface.

BIO: REF: hydrothermal vent thermal plume (Kelley et al. 2002 Science).
"""
import math
from dataclasses import dataclass, field
from typing import List


def _dist_to_cylinder_surface(pos: List[float], center: List[float],
                               radius: float, half_height: float) -> float:
    """Shortest distance from pos to cylinder surface. Returns 0 if inside."""
    dx = pos[0] - center[0]
    dy = pos[1] - center[1]
    dz = pos[2] - center[2]
    radial = math.sqrt(dx * dx + dy * dy)
    within_height = abs(dz) <= half_height

    if within_height:
        # Inside or outside the infinite cylinder
        return max(0.0, radial - radius)
    else:
        dz_to_rim = abs(dz) - half_height
        if radial <= radius:
            # Directly above/below the cap
            return dz_to_rim
        else:
            # Outside both radially and vertically (corner case)
            return math.sqrt((radial - radius) ** 2 + dz_to_rim ** 2)


@dataclass
class CylindricalHeatSource:
    """TYPE:BIO — Cylindrical heat source with Gaussian thermal field.

    BIO: Hydrothermal vent: physical volume + surface diffusion.
    SEMI: Thermal energy reservoir with first-order regeneration.
    """

    center: List[float]          # [x, y, z] of cylinder axis midpoint
    radius: float = 6.0          # collision / thermal radius (units)
    height: float = 16.0         # total height (±8 from center)
    T_surface: float = 5.0       # base surface temperature
    T_ambient: float = 0.15      # far-field ambient temperature
    sigma: float = 25.0          # Gaussian diffusion length (units)
    energy: float = 1000.0       # remaining thermal energy
    energy_initial: float = field(default=None, repr=False)
    regeneration_rate: float = 0.002  # energy replenishment per step

    def __post_init__(self):
        if self.energy_initial is None:
            self.energy_initial = self.energy

    @property
    def alive(self) -> bool:
        return self.energy > 0.01

    @property
    def effective_T_surface(self) -> float:
        """Surface temperature scales with remaining energy."""
        if self.energy <= 0:
            return self.T_ambient
        frac = min(1.0, self.energy / self.energy_initial)
        return self.T_ambient + (self.T_surface - self.T_ambient) * frac

    def temperature_at(self, pos: List[float]) -> float:
        """Gaussian field from cylinder surface."""
        if not self.alive:
            return self.T_ambient
        d = _dist_to_cylinder_surface(pos, self.center, self.radius,
                                       self.height / 2.0)
        return self.T_ambient + (self.effective_T_surface - self.T_ambient) * math.exp(
            -d * d / (2.0 * self.sigma * self.sigma)
        )

    def absorb(self, amount: float) -> float:
        """Deduct absorbed energy. Returns actual deducted amount."""
        actual = min(amount, self.energy)
        self.energy -= actual
        return actual

    def step(self, dt: float = 1.0):
        """Regenerate energy up to initial level."""
        self.energy = min(self.energy_initial,
                          self.energy + self.regeneration_rate * dt)
```

**World.temperature_at() 修改：**

在 `world.py` 的 `World` 类中，新增 `cylindrical_sources: List[CylindricalHeatSource]`，并修改 `temperature_at()`：

```python
def temperature_at(self, pos: List[float]) -> float:
    """Gaussian temperature field from all cylindrical heat sources."""
    T = 0.15  # T_ambient baseline
    for src in self.cylindrical_sources:
        if src.alive:
            T += src.temperature_at(pos) - 0.15  # add delta above ambient
    # Legacy point sources (if any) — keep for backward compat
    for src in self.heat_sources:
        if src.alive:
            d = _distance(pos, src.position)
            if d < src.radius:
                T += src.effective_temperature() * (1.0 - d / src.radius)
    return T
```

---

## 五、Step 2：Body 偏航 + SkinPatch.world_position()

**修改文件：** `nexus_v1/components/world.py`

### Body 新增字段（在 `@dataclass class Body` 中）

```python
# World 2.0: explicit yaw orientation (rotation around z-axis)
yaw: float = 0.0              # current heading angle (radians)
angular_velocity: float = 0.0 # yaw rate (rad/step)
inertia: float = 1.0          # moment of inertia
angular_friction: float = 3.0 # overdamped: τ = 1/3.0 ≈ 0.33s
```

### Body.apply_yaw_torque() 新增方法

```python
def apply_yaw_torque(self, torque: float, dt: float = 0.001):
    """Overdamped angular dynamics (exponential decay formulation).

    BIO: viscous drag in fluid medium dominates angular momentum.
    PHYS: exact half-step solution to: I*dω/dt = τ - γ*ω
    """
    self.angular_velocity = (
        self.angular_velocity + torque / self.inertia * dt
    ) * math.exp(-self.angular_friction * dt)
    self.yaw += self.angular_velocity * dt
    # Wrap yaw to [-π, π]
    self.yaw = (self.yaw + math.pi) % (2 * math.pi) - math.pi
```

### SkinPatch.world_position() 替换

将现有的速度推算朝向逻辑替换为显式 yaw 旋转：

```python
def world_position(self, body: 'Body') -> List[float]:
    """Patch world position via explicit yaw rotation around z-axis.

    Body frame: x=forward, y=left, z=up.
    World frame: yaw=0 → body points in +x direction.
    """
    cos_y = math.cos(body.yaw)
    sin_y = math.sin(body.yaw)
    lx, ly, lz = self.local_offset
    wx = lx * cos_y - ly * sin_y
    wy = lx * sin_y + ly * cos_y
    return [
        body.position[0] + wx,
        body.position[1] + wy,
        body.position[2] + lz,
    ]
```

> **注意：** 原 `world_position()` 从速度推算朝向。改为显式 yaw 后，初始 yaw=0 对应 +x 朝向。如果实验脚本设置了特定的初始速度方向，需要相应初始化 `body.yaw`。

---

## 六、Step 3：碰撞检测 + damage 注入

**修改位置：** `world.py` 中 `Body` 的位置更新逻辑（`update_position()` 或等价方法）

在每步位置更新之后、skin patch 采样之前，对每个柱体热源检测碰撞：

```python
def _collide_with_cylinder(self, src: 'CylindricalHeatSource', dt: float):
    """Viscous collision response + damage injection.

    PHYS: normal velocity reflected+damped; tangential velocity reduced by friction.
    BIO: collision → mechanical stress → skin damage → Loop B repair cost.
    """
    # Compute normal vector (horizontal only, yaw-plane collision)
    dx = self.position[0] - src.center[0]
    dy = self.position[1] - src.center[1]
    dist_xy = math.sqrt(dx * dx + dy * dy + 1e-12)
    nx, ny = dx / dist_xy, dy / dist_xy  # horizontal outward normal

    body_r = self.effective_radius
    collision_dist = src.radius + body_r

    # Check if within cylinder height range
    dz = self.position[2] - src.center[2]
    within_height = abs(dz) <= src.height / 2.0

    if within_height and dist_xy < collision_dist:
        # ── Velocity response ──
        vx, vy = self.velocity[0], self.velocity[1]
        v_normal = vx * nx + vy * ny  # normal component (positive = away)
        if v_normal < 0:  # approaching
            vtx = vx - v_normal * nx
            vty = vy - v_normal * ny
            # Reflect + damp normal; reduce tangential
            vx_new = (-v_normal * 0.7) * nx + vtx * 0.9
            vy_new = (-v_normal * 0.7) * ny + vty * 0.9
            v_after_sq = vx_new**2 + vy_new**2 + self.velocity[2]**2
            v_before_sq = vx**2 + vy**2 + self.velocity[2]**2
            self.velocity[0] = vx_new
            self.velocity[1] = vy_new

            # ── Geometric pushout (prevent float tunneling) ──
            overpenetration = collision_dist + 0.01 - dist_xy
            self.position[0] += nx * overpenetration
            self.position[1] += ny * overpenetration

            # ── Damage injection → Loop B ──
            delta_KE = 0.5 * self.mass * max(0.0, v_before_sq - v_after_sq)
            K_impact = 0.01  # EXP-W2-001: to be calibrated in Phase 1
            # Inject into front patch (facing the collision)
            for patch in self.skin_patches:
                if patch.patch_id == "front":
                    patch.damage_integral += K_impact * delta_KE
                    break
```

在 `Body` 的 `step()` 或位置更新主循环末尾调用：
```python
for src in world.cylindrical_sources:
    if src.alive:
        self._collide_with_cylinder(src, dt)
```

### 硬边界（已有 or 确认存在）

若现有代码中已有边界钳位，确认逻辑：
```python
for i in range(3):
    if self.position[i] < 0.0:
        self.position[i] = 0.0
        self.velocity[i] = abs(self.velocity[i]) * 0.8
    elif self.position[i] > 100.0:
        self.position[i] = 100.0
        self.velocity[i] = -abs(self.velocity[i]) * 0.8
```

---

## 七、Step 4：ThermalMouth（新建文件）

**文件：** `nexus_v1/components/thermal_mouth.py`

```python
"""nexus_v1.components.thermal_mouth — Oral thermal energy intake via temperature gradient.

TYPE:BIO — Analogous to chemosynthetic feeding: organism absorbs thermal
energy through mouth organ when warmer than environment.

BIO: REF: thermosynthesis in hydrothermal vent organisms (Muller 1995).
PHYS: Fourier heat transfer + body cooling pool (blood circulation analog).

Parameters (all require justification):
  k=2.0    # NORM: same as SkinPatch conductance (world.py)
  A=1.0    # NORM: unit area, dimensionally consistent
  eta=0.02 # EXP-W2-002: heat-to-metabolic conversion efficiency; to calibrate
  tau_heat=13  # DERIVED: yields T_mouth_ss≈4.0 at T_env=5.0, T_body=0.15, tau_cool=50
  tau_cool=50  # DESIGN: slow drainage maintains temperature differential
"""
import math
from dataclasses import dataclass


@dataclass
class ThermalMouth:
    """TYPE:BIO — Oral thermal exchange organ."""

    # Position in body frame (forward-facing)
    local_offset: list = None  # set in __post_init__ to [body_r+0.5, 0, 0]

    # Thermal physics
    temperature: float = 0.15    # initial mouth temperature = T_ambient
    # T_body: dynamically read from world.ecm_temperature in step() (修正4)
    # Do NOT hardcode T_body — binds mouth cooling to ECM thermal state.
    conductance: float = 2.0     # k: same as SkinPatch (NORM: world.py)
    area: float = 1.0            # A: heat exchange area
    eta: float = 0.02            # η: heat→metabolic conversion efficiency
    tau_heat: float = 13.0       # DERIVED: see module docstring
    tau_cool: float = 50.0       # DESIGN: slow drainage to maintain ΔT

    # State
    energy_intake: float = 0.0   # energy deposited this step

    def __post_init__(self):
        if self.local_offset is None:
            self.local_offset = [2.0, 0.0, 0.0]  # 2.0 ≈ body_radius + 0.5

    def world_position(self, body) -> list:
        """Mouth world position, rotated with body yaw."""
        cos_y = math.cos(body.yaw)
        sin_y = math.sin(body.yaw)
        lx, ly, lz = self.local_offset
        return [
            body.position[0] + lx * cos_y - ly * sin_y,
            body.position[1] + lx * sin_y + ly * cos_y,
            body.position[2] + lz,
        ]

    def step(self, world, body, energy_store, dt: float = 0.001):
        """Update mouth temperature and deposit energy into EnergyStore.

        PHYS: dT_mouth/dt = (T_env - T_mouth)/tau_heat - (T_mouth - T_body)/tau_cool
        FIX-PHASE1-002: T_body dynamically bound to ECM temperature.
          Enables "fever → appetite suppression" to emerge naturally.
          Noether audit can track heat transfer mouth → ECM.
        Returns energy_intake this step.
        """
        pos = self.world_position(body)
        T_env = world.temperature_at(pos)

        # FIX-PHASE1-002: read T_body from ECM, not hardcoded constant.
        # Fallback 0.15 = T_ambient for environments without ECM.
        T_body = getattr(world, 'ecm_temperature', 0.15)

        # Thermal dynamics (Euler step)
        dT = ((T_env - self.temperature) / self.tau_heat
              - (self.temperature - T_body) / self.tau_cool)
        self.temperature += dT * dt

        # Energy intake: only when mouth is cooler than environment
        delta_T = max(0.0, T_env - self.temperature)
        total_heat_flux = self.conductance * self.area * delta_T * dt
        self.energy_intake = self.eta * total_heat_flux

        if self.energy_intake > 0:
            energy_store.deposit(self.energy_intake)
            # FIX-PHASE1-001: deduct total heat flux, not just converted ATP.
            # eta=0.02 means 2% → EnergyStore, 98% waste heat still extracted
            # from heat source (first law of thermodynamics).
            for src in getattr(world, 'cylindrical_sources', []):
                if src.alive:
                    src.absorb(total_heat_flux)  # ← total, not energy_intake
                    break

        return self.energy_intake
```

---

## 八、Step 5：variant_adapter.py 集成

### 新增初始化（`__init__` 末尾）

```python
# World 2.0: thermal mouth (oral energy intake)
from ..components.thermal_mouth import ThermalMouth
self.thermal_mouth = ThermalMouth()
```

### step() 中集成（能量段，`self.yolk_sac.step()` 之后）

```python
# FIX-PHASE1-003: Phase 1 planar approximation — lock Z axis.
# Body motion constrained to Z=25 plane. Prevents non-physical vertical
# ejection when body enters cylinder height range from above/below.
# TEMP: to be removed in Phase 2 (full 3D motion).
self.body.position[2] = 25.0
self.body.velocity[2] = 0.0

# World 2.0: thermal mouth energy intake
self.thermal_mouth.step(self.world, self.body, self.energy_store, dt)

# World 2.0: yaw torque from left-right temperature differential
# BIO: spinal thermal reflex — immediate postural response to gradient
# REF: thermotaxis reflex arcs (Hedgecock & Russell 1975, C. elegans)
patch_temps = self.body.sample_skin(self.world, dt)  # already called above
T_left  = patch_temps.get("left",  (0.15, 0, 0))[0]
T_right = patch_temps.get("right", (0.15, 0, 0))[0]
delta_T_lr = T_left - T_right
YAW_GAIN = 0.1  # EXP-W2-003: to calibrate; positive → turn toward warmer side
motor_torque = delta_T_lr * YAW_GAIN
self.body.apply_yaw_torque(motor_torque, dt)
```

---

## 九、Step 6：diag_world2_physics.py（单元测试）

**文件：** `nexus_v1/tests/diag_world2_physics.py`

必须覆盖的测试用例：

```
W1: temperature_at() 连续性
  - 柱体内部点 → T ≈ T_surface
  - 柱体表面点 → T = T_surface × exp(0) = T_surface
  - 距离 σ 处 → T ≈ T_surface × exp(-0.5) ≈ 0.607 × T_surface
  - 距离 3σ 处 → T ≈ T_ambient

W1b: 柱体距离函数 _dist_to_cylinder_surface()
  - 内部点 → 0.0
  - 正侧面点（在高度范围内）→ 水平距离 - radius
  - 正上方帽面点 → 垂直距离 - half_height
  - 帽沿角点 → sqrt(Δr² + Δz²)

W4: 偏航动力学
  - 初始 yaw=0，施加正力矩，yaw 应增加
  - 撤去力矩后，angular_velocity 应以 exp(-3.0×dt) 速率衰减
  - SkinPatch.world_position() 随 yaw=π/2 旋转 90°

W2/W3: 碰撞
  - body 推入柱体 → 位置推出，velocity 反向衰减
  - front_patch.damage_integral 增加
  - 连续 1000 步碰撞后 energy_store.fill_fraction 下降

W5/W6: 口器供能
  - 置于 T_env=5.0 处，1000 步后 energy_store 应有正增量
  - 置于柱体中心 10000 步，energy_intake 不应归零（无热平衡死锁）

W7: 边界反弹
  - body 冲向 x=0 边界，velocity[0] 应反转
  - body 冲向 x=100 边界，velocity[0] 应反转

W8: 温差→偏航
  - T_left=3.0, T_right=1.0 → motor_torque=0.2 → body.yaw 增加
```

---

## 十、Step 7：exp_world2_phase1.py（探测实验）

**文件：** `nexus_v1/tests/exp_world2_phase1.py`

**初始条件：**
```python
# Single cylindrical heat source at world center
cylindrical_sources = [CylindricalHeatSource(
    center=[50.0, 50.0, 50.0],
    radius=6.0, height=16.0,
    T_surface=5.0, sigma=25.0,
    energy=1000.0, regeneration_rate=0.002
)]
# Body starts 20 units from cylinder surface (dist=26 from center)
body = Body(position=[76.0, 50.0, 50.0], ...)
# YolkSac: 200 units initial reserve
```

**验收标准 W9：** 100k 步后 `fill_fraction > 0`（口器供能接替 YolkSac）

**监控字段（每 1000 步输出一行）：**
```
step | fill | yolk% | mouth_intake | dist_to_cylinder | yaw | T_front | T_left | T_right | Nv
```

---

## 十一、参数标定计划（Phase 1 过程中）

| 参数 | 暂定值 | 标定方法 | 合理范围判断 |
|------|--------|----------|-------------|
| `K_impact` | 0.01 | 碰撞 100 次后检查 fill 下降幅度 | 下降 5-20%/百次碰撞 |
| `eta`（热电转换效率）| 0.02 | 在柱体表面静止，测定稳态 energy_intake | 应 > 基础代谢率 ≈ 0.001/步 |
| `YAW_GAIN` | 0.1 | 固定 ΔT=1.0，测定 10k 步后 yaw 偏转量 | 应在 0.1~1.0 rad 之间 |
| `tau_heat` | 13 | 固定 T_env，测定口器温度平衡曲线 | T_ss ≈ 0.75-0.85 × T_env |

---

## 十二、回归保护

实施完成后必须运行：

```bash
cd /j/cell-cc/cell-cc-other
PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.test_regression
# 必须 21/21 PASS
```

如有回归，在 `degradation_registry.md` 记录 DEG-XXX 并立即定位根因。

---

## 十三、文件变更清单（完整）

| 文件 | 操作 | 关键变更 |
|------|------|---------|
| `components/heat_source.py` | **新建** | `CylindricalHeatSource`，`_dist_to_cylinder_surface()` |
| `components/thermal_mouth.py` | **新建** | `ThermalMouth`；τ_heat=13；`total_heat_flux` 扣费；`T_body→ECM` 动态绑定 |
| `components/world.py` | **修改** | `World.temperature_at()` 高斯场；`Body.yaw/angular_velocity/inertia/angular_friction`；`Body.apply_yaw_torque()`；`Body._collide_with_cylinder()`；`SkinPatch.world_position()` 用显式 yaw |
| `circuit/variant_adapter.py` | **修改** | Z 轴锁定（Phase 1）；`ThermalMouth` 集成；偏航力矩计算；`World` 构造传入 `cylindrical_sources` |
| `tests/diag_world2_physics.py` | **新建** | 物理层 8 项单元测试（W1-W8） |
| `tests/exp_world2_phase1.py` | **新建** | 100k 步探测实验脚本（W9） |

---

## 十四、v2.1 三处修正说明（设计意图）

### 修正 3：热源扣费 = 总热通量

`src.absorb(total_heat_flux)` 扣除全部提取热量，而非仅 `energy_intake`。`eta=0.02` 控制转化效率，2% 进入 `EnergyStore`，98% 废热仍来自热源。废热散失到环境后会通过温度场重新分布——但热源能量余额必须反映全部提取，否则热源能量被低估，违反热力学第一定律。

### 修正 4：T_body 绑定 ECM 温度

`T_body = getattr(world, 'ecm_temperature', 0.15)` 使口器散热路径可被 Noether 审计追踪。物理闭环：ECM 温度升高 → 口器与体内温差缩小 → 散热效率降低 → 进食功率下降。"发烧→食欲不振"从物理结构中涌现，无需硬编码。

### 修正 5：Z 轴锁定（Phase 1 工程简化）

`position[2] = 25.0; velocity[2] = 0.0`，在 `variant_adapter.step()` 位置更新之后执行。解决从柱体正上方降落时 `within_height` 突变导致的非物理水平弹射。**这是临时简化**，Phase 2 解除锁定，恢复完整 3D 运动。代码注释标注 `# TEMP: remove in Phase 2`。

---

## 十五、P2 技术债（不阻塞 Phase 1，独立并行）

| 技术债 | 修复方向 | 状态 |
|--------|----------|------|
| V-03 Deviation Reflex 结构化 | `DeviationRelayNeuron` + STDP 束 | P2，待处理 |
| V-04 Xin Relay Bundle 化 | `XinIntegratorNeuron` 适配器 + Bundle | P2，待处理 |
| Shadow `K_ema` 发散 | 添加指数衰减项（`energy_ledger.py`）| P2，待处理 |
| `xin_conservation` 违规 | 检查 `Memristor.apply_dw` 是否绕过 KCL | P2，待处理 |

以上均与 World 2.0 Phase 1 无文件冲突，可在 Phase 1 实施过程中并行推进。
