# POSTERIOR0_STATE_REPORT — Step A Substrate + Reachability

日期：2026-09-21 ｜ 数据：`data/substrate_audit.json`

## Substrate（rc_main，t_rearm_W=5387，边界重放逐位=冻结值）

| 面 | residual_start | τ_residual | last≥ε(1e-6) | last≥0.028·θ₂ |
|:---|:---|:---|:---|:---|
| membrane vm（Z-primary） | 0.32508 | **500.0 步**（=C×R 物理值） | 11732 | **6131** |
| activation 读出 | 0.00066 | 6.4 步 | 5426 | —（无） |

关键结论：activation 面的快速坍缩是 **DEG-019 MOSFET 硬截零读出效应**（vm<0.3 截零），
不是膜态消失；Z-primary 载体（膜电压）以 τ=500 步（=C·R=0.1×5）正常 RC 衰减。
τ_residual(500) ≠ rearm₂(456)：closure 标定的 tau_decay2_s=0.456 测的是 activation
域衰减，膜域时标为纯 RC 值——两者差异登记为观测事实（不改任何冻结参数）。

## Reachability（R-1(a) 主路径 + R-1(c) 一次后备）

- probe1（t_on=4780/P=600）：**零 occurrence**——collector 越阈 k=5402 落支撑窗
  [4780,5379] 外 23 步（NF-1 同机制；此即 L1 尾容限 <23 步的实测上界）。
- probe2_r1c（同 t_on/P=900，R1C_FALLBACK，probe1=paired control）：
  occurrence **(5402,5541,6041)**，t_up=5402 > 5387 ⇒ **NEAR reachable**。

## 硬 Gate

Δ(t_up=5402) ≤ qrel 窗尾(6131)：**重叠 729 步** ⇒ PROCEED_STEP_B。
POSTERIOR_SUBSTRATE_ABSENT 不成立（反馈 §十三判据：T_residual ≥ T_min_reachable）。
