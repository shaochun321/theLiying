# 母本分化 × 自由能 × 全局污染 — 深度审计

## 一、影子层自由能是否发散？

### 结论：**不会发散，但会饱和在无用值**

#### 机制审查

[_update_free_energy](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py#L690-L702):

```python
K = sum(xi ** 2 for xi in xin_values)        # 瞬时预测误差平方和
self._k_ema = self._k_ema * 0.99 + K * 0.01  # EMA α=0.01
```

**上界分析：**
- `xin_values` 来自主回路 `b.config.xin_tension`
- `xin_tension` 本身有指数泄漏：`leak_factor = exp(-dt/1000)` → τ=1000s
  - 见 [bundle.py:L434-437](file:///d:/cell-cc/nexus_v1/circuit/bundle.py#L434-L437)
- 因此 `|xin|` 有界 → `K` 有界 → `K_ema` 有界

**不会发散，但存在另一个问题：**

当 Thermo 积分器饱和（act: 0→10）时，xin_tension 所有 soma bundle = **0.000**（EXP-016c 确认）。这意味着：

```
K = Σ(0²) = 0   →   K_ema → 0   →   ν = dK_ema/dt = 0
```

> [!WARNING]
> 自由能没有发散，而是**坍缩为零**。Shadow 层看到的世界是完全静止的——虽然数学上稳定，但信息论上已死。

---

## 二、母本分化是否仍不足？

### 结论：**工厂模式正确，但 `copy()` 有两处确认的交叉污染 bug**

#### ✅ 正确的部分：工厂函数隔离

每个 NeuronConfig 工厂函数（`_encoding_config`, `_column_config`, `_motor_config`, `create_shadow_config`）都是**每次调用创建全新实例**：

```python
def _encoding_config(name: str) -> NeuronConfig:
    return NeuronConfig(        # ← 每次 return 新对象
        neuron_id=f"enc_{name}",
        capacitance=0.15,
        ...
    )
```

- [hebbian.py L273-276](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py#L273-L276): 每个 neuron 拿到独立的 config ✅
- [chain.py L184-187](file:///d:/cell-cc/nexus_v1/somatosensory/chain.py#L184-L187): 每个 patch 独立 config ✅
- [shadow_sandbox.py L83-124](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py#L83-L124): `create_shadow_config()` 独立 ✅

#### ✅ 正确的部分：新区域扩展

[_expand_for_new_axes](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py#L345-L498) 是**纯增量**的：

```python
# INCREMENTAL: never modifies existing neurons/bundles.
# 注释是真的——代码确认：
for axis in new_axes:
    self.neurons[nid] = Neuron(create_shadow_config(...))  # 新实例
    self.bundles[bid] = SynapticBundle(cfg, ...)            # 新实例
self._axes.extend(new_axes)  # 只 append，不 clear
```

这段代码不会触碰已有的 neurons/bundles。 ✅

#### 🔴 BUG: `Neuron.split()` 使用浅拷贝

[neuron.py L672-674](file:///d:/cell-cc/nexus_v1/components/neuron.py#L672-L674):

```python
from copy import copy
child_config = copy(self.config)  # ← SHALLOW COPY
```

**实测验证：**

```
=== Shallow copy(NeuronConfig) ===
c1.channels is c2.channels: True           ← 共享同一个 list 对象！
c1.channels[0] is c2.channels[0]: True     ← 共享同一个 ChannelConfig！

After c2.channels[0].v_threshold = 999:
  c1.channels[0].v_threshold = 999.0       ← 母本被污染！
  CONTAMINATION: True
```

**影响范围：**

| 字段 | 类型 | `copy()` 后共享？ | 运行时是否被修改？ | 风险 |
|------|------|---|---|---|
| `channels` | `List[ChannelConfig]` | ✅ 共享 | 目前无直接修改代码 | 🟡 潜在 |
| `theta_m` | `float` | ❌ 独立 | BCM 每步修改 | ✅ 安全 |
| `potential_phi` | `float` | ❌ 独立（split 时显式 reset） | 每步累加 | ✅ 安全 |
| `energy` | `float` | ❌ 独立（split 时显式设置） | 每步增减 | ✅ 安全 |

**channels 虽然目前没有被运行时修改，但这是一颗定时炸弹**——任何未来添加的动态通道调节（如"慢Na+失活"）都会通过共享引用污染母本。

#### 🔴 BUG: `SynapticBundle.sprout()` 使用浅拷贝

[bundle.py L646-651](file:///d:/cell-cc/nexus_v1/circuit/bundle.py#L646-L651):

```python
from copy import copy
child_config = copy(self.config)  # ← SHALLOW COPY
```

**实测验证：**

```
=== Shallow copy(BundleConfig) ===
b1.silent_snapshot is b2.silent_snapshot: True   ← 共享同一个 dict！
After b2.silent_snapshot['test'] = True:
  b1.silent_snapshot = {'w': 0.5, 'test': True}  ← 母本被污染！
  CONTAMINATION: True
```

**影响范围：**

| 字段 | 类型 | `copy()` 后共享？ | 运行时修改？ | 风险 |
|------|------|---|---|---|
| `silent_snapshot` | `dict` | ✅ 共享 | `_manage_silent_synapses` 每步写入 | 🔴 **活跃 bug** |
| `xin_tension` | `float` | ❌ 独立（sprout 显式 reset） | 每步累加 | ✅ 安全 |
| `fruit_state` | `str` | ❌ 独立 | 每步更新 | ✅ 安全 |
| `_sw_*` 驻波字段 | `int/float` | ❌ 独立 | 每步更新 | ✅ 安全 |

`silent_snapshot` 是**活跃 bug**——当 sprout 的 cross_axis bundle 进入 silent 状态时，`shadow_sandbox._manage_silent_synapses()` 会写入 `bundle.config.silent_snapshot`，这会**同时修改母本 bundle 的快照**。

#### 🔴 BUG: `_rewire_after_split()` 也使用浅拷贝

[hebbian.py L1004](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py#L1004):

```python
child_config = copy(bundle.config)  # ← SHALLOW COPY
```

同上：`silent_snapshot` 共享。

---

## 三、区域修改/新增是否仍会改变全局母本？

### 结论：**工厂创建不会，但分裂/发芽会**

#### ✅ 新增区域不改变母本

1. **HebbianCircuit.__init__()**: `extra_axes` 只影响 init 时创建的 neurons/bundles，不修改 VestibularChain 已有的任何组件 ✅

2. **VariantCircuit.__init__()**: `super().__init__(extra_axes=_patch_axes)` 将 patch 轴传入，HebbianCircuit 创建独立的 enc/col neurons 和 bundles。不修改任何已有组件 ✅

3. **Shadow _expand_for_new_axes**: 纯 append，注释和代码一致 ✅

4. **VariantCircuit.step()**: `super().step()` 调用不修改母类任何状态，所有 variant 效果是 post-hoc ✅

#### 🔴 分裂/发芽会通过浅拷贝污染

分裂（`Neuron.split()`）和发芽（`SynapticBundle.sprout()`）创建的子代与母本共享 `channels` list 和 `silent_snapshot` dict。

这两个场景在运行时都会触发：
- **分裂**：Motor neuron 的 FatigueCapacitor 超过阈值时触发（`_check_mitosis` 每 10k 步检查）
- **发芽**：`_structural_growth` 每 10k 步检查 `|ξ| > 0.3`

---

## 修复方案

> [!IMPORTANT]
> 修复非常简单：将三处 `copy()` 替换为 `deepcopy()`。

```diff
# neuron.py L672-674
- from copy import copy
- child_config = copy(self.config)
+ from copy import deepcopy
+ child_config = deepcopy(self.config)

# bundle.py L646-651
- from copy import copy
- child_config = copy(self.config)
+ from copy import deepcopy
+ child_config = deepcopy(self.config)

# hebbian.py L988/L1004
- from copy import copy
- child_config = copy(bundle.config)
+ from copy import deepcopy
+ child_config = deepcopy(bundle.config)
```

`deepcopy` 会递归复制 `channels` list 中的每个 `ChannelConfig` 和 `silent_snapshot` dict，保证子代与母本完全隔离。

**性能影响**：`deepcopy(NeuronConfig)` 约 10-50μs，仅在分裂/发芽时调用（每 10k 步最多 3 次），完全可忽略。

---

## 状态总结

| 问题 | 状态 | 严重度 |
|------|------|--------|
| 影子层自由能发散 | ❌ 不发散，但**坍缩为零** | 🟡 功能缺失 |
| 母本分化·工厂函数 | ✅ 每次创建独立实例 | — |
| 母本分化·split/sprout | 🔴 浅拷贝共享可变字段 | 🔴 定时炸弹 |
| 区域新增改变全局 | ✅ 新增不污染 | — |
| 分裂/发芽改变母本 | 🔴 通过 silent_snapshot 污染 | 🔴 活跃 bug |
