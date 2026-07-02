# Technical Debt: 硬编码清单

> **核心原则**：所有硬编码在后期必须删除并重构为结构性涌现（SynapticBundle + STDP + 生物参数推导）。
> 本文件是强制性技术债追踪，不是可选的。

---

## 什么是本项目的"硬编码"

按 CLAUDE.md 定义，以下任一情况均为硬编码：

| 类别 | 判断标准 | 示例 |
|------|---------|------|
| **语义数学** | Python 数学直接计算语义结论 | `sign(∇T · v)` 判断朝热源 |
| **直接注入** | 不经 SynapticBundle 向神经元注入电流 | `neuron.step(I_ext, dt)` 从外部直接调用 |
| **逻辑替代电路** | `if`/`sign`/`dot product` 替代物理回路 | `if da > 0.5: reward = 1` |
| **目标写死** | 把行为目标写进代码 | `if approaching: DA += 0.1` |
| **无来源参数** | 参数无生物/物理推导依据 | `initial_weight=0.5`（凭感觉） |

---

## 当前已知硬编码清单

### HC-001: slow_relay τ=300k 生物依据重新分类 ⚠️ RECLASSIFIED (2026-07-01)
- **位置**: `nexus_v1/circuit/variant_adapter.py`，`_init_da_circuit()` 的 slow_relay NeuronConfig
- **原始问题**: τ=300k 步（300s）被认为无生物依据，启动 FIX-004 尝试改为 SA-II τ=15-30s
- **FIX-004 结果**: ABANDONED — C=15.0 和 C=30.0 均导致方向学习反转（wR-wL<0，从 step 10k 即建立）
- **根因分析**: 方向错误在 slow_relay 产生任何影响之前就已建立（C=30 时 step 10k sr_R/rl_R=0.030×），
  真正根因是 HC-002（全对全拓扑）：前庭信号在前 10k 步创造 wL>wR 偏压，体运动向左，
  热梯度信号本身被污染，无法恢复。
- **重新分类**: τ=300k 对应导航背景减除机制（哺乳动物热导航积分时间尺度，分钟级），
  SA-II τ=15-30s 是感觉纤维适应，是错误的生物类比。τ=300k 保留为已验证值。
- **V2.0 行动**: 在地址化连接（patch-specific soma→DA）中，才能正确实现 SA-II τ（不受前庭污染）
- **DEG 关联**: DEG-002（重新开启），FIX-004（ABANDONED）
- **分析报告**: `cell-cell/工作报告/FIX004_analysis_2026-07-01.md`

### HC-002: soma_to_da 全对全拓扑（结构性语义硬编码）
- **位置**: `nexus_v1/circuit/variant_adapter.py`，`_init_da_circuit()`
- **问题**: `SynapticBundle(cfg_soma, relay_neurons, da_list)` — relay_neurons 包含全部 4 个 patch relay，da_list 包含全部 3 个 DA 神经元。全对全连接在设计上让热梯度信号相互抵消，是一种"结构性硬编码"：把"DA 接收全局热信号"这一语义写死进了电路拓扑
- **代码标注**: 无（需添加 `# STRUCTURAL-DEBT: all-to-all suppresses directional gradient`）
- **影响**: 方向学习效率低；RC-4 slow_relay 是 workaround，非根治
- **重构目标**: V2.0 重构时改为地址化独立子回路（patch-specific soma → patch-specific DA）
- **DEG 关联**: DEG-001
- **优先级**: 高（根治需要 V2.0）

### HC-003: slow_to_da synapse_gain=-1.0 和 initial_weight=0.5（架构性设计）
- **位置**: `nexus_v1/circuit/variant_adapter.py`，slow_to_da BundleConfig
- **问题**: `synapse_gain=-1.0`（抑制性）和 `initial_weight=0.5`（与 soma_to_da 对称）是人工设计的"差减电路"语义，而非从生物结构涌现
- **代码标注**: 无
- **影响**: 固定了"减去热背景"这一操作的增益和时序，不具备自适应性
- **重构目标**: 理想上应让 slow_relay→DA 的权重通过 Hebbian 规则自适应（而非 frozen=0.5）。但需先解决 DEG-002（τ 无依据）
- **DEG 关联**: DEG-002
- **优先级**: 低（当前不可知是否必要）

