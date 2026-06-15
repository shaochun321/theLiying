# DEGRADED 标注审计：回升 / 保留 / 舍弃

> 全系统 8 个 engine 文件，共计 **~80 个** DEGRADED 标注
> 按三级裁定：**回升**（值得实现）/ **保留**（当前够用）/ **舍弃**（不需要）

---

## 裁定原则

你的原话：
> *不需要完全照搬生物学机制。消耗机制与生长机制非常有用。因果机制不能设置太复杂。*

据此，裁定标准是：
1. **对管道畅通和涌现有因果影响** → 回升
2. **已经是足够好的代理，回升不会改变系统行为** → 保留
3. **属于生物学细节，不影响物理/结构计算** → 舍弃

---

## 一、HebbianCircuit (38 个标注)

### 回升 (6 个) — 对涌现行为有直接因果影响

| # | 当前代理 | 真实机制 | 为什么需要 |
|---|---|---|---|
| 1 | 外部熵账本 | `local_substrate_thermodynamics` | **v41.0 已部分回升**（代谢环路）。但 energy 计量仍是全局 pool，应拆分为层级 energy budget |
| 2 | 深度限 DFS (depth≤4) | 完整同调环路检测 | P/R 环路检测只看 4 步以内，会漏掉长程环路。**但算力约束下可接受** — 标记为 **可选回升** |
| 3 | 均匀反馈权重 | `emergent_feedback_topology` | z_t → sig 的反馈全部均匀初始化。**STDP 正在逐步回升这个**——需要验证 500 tick 后权重是否分化 |
| 4 | EMA 学习 | `BCM_learning_rule` | Column 层目前用 EMA 巩固，BCM 的 sliding threshold 特性更适合选择性。**但 STDP+homeostasis 已部分替代** |
| 5 | 共激活矩阵 | `ACC_push_pull_conflict_monitoring` | 收敛检测用简单乘积，ACC 的 push-pull 能区分真收敛和噪声共变。**但当前阈值+年龄门控已经工作** |
| 6 | 单层 px_ | `hierarchical_motor_cortex_planning` | practice_cortex 是 flat 层，真实运动规划是 SMA→PMC→M1 三层。**对复杂运动序列有影响，但当前够用** |

### 保留 (21 个) — 代理已足够好

| # | 当前代理 | 真实机制 | 为什么保留 |
|---|---|---|---|
| 1 | 线性耗竭+指数恢复 | `mitochondrial_ATP_synthesis` | 代谢 v41.0 已接管全局能量。单神经元级 ATP 模拟无必要 |
| 2 | 慢 EMA | `voltage_gated_ion_channel_redistribution` | resting_potential 适应用 EMA 足够，离子通道动力学太细 |
| 3 | Ca²⁺比例恢复 | `mitochondrial_ATP_synthesis` | 与 #1 同理 |
| 4 | 激活方差 | `perineuronal_net_formation_and_degradation` | 惯性适应用方差代理合理，围神经网的蛋白酶动力学无必要 |
| 5 | 比例耗竭 | `synaptic_vesicle_pool_recycling` | 囊泡池回收的完整模型对当前系统无因果影响 |
| 6 | 慢 EMA | `transcription_factor_regulation` | 基因表达的时间尺度（小时）远超 tick 尺度（ms），保留 EMA |
| 7 | log2 标度 | `cortical_logarithmic_hierarchy_compression` | 成熟阈值用 log2 是合理近似 |
| 8 | Mg²⁺ sigmoid | `NMDA_receptor_Mg2_voltage_dependent_unblock` | 当前 sigmoid 已捕获电压依赖门控的本质 |
| 9 | 成熟标量 | `NMDA_receptor_density_regulation` | NMDA 密度用成熟阶段标量足够 |
| 10 | 线性耗竭 | `presynaptic_vesicle_release_probability` | 突触前释放概率的完整模型不影响系统级行为 |
| 11 | float 字段 | `cortical_laminar_identity_dynamics` | 层内 occupancy/temperature 用 float 足够 |
| 12 | 比例耗竭 | `dendritic_transport_ATP_consumption` | 树突 ATP → 已被 v41.0 全局 pool 替代 |
| 13 | 比例耗竭 | `axonal_transport_ATP_consumption` | 同上 |
| 14 | F 标度 σ | `GABAergic_interneuron_metabolic_sensitivity` | GABA 代谢敏感性已通过除法归一化间接实现 |
| 15 | Ca²⁺标度 | `basket_cell_interneuron_dynamics` | 篮状细胞动力学已通过侧抑制代理 |
| 16 | 直接发射/捕获 | `protein_synthesis_and_diffusion_dynamics` | PRP 发射/捕获的扩散模型不影响学习结果 |
| 17 | Xin 张力 | `dopaminergic_modulation_of_eligibility_traces` | 三因子学习用 Xin 张力替代多巴胺合理 |
| 18 | delta 门控恢复 | `oligodendrocyte_myelination_dynamics` | 髓鞘化的时间尺度太长 |
| 19 | 衰减率门控 | `ion_channel_desensitization_recovery` | 去敏感化动力学太细 |
| 20 | 强度门控衰减 | `synaptic_elimination_complement_tagging` | 补体标记系统是免疫学细节 |
| 21 | 代谢退出 | `metabolic_withdrawal_quiescence` | 已通过 energy→0 实现 |

