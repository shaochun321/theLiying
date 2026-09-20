# POSTERIOR0_NEGATIVE_RESULTS — 负结果与限制登记

日期：2026-09-21 ｜ 数据：`data/posterior_negative_controls.json` /
`p0_timing_freeze.json` / `p0_probe_manifest.json`

## NF-P1 载体级加法性（本轮最重要负发现）

§19 分离性审计（窗 [5402,7592)）：W 可归因膜分量不变性
**w_shift_vm = 3.01e-15**（float 噪声地板）⇒ **Δ 没有改变 W 的膜分量**——
膜电压严格线性叠加（E1 膜面 D1=D0=0.54134 逐位加法）。
𝔅 在 Z-primary 线性载体分量上 = **id**；非加法交互（w_shift_act=5.99e-2）
全部由阈值读出承载。→ 终裁 RULING_EXPOSURE 的事实基础。

## NF-P2 occ_Q 事件面惰性

Q 相位斜坡峰值出现在支撑窗尾，越阈落窗外 → ΔC_phys 门拒绝确认 →
全臂 occ_Q=0（含 M_Q=+0.25 的越阈臂）。事件面（occurrence existence）
对本 Q 形状结构性失灵；margin 面（M_Q 符号翻转）与连续面有效。
（NF-1 同语义；如需事件面活性需重新设计 Q 窗形——本轮冻结不改。）

## BLOCK_LIMITATION（反馈 §二十五 M5 条款）

阻断审计第 3 项（tin_c energy used）不可测：blocked 臂 vs (1,0) 臂总耗散差
= 精确 0.0（PowerRail r_supply=0.01 快速回充 + 该驱动域阈下换能零可测耗散）。
其余 4/5 项 PASS；transplant 主因果门强成立 → 按条款披露、不自动 FAIL。

## LIM-POSTERIOR-TIMING-FAR

FAR 时点（δt=4τ）**未尝试**：new_g0 预算 4/4 耗尽
（probe1/probe2_r1c/middle/hold_timing）。外推 t_on≈6540/P=900 可能可达但未测
——登记为"未尝试"而非"不可达"（诚实措辞）。

## probe1 负结果（NF-1 定量延伸）

t_on=4780/P=600 零 occurrence：越阈 5402 落支撑尾 5379 后 23 步 ⇒
**L1 尾容限 < 23 步**（NF-1 原登记为 <37 步，本轮收紧上界）。
s23 缓存 `p0_probe_near.csv` 保留为证据。

## 其他

- τ_residual(膜)=500 步 ≠ rearm₂=456：closure 标定的 tau_decay2_s 测的是
  activation 域衰减；膜域=纯 RC（C×R=0.5s）。观测登记，不改冻结参数。
- MIDDLE 潜伏外推误差 10 步（预测 6334 vs 实测 6344）——NF-1 漂移模型
  在 t_on=5660 仍近线性。
