# nexus_v1 修复记录注册表 (Fix Registry)

> **格式说明**: 见 RULES.md 原则 8

---

### FIX-001: tau_gate 单位修正
- **日期**: 2026-05-21
- **关联降级**: DEG-001
- **修改文件**: `vestibular/chain.py`
- **修改内容**: K通道 tau_gate: 5.0 → 0.005; Ca通道 tau_gate: 1.0 → 0.001
- **推导依据**: `dm/dt = (m_inf - m) * dt / tau`; dt=0.001 时 tau=5ms 应为 0.005
- **验证**: K gate 在 t=1200 达到 0.81 (之前 0.04)
- **副作用**: 无

---

### FIX-002: MET 通道机械门控
- **日期**: 2026-05-21
- **关联降级**: DEG-001
- **修改文件**: `vestibular/chain.py`
- **修改内容**: MET v_threshold: 0.05 → 0.001; gm: 1.0 → 2.0
- **推导依据**: MET 通道由机械力开启非电压门控，v_threshold 应接近零
  REF: Fettiplace & Kim 2014
- **验证**: MET activation 0.97 at t=999 (之前 0.0007)
- **副作用**: 无

---

### FIX-003: 非脉冲神经元用 activation 传播
- **日期**: 2026-05-21
- **关联降级**: DEG-001 (pre_trace 正反馈)
- **修改文件**: `circuit/bundle.py`
- **修改内容**: propagate() 对 spiking 用 pre_trace, non-spiking 用 activation
- **推导依据**: non-spiking 神经元输出连续, 不需要 EPSP 时间展宽;
  pre_trace 在 non-spiking 下无限积累导致正反馈爆炸
- **验证**: HC→Aff 电流从 ~4.8 降至 ~0.048 (合理)
- **副作用**: 需要 synapse_gain 补偿

---

### FIX-004: synapse_gain 补偿 dt 缩放
- **日期**: 2026-05-21
- **关联降级**: DEG-001
- **修改文件**: `circuit/bundle.py`, `vestibular/chain.py`, `circuit/hebbian.py`
- **修改内容**: 新增 BundleConfig.synapse_gain;
  MET→HC=5, HC→Aff=80, Aff→Enc=40, Enc→Col=20, Col→Motor=10
- **推导依据**: ISI=20steps, ΔV=0.153, C=0.5 → I_needed=3.83;
  I_without=0.048 → gain=80
- **验证**: 信号深度 6/6
- **副作用**: DEG-002 (能量耗竭), DEG-005 (Motor 过快)

---

### FIX-005: activation clamp ±10
- **日期**: 2026-05-21
- **关联降级**: DEG-006
- **修改文件**: `components/neuron.py`
- **修改内容**: gated_conduct(vm) 和 vm 输出 clamp 到 [-10, 10]
- **推导依据**: TYPE:MATH — 生物饱和，神经元不能产出无限输出
- **验证**: 无 NaN
- **副作用**: 无

---

### FIX-006: P0 (τ_RC) + A/B/C/D 补偿机制
- **日期**: 2026-05-22
- **关联降级**: DEG-002 (能量耗竭), DEG-003 (Column跳变)
- **修改文件**:
  - `components/compensation.py` [NEW] — 4 个补偿组件
  - `components/neuron.py` — 集成补偿到 NeuronConfig + step()
  - `circuit/hebbian.py` — Encoding/Column/Motor 配置
- **修改内容**:
  - P0: Encoding τ_RC = 200ms (C=10, R=20); Column τ_RC = 240ms (C=12, R=20)
  - A. VoltageRegulator: coeff=0.5, max=5.0 (REF: Attwell & Laughlin 2001)
  - B. DecouplingCapacitor: Enc τ=20ms, Col τ=250ms (REF: Koch 1999)
  - C. BiasCurrentSource: Enc/Col 0.001, Motor 0.01 (REF: Goldberg 2000)
  - D. AGC: base_gain=5.0, target=0.5 (REF: Turrigiano 2008)
