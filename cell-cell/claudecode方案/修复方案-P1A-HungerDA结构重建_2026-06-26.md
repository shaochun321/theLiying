# 修复方案 P1-A：Hunger DA 结构重建（V-01 + D-04）

**方案日期**: 2026-06-26  
**覆盖问题**: V-01（Hunger DA 绕过 bundle）+ D-04（DA 注入量级未校准）  
**关联 DEG**: DEG-P4-005  
**执行前提**: P0 快速修复已完成  
**复杂度**: 中等（新建 1 个 Neuron 配置 + 1 条 Bundle，不修改母本代码）  
**目标文件**: `cell-cc-other/nexus_v1/circuit/variant_adapter.py`  

---

## 三问强制回答

### Q1. 生物对应物

**Hunger DA 来源**：下丘脑外侧区（Lateral Hypothalamus, LH）在能量不足时向 VTA 多巴胺神经元发送持续兴奋投射。

```
BIO: 下丘脑外侧区（LH）→ VTA 多巴胺神经元（饥饿驱动）
REF: Wise 2004, Nat Rev Neurosci 5:483-494 — LH lesions abolish hunger-driven DA
REF: Stuber & Wise 2016, Nat Neurosci 19:198-205 — LH→VTA circuit for caloric deficit
```

**HungerDriveNeuron 对应物**：LH 的 Orexin/MCH 神经元，受血糖（即 fill_fraction）调控。
- Orexin 神经元在饥饿时（低血糖）激活，投射到 VTA
- 在能量充足时沉默（fill > 0.5 以上时 → 抑制 LH Orexin）

```
BIO: Orexin (hypocretin) neurons in LH
REF: Adamantidis et al. 2007, Nature 450:420-424 — Orexin→VTA pathway
```

### Q2. 物理结构

```
EnergyStore.fill_fraction
    ↓ (inversely: 饥饿度 = 1 - fill)
HungerDriveNeuron  [TYPE:HYBRID — Orexin 神经元 + Capacitor 积分]
    ↓ SynapticBundle: hunger_to_da
        initial_weight = W_hunger
        synapse_gain = G_hunger
        learning_rule = "hebbian"  (不用 STDP：饥饿→DA 是固定反射)
        stdp_lr = 0.0
DA Neurons (da_neuron_0, da_neuron_1, ...)
```

**已有对象**：`self.da_neurons`（已注册在 `get_all_neurons()`）  
**新建对象**：`self._hunger_neuron`（Neuron）+ `self._bundle_hunger_to_da`（SynapticBundle）

HungerDriveNeuron 的驱动方式：每步将 `(1 - fill_fraction) * HUNGER_DRIVE_SCALE` 作为电流注入，通过 Neuron 的膜积分转换为激活值，再经 bundle 传递到 DA 神经元。

这与 `extra_axes` 中热传感的处理方式一致（`enc_reg.step(tonic_val * 5.0, dt)`），是系统已有的"传感器→Neuron"接口模式。

### Q3. 参数依据

**目标行为**：fill=0.5 时 hunger_da=0（DA 不受 hunger 影响），fill=0 时 hunger_da 使 DA 激活达到约 50% 的基础放电率（温和驱动，不饱和）。

**现有 DA 基础激活**（来自 bc_current）：
```
V_ss(DA, bias) = bc_current × R_leak = 0.1 × 5.0 = 0.5V
DA v_peak ≈ 0.3~0.5（需从 _init_da_circuit 读取）
```

**期望：hunger 注入使 DA 膜电压增加 ≤ 30% × (v_peak - V_ss)**

推导：
1. fill=0 → `hunger_input = (1 - 0) × HUNGER_DRIVE_SCALE = HUNGER_DRIVE_SCALE`
2. HungerDriveNeuron 稳态：`V_hunger_ss = hunger_input × R_hunger`（需设计）
3. HungerDriveNeuron 激活 `act_hunger ∈ [0,1]`
4. Bundle 传入 DA：`I_da = act_hunger × synapse_gain × weight`
5. DA 稳态偏移：`ΔV_da = I_da × R_da`；要求 `ΔV_da ≤ 0.30 × (0.5 - V_ss(bias)) = 0.30 × 0.0`
   等等，V_ss(bias)=0.5 而 v_peak=? 需要查 DA 配置。

