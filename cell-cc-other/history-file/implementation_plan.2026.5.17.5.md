# Phase 1 修正版：介质作为物理实体

**核心修正**: 介质不是公式，介质是**第四个物理系统**。

---

## 架构对比

### ❌ 路径 A（已否决）

```python
# "上帝视角"：直接在公式里写 e^{-αr}
def received_at(self, pos, t):
    return A * exp(-alpha * r) / r**n   # α 从哪来？凭空的数字
```

### ✅ 路径 C（采纳）

```python
# 介质是物理实体：信号在介质粒子间传播
class Medium3D:
    """介质晶格。信号从源注入后在粒子间逐 tick 传播。"""
    particles: List[MediumParticle]  # 轻质、固定位置、有阻尼
    
# 衰减不是公式——衰减是粒子阻尼导致的能量损耗
# 速度不是参数——速度是 √(k/m) 从弹簧常数和质量涌现
# 阻抗不是系数——阻抗是 ρ·v = √(k·m) 从材料属性涌现
```

---

## Medium3D 物理设计

### 1. 结构：晶格粒子

介质粒子不是自由体。它们固定在 3D 晶格上，只能做微小振动——就像晶体中的原子。

```python
@dataclass
class MediumParticle:
    """介质晶格节点。固定位置，只做振动。"""
    gid: int                    # grid index
    x0: float; y0: float; z0: float  # 平衡位置 (固定)
    ux: float; uy: float; uz: float  # 位移 (振动)
    vx: float; vy: float; vz: float  # 速度
    energy: float               # 携带的信号能量
    
    # 材料属性 (从 Medium 类型继承)
    mass: float                 # 粒子质量
    damping: float              # 阻尼系数 → 产生吸收
```

### 2. 物质：三种介质类型

| 属性 | 空气介质 (acoustic) | 热介质 (thermal) | 光介质 (luminous) |
|---|---|---|---|
| **粒子质量 m** | 1.0 (空气密度) | 5.0 (组织密度) | 0.001 (光子无质量, 用极小值) |
| **弹簧刚度 k** | 2.0 | 0.05 | 1000.0 |
| **阻尼 γ** | 0.01 (空气低阻尼) | 0.5 (组织高阻尼) | 0.0001 (光几乎不损耗) |
| **晶格间距 d** | 0.5 | 0.5 | 0.5 |

### 3. 物理：涌现属性

从上面三个材料常数，以下物理量**自动涌现**：

```
传播速度:     v = d · √(k/m)
  acoustic:   v = 0.5 × √(2.0/1.0)   = 0.707 unit/tick
  thermal:    v = 0.5 × √(0.05/5.0)   = 0.05  unit/tick
  luminous:   v = 0.5 × √(1000/0.001) = 500   unit/tick

穿透深度:     L_pen = v / γ  (阻尼导致的 1/e 衰减距离)
  acoustic:   L_pen = 0.707 / 0.01  = 70.7  units (远超 box)
  thermal:    L_pen = 0.05 / 0.5    = 0.1   units (极短！)
  luminous:   L_pen = 500 / 0.0001  = 5×10⁶ units (无穷)

特征阻抗:     Z = √(k·m) / d²
  acoustic:   Z = √(2×1) / 0.25     = 5.66
  thermal:    Z = √(0.05×5) / 0.25  = 2.0
  luminous:   Z = √(1000×0.001) / 0.25 = 4.0
```

> [!IMPORTANT]
> **thermal 的穿透深度只有 0.1 units！** 这意味着 thermal 信号在介质中传播 0.1 个单位就衰减到 1/e。
> 这太短了——我们需要调整。
>
> 修正：thermal 不是弹性波传播，是**扩散**。它的传播方程不同：
> - 波：$\partial^2 u / \partial t^2 = (k/m) \nabla^2 u - \gamma \partial u / \partial t$
> - 扩散：$\partial T / \partial t = \kappa \nabla^2 T$
>
> 这是两种不同的物理机制，需要不同的更新规则。

---

## 信号传播的两种物理机制

### 机制 1：波动传播 (acoustic, luminous)

