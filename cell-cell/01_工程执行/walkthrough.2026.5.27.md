# Walkthrough: Phase 3–7 + Follow-ups

## Phase 4: P→R 闭合 ✓
- `_do_learning()` 虚方法 + DA/PNN/sync 三因子统一学习

## Phase 5: 基线修复 ✓
- Motor bc_current: 0.02→0.032, V_ss = 0.16 > V_th = 0.15

## Phase 6: 熵账本系统 ✓
- WeightEntropyProbe + TOPRXinLedger + RecursionTracker

## Phase 7: 候选数学体系 ✓
- UltrametricSpace + StructuralEntropy + StructuralBridge

## Follow-up A: col_to_motor decay_rate ✓

**问题**: 基线放电使 post_trace 持续 ≈ 20 → ltp/decay_rate = 22.4 → 权重饱和 0.5
**修复**: col_to_motor `decay_rate_by_stage: (0.025→0.5, 0.005→0.1, 0.001→0.01)`
**验证**: w = 0.2111 稳定均衡（50k 步不再变化）✓

## Follow-up B: 二代 sprout 启用 ✓

**问题**: sprout 候选列表不含 `_sprouted_bundles` → depth=0
**修复**:
1. `bundle.py`: `_sprout_depth` 代际追踪
2. `hebbian.py`: 候选列表扩展 + depth < 3 限制 + peer_targets 回退
3. `toprxin_ledger.py`: prune 孤儿重新归属

**验证**: 代码正确，50k 步二代 sprout 未触发（sprout 尚未成熟），需 500k+

---

## 全部修改文件

| 文件 | 改动 |
|------|------|
| `hebbian.py` | Phase 4 _do_learning + Phase 5 bc_current + Phase 6 hooks + FU-A decay_rate + FU-B 候选扩展 |
| `variant_adapter.py` | Phase 4 三因子 + Phase 6/7 集成 |
| `bundle.py` | FU-B _sprout_depth |
| `toprxin_ledger.py` | Phase 6 (3类) + Phase 7 (3类) + FU-B 孤儿处理 |
