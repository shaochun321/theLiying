# 最小实验: 热感 + 运动耦合 → 观察超图分化

## 目标

**不做进食消化。** 只加热感 + 运动，观察：
1. 现有赫布超图能否承载新模态
2. 绑定层是否自然产生分化区域
3. 影子层跨轴权重是否出现跨模态特征

## 最小实现

只需 3 个新文件 + 2 个修改：

---

### [NEW] `nexus_v1/components/world.py`

3D 空间 + 可消耗热源 + Body 物理。极简。

```python
@dataclass
class HeatSource:
    position: list       # [x, y, z]
    energy: float = 50.0 # 可消耗（每步被附近生物吸收）
    temperature: float = 5.0
    radius: float = 20.0 # 影响半径

class Body:
    position: list = [50, 50, 50]  # 3D
    velocity: list = [0, 0, 0]
    mass: float = 1.0
    friction: float = 0.5
    
    def step(self, forces, dt):
        """F = ma - μv"""
        for i in range(3):
            a = (forces[i] - self.friction * self.velocity[i]) / self.mass
            self.velocity[i] += a * dt
            self.position[i] += self.velocity[i] * dt

class World:
    heat_sources: List[HeatSource]
    body: Body
    ambient_temp: float = 0.1
    
    def temperature_at(self, pos) -> float
    def gradient_at(self, pos) -> Vec3
    def consume_nearby(self, pos, amount) -> float
```

**~80 行代码。**

---

### [NEW] `nexus_v1/components/thermal_membrane.py`

表皮热感。6 方向受体簇 + 甲基化适应。

```python
class ThermalMembrane:
    """细胞膜热感表皮"""
    
    cluster_directions = [
        [+1,0,0], [-1,0,0],  # ±x
        [0,+1,0], [0,-1,0],  # ±y
        [0,0,+1], [0,0,-1],  # ±z
    ]
    body_radius: float = 1.0
    methylation: list  # 6 个适应状态
    methylation_tau: float = 200
    _prev_T: float = 0.0
    
    def sense(self, world, body) -> dict:
        """返回 {'therm': T_adapted, 'dtherm': dT/dt}"""
        # 1. 各簇位置温度
        T_clusters = []
        for d in self.cluster_directions:
            pos = [body.position[i] + d[i] * self.body_radius for i in range(3)]
            T_clusters.append(world.temperature_at(pos))
        
        # 2. 甲基化适应
        for i in range(6):
            self.methylation[i] += (T_clusters[i] - self.methylation[i]) * dt / self.methylation_tau
            T_clusters[i] -= self.methylation[i]  # 减去适应基线
        
        # 3. 输出
        T_mean = sum(T_clusters) / 6
        dT = T_mean - self._prev_T
        self._prev_T = T_mean
        
        return {'therm': T_mean, 'dtherm': dT}
```

**~60 行代码。**

---

### [NEW] `nexus_v1/components/muscle.py`

Motor → 力 → Body 移动。极简。

```python
class MuscleGroup:
    """3 组肌肉 (xyz)，接 Motor neurons"""
    gain: float = 0.1
    max_force: float = 1.0
    delay_steps: int = 2
    _buffer: deque  # FIFO 延迟
    
    def contract(self, motor_activation: float) -> float:
        force = clamp(motor_activation * self.gain, -self.max_force, self.max_force)
        self._buffer.append(force)
        return self._buffer.popleft() if len(self._buffer) > self.delay_steps else 0
```

**~30 行代码。**

---

### [MODIFY] `nexus_v1/circuit/hebbian.py`

在 6 轴基础上新增第 7 轴 `therm`。

改动点：
- `AXES` 列表: `['yaw','pitch','roll','oto_x','oto_y','oto_z']` → 加 `'therm'`
- 新增 2 个编码神经元: `enc_reg_therm`, `enc_irr_therm`
- 新增 1 个列神经元: `col_therm`
- 新增 Bundle: `enc_to_col_therm`
- 绑定层: C(6,2)=15 → C(7,2)=21

