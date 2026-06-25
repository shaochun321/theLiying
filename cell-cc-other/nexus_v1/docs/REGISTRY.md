# 工程档案系统 — 主索引

> 版本: v1.7.2 | 日期: 2026-06-08 | Git: a2d55c4

---

## 架构地图 (atlas/)

| 文档 | 内容 | 状态 |
|---|---|---|
| [GLOBAL_ARCH.md](atlas/GLOBAL_ARCH.md) | 全局信号链、层级计数、文件映射 | ✅ v1.7.2 |
| [LOCAL_vestibular.md](atlas/LOCAL_vestibular.md) | 前庭链: MET→HC→Aff, 6轴定义 | ✅ v1.7.2 |
| [LOCAL_circuit.md](atlas/LOCAL_circuit.md) | Hebbian 电路: 拓扑、学习、结构生长 | ✅ v1.7.2 |
| [LOCAL_motor.md](atlas/LOCAL_motor.md) | 运动管线: Column→Motor→Body | ✅ v1.7.2 |
| [LOCAL_entropy.md](atlas/LOCAL_entropy.md) | 熵账本+Noether 三层审计 | ✅ v1.7.2 |
| [LOCAL_shadow.md](atlas/LOCAL_shadow.md) | 影子层+DA回路 | ✅ v1.7.2 |
| [LOCAL_energy.md](atlas/LOCAL_energy.md) | 能量系统: EnergyStore+代谢预算 | ✅ v1.7.2 |
| [LOCAL_motion_state.md](atlas/LOCAL_motion_state.md) | 运动状态识别与存储 | ✅ v1.7.2 |
| [RELATIONS.md](atlas/RELATIONS.md) | 全局↔局部关系、数据/能量/信息流 | ✅ v1.7.2 |

## 组件档案 (components/)

每个组件一个文件，包含: 物理对应、参数、理论、修改历史。
15/15 组件已覆盖。

→ 机器可读索引: [registry.json](registry.json)

## 理论档案 (theory/)

| 编号 | 名称 | 状态 | 关键代码 |
|---|---|---|---|
| T001 | Noether 守恒 | ✅ 已验证 | noether_probe.py |
| T002 | STDP/BCM 学习 | ✅ 已验证 | bundle.py L286 |
| T003 | Fruit 生命周期 | ✅ 已验证 | bundle.py L436 |
| T004 | 环流理论 | ⚠️ 代码存在未回归测试 | circulation.py |
| T005 | T·S·I 框架 | ⚠️ 代谢约束路径探索中 | variant_adapter.py |
| T006 | 理论锚点 | ✅ 已归档 | 四物理对标 |

## 修改历史 (history/)

| 文档 | 内容 | 状态 |
|---|---|---|
| [VERSION_LOG.md](history/VERSION_LOG.md) | 版本迭代记录 v0.10.1→v1.7.2 | ✅ |
| [PARAM_CHANGELOG.md](history/PARAM_CHANGELOG.md) | 参数变更日志 + 当前值速查 | ✅ |
| [EXPERIMENT_LOG.md](history/EXPERIMENT_LOG.md) | 实验记录 EXP-001→EXP-007 | ✅ |

## 验证系统 (verification/)

| 文档 | 内容 | 状态 |
|---|---|---|
| [INDEX.md](verification/INDEX.md) | 验证体系索引 | ✅ |
| [V001_regression_baseline.md](verification/V001_regression_baseline.md) | 回归基线 v1.7.2 | ✅ |
| [V002_P2.1_thermodynamic_ceiling.md](verification/V002_P2.1_thermodynamic_ceiling.md) | P2.1 验证 | ✅ |

| 系统 | 功能 | 运行方式 |
|---|---|---|
| Regression test | 21 项 29s 快速检查 | `python -m nexus_v1.tests.test_regression` |
| Noether probe | 运行时守恒审计 | 嵌入 VariantCircuit.step() |
| Entropy ledger | 结构事件记录 | 嵌入 VariantCircuit pre/post_step |

## 追踪 (根目录)

| 文档 | 内容 |
|---|---|
| [TRACKER_v1.0.md](TRACKER_v1.0.md) | 项目主追踪表 (S/N/P/E/C/M/D) |

---

## 使用规则

1. **每次代码修改后**: 更新对应的 LOCAL_*.md 和 components/*.md
2. **每次版本号变更**: 更新 VERSION_LOG.md、PARAM_CHANGELOG.md、GLOBAL_ARCH.md
3. **新增组件**: 在 components/ 下创建 .md，在 registry.json 添加条目
4. **新增理论**: 在 theory/ 下创建 T00x.md，在 registry.json 添加条目
5. **实验完成**: 在 EXPERIMENT_LOG.md 添加记录
6. **验证完成**: 在 verification/ 下创建 V00x.md

> ⚠️ 文档是熵账本审计数据的一部分。每个 LOCAL 视图的版本历史节
> 必须与代码变更同步。不同步 = 审计违规。
