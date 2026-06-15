# v37.4.80 — 蓝图合规升级（§16 数据管道 + §18 伪代码对齐 + §11 扩展验收指标）

## 背景

当前系统 v37.4.70 已通过 28/28 基础检查。与蓝图交叉比对（analysis_results.md）仍有以下关键结构性差距需要弥补：

| 差距 | 蓝图节 | 严重性 | 当前状态 |
|------|:---:|:---:|:---:|
| Φ_t 运动势从 z_t 导出 | §4.4 / §18.2 | 高 | 仅用 cumulative_potential 简单累加 |
| §18.1 总入口链路缺失 | §18.1 | 高 | 无 z_t → engine.step(event, z, ledger) 结构 |
| promotion_decision 表 | §16.7 | 中 | 有 verdict 表但无蓝图格式的 promotion_decision |
| ab_stress_metrics 表 | §16.6 | 中 | 通过 metric_log 间接实现 |
| engine_state 表 | §16.4 | 中 | 无 per-tick class-level state 快照 |
| r_band_activation_delay | §11.2 | 中 | 未实现 |
| memory_peak_mb | §11.5 | 低 | 未实现 |

## 执行方案（3 个批次）

---

### Batch 1: z_t 非语义测度坐标全链路集成

**目标**: 将蓝图 §18.1 的伪代码结构在 runner 中落地——每个事件先构建 z_t，再传给引擎。

#### [MODIFY] [hebbian_ab_engine.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/hebbian_ab_engine.py)

- 新增 `MeasureCoordinate` dataclass（7 维 z_t）
- `feed_update()` 增加可选 `z_t: MeasureCoordinate` 参数
- Engine B 的 `compute_motion_potential()` 从 z_t 导出 Φ_t（蓝图 §4.4: 6 项能量组合），替代当前简单的 `cumulative_potential += xin_force`
- Engine B 的 Φ_t 写入 `measure_coordinate` 表（每个 tick 写一次聚合 z_t）

#### [MODIFY] [run_v37450_ab_test.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v37450_ab_test.py)

- Phase 2-4 中每个 update 调用前构建 `z_t`
- `harness.feed_update(..., z_t=z_t)` 传入

---

### Batch 2: §16 审计表完善

#### [MODIFY] [pipeline_engine.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/pipeline_engine.py)

- 新增 migration：`promotion_decision` 表（§16.7 完整格式，含 `compute_overhead_pct`, `holdout_metric_delta`, `chaos_survival_delta` 等）
- 新增 migration：`ab_stress_metrics` 表（§16.6 — 每流每引擎的指标记录）
- 新增 migration：`engine_state` 表（§16.4 — per-tick fast/slow/prior state）

#### [MODIFY] [hebbian_ab_engine.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/hebbian_ab_engine.py)

- `render_verdict()` 同时写入 `promotion_decision` 表
- `log_metrics()` 同时写入 `ab_stress_metrics` 表
- 新增 `flush_engine_state()` 写入 `engine_state` 表

---

### Batch 3: §11 扩展验收指标 + 验证

#### [MODIFY] [run_v37450_ab_test.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v37450_ab_test.py)

- V21: `r_band_activation_delay` — 在 Phase 4 regime shift 中追踪 R-band 边首次出现的延迟
- V22: `memory_peak_mb` — 使用 `tracemalloc` 追踪峰值内存
- V23: `promotion_decision` 表记录验证
- V24: `ab_stress_metrics` 表记录验证
- V25: `engine_state` 表记录验证
- V26: z_t `measure_coordinate` 多记录验证（从 1 条升为每 phase 1 条）

---

## Open Questions

> [!IMPORTANT]
> **Q1**: z_t 的 Φ 导出系数（a1..a6）是否固定使用蓝图 §4.4 的推荐值，还是需要通过 A/B 测试调参？建议初始使用均匀系数（各 1/6），后续根据 holdout 表现调整。

> [!IMPORTANT]  
> **Q2**: `engine_state` 表的写入频率？蓝图暗示 per-tick，但在 ~200 ticks × 3 engines × ~500 edges = 300K 行/run。建议 per-phase 写入（6 条/engine/run = 18 条总计），除非你需要逐 tick 回放。

---

## Verification Plan

### Automated Tests
- 全部 runner 从 `runners/` 目录执行
- `run_v37450_ab_test.py`: 26/26 ALL PASS（原 20 + 6 新增）
- `run_v37460_integrated.py`: 8/8 ALL PASS（无回归）
- z_t `measure_coordinate` 表验证 ≥6 条记录
- `promotion_decision` 表验证 ≥1 条记录

### Manual Verification
- 确认 z_t 7 维向量的各分量非零
- 确认 promotion_decision 的 `compute_overhead_pct` 与实际一致
