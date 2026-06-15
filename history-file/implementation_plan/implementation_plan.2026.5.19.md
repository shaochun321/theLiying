# 消融修正方案 — A/B/C 三条路径

## 物理分析结果

```
                    物理量    注入到神经元    与lever的比
lever (杠杆)        5.0       0.5             1×
gradient (梯度)     0.002     0.009           1/43~1/143×
```

梯度不是"极弱"，而是比杠杆**弱 40-140×**。这在物理上正确：
$$\nabla\Phi = \frac{n \cdot A}{r^{n+1}} = \Phi_{\text{recv}} \cdot \frac{n}{r}$$

在 r=5, box=10 的条件下，梯度自然比总信号小一到两个量级。

**根因不是"信号太弱"，而是"信号弱于 STDP 的灵敏度阈值"**。

---

## Path A: 改物理引擎

### 原理
不是"凭空放大"，而是改变实验条件使梯度在物理上更强。

### 实现

#### [MODIFY] [practice_engine.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/practice_engine.py)

**方案 A1: 缩小盒子 (box_size=5)**
- r 减半 → 梯度增 4× (∵ 1/r^(n+1))
- 这是"把食物放近一点"——合理的实验条件变化

**方案 A2: 增加衰减指数 (decay=3)**
- 梯度 = recv × 3/r → 增强 50%
- 这是"让信号更集中"——近处很强，远处快速衰减
- 生物参照：化学信号的 short-range 衰减 (pheromones)

> [!WARNING]
> 缺点：改变了物理条件，所有之前的消融数据需要重做。
> 论文中需要声明"在缩小的空间条件下"。

---

## Path B: 系统自身的放大机制

### 原理
系统已经有 **Homeostatic Synaptic Scaling (HSS)** 机制：
当 target neuron 的 calcium < target_rate 时，所有输入权重**乘性放大**。

当前 motor 神经元 `target_rate = 0.0`，意味着 HSS **永远不会放大** motor 输入权重。

如果给 motor 神经元一个非零 target_rate（比如 0.01），HSS 会：
1. 检测到 motor calcium < 0.01（因为 CPG babbling 主导，gradient 贡献微弱）
2. **对所有输入 bundle 的权重做乘性放大**
3. 但 HSS 放大是 **非选择性的**（所有 bundle 一起放大），所以不会单独放大 gradient
4. **关键**：结合 STDP 的选择性修剪，HSS 放大所有权重 → STDP 修剪无用的 → 最终只有因果相关的 gradient 权重存活

这就是生物学中的 **HSS + STDP 协同**：
- HSS 维持总活动水平（"保证有信号"）
- STDP 选择因果路径（"保证信号有意义"）

### 实现

#### [MODIFY] [_phase5_pipeline.py](file:///D:/cell-cc/experiments/_phase5_pipeline.py)

```python
# Motor neurons: non-zero target_rate for HSS to function
# Biological basis: motor neurons have spontaneous firing rates
# (Bernstein 1967, motor readiness potential)
for m in ["move_x", "move_y", "move_z"]:
    mot.neurons[m].target_rate = 0.01
```

**这不是数值 hack**——是修正一个结构性遗漏。真实的运动神经元有**自发放电率**（motor readiness potential, Bereitschaftspotential），target_rate=0 意味着系统认为运动神经元"不应该发放"，这与运动系统的生物现实不符。

### 验证方式
- HSS 是否让 grad_to_motor 的权重上升？
- 同时 STDP 是否选择性保留 gradient 方向与运动方向一致的权重？
- 消融 HSS（target_rate 改回 0）应让权重回到 0

> [!IMPORTANT]
> **Path B 的风险**：HSS 也会放大 CPG → motor 的权重（如果 cpg_to_motor 不是 frozen）。
> 但 cpg_to_motor 的 learning_rule="none"，所以 STDP 不会改变它。
> HSS 的乘性放大只影响 weights[][]，不影响 learning_rule。
> 需要检查 HSS 是否只放大 STDP-active 的 bundle。

---

## Path C: 承认限制

### 论文措辞

> **Section 5.x: Limitations and Ablation Results**
>
> We performed systematic ablation studies (5 conditions × 3 seeds × 1000 ticks)
> to assess the functional contribution of each architectural component.
>
> **Positive findings:**
> 1. STDP topology is signal-dependent: white noise ablation eliminates
>    the selective pruning pattern (transition/drift preserved, churn/potential_disp pruned),
>    confirming that the topology reflects input statistics rather than algorithmic bias.
> 2. The encoding topology is robust across random seeds (3-seed consistency).
>
> **Negative findings:**
> 1. Gradient→motor STDP learning did not converge under current experimental conditions.
>    The spatial gradient magnitude (~0.002) is 40-140× weaker than lever arm signals,
>    falling below the STDP sensitivity threshold for single-synapse learning.
> 2. The sediment layer, while structurally functional (resting_potential accumulation
>    confirmed), does not measurably affect system behavior in 1000-tick runs.
>
> These limitations indicate that behavioral adaptation (as opposed to internal
> encoding adaptation) requires either stronger environmental gradients or
> multi-synaptic amplification mechanisms — a direction for future work.

---

## 推荐

> [!IMPORTANT]
> **推荐先做 B，再做 C。**
>
> B 是修正 motor target_rate 的结构性遗漏（一行代码），如果有效，
> 证明 HSS+STDP 协同可以从弱信号中提取因果路径。
> 如果无效（HSS 放大不够），再用 C 诚实记录限制。
>
> A 最后做（或不做）——改物理条件不如让系统自己解决问题有价值。

## Open Questions

> [!IMPORTANT]
> HSS 对 inter_layer_bundles 是否生效？
> 当前 HSS 代码在 maintain() 中遍历 `layer.bundles`（层内束），
> 但 grad_to_motor 是 `inter_layer_bundles`（层间束）。
> 需要确认 HSS 覆盖了层间束，否则 Path B 无效。
