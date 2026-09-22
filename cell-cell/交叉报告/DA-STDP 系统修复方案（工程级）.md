# DA-STDP 系统修复方案（工程级）

**日期**: 2026-07-08
**依据**: DA-STDP系统清查报告 (DA_STDP_audit_2026-07-08.md)
**前置**: 所有问题已定位，现给出可直接执行的代码修改


## 执行摘要

| 优先级 | 数量 | 内容 |
| :--- | :--- | :--- |
| **P0 立即修复** | 3项 | pre_trace公式、CPG移除、gain_factor拆分 |
| **P1 第一批** | 3项 | da_ema_tau缩短、RPE负相位、hunger→调制 |
| **P2 第二批** | 2项 | trace_tau来源、_activation_ema配置 |


## P0-1: 修复 pre_trace 公式（标度错误）

**文件**: `components/neuron.py:589`

**当前代码**:
```python
self.pre_trace = self.pre_trace * decay_pre + abs(self.activation)
```

**修复后**:
```python
# 标准EMA归一化：稳态值 = 输入值，而非输入值/(1-decay)
self.pre_trace = self.pre_trace * decay_pre + abs(self.activation) * (1.0 - decay_pre)
```

**连锁影响**: 所有使用 `eligibility_gain` 的束需要重新校准，**乘以约 20 倍**（因为当前pre_trace稳态放大20.5倍）。具体值见下。

**验证**: 修正后，proj以0.1发放率(10步/次)时，pre_trace稳态应为0.1（而非2.05）。E(t)充电速率恢复正常标度。

**连锁校准**:
| 束 | 原 eligibility_gain | 新 eligibility_gain | 依据 |
|---|:---:|:---:|:---|
| relay_to_da | 1.0 | **0.05** | 原被20×放大补偿，修正后下调 |
| D1弧/影子层/therm_z | 1e-5 | **2e-4** | 同上，20×上调 |
| gated_reflex | 1e-4 | **2e-3** | 同上 |


## P0-2: 移除 CPG 通路（化石清理）

**文件**: `circuit/variant_adapter.py`

### 2.1 删除 CPG 神经元创建（约 L620-640）

```python
# 删除以下代码块：
# CPG 2Hz pacemaker - Van der Pol oscillator
self.cpg = CPGNeuron(...)
```

### 2.2 删除 cpg_to_da 束创建（约 L3036-3065）

```python
# 删除整个 cpg_to_da bundle 创建代码块
```

### 2.3 删除 CPG 步进调用

```python
# 删除 variant_adapter.step() 中的：
self.cpg.step(dt)
```

### 2.4 更新/删除过时注释

```python
# 删除以下位置的过时注释：
# L697-699: "CPG keeps DA.post_trace > 0"
# L2129: 同上
# L3037-3039: "CPG 2Hz pacemaker → keeps DA.post_trace > 0"
```

**验证**: 重跑T-092，确认DA_ema和LTP不受影响。移除后DA._activation_ema仍由bc_current维持~0.09。


## P0-3: 拆分 gain_factor()（语义混淆修复）

**文件**: `components/modulator.py`

### 3.1 新增 d1_gain_factor()

```python
def d1_gain_factor(self, conc: Optional[float] = None) -> float:
    """D1受体样增益调制——用于突触电流传播（快速，在线）"""
    c = conc if conc is not None else self.concentration
    return 1.0 + self.alpha_gain * (c - self.baseline)
```

### 3.2 新增 da_lr_gate()

```python
def da_lr_gate(self, conc: Optional[float] = None) -> float:
    """DA门控学习速率——用于三因子STDP（慢速，离线）"""
    c = conc if conc is not None else self.concentration
    # 低于baseline → gate<1（抑制），高于baseline → gate>1（增强）
    # baseline处 → gate=1（无偏置）
    return 1.0 + self.alpha_lr * (c - self.baseline)
```

### 3.3 更新调用点

**文件**: `circuit/variant_adapter.py:2483`
```python
# 原:
gain = self.dopamine.gain_factor()
# 改:
gain = self.dopamine.d1_gain_factor()
```

**文件**: `circuit/variant_adapter.py:2686`
```python
# 原:
gate = self.dopamine.gain_factor()
# 改:
gate = self.dopamine.da_lr_gate()
```

**验证**: 语义分离后，突触调制仍由DA驱动，学习门控可独立配置。baseline处门控无偏置（=1.0）。


## P1-1: 缩短 da_ema_tau（时间尺度对齐）

**文件**: `circuit/bundle.py:121`

**当前**:
```python
da_ema_tau: float = 5000.0
```

**修复后**:
```python
# τ=500 步匹配 eligibility_tau=300，实现精确时间信用分配
# 来源: T-092 证明 5000 过长导致门控失效
da_ema_tau: float = 500.0
```

