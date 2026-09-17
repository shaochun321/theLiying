# TSS_FREEZE_2026-09-18 — TSS 研究轨正式冻结登记

依据：`cell-cell/交叉比对/TSS 收尾与主线重启：World 重资格化及旧温感实例剥离执行方案.md` §0/§2（理论侧总裁定）。
本文档只登记事实。证据指针指向 `tss/QUALIFICATION_LEDGER.md`（下称 QL）、`tss/EXPERIMENT_MANIFEST.md`、工作报告与 commit。

```text
TSS_RESEARCH = FREEZE          （此后仅允许 bugfix / 回归修复；禁止新增理论模块）
K-07         = DO_NOT_START
F3/F5        = FROZEN
F1_A8v2_PHYSICALLY_VALIDATED = CONDITIONAL（用途=生成资格审计参考实例）
```

---

## 一、冻结清单（逐项 + 证据指针）

| # | 冻结对象 | 状态 | 证据 |
|---|---|---|---|
| 1 | Occurrence / Entry | RETAINED_CORE | `tss/generators/occurrence.py`（OccurrenceClosure，ARMED/ACTIVE/REFRACTORY，θ_up=0.01/θ_down=0.001/rearm=500=EXP-P2A1b3-CALIBRATED）；`tss/relations/entry_gate.py`（PhysicalEntryGate，TSS-R1b 10/10）；DEG-018 双时钟=DESIGN_DECISION_QUANTIFIED（QL E0-fix 段） |
| 2 | H_τ 物理历史保持核 | RETAINED_CORE | QL M1：T-R1C 8/8（db92165）；可读窗 723 步（解析=实测）；τ_h=600（TSS-3a 裁定） |
| 3 | Θ 统一比较器 | RETAINED_CORE | QL M2：T-TH 9/9（dafba5f）；C-02=全物理 MOSFET（用户裁定 2026-09-06）；阻断 0.2146 vs 0.0 |
| 4 | relation re-eventization（关系再事件化） | RETAINED_CORE | `relation_occurrence.py`（RelationOccurrence/Finalizer）+ `relation_event_adapter.py`（C=7.920427e-07 反解，EXP-C1-01，18ec583） |
| 5 | C1 engineering recursion | FROZEN_RECURSION_RESULT: **PASS** | QL C1/EXT-2：test_c1_coupling 12/12（7f629fa + T-C1-6b）；§11 判据链 真实发生@389→r@701/749→c_ro@[749]→下游 0.4362 vs 阻断 0.0 |
| 6 | C1 reconstructibility（父层同类可重构） | FROZEN: **A8_NOT_MET 稳定复现** | T-C1-6b：14 Δt₂∈[1,800] 同型 H_τ+Θ 栈重构残差 bit-exact 0.0（外部 5.12e-15 仅浮点）；该测试 PASS 的语义=NOT_MET 复现，非资格 PASS |
| 7 | amplitude loss（adapter 信息压缩） | FROZEN（设计现状，非 bug） | `_diag_c1_parent_amplitude_information_loss` exit 0：49 越阈幅度组合输出全等 0.4340310902405273；禁改 adapter 阈值保留幅度（QL EXT-2） |
| 8 | cross-occurrence reconstruction | FROZEN | `_diag_c1_cross_occurrence_history_reconstruction` exit 0：8 gap 增强 ×1.0004~×1.1995 全复现，解析 H_τ 叠加残差 9.81e-15；**no independent persistent organization variable established** |
| 9 | A8-v1 | **NOT_MET**（RULING，EXT-2） | QL EXT-2 A8 段；机器可读常量 `tss/relations/coupling_contract.py` C1_* |
| 10 | A8-v2 criterion | FROZEN_QUALIFICATION_METHOD（草案已定义） | 第二轮定义（R1/R2 切分 + M3/M4 附加条款防计数器，c63b17c）；采纳状态=按需调用的 qualification test（见 §三） |
| 11 | F1 physical candidate | **F1_A8v2_PHYSICALLY_VALIDATED = CONDITIONAL** | 第四轮六门 M1-M5+M5-P 全 PASS（a312190）；fingerprint `bdbdb0305c191e94`；条件=canonical Scale-B 裁定 + dt 数值建模声明；报告 `cell-cell/工作报告/F1_A8v2最小物理闭合复审工作报告_2026-09-18.md` |
| 12 | known LIM XFAIL | FROZEN（禁调阈值） | LIM-RPREC-READOUT-001：压缩 297×=8.3××35.8×，效应上限 0.117%<1%；EXP-LIM-01 多束方向定量否证（N-不变/N*≈132）；2 xfail 保持（QL LIM 段） |
| 13 | 全部阴性结果 | FROZEN | A8 第一轮 NO_CANDIDATE_FOUND_IN_TESTED_TOPOLOGIES（b01444d，"缺恒流偏置"已勘误）；Scale-A=M1-only/NOT_REACHED；r_ρ 升格未完成（T3-B/T3-C2 原型止步）；K-06 BLOCKED（R-E0-3 未裁定）；A9 runtime relation-instance lineage GAP（`_diag_c1_runtime_lineage_collision`）；Λ 资格降格（Y_broad^cut≡Y_local，TSS-2b）；E^↑ R1a 降格为参考检测器（entry_boundary.py→archive） |

## 二、两条不等式（显式登记，永久有效）

