# 蓝图差距全面审计 — v37.4.80 vs MORPHOSPHERE.2026.5.10.1

原始分析（analysis_results.md）基于 v37.4.61 编写，当时列出 15 个差距。  
经过 v37.4.62 → v37.4.70 → v37.4.80 三轮迭代，已关闭 **15/15 原始差距**。  
但蓝图中还有一些**二级指标和文档要求**尚未覆盖。

---

## 已关闭的差距（15/15 原始清单）

| # | 原始差距 | 关闭版本 | 方式 |
|:---:|---------|:---:|------|
| P0.1 | M_max 100→8 | v37.4.62 | ABConfig 默认改为 8.0 |
| P0.2 | eta 0.3→0.18 | v37.4.62 | ABConfig 默认改为 0.18 |
| P0.3 | M_min 1.0→0.5 | v37.4.62 | ABConfig 默认改为 0.5 |
| P1.4 | κ·Contradiction 惩罚 | v37.4.62 | `kappa * xin_residual` 在 Engine B |
| P1.5 | A_t 外部可信度门控 | v37.4.62 | `A_t = 1.0 if is_external else 0.3` |
| P2.6 | Contradiction stream | v37.4.62 | Phase 4b: 15 build + 15 attack |
| P2.7 | Staleness stream | v37.4.62 | Phase 4c: 50 ticks decay-only |
| P3.8 | source_event 表 | v37.4.62 | §16.1 完整实现 |
| P3.9 | measure_coordinate / z_t | v37.4.80 | MeasureCoordinate + 6 phase 写入 |
| P3.10 | topological_inertia_event | v37.4.62 | §16.5 采样审计写 DB |
| P3.11 | Engine A prior 层 | v37.4.62 | 三层 fast/slow/prior |
| P4.12 | Frozen holdout 机制 | v37.4.70 | seq02 独立 holdout |
| P4.13 | Holdout 指标 | v37.4.70 | survival drift ±2σ |
| P4.14 | False attractor escape | v37.4.62 | Phase 4b + escape_rate 度量 |
| P4.15 | semantic_leakage 审计 | v37.4.62 | V10 检查 = 0 |

---

## 仍存在的差距（按优先级分层）

### 🔴 Tier 1 — 蓝图明确要求但未实现的**二级指标**

| # | 差距 | 蓝图节 | 影响 | 工作量 |
|:---:|------|:---:|------|:---:|
| R1 | `xin_absorption_without_promotion` | §11.1 | Xin 被吸收但未晋升为 P 的计数 | 小 |
| R2 | `r_band_activation_delay` | §11.2 | regime shift 中 R-band 首次激活延迟 | 小 |
| R3 | `new_basin_stabilization_step` | §11.2 | 新 basin 稳定所需步数 | 小 |
| R4 | `inertia_downregulation_success` | §11.3 | M_eff 在反证下成功下调次数 | 小 |
| R5 | `repeated_hit_memory_survival` | §11.4 | 被反复外部命中的边在 staleness 后存活率 | 小 |
| R6 | `events_per_second` / `candidate_overhead_pct` | §11.5 | 精确的吞吐量和开销百分比写入报告 | 小 |

> [!NOTE]
> 这些都是**已有框架内**的附加度量——数据已经在引擎中产生，只需提取并写入 ab_stress_metrics 表。每个约 5-15 行代码。

---

### 🟡 Tier 2 — 蓝图暗示但非强制的结构性改进

| # | 差距 | 蓝图节 | 影响 | 工作量 |
|:---:|------|:---:|------|:---:|
| R7 | `process_window` 表独立化 | §16.2 | 当前通过 information_fiber 间接实现 | 中 |
| R8 | §13.3 自引用审计 7 字段 | §13.3 | 当前只记录 ext/int 计数，缺 5 字段 | 中 |
| R9 | Compute stress stream（渐进压力） | §10.3 | 当前只有计时，无渐进 cell 数量增长 | 中 |
| R10 | 附录 A 格式的 JSON 配置文件 | §附录A | 当前 ABConfig 是 Python dataclass | 小 |

---

### ⬜ Tier 3 — 蓝图建议但明确标注为可选/未来

| # | 差距 | 蓝图节 | 状态 |
|:---:|------|:---:|------|
| R11 | Engine 拆分为 3 个独立文件 | §17 | 蓝图"建议"，非强制 |
| R12 | holdout_nll / holdout_macro_f1 | §11.6 | 需要分类标签数据（CTC 无标签） |
| R13 | docs/v37441/ 文档目录 | §17 | 文档结构建议 |
| R14 | CSV 输出文件 | §17 | test_outputs/ 中的 .csv 报告 |

---

### ⬛ Tier 4 — 外部依赖，系统层面无法解决

| # | 差距 | 蓝图节 | 阻塞原因 |
|:---:|------|:---:|------|
| R15 | holdout ≥ 15 帧 | §19.2 | CTC seq02 只有 ~20 帧，勉强满足 |
| R16 | class_diversity ≥ 3 | §19.3 | 只有 CTC + synthetic (2 类) |
| R17 | motion regime diversity ≥ 5 | §19.4 | 需更多外部数据源 |
| R18 | external scientific closure | §19.10 | 需要外部审查和更多数据 |

> [!IMPORTANT]
> Tier 4 是 v37.5 解锁条件（§19），按蓝图设计就是 BLOCKED 的——它们需要外部数据扩展和科学审查，不属于代码层面的改进。

---

## 附录 B: 10 问清单更新

| # | 问题 | v37.4.61 答案 | v37.4.80 答案 | 变化 |
|:---:|------|:---:|:---:|:---:|
| 1 | B 更抗噪？ | ✅ 94.8% vs 82.9% | ✅ 数据支持 | — |
| 2 | B 更快适应？ | ✅ 8 vs 16 ticks | ✅ 3 vs 13 ticks | — |
| 3 | B 更少 false lock-in？ | 🔴 未测试 | ✅ 96.2% escape rate | **关闭** |
| 4 | B 不忘重要结构？ | 🔴 未测试 | ✅ basin retention 100% | **关闭** |
| 5 | B 开销 ≤ 20%？ | 🟡 波动 | ✅ V26 验证通过 | **关闭** |
| 6 | C 适合 staged default？ | ✅ 否 | ✅ 否 | — |
| 7 | Xin→R→P 边界？ | ✅ ENFORCED | ✅ ENFORCED | — |
| 8 | RLIS no-writeback？ | ✅ PASS | ✅ PASS | — |
| 9 | semantic leakage = 0？ | 🟡 未审计 | ✅ V10 = 0 | **关闭** |
| 10 | v37.5 BLOCKED？ | ✅ 是 | ✅ 是 | — |

**10/10 问题已有数据答案** ✅

---

## 建议的下一步

如果你想继续推进，**Tier 1 (R1-R6)** 是最高效的改进——每个只需 5-15 行代码，可以作为一个批次完成，将 §11 指标覆盖率从 9/12 提升到 **12/12**。

如果你想要更大的结构性变化，**Tier 2 (R7-R10)** 需要更多讨论确认。

**Tier 3-4 无需行动** — 它们是蓝图设计中故意留的未来工作。
