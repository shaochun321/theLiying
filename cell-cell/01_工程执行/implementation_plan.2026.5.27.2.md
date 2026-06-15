# M4: `.activation` 全量审计 — 每个消费者需要什么物理量

## activation 的三种物理定义

| 代码位置 | 赋值 | S0 物理量 | 单位类比 |
|----------|------|-----------|----------|
| neuron.py L351 | `gated_conduct(Vm)` | MOSFET 输出电流 I_ds | 安培 |
| neuron.py L379 | `Vm` | 膜电容电压 | 伏特 |
| neuron.py L456 | `1 if spike else 0` | 比较器数字输出 | 逻辑电平 |

**三种不同物理量塞进同一个字段 — 这是 bug 的根源。**

---

## 逐条审计：40 个消费者

### 1. bundle.py — 突触传递 & 学习

| 行 | 代码 | 实际需要 | 当前取值 | 问题 |
|----|------|----------|----------|------|
| L140 | `a_src = src.activation` (propagate) | **I_out** — 驱动下游膜电流 | 非脉冲用 I, 脉冲用 pre_trace ✓ | L137 已区分，**无 bug** |
| L235-236 | `abs(tgt/src.activation)` (BCM learn) | **\|I_out\|** — 突触后电流强度 | 脉冲={0,1} | ⚠ 脉冲时 BCM 无意义（全0或全1） |
| L258-259 | `abs(src/tgt.activation)` (hebbian_decay) | **\|I_out\|** — 相关性度量 | 同上 | ⚠ 同上（但 L4→L5 是脉冲→脉冲） |
| L320 | `abs(tgt.activation)` (Xin predict) | **\|I_out\|** — 预测目标 | 脉冲={0,1} | ⚠ Xin 预测对脉冲无连续梯度 |
| L328 | `abs(src.activation)` (Xin prev) | **\|I_out\|** — 上步源强度 | 同上 | ⚠ 同上 |

### 2. circulation.py — 环流计量

| 行 | 代码 | 实际需要 | 当前取值 | 问题 |
|----|------|----------|----------|------|
| L127 | `cell.activation < 0.01` | **Vm** — binding cell 活跃度 | BindingCell.activation（连续） | ✓ 无 bug |
| L143 | `column_neurons[axis].activation` | **Vm** — 膜电压用于 δa | 脉冲={0,1} | ⚠ col 是脉冲神经元，δa 无连续值 |
| L159 | `cell.activation` | **Vm** — binding 连续强度 | BindingCell（连续） | ✓ |
| L349 | `neuron.activation` (baseline) | **Vm** — 跟踪基线 | 脉冲={0,1} | ⚠ 脉冲基线 EMA 趋近 spike_rate |

### 3. variant_adapter.py — 主回路

| 行 | 代码 | 实际需要 | 当前取值 | 问题 |
|----|------|----------|----------|------|
| L343-347 | `mot.activation` (motor→muscle) | **I_out** — 连续力驱动 | 脉冲={0,1} | ⚠ **严重**：肌肉收到二值信号 |
| L444 | `enc.activation` (damper) | **Vm** — 阻尼判据 | 脉冲={0,1} | ⚠ 脉冲时阻尼要么0要么满 |
| L454 | `col.activation` (damper) | **Vm** | 脉冲={0,1} | ⚠ 同上 |
| L478 | `col.activation` (WTA inhibition) | **Vm** — 连续竞争 | 脉冲={0,1} | ⚠ WTA 全是二值比较 |
| L485 | `col.activation = max(0, ...)` | **直接写 Vm** | 写入 activation 字段 | ⚠ **写入覆盖了 step() 的计算** |
| L489 | `col.activation` (binding input) | **Vm** — 连续跨模态 | 脉冲={0,1} | ⚠ binding 收到二值 |
| L516 | `enc.activation` (Xin detect) | **\|Vm\|** — 活跃度 | 脉冲={0,1} | ⚠ |
| L518 | `col.activation` (Xin detect) | **\|Vm\|** | 脉冲={0,1} | ⚠ |
| L572 | `col.activation` (DA inject) | **\|Vm\|** — 调制比例 | 脉冲={0,1} | ⚠ DA 注入全开或全关 |
| L591 | `mot.activation > 0.5` | **spike** — 放电检测 | 脉冲={0,1} | ✓ 正好需要二值 |
| L610 | `n.activation` (maturation Φ) | **\|Vm\|** — 活跃度累积 | 混合 | ⚠ 脉冲时 Φ 只在 spike 步+1 |
| L744 | `n.activation` (total activity) | **\|Vm\|** — 总活跃度 | 混合 | ⚠ |

### 4. 其他文件

| 文件:行 | 实际需要 | 问题 |
|---------|----------|------|
| observer.py L148 | 记录用，无物理要求 | ✓ |
| observer.py L191 | \|Vm\| 统计 | ⚠ |
| hebbian.py L806 | 记录用 | ✓ |
| entropy_ledger.py L144 | \|Vm\| 统计 | ⚠ |
| shadow_sandbox.py L379 | \|Vm\| 统计 | ✓ shadow 全非脉冲 |
| shadow_sandbox.py L597,605 | Vm 基线 | ✓ shadow 全非脉冲 |
| neuron.py L419 | release_rate 代理 | ⚠ 非脉冲时 = \|Vm\|，概念混淆 |
| neuron.py L466-475 | trace 计算 | 部分 ✓ (L467 已区分 spiking) |
| neuron.py L480 | EMA | ⚠ 脉冲时 EMA 是 spike_rate |
| neuron.py L496 | VR activity | ✓ 已区分 spiking |
| neuron.py L513 | AGC | ⚠ 混合输入 |

---

## 诊断总结

### 无 bug（8 处）
- bundle L140：已用 pre_trace 区分脉冲
- circulation L127, L159：BindingCell 是连续的
- variant_adapter L591：正好需要 spike
- observer, hebbian（记录用）
- shadow_sandbox（全非脉冲）
- neuron L496 VR（已区分）

### 有 bug（17 处）
全部是同一类问题：**消费者期望连续 Vm，但脉冲神经元给出 {0,1}**

最严重的 4 处：

> [!CAUTION]
> 1. **L343-347 motor→muscle**: 肌肉收到 {0,1} 脉冲信号作为力的驱动，导致力的产生是全有或全无。应该用 `_activation_ema`（放电率）或 `_membrane.voltage`。
> 2. **L485 WTA 直接写 activation**: 覆盖了 step() 的计算结果。应该写 `_membrane.charge`。
> 3. **L478 WTA 读 activation**: 二值比较无法区分"强烈放电"和"刚好放电"。应该用 `_activation_ema`。
> 4. **L572 DA inject**: DA 调制全开全关。应该用 `_activation_ema`。

## Open Questions

> [!IMPORTANT]
> 1. **根本决策**: 是否完全删除 `activation` 字段？改为消费者直接读 `_membrane.voltage` / `_activation_ema` / `_spiked_this_step`？
> 2. **motor→muscle**: 用 `_activation_ema`（放电率，平滑但延迟）还是 `_membrane.voltage`（瞬时但 spike 间低）？
> 3. **L485 WTA 写入**: 改为操作 `_membrane.charge` 还是 `_membrane.inject(-inhibition, dt)`？
