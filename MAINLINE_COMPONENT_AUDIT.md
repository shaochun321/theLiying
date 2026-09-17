# MAINLINE_COMPONENT_AUDIT — 旧主线考古与结构剥离（Phase M0）

日期：2026-09-18
依据：《TSS 收尾与主线重启》§1/§3/§4（M0 不改动力学，只归类）。
路径修正：方案假设的 `nexus_v1/generators/` 已于 2026-09-06 整体迁至 `tss/generators/`（纯移动零改名，映射见 `tss/README.md`）；`world/` 目录不存在，World 实现在 `nexus_v1/components/`。本审计按实际路径执行。

**核心问题：旧 P2 中哪些是项目本体，哪些只是温感实验实例？**
**归类纪律：禁止因"曾成功运行"把 THERMAL_SPECIFIC 升级为 GENERIC。**

---

## 一、七类归类总表

类别：A GENERIC_PHYSICAL_PRIMITIVE / B GENERIC_GENERATOR_CORE / C GENERIC_INTERFACE / D THERMAL_SPECIFIC / E WORLD_INSTANCE_SPECIFIC / F LEGACY_RELATION / G OBSERVATION_ONLY

| 组件 | 位置 | 类 | 依据 |
|---|---|---|---|
| Capacitor / MOSFET / Memristor / PowerRail | `nexus_v1/components/semiconductor.py` | A | 四大原语，全项目地基，无域参数 |
| Neuron / NeuronConfig | `nexus_v1/components/neuron.py` | A | 单一神经元模型，配置分化 |
| SynapticBundle | `nexus_v1/circuit/bundle.py` | A | 单一连接模型 |
| 十神经元 ensemble 结构（10×Neuron+bundles+collector 拓扑） | `nexus_v1/circuit/variant_adapter.py:141`（_Q_N_ENSEMBLE=10）+ `:1702 _init_quantum_thermal_pathways` | B（结构）/ D（实例化） | 结构合同是通用生成元核心；**当前唯一实例被温感参数化**（32 Fibonacci 球面点×warm/cool，L1=ThermalDeltaNeuron）。按纪律不因运行成功升 GENERIC——通用性待 G1 新输入合同检验 |
| BaseGenerator（G0 可寻址句柄） | `tss/generators/base_generator.py:95` | B | wrap 抽取不新建对象；接口 𝒢_i:(u_i,z_i)→(ż_i,ξ_i^occ)；feed/feed_from_skin 双入口（DEG-021 互锁） |
| OccurrenceClosure / Occurrence（χ_i^k） | `tss/generators/occurrence.py:209/:127` | B | trigger/exit/rearm 三相状态机，域无关；阈值 θ_up/θ_down/rearm 的**当前数值**是温感标定（EXP-P2A1b3-CALIBRATED）——结构 B、参数 D |
| GeneratorTrajectory | `tss/generators/trajectory.py:78` | G | 只读物理账本（自述 TYPE:INFRA 不融合进 Occurrence）；字段 `q_skin_raw` 是温感残留命名 |
| collector | BaseGenerator.collector（Neuron 实例） | B | 角色定义于结构合同 |
| D_i 转导合同（typed physical transduction contract） | 概念层（方案 §10） | C | 接口 𝒟_i: X_local^world→u_i；**目前无域无关实现** |
| D_i^sim 温感实现（κ_i） | `tss/generators/skin_transduction.py:74`（TransductionConfig/REFERENCE_TRANSDUCTION_CONFIG，κ_i≈0.0013759 由 T-STP-6/7/8 反解） | D | **LEGACY_TRANSDUCTION_INSTANCE**——D_i 的唯一 legacy 实现 |
| 上游换能层（ThermalDeltaNeuron + HC） | `nexus_v1/somatosensory/transducer_neurons.py:252` | D | 温度差换能神经元 |
| ThermalFieldGraph / ThermalCell / ThermalLink | `nexus_v1/components/dynamic_thermal_field.py:227/:165/:190` | E | normalized World 本体（W1）；每节点 1 动态变量；结构上是通用 RC 场但以温度物理命名与参数化，资格未证明为通用 |
| SkinThermalState / ThermalContact / couple_world_skin_step | `nexus_v1/components/skin_thermal_contact.py:138/:188/:273` | D | 世界-皮肤热交换边界（P0） |
| q_skin / 三点皮肤 | `nexus_v1/components/skin_three_point.py:77` | D | P2-A2 皮肤实例（3 节点） |
| InstantFieldWorld（World/HeatSource/SkinPatch/Body） | `nexus_v1/components/world.py:500/:52/:110/:298` | E | 瞬时查询场 T=F(x)，场自身 0 动态变量 |
| DynamicHeatSource / ThermalFieldLocator | `nexus_v1/components/thermal_source_coupling.py:122/:82` | E | W2A 守恒注入 |
| JointThermalStepPlan / JointThermalTrajectory | `nexus_v1/components/joint_thermal_step_plan.py:169/:696` | E | P1 联合守恒调度 |
| thermal_membrane / thermal_mouth / thermal_transport_plan / ordered_excess_thermal_energy_link | `nexus_v1/components/` | D | 母体温感器官（organism 侧，21 项回归覆盖） |
| r_prec 家族（T1/T2/T3/plastic） | `tss/relations/temporal_r_prec*.py` | F | TSS 冻结 findings；主线视角 legacy relation |
| r_part / r_ρ（升格未完成） | `tss/relations/ratio_r_part*.py` | F | 同上 |
| ρ_{A≺B}^fast 关系实例 | `tss/relations/relation_occurrence.py:70` | F | ≠ r_ρ（对照矩阵拆分，见 P2_TSS_RECONCILIATION_DRAFT） |
| site_selection（T0 ξ^occ 选点） | `tss/relations/site_selection.py` | D | 自述"温感轨最小支撑" |
| trajectory / occurrence_tap / probes / census / kernel_ledger | tss 各处 | G | 只读观测/账本 |

