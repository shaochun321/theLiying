# 自我坐标机制：Binding Layer 激活与 L2 违规清除

> **问题**：热感 STDP 在 500k 步后权重回归初始值（0.50），无方向性分化。
> **根因**：信用分配失败 — 运动通路与热感通路平行无交汇，STDP 不知道"哪个运动导致了温度变化"。
> **根因 2**：`process_hunger` 作为 L2 硬编码直接注入趋热电流，绕过了学习通路，使 STDP 沦为旁观者。

## 核心原则声明

> [!IMPORTANT]
> 本方案严格遵守项目守则：
> - **L2 只注入物理后果，不注入行为规则**（TRACKER L193-196）
> - **禁止人工比较器**（B.03 废弃决策 2026-06-11）
> - **预测热觉变化 = Shadow 层 STDP 本职工作**（TRACKER B.03 约束）
> - **在物理接口上寻找解药**
> - **结构约束动力学** — 只添加物理结构（突触连接），不添加行为逻辑

---

## User Review Required

> [!WARNING]
> **Phase 0 是破坏性变更**：移除 `process_hunger` 后，系统在 Binding STDP 学会之前将没有任何趋热驱动力。
> 这意味着初期（0~50k 步）有机体不会主动趋热。这是有意为之 — 趋热性必须从 STDP 学习中涌现，而不是从代码中读取。
> 
> **如果您认为需要保留过渡期反射**，请告知，我可以设计一个衰减方案（反射增益随学习进展递减）。

> [!IMPORTANT]
> **Binding→Motor 拓扑选择**：21 个 binding cell 中只有 12 个是运动×热感交叉对（见下表）。
> 方案只为这 12 个交叉对创建 STDP 束，其余 9 个（vest×vest 和 therm×therm）保持休眠。
> 这是**拓扑约束**（前庭脊髓束的解剖学连接模式），不是行为规则。

## Open Questions

1. **衰减过渡**：移除 `process_hunger` 后是否需要一个过渡期（如 50k 步内线性衰减），还是直接切除？
2. **Binding→Motor 初始权重**：0.01 vs 0.001？太低则学习启动太慢，太高则未经学习就有驱动力。

---

## 证据摘要

### 500k 步实验数据（EXP-023）

```
热感束权重（全部回归初始值 0.50）：
  therm_back_to_move_x:  0.489 → 0.500  Δ=+0.011  ← 无分化
  therm_front_to_move_x: 0.496 → 0.500  Δ=+0.004  ← 无分化
  therm_left_to_move_y:  0.490 → 0.500  Δ=+0.010  ← 无分化
  therm_right_to_move_y: 0.499 → 0.500  Δ=+0.001  ← 无分化

前庭束权重（有分化）：
  col_yaw_to_move_x:   0.419 → 0.441  Δ=+0.022  ← 正向学习
  col_pitch_to_move_y:  0.413 → 0.438  Δ=+0.026  ← 正向学习
```

### 信用分配失败的物理分析

```
当前信号流（平行线，无交汇）：

  前庭 Column ──────→ Motor ──→ 运动 ──→ 位移
       ↑ efference copy ─┘                  ↓
                                        热感变化 (ΔT)
  热感 Column ──────→ Motor                 ↓
                                        DA 奖励 (进食)

问题：热感 Column 激活 ≠ "我的运动导致了热变化"
      热感 Column 只编码"当前热梯度"，不编码因果关系
      → STDP 对 therm→motor 做 LTP 时，不知道这是自主运动的结果还是巧合
      → 权重在 LTP 和 LTD 之间随机游走，最终回归均值
```

### 用户 2026-06-13 假设的核心映射

| 用户概念 | 架构映射 | 物理实现 |
|---------|---------|---------|
| 自身坐标结构 | Binding Layer 的跨模态 cell | `bind(yaw, therm_front)` — AND 门 |
| "小结构"存储改变 | Binding cell 的 `_activation_ema` | 电容式时间积分 |
| 虚位（反向补偿脉冲） | Efference copy error | `actual_acc - predicted_acc` |
| 生存机制捆绑 | DA 门控的 Binding→Motor STDP | 三因子学习规则 |
| 影子层该做的事 | Shadow 预测误差 → DA → 门控学习 | 已有 shadow→DA 通路 |