### HC-005: G_ORIENT=200 硬编码热趋性反射（最高优先级）⚠️ SEMANTIC HARDCODING
- **位置**: `nexus_v1/circuit/variant_adapter.py` 约第 726 行
- **代码**:
  ```python
  G_ORIENT = 200.0
  delta_T_orient = self._patch_temps['right'][0] - self._patch_temps['left'][0]
  mechanical_inputs['yaw'] += delta_T_orient * G_ORIENT
  ```
- **问题**: 用 Python 减法直接计算「右侧更热→右转」这一语义结论，绕过所有 SynapticBundle，违反"行为从结构涌现"原则。注释本身写明"T_right > T_left → 热源在右 → 正 yaw"——即把行为目标硬写入代码。
- **影响（严重）**: Phase 6/7/8 及 Phase 3 中所有热趋性实验结果均受污染：
  - **DR5≈96%（Phase 6/7）**：被 G_ORIENT 直接制造，不是 STDP 涌现
  - **DR2 dist 减少**（所有实验）：G_ORIENT 驱动 yaw，body 自然靠近热源
  - **Phase 8 wR>wL "方向正确"**：G_ORIENT 持续推 body 向 S1 → 右 patch 更热 → STDP 被动跟随
  - Phase 3 实验证伪：STDP 在没有 G_ORIENT 辅助时（三热源、前庭干扰）学到错误方向（wL>wR）
- **代码标注**: 需添加 `# HC-005: SEMANTIC HARDCODING — remove in V2.0`
- **重构路径**: 改为 `SynapticBundle(thermo_to_relay_right, relay_right → motor_yaw_right)` 和 `SynapticBundle(thermo_to_relay_left, relay_left → motor_yaw_left)` 独立束，让方向性从补丁激活差异中物理涌现，用 STDP 习得而非公式计算
- **V2.0 行动**: 删除此代码块，用 patch-specific thermo→motor 通路替代
- **优先级**: 最高（污染全部热趋性实验结论）

### HC-006: feed_alignment 点积直接注入 DA 奖励（语义数学 + 目标写死）⚠️ CRITICAL
- **位置**: `nexus_v1/circuit/variant_adapter.py`，`step()`，约 762-775 行
- **代码**:
  ```python
  alignment = dot(heat_dir, vel_dir)
  feed_alignment = max(0.0, alignment) * thermal_err
  # → 注入 CirculationProportionCircuit → 驱动 DA
  ```
- **问题**: Python 直接计算「身体朝热源移动吗？」这一语义结论，然后注入 DA 奖励。`max(0.0, ...)` 符号钳位显式编码「接近=好」的行为目标。与 HC-005 并列为热趋性污染的两大源头。
- **影响**: Phase 6/7/8 的 DA 奖励信号不是从电路物理中涌现，而是从 Python 数学中写死。
- **V2.0 修复**: 创建前/后 patch relay → DA 专用 SynapticBundle，让接近信号从前后 patch 差异中物理涌现。
- **优先级**: 最高（与 HC-005 并列）

### HC-007: extra_axes 直接注入 Encoding 神经元（绕过 SynapticBundle）⚠️ CRITICAL
- **位置**: `nexus_v1/circuit/hebbian.py`，`step()`，约 547-561 行
- **代码**:
  ```python
  enc.step(tonic_val * 5.0, dt)  # 直接注入，无 SynapticBundle
  ```
