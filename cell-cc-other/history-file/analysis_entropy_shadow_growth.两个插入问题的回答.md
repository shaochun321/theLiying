# 两个插入问题的回答

---

## Q1：熵账本在哪里构建？是否更新过？

### 现状审计

系统中存在 **两个不同的"熵"组件**，功能重叠但架构分离：

| 组件 | 文件 | 是否集成到 step loop | 状态 |
|---|---|---|---|
| **EntropyLedger** | [entropy_ledger.py](file:///d:/cell-cc/nexus_v1/components/entropy_ledger.py) | ❌ 未集成 | 独立观测器，需手动调用 `ledger.record(circuit, dt)` |
| **WeightEntropyProbe** | [toprxin_ledger.py](file:///d:/cell-cc/nexus_v1/circuit/toprxin_ledger.py) | ✅ 集成 | 每 100 步在 `_entropy_ledger_pre_step()` 中自动执行 |

### EntropyLedger 现状

```python
# entropy_ledger.py — 473 行，完整实现
# 功能: 能量收支, ISI 熵, 层间传递熵, Landauer 约束检查
# 问题: 从未被 VariantCircuit.__init__() 实例化
# variant_adapter.py 中没有 "from .entropy_ledger import" 或 "EntropyLedger"
```

**结论**: `EntropyLedger` 是一个建好但**从未安装的仪表**。

只有测试文件 (`test_entropy_ledger.py`, `test_combined_entropy_shadow.py`) 使用它。

### 实际在 step loop 中运行的

```python
# variant_adapter.py L294
self._entropy_probe = WeightEntropyProbe()  # ← 这才是实际运行的

# _entropy_ledger_pre_step() 中调用:
self._entropy_probe.accumulate_heat(total_heat)    # 每步
self._entropy_probe.measure(self, tick)             # 每 100 步
```

`WeightEntropyProbe` 追踪的是 **权重分布的 Shannon 熵**（dw 信号质量），不是完整的热力学账本。

### 未追踪的关键指标

- ❌ 影子层的能量收支（shadow neurons 有自己的 VR + heat）
- ❌ DA 回路的能量收支
- ❌ Coupler 存储能量（`_cumulative_energy_in/out`）
- ❌ 全局 Landauer 约束验证 (ΔS_total ≥ 0)
- ❌ 层间信息传递效率 (bits/joule)

> [!WARNING]
> 熵账本存在但未部署。这意味着系统的热力学守恒目前仅依赖 Noether probe（权重/Xin 守恒），没有 Landauer 层面的全局验证。

---

## Q2：影子层使用定额结构

### 现状审计

影子层 `ShadowSandbox.initialize()` 创建的拓扑是 **完全固定的**：

```
构建时确定，此后永不变化：
  Neurons:  2×7(enc) + 7(col) + 3(mot) = 24 固定
  Bundles:  7(enc→col) + 7(col→mot) + 21(cross) = 35 固定
  无 sprout / 无 prune / 无 mitosis / 无 fruit
```

`observe()` 方法中：
- ✅ 权重学习（STDP/BCM）
- ✅ 沉默突触管理（`_manage_silent_synapses`）
- ❌ 没有 `bundle.update_fruit()` 调用
- ❌ 没有 `_structural_growth()` 调用
- ❌ 没有 neuron `should_split()` 检查
- ❌ 没有 `should_prune()` 调用

### 这导致哪些问题无法回答？

| 问题 | 为什么需要结构增长 | 当前状态 |
|---|---|---|
| **沉积厚度** | 层的厚度 = 该层 neuron 数量。固定 = 无法涌现 | 硬编码 7 col |
| **内部链路拓扑** | 哪些 col↔col 连接应该存在是结构问题 | 硬编码 21 cross |
| **环流机制并行存在** | 不同子回路需要不同密度 | 所有 axis 相同结构 |
| **影子层对自身规模的渴求** | Xin tension → Fruit → expand/contract | Fruit 未启用 |
| **跨轴关联强度** | 哪些 cross 链接有意义应涌现 | 全部 dormant |

### 与主层的对比

```
主层 (HebbianCircuit._structural_growth):
  ✅ Fruit lifecycle: Xin → dormant → mature → expand/contract
  ✅ Bundle sprout: 母本分化，STDP 选择存亡
  ✅ Bundle prune: grace period → weight 低于阈值 → 移除
  ✅ Neuron mitosis: fatigue → split → daughter 竞争

影子层 (ShadowSandbox.observe):
  ❌ 无 Fruit lifecycle
  ❌ 无 Bundle sprout/prune
  ❌ 无 Neuron mitosis
  仅有: 沉默突触 activate/deactivate (§3)
```

### 设计思考

你说的对：**影子层作为"内省预测器"，自身也需要 Merzenich 式结构可塑性**。

理由：
1. 如果主层通过 expand/contract 改变了 7→9 个 axis，影子层停留在 7 axis 的固定结构上，就无法追踪主层的新结构
2. 影子层的 cross-axis 链接应该通过竞争涌现（哪些轴间有预测关系），而不是预先铺设 21 条全部dormant
3. 影子层的 col 数量应该反映"需要多少个独立预测通道"——这应该是 Xin 驱动的结构决策

但有一个关键前提：**影子层的结构增长必须与主层解耦**。否则影子层变成主层的递归拷贝，丧失"外部观测者"地位。

> [!IMPORTANT]
> **执行顺序建议**: 
> 先完成 DA→Motor 闭环验证（当前阻断点），
> 再实施影子层结构增长（需要工作的 DA 调制来驱动 Fruit）。
> 影子层 Fruit 的成熟条件应该用影子层自己的 Xin，不是主层的 Xin。

---

## 行动清单

### 熵账本
- [ ] 决定：保留 EntropyLedger（合并进 step loop），还是扩展 WeightEntropyProbe？
- [ ] 无论哪个，需要覆盖 shadow neurons + DA neurons + coupler 能量

### 影子层结构增长
- [ ] 在 `observe()` 中启用 Fruit lifecycle (`bundle.update_fruit()`)
- [ ] 实现影子层 sprout/prune（复用主层 `bundle.sprout()`/`should_prune()`）
- [ ] 考虑影子层 neuron mitosis（col 层扩展）
- [ ] 影子层结构变更 → 反传到 DA circuit（shadow_to_da 需要动态更新 sources 列表）

> [!CAUTION]
> 影子层加入结构增长后，shadow→DA bundle 的 sources 列表会变化。
> 当前 shadow_to_da bundle 在 DA 初始化时固定了 sources。
> 需要在 sprout/mitosis 后更新 DA bundle 的 source 引用。
