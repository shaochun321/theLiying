# Phase 3b: 基质约束的 Mitosis — 修订方案

## 关键纠正

### 你的批评：坐标为信息被约束至结构来客观实现

项目没有显式时空坐标（公理 Ω-1）。我的方案中"空间坐标 + 领地划分"违反了这个公理——
它从外部注入了一个坐标系统，而不是让空间从结构中涌现。

```
错误思路（P3 领地版）:
  给每个 neuron 分配坐标 (x, y, z)
  领地 = 空间距离 < R
  → 注入了外部坐标 → 违反 Ω-1

正确思路:
  "空间" = 拓扑邻近性 = 连接距离
  neuron A 和 B 的"距离" = 它们之间需要经过多少个 bundle
  "领地" = 共享同一组 bundle 的 neuron 集合
  → 坐标从结构涌现 → 符合 Ω-1
```

### T/O/P/R/Xin 架构的数学基础（已找回）

来自 [revised_math_framework_v2.md](file:///L:/Users/%E7%BB%8D%E6%98%A5/.gemini/antigravity-ide/brain/b28b1552-1fcc-4344-b53a-904fd4f4bced/revised_math_framework_v2.md) 和 [modeling_hierarchical_prxin.md](file:///L:/Users/%E7%BB%8D%E6%98%A5/.gemini/antigravity-ide/brain/b28b1552-1fcc-4344-b53a-904fd4f4bced/modeling_hierarchical_prxin.md)：

- **公理 Ω-1**: 项目不访问客观层变量（position, mass 等）
- **公理 Ω-3**: 空间、时间、因果知识只能从输入流的关联结构中生成
- **公理 Ψ-1**: T/O/P/R/Xin 是组织语法，不是运行规则
- **§2.2**: ds² = Σ g_ij · δa_i · δa_j，其中 g_ij = w_cross(i,j)
- **递归**: 每层有自己的 P/R/Xin 循环；P/R 切换模式 = 上一层的环流

---

## Phase 3 失败的根因（重新分析）

从 T/O/P/R/Xin 视角：

| T/O/P/R/Xin 阶段 | 当前 Mitosis 的问题 |
|---|---|
| **T (传递)** | 子代获得了传递通道（bundle 重连），但不确定通道是否有效 |
| **O (观测)** | 子代没有观测历史——它的 δa = a（无基线），ds² 无法定义 |
| **P (预测)** | 子代没有内部模型——不知道"应该看到什么" |
| **R (修订)** | 子代的权重 = 1e-4——几乎无学习基础 → STDP 无法启动 |
| **Xin (残差)** | 子代的 Xin 没有意义——没有预测就没有残差 |

**根因**：子代出生时处于 T/O/P/R/Xin 循环的"冷启动"状态。
它没有 O 历史、没有 P 模型、没有有意义的 Xin。
它在信息空间中"不存在"——因为它没有任何关联结构。

> **你的表述完美**："存在是时间/空间/物质的组合"
> 子代缺少时间（无历史）、空间（无拓扑位置）、物质（无能量预算）。

---

## 修订方案

### 核心原则：不引入新坐标，利用已有结构

| 维度 | 信息载体 | 已有组件 |
|------|---------|---------|
| **时间** | 疲劳电容历史 + 基线 EMA | `FatigueCapacitor`, `_activation_ema` |
| **空间** | 拓扑邻近性（共享 bundle 数） | `SynapticBundle.sources/targets` |
| **物质** | PowerRail IR-drop（共享供电） | `PowerRail` in `neuron.py` |

### 修改 1：PowerRail 容量约束（物质维度）

**已有的物理**：PowerRail 有 `V_actual = Vdd - I_total * R_internal`。
当同一 PowerRail 上的 neuron 增加时，I_total 增加 → V_actual 下降。

**当前问题**：每个 neuron 有独立的 PowerRail 实例。

**修改**：Motor 层共享一个 PowerRail。分裂增加负载 → 电压下降 → 自限。

```python
# 在 HebbianCircuit.__init__:
self._motor_power_rail = PowerRail(vdd=1.2, r_internal=0.1)

# 所有 motor neuron 共用:
for key, config in motor_configs:
    config.power_rail = self._motor_power_rail
```

当 motor neuron 从 3 → 6 时：
- I_total ≈ 翻倍
- V_actual = 1.2 - 6×I_per × 0.1 → 电压下降
- 弱 neuron（低输入）的 V < V_th → 自然静默 → 能量耗尽 → 凋亡
- **无需外部控制器，PowerRail 物理自动完成**

#### [MODIFY] [neuron.py](file:///d:/cell-cc/nexus_v1/components/neuron.py)
- `split()` 中：子代继承父代的 PowerRail 引用（共享供电）

#### [MODIFY] [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py)
- Motor 层使用共享 PowerRail

---

### 修改 2：Apoptosis — 物质驱动的自然死亡

不用软件计数器，用已有的 `energy` 字段：

```python
def should_die(self) -> bool:
    """Energy below survival threshold for sustained period.
    
    S0: reads energy (PowerRail voltage × duty cycle).
    BIO: ATP depletion → caspase cascade → programmed cell death.
    """
    if self.energy < 0.05:
        self._apoptosis_counter += 1
    else:
        self._apoptosis_counter = max(0, self._apoptosis_counter - 1)
    return self._apoptosis_counter >= self.config.apoptosis_confirm_steps
```

- energy < 0.05 是 PowerRail IR-drop 的物理后果
- 不需要活动监测（firing_rate 是软件统计）
- 子代如果没获得足够输入 → 没活动 → 没能量恢复 → energy → 0 → 死亡
- **自然选择，不是人为判决**

#### [MODIFY] [neuron.py](file:///d:/cell-cc/nexus_v1/components/neuron.py)
- `NeuronConfig`: 添加 `enable_apoptosis`, `apoptosis_confirm_steps=30000`
- `Neuron`: 添加 `_apoptosis_counter`, `should_die()`

#### [MODIFY] [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py)
- `_check_mitosis()` 同时检查 `should_die()`
- 死亡时：从 motor_neurons 移除，清理相关 bundle

---

### 修改 3：Mitosis 阈值回调 — 防止级联分裂

分裂后父代的疲劳电容被清零（已实现），但子代继承了相同的 config →
子代可能立刻开始累积疲劳 → 再次分裂。

**修改**：子代出生后有 grace period（与 sprout 相同逻辑）：

```python
def split(self, child_id):
    child = ...
    child._mitosis_counter = -self.config.mitosis_confirm_steps  # 负值 = 冷却期
    # 子代需要先回到 0，再累积到 confirm_steps 才能分裂
    # 总冷却 = 2 × confirm_steps = 60s
```

---

### 修改 4：拓扑邻近性重连（空间维度）

不用随机 50/50，而是根据**信号相关性**分配入边：

```python
def _rewire_after_split(self, parent, child):
    """Rewire based on signal correlation, not random.
    
    Each incoming bundle's recent activation history is compared
    with the parent's activation history. Bundles that correlate
    MORE with the parent stay; those that correlate LESS go to child.
    
    This creates functional differentiation:
    - Parent keeps its "best-matching" inputs
    - Child gets the "mismatch" inputs → different functional role
    
    BIO: dendritic refinement by activity-dependent pruning.
    S0: uses pre_trace / post_trace (existing component traces).
    """
    for bundle in incoming_bundles:
        # Use bundle's mean_weight as proxy for correlation strength
        # (weight = accumulated STDP correlation)
        # Higher weight = more correlated with parent → stays
        # Lower weight = less correlated → goes to child
        if bundle.mean_weight() < median_weight:
            bundle.replace_target(parent, child)
```

---

## Open Questions

> [!IMPORTANT]
> **PowerRail 共享的粒度**：是所有 motor neuron 共享一个 PowerRail，
> 还是按 axis 分组（move_x 族一个，move_y 族一个，move_z 族一个）？
> 按 axis 分组可能更合理：同族 neuron 竞争，跨族不竞争。

> [!IMPORTANT]
> **子代的初始连接强度**：当前出边 w=1e-4。
> 是否太弱？如果 ECM PNN maturity 已经较高（g_ℓ ≈ 0.2），
> 那么 STDP lr 已经被门控到很低 → w=1e-4 永远长不起来。
> 可能需要：子代的 maturation_stage 重置为 0（最大可塑性）。

---

## Verification Plan

### Automated Tests
1. `test_governance.py`：确认不破坏 fuse
2. 500k 步运行：
   - 观察分裂是否发生
   - 观察僵尸 neuron 是否被凋亡清除
   - 观察是否仍有级联分裂
   - motor 总数是否稳定在合理范围（3-8）

### 预期行为
- ~200s：首次分裂（V_fat > 0.4 持续 30s）
- ~260s：僵尸子代凋亡（energy < 0.05 持续 30s）
- 最终：4-6 个活跃 motor neuron，无僵尸
- Motor rate：每个 neuron 2-4 Hz（分流后下降）
