# TSS 实验清单 (EXPERIMENT MANIFEST)

> 建立于 2026-09-06（外部实测反馈清单 §5 的诉求）。**"pytest 全绿"≠"全部
> 实验体系通过"**——本清单是完整边界：pytest 收集的 test_*、不被收集的
> exp_*/_diag_*/_probe_* 全部在册。格式用 md 表（项目惯例；反馈建议的
> yaml 语义等价）。
>
> 时长为两列（2026-09-08 起，外部评判《TSS (3) 清单》§7）：**参考机**
> （本仓库参考机近似值）与**外部复现**（外部评判独立机器实测，2026-09-07
> 一轮）。机器/Python 版本/并行负载影响很大，两列都是 representative，
> 不作为判定依据；"—"表示该轮未单独计时。
>
> 统一入口：仓库根目录 `python -m tss.tests.<模块名>`（`-m` 为规范方式；
> 直接路径运行为兼容尽力而为）。pytest 分层：`pytest tss/tests -m "not longrun"`。
> TSS ↔ nexus_v1 版本配对声明：`tss/VERSION_PAIRING.json`（fail-fast 测试
> `test_version_pairing`）。

## 一、资格套件（required——冻结资格依赖这些）

| 模块 | 资格归属 | marker | 入口 | 参考机 | 外部复现 | 状态 |
|---|---|---|---|---|---|---|
| test_entry_gate | TSS-R1b ℰ↑ 物理门(10项) | longrun | run() / pytest | ~10min | 288s | PASS |
| test_history_kernel | TSS-R1c/M1 H_τ (T-R1C-1~8) | longrun | main() / pytest | ~2min | 281s | PASS |
| test_theta_unified | TSS-M2 统一Θ (T-TH-1~9) | longrun | main() / pytest | ~3min | — | PASS |
| test_c0_relation_order_audit | C0 目标对审计(EXP-C0-02) | longrun | run() / pytest | ~8min | 完整跑通 | PASS(25对合格) |
| exp_C1_adapter_calibration | C1 适配器标定(EXP-C1-01) | 不被pytest收集 | run() | ~5s | — | PASS |
| test_c1_coupling | C1 c_ro 资格(T-C1-1~11 含 6a/6b/9a，共12项) | longrun | main() / pytest | ~10min(10种子) | 497s | Engineering PASS; A8 NOT_MET; A9-runtime GAP; not generator-qualified（EXT-2 复审 2026-09-10；6b PASS 语义=A8_NOT_MET 复现） |
| test_boundary_process | p_α 边界端口 | longrun | run() / pytest | ~7min | 530s | PASS |
| test_occurrence_identity | D1 实例身份 | fast | pytest | ~5s | — | PASS |
| test_e0_event_type_audit | E0 类型审计(T-E0-1~4 含 EXP-E0-01 复放地板) | integration | main() / pytest | ~1min | — | PASS |
| test_e0_kernel_ledger | E0 修复:ℒ账本+K快照(T-KL-1~5 含跨账本守恒) | fast | main() / pytest | ~30s | — | PASS |
| test_deg021_dual_drive_interlock | DEG-021 双驱动互锁(T-DD-1~3) | integration | main() / pytest | ~1min | 3/3 PASS(补母体标记后) | PASS |

注：C0 的 pytest wrapper 于 2026-09-08 补齐（评判 §11 方案A——此前
pytest 收集为 0 项 exit 5，仅 run() 入口覆盖）。

## 二、机制/契约测试（required，快速层）

| 模块 | marker | 参考机 | 外部复现 | 状态 |
|---|---|---|---|---|
| test_generator_contract | fast | 秒级 | — | PASS |
| test_event_support_binding | fast | 秒级 | — | PASS |
| test_natural_unit / test_skin_transduction | fast | 秒级 | — | PASS |
| test_occurrence_tap / test_selection_contract / test_selection_pool(_seed) | fast | 秒级 | — | PASS |
| test_version_pairing | integration | ~30s | — | PASS(TSS↔nexus_v1 配对 fail-fast，2026-09-08新增) |
| test_basegen_thermal_t0/t1/t3_ratio | integration | <60s | — | PASS |
| test_r1_structure / test_tss2a_scale_audit | integration | <60s | — | PASS |

## 三、历史原型与长程验证（长时层）

