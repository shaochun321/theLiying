---
tags: [MOC, 导航, 工程流程, 映射]
concepts: [implementation_plan, walkthrough, analysis, 三角映射, Plan-Build-Reflect, 时序]
type: MOC
date: 2026-06-14
aliases: [三角映射, 工程流程, Plan-Walkthrough-Analysis, plan-walkthrough-analysis]
---
# 🔀 Plan → Walkthrough → Analysis 三角映射

> **顺序**: 本页按时间线排列，展示 implementation_plan（该做什么）、walkthrough（实际做了什么）、analysis（为什么这么做/做得对吗）之间的对应关系。
> **最后更新**: 2026-06-14

---

## 📋 时序规律

```
标准流程（约 70%）:
  implementation_plan ──→ walkthrough ──→ analysis
  (设计规范)              (代码变更记录)    (反思/诊断/批判)

变异流程:
  modeling_*.md ──→ walkthrough ──→ analysis    (建模替代 Plan)
  implementation_plan ──→ (对话日志) ──→ analysis  (6月9日后无独立Walkthrough)

analysis 双份模式:
  第一份: 提案评判 (pre-build, 如 Doc9.6 vs Doc9.7)
  第二份: 结果反思 (post-build, 如 L2.08 → L2.09 推翻)
```

---

## 一、日期对齐（五月 / 六月）

### 2026.5.16 — 结构性分化

| 类型 | 文件 | 主题 |
|------|------|------|
| **Plan** | [[01_工程执行/implementation_plan.2026.5.16]] (+ .1~.8) | v40.6: 结构分化、阈值多样性、时空窗口获取 |
| **Walkthrough** | [[01_工程执行/walkthrough.2026.5.16]] (+ .1~.6) | v40.6 HebbianCircuit 实现 |
| **Analysis** | [[2026-05/analysis_structural_critique.2026.5.16]] · [[2026-05/analysis_physics_audit.2026.5.16]] | 结构批判、物理审计 |
| **时序** | Plan → Walkthrough → Analysis | ✅ |

---

### 2026.5.17 — 公式批判与偏好涌现

| 类型 | 文件 | 主题 |
|------|------|------|
| **Plan** | [[01_工程执行/implementation_plan.2026.5.17]] (+ .1~.5) | 衰减恢复路线图 (Phase 0-5)、IntegratorColumn |
| **Walkthrough** | [[01_工程执行/walkthrough.2026.5.17]] (+ .1~.6) | v40.10b IntegratorColumn + 闭环实现 |
| **Analysis** | [[2026-05/analysis_formula_critique.2026.5.17]] · [[2026-05/analysis_verified_formulas.2026.5.17.公式]] · [[2026-05/analysis_preference_emergence.2026.5.17]] | **Xin≠梯度下降** 关键修正、公式验证、偏好涌现 |
| **时序** | Plan → Walkthrough → Analysis | ✅ |

---

### 2026.5.18 — 影子层发现

| 类型 | 文件 | 主题 |
|------|------|------|
| **Plan** | ❌ 缺 | 无 5.18 日期 Plan |
| **Walkthrough** | [[01_工程执行/walkthrough.2026.5.18]] (+ .1~.8) | v40.x 列对齐、电路修复 |
| **Analysis** | [[2026-05/analysis_shadow_layer.2026.5.18]] · [[2026-05/analysis_spacetime_circulation.2026.5.18]] | **影子层首次观察**（休眠果实 10× 增长）、时空环流 |
| **时序** | (5.17 Plan) → Walkthrough → Analysis | ⚠️ 缺当日 Plan |

---

### 2026.5.19 — 最终裁决

| 类型 | 文件 | 主题 |
|------|------|------|
| **Plan** | [[01_工程执行/implementation_plan.2026.5.19]] (+ .1) | 消融修正 (Path A/B/C) |
| **Walkthrough** | ❌ 缺 | 无 5.19 日期 Walkthrough |
| **Analysis** | [[2026-05/analysis_final_verdict.2026.5.19]] | 最终裁决 |
| **时序** | Plan → (缺Walkthrough) → Analysis | ⚠️ 缺 Walkthrough |

---

### 2026.5.20 — 元结构体系

| 类型 | 文件 | 主题 |
|------|------|------|
| **Plan** | [[01_工程执行/implementation_plan.2026.5.20]] (+ .1) | 神经链接集成、gap audit |
| **Walkthrough** | [[01_工程执行/walkthrough.2026.5.20]] (+ .1) | 后置调制工作 |
| **Analysis** | [[2026-05/analysis_meta_guide.2026.5.20]] · [[2026-05/analysis_circuit_audit.2026.5.20]] | **元结构体系**（5 大 Meta 结构）、电路审计（Xin 首次理论定义） |
| **时序** | Plan → Walkthrough → Analysis | ✅ |