### 舍弃 (11 个) — 生物学细节，对系统无因果影响

| # | 真实机制 | 为什么舍弃 |
|---|---|---|
| 1 | `local_metabolic_heat_dissipation` | 热耗散已通过 temperature 全局追踪，局部热方程无必要 |
| 2 | `persistent_sodium_current_I_NaP` | CPG 用半中心振荡已工作，I_NaP 是离子通道级细节 |
| 3 | `sleep_dependent_memory_trace_maintenance` | 睡眠/觉醒周期在当前系统中无意义 |
| 4 | `spontaneous_reactivation_during_rest` | 同上——没有"休息"状态 |
| 5 | `association_cortex_engram_crystallization` | 已有 cx_ 晶化机制，真实 ACC 的完整模型无必要 |
| 6 | `predictive_coding_top_down_generation` | Xin 已实现预测残差，完整预测编码太复杂 |
| 7 | `glucose_dependent_synaptic_plasticity` | 葡萄糖代谢 → 已被 v41.0 energy pool 替代 |
| 8 | `gibbs_free_energy_thermodynamic_potential` | 自由能的热力学严格计算不影响行为 |
| 9 | `CPG_half_center_reciprocal_inhibition` | **注意：这个不是真的降级**——CPG 已经实现了半中心！标注本身有误 |
| 10 | `laminar_cortical_column_microcircuit` | 皮层柱的 6 层微回路在当前系统中无意义 |
| 11 | `basal_ganglia_selection_gating` | 基底节选择门控需要完整 striatum 模型 |

---

## 二、PracticeEngine (12 个标注)

### 回升 (2 个)

| # | 当前代理 | 真实机制 | 为什么需要 |
|---|---|---|---|
| 1 | 标量梯度响应 | `brainstem_taxis_reflex_arc` | **最关键！** 这是硬编码反射→学习型导航的瓶颈。v41.0 的代谢环路已开始替代它 |
| 2 | 阈值检测 | `continuous_attractor_dynamics` | 连续吸引子能让 origin 估计更平滑，但当前阈值检测+origin_tracker 已工作 |

### 保留 (7 个)

| # | 当前代理 | 真实机制 | 为什么保留 |
|---|---|---|---|
| 1 | 粒子力代理 | `embodied_sensorimotor_system` | 完整体化需要关节/肌肉，远超当前范围 |
| 2 | 1/r 点源 | `continuous_field_PDE` | 连续场方程算力太高，1/r 物理正确 |
| 3 | 标量 lever | `6DOF_vestibular_IMU` | **已回升！** vestibular_system.py 已实现 6 轴 |
| 4 | 忽略倾斜/平移 | `otolith_canal_cross_validation` | 爱因斯坦等价原理对当前粒子系统无意义 |
| 5 | 恒等坐标变换 | `cerebellar_coordinate_transform` | 没有头/身体区分，恒等变换合理 |
| 6 | 单标量积分器 | `distributed_NPH_MVN_integrator_network` | 积分器已工作，分布式网络无必要 |
| 7 | 粒子质心 | `rigid_body_COM` | 粒子系统没有刚体，质心足够 |

### 舍弃 (3 个)

| # | 真实机制 | 为什么舍弃 |
|---|---|---|
| 1 | `wave_equation_propagation` | 声波/热波传播方程对当前 1/r 场无影响 |
| 2 | `frequency_dependent_absorption` | 频率依赖吸收在静态场中无意义 |
| 3 | `impedance_matching_and_reflection` | 阻抗匹配在粒子系统中无介质界面 |

---

## 三、PhysicsParticleSystem (8 个标注)

### 保留 (5 个)

