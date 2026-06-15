# 实施计划：第二主体（热）构建

> 前身路径：先链路对应 → 再阻抗匹配 → 最后涌现

---

## Phase 0: Shadow 动态生长（前提条件）

> 不解决此问题，后续所有新轴加入后 shadow 无法适配

### [MODIFY] [shadow_sandbox.py](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py)

**问题**：`initialize()` 在首次调用时固定拓扑。新 patch 轴加入 `all_axes` 后，shadow 不会自动扩展。

**改动**：
1. 添加 `_expand_for_new_axes(circuit)` 方法 — 在 `observe()` 中检测 `circuit.all_axes` 是否比 `self._axes` 多了新轴
2. 对每个新轴：创建 `s_enc_reg_{axis}`, `s_enc_irr_{axis}`, `s_col_{axis}` 三个神经元
3. 创建对应 bundle：`s_enc_to_col_{axis}`, `s_col_to_mot_{axis}`, 以及与已有轴的 `s_cross_*` bundles
4. 更新 `_xin_routing` 映射
5. **不修改已有神经元/bundle** — 只做增量添加

**不做**：
- 不做 shadow 层自己的 sprout/prune — 主系统的 sprout/prune 逻辑足够复杂，shadow 保持"plastic weights, growing topology"
- 不做修剪虚位机制 — 当前不需要

**验证**：单元测试 — shadow 初始化后动态添加新轴，确认新神经元和 bundle 被正确创建

---

## Phase 1: 物理壳体 + 皮肤 Patch (B.00 + B.01)

### [MODIFY] [world.py](file:///d:/cell-cc/nexus_v1/components/world.py)

**Body 扩展**：
1. 添加 `skin_patches: List[SkinPatch]` — 4 个 patch（front/back/left/right）
2. 每个 `SkinPatch` 有固定的 `local_direction: List[float]` （体框架坐标，相对 body heading）
3. `SkinPatch.sample_temperature(world, body)` — 在 patch 方向偏移位置采样温度
4. Body heading 由 velocity 方向推导（不添加新状态变量）

```python
@dataclass
class SkinPatch:
    """一片体表皮肤 — 在 body 上的固定位置。"""
    patch_id: str                    # "front", "back", "left", "right"
    local_offset: List[float]        # 体框架坐标 [dx, dy, dz]（相对 body center）
    patch_radius: float = 2.0        # 采样半径
    
    def world_position(self, body: Body) -> List[float]:
        """Patch 在世界坐标中的位置 = body.position + heading_rotated(offset)"""
        ...
    
    def sample_temperature(self, world: World, body: Body) -> float:
        """在 patch 的世界位置采样温度"""
        return world.temperature_at(self.world_position(body))
```

**最小 4 patch 布局**：
```
front: offset = [+r, 0, 0]    (velocity 方向)
back:  offset = [-r, 0, 0]
left:  offset = [0, +r, 0]
right: offset = [0, -r, 0]
```
其中 r = body 有效半径（从 total_volume 推导）

**验证门（Phase 1 Gate）**：
- 测试：body 静止在热源旁 → front patch 温度 > back patch 温度
- 测试：body 转向 → patch 温度分布跟随变化

---

## Phase 2: 感受链 + SomatoRelay (B.02 + B.02b)

### [NEW] [somatosensory/chain.py](file:///d:/cell-cc/nexus_v1/somatosensory/chain.py)

**结构**（类比 `vestibular/chain.py`）：

```
SkinPatch → Thermoreceptor (Reg, C=5.0, τ=100ms)
          → Nociceptor (Irr, C=0.5, τ=4ms)
                ↓
          SomatoRelay (lateral inhibition, gain=0.05 起步)
                ↓
          输出 → Encoding 层（通过 all_axes 注册）
```

每个 patch 2 个感受神经元 + 1 个中继神经元 = 12 个神经元 + 12 个 bundle。

#### Thermoreceptor 配置
```python
def _thermoreceptor_config(patch_id: str) -> NeuronConfig:
    """压电式热-电转换器。类 MET 但 τ 200× 长。"""
    return NeuronConfig(
        neuron_id=f"thermo_{patch_id}",
        capacitance=5.0,       # 200× MET → 温度变化慢
        r_leak=20.0,           # τ = C×R = 100ms
        channels=[ChannelConfig(
            name="trp", v_threshold=0.01, gm=1.0,
            tau_gate=0.05, reversal=0.5, sign=1.0,
        )],
    )
```

#### Nociceptor 配置
```python
def _nociceptor_config(patch_id: str) -> NeuronConfig:
    """伤害感受器。快通道，高阈值。"""
    return NeuronConfig(
        neuron_id=f"noci_{patch_id}",
        capacitance=0.5,       # 快反应
        r_leak=8.0,            # τ = 4ms
        spiking=True,
        v_peak=0.5,            # 物理阈值 — 由组织损伤线决定
        v_reset=0.1,
        b_adapt=0.05,          # AC 通道 = 强适应
    )
```

#### SomatoRelay 配置
- 每个 patch 一个中继神经元
- 中继间 lateral inhibition：相邻 patch 互抑（gain=0.05，可反馈调节）
- 连接拓扑 = 体表邻接图（front↔left, front↔right, back↔left, back↔right）
- **不连接** front↔back（对径，不相邻）

