# WT0_CROSS_PAIR_AND_REDUCTION_REPORT — 剂量攻击复现 + Cross-Pair 矩阵 + 终裁

日期：2026-09-18
脚本：`research/wt0/{wt0_dose_attack,wt0_cross_pair_matrix}.py`
数据：`research/wt0/data/{wt0_dose_attack.json, WT0_CROSS_PAIR_MATRIX.csv,
wt0_cross_pair_summary.json}`

---

## 一、剂量攻击仓内复现（§7，裁定 R-4）

协议：node0 持续驱动 2000 步 + 撤去 2000 步；G0 = exp_P2A1b_3 模板
（rearm=500）；amp∈{0.01, 0.1, 0.25, 0.5, 1.25, 5, 50}。

| amp | q_max 实测 | 外部声称 | floor/ceil/interior | occurrence | duration |
|---|---|---|---|---|---|
| 0.01 | 0.77 | ≈0.76 | 1.000/0/0 | 0 | — |
| 0.1 | 7.67 | — | 1.000/0/0 | 0 | — |
| 0.25 | 19.17 | — | 1.000/0/0 | 0 | — |
| 0.5 | 38.33 | ≈37.96 | 1.000/0/0 | 0 | — |
| 1.25 | 95.83 | ≈94.91 | 0.040/0.887/0.043 | 1 | **395** |
| 5 | 383.31 | — | 0.004/0.990/0.003 | 1 | **390** |
| 50 | 3833.06 | ≈3796.27 | 0.000/1.000/0.001 | 1 | **391** |

- 线性自洽：q_max/amp = 76.6611，max_rel_dev = 1.19e-14。
- 与外部比对：**定性全吻合**（弱输入 u≡0/occurrence=0；强输入均大量
  进入 u=0.04、各 1 次 occurrence）；**duration 395/390/391 与外部声称
  "≈390 步"精确吻合**；q_max 系统性偏高 ~1%（76.66 vs 隐含 75.93/amp）
  ——外部未指明驱动时长，归因协议时长差异，登记不影响判定。
- 40× 物理幅度差（1.25 vs 50）被压缩为同一"1 次 occurrence、duration
  差 4 步"——顶棚饱和抹平剂量信息，实锤。

```text
W0_E_TRANSDUCTION_BOTTLENECK = CONFIRMED（R-4 复现达标，准予冻结）
```

## 二、Cross-Pair 矩阵（§12）+ 信息缩减两端审计（§11）

网格：κ∈{0.025, 0.05, 0.1}（r_leak=10/κ 绑定保持，解绑属 W1）×
驱动节点{0,2} × 幅值{0.65, 1.0, 1.5} × 时序{持续300, 双脉冲6a×25×2}
= 每 κ 12 历史，同 κ 内两两配对 66 对 ×3 = 198 对；T=2000 步；
度量按 T1-A §8 新契约（绝对值+归一值+占用率并报，禁止裸 ratio）。

### 分 κ 汇总（198 对全部满足前提 D̂_world>0.1）

| κ | r_leak | 完全湮灭 full/reduced | 平均地板占用 | retention_full min/med/max |
|---|---|---|---|---|
| 0.025 | 400 | 0 / 1 | 0.840 | 1.085 / 1.656 / 3.725 |
| 0.05（TEST 档） | 200 | 0 / 3 | 0.931 | 1.133 / 1.501 / 4.593 |
| 0.1 | 100 | **6** / **15** | 0.976 | **0.000** / 1.097 / 5.026 |

### 两端案例（§11，禁止只报平均；retention 必须连同分子分母读）

- **D_preserve^max（full）**：κ=0.1，n0_a1.5_sus vs n2_a1.5_sus——
  D̂_world=0.2643，D_tr_abs=**0.003706**，retention=5.03，fl=0.93/0.93。
  归一值虚高 5 倍而绝对差仅 0.0037：**保留之最仍是基线归零放大区**。
- **D_loss^max（full）**：κ=0.1，n0_a0.65_sus vs n0_a1_sus——
  D̂_world=0.3500，D_tr_abs=**0.000000**（双双全地板 fl=1.00）：
  同节点 1.54× 剂量差在转导后完全不可见。
- **D_loss^max（reduced）**：κ=0.025，n2_a0.65_sus vs n2_a0.65_pulse——
  D̂_world=0.6569（时序结构差，非幅值差）→ D_tr_red_abs=0.000000：
  **纯时序历史差异被完整湮灭**。

### 核心发现

**legacy 转导在整个 World v1 合法参数域内不存在保真区**：198 个有效对
的 retention 要么 >1（基线归零失真放大，最低 1.085，全部伴随
fl≥0.84），要么 =0（完全湮灭）。κ 从 TEST 档 0.05 变到合法值 0.1
即出现 6/66 全湮灭对——只有"专配组合"（TEST κ + amp≈1 稳态段）落窗：

```text
CO_ADAPTATION_RISK = HIGH（§12 判据触发：交叉即失效）
```

## 三、§23 终裁

| 前置件 | 结果 |
|---|---|
| 三对象合同 + Y_B 显式定义（R-3） | 已冻结（CONTRACT 文档 §一/§二） |
| WORLD_HIDDEN_DYNAMICS_POSITIVE_CONTROL | ESTABLISHED（三门 PASS） |
| Boundary Replay | HIDDEN_SIDE_CHANNEL = PASS（两 Gate 逐位一致） |
| 剂量攻击复现（R-4） | CONFIRMED |
| 转导角色审计（§9） | **TRANSDUCTION_ROLE = OVERLAPPING_UNRESOLVED**（u 按 dT_raw 速率语义被 L1 消费；affine+clip 偷承担事件筛选/幅值分类/动态范围选择） |

```text
WT0 终裁 = WT0_TRANSDUCTION_CONTRACT_UNRESOLVED
```

按 §23 语义：D_i 职责与 L1（ThermalDeltaNeuron）重叠未解除，**W1 不得
开始**。这与 R-1 冻结序完全一致——T1-A（转导结构合同轮）本就排在 W1
之前，其第一约束已在 CONTRACT 文档 §五.3 登记（职责指派 + 幅值/速率
端口语义一致性）。侧信道与正对照两项均 PASS，未触发
WT0_SIDE_CHANNEL_FAIL；T1-A 完成职责解除后 W1 即可开工。

## 四、测试结果（本轮收口）

母体 nexus_v1/ 与 tss/ 零改动（G0 只运行未修改；新增 research/wt0/
4 脚本与 3 文档）。回归状态：test_regression 21/21 PASS（exit 0）；
tss version_pairing PASS；tss fast 43 passed。

## 复现入口

```bash
PYTHONIOENCODING=utf-8 python research/wt0/wt0_dose_attack.py        # exit 0
PYTHONIOENCODING=utf-8 python research/wt0/wt0_cross_pair_matrix.py  # exit 0
PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.test_regression
PYTHONIOENCODING=utf-8 python -m pytest tss/tests -m fast -q
```
