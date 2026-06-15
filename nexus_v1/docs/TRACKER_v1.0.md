# 项目主追踪表 v1.0

> 编号规则: `领域.序号` | 状态: ✅完成 ⚠️部分 ❌未做 🔬需建模

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
- [ ] **N.11** 环流→Motor 直接激活路径 — deviation 只驱动 DA，未直接激活运动
- [ ] **N.12** 环流→进食激活路径 — 偏激反向传播未实现
- [ ] **N.13** 环流记忆 / 长期 EMA 落地 — 进化尺度存储无结构

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
