# ORC与里奇流 → TOPRXin 映射：量纲核查与整合更新（修订版）

**核查日期**：2026-07-07
**版本**：1.1
**依据**：ORC计算和里奇流动态度量转换文档 + TOPRXin语言规范
**状态**：✅ 逻辑自洽，量纲闭合，可进入工程规格
**修订项**：补充“先修补后理论”执行原则；新增量纲确认工具嵌入位置的工程规格；明确与实验体系的衔接关系


## 一、量纲核查总表

| 概念 | 公式 | TOPRXin对应 | 量纲分析 | 核查结论 |
| :--- | :--- | :--- | :--- | :--- |
| **Xin张力ξ** | `ξ = α·R + β·dR/dt + γ·∫R` | Xin张力 | ξ = 电压 [V] | ✅ 已有 |
| **拓扑距离 L** | `L_ij = ||p_i - p_j||₂` | 空间测度S | L = 长度 [mm] | ✅ 已有 |
| **ORC κ** | `κ ∝ |ξ_i-ξ_j|/L_ij - mean(|ξ_i-ξ_k|/L_ik)` | 二阶空间统计量 | κ = 无量纲 [V/mm / V/mm] | ✅ 自洽 |
| **里奇流 ∂g/∂t** | `∂g/∂t ∝ Cov(∂ξ_i/∂t, ∂ξ_j/∂t)` | 时空测度ds²的演化 | ∂g/∂t = [V²/s²] | ⚠️ 需确认归一化 |
| **BCM阈值 θ_m** | `θ_m = E[ξ²]` | 滑动阈值（第四理念公式5） | θ = [V²] | ✅ 已有 |
| **DA极限环** | `DA(t)` | 门控动力学（第四理念公式6） | DA = 无量纲（0-1）| ✅ 已有 |

### 1.1 量纲一致性的关键结论

**ORC是无量纲的**。因为 `|ξ_i-ξ_j|/L_ij` 的量纲为 `[V]/[mm]`，两者相减得到一个同量纲的差值，再除以同量纲的项，得到无量纲标量。这使其天然适合作为拓扑重要性指标（无需额外归一化）。

**里奇流的归一化问题**：`Cov(∂ξ_i/∂t, ∂ξ_j/∂t)` 的量纲为 `[V²/s²]`。在离散实现中，需要乘以 `dt²` 进行归一化：
```
Δg = -2 × Cov(∂ξ_i/∂t, ∂ξ_j/∂t) × dt²
```
这使 Δg 成为无量纲的权重变化量，与 STDP 更新规则量纲一致。


## 二、TOPRXin语言翻译总表

### 2.1 ORC计算的项目语言转换

| 原始判据 | TOPRXin语言 | 量纲 |
| :--- | :--- | :--- |
| 边的Xin张力差异 | `|ξ_i - ξ_j|` | [V] |
| 归一化张力梯度 | `|ξ_i - ξ_j| / D_ij` | [V/mm] |
| 局部邻域平均梯度 | `mean_{k∈N(i,j)} |ξ_i - ξ_k| / D_ik` | [V/mm] |
| ORC（负=重要） | `κ = (|ξ_i-ξ_j|/D_ij) - mean(...)` | 无量纲 |
| 节点连通度 | `C_eff(n_i) = (1/|N|) Σ_j 1[W_ij > w_th]` | 无量纲 |
| 节点状态分类 | 基于 `A_n`（活动度）和 `I_topo`（拓扑重要性）| — |

### 2.2 里奇流动态演化的项目语言转换

| 原始判据 | TOPRXin语言 | 量纲 |
| :--- | :--- | :--- |
| 特征几何演化 | `∂g_ij/∂t ∝ Cov(∂ξ_i/∂t, ∂ξ_j/∂t)` | [V²/s²] |
| 离散实现 | `Δw_ij = -κ_ij × w_ij × LR_ricci × dt` | 无量纲 |
| 演化停止条件 | `∂ξ_i/∂t → 0`（居中定居/固化态）| — |

