# v41.1 Column Forward Model (Cerebellar Phase Alignment)

## 日期
2026-05-18

## 路线
Column 被动 EMA 记录器 → Column 主动前向模型（小脑类比）

## 核心理念
Column 层是进化塑造的"固定算法"——学得快（BCM）、固定得牢（高惯性）、选择性强（侧抑制）。
它不是一个通用学习器，而是一个在千万年进化中被打磨出来的**时序预测模块**。

在 Morphosphere 中：
- "苔藓纤维" = col_raw_* （绕过丘脑门控的原始信号）
- "传出副本" = CPG 相位状态
- "预测误差" = 信号 × (1-gate)
- "运动校正" = CPG 相位重置

## 讨论要点（与用户）
- 用户提出 Column 可以用做"对齐"或"翻译"→ 确认类似小脑角色
- Column 是超图中一个有特殊属性的子图，不是独立模块
- maturation="column" 赋予四个特权：lat_sup=3, ltp_boost=2, inertia=2, BCM
- 三个功能子群：巩固组(7) + 苔藓纤维组(3) + 对齐组(7) = 17 neurons

## 实施
- `hebbian_circuit.py`: `_column_forward_step()` 方法
- `_phase5_pipeline.py`: `col_raw_*` 苔藓纤维注入（用 received_* 而非 gradient_*）
- `maintain()` 中 `_cpg_step()` 后调用 `_column_forward_step()`

## 测试结果
| 指标 | 均匀介质前 | 异质介质后 |
|------|-----------|-----------|
| align_ratio | 0.55 | 0.53 |
| Phase acoustic | +0.058 | +0.051 |
| Phase thermal | +0.0005 | +0.002 |
| Phase luminous | +0.058 | +0.051 |

## 降级变化
- NEW (标为降级): `cerebellar_forward_model_timing_prediction` — 功能已实现但简化了微电路
