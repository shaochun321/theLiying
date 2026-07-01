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

### FIX-004: （待实施）slow_relay τ 生物推导修正

- **日期**: 待定
- **关联降级**: DEG-002
- **修改文件**: `nexus_v1/circuit/variant_adapter.py`（slow_relay capacitance 参数）
- **修改内容**: 依据 SA-II 纤维生物文献推导 τ_norm，替换当前 τ=300k
- **推导依据**: 待查（Duclaux & Kenshalo 1980 Fig.4；目标：SA-II τ_bio ≈ 5–30 s → τ_norm = 5000–30000 steps）
- **验证**: 待实施后运行 regression + Phase 8 长程实验
- **副作用**: 待评估（τ 变化影响 slow_relay 充电速度，可能影响 DA phasic 信号强度）
