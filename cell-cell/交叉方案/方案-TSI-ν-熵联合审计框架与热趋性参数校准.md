# 方案：TSI-ν-熵联合审计框架与热趋性参数校准

**日期**：2026-07-02
**版本**：v2.0（基于评判与补充方案整合）
**性质**：可执行实施方案
**前置**：TSI-ν-熵方案评判报告、补充方案、冷启动DA诊断


## 一、核心理念：从“事前约束”到“事后审计”

原方案试图用 `P_T(gain) ≤ P_input × 0.8` 作为参数调整的**事前约束**，这在物理上是无效的——两个量在不同流形上，缺少合法的转换映射。

| 原方案 | 修正后 |
| :--- | :--- |
| 事前约束：预测参数是否合法 | 事后审计：测量参数调整后的系统响应是否在物理边界内 |
| 单一不等式 | 三重审计（TSI + ν + 熵） |
| 假设量纲可直接比较 | 通过扫描实验建立实测映射 |


## 二、核心数理框架

### 2.1 运动势 ν（功率量纲修正）

ν 是系统偏离稳态的**功率通量**：

$$
\nu(t) = \sum_i \frac{1}{R_{\xi}} \cdot \xi_i(t) \frac{d\xi_i(t)}{dt}
$$

- $\xi_i$：Xin 张力（电压量纲 V）
- $R_{\xi}$：认知网络等效流形阻抗（量纲 Ω）
- $\nu > 0$：探索态（系统偏离稳态）
- $\nu < 0$：固化态（系统回归稳态）
- $\nu$ 的量纲：$V^2/\Omega = W$（已修正）

### 2.2 信息熵 H

系统权重的信息熵：

$$
H(t) = -\sum_j \xi_j(t) \ln \xi_j(t)
$$

- $dH/dt < 0$：结构在固化（信息在压缩）
- $dH/dt \approx 0$：无信息增益（学习停滞）
- $dH/dt > 0$：结构在发散（可能噪声主导）

### 2.3 TSI 功率账本

$$
P_{in}(t) \ge P_T(t) + P_S(t) + P_I(t)
$$

| 项 | 公式 | 量纲 | 说明 |
| :--- | :--- | :--- | :--- |
| $P_{in}$ | VascularCooling 模型 | W | 环境能量输入 |
| $P_T$ | $\sum_i (I_{syn,i}^2 R_m + V_i^2/R_{leak})$ | W | 传输功率（突触+漏电）|
| $P_S$ | $\eta_s \sum_{ij} (dw_{ij}/dt)^2 \cdot d_{ij}$ | W | 结构功率（含距离惩罚）|
| $P_I$ | $\nu$（已修正）| W | 信息功率（Xin动力学）|


## 三、执行流程

### 步骤 0：前置准备

- 确认 NuProbe 已实现（`system_ν_ema`、`charging_fraction`）
- 确认 WeightEntropyProbe 已实现（全系统熵值）
- 确认 EnergyStore 可输出 `drain_rate` 和 `deposit_rate`

### 步骤 1：增益扫描实验

**目标**：建立 `THERMAL_TRANSDUCTION_GAIN → 系统响应` 的实测映射。

**设置**：
- body 固定于 $d=20$（远离热源）
- 肌肉增益 = 0（body 不移动）
- 每增益值：3000 步预热 + 2000 步测量

**测量项**：

| 测量项 | 来源 | 记录值 |
| :--- | :--- | :--- |
| `relay_activation_mean` | relay 神经元 | 是否 ≥ 0.01 |
| `drain_rate` | EnergyStore | fill/步 |
| `ν` | NuProbe | system_ν_ema |
| `entropy` | WeightEntropyProbe | H |
| `DA_post_trace` | DA 神经元 | post_trace 均值 |

**扫描范围**：
`gain ∈ {0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0}`

### 步骤 2：三重审计判定（替代原“TSI上限约束”）

对每个增益值，依次应用以下审计：

#### 审计 1：信号检测（物理合法）

| 条件 | 通过 | 失败 |
| :--- | :--- | :--- |
| `relay_activation_mean ≥ 0.01` | 信号已进入系统（增益有效）| 增益不足，跳过后续审计 |
| `DA_post_trace_mean > 0` | 学习信号在传递 | DA 稳态死锁 |

#### 审计 2：代谢可持续（TSI）

$$
\text{drain\_rate}(gain) < \frac{\text{fill\_capacity}}{50k}
$$

- 不是 `drain_rate ≤ deposit_rate`（在冷区 d=20 时 deposit_rate 极低，过度保守）
- 而是“保证不提前饿死”——fill 耗尽时间 > 50k 步

#### 审计 3：探索态持续（ν）

- **判据修正**：ν>0 仅作为**上下文参考**，不独立决定通过/失败
- 对比：ν(gain) vs ν(baseline) 的差异是否显著（>10%）
- 若增益提高后 ν 显著高于基线，说明系统确实进入了更强的探索态

#### 审计 4：信息增益（熵）

- **判据修正**：熵值仅作为**上下文参考**，不独立决定通过/失败
- 检查：熵是否继续增长（信息在增加）而非停滞或无序暴涨（噪声主导）
- 若熵增长率随增益提高而**下降**，可能是增益无效或饱和

