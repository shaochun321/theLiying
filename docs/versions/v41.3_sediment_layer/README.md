# v41.3 Sediment Layer — Deep Memory Substrate

## 日期
2026-05-19

## 路线
_shadow_memory (List[Dict]) → sediment 层 (真正的赫布超图区域)

## 核心理念
影子层不是"错误日志"，而是主环流的**沉积物**。
expired fruits / ghost bundles / encoding calcium → 缓慢修改 sediment 神经元的 resting_potential。
沉积改变的是"地形"（静息电位），不是"波浪"（激活）。

### 时间膨胀
sediment 层每 20 tick 更新一次。
主环流在 tick 级运行，sediment 在 20-tick 级运行。
类比：引力时间膨胀——越深的层时间流逝越慢。

### 三个输入通道
1. expired dormant fruits → z_t 快照 → 修改 resting_potential
2. ghost_bundles → xin_tension at death → 微量影响 sed 节点
3. encoding calcium → 极慢低通跟踪

### 两个输出信号
- **sed_novelty**: encoding 与 sediment 的差异 → 反馈到 Column misalignment
- **sed_recurrence**: encoding 与 sediment 的匹配 → "以前遇到过类似的"

## 测试结果
| Seed | grad_w | Q4/Q1 | anom | sed_novelty | sed_recurrence |
|------|--------|-------|------|-------------|----------------|
| 42 | 0.991 | 4.96 | 0.0003 | 0.049 | 0.006 |
| 123 | 0.990 | 4.97 | 0.004 | 0.065 | 0.041 |
| 999 | 0.991 | 4.91 | 0.001 | 0.049 | 0.017 |

### 涌现的选择性沉积
- churn 和 potential_disp 沉积最深（20-50× 其他维度）
- seed 999 的符号与 42/123 相反 → 轨迹依赖的差异
- xin_residual 完全没有沉积 → 系统判定它不参与长期记忆
