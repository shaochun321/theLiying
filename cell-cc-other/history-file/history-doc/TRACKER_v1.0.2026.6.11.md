# 项目主追踪表 v1.1

> 编号规则: `领域.序号` | 状态: ✅完成 ⚠️部分 ❌未做 🔬需建模 ❓待确定

---

## S. 结构/组件层

- [x] **S.01** Capacitor KCL 追踪 (`_q_in/_q_out/_q_initial`)
- [x] **S.02** Memristor 分项审计 (`apply_dw` + `_cum_ltp/_cum_ltd`)
- [x] **S.03** MOSFET 亚阈值修复 (`conduct()` 返回 0)
- [x] **S.04** NDR 元件 (Afferent 特有)
- [x] **S.05** PowerRail (Motor 特有)
- [x] **S.06** D2R 自受体 (DA 特有)
- [x] **S.07** Temporal Coupler C-layer + B-layer — **EXP-013 验证 5/6 pass**: C-layer 正常 (τ_eff/τ_base=0.4), B-layer 调制弱 (6-8%)
- [x] **S.08** CirculationProportionCircuit (环流比例结构载体)
- [x] **S.09** EnergyStore (外部能量储库)
- [x] **S.10** LiquidMetalRouter (Enc→Col 结构可塑性)
- [ ] **S.11** Encoding 层特有元组件 — 当前只有通用 VR+bias，缺少分化组件
- [ ] **S.12** Column 层特有元组件 — lateral inhibition 是外部注入，非内置
- [/] **S.13** 热源动态 — regenerate 已有，但位置静态，缺多源消耗
- [ ] **S.14** 世界介质参数 — Z=1.0 默认值，未定义深海/硅基属性
- [x] **S.15** DA 乘法调制 — `_propagate_bundles()` 钩子 + gain_factor 缩放

---

## B. 体表/感受层 — 第二主体：热 ❓待确定

> 第一主体（运动）通过前庭链获得完整转导：MET→HC→Aff→Enc→Col→Mot。
> 第二主体（热）目前只有标量 therm→Encoding 旁路，缺空间感受和因果学习。
> 项目前身从细胞球体→分化前庭系统的路径：先链路对应验证，再架构可行性，最后涌现。
> 以下为 2026-06-10/11 讨论产出，需用户确认架构方向后再排入执行。

- [ ] **B.00** 刚体壳定义 — 几何/质量/惯量，外皮体积可调
- [ ] **B.01** 外皮 patch 拓扑 — 最小 4 patch（前后左右），感受带宽 = patch 数 × 模态数
- [ ] **B.02** 皮肤感受神经元 (Thermoreceptor + Nociceptor) — 压电式热-电转换器，类 MET 但 τ 更长
- [ ] **B.02b** SomatoRelay 体感中继层 — 脊髓背角类比，空间滤波 + lateral inhibition，**连接拓扑隐式编码体表 2D 流形**
- [ ] **B.03** 自身原点模块 (小脑类比) — **三层交汇结构，非单一层级附属**:
  - 交感层输入: skin afferent（我感受到了什么）
  - Motor 输入: efference copy（我做了什么）
  - Shadow 输入: prediction error（我预期感受什么）
  - 比较结果: 匹配=自我运动, 不匹配=外部刺激
- [ ] **B.04** 感受→DA 闭环 — 热接触→能量变化→shadow→DA→STDP 方向学习
- [ ] **B.05** 感受带宽扩展 — patch 数按需增加，皮层体积可调
- [ ] **B.06** 热势 ν_th = dE_thermal/dt — 类比运动势 ν，ν×ΔT 相关性是 STDP 方向信号

> **架构约束**:
> - 感受转导在交感层（传入链），不在影子层。影子层是对外层表征的抽象预测。
> - 自身原点是三层间的**第四种结构**（小脑类比），同时读取交感层/Motor/Shadow。
> - SomatoRelay 的连接拓扑 + 时间编码 → 隐式 3D/4D 流形（体表×时间×模态）。
> - 时间耦合器需要热专用参数: τ_couple ≈ 100ms（vs 运动链 2ms），因温度变化远慢于机械振动。
>
> **依赖**: B.00 → B.01 → B.02 → B.02b → B.03 → B.04。
> B.03 依赖 A7 运动势 + Motor→Col 反馈(已有) + Shadow(已有)。
> **环流记忆(N.13)不阻塞**: 感受→DA 闭环只需当前步 deviation，不需进化级记忆。
> **验证方法**: 同前身——先链路对应（信号能流通），再架构可行性（层间阻抗匹配），最后行为涌现。

---

## N. 神经/信号链

- [x] **N.01** 前庭链 Met→HC→Aff(reg/irr)→Enc→Col→Mot
- [x] **N.02** 热感链 therm→Enc→Col→Mot
- [x] **N.03** Encoding bias 修复 (0.05→0.02)
- [x] **N.04** Col→Mot 轴特异拓扑 (3×1×1 + 1×7×3)
- [x] **N.05** DA 神经元池 (3 个 VTA DA)
- [x] **N.06** Shadow→DA + Xin→DA bundles
- [x] **N.07** Motor→Column 反馈 (efference copy)
- [x] **N.08** Lateral inhibition (Column 间)
- [x] **N.09** Binding layer (跨模态)
- [x] **N.10** Spike-before-leak 顺序确认
- [x] **N.11** DA→Motor 乘法调制 — `_propagate_bundles()` 覆写，gain = 1+α·DA
- [ ] **N.12** 环流→进食激活路径 — 偏激反向传播未实现
- [ ] **N.13** 环流记忆 / 长期 EMA 落地 — 进化尺度存储无结构
- [ ] ❓**N.14** 外皮感受→Encoding 传入链 — 依赖 B.02

