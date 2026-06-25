# Walkthrough: Phase 3–7 Summary

## Phase 3: Neuron Splitting (Mitosis) — 暂停
- Mitosis + PowerRail + 凋亡框架完整

## Phase 4: P→R 闭合 ✓
- `_do_learning()` 虚方法 + DA/PNN/sync 三因子统一学习
- DA gain = 1.270, PNN 关键期关闭, col_to_motor 不饱和

## Phase 5: 基线修复 ✓
- Motor bc_current: 0.02→0.032, V_ss = 0.16 > V_th = 0.15
- Follow-up: col_to_motor decay_rate 需调整（基线放电导致权重重新饱和）

## Phase 6: 熵账本系统 ✓

三组件（纯观察者）：
1. **WeightEntropyProbe**: Shannon 熵 + Landauer bound — S 从 2.08→1.84
2. **TOPRXinLedger**: 每 bundle 的 T/O/P/R/Xin 五相位强度
3. **RecursionTracker**: sprout/prune/mitosis → 递归循环族谱

修改文件：toprxin_ledger.py (NEW), hebbian.py, variant_adapter.py

## Phase 7: 候选数学体系 ✓

三组件（纯观察者，候选构建）：
1. **UltrametricSpace**: d_u = 1/(1+depth(LCA)) — 强三角不等式验证通过
2. **StructuralEntropy**: H_struct = 树深度分布 Shannon 熵
3. **StructuralBridge**: corr(d_u, |Δw|) — ds²/ν ↔ 超度量桥梁

验证：
- 强三角不等式 SATISFIED（0 violations / 84 triples）✓
- 50k 步结构 trivial（depth=0），需 500k+ 步观察嵌套

修改文件：toprxin_ledger.py (3 new classes), variant_adapter.py

---

## 全阶段修改文件清单

| 文件 | Phase | 改动 |
|------|-------|------|
| `hebbian.py` | 4,6 | _do_learning 虚方法 + 结构事件钩子 |
| `variant_adapter.py` | 4,5,6,7 | 三因子学习 + bc_current + 账本集成 |
| `toprxin_ledger.py` | 6,7 | 全新：6 个类（3 账本 + 3 超度量） |

## Follow-ups

1. **col_to_motor decay_rate**: 基线放电下权重饱和问题
2. **500k+ 长运行**: 验证超度量结构深度 > 0
3. **二代 sprout**: 需要 sprout 从其他 sprout 产生（当前只从原始 bundle）

## 新旧体系关系

```
旧体系 (ds²/ν/Xin) — 结构内信号流 — 保留不变
  ↕ StructuralBridge (corr, influence)
新体系 (超度量/H_struct) — 结构本身演化 — 候选构建
```

- 不重构旧体系
- 新体系在 RecursionTracker 族谱树上运作
- ds²/ν 恰好是两层的桥梁
