# Morphosphere v38 债务清理 — Task Tracker

## 1. sklearn 外部基线 (🔴 高) ✅
- `[x]` 检查 sklearn 是否已安装 — **scikit-learn 1.8.0**
- `[x]` 创建 `run_v38_sklearn_baselines.py` — k-means / GMM / PCA 基线对比
- `[x]` 运行并验证结果:
  - Bayesian **84.9%** > KMeans 76.3% (p=0.0007, d=1.55) ✅
  - Bayesian 84.9% ≈ sklearn GMM 83.6% (p=0.39, d=0.33) ⚠️ 非显著
  - Bayesian > PCA+Centroid 80.8% (p=0.0002, d=2.04) ✅
  - NMI: GMM > Bayesian (-0.068) — 离线优化优势
- `[x]` 报告已保存: `db/v38_sklearn_baselines.json`

## 2. 消除 motion_recognition_engine.py 双文件 (🟡 中) ✅
- `[x]` 用 importlib.util re-export shim 替换 `engines/motion_recognition_engine.py`
- `[x]` 验证所有 import 路径正常（allen_integration 6/6 PASS）

## 3. 最终验证 ✅
- `[x]` 重新运行 final_report.py — **12/12 PASS, PROMOTED**
- `[x]` 回归测试 allen_integration — **6/6 PASS**
- `[x]` 更新 walkthrough
