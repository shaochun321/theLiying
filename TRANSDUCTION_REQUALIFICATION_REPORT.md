# TRANSDUCTION_REQUALIFICATION_REPORT — 𝒟_i 转导合同重资格化（Phase T0）

日期：2026-09-18
依据：主线重启 R1 收口（fbccfa1）W0-E 判定"塌缩在 𝒟_i 转导窗非场层"；
方案经用户批准（BACKLOG Phase T0 行）。
脚本：`research/transduction_requalification/t0_window_audit.py`
数据：`research/transduction_requalification/data/{t0_window.json, t0_traj_scale*.csv}`

**状态变更**：`REFERENCE_TRANSDUCTION_CONFIG`（`tss/generators/skin_transduction.py`，
已冻结 LEGACY_TRANSDUCTION_INSTANCE）的资格域首次实测登记：
**三历史类下仅 scale∈[0.65, 1.5] 三对全保留（≈0.36 个十倍程，双侧有界）；
窗外 NOT_QUALIFIED；u_interior 保证对参考类轨迹不成立（见 §四）。**

---

## 一、测量对象与契约

- 对象：u=clip[κ(q−q0)+b]，κ≈0.0013759，b≈−0.0550663，clip=[0, 0.04]。
- 度量契约逐字继承 W0-E（import 复用 `w0e_history_discrimination.py` 的
  run_history/dhat；判定 ratio<0.01→COLLAPSE / [0.01,0.5)→PARTIAL / ≥0.5→PRESERVED，
  前提 D̂_world>0.1）。scale=1.0 三对 r3=5.7249/1.5790/1.5213，与 W0-E 冻结值
  **逐位一致**（可比性确认）。
- 解析预测先登记后实测：T_floor=−b/κ=40.01；T_ceil=(0.04−b)/κ=69.10。
- 本轮 `nexus_v1/` 与 `tss/` 代码零改动；support 读出止于 u_i（G0 入口），
  closure 级留 G1。

## 二、T0-A 资格窗边界测绘（13 档扫描 + 4 档自动加密）

| scale | T_peak | A-B r3 / verdict | A-C r3 | B-C r3 |
|---|---|---|---|---|
| 0.1~0.3873 | ≤38.1 | 0.0000 COLLAPSE | 0.0000 COLLAPSE | 0.0000 COLLAPSE |
| 0.5~0.6245 | 49.1~61.4 | 0.0000 **COLLAPSE** | 1.1606 PRESERVED* | 1.1623 PRESERVED* |
| 0.65 | 63.9 | 6.4729 PRESERVED | 1.1606 PRESERVED | 1.1623 PRESERVED |
| 1.0 | 98.3 | 5.7249 PRESERVED | 1.5790 PRESERVED | 1.5213 PRESERVED |
| 1.5 | 147.4 | 1.7742 PRESERVED | 1.4085 PRESERVED | 1.4159 PRESERVED |
| 2.1213 | 208.5 | 0.4818 **PARTIAL** | 1.3823 PRESERVED | 1.3601 PRESERVED |
| 3.0 | 294.8 | 0.0828 PARTIAL | 1.2393 PRESERVED | 1.2388 PRESERVED |
| 5.4772 | 538.2 | 0.0000 **COLLAPSE** | 0.8776 PRESERVED | 0.8790 PRESERVED |
| 10 | 982.7 | 0.0000 COLLAPSE | 0.5912 PRESERVED | 0.5920 PRESERVED |
| 50 | 4913.5 | 0.0000 COLLAPSE | 0.4481 **PARTIAL** | 0.4488 PARTIAL |

（T_peak = 三历史全局峰温，由 Γ_C 的 6× 脉冲主导；Γ_A 峰温 = 61.826×scale。）

**边界实测 vs 解析预测：**
- A-B 地板侧跳变夹在 [0.6245, 0.65]，预测 0.647（=40.01/61.826，Γ_A/Γ_B 峰温过
  T_floor）**落在夹层内 ✓**。
- A-C/B-C 地板侧跳变夹在 [0.3873, 0.5]，预测 0.407（=40.01/98.27，Γ_C 6× 脉冲
  峰温过 T_floor）**落在夹层内 ✓**。
- \* 但 s∈[0.5, 0.6245] 的 A-C/B-C "PRESERVED" 是**退化保留**：Γ_A/Γ_B 地板命中率
  =1.000（support 恒 0），仅 Γ_C 脉冲探出地板——区分完全靠"可见/不可见"二值差，
  不是历史结构差。
- **高幅侧新发现**：A-B 在 s≥2.12 退化 PARTIAL、s≥5.48 完全塌缩（连续加热史被
  顶棚 0.04 饱和抹平）；A-C/B-C 到 s=50 亦退 PARTIAL。**资格窗双侧有界**——
  W0-E 只测了 {1.0, 0.1} 两档，未看到顶棚侧。

```text
三对全保留窗 = scale ∈ [0.65, 1.5]（宽 2.31×，≈0.36 个十倍程）
```

## 三、T0-B 塌缩机制三段分解（乘法：r3 = 1 × f_bias × f_clip）

