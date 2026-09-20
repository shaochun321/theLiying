# POSTERIOR0_FINAL_RULING — 六门终裁

日期：2026-09-21 ｜ 数据：`data/qualification_summary.json`

## 六门（反馈 §二十五定义）

| 门 | 判定 | 关键数值 |
|:---|:---|:---|
| PC0-M1 Closed-history usable substrate | **PASS** | qrel 窗尾 6131 ≥ Δ t_up 5402（重叠 729 步；τ_vm=500） |
| PC0-M2 Physical posterior entry | **PASS** | C 脉冲→G0 换能(R1C_FALLBACK)→port→tin_c→bundle_c→cell；无 direct write；Δ 无新 occurrence |
| PC0-M3 Persistent organizational state | **PASS** | washout 后 Z11−Z10(膜)=1.141>ε；RESOURCE_TRACE_ONLY 未用 |
| PC0-M4 Prior-dependent interaction | **PASS** | I_W^traj(act)=1.651e-2>ε（连续主判据）；事件面惰性披露（NF-P2）；时序依赖 6.71× |
| PC0-M5 Causal carrier | **PASS** | transplant 正/反向 RMSE=0.0 逐位；block 逐位消除 + BLOCK_LIMITATION 披露 |
| PC0-M6 Immutable/Blind/Ledger | **PASS** | 过去 SHA 逐字节不变（git porcelain 空）；hold6 先封后跑 6/6 零回调；预算全域内 |

## 终态

```text
terminal = A_CONDITIONAL
POSTERIOR_STATE_REORGANIZATION_V0_QUALIFIED = TRUE
  scope: prior-conditioned readout projection H_W（方案 §23/§24 算子定义面）
         + REPLAY/REFERENCE（CAUSAL_VARIANT_REQUIRED_BEFORE_LIVE_D2 不变）
POSTERIOR_OPERATOR_CANDIDATE = YES
operator_class = THRESHOLD_READOUT_GATING
```

𝔅_ΔΓ^W ≠ id 的证据面：H_W（读出投影）上 ‖H'_W − H_W^sham‖=1.65e-2 > ε，
四条件齐（I_W≠0 ✓ / block 消除 ✓ / transplant 重建 ✓ / past raw 不变 ✓）。

**机制**：Δ 残尾把 RelationCell 工作点抬过 DEG-019 硬阈值（vm=0.3），
门控 W 历史残余的下游可见性——"后来的事件改变了过去在当前系统中的
存在方式"在本架构的物理形态 = 历史残余的可读性被后验事件重新组织。

## ⚠ RULING_EXPOSURE（自曝条款，F1 A8-v2 条件化先例）

**NF-P1**：Z-primary 线性载体分量上 𝔅=id（w_shift_vm=3.0e-15）——Δ 不弯曲
W 的膜分量，重组织只存在于读出投影。反馈 §十九字面触发条件（Δ 后新
occurrence）未满足（PNS=False），故未强制降格；但若用户裁定
**"载体分量改变"是 reorganization 的支配判据**（§十九精神扩展到无新
occurrence 情形），则本终态按预登记路径降格为：

```text
terminal = C  POSTERIOR_EFFECT_ADDITIVE_ONLY (at carrier)
+ THRESHOLD_READOUT_INTERACTION 登记为正发现（时序依赖、因果闭合）
```

两种读法下的实验事实完全相同；差别仅在"reorganization"一词的授予面。
**READY_FOR_POSTERIOR_1 = pending user ruling on RULING_EXPOSURE。**

## 命名纪律（反馈 §二十六）

未宣布：Xin qualified / Xin implemented / TOPRXin confirmed /
posterior cognition / reinterpretation / meaning update。
Posterior-0 仅为第一次物理后验状态重组织实验（readout-gating 类）。

## 冻结

Posterior-0 FREEZE：NEAR=(5402,5541,6041) R1C_FALLBACK / washout=456 /
Q=ramp639@Δ_rearm+456 / hold6 SHA=edeff45cc85f97ba…；
G0/D2-0/D2-1 全程 READ_ONLY 未动（git 逐字节验证）。
下一步（终态 A 确认后）= Posterior-1：跨多个 W,ΔΓ 提取重复出现的后验算子族
（方案 §35）；若降格 C 则下一步问题 = "载体级可重组织的基质在哪里"。
