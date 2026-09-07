# TSS 实验清单 (EXPERIMENT MANIFEST)

> 建立于 2026-09-06（外部实测反馈清单 §5 的诉求）。**"pytest 全绿"≠"全部
> 实验体系通过"**——本清单是完整边界：pytest 收集的 test_*、不被收集的
> exp_*/_diag_*/_probe_* 全部在册。格式用 md 表（项目惯例；反馈建议的
> yaml 语义等价）。时长为参考机近似值（PYTHONIOENCODING=utf-8，可修订）。
>
> 统一入口：仓库根目录 `python -m tss.tests.<模块名>`（`-m` 为规范方式；
> 直接路径运行为兼容尽力而为）。pytest 分层：`pytest tss/tests -m "not longrun"`。

## 一、资格套件（required——冻结资格依赖这些）

| 模块 | 资格归属 | marker | 入口 | 约时长 | 状态 |
|---|---|---|---|---|---|
| test_entry_gate | TSS-R1b ℰ↑ 物理门(10项) | longrun | run() / pytest | ~10min | PASS |
| test_history_kernel | TSS-R1c/M1 H_τ (T-R1C-1~8) | longrun | main() / pytest | ~2min | PASS |
| test_theta_unified | TSS-M2 统一Θ (T-TH-1~9) | longrun | main() / pytest | ~3min | PASS |
| test_c0_relation_order_audit | C0 目标对审计(EXP-C0-02) | longrun | run() | ~8min | PASS(25对合格) |
| exp_C1_adapter_calibration | C1 适配器标定(EXP-C1-01) | 不被pytest收集 | run() | ~5s | PASS |
| test_c1_coupling | C1 c_ro 资格(T-C1-1~11) | longrun | main() / pytest | ~10min(10种子) | PASS |
| test_boundary_process | p_α 边界端口 | longrun | run() / pytest | ~7min | PASS |
| test_occurrence_identity | D1 实例身份 | fast | pytest | ~5s | PASS |
| test_e0_event_type_audit | E0 类型审计(T-E0-1~4 含 EXP-E0-01 复放地板) | integration | main() / pytest | ~1min | PASS |

## 二、机制/契约测试（required，快速层）

| 模块 | marker | 约时长 | 状态 |
|---|---|---|---|
| test_generator_contract / test_generator_lambda / test_generator_sigma | fast | 秒级 | PASS(λ/σ 为降格保留资产的守卫) |
| test_event_support_binding | fast | 秒级 | PASS |
| test_natural_unit / test_skin_transduction | fast | 秒级 | PASS |
| test_occurrence_tap / test_selection_contract / test_selection_pool(_seed) | fast | 秒级 | PASS |
| test_basegen_thermal_t0/t1/t3_ratio | integration | <60s | PASS |
| test_r1_structure / test_r2_fork / test_tss2a_scale_audit | integration | <60s | PASS |

## 三、历史原型与长程验证（长时层）

| 模块 | marker | 约时长 | 状态 |
|---|---|---|---|
| test_entry_boundary | longrun | ~7min | PASS(R1a 参考检测器,已降格) |
| test_basegen_thermal_t1_real_occurrence | longrun | 分钟级 | PASS |
| test_r_prec_t2 / test_r_prec_t3 | longrun | ~5min / ~20min(需独占CPU) | PASS |
| test_r1_x2c / test_r2_x2c | longrun | ~2min / ~6min | PASS(x2c fixture 已修 2026-09-06) |
| test_relation_occurrence(_dedup/_e2e) | longrun(dedup=fast级) | ~6min | PASS |
| test_activation_cloud_runtime | longrun | ~60s | PASS |
| test_p2a_generator_core / test_p2a1b3_skin_generator_integration | longrun | 分钟级 | PASS |
| test_tss3a_theta_distance_audit | longrun | ~4min | 测量脚本(无断言判定) |
| test_r_prec_plastic_learning | longrun | 分钟级(50k步训练) | PASS |
| test_r_prec_replay_aprime | longrun | 分钟级 | PASS |

## 四、已知未达标项（LIM，红色可见，不许调参放行）

| 模块 | 分层 | 状态 |
|---|---|---|
| test_r_prec_replay_simple | 机制层 PASS / 效应量层 **xfail** | LIM-RPREC-READOUT-001(总压缩297×,结构性不可达,见 degradation_registry LIM 节) |
| test_r_prec_replay | R1/R3 PASS / R2 效应量层 **xfail** | 同上 |

## 五、诊断/探针/实验脚本（不被 pytest 收集，diagnostic）

| 脚本 | 用途 | 入口 |
|---|---|---|
| _diag_rprec_effect_compression | LIM-RPREC-READOUT-001 压缩链定量(2026-09-06) | run(), ~3min |
| _diag_t3_c0_ratio_audit / _diag_t3_c0_multiseed / _probe_t3_c0_seed | T3-C0 比例/多种子对照 | run() |
| _diag_t3_c1r_readout_ab | 读出机制 R-A/R-B 判别 | run(), 建议 PYTHONHASHSEED=0 |
| exp_P2A1a_*(2) / exp_P2A1b_*(3) / exp_P2A3_*(2) / exp_P2A_highinput_root_cause | P2-A 系列标定/根因实验 | run() |
| exp_memristor_stable_hash_verification | 哈希扰动稳定性验证 | run() |

## 维护约定

- 新增资格套件必须同步登记本清单 + `tss/QUALIFICATION_LEDGER.md`（结果台账）
- marker 分层定义在 `tss/tests/conftest.py`，按实测时长修订
- 状态列反映最近一次全量验证（见 QUALIFICATION_LEDGER 的运行记录）