### 步骤 3：输出

| 输出 | 定义 | 用途 |
| :--- | :--- | :--- |
| `gain_min` | 使 relay_activation_mean ≥ 0.01 的最小增益 | 信号阈值 |
| `gain_max` | 使 `drain_rate ≥ fill_capacity/50k` 的临界增益 | 代谢上限 |
| `gain_opt` | 在 `[gain_min, gain_max]` 内，ν 最高且熵继续增长的增益 | **推荐值** |

`gain_opt` 的选取：偏向 `gain_min` 向上浮动 10%-20%（为长程实验中 STDP 权重增长预留代谢空间）。


## 四、增益扫描的长期验证

步骤 1-3 提供了**初步有效范围**，但最终验证必须通过 500k 步长程实验：

| 检查 | 通过条件 | 失败条件 |
| :--- | :--- | :--- |
| fill 轨迹 | 250k 步内未归零 | fill 提前耗尽 |
| ν 轨迹 | ν>0 持续出现 | ν 长期为负（系统固化） |
| 熵轨迹 | 熵先升后降（学习发生）| 熵停滞或无序暴涨 |
| 权重分化 | |Δw| > 0.01 | 权重不分化 |


## 五、增益扫描的结果填入

待扫描脚本 `exp_calibrate_gain.py` 完成后填入：

| gain | relay_act | drain_rate | ν | entropy | DA_post_trace | 审计结果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0.1 | | | | | | |
| 0.2 | | | | | | |
| ... | | | | | | |
| gain_opt | | | | | | 推荐 |


## 六、增益扫描的工程落地

### 6.1 测量脚本框架

```python
# nexus_v1/tests/exp_calibrate_gain.py

def scan_gain(gain_values, steps_per_point=5000, settle_steps=3000):
    results = []
    for gain in gain_values:
        # 设置增益
        set_thermal_transduction_gain(gain)
        
        # 预热
        for _ in range(settle_steps):
            variant_adapter.step()
        
        # 测量
        relay_acts = []
        drain_rates = []
        nus = []
        entropies = []
        da_post_traces = []
        
        for _ in range(steps_per_point):
            variant_adapter.step()
            relay_acts.append(relay.activation)
            drain_rates.append(energy_store.drain_rate)
            nus.append(nu_probe.system_nu_ema)
            entropies.append(weight_entropy_probe.H)
            da_post_traces.append(da_neuron.post_trace)
        
        results.append({
            'gain': gain,
            'relay_act_mean': mean(relay_acts),
            'drain_rate_mean': mean(drain_rates),
            'nu_mean': mean(nus),
            'entropy_mean': mean(entropies),
            'da_post_trace_mean': mean(da_post_traces),
        })
    return results
```

### 6.2 判定实现

```python
def audit_gain(result):
    # 审计1：信号检测
    if result['relay_act_mean'] < 0.01:
        return 'GAIN_INSUFFICIENT'
    
    # 审计2：代谢可持续
    if result['drain_rate_mean'] >= FILL_CAPACITY / 50000:
        return 'GAIN_EXCESSIVE_METABOLIC'
    
    # 审计3：探索态（参考）
    if result['nu_mean'] < 0:
        return 'GAIN_MAY_BE_SATURATED'
    
    # 审计4：熵（参考）
    # 需要对比基线熵
    if result['entropy_mean'] < BASELINE_ENTROPY:
        return 'GAIN_MAY_BE_INVALID'
    
    return 'GAIN_VALID'
```


## 七、冷启动 DA 的集成

增益扫描发现的 `gain_opt` 在长程实验中使用时，需配合 DA 冷启动机制：

```python
# 在 DA 神经元 step 中
DA_v_mem += max(0, (FILL_REF - fill_fraction)) * HUNGER_GAIN  # 饥饿基线
DA_v_mem += EPSILON * sin(2 * pi * FREQ * t)  # 微幅振荡
```

- `EPSILON = 0.01V`（远小于 v_peak，不干扰主信号）
- `FREQ = 2Hz`（与 VitalOscillator 同频）
- 振荡提供持续的 `post_trace`，防止 DA 稳态死锁


## 八、时间线

| 步骤 | 任务 | 预计时间 |
| :--- | :--- | :--- |
| 1 | 编写增益扫描脚本 | 2 小时 |
| 2 | 执行增益扫描 | 1 小时（运行时间）|
| 3 | 三重审计判定 | 0.5 小时 |
| 4 | 选定 `gain_opt` | 即时 |
| 5 | 500k 步长程验证（含冷启动 DA）| ~35 分钟 |


## 九、总结

| 组件 | 状态 | 说明 |
| :--- | :--- | :--- |
| 增益扫描 | ✅ 可执行 | 脚本框架已定义 |
| TSI 审计 | ✅ 修正 | `drain_rate ≤ fill_capacity/50k` |
| ν 审计 | ✅ 修正 | 参考判据，非独立决定 |
| 熵审计 | ✅ 修正 | 参考判据，非独立决定 |
| 冷启动 DA | ✅ 集成 | 饥饿基线 + 微幅振荡 |
| 最终裁决 | ⏳ 待执行 | 500k 步长程实验 |