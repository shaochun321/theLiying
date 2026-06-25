# 前神经系统 → HebbianCircuit 继承分析

## 前神经系统的定位

```
前神经系统 (PreNeural) 不是 HebbianCircuit 的前级模块。
它是一个 验证架构 — 先验证概念，然后指导 HebbianCircuit 的构建。

时间线:
  1. 细胞球数据 → 前神经系统 → 状态分离验证
  2. 验证通过 → 概念被确认
  3. HebbianCircuit 用这些已验证的概念构建类神经系统
  4. 前神经系统退役，但代码保留为参考
```

---

## 前神经系统验证了什么 (7 个已验证原则)

从 state_separation_v0.1 的验收报告:

| # | 已验证原则 | 验证数据 |
|---|-----------|---------|
| 1 | 无语义时空事件能分离成多条轨迹 | 1500 events → 5 trajectories, 1498/1500 绑定成功 |
| 2 | 轨迹有连续性 | continuity_score = 0.972 |
| 3 | 轨迹有守恒性 | conservation_score = 0.767 |
| 4 | 轨迹有相位一致性 | phase_coherence = 0.794 |
| 5 | 噪声下不崩溃 | 30% noise 下 stability 仍 > 0.87 |
| 6 | Xin 残余独立记账 | 2 residues, mass proxy 随噪声增加 |
| 7 | 跨通道用相位绑定而非语义 | 15 probes, avg_coherence = 0.925 |

```
额外关键验证:
  ✅ 隐藏的低频结构 → 被识别为 xi_proto_candidate (不是噪声)
  ✅ 轨迹回投到 3D 细胞球 → 误差比全局基线低 55%
```

---

## 前神经系统的结构对应

### PatchAfferentNode → MetaNeuron

```
PatchAfferentNode:                MetaNeuron:
  node_id                          neuron_id
  position (x,y,z)                 (无显式位置)
  normal (法向量)                   (无)
  V_hair_cell = -65.0              activation
  calcium = 0.0                    calcium = 0.03         ✅ 保留
  release_rate = 0.0               (通过 STDP 体现)
  V_afferent = -70.0               (膜电位 → Capacitor)
  met_open_probability = 0.0       (→ MOSFET conduct)
  spike_rate = 0.0                 (→ activation_count)
  regularity = 0.0                 (→ coherence?)
  timing_precision = 0.0           (→ trace_tau?)
  
  source_cell_ids → 知道自己来自哪些细胞   (当前: proxy_for)
  weights_to_cells → 每个细胞的贡献权重    (当前: 无)
```

### PatchAfferentEdge → MetaSynapticBundle

```
PatchAfferentEdge:                MetaSynapticBundle:
  source, target                   source_neuron_ids, target_neuron_ids
  weight = 1.0                     weight_matrix              ✅ 保留
  delay = 0.0                      cable_delay                ✅ 保留
  edge_kind (5种)                  (无, 只有一种边)
  provenance                       (无)
```

### 前神经核心链路 → HebbianCircuit 链路

```
前神经:
  raw_event_stream
    → origin_anchor (动态原点)
    → latent_trajectory (潜轨迹)
    → trajectory_event_binding (绑定)
    → xin_residue_state (残余)
    → reprojection_report (回投)

HebbianCircuit:
  _compute_sensory() (输入)
    → transport() (T)
    → observe() / detect_circulations() (O/P/R)
    → accumulate_xin() (Xin)
    → (无回投)
```

---

## 什么被保留, 什么被丢失

### ✅ 保留的

```
1. calcium 机制 → MetaNeuron.calcium (EMA 基线)
2. 连接图结构 → MetaSynapticBundle (源→目标)
3. 权重可塑性 → STDP (Hebbian learning)
4. Xin 作为残余 → xin_tension on bundles
5. 管道延迟 → cable_delay
6. 无语义原则 → 项目级原则
```

### ❌ 丢失的

```
1. 1:1 细胞对应
   前神经: 每个 PatchNode 知道自己来自哪些 source_cell_ids
   HebbianCircuit: _compute_sensory() 压缩 30→7

2. 动态原点 (origin_anchor)
   前神经: origin_anchor 由前神经节点活动动态更新
   HebbianCircuit: 没有"原点"概念

3. 潜轨迹 (latent_trajectory) 跟踪
   前神经: 轨迹有 centroid, velocity, phase, continuity_score...
   HebbianCircuit: 只有当前 tick 的环流, 无跨 tick 轨迹

4. 回投能力
   前神经: trajectory_reprojection_report (55% improvement)
   HebbianCircuit: 无法回投到源数据

5. 跨通道相位绑定
   前神经: 3 channels × phase coherence binding
   HebbianCircuit: 7 个标量特征, 通道信息已压缩

6. 边的类型多样性
   前神经: 5 种边 (contact, synaptic, functional, spatial, diagnostic)
   HebbianCircuit: 1 种边 (MetaSynapticBundle)

7. 噪声鲁棒性验证
   前神经: 有系统的噪声 sweep 测试
   HebbianCircuit: 无此测试基础设施
```

---

## 前神经 → 运动状态分离 → 固化 的链路

```
你描述的历史流程:

  1. 细胞球产生原始信号 (1500 events, 3 channels, 500 cell snapshots)
     → 前神经系统接收
     
  2. 前神经系统做状态分离
     → 5 条潜轨迹 (无语义)
     → 每条有 continuity + conservation + phase coherence
     
  3. 验证: 反向驱动细胞球
     → 用分离好的数据模型反向驱动底层
     → 外部判断行为状态是否对齐
     → reprojection improvement = 55%
     
  4. 屏蔽测试:
     → 遮蔽部分底层输入
     → 看系统是否仍能正确分类
     → 稳定性 > 0.87 at 30% noise
     
  5. 固化:
     → 通过验证的轨迹模式成为"参考"
     → 指导 HebbianCircuit 的构建
     → 但具体的固化机制 (怎么把轨迹模式写入 HebbianCircuit)
        似乎在代码中没有显式实现
```

---

## 关于运动状态种类

```
前神经系统分离出 5 条 latent_trajectory。
这对应你说的运动状态分离。

但 5 是否 = "平移, 旋转, 振动, 静止/惯性 + 某种复合"?
还是数据驱动的任意 5 条?

从代码看, trajectory 数量不是预设的——
它由 state_separation 算法从数据中发现。

建议:
  如果用球谐分析来指导, l=0,1,2 对应:
  l=0: 呼吸/膨胀 (静止?)
  l=1: 平移 (3 个子模式: x,y,z)
  l=2: 变形/旋转 (5 个子模式)
  
  但需要确认: 前神经的 5 条轨迹是否和球谐模式对应?
```

---

## 关键结论

```
前神经系统是一个成功的验证原型:
  18/18 + 39/39 + 20/20 全部通过

它验证的概念应该在 HebbianCircuit 中得到继承:
  ✅ 已继承: calcium, connectivity, STDP, Xin, delay
  ❌ 未继承: 1:1 对应, 动态原点, 轨迹跟踪, 回投, 相位绑定

"固化"的关键问题:
  前神经验证了模式存在,
  但模式→HebbianCircuit 的写入机制
  似乎是隐含的 (通过架构设计指导),
  而非显式的 (没有 "把模式写入权重" 的代码)。
```
