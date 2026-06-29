

> 本方案基于完整的架构审计报告（2026-06-27 Part1/Part2）及用户的反向意见制定。  
> 核心目标：以最少的架构侵入，从物理层面打破STDP对称死锁，建立YAW学习通路。  
> 原理：采用v·∇T作为DA的方向性门控，属于L2:SELECTION层。方案A是影子层就位前的L2脚手架，后期可自然过渡到影子层接管。


## 一、核心诊断

| 问题 | 诊断 | 后果 |
|------|------|------|
| DA 方向盲 | DA=Δfill/dt 不编码方向 | front/back 同时获奖励，对称死锁 |
| YAW 无学习 | apply_yaw_torque() 只有一个调用点，不经过 Bundle | body 无法学会主动朝向热源 |
| Motor 边缘化 | k_conv 贡献是 Motor 的 12 倍 | 学习结果对行为无影响 |

**对称死锁的本质**：在 Phase 3 实验中，body 在 S1 附近以 yaw≈-3° 振荡，front/back 皮肤交替接近热源，两者都触发 DA。STDP 无从区分方向，双束同步饱和。这是信号架构的内在属性，不是参数问题——即使 eligibility_gain 降至任意小值，只要振荡持续足够长时间，两束权重比依然收敛到 1.0。


## 二、三项架构改动

### 改动 1：DA 方向化（L2:SELECTION 门控）

**位置**：`circuit/variant_adapter.py`，DA 计算段

**数理形式**：

```
approach_rate = v[0]*grad_T[0] + v[1]*grad_T[1]          // v·∇T
approach_factor = max(0, tanh(approach_rate / 0.05))     // V_REF = 0.05
DA = DA_raw × approach_factor
```

**V_REF 来源**：`k_conv × |∇T|` 量级估算（0.5 × 0.1 = 0.05 units/step）

**物理合法性论证**：

| 操作 | 物理量 | 合法性 |
|------|--------|--------|
| k_conv ∇T | ∇T → 速度 | 环境→身体的直接力作用（已有）|
| v·∇T 门控 DA | v·∇T → 学习率 | 内稳态→学习的调制作用（本方案）|

两者使用相同的物理量（v 和 ∇T），作用对象不同，都遵循“物理量→物理效果”的物理映射原则。这属于 L2:SELECTION 层——进化固化的先天学习门控，与 YAW_GAIN 反射在物理合法性上完全同构。

**与影子层的关系**：方案 A 是 L2 脚手架，在影子层就位前为 STDP 提供方向性学习信号。一旦影子层修复，Xin 可接管 DA 调制，方案 A 的门控自然过渡。

**实施方式**（在实验脚本中覆写，不修改母代码）：

```python
def _da_with_direction(self, fill_fraction, dt):
    delta_fill = fill_fraction - self._prev_fill
    self._prev_fill = fill_fraction
    rpe_raw = max(0.0, 7.5 * delta_fill / dt)
    
    v = circuit.world.body.velocity
    grad = circuit.world.gradient_at(circuit.world.body.position)
    approach_rate = v[0]*grad[0] + v[1]*grad[1]
    direction_factor = max(0.0, min(1.0, approach_rate / 0.05))
    
    return rpe_raw * direction_factor

circuit.da_gate.step = _da_with_direction.__get__(circuit.da_gate)
```

### 改动 2：YAW 可学习通路

**位置**：
- `nexus_v1/circuit/hebbian.py`（新增 Bundle 定义）
- `nexus_v1/circuit/variant_adapter.py`（新增 `rotate_yaw` motor 轴）

**核心思想**：当前 YAW 控制完全在 Bundle 架构外，`apply_yaw_torque()` 只有一个调用点。新增 `therm_left/right_col → rotate_yaw` Bundle，使 YAW 转向可被 STDP 学习。

**实施内容**：

