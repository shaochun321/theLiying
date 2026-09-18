# T1B_CALIBRATION_AND_CROSS_WORLD_REPORT — 标定集 + cross-pair + LORO + v1 参照

日期：2026-09-19
脚本：`research/transduction_v2/t1b/{t1b_dataset,t1b_calibration_cross_world,t1b_timebase_audit}.py`
数据：`research/transduction_v2/t1b/data/`

---

## 一、数据集（§6-§8）

- W_cal=30（WorldSampler seed=1001 直采 Θ_legal）；W_hold=20（seed=2001
  分层，**含全部困难角**：强耗散 r_leak<50 ×3 / 3 源 / N=3 / N=20 /
  错时源 / REDUCED 非 node0；建成即 SHA256 封存=BLIND）；W_ref=v1 三历史。
- strata 只按物理量（无语义标签，§8）；LORO 成员列登记于 manifest
  （LORO-A=cal 中 r_leak≥50 共 23；LORO-B=cal 中 ≤2 源共 16）。

## 二、calibration 三候选陪跑（§22）

| 候选 | cal 30 episodes 状态分布 |
|---|---|
| legacy（负控制） | DEGRADED=20, SEMANTIC_FAIL=9, QUALIFIED=1——旧病（floor/ceiling/动态范围塌缩）在 World v2 合法域全域复现 |
| **A（U_T）** | **QUALIFIED=30/30** |
| **B（U_Ṫ）** | **QUALIFIED=30/30** |

状态分类与 §37 归因规则先声明于 `t1b_common.py` docstring（五类 +
WORLD_ALREADY_REDUCED / TRANSDUCTION_LOSS 归因）。

## 三、参数合法域（§12/§23——无 argmax）

S、g ∈ [1e-5, 1e3] log 网格全部 numeric_ok：**线性映射在数值溢出前无
内在失效边界**（如实登记）；下游 L1 钳位子域仅信息性（§33 L1=接口后果
非目标）。canonical 值与 provenance 见合同 §四（CANONICAL_REFERENCE，
held-out 锁定前预承诺，≠OPTIMAL）。

## 四、cross-pair 共谋攻击（§20）+ LORO（§21）

- **一套 canonical θ_D 横跨全部 30 个 World 条件**（N/κ/r_leak/源数全
  变化）：A/B 零 NUMERIC/SEMANTIC_FAIL ⇒ `CO_ADAPTATION_RISK = LOW`。
- LORO：canonical 参数**未经任何拟合** ⇒ LORO 退化为跨域状态检查
  （如实登记退化形态）：LORO-A 排除域（r_leak<50，7 eps）与 LORO-B
  排除域（3 源，14 eps）上 A/B 零失败。

## 五、World v1 reference（§6 历史可比性）

w0e 三历史 scale=1.0 × 三候选：legacy A-B 归一比 **5.72**（基线归零
假放大与 T0/WT0 冻结值逐位一致复现）；A retention=**1.000**（跨代
World 线性保真基准延续）；B 保留时序区分。

## 六、timebase 审计（§9-§11 + 合同 C2）

同一物理 episode（T_phys=2000 s）积分 dt∈{1, 0.1, 0.01}，整秒采样：

| 序列 | 1.0→0.1 | 0.1→0.01 | 判定 |
|---|---|---|---|
| boundary | 1.99e-3 | 1.98e-4 | 收敛（W1 基线） |
| **A** | 1.99e-3 | 1.98e-4 | **AMPLITUDE_PORT_DT_INVARIANT**（=边界收敛量级） |
| **B（dt-aware）** | 7.72e-3 | 7.39e-4 | 收敛 ✓ |
| naive 每步差分（负控制） | 幅值比 0.100/0.100 | — | **RATE_PORT_DT_DEPENDENT_FAIL**（每细化一档幅值精确 ×0.1——T1-A D2 债务的定量实证；naive 形式弃用） |

MAINLINE_TIMEBASE_CONTRACT（Δt_ext=1 s）由此实测背书。
