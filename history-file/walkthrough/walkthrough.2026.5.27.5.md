# Walkthrough: All Fixes Complete

## Summary Table

| # | 问题 | 修复 | 验证 |
|---|------|------|------|
| P4 | P→R 断裂 | _do_learning 三因子 | ✓ |
| P5 | 基线=0 | bc_current=0.032 | ✓ |
| P6 | 无熵账本 | WeightEntropyProbe + Ledger | ✓ |
| P7 | 无候选数学 | Ultrametric + StructuralEntropy + Bridge | ✓ |
| FU-A | col_to_motor 饱和 | decay_rate 0.5 | w=0.19 ✓ |
| FU-B | 无二代 sprout | 候选扩展 + depth + 孤儿 | 代码就绪 |
| M1/M3 | ds²用\|a\| | δa=a-ā (EMA) | 基线收敛 ✓ |
| A3 | 热瞬时穿透 | 100步延迟 + 阈值0.001 | 延迟活跃 ✓ |
| A4 | Body无物理 | kinetic_damping + mass_inertia + thermal_mass | 通道就绪 ✓ |
| T2 | PNN只成熟 | DA→PNN降解 (MMP-9) | 双向调控 ✓ |
| T3 | fruit hack权重 | 结构触发 (expand/contract) | 噪声过滤 ✓ |
| T4 | 无守恒验证 | NoetherProbe (4律) | 500检0违规 ✓ |

## Modified Files

| 文件 | 改动 |
|------|------|
| `hebbian.py` | P4/P5 + FU-A/B + T3 fruit wiring |
| `variant_adapter.py` | P4/P6/P7 + A3 + A4 + T2 + T4 |
| `bundle.py` | FU-B + T3 fruit redesign |
| `toprxin_ledger.py` | P6 + P7 + FU-B |
| `circulation.py` | M1 δa |
| `shadow_sandbox.py` | M1 baseline |
| `world.py` | A4 body physics |
| `ecm.py` | T2 PNN degradation |
| `noether_probe.py` | T4 [NEW] |

## Remaining

| # | 问题 | 状态 |
|---|------|------|
| M4 | activation 取哪个值 | 未开始 |
| — | 500k 长运行验证 | 需要执行 |