---

### 2026.5.21 — ⚡ 修正密集日

| 类型 | 文件 | 主题 |
|------|------|------|
| **Plan** | [[01_工程执行/implementation_plan.2026.5.21]] | Phase 0+2a: CircuitObserver (RLIS)、VestibularStore |
| **Walkthrough** | [[01_工程执行/walkthrough.2026.5.21]] | Phase 0+2a 完成: rlis_observer.py、vestibular_store.py |
| **Analysis** | [[2026-05/analysis_concept_evolution.2026.5.21]] · [[2026-05/analysis_correction_toprxin.2026.5.21]] · [[2026-05/analysis_corrected_understanding.2026.5.21]] | **T/O/P/R/Xin: 管道→递归**关键修正、概念变迁总册 |
| **时序** | Plan → Walkthrough → Analysis | 🔥 **最强对齐** |

---

### 2026.5.22 — 超图数学日

| 类型 | 文件 | 主题 |
|------|------|------|
| **Plan** | [[01_工程执行/implementation_plan.2026.5.22]] | nexus_v1 安全策略、零损伤回滚 |
| **Walkthrough** | [[01_工程执行/walkthrough.2026.5.22]] | nexus_v1 信号链全通 (6/6 at t=2000) |
| **Analysis** | [[2026-05/modeling_hypergraph_math.2026.5.22]] · [[2026-05/modeling_coupling_recursion_vfe.2026.5.22]] | 超图数学（10维状态空间）、耦合递归 VFE |
| **时序** | Plan → Walkthrough → Analysis | ✅ |

---

### 2026.5.23 — 💎 结晶日

| 类型 | 文件 | 主题 |
|------|------|------|
| **Plan** | [[01_工程执行/implementation_plan.2026.5.23]] | L6 Motor 分化（母本分化） |
| **Walkthrough** | [[01_工程执行/walkthrough.2026.5.23]] | 环流架构 + 影子层激活 + 参数演化 |
| **Analysis** | [[2026-05/analysis_shadow_structural_grounding.2026.5.23]] · [[2026-05/analysis_hypergraph_circulation_foundation.2026.5.23]] · [[2026-05/analysis_circulation_zero_diagnosis.2026.5.23]] | **影子: 矩阵→物理副本**；环流: "没有环流系统——环流是结构做的事"；μ=0 诊断 |
| **时序** | Plan → Walkthrough → Analysis | ✅ |

---

### 2026.5.24 — ds²/ν 框架

| 类型 | 文件 | 主题 |
|------|------|------|
| **Plan** | [[01_工程执行/implementation_plan.2026.5.24]] (+ 双系统) | 最小实验: 热感+运动耦合 |
| **Walkthrough** | [[01_工程执行/walkthrough.2026.5.24]] (+ 里程碑) | 前庭超图 (Phase 1-4) |
| **Analysis** | [[2026-05/analysis_unified_master_method.2026.5.24]] · [[2026-05/analysis_gain_chain.2026.5.24]] | **ds²/ν 统一框架首次出现**、增益链分析 |
| **时序** | Plan → Walkthrough → Analysis | ✅ |

---

### 2026.5.25 — 递归分化

| 类型 | 文件 | 主题 |
|------|------|------|
| **Plan** | [[01_工程执行/implementation_plan.2026.5.25]] | 递归分化沉积: sprout (ξ,κ) / prune (w→0) |
| **Walkthrough** | [[01_工程执行/walkthrough.2026.5.25]] (+ .2, .3) | RULE S2 递归分化沉积实现 |
| **Analysis** | [[2026-05/analysis_toprxin_topology_critique.2026.5.25]] · [[2026-05/analysis_longrun_diagnosis.2026.5.25]] | TOPRXin 拓扑批判、50k 长期诊断 |
| **时序** | Plan = Walkthrough → Analysis | 🔥 **最强对齐** |

---

### 2026.5.26 — 有丝分裂

| 类型 | 文件 | 主题 |
|------|------|------|
| **Plan** | [[01_工程执行/implementation_plan.2026.5.26]] (+ .1) | Phase 3: 神经元分裂 (mitosis) |
| **Walkthrough** | [[01_工程执行/walkthrough.2026.5.26]] (+ .1) | Phase 3 实现: 6 迭代 (机械→基底约束) |
| **Analysis** | [[2026-05/analysis_substrate_secondary_networks.2026.5.26]] | 基底二次网络 |
| **时序** | Plan → Walkthrough → Analysis | 🔥 **最强对齐** |

---

### 2026.5.27 → 5.31 — 收尾

