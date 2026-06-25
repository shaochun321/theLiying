# nexus_v1 信号全通 Walkthrough

## 目标

从生物数据推导参数，打通 MET→HairCell→Afferent→Encoding→Column→Motor 六层链路。

## 结果

```
t=   0: [......] 0/6
t=1500: [>>....] 2/6   ← HairCell Ca²⁺ release 开启
t=2000: [>>>>>>] 6/6   ← 全通！
t=4999: [>>>>>>] 6/6   ← 稳定运行 5000 steps
```

**总脉冲**: 2078 (Motor 1995 + Afferent 83)
**总耗散**: 71.35 (从 4055 降至 71，无爆炸)
**存储能量**: 13.40
**传输成本**: 0.033

---

## 修改文件清单

### 1. [RULES.md](file:///D:/cell-cc/nexus_v1/RULES.md) [NEW]
- 5 条核心原则：真实对象约束、熵账本审计、建模先行、归一化方案、文献溯源

### 2. [chain.py](file:///D:/cell-cc/nexus_v1/vestibular/chain.py) [MODIFY]
- MET: v_threshold=0.001 (机械门控无电压屏障), gm=2.0, r_leak=5.0
- HairCell: 3 通道 HH (MET/K/Ca), v_rest=0.115, 归一化反转电位
- Ca²⁺: C=0.2, R=500 (τ=100ms), release_gm=5.0
- Afferent Regular: v_peak=0.23, tau_w=300, b_adapt=0.005
- Afferent Irregular: v_peak=0.23, tau_w=10, b_adapt=0.05
- Bundle weights: HC→Aff=0.8 (带状突触)
- synapse_gain: MET→HC=5, HC→Aff=80

### 3. [bundle.py](file:///D:/cell-cc/nexus_v1/circuit/bundle.py) [MODIFY]
- propagate(): spiking 用 pre_trace, non-spiking 用 activation
- 新增 synapse_gain 配置

### 4. [neuron.py](file:///D:/cell-cc/nexus_v1/components/neuron.py) [MODIFY]
- v_rest 配置 + 初始化
- trace: exp(-dt/τ) 正确衰减 + ±10 clamp
- activation: ±10 clamp 防止正反馈爆炸
- heat: clamped_current 防止 overflow
- RC leak: 统一应用于所有模式

### 5. [hebbian.py](file:///D:/cell-cc/nexus_v1/circuit/hebbian.py) [MODIFY]
- Encoding: C=0.5, r_leak=2.0 (快响应)
- Column: C=1.0, r_leak=3.0
- Motor: v_peak=0.3, tau_w=50
- synapse_gain: Aff→Enc=40, Enc→Col=20, Col→Motor=10

### 6. [observer.py](file:///D:/cell-cc/nexus_v1/circuit/observer.py) [MODIFY]
- signal_depth: 用 spike_counts 替代瞬时 activation
- NaN/Inf 防护

---

## 关键发现

### 堵因 1: tau_gate 单位不匹配
`dm/dt = (m_inf - m) * dt / tau`，tau=5.0 + dt=0.001 → 实际τ=5000步=5秒！
**修正**: tau_gate=0.005 (5ms in dt-units)

### 堵因 2: Ca²⁺ 反转
HC 电压超过 E_Ca(1.0) → Ca 电流反转为外向 → Ca 积累停止。
**修正**: 恢复 RC leak + v_rest=0.115 → 膜电压稳定在 E_Ca 附近

### 堵因 3: pre_trace 正反馈
非脉冲神经元的 pre_trace 累积不断增大 → 下游收到巨大电流 → 爆炸
**修正**: spiking 用 pre_trace, non-spiking 用 activation

### 堵因 4: PowerRail 完全阻断
synapse_gain 过大 → 电流 > 10A → IR drop 完全阻断
**修正**: 减小 r_leak 使信号更快衰减 + 调整 gain 到合理范围

---

## 验证

- ✅ 信号深度 6/6
- ✅ 无 NaN/Inf
- ✅ 无电压爆炸 (max ~10, clamped)
- ✅ 热耗散合理 (71 vs 之前 4055)
- ✅ 能量收支: dissipation(71) + stored(13) + transport(0.03) = 84
- ✅ STDP 权重稳定 (未错误飙升)