### 2.3 拓扑保真度修剪判据（纯TOPRXin语言）

**修剪的数学条件**：

```
Prune(i,j) = 1[ |ξ_i - ξ_j| < ξ_threshold  AND  κ(i,j) > 0 ]
```

**物理含义**：
- `|ξ_i - ξ_j| < ξ_threshold`：这条边两端没有显著的Xin张力差异 → 当前未承载预测误差 → 低活动度
- `κ(i,j) > 0`：正曲率 → 移除它不会破坏网络的信息瓶颈 → 拓扑非关键
- **同时满足 → 修剪（功能沉默）**

**保留（静默中继）的数学条件**：

```
Keep(i,j) = 1[ |ξ_i - ξ_j| < ξ_threshold  AND  κ(i,j) < 0 ]
```

**物理含义**：
- `|ξ_i - ξ_j| < ξ_threshold`：当前静默（未激活）
- `κ(i,j) < 0`：负曲率 → 处于局部Xin张力梯度的“瓶颈”位置 → 拓扑关键
- **同时满足 → 作为“静默中继”被保护**

### 2.4 状态分类的项目语言

| 节点状态 | TOPRXin条件 | 处置 |
| :--- | :--- | :--- |
| **HUB（核心枢纽）** | `A_n > A_high` 且 `I_topo > I_high` | 保留强化，STDP正常 |
| **SILENT_RELAY（静默中继）** | `A_n < A_low` 且 `I_topo > I_high` | **保护免修剪**（负曲率边）|
| **EFFICIENT（高效节点）** | `A_n > A_high` 且 `I_topo < I_low` | 保留，STDP正常 |
| **NOISE（噪声节点）** | `A_n > A_high` 且 `I_topo < I_low` 且激活模式随机 | 削弱连接（LTD）|
| **GHOST（幽灵节点）** | `A_n < A_low` 且 `I_topo < I_low` 且 `C_eff < C_th` | 完全静默，结构保留 |
| **FUNCTIONAL（功能性节点）** | 中间状态 | 正常参与网络 |


## 三、与第四理念六个公式的关系

| 第四理念公式 | TOPRXin对应 | ORC/里奇流的关系 |
| :--- | :--- | :--- |
| 公式1：香农-哈特利信道容量 | TSI功率账本的“信息带宽”维度 | ORC计算所需的节点活动度分布，受限于信道容量 |
| 公式2：互信息流 $C_{E→L}$ | 第四审计维度 | $C_{E→L}$ 是驱动ORC/里奇流演化的“燃料” |
| 公式3：信息熵变分 $dH/dt$ | 熵账本的时间导数 | $dH/dt → 0$ 时，网络拓扑趋于稳定，ORC/里奇流收敛 |
| 公式4：Sigmoid信道墙 | 感觉增益约束 | 防止ORC计算被饱和信号淹没（Xin张力需在可辨范围内）|
| 公式5：BCM滑动阈值 $θ_m$ | Xin张力$\xi$的滑动阈值 | $θ_m$ 决定哪些边能获得LTP，从而改变ORC分布 |
| 公式6：DA极限环 | 门控动力学 | DA脉冲是ORC/里奇流演化的**时间锚点** |


## 四、整合后的执行规格

### 4.1 新增数据结构（项目语言命名）

| 结构名 | 类型 | 包含字段 | 位置 |
| :--- | :--- | :--- | :--- |
| `CurvatureRecord` | dataclass | `edge_id`, `curvature`, `timestamp`, `xi_diff`, `xi_gradient` | 连接记录 |
| `NodeState` | Enum | `HUB`, `SILENT_RELAY`, `EFFICIENT`, `NOISE`, `GHOST`, `FUNCTIONAL` | 节点状态 |
| `TopologyProbe` | Class | `mean_curvature`, `negative_ratio`, `curvature_entropy` | 审计探针 |

