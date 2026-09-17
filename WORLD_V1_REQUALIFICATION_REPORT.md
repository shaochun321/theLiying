# WORLD_V1_REQUALIFICATION_REPORT — World v1 重资格化测量（Phase W0）

日期：2026-09-18
依据：《TSS 收尾与主线重启》§5-§9/§26-§28。
脚本：`research/world_requalification/{w0_structure_audit,w0e_history_discrimination}.py`
数据：`research/world_requalification/data/{w0_structure.json,w0e_history.json,w0e_traj_scale*.csv}`

**状态变更（§5）**：旧 World 撤销 `WORLD_QUALIFIED`，改记 `LEGACY_WORLD_V1`。
历史资格仅保留为"曾足以产生一个局部真实发生"（本轮登记名
`QUALIFIED_FOR_OLD_P2A_LOCAL_OCCURRENCE`；真实记录 = 审查点 1：
T-WQR-1~3 + `cell-cell/工作报告/世界物理资格审查_2026-07-17.md` §5
"带债务通过 / 对单点局部发生足够 / 对多源区分不足"）。

---

## 一、测量对象

| World | 实现 | M0 状态 |
|---|---|---|
| normalized ThermalFieldGraph | `nexus_v1/components/dynamic_thermal_field.py`；实测实例 = P2-A 三点皮肤（TEST 档 κ=0.05, r_leak=200） | REQUALIFICATION_REQUIRED（本报告对象） |
| InstantFieldWorld | `nexus_v1/components/world.py`（T=F(x) 瞬时查询） | LEGACY_WORLD_INSTANCE（仅结构枚举） |

## 二、W0-A 自由度

- **normalized 三点皮肤：N_dyn = 3**（每节点唯一动态标量 = Capacitor.charge），脉冲后活跃 3/3。
- InstantFieldWorld：**场自身动态变量 = 0**（瞬时查询函数）；代理状态 ≈113 标量（8 源×7 + world 4 + Body 17 + 12 patch×3），但源/身体/皮肤是代理对象，不构成场。
- **判定：方案 §6 的怀疑属实——当前 World 本质上是"少数节点 + 单变量 + 近线性扩散"。** 正式登记。

## 三、W0-B 局部相互作用

- normalized：中间节点对两端注入均有响应（13.59/13.59，多过程共同作用 ✓）；耦合为线性扩散 → **weakly coupled linear field**。
- InstantFieldWorld：patch 间零相互作用（各 patch 只读 T=F(x) + 自身 RC）→ **independent channel**。

## 四、W0-C 时间尺度

实测脉冲响应谱（三点，TEST 档）：τ = {6.0, 17.8, 200.0} 步，与解析
{6.5, 18.2, 200}（链式 Laplacian 特征值 ×κ + leak）吻合。
**但独立参数只有 2 个（κ, r_leak），且默认档绑定 r_leak=10/κ ⇒ 实际独立
时间尺度 = 1（全谱由 κ 单参数派生）。** normalized 生产档 τ_ref=357143
步（远超一切实验时长，实验全部用 TEST 档）。InstantFieldWorld：SkinPatch
单 RC τ=5000 步。

```text
MULTISCALE_SUPPORT = NOT_ESTABLISHED
```

## 五、W0-D 非线性

- 叠加残差 max 4.44e-14（机器精度）⇒ **线性**。
- 3 组初态终态数 = 1 ⇒ **单吸引子**（ambient）。
- 1e-9 扰动 500 步后衰减至 2.74e-11 ⇒ **无敏感依赖**。
- 分类：`线性 / 单吸引子 / 无敏感依赖`。按 §18 纪律只登记，不造混沌。

## 六、W0-E 可区分世界历史（核心门）

三历史等能量（E=scale×300，空间分布/时序差异，非幅值差）：
Γ_A 静止源 / Γ_B 移动源扫过 / Γ_C 双脉冲时序。support = D_i^sim 转导输出
u_i（REFERENCE_TRANSDUCTION_CONFIG，标定域 T∈[43.65,61.83]）。
度量契约见脚本 docstring（先冻结后实验）。