- stage1 纯 κ 缩放：ratio≡1.0（<1e-9 断言通过，自检门）——**κ 本身零损失**。
- f_bias（+偏置 b）：单调随 scale——0.046(s=0.1) → 0.539(s=1.0) → 1.180(s=5.48)
  → 1.024(s=50)。小信号区偏置支配 RMS 分母，压掉 ~95% 区分度（W0-E lin 对照
  0.046/0.54 是该曲线的两个点）。
- f_clip：地板侧塌缩全部由 f_clip=0 完成（死区截断）；窗内 f_clip=2.5~19（放大，
  来源见 §四）；顶棚侧 A-B 的 f_clip 从 2.2(s=1.5) 崩到 0.47(s=2.12)、0(s≥5.48)。

## 四、T0-C 窗内 clip 审计——u_interior 保证不成立（核心发现）

合同宣称参考类映入 u_interior=[0.005, 0.03]。实测 scale=1.0（W0-E 的"域内"组）：

| 历史 | 地板命中率 | 顶棚命中率 | u_interior 占比 |
|---|---|---|---|
| Γ_A | 92.1% | 0 | 5.3% |
| Γ_B | 92.4% | 0 | 4.7% |
| Γ_C | 96.5% | 0.7% | 1.4% |

**参考类轨迹 >92% 样本被地板 clip 归零，u_interior 占比 ≤5.3%。** 原标定
（EXP-P2A1b2-001）用的是六场景**稳态端点**温度 [43.65, 61.83]，而真实轨迹从
静息 T=0 升温、注入停止后 τ=200 步衰减回 T<40——绝大部分时间在死区内。
由此定性 W0-E 的窗内放大（ratio>1）：**clip 把共同基线归零 → RMS 分母塌缩 →
D̂_supp 虚高。这是失真（baseline-zeroing artifact），不是保真。** 判定：
窗内放大 = **合同保真性违约**，"PRESERVED" 判定部分建立在失真之上。

## 五、T0-D 下游需求端锚点（文档比对，未跑 G0）

- u_on∈[0.0004, 0.0006]（P2-A1b-0 实测，引自 skin_transduction docstring +
  `cell-cell/工作报告/P2-A1b-0边界复核…_2026-07-21.md`）。
- 𝒮_cap 转折 u=0.05（P2-A1a-R：activation_L1=min(200u,10)）。
- 下游可用动态范围 ≈[0.0006, 0.05]（~1.9 个十倍程）；合同目标区 [0.005, 0.03]
  只占 ~0.78 个十倍程，**利用率 ~41%**；且如 §四所示连该目标区都未真实兑现。

## 六、停止条件评估

| 要求 | 实测 | 满足? |
|---|---|---|
| 转导窗覆盖世界可产生的历史类 | 三对全保留窗仅 0.36 个十倍程，双侧有界 | ✗ |
| 窗内保真（区分度传递非失真） | ratio>1 = 基线归零假象；u_interior 占比 ≤5.3% | ✗ |
| 静息附近可见性（W0-E 塌缩已证） | T<40.01 死区，support 恒 0 | ✗ |
| 下游动态范围利用 | 0.78/1.9 十倍程（~41%），且未兑现 | ✗ |

```text
TRANSDUCTION_V2 = REQUIRED（T0 判定成立）
```

## 七、对 W0-E 的勘误性澄清（不改变其结论）

W0-E 标注 scale=1.0 为"域内（T 峰 61.8）"——该峰温仅为 Γ_A；全局峰温实为
98.27（Γ_C 6× 脉冲），已越过 T_ceil=69.10（Γ_C 顶棚命中 0.7%）。塌缩定位结论
（场忠实/转导截断）不受影响，但"域内"标签应读作"Γ_A 稳态落入标定域"。

## 八、T1 设计要点登记（本轮不建设）

① **去偏置/静息锚定**：q_i0 锚定静息基线，静息以上偏离即可见（现行 b=−0.055
把 T<40 全部藏进死区）。② **轨迹标定替代端点标定**：以参考轨迹分布（含升温/
衰减段）而非稳态端点校准，u_interior 保证才可兑现。③ **压缩型映射**覆盖全
物理域 →[10×u_on, 0.045]：候选饱和形式需 Q1 生物对应（热感受器传递函数），
T1 查文献后定，本轮不填。④ **与 W1 接口共设计**：World v2 输出动态范围规格
与转导窗互为合同（W0 已登记 W1 三缺口，本条为第四项接口约束）。

## 九、测试结果（本轮收口）

母体 nexus_v1/ 与 tss/ 零改动（仅新增 research/ 脚本与文档）。
回归状态：test_regression 21/21 PASS（exit 0）；tss version_pairing PASS；
tss fast 43 passed（11.4s）。脚本自检门：等能量（相对误差<1e-9）✓、
stage1 ratio≡1.0 ✓、T_peak/scale 线性最大相对偏差 7.2e-16 ✓。

## 复现入口

```bash
cd <repo根>
PYTHONIOENCODING=utf-8 python research/transduction_requalification/t0_window_audit.py
PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.test_regression
PYTHONIOENCODING=utf-8 python -m tss.tests.test_version_pairing
PYTHONIOENCODING=utf-8 python -m pytest tss/tests -m fast -q
```