- **问题**: 所有 extra-axis 信号（包括热觉）直接注入 Encoding 神经元，gain=5.0 无 BIO:/REF:。此路径：(1) 无 Memristor 权重，STDP 永远无法修改热觉转导增益；(2) 无 Xin 残差累积；(3) 无 sprout/prune；(4) 整个项目生命周期内热觉→Encoding 跳零可塑性。
- **影响**: 严重——热觉信号的第一跳完全没有结构可塑性，整个热趋性学习从一开始就残废。
- **V2.0 修复**: 创建 `bundles_extra_to_enc` SynapticBundle，gain 和 weight 由 BundleConfig 携带。
- **优先级**: 最高（热觉学习根本修复）

### HC-008: HairCell activation 被覆盖，STDP trace 双重更新⚠️ CRITICAL
- **位置**: `nexus_v1/vestibular/chain.py`，`step()`，约 351、354-357 行
- **代码**:
  ```python
  hc.activation = hc.release_rate          # 覆盖 MOSFET 物理计算结果
  hc.pre_trace = release_rate * decay ...  # STDP trace 被替换
  ```
- **问题**: HC 神经元的半导体物理 activation 被 Ca²⁺ release_rate 赋值覆盖；STDP pre_trace 被重置为 release_rate。导致 STDP 每步执行两次（不同信号），第二次（Ca²⁺ 版本）获胜。
- **V2.0 修复**: 创建独立 ReleaseNeuron（TYPE:BIO, 对应 IHC active zone），通过 SynapticBundle 连接到 HairCell。
- **优先级**: 最高（前庭 STDP 根本修复）

### HC-009: thermoreceptors.step(T) 直接注入 + noci_total 跨模态融合⚠️ CRITICAL
- **位置**: `nexus_v1/somatosensory/chain.py`，`step()`，约 345、357-360 行
- **问题**: (1) 原始环境温度直接注入神经元，无 SynapticBundle，无 STDP，无 Xin；(2) `noci_total = abs(dT)*200 + damage*10` 在 Python 中融合两种感觉，abs() 抹除 dT 符号，TRPV1/TRPA1 双通道分离失效。
- **V2.0 修复**: 创建 `transducer_env_to_thermo_{pid}` 和独立 dT / damage 换能束。
- **优先级**: 最高（感觉边界违规）

### HC-010: AutomaticGainControl 驱动 activity=1.0（目标写死 + 覆盖 STDP）⚠️ CRITICAL
- **位置**: `nexus_v1/components/compensation.py`，`AutomaticGainControl`，约 155-203 行
- **问题**: 每步 gain(t) = K/(1 + ā/a_target=1.0)，在全系统覆盖 STDP 动态。base_gain=20（Turrigiano 2008 范围的 10-13×），tau_agc=0.1（生物稳态塑性实际是小时-天）。
- **V2.0 修复**: 完全删除 AGC。稳态通过 SynapticBundle 权重衰减 + PowerRail 能量限制自然涌现。
- **优先级**: 最高（主动干扰全系统 STDP）

### HC-011: shadow 运动分配 if/elif 字符串匹配（逻辑替代电路）⚠️ CRITICAL
- **位置**: `nexus_v1/components/shadow_sandbox.py`，`initialize()`，约 243-255 行
- **代码**:
  ```python
  if axis == 'yaw':   mot_assignment = 'x'
  elif axis == 'therm': mot_assignment = 'x'  # "no spatial bias"
  ```
- **问题**: VOR/VSR 几何映射由 Python if/elif 硬写死；`therm→x` 硬编码方向偏好；shadow 电路永远无法从感觉数据中发现更优运动耦合。
- **V2.0 修复**: 删除 mot_assignment，创建全连接 col→mot（所有轴 × 所有 3 个 motor，initial_weight=0.001），由 STDP+Xin 竞争决定。
- **优先级**: 高（shadow 层学习残废）