- **推导依据**:
  - 傅里叶分析: modeling_003 (ISI=80ms, f_drive=12.5Hz)
  - 能量平衡: Column heat/recovery = 30322:1
  - Laplace: Enc DC f_3dB=8Hz, Col DC f_3dB=0.64Hz
  - 完备性: modeling_004, modeling_005
- **验证**:
  - 信号深度: 6/6 持续（之前 4/6↔6/6 波动）
  - Column activation: 10.98 稳定（之前 0↔6 跳变）
  - Encoding energy: 12.0（之前 0.001）
  - 活跃神经元: 19-20 稳定（之前 2-5 波动）
- **副作用**: DEG-008 (Motor 偏置过多), DEG-009 (Motor energy), DEG-010 (热耗散)

---

### FIX-007: Ca²⁺ 电流模型修正 (Block 1)
- **日期**: 2026-05-22
- **关联降级**: DEG-004 (传入放电率偏低)
- **修改文件**:
  - `components/neuron.py` L278-287 — i_ca = g (gate activation)
  - `vestibular/chain.py` — ca_release_gm: 5.0 → 0.07
- **修改内容**:
  1. Ca²⁺ 积累改用通道门控激活值，非驱动力模型
  2. release gm 按 Ca_ss 推导: gm = 0.5 / (Ca_ss - 0.01)
- **推导依据**:
  - 归一化坐标系中 E_Ca=1.0, 但 HC vm 达到 3.0 → 驱动力反转
  - 生物真实: E_Ca=+130mV >> V_m(-65mV), Ca 总是向内流
  - release gm: Ca_ss=6.4 → gm=0.5/6.39=0.079 → 使用 0.07
- **验证**:
  - HC release: [0.004, 0.448] → 契约 C2 通过
  - HC 动态范围: 101:1 (之前 1.2:1)
  - Aff 频率: 24.3 Hz (之前 12.6 Hz)
- **副作用**: Aff CV=0.509 (需进一步调查)

---

### FIX-008: Vestibular 层 VR 扩展 (Block 3)
- **日期**: 2026-05-22
- **关联降级**: DEG-011 (MET energy), DEG-012 (HC energy)
- **修改文件**: `vestibular/chain.py` — MET/HC configs
- **修改内容**: 为 MET 和 HC 添加 VoltageRegulator (coeff=0.3, max=3.0)
- **推导依据**: Eatock & Songer 2011 — 感觉细胞有高代谢需求
- **验证**:
  - MET energy: 0.001 → 6.0
  - HC energy: 0.001 → 5.9
  - Col energy: 0.001 → 6.0 (间接改善)
- **副作用**: 无

---

### FIX-009: dt 传播修复 (严重 Bug)
- **日期**: 2026-05-22
- **关联降级**: DEG-008, DEG-009, DEG-010
- **修改文件**:
  - `circuit/bundle.py` — apply_to_targets 加 dt 参数
  - `circuit/hebbian.py` — 所有 apply_to_targets 调用传 dt
- **根因**: bundle.apply_to_targets(currents) 中 tgt.step(current) 没传 dt → dt 默认 1.0
- **验证**:
  - Motor silence: 124 → 0
  - 热耗散: 567 → 25 (-96%)
  - Motor energy: 0.001 → 1.0

---

### FIX-010: AGC 移除
- **日期**: 2026-05-22
- **修改文件**: `circuit/hebbian.py` — Enc/Col 配置移除 AGC
- **根因**: dt fix 后 AGC×5 使 scaled_current=50 → PowerRail 阻断
- **推导**: scaled=49.9, v_ratio=max(0, 1-49.9×0.1)=0

---

### FIX-011: Aff VR + 增益重校准
- **日期**: 2026-05-22
- **修改文件**:
  - `vestibular/chain.py` — Aff 加 VR, HC→Aff gain 80→20
  - `components/neuron.py` — VR 对 spiking 用 _activation_ema
