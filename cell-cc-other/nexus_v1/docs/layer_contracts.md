# nexus_v1 层接口契约 (Layer Interface Contracts)

> **格式说明**: 见 RULES.md 原则 10
> **日期**: 2026-05-22
> **基线**: modeling_007 互信息分析数据

---

## 契约总览

```
MET ──▶ HairCell ──▶ Afferent ──▶ Encoding ──▶ Column ──▶ Motor
 C1       C2          C3           C4           C5         C6
```

---

### C1: MET (机械电转换)
- **输出类型**: continuous (activation)
- **输出范围**: [0.0, 5.0]
- **动态范围**: ≥ 5:1 (激活 vs 静息)
- **能量**: > 0.5
- **响应时间**: < 5 ms (快速机械通道)
- **当前实测**: activation = 4.85 (OK)

### C2: HairCell (毛细胞)
- **输出类型**: continuous (release_rate)
- **输出范围**: [0.001, 0.5]
- **动态范围**: ≥ 10:1 (信号调制深度)
- **能量**: > 0.5
- **Ca²⁺ 动态**: Ca 应有 phasic 响应 (不能恒定)
- **互信息**: MI(MET_input, release_output) ≥ 1.0 bit
- **当前实测**: release = 0.014-0.016 → 动态范围 1.15:1 → **违约!**
- **违约原因**: Ca²⁺ 饱和 → DEG-004

### C3: Afferent (传入神经)
- **输出类型**: spiking
- **频率范围**: [20, 100] Hz (Regular), [10, 300] Hz (Irregular)
- **CV**: Regular ≤ 0.2, Irregular ≥ 0.4
- **能量**: > 0.5
- **互信息**: MI(release_input, spike_output) ≥ 0.5 bit
- **当前实测**: 12.5 Hz, CV=0.111 → 频率 **违约!** (< 20 Hz)
- **违约原因**: 上游 C2 违约 (release 太低)

### C4: Encoding (编码层)
- **输出类型**: continuous (activation, smoothed by DecouplingCap)
- **输出范围**: [0.1, 10.0]
- **动态范围**: ≥ 5:1
- **能量**: > 0.1
- **互信息**: MI(spike_input, activation_output) ≥ 0.3 bit
- **当前实测**: activation = 15-20 → 范围上限超 → 边界警告
- **能量**: 1.0 (OK)

### C5: Column (柱层)
- **输出类型**: continuous (activation, integrated)
- **输出范围**: [0.05, 10.0]
- **动态范围**: ≥ 3:1 (积分层允许较窄)
- **能量**: > 0.1
- **当前实测**: activation = 10.98 → OK (但 energy=0.001 → **违约!**)
- **违约原因**: VR 恢复 < 耗散 → DEG-002 (partial)

### C6: Motor (运动层)
- **输出类型**: spiking
- **频率范围**: [0, 200] Hz (静息时不放电)
- **静息约束**: 无输入时 = 0 Hz (不自发放电)
- **能量**: > 0.1
- **信噪比**: ≥ 5:1 (信号 vs 噪声脉冲)
- **当前实测**: 124 spikes, 全为噪声, SNR=0 → **违约!**
- **违约原因**: 上游 C5 能量耗尽 → 无信号驱动

---

## 契约违约清单 (当前)

| 层 | 契约 | 违约项 | 关联 DEG | 根因 |
|----|------|--------|---------|------|
| C2 HairCell | 动态范围 ≥ 10:1 | 实际 1.15:1 | DEG-004 | Ca²⁺ 饱和 |
| C3 Afferent | 频率 ≥ 20 Hz | 实际 12.5 Hz | DEG-004 | C2 违约传播 |
| C5 Column | energy > 0.1 | 实际 0.001 | DEG-002 | VR 不足 |
| C6 Motor | SNR ≥ 5:1 | 实际 0 | DEG-008 | C5 违约传播 |

## 级联分析

```
C2 违约 (Ca饱和) ──▶ C3 违约 (频率低) ──▶ C4 边界 ──▶ C5 违约 (能量) ──▶ C6 违约 (SNR=0)
 ▲                                                        ▲
 根因 1                                                   根因 2 (独立)
```

**根因 1**: C2 HairCell Ca²⁺ 饱和 → 修复此处可同时解决 C2, C3
**根因 2**: C5 Column 能量不足 → 独立于 C2，需单独修复 VR 参数

**预测**: 修复 C2 后，C3 自动恢复契约（如果 release 范围正确，
Afferent 频率会提升到契约范围）。C6 需要 C5 和 C2 都修复后才恢复。