先用已知数据反推：

**Phase 4 实验中**，`_hunger_da = max(0, 1.0 × (0.5 - fill)) = 0.5` 时（fill=0），
`inject(0.5, 0.001)` → dQ = 0.0005 → dV/step = 0.0005/C_da。
若 C_da=0.15：dV = 0.0033V/step，稳态 V_da_ss ≈ 0.0033/（V_da × dt/τ_da）。

实验中 DA 神经元确实饱和放电（Phase 4 前 20k 步 DA=1.0），说明 `θ_hunger=1.0` 量级过大。

**修正目标**：fill=0.2（轻度饥饿）时，hunger 贡献约 20% DA 激活增加。

---

## 实现计划

### 步骤 1：在 `__init__` 中创建 HungerDriveNeuron

在 `_init_da_circuit()` 之前初始化（因为 hunger neuron 需要在 DA circuit 初始化时作为 source）：

```python
# circuit/variant_adapter.py，__init__ 中 DA 神经元初始化之后

# ── Hunger Drive Neuron: LH Orexin analog ──
# TYPE:HYBRID — Orexin neuron integrates caloric deficit → drives VTA DA
# BIO: LH lateral hypothalamus Orexin neurons, activated by low blood glucose
# REF: Stuber & Wise 2016, Nat Neurosci 19:198-205
# NORM: τ_hunger = C × R = 2.0 × 5.0 = 10s (slow metabolic timescale)
#       V_ss at full hunger (fill=0): HUNGER_DRIVE_SCALE × R = 0.02 × 5.0 = 0.10
#       act_hunger at full hunger ≈ sigmoid(V_ss) ≈ 0.1 (modest activation)
HUNGER_DRIVE_SCALE = 0.02  # BIO: tonic LH→VTA current at maximal deficit
                            # NORM: gives V_ss=0.10 at fill=0, sub-threshold at fill=0.5
from ..components.neuron import Neuron, NeuronConfig, ChannelConfig
self._hunger_neuron = Neuron(NeuronConfig(
    neuron_id="hunger_lh",
    # τ = C × R = 2.0 × 5.0 = 10s — metabolic timescale (slow, matches fill dynamics)
    # BIO: orexin neurons integrate metabolic state over minutes, not ms
    capacitance=2.0,
    r_leak=5.0,
    inertia=0.0,
    vdd=1.0,
    r_supply=0.1,
    spiking=False,     # BIO: Orexin neurons are non-spiking graded release
    v_peak=1.0,        # not used (spiking=False)
    v_reset=0.0,
    channels=[
        ChannelConfig(
            name="lh_orexin",
            v_threshold=0.0,    # always conducting (graded)
            gm=0.5,
            tau_gate=0.0,
            reversal=0.0,
            sign=1.0,
        ),
    ],
    use_voltage_regulator=False,
    use_bias_current=False,
))
self._bundle_hunger_to_da: SynapticBundle | None = None  # init later in _init_da_circuit
```

### 步骤 2：在 `step()` 中驱动 HungerDriveNeuron

替换当前 `inject(_hunger_da, dt)` 的位置（约第 894-903 行）：

```python
# BEFORE（直接注入，绕过结构）:
_rpe_da = self.da_gate.step(self.energy_store.fill_fraction, dt)
_hunger_da = max(0.0, 1.0 * (0.5 - self.energy_store.fill_fraction))
_da_drive = max(_rpe_da, _hunger_da)
if _da_drive > 0:
    for nid, neuron in self.da_neurons.items():
        neuron._membrane.inject(_da_drive, dt)
```

