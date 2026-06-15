# nexus_v1 降级追踪注册表 (Degradation Registry)

> **格式说明**: 见 RULES.md 原则 6

---

### DEG-001: MET 信号无法到达 HairCell (信号深度 1/6)
- **发现时间**: 2026-05-21
- **现象**: MET activation > 0, haircell activation = 0, signal_depth = 1/6
- **影响层**: HairCell, Afferent, Encoding, Column, Motor (全链路)
- **根因**: 多重因素:
  - tau_gate 单位不匹配 (5.0 实际 = 5000 steps)
  - Ca²⁺ 反转电位问题 (vm > E_Ca 后电流反转)
  - pre_trace 正反馈爆炸
- **状态**: FIXED
- **修复**: FIX-001, FIX-002, FIX-003, FIX-004

---

### DEG-002: 能量耗竭导致链路中断
- **发现时间**: 2026-05-22
- **现象**: 所有神经元 energy → 0.001，信号深度在 6/6 ↔ 4/6 振荡
- **影响层**: Column (主要), Motor, Encoding
- **根因**: metabolic_recovery (0.001) << 平均耗散 (30.32)，亏缺比 30322:1
- **状态**: FIXED (Encoding/Column), PARTIAL (Motor)
- **修复**: FIX-006 (P0 + VoltageRegulator)
- **备注**: Encoding energy 从 0.001 恢复到 12.0; Motor 仍耗尽 → DEG-009

---

### DEG-003: Column 电压跳变 (0 ↔ 6)
- **发现时间**: 2026-05-22
- **现象**: Column activation 在 0 和 ~6 之间跳变而非平滑
- **影响层**: Column → Motor
- **根因**: τ_RC(Column) = 3 ms << ISI(Afferent) = 80 ms；
  两次脉冲之间完全衰减（保留率 0%）
- **数学证明**: e^(-80/3) ≈ 2.7 × 10^{-12} ≈ 0
- **状态**: FIXED
- **修复**: FIX-006 (P0: τ_RC 增至 240ms, 保留率 72%)
- **验证**: Column activation 稳定在 10.98，不再跳变

---

### DEG-004: 传入放电率偏低
- **发现时间**: 2026-05-22
- **现象**: Regular afferent 12.5 Hz，生物目标 50-100 Hz
- **影响层**: Afferent → Encoding (信号驱动不足)
- **根因**: HC release_rate ≈ 0.01，HC→Aff synapse_gain = 80，
  导致充电速率 dV/dt = 0.048 × 80 × 0.001 / 0.5 = 0.0077/step。
  ISI = V_span / dV = (0.23 - 0.077) / 0.0077 ≈ 20 steps (50 Hz)。
  实测 80 steps 因为 release_rate 不稳定。
- **状态**: OPEN
- **修复**: 待分析

---

### DEG-005: Motor 放电过快
- **发现时间**: 2026-05-22
- **现象**: Motor 665 spikes / 3500 ms ≈ 190 Hz，生物最大约 200 Hz
- **影响层**: Motor
- **根因**: 下游增益链过强 (Enc→Col→Motor 多级放大)
- **状态**: SUPERSEDED by DEG-008
- **修复**: 补偿机制改变了行为模式

---

### DEG-006: NaN 在 Encoding 层传播
- **发现时间**: 2026-05-21
- **现象**: Encoding activation 爆炸到 10^255 → NaN
- **影响层**: Encoding → Column → Motor
- **根因**: MOSFET conduct(vm) 在高 vm 下线性增长无上限
- **状态**: FIXED
- **修复**: FIX-005 (activation clamp ±10)

---

### DEG-007: STDP 权重不演化
- **发现时间**: 2026-05-22
- **现象**: HC→Aff 权重 0.8000 不变, Enc→Col 权重 0.1500 不变
- **影响层**: 全链路 (学习不发生)
- **根因**: 待分析 — 可能是 pre_trace/post_trace 衰减过快
  或 stdp_lr 过小相对于 trace 幅度
