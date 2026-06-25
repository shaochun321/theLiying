# Morphosphere v40 — 赫布超图-神经系统 架构文档

---

## §1 方案

### 实施目标

在现有 v39 管线上方构建一个**赫布电路层**，使其：
1. 拥有自己的 T/O/P/R/Xin 生命周期
2. 超图的环流拓扑即电路连线
3. 影子超图从"墓地"升级为"休眠果实层"
4. 坐标量由元组件之间的关系涌现，而非外部公式计算

### 实施范围（v40 初版）

| 组件 | 实施 | 降级 | 未实施 |
|------|------|------|--------|
| MetaNeuron 基类 | ✅ 完整 | — | — |
| MetaSynapticBundle 超边 | ✅ 完整 | — | — |
| Substrate 基质 | ✅ 能量预算 + 温度 | 废热细节简化 | 化学梯度 |
| 棘层 T/O/P/R/Xin | ✅ 完整电路 | — | — |
| 柱层 | ⚠️ 接口定义 | 学习规则简化 | 完整固化机制 |
| 区层 | ❌ | — | 全部 |
| 环流检测 | ✅ 闭合路径追踪 | 拓扑不变量简化 | 同调分析 |
| 影子休眠果实 | ✅ 蜷缩/激活机制 | — | 多层下沉 |
| 元组件分化 | ✅ spine→column 提升 | column→area 省略 | 自动分化 |
| 突触生成/修剪 | ✅ 修剪 | — | 生成 |

### 文件计划

```
engines/
├── _common.py                    # 现有（不修改）
├── hebbian_circuit.py            # ← 新：赫布电路核心
│   ├── MetaNeuron
│   ├── MetaSynapticBundle
│   ├── Substrate
│   ├── CircuitLayer
│   └── HebbianCircuit (含 T/O/P/R/Xin)
├── hebbian_hypergraph.py         # 现有（扩展查询接口）
└── shadow_hypergraph.py          # 现有（升级为休眠果实层）

runners/
└── run_v40_circuit_validation.py  # ← 新：电路验证
```

---

## §2 原始构想哲学

### 信息量与坐标量的分离

项目从最初就将两种量分开：

- **信息量**：ΔF/F 信号、传输代价、假设置信度——这些是管线中流动的**数据**
- **坐标量**：z_t、Φ、d_σ_t——这些应该是系统的**内在几何**

当前的问题是坐标量被当成了信息量的函数（`z_t = W × features`）。在构想中，坐标量应该是**元组件之间的关系涌现物**：

> 两个元神经细胞之间的"距离"不是被计算的，
> 而是由它们之间突触束的传播延迟、耗散量、
> 共享环流数量等属性**定义**的。

### 超图环流 = 神经电路

超图不是一个数据结构，它**就是**电路。在超图上：
- **节点**是元神经细胞——有状态的计算单元
- **超边**是元突触束——多对多的有向连接
- **环流**是闭合超边路径上的稳定激活流——这就是"电路"

环流不应该总是被改变。主环流（P）一旦建立，就有惯性。改变环流 = 相变 = 需要足够能量突破迟滞门控。

### 影子超图的哲学升级

影子超图不是墓地，而是**超图拓扑的对偶结构**：

- 主超图存储**活跃态**：当前正在流通的环流、突触权重
- 影子超图存储**休眠态**：曾经的环流拓扑印记，蜷缩在共边中

"幽灵果实"是一个精确的隐喻：果实长在主超图的边上，但处于蜷缩（dormant）态。当主环流受到偏置（bias）时，偏置使得主环流的能量重新分配，某些共边上的果实获得了足够能量而展开（activate）。

### T/O/P/R/Xin 的超图内化

管线的 T/O/P/R/Xin 处理**数据**。超图的 T/O/P/R/Xin 处理**自身的结构演化**：

| | 数据管线 | 超图内化 |
|---|---|---|
| **T** | 细胞间传输代价 | 超边上的激活传播代价（含基质耗散） |
| **O** | 可测观测量 | 超图构型变化的可测投影 |
| **P** | 主假设 P-Core | 主环流：赢家通吃的闭合激活路径 |
| **R** | 备选 R-Core | 次级竞争环流（与P共享部分超边） |
| **Xin** | 预测残差 | 环流预测但未实现的激活——蜷缩为共边张力 |

---

## §3 数理文档

### 3.1 超图环流的形式化

设超图 $H = (V, E)$，其中 $V$ 是元神经细胞集合，$E$ 是超边（突触束）集合。

**环流**定义为超边序列 $\gamma = (e_1, e_2, \ldots, e_k)$，满足：
- $\text{target}(e_i) \cap \text{source}(e_{i+1}) \neq \emptyset$（相邻超边共享节点）
- $\text{target}(e_k) \cap \text{source}(e_1) \neq \emptyset$（闭合条件）

**环流流量** $f(\gamma)$ = 沿环流传播的激活量：

$$f(\gamma) = \min_{e \in \gamma} w(e) \cdot a(\text{source}(e))$$

其中 $w(e)$ 是超边权重，$a(v)$ 是源节点激活值。

### 3.2 P/R 竞争的能量模型

环流在基质中竞争自由能。设基质自由能为 $F$，环流 $\gamma_i$ 的能量需求为 $E(\gamma_i)$：

$$E(\gamma_i) = \sum_{e \in \gamma_i} \frac{|a_{\text{pre}}(e) \cdot a_{\text{post}}(e)|}{M(e)}$$