- **推导**: release_ss=0.4, gain = 3.83/(0.4×0.48) = 20

---

### FIX-012: Enc/Col τ_RC 重校准 + DecouplingCap 移除
- **日期**: 2026-05-22
- **修改文件**: `circuit/hebbian.py`
- **修改内容**: Enc τ 200→5ms, Col τ 240→10ms, 移除 DecouplingCap
- **根因**: dt=0.001 时 τ=200ms 需 200s 达稳态; DecouplingCap 增加 20ms 延迟
- **验证**: Enc act: 0.0014 → 6.49

---

### FIX-013: Motor VR base_rate
- **日期**: 2026-05-22
- **修改文件**: `circuit/hebbian.py` — Motor vr_base_rate 0.001→0.1
- **根因**: Motor 持续收到 Col 电流产生 heat，base_rate 不足以补偿

---

### FIX-014: Motor VR 重校准 + 稳态调节 (DEG-009)
- **日期**: 2026-05-23
- **关联降级**: DEG-009 (Motor energy 耗尽)
- **修改文件**: `circuit/hebbian.py`
- **修改内容**:
  1. Motor VR: base_rate 0.1→0.5, activity_coeff 0.3→1.0, max_rate 3→5
  2. 新增 `_motor_homeostasis()`: 每 100 步检查 Motor 能量
     - E < 0.3: 调用 adapt_threshold() 提高放电阈值 (BIO: Na⁺失活)
     - E < 0.5: 缩放 col_to_motor synapse_gain (BIO: Turrigiano 2008)
     - E > 0.45: 恢复 threshold 和 gain
- **推导依据**:
  - heat_typical = (0.917/0.5)² × 0.1 = 0.335/step
  - 需 VR ≥ 0.335: base=0.5 + coeff×EMA ≈ 0.6 > 0.335 ✓
  - ESTIMATED: Motor VR ~5x sensory, CONFIDENCE: medium
  - BIO: Roberts 2003 (motor metabolic rate)
- **验证**: Motor E 从 0.14 → 0.50 (稳定)
- **副作用**: 暴露了 DEG-013 (Binding 爆炸)

---

### FIX-015: Binding activation 饱和 (DEG-013)
- **日期**: 2026-05-23
- **关联降级**: DEG-013 (Binding 指数爆炸)
- **修改文件**: `components/binding.py`
- **修改内容**: BindingCell.compute() 输出 clamp 到 10.0
- **推导依据**:
  - 乘积式 Π (a-θ)/θ 在 col_act=0.41, θ=0.05 时产出 52
  - 随 col_act 增长, O(a^n) 无限爆炸
  - BIO: 受体饱和 + 囊泡耗竭限制真实突触的 AND 门输出
  - clamp=10 与神经元 activation clamp ±10 对齐
- **验证**: b_max 从 8717→10.0, Motor E 稳定在 0.50
- **副作用**: 无

---

### FIX-016: Motor SFA + col→mot gain 重校准 (DEG-014)
- **日期**: 2026-05-23
- **关联降级**: DEG-014 (Motor spike 永久抑制)
- **修改文件**: `circuit/hebbian.py`
- **修改内容**:
  1. tau_w: 50→1.0s (BIO: Benda & Herz 2003, motor SFA τ=0.5-2s)
  2. b_adapt: 0.02→0.005 (milder per-spike increment)
  3. col_to_motor synapse_gain: 10→3
     (6 col × act=2.36 × G=0.111 × gain=10 = scaled=31 >> PowerRail max=10)
- **推导依据**:
  - tau_w=50s → decay/step=0.99998, w_adapt=0.35 after 18 spikes → 永不衰减
  - tau_w=1.0s → decay/step=0.999, w_adapt 稳定在 0.05 (正常 SFA)
  - gain=3: scaled=9.4, 在 PowerRail 容量内 (v_avail > 0)