- **状态**: OPEN
- **修复**: 待分析

---

### DEG-008: Motor 偏置自发放电过多
- **发现时间**: 2026-05-22
- **现象**: Motor 375/458 脉冲 (82%) 来自偏置电流驱动的自发放电，
  不是信号驱动。在传入信号到达前 (t<1500) 就已产生 375 spikes。
- **影响层**: Motor
- **根因**: bc_current=0.01 对 Motor (C=1, R=5) 过大，
  V_ss = 0.01/0.5 × 5 = 0.1，接近 v_peak=0.3 的 33%。
  加上 AGC base_gain=5 × bias 被放大。
- **状态**: OPEN
- **修复**: 待分析 — 可降低 Motor bc_current 或关闭 Motor AGC

---

### DEG-009: Motor energy 仍耗尽
- **发现时间**: 2026-05-22
- **现象**: Motor energy = 0.003 (几乎归零)
- **影响层**: Motor
- **根因**: 多重因素:
  1. Motor VR max_rate=3.0 不足以覆盖高频 spiking 耗散
  2. Binding layer activation 指数爆炸 (DEG-013) → heat=1000
- **状态**: FIXED
- **修复**: FIX-014 (VR 重校准 + 稳态调节), FIX-015 (Binding 饱和)

---

### DEG-010: 热耗散偏高
- **发现时间**: 2026-05-22
- **现象**: 总热耗散 1180 (主要来自偏置驱动的无信号放电)
- **影响层**: 全系统
- **根因**: 补偿机制增加了活跃神经元数 (19-20)，每个都在消耗能量
- **状态**: OPEN
- **修复**: 待分析 — 可能是正常代价

---

### DEG-011: MET 能量耗尽
- **发现时间**: 2026-05-22 (契约验证发现)
- **现象**: MET energy = 0.001 (C1 契约要求 > 0.5)
- **影响层**: MET
- **根因**: MET 无 VoltageRegulator，固定 metabolic_recovery=0.001
- **契约**: C1 energy > 0.5 → 违约
- **状态**: OPEN
- **修复**: 待分析 — 需要为 vestibular 层也加 VR

---

### DEG-012: HairCell 能量耗尽
- **发现时间**: 2026-05-22 (契约验证发现)
- **现象**: HC energy = 0.001 (C2 契约要求 > 0.5)
- **影响层**: HairCell
- **根因**: HC 无 VoltageRegulator，固定 metabolic_recovery=0.001
- **契约**: C2 energy > 0.5 → 违约
- **状态**: OPEN
- **修复**: 待分析 — 与 DEG-011 同根因，需扩展 VR 到 vestibular 层

---

### DEG-013: Binding layer activation 指数爆炸
- **发现时间**: 2026-05-23
- **现象**: BindingCell activation 从 53 → 8717+ (t=9500)，Motor heat=1000 (clamped)
- **影响层**: Binding → Motor
- **根因**: BindingCell.compute() 使用乘积式 Π ReLU((a-θ)/θ)，
  col_act=0.41, θ=0.05 → normalized=7.2, product=7.2²=52。
  随 col_act 增长，product 以 O(a^n) 速率爆炸，无饱和限制。
  爆炸的 activation 通过 mot._membrane.inject() 绕过 PowerRail
  直接注入 Motor 膜 → heat = (100)² × 0.1 = 1000 (clamped at 100)
- **状态**: FIXED
- **修复**: FIX-015

---

### DEG-014: Motor spike 永久抑制
- **发现时间**: 2026-05-23
- **现象**: Motor 在 18 次 spike 后永久静默, V_mem → -0.83
- **影响层**: Motor
- **根因**: 双重因素:
  1. tau_w=50s → w_adapt=0.35 几乎不衰减 (ε=0.99998/step)
  2. col_to_motor synapse_gain=10, 6 col sources → scaled=31 >> PowerRail max=10
     → v_avail=0, 正向注入为零, 仅剩 w_adapt 负注入 → V 不可逆下降
- **状态**: FIXED
- **修复**: FIX-016

