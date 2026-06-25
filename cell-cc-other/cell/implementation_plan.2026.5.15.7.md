# 赫布电路—类神经系统内嵌超图 架构设计

## 现状诊断：为什么当前系统不是"神经系统"

当前系统的结构是：

```
W_signal: float[6][7]     ← 一个平面矩阵，没有拓扑
WeightEntry: (from, to, w) ← 成对连接，不是超边
MeasureCoordinate: 7-tuple ← 一个向量，没有场结构
```

这不是神经系统，这是**线性代数**。没有细胞，没有突触束，没有基质。W_signal 的每个元素与其他元素之间没有结构关系——修改 W[2][3] 不会影响 W[4][5]。在真正的神经系统中，修改一个突触会通过网络拓扑影响所有相关路径。

---

## 核心设计：三元原语

### 1. MetaNeuron（元神经细胞）

元神经细胞不是数据细胞（CellRecord），而是**计算节点**。每个元神经细胞是一个具有内部状态的处理单元，它接收输入、维持膜电位、产生激活。

```python
@dataclass
class MetaNeuron:
    """赫布电路中的计算节点。
    
    类比：
      生物神经元有膜电位、离子通道、突触后电位。
      MetaNeuron 有激活值、势能累积、惯性质量。
      
    与现有系统的映射：
      - WeightEntry 的 (cumulative_potential, inertia_mass) → 神经元内部状态
      - MeasureCoordinate 的每个维度 → 一个元神经细胞
      - 未来：细胞级超图中的每个节点 → 一个元神经细胞
    """
    neuron_id: str
    layer_id: str               # 属于哪一层
    
    # ── 内部状态 ──
    activation: float = 0.0     # 当前激活值（膜电位类比）
    resting_potential: float = 0.0  # 静息电位（无输入时回归）
    potential: float = 0.0      # 累积势能 Φ（历史深度）
    inertia: float = 1.0        # 惯性质量 M（抗变化能力）
    
    # ── 代谢状态 ──
    energy: float = 1.0         # 可用能量（耗尽→死亡→入影子层）
    heat_output: float = 0.0    # 上一 tick 产生的热（耗散到基质）
    
    # ── 代理槽 ──
    proxy_slot: Optional[str] = None  # 当前托管的代理模块名称
    is_proxy_host: bool = False       # 是否正在托管代理
```

### 2. MetaSynapticBundle（元突触束）

突触束不是单个权重 W[i][j]，而是一组从**源神经元集合**到**目标神经元集合**的定向连接。这就是"超边"——它连接的不是两个节点，而是两个**集合**。

```python
@dataclass
class MetaSynapticBundle:
    """赫布超图中的超边。
    
    关键区别：
      普通图的边: A → B（一对一）
      超边:       {A, B, C} → {D, E}（多对多）
      
    物理类比：
      一束轴突从若干源细胞投射到若干目标细胞。
      束中每根轴突有自己的权重，但束作为整体
      有一个"束强度"——当束强度低于阈值时，
      整束被修剪（突触束消除）。
      
    赫布学习：
      ΔW_bundle = η · pre_activation · post_activation / M_bundle
      其中 M_bundle 是束的惯性质量（来自 Engine B 的拓扑迟滞）。
    """
    bundle_id: str
    source_neurons: List[str]   # 源神经元 ID 集合
    target_neurons: List[str]   # 目标神经元 ID 集合
    
    # ── 权重张量 ──
    # weights[i][j] = 从 source_neurons[i] 到 target_neurons[j] 的连接强度
    weights: List[List[float]] = field(default_factory=list)
    
    # ── 束级属性 ──
    bundle_strength: float = 1.0    # 整束的强度（低于阈值→修剪）
    bundle_inertia: float = 1.0     # 束的惯性（深层束难以修改）
    transport_cost: float = 0.0     # 通过此束传输的代价
    
    # ── 赫布学习状态 ──
    learning_rule: str = "oja"      # "oja" | "stdp" | "bcm" | "frozen"
    last_pre_activation: float = 0.0
    last_post_activation: float = 0.0
```

### 3. Substrate（基质）

基质是神经系统的"体液环境"——它不传递信号，但它接收所有计算产生的热量，维持整体的能量预算，决定系统的"温度"。

