# Follow-up 问题详解

## 问题 1: col_to_motor 权重饱和 (decay_rate)

### 现象

Phase 5 修复了基线放电（`bc_current=0.032`，`V_ss=0.16 > V_th=0.15`），但副作用：
`col_to_motor` 权重重新饱和到 `weight_max=0.5`。

### 根因分析

STDP 学习规则（[bundle.py:L215-L230](file:///d:/cell-cc/nexus_v1/circuit/bundle.py#L215-L230)）：

```python
ltp = src.pre_trace * tgt.post_trace          # 增强项
decay = decay_rate_by_stage[0] * w             # 衰减项  
dw_raw = stdp_lr * dt * (ltp - decay)          # 净变化
```

**均衡条件**：`dw/dt = 0` 当且仅当 `ltp = decay_rate × w`

$$w_{eq} = \frac{\text{pre\_trace} \times \text{post\_trace}}{\text{decay\_rate}}$$

### 数值推导

**Phase 5 之前**（无基线放电）：

| 参数 | 值 | 来源 |
|------|-----|------|
| Motor post_trace (基线) | ≈ 0 | V_ss < V_th → 不放电 → 无 spike |
| Motor post_trace (刺激) | 间歇 > 0 | 仅当 col 输入足够时 |
| ltp 平均 | 很小 | 只在刺激时非零 |
| decay_rate | 0.025 | BundleConfig 默认 |

→ w_eq ≈ ltp_avg / 0.025 ≈ 较低值 ✓

**Phase 5 之后**（有基线放电 ~3 Hz）：

| 参数 | 值 | 来源 |
|------|-----|------|
| Motor post_trace (基线) | **持续 > 0** | bc=0.032, V_ss=0.16 > V_th → 基线 spike |
| trace_tau_post | 20 ms | NeuronConfig 默认 |
| decay_post | exp(-dt/0.02) = exp(-0.05) = 0.951 | dt=0.001 |
| post_trace 稳态 | ≈ 1.0/(1-0.951) ≈ **20** (每次 spike 加 1.0) | 几何级数 |
| Col pre_trace | ≈ 0.007 × 4 axes | 典型值 |
| ltp = pre × post | ≈ 0.028 × 20 = **0.56** | 持续非零！ |
| w_eq = ltp / decay_rate | 0.56 / 0.025 = **22.4** | 远超 weight_max=0.5 |

**结论**：`ltp / decay_rate = 22.4 >> weight_max = 0.5`

权重被 multiplicative soft bound 限制在 0.5，但净驱动力始终为正。
乘法因子 `(weight_max - w)` 只是让接近上限时变慢，不是真正的均衡。

> [!IMPORTANT]
> 实际稳态由 soft bound 决定：w → weight_max，增速指数衰减但永不停止。
> 从测试看（Phase 5 后 50k 步），w 已回到 0.5。

### 解决方案

需要提高 `decay_rate` 使 w_eq 落在合理范围内。

**目标**：w_eq ≈ 0.25（weight_max=0.5 的中点）

$$\text{decay\_rate} = \frac{\text{ltp\_avg}}{w_{eq}} = \frac{0.56}{0.25} \approx 2.24$$

但这太大了（原来是 0.025）。原因：post_trace 的稳态值 ≈ 20 太高。

**更实际的方案**：

分两步——

**方案 A**：仅调 decay_rate

```
decay_rate: 0.025 → 0.5
w_eq = 0.56 / 0.5 = 1.12 → 被 weight_max=0.5 截断
```

但 0.5 仍太高（post_trace 的持续注入太强）。需要更大的 decay_rate 或更小的 post_trace。

**方案 B**：调 col_to_motor 的 `plasticity_by_stage[0]`

当前 `plasticity_by_stage = (0.18, 0.01, 0.001)`，stage 0 的乘数 = 0.18。
降到 0.02 会将有效 dw 缩小 9 倍。

**方案 C**（推荐）：为 col_to_motor 单独设置更高的 decay_rate

```python
# hebbian.py line 342-356: col_to_motor BundleConfig
BundleConfig(
    ...
    decay_rate_by_stage=(0.5, 0.1, 0.01),  # was (0.025, 0.005, 0.001)
    ...
)
```

这样 col_to_motor 的 STDP 衰减与其高 post_trace 匹配，
而其他 bundle（vest→enc, enc→col）不受影响。

> [!WARNING]
> 修改后需要重新验证：
> 1. 权重是否真的不再饱和
> 2. 权重是否还能学习到有意义的结构（不是全部衰减到 0）
> 3. 基线放电是否仍然存在（不受权重衰减影响，因为 bc_current 是独立的）

---

## 问题 2: 超度量深度 = 0（无二代 sprout）

### 现象

50k 步测试中，9 个递归循环全部 depth=0（无嵌套）。
超度量距离全部 = 1.0（最大距离）。
强三角不等式平凡满足。

### 根因分析

在 [hebbian.py:L511-L515](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py#L511-L515)：

```python
candidates = (self.bundles_vest_to_enc
              + self.bundles_enc_to_col
              + self.bundles_col_to_motor)
```

**只有原始 bundle 是 sprout 候选。`_sprouted_bundles` 不在候选列表中。**

所以 sprout 的 parent 永远是原始 bundle → parent 没有 cycle_id → depth = 0。

### 两个子问题

**子问题 A: 为什么 `_sprouted_bundles` 不在候选列表中？**

这是有意设计：
- 原始 bundle 有稳定的源和目标（固定拓扑）
- sprout 可能被 prune → 如果 sprout 从 sprout 生出子代，prune 父代时子代怎么办？
- 无限嵌套可能导致 bundle 数量爆炸

**子问题 B: 如何启用二代 sprout？**

需要修改候选列表，让 `_sprouted_bundles` 也参与 sprouting：

```python
candidates = (self.bundles_vest_to_enc
              + self.bundles_enc_to_col
              + self.bundles_col_to_motor
              + self._sprouted_bundles)  # ← 新增
```

但需要同时处理：
1. **孤儿问题**：父 sprout 被 prune 时，子 sprout 需要降级（parent_cycle_id 变为 grandparent）
2. **爆炸问题**：`MAX_TOTAL_BUNDLES` 已限制总数，但嵌套深度无限可能导致族谱树过深
3. **peer_targets 问题**：sprout 的 targets 可能已经变异（cross-target mutation），从 sprout 再 sprout 时 peer_targets 如何选择？

### 解决方案

**方案 A**（保守）：不改候选列表，改 parent tracking

当前问题不是 sprout 不能嵌套，而是 RecursionTracker 没有正确识别 parent。
原始 bundle（如 `col_to_motor`）没有 cycle_id，所以 sprout 的 parent_cycle_id = None → depth = 0。

修复：为原始 bundle 创建"根循环"（depth=-1），使 sprout 的 depth = 0 仍然有意义。

**方案 B**（推荐）：启用二代 sprout + 限制嵌套深度

```python
# 在 _structural_growth 中：
candidates = (self.bundles_vest_to_enc
              + self.bundles_enc_to_col
              + self.bundles_col_to_motor
              + [b for b in self._sprouted_bundles
                 if b._sprout_depth < MAX_SPROUT_DEPTH])

MAX_SPROUT_DEPTH = 3  # 最多三代嵌套
```

同时在 `sprout()` 中传递深度：
```python
child._sprout_depth = getattr(self, '_sprout_depth', 0) + 1
```

孤儿处理：prune 时不删除子代，而是将子代的 parent_cycle_id 上移到 grandparent。

> [!IMPORTANT]
> **依赖关系**：方案 B 需要先修改 bundle.py（添加 _sprout_depth）和 hebbian.py（扩展候选列表），
> 然后修改 RecursionTracker（孤儿降级逻辑）。
> 这是一个结构性改动，影响生长竞争的动态。

---

## 建议执行顺序

```
Step 1: col_to_motor decay_rate 调整（方案 C，仅改 BundleConfig）
        → 验证权重不再饱和
        → 验证基线放电不受影响

Step 2: 启用二代 sprout（方案 B，改 bundle + hebbian + tracker）
        → 500k 运行验证 depth > 0
        → 验证超度量距离非平凡
        → 验证强三角不等式仍然满足
```
