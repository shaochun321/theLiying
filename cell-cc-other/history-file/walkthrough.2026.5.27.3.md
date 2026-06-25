# Walkthrough: Phase 4–7 + Follow-ups + M1/M3 + A3

## Phase 4: P→R 闭合 ✓
## Phase 5: 基线修复 ✓
## Phase 6: 熵账本系统 ✓
## Phase 7: 候选数学体系 ✓
## Follow-up A: col_to_motor decay_rate ✓ (w=0.20 稳定)
## Follow-up B: 二代 sprout ✓ (代码就绪，需长运行)

## M1/M3: 度规修正 δa ✓

- `circulation.py`: flow 改用 δa = |a - ā| (EMA 基线)
- `shadow_sandbox.py`: 基线 EMA bug 修复

## A3: 热场有限传播 ✓

**问题**: 热传导瞬时（无延迟）且无穿透限制（任何 ΔT 都传导）。

**修复**:
1. `_ThermalDelayBuffer`: 100 步 FIFO 环形缓冲，模拟有限热传播速度
2. 穿透阈值 0.001: ΔT < 阈值 → 不传导

**验证**: vest↔enc 延迟活跃（100/100 非零），enc↔col 被穿透阈值阻断（0/100）✓

---

## 全部修改文件

| 文件 | 改动 |
|------|------|
| `hebbian.py` | P4/P5 + FU-A decay + FU-B 候选扩展 |
| `variant_adapter.py` | P4/P6/P7 集成 + A3 热延迟 + _ThermalDelayBuffer |
| `bundle.py` | FU-B _sprout_depth |
| `toprxin_ledger.py` | P6 (3类) + P7 (3类) + FU-B 孤儿处理 |
| `circulation.py` | M1: δa 基线 |
| `shadow_sandbox.py` | M1: 基线 bug 修复 |

## 剩余

| 编号 | 问题 | 状态 |
|------|------|------|
| A4 | Body 无物理 | 未开始 |
| M4 | activation 定义 | 未开始 |
| T2 | PNN 解冻 | 未开始 |
| T3 | Xin→fruit 重设计 | 未开始 |
| T4 | Noether 离散验证 | 未开始 |
| — | 500k 长运行 | 需要执行 |
