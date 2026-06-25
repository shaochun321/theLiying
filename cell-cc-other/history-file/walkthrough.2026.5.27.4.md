# Walkthrough: Phase 4–7 + All Fixes

## Completed

| # | 问题 | 修复 | 验证 |
|---|------|------|------|
| P4 | P→R 断裂 | _do_learning 三因子统一 | ✓ |
| P5 | 基线=0 | bc_current=0.032 | ✓ |
| P6 | 无熵账本 | WeightEntropyProbe + Ledger + Tracker | ✓ |
| P7 | 无候选数学 | UltrametricSpace + StructuralEntropy + Bridge | ✓ |
| FU-A | col_to_motor 饱和 | decay_rate: 0.025→0.5 | w=0.19 ✓ |
| FU-B | 无二代 sprout | 候选扩展 + depth 限制 + 孤儿处理 | 代码就绪 |
| M1/M3 | ds²/κ 用\|a\| | δa=a-ā (EMA基线) | 基线收敛 ✓ |
| A3 | 热瞬时穿透 | 100步延迟 + 穿透阈值0.001 | 延迟活跃 ✓ |
| A4 | Body 无物理 | kinetic_damping + mass_inertia + thermal_mass | 通道就绪 ✓ |

## 修改文件

| 文件 | 改动 |
|------|------|
| `hebbian.py` | P4/P5 + FU-A + FU-B |
| `variant_adapter.py` | P4/P6/P7 + A3 延迟 + A4 反馈 |
| `bundle.py` | FU-B _sprout_depth |
| `toprxin_ledger.py` | P6 + P7 + FU-B 孤儿 |
| `circulation.py` | M1 δa |
| `shadow_sandbox.py` | M1 基线 bug |
| `world.py` | A4 body 物理 |

## 剩余

| 编号 | 问题 |
|------|------|
| M4 | activation 定义 |
| T2 | PNN 解冻 |
| T3 | Xin→fruit 重设计 |
| T4 | Noether 离散验证 |
| — | 500k 长运行 |
