# 补偿机制完备性分析 (Completeness Analysis)

> **日期**: 2026-05-22
> **阶段**: 补偿组件构建后、测试/调参前
> **遵循**: RULES.md 原则 9 (Completeness Before Tuning)

---

## 组件清单与类型标注

| 组件 | TYPE | 文件 | 生物对标 | 半导体对标 |
|------|------|------|---------|-----------|
| VoltageRegulator | TYPE:SEMI | compensation.py | 线粒体ATP | LDO稳压器 |
| DecouplingCapacitor | TYPE:SEMI | compensation.py | 树突电容 | 去耦电容 |
| BiasCurrentSource | TYPE:SEMI | compensation.py | 张力放电 | 恒流源 |
| AutomaticGainControl | TYPE:SEMI | compensation.py | 稳态可塑性 | AGC环路 |

## 四项审查结果

### a. I/O 端口连接

| 组件 | 输入来源 | 输出去向 | 状态 |
|------|---------|---------|------|
| VoltageRegulator | Neuron.activation | Neuron.energy += recovery | OK |
| DecouplingCapacitor | PowerRail output (injected) | Capacitor.inject() | OK |
| BiasCurrentSource | 无 (常量) | total_input += i_bias | OK |
| AGC | Neuron.activation | scaled_current *= gain | OK |

### b. 能量收支

| 组件 | 收支状态 | 问题 |
|------|---------|------|
| VoltageRegulator | max_recovery=5.0 < Column mean_heat=30.32 | P0 先降热量 |
| DecouplingCapacitor | τ/ISI = 2.50 ≥ 2.0 | OK |
| BiasCurrentSource | bias = 50% threshold | OK |
| AGC | base_gain=20 → PowerRail 阻断 | 降至 ≤5.0 |

### c. 时间常数匹配

```
DecouplingCapacitor τ = 200 ms >> ISI = 80 ms → OK
AGC τ = 100 ms (UNGROUNDED: biology = hours-days)
VoltageRegulator: instantaneous
BiasCurrentSource: constant
```

### d. 边界条件

| 组件 | NaN/Inf | 负值 | 极值 |
|------|---------|------|------|
| VoltageRegulator | OK (abs + clamp) | OK | Capped at max_rate |
| DecouplingCapacitor | OK | OK | 大输入仍有限 |
| BiasCurrentSource | N/A | N/A | enabled=False → 0 |
| AGC | OK | OK | activity→∞ → gain→0 |

## 判定

**2 个问题，均可解决**:

1. VR max_recovery < Column heat → 需先执行 P0 (增大 τ_RC) 降低热耗散
2. AGC base_gain=20 与 PowerRail R_supply=0.1 冲突 → 降至 ≤5.0

**实施顺序**:
```
Step 1: P0 — 增大 Encoding/Column 的 τ_RC (降低耗散 ~100×)
Step 2: 启用 A/B/C/D 全部补偿
Step 3: 熵审计验证
```

**不推荐**: 未执行 P0 就启用补偿 → VR 无法闭合 Column 能量缺口