```python
@dataclass
class Substrate:
    """热力学基质——赫布电路的能量环境。
    
    物理类比：
      大脑的脑脊液/血液系统。不传递神经信号，
      但它：
      1. 带走代谢废热（死亡的突触、失败的假设）
      2. 供给能量（ATP → 突触传递需要能量）
      3. 维持温度（太热→过度激活/癫痫；太冷→沉默）
      
    与现有系统的映射：
      - 外部熵账本 → 基质温度的测量工具
      - 影子层的 shadow_energy 衰减 → 废热排放
      - Engine B 的 Oja λ 衰减 → 能量消耗
      - d_σ_t → 基质中的时间流速
    """
    temperature: float = 1.0        # 系统温度（0=冻结, 1=正常, >2=过热）
    free_energy: float = 100.0      # 可用自由能（限制每 tick 总 ΔW）
    heat_sink: float = 0.0          # 累积废热
    entropy: float = 0.0            # 当前熵水平（来自熵账本）
    
    # ── 能量预算 ──
    energy_per_tick: float = 10.0   # 每 tick 补充的能量
    max_delta_w_budget: float = 1.0 # 每 tick 允许的总 |ΔW| 预算
```

---

## 多层赫布电路 ⟷ 多层超图 的对应关系

现有管线可以自然映射为 4 层神经电路，每层有自己的超图拓扑：

```
Layer 0 (感觉层): CellRecord 信号 → Transport 边代价
  ├── 超图节点: 数据细胞 (214个)
  ├── 超图边:   Transport 边 (cell_i → cell_j, cost)
  └── 赫布规则: 共同传输的细胞对 → 边权增强

Layer 1 (编码层): 信号特征 → z_t 测度坐标
  ├── 超图节点: 信号特征维度 (6个) + z_t 维度 (7个)
  ├── 超图边:   W_signal 的每一行 = 一个突触束
  │             (1个信号特征 → 7个z_t维度 = 1对7的超边)
  └── 赫布规则: Oja 规则 (当前)

Layer 2 (整合层): z_t → Φ → d_σ_t
  ├── 超图节点: 7个 z_t 维度 + Φ + d_σ_t
  ├── 超图边:   to_phi 的系数 + to_d_sigma_inputs 的映射
  └── 赫布规则: 尚未定义 (当前是固定系数)

Layer 3 (决策层): d_σ_t → 运动模式分类
  ├── 超图节点: 8个运动模式 (regimes)
  ├── 超图边:   BayesianMotionRecognizer 的后验分布
  └── 赫布规则: Bayesian 在线学习 (当前)
```

### 层间连接 = 元突触束

```
Layer 0 → Layer 1:  6 条突触束 (每个信号特征对应一束)
                    当前: extract_signal_features 的 6 个统计量
                    结构性改进: 应包含 Transport 层的边代价信息

Layer 1 → Layer 2:  to_phi() 和 to_d_sigma_inputs()
                    当前: 固定系数
                    结构性改进: 系数应由 Layer 1 超图的拓扑决定

Layer 2 → Layer 3:  FeatureExtractor.extract → BayesianMotionRecognizer
                    当前: 8 维特征向量
                    结构性改进: 应包含 d_σ_t 的时间序列特性
```

---

## 关键设计问题："内嵌"的含义

你问的核心是：**如何让赫布电路内嵌超图**。有两种理解：

### 理解 A：超图是电路的**拓扑**

```
电路的连接方式 = 超图的邻接结构
神经元 = 超图节点
突触束 = 超图的超边
赫布学习 = 修改超图的边权重
```

这是自然的映射。但它意味着**学习只改变权重，不改变拓扑**。拓扑是固定的（6 个信号特征 → 7 个 z_t 维度），权重是可变的。

### 理解 B：超图是电路的**计算基底**

```
电路运行在超图上 = 电路的每次激活传播
都沿着超图的超边进行。
修改超图拓扑 = 修改电路的连接方式。
赫布学习可以：
  1. 修改边权重（弱变化）
  2. 创建新超边（突触生成 synaptogenesis）
  3. 删除超边（突触修剪 synaptic pruning）
  4. 分裂/合并节点（神经元分化/聚合）
```

这是更强的含义——超图不仅是拓扑，**超图本身在学习过程中演化**。

> [!IMPORTANT]
> 理解 B 更接近真实神经系统。在大脑中，突触不是固定的——突触生成和修剪是学习的核心机制。W_signal 目前是固定 6×7 = 不允许新突触 = 不允许拓扑变化。

---

## 具体嵌入方案

### HebbianCircuit：赫布电路类