```text
C1 PASS                    ≠  new generator
F1 physical validation     ≠  A8 MET  ≠  new generator
```

当前总状态（沿 QL EXT-2）：`C1 engineering recursion: PASS；new-generator qualification: NOT_QUALIFIED；K-06 organization qualification: BLOCKED`。

## 三、A8-v2 与 F1 的新位置

- **A8-v2** = qualification test：不再是建设任务；仅当某候选声称"新的生成深度"时才调用。方法冻结于第二轮定义 + 第四轮 M5-P 扩展（六门制）。
- **F1** = `REFERENCE_A8_POSITIVE_CONTROL`：用途=验证未来资格测试没有失效（正向对照）。**不自动植入** G0 / relation layer / World / Shadow / Xin。代码与数据保留于 `research/A8_state_audit/`（含 F1_FEEDBACK_POWER_CONTRACT.md、NEXUS_SOURCE_MANIFEST.json）。

## 四、逻辑四分类登记表（替代物理目录重组）

> 处置说明：方案 §2 要求目录转为 `tss/core|qualification|findings|archive`。
> 该重组与 2026-09-06 已裁定并写入 `tss/tests/conftest.py`/`tss/README.md` 的
> "不搬目录"约定直接冲突（影响面实测：161 条绝对 import + 36 相对 import +
> manifest/QL 26 处路径命令 + VERSION_PAIRING + research/ 6 脚本），且方案 §21
> 自身禁止"为架构整洁强行统一"。故降级为**逻辑分类标签**，物理目录不动。

**CORE（物理机制，冻结后仍被消费）**

| 文件 | 定位 |
|---|---|
| generators/occurrence.py | χ 闭合状态机（P2-A 核心） |
| generators/base_generator.py | 十神经元 G0 可寻址句柄（P2-A 核心） |
| generators/trajectory.py | 生成元轨迹账本 |
| generators/natural_unit.py | 单 occurrence 自然化接口（χ≠𝔫） |
| generators/occurrence_identity.py | D1 实例身份查找表 |
| generators/occurrence_tap.py | 只读 occurrence 观察适配器 |
| generators/input_envelope.py | 输入包络扫描工具 |
| relations/entry_gate.py | E^↑ 物理门（R1b） |
| relations/history_kernel.py | H_τ（M1） |
| relations/theta_comparator.py | Θ（M2） |
| relations/relation_event_adapter.py | C1 关系事件→脉冲适配器 |
| relations/relation_occurrence.py | 在线 D2 关系实例闭合 / R1 时间投影 |
| relations/r1_structure.py | R1 最小结构块 |
| relations/boundary_process.py | 实时发生边界端口（R0） |

**QUALIFICATION（资格审计/契约/账本，只读不进物理路径）**

| 文件 | 定位 |
|---|---|
| relations/coupling_contract.py | C0/C1 类型契约 + C1_* 状态常量 |
| relations/generator_contract.py | TSS-0 有类型接口映射 |
| relations/selection_contract.py | S0-a 选择资格与反硬编码边界 |
| relations/census.py | 关系层独立账本 |
| relations/probes.py | 通用探针 + frozen 权重检查 |
| events/event_core_contract.py | E0 事件核六分量审计契约 |
| events/kernel_ledger.py | ℒ 资源账本 + K 持久存储承载 |
| events/event_support.py | 关系实例谱系绑定基础设施 |

**FINDINGS（承载已冻结结论/阴性结果的实验结构）**

| 文件 | 冻结结论 |
|---|---|
| relations/temporal_r_prec.py /_t2 /_t3 | r≺ T1/T2/T3 边 |
| relations/temporal_r_prec_plastic.py | P2-B1 学习资格（LIM XFAIL 载体） |
| relations/ratio_r_part.py /_ternary | r_part 原型；**r_ρ 升格未完成** |
| relations/r2_fork.py | P2-C1F 共同源分叉 R2 |
| relations/generator_sigma.py | Σ_support 原型（longrun 守卫） |
| relations/generator_lambda.py | Λ 资格已降格（TSS-2b：仅 Σ 嵌套支撑） |
| relations/activation_cloud.py | TSS-A0 锚定契约 |
| relations/selection_pool.py | S0-b 候选池（未接入竞争） |
| relations/site_selection.py | T0 冻结 ξ^occ 选点（**温感轨支撑**） |
| generators/skin_transduction.py | **LEGACY_TRANSDUCTION_INSTANCE**（κ_i 温感换能，D_i 的 legacy 实现） |

**ARCHIVE（降格/被取代）**

| 文件 | 原因 |
|---|---|
| relations/entry_boundary.py | R1a 判定规则版，被 entry_gate.py 物理门取代，保留为参考检测器 |

## 五、暂停清单（方案 §25，回接完成前不启动）

Xin / Shadow / TOPRXin / 运动势 / K-07 / K-06 / F3/F5 / 正式空间生成元 / 高层组织命名；亦不扩大温感系统。

## 六、TSS 回接条件（方案 §19）

仅当主线 World、D_i、G0、SCALE-0 完成最低资格后回接。正式接口 `𝒢_i → ξ_i^occ → TSS`；TSS 不接 raw World / raw skin / raw membrane voltage，默认入口 = qualified physical occurrence。旧 P2 与 TSS 的机制对应见 `tss/P2_TSS_RECONCILIATION_DRAFT.md`。