| 模块 | marker | 参考机 | 外部复现 | 状态 |
|---|---|---|---|---|
| test_r2_fork | longrun | ~3.5min(2026-09-10 全量复验实测 r2f_3=209s) | 182s/121.5s | PASS(marker 2026-09-10 integration→longrun：外部连续两轮实测超 integration ≲60s 定义，EXT-2 清单裁定并被参考机实测追认；仅 marker 修复不改行为) |
| test_generator_lambda | longrun | ~2min | 126s | PASS(λ 降格保留资产守卫；2026-09-08 自 fast 移出——评判 §4：实测分钟级违反 fast 定义) |
| test_generator_sigma | longrun | ~3min | 191s | PASS(σ 同上) |
| test_entry_boundary | longrun | ~7min | 528s | PASS(R1a 参考检测器,已降格) |
| test_basegen_thermal_t1_real_occurrence | longrun | 分钟级 | — | PASS |
| test_r_prec_t2 / test_r_prec_t3 | longrun | ~5min / ~20min(需独占CPU) | 205s / 701s | PASS |
| test_r1_x2c | longrun | ~2min | 完整跑通 | PASS(2026-09-08 pytest 覆盖恢复：ISO-1/2+K_R1/K_gen/K_out 独立收集，共6项——此前仅 cut_0 一项，"pytest 全绿"保护不了 X2c 资格) |
| test_r2_x2c | longrun | ~6min | 403s | PASS(已有真 pytest 项 T-R2C-0/1/2) |
| test_relation_occurrence(_dedup/_e2e) | longrun(dedup=fast级) | ~6min | — | PASS |
| test_activation_cloud_runtime | longrun | ~60s | — | PASS |
| test_p2a_generator_core / test_p2a1b3_skin_generator_integration | longrun | 分钟级 | — | PASS |
| test_tss3a_theta_distance_audit | longrun | ~4min | 全部执行完成 | 测量脚本(无断言判定,状态=MEASURED 非 PASS) |
| test_r_prec_plastic_learning | longrun | 分钟级(50k步训练) | — | PASS |
| test_r_prec_replay_aprime | longrun | 分钟级 | — | PASS |

## 四、已知未达标项（LIM，红色可见，不许调参放行）

| 模块 | 分层 | 状态 |
|---|---|---|
| test_r_prec_replay_simple | 机制层 PASS / 效应量层 **xfail** | LIM-RPREC-READOUT-001(总压缩297×,结构性不可达,见 degradation_registry LIM 节；外部复评确认两 XFAIL 应保留,禁调阈值放行) |
| test_r_prec_replay | R1/R3 PASS / R2 效应量层 **xfail** | 同上 |

## 五、诊断/探针/实验脚本（不被 pytest 收集，diagnostic）

| 脚本 | 用途 | 入口 |
|---|---|---|
| _diag_rprec_effect_compression | LIM-RPREC-READOUT-001 压缩链定量(2026-09-06) | run(), ~3min |
| _diag_deg018_dual_clock_equivalence | DEG-018 双时钟等价性审计(EXP-DEG018-01, 2026-09-07) | main(), ~4min |
| _diag_lim_population_readout_model | LIM 多束读出标度律(EXP-LIM-01, 2026-09-07) | main(), ~8min |
| _diag_t3_c0_ratio_audit / _diag_t3_c0_multiseed / _probe_t3_c0_seed | T3-C0 比例/多种子对照 | run() |
| _diag_t3_c1r_readout_ab | 读出机制 R-A/R-B 判别 | run(), 建议 PYTHONHASHSEED=0 |
| exp_P2A1a_*(2) / exp_P2A1b_*(3) / exp_P2A3_*(2) / exp_P2A_highinput_root_cause | P2-A 系列标定/根因实验 | run() |
| exp_memristor_stable_hash_verification | 哈希扰动稳定性验证 | run() |
| _diag_c1_runtime_lineage_collision | A9 运行时实例谱系缺口登记(EXT-2 P1-2, 2026-09-10)——exit 0=GAP 已登记非 A9 PASS | main(), 秒级 |
| _diag_c1_parent_amplitude_information_loss | adapter 二值化删除父关系幅度信息(EXT-2 P1-4)——只诊断不判 bug | main(), ~1min |
| _diag_c1_cross_occurrence_history_reconstruction | 跨 occurrence 历史增强可由 H_τ 叠加完全重构(EXT-2 P1-5)——history dependence EXISTS / independent organization NOT ESTABLISHED | main(), ~1min |

注：exp_P2A1b_3_closure_calibration 于 2026-09-08 同步 epoch/token 语义
（评判 §2——旧版判据4 exit 1 是门控正确工作而非状态机 bug）并新增判据6
负对照（同一支撑 epoch 仅 1 次 occurrence），现 exit 0。

## 维护约定

- 新增资格套件必须同步登记本清单 + `tss/QUALIFICATION_LEDGER.md`（结果台账）
- marker 分层定义在 `tss/tests/conftest.py`，按实测时长修订
- 状态列反映最近一次全量验证（见 QUALIFICATION_LEDGER 的运行记录）
- TSS ↔ nexus_v1 版本配对：接口清单变更时同步 `tss/VERSION_PAIRING.json`
