# tss/ — TSS/基础生成元理论轨

## 这是什么

时间/空间/尺度（Temporal/Spatial/Scale）生成算子研究线：探究一个有限、耗散、
局部可感的物理系统如何从真实过程取得"发生"（occurrence），在内部生成时间/
空间/尺度组织，再耦合成更高阶生成元并后验修正自己。核心概念（基础生成元 𝒢、
实时发生 p_α、后验发生记录 Occurrence、首次进入门 ℰ↑、关系 Θ/Σ/Λ）的完整
定义见理论文本（下方指引）。

本轨是构建在 `nexus_v1/`（organism 活体电路）之上的**离线分析/理论验证层**，
不是 organism 的一部分。

## 依赖方向纪律（硬性约束）

```
tss/*      → nexus_v1/*    允许（单向引用活体 Neuron/SynapticBundle 对象）
nexus_v1/* → tss/*         禁止（organism 对本轨零 import、零感知）
```

违反第二条即破坏"不修改母体代码加功能"原则（nexus_v1/RULES.md）。
已知护栏缺口：`base_generator.feed()` 与 `circuit.step()` 的双驱动互斥
仅有文档警告、无代码级互锁——见 DEG-021（cell-cell/docs/degradation_registry.md）。

## 迁移记录（2026-09-06）

自 `nexus_v1/` 迁出，动机：本轨已积累 ~7000 行代码 + 50+ 测试脚本（占原
nexus_v1/tests/ 的近四成），与 organism 本体边界混淆。经用户裁定迁至顶层
`tss/`（与 `nexus_v1/`、`governance/` 平级）。

**纯搬迁声明**（遵守理论文本约束：不批量改名冒充新资格、不趁机重构）：
- 零模块名/类名/符号名改动；`occurrence.py` 三态机、`PhysicalEntryGate` 未动
- 仅改动：目录位置 + import 语句（`from ..components.X` → `from nexus_v1.components.X`
  等约 55 处；测试内 `nexus_v1.generators|relations|events|tests` → `tss.*`）
  + 各模块 docstring 首行自述路径
- 各模块的理论资格状态（冻结/降格/候选）不因迁移发生任何变化

| 旧路径 | 新路径 |
|---|---|
| `nexus_v1/generators/` | `tss/generators/` |
| `nexus_v1/relations/` | `tss/relations/` |
| `nexus_v1/events/` | `tss/events/` |
| `nexus_v1/tests/test_basegen_*` 等 51 个理论轨脚本 | `tss/tests/` |

测试入口（与迁移前同约定，仓库根目录运行）：
```bash
PYTHONIOENCODING=utf-8 python -m tss.tests.test_<name>
```

## 当前状态与重启指引（2026-09-06 暂停时点）

- 进度冻结在 TSS-R1b（`entry_gate.py`/PhysicalEntryGate 已冻结，10/10 PASS）
- 已冻结资产：p_α 边界端口（`relations/boundary_process.py`）、ℰ↑ 物理门
  （`relations/entry_gate.py`）；`occurrence.py` 冻结为后验审计；Σ/Λ 降格保留
- 理论路线图下一步：M1 R1c — H_τ 物理历史保持核（输入只来自 PhysicalEntryGate，
  真实电容泄漏；**不扩展门、不重构 occurrence.py**）
- 理论文本（权威）：`cell-cell/理论文本_2026-08-14/`（原件另存于 J:/文本，两套独立保存）
  - 先读 `理论主线文档集_2026-08-14/06_当前冻结状态与未决问题.md`
  - 再读 `理论主线文档集_2026-08-14/08_下一阶段路线图.md`
  - 禁止扩张清单：`理念原典审计_2026-08-14/07_最小确认内核与禁止扩张.md`
- 相关登记：DEG-018（occurrence 双时钟）、DEG-019（MOSFET 阈下截零）、
  DEG-020（重复魔数阈值）、DEG-021（双驱动无互锁）
