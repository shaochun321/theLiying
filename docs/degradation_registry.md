# Degradation Registry

> 格式：RULES.md 原则 6。每条降级必须有后续分析计划或关联修复。
> 状态：OPEN / INVESTIGATING / FIXED / WONTFIX

---

### DEG-001: soma_to_da 全对全连接导致热梯度信号抵消

- **发现时间**: 2026-07-01
- **现象**: soma_to_da（4 relay → 3 DA）全对全连接。体运动时某侧升温被另侧降温抵消，DA 总输入恒定（tonic 0.24）。STDP post_trace ≈ 0，权重不学习热梯度方向，方向由 hash 初始化随机决定。
- **影响层**: soma_to_da bundle，DA 神经元，所有依赖 DA-STDP 的学习路径
- **根因**: 电路拓扑问题：全对全连接在统计上消除方向信息。需要地址化独立子回路（patch-specific DA 子电路）或 V2.0 重构
- **状态**: INVESTIGATING
- **修复**: FIX-003（RC-4 部分缓解：slow_relay 差减使 DA phasic，但全对全拓扑未根治）

---

### DEG-002: slow_relay τ=300k 生物依据分类（HC-002 根因）

- **发现时间**: 2026-07-01
- **现象**: RC-4 引入的 slow_relay 的 τ=300k 步（C=300）被认为无生物依据，尝试改为 SA-II τ=15-30s。
- **FIX-004 尝试结果 (2026-07-01)**:
  - C=15（τ=15k）→ FAIL: wR-wL=-0.018，ratio 7.7×@100k
  - C=30（τ=30k）→ FAIL: wR-wL=-0.034（step 10k 时 slow_relay 仅 0.030×，方向错误不是 slow_relay 所致）
- **根因重新分类**: 方向学习失败的真正原因是 **HC-002（全对全拓扑）**，而非 τ 值。
  前 10k 步前庭信号造成短暂 wL>wR，体运动向左破坏热梯度信号。任何短 τ 都无法在 V1 架构下通过。
  τ=300k 对应导航背景减除机制（整体导航时间尺度，分钟级），不是 SA-II 纤维适应。
- **影响层**: slow_relay 神经元（保留 C=300），根本问题在 soma_to_da 拓扑（HC-002）
- **状态**: RECLASSIFIED → 依赖 DEG-001（HC-002 全对全拓扑），在 V2.0 重构前无法独立修复
- **修复路径**: V2.0 地址化连接（patch-specific soma→DA）实现后，可以在正确拓扑中重新实现 SA-II τ
- **分析报告**: `cell-cell/工作报告/FIX004_analysis_2026-07-01.md`

---

### DEG-003: Phase 8 soma_to_da 初始权重为 0 的根因未查清

- **发现时间**: 2026-07-01
- **现象**: Phase 8 with RC-4 实验中，step 0 时 `_get_weights()` 返回 wL=wR=wF=wB=0.0000，而 `BundleConfig(initial_weight=0.5)` 应产生 hash 扰动后约 0.375–0.625 的初始权重。50k 步后权重从 0 正确增长到 0.52–0.55（方向正确），但 step 0 为 0 的原因未经验证。
- **影响层**: soma_to_da bundle，`_get_weights()` 函数，Phase 8 实验结果解释
- **根因**: 未查清。可能是：(A) 某初始化路径使 da_list 为空 → 空 weight matrix 返回 0；(B) `_init_da_circuit()` 调用时序问题；(C) RC-4 改变了某初始化顺序。
- **状态**: OPEN
- **修复**: 待排查（可通过在 step=0 加调试打印验证 `bundles_soma_to_da[0].weight_matrix()` 的实际值）

---

### DEG-004: Motor 层信号路径弱耦合（C6 合约偶发失败）

- **发现时间**: 之前已知（参见 CLAUDE.md "Current state"）
- **现象**: Col→Motor 耦合偏弱，C6 Motor-signal contract 在某些输入下失败。
- **影响层**: col_to_motor bundles，Motor 层
- **根因**: col_to_motor 初始权重偏小，STDP 在当前实验中未能强化该路径
- **状态**: OPEN
- **修复**: 未开始

---

### DEG-005: shadow-layer free energy K_ema 无界增长

- **发现时间**: 之前已知（参见 CLAUDE.md "Current state"）
- **现象**: shadow layer 的 `K_ema` 参数随时间无界增长，free energy 发散
- **影响层**: `components/shadow_sandbox.py`，shadow_to_da bundle
- **根因**: K_ema 更新规则中缺乏上界约束
- **状态**: OPEN
- **修复**: 未开始

---

### DEG-006: motor_neurons dict key 与 neuron.id 不一致导致度量指标错误

- **发现时间**: 2026-07-07（T-077 Motor 链诊断）
- **现象**: `c.motor_neurons['move_x']` 指向的神经元实际 ID 为 `'motor_move_x'`，而非 dict key `'move_x'`。  
  T-073 实验过滤条件 `self.id in ('move_x', 'move_y', 'move_z')` → 0 命中，被误判为"神经元未被步进"。  
  进而写了错误的 T-077 任务和 T-073 报告 §四"Motor 链失联"结论。
- **错误对应链**（保留以防重蹈覆辙）:
  1. `c.motor_neurons` dict key `'move_x'` ≠ 神经元 `.id 'motor_move_x'`
  2. 用 dict key 作 ID 过滤 → 0 命中 → 误判"未步进"
  3. T-073 在 `c.step()` 后读 `activation` → 神经元最后一次调用 input≈0，spiked=False，act=0.0 → 永远读到 0.0
  4. 结论："Motor_x peak=0.0000，Motor 链 broken" → **错误**
- **真实情况**: Motor 链完全正常。每 circuit step 内 motor_move_x 被调用 6-7 次，其中 2-3 次 spiked=True。EMA=0.33-0.44，variant_adapter axis_acts 基于 EMA 正常驱动 muscle force。
- **影响层**: 所有度量脚本 Motor 读取逻辑；T-073 报告 §四（结论已失效，以本条目为准）
- **根因分类**:
  - (A) dict key 是"轴别名"，`.id` 是"完整神经元名"，二者不同
  - (B) 度量脚本应读 `_activation_ema`（firing rate），而非 `activation`（瞬时 0/1）
  - (C) 神经元在一个 circuit step 内被多个 bundle 多次调用，最终状态非峰值
- **状态**: DOCUMENTED（不修复电路，修复度量规范）
- **修复**: 见 FIX-006（度量规范）；T-073 报告 §四 结论已失效（参见本条目）
