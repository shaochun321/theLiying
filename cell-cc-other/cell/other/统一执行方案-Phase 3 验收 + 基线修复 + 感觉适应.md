
### 一、当前状态确认

| 组件 | 状态 | 证据 |
|------|------|------|
| Phase 3 三因子适格迹 | ✅ 验证通过 | E(220)/E(25) ≈ exp(-195/300)=0.522 |
| 热编码基线审计 | ✅ 诚实性确认 | 关键结论基于差分测量，共模基线不影响 |
| 回归测试 | ⚠️ 11/12 | T2.2 前提有误：ambient=0.1 ≠ 0 |

**结论**：系统物理层完整、诚实。问题在于测试层对“闭环世界始终有温度场”的事实视而不见。


### 二、三层架构已闭合（确认）

| 层级 | 机制 | 门控信号 | 状态 |
|------|------|----------|------|
| **外层** | Phase 3 适格迹 | DA（全局价值）| ✅ LTP 由 DA 门控 |
| **中层** | Phase 1 差分拓扑 | 结构路由 | ✅ 方向选择性已建立 |
| **内层** | Phase 2 能量冻结 | fill_fraction | ✅ 能量枯竭时全部冻结 |


### 三、执行步骤

#### 步骤 1：测试确定性与差分阈值（立即执行）

**1a. pytest fixture 固定随机种子**

```python
# test_regression.py - circuit_10k() fixture
import random
random.seed(42)
```

消除热源初始漂移的混沌敏感性，使回归测试确定性通过。

**1b. T2.2 改为相对选择性比**

```python
# 原：assert enc_quiet < 0.5  ← 物理前提错误
# 改：assert enc_active / enc_quiet > 1.5  ← 差分/比率测度
```

**1c. EXP-014 Gate 2 改为差分检查**

```python
# 原：any(v > 0 for v in snapshot.values())  ← 共模基线会 PASS
# 改：enc_front - enc_back > threshold  ← 只验证梯度信息
```


#### 步骤 2：慢速适应电容/高通滤波（立即执行）

**目的**：用物理机制消除环境基线，只透传温度变化率（梯度）。

**物理原理**：一阶 RC 高通滤波 = 尖峰频率适应（Spike Frequency Adaptation）

```python
# VariantCircuit.__init__()
self._thermal_adapt = {pid: 0.0 for pid in ['front', 'back', 'left', 'right']}
self.tau_adapt = 5000.0  # 适应时间常数，追踪环境基线

# get_mechanical_inputs() 中
decay = math.exp(-dt / self.tau_adapt)

for pid in ['front', 'back', 'left', 'right']:
    raw = self.relays[pid]._activation_ema
    
    # 慢速电容追踪基线（DC分量）
    self._thermal_adapt[pid] = (
        self._thermal_adapt[pid] * decay + raw * (1.0 - decay)
    )
    
    # 高通输出：只透传变化率（AC分量）
    result[f"therm_{pid}"] = max(0.0, raw - self._thermal_adapt[pid])
```

**效果**：
- 恒定 ambient=0.1 被吸收 → 热编码静默
- 快速温度变化（靠近热源）→ 差分信号爆发
- 自动适应任何环境温度（无需预设基线）

**为什么用这方案**：
- ✅ 无需预设基线，不依赖起始位置
- ✅ 纯物理实现（RC 滤波），无 if-else 分支
- ✅ 符合尖峰频率适应的生物物理机制
- ✅ 对梯度敏感，对环境底噪不敏感


#### 步骤 3：Phase 3 验收归档

将 EXP-019 数据记录到 `EXPERIMENT_LOG.md`：

| 组 | DA 条件 | Δw |
|----|---------|-----|
| A | DA=0 全程 | -0.013 |
| B | DA=0.5 @ t=20 | +0.041 |
| C | DA=0.5 @ t=220 | +0.002 |

适格迹动力学验证：E(220)/E(25) ≈ exp(-195/300) = 0.522 ✅


### 四、注意事项（否决项）

| 不要做 | 理由 |
|--------|------|
| 修改增益链参数 | 系统对梯度的敏感度是完整的，改参数会破坏它 |
| 使用静态基线减法 | 初始化位置异常时会致盲 |
| 绝对阈值测试 | 闭环世界始终有温度场 |


### 五、预期产出

| 步骤 | 产出 |
|------|------|
| 步骤 1 | 12/12 全绿回归 |
| 步骤 2 | 感觉适应机制生效，热编码基线被吸收 |
| 步骤 3 | Phase 3 验收文档归档 |


### 六、三问

**Q1：这会改变已有实验结论吗？**

不会。所有关键结论基于差分测量（Δw、空间分化、比率），对共模基线天然鲁棒。修复只涉及测试层和感觉适应层，不改变物理内核。

**Q2：高通滤波与 Phase 2 能量冻结冲突吗？**

不冲突。高通滤波作用于**传入信号**（感觉适应），Phase 2 作用于**权重更新**（突触沉积）。不同层级，无交叉。

**Q3：如何验证修复有效？**

`diag_thermal_gradient.py` 运行后，热编码神经元在 ambient=0.1 下应保持静默，仅在进入热梯度时产生差分信号。