| 日期 | Plan | Walkthrough | Analysis | 结论 |
|------|------|-------------|----------|------|
| **5.27** | [[01_工程执行/implementation_plan.2026.5.27]] | walkthrough.5.27 (+.1~.5) | [[2026-05/analysis_followup_diagnosis.2026.5.27]] | ✅ |
| **5.28** | [[01_工程执行/implementation_plan.2026.5.28]] (增益链诊断) | walkthrough.5.28 (14修复完成) | ❌ 无 | ✅ |
| **5.29** | ❌ 无 | ❌ 无 | [[2026-05/analysis_2M_growth.2026.5.29]] · [[2026-05/analysis_timespace_circulation.2026.5.29]] | 📊 纯分析日 |
| **5.30** | [[01_工程执行/implementation_plan.2026.5.30]] (2M四优先) | ❌ 无 | [[2026-05/analysis_2M_postfix.2026.5.30]] | ✅ |
| **5.31** | ❌ 无 | [[01_工程执行/walkthrough.2026.5.31]] (系统全景图) | [[2026-05/glossary.2026.5.31]] · [[2026-05/system_narrative.2026.5.31]] | ✅ |

---

### 2026.6.4-6.5 — 决策框架 & 统一日

| 日期 | Plan | Walkthrough | Analysis | 结论 |
|------|------|-------------|----------|------|
| **6.4** | ❌ 无 | ❌ 无 | [[2026-06/decisions_and_framework.2026.6.4]] · [[2026-06/decisions_and_framework_cont.2026.6.4]] | 📊 纯分析: 9项决策 |
| **6.5** | [[01_工程执行/implementation_plan.2026.6.5]] (+.1, .2) (并行任务 D1/C1/C2/C4) | ❌ 无 | [[2026-06/analysis_TSI_metric_unification.2026.6.5]] · [[2026-06/analysis_shadow_architecture.2026.6.5]] · [[2026-06/critique_evaluation.2026.6.5]] | 🔥 **强对齐**: T·S·I统一 + 影子根因 + 自我批判 |

---

### 2026.6.6 — v0.9.0

| 类型 | 文件 | 主题 |
|------|------|------|
| **Plan** | [[01_工程执行/implementation_plan.2026.6.6]] (+.1~.3) | 熵账本前置化 (Phase 0 guard)、C3' 环流耦合 |
| **Walkthrough** | [[01_工程执行/walkthrough.2026.6.6]] (+.3) | 母本分化 (3 新补偿组件)、DA 电路变更 |
| **Analysis** | [[2026-06/system_state_v0.9.0.2026.6.6]] · [[2026-06/CHANGELOG.2026.6.6]] | v0.9.0 系统状态 + 变更日志 |
| **时序** | Plan = Walkthrough → Analysis | ✅ |

---

### 2026.6.7 — 审计+回归

| 类型 | 文件 | 主题 |
|------|------|------|
| **Plan** | ❌ 无 | — |
| **Walkthrough** | ❌ 无 | — |
| **Analysis** | [[2026-06/analysis_500k_regression_v1.6.2026.6.7]] · [[2026-06/audit_implementation_v1.项目实现审计-v1.0-2026-06-07]] | 500k 回归 v1.6、实现审计 |
| **时序** | (前期Plan驱动) → (缺Walkthrough) → Analysis | 📊 纯分析日 |

---

### 2026.6.8 — Epoch 1 验证

| 类型 | 文件 | 主题 |
|------|------|------|
| **Walkthrough** | [[01_工程执行/walkthrough.Epoch-1-验证报告]] | 5 突变: 全波整流/BCM钙修复/偏差0.05→0.01/增益0.3→1.0/θ_m τ 100→10000。影子层控制阀觉醒: DA 0→0.6536 |
| **Analysis** | [[2026-06/analysis_loop_design_blockers.环路设计阻断分析-影子层本体-时间耦合器-生命编码]] | 阻断诊断: 环路设计阻断分析 |
| **时序** | Walkthrough → Analysis | ✅ |

---

## 二、6月9日—13日：热感知构建 + L2 筛选

> ⚠️ **6月9日后无独立的 dated implementation_plan 或 walkthrough 文件**。
> 实现过程记录在 `02_AI对话日志/` 中，Plan 来自较早的主题文件，Walkthrough 嵌入在对话中。

### 6.9 — 代码迁移 + 回归

| 类型 | 文件 | 主题 |
|------|------|------|
| **对话** | [[02_AI对话日志/Refactoring Neural Hypergraph Physics.2026.6.9]] (+.1~.4) | 代码库迁移、21/21 回归通过、DA→Motor 链冻结 |
| **Analysis** | [[2026-06/analysis_da_calibration_v2.2026.6.9]] | DA 校准 V2: 三刀修复 |

---

