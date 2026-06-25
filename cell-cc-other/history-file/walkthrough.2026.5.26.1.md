# Phase 3 Walkthrough: Neuron Splitting (Mitosis)

## 实施时间线

Phase 3 经历了 6 轮迭代，从纯机械分裂到基质约束分裂。

---

## S0 清理（Phase 3 前置）

移除了 `_motor_homeostasis` 中的两个 S0 违规：

| 移除项 | 违规原因 | 替代 |
|--------|---------|------|
| 阈值适应 (`_thresh_adapt_targets`) | 使用 `firing_rate()`（软件统计） | FatigueCapacitor（S0 组件） |
| 突触缩放 (`_base_col_mot_gain`) | 使用跨 neuron 能量均值（无物理组件） | 已有 Hebbian STDP |

---

## Phase 3a: 基础 Mitosis 机制

### 新增代码

| 文件 | 改动 |
|------|------|
| [neuron.py](file:///d:/cell-cc/nexus_v1/components/neuron.py) | `NeuronConfig`: mitosis 字段（threshold, confirm, max_splits） |
| | `Neuron.__init__`: `_mitosis_counter`, `_split_count` |
| | `Neuron.step()`: 疲劳电压驱动 counter |
| | `Neuron.should_split()`: 检查 counter ≥ confirm_steps |
| | `Neuron.split()`: 创建子 neuron，分配能量 |
| [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py) | `replace_source()`, `replace_target()`: 重连方法 |
| [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) | `_check_mitosis()`: 扫描 motor → 触发分裂 |
| | `_rewire_after_split()`: 入边 50/50 分配，出边弱副本 |
| [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) | 动态 motor neuron 兼容（3 处懒初始化） |

### 阈值调优

| 版本 | V_fat threshold | confirm_steps | 结果 |
|------|----------------|---------------|------|
| v1 | 0.8 | 50000 | 0 次分裂（疲劳阻止了高频 → V_fat 永远 < 0.8） |
| v2 | 0.4 | 30000 | 27 次分裂，但级联暴走（145 Hz, 52.9%） |

---

## Phase 3b: 基质约束 Mitosis

### 理论动机

用户提出：
> "不能单纯靠调节已有组件来让系统达到预期。真实的神经系统允许复杂性和差异性的存在。存在是时间/空间/物质的组合。可能有次级网络来留存神经元的存在？同时基质的作用是否被低估？"

### 关键设计决策

1. **坐标不外部注入**（公理 Ω-1）：
   - ~~空间坐标 + 领地划分~~ → 拓扑邻近性（bundle 连接距离）
   - 用户："坐标为信息被约束至结构来客观实现"

2. **子代可塑性重置**：`maturation_stage = 0`（最大学习窗口）

3. **族的定义**（临时用 axis 名前缀，未来改用环流拓扑归并）

### 新增代码（Phase 3b）

| 文件 | 改动 |
|------|------|
| [neuron.py](file:///d:/cell-cc/nexus_v1/components/neuron.py) | Apoptosis config: `enable_apoptosis`, `apoptosis_energy_threshold=0.05`, `apoptosis_confirm_steps=30000` |
| | `basal_metabolic_cost=0.0002`（默认）/ `0.0008`（motor） |
| | `_shared_power_rail`: 可外部注入的共享 PowerRail |
| | `split()`: 子代 maturation=0, 负 counter 冷却期, 继承共享 PowerRail |
| | `should_die()`: energy < threshold 持续确认 → 凋亡 |
| | Energy recovery: `recovery *= v_ratio`（共享 PowerRail 约束） |
| [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) | Motor 层共享 PowerRail（x/y/z 三组，R=2.0） |
| | Step 4c: 每步计算轴组总 `_activation_ema` → `rail.draw()` |
| | `_check_mitosis()`: 增加凋亡检查 + 死亡 neuron 清理 |
| | `_cleanup_dead_neuron_bundles()`: 清除死亡 neuron 的 bundle |
| | `_motor_axis()`: 静态方法，从 key 提取轴名 |

---

## 实验结果汇总

| 轮次 | R_internal | basal_cost | 分裂 | 凋亡 | Max Hz | Max % | Motor 数 |
|------|-----------|-----------|------|------|--------|-------|---------|
| 1 (V_fat=0.8) | — | — | 0 | — | 3.6 | 33.8% | 3 |
| 2 (V_fat=0.4) | — | — | 27 | — | 145.2 | 52.9% | 30 |
| 3 (+apoptosis) | 0.1 | 0.0002 | 27 | 0 | — | — | 30 |
| 4 (+parent cooldown) | 0.1 | 0.0002 | 24 | 0 | 168.6 | 81.9% | 27 |
| 5 (+basal cost) | 0.1 | 0.0008 | 16 | 0 | 340.9 | 81.9% | 19 |
| **6 (R=2.0)** | **2.0** | **0.0008** | **27** | **0** | **6.5** | **15.0%** | **30** |

### 关键发现

**成功**：
- PowerRail IR-drop（R=2.0）有效压制了暴走（340 Hz → 6.5 Hz）
- 负载分布从"一个暴走"变为"梯度分散"
- col_to_motor 权重不再饱和（0.33 vs 0.50）
- 3 个 strong sprouts 存活（w 最高 0.43）

**未解决**：
- 0 次凋亡（Catch-22：PowerRail 压制高频 → 低电流 → 无 IR-drop → 僵尸存活）
- 级联分裂仍在（8 层深，虽然每层只贡献 1-6%）
- 僵尸不造成伤害但占用拓扑空间

---

## 理论方向记录

### 用户假想：生长竞争作为 T/O/P/R/Xin 递归

> 如果说生长是一种 T/O/P/R/Xin 递归，那么修剪也是一种 T/O/P/R/Xin 递归。递归的时空信息轨迹会是一种带震荡节的流形。
>
> 引入几种生长竞争，用不同的时间空间环流来约束划定，让彼此竞争。生长会是一个震荡交汇的过程。
>
> 如果抛开显式时空，项目的生长会是外部与客观基底的时空注入下不断带来的新 T 下交汇出的核心区域 P 与带宽区域 R。这是如记录未来和过去一般不断形成的节点，而 Xin 则是不断提醒着系统是被基底时间空间带动一般让系统持续震荡的原因之一。

### 理论含义

| 当前实现 | 问题 | 理论指向 |
|---------|------|---------|
| 单一分裂链（最新子代垄断 T） | 无竞争 R | 需要多种生长模式的 P/R 竞争 |
| sprout 总在同一组 parent 萌芽 | 单一 P 环流 | 不同环流应争夺萌芽资源 |
| 僵尸无害但不消亡 | 无"存在的理由" | Xin 应度量结构的预测贡献 |
| 调参数逼行为 | 优化 ≠ 涌现 | 生长/修剪应从环流竞争中涌现 |

### 下一阶段方向

1. **熵账本系统**（用户提出）：
   - T/O/P/R/Xin 的显式应用在熵账本中划定递归
   - 坐标计算交给熵账本（传统数理坐标 → 主观层构建）

2. **生长竞争**（用户假想的实施路径）：
   - 多种 sprouting 策略竞争（不同 parent 组、不同层级、不同时间窗口）
   - 每种策略是一个 T/O/P/R/Xin 递归
   - 策略间通过共享资源（PowerRail、连接容量）竞争
   - 存活的策略 = P 环流，被淘汰的 = R 环流的历史

3. **僵尸问题的根本解**：
   - 不是"调参数让僵尸死"，而是"让另一种生长来取代僵尸占据的拓扑位置"
   - 当新的生长递归占据了僵尸的连接空间，僵尸自然消亡（信息层面的"不存在"）

---

## 确认路线图

```
Phase 4: P→R 闭合 (Xin → DA → α_lr → Δw)     — v2.0 §1E.5 全链路
Phase 5: 基线修复 (V_ss > V_th → δa 有方向)     — v2.0 §1E.1
Phase 6: 熵账本系统 (T/O/P/R/Xin 显式记录)     — 主观层基础设施
Phase 7: 候选数学体系 (超度量/结构演化)          — 平行于 ds²/ν，不替代
```

### 新旧数学体系关系（已确认）

- 旧体系（ds²/ν/Xin）= 结构内信号流，保留不变
- 新体系（超度量/p-adic）= 结构本身的演化，候选构建
- 桥梁 = ds²/ν/Xin 同时属于两层：实数层计算，超度量层读取
- 不重构，不替代，待验证后决定是否合并

---

## 当前系统状态

Phase 3 代码已合并，mitosis + apoptosis 框架就绪。当前行为：
- 分裂正常触发（V_fat > 0.4, 30s 确认）
- 共享 PowerRail 有效压制暴走
- 凋亡框架存在但未触发（需要生长竞争来激活）
- 系统可稳定运行 500s+，motor rate 在合理范围（0.5-7 Hz）
