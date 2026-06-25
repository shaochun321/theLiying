# 赫布闭环 + 熵账本驱动 — 实施计划

> 目标: 让 Morphosphere 从"有结构"变成"结构在运转"

## User Review Required

> [!IMPORTANT]
> 这三个修正按优先级排列。每一个都可以独立实施和验证。
> 请确认：
> 1. 是否全部执行，还是只做 Priority 1?
> 2. FHPMS 权重回流的门控策略是否接受（赫布记忆越强 → θ 越宽松 → 传输越容易通过）?
> 3. 熵账本驱动方向是否接受（pi_X > 0.4 时抑制新假设生成）?

---

## Priority 1: 赫布闭环 — FHPMS 权重回流到管线决策

**核心问题**: `FHPMSWriter.write_hebbian_weight()` 写了权重，但 `read_potential_guided()` 从未被调用。

### 改动

#### [MODIFY] [pipeline_engine.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/pipeline_engine.py)

1. 在 `write_transport()` 开头添加 FHPMS 权重查询:
   - 查询 `fhpms_hebbian_association_weight` 表获取当前 run 中已积累的权重
   - 计算 **赫布记忆强度** = AVG(weight_value) × 活跃权重数
   - 用记忆强度调制传输门控 θ:
     - `theta_adjusted = theta_base × (1 + hebbian_memory_strength × 0.3)`
     - 赫布记忆越强 → θ 越宽松 → 已记忆的传输路径更容易通过
   - 这实现了"经验影响感知"的闭环

2. 在 `write_hypotheses()` 中添加赫布先验:
   - 查询当前假设成员节点的赫布关联历史
   - 权重 > 0.3 的关联 → support_score 加成 10%
   - 这实现了"记忆增强确认"的闭环

#### [MODIFY] [writer.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/src/morphosphere/active_exec/runtime/fhpms/writer.py)

- 完善 `read_potential_guided()`:
  - 接受 `cell_uids` 参数，查询与这些节点相关的权重
  - 返回结构化的赫布先验信息
  - 添加 `read_hebbian_memory()` 方法: 查询两节点间的历史权重

---

## Priority 2: 熵账本驱动管线行为

**核心问题**: `FreeEnergyRouter.route_delta_f()` 计算了 pi_P/pi_R/pi_X/pi_M/pi_U 分配，但分配结果从未被消费。

### 改动

#### [MODIFY] [pipeline_engine.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/pipeline_engine.py)

1. 在每个 window 的管线末尾调用 `FreeEnergyRouter`:
   - 用该窗口的实际 p_measure, r_measure, x_measure 作为输入
   - 获取 `pi_P, pi_R, pi_X` 分配

2. 用路由结果影响下一窗口:
   - 当 `pi_X > 0.4` → 增加 Xin 的 decay_rate (加速清理残差)
   - 当 `pi_P > 0.5` → 降低下一窗口 P_frozen 的传输支持阈值 (加速 P 确认)
   - 当 `pi_R > 0.4` → R_frozen 的 persistence 要求从 k>=4 降到 k>=3

3. 将路由历史写入管线的审计日志

#### [MODIFY] [engines.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/src/morphosphere/active_exec/runtime/spms/engines.py)

- 在 `FreeEnergyRouter` 添加 `get_last_routing()` 方法，返回最近一次路由结果
- 添加 `get_cumulative_pressure()` 方法，返回近 N 窗口的累积压力

---

## Priority 3: 统一赫布超图入口

**核心问题**: HebbianSignalTransform, FHPMS hebbian_weight, Engine A/B/C 三套独立系统。

### 改动

#### [NEW] [hebbian_hypergraph.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_hypergraph.py)

创建统一入口类 `HebbianHypergraph`:

```python
class HebbianHypergraph:
    """统一的赫布超图 — 所有赫布系统的唯一入口。

    三种超边类型:
      1. signal_edge: W_signal (6×7) — 信号→z_t 映射
      2. temporal_edge: FHPMS hebbian_weight — 时序 block 关联
      3. structural_edge: Engine B weights — 拓扑惯性

    所有边共享:
      - d_σ_t 加权的衰减
      - Φ(t) 调制的更新
      - 统一的 get_memory_strength() 查询接口
    """
    def __init__(self, signal_transform, fhpms_writer, engine_b=None):
        self.signal = signal_transform    # W_signal (6×7)
        self.temporal = fhpms_writer       # FHPMS 权重
        self.structural = engine_b         # Engine B 拓扑惯性

    def query_memory(self, entity_ids):
        """统一查询: 给定实体ID，返回所有三层的赫布记忆强度。"""
        ...

    def update_all(self, signal_values, z_t, block_id_prev, block_id_curr):
        """统一更新: 信号更新 W_signal，时序更新 FHPMS，结构更新 Engine B。"""
        ...

    def get_d_sigma_weighted_strength(self, entity_ids):
        """d_σ_t 加权的综合记忆强度 — 用于管线决策。"""
        ...
```

- 让 `pipeline_engine.py` 和 `run_v38_allen_integration.py` 通过这个统一入口访问赫布系统
- 不删除任何现有模块 — HebbianHypergraph 是聚合层，不是替代层

---

## Verification Plan

### 自动化测试

1. **闭环验证**: 运行 Allen Integration，检查:
   - FHPMS 权重被查询的次数 > 0
   - 传输 θ 在后期窗口与前期窗口有差异（赫布记忆在起作用）
   - support_score 在赫布权重强的区域有提升

2. **熵驱动验证**: 运行多窗口管线，检查:
   - FreeEnergyRouter 被调用且输出被记录
   - pi_X > 0.4 时 Xin decay_rate 确实增加了
   - 路由历史与管线行为变化的相关性

3. **回归**: 全部现有 v38 测试必须通过（12/12 + 7/7 + 10/10）

### 手动验证

- 检查 `fhpms_hebbian_association_weight` 表中的权重是否在多次运行后收敛
- 检查 θ 调制是否在合理范围内（不会让所有传输都通过或全部拒绝）
