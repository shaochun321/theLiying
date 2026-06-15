# Walkthrough: Phase 4–7 + Follow-ups + M1/M3

## Phase 4: P→R 闭合 ✓
## Phase 5: 基线修复 ✓
## Phase 6: 熵账本系统 ✓
## Phase 7: 候选数学体系 ✓

## Follow-up A: col_to_motor decay_rate ✓
- decay_rate: 0.025→0.5 → w 稳定 0.19

## Follow-up B: 二代 sprout ✓
- 候选列表扩展 + depth 限制 + 孤儿处理

## M1/M3: 度规修正 δa ✓

**问题**: ds²/κ 计算和 circulation flow 用 |a|（绝对激活），应该用 δa = a - ā（偏离基线）。

**修复**:
1. `circulation.py`: 添加 `_baseline_ema` + `_update_baselines()`, flow 用 `|a - ā|`
2. `shadow_sandbox.py`: 修复基线 bug（`abs(n.activation)` → `n.activation`）

**验证**: 7 个列神经元基线 EMA 正常收敛，无回归。

---

## 全部修改文件

| 文件 | 改动 |
|------|------|
| `hebbian.py` | Phase 4/5 + FU-A decay_rate + FU-B 候选扩展 |
| `variant_adapter.py` | Phase 4/6/7 集成 |
| `bundle.py` | FU-B _sprout_depth |
| `toprxin_ledger.py` | Phase 6 (3类) + Phase 7 (3类) + FU-B 孤儿处理 |
| `circulation.py` | M1: δa 基线 + flow 用 δa |
| `shadow_sandbox.py` | M1: 基线 bug 修复 |

## 剩余问题

| 编号 | 问题 | 状态 |
|------|------|------|
| A3 | 热场穿透限制 | 未开始 |
| A4 | Body 无物理 | 未开始 |
| M4 | activation 定义 | 未开始 |
| T2 | PNN 解冻 | 未开始 |
| T3 | Xin→fruit 重设计 | 未开始 |
| T4 | Noether 离散验证 | 未开始 |
| — | 500k 长运行 | 需要执行 |
