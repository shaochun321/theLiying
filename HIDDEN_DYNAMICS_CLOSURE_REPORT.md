# HIDDEN_DYNAMICS_CLOSURE_REPORT — 隐藏动力学闭合第一例（振荡相位）

日期：2026-09-19　轮次：G0-R1/OCC Step4　依据：外部方案 §12-§15（E-9/E-10）

## 一、twin 构造（利用 G0_OSCILLATOR_PHASE_SENSITIVITY）

A/B 两 fresh G0，等量预驱动（u=0.03，900 子步）错开 Δ=300 子步（≈先证
600-700 步振荡周期之半）。t0=4917（静息窗内 argmin |col_A−col_B|）：

- 可见面（预注册=G0 对外口 (l1.activation, collector.pre_trace)）：
  |Δcol| = **1.01e-05**（近似相等 ✓）
- 隐藏态：hc+ensemble+collector pre_trace 向量 L2 距离 = **1.3733**
  （O(1)，与 G0-R0 登记的相位失相干量级一致）

## 二、未来分叉（相同未来协议：t0+1000 处 500 子步探测脉冲）

baseline：next_occ_latency A=92 / B=30 子步，轨迹 RMSE=0.333 ⇒
**DIVERGED**——振荡相位真实改变后续 occurrence（评判 E-10 预期兑现，
非 MICROSTATE_ONLY）。

## 三、干预（DIAGNOSTIC_INTERVENTION，E-9 登记：研究区专用，禁止流入 production）

| 臂 | 移植内容 | latency | RMSE vs A | 等化 |
|---|---|---|---|---|
| sham（负对照） | 仅 L1 状态 | 30 | 0.333 | ✗（分叉保持 ✓ 负对照成立） |
| Z_low | hc+ens+col 的 pre_trace ×10 | 35 | 0.330 | ✗ |
| **Z_full** | hc+ens+col 完整状态 | **92** | **0.000e+00** | **✓ 逐位等化** |

## 四、裁定（§13/§14）

- **HIDDEN_STATE_CAUSALLY_SUPPORTED**（Z_full 移植后未来与 A 逐位一致；
  sham 负对照不消除分叉）。
- 关键否定发现：**Z_low（pre_trace 10 维）不充分**——相位载体在膜电容
  电荷等完整神经元状态中，不在 trace 层。
- 最小充分态候选 = **Z_full（hc+ensemble+collector 完整状态，当前实验
  分辨率）** → CURRENT_MINIMAL_SUFFICIENT_STATE_CANDIDATE +
  **STOP_DEEPER_DECOMPOSITION**（§14：除非未来出现 P*_A=P*_B 而
  Future_A≠Future_B 的反例，禁止继续拆 Z→Z1→Z2；亦不把全部 neuron
  state 提升为生成元状态——本裁定只授予"候选"）。

## 数据交付

`r1_occ/data/hidden_twin_pairs.csv` / `hidden_interventions.csv` /
`minimal_state_ruling.json`。Commit：79070a4。