### HC-012: world.gradient_at() + DR5 使用全局特权信息⚠️ CRITICAL
- **位置**: `nexus_v1/components/world.py`，`gradient_at()`，约 204-217 行
- **问题**: DR5 = dot(world.gradient_at(pos), body.velocity) 使用电路本身无法访问的全局梯度信息来判断「热趋性是否涌现」。所有 Phase 5/6/7/8 的 DR5 PASS 结果均无效，因为 benchmark 本身使用了特权信息。
- **V2.0 修复**: 重命名为 `_gradient_diagnostic()`；用 patch 温度差（T_front - T_back）重定义 DR5。
- **优先级**: 最高（实验数据根本失效）

### HC-013: _motor_config() 中 \\n 转义导致 FIX-017 bc_current 未生效（静默 Bug）⚠️ CRITICAL
- **位置**: `nexus_v1/circuit/hebbian.py`，`_motor_config()`，约 204 行
- **代码**:
  ```python
  # BIO: ...\\n        use_bias_current=True,\\n        bc_current=0.01,
  ```
- **问题**: `\\n` 是字面转义，`use_bias_current=True` 和 `bc_current=0.01` 在注释字符串内，从未执行。FIX-017 标注为已修复，但实际从未生效。运动神经元没有 bc_current 基线，所有基于 Motor 信号的分析均建立在错误假设上。
- **V2.0 修复**: 去转义 `\\n` 为真实换行，使 `use_bias_current=True` 和 `bc_current=0.01` 成为实际赋值语句。

---

## HC-014 至 HC-060：汇总表（详见审计报告）

完整细节见：`cell-cell/工作报告/全链路审计综合报告_2026-07-02_Part1.md`