| # | 当前代理 | 真实机制 | 为什么保留 |
|---|---|---|---|
| 1 | LIF 代理 | `hodgkin_huxley_conductance_model` | HH 太贵，LIF 足够 |
| 2 | 线性弹簧 | `viscoelastic_kelvin_voigt_model` | 粘弹性对当前行为无影响 |
| 3 | 离散弹簧 | `finite_element_continuum_mechanics` | FEM 算力不可承受 |
| 4 | 各向同性 | `anisotropic_tissue_tensor` | 粒子系统无方向性 |
| 5 | 被动弹簧 | `active_stress_actomyosin_contractility` | 肌动蛋白马达需要完整细胞骨架 |

### 舍弃 (3 个)

| # | 真实机制 | 为什么舍弃 |
|---|---|---|
| 1 | `cell_cycle_proliferation_apoptosis` | 粒子数固定是设计选择 |
| 2 | `intercellular_chemical_signaling` | 化学信号需要完整的分子模型 |
| 3 | `extracellular_matrix_adhesion` | ECM 需要纤维网络模型 |

---

## 四、前庭 & 本体感觉 (6 个标注)

### 保留 (5 个)

| # | 当前代理 | 真实机制 | 为什么保留 |
|---|---|---|---|
| 1 | 线性过阻尼 | `hair_cell_mechanoelectric_transduction` | 毛细胞转导太细 |
| 2 | 正交通道 | `anatomical_canal_geometry` | 实际偏角 <15°，影响 <3% |
| 3 | 简化梭内纤维 | `intrafusal_fiber_dynamics` | bag1/bag2/chain 模型无因果影响 |
| 4 | 无 gamma 驱动 | `gamma_motor_fusimotor_system` | 融合运动系统需要完整脊髓 |
| 5 | 瞬时感知 | `afferent_conduction_delay` | 5-80ms 延迟在 tick 尺度不影响 |

### 舍弃 (1 个)

| # | 真实机制 | 为什么舍弃 |
|---|---|---|
| 1 | `velocity_storage_integrator` | 前庭积分器 → 已有 leaky integrator |

---

## 五、介质系统 & HH (7 个标注)

### 保留 (4 个)

| # | 当前代理 | 真实机制 | 保留原因 |
|---|---|---|---|
| 1 | 离散格点 | `wave_equation_FDTD` | FDTD 算力不可承受 |
| 2 | 均匀格点 | `heterogeneous_medium` | 非均匀介质需要完整物性场 |
| 3 | 单室 HH | `multi_compartment_cable_model` | 多室模型算力太高 |
| 4 | 2 离子种 | `extended_ionic_model` | Ca²⁺/Cl⁻ 对当前系统无影响 |

### 舍弃 (3 个)

| # | 真实机制 | 为什么舍弃 |
|---|---|---|
| 1 | `scattering_cross_section` | 散射在均匀介质中无意义 |
| 2 | `coupled_multiphysics` | 热-声耦合在当前无因果影响 |
| 3 | `channel_expression_homeostasis` | 离子通道表达调控太慢 |

---

## 总结

```
┌─────────────┬────────┬────────┬────────┬────────┐
│ 模块         │ 回升   │ 保留   │ 舍弃   │ 合计   │
├─────────────┼────────┼────────┼────────┼────────┤
│ HebbianCircuit │   6  │   21   │   11   │   38  │
│ PracticeEngine │   2  │    7   │    3   │   12  │
│ PhysicsParticle │  0  │    5   │    3   │    8  │
│ Vestibular/Proprio │ 0 │   5   │    1   │    6  │
│ Medium/HH    │   0   │    4   │    3   │    7  │
├─────────────┼────────┼────────┼────────┼────────┤
│ **合计**      │ **8** │ **42** │ **21** │ **71**│
└─────────────┴────────┴────────┴────────┴────────┘
```

> [!IMPORTANT]
> **8 个回升**中，v41.0 代谢环路已回升了 2 个（熵账本 + 反射弧）。
> 剩余 6 个均为**可选回升**——只在系统规模扩大时才有因果影响。
> 
> **42 个保留**是足够好的代理，回升它们只增加复杂性不增加涌现能力。
> 
> **21 个舍弃**是纯生物学/物理学细节，对项目的物理计算/结构计算/物质计算框架无影响。

> [!TIP]
> 建议：将舍弃的 21 个标注从 `DEGRADED` 改为 `INTENTIONAL_SIMPLIFICATION`，
> 表明这不是"还没做"而是"不需要做"。这在论文中也更清晰。