#### TemporalCoupler 参数
```
感受→Relay: τ_couple = C(50.0) × R(2.0) = 100ms
Relay→Encoding: τ_couple = C(10.0) × R(2.0) = 20ms
```

### [MODIFY] [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py)

- 在 `__init__` 中注册新轴：`extra_axes` 扩展为包含每个 patch 的 `therm_front`, `therm_back`, `therm_left`, `therm_right`
- 替换现有单一 `therm` 轴
- Encoding 层自动为每个新轴创建 reg/irr 对

### [MODIFY] [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)

- `step()` 中：每步调用 `somatosensory.step(world, body, dt)`
- 从 SomatoRelay 输出读取 per-patch relay 活动
- 将 relay 输出作为 `mechanical_inputs[f'therm_{patch_id}']` 传入

**验证门（Phase 2 Gate）**：
- 链路对应：patch 温度变化 → thermoreceptor 激活 → relay 激活 → encoding 激活
- 阻抗匹配：各层输出幅度在下一层工作区间内（不饱和、不失聪）
- SomatoRelay 梯度放大：单侧加热时，梯度侧 relay 输出 >> 对侧

---

## Phase 3: 自身原点 + DA 闭环 (B.03 + B.04 + B.06)

> Phase 3 只在 Phase 2 验证通过后执行

### [NEW] [self_origin.py](file:///d:/cell-cc/nexus_v1/components/self_origin.py)

B.03 自身原点模块（小脑类比）— 三路比较器：

```python
class SelfOriginModule:
    """三层交汇结构：交感层 × Motor × Shadow。
    
    输入：
      skin_signal: 各 patch relay 活动 (afferent)
      motor_signal: Motor 膜电压 EMA (efference copy, 已有)
      shadow_error: Shadow prediction error (已有)
    
    输出：
      mismatch: 感受变化与预期的偏差
      → 大 mismatch = 外部刺激（需要学习）
      → 小 mismatch = 自我运动后果（预期中）
    """
```

最小实现：一组比较神经元（4 个，每 patch 一个），每个接收 3 路输入：
- Patch relay 活动 (excitatory)
- Motor EMA (inhibitory — 如果我自己在动，期望感受变化)
- Shadow error (modulatory)

输出 mismatch 信号 → 注入 DA 系统作为额外输入。

### B.04: 感受→DA 闭环

已有的 DA 系统架构不需要修改。关键连接：
1. 新 patch 轴加入 → shadow 自动扩展（Phase 0）→ shadow col 活动变化 → shadow→DA bundle 传导 → DA 浓度变化
2. 热接触 → EnergyStore.deposit() 增加（已有）→ shadow 预测误差减小 → DA 稳定
3. 远离热源 → energy 减少 → deviation 增大 → DA 升高 → STDP 强化相关运动方向

### B.06: 热势 ν_th

在 MotionState 中添加 `thermal_gradient` 和 `thermal_potential`：
- `thermal_gradient = [T_front - T_back, T_left - T_right]`
- `thermal_potential = d(energy_absorbed)/dt`
- 这些是物理测量值，不是语义标签

**验证门（Phase 3 Gate）**：
- DA 闭环：agent 靠近热源 → DA 上升；远离 → DA 下降
- 方向信号：ν × ΔT 的相关性在 STDP 窗口内可测
- 100k 步热趋性测试：距离轨迹应该显示偏向热源的趋势（vs EXP-009 纯随机）

---

## 执行顺序与时间估计

```
Phase 0: Shadow 动态生长          ~1h  (改 1 个文件 + 测试)
  ↓ 验证: 新轴加入后 shadow 正确扩展
Phase 1: Body patch               ~1h  (改 1 个文件 + 测试)  
  ↓ 验证: patch 温度采样正确
Phase 2: 感受链 + SomatoRelay     ~3h  (新建 1 文件, 改 2 文件 + 测试)
  ↓ 验证: 链路对应 + 阻抗匹配
Phase 3: 自身原点 + DA 闭环       ~2h  (新建 1 文件, 改 2 文件 + 100k 验证)
  ↓ 验证: 热趋性 vs EXP-009 对照
```

总改动：**新建 2 文件 (somatosensory/chain.py, self_origin.py)**，**修改 4 文件 (world.py, shadow_sandbox.py, hebbian.py, variant_adapter.py)**

---

## 不做的事

- ❌ 不做修剪虚位重整化塔（用户确认当前不需要）
- ❌ 不做 Shadow sprout/prune（保持 plastic weights + growing topology）
- ❌ 不做 Binding 扩展（平行测试方向，不在关键路径）
- ❌ 不做 P_ν × P_th 守恒验证（需要第二主体建成后的实验数据）
- ❌ 不改 thermal_membrane.py（保留单点标量传感器作为 legacy，新系统独立）

---

## 风险

| 风险 | 缓解 |
|---|---|
| 4 patch 轴 × 2 模态 = 8 个新 Encoding 轴，Binding C(15,2)=105 cells | metabolic_tax 自然修剪；先用 4 patch 验证 |
| SomatoRelay lateral inhibition 导致 patch 间振荡 | gain=0.05 起步，观测后调节 |
| Shadow 扩展后维数过多，权重不收敛 | shadow_K=10 已有慢尺度；ECM PNN 会冻结 |
| 新 bundle 数量增多拖慢运行速度 | 先 4 patch（+12 neurons, +12 bundles），可控 |
