# 并行分析结论与下一步方案

## 发现

互信息分析揭示了**信号链中两个瓶颈点**：

```
MET ─(76%)─▶ HC_vm ─(82%)─▶ Ca ─(100%)─▶ Release ─(0.5%)─▶ Aff ─(4.4%)─▶ Enc ─(35%)─▶ Col
                                               ▲                      ▲
                                          瓶颈 1                  瓶颈 2
```

### 瓶颈 1: Release → Aff (MI = 0.5%)

**原因**: HairCell Ca²⁺ **饱和在释放态** — Ca 100% 时间 > threshold。

HC 电压达到 3.065（远超 E_Ca=1.0），Ca 从不回落到阈值以下，
所以 release_rate ≈ 常数 0.015。这变成了一个 **DC 偏置**，
不携带任何信号调制信息。Aff 只是被恒定电流慢慢充电。

> [!IMPORTANT]
> **HC 应该产生 phasic (相位性) 响应** — 信号变化时 release 增加，
> 稳态时 release 下降。当前是 tonic 饱和。

**可能的修复方向**：
1. 增大 Ca 衰减速率（减小 Ca_R 或 Ca_C），让 Ca 有动态范围
2. 提高 Ca release threshold，让 release 不是一直 on
3. 加入 Ca-dependent K 通道（BK），产生适应性

### 瓶颈 2: Aff → Enc (MI = 4.4%)

**原因**: Aff 是 spiking (输出 0/1)，Enc 有 DecouplingCap（τ=20ms 平滑）。
两个信号的统计结构完全不同 → 互信息低。

**可能的修复方向**：
1. 这可能不是问题 — DecouplingCap 的目的就是将 spike train 转化为 rate code
2. 需要更长的观测窗口才能看到 MI 效果

### 线 B 新发现: Motor 信号驱动为零

去掉 Motor bias 后，Motor **完全不收到信号驱动的脉冲**。
原因链: Column energy 也耗尽 (0.001) → Column 无法驱动 Motor。

> [!WARNING]
> Column 的 VR activity_coeff=0.5 不够覆盖 Column 的耗散。
> 需要检查 Column 的实际耗散率并调整 VR 参数。

## 建议的下一步

| 优先级 | 目标 | 方法 |
|--------|------|------|
| **P0** | **HC Ca²⁺ 去饱和** | 减小 Ca_C/Ca_R 或提高 threshold |
| P1 | Column VR 参数 | 匹配 Column 实际耗散率 |
| P2 | 瓶颈 2 评估 | 确认是预期行为还是需要修复 |
