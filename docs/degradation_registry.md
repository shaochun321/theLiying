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

### DEG-002: slow_relay τ=300k 无生物来源（RC-4 技术债）

- **发现时间**: 2026-07-01
- **现象**: RC-4 引入的 slow_relay 神经元（`nexus_v1/circuit/variant_adapter.py`）的时间常数 τ=300k steps（C=300, r_leak=1.0）是按照 Phase 8 实验时长设定的，**没有生物学依据**。代码已标注 `# UNGROUNDED`。
- **影响层**: slow_relay 神经元，slow_to_da bundle，phasic DA 信号质量
- **根因**: 参数工程驱动而非生物推导。真实 SA-II 纤维适应时间常数应从文献推导（Duclaux & Kenshalo 1980 Fig.4；典型 SA-II τ ≈ 5–30 s → τ_norm = 5000–30000 steps at dt=0.001）
- **状态**: OPEN
- **修复**: 待查文献后实施 FIX-004（重新推导 τ_SA）

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