| HC-ID | 严重度 | 类别 | 位置 | 问题简述 |
|-------|--------|------|------|---------|
| HC-014 | HIGH | SEMANTIC_MATH | variant_adapter.py:756 | thermal_stability = 1/(1+err×10) 注入 CPC |
| HC-015 | HIGH | DIRECT_INJECT | vestibular/chain.py:340 | if/else dispatch 绕过 apply_to_targets |
| HC-016 | HIGH | DIRECT_INJECT | variant_adapter.py:802 | 稳态偏差直接注入所有 Motor 神经元 |
| HC-017 | HIGH | DIRECT_INJECT | variant_adapter.py:793 | CPC 偏差直接注入 DA 神经元膜 |
| HC-018 | HIGH | SEMANTIC_MATH | variant_adapter.py:1052 | grad_T 和 grad_dot_v 存入 MotionState（DR5 来源）|
| HC-019 | HIGH | LOGIC_REPLACES_CIRCUIT | hebbian.py:799 | activity_match=0.3 过滤 sprout 候选（替代 STDP 筛选）|
| HC-020 | HIGH | GOAL_HARDCODED | hebbian.py:306 | therm 轴专用 _thermal_column_config（字符串匹配）|
| HC-021 | HIGH | LOGIC_REPLACES_CIRCUIT | shadow_sandbox.py:381 | abs(xi) 抹除 Xin 符号（半波整流器用 Python 替代）|
| HC-022 | HIGH | LOGIC_REPLACES_CIRCUIT | bundle.py:559 | if birth>0 决定 expand/contract（应为 MOSFET 比较器）|
| HC-023 | HIGH | DIRECT_INJECT | variant_adapter.py:563 | 跨轴 Motor 侧抑制用 Python 算术+直接注入膜 |
| HC-024 | HIGH | DIRECT_INJECT | variant_adapter.py:957 | binding→motor Python 权重矩阵+直接注入（无 Bundle）|
| HC-025 | HIGH | LOGIC_REPLACES_CIRCUIT | motor_decision.py:213 | CPG 用 sin(phi) 数学公式替代振荡电路 |
| HC-026 | HIGH | LOGIC_REPLACES_CIRCUIT | hebbian.py:957+variant:642 | _motor_efficacy Python 前向模型门控有丝分裂 |
| HC-027 | HIGH | UNGROUNDED_PARAM | variant_adapter.py:697,715 | OTOLITH_GAIN=500, ANGULAR_GAIN=50（无 BIO:）|
| HC-028 | HIGH | DIRECT_INJECT | somatosensory/chain.py:372 | relay 电流 Python 手动求和后直接注入 |
| HC-029 | HIGH | GOAL_HARDCODED | world.py:163 | MIN_ALIVE=2 保证始终有热源（生存目标写死）|
| HC-030 | HIGH | LOGIC_REPLACES_CIRCUIT | neuron.py:593 | I²R 用钳位前电流计算，高估耗散 |
| HC-031 | MEDIUM | DIRECT_INJECT | variant_adapter.py:866 | 振荡器直接覆盖膜电荷 `_membrane.charge = new_charge` |
| HC-032 | MEDIUM | DIRECT_INJECT | variant_adapter.py:915 | NDR `_membrane.charge *= (1-reduction)`（无 BIO:）|
| HC-033 | MEDIUM | LOGIC_REPLACES_CIRCUIT | variant_adapter.py:987 | LMR 直接减 neuron.energy（绕过能量计量）|
| HC-034 | MEDIUM | LOGIC_REPLACES_CIRCUIT | variant_adapter.py:899 | MFD 直接减 neuron.energy（能量汇无 Noether 记录）|
| HC-035 | MEDIUM | LOGIC_REPLACES_CIRCUIT | shadow_sandbox.py:400 | construction_power: n.energy=max(e,5.0) 硬赋值 |
| HC-036 | MEDIUM | DIRECT_INJECT | shadow_sandbox.py:453 | ecm._temperature /=3（假设均分，无 BIO:）|
| HC-037 | MEDIUM | LOGIC_REPLACES_CIRCUIT | shadow_sandbox.py:490 | xin 符号乘积决定 silent synapse 再激活（应为 Hebbian）|
| HC-038 | MEDIUM | LOGIC_REPLACES_CIRCUIT | hebbian.py:957 | _motor_efficacy<0.3 门控有丝分裂（无 BIO:）|
| HC-039 | MEDIUM | SEMANTIC_MATH | variant_adapter.py:617 | MotionState.nu/polarization 用 Python EMA+ratio 计算 |
| HC-040 | MEDIUM | GOAL_HARDCODED | variant_adapter.py:679 | damage = max(0, T-0.8) ReLU（无 TRPV1 MOSFET）|
| HC-041 | MEDIUM | DIRECT_INJECT | variant_adapter.py:1074 | shadow→DA tanh 饱和在 Python 覆盖 Bundle 输出 |
| HC-042 | MEDIUM | LOGIC_REPLACES_CIRCUIT | neuron.py:504 | 能量耗尽时强制 charge×=0.5（无 PHYS:）|
| HC-043 | MEDIUM | LOGIC_REPLACES_CIRCUIT | neuron.py:424,452 | activation 硬钳位±10（应为 Zener-MOSFET）|
| HC-044 | MEDIUM | UNGROUNDED_PARAM | variant_adapter.py:267 | efference copy feedback_gain=0.05, tau=500ms（Cullen 2004 实际≈50ms）|
| HC-045 | MEDIUM | UNGROUNDED_PARAM | hebbian.py:163 | MFD alpha/beta（无推导，enc/col 非对称无依据）|
| HC-046 | MEDIUM | UNGROUNDED_PARAM | compensation.py:52+ | 6个补偿组件20+个未接地参数（VR/BiasCS/D2R/DeC/CRI/DNR）|
| HC-047 | MEDIUM | UNGROUNDED_PARAM | vestibular/chain.py:180+ | v_peak=0.23、b_adapt、synapse_gain=5 均为工程调参 |
| HC-048 | MEDIUM | UNGROUNDED_PARAM | somatosensory/chain.py:103+ | 3个神经元类型 VR 参数复制粘贴（无各类型生物推导）|
| HC-049 | MEDIUM | UNGROUNDED_PARAM | bundle.py:52+ | plasticity_by_stage、MATURATION_TICKS=500等7个未接地参数 |
| HC-050 | MEDIUM | UNGROUNDED_PARAM | world.py:33+ | E_HALF=10、friction=0.5、V_REF=0.5等7个 world 参数 |
| HC-051 | MEDIUM | UNGROUNDED_PARAM | neuron.py:90+ | basal_cost=0.0002、trace_tau、activation_ema=0.01（dt耦合 bug）|
| HC-052 | LOW | SUSPICIOUS | variant_adapter.py:600 | ms.thermal=T_prev-methylation（不确定是否被行为门控使用）|
| HC-053 | LOW | SUSPICIOUS | variant_adapter.py:642 | _motor_efficacy 只写不读（疑似死代码或隐藏依赖）|
| HC-054 | LOW | SUSPICIOUS | shadow_sandbox.py:574 | get_state() 语义标签（'contracting'等）可能被行为门控使用 |
| HC-055 | LOW | LOGIC_REPLACES_CIRCUIT | bundle.py:272 | 字符串 role='cross_axis' 决定 plasticity rule |
| HC-056 | LOW | UNGROUNDED_PARAM | hebbian.py:267+ | XI_SPROUT=0.3、ZCR_PROTECT=0.15、_base_col_mot_gain=5 |
| HC-057 | LOW | UNGROUNDED_PARAM | shadow_sandbox.py:90+ | shadow 层神经元参数、initial_weight、K_MM_LIMIT=1000 |
| HC-058 | LOW | UNGROUNDED_PARAM | compensation.py:180 | tau_agc=0.1（自注释 UNGROUNDED，时间压缩 10^6×）|
| HC-059 | LOW | SUSPICIOUS | compensation.py:279+ | CRI 硬重置（vs RC drain）；BiasCS 绕过 Bundle 注入 |
| HC-060 | LOW | LOGIC_REPLACES_CIRCUIT | somatosensory/chain.py:19+ | 侧抑制邻接图硬编码 front↔back 不相邻（无 BIO: 说明）|