```python
# AFTER（RPE 保留直接注入作为过渡；Hunger 经 Neuron + Bundle 结构路径）:

# RPE (Schultz 1997): 保留直接注入，待 V-01 完整修复后再结构化
_rpe_da = self.da_gate.step(self.energy_store.fill_fraction, dt)
if _rpe_da > 0:
    for nid, neuron in self.da_neurons.items():
        neuron._membrane.inject(_rpe_da, dt)

# Hunger (Stuber & Wise 2016): 经 LH Orexin 神经元 → bundle → DA
# BIO: LH Orexin activation ∝ caloric deficit (1 - fill_fraction)
# at fill=0.5: hunger_input=0 → hunger_neuron silent → no DA contribution
# at fill=0.0: hunger_input=HUNGER_DRIVE_SCALE → hunger_neuron activates → DA +
_hunger_input = max(0.0, (0.5 - self.energy_store.fill_fraction) * HUNGER_DRIVE_SCALE)
self._hunger_neuron.step(_hunger_input, dt)

# Bundle propagation happens in _do_learning or after super().step()
# (see Step 3: bundle propagation)
```

### 步骤 3：在 `_init_da_circuit()` 中创建 hunger_to_da bundle

找到 `_init_da_circuit()` 方法（约第 1689 行），在 `xin_to_da` bundle 创建后添加：

```python
# 在 _init_da_circuit() 末尾，da_list 已准备好之后添加：

# ── Hunger → DA bundle (LH Orexin → VTA) ──
# TYPE:HYBRID — fixed-weight (hebbian, no STDP): hunger→DA is hard-wired reflex
# BIO: LH Orexin→VTA projection is anatomically fixed (Adamantidis 2007)
# weight: calibrated so full hunger (act≈0.1) → DA ΔV ≈ 0.15 × (v_peak - V_ss)
# initial_weight=1.5: act_hunger × synapse_gain × weight = 0.1 × 1.0 × 1.5 = 0.15
# ΔV_da = 0.15 × dt / C_da ≈ 0.15 × 0.001 / 0.15 = 0.001V/step → reasonable
# REF: Stuber & Wise 2016; initial_weight ESTIMATED — mark for EXP validation
cfg_hunger = BundleConfig(
    bundle_id="hunger_to_da",
    learning_rule="hebbian",    # fixed reflex, not STDP
    initial_weight=1.5,         # ESTIMATED: 0.1 act × 1.5 → ΔV_da ≈ 0.001V/step
    weight_max=3.0,             # ceiling: prevent runaway
    weight_min=0.0,
    stdp_lr=0.0,                # no plasticity: hunger→DA is hard-wired
    synapse_gain=1.0,
    bundle_role="neuromodulatory",
)
self._bundle_hunger_to_da = SynapticBundle(
    cfg_hunger, [self._hunger_neuron], da_list)
```

### 步骤 4：在 step() 中传播 hunger_to_da bundle

在 `super().step(mechanical_inputs, dt)` 之后（约第 954 行）, 与其他 DA bundle 传播位置一起：

```python
# 在 DA input bundles 传播段（约第 1144-1150 行附近）添加：
if self._bundle_hunger_to_da is not None:
    h_currents = self._bundle_hunger_to_da.propagate()
    self._bundle_hunger_to_da.apply_to_targets(h_currents, dt)
```

### 步骤 5：更新 census 方法

```python
def get_all_neurons(self):
    neurons = super().get_all_neurons()
    neurons.extend(self.da_neurons.values())
    neurons.append(self._xin_relay)
    neurons.append(self._hunger_neuron)          # ← 新增
    neurons.extend(self.somatosensory.get_all_neurons())
    return neurons

def get_all_bundles(self):
    bundles = super().get_all_bundles()
    bundles.extend(self.bundles_shadow_to_da)
    bundles.extend(self.bundles_xin_to_da)
    if self._bundle_hunger_to_da is not None:
        bundles.append(self._bundle_hunger_to_da)  # ← 新增
    bundles.extend(self.somatosensory.get_all_bundles())
    return bundles
```

### 步骤 6：删除旧的 Hunger 直接注入代码

