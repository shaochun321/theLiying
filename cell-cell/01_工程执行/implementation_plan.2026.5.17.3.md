# 下一步计划

## 当前状态

```
✅ 量源场衰减 ratio=1.000
✅ 前庭层 10 neurons, occ=0.856
✅ IntegratorColumn 积分器 (leaky + log)
✅ μ(G) = 1.201, 3条活跃环流
✅ 实践皮层 3个 px_ 结晶
✅ 分辨力 cos=-0.333 ✅ YES
```

## 🔴 关键修复: px_ 输入束缺失

px_ 神经元结晶后 `act=0.000` — **永远不会被激活**。

原因: 只创建了输出束 (px_→motor, px_→encoding)，没有输入束。
对比: encoding 的 cx_ 在结晶时创建了 `dim → cx_` 的输入束 (L1921-1926)。

```python
# encoding cx_ 有这个:
for dim_id in node["dims"]:
    if dim_id in enc.neurons:
        b = enc.add_bundle(source_ids=[dim_id], target_ids=[crystal_nid])

# practice px_ 缺这个！
# 需要: constituent neurons → px_ 的跨层输入束
```

修复: 在 px_ 结晶时，添加 constituent → px_ 的 inter-layer 输入束。

---

## Phase 1: 修复 + 激活 px_ (立即)

1. 在 `_detect_practice_convergence()` 的结晶代码中添加输入束
2. constituent neurons (在 motor/vestibular 层) → px_ (在 practice_cortex 层)
3. 运行 500 tick 验证 px_ activation > 0

## Phase 2: 长训练 + 内部结构 (随后)

1. 1000 tick 训练 — 验证稳定性
2. px_ 之间的 intra-layer 束 — 实践皮层内部结构分化
3. 观察: 三源平衡是否形成? μ(G) 是否继续增长?

## Phase 3: Origin-环流耦合 (后续)

origin_confidence × μ(G) → 新原点定义的候选构建

```
现有: origin_confidence = 散度接近1的程度
现有: μ(G) = 环流强度
候选: 新原点 = argmax(origin_confidence × μ(G))
```

即: 新原点是**同时具有最高环流活性和最高散度收敛**的概率区域。
这与之前讨论的"散度无限接近1的概率原点"对齐。

---

## 降级候选

| 完整版 | 降级候选 |
|---|---|
| 树突输入整合 (dendritic computation) | 线性加权和 |
| 多突触输入竞争 (synaptic competition) | 平等输入 |
