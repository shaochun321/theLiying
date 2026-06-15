# v2.0 蓝图补充的关键概念

读完两份早期定义后，系统的完整图景更清晰了。以下是 v2.0 蓝图补充的关键内容。

---

## 1. 系统的正确名称

```
你的系统不叫 "HebbianCircuit"——那只是其中的一个组件。

正确名称:
  HG-FHPMS = Hebbian-Guided Fiber-Hypergraph Potential Memory Store
  赫布指导的纤维—超图—势记忆存储系统

  RLIS = Relativistic Ledger Information Store
  相对论化账本信息存储

代码中的 HebbianCircuit ≈ HG-FHPMS 的一个降级实现
代码中的 entropy_ledger_proxy ≈ RLIS 的一个占位符
```

---

## 2. 系统的核心任务

```
不是: "学习", "分类", "预测"
不是: "记忆", "回忆", "识别"

而是: 区分运动

5 种运动:
  P core  = 稳定吸收运动 ("这个信息被稳定地锚定了")
  P band  = 可吸收边沿 ("这个信息正在被吸收")
  R core  = 反压修正运动 ("这个信息在挑战现有解释")
  R band  = 反压成核带 ("反压正在形成但还不够强")
  M band  = 屏蔽过渡运动 ("masking 正在介入")
  Xin     = 残余游走 ("无法被 P/R/M 消化的残余")
  U       = 不可见 / heat bath ("完全未解决")

主线只做这件事: 分辨输入属于哪种运动, 以什么比例。
不做语义解释。
```

---

## 3. P/R/Xin 的完整 7 分量测度

```
之前 (v1): ρ = (p, r, x, u)          ← 4 分量
v2.0 蓝图: ρ = (p_c, p_b, r_c, r_b, m_b, x, u) ← 7 分量

  p_c + p_b + r_c + r_b + m_b + x + u = 1

每个分量的含义:
  p_c = P core (已稳定锚定的核心部分)
  p_b = P band (正在被吸收的边沿)
  r_c = R core (已形成的反压核心)
  r_b = R band (正在形成的反压带)
  m_b = masking band (屏蔽/过渡区)
  x   = true Xin (真正的残余)
  u   = unresolved (未解决 / 热浴)
```

```
当前代码的差距:

  代码中没有 7 分量测度。
  P = 最强环流路径 (有/无)
  R = 第二强环流 (有/无)
  xin_tension = 一个标量
  没有 p_band, r_band, m_band, u
```

---

## 4. HG-FHPMS 不只是存储——它做运动势垫支

```
你的核心理念:
  "Hebbian 电路与超图不是只存储过去,
   而是生成并提供运动势, 为后续行为做运动势垫支。"

预置运动势:
  Φ_pre = Φ_Hebb + Φ_Hyper + Φ_PRX + Φ_Ledger

  新的输入不是落在空白空间——
  而是落入被历史和结构预先塑形的势场。

  长期稳定的 P 路径 → 降低该路径的有效自由能
  → 形成 "垫支出来的最小自由能通道"
  → 新输入自然倾向于走这条已铺好的路

  q_t* = argmin_q [D(q, Encode(I_t)) + Φ_pre(q,t)]
```

```
类比:
  你经常走同一条路回家。
  走得多了, 这条路变得越来越"顺"——
  不是路变了, 是你的内部势场变了:
  那条路的"阻力"降低了, 你自然就走那条。

  这就是运动势垫支:
  过去的经验预先塑形了未来的行为倾向。
```

```
当前代码的差距:
  ✅ Hebbian 学习存在 (STDP 修改权重)
  ✅ 环流检测存在 (P/R 路径)
  ❌ 没有构建 Φ_pre 预置势
  ❌ 新输入不落入势场——直接走前向传播
  ❌ 没有 argmin_q 的最小自由能搜索
```

---

## 5. Xin 账目守恒

```
Xin 不能凭空出现或消失!

  X(t₁) - X(t₀) = S_X + I_X - A_P - A_R - D_X - H_X

  S_X = 起始背景 Xin
  I_X = 新增的无法吸收输入
  A_P = 被 P 吸收的 Xin
  A_R = 被 R 消解的 Xin
  D_X = 衰减耗散
  H_X = heat bath 去向

  积分形式:
  X₀ + ∫J_X^in dt = X₁ + ∫(J_X^P + J_X^R + J_X^D + J_X^H) dt
```

