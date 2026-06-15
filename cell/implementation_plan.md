# Morphosphere v37.4.50 — 能量基底 + 拓扑惯性 A/B 压测实施计划

## 背景与兼容性分析

`2026.5.10.1.txt` 提出了 HG-FHPMS 的理论升级路线，核心是三项重构：
1. **能量基模型（EBM）**：将离散测度哈希升级为连续能量面
2. **Oja 法则 + 遗忘衰减**：替换纯增强 Hebbian
3. **拓扑惯性 $\mathcal{M}(\Phi)$**：用运动势内生定义"速度"，取代硬编码时钟

### 与现有路线的兼容性判定：✅ 不冲突

| 现有路线组件 | 2026.5.10.1 要求 | 判定 |
|---|---|---|
| v37.4.21 Variational EM | 保持不变，EM 是外部分析层 | ✅ 正交 |
| BayesianMotionRecognizer | 保持不变，运动识别是底层信号源 | ✅ 正交 |
| FormulaCandidateCompetition | 竞赛框架可复用为 A/B 的评估机制 | ✅ 可整合 |
| FHPMS Hebbian 权重更新 | **直接升级目标**：加入衰减项 + 惯性分母 | ⬆️ 演进 |
| RLIS Minkowski 审计 | 保持不变，RLIS 仍为只读旁路 | ✅ 正交 |
| P/R/Xin 分类逻辑 | **守住"Xin→R→P"路径约束**，已有 `pr_confirmation_graph` 支撑 | ✅ 加固 |
| 非语义坐标原则 | **核心不变**，坐标仍为转换代价 | ✅ 一致 |
| SQLite 存储层 | 新增表，不修改主线存储 | ✅ 无破坏 |

> [!IMPORTANT]
> 文档最终立场极其务实：**不急于上"优美公式"，而是要求通过 A/B 双盲对照来判决**。这与我们一贯的"数据驱动验证"工程纪律完全一致。

---

## 从实际出发的优化与取舍

文档的理论纯度极高，但直接落地会遇到以下工程现实：

### 1. 放弃全局能量面的"一步到位"

文档要求"构建全局标量函数 $E(x)$"——这在数百节点的 SQLite 管线中直接用矩阵求解不现实。

**实际方案**：用**局部势能差（pairwise potential difference）** 替代全局能量面。在已有的 `fhpms_distance_spacetime_potential` 表基础上，对每对相邻 block 计算局部势能，并通过 Hebbian 更新传播。这在物理上等价于 lattice Boltzmann 的离散近似。

### 2. 惯性质量 $\mathcal{M}(\Phi)$ 需要夹紧

文档自己警告了"质量坍缩"和"质量奇点"风险。

**实际方案**：$\mathcal{M}(\Phi) = 1 + \alpha \cdot \Phi$（线性模型），严格夹紧在 $[1, M_{max}]$。$M_{max}$ 初始设为 100，通过 A/B 测试调参。避免指数/幂律导致的数值灾难。

### 3. 遗忘机制用拉普拉斯平滑而非主动删除

**实际方案**：每轮 Tick 对所有 Hebbian 权重施加 $w_{ij} \leftarrow w_{ij} \times (1 - \epsilon)$，$\epsilon = 0.02$。这是一阶近似的势能面扩散，计算成本 $O(N)$。

### 4. A/B 测试复用现有竞赛框架

不新建测试框架。将 `FormulaCandidateCompetitionEngine` 扩展为支持"引擎级别"的 A/B，复用其 round-evaluation-selection 机制。

---

## 变更方案

### 组件一：Hebbian 引擎升级（核心）

#### [MODIFY] [pipeline_engine.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/pipeline_engine.py)

在 `write_v374_fhpms_rlis_trace()` 中的 Hebbian 更新部分，引入两项改进：

**A. Oja 衰减项（遗忘）**：
```python
# 现有: weight = eta * a_i * a_j * freeze_bonus * cross_domain_bonus
# 升级后 (惯性方案B):
decay = lambda_decay * w_prev  # Oja decay term
force = eta * a_i * a_j * freeze_bonus * cross_domain_bonus - decay
M_phi = 1.0 + alpha * cumulative_potential  # 惯性质量，夹紧 [1, M_max]
M_phi = max(1.0, min(M_max, M_phi))
delta_w = force / M_phi
weight = max(0.01, min(1.0, w_prev + delta_w))
```

**B. 全局衰减扫描（热力学风化）**：
新增函数 `apply_global_hebbian_decay(conn, run_id, decay_factor=0.98)`，每个 window 结束后调用，对所有 Hebbian 权重统一乘以 decay_factor。

---

#### [NEW] `hebbian_ab_engine.py`

双盲 A/B 引擎，实现两套完全隔离的 Hebbian 更新逻辑：

```python
class HebbianEngine_A_ManualStrata:
    """基线A：机械分层。快速层每 Tick 更新，慢速层每 1000 Tick 吸收。"""
    
class HebbianEngine_B_TopologicalInertia:
    """候选B：拓扑惯性。ΔW = Force / M(Φ)，无硬编码时钟。"""
```

两者共享相同的输入接口：`(from_id, to_id, a_i, a_j, gamma, freeze_bonus, cross_domain_bonus)`。

---

### 组件二：A/B 评估指标

#### [NEW] DB Migration: `025_v37450_ab_test.sql`

