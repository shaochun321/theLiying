# Morphosphere v38 剩余架构债务清理 (2026.5.15)

## 背景

2026.5.14.2 session 完成了 v38 的 4 个 Phase 并通过了 12/12 checklist。但诚实评估识别出了 5 个架构债务。上次 session 尾部修复了 3 个（burst/sustained 生成器、W_signal 冻结生命周期、Oja 自循环）。本次继续清理剩余的 **2 个高/中优先级债务**，并做整体工程收尾。

## Proposed Changes

### 1. sklearn 外部基线 (🔴 高优先级)

> [!IMPORTANT]
> 这是"论文级"声称的硬性前置条件。当前 Phase 4.2 只比了 Bayesian vs Legacy vs Random，没有与 sklearn 的 k-means/GMM/PCA 对比。

#### [NEW] `runners/run_v38_sklearn_baselines.py`

- 使用 sklearn.cluster.KMeans (K=8) 作为 PRX 分解的基线
- 使用 sklearn.mixture.GaussianMixture (K=8) 与 VariationalGMMEngine 对比
- 使用 sklearn.decomposition.PCA + 阈值作为运动识别基线
- 输出：NMI（归一化互信息）、ARI（调整 Rand 指数）、准确率对比
- 统计检验：10-seed 配对 t-test, Cohen's d

#### [MODIFY] `runners/run_v38_final_report.py`

- 在 Phase 4.2 section 追加 sklearn 基线对比结果
- 更新 v38_final_report.json 追加 `sklearn_baselines` 字段

---

### 2. 消除 motion_recognition_engine.py 双文件 (🟡 中优先级)

#### [MODIFY] `engines/motion_recognition_engine.py`

- 删除 `engines/motion_recognition_engine.py` 这个副本文件
- 在其原位创建一个 **re-export shim**（2 行代码），从根目录的真实文件 re-import
- 确保所有 `from engines.motion_recognition_engine import ...` 路径继续工作

---

### 3. 更新最终报告和 walkthrough

#### [MODIFY] `db/v38_final_report.json`

- 追加 sklearn 基线对比数据
- 更新 checklist 到 14/14（新增 sklearn 两项）

## Verification Plan

### Automated Tests
1. `python runners/run_v38_sklearn_baselines.py` — 运行 sklearn 基线
2. `python runners/run_v38_final_report.py` — 重新生成最终报告
3. `python runners/run_v38_allen_integration.py` — 回归测试
4. `python runners/run_v38_honest_baseline.py` — 回归测试

### Acceptance Criteria
- Bayesian **显著优于** k-means 和 PCA（p < 0.05）
- VariationalGMM 的 ELBO/聚类质量 ≥ sklearn GMM
- engines/ 目录不再有 motion_recognition_engine.py 的完整副本
