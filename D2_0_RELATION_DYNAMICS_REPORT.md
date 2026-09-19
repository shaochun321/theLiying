# D2_0_RELATION_DYNAMICS_REPORT — 关系过程动力学实测

日期：2026-09-20　轮次：D2-0/P2-B Step3-4b　依据：方案 §8-§18 + 反馈
§四/§六/§十一~§十七

## 一、物理实现（E-3 强制换能链，零母本修改）

```
ϑ_a(t) → RelationInputNeuron_a → frozen SynapticBundle_a ─┐
                                                           ├→ RelationCell(x_ρ)
ϑ_b(t) → RelationInputNeuron_b → frozen SynapticBundle_b ─┘
```
RelationCell = 非 spiking Neuron（C=0.1, R=5.0, τ=0.5s；BIO=树突符合
检测/NMDA 慢积分，Schiller 2000/Wang 2002，与既有 relation collector 同
族）。两束同 physical_seed=73142 ⇒ 通道增益对称（设计约束）。两束电流
求和后单次 cell.step（chain.py:467 先例）。x_ρ=cell.activation，能量=
PowerRail。reference 方程仅 REFERENCE 身份（relation_reference.py）。

## 二、标定（adaptive boundary search，7 评估 ≤16；§22 禁抄 G0 值）

| 量 | 实测 | 说明 |
|---|---|---|
| u_silent | 0.0 | 零驱动 8s 物理静息地板 |
| g_rel canonical | 0.25 | 规则=peak(C2_sim)∈[4.5,5.5] 线性区中点（u_work=5.233） |
| 失败沿 | [9.77e-4, 1.0] 括号 | 下=响应湮灭 / 上=钳位起点 |
| **τ_decay** | **0.456 s** | vs 设计 τ=C·R=0.5s——**RC 物理载体独立确认** |

## 三、C0-C5 矩阵（Step4，全 replay，判据预注册）

峰值：C2=5.233 ≥ C5_strong=4.527 ≥ C5_weak=3.619 ≥ C3_m=3.335（T4 ✓）；
|Δt| 轴严格有序 C3 s/m/l=4.336/3.335/2.636（T2 ✓）；共时 vs 时序可区分
（T3 ✓）；全轨迹 x_end=0.000（T5 耗散 ✓）；峰≤10（T6 ✓）；
C2 > 单父 2.50（T7 叠加 ✓）。

**T1 结构预判证伪（重要发现）**：预注册预测"对称细胞下 C3_m≡C4_m 逐位
相同"——实测 RMSE=2.15e-2 ≠ 0。根因精确定位：**site28 换能潜伏期 521
子步 vs site31=529（8ms 个体差异，G0 链突触扰动）**，occurrence 窗非
镜像；关系细胞本身通道对称。⇒ C3/C4 差异源于 parent 物理个体性，
非 order 检测机制；命名纪律维持（不宣称 order generator）。

## 四、负对照（反馈 §十四，四件不删减）

- NC1 纯共现：ϑ_a·ϑ_b 瞬时积在 C2/C5 非零（RELATION_SIGNAL=YES）、
  无状态（RELATION_PROCESS=NO）——"算出关系值≠产生关系过程"实证
- NC2 无历史映射：同 (标签,瞬时输入)=(0,0) 双时刻 x_pre=0.0 vs
  x_gap>1e-4——**无任何无记忆函数可复现 x_ρ**（兼 D2-M6 核心证据）
- NC3 自激：零驱动 x≡0（无源 RC 无自持振荡）；无父支撑 ⇒ ΔC_phys=0
- NC4 lineage block：阻断 A/B 各使轨迹显著改变（RMSE 1.4/1.9 量级>1e-3）；
  attack：site23 顶替 G_b 过程成立（泛化 ✓）

## 五、C6 + Hidden Dynamics（Step4b，干预 3/6）

C6：同当前输入 (0,0) 下 x(t0)=0.559（双父前史）vs 0.049（单父前史），
未来 RMSE=0.118 ⇒ **RELATION MEMORY CONFIRMED**。
干预：sham 不消除 / tier0（换能神经元态）不消除（trace τ≈0.1s 在 t0
已衰竭，预期兑现）/ **tier1（RelationCell 膜态移植）RMSE 精确 0.0**
⇒ RELATION_STATE_CAUSALLY_SUPPORTED；最小充分候选 = RelationCell 膜态
（单细胞 x_ρ 载体）+ STOP_DEEPER_DECOMPOSITION。

数据：relation_calibration.json / relation_trials.csv / d2_trials.json /
relation_hidden_twins.csv / relation_interventions.csv /
relation_energy_ledger.csv。Commits：249e63b / bec3b4d / c39af26。