- **验证**:
  - Motor spikes: 18(永久停止) → 85(15000步持续发放)
  - V_mem@t=14800: -0.83 → +0.19
  - heat@t=14800: 84 → 8.05
  - w_adapt 稳态: 0.35 → 0.05
- **副作用**: 无

---

### FIX-017: Motor PowerRail 崩溃 + Afferent 能量耗尽
- **日期**: 2026-05-24
- **关联降级**: Motor 完全沉默（0 spikes/20k步）
- **修改文件**:
  - `circuit/hebbian.py` — col→motor gain/weight, Motor config, homeostasis
  - `vestibular/chain.py` — Afferent bc_current + VR rate
- **根因分析**:
  1. Col→Motor 电流 = 1437 vs 允许上限 I_max = 6.67（61× 过载）
  2. V_supply = VDD×E/(1+I×R_s) = 0.508/144.76 = 0.004（阈值 0.3）
  3. Afferent 能量耗尽: E=0.015（从 1.0 降至 1.5%）
  4. Homeostasis `_base_col_mot_gain=3.0` 覆盖 bundle 配置
- **修改内容**:
  1. col_to_motor synapse_gain: 3.0 → 0.1
  2. col_to_motor weight_max: 1.0 → 0.5
  3. _base_col_mot_gain: 3.0 → 0.1（与 bundle 同步）
  4. Motor v_peak: 0.3 → 0.2（匹配降低的增益）
  5. Motor bc_current: 0 → 0.02（自发放电基线）
  6. Homeostasis threshold target: 0.3 → 0.2
  7. Afferent bc_current: reg 0→0.05, irr 0→0.03（Goldberg 2000 自发放电）
  8. Afferent vr_base_rate: 0.001 → 0.05（防止能量耗尽）
- **推导依据**:
  - 约束方程: I_max = (VDD×E/V_th - 1)/R_s = (1×0.5/0.3 - 1)/0.1 = 6.67
  - 方案 C: gain=0.1, w=0.5 → I=48×0.96×0.1=4.6 < 6.67 ✓
  - V_supply = 0.508/(1+4.6×0.1) = 0.348 > 0.2 ✓
- **验证**:
  - Motor spikes: 0 → 1131/20k步
  - V_supply: 0.004 → 0.93~0.98
  - Body movement: 0.10 → 0.18 units
  - Afferent E: 0.015 → 0.064
- **副作用**: 无

---

### FIX-018: 跨模态 Hebbian+decay 学习规则
- **日期**: 2026-05-24
- **关联降级**: 影子层跨模态权重 BCM 竞争崩塌
- **修改文件**: `circuit/bundle.py` — learn() 方法新增 hebbian_decay 规则
- **根因分析**:
  BCM θ 跟踪目标神经元总活动（由轴内 enc→col 主导）。
  跨模态信号微弱 → (a_tgt - θ) 的符号完全由前庭活动决定。
  最强的跨模态轴（oto_x）激活 s_col_oto_x 最高 → θ 最先超过 →
  BCM 变成 anti-Hebbian → 权重崩塌到 0。
  = BCM 的竞争淘汰杀死了最强的方向信号。
- **修改内容**:
  cross_axis 束使用 `hebbian_decay` 规则:
  `dw = η × |a_src| × |a_tgt| - λ × w`
  - 无竞争 θ → 方向关联存活
  - 衰减项防止无限增长（替代 BCM 的增长控制角色）
- **推导依据**:
  BIO: 联络纤维（连接不同皮层区）与局部回路有不同可塑性机制
  REF: Abbott & Nelson 2000 — correlation-based vs competition-based
- **验证**:
  - BCM: w(oto_x,therm) 0.003→0.000（step 20k→30k 崩塌）
  - Hebbian+decay: w(oto_x,therm) 0.003→0.004（持续增长→收敛）
  - w(oto_x)/w(oto_y) = 1.49× → 方向学习成功
- **副作用**: 跨轴权重不再受 BCM 竞争修剪（但有衰减限制增长）

