# 对外部提案 2026.5.25.1 的批判分析

## 外部诊断的准确性

### 正确的观察

| 诊断 | 评判 | 说明 |
|------|------|------|
| 萌芽速度 > 淘汰速度 | ✅ 准确 | 48 sprouts, 0 pruned |
| 弱连接无代价存活 | ✅ 准确 | sprout 创建后无持续开销 |
| 计算开销增长 | ✅ 准确 | 80 bundles vs 32, propagate 成本 ~2.5× |
| 修剪未启动 | ✅ 准确 | mean_weight ~0.001 > 阈值的 0.005 有歧义，但确实无修剪 |

### 不准确的诊断

| 诊断 | 评判 | 说明 |
|------|------|------|
| "连锁危机" | ⚠️ 夸大 | 系统运行稳定，能量 avg=0.896，motor 正常 2.9-4.5 Hz |
| "电压崩溃风险" | ❌ 未发生 | PowerRail 未被拉低，motor 仍在 spike |
| "脑死亡" | ❌ 危言耸听 | motor 差异化反而**改善**了 (33/33/33 → 27/33/41) |
| "无限制萌芽" | ⚠️ 不准确 | MAX_TOTAL_BUNDLES=80 已生效，80 步就停了 |

> [!NOTE]
> 外部分析的诊断在方向上正确（萌芽/修剪不平衡确实存在），但在程度上夸大了紧急性。系统并未"危机"，而是在一个**不够理想但稳定**的状态。

---

## 逐条审查建议

### 3.1 突触维持税 — **概念有效，实现需修正**

> "让每一个存活的 bundle 持续消耗能量"

**概念判定：✅ 有效。** 生物学中突触维持确实需要能量（ATP）。持续代谢压力是淘汰弱连接的物理基础。

**实现问题：**

1. **`src.outgoing_bundles` 不存在。** 当前 Neuron 不维护出边列表。需要新增数据结构。但这只是工程问题，不涉及原则。

2. **`scale_weights(0.999)` 是纯数学操作。** 直接乘以常数因子作用在 Memristor 电导上 — 这可以接受吗？

   分析：`scale_weights` 等价于 "当宿主 neuron 能量不足时，Memristor 电导下降"。物理映射：**维持电导需要持续的离子浓度梯度，能量不足 → 浓度梯度衰减 → 电导下降**。这是物理过程，不是优化算法。

   但 0.999 是 magic number。更好的做法：用一个 **代谢 MOSFET**，以 neuron.energy 为 gate voltage，当 energy < threshold 时 MOSFET 导通（漏电流），该漏电流直接减小 Memristor 的 w。

   ```python
   # S0-compliant: metabolic MOSFET
   metabolic_gate = MOSFET(v_threshold=0.3, gm=0.001)
   leak_current = metabolic_gate.conduct(energy_deficit)
   memristor.w -= leak_current * dt  # energy deficit → conductance decay
   ```

   不过这为每个 bundle 增加一个 MOSFET 组件，计算开销较大。**折中方案**：在 bundle 级而非 memristor 级做代谢检查。能量不足时统一衰减该 bundle 所有权重。这仍然是 S0 合规的（能量检查是观测，权重衰减是 Memristor 的物理响应）。

**判定：采纳概念，用简化的组件映射实现。**

### 3.2 双条件宽限期修剪 — **部分有效**

> "宽限期 + 权重条件 + 局部 ξ 条件"

**宽限期（grace period）：✅ 有效。** 新芽需要时间让 STDP 决定其命运。2000 步（2s）合理。

**双条件（权重 + ξ）：⚠️ 过度工程。** 
- 权重条件：已有（mean_weight < threshold）
- ξ 条件：bundle 的 `xin_tension` 已存在，可直接复用

但增加"局部 ξ 积分器（新 Capacitor）"的建议 — 每个 bundle 已经有 `config.xin_tension`，这就是局部残差积分器。**不需要新增组件。**

**"已成熟的 bundle 不修剪"：✅ 有效。** PNN 保护的连接代表已沉积的结构，不应轻易移除。但当前 sprouts 没有 PNN 保护（maturation_stage=0），这个条件对 sprouts 不适用。

**判定：采纳宽限期 + 降低修剪阈值，但不需要新增局部 ξ 积分器。**

### 3.3 萌芽节制 — **部分违反 S2**

