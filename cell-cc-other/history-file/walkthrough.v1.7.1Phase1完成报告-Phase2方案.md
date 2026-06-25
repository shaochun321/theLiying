# v1.7.1 Phase 1 完成报告 + Phase 2 方案

> 2026-06-07 session (commits 6462160..050c53c)

---

## Phase 1 完成：E1 + T·S·I 验证

### 已完成工作

#### E1: 扩容后自检机制

| 迭代 | 方法 | 结果 |
|---|---|---|
| Round 1 | 单 bundle Xin snapshot (countdown=10) | ❌ 评估在 sprout 前完成 |
| Round 2 | 延长 countdown=150 (15k steps) | ❌ ratio=2.000 (leaky integrator 数学必然) |
| Round 3 | expand_boost (30% parent weight) | ❌ ratio=2.000 (sprout 不影响父 bundle 的 R(t)) |
| **Round 4** | **系统级 mean Xin per bundle** | **✅ 7/7 OK, ratio≈0.95** |

**关键发现**: 
- Per-bundle Xin 的稳态只取决于 $R(t)$，与外部变化无关
- 系统级测量正确: mean_xi 从 1644.7 → 1160.9 (-29%) as N: 37→58 (+57%)
- Expansion 有效地分摊预测误差到更多 bundle

#### T·S·I 新代理变量

| 指标 | 值 | CV | 稳定？ |
|---|---|---|---|
| I_norm (Xin 归一化熵) | 0.664 | 0.015 | ✅ 尺度不变量 |
| S×I_raw | 371.5 | 0.083 | ⚠️ 单调增长 |
| S×I_norm | 67.5 | 0.054 | ⚠️ 增长 |

**I_norm ≈ 0.664 是真正的发现**: Xin 分布均匀性在 N=37→60 范围内保持不变。

#### 理论评审归档

三份外部评审 (2026.6.7.2/3/4) 提供了：
- ξ 符号注释修正 (论文级)
- **废除 MAX_BUNDLES=80** (架构级) ← 三份评审一致要求
- I_norm 违反 S0 局部性 (只做诊断)
- coupler 延迟 → expand 的因果链 (理论深化)
- **T·S·I ≤ P_input** 代谢约束 (理论闭合路径)
- 四个物理学锚点 (Landauer, FEP, 建构定律, Margolus-Levitin)

### 代码变更

| 文件 | 变更 |
|---|---|
| [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py) | expand_boost, E1 snapshot 简化 |
| [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) | system-level E1 eval, expand_boost 传递 |
| [EXPERIMENT_LOG.md](file:///d:/cell-cc/nexus_v1/docs/history/EXPERIMENT_LOG.md) | EXP-005, EXP-006 |
| [T006_theoretical_anchors.md](file:///d:/cell-cc/nexus_v1/docs/theory/T006_theoretical_anchors.md) | 四理论锚点 [NEW] |

### 回归测试

所有变更后 21/21 通过 (T1.1-T9.1)。

---

## Phase 2 方案：三个优先任务

根据评审反馈 + 路线图，按优先级排列：

### P2.1: 废除 MAX_BUNDLES=80 — 用能量墙替代硬上限

> **优先级**: 🔴 最高 (三份评审一致要求)
> **理论依据**: 建构定律 + Landauer 原理

#### 当前问题
```python
# hebbian.py L627
MAX_TOTAL_BUNDLES = 80  # 上帝用手按住了膨胀的宇宙
```

#### 方案

1. **增加基底维持功耗** (`_apply_metabolic_tax`):
   ```python
   # 当前: TAX_PER_BUNDLE = 5e-5 (太低，无限制效果)
   # 修改: 让 tax 随 N_bundles 非线性增长
   BASAL_COST_PER_BUNDLE = 0.001  # 每步每 bundle 的静态维持
   COST_SCALING = 1.5  # 超线性：维持 N 个 bundle 的成本 ∝ N^1.5
   total_cost = BASAL_COST_PER_BUNDLE * N_bundles ** COST_SCALING
   ```

2. **Sprouting 条件加入能量检查**:
   ```python
   # 不仅检查源神经元能量，还检查系统 EnergyStore
   can_afford = (energy_store.level > SPROUT_ENERGY_COST * 2
                 and all(s.energy > SPROUT_ENERGY_COST for s in bundle.sources))
   ```

3. **移除硬上限**:
   ```python
   # 删除: if total_bundles >= self.MAX_TOTAL_BUNDLES
   # 替换: 能量自然限制
   ```

4. **零和入侵**: 活跃区域 expand 必须等非活跃区域 contract 释放能量

#### 验证
- 80k 运行：N_bundles 是否自动收敛到某个值？
- EnergyStore.level 是否稳定？
- axis/cross ratio 是否保持 > 2.0？

---

### P2.2: ξ 符号注释修正 + PAPER 更新

> **优先级**: 🟡 中 (论文级，不影响代码行为)

代码中 `predicted - actual > 0` 对应**过度预测**，论文中误标为 "underprediction"。

#### 修正内容
- [PAPER_structural_reorganization.md](file:///d:/cell-cc/nexus_v1/docs/theory/PAPER_structural_reorganization.md): §2.3 符号对齐
- bundle.py: 注释中 "underprediction → expand" 改为 "capacity surplus signal → expand"
- 根据 Review 2 的分析：expand 的真正驱动力是 **coupler 延迟的系统性相位差**

---

### P2.3: T·S·I 重构 — 代谢约束路径

> **优先级**: 🟡 中 (理论级)

#### 新方向

基于 T006 理论锚点 §4:

$$T \cdot S \cdot I \leq P_{input}$$

其中:
- $T$ = 结构事件后的能量恢复时间（动态，非常数）
- $S$ = $N_{eff} \times \langle\Delta w\rangle$（有效连接 × 学习容量）
- $I$ = $\bar{\xi}$（平均预测误差，局部可测，符合 S0）
- $P_{input}$ = EnergyStore 的输入功率（来自世界中的热源消耗）

#### 验证方法
1. 在 80k 运行中测量 $T_{recovery}$（每次 sprout/prune 后 EnergyStore 恢复稳态的步数）
2. 计算 $T \times S \times I$ 的时间序列
3. 与 $P_{input}$（cumulative energy absorbed / time）比较

---

## 后续路线 (Phase 2 之后)

| 阶段 | 内容 | 前置 |
|---|---|---|
| P2.1 | 废除硬上限 | - |
| P2.2 | 符号修正 | - |
| P2.3 | T·S·I 代谢路径 | P2.1 (需要动态 N) |
| P3 | 影子层本体 (A8) | P2.1 (影子层需要动态拓扑) |
| P4 | C3' 进食-运动耦合 | P3 (需要影子层反馈) |
| P5 | 运动分化增强 | P2.1 (需要 cross-axis 动态) |
