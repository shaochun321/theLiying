# v40.8 Implementation Plan (Consolidated)

## Phase 1: 结构完整性收尾 + 凋亡机制

**范围**：CircuitLayer 动力学 + 神经元凋亡 + inter_layer pruning

### 1A. CircuitLayer 动力学

**问题**：三元结构中最后一个没有动力学的原语。

#### [MODIFY] [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py)

为 CircuitLayer 添加：
- `layer_temperature`: 由层内 neuron heat 聚合生成，向全局 T 松弛衰减，耦合到层内 STDP
- `layer_occupancy`: 活跃神经元比例 EMA，耦合到拥塞抑制

将 maintain() 中已有的 per-layer heat 聚合从 `self._temperature` 迁移到 `layer.layer_temperature`。

### 1B. 结构性退化级联（替代“细胞死亡”）

**物理动机**：真实神经系统的“遗忘”不是神经元死亡，而是突触退缩→局部环路崩塔→主环路微调的渐进级联。

**实现：三级级联**

**① 突触收缩**（Synaptic Contraction）
- 弱 bundle 不是瞬间 prune → ghost，而是**渐进收缩**
- 每 tick：bundle_strength < 0.1 的束，权重 ×0.99（轴突退缩代理）
- transport_cost ×1.05（退缩的突触更贵）
- 只有持续收缩到 strength < 0.02 才 ghost
- degraded_from = "synaptic_elimination_complement_tagging"

**② 局部环路崩塔**（Local Circuit Collapse）
- 当一个神经元的所有连接 bundle 总强度 < 阈值：
  - 神经元进入 "quiescent" 状态（不是死亡，是休眠）
  - 能量停止恢复（代谢撤离）
  - 不参与 transport / STDP
  - 但保留结构位置（可以被重新激活）
- degraded_from = "metabolic_withdrawal_quiescence"

**③ 粗粒度合并**（Coarse-grained Merge）— 重整化群代理
- 当同层多个神经元激活模式高度相似（cos > 0.95）：
  - 合并为单个有效神经元（继承联合连接）
  - 这是结构性的 renormalization：粗粒度切分
  - 减少节点数而保留拓扑信息
- degraded_from = "cortical_renormalization_coarse_graining"

> [!NOTE]
> ③ 的实现复杂度较高（需要重路由 bundle），先实现 ①②，③ 观察数据后再决定。

### 1C. Inter-layer bundle pruning（来自处刑一）

**问题**：`inter_layer_bundles` 列表没有 pruning。

**实现**：在 maintain() 末尾，对 `self.inter_layer_bundles` 执行与层内 bundle 相同的 `should_prune()` 检查。被 prune 的束同样进入 ghost 状态。

### 验证

- 运行 run_v40_integrated.py，确认：
  - CircuitLayer 有 temperature/occupancy 输出
  - 无神经元死亡（当前 energy 最低 0.045，应该不触发凋亡）
  - inter_layer pruning 逻辑存在但不触发（束仍然活跃）

---

## Phase 2: 结晶神经元成熟级联

**范围**：cx_ 成熟 + 增长容量控制

### 2A. cx_ 成熟条件 + 对数层级

cx_ 神经元使用与普通 spine 相同的 `try_mature()` 逻辑。

**调整**：
1. cx_ 的初始 potential 从 constituent dims 的 potential 均值获得
2. 对数层级放大：成熟阈值用 log(N) 而非线性 N
   - spine→column: potential > log2(维度数) × base_threshold
   - 这意味着7维的系统需要 ~2.8× base，14维需要 ~3.8×
   - 不是线性累进，而是结构性的对数压缩

### 2B. 增长容量控制

**问题**：cx_ 数量无上界（处刑一的有效部分）。

**实现**：结晶化前检查当前 encoding 层 cx_ 数量。如果 cx_ 数量 ≥ 当前层 z_t 维度数的 2 倍（当前=14），跳过结晶。这是按比例而非固定上限——规模随系统复杂度自然缩放。

### 验证

- cx_ 是否有可能成熟为 column
- 结晶数量是否被 cap 限制

---

## Phase 3: Pipeline 集成

**范围**：v40 circuit 嵌入 pipeline_engine 主循环

**决策**：
- circuit 状态**不持久化**（每次 run 从零构建）。原因：物理规则仍在迭代，持久化的旧 circuit 会与新规则不兼容。
- 3D 物理系统集成在 Phase 3 之后。原因：先确保处理器完整，再替换输入源。

---

## Phase 4: 稳定性压力测试

**时间尺度**：500 ticks → 2000 ticks

**决定理由**：
- 结晶需要 50 ticks 触发，500 ticks = ~10 代结晶/衰亡周期
- Bundle inertia 恢复到 5.0 需要 ~600 tick stable
- 2000 ticks 能暴露所有慢变量（energy, inertia, PRP）的极端行为
- 超过 2000 无额外信息增益

**监控指标**：energy 分布、cx_ 数量、bundle 总数、F、avg_cos 随 tick 的时间序列。

#### [MODIFY] [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py)

添加 tick snapshot 每 100 tick 记录一次系统状态。
