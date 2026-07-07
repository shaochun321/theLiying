# Fix Registry

> 格式：RULES.md 原则 8。每条修复必须交叉引用对应 DEG-XXX。
> 所有修复应在实施时运行熵审计验证。

---

### FIX-001: RC-2 thermo_to_relay synapse_gain 3.0→0.3

- **日期**: 2026-07-01
- **关联降级**: DEG-001（部分缓解：relay pre_trace 不再饱和）
- **修改文件**: `nexus_v1/somatosensory/chain.py` 行 222
- **修改内容**: `synapse_gain: 3.0 → 0.3`
- **推导依据**: Craig & Dostrovsky 1999：Aδ→WDR 突触效能 1.5–3 mV/spike；原值导致 relay.activation 饱和（3.7 → 0.37 目标区间）
- **验证**: Phase 8 6/6 DR PASS；relay activation 3.7→0.37，pre_trace 不再钳位
- **副作用**: 无新增降级

---

### FIX-002: RC-3 D2R 参数修复（d2_conductance + d2_da_r_leak）

- **日期**: 2026-07-01
- **关联降级**: DEG-001（DA 基线从 0.03 → 0.24，STDP 基础条件改善）
- **修改文件**: `nexus_v1/circuit/variant_adapter.py`
- **修改内容**: `d2_conductance: 0.5 → 0.1`；`d2_da_r_leak: 100 → 20`（D2R g×τ 乘积 50 → 2）
- **推导依据**: Ford 2014（D2R conductance 0.1 nS 量级）；Benoit-Marand 2000（DAT 清除时间 ~100 ms）
- **验证**: Phase 8 6/6 DR PASS；DA 稳定 0.24（Phase 7 为 0.03，提升 7×）
- **副作用**: 无新增降级

---

### FIX-003: RC-4 两时间尺度 relay 差减（phasic DA）

- **日期**: 2026-07-01
- **关联降级**: DEG-001（DA 变为 phasic；STDP 首次正确编码热梯度方向）
- **修改文件**: `nexus_v1/circuit/variant_adapter.py`（`_init_da_circuit()`，step 函数，census 方法）+104 行
- **修改内容**: 添加 slow_relay 神经元（τ=300k，C=300，r_leak=1.0，multi-channel linear）+ relay_to_slow bundle（frozen, W=1.0）+ slow_to_da bundle（frozen, W=0.5, gain=-1.0）
- **推导依据**: Duclaux & Kenshalo 1980；Morin & Bushnell 1998 Prog. Brain Res. 113:303（SA WDR 背景减法）。**τ=300k 无生物来源（见 DEG-002）**
- **验证**: 21/21 regression PASS；Phase 8 6/6 DR PASS；wR>wL 方向正确（之前为 hash 随机）；熵审计 6/6 signal depth，energy>0，无 NaN
- **副作用**: DEG-002（τ 无生物来源），DEG-003（初始权重为 0 根因未查清）

---

### FIX-004: slow_relay τ 生物推导修正 ❌ ABANDONED on V1 (2026-07-01)

- **日期**: 2026-07-01
- **关联降级**: DEG-002（RECLASSIFIED，见下）
- **尝试记录**:
  - Round 1: `capacitance 300.0 → 15.0`（τ=15k步，SA-II 中值 15s）→ FAIL
    - 比率 7.70× @100k（>3×），wR-wL=-0.018（反向）
    - step 30k 时 slow_relay 已超调 4.5×，体运动向左，热梯度信号被破坏
  - Round 2: `capacitance=30.0`（τ=30k步，SA-II 上限 30s）→ FAIL
    - step 10k 时 sr_R/rl_R=0.030×（slow_relay 极小），但 wR-wL=-0.034（比 Round1 更负）
    - **方向错误在 slow_relay 产生任何影响之前就已建立**
- **根因（修正）**: 不是 τ 值问题，而是 HC-002（全对全 soma_to_da 拓扑）：
  前 10k 步前庭信号短暂驱动 left relay.act > right relay.act，
  STDP 锁定 wL>wR，体运动向左，relay_right.act 下降，热梯度本身被污染。
  τ=300k 之所以能工作，是因为在学习关键期（前 200k 步）slow_relay 保持足够小，
  热梯度长期优势（src1 持续在右）最终覆盖前庭短暂偏压。
- **ABANDONED 原因**: SA-II τ=15-30s 在 V1 全对全架构下不可行。
  需 V2.0 地址化连接（patch-specific soma→DA，HC-002 根治）后才能正确实现。
- **capacitance 恢复**: 300.0（已验证有效值；重新分类为"导航背景减除 τ≈5min"而非"无依据"）
- **DEG-002**: RECLASSIFIED（真正根因是 HC-002，等待 V2.0）
- **分析报告**: `cell-cell/工作报告/FIX004_analysis_2026-07-01.md`

---

### FIX-005: P0 DA_ema + lambda_metabolic 权重保留修复

- **日期**: 2026-07-07
- **关联降级**: T-067 观察（fill 饱和后 740 步权重归零）
- **修复内容**:
  1. `bundle.py BundleConfig` 新增 `da_ema_tau=5000.0`, `lambda_metabolic=1e-6`
  2. `SynapticBundle.__init__`: 新增 `self._da_ema = 0.0`
  3. `SynapticBundle.learn()`: DA_ema 替代点采样；LTP/LTD 均用 DA_ema 门控；被动衰减用 lambda_metabolic 替代 decay_rate_by_stage[0]=0.025
- **验证**: T-073 3/3 PASS，w_ccw 保留率 99.8%（vs P0 前 ≈0%）
- **Commit**: 4d3526a

---

### FIX-006: Motor 度量规范修正（DEG-006 后续）

- **日期**: 2026-07-07
- **关联降级**: DEG-006（motor_neurons dict key 与 neuron.id 不一致）
- **规范内容**（适用于所有新实验脚本）:
  1. **正确的 Motor axis 过滤**: 用 `'move_x' in neuron.id`（子串匹配），而非 `neuron.id == 'move_x'`
     - 正确: `if 'move_x' in mot.id:`  
     - 错误: `if mot.id == 'move_x':` 或 `if key == 'move_x':`
  2. **正确的 Motor 激活度量**: 读 `neuron._activation_ema`（firing rate，variant_adapter 实际使用的值），而非 `neuron.activation`（瞬时 0/1，circuit step 结束时永远是 0）
     - 正确: `motor_ema = mn._activation_ema`  
     - 错误: `motor_peak = max(peak, abs(mn.activation))`
  3. **多次步进注意**: 神经元在一个 circuit step 内可被多个 bundle 多次调用。`activation` 反映最后一次调用状态，不代表该 step 内的峰值激活。
  4. **axis_acts 的实际驱动**: 确认 `variant_adapter.py:1210` 用 `mot._activation_ema` 计算 axis_acts，motor force = muscle.gain × axis_acts。
- **未修改代码**（已正确）: variant_adapter 本身的 axis_acts 计算逻辑正确（已用 EMA），无需改动。只需修正外部度量脚本。
