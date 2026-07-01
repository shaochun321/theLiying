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
