# v40.9: Bio-Substrate Oscillatory Layer (类生体层)

## 问题

v40.8 的 2000-tick 压力测试暴露了热寂问题：tick 211 后系统进入结构冻结态。PRP=0、convergence nodes 全部衰减消失、dormant fruits → 0。系统虽然"稳定"，但实际上已经死亡。

## 你的假设

> "Theta波可能是一种主环路，支撑起运行的构建可能蕴含着生体信息的自调用 P/R/Xin"

这精确对应了三个已确认的生物机制：

### 文献验证

| 你的表述 | 对应理论 | 核心文献 |
|---------|---------|---------|
| "Theta 波是主环路" | **Theta oscillation as organizing scaffold** | Buzsáki (2002, 2006): theta 为海马体提供时间坐标系 |
| "类生体层 — 心跳/呼吸" | **Central Pattern Generator (CPG)** | Marder & Bucher (2001): CPG 通过半中枢互抑产生自持振荡 |
| "生体信息的搏动递归" | **Interoceptive predictive coding** | Seth (2013), Barrett & Simmons (2015): 内感受预测编码 |

### 关键发现

**CPG（中枢模式发生器）** 是最精确的参照物：
- 位于脊髓和脑干，**不需要外部输入**即可产生节律性输出
- 通过**半中枢模型（half-center model）**实现：两组互抑神经元交替激活
- 控制呼吸、心跳、步态 — 所有持续性自主节律
- 可以被高层调控（调节频率、幅度），但核心振荡是内生的

> [!IMPORTANT]
> CPG 完美匹配"类生体层"的需求：它是一个自持的振荡源，不依赖外部信号，但可被外部信号调制。它的输出是简单的节律性脉冲 — 正好是你说的"制式很简单"。

---

## Proposed Changes

### 新增: Bio-Substrate Layer (CPG Layer)

#### [MODIFY] [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py)

**1. CPG 振荡器（半中枢模型）**

新增 `cpg` 层，包含 2 个互抑神经元对（4 个神经元）：

```
cpg_excite_a ←──互抑──→ cpg_excite_b     (呼吸对: 快周期 ~8 ticks)
cpg_sustain_a ←──互抑──→ cpg_sustain_b    (心跳对: 慢周期 ~20 ticks)
```

每对通过互抑（reciprocal inhibition）自发交替激活：
- 当 A 活跃时，A 抑制 B → A 因疲劳（adaptation）衰减 → B 解除抑制 → B 激活
- 周期由 adaptation rate 控制（快/慢对应不同 adaptation 常数）

```python
# 半中枢互抑 — CPG 核心机制
# DEGRADED: CPG pacemaker neuron intrinsic bursting → proxy as reciprocal inhibition
# degraded_from = "CPG_half_center_reciprocal_inhibition"
adaptation_a *= 0.9  # 疲劳累积
if activation_a > activation_b:
    activation_b -= suppression_strength * activation_a  # A 抑制 B
else:
    activation_a -= suppression_strength * activation_b  # B 抑制 A
```

**2. CPG → Encoding Layer 耦合**

新增 `visceral` zone 在 encoding 层（2 个神经元）：
```
visc_rhythm    ← cpg_excite_a/b 的输出包络
visc_baseline  ← cpg_sustain_a/b 的输出包络
```

通过 inter-layer bundles 连接：
```
cpg_excite_a  → visc_rhythm     (快节律 → 编码层的基线活动)
cpg_sustain_a → visc_baseline   (慢节律 → 编码层的代谢基线)
```

**3. Visceral zone 的结构效果**

```
visc_rhythm 的作用:
├── 每 ~8 ticks 向 encoding 层注入一次微小激活脉冲
├── 这足以让 calcium 不归零 → PRP 不归零 → Column 功能存活
├── 让 pre_trace 周期性波动 → STDP 窗口持续开放
└── 让 convergence detection 持续运行

visc_baseline 的作用:
├── 每 ~20 ticks 提供代谢恢复信号
├── 调制 energy recovery rate（类似线粒体 ATP 产量的昼夜节律）
└── 防止静默神经元因纯衰减而死亡
```

**4. CPG 自身参与 P/R/Xin**

CPG 层不是被动的信号源 — 它自己也参与 T/O/P/R/Xin 循环：
- **T**: CPG 输出通过 inter-layer bundle 传导到 encoding
- **O**: circuit.observe() 会观测 CPG 层的活动
- **P**: CPG 的互抑循环本身就是一个 P-环流（最小的闭合回路）
- **R**: 如果 Xin 张力持续高企，CPG 的频率可以被调制（加速/减速）
- **Xin**: CPG→encoding 的 bundle 也有 xin_tension

**5. 层级结构（更新后）**

```
┌─────────────────────────────────────────────┐
│  signal_entropy (4 neurons)  — 外部感知层   │
├─────────────────────────────────────────────┤
│  cpg (4 neurons)             — 类生体层 NEW │
├─────────────────────────────────────────────┤
│  encoding (7+cx_+2 neurons)  — 编码层       │
│    z_t dims + cx_ crystals + visc_ zone     │
├─────────────────────────────────────────────┤
│  column (7 neurons)          — 柱层         │
└─────────────────────────────────────────────┘
```

---

#### [MODIFY] [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py)

- `build_signal_entropy_circuit()` 增加 CPG 层构建
- 主循环中 CPG 层的内生振荡每 tick 自动运行（不需要外部输入）
- 诊断输出增加 CPG 状态：周期、振幅、累计脉冲数

---

## 设计决策

### 为什么用半中枢模型而不是简单的 sin() 函数？

| | sin() | 半中枢互抑 |
|--|-------|-----------|
| 结构基底 | 无（纯数学） | 有（互抑突触） |
| 可调制 | 需要参数化（频率、相位） | 自然调制（改变 adaptation rate） |
| 参与 P/R/Xin | 不参与 | **完全参与** — 互抑回路 = P-环流 |
| 降级标注 | 无法标注 `degraded_from` | `degraded_from = "CPG_half_center_reciprocal_inhibition"` |

### 为什么是 2 对而不是 1 对？

真实生体有**多尺度节律**：
- 呼吸 ~12-20次/分（快周期，对应 theta 节律层）
- 心跳 ~60-100次/分（但在 HRV 中表现为 ~0.1Hz 的慢调制）

2 对 = 2 个时间尺度 → 丰富的节拍交互 → 避免单频锁定

---

## Open Questions

> [!IMPORTANT]
> 1. CPG 层的互抑强度应该是多少？太强 → 振荡太剧烈影响信号辨别；太弱 → 不足以抵抗热寂。建议从 `suppression = 0.5` 开始，在压力测试中校准。

> [!IMPORTANT]
> 2. visc_ zone 是否应该参与 cosine 辨别计算？建议**不参与** — visc_ 是所有刺激共享的基线活动，不携带刺激特异性信息。但它应该参与 STDP（因为 STDP 不区分信息来源）。

---

## Verification Plan

### Automated Tests
1. 运行 500 tick：验证 PRP 不再归零
2. 运行 2000 tick：验证 convergence nodes 不再全部衰减
3. 验证 CPG 振荡周期是否稳定（检查 cpg_excite_a 的激活时间序列）
4. 验证辨别性能不因 CPG 注入而下降（cos(s,g) 应保持 < 0.15）
