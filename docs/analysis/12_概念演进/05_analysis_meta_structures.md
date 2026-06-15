# 元结构定义

## 已有的原子单元

代码中已经存在三种原子类:

```
1. MetaNeuron (L74)
   = Capacitor + MOSFET + PowerRail + STDP traces + homeostasis + maturation
   = 一个完整的计算单元

2. MetaSynapticBundle (L330)
   = weight matrix + cable (delay + attenuation + pulse_queue)
   + STDP/BCM/Oja + xin_tension + transport_cost
   = 一个完整的传输管道

3. SubstrateNetwork (L880)
   = node_energy + edges (conductance) + neuron binding
   = 一个能量分配网络
```

**这三个就是元结构的基础。** 它们已经有了物理属性和经过验证的行为。

---

## 元结构定义

### 元单元 (MetaUnit)

```
一个 MetaUnit = 一个 MetaNeuron 实例

构成:
  · 1 × Capacitor (膜电容 → 状态存储)
  · 1 × MOSFET (阈值门控 → 选择性激活)
  · 1 × PowerRail (能量供应 → 代谢约束)
  · STDP traces (时序记忆)
  · homeostatic regulation (自稳态)
  · maturation state (分化阶段: spine → column → area)

不变量:
  · activate() 的逻辑不改 — 这是母本
  · decay() 的逻辑不改 — 这是母本

可分化的参数:
  · target_rate (活动目标)
  · calcium_tau (时间常数)
  · threshold (灵敏度)
  · inertia (惯性)
  · maturation 初始状态
  · r_leak (泄漏电阻)
```

### 元管道 (MetaPipe)

```
一个 MetaPipe = 一个 MetaSynapticBundle 实例

构成:
  · weight matrix (权重张量)
  · cable_length + propagation_velocity + cable_resistance (物理传输)
  · pulse_queue (延迟传导)
  · arrival_trace (突触时序)
  · learning_rule (学习规则选择)
  · xin_tension (残差张力)

不变量:
  · propagate() 的逻辑不改
  · inject_pulse() / deliver_pulses() 不改
  · stdp_update() 不改

可分化的参数:
  · cable_length (距离 → 决定延迟)
  · cable_resistance (衰减)
  · propagation_velocity (传导速度)
  · learning_rule ("oja" / "bcm" / "frozen")
  · _arrival_trace_decay (突触时序衰减)
```

### 元块 (MetaBlock)

```
一个 MetaBlock = SubstrateNetwork 中的一个 node

构成:
  · node_energy (能量水平)
  · node_capacity (最大容量)
  · edges → 其他 MetaBlock (能量流通)
  · neuron_binding → 多个 MetaUnit (绑定供能)

不变量:
  · dV/dt = Σ G_ij (V_j - V_i) + source - consumption
  · 能量守恒

可分化的参数:
  · capacity (最大能量)
  · conductance (各 edge 的导率)
```

---

## 规模对应规则

```
你的原始设计:
  1 cell ↔ 1 pipeline ↔ 0.5 T/O/P/R/Xin

用元结构表达:
  1 cell ↔ 1 MetaUnit ↔ 1 MetaPipe ↔ 0.5 T/O/P/R/Xin slot

  N cells → N MetaUnits (encoding)
          → N MetaPipes (encoding → column)
          → N MetaUnits (column)
          → N/2 T/O/P/R/Xin 处理槽位
```

### 当前代码 vs 正确对应

```
当前 (断裂的):
  build_circuit_from_signal_transform():
    feature_names = ["sig_mean", "sig_std", ...] ← 6个, 硬编码
    cost_names = ["transition", "drift", ...]     ← 7个, 硬编码
    → 13 个 MetaUnit, 与 N 无关

应该是:
  build_circuit_from_cells(n_cells):
    for i in range(n_cells):
      enc.add_neuron(f"cell_{i}")              ← N 个 MetaUnit
    for i in range(n_cells):
      col.add_neuron(f"col_{i}")               ← N 个 MetaUnit
    for i in range(n_cells):
      pipe = enc.add_bundle(                   ← N 个 MetaPipe
        source_ids=[f"cell_{i}"],
        target_ids=[f"col_{i}"])
    
    substrate.add_node("enc_sub", capacity=f(N))
    substrate.add_node("col_sub", capacity=f(N))
    → 2N 个 MetaUnit + N 个 MetaPipe
    → 规模随 N 自动缩放
```

---

## 分化建立在元结构之上

```
所有区域共享同一种 MetaUnit 母本:
  activate(), decay(), try_mature()  ← 不改

分化 = 参数向量不同:

  encoding 区的 MetaUnit:
    target_rate=0.05, calcium_tau=10, maturation="spine"
    → 快速响应, 低阈值, 易于学习

  column 区的 MetaUnit:
    target_rate=0.03, calcium_tau=20, maturation="column"
    → 慢速响应, 需要持续信号, 巩固用

  sediment 区的 MetaUnit:
    target_rate=0.01, calcium_tau=50, maturation="area"
    → 极慢响应, 长期积累

门控 (之前实验的 GateTemplate):
  也是 MetaUnit 的一种特化 — 
  一个 MetaUnit 可以扮演门控角色:
    输入 = 同步性 + 对比度
    输出 = 门控信号 → 调制相邻 MetaPipe 的 learning_rule
    参数 = (τ, θ, cw) ← 分化

  不需要单独的 GateTemplate 类。
  门控就是一个特化的 MetaUnit。
```

---

## 元管道的 T/O/P/R/Xin

```
每个 MetaPipe 内部就包含 T/O/P/R/Xin 的处理:

  T (传递): propagate() 的前向传播
  O (观测): last_pre_activation / last_post_activation
  P (预测): 下一 tick 的 target_acts 预期
  R (反馈): STDP/BCM 的反向权重调整
  Xin (残差): xin_tension 字段

  这 5 个不是独立的模块,
  而是每个 MetaPipe 内部的 5 个阶段。

  2 个 MetaPipe 共享 1 套 T/O/P/R/Xin 处理
  = 你原始设计的 "1 pipeline : 0.5 T/O/P/R/Xin"
```

---

## 总结

```
元结构:
  MetaUnit  = MetaNeuron (已有, 母本不改)
  MetaPipe  = MetaSynapticBundle (已有, 母本不改)
  MetaBlock = SubstrateNetwork.node (已有, 母本不改)

规模规则:
  N cells → N MetaUnit + N MetaPipe + N MetaUnit(column) + MetaBlock(auto)

分化规则:
  同一母本 + 不同参数向量 = 不同区域行为
  门控 = 特化的 MetaUnit
  T/O/P/R/Xin = MetaPipe 内部的 5 个处理阶段

恢复对应:
  build_circuit_from_cells(n_cells) 替代 build_circuit_from_signal_transform()
  _compute_sensory() 返回 per-cell 信号而非聚合统计
```

> [!IMPORTANT]
> **关键: 三个元结构的代码都已经存在且经过验证。**
> 不需要重写——需要的是:
> 1. 把 build_circuit 从硬编码 6+7 改成 N 驱动
> 2. 把 _compute_sensory 从聚合改成 per-cell
> 3. 让所有分化通过参数向量实现, 不改母本
