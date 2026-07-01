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