```python
def propagate_wave(self, dt):
    """弹性波传播：d²u/dt² = (k/m)·∇²u - γ·du/dt"""
    for p in self.particles:
        # 弹簧力来自邻居的位移差
        fx = fy = fz = 0.0
        for nb in p.neighbors:
            fx += self.k * (nb.ux - p.ux)
            fy += self.k * (nb.uy - p.uy)
            fz += self.k * (nb.uz - p.uz)
        # 阻尼
        fx -= self.gamma * p.vx
        fy -= self.gamma * p.vy
        fz -= self.gamma * p.vz
        # 加速度 = F/m
        ax = fx / p.mass
        ay = fy / p.mass
        az = fz / p.mass
        # Verlet 积分
        p.vx += ax * dt;  p.vy += ay * dt;  p.vz += az * dt
        p.ux += p.vx * dt; p.uy += p.vy * dt; p.uz += p.vz * dt
        # 能量 = 0.5 * m * v²
        p.energy = 0.5 * p.mass * (p.vx**2 + p.vy**2 + p.vz**2)
```

### 机制 2：扩散传播 (thermal)

```python
def propagate_diffusion(self, dt):
    """热扩散：dT/dt = κ·∇²T - λ·T"""
    new_energy = [0.0] * len(self.particles)
    for i, p in enumerate(self.particles):
        laplacian = 0.0
        for nb in p.neighbors:
            laplacian += (nb.energy - p.energy)
        laplacian /= (self.spacing ** 2)
        # 扩散 + 衰减
        new_energy[i] = p.energy + dt * (self.kappa * laplacian - self.decay * p.energy)
    for i, p in enumerate(self.particles):
        p.energy = max(0.0, new_energy[i])
```

---

## 阻抗匹配：从密度比涌现

当信号从**介质**到达**身体**（ParticleSystem3D 的粒子），发生界面耦合。

```
   介质粒子 (mass=m_med, k=k_med)
       ↕  界面
   身体粒子 (mass=m_body, k=k_body)
```

透射系数从两种材料的特征阻抗之比涌现：

$$T = \frac{2 Z_{body}}{Z_{body} + Z_{medium}} = \frac{2\sqrt{k_b m_b}}{\sqrt{k_b m_b} + \sqrt{k_m m_m}}$$

```python
# 身体粒子 (ParticleSystem3D):
#   m_body = 1.0, k_body = 2.0 → Z_body = √2 ≈ 1.41

# acoustic 介质:
#   Z_med = 5.66 → T = 2×1.41/(1.41+5.66) = 0.40

# thermal 介质:
#   Z_med = 2.0  → T = 2×1.41/(1.41+2.0) = 0.83

# luminous 介质:
#   Z_med = 4.0  → T = 2×1.41/(1.41+4.0) = 0.52
```

> [!NOTE]
> 这些透射系数是**从结构涌现的**，不是手动设定的！
> acoustic T=0.40 < luminous T=0.52 < thermal T=0.83
> 
> 对比真实生物：中耳补偿后 T≈0.6, 皮肤 T≈0.3, 视网膜 T≈0.8。
> 数值不完全匹配——因为我们还没有"中耳"这个适配器。
> **中耳是一个专门用来提高 T 的进化产物。我们的系统还没进化到那一步。**

---

## 完整信号链路

```
tick t:
  1. 源注入: QuantitySource 在自身位置的介质粒子上注入能量
  2. 介质传播: Medium3D.step() — 波动或扩散
  3. 界面耦合: 身体表面粒子接收介质粒子的能量 × T
  4. 感觉读取: PracticeEngine 读取身体表面粒子的接收能量
  5. 积分+taxis: 与现有流程相同
```

---

## 实现文件

### [NEW] engines/medium_system.py

```
MediumParticle     晶格节点 (位置固定, 只振动/携带能量)
MediumLattice3D    晶格系统
  ├── __init__(medium_type, box_size, spacing)
  │     根据 medium_type 设置 m, k, γ
  │     生成 3D 均匀晶格
  │     建立近邻连接 (6-连通 或 26-连通)
  ├── inject(source_pos, amplitude, t)
  │     在最近的晶格节点注入能量
  ├── step()
  │     wave: Verlet 积分
  │     diffusion: 有限差分扩散
  ├── read_at(observer_pos) → float
  │     在观察者位置插值读取能量
  └── coupling_force(body_particle) → (fx, fy, fz)
        界面力传递
```