1. 在 `hebbian.py` 中新增 `therm_left/right → yaw_motor` 束：
   - `initial_weight = 0.01`
   - `weight_max = 0.3`
   - `eligibility_gain = 1e-5`
   - `synapse_gain = 0.1`

2. 在 `variant_adapter.py` 中新增 `rotate_yaw` 轴，在 step() 中读取其激活值并调用 `apply_yaw_torque()`。

3. 不修改 `apply_yaw_torque()` 的硬连线反射 `YAW_GAIN=0.1`，两通路并行。

**三问确认**：
- Q1: BIO 对应物是脊髓-前庭脊髓束（Bautista et al. 2007）
- Q2: 使用 `rotate_yaw` motor 轴 + Bundle
- Q3: 参数见上

**与改动 1 的关系**：改动 1 解决方向性学习的根本问题，改动 2 是补充，在改动 1 验证有效后实施。

### 改动 3：Motor 增益提升

**位置**：`nexus_v1/components/muscle.py` 或实验脚本中 `circuit.muscle_system.gain = 0.5`

**原理**：k_conv=0.5 是 Motor 的 12 倍，学习结果对行为影响微弱。提升 Muscle gain 使 Motor 贡献与 Langevin 量级相当。

**实施**：`Muscle.gain = 0.1 → 0.5`


## 三、执行顺序与参数

| 顺序 | 改动 | 预估代码量 | 依赖 |
|------|------|-----------|------|
| 1 | 改动 1：DA 方向化 | ~30 行 | 无 |
| 2 | 运行短程诊断（10k 步）确认方向门控 | — | 1 |
| 3 | 改动 3：Motor 增益提升 | ~5 行 | 无 |
| 4 | 改动 2：YAW 可学习通路 | ~100 行 | 1（可选，验证后执行）|

| 参数 | 值 | 说明 |
|------|-----|------|
| eta | 0.50 | Phase 3 已验证 |
| k_conv | 0.50 | Phase 2 临界值 |
| eligibility_gain | 1e-5 | 默认值 |
| YAW_GAIN 反射 | 0.10 | 保留 |
| 起始位置 | [65, 50, 25] | 偏向 S1，创造单向接近条件 |
| V_REF | 0.05 | 由 k_conv×|∇T| 估算 |


## 四、验收标准

| 指标 | 目标 | 说明 |
|------|------|------|
| w_front/w_brake > 1.5 | @200k 步 | DA 方向门控打破对称 |
| w_front/w_brake > 2.0 | @500k 步 | 方向性学习成熟 |
| fill > 0.1 | 全程 500k | 能量自持 |
| approach_count ≥ 3 | 全程 | 多次接近周期 |


## 五、实施前确认清单

1. **`world.gradient_at()` 是否已实现？** 若否，需先实现（高斯温度场的解析梯度）。

2. **`v·∇T` 的 L2:SELECTION 定位**：确认接受方案 A 作为 L2 脚手架。

3. **YAW Bundle 的调用接口**：确认 `apply_yaw_torque()` 是否接受来自 Motor 神经元的输入。


## 六、与用户反向意见的对应关系

| 用户反向意见 | 本方案的回应 |
|-------------|-------------|
| v·∇T 是语义硬编码 | 重新定位为 L2:SELECTION（进化固化的先天学习门控），与 YAW_GAIN 同构 |
| 影子层太早，不应现在修复 | 方案 A 是 L2 脚手架，不是影子层修复，后期可自然过渡 |
| 需要下丘脑/脑干/脊髓结构 | 方案 A（下丘脑式 DA 调制）+ 改动 2（脑干/脊髓 YAW 通路）构成同构结构 |


## 七、建议优先执行

**建议先实施改动 1（DA 方向化），运行短程诊断确认方向门控生效。** 改动 2 和改动 3 可以在确认方向门控有效后再执行。如果需要，改动 2 可以延迟到方案 A 验证通过后。改动 3 可以在同一轮实施中完成（工程量极小）。