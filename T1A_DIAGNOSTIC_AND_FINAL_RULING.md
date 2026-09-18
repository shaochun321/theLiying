# T1A_DIAGNOSTIC_AND_FINAL_RULING — 诊断结果 + 五门九问终裁

日期：2026-09-18
脚本：`research/transduction_v2/prototypes/t1a_diagnostic_replay.py`
数据：`research/transduction_v2/data/{t1a_diagnostic_replay.json, candidate_response.csv}`
前置：`T1A_PORT_AND_ROLE_AUDIT.md` / `T1A_THERMORECEPTOR_Q1_REVIEW.md` /
`T1A_CANDIDATE_ARCHITECTURES_AND_METRICS.md`（合同先冻结后实验）

---

## 一、九问首屏直答（§30）

1. **当前 D_i 真正承担了哪些职责？** 单位/尺度映射（名义）+ 幅值窗选择、
   死区事件预筛、饱和压缩、动态范围选择（越权，WT0 已裁）。证据：审计
   文档 §四矩阵 + 本轮 legacy 行（R1/R7 zero=1.000、R6 sat=1.000）。
2. **当前 L1 真正承担了哪些职责？** 半波整流 + ×200 增益 + 上钳 10。
   仅此。无微分、无适应（`transducer_neurons.py:305-323`）。
3. **两者在哪里重复？** 饱和（D_i clip 0.04 vs L1 上钳 10）与事件预筛
   （D_i 死区 vs closure θ_up）；另有**两轨类目冲突**：TSS 把 L1/HC 划入
   D_i^sim（`base_generator.py:100-103` 自述），nexus 把 ThermalDelta
   划入 L1 感觉链（LAYER_CATEGORY_CONFLICT，审计 §四）。
4. **当前 u_i 是幅值还是速率？** 幅值（κ(q−q0)+b 为温度幅值的仿射像），
   却被按速率口消费。`PORT_SEMANTIC_MISMATCH = CONFIRMED（限 TSS
   WORLD_COUPLED 支路；生产支路 SkinPatch.dT→L1 语义自洽）`。
5. **当前端口是否量纲一致？** 否（支路 W）：[u]≠[T/step]，且无 S 声明
   衔接该换类；另登记 D2（dT 为每步差分未除 dt）与 D3（皮肤/生成元双
   时钟）两项量纲约束（审计 §二）。
6. **Transduction v2 应是无状态还是有状态？** **D 层无状态薄接口**
   （Gate A=YES）。适应态（X_D）按 Q1 卡 2/3 属 L1 内部机制，置于 D 层
   =搬错层（Gate D）。
7. **速率提取应该属于 D_i 还是 L1？** **应然属 L1**（Q1：速率敏感从
   幅值换能+受体内适应态涌现，非外置微分器）；**现状工程先例在
   Boundary 层**（SkinPatch.dT，支路 P）。过渡形态允许显式 𝒫_Ṫ（声明
   单步寄存器身份，Candidate B），不许藏在无状态 transduce() 名下。
8. **G0 端口合同是否必须修改？** `G0_PORT_CONTRACT_CHANGE_REQUIRED`
   （§22 登记，本轮不改代码）：端口声称语义（dT_raw 速率）与 de facto
   用法（P2-A 抽象 u）已分裂；目标架构（薄幅值 D + L1 内速率提取）需要
   端口改名/改语义，留 T1-B/G0 回接阶段。
9. **是否 T1A_ARCHITECTURE_READY？** **是**（见 §四终裁）。

## 二、诊断结果要点（R1-R8 × 5 候选；全数据见 JSON/CSV）

### legacy（负对照）——八项冻结负结果全部复演
R1/R7 全地板（zero=1.000，L1 全程静默）；R3 sat=0.512 / R6 sat=1.000
（峰时信息被毁 peakΔt=−1998）；R4/R5/R8 三对全部
`BASELINE_ZEROING_ARTIFACT=TRUE`（归一比 0.70/1.00/1.33 虚高，
伴随 zero=0.64/0.98/0.91）。

### Candidate A（薄幅值口）
- 全场景零地板/零饱和（port 级）；三对 retention **精确=1.0**
  （D_port_norm ≡ D_boundary_norm：0.428/0.453/0.922），无假象——
  **线性薄接口是保真基准**。
- 但喂进现 L1 即复演支路 W 错位：L1 把幅值当速率 → L1_nonzero_frac
  =1.00（常燃），R2/R3/R6 L1 上钳 10 触顶（饱和被推到下游）。
  ⇒ A 的自洽性**条件于 L1 端口改语义**（第 8 问）。

### Candidate B（显式速率口）
- 与现 L1 语义一致（半波留给 L1）；符号保留 neg_decay=1.00（降温可表达，
  L1 半波按 BIO 合同丢弃冷侧——cool 支路职责，非缺陷）。
- **R4 核心测试**：同峰值不同上升速度对 D_port_norm=0.678 >
  边界 0.428（真速率敏感，D_port_abs=3.35e-02 实值非假象，zero=0）。