## 二、§1 四状态正式登记

| 对象 | 新状态 | 处置 |
|---|---|---|
| 十神经元 BaseGenerator（结构合同+句柄） | `RETAINED_CORE` | 不改；G1 阶段用新输入合同检验结构稳定性 |
| OccurrenceClosure / trigger-exit-rearm | `RETAINED_CORE` | 不改；阈值数值标记为温感标定，重标定属 T0/G1 |
| GeneratorTrajectory / 物理账本 | `RETAINED_CORE` | 不改；`q_skin_raw` 字段名列入未来通用化清单（本轮不动） |
| ThermalFieldGraph / 热源 / 热皮肤 | `LEGACY_WORLD_INSTANCE` | **登记层剥离**：状态标签在此登记；物理文件留在 `nexus_v1/components/`（母体组件、21 项回归覆盖，物理移动违反不改母体红线；方案 §12 亦要求不得删除）。用途=回归样本/负控制/World v1-v2 对照 |
| 温感 D_i^sim（skin_transduction κ_i + ThermalDeltaNeuron 链） | `LEGACY_TRANSDUCTION_INSTANCE` | 同上登记层剥离；是 𝒟_i 合同的 legacy 实现，不再承担"默认输入"资格 |
| 旧 normalized World（dynamic_thermal_field） | `REQUALIFICATION_REQUIRED` → 本轮 W0 实测 | 见 `WORLD_V1_REQUALIFICATION_REPORT.md` |
| TSS occurrence→relation | `FROZEN_RELATION_SUBSTRATE` | 见 `tss/TSS_FREEZE_2026-09-18.md` |
| TSS C1 | `FROZEN_RECURSION_RESULT`（PASS ≠ new generator） | 同上 |
| A8-v2 / F1 | `FROZEN_QUALIFICATION_METHOD` / `REFERENCE_A8_POSITIVE_CONTROL` | 同上 §三 |

**撤销的资格**：旧 World 不再持有 `WORLD_QUALIFIED`；改记 `LEGACY_WORLD_V1`，历史资格仅为"曾足以产生一个局部真实发生"（真实记录=审查点 1：`nexus_v1/tests/test_world_physical_qualification_review.py` T-WQR-1~3 + `cell-cell/工作报告/世界物理资格审查_2026-07-17.md` §5"带债务通过/单点局部发生足够/多源区分不足"；方案标签 `QUALIFIED_FOR_OLD_P2A_LOCAL_OCCURRENCE` 为本轮新登记名，仓库原文无此字面量）。不得由此推导适合规模研究/关系生成/多源区分/空间生成/长期组织/真实神经复杂度。

## 三、M1 前置核验（不改代码，只核验存在性与可运行性）

| 核验项 | 结果 | 证据 |
|---|---|---|
| 旧实现仍存在 | ✓ | `tss/generators/base_generator.py:95`（ensemble/bundles/collector/closure/trajectory 齐备）；母体原址 `variant_adapter.py:1702` |
| 接口仍完整 | ✓ | feed(dT_raw,dt) / feed_from_skin(q_skin,cfg,dt) / tick()→Optional[Occurrence]；wrap_base_generator 按 (site_index,polarity) 抽取 |
| 是否被 TSS 修改污染 | 未污染 | `tss/generators/` 最后改动 f08fff7（2026-09-08，DEG-024 量纲修复），之后零改动；nexus_v1 对 tss 零 import（单向依赖保持） |
| 测试仍可运行 | ✓ | EXT-2 全量复验（2026-09-10）222 passed+2 xfailed；G0 相关（test_p2a_generator_core 20 项、test_basegen_thermal_t0/t1/t3、test_deg021 等）全绿；本轮抽测见收口记录 |

**结论：G0 无需重定义，代码与冻结文档无冲突。**

## 四、§27 前两问的回答

1. **真正通用的**：四大原语、Neuron/SynapticBundle、十神经元结构合同（拓扑+closure 状态机+trajectory 账本+𝒢_i 接口）、C1 适配器机制（结构层）、H_τ/Θ 物理机制（结构层）。
2. **只是温感实例的**：κ_i 转导（skin_transduction）、ThermalDeltaNeuron/HC 换能链、三点皮肤与热接触边界、ThermalFieldGraph 的温度参数化、InstantFieldWorld 全部、closure 阈值的当前数值、site_selection 选点、`q_skin_raw` 等命名残留。
   **双重性组件**（结构 B/参数 D）：十神经元实例、OccurrenceClosure 阈值——结构保留，参数资格随 T0/G1 重检。
