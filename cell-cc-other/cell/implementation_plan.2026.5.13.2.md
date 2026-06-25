# v37.4.92 — d_σ_t 内部测度时间 + V_Φ(t) 速度追踪

## 背景

系统处于 **v37.4.91 (48/48 ALL PASS)**。蓝图 §4.5 和 §4.6 定义了两个尚未实现的内部物理量：

- **§4.5 d_σ_t**: 替代绝对 dt 的 6 维内部测度时间增量
- **§4.6 V_Φ(t)**: 运动势在内部测度时间下的"速度"

两者在逻辑上是独立且互补的（V_Φ 依赖 d_σ_t），可以同时实现。

## 用户要求

> [!IMPORTANT]
> **保留历史输出**：不覆盖已有 DB 和报告文件。新运行使用新 DB 文件名，旧数据完整保留。

## 设计原则

1. **候选功能**：d_σ_t 和 V_Φ 作为**审计指标**并行计算，**不替换**主线 tick 机制
2. **不破坏现有**：所有 48 项测试保持通过
3. **保留历史**：Runner 使用带时间戳的新 DB 文件（`v37492_*.db`），旧 DB 不覆盖

---

## Proposed Changes

### Engine 核心层

#### [MODIFY] [hebbian_ab_engine.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/hebbian_ab_engine.py)

**新增 d_σ_t 计算器**（蓝图 §4.5 精确公式）：

```python
@dataclass
class InternalMeasureTime:
    """d_σ_t — Internal measure time increment (blueprint §4.5).
    
    d_σ_t = c1·Δclock + c2·Δsource + c3·Δreproj + c4·ΔΦ + c5·Δrlis + c6·Δchurn
    
    This is NOT physical time — it is a 6-dimensional measure-theoretic 
    time increment that adapts to system dynamics.
    """
    c1: float = 1.0    # normalized_clock_delta weight
    c2: float = 0.8    # source_interval_delta weight
    c3: float = 0.5    # origin_reprojection_delta weight
    c4: float = 1.2    # motion_potential_displacement weight
    c5: float = 0.6    # rlis_interval_delta weight
    c6: float = 0.4    # cross_slice_churn weight
    
    def compute(self, clock_delta, source_delta, reproj_delta,
                phi_displacement, rlis_delta, churn_delta) -> float:
        return (self.c1 * clock_delta + self.c2 * source_delta
                + self.c3 * reproj_delta + self.c4 * phi_displacement
                + self.c5 * rlis_delta + self.c6 * churn_delta)
```

**在 Engine B 的 `tick()` 中添加 d_σ_t 和 V_Φ 追踪**：

- 每 tick 计算 d_σ_t（从 MeasureCoordinate 的 7 维投影到 6 维时间增量）
- 每 tick 计算 V_Φ(t) = |Φ_t - Φ_{t-1}| / (ε + d_σ_t)
- 将 history 保存在 `self.d_sigma_history` 和 `self.v_phi_history` 列表中
- 在 `get_metrics()` 中输出统计摘要

**MeasureCoordinate 新增 `to_d_sigma()` 方法**：将 7 维 z_t 映射到 6 维 d_σ_t 输入

**在 DualBlindABHarness 中添加追踪**：
- `flush_d_sigma_v_phi()` → 写入 `d_sigma_v_phi_log` 表
- harness 级 d_σ_t 和 V_Φ 聚合统计

---

### Runner 层

#### [MODIFY] [run_v37450_ab_test.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v37450_ab_test.py)

- DB_PATH 改为 `v37492_ab_test.db`（保留旧 `v37490_ab_test.db`）
- 在各 phase 结束后收集 d_σ_t 和 V_Φ 统计
- 新增 3 个验证检查：
  1. `d_sigma_t computed`: d_σ_t history 非空
  2. `v_phi_trajectory non-trivial`: V_Φ 在不同 phase 有不同值域
  3. `d_sigma_v_phi_log DB rows > 0`
- 结果从 40/40 → **43/43**
- 新增 CSV 输出：`d_sigma_v_phi_trajectory.csv`

#### [MODIFY] [run_v37460_integrated.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v37460_integrated.py)

- DB_NAME 改为 `v37492_integrated.db`（保留旧 `v37460_integrated.db`）
- 不增加新的 d_σ_t/V_Φ 功能（集成管线不使用 Hebbian AB 引擎）
- 保持 8/8

---

### DB 迁移层

#### [MODIFY] [pipeline_engine.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/pipeline_engine.py)

新增 migration：

```sql
CREATE TABLE IF NOT EXISTS d_sigma_v_phi_log (
    record_id TEXT PRIMARY KEY,
    run_id TEXT,
    engine_id TEXT,
    tick INTEGER,
    phase TEXT,
    d_sigma_t REAL,
    phi_t REAL,
    phi_prev REAL,
    v_phi REAL,
    clock_delta REAL,
    source_delta REAL,
    reproj_delta REAL,
    phi_displacement REAL,
    rlis_delta REAL,
    churn_delta REAL,
    created_at TEXT
);
```

---

### 工具层

#### [MODIFY] [scripts/run_all_checks.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/scripts/run_all_checks.py)

更新 expected pass count 描述（43 + 8 = 51）

---

## Open Questions

> [!IMPORTANT]
> **d_σ_t 系数校准**：蓝图只给出了 6 维权重的框架（c1-c6），但未指定精确值。我建议使用上述默认值作为初始校准。这些系数将来可以通过数据驱动方式调整。是否可接受？

> [!NOTE]
> 关于保留历史输出：Runner 将使用 `v37492_*.db` 新文件名。所有旧 DB（`v37490_ab_test.db`、`v37460_integrated.db`）完整保留。旧报告同样不会被覆盖。

## Verification Plan

### Automated Tests
1. `python runners/run_v37450_ab_test.py` → 43/43 ALL PASS
2. `python runners/run_v37460_integrated.py` → 8/8 ALL PASS
3. 确认旧 DB 文件仍存在：`v37490_ab_test.db`, `v37460_integrated.db`
4. 确认 d_sigma_v_phi_trajectory.csv 已生成且非空
5. `python scripts/gen_db_lock.py db/v37492_ab_test.db` 生成新锁文件

### 手动验证
- V_Φ 在 noise_storm 阶段应显著高于 warmup（运动势剧烈变化）
- d_σ_t 在 staleness 阶段应接近零（无新输入 → 时间几乎不流动）