> "按 ξ 大小排序，只对前 N 个执行萌芽"

**能量预算检查：✅ 已有。** 当前代码已检查 `s.energy > SPROUT_ENERGY_COST`。

**按 ξ 排序选择前 N 个：❌ 违反盲芽原则。**

> [!WARNING]
> 排序 ξ 并选择 "最高" 的 = **引入了全局优先级判断**。这不是盲目萌芽 — 它假设 "ξ 最高的 bundle 最需要萌芽"，这是一个优化决策。

**盲芽的正确做法**：每个 bundle 独立判断自己的 ξ 是否超阈值，不与其他 bundle 比较。如果同时有多个 bundle 超阈值，**随机选择**而非按 ξ 排序。或者更简单：保持当前的遍历顺序（确定性但不是按 ξ 优化的）。

**MAX_SPROUTS_PER_STEP=2 的限制：✅ 有效。** 但这是计算资源限制，不是信号路径决策。可以接受。

**能量预支（宽限期维持税）：⚠️ 可选。** 这增加了复杂度。更简单的做法：提高 SPROUT_ENERGY_COST 来涵盖预期的维持成本。

**判定：采纳 MAX_SPROUTS_PER_STEP，拒绝 ξ 排序，保持盲目遍历。**

### 3.4 计算优化 — **纯工程，无原则问题**

"惰性修剪"和"静默状态"都是合理的工程优化。与项目原则无冲突。

### 3.5 保持盲目萌芽 — **自相矛盾**

> "上述修改不引入任何协方差引导或梯度信息"

但 3.3 中按 ξ 排序本质上就是梯度引导 — ξ 是预测残差，排序 ξ 等价于 "梯度最大的方向优先"。外部分析在这里自相矛盾。

---

## 综合裁决

| 建议 | 判定 | 理由 |
|------|------|------|
| 突触维持税 | ✅ 采纳 | 物理合理，代谢压力是淘汰弱连接的正确机制 |
| scale_weights 方法 | ⚠️ 修正 | 用能量-电导耦合而非 magic number |
| 宽限期 | ✅ 采纳 | 新芽需要时间让 STDP 决定 |
| 双条件修剪 | ⚠️ 简化 | 用现有 xin_tension 代替新积分器 |
| ξ 排序选择 | ❌ 拒绝 | 违反盲芽原则（RULE S2） |
| MAX_SPROUTS_PER_STEP | ✅ 采纳 | 计算资源限制，合理 |
| 能量预支 | ⚠️ 简化 | 提高 SPROUT_ENERGY_COST 即可 |
| 惰性修剪 | ✅ 采纳 | 纯工程优化 |
| PNN 保护 | ✅ 采纳 | 已沉积结构不应修剪 |

## 建议的实施方案

### 1. 突触维持税（最关键）

```python
# 在 HebbianCircuit.step() 中，每 100 步检查一次：
def _apply_metabolic_tax(self, dt):
    """代谢税：每个 bundle 持续消耗源 neuron 能量。
    
    BIO: 突触维持需要 ATP（离子泵、受体周转、线粒体）。
    当源 neuron 能量不足时，其出边 Memristor 电导自然衰减。
    """
    TAX_RATE = 1e-5  # 每 bundle 每步的能量成本
    ENERGY_FLOOR = 0.1  # 能量低于此值 → 权重衰减
    
    for bundle in self.get_all_bundles():
        for src in bundle.sources:
            src.energy -= TAX_RATE * dt
        # 能量不足时：权重自然衰减（Memristor 退化）
        avg_src_energy = sum(s.energy for s in bundle.sources) / len(bundle.sources)
        if avg_src_energy < ENERGY_FLOOR:
            deficit_ratio = avg_src_energy / ENERGY_FLOOR  # 0~1
            for row in bundle._memristors:
                for m in row:
                    m.w *= (0.999 + 0.001 * deficit_ratio)  # 衰减幅度随能量降低而增大
```

### 2. 修剪升级

- 宽限期 2000 步
- 阈值降低：w < 0.001（不是 0.005）
- 加入 |ξ| < 0.01 辅助条件（复用现有字段）

### 3. 并发限制

- MAX_SPROUTS_PER_INTERVAL = 3（每次检查最多 3 个萌芽）
- 保持遍历顺序，不排序