### 6.10 — 热感知架构设计

| 类型 | 文件 | 主题 |
|------|------|------|
| **Plan** | [[01_工程执行/implementation_plan.实施计划-第二主体（热）构建]] (无日期主题文件) | 第二主体(热)构建: Phase 0 影子动态生长 → Phase 1 物理外壳+皮肤补丁 |
| **Analysis** | [[2026-06-continued/analysis_body_sensing_architecture.方向性文档-外皮感受机制的架构设计]] | **Pre-build**: 体感架构方向设计。区分"感觉"与"运动判别"为不同输入模态 |
| **时序** | Plan → Analysis(设计) | 📋 设计日 |

---

### 6.11 — ⚡ 热感知实现 + EXP-014/015

| 类型 | 文件 | 主题 |
|------|------|------|
| **对话** | [[02_AI对话日志/Refactoring Neural Hypergraph Physics.2026.6.11]] (+.1~.4) | **实现会话**: 4热补丁轴、SomatosensoryChain集成、损伤积分修复、Phase 3调试 |
| **Analysis (pre)** | [[2026-06-continued/analysis_skin_neuron_modeling.分析-第二主体（热）的皮肤-神经元建模]] | 热→神经元信号链数学模型: P_th, nu_th = dE_thermal/dt |
| **Analysis (post)** | [[2026-06-continued/status_report_0611.项目状态报告-2026-06-11]] | **EXP-014**: 6/6 Gates PASS (全热链存活) · **EXP-015**: 信号正确，行为未涌现 (3瓶颈) |
| **Meta-review** | [[2026-06-continued/analysis_doc611_review_shadow_audit.客观评判-Doc 6.11.1-6.11.2-Shadow生长审计]] | 评判两份 AI 生成分析 + 影子结构塑性审计 (**sprout/prune/mitosis 均缺失**) |
| **时序** | Plan(主题) → 对话(实现) → Analysis(pre+post+meta) | 🔥 **三层覆盖** |

---

### 6.12 — L2 筛选: 假阳性发现

| 类型 | 文件 | 主题 |
|------|------|------|
| **分析(pre)** | [[2026-06-continued/analysis_L2_screening_results(L2_08-Biological_Screening_FULL_PASS-4_4)]] | **L2.08**: 4/4 FULL PASS — 100k步避害成功 |
| **分析(post)** | [[2026-06-continued/analysis_L2_09_systemic_diagnosis.L2.09 三重死亡拷问 — 系统性诊断]] | **L2.09**: 26参数组合 → **0死亡** → L2.08 的 FULL PASS 是**假阳性**。根因: 基线随机游走独立于 L2 反馈 |
| **参考** | [[2026-06-continued/mechanism_archive.nexus_v1 机制总档案]] | nexus_v1 40+ 机制总目录 (代码快照 6/12) |
| **时序** | 对话(6.11构建) → L2.08(FULL PASS) → L2.09(推翻) | 🔥 **双份 analysis 模式** |

---

### 6.13 — 根因诊断 + 摄食链

| 类型 | 文件 | 主题 |
|------|------|------|
| **对话** | [[02_AI对话日志/Refactoring Neural Hypergraph Physics.2026.6.13]] (+.1, .2, .4) | L2.09 死亡拷问扫参构建、摄食链集成、SpinalReflexArc |
| **Walkthrough** | [[01_工程执行/walkthrough.Feeding Chain Integration — Walkthrough]] | 摄食/能量链接线: fill_fraction, 饥饿趋近反射 (MOSFET门控), god-view移除 |
| **Analysis** | [[2026-06-continued/analysis_hypothesis_coordinate_reset(假设评判：自身坐标结构 × 虚位 × 复位耦合)]] | **转折点分析**: L2.09 失败的根因 = 机体是"无记忆布朗运动代理"。缺失: 自身坐标/路径积分/传出副本/复位脉冲/发散比较器。SpatialNavigator 是空壳(`pass`) |

---

## 三、主题对齐（无日期文件）