---

## Proposed Changes

### Phase 0: L2 违规清除 — 移除 `process_hunger`

> 移除行为规则，保留物理后果。

#### [MODIFY] [spinal_reflex.py](file:///D:/cell-cc/nexus_v1/components/spinal_reflex.py)

1. **保留** `process()` — 伤害回避反射（L2.03 合法：物理后果）
2. **保留** `SpinalReflexConfig` 中的 noci 参数
3. **废弃** `process_hunger()` 方法 — 改为返回零值 + 废弃警告
4. **废弃** `SpinalReflexConfig` 中的 hunger 参数（`hunger_approach_gain`, `hunger_gate_*`, `da_*_gain`）
5. **保留** `_hunger_gate` MOSFET 实例 — 未来可能用于其他门控

```python
def process_hunger(self, *args, **kwargs) -> Dict[str, float]:
    """DEPRECATED (2026-06-25): L2 violation — behavioral rule, not physical consequence.
    
    Thermotaxis must emerge from Binding Layer STDP, not hardcoded reflex.
    See: implementation_plan.md "自我坐标机制"
    """
    import warnings
    warnings.warn("process_hunger is deprecated (L2 violation)", DeprecationWarning, stacklevel=2)
    return {"move_x": 0.0, "move_y": 0.0, "move_z": 0.0}
```

#### [MODIFY] [variant_adapter.py](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py)

1. **注释掉** L780-796 的 `process_hunger` 调用块
2. 添加注释说明废弃原因

---

### Phase 1: Binding→Motor STDP 束激活

> 将休眠的 `_binding_motor_weights` 字典替换为正式的 `SynapticBundle` 对象，
> 具有 DA 门控的 eligibility trace STDP。

#### 交叉模态 Binding Cell 拓扑

21 个 Binding Cell 中，12 个是运动×热感交叉对（自我坐标的物理载体）：

| Binding Cell | 含义 | 目标 Motor |
|-------------|------|-----------|
| `bind_yaw_therm_front` | 偏航转向 + 前方变暖 | `move_x` |
| `bind_yaw_therm_back` | 偏航转向 + 后方变暖 | `move_x` |
| `bind_yaw_therm_left` | 偏航转向 + 左方变暖 | `move_y` |
| `bind_yaw_therm_right` | 偏航转向 + 右方变暖 | `move_y` |
| `bind_pitch_therm_front` | 俯仰 + 前方变暖 | `move_x` |
| `bind_pitch_therm_back` | 俯仰 + 后方变暖 | `move_x` |
| `bind_pitch_therm_left` | 俯仰 + 左方变暖 | `move_y` |
| `bind_pitch_therm_right` | 俯仰 + 右方变暖 | `move_y` |
| `bind_roll_therm_front` | 翻滚 + 前方变暖 | `move_z` |
| `bind_roll_therm_back` | 翻滚 + 后方变暖 | `move_z` |
| `bind_roll_therm_left` | 翻滚 + 左方变暖 | `move_z` |
| `bind_roll_therm_right` | 翻滚 + 右方变暖 | `move_z` |

**为什么只选 vest×therm 对**：
- vest×vest 对（如 `bind_yaw_pitch`）不携带热感信息，对趋热性无贡献
- therm×therm 对（如 `bind_therm_front_therm_back`）不携带运动信息，无法建立因果关联
- 只有 vest×therm 交叉对同时编码"运动方向"和"热变化方向"

#### [MODIFY] [binding.py](file:///D:/cell-cc/nexus_v1/components/binding.py)

1. 为 `BindingCell` 添加 `pre_trace` 和 `spike_times` 属性
   - 让 Binding cell 可以作为 `SynapticBundle` 的 source
   - `pre_trace` = 当 activation > threshold 时递增，否则衰减
   - `spike_times` = 记录激活超阈事件的时间戳
2. 添加 `Neuron`-compatible 接口：`_activation_ema`, `energy`, `config.neuron_id`
   - 这不是让 BindingCell 变成 Neuron，而是让它满足 SynapticBundle 的 duck-typing 接口