| scale | 对 | D̂_world | D̂_supp(clip) | ratio | 判定 |
|---|---|---|---|---|---|
| 1.0（域内，T 峰 61.8） | A-B | 0.2013 | 1.1522 | 5.72 | PRESERVED |
| 1.0 | A-C | 0.8617 | 1.3606 | 1.58 | PRESERVED |
| 1.0 | B-C | 0.8604 | 1.3089 | 1.52 | PRESERVED |
| 0.1（域外，T 峰 6.2） | A-B | 0.2013 | **0.0000** | 0.000 | **WORLD_TO_SUPPORT_COLLAPSE** |
| 0.1 | A-C | 0.8617 | **0.0000** | 0.000 | **WORLD_TO_SUPPORT_COLLAPSE** |
| 0.1 | B-C | 0.8604 | **0.0000** | 0.000 | **WORLD_TO_SUPPORT_COLLAPSE** |

线性读出对照（无 clip）：域内 ratio≈0.54（κ 线性压缩、区分保留）；
域外 ratio≈0.046（工作点偏置压掉 ~95% 区分度）。

**结论：塌缩不发生在场——场是线性的、忠实保留全部历史区分
（D̂_world 三对均 >0.1）。塌缩发生在 D_i^sim 转导层的窄工作窗：窗内
甚至因 clip 非线性放大区分（ratio>1），窗外世界历史对下游完全不可见
（support 恒 0）。** 这把"World 不合格"的问题重新定位为
"World 过于简单（贫瘠但忠实）+ 转导窗过窄（丰富历史被裁切）"两件事。

## 七、§28 停止条件评估

| 要求 | 实测 | 满足? |
|---|---|---|
| 产生丰富可区分局部过程 | 3 自由度、线性、单吸引子——历史可区分但过程种类贫乏 | ✗ |
| 支持多时间尺度 | 单参数派生谱，MULTISCALE_SUPPORT=NOT_ESTABLISHED | ✗ |
| 支持不同历史 | ✓（域内 PRESERVED；场层全保留） | ✓ |
| 支持规模测试 | 3 节点实例；结构可扩展但未证明 | 未证明 |

```text
WORLD_V2 = REQUIRED（W0 判定成立）
```

W1 设计要点（本轮不建设，仅登记 W0 证据指向）：缺口按 §7 排序 =
①独立可变局部自由度数量 ②独立时间尺度（解除 r_leak=10/κ 绑定 +
异质 κ/C）③外部驱动复杂性；**不需要**先加多模态物理场（§7：单一
温度场未证明不足——当前不足在自由度/尺度/驱动，不在物理量种类）；
不需要混沌（§18）。转导窗问题属 Phase T0（𝒟_i 合同重资格化），
不是 World v2 的职责。

## 八、§27 五问回答

1. **旧 P2 中哪些组件真正通用？** 四大原语、Neuron/SynapticBundle、十神经元结构合同（拓扑+OccurrenceClosure 状态机+trajectory 账本+𝒢_i 接口）、C1 适配器/H_τ/Θ 的物理机制层。（M0 表一）
2. **哪些只是温感实例？** κ_i 转导（skin_transduction）、ThermalDeltaNeuron/HC 换能链、三点皮肤与热接触边界、ThermalFieldGraph 温度参数化、InstantFieldWorld 全部、closure 阈值当前数值、site_selection 选点。（M0 表一/表二）
3. **旧 World 有多少有效动态自由度？** normalized 实用实例 **3**（每节点 1 标量）；InstantFieldWorld 场自身 **0**（代理 ~113）。
4. **它在哪一级把不同世界历史压平？** **不在场级**（场线性忠实，D̂_world 全对 >0.1）；**在 D_i^sim 转导级**——工作窗 [43.65,61.83] 之外 support 恒 0（clip 死区 + 工作点偏置），窗内反而放大。W0-E 双幅度组实测。
5. **TSS 与旧 P2-B/P2-C 重叠多少？** 见 `tss/P2_TSS_RECONCILIATION_DRAFT.md`：ξ_i^occ/χ_i^k 为 SAME（同一实现）；r_prec^τ 与 H_τ+Θ 为 COEXIST（不同机制层级）；r_ρ 未升格（NOT_COVERED）；P2-C(R2) 与 C1 为 DIFFERENT（分叉生成 vs 递归耦合）；relation qualification ⊂ A8-v2（EXTENSION）。

## 九、测试结果（本轮收口）

母体 nexus_v1/ 与 tss/ 代码零改动（仅新增 research/ 观测脚本与文档）；
回归见收口记录（BACKLOG F0+M0+W0 行）。

## 复现入口

```bash
cd /j/cell-cc
PYTHONIOENCODING=utf-8 python research/world_requalification/w0_structure_audit.py
PYTHONIOENCODING=utf-8 python research/world_requalification/w0e_history_discrimination.py
```