```sql
-- A/B 引擎权重镜像表
CREATE TABLE IF NOT EXISTS v37450_ab_weight_mirror (
    record_id TEXT PRIMARY KEY,
    run_id TEXT, engine TEXT,  -- 'A_strata' or 'B_inertia'
    from_entity_id TEXT, to_entity_id TEXT,
    weight_value REAL, inertia_mass REAL,
    cumulative_potential REAL, tick INTEGER, created_at TEXT
);

-- A/B 指标表
CREATE TABLE IF NOT EXISTS v37450_ab_metric_log (
    record_id TEXT PRIMARY KEY,
    run_id TEXT, engine TEXT, tick INTEGER,
    p_core_survival_rate REAL,    -- 指标1: 噪音风暴下P-Core存活率
    adaptation_latency REAL,       -- 指标2: 新规律响应延迟(Tick数)
    compute_overhead_ms REAL,      -- 指标3: 计算开销
    weight_entropy REAL,           -- 权重分布熵(辅助)
    dead_node_count INTEGER,       -- 死节点数(惯性奇点监控)
    created_at TEXT
);

-- A/B 最终判决
CREATE TABLE IF NOT EXISTS v37450_ab_verdict (
    verdict_id TEXT PRIMARY KEY,
    run_id TEXT,
    winner TEXT,  -- 'A_strata', 'B_inertia', or 'DRAW'
    survival_a REAL, survival_b REAL,
    latency_a REAL, latency_b REAL,
    overhead_a_ms REAL, overhead_b_ms REAL,
    rationale TEXT, created_at TEXT
);
```

---

### 组件三：A/B 测试运行器

#### [NEW] `run_v37450_ab_test.py`

完整的 A/B 测试管线：

1. **Phase 0**: 标准管线（复用 v37.4.21 流程）生成基础数据
2. **Phase 1**: 双引擎初始化，从相同的初始权重状态出发
3. **Phase 2**: 正常运行 200 Tick（双引擎并行处理同一数据流）
4. **Phase 3**: 噪音风暴测试（500 Tick 纯随机 Xin）→ 测量 P-Core 存活率
5. **Phase 4**: 规律突变测试（突然改变输入拓扑，持续 200 Tick）→ 测量响应延迟
6. **Phase 5**: 计算开销测量 → CPU 时间对比
7. **Phase 6**: 判决输出

---

### 组件四：马尔可夫毯约束加固

#### [MODIFY] [pipeline_engine.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/pipeline_engine.py)

在 `write_hypotheses()` 中硬编码 **"Xin → R → P" 路径约束**：

```python
# 铁律：Xin 绝不允许直接跳过 R 转化为 P
# 现有逻辑已部分满足（k >= 3 才能 P_frozen），但需强化为：
# 1. 任何 P_frozen 必须有对应的 R_frozen 前驱
# 2. 新增 xin_to_p_violation_count 监控
```

---

## 不改动的部分（确认不冲突）

| 组件 | 理由 |
|---|---|
| `variational_em_engine.py` | EM 是外部分析层，与 Hebbian 引擎正交 |
| `motion_recognition_engine.py` | 底层运动识别不受 Hebbian 策略影响 |
| `formula_candidate_registry.py` | 竞赛框架保持不变，A/B 引擎是新维度 |
| RLIS 全链路 | 只读旁路，不受影响 |
| v36.6/v36.7 硬化层 | 治理层不变 |

---

## 验证计划

### 自动化测试

```bash
# 1. 运行 A/B 测试
python run_v37450_ab_test.py

# 2. 检查判决
python -c "import sqlite3; c=sqlite3.connect('v37450_ab_test.db'); print(c.execute('SELECT * FROM v37450_ab_verdict').fetchall())"
```

### 三大判决指标（来自文档）

| 指标 | 判定条件 | 数据源 |
|---|---|---|
| P-Core 存活率 | B > A | 500 Tick 纯噪音后幸存的 P_frozen 数量 |
| 概念响应延迟 | B < A (更快) | 规律突变后首次正确识别的 Tick 数 |
| 计算开销 | B 不超过 A 的 120% | `time.perf_counter_ns()` 测量 |

> [!WARNING]
> 如果 B（拓扑惯性）仅打平或部分胜出，按奥卡姆剃刀原则保留 A（机械分层）。B 必须**三项全胜**才能合并。

### 惯性方案安全护栏

- **死节点监控**：每 100 Tick 扫描 $\mathcal{M} > M_{max} \times 0.9$ 的节点数，报警阈值 10%
- **爆炸监控**：$\Delta W > 1.0$ 的更新自动截断并记录
- **权重熵**：Shannon 熵低于 0.1 时触发全局 re-initialization 告警

---

## Open Questions

> [!IMPORTANT]
> **关于 $M_{max}$ 的选择**：文档未给出具体数值。我建议初始值 100（对应"经历了约 100 次有效冲击后惯性翻倍"），但这需要实际数据校准。是否接受此初始值？

> [!IMPORTANT]
> **关于遗忘速率 $\epsilon$**：文档提到"拉普拉斯平滑"但未给出具体速率。我建议 $\epsilon = 0.02$（每 Tick 衰减 2%），意味着未被加强的权重约 35 个 Tick 后降至原值的 50%。这个速率是否合适？

> [!IMPORTANT]
> **关于测试数据规模**：文档建议 500 Tick 噪音 + 200 Tick 规律突变。考虑到目前管线的 12 窗口规模，我建议先在 60 窗口（与运动识别一致）上运行 A/B，如果结果显著再扩展到 500。是否同意？