```python
# BindingCell 添加的接口（duck-typing for SynapticBundle source）
@property
def _activation_ema(self) -> float:
    return self._activation_ema_val

@property
def energy(self) -> float:
    return 1.0  # binding cells don't consume energy (no VR)

# 在 compute() 末尾更新 pre_trace
def compute(self, col_activations, dt=1.0):
    # ... existing AND gate logic ...
    # Update pre_trace for STDP compatibility
    if self.activation > self.config.co_activation_threshold:
        self._pre_trace = min(1.0, self._pre_trace + 1.0)
        self._spike_times.append(self._step_count)
    else:
        self._pre_trace *= 0.95  # decay
    self._step_count += 1
    return self.activation
```

#### [MODIFY] [variant_adapter.py](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py) — Binding→Motor 束创建

1. **替换** `_binding_motor_weights` 字典为 `bundles_binding_to_motor` 列表
2. **创建** 12 个 `SynapticBundle` 对象（vest×therm → motor）
3. 参数设定：

| 参数 | 值 | 物理依据 |
|------|-----|---------|
| `initial_weight` | 0.01 | 极低：必须通过 STDP 挣得 |
| `weight_max` | 0.3 | 低于直接热感束（0.5），subordinate |
| `synapse_gain` | 5.0 | 中等：不如直接通路（10.0），但足以产生可测量的电流 |
| `stdp_lr` | 0.05 | 关键期高可塑性 |
| `use_eligibility_trace` | True | DA 确认后才做 LTP |
| `eligibility_tau` | 500.0 | 桥接运动→热变化→进食的时间延迟（>300步） |
| `learning_rule` | "stdp" | 标准三因子学习 |

4. **删除** 步骤 6b 中旧的 `_binding_motor_weights` 字典注入代码（L984-1000）
5. **添加** `bundles_binding_to_motor` 到 `_propagate_bundles()` 和 `_do_learning()`
6. Binding→Motor 的 STDP 门控：`gate_col × da_lr_mod` （无 sync gate — binding 本身就是 sync）

#### 目标→Motor 映射规则

```
bind_*_therm_front → move_x  (前方热感 × 任意运动 → 前进)
bind_*_therm_back  → move_x  (后方热感 × 任意运动 → 前进，gain 为负)
bind_*_therm_left  → move_y  (左方热感 × 任意运动 → 左移)
bind_*_therm_right → move_y  (右方热感 × 任意运动 → 左移，gain 为负)
bind_*_therm_*     → move_z  (仅 roll 相关对)
```

