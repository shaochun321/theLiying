# 实现计划：结构化 DA 回路

## 问题

DA 通路当前是硬编码的 Python 变量读取，没有经过 Neuron、Bundle、STDP、sprout/prune。
不是一条真实的神经通路——是一行代码读一个 float。

## 目标架构

```
┌─ Shadow Layer ──────────┐     ┌─ Main Layer ──────────┐
│ s_col_yaw               │     │ Xin integrator        │
│ s_col_pitch             │     │ (Capacitor voltage)    │
│ s_col_roll              │     │         │              │
│ s_col_oto_x/y/z         │     │    xin_relay_neuron   │
│ s_col_therm             │     │         │              │
│         │               │     │         │              │
└─────────│───────────────┘     └─────────│──────────────┘
          │                               │
   [Bundle: shadow→DA]            [Bundle: xin→DA]
   STDP, sprout/prune              STDP, sprout/prune
          │                               │
          └───────────┬───────────────────┘
                      ▼
               ┌─ DA Neuron Pool ─┐
               │ da_vta_0         │
               │ da_vta_1         │  (3 neurons, non-spiking)
               │ da_vta_2         │
               └──────┬───────────┘
                      │
                      ▼ activation = DA concentration
                      │ (volumetric broadcast — biology)
                      │
          ┌───────────┼──────────────┐
          ▼           ▼              ▼
    STDP gate    Col gain      Fruit gate
```

## 修改文件

---

### [MODIFY] [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)

#### 新增组件（`__init__` 中）

```python
# DA neuron pool (3 VTA neurons, non-spiking)
self.da_neurons: Dict[str, Neuron] = {}
for i in range(3):
    nid = f"da_vta_{i}"
    cfg = NeuronConfig(
        neuron_id=nid,
        capacitance=2.0,        # τ = C*R = 2*1 = 2s (matches current DA τ_decay)
        r_leak=1.0,
        v_rest=0.0,
        channels=[ChannelConfig(name="default", v_threshold=0.01, gm=1.0)],
        bc_current=0.01,        # baseline activity → DA baseline ≈ 0.1
        energy=10.0,
        spiking=False,
        maturation_stage=0,     # spine stage: full plasticity on input bundles
    )
    self.da_neurons[nid] = Neuron(cfg)

# Xin relay neuron: mirrors Xin integrator voltage
self._xin_relay = Neuron(NeuronConfig(
    neuron_id="xin_relay",
    capacitance=0.5,    # fast tracking
    r_leak=2.0,
    v_rest=0.0,
    channels=[ChannelConfig(name="default", v_threshold=0.01, gm=1.0)],
    spiking=False,
))
```

> [!NOTE]
> DA 神经元的 `bc_current=0.01` 产生基线活动 ≈ 0.1（对应当前 DA baseline）。
> 外部输入增加 → 活动升高 → DA 升高。
> 无外部输入 → 衰减到基线。全部由膜电路自然实现。

#### 延迟初始化 DA Bundles

Shadow 层是延迟初始化的（首次 observe 时才有 neuron）。DA bundles 也需要延迟初始化：

```python
def _init_da_circuit(self):
    """Create DA input bundles after shadow layer is ready."""
    # Shadow col → DA neurons
    shadow_cols = [n for nid, n in self.shadow_sandbox.neurons.items()
                   if nid.startswith('s_col_')]
    da_list = list(self.da_neurons.values())
    
    self.bundles_shadow_to_da = []
    cfg = BundleConfig(
        bundle_id="shadow_to_da",
        initial_weight=0.05,
        stdp_lr=0.01,
        synapse_gain=5.0,
        bundle_role="feedforward",
    )
    self.bundles_shadow_to_da.append(
        SynapticBundle(cfg, shadow_cols, da_list))
    
    # Xin relay → DA neurons
    self.bundles_xin_to_da = []
    cfg_xin = BundleConfig(
        bundle_id="xin_to_da",
        initial_weight=0.1,
        stdp_lr=0.005,
        synapse_gain=3.0,
        bundle_role="feedforward",
    )
    self.bundles_xin_to_da.append(
        SynapticBundle(cfg_xin, [self._xin_relay], da_list))
    
    self._da_circuit_initialized = True
```

#### 重写 `_update_neuromodulation`

```python
# 8b. Step DA circuit (replaces all inline DA release logic)
if not getattr(self, '_da_circuit_initialized', False):
    self._init_da_circuit()

# Xin relay: mirror integrator voltage
self._xin_relay.step(self._xin_integrator.voltage * 0.5, dt)

# Shadow→DA propagation
for bundle in self.bundles_shadow_to_da:
    currents = bundle.propagate()
    for j, da_n in enumerate(self.da_neurons.values()):
        if j < len(currents):
            da_n.step(currents[j], dt)

# Xin→DA propagation
for bundle in self.bundles_xin_to_da:
    currents = bundle.propagate()
    for j, da_n in enumerate(self.da_neurons.values()):
        if j < len(currents):
            da_n._membrane.inject(currents[j] if j < len(currents) else 0, dt)

# DA neuron activation → dopamine concentration
mean_da_act = sum(n.activation for n in self.da_neurons.values()) / 3
self.dopamine._concentration = max(0.0, min(1.0, mean_da_act))

# STDP on DA input bundles
for bundle in self.bundles_shadow_to_da + self.bundles_xin_to_da:
    bundle.learn(dt=dt)
    bundle.compute_xin(dt)
```

> [!IMPORTANT]
> `dopamine.step(dt)` 不再调用（浓度由 DA neuron 直接设置）。
> `dopamine.release()` 不再调用（释放由 bundle 传播实现）。
> DA 的 baseline、decay、saturation 全部由 Neuron 的膜电路实现。

#### 删除的代码

- L622-646: Xin integrator → DA release 的 inline 代码
- L648-662: Shadow WCR → DA release 的 inline 代码
- L664: `self.dopamine.step(dt)`
- 保留 L666-678: DA gain → column（读取 `dopamine.concentration`，接口不变）

---

### [MODIFY] [shadow_sandbox.py](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py)

无修改。Shadow 层保持纯观察者角色。DA 回路读取 shadow neuron 的激活值，但不修改 shadow 内部状态。

---

## 垫支路径

DA 回路的垫支路径：

```
初始：shadow→DA 权重均匀 (0.05)
STDP：学习哪些 shadow col 信号与"需要 DA"相关
  → 有些权重增长（yaw/pitch col → DA，因为这些轴有输入变化）
  → 有些权重衰减（oto_x col → DA，因为该轴无输入）
Sprout：如果 Xin > threshold，shadow→DA 可以 sprout 子 bundle
Prune：弱子 bundle 被修剪
垫支：最终存活的权重矩阵 = "正常 DA 水平"的结构编码
```

## 验证计划

1. **治理测试**：`pytest test_governance.py` 无回归
2. **稳定输入**：50k 步，DA 应收敛到 baseline（非 1.0）
3. **输入突变**：稳定→改变→稳定，DA 应升高然后回落
4. **DA 权重收敛**：shadow→DA bundle 权重应有分化（非均匀）