### 4.2 新增常量（项目语言命名）

| 常量名 | 符号 | 默认值 | 量纲 | 确定方式 |
| :--- | :--- | :--- | :--- | :--- |
| `PRUNE_XI_THRESHOLD` | `ξ_th` | 待实测 | [V] | 由Xin张力分布决定 |
| `PRUNE_CURVATURE_THRESHOLD` | `κ_th` | 0.0 | 无量纲 | 理论值（正曲率修剪）|
| `RICCI_FLOW_LR` | `LR_ricci` | 待实测 | 无量纲 | 由收敛速率决定 |
| `HUB_ACTIVITY_THRESHOLD` | `A_high` | 待实测 | 无量纲 | 由活动度分布决定 |
| `SILENT_ACTIVITY_THRESHOLD` | `A_low` | 待实测 | 无量纲 | 由活动度分布决定 |
| `TOPOLOGY_IMPORTANCE_HIGH` | `I_high` | 待实测 | 无量纲 | 由ORC分布决定 |
| `TOPOLOGY_IMPORTANCE_LOW` | `I_low` | 待实测 | 无量纲 | 由ORC分布决定 |
| `CURVATURE_UPDATE_INTERVAL` | `T_curv` | 1000 | 步 | 暂定 |
| `PRUNE_INTERVAL` | `T_prune` | 10000 | 步 | 暂定 |
| `GHOST_CONNECTIVITY_THRESHOLD` | `C_th` | 0.01 | 无量纲 | 暂定 |

### 4.3 新增方法签名（项目语言命名）

| 方法名 | 输入 | 输出 | 频率 |
| :--- | :--- | :--- | :--- |
| `compute_forman_ricci()` | `WeightMatrix`, `xi_vector`, `D_matrix` | `CurvatureRecord[]` | 每 `T_curv` 步 |
| `apply_ricci_flow()` | `WeightMatrix`, `CurvatureRecord[]`, `dt` | `WeightMatrix`（原地更新）| 每 `T_curv` 步 |
| `apply_topology_pruning()` | `WeightMatrix`, `CurvatureRecord[]`, `xi_vector` | `PruneReport` | 每 `T_prune` 步 |
| `classify_nodes()` | `WeightMatrix`, `CurvatureRecord[]`, `activity_vector` | `NodeState[]` | 每 `T_prune` 步 |
| `compute_curvature_entropy()` | `CurvatureRecord[]` | `float` | 每 `T_curv` 步 |


## 五、与现有探针体系的整合

| 现有探针 | 新增能力 |
| :--- | :--- |
| `NuProbe`（ν探针）| ν作为里奇流演化的**宏观指示器**：ν>0 → 拓扑流动；ν<0 → 拓扑固化 |
| `WeightEntropyProbe`（熵探针）| 熵变分分解：`dH/dt = dH_curvature/dt + dH_ricci/dt` |
| `EnergyStore`（TSI账本）| 修剪成本计入`P_S`：`ΔP_S = η_prune × Σ(修剪边的权重²) × dt` |
| `ForagingDR5`（状态门控）| 修剪速率受DA门控：`prune_rate ∝ DA(t)` |


## 六、量纲确认工具的工程规格

### 6.1 嵌入位置

在 ORC 计算流程中，每 `T_curv` 步执行完曲率更新后，立即运行一次量纲自检：

```
# 位置：compute_forman_ricci() 返回后，apply_ricci_flow() 执行前
# 频率：每 T_curv 步执行一次
assert_dimension("|ξ_i-ξ_j|", xi_diff, "V")
assert_dimension("|ξ_i-ξ_j|/D_ij", xi_gradient, "V/mm")
assert_dimension("ORC κ", curvature_value, "dimensionless")
assert_dimension("Ricc flow Δw", delta_w_ricci, "dimensionless")
```

### 6.2 实现方式

