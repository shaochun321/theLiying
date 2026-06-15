# v40.8+ Next Phase Plan

## Current State (v40.7h.1)

系统已达到**结构动力学完备**状态：
- **40 个神经元**（35 原始 + 5 结晶），全部存活
- **avg cos = 0.251**（历史最佳），**Xin tension = 1.88**（历史最低）
- **20 个降级代理模块**，全部标注 `degraded_from`
- **完整的自生长循环**：共激活 → 收敛 → 结晶 → column 前馈 → PRP → 果实

> [!IMPORTANT]
> 以下计划按**优先级**排序。Phase 1 是结构完整性的最后缺口。Phase 2 是最具物理意义的扩展。Phase 3-4 需要确认方向。

---

## Phase 1: CircuitLayer 动力学（结构完整性收尾）

**问题**：`CircuitLayer` 是三个元结构中唯一没有任何动力学的原语。它只是 dict + list 的容器。

**物理动机**：皮层的不同层有不同的处理特性：
- Layer 4（signal_entropy）：接受丘脑皮层输入，高敏感度
- Layer 2/3（encoding）：侧向处理，可塑性最高
- Layer 5/6（column）：输出层，稳定性最高，反馈到丘脑

**实现**：

#### [MODIFY] [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py)

为 CircuitLayer 添加层级动力学字段：

```python
@dataclass
class CircuitLayer:
    layer_id: str
    neurons: Dict[str, MetaNeuron] = field(default_factory=dict)
    bundles: List[MetaSynapticBundle] = field(default_factory=list)
    
    # v40.8: Layer-level dynamics
    layer_temperature: float = 1.0     # 生成: 神经元 heat 聚合; 衰减: 向全局 T 松弛
    layer_plasticity: float = 1.0      # 生成: 活动驱动; 衰减: 向基线松弛; 耦合: STDP 倍率
    layer_occupancy: float = 0.0       # 生成: 活跃神经元比例; 衰减: EMA; 耦合: 拥塞抑制
    # DEGRADED: cortical layer identity → proxy as float fields
    # degraded_from = "cortical_laminar_identity_dynamics"
```

**影响范围**：maintain() 中 heat 聚合已经是 per-layer 的，只需将结果写入 `layer_temperature` 而不是 `self._temperature`。

---

## Phase 2: 结晶神经元成熟级联

**问题**：cx_ 神经元的 activation_count 已达 60-94（远超成熟阈值 20），但 potential 不够。它们参与计算但无法成为 Column。

**物理动机**：association cortex 中的收敛区域最终形成**稳定的功能柱**（如 FFA、PPA）。结晶 → 成熟 → Column 特权 → 发射 PRP → 捕获更远的果实 = 层级化抽象的涌现。

**实现**：

1. 降低 cx_ 神经元的成熟阈值（收敛区更容易巩固）
2. cx_ 成为 Column 后，它们发射 PRP，可以被其他 cx_ 的 dormant fruit 捕获
3. cx_ Column 之间形成新的 convergence → 更高阶 cx_cx_ 结晶

> [!WARNING]
> 这可能导致指数增长。需要 **capacity cap**：每层最多 N 个 cx_ 神经元。

---

## Phase 3: Pipeline 集成

**问题**：`pipeline_engine.py` 仍然是 v36.6/36.7，没有使用 v40 的 Hebbian circuit。当前 circuit 只在 `run_v40_integrated.py` runner 中运行。

**范围**：

1. 将 circuit 的 `run_tick()` 嵌入 pipeline 的 per-window processing loop
2. 将 pipeline 的 entropy ledger 作为 circuit 的 `_entropy_ledger_proxy`
3. 将 circuit 的观测输出（z_t profiles, convergence nodes, crystal neurons）写入 pipeline DB

> [!IMPORTANT]
> 这是个重大集成任务。建议在 Phase 1-2 稳定后进行。需要确认：
> - pipeline_engine 的 per-window 调用频率与 circuit tick 的对应关系
> - 是否需要 circuit 状态的 DB 持久化（跨 run 的 circuit 记忆）

---

## Phase 4: 长窗口稳定性压力测试

**目标**：验证 v40.7/40.8 的动力学系统在长时间运行（1000+ ticks）下是否稳定。

**关注点**：
- 能量是否趋向平衡而非崩溃或爆炸
- 结晶神经元数量是否收敛
- PRP/果实系统是否持续产生有意义的结构变化
- Bundle inertia 是否在合理范围内振荡
- Free energy F 是否保持正值

**方法**：修改 runner 循环次数为 1000+ 轮，记录每 100 tick 的系统状态快照。

---

## 估计工作量

| Phase | 复杂度 | 预计时间 | 依赖 |
|-------|:------:|:--------:|------|
| 1: CircuitLayer 动力学 | 中 | 1 轮 | 无 |
| 2: 结晶成熟级联 | 中 | 1 轮 | Phase 1 |
| 3: Pipeline 集成 | **高** | 2-3 轮 | Phase 1-2 |
| 4: 压力测试 | 低 | 1 轮 | Phase 1-2 |

## Open Questions

1. **Phase 2 的增长控制**：每层 cx_ 神经元上限设为多少？建议 encoding 层 ≤ 20，column 层 ≤ 10。
2. **Phase 3 的持久化**：circuit 状态是否应该在 runs 之间持久化？还是每次 pipeline 运行重新构建 circuit？
3. **Phase 4 的时间尺度**：1000 ticks 足够吗？是否需要 adaptive time stepping？
4. **3D 物理系统集成**：之前的对话讨论了 3D spring-repulsion 粒子系统和 LIF 动力学。这些应该在 Phase 3 之前还是之后集成？