### [MODIFY] practice_engine.py

| 修改 | 内容 |
|---|---|
| `__init__` | 创建 3 个 MediumLattice3D (acoustic, thermal, luminous) |
| `step` | 每 tick: (1) 源注入 (2) 介质传播 (3) 读取替代 `received_at` |
| `received_at` | 保留作为 fallback (α=0 模式), 标注为 DEGRADED |
| `gradient_at` | 从介质场的空间差分计算, 不再用解析公式 |
| 降级标注 | 更新: "RECOVERED: medium propagation" |

### [NEW] experiments/_phase1_medium_test.py

验证:
1. 波在 acoustic 介质中以 v = d·√(k/m) 速度传播
2. 热在 thermal 介质中扩散, 穿透深度符合 √(κ/f)
3. 阻抗匹配透射系数与理论一致
4. DERC 与 Phase 0 对比

---

## 计算量评估

### 晶格规模

```
box_size = 10, spacing = 0.5
→ 20 × 20 × 20 = 8000 晶格粒子 per medium
→ 3 media × 8000 = 24000 粒子
→ 每个粒子 6 邻居 → 24000 × 6 = 144000 弹簧力计算/tick
```

> [!WARNING]
> **24000 粒子 vs 当前 30 粒子。计算量增加 ~800×。**
>
> 优化方案：
> 1. 降低分辨率: spacing=1.0 → 10³=1000 粒子/medium → 可行
> 2. 只计算源附近的活跃区域 (稀疏更新)
> 3. thermal 用扩散方程 (不需要 velocity, 节省一半变量)
> 4. luminous 用解析近似 (v 太快, 实质即时) → 不需要晶格

### 优化后的方案

```
acoustic: 1000 粒子晶格, 波动传播       → 主要计算
thermal:  1000 粒子晶格, 扩散传播       → 轻量
luminous: 保持解析公式 (v=∞ 近似)       → 零成本
                                        → 总计 ~2000 粒子
```

---

## 降级标注

```python
class MediumLattice3D:
    """3D 晶格介质系统。
    
    信号在晶格粒子间通过弹簧力链 (波) 或能量扩散 (热)
    逐 tick 传播。衰减、速度、阻抗从材料属性涌现。
    
    DEGRADED: 连续波动方程 (∇²Φ - v⁻²∂²ₜΦ = 0) → 离散质点弹簧晶格
    degraded_from = "wave_equation_FDTD"
    DEGRADED: 非均匀介质 (ρ(x), k(x)) → 均匀晶格
    degraded_from = "heterogeneous_medium"
    DEGRADED: 散射 (Rayleigh, Mie) → 无散射
    degraded_from = "scattering_cross_section"
    DEGRADED: 多模态耦合 (声热耦合) → 独立介质
    degraded_from = "coupled_multiphysics"
    """
```

---

## 验证假说

| # | 假说 | 如何检验 |
|---|---|---|
| H1 | 波在介质中速度 = d·√(k/m) | 脉冲注入, 测量到达时间 vs 距离 |
| H2 | thermal 穿透深度 = √(κ·t) | 阶跃注入, 测量能量前沿位置 vs 时间 |
| H3 | 透射系数 T = 2Z_b/(Z_b+Z_m) | 测量界面处入射/透射能量比 |
| H4 | 保持 DERC 三区结构 | N=20 DERC 扫描 |
| H5 | thermal 源在 L > L_pen 处无 taxis | 单源远距离实验 |

## 时间估计

| 步骤 | 时间 |
|---|---|
| MediumParticle + MediumLattice3D 基础 | 1 天 |
| 波动传播 + 测试 | 1 天 |
| 扩散传播 + 测试 | 1 天 |
| 阻抗匹配界面 | 1 天 |
| PracticeEngine 集成 | 1 天 |
| DERC + 拉丁方验证 | 1 天 |
| 性能优化 | 1 天 |
| 论文图表 | 1 天 |
| **总计** | **~8 天** |
