# Frozen Holdout + 存储架构改进方案

## 一、Frozen Holdout 解决方案

### 现状诊断

你的 CTC 真实数据已有 **两个独立序列**（seq01, seq02），共 4575 条记录：

| 序列 | 帧数 | 轨迹数 | 状态 |
|:---:|:---:|:---:|:---:|
| seq01 | 92 帧 | 28 tracks | ✅ 已用于 calibration |
| seq02 | 92 帧 | 58 tracks | ⬛ **从未使用** |

> [!IMPORTANT]
> **不需要下载新数据源。** seq02 就是天然的独立 holdout。它和 seq01 来自同一实验但不同视野（CTC 竞赛的标准做法），满足蓝图 §14 "frozen holdout 必须来自独立生成过程"的要求。

### 实现思路

```
数据分割策略（3-split）：
  seq01 帧 0-69  → calibration  (70 帧，训练用)
  seq01 帧 70-91 → validation   (22 帧，开发调优)
  seq02 全部     → holdout      (92 帧，冻结不动)
```

#### 具体代码改动

1. **`source_event` 表扩展**：每条 CTC 记录写入 `split_role`（calibration / validation / holdout）
2. **新增 `FrozenHoldoutEvaluator`**：
   - 用 calibration split 训练/调优
   - 在 holdout split 上 **只跑一次推断，不允许回传梯度**
   - 比较 holdout 上的 survival/escape 指标是否落入 calibration 指标的 ±2σ 范围
3. **蓝图 §14 检查**：holdout 指标若偏离 calibration 超过 3σ → 触发 `OVERFIT_ALERT`

#### 要不要下载更多数据？

| 选项 | 数据量 | 工作量 | 建议 |
|------|:---:|:---:|:---:|
| **A: 用现有 seq02** | 58 tracks × 92 帧 | 低（~2h 代码） | ✅ **推荐** |
| B: 下载 CTC 其他数据集 | 需要新的 CSV 解析 | 中 | 后续可扩展 |
| C: 接入你的自有实验数据 | 取决于数据格式 | 高 | 最终目标 |

**建议先执行 A，快速建立 holdout 机制，之后再扩展数据源。**

---

## 二、存储系统结构分析

### 当前问题

项目目录现在积压了大量历史产物：

| 类别 | 数量 | 总大小 | 问题 |
|------|:---:|:---:|------|
| `.db` 文件 | 18 个 | **104 MB** | 每个 runner 各生成一个，互不关联 |
| `run_*.py` 文件 | 19 个 | — | 大量遗留 runner，功能重叠 |
| `*_reports/` 目录 | 11 个 | — | 散落在根目录 |
| `QUICKSTART_*.md` | 15 个 | — | 文档碎片化 |
| `REPORT_*.md` | 4 个 | — | 遗留报告 |

> [!WARNING]
> **核心问题：没有单一权威 DB**。每次运行都创建新数据库，导致：
> - 无法跨版本做回归对比
> - source_event / measure_coordinate 等长期表无法积累数据
> - holdout 的"冻结"语义无法保证（每次重建 DB 就丢失了）

### 改进方案

```
morphosphere_v2pp/
├── data/                          # 不可变数据源
│   ├── ctc_centroids_real_v24.csv  ← 保留
│   └── holdout_freeze_manifest.json ← 新增：记录 holdout 冻结时间戳
│
├── db/                            # 新增：统一 DB 存储
│   ├── morphosphere_canonical.db   ← 唯一长期 DB（所有 run 写入同一库）
│   └── scratch/                    ← 临时实验用 DB（可删除）
│
├── migrations/                    # 保留
│   └── 026_v37470_blueprint_tables.sql
│
├── engines/                       # 新增：核心引擎模块
│   ├── hebbian_ab_engine.py
│   ├── variational_gmm_engine.py
│   ├── variational_em_engine.py
│   ├── motion_recognition_engine.py
│   ├── formula_candidate_registry.py
│   └── ctc_source_adapter.py
│
├── runners/                       # 新增：runner 归档
│   ├── run_v37450_ab_test.py       ← 当前主力
│   ├── run_v37460_integrated.py    ← 当前主力
│   └── archive/                    ← 旧 runner 归档
│       ├── run_v37412_*.py
│       ├── run_v37415_*.py
│       └── ...
│
├── reports/                       # 统一报告目录
│   └── {run_id}/
│       └── ab_test_report.json
│
├── pipeline_engine.py             # 保留
└── src/                           # 保留
```

### 关键改进点

#### 1. 单一权威 DB（Canonical DB）

```python
# 所有 runner 都写入同一个 DB
DB_PATH = ROOT / "db" / "morphosphere_canonical.db"

# run_manifest 通过 run_id 隔离不同运行
# 可以跨 run_id 比较：
#   SELECT * FROM v37450_ab_verdict ORDER BY created_at DESC LIMIT 5
```

#### 2. 旧 DB 清理策略

| DB | 大小 | 处理 |
|---|:---:|---|
| v37450_ab_test.db | 7.0 MB | → 合并入 canonical |
| v37460_integrated.db | 3.8 MB | → 合并入 canonical |
| v37412_*.db (×5) | 52 MB | → archive/ 或删除 |
| v37419_issue_fixes.db | 11.8 MB | → archive/ 或删除 |
| 其他旧 DB | 30 MB | → archive/ 或删除 |

#### 3. Holdout 冻结保证

```python
# holdout_freeze_manifest.json
{
  "freeze_date": "2026-05-11T22:00:00Z",
  "dataset": "Fluo-N2DH-GOWT1",
  "split": "seq02_full",
  "rows": 2693,
  "sha256": "a1b2c3...",  # CSV 子集哈希，防篡改
  "touched_since_freeze": false
}
```

---

## Open Questions

> [!IMPORTANT]
> **Q1**: 旧的 12 个 DB 文件（batch2-6, issue_fixes 等）是否还需要保留？还是可以归档/删除？它们占了 ~95 MB。

> [!IMPORTANT]
> **Q2**: 是否同意将目录结构重组为上述方案？这会涉及移动文件和更新 import 路径。

> [!IMPORTANT]
> **Q3**: Frozen holdout 用现有 seq02 先行实现是否可接受？还是你更倾向先接入自有实验数据？

---

## 执行计划

| 阶段 | 内容 | 预计 |
|:---:|------|:---:|
| 1 | 实现 Frozen Holdout（用 seq02） | 立即可做 |
| 2 | 创建 `db/` + `engines/` + `runners/` 目录结构 | 需要确认 Q2 |
| 3 | 归档旧 DB 和旧 runner | 需要确认 Q1 |
| 4 | 合并到 canonical DB | 阶段 2 之后 |

## Verification Plan

### Automated Tests
- Frozen holdout: 在 seq02 上运行推断，检查 survival 是否在 calibration ±2σ 范围
- Canonical DB: 验证多次 run 写入同一 DB 后 run_manifest 正确隔离
- Import 路径: 所有 `run_*.py` 在新目录结构下正常运行

### Manual Verification
- 确认 holdout_freeze_manifest.json 的 SHA256 与 CSV 内容匹配