---

### HC-004: Phase 8 soma_to_da 初始权重为 0（未解释行为）
- **位置**: `nexus_v1/circuit/variant_adapter.py`，`_init_da_circuit()`
- **问题**: Phase 8 with RC-4 中 `_get_weights()` 在 step=0 返回全 0，而 `initial_weight=0.5` 应产生 hash 扰动后约 0.375–0.625 的值。根因未查清（可能是 da_list 初始化时序问题）
- **代码标注**: 无（需要调查）
- **影响**: 权重从 0 增长到 0.52 的 STDP 动态与从 0.5 开始不同；RC-4 的结果可能依赖于这一未记录的行为
- **重构目标**: 查清根因，记录到 DEG-003。如属 bug 需修复，如属预期行为需文档化
- **DEG 关联**: DEG-003
- **优先级**: 中（影响实验可重复性）

---

## 历史硬编码（已解决）

| 编号 | 描述 | 解决方式 | 时间 |
|------|------|---------|------|
| HC-H01 | shadow_to_da W=1.0→0.1（DA 饱和）| 参数修正 | 2026-06 |
| HC-H02 | thermo_to_relay gain=3.0→0.3（relay 饱和）| RC-2（FIX-001）| 2026-07-01 |
| HC-H03 | D2R 参数 g×τ=50→2（DA 过抑制）| RC-3（FIX-002）| 2026-07-01 |

---

## 重构原则

当重构硬编码时，遵循以下优先级：

1. **先查生物文献**（原则 1/5）：找到对应真实生物结构，引用 REF/BIO 标注
2. **换成 SynapticBundle + 物理参数**（原则 9）：不用 Python 数学替代电路
3. **运行熵审计**（原则 2）：确认 signal_depth 和 energy 不退化
4. **更新注册表**（原则 6/8）：更新本文件 + DEG + FIX

> **提醒**：重构不是"删掉就好"，是用**正确的生物结构**替换。不能引入新的未接地参数。
