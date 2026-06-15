# 降级状态审计 — v41.1 完成后

## 总览

| 类别 | 数量 | 说明 |
|------|------|------|
| **unique degraded_from 标签** | 44 | 代码中标注的降级 |
| **INTENTIONAL_SIMPLIFICATION** | 8 | 有意不做（有理由） |
| **本轮已回升/新增** | 5 | 本次会话实现 |
| **仍在降级** | 39 | 需评估优先级 |

---

## ✅ 已回升/功能性恢复的降级

| degraded_from | 回升方式 | 状态 |
|---|---|---|
| `CPG_half_center_reciprocal_inhibition` | v41.1: 对称性破缺 + additive drive + full suppression | **结构性回升** — 不再是退化代理，是真正的半中心振荡器 |
| `cerebellar_forward_model_timing_prediction` | v41.1: Column 前向模型 + phase reset | **新增并标为降级** — 功能已实现但仍是简化版（无颗粒→浦肯野微电路）|
| `wave_equation_FDTD` | v41.1: MediumLattice3D 离散波格 | **部分回升** — 有3D晶格波传播，但仍是离散而非连续FDTD |
| `signal_propagation_delay` | v40: t_ret = r/v retardation | **完全回升** ✅ |
| `metabolic_energy_pool` | v41.0: 全局能量池 + 饥饿→运动驱动 | **功能性回升** — 不是真ATP但闭合了能量环路 |

---

## 🔵 INTENTIONAL_SIMPLIFICATION（不需要回升）

| 简化 | 理由 |
|---|---|
| strict Gibbs free energy | 全局能量池 (v41.0) 足够 |
| full predictive coding hierarchy | Xin 残差已捕获预测误差 |
| glucose-dependent plasticity | v41.0 代谢能量池替代 |
| local heat PDE | 全局热聚合足够；空间热不影响行为 |
| sleep-dependent memory reactivation ×2 | 无睡眠/觉醒周期 |
| full ACC engram model | cx_ 结晶已工作 |

---

## 🔴 仍在降级 — 按优先级分层

### Tier 1: 高影响、可执行（1-3天/项）

| # | degraded_from | 当前代理 | 回升方案 | 影响 |
|---|---|---|---|---|
| **1** | **`heterogeneous_medium`** | 均匀晶格 (k,ρ 常数) | **ρ(x), k(x) 空间变化** → 折射 + 通道分化 | ⭐⭐⭐ 直接影响偏好涌现 |
| 2 | `BCM_learning_rule` | Column 用 EMA | BCM (Bienenstock-Cooper-Munro) 滑动阈值 | ⭐⭐ Column 作为前向模型需要更好的学习规则 |
| 3 | `emergent_feedback_topology` ×2 | 统一反馈权重 | 让反馈权重通过STDP涌现 | ⭐⭐ 当前反馈是手工设计的 |
| 4 | `rigid_body_COM` | 平均粒子位置 | 带质量加权的真质心 | ⭐ 简单修复 |
| 5 | `population_lognormal_gain_encoding` | 单个标量积分器 | 多个积分器×对数正态增益采样 | ⭐ 增加感觉多样性 |

### Tier 2: 中等影响、需要更多设计

| # | degraded_from | 当前代理 | 挑战 |
|---|---|---|---|
| 6 | `NMDA_receptor_Mg2_voltage_dependent_unblock` | 简化的后突触增益 | 需要电压依赖的 Mg²⁺ 解除阻塞模型 |
| 7 | `basket_cell_interneuron_dynamics` | calcium-scaled 阈值推 | 需要显式的basket cell interneuron |
| 8 | `dopaminergic_modulation_of_eligibility_traces` | Xin tension 幅度代理 | 需要资格追踪 + 多巴胺调制 |
| 9 | `basal_ganglia_selection_gating` | 环流阈值代理 | 需要 striatum→GPi→thalamus 通路 |
| 10 | `6DOF_vestibular_IMU` | 标量杠杆率 | 需要旋转动力学 |
| 11 | `distributed_NPH_MVN_integrator_network` | 单个漏积分器 | 需要多神经元积分器网络 |

### Tier 3: 低优先级/研究前沿

| # | degraded_from | 说明 |
|---|---|---|
| 12-13 | `mitochondrial_ATP_synthesis` ×2 | 真线粒体ATP合成=分子生物学 |
| 14 | `voltage_gated_ion_channel_redistribution` | 离子通道重分布=HH模型前提 |
| 15 | `perineuronal_net_formation_and_degradation` | 围神经元网=发育神经科学 |
| 16 | `synaptic_vesicle_pool_recycling` | 囊泡池动力学 |
| 17 | `transcription_factor_regulation` | 基因表达调控 |
| 18 | `cortical_laminar_identity_dynamics` | 6层皮质柱 |
| 19 | `protein_synthesis_and_diffusion_dynamics` | PRP扩散=偏微分方程 |
| 20 | `oligodendrocyte_myelination_dynamics` | 髓鞘形成 |
| 21 | `ion_channel_desensitization_recovery` | 离子通道脱敏 |
| 22 | `synaptic_elimination_complement_tagging` | 补体标记修剪 |
| 23-26 | `embodied_sensorimotor`, `continuous_field_PDE`, etc. | 范式边界 |

---

## 建议下一步

> [!IMPORTANT]
> **最高优先级：`heterogeneous_medium`（异质介质）**
>
> 理由：
> 1. **直接可验证**：ρ(x),k(x) 空间变化 → 信号折射 → 可测量的通道分化
> 2. **纸论文已预留**：paper3 的 "Limitations" 节已提到
> 3. **与 Column 前向模型联动**：异质介质 → 不同通道传播速度不同 → Column 的 phase memory 会分化 → 真正的结构性偏好
> 4. **工作量约1天**：只需修改 `medium_system.py` 的 MediumLattice3D

### 具体方案

```python
# 当前（均匀）:
k = 2.0  # 全局弹性常数
gamma = 0.03  # 全局衰减

# 回升后（异质）:
k[x,y,z] = k_base + δk(x,y,z)     # 空间变化的弹性
rho[x,y,z] = rho_base + δρ(x,y,z) # 空间变化的密度
v_phase = sqrt(k/rho)               # 局部相速度
# → 信号通过不同区域速度不同 → 折射
# → acoustic 可能在某区域快、luminous 在另一区域快
# → agent 在不同位置接收到不同的 "频谱"
```

### 预期效果

| 指标 | 均匀介质 (现在) | 异质介质 (回升后) |
|---|---|---|
| 通道偏好 | acoustic ≈ luminous (都 ~0.97) | acoustic ≠ luminous（取决于位置） |
| Column phase memory | acoustic ≈ luminous (都 +0.058) | 分化（不同传播延迟）|
| 导航策略 | 向最近source | 可能绕行"快速通道" |
| 论文价值 | "偏好涌现" | "环境塑造偏好"（更强的主张）|

### 其他可选方向

| 方向 | 影响 | 难度 |
|---|---|---|
| BCM 学习规则回升 | Column 有更真实的可塑性 | 中 |
| 反馈拓扑涌现 | 消除手工设计 | 中 |
| NMDA 电压门控 | 更真实的 STDP | 高 |
| HH 离子通道 | 完全不同的神经动力学 | 很高（重写） |
