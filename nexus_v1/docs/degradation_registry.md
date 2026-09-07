# nexus_v1 降级追踪注册表 (Degradation Registry)

> **格式说明**: 见 RULES.md 原则 6
>
> **路径迁移说明（2026-09-06）**: `nexus_v1/generators|relations|events` 已整体
> 迁至顶层 `tss/`（纯搬迁，零改名零重构，见 `tss/README.md` 映射表）。以下
> 历史条目中的旧路径按该映射对应。
>
> **编号分叉已解决（2026-09-07，用户裁定重编号）**: 本文件原 DEG-015/016
> 与 `cell-cell/docs/degradation_registry.md`（主本）编号冲突，已重编号为
> **DEG-022/DEG-023**（含全部代码/文档引用同步）。主本编号空间 DEG-001~021
> + LIM 为权威；本文件后续新增条目从 DEG-024 起、且需先查主本避让。

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

---

### DEG-022 (原DEG-015，2026-09-07重编号): P2-A 生成元核心高输入完全静默（带通响应高端截止）
- **发现时间**: 2026-07-21
- **现象**: P2-A1a 输入包络扫描（`exp_P2A1a_input_envelope_scan.py`）发现
  基础生成元(`BaseGenerator`)在输入 u≥0.2 时 n_occ 归零、`peak_pre_trace`
  归零——不是持续高位不退出式饱和，而是完全静默，形成非单调带通响应
  （u∈[0.0005,0.1]活跃，u≥0.2静默）。
- **影响层**: `nexus_v1/generators/`（P2-A 基础生成元）→
  `somatosensory/transducer_neurons.py`（L1 ThermalDeltaNeuron）
- **根因**: 用户指定方法（比对u=0.1/0.2/0.5逐级检查L1/HC/ensemble/collector,
  见`exp_P2A_highinput_root_cause.py`）实测定位：
  1. `ThermalDeltaNeuron.step()` 完全覆写基类 `Neuron.step()`（PHYS注释
     "bypasses RC"），从未经过基类的 ±10.0 activation 钳位，输出
     `max(0,dT×200)` 理论线性无界增长。
  2. 精细网格实测（L1=1→40）显示 ensemble PowerRail 的
     `v_actual=max(0,vdd-I·r_internal)` 随 L1 输出连续平滑衰减
     （0.925→0.808→0.458→0.025→0），在 L1≈20（u=0.1）时已几乎完全崩溃
     （0.03-0.04），L1≥30（u≥0.15）时精确坍缩为 0——collector 随之完全
     收不到输入。
  - 与 DEG-014/`project_memristor_saturation_edge_bug` 记录的同一机制
    （注入电流超过 PowerRail 供电能力 → v_avail 钳死为 0）同源，
    2026-07-11 的规避（L1→HC bundle weight 降到 0.3）只假设"dT≤0.1安全"，
    未在 L1 输出本身设上限，该假设在 ensemble 这一级实测已不成立。
- **状态**: FIXED
- **修复**: FIX-019

---

### DEG-023 (原DEG-016，2026-09-07重编号): 近热接近与 DR5 性能相对 2026-07-03 历史验证退化
- **发现时间**: 2026-07-28
- **触发场景**: 审查点2②「FIX-019 第二生产路径验证」——重跑
  `exp_validate_thermal_delta_50k.py`（50000步，用于验证 ThermalDeltaNeuron
  暖启动 DA 通路，见 FIX-019/DEG-022）。
- **现象**（如实记录，不预设根因）：
  - 历史验证（`工作报告/ThermalDelta修复报告_2026-07-03.md`，commit 37e664e）：
    50k 步终态 `d≈9.3`，relay_to_da 四方向（front/back/left/right）权重均衡
    增长（Δ分别 +0.058/+0.064/+0.112/+0.094）。
  - 本次重跑（同一脚本，同一场景，当前代码状态）：50k 步终态仅 `d≈12.0`；
    `DR5` 指标在约 30000 步后降至 `0.0%` 并持续到结束；`relay_to_da` 四方向
    权重表现分化——front/back/left 权重**精确保持初始值不变**（Δ=0.00000，
    非缓慢变化/非饱和），仅 right 权重从 0.0966 增长到 0.29954（接近
    `weight_max=0.3` 上限）。
- **裁定措辞（重要，避免过早归因）**：**FIX-019 第二生产路径不是"验证失败"，
  而是"因上游运动回归而未被有效验证"**——`_soma_proj` 需要 `relay.act>0.35`
  （对应 `d<12`）才大量获得放电机会，本次重跑全程 `d` 直到最后一步才刚好
  摸到 12.0，意味着绝大多数步数里 STDP 学习条件本身没有被充分激活；
  front/back/left 的"零权重变化"首先可以由此解释。right 的权重饱和更可能
  是早期身体朝向瞬态期间的一次性激活后触顶，不代表四方向正常学习。**不裁定
  "FIX-019 钳位失效"，也不裁定"STDP 回归"或具体某个 motor/decision/muscle
  子系统的 bug**——根因指向趋热接近速度本身（`d` 下降过慢）与 `DR5` 坍缩，
  但具体是哪个环节（运动生成、决策电路、朝向控制等）导致尚未定位。
- **影响层**: `nexus_v1/circuit/variant_adapter.py` 的运动/趋热决策链路
  （具体子系统未定位）；下游连带 `bundles_relay_to_da` STDP 学习资格。
- **已知限制**: 当前代码与历史验证所在的 commit（84165c4/37e664e）已大幅
  分岔，缺少可直接重放的同构基线，无法简单二分定位是哪次改动引入。
- **状态**: **确认存在性能退化信号，根因未定位**（不是 FIXED，也不是常规
  意义的 OPEN bug 报告——是一个需要独立调查会话来定位具体机制的性能退化）。
- **下游影响登记**（供后续阶段参考，不阻塞当前工程）：
  - P2-B0：不受影响，可正常进入。
  - P2-B1：不被本 DEG 自动阻塞，但不能直接假设"STDP 应该没问题"——需要在
    P2-B1 自己的 D2 结构中独立验证 `pre/post活动→eligibility→DA门控→Δw≠0`
    这条链路，以及阻断候选关系后是否改变未来输出。
  - 运动/趋热生产路径（`exp_validate_thermal_delta_50k.py` 等）在本 DEG
    修复前**不可作为"系统健康"的验证基线**使用。
- **修复**: 待定（需要独立调查会话）