> [!WARNING]
> **热轴不经过前庭链 (MET→HC→Aff)**。直接从 ThermalMembrane → Encoding。
> 这对应真实生物: 热感比前庭少 1 级（无 HairCell）。
> 意味着热信号比前庭信号**早 1 步**到达编码层。

---

### [MODIFY] `nexus_v1/circuit/variant_adapter.py`

在 step() 中集成 World + Body + Muscle + ThermalMembrane。

```python
def step(self, signal, dt=0.001):
    # 0. Motor → Muscle → Body 移动
    forces = [self.muscles[i].contract(self.motor_neurons[axis].activation) 
              for i, axis in enumerate(['x','y','z'])]
    self.world.body.step(forces, dt)
    
    # 1. 热感
    therm_signal = self.thermal_membrane.sense(self.world, self.world.body)
    
    # 2. 合并信号: 前庭 6 轴 + 热 1 轴
    signal['therm'] = therm_signal['therm']
    # dtherm 映射到 irr 通道（通过编码层 irr neuron）
    
    # 3. 正常 step（现在 7 轴）
    # ... 现有逻辑不变 ...
```

---

## 观测计划

### 实验 1: 静态热源 + 随机运动 (5 万步)

```
热源: 位置 [70, 50, 50], 不消耗
身体: 初始 [50, 50, 50], 随机扰动输入
```

**观测:**
- 绑定层 21 个节点的激活频率分布
- 纯前庭 15 个 vs 跨模态 6 个的 PNN 成熟度差异
- 影子层 C(7,2)=21 个跨轴权重的分布

**预期:** 跨模态绑定节点的激活频率 << 纯前庭 → PNN 成熟更慢 → 保持更高可塑性

### 实验 2: 可消耗热源 + 自由运动 (10 万步)

```
热源: 能量 50, 可消耗
身体: Motor 驱动自由运动
```

**观测:**
- 热源消耗前 vs 消耗后的绑定层权重变化
- 影子层跨模态权重是否"记住"了热源位置
- 运动轨迹是否趋向热源 (即使未编程趋热行为)

**预期:** STDP 学到 "oto_x 增加 → therm 增加" → motor 偏向热源方向

### 实验 3: 观察分化区域

**关键测量:**
```python
# 绑定层分区分析
intra_vest = [b for b in bindings if 'therm' not in b.id]  # 15 个
cross_modal = [b for b in bindings if 'therm' in b.id]      # 6 个

# 比较
for group_name, group in [('intra_vest', intra_vest), ('cross_modal', cross_modal)]:
    avg_weight = mean(b.mean_weight() for b in group)
    avg_pnn = mean(b.pnn_maturity for b in group)
    avg_activation = mean(b.mean_activation for b in group)
    activation_variance = var(b.activation_history for b in group)
```

---

## 实施顺序

| 步骤 | 内容 | 估计 |
|------|------|------|
| 1 | world.py (World + Body + HeatSource) | 小 |
| 2 | thermal_membrane.py (表皮 + 甲基化) | 小 |
| 3 | muscle.py (Motor→Force) | 极小 |
| 4 | hebbian.py 加第 7 轴 | 中 |
| 5 | variant_adapter.py 集成 | 中 |
| 6 | 实验 1: 静态热源观测 | 小 |
| 7 | 实验 2: 可消耗热源观测 | 中 |

**总计: ~250 行新代码 + ~80 行修改**

---

## Open Questions

> [!IMPORTANT]
> **热轴的编码层结构**: 热轴跳过前庭链 (MET→HC→Aff)，直接进入 Encoding。
> 信号延迟比前庭少 1 步。这个时间差是特征还是问题？
> (我认为是特征 — 区分"被动热变化"和"主动运动导致的热变化")

> [!IMPORTANT]
> **影子层扩展**: 跨轴从 C(6,2)=15 → C(7,2)=21。
> 新增 6 个 shadow cross-axis bundles。确认？

## Verification Plan

### Automated Tests
1. 端到端导入测试 (7 轴 + 21 绑定)
2. 1000 步烟雾测试 (无崩溃)
3. 实验 1 + 2 + 3 的测量脚本