```
当前代码:
  xin_tension 存在 → 但没有守恒检查
  fruit dissolution 存在 → 但消亡的 Xin 去了哪里没有记账
  sediment 吸收果实 → 但没有记录"从 Xin 账目中扣除了多少"

  = Xin 在系统中是"漏的": 可以出现也可以消失, 没有守恒
```

---

## 6. 四源耦合评分

```
一个信息块的运动分类不是由单一来源决定:

  Score_z(W_k) = λ_L × Score_RLIS
               + λ_C × Score_CounterMask
               + λ_H × Score_FHPMS
               + λ_B × Score_BottomMotion

  z ∈ {P_c, P_b, R_c, R_b, M_b, X, U}

  归一化: ρ_z = softmax(Score_z)

  四个评分来源:
    RLIS: 总览自由能变分与 Xin 账目
    Counter-Masking: 内部反压、屏蔽、R-band 成核
    HG-FHPMS: 内部记忆势、历史模式
    BottomMotion: 底层真实物理运动
```

```
当前代码:
  ❌ 没有四源评分
  ❌ 运动分类靠单一的环流检测
  ❌ 没有 softmax 归一化
  ❌ 没有 Counter-Masking 独立评分
```

---

## 7. 降级边界 — 你自己明确的

蓝图中有一张降级表, 承认这些都是"代理", 不是真实物理:

| 理念 | 当前降级 |
|------|---------|
| 真实物理势场 | distance-spacetime potential proxy |
| 真实 Hebbian 电路 | HG-FHPMS internal Hebbian guidance gate |
| 真实 Minkowski 时空 | RLIS Minkowski-like interval proxy |
| 真实路径积分 | path-weight proxy |
| Ricci flow | metric-smoothing analysis proxy |
| 辛几何 | information phase-space proxy |
| 超图物理动力学 | hypergraph potential trend proxy |
| 庞加莱 / 拓扑证明 | topology-inspired consistency audit |
| 真实底层连续流 | bounded bottom-motion window proxy |
| 完整四维回投 | coarse reprojection trace |

**这意味着系统不需要实现"真实的"物理——只需要做好降级代理。**

---

## 8. 综合差距 (两份文档 + 代码)

```
材料层 (已实现):
  ✅ MetaNeuron = 元单元 (电容+MOSFET+PowerRail)
  ✅ MetaSynapticBundle = 超边 (权重+延迟+衰减+STDP)
  ✅ SubstrateNetwork = 能量网络
  ✅ 环流检测 (P/R 路径)
  ✅ Xin 张力 (xin_tension)
  ✅ 果实/结晶 (标记-确认-固化)
  ✅ 管道延迟 (cable → 时空结构)

架构层 (缺失):
  ❌ 距离测度坐标 → 只有笛卡尔
  ❌ 7 分量纤维测度 ρ → 只有二元 P/R + 标量 Xin
  ❌ 复合运动势 Φ_pre → 没有
  ❌ 运动势垫支 → 没有
  ❌ Xin 账目守恒 → 没有
  ❌ 四源耦合评分 → 没有
  ❌ 审计光锥 s²_L → 没有
  ❌ 拉格朗日代理 → 没有
  ❌ 多轮收敛分析 → 没有
  ❌ 回投链 → 没有
  ❌ 1:1 规模对应 → 断裂

组织层 (命名混乱):
  HebbianCircuit ≠ HG-FHPMS (应该是后者的子组件)
  entropy_ledger_proxy ≠ RLIS (应该升级)
```

> [!IMPORTANT]
> **总结: 代码有了优秀的物理零件, 但缺少你设计的组织框架。**
> 
> 零件 = MetaNeuron, Bundle, STDP, homeostasis, cable delay
> 框架 = HG-FHPMS, RLIS, 7分量纤维测度, 运动势垫支, Xin守恒, 四源评分
> 
> 零件是对的。框架需要补上。
> 而且这个框架有明确的降级边界——不需要实现真实物理,
> 只需要做好降级代理。
