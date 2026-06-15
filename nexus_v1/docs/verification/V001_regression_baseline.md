# V001: 回归测试基线 — v1.7.2

> **Date**: 2026-06-08
> **Commit**: 63995a0
> **Result**: 21/21 PASS

---

## 测试结果

| ID | 测试 | 值 | 阈值 | 状态 |
|---|---|---|---|---|
| T0.1 | Circuit builds | OK | no crash | ✅ |
| T0.2 | 10k steps complete | OK | no crash | ✅ |
| T1.1 | Noether violations | 0 | == 0 | ✅ |
| T1.2 | Energy balance | 0.000088 | < 0.01 | ✅ |
| T1.3 | Landauer bound | True | True | ✅ |
| T2.1 | Active encoding | 0.6717 | > 0.3 | ✅ |
| T2.2 | Quiet encoding | 0.0000 | < 0.5 | ✅ |
| T2.3 | Encoding selectivity | 671.69× | > 1.5× | ✅ |
| T3.1 | Vest column active | 0.6776 | > 0.3 | ✅ |
| T3.2 | Thermal < vest | 0.495 < 0.678 | therm < vest | ✅ |
| T4.1 | Axis/cross ratio | 6.35× | > 2.0× | ✅ |
| T4.2 | Cross weight max | 0.0726 | < 0.20 | ✅ |
| T4.3 | Motor diff | 0.0174 | > 0.001 | ✅ |
| T5.1 | Xin peak freq | 0.49Hz | 0.5 ± 0.2 | ✅ |
| T5.2 | Xin input power | 58.6% | > 10% | ✅ |
| T6.1 | Sprouted at 10k | 3 | < 20 | ✅ |
| T7.1 | Kinetic energy | 0.005726 | > 0 | ✅ |
| T7.2 | Polarization | 0.5117 | [0.3, 1.0] | ✅ |
| T8.1 | H_struct | 4.1841 | > 0 | ✅ |
| T8.2 | H_flow | 4.0497 | > 0 | ✅ |
| T9.1 | Fan-in ratio | 0.97× | < 2.0× | ✅ |

## 运行环境

- 输入: `oto_x = 200 × sin(2π × 0.5 × t)`, 10k steps
- 其他轴: 无输入
- 时间: 28.8s

## 与 v1.7.1 基线对比

| 指标 | v1.7.1 | v1.7.2 | 变化 |
|---|---|---|---|
| Noether violations | 0 | 0 | 不变 |
| Axis/cross ratio | 6.40× | 6.35× | -0.8% |
| Sprouted at 10k | 3 | 3 | 不变 |
| Xin peak | 0.49Hz | 0.49Hz | 不变 |
| H_struct | 4.1841 | 4.1841 | 不变 |

**结论**: P2.1 的 MAX_BUNDLES 移除和 metabolic_tax 重构**不影响 10k 步行为**。