- R5 隐藏历史分叉在速率像中强表达（0.991）；peakΔt=+1（onset 响应）。
- **结构自洽且不动 L1**：Y_B → 𝒫_Ṫ（声明的单步寄存器，SkinPatch 先例）
  → u̇ → 现 L1。

### Candidate C（D 层适应态）
- corr(u_B,u_C)@R3=0.62（τ_a=200）——**非 B 的纯重复**（相关中等）；
  但按 Q1 卡 2/3，适应态的生理载体在受体（L1）内部，置于 D 层=搬错层，
  且与支路 P 的 SkinPatch 差分职责部分重叠。
- 判定：`CANDIDATE_C = REJECTED_AT_D_LAYER`（非因数值差——因层位；
  其机制本体登记为未来 L1 内部候选，属 G0/L1 接口阶段，非本轮）。

### Mathematical control（asinh 宽域压缩）
- 三对 D_port_norm=0.370/0.400/0.734 **全部低于薄线性 A**——
  "动态范围好看"的压缩函数反而丢区分度。对照结论：**复杂压缩不构成
  改进方向，§32 红线（v2 更薄）被数值面证实**。不升级为候选。

## 三、五决策门（§21）

| 门 | 判定 | 依据 |
|---|---|---|
| Gate A：D_i 应为无状态薄接口？ | **YES** | A 保真基准（retention≡1.0 无假象）+ Q1 表 + M 对照反证 |
| Gate B：L1 应承担速率提取？ | **YES**（应然） | Q1 卡 2：速率敏感=幅值换能+受体内适应态的涌现；现状工程先例在 Boundary（SkinPatch） |
| Gate C：现 ThermalDeltaNeuron 已实现该职责？ | **PARTIAL** | 半波+增益有；微分/适应无（runtime 无态，审计 §五） |
| Gate D：需要独立动态传感器态 X_D？ | **NOT_REQUIRED（D 层）** | C 被层位否决；适应态归 L1 未来工作（登记非绕开） |
| Gate E：G0 端口须改名/改语义？ | **PORT_CHANGE_REQUIRED**（本轮不执行） | 第 8 问；§22 出口 |

## 四、终裁（§26）

十项 PASS 条件逐条：①职责无重叠（矩阵+指派完成，重叠项全部定位并
指派）✓ ②幅值/速率端口语义明确（U_T/U_Ṫ 已定义并逐支路判定）✓
③量纲可追踪（S_in/S_out+D1-D3 登记）✓ ④至少一个结构自洽方案
（**Candidate B 链路不动 L1 即自洽**；A+L1 改语义为目标态）✓
⑤候选不依赖 World 隐藏态（只消费 Y_B）✓ ⑥replay 仍成立（候选为
纯边界轨迹消费者；WT0 replay 本轮复跑 PASS）✓ ⑦不依赖 legacy
floor/ceiling 预筛（A/B/C 均无 clip/死区）✓ ⑧未以 occurrence 调参
（本轮零 occurrence 指标）✓ ⑨未冻结 World-v1 专用参数（只冻结参数
角色/量纲/合法域）✓ ⑩G0 端口改动已登记非绕开
（G0_PORT_CONTRACT_CHANGE_REQUIRED）✓

```text
T1-A 终裁 = T1A_ARCHITECTURE_READY
附带登记：G0_PORT_CONTRACT_CHANGE_REQUIRED（留 T1-B/G0 回接阶段执行）
         LAYER_CATEGORY_CONFLICT（TSS vs nexus 的 L1 归类，T1-B 前须裁定）
         CANDIDATE_C = REJECTED_AT_D_LAYER（机制保留为未来 L1 内部候选）
```

按 §31：下一轮 **W1（World v2 建设）**；最终转导标定与候选择一属 T1-B
（World v1 reference + v2 calibration + v2 held-out，§20 纪律）。

## 五、§29 冻结回归复跑（本轮收口）

WT0 四脚本（positive_control / boundary_replay / dose_attack /
cross_pair_matrix）全部 exit 0 复现；test_regression 21/21 exit 0；
tss version_pairing PASS；tss fast 43 passed。母体 nexus_v1/tss 零改动
（本轮仅新增 research/transduction_v2/ 与文档）。

## 复现入口

```bash
PYTHONIOENCODING=utf-8 python research/transduction_v2/prototypes/t1a_diagnostic_replay.py
PYTHONIOENCODING=utf-8 python research/wt0/wt0_positive_control.py
PYTHONIOENCODING=utf-8 python research/wt0/wt0_boundary_replay.py
PYTHONIOENCODING=utf-8 python research/wt0/wt0_dose_attack.py
PYTHONIOENCODING=utf-8 python research/wt0/wt0_cross_pair_matrix.py
PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.test_regression
PYTHONIOENCODING=utf-8 python -m pytest tss/tests -m fast -q
```
