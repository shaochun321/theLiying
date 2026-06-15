# v40.6 结构分化 — Task Checklist

## 方案 C: Contrastive Gain 动态化
- [x] C.1: 从 DB 计算 ho_means/ho_stds，替换硬编码

## 方案 A: 阈值多样性结构分化
- [x] A.1: Zone target_rate 差异化（spectral=0.05/fano=0.02/synchrony=0.06/gradient=0.08）
- [x] A.2: z_t target_rate 差异化（7 个维度各不同：0.02~0.04）
- [x] A.3: calcium_tau 动态化 + threshold floor 比例化 + threshold_adapt_rate 按 target_rate 调节

## 方案 B: Movie 零激活 → 时空窗口主动获取
- [x] B.1: 新增 compute_temporal_resolution_augmentation() 函数（pipeline_engine.py）
- [x] B.2: Phase 1.7 时空分辨率审计
- [x] B.3: 合成窗口注入 circuit loop（entropy→z_t 直接注入 + z-scored 差异化）

## 验证
- [x] 运行 run_v40_integrated.py — 成功通过
- [x] threshold std = 0.001134 > 0.001 ✅
- [x] movie active dims = 4/7 ≥ 2/7 ✅
- [x] cos(scenes, gratings) = 0.059 < 0.20 ✅
- [x] alive = 35/35 ✅
- [ ] avg cos = 0.329 > 0.10 ⚠️ (trade-off: movie activation raises avg cos)