```python
class HebbianCircuit:
    """多层赫布电路，内嵌于超图拓扑。
    
    每一层是一组 MetaNeuron + 连接它们的 MetaSynapticBundle。
    层间连接也是 MetaSynapticBundle。
    整个电路共享一个 Substrate。
    
    拓扑可以演化：
      - 超边权重低于阈值 → 修剪 (pruning)
      - 两个活跃神经元之间无连接 → 生成 (synaptogenesis)
      - 神经元能量耗尽 → 死亡 → 入影子层 (apoptosis)
    """
    
    def __init__(self):
        self.layers: Dict[str, CircuitLayer] = {}
        self.inter_layer_bundles: List[MetaSynapticBundle] = []
        self.substrate = Substrate()
        self.shadow: Optional[ShadowHypergraph] = None
    
    def propagate(self, input_activations: Dict[str, float]):
        """前向传播：逐层激活，沿超边传递。"""
        ...
    
    def learn(self):
        """赫布学习：每条超边根据自己的规则更新。"""
        ...
    
    def maintain(self):
        """维护：修剪弱超边，生成新超边，能量耗尽→死亡。"""
        ...


@dataclass
class CircuitLayer:
    """赫布电路的一层。"""
    layer_id: str
    neurons: Dict[str, MetaNeuron] = field(default_factory=dict)
    internal_bundles: List[MetaSynapticBundle] = field(default_factory=list)
    
    # 层内超图拓扑
    # adjacency[neuron_a] = [(bundle_id, neuron_b, weight), ...]
    adjacency: Dict[str, List] = field(default_factory=dict)
```

### 与现有系统的嵌入映射

```python
# 如何从现有系统构造 HebbianCircuit

def build_circuit_from_pipeline(signal_transform, engine_b, shadow):
    circuit = HebbianCircuit()
    
    # Layer 1: 信号→z_t（编码层）
    L1 = CircuitLayer(layer_id="encoding")
    # 6 个信号特征 → 6 个输入神经元
    for i, fname in enumerate(signal_transform.SIGNAL_FEATURES):
        L1.neurons[fname] = MetaNeuron(
            neuron_id=fname, layer_id="encoding")
    # 7 个 z_t 维度 → 7 个输出神经元
    for j, cname in enumerate(["trans","drift","gamma","xin","potential","churn","mag"]):
        L1.neurons[cname] = MetaNeuron(
            neuron_id=cname, layer_id="encoding")
    
    # W_signal 的每一行 → 一条突触束
    for i, fname in enumerate(signal_transform.SIGNAL_FEATURES):
        bundle = MetaSynapticBundle(
            bundle_id=f"W_signal_row_{i}",
            source_neurons=[fname],
            target_neurons=["trans","drift","gamma","xin","potential","churn","mag"],
            weights=[signal_transform.W[i]],  # 直接使用现有权重
            learning_rule="oja",
        )
        L1.internal_bundles.append(bundle)
    
    circuit.layers["encoding"] = L1
    
    # Layer 2: z_t→Φ→d_σ_t（整合层）
    # ... 类似构造
    
    circuit.substrate = Substrate()
    circuit.shadow = shadow
    return circuit
```

---

## 基质与热力学交换

```
每 tick:
  1. 基质补充 energy_per_tick 的自由能
  2. 所有突触束的 |ΔW| 消耗自由能
  3. 如果自由能不足 → 优先修改 inertia 最小的束（年轻的先变）
  4. 死亡的神经元释放其 energy 到 heat_sink
  5. 基质 temperature = heat_sink / (tick + 1)
  6. 高温 → 所有学习率 × temperature（过热=过度学习）
  7. 低温 → 所有学习率 × temperature（过冷=学习停滞）
  
  → 外部熵账本 = 基质温度的测量仪器
  → 影子层 = 死亡神经元的墓地
  → d_σ_t = 基质中的局部时间流速
```

---

## 决策点

> [!IMPORTANT]
> 1. **拓扑演化是否启用？** 如果启用突触生成/修剪，W_signal 的维度会动态变化。这是根本性改变。建议初版只启用修剪（删除弱超边），不启用生成。
>
> 2. **基质温度是否反馈到学习率？** 如果是，这打破了当前的"熵账本不影响管线"的铁律。建议：基质温度影响学习率，但外部熵账本只是测量温度的工具，不直接设定温度。这样铁律变为"外部熵账本不直接影响管线，但通过基质间接影响"。
>
> 3. **Layer 0（感觉层）是否需要实现？** 在数据细胞之间建立超图需要 O(N²) 的边（214² = 45796）。建议初版只实现 Layer 1（编码层）和 Layer 2（整合层）。
>
> 4. **与现有代码的兼容性**：`HebbianCircuit` 是一个**新的并行结构**，不替代 `pipeline_engine.py`。管线继续运行，电路从管线的中间产物中提取信号并做自己的学习。当电路成熟后，可以逐步替换管线中的对应模块。