其中 $M(e)$ 是超边的惯性质量。

**P 环流**是满足能量约束的最大流量环流：

$$P = \arg\max_\gamma f(\gamma) \quad \text{s.t.} \quad E(\gamma) \leq F$$

**R 环流**是去除 P 的专属边后的次优环流。

### 3.3 Xin 蜷缩的张力模型

当 P 环流预测超边 $e$ 上应有激活 $\hat{a}$，但实际激活为 $a$，Xin 张力为：

$$\xi(e) = \hat{a}(e) - a(e)$$

- $\xi > 0$：**正张力**（预测了但没发生 → 缺失 → 蜷缩为"渴望"）
- $\xi < 0$：**负张力**（没预测但发生了 → 意外 → 产生新 R 候选）
- $\xi \approx 0$：环流预测准确，无张力

正张力蜷缩在超边上，成为影子层的休眠果实。当后续 tick 中 $a(e)$ 增大使得 $\xi \to 0$，果实"展开"——休眠值被激活回主环流。

### 3.4 基质温度与学习率耦合

基质温度 $T_s$ 由废热决定：

$$T_s(t) = \frac{\sum_{e} |{\Delta W(e)}|^2}{\text{tick\_count}}$$

学习率受温度调制（但外部熵账本不直接设定温度）：

$$\eta_{\text{eff}} = \eta_0 \cdot \sigma(T_{\text{optimal}} - T_s)$$

$\sigma$ 是 sigmoid：温度过高 → 学习率降低（防止过度激活）；温度过低 → 学习率正常。

### 3.5 坐标量的涌现

两个元神经细胞 $v_i, v_j$ 之间的**涌现距离**：

$$d(v_i, v_j) = \sum_{\gamma: v_i \to v_j} \frac{1}{f(\gamma)} \cdot \text{len}(\gamma)$$

即通过所有从 $v_i$ 到 $v_j$ 的路径，加权路径长度。流量大的路径贡献小距离（"近"），流量小的贡献大距离（"远"）。这个距离是超图拓扑的涌现物，不需要外部坐标。

> [!NOTE]
> v40 初版暂不实现涌现距离（需要全局路径搜索）。保留 `MeasureCoordinate` 作为代理，但在审计日志中标注 `coordinate_source = "proxy"` 而非 `"emergent"`。

---

## §4 未实施部分

### 4.1 区层（Area Layer）
- **原因**：需要跨实验持久化机制（当前 DB schema 不支持跨 run_id 的权重存储）
- **依赖**：柱层的固化机制必须先验证
- **预计**：v41

### 4.2 突触生成（Synaptogenesis）
- **原因**：动态增加超边会改变 W_signal 的维度，影响所有下游组件
- **依赖**：需要先验证修剪机制是否稳定
- **预计**：v41

### 4.3 涌现坐标（Emergent Coordinates）
- **原因**：全局路径搜索的计算复杂度为 O(|V|²|E|)
- **依赖**：需要先验证环流检测机制
- **预计**：v42（可能需要近似算法）

### 4.4 多层影子下沉
- **原因**：棘层 Xin → 柱层影子 → 区层影子的级联需要区层存在
- **依赖**：§4.1
- **预计**：v41

### 4.5 同调分析（Homology）
- **原因**：超图的 Betti 数计算需要代数拓扑库
- **依赖**：环流检测必须先稳定
- **预计**：v42+

---

## §5 暂时降级部分

以下功能在 v40 中以简化形式实现，标注为降级：

### 5.1 基质废热细节 → 降级为标量温度
- **完整版**：废热应有空间分布（超图不同区域温度不同）
- **降级版**：全局标量温度 $T_s$
- **标注**：`degraded_from = "spatial_heat_distribution"`

### 5.2 柱层学习规则 → 降级为简单指数平均
- **完整版**：柱层应有自己的 BCM 规则（Bienenstock-Cooper-Munro）
- **降级版**：$W_{\text{column}} \mathrel{+}= \eta_{\text{slow}} \cdot (W_{\text{spine}} - W_{\text{column}})$
- **标注**：`degraded_from = "BCM_learning_rule"`

### 5.3 环流检测 → 降级为固定深度 DFS
- **完整版**：应检测所有环流并计算同调群
- **降级版**：DFS 深度限制为 4（最多 4-hop 环流）
- **标注**：`degraded_from = "full_homology_computation"`

### 5.4 P/R 竞争 → 降级为 Top-2 选择
- **完整版**：所有环流竞争基质自由能，按能量效率排序
- **降级版**：只保留流量最大（P）和次大（R）的环流
- **标注**：`degraded_from = "full_energy_competition"`

### 5.5 MeasureCoordinate → 降级保留为代理
- **完整版**：坐标量由涌现距离定义
- **降级版**：保留 `z_t = W × features`，但标注 `coordinate_source = "proxy"`
- **标注**：`degraded_from = "emergent_coordinate"`

---

## §6 实施顺序

```
Step 1: engines/hebbian_circuit.py — 核心类型
        MetaNeuron + MetaSynapticBundle + Substrate + CircuitLayer

Step 2: HebbianCircuit — 棘层 T/O/P/R/Xin 电路
        propagate() + learn() + detect_circulation() + maintain()

Step 3: 影子休眠果实升级
        shadow_hypergraph.py 添加 dormant_fruit / activate 机制

Step 4: 从现有管线构造电路
        build_circuit_from_pipeline() — 桥接 v39 → v40

Step 5: 验证
        run_v40_circuit_validation.py
```