```python
def assert_dimension(name, value, expected_unit):
    """
    量纲自检：比较当前值的量纲与预期量纲。
    在运行时记录，不修改任何物理量。
    若量纲不匹配，记录 WARNING 日志但继续运行（不崩溃）。
    """
    pass  # 具体实现依赖于项目已有的单位追踪体系
```

### 6.3 备注

- 此自检程序在当前 Python 仿真阶段主要用于辅助诊断
- 若未来项目移植到强类型语言（如Rust），量纲检查可在编译期完成，彻底消除运行时的量纲错误


## 七、“先修补后理论”的执行原则

### 7.1 原则声明

本文档所涉及的一切理论——ORC曲率计算、里奇流动态演化、拓扑保真度修剪——在当前阶段均属于**远期架构愿景**。**绝对禁止**将此框架中的任何机制嵌入当前实验主循环，包括但不限于：

- 禁止在主步进循环中计算ORC或执行里奇流
- 禁止在STDP更新中混合拓扑修剪逻辑
- 禁止修改现有WeightMatrix以添加曲率字段

### 7.2 允许的操作

在不影响主循环执行的前提下，允许以下独立的、分析性质的探索：

- 离线分析已有实验数据（T-059、T-062、T-064），计算节点活动度分布和Xin张力分布，为未来ORC计算提供参数标定基础
- 在分析脚本中实现ORC的初步计算（以活动相关性图为输入），验证曲率分布是否符合理论预期

### 7.3 启动条件

此框架的任何工程实现（包括数据结构、方法、探针），必须在满足以下**全部**条件后才能启动：

1. T-063（双热源鞍点实验）完成且PASS
2. T-060系列（指标体系升级、前庭消融验证）全部完成且PASS
3. 当前主循环稳定运行，无未解决的技术债阻塞

**核心原则**：**所有细节必须先修补，再研究理论上的拓展。** 当前最高优先级仍为 T-060 系列实验。


## 八、与当前实验体系的衔接关系声明

### 8.1 不改变当前执行路径

本文档及静默中继框架、模块-核团映射框架均为**远期架构愿景**，不改变当前执行路径。当前最高优先级仍为 T-060 系列实验（指标体系升级、前庭消融验证、双热源实验）。

### 8.2 渐进验证路径的定位

静默中继框架中定义的渐进验证路径（V1-V4）将在 T-063 通过后逐步启动。本文档的工程规格（数据结构、常量、方法签名）将在 V1 阶段首次引入时实现，当前仅作为技术储备文档。


## 九、结论

| 问题 | 回答 |
| :--- | :--- |
| ORC如何表达为TOPRXin语言？ | `κ = (|ξ_i-ξ_j|/D_ij) - mean(|ξ_i-ξ_k|/D_ik)`，量纲为无量纲 |
| 里奇流如何表达为TOPRXin语言？ | `Δw_ij = -κ_ij × w_ij × LR_ricci × dt`，离散里奇流更新规则 |
| 修剪判据的纯TOPRXin形式？ | `Prune=1[|ξ_i-ξ_j|<ξ_th AND κ>0]`；`Keep=1[|ξ_i-ξ_j|<ξ_th AND κ<0]` |
| 量纲是否闭合？ | ✅ ORC无量纲；里奇流乘以`dt²`后无量纲；修剪判据纯无量纲比较 |
| 量纲确认工具何时运行？ | 每 `T_curv` 步，在曲率更新后、里奇流执行前自动执行 |
| 何时启动工程实现？ | T-063 全部 PASS 后，且当前主循环无阻塞性技术债 |
| 与第四理念公式的关系？ | 完整映射——能量层(公式1,4) → 状态层(公式2,6) → 结构层(公式3,5,ORC/里奇流) |
| 当前可以做什么？ | 离线分析已有数据，标定Xin张力分布和节点活动度分布；在分析脚本中试算ORC |
| 当前绝不能做什么？ | 绝不修改主循环；绝不混合拓扑修剪与STDP；绝不修改现有WeightMatrix结构 |