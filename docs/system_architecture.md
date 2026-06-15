# 系统现状完整图谱

## §1 信号流程（每步 dt=0.001s 执行一次）

```
┌──────────────────── 每步信号流 ────────────────────┐
│                                                     │
│  ① Motor EMA → MuscleSystem → Body.step(forces)     │
│     (上一步的 motor 输出驱动本步的身体运动)            │
│         ↓                                           │
│  ② MotionState 提取                                  │
│     motion_potential, temporal, spatial, otolith      │
│         ↓                                           │
│  ③ MotorDecisionLayer.process()                      │
│     CPG 节律调制 → DirectionSelect(stub) → output     │
│         ↓                                           │
│  ④ Kinetic damping + Body.step(forces)               │
│         ↓                                           │
│  ⑤ Efference copy: predicted_acc vs actual_acc       │
│         ↓                                           │
│  ⑥ ThermalMembrane.sense() → therm signal            │
│         ↓                                           │
│  ⑦ Otolith: body.acc × 500 → oto_x/y/z 注入         │
│         ↓                                           │
│  ⑧ Oscillator modulation (每轴一个振荡器)             │
│         ↓                                           │
│  ⑨ Mother step: HebbianCircuit.step()                │
│     Met → HC → Aff(reg/irr) → Enc → Col → Motor     │
│         ↓                                           │
│  ⑩ 后处理：                                          │
│     - Aff 膜电压振荡器调制                            │
│     - Enc/Col 自适应阻尼                              │
│     - NDR 不应期门控                                  │
│     - DA 更新 (dξ/dt)                                │
│     - Binding Layer 跨模态检测                        │
│     - Motor 反馈抑制                                  │
│     - 影子层观测                                      │
│         ↓                                           │
│  ⑪ 每 10000 步：结构生长检查                          │
│     sprout / prune / mitosis / apoptosis             │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## §2 组件清单

### 信号通路（主层 — 活跃）

| 层 | 组件 | 数量 | 文件 | 状态 |
|----|------|------|------|------|
| L0 | Body (质点) | 1 | `world.py` | ✅ 活跃 |
| L0 | MuscleSystem (3 肌肉) | 1 | `muscle.py` | ✅ 活跃 |
| L0 | ThermalMembrane | 1 | `thermal_membrane.py` | ✅ 活跃 |
| L1 | Met (机械转导 MOSFET) | 6 (每轴 1) | `chain.py` | ✅ 活跃 |
| L2 | HC (毛细胞, 3 通道) | 6 | `chain.py` | ✅ 活跃 |
| L3 | Aff_reg (正则传入) | 6 | `chain.py` | ✅ 活跃，脉冲 |
| L3 | Aff_irr (不正则传入) | 6 | `chain.py` | ✅ 活跃，脉冲 |
| L4 | Enc (编码) | 14 (7轴×2) | `hebbian.py` | ✅ 活跃，脉冲 |
| L5 | Col (柱状) | 7 | `hebbian.py` | ✅ 活跃，脉冲 |
| L6 | Motor | 60 (20/axis) | `hebbian.py` | ✅ 活跃，脉冲 |
| — | Binding Layer | 21 cells | `binding.py` | ⚠️ 存在但 dormant |

### 中间决策层（新增）

| 组件 | 文件 | 状态 |
|------|------|------|
| MotionState 提取 | `variant_adapter.py` L357 | ✅ 活跃 |
| MotorRhythmGenerator (CPG) | `motor_decision.py` | ✅ 活跃 |
| DirectionSelector | `motor_decision.py` | ⬜ Stub (passthrough) |
| SpatialNavigator | `motor_decision.py` | ⬜ Stub (passthrough) |

### 影子层

| 组件 | 数量 | 文件 | 状态 |
|------|------|------|------|
| Shadow Enc neurons | 14 | `shadow_sandbox.py` | ⚠️ 观测者，不反馈 |
| Shadow Col neurons | 7 | `shadow_sandbox.py` | ⚠️ 观测者，不反馈 |
| Shadow Motor neurons | 3 | `shadow_sandbox.py` | ⚠️ 观测者，不反馈 |
| Shadow Enc→Col bundles | 7 | `shadow_sandbox.py` | ⚠️ STDP 在跑 |
| Shadow Col→Mot bundles | 7 | `shadow_sandbox.py` | ⚠️ STDP 在跑 |
| Shadow Cross-axis bundles | 21 | `shadow_sandbox.py` | ⚠️ 多数 silent |
| Shadow ECM (3 层) | 3 | `shadow_sandbox.py` | ⚠️ PNN 在积累 |
| Shadow Vascular | 1 | `shadow_sandbox.py` | ⚠️ 低流量冷却 |

> [!IMPORTANT]
> **影子层的现状**：代码完整，每 10 步执行一次 observe()。它有自己的 Neuron、Bundle、ECM、Vascular——全部是真实组件。它接收主层的 Xin 作为输入，运行 STDP 学习，计算 κ（收缩度）和 ν（运动势）。
> 
> **但它是纯观察者**——计算结果（κ, ν, ds²）不反馈到主层。主层不知道影子层的存在。

### 治理与监督

| 组件 | 文件 | 状态 |
|------|------|------|
| Noether Probe (能量守恒) | `noether_probe.py` | ✅ 活跃，0 违反 |
| Governance (Fuse+Ledger+Modeler) | `governance/` | ✅ 活跃 |
| TOPRXin Ledger (信息账本) | `toprxin_ledger.py` | ✅ 活跃 |
| Ultrametric (超度量树) | `toprxin_ledger.py` | ✅ 活跃，depth=5 |
| RecursionTracker (分裂谱系) | `toprxin_ledger.py` | ✅ 活跃 |

### 学习与生长

| 机制 | 触发条件 | 频率 | 状态 |
|------|---------|------|------|
| STDP | 每步 | 每步 | ✅ 活跃（主层+影子层） |
| Sprout (发芽) | \|ξ\| > 0.3 | 每 10k 步 | ✅ ~55/200k |
| Prune (修剪) | w < 0.001 | 每 10k 步 | ✅ ~55/200k（与 sprout 平衡） |
| Mitosis (分裂) | V_fat 持续高 | 不定 | ✅ 200k 后停止（cap=20） |
| Apoptosis (凋亡) | E 持续低 | 不定 | ✅ 存在但从未触发 |
| Fruit 状态转移 | STDP 累积 | 连续 | ⚠️ 存在，多数 dormant |
| Maturation | Φ 累积 | 连续 | ⚠️ 存在，stage 未转变 |

### 反馈机制

| 机制 | 连接 | 状态 |
|------|------|------|
| 感觉运动闭环 | Motor→Muscle→Body→Otolith→Aff | ✅ 活跃 |
| Efference copy | Motor acts vs Body acc | ✅ P0 新增 |
| Motor 反馈抑制 | Motor→Col 抑制 | ✅ 存在 |
| CPG 节律调制 | MotionState→CPG→Motor | ✅ 新增 |
| DA 调制 | dξ/dt→DA→学习率 | ⚠️ 始终 baseline |
| 影子层→主层 | — | ❌ 不存在 |

---

## §3 更新术语表（新增条目）

### 成熟阶段（Neuron Maturation）

| 阶段 | 英文 | 中文 | 特性 | 代码 |
|------|------|------|------|------|
| Stage 0 | Spine | 新兵 | 最高可塑性，STDP 学习率最大 | `neuron.py` maturation_stage=0 |
| Stage 1 | Column | 成熟 | BCM 精调，中等可塑性 | maturation_stage=1 |
| Stage 2 | Area | 老兵 | 冻结，不再学习 | maturation_stage=2 |
| 转变条件 | — | — | 累积激活量 Φ > 阈值 (Φ₁=50, Φ₂=500) | potential_phi |

### 果实生命周期（Fruit State on Bundle）

| 阶段 | 英文 | 中文 | 条件 |
|------|------|------|------|
| dormant | 休眠 | 权重太低 | w < threshold |
| growing | 生长中 | Xin 驱动学习 | Xin > 0, w 在增 |
| ripe | 成熟 | 功能稳定 | w 稳定 |
| decayed | 衰退 | prune 候选 | w 持续下降 |

### 影子层专用术语

| 术语 | 中文 | 定义 |
|------|------|------|
| **κ (kappa)** | 收缩度 | 跨轴相关 / 自方差，>1=扩张, <1=收缩 |
| **ν (nu)** | 运动势 | dK/dt，自由能变化率 |
| **K** | 自由能核 | Σ ξ²，所有 Xin 的平方和 |
| **ds²** | 时空间隔 | g_ij·δa_i·δa_j，<0=类时, >0=类空 |
| **δa** | 偏差激活 | a_i - ā_i，去基线后的激活 |
| **Silent synapse** | 沉默突触 | 权重过低的跨轴 bundle，冻结但可唤醒 |
| **Construction power** | 建设模式 | 影子层能量无限（调试用） |

### CPG 专用术语

| 术语 | 中文 | 定义 |
|------|------|------|
| **Phase φ** | 相位 | 振荡器在 [0, 2π] 上的位置 |
| **Envelope** | 包络 | 0.5+0.5sin(φ)，调制 motor 输出 |
| **Entrainment** | 锁频 | 外部信号拉动 CPG 频率 |
| **Phase coupling** | 相位耦合 | Kuramoto 模型，轴间保持 120° |

---

## §4 影子层的真相

影子层的代码量很大（657 行），构建很完整：
- 21 个 shadow 神经元（enc×14 + col×7 + mot×3 = 24... 实际是 14+7+3）
- ~35 个 shadow bundle（enc→col, col→mot, cross-axis）
- 独立的 ECM、Vascular、PNN
- 计算 κ、ν、ds²

**但它的输出（κ, ν, ds²）从未被任何其他代码读取或使用。**

影子层在 `variant_adapter.py` L725 每步被调用：
```python
self.shadow_sandbox.observe(self, self._maturation_tick)
```

但 `observe()` 是纯观察——它不返回值，也不修改主层。

影子层的状态可以通过 `get_state()` 查看（L960 中包含在 summary 输出里），但没有任何代码基于影子层的输出做决策。

**总结：影子层已建好但未连线。** 它像一个戴着耳机看比赛的教练——在分析比赛，但没有对讲机告诉球员该怎么做。
