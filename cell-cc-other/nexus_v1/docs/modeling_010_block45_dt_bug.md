# 建模分析 010 — Block 4/5 诊断 + dt Bug 发现

> **日期**: 2026-05-22
> **阶段**: Block 4 (Aff CV) + Block 5 (Motor signal chain)

## 严重 Bug 发现: dt 未传播 (FIX-009)

### 问题

`bundle.apply_to_targets(currents)` 调用 `tgt.step(current)` 时
**没有传递 dt 参数**，导致 dt 默认为 1.0（系统用 0.001）。

### 影响

所有通过 bundle 传播的神经元 (Encoding, Column, Motor) 使用了
错误的 dt=1.0，意味着：
- 注入: ΔV = I × 1.0 / C (应为 I × 0.001 / C) → 1000x 过大
- 泄漏: exp(-1.0/τ) 远大于 exp(-0.001/τ) → 1000x 过快
- 两者部分抵消，但时间常数行为完全错误

### 修复后影响

1. **Motor silence: PASS** (124 → 0 噪声脉冲)
2. **Motor energy: PASS** (0.001 → 1.0)
3. **Enc activation: 接近 0** — AGC×PowerRail 阻断
4. 需要移除 AGC 并调整 synapse_gain

## AGC×PowerRail 阻断

修复 dt 后，Aff spike 在 Enc 处的路径：
```
Aff=1.0 → G(0.2)=0.125 → gain=40 → I=4.99
→ /inertia(0.5) = 9.97 → ×AGC(5) = 49.9
→ PowerRail: 1.0 - 49.9×0.1 = -3.99 → 0 = BLOCKED
```

### 解决

- 移除 Enc/Col AGC
- synapse_gain: Aff→Enc 40→10, Enc→Col 20→5
- 推导: scaled=1.25/0.5=2.5, v_ratio=0.75, dV/spike=0.000188

## Aff CV = 0.509

诊断发现 Aff 在 t=5000 后完全停止放电（不是 CV 问题，是放电终止）。
Ca ramp-up 阶段的 ISI 变异造成高 CV。需更长模拟确认稳态行为。
