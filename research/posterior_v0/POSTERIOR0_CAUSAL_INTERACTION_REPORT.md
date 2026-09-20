# POSTERIOR0_CAUSAL_INTERACTION_REPORT — Step D/F 主交互与因果闭合

日期：2026-09-21 ｜ 数据：`data/posterior_interaction.json` /
`posterior_path_block.json` / `posterior_state_intervention.json`

## 2×2 主交互（eval 窗 = [q_up, q_up+639+456)，washout=456 已过）

| 集 | I_W^traj(activation, PRIMARY) | I_W^traj(membrane) | I_W^occ |
|:---|:---|:---|:---|
| NEAR（Δ=5402，R1C_FALLBACK） | **1.651e-2** | 3.09e-15 | 0 |
| MIDDLE（Δ=6344，qrel 窗外/ε 窗内） | 2.478e-3 | 2.86e-15 | 0 |
| TIMING-CONTROL（Δ=4577，rearm 前，CONTROL） | 2.459e-3 | 3.82e-15 | — |

- **PL2 达标**：I_W(NEAR)=1.65e-2 ≫ ε_num=1e-6（连续主判据，反馈 §十六）。
- **时序依赖**：NEAR/TC = **6.71×**（同剂量错时对照，方案 §18）；
  §19 弧：NEAR(1.65e-2) → MIDDLE(2.5e-3, 边界) 实测。
- **PL1**：washout 后 Z11−Z10（膜）=1.141 > ε（RESOURCE_TRACE 单列未用）。
- **PNS=False**：Δ 未触发新 χ_ρ₂（合同 §六.5 兑现）；四臂 W 边界逐位 (3332,4931,5387) 不变。
- **M_Q margin 面**（heldout 证据）：Δ-present 臂 **+0.25**（Q 峰越 θ₂）vs
  sham 臂 **−0.065** ——存在级符号翻转；occ_Q 事件面惰性
  （Q 斜坡峰值贴支撑窗尾，ΔC_phys 门拒绝——NF-1 同语义，NF-P2 登记）。

## 交互机制定位（诊断，非门）

逐点交互峰在 **k*=6497（Q 起步）**：vm@k* = {11: 1.174, 10: 0.035, 01: 1.147,
00: 0.008}。W 残余差(≈0.027)在 Δ-present 臂（vm 阈上）线性穿透读出，在 sham 臂
（vm<0.3 **阈下截零**）不可见——非加法性 = **Δ 残尾把工作点抬过 DEG-019 硬阈值，
门控历史残余的下游可见性**（THRESHOLD_READOUT_GATING）。

## 因果闭合（Step F）

- **Block（F1，DIAGNOSTIC）**：bundle_c 于 [5387,6497) 断传播、tin_c 照常换能。
  blocked 臂与 (1,0) 臂 **逐位 RMSE=0.0** ⇒ Δ 全部影响走 bundle_c ⇒ I_W'→0。
  审计 4/5（tin 接收 ✓/状态变 ✓/传输零 ✓/cell 剂量零 ✓）；能耗项吞吐差=精确 0.0
  ——**BLOCK_LIMITATION**（该基质阈下换能零可测耗散；反馈 §二十五 M5 条款披露，不自动 FAIL）。
- **Transplant（F2，主因果门）**：t0=6496 tier1 cell.__dict__ 移植。
  sham 保持分叉（vs near_10 逐位 0.0；基线 11-vs-10 RMSE=0.428）；
  **forward Z10←Z11 RMSE=0.0 逐位等化**；reverse Z11←Z10 同样 0.0。
  ⇒ POSTERIOR_MINIMAL_SUFFICIENT_STATE_CANDIDATE = **RelationCell 单细胞膜态**，
  STOP_DEEPER_DECOMPOSITION。