| 主题 | Plan | Walkthrough | Analysis |
|------|------|-------------|----------|
| **熵账本重构** | [[01_工程执行/implementation_plan.熵账本系统重构-方案B实施计划(修正版)]] | [[01_工程执行/walkthrough.熵账本重构-完成总结]] | [[archive/undated/analysis_A7_entropy_audit.A7实施方案审计-熵账本系统架构决策]] · [[archive/undated/analysis_exp016c_entropy_report.EXP-016c 熵账本诊断报告]] · [[archive/undated/analysis_differentiation_entropy_blindspot.母本分化-熵账本-盲区审计]] |
| **VitalOscillator** | [[01_工程执行/implementation_plan.VitalOscillator实现方案体征搏动器]] | [[01_工程执行/walkthrough.VitalOscillator Implementation Walkthrough]] | [[archive/undated/analysis_vital_oscillator两份分析评判-体征模块思考]] |
| **A7 运动势** | [[01_工程执行/implementation_plan.A7-运动势-熵账本结构追踪-实现方案]] | — | [[archive/undated/analysis_A7_entropy_audit.A7实施方案审计-熵账本系统架构决策]] · [[archive/undated/analysis_motor_energy_zero.L6_Mot_Energy=0诊断报告]] |
| **时间耦合器+Noether** | (含在日期 Plan 中) | [[01_工程执行/walkthrough.自适应时间耦合器 + Noether 严格化 — 完整 Walkthrough]] · [[01_工程执行/walkthrough.自适应时间耦合器 — 实现总结]] | [[archive/undated/analysis_noether_strictness.Noether 严格化分析 (B1)]] · [[archive/undated/analysis_B1_B5_coupling.C1-Noether-Polarization-能量预算钳制振荡幅度]] · [[2026-06/analysis_adaptive_coupler_math.2026.6.7]] |
| **B-tier Motor分化** | [[01_工程执行/implementation_plan.B-tier-运动分化 — 实施计划]] | [[01_工程执行/walkthrough.A-B-C全Tier-Walkthrough]] | [[archive/undated/analysis_B1_B5_coupling.C1-Noether-Polarization-能量预算钳制振荡幅度]] |
| **DA 系统稳定化** | [[01_工程执行/implementation_plan.Phase-P0-P2-DA系统稳定化-热趋性前置]] | [[01_工程执行/walkthrough.Walkthrough-DA-乘法调制-先天通路修复]] | [[2026-06/analysis_da_circuit_report.2026.6.5]] · [[2026-06/analysis_da_calibration_v2.2026.6.9]] · [[2026-06/analysis_doc96_vs_doc97.批判性分析-Doc 9.6vsDoc 9.7的工程分歧]] · [[2026-06/analysis_two_reviews_comparison.两份分析的客观评判]] |
| **P2.1 物理能量墙** | [[01_工程执行/implementation_plan.P2.1-废除 MAX_BUNDLES=80-纯物理能量墙]] | [[01_工程执行/walkthrough.v1.7.1Phase1完成报告-Phase2方案]] | — |
| **第二主体(热)构建** | [[01_工程执行/implementation_plan.实施计划-第二主体（热）构建]] | (嵌入 6.11 对话) | [[2026-06-continued/analysis_body_sensing_architecture.方向性文档-外皮感受机制的架构设计]] · [[2026-06-continued/analysis_skin_neuron_modeling.分析-第二主体（热）的皮肤-神经元建模]] |
| **工程档案系统** | [[01_工程执行/implementation_plan.工程化档案系统-设计方案]] | [[01_工程执行/walkthrough.项目全局态势与路线图-v1.7.1]] | — |
| **基因隔离手术** | — | [[01_工程执行/walkthrough.Walkthrough-基因隔离手术-F6信息热寂熔断]] | — |
| **摄食链集成** | (6.6 Plan中的 C3') | [[01_工程执行/walkthrough.Feeding Chain Integration — Walkthrough]] | — |

---

## 四、analysis 双份模式

| 模式 | 第一份 (pre) | 第二份 (post) | 关系 |
|------|-------------|--------------|------|
| **L2 筛选** | [[2026-06-continued/analysis_L2_screening_results(L2_08-Biological_Screening_FULL_PASS-4_4)\|L2.08: 4/4 FULL PASS]] | [[2026-06-continued/analysis_L2_09_systemic_diagnosis.L2.09 三重死亡拷问 — 系统性诊断\|L2.09: 0死亡 → FULL PASS是假阳性]] | ✅ 推翻 |
| **Doc 评审** | [[2026-06/analysis_two_reviews_comparison.两份分析的客观评判\|6.7: 两份分析评判]] | [[2026-06-continued/analysis_doc611_review_shadow_audit.客观评判-Doc 6.11.1-6.11.2-Shadow生长审计\|6.11: Doc 6.11评审+影子审计]] | 🔄 重复模式 |
| **DA 决策** | [[2026-06/analysis_doc96_vs_doc97.批判性分析-Doc 9.6vsDoc 9.7的工程分歧\|Doc 9.6 vs 9.7 方案评判]] | [[2026-06/analysis_da_calibration_v2.2026.6.9\|DA 校准 V2: 实现后调优]] | ✅ 决策→验证 |
| **公式批判** | [[2026-05/analysis_formula_critique.2026.5.17\|公式批判 (Xin≠梯度下降)]] | [[2026-05/analysis_verified_formulas.2026.5.17.公式\|验证公式]] | ✅ 修正→验证 |
| **概念演化** | [[2026-05/analysis_corrected_understanding.2026.5.21\|纠正理解]] | [[2026-05/analysis_concept_evolution.2026.5.21\|概念变迁总册]] | ✅ 纠正→总册 |

---

## 五、统计

| 维度 | 统计 |
|------|------|
| **总 Plan 文件** | 47 (日期 39 + 主题 8) |
| **总 Walkthrough 文件** | 54 (日期 43 + 主题 11) |
| **总 Analysis 文件** | 93 (2026-05: 73, 2026-06: 13, continued: 7) |
| **强对齐日期** | 5.16, 5.17, 5.20, **5.21**, 5.22, 5.23, 5.24, **5.25**, **5.26**, 5.28, 5.30, 5.31, **6.5**, 6.6 |
| **缺 Plan 日期** | 5.18, 5.29, 6.4 |
| **缺 Walkthrough 日期** | 5.19, 6.5, 6.7, 6.9 |
| **纯分析日** | 5.29, 6.7, 6.9, 6.10 |
| **6.9+ 特有** | Plan/Walkthrough 嵌入对话日志，无独立文件 |

---

## 📂 相关链接

- [[概念演化链]] — 概念时间线
- [[矛盾·遗留·生长点]] — 矛盾点/遗留点/生长点
- [[理念架构图]] — 概念层级关系
- [[架构演化树]] — 决策/降级/未完成 Canvas 视图

---

## 六、非 Plan/Walkthrough/Analysis 文档补充映射

> 以下文件不含 `analysis_` / `implementation_plan` / `walkthrough.` 前缀，但有关键内容。按日期并入。

### 🏛️ 正式文档（docs/ 工程文档系统）

| 日期 | 文件 | 类型 | 核心内容 |
|------|------|------|----------|
| 5.21→ | [[docs/degradation_registry]] | 退化注册表 | 14 项 DEG 从发现到修复的全生命周期 |
| 5.21→ | [[docs/fix_registry]] | 修复注册表 | 18+ 项 FIX 手术日志，含副作用 |
| 5.22 | [[docs/layer_contracts]] | 接口契约 | 6 层 (Met/HC/Aff/Enc/Col/Motor) 的 I/O 类型、能量、响应时间合约 |
| 5.22 | [[docs/modeling_003_compensation_fourier]] | 建模分析 | Col 激活的 Fourier 频谱: 0.29Hz 耗尽周期 + 11Hz 传入驱动 |
| 5.22 | [[docs/modeling_014_cv_rootcause]] | 建模分析 | CV=0.471 100%瞬态，稳态 CV<0.05；根因: Ca 延迟 |
| 5.22 | [[docs/modeling_016_shadow_layer]] | 架构规范 | 21 神经元影子层 (Enc→Col→Mot 副本)，C=3 慢速内省 |
| 5.22 | [[docs/modeling_017_circulation_architecture]] | 架构规范 | 影子层反馈设计，安全约束，仿真优先 |
| 5.23 | [[docs/concept_C001_circulation_architecture]] | 概念文档 | 环流不是独立系统——超图是基底，环流计是测量工具 |
| 5.23 | [[docs/concept_C002_learning_maturation]] | 概念文档 | 三方学习: 交界STDP / 影子收缩 / 结晶+成熟 (Spine→Column→Area) |
| 5.23 | [[docs/concept_C003_nature_coupling_third_factor]] | 概念文档 | Nature 2026 Park et al. climbing fiber → 项目映射: CF同步→绑定层共激活 |
| 5.24 | [[docs/global_G001_math_formulas]] | 数学参考 | RC-MOSFET 膜方程、STDP、束传播、ECM 热扩散、Hebbian 学习 |
| 5.24 | [[docs/global_G002_architecture]] | 架构参考 | 系统全景图、闭环 Motor→Muscle→Body→World→Thermal→Enc→Col→Motor |
| 5.24 | [[docs/concept_C004_autogenous_spacetime]] | 认识论文档 | 时空不由外部给定——代理从输入流相关性构建。距离=w_cross，方向=w_cross(yaw,therm) |
| 5.24 | [[docs/concept_C005_topr_meta_architecture]] | 元架构 | TOPR/Xin 是建造者组织框架，不是系统运行时特性（如同牛顿力学不被行星"知道"） |
| 5.24 | [[docs/next_phase_priorities]] | 优先级自评 | 诚实审计: 输入不对称影响涌现声明，Motor分化可能是噪声伪迹，影子需重新思考 |
| 5.24 | [[docs/discovery_log]] | 发现日志 | DIS-001~006: PowerRail行为塑形、BCM扼杀最强信号、方向来自标量感知… |
| 6.7 | [[docs/TRACKER_v1.0]] | 主追踪表 | 44 项 (S14/N6/E4/P9/C6/M5)，完成状态细分 |
| 6.7 | [[docs/AUDIT_v1.0]] | 实现审计 | 13 项验证通过，5 项标记，可靠度警告: Motor 分化可能为噪声伪迹 |
| 6.7 | [[docs/CROSSREF_master_task_v1.5]] | 交叉审计 | A-track 决策 vs 实际 v1.5 状态 对照 |
| 6.7 | [[docs/CHANGELOG]] | 变更日志 | nexus_v1 v1.4.0→v1.5.0: C.04 偏差→motor, S.13 热漂移, N.03 bias修复… |
| 6.8 | [[docs/ROADMAP_v1.7.2]] | 决策路线图 | 9 项 A-track + C-track 执行状态，含 v1.7.2 标注 |
| 6.8 | [[docs/REGISTRY]] | 文档注册表 | 工程文档主索引: 9 atlas 文件, 15 组件文件, theory/crossref/ledger |
| 6.9 | [[docs/SERIAL_DEPENDENCIES_v1.5]] | 依赖图 | 6 条不可跳过的串行链: 运动势/影子Scout/空间导航/数学严格化/数学基因/熵账本 |

### 📐 五月专用文档

| 日期 | 文件 | 类型 | 核心内容 |
|------|------|------|----------|
| 5.22 | [[2026-05/nexus_v1_chain_anatomy.2026.5.22]] | 架构参考 | 单前庭轴全信号路径 (float 0.8: Met→HC→Aff→Enc→Col→Motor, 6轴) |
| 5.22 | [[2026-05/modeling_hypergraph_math.2026.5.22]] | 数学形式化 | 10 维状态向量 s_i(t) + 膜方程 + STDP + 超边耦合 |
| 5.22 | [[2026-05/modeling_coupling_recursion_vfe.2026.5.22]] | 理论基础 | 超边耦合曲面 + 影子递归 + 变分自由能核 |
| 5.22 | [[2026-05/modeling_hierarchical_prxin.2026.5.22]] | 理论基础 | 层级 P/R/Xin 递归 (标记 DEGRADED: 单层模型是实际目标) |
| 5.22 | [[2026-05/modeling_analysis.2026.5.22]] | 建模分析 | 前庭数据→半导体参数的量纲分析，归一化方案 |
| 5.22 | [[2026-05/modeling_parallel_conclusions.2026.5.22]] | 瓶颈诊断 | 两瓶颈: Release→Aff (MI=0.5%), Aff→Enc (MI=4.4%) |
| 5.24 | [[2026-05/revised_math_framework_v2.2026.5.24]] | 框架草案 | 双层架构 (客观 vs 主观层)，整合 C-001~C-005, G-001 |
| 5.31 | [[2026-05/glossary.2026.5.31]] | 术语表 | 完整词条索引 (组件/信号层/生长机制/信息量/物理系统/治理/元概念/常数) |
| 5.31 | [[2026-05/system_narrative.2026.5.31]] | 系统叙事 | 从物理到脉冲: 身体在 100³ 环面世界，3 肌肉，前庭+热量为唯一外部输入 |

### 🏗️ 六月专用文档

| 日期 | 文件 | 类型 | 核心内容 |
|------|------|------|----------|
| 6.4 | [[2026-06/theory_oscillation_manifold.2026.6.4]] | 理论讨论 | P 不是贝叶斯先验而是"过去 R 的压缩投影"；P(t) = STDP 卷积和 |
| 6.4 | [[2026-06/bio_correspondences.2026.6.4]] | 文献映射 | 项目→生物: provisioning→髓鞘化, 影子层→海马→皮层转移, BCM→关键期 |
| 6.4 | [[2026-06/decisions_and_framework.2026.6.4]] + cont | 决策记录 | 8 项待决: 影子角色/ Motor分化/ P精度/ 递归深度/ 运动势/ 影子本体/ 影子生长 |
| 6.5 | [[2026-06/critique_evaluation.2026.6.5]] | 自我批判 | 三层评价: 理论-工程鸿沟(对)/术语膨胀(部分正确)/参数振荡(正确但非 bug) |
| 6.5 | [[2026-06/review_circulation_memory.2026.6.5]] | 设计审查 | `float rho_normal_ema=0.7` 是作弊——真实记忆必须在结构中 |
| 6.4 | [[2026-06/summary_recent_ideas.2026.6.4]] | 想法总结 | 2M 后实验事实: Motor上限60有效, Oto Xin振荡 19-147, 权重熵=0, 超度量深度=5 |
| 6.5 | [[2026-06/master_task_list.2026.6.5]] | 主任务清单 | 4 轨 (A-架构9, B-数学4, C-执行9, D-实验4) 含状态与依赖 |
| 6.6 | [[2026-06/CHANGELOG.2026.6.6]] | 变更日志 | v0.9.0: 母本分化, 熵账本前置化, DA电路修复 |
| 6.6 | [[2026-06/system_state_v0.9.0.2026.6.6]] | 系统状态 | v0.9.0 全景: VariantCircuit 树, HebbianCircuit, 影子 Sandbox, Noether探针 |
| 6.7 | [[2026-06/audit_implementation_v1.项目实现审计-v1.0-2026-06-07]] | 实现审计 | 13项通过, 可靠度警告: Motor 分化可能是噪声伪迹 |
| 6.7 | [[2026-06/audit_master_task_crossref.2026.6.7]] | 交叉审计 | master_task_list vs 实际 v1.5: A1-DA部分, A2-不足, A7-未实现, A9-未完成 |
| 6.8 | [[2026-06/diagnosis_S07_A8_combined.S.07-A8综合诊断报告]] | 诊断报告 | B层37/40存活但弱(±1.5%); A8影子收敛失败(ratio=18.4) |
| 6.11 | [[2026-06-continued/status_report_0611.项目状态报告-2026-06-11]] | 状态报告 | EXP-014 6/6 PASS, EXP-015 行为未涌现, 3瓶颈: DA崩塌/无基线运动/缺dT/dt→DA |
| 6.12 | [[2026-06-continued/mechanism_archive.nexus_v1 机制总档案]] | 机制档案 | nexus_v1 40+ 机制总目录: P(4)+N(3)+S(3)+D(7)+R(8)+O(5)+M(5) |

### 📋 任务追踪 (01_工程执行)

| 日期 | 文件 | 跟踪内容 |
|------|------|----------|
| 5.16 | [[01_工程执行/task.2026.5.16]] (+.1~.3) | v40.6 对比增益 (Zone target_rate)、v40.8 结构完整性、v40.9 CPG 基底、v40.10 练习层 |
| 5.17 | [[01_工程执行/task.2026.5.17.1]] | 练习层 Hebbian 超图分化 |
| 5.18 | [[01_工程执行/task.2026.5.18.1]] | Phase 1 介质物理: MediumParticle, 波传播, DERC 扫描 |
| 5.21 | [[01_工程执行/task.2026.5.21]] | 半导体物理层重建: C/MOSFET/Memristor/PowerRail, 6/6 涌现测试 |
| ~6月 | [[01_工程执行/task.环流耦合实施任务]] | C3' 环流耦合: 多热源, DA释放, 果实成熟, 50k步 ALL PASSED |

### 💬 AI 对话日志摘要 (02_AI对话日志/)

| 日期范围 | 文件数 | 核心议题 |
|----------|--------|----------|
| 5.16-5.19 | ~15 | Morphosphere v40 实现、Hebbian 优化、介质物理、认知架构、代谢涌现 |
| 5.20-5.31 | ~7 | 补偿机制/Fourier、系统叙事构建、P0P1P2 后分析 |
| 6.4-6.8 | ~12 | 决策框架、v0.9.0 母本分化、实现审计、S.07+A8 诊断、路线图 v1.7.2 |
| 6.9-6.13 | ~16 | 档案系统、机制档案组装、EXP-014 闭环验证、状态报告、L2 筛选、摄食链集成 |

---

## 七、全量统计（含所有文档类型）

| 类型 | 文件数 | 日期范围 | 说明 |
|------|--------|----------|------|
| **implementation_plan** | 47 | 5.16-6.6 | 设计规范: 该做什么 |
| **walkthrough** | 54 | 5.16-6.13 | 代码变更记录: 实际做了什么 |
| **analysis** | 93 | 5.16-6.13 | 反思/诊断/批判: 为什么+做得对吗 |
| **modeling** | 15 | 5.22 | 数学建模与频谱分析 (2026-05 + docs/) |
| **task** | 8 | 5.16-6月 | 任务检查清单 |
| **system/glossary/narrative** | 3 | 5.31 | 系统全景+术语表+叙事 |
| **decisions/critique/review** | 5 | 6.4-6.5 | 决策记录+自我批判+设计审查 |
| **audit/diagnosis** | 4 | 6.7-6.8 | 实现审计+诊断报告 |
| **docs/ 工程文档** | 34 | 5.21-6.12 | atlas/components/theory/history/verification + 顶层追踪 |
| **AI 对话日志** | 49 | 5.16-6.13 | 原始实现过程记录 |
| **Dashboard** | 7 | — | 导航索引 |
| **合计** | **~319** | **5.16-6.13** | (不含 .obsidian/.claude/.claudian) |
