# Spike-Before-Leak 时序审计 (#6)

## 当前操作顺序

```
Neuron.step():
  1. Input injection (bias + D2 + AGC → membrane.inject)
  2. Multi-channel currents (Na/K/Ca → membrane.inject(-i_total))
  3. Spike detection (BEFORE leak ✅)
     a. Adaptation current inject (-w_adapt)
     b. Fatigue hyperpolarizing current
     c. if V_m > v_peak → spike! → reset
  4. Membrane leak (RC discharge → rest)
  5. Ca²⁺ subsystem
  6. Traces + metabolism
```

## 生物一致性验证

| 步骤 | 生物过程 | 时间尺度 | 当前顺序 | 正确？ |
|---|---|---|---|---|
| Input inject | 突触后电位 (EPSP/IPSP) | ~0.5-2ms | 1st | ✅ |
| Channel currents | 离子通道门控电流 | ~0.1-1ms | 2nd | ✅ |
| Adaptation | 慢K⁺电流 (SFA) | ~10-100ms | 3a | ✅ |
| Fatigue | Ca²⁺-K⁺ (AHP) | ~50-200ms | 3b | ✅ |
| Spike check | Na⁺ 通道激活 | ~0.1ms | 3c | ✅ |
| Leak | 被动 RC 放电 | ~1-50ms | 4th | ✅ |

## 结论

**顺序已正确**。关键设计决策：

1. **Spike BEFORE leak** — 防止 dt >> τ_RC 时信号被 leak 消灭后再检测
2. **Fatigue BEFORE spike** — 防止疲劳神经元仍然 spike
3. **Adaptation BEFORE spike** — 适应电流降低 Vm，减少 spike 概率
4. **Channels BEFORE spike** — 离子电流先修改 Vm，然后检测阈值

无需修改。