步骤 2 已完成替换，确认旧代码块已删除：
```python
# 确认以下代码已删除：
# _hunger_da = max(0.0, 1.0 * (0.5 - self.energy_store.fill_fraction))
# _da_drive = max(_rpe_da, _hunger_da)
# if _da_drive > 0:
#     for nid, neuron in self.da_neurons.items():
#         neuron._membrane.inject(_da_drive, dt)
```

---

## 参数校准说明

### HUNGER_DRIVE_SCALE = 0.02 推导

目标：fill=0 时，hunger 贡献使 DA 轻度激活（不饱和）：

```
hunger_input @ fill=0 = 0.5 × HUNGER_DRIVE_SCALE = 0.5 × 0.02 = 0.01
HungerNeuron 稳态：V_ss = I × R = 0.01 × 5.0 = 0.05V
act_hunger ≈ MOSFET.conduct(0.05) ≈ 小量（通道阈值=0, gm=0.5 → act=0.025）
Bundle 电流：0.025 × 1.0 × 1.5 = 0.0375
inject(0.0375, 0.001) → dV_da = 0.0375 × 0.001 / C_da
若 C_da=0.15 → dV_da = 0.00025V/step（温和）
```

标注：`# ESTIMATED: needs EXP-hunger-calibration to verify DA activation at fill=0.2`

### 与 RPE 的分离

- RPE：瞬时大幅信号（Δfill 大时），直接 inject（保留现有路径作为过渡）
- Hunger：慢速持续信号（fill 低时），经 bundle
- 两者不再 `max()` 合并，各自独立传播到 DA 神经元

---

## 验证计划

### 单元测试

```python
# 快速验证 hunger_neuron 已注册在 census 中
c = VariantCircuit()
assert any(n.config.neuron_id == "hunger_lh"
           for n in c.get_all_neurons()), "hunger_neuron missing from census"
assert any(b.config.bundle_id == "hunger_to_da"
           for b in c.get_all_bundles()), "hunger_to_da bundle missing from census"
```

### 行为测试

```python
# 模拟 fill 从 0.5 下降到 0，观察 hunger_neuron 激活
c = VariantCircuit()
c.energy_store._level = 0.0   # 强制 fill=0
for _ in range(1000):
    c._hunger_neuron.step(
        max(0.0, (0.5 - c.energy_store.fill_fraction) * 0.02), 0.001)
print("hunger_neuron activation:", c._hunger_neuron.activation)
# 预期：activation > 0, < 0.1（温和，不饱和）
```

### 回归验证

```bash
PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.test_regression
# 预期：21/21 PASS
```

### 熵审计

```bash
PYTHONIOENCODING=utf-8 python nexus_v1/run_audit.py
# 新增检查项：
# - hunger_neuron 出现在 signal_depth 报告中
# - hunger_to_da 出现在 bundle_weights 报告中
# - Noether 权重守恒：hunger_to_da 权重纳入 Σw 计算
```

---

## 风险评估

| 风险 | 可能性 | 影响 | 缓解 |
|------|--------|------|------|
| hunger_neuron 激活过低（无效） | 中 | 低 | 实验 EXP-hunger-calibration 调整 HUNGER_DRIVE_SCALE |
| hunger_neuron 激活过高（DA 饱和） | 低 | 高 | V_ss 推导保守，初始 HUNGER_DRIVE_SCALE=0.02 << Phase4 的 0.5 |
| bundle 延迟（lazy init 时序） | 低 | 中 | 检查 _bundle_hunger_to_da is not None 前置条件 |
| census 遗漏导致 Noether 审计错误 | 低 | 中 | 步骤 5 明确更新两个 census 方法 |

---

## 后续：D-03 Column v_peak 修正

P1-A 完成后，按以下生物推导修正 Column v_peak（见方案 P1-B §D-03 节）：

```
V_norm = (V_bio - E_K) / (E_Ca - E_K)
皮层柱整合神经元 AP 阈值 V_th_bio ≈ -55mV
V_th_norm = (-55 + 80) / 130 = 0.192
→ v_peak 应不低于 0.15（对应 V_bio = -60.5mV）
```

关联方案：P0 快速修复、P1-B 量纲校准、P2 技术债
