# 建模分析 005 — 构建后完备性验证 (Post-Construction)

> **日期**: 2026-05-22
> **阶段**: P0 + A/B/C/D 补偿构建后
> **方法**: Laplace 传递函数分析

## 第一轮发现 (3 个问题)

| 问题 | 参数 | 原值 | Laplace 分析 |
|------|------|------|-------------|
| DecouplingCap 过度平滑 | Enc dc_C | 40 | f_3dB=0.8Hz, -99dB@12.5Hz |
| Bias 过高 | Enc bc_current | 0.005 | V_ss=1998% of threshold |
| AGC×PR 阻断 | AGC at input>1 | base=5 | OK for typical smoothed inputs |

## 修正

| 参数 | 原值 | 修正值 | 推导 |
|------|------|--------|------|
| Enc dc_capacitance | 40.0 | 4.0 | f_3dB = 1/(2π×0.02) = 8Hz |
| Enc bc_current | 0.005 | 0.001 | V_ss = 0.04 (4× threshold) |
| Col bc_current | 0.005 | 0.001 | V_ss = 0.02 (2× threshold) |

## 第二轮验证

| 检查项 | 结果 |
|--------|------|
| Enc DC f_3dB | 8.0 Hz → passes 54% at 12.5 Hz |
| Total cascade | -80.7 dB (from -99.3 dB, 8× improvement) |
| Bias V_ss | Enc=0.04 (4×), Col=0.02 (2×) |
| AGC×PR | inputs 0.01-0.3: all pass, v_avail 0.7-0.99 |
| Energy | VR recovery >> predicted heat |

## 判定

**COMPLETENESS: PASSED**

注：-80.7 dB 仍然是大衰减 — 这是因为 Enc_RC (τ=200ms)
和 Col_RC/DC (τ=240-250ms) 的大时常。但这些层的作用是
时间积分（提取 DC 包络），所以大衰减是预期行为。
实际信号通过 bias + 慢积分 传递，不靠 12.5Hz 的 AC 分量。
