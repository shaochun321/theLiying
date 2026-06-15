# v37.4.93 系统审计 — 五个关键问题

## 1. dead_node_suspected 可还原路径

### 当前状态

**检测已实现，但追溯路径不完整。**

Engine B 在 [engine_b_topological_inertia.py:183-191](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/engine_b_topological_inertia.py#L183-L191) 中正确检测 `dead_node_suspected`（V_Φ 连续 8 tick = 0），并通过 `v_phi_alert_log` 表持久化。

**但存在三个缺口：**

| 层级 | 已有 | 缺失 |
|------|------|------|
| **检测** | ✅ V_Φ = 0 连续 ≥ 8 tick → alert | — |
| **alert 写入** | ✅ `v_phi_alert_log` (tick, alert_type, v_phi 值) | ❌ **缺少 node_id** — 只知道"某处死了"，不知道是哪个节点 |
| **边级还原** | ✅ `WeightEntry` 有 `inertia_mass`, `cumulative_potential` | ❌ **未持久化** — `WeightEntry` 只在内存中，harness 结束后消失 |
| **因果链** | ❌ 无法回答"为什么这个节点死了" | ❌ 需要记录导致 M → M_max 的 Φ 增长轨迹 |

### 赫布超图能做到吗？

**能做到。** `pipe_{ns}_hebbian_weight` 已经保存了每条边的 `from_entity_id` 和 `to_entity_id`。只需：

1. **在 `WeightEntry` 持久化时加入 `inertia_mass` 和 `cumulative_potential` 字段** — 当前只写 `weight_value`
2. **在 `v_phi_alert_log` 中加入受影响的 edge keys** — 当前只记录全局 V_Φ，不知道是哪些边贡献了 dead node
3. **写一个 `dead_node_trace` 表** — 记录 (node_id, M_eff, Φ_cumulative, tick_suspected, tick_recovered_or_null)

### 建议实现

```python
# 新表: pipe_{ns}_dead_node_trace
CREATE TABLE pipe_{ns}_dead_node_trace (
    trace_id TEXT PRIMARY KEY,
    from_entity_id TEXT,
    to_entity_id TEXT,
    inertia_mass REAL,        -- M_eff at detection
    cumulative_potential REAL, -- Φ at detection
    external_hits INTEGER,
    internal_hits INTEGER,
    tick_suspected INTEGER,
    tick_recovered INTEGER,    -- NULL if still dead
    recovery_cause TEXT,       -- 'xin_impact' / 'decay' / NULL
    pipeline TEXT,
    created_at TEXT
);
```

> [!IMPORTANT]
> **优先级：高。** 没有 node-level trace，dead_node_suspected 只是一个全局警报，无法定位具体的"死亡"边。这是赫布超图审计链的一个漏洞。

---

## 2. 存储结构优化

### 当前问题

| 问题 | 严重性 | 详情 |
|------|:------:|------|
| **DB 文件激增** | 🟡 中 | 每次运行生成新 DB（v37492_*.db, v37493_*.db），`db/` 目录已有 5+ 个 GB 级 DB |
| **全局表 vs 命名空间表** | 🟡 中 | 旧管线写 `fhpms_hebbian_association_weight`（全局），新管线写 `pipe_{ns}_hebbian_weight`（命名空间）。两套并存 |
| **WeightEntry 不持久化** | 🔴 高 | Engine B 的 `WeightEntry` 只在内存中（含 M_eff, Φ, external_hits 等），`pipe_{ns}_hebbian_weight` 只存了 weight_value |
| **Oracle 重复计算** | 🟡 低 | `classify_all` 每次从 adapter 重新生成 cells，应该能从 DB 读取已 ingest 的数据 |

### 建议

1. **扩展 `pipe_{ns}_hebbian_weight` 表**：增加 `inertia_mass REAL, cumulative_potential REAL, external_hits INTEGER, stability_ticks INTEGER` 列。这样每条边的完整生命周期状态都可追溯。

2. **统一 DB 策略**：考虑所有管线共用一个 DB（当前已如此），但通过 `pipeline` 列严格隔离。旧全局表保留但标注为 `legacy`。

3. **DB 清理脚本**：`db/` 下的旧版 DB（v37460_*, v37470_*）可以归档到 `db/archive/`。

---

## 3. 降级实现清单

以下是当前代码中**设计意图完整但实现被简化/降级**的部分：

| # | 模块 | 当前状态 | 应有状态 | 恢复难度 |
|:-:|------|---------|---------|:-------:|
| D1 | `_regime_to_prx()` | 静态查表 | 应从赫布权重 + V_Φ 轨迹动态推导 | 中 |
| D2 | `IsolatedPipeline.run_convergence()` | 简化 PRX（无四源融合） | 应使用 `run_triview_prx_round` 的隔离版本 | 中 |
| D3 | `MotionRegimeOracle.classify_all()` | 从 adapter 重新生成 cells | 应从 DB 读取已 ingest 的位移数据 | 小 |
| D4 | Hebbian 权重写入 | 只写 `weight_value` | 应写完整 `WeightEntry` 状态 | 小 |
| D5 | `pipe_{ns}_metric_log` | 只记录 entropy/avg/max | 缺少 d_σ_t 和 V_Φ 统计 | 小 |
| D6 | 跨管线 transport | 不存在 | 蓝图有 `write_cross_domain_transport` 但新管线未使用 | 中 |

> [!TIP]
> **最高 ROI**：D4 (完整 WeightEntry 持久化) — 一次改动同时解决 dead_node 可追溯性和存储完整性。

---

## 4. 未实现的蓝图理念

### 来自 gap_audit.2026.5.13.md 的 R1-R6（Tier 1 二级指标）

| # | 指标 | 蓝图节 | 当前状态 |
|:-:|------|:------:|---------|
| R1 | `xin_absorption_without_promotion` | §11.1 | ❌ Xin 被吸收但未晋升为 P 的计数 |
| R2 | `r_band_activation_delay` | §11.2 | ❌ regime shift 中 R-band 首次激活延迟 |
| R3 | `new_basin_stabilization_step` | §11.2 | ❌ 新 basin 稳定所需步数 |
| R4 | `inertia_downregulation_success` | §11.3 | ❌ M_eff 在反证下成功下调次数 |
| R5 | `repeated_hit_memory_survival` | §11.4 | ❌ 被反复外部命中的边在 staleness 后存活率 |
| R6 | `events_per_second` / `candidate_overhead_pct` | §11.5 | ❌ 精确吞吐量 |

### 来自蓝图但未在 gap_audit 中列出的

| # | 理念 | 蓝图节 | 当前状态 |
|:-:|------|:------:|---------|
| U1 | **Xin 生命周期闭环** | §19.10 | `write_xi_lifecycle_closure()` 函数存在但新管线未调用 |
| U2 | **holdout_nll / holdout_macro_f1** | §11.6 | 需要分类标签数据，CTC 无标签 |
| U3 | **§13.3 自引用审计 7 字段** | §13.3 | 只记录 ext/int 计数，缺 5 个字段 |
| U4 | **渐进压力测试** | §10.3 | 只有固定 cell 数，无渐进增长的压力曲线 |
| U5 | **跨域 transport 对齐** | §12 | `write_cross_domain_transport` 存在但新隔离管线未使用（按设计隔离） |

> [!NOTE]
> R1-R6 都是**已有数据框架内的提取工作**，每个约 5-15 行代码。U1-U5 需要更多设计决策。

---

## 5. 第五个 Regime？

### 当前 Regime 分布（v37493 实测）

```
stationary:  3  (7.5%)
slow_drift: 22  (55.0%)
fast_drift:  3  (7.5%)
jump:       12  (30.0%)
```

**检出 4/6 个已定义 regime**。`oscillation` 和 `diffusion` 未被检出。

### 分析

蓝图 §19.4 要求 `motion_regime ≥ 5`。当前系统定义了 6 个 regime 但只检出 4 个。问题不在于需要"第五个 regime"，而在于：

1. **`oscillation` 未被触发** — 需要数据中存在周期性运动。CTC 细胞和地震数据都以单向运动为主，缺乏振荡模式。

2. **`diffusion` 未被触发** — 需要高方差 + 中等均值的位移模式。当前阈值 `cv > 1.2 && mean_d ∈ [5, 15)` 较严格。

### 建议

**不需要新增第五种 regime 定义**，而是需要：

| 方案 | 效果 | 工作量 |
|------|------|:------:|
| **A: 调低 oscillation/diffusion 阈值** | 从现有数据中提取更多模式 | 小 |
| **B: 在 oracle 中加入频域分析** | 对位移序列做 FFT，检测周期性 → oscillation | 中 |
| **C: 增加第 4 个数据源**（如 EEG 时序） | 自然包含 oscillation | 大 |

> [!TIP]
> **推荐方案 A + B**：调低阈值 + 加入简单的自相关检测（lag-1 autocorrelation < -0.3 → oscillation）。这样不需要新数据源就能满足 `motion_regime ≥ 5`。

---

## 优先级排序建议

| 优先级 | 任务 | 解锁 | 工作量 |
|:------:|------|------|:------:|
| **P0** | WeightEntry 完整持久化 (D4) + dead_node_trace 表 | dead_node 可追溯 | 小 |
| **P1** | oscillation 检测增强 (方案 A+B) | R17 motion_regime ≥ 5 | 小 |
| **P2** | R1-R6 二级指标 | §11 指标覆盖 12/12 | 小×6 |
| **P3** | IsolatedPipeline 四源融合升级 (D2) | PRX 完整性 | 中 |
| **P4** | Xin 生命周期闭环 (U1) | R18 external closure | 中 |
| **P5** | DB 存储整理 | 工程卫生 | 小 |
