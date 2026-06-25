# Phase 3: Neuron Splitting (细胞分裂)

## 背景

当前系统已实现：
- ✅ Bundle 萌芽/修剪（结构边的增减）
- ✅ 疲劳电容（per-neuron 速率自限）
- ✅ 跨目标萌芽（非冗余路径探索）
- ✅ 3 个新芽首次存活（w=0.93）

**缺失的关键能力**：系统只能增减**边**（bundle），不能增减**节点**（neuron）。
真实大脑的神经发生（neurogenesis）和神经元分化（differentiation）需要节点分裂。

## 问题根因

Motor neuron 在 300s+ 达到 52 Hz，根因是：
- 存活新芽向 encoding 层注入额外信号
- col→motor 权重被 STDP 推到 0.5（饱和）
- 3 个 motor neuron 承载了所有输出，无法分化

**Phase 3 解决方案**：当 neuron 持续过载时，分裂为两个子 neuron，
每个子 neuron 继承部分连接 → 单 neuron 负载下降 → rate 自然回落。

---

## 设计原则

> [!IMPORTANT]
> **S0 合规**：分裂触发条件读取 FatigueCapacitor 电压（组件状态），
> 不使用 `firing_rate()` 等软件统计。

> [!IMPORTANT]
> **涌现性**：不预设哪些 neuron 应该分裂。任何 spiking neuron 都可以分裂，
> 前提是疲劳电压长期超过阈值。

---

## 分裂机制

### 触发条件

```
疲劳电压 V_fat > V_mitosis 持续 T_confirm 步
```

- `V_mitosis = 0.8`：疲劳电压阈值（意味着 neuron 长期高频放电）
- `T_confirm = 50000`：确认窗口（50s，防止瞬态触发）
- BIO：细胞应激信号（p53, HSP70）需要持续累积才触发有丝分裂

### 分裂过程

```
Parent neuron (P) → Child_A (继承) + Child_B (新生)

1. Child_A 继承 P 的全部状态（膜电压、疲劳电容、能量）
2. Child_B 以默认状态创建（V=0, fatigue=0, energy=0.5）
3. P 的入边 bundles 随机分配给 A 和 B（各约 50%）
4. P 的出边 bundles: A 继承全部，B 获得弱副本
5. P 从系统中移除
```

### 连接重分配

```
分裂前:
  bundle_1 → P → bundle_3
  bundle_2 → P → bundle_4

分裂后 (一种可能):
  bundle_1 → A → bundle_3 (A继承)
  bundle_2 → B → bundle_3_copy (B获得弱副本)
             B → bundle_4_copy (B获得弱副本)

入边: 随机分配（50/50）
出边: A全部继承，B获得权重=1e-4的副本
```

BIO：轴突分支继承现有突触，新生突触以弱权重开始竞争。

---

## Proposed Changes

### Neuron

#### [MODIFY] [neuron.py](file:///d:/cell-cc/nexus_v1/components/neuron.py)

1. **NeuronConfig** 添加分裂参数：
   ```python
   # Mitosis (Phase 3)
   enable_mitosis: bool = False
   mitosis_v_fat_threshold: float = 0.8   # V_fat > this triggers
   mitosis_confirm_steps: int = 50000     # must stay above for this long
   ```

2. **Neuron** 添加分裂状态跟踪：
   ```python
   self._mitosis_counter: int = 0  # 连续超阈值步数
   ```

3. **Neuron.step()** 末尾添加分裂检查：
   ```python
   # Mitosis check: fatigue voltage sustained above threshold
   if self._fatigue_cap is not None and self.config.enable_mitosis:
       if self._fatigue_cap.voltage > self.config.mitosis_v_fat_threshold:
           self._mitosis_counter += 1
       else:
           self._mitosis_counter = max(0, self._mitosis_counter - 1)  # slow decay
   ```

4. **Neuron.should_split()** 新方法：
   ```python
   def should_split(self) -> bool:
       return (self.config.enable_mitosis
               and self._mitosis_counter >= self.config.mitosis_confirm_steps)
   ```

5. **Neuron.split()** 新方法：
   ```python
   def split(self, child_id: str) -> 'Neuron':
       """Create child neuron. Parent becomes Child_A (keeps state)."""
       child_config = copy(self.config)
       child_config.neuron_id = child_id
       child = Neuron(child_config)
       child.energy = 0.5  # newborn starts with half energy
       # Reset parent's mitosis counter and fatigue
       self._mitosis_counter = 0
       self._fatigue_cap.charge = 0.0
       return child
   ```

---

### Bundle

#### [MODIFY] [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py)

添加 target/source 替换方法（用于分裂时重新连线）：

```python
def replace_source(self, old: Neuron, new: Neuron):
    """Replace a source neuron (for mitosis rewiring)."""
    for i, src in enumerate(self.sources):
        if src is old:
            self.sources[i] = new
            return True
    return False

def replace_target(self, old: Neuron, new: Neuron):
    """Replace a target neuron (for mitosis rewiring)."""
    for i, tgt in enumerate(self.targets):
        if tgt is old:
            self.targets[i] = new
            return True
    return False
```

---

### Hebbian Circuit

#### [MODIFY] [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py)

1. **Motor config** 启用 mitosis：
   ```python
   enable_mitosis=True,
   mitosis_v_fat_threshold=0.8,
   mitosis_confirm_steps=50000,
   ```

2. **新方法 `_check_mitosis()`**：在 step loop 每 10k 步检查一次：
   ```python
   def _check_mitosis(self):
       for layer_name, neurons_dict in [
           ("motor", self.motor_neurons),
       ]:
           to_split = [(k, n) for k, n in neurons_dict.items()
                       if n.should_split()]
           for key, neuron in to_split:
               child = neuron.split(f"{key}_m{self._step_count}")
               neurons_dict[child.id] = child
               self._rewire_after_split(neuron, child, layer_name)
   ```

3. **`_rewire_after_split(parent, child, layer)`**：
   - 入边 bundles：随机 50% 的 target 从 parent 换到 child
   - 出边 bundles：parent 保留全部，为 child 创建弱副本

---

## Open Questions

> [!IMPORTANT]
> **分裂上限**：Motor layer 最多允许几个 neuron？
> 建议：初始 3 个，最多 12 个（4× 扩展）。
> 超过上限 → disable_mitosis。

> [!IMPORTANT]
> **哪些层启用分裂？** 
> 初期建议只在 Motor 层启用（问题最明显）。
> Column 和 Encoding 层的分裂可以在 Motor 验证后再启用。

---

## Verification Plan

### Automated Tests
1. `test_governance.py`：确认不破坏现有 fuse
2. 新增 `test_mitosis.py`：
   - 人为设置 V_fat > 0.8 持续 50k 步 → 验证 should_split() == True
   - 验证分裂后 child neuron 状态正确
   - 验证 bundle 重连后信号流通
3. 500k 步长运行：观察 motor neuron 是否分裂、分裂后 rate 是否下降

### 预期行为
- Motor 在 ~300s 时 V_fat 持续高于 0.8
- 300s + 50s 确认 = ~350s 触发分裂
- 分裂后：每个子 neuron 接收约 50% 的 col 输入
- 单 neuron rate 下降约 50%（从 50 Hz → ~25 Hz）
- 进一步分裂可能在 400-500s 发生
