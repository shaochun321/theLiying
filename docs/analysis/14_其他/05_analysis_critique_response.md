# 三条"处刑"客观分析

## 评估方法

对每条批评，检查：
1. **描述的问题在当前代码中是否真实存在？**（用 grep 验证）
2. **批评者的解决方案是否合理？**
3. **优先级如何？**

---

## 处刑一：癌症式增殖 — ⚠️ **部分有效**

### 批评者说的

> 系统只长不掉。如果每次遇到张力就长出新连接，超图会变成全连接的毛线球。

### 实际代码现状

| 机制 | 增长 | 收缩 | 代码位置 |
|------|:----:|:----:|---------|
| 神经元 | ✅ 结晶创建 cx_ | ❌ **无删除机制** | L1539-1571 |
| Bundle (层内) | ✅ 结晶创建 | ✅ `should_prune()` → ghost | L540, L1346 |
| Bundle (层间) | ✅ 结晶输出 | ❌ **inter_layer 无 prune** | L1578-1593 |
| 收敛节点 | ✅ 共激活创建 | ✅ 衰减 ×0.99 → 删除 | L1479-1486 |
| 果实 | ✅ tension 创建 | ✅ trace 衰减 → 过期 | L548, L1256 |

### 客观评价

**有效的部分**：
- 确实没有**神经元删除**机制。Bundle 可以被 prune 到 ghost，但 neuron 一旦创建就永远存在。
- `inter_layer_bundles` 没有 pruning 逻辑（只有 `layer.bundles` 有）。
- 如果运行 10000 ticks，cx_ 数量理论上可以无限增长。

**过度夸大的部分**：
- 结晶条件很严格：age > 50 AND strength > 0.01 AND 不重复。在 111 ticks 中只产生了 5 个 cx_。
- 收敛节点有衰减（×0.99/tick），弱节点被删除（< 0.01 × threshold）。不是"只长不掉"。
- Bundle pruning 存在且有效（`should_prune` 考虑 weight + conductance + activity）。

**真实需要修的**：
1. ✅ 需要：**神经元凋亡**（energy 持续 < 0.01 → 删除）
2. ✅ 需要：`inter_layer_bundles` 的 pruning
3. ❌ 不需要"全面凋亡"——当前增长率 5/111 ticks = 0.045/tick，远非指数增长

### 优先级：**中**（Phase 1 可以顺便修）

---

## 处刑二：假装分化的柱层 — ❌ **已过时，不再成立**

### 批评者说的

> Column 只是"权重大于阈值的 Spine"，没有不对称物理方程。

### 实际代码现状

Column 在 v40.7a 中已获得 **4 种 Spine 不具备的物理行为**：

```python
# L299-305: try_mature() 中的 Column 特权
self.maturation = "column"
self.lateral_suppression_radius = 3    # 不对称：Spine = 0
self.stdp_ltp_boost = 2.0              # 不对称：Spine = 1.0
self.prp_threshold = target_rate * 1.5 # 不对称：Spine = 0.0
```

| 物理行为 | Spine | Column | 代码 |
|----------|:-----:|:------:|------|
| Lateral suppression | ❌ 无 | ✅ 3-hop 抑制 | L1157-1178 maintain() |
| STDP LTP boost | 1.0× | 2.0×（可疲劳/可恢复） | L448-455 stdp_update() |
| PRP emission | ❌ 无 | ✅ calcium 门控 | L261-269 decay() |
| Plasticity (learning rate) | 0.18 | 0.01（慢 18×） | L148 property |
| Inertia | 自适应 | ≥ 2.0（更稳定） | L300 |

**Column 的 lateral suppression 物理机制**：

```python
# L1157-1178: Column 产生负向张力（抑制力），压制邻近 Spine
# 这正是批评者要求的"抑制周围 k-hop 的 Spine"
for idx2 in range(max(0, idx-r), min(len(neuron_ids), idx+r+1)):
    if idx2 == idx: continue
    neighbor = layer.neurons[neuron_ids[idx2]]
    if neighbor.maturation == "spine":
        suppression = ca_ratio * abs(neuron.activation) / (abs(idx - idx2) + 1)
        neighbor.threshold += suppression * 0.01
```

### 客观评价

**这条批评完全不再成立。** Column 有不对称的物理方程，有侧向抑制，有 PRP 特权，有不同的学习速率。批评者可能看到的是更早的版本。

### 优先级：**无**（已解决）

---

## 处刑三：Python 循环瓶颈 — ⚠️ **技术上正确，但时机过早**

### 批评者说的

> N=40 时几毫秒，N=4000 时 2.5 秒。应该用稀疏矩阵/Graph Laplacian/PyTorch Geometric。

### 实际性能现状

```
N=40 neurons, B=37 bundles → 111 ticks → ~50 秒（含 IO/DB/数据加载）
纯 circuit 部分估算 → ~5 秒 / 111 ticks ≈ 45ms/tick
```

### 客观评价

**技术上正确的部分**：
- O(N×B) 的 for 循环确实是 O(n²) 级别
- 如果 N=4000，每 tick 会从 45ms 涨到 ~45s（线性外推，实际可能更差）
- 稀疏矩阵是正确的工程方向

**过早优化的部分**：
- 当前系统是**研究原型**，目的是验证物理动力学规则，不是生产部署
- 在 N=40 时优化到 GPU 稀疏矩阵，会让代码变得极难理解和修改
- 我们还在每周改动 `decay()`, `propagate()`, `stdp_update()` 的物理公式。如果这些公式锁定在 torch 张量运算中，每次修改都是重写
- 当前瓶颈不在 circuit 而在 IO/DB 操作

**什么时候应该做这个**：
- 当物理规则稳定（不再每周修改公式）
- 当 N > 500 成为真实需求
- 当 circuit 性能确实成为瓶颈（而不是 IO）

> [!TIP]
> 正确的做法是：现在用 OOP 验证物理正确性，**后期**用 `torch.sparse` 重写核心热路径（propagate + stdp_update），保持相同的物理语义。这两步不矛盾。

### 优先级：**低**（Phase 4 之后）

---

## 总结

| 处刑 | 判定 | 需要行动？ |
|------|------|:----------:|
| ① 癌症增殖 | **部分有效** — 缺神经元凋亡 + inter_layer pruning | ✅ Phase 1 |
| ② 假分化 Column | **已过时** — v40.7 已实现完整不对称物理 | ❌ |
| ③ Python 瓶颈 | **正确但过早** — 研究原型 ≠ 生产系统 | ⏳ 后期 |

批评者的核心洞察（凋亡、分化、并行）是对的，但对当前代码状态的判断有误：
- Column 分化已经实现（批评者可能看到了旧版本）
- 增殖有多重制动机制（只是缺少神经元级别的删除）
- 性能优化在原型阶段是次要矛盾