**连锁影响**:
- DA_ema 现在反映约500步内的DA水平（而非5000步）
- OFF→ON 转换时，DA_ema 在~500步内达到新稳态（而非5000步）
- 与 E(t) τ=300 的时间尺度从“16.7倍失配”变为“1.7倍匹配”

**验证**: 重跑T-088 RPE签名，确认DA_ema收敛速度加快但RPE方向性保留。


## P1-2: 修复 RPE 负相位缺失

**文件**: `components/da_differential_gate.py:69`

**当前**:
```python
_rpe_da = max(0.0, self.eta_da * delta_fill)
self._da_drive = min(self.clip_max, _rpe_da)
```

**修复后**:
```python
# 完整RPE：正相位（好于预期）+ 负相位（差于预期）
_raw_rpe = self.eta_da * delta_fill  # 可为正或负
# 保留完整符号，不截断
self._da_drive = max(-self.clip_max, min(self.clip_max, _raw_rpe))
```

**连锁影响**: DA偏离基线现在双向驱动——正偏离强化学习，负偏离抑制学习。这要求DA门控使用偏离基线而非绝对值。

**验证**: 重跑T-088，确认撤源时DA dip低于基线（负RPE），而非仅回落至基线。


## P1-3: hunger 从驱动改为调制

**文件**: `circuit/variant_adapter.py:3418-3430`

**当前**:
```python
# hunger → DA: 直接注入
self.bundle_hunger_to_da = SynapticBundle(
    config=BundleConfig(..., initial_weight=0.04, synapse_gain=1.0),
    sources=[hypothalamus_hunger],
    targets=self.da_neurons
)
```

**修复后**（新增架构）:
```python
# hunger → DA增益调制: 不注入DA，调制DA对其他输入的响应
# 物理实现: hunger信号作为MOSFET栅压，调制DA神经元的总输入增益
self.hunger_mod_gain = Capacitor(capacitance=100.0)  # 慢积分

def get_hunger_modulation(self) -> float:
    """hunger调制因子: 1.0(饱腹) ~ 3.0(极度饥饿)"""
    h_act = self.hypothalamus_hunger.activation
    return 1.0 + 2.0 * h_act  # 最大3倍增益调制
```

**在 DA 神经元步进中应用**:
```python
# 原: total_input = Σbundle_I + bc_current + i_girk
# 改:
hunger_mod = self.get_hunger_modulation()
total_input = (Σbundle_I + bc_current + i_girk) * hunger_mod
```

**验证**: 饱腹时(饥饿=0)调制=1.0，饥饿时(饥饿=1)调制=3.0。DA响应饥饿状态，但不直接注入DA。


## P2-1: trace_tau 来源补充与配置化

**文件**: `components/neuron.py:94-95`

**当前**:
```python
trace_tau_pre: float = 0.02    # 20ms
trace_tau_post: float = 0.02   # 20ms
```

**修复后**:
```python
# trace_tau_pre: 突触前脉冲迹衰减时间常数
# 参考文献: Markram et al. 1998 (Neuron, 20:167-176) — 成对脉冲STDP窗口τ~20ms
# 本系统映射: 1步 = 1ms, 20ms = 20步
# 注: 该值应与bundle.eligibility_tau(300步)配合使用
trace_tau_pre: float = 0.02   # 20ms (Markram 1998, STDP window)
trace_tau_post: float = 0.02  # 20ms (对称)
```

**同时**: 将这两个参数加入 `NeuronConfig` 的配置入口（而非硬编码），允许实验扫描。


## P2-2: _activation_ema α 配置化

**文件**: `components/neuron.py:603`

**当前**:
```python
alpha = 0.01  # 硬编码
self._activation_ema = self._activation_ema * (1 - alpha) + activation * alpha
```

**修复后**:
```python
# 使用配置参数，默认0.01 (100步EMA)
alpha = self.config.activation_ema_alpha  # 需在NeuronConfig中新增字段
self._activation_ema = self._activation_ema * (1 - alpha) + activation * alpha
```

**新增 `NeuronConfig` 字段**:
```python
activation_ema_alpha: float = 0.01  # α=0.01 → τ≈100步
```


## 修复顺序与验证

```
P0-1: pre_trace公式修复 → 重跑T-092，确认E(t)充电速率正常
P0-2: CPG移除 → 重跑21/21回归，确认无影响
P0-3: gain_factor拆分 → 重跑T-089，确认热趋性保全
        ↓
P1-1: da_ema_tau缩短 → 重跑T-088 RPE签名
P1-2: RPE负相位修复 → 重跑T-088，确认撤源dip
P1-3: hunger调制重构 → 重跑饥饿vs饱腹对照
        ↓
P2-1: trace_tau来源补充
P2-2: _activation_ema配置化
```

---

**这个方案可以直接交给我执行。**

后续工程与理论层面的整合（CPG作为“系统的定义者”、CPC作为“偏离检测后的执行器”），可以在这些修复验证通过后继续进行。