**为什么 gain 有正负**：与现有热感差分束（[hebbian.py:532-537](file:///D:/cell-cc/nexus_v1/circuit/hebbian.py#L532-L537)）的拓扑对齐。
前方变暖 → 激励前进 (+)，后方变暖 → 抑制前进 (-)。
这是拓扑约束（类似视交叉的发育连线），不是行为规则。

---

### Phase 2: Efference Copy → Binding 调制

> 让 Binding Layer 区分"主动运动"和"被动运动"。
> 
> 这是用户假设的核心："真正应该在意项目是主动还是被动的，是以自身坐标结构为枢纽中心的特殊结构。"

#### [MODIFY] [variant_adapter.py](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py) — 步骤 6b 增强

现有 efference copy 计算（L616-634）已经产出 `_motor_efficacy[axis]` — 当 motor output 成功产生运动时，efficacy → 1.0；当 motor output 无效（碰壁）时，efficacy → 0.0。

**修改**：在 Binding 激活计算前，用 motor efficacy 调制前庭 column 的激活值：

```python
# 步骤 6b 修改：efference copy 调制 binding 输入
col_act_dict = {}
for ax in self.all_axes:
    raw_act = self.column_neurons[ax]._activation_ema
    if ax in self.vestibular.axes:
        # 前庭轴：用 efference copy efficacy 调制
        # 高 efficacy（主动运动）→ 保持原值
        # 低 efficacy（被动运动/碰壁）→ 衰减
        axis_key = {'yaw': 'x', 'pitch': 'y', 'roll': 'z'}[ax]
        eff = self._motor_efficacy.get(axis_key, 1.0)
        col_act_dict[ax] = raw_act * eff
    else:
        # 热感轴：不调制（热变化来自外部，不受 efference copy 影响）
        col_act_dict[ax] = raw_act

binding_activations = self.binding_layer.compute_all(col_act_dict)
```

**物理含义**：
- 当有机体**主动运动**时：motor efficacy ≈ 1.0 → 前庭 column 激活正常传入 Binding → Binding 交叉对正常激活 → STDP 学习
- 当有机体**被推动/碰壁**时：motor efficacy ≈ 0.0 → 前庭 column 激活被衰减 → Binding 交叉对不激活 → STDP 不学习

这实现了用户的"虚位"概念的最小形式：系统不学习被动运动带来的热感变化，只学习主动运动的后果。

---

### Phase 3: 保留现有热感差分束

> 不删除 [hebbian.py:532-573](file:///D:/cell-cc/nexus_v1/circuit/hebbian.py#L532-L573) 的热感→Motor 差分束。
> 它们和 Binding→Motor 束共存，物理上是加法叠加（Kirchhoff 定律）。

```
I_motor_total = I_vestibular(col→motor)      ← 已有，前庭驱动
              + I_thermal(therm_col→motor)    ← 已有，热梯度直接驱动
              + I_binding(bind→motor)         ← 新增，跨模态关联驱动
              + I_vital(oscillator)           ← 已有，基线游动
```

**为什么保留**：
1. 热感差分束提供**反应性**驱动（当前热梯度 → 立即响应）
2. Binding 束提供**关联性**驱动（历史运动×热变化 → 学习后的策略）
3. 两者不矛盾 — 反应性是快通道，关联性是慢通道
4. 如果 Binding STDP 成功学习，binding 束权重 >> 热感差分束权重 → 关联性自然主导

---

## Verification Plan

### 自动化测试

```bash
# 1. 回归测试：确保移除 process_hunger 不破坏现有功能
python -m pytest nexus_v1/tests/ -v

# 2. 500k 步长程验证（无 process_hunger）
python -m nexus_v1.exp_023_500k_validation

# 3. Binding 束权重分化检查
#    期望：bind_yaw_therm_front → move_x 权重 > 0.05（从 0.01 起步）
#    期望：bind_yaw_therm_back → move_x 权重 < bind_yaw_therm_front
```

### 成功标准

| 指标 | 期望 | 当前基线 |
|------|------|---------|
| Binding→Motor 权重分化 | max Δw > 0.02 | 0（不存在） |
| 热感差分束权重分化 | 至少一对 front/back 差值 > 0.05 | 0（全部 0.50） |
| 距离轨迹 | 50k→500k 平均距离递减 | 随机（无趋势） |
| fill_fraction | > 0.30 @500k | 0.68（但由 process_hunger 贡献） |
| DA_mean | ∈ [0.05, 0.80] | 0.0487（刚好在边界外） |

### 手动验证

- 检查 EXP-023 日志中 Binding 束的 SNAP 权重快照
- 确认 `process_hunger` 返回值全为 0.0（废弃确认）
- 确认 Binding cell 的 `_activation_ema` 在运动+热变化同时发生时 > 0

---

## 时间线

| 阶段 | 内容 | 预估 |
|------|------|------|
| Phase 0 | 移除 process_hunger | 15 min |
| Phase 1a | BindingCell 添加 STDP 接口 | 20 min |
| Phase 1b | 创建 12 个 Binding→Motor SynapticBundle | 30 min |
| Phase 1c | 集成到 _propagate_bundles + _do_learning | 20 min |
| Phase 2 | Efference copy → Binding 调制 | 15 min |
| 验证 | 回归测试 + 500k 长程验证 | 60 min（运行时间） |

---

## 附录：与已有方案的关系

| 已有方案 | 本方案处理 |
|---------|-----------|
| B.03 废弃（禁止人工比较器） | **遵守** — 没有比较器，只有 AND 门 + STDP |
| 双源驱动统一方案 | **部分采纳** — 拓扑修补（Phase 3）已执行；反射增强（Phase 1）被废弃 |
| 六刀稳态方案 | **全部保留** — 参数不动 |
| D.12 Binding 扩展验证 | **正式启动** — 从显式延后变为主线任务 |
| 自身坐标假设（2026-06-13） | **核心采纳** — Binding Layer = 自我坐标，efference copy = 虚位过滤 |