---

## P. 可塑性/学习

- [x] **P.01** STDP 软边界 (乘法)
- [x] **P.02** BCM 滑动阈值
- [x] **P.03** Hebbian decay
- [x] **P.04** Fruit 成熟/修剪/萌芽
- [x] **P.05** ZCR 驻波引导修剪 (#5)
- [x] **P.06** PNN gate 传递到 learn()
- [x] **P.07** 三因子学习 (DA × pre × post)
- [x] **P.08** 突触维持税结构化 — P2.1: 常数基底漏电从 EnergyStore 扣除
- [x] **P.09** 先天通路冻结 — shadow→DA + xin→DA 设为 `learning_rule="frozen"`

---

## E. 能量/守恒

- [x] **E.01** Noether energy conservation
- [x] **E.02** Xin conservation (baselined)
- [x] **E.03** Landauer Shannon entropy
- [x] **E.04** Weight stability check
- [x] **E.05** 熵账本 pre-step guard → `_ledger_pre_step` (v1.7.2 重命名)
- [x] **E.06** ECM 负温度修复
- [ ] **E.07** 能量来源标签 — 追踪 E_in 来自哪个 source
- [x] **E.08** P2.1: 废除 MAX_BUNDLES=80 硬上限 — 热力学能量墙替代
- [x] **E.09** EnergyStore P_inflow 恒定上限 (max_deposit_per_step=0.05)
- [x] **E.10** 系统级 E1 评估 (mean_xi per growth interval)
- [x] **E.11** `nexus_v1/ledger/` 子包重构 — 统一 6 个观测模块
- [x] **E.12** EntropyLedger 安装 — 首次接入 step loop (每 1000 步)
- [x] **E.13** EntropyLedger 层覆盖扩展 — Shadow + DA 层
- [x] **E.14** PowerRail R_internal 2.0→0.3 — 修复 Motor 层褒电崩溃
- [x] **E.15** 绝对能量锁 (SPIKE_ENERGY_COST=0.005) — 消灭热力学丧尸

---

## C. 环流/耦合

- [x] **C.01** CirculationMeter (rho 测量)
- [x] **C.02** CirculationProportionCircuit (rho→deviation→DA)
- [x] **C.03** 进食-运动-体征三路耦合概念
- [ ] **C.04** 环流偏激反向传播 — deviation→DA 有，但无直接 motor/feed 激活
- [ ] **C.05** 环流与震荡同构关系 — 概念讨论过，未建模
- [ ] **C.06** 等势环流巩固 — fruit 间耦合协同成熟未实现

---

## M. 数理/理论

- [x] **M.01** B1+B5 耦合定理 (能量钳制振荡)
- [x] **M.02** 时间窗验证 (1-6s 不对称)
- [x] **M.03** TSI 参数方程 (候选)
- [x] **M.04** TSI metric unification (候选)
- [x] **M.05** Adaptive coupler 数学分析
- [ ] **M.06** 参数→T/O/P/R/Xin 关系方程 — 系统化工具未实现
- [ ] **M.07** 元件参数→震荡频率/幅度映射 — 未建模
- [ ] **M.08** 收缩映射证明 (STDP Jacobian 谱半径) — 数学难题

---

## D. 文档/工具

- [x] **D.01** G-001 全局数学公式
- [x] **D.02** G-002 全局架构图
- [x] **D.03** 版本号迭代记录系统 → [VERSION_LOG.md](history/VERSION_LOG.md)
- [x] **D.04** 参数变更日志 → [PARAM_CHANGELOG.md](history/PARAM_CHANGELOG.md)
- [x] **D.05** 本追踪表
- [x] **D.06** 回归测试 pytest 化 — 12 个 pytest 函数 + 直接运行 21 项
- [x] **D.07** ledger/ re-export shims — 旧路径向后兼容

---

## 优先执行分类

### 🔧 可直接完成 (代码修改)

| 编号 | 项目 | 预估 |
|---|---|---|
| C.04 | 环流 deviation→motor 直接激活 | 15min |
| S.13 | 热源位置漂移 + 多源 | 10min |
| P.08 | 突触维持税用能量-电导耦合替代 magic 0.999 | 10min |
| N.11 | 环流→Motor 直接路径 | 同 C.04 |
| E.07 | 能量来源标签 | 15min |
| D.03 | 版本号 + 变更日志框架 | 5min |

### 🔬 需建模/数理候选 (延后)

| 编号 | 项目 | 原因 |
|---|---|---|
| S.11 | Encoding 特有组件 | 需确定生物对应 |
| S.12 | Column 特有组件 | 需确定功能需求 |
| C.05 | 环流-震荡同构 | 需数学框架 |
| C.06 | 等势环流巩固 | 需跨 bundle 耦合理论 |
| M.06 | 参数关系方程 | 需系统实验 |
| M.07 | 元件→震荡映射 | 需频响分析 |
| M.08 | 收缩映射证明 | 纯数学 |
| N.13 | 环流记忆落地 | 需进化论框架 |

### ❓ 待确定 (需架构决策)

| 编号 | 项目 | 前置依赖 |
|---|---|---|
| B.00 | 刚体壳定义 | S.14 世界介质 |
| B.01 | 外皮 patch 拓扑 | B.00 |
| B.02 | 皮肤感受→Encoding | B.01, N.02 |
| B.03 | 自身原点坐标 | B.01, A7 |
| B.04 | 感受→DA 闭环 | B.02, N.06 |
| B.05 | 感受带宽扩展 | B.02 验证后 |
