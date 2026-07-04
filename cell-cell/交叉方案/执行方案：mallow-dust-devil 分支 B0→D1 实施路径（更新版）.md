# 执行方案：mallow-dust-devil 分支 B0→D1 实施路径（更新版）

**日期**：2026-07-04
**关联**：阶段回顾报告、V3.0-final、脑区空间归类方案
**状态**：待执行


## 一、执行路径总览

```
B0（TemporalCoupler B-layer 诊断）
    ↓
200k 基线实验（含 ν 分布统计）
    ↓
B1（HC-016/023 替换：deviation→VitalOscillator + Renshaw 侧抑制）
    ↓
C1（ν→DA/AGC 接线：NuThresholdNeuron）
    ↓
清理 relay→yaw 负债
    ↓
D1（phasic_relay→spinal_turn_toward STDP+DA门控）
    ↓
D2（spinal_turn_toward→motor_turn）
```

**关键依赖**：C1 必须在 D1 之前完成。D1 的 STDP 需要 DA 门控，C1 是 DA 门控的物理来源。此顺序不可颠倒。


## 二、B0：TemporalCoupler B-layer 诊断

### 2.1 内容

只读检查 TemporalCoupler B-layer 参数配置，不改变任何行为。

### 2.2 检查项

| 检查项 | 文件 | 目标 |
| :--- | :--- | :--- |
| `blayer_c_slow` 传递路径 | `bundle.py` → `TemporalCoupler.__init__` | 确认参数未被默认 0.0 覆盖 |
| B-layer 差分 MOSFET `v_threshold` | `temporal_coupler.py` | 确认阈值未过高阻断导通 |
| `leak_resistance_slow` | `temporal_coupler.py` | 确认未将 V_slow 短路接地 |
| `ema_up`/`ema_down` 更新 | `temporal_coupler.py` | 确认输入 EMA 值被正确更新 |
| RC 时间常数 | `temporal_coupler.py` | 确认 τ 与预期反应时间匹配（不退化 fast）|

### 2.3 验收

| 检查项 | 通过条件 |
| :--- | :--- |
| 参数传递 | `blayer_c_slow` 非 0.0 且被正确传递 |
| v_threshold | ≤ 0.1 |
| r_leak_slow | ≥ 1.0 |
| EMA 更新 | 每步 ema_up/ema_down 有非零变化 |
| 回归测试 | 21/21 PASS |

### 2.4 产出

B-layer 诊断报告：参数状态、根因假设（如有）、修复建议。


## 三、200k 基线实验（含 ν 分布统计）

### 3.1 内容

在 B0 完成后，运行 200k 基线实验，采集系统在无重大结构改动前的行为数据和 ν 分布。

### 3.2 实验配置

| 参数 | 值 |
| :--- | :--- |
| 热源 | [70,50,25]，T=5，radius=30，静止 |
| Body 初始 | [50,50,25]，朝 +x |
| 步数 | 200,000 |
| dt | 0.001 |
| DR5 定义 | d(t) < d(t-1000) 的步数比例 |
| 记录项 | d(t), yaw, patch_temps, relay activations, ν_ema, fill |

### 3.3 验收

| 检查项 | 通过条件 |
| :--- | :--- |
| ν 分布统计 | 计算 ν_mean、ν_std、ν_90th（90% 分位数）|
| 回归测试 | 21/21 PASS |
| 行为可复现 | 与 Phase A 基线行为一致（无退化）|

### 3.4 产出

ν 分布统计值（ν_mean、ν_std、ν_90th），作为 C1 阈值设定的数据基础。


## 四、B1：HC-016/023 替换

### 4.1 B1a：HC-016 替换（deviation→VitalOscillator）

**结构**：
```
下丘脑 deviation 信号 → [Bundle, frozen, gain=0.3, w=0.5] → VitalOscillator（振幅调制，非频率）
```

**关键设计**：偏差信号调制节律**振幅**，而非频率。饥饿时步伐更大，而非步频更高。

**验收**：
- 原始 `_membrane.inject()` 调用已删除
- 新 Bundle 在 census 中可见
- Noether 0 violations
- 回归测试 21/21 PASS

**三问**：
- Q1 BIO：下丘脑外侧区（LH）→ 脑干被盖（PPTg/LDT）arousal 投射（Saper 2002）
- Q2 结构：下丘脑 L2 → VitalOscillator 冻结 Bundle
- Q3 参数：gain=0.3，w=0.5

### 4.2 B1b：HC-023 替换（Motor 侧抑制 → Renshaw Bundle）

**结构**：
```
motor_move_x → [Bundle, frozen, gain=1.0, w=0.3] → Renshaw_interneuron → [Bundle, frozen, gain=-0.5, w=0.3] → motor_move_y/z
```

**验收**：
- 原始侧抑制 `_membrane.inject()` 已删除
- Renshaw 中间神经元（region=0x01）已创建
- 两条 Bundle 在 census 中可见
- 回归测试 21/21 PASS


## 五、C1：ν→DA/AGC 接线

### 5.1 内容

创建 `NuThresholdNeuron`，将 shadow_sandbox._nu 经阈值比较器接入 DA 调制。

### 5.2 阈值设定

| 方法 | 说明 |
| :--- | :--- |
| 主方案 | 使用 ν 的 90% 分位数（ν_90th）作为阈值（从 200k 基线统计）|
| 备选 | ν_mean + 1σ，仅在 ν 分布接近正态时使用 |

**警示**：ν 分布可能为长尾分布，ν_mean + 1σ 可能被极端值拉高。建议优先使用分位数。

**补充**：ν是宏观功率量纲（W）的全局积分量，而DA释放是局部电化学事件。ν的下降是Xin局部坍缩的宏观滞后指标，不是触发DA的直接因果信号。NuThresholdNeuron的阈值比较只是工程近似——真正的“顿悟”应发生在局部Xin坍缩的瞬时，而非ν穿越阈值的时刻。当前实现是合理的，但应标注这一物理层级差异，作为远期精化的预留接口。

### 5.3 结构

```
shadow_sandbox._nu → NuThresholdNeuron（0x05，阈值=ν_90th）→ [Bundle, frozen, gain=1.0] → DA 神经元
```

### 5.4 验收

| 检查项 | 通过条件 |
| :--- | :--- |
| NuThresholdNeuron | 在 census 中可见 |
| ν > 阈值时 | DA 升高 |
| ν < 阈值时 | DA 基线 |
| 回归测试 | 21/21 PASS |


## 六、清理 relay→yaw 负债（D1 前）

### 6.1 清理清单

| 负债 | 操作 |
| :--- | :--- |
| `bundles_relay_to_yaw`（LTP 4条 + LTD 2条）| 从 census 注销，删除配置块 |
| relay→yaw 绕过路径 | 统一修正为 phasic_relay→spinal_turn_toward |

### 6.2 清理确认

| 检查项 | 通过条件 |
| :--- | :--- |
| 束已删除 | 不在 census 中 |
| 幽灵连接 | 无残留 inject 调用 |
| TSI 账本 | Noether 0 violations |


## 七、D1：phasic_relay→spinal_turn_toward

### 7.1 结构

```
relay（绝对温度，tonic）
    │ [Bundle, frozen, gain=+1.0]
    ▼
PhasicRelayNeuron
    │ 膜电位 = relay - slow_relay（KCL 减法，通过兴奋+抑制两条 Bundle）
    │ ChannelConfig: v_threshold=0.01（整流）
    │
    │ [Bundle, frozen, gain=+1.0]
    ▼
spinal_turn_toward（脊髓中间神经元，0x01）
    │ [Bundle, plasticity=True, STDP, DA门控]
    ▼
motor_turn（主层 0x03，D2）
```
**两个确认点**：

兴奋和抑制两条Bundle都应为frozen——这是一个固定的信号处理电路，不参与学习。

PhasicRelayNeuron的膜电容和漏电阻应明确标注在三问中，这些参数决定了phasic信号的时间常数（即对多快的温度变化敏感），影响后续STDP的因果锁相窗口。


### 7.2 关键设计决策

| 决策 | 内容 |
| :--- | :--- |
| 信号源 | PhasicRelayNeuron（relay - slow_relay，KCL 实现）|
| 整流 | ChannelConfig v_threshold=0.01（正向通过）|
| 目标节点 | spinal_turn_toward（脊髓中间神经元）|
| STDP | 可塑，DA 门控来自 C1 |
| 生物依据 | 上丘感觉运动整合（Basso & May 2017）|

### 7.3 验收

| 检查项 | 通过条件 |
| :--- | :--- |
| 负债清理 | relay→yaw 束已删除 |
| PhasicRelayNeuron | KCL 正确实现，census 可见 |
| spinal_turn_toward | 在 census 中可见 |
| STDP 方向学习 | 靠近热源时方向选择性 LTP |
| 200k 验证 | d < 5.0，yaw 偏转 < 30°，停留 > 50k 步 |
| 与 P3 对比 | 优于 P3 基线（d=5.8，振荡 ±150°）|
| 回归测试 | 21/21 PASS |


## 八、实施检查清单

| 顺序 | 任务 | 依赖 | 状态 |
| :--- | :--- | :--- | :--- |
| 1 | B0：TemporalCoupler B-layer 诊断 | 无 | 待执行 |
| 2 | 200k 基线实验（含ν分布统计）| B0 完成 | 待执行 |
| 3a | B1a：HC-016 替换 | 200k 完成 | 待执行 |
| 3b | B1b：HC-023 替换 | 200k 完成 | 待执行 |
| 4 | C1：ν→DA/AGC 接线 | B1 完成 | 待执行 |
| 5 | 清理 relay→yaw 负债 | C1 完成 | D1 前 |
| 6 | D1：phasic_relay→spinal_turn_toward | C1 完成 | 待执行 |
| 7 | D2：spinal_turn_toward→motor_turn | D1 验证 | 待执行 |


## 九、成功标准

| 指标 | 目标 |
| :--- | :--- |
| 回归测试 | 全程 21/21 PASS |
| C1 后 DA 门控 | ν > 阈值时 DA 升高 |
| D1 方向学习 | 靠近热源时 STDP LTP 方向正确 |
| 200k 验证 | d < 5.0，yaw 偏转 < 30°，停留 > 50k 步 |
| 与 P3 对比 | 显著优于 DC 信号基线 |


## 十、与 V3.0-final 的对应关系

| 本方案 | V3.0-final | 说明 |
| :--- | :--- | :--- |
| B0 | P0a（TemporalCoupler B-layer）| 诊断 |
| 200k | — | 基线数据采集 |
| B1a | P3a（HC-016/023）| HC-016 部分 |
| B1b | P3a（HC-016/023）| HC-023 部分 |
| C1 | P0c（ν→DA 接线）| — |
| D1 | C1（phasic_relay→spinal_turn_toward）| 正确路径 |
| D2 | C2（spinal_turn_toward→motor_turn）| 本方案未含，D1 验证后推进 |


## 十一、当前状态

| 项目 | 状态 |
| :--- | :--- |
| 负债清理 | 延后至 D1 前 |
| 执行路径 | B0 → 200k → B1 → C1 → D1（已锁定）|
| 前置依赖 | C1 必须在 D1 之前 |
| P3 数据 | 保留，作为 D1 对照基线 |
| 当前阻塞 | 无——可立即开始 B0 |