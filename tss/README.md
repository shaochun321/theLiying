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
DEG-021 已解决（2026-09-07）：BaseGenerator 与 `VariantCircuit.step()`
之间已有 `_step_serial` 双驱动 fail-fast 互锁（T-DD-1~3；母体侧为用户
授权的 1 行最小标记）。母体版本配对约束见 `tss/VERSION_PAIRING.json`
（运行时 fail-fast：`python -m tss.tests.test_version_pairing`）。

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

## 当前状态（2026-09-06：时间支路 M1+M2 完成）

**基础生成元时间支路已走通**（用户裁定范围 2026-09-06）：

```
真实外部发生 → collector(p_α) → E^↑ 门(b^↑) → H_τ 历史核(h^(τ)) → C_Θ 比较器 → r_{i≺j}
   物理热源      活体神经元      entry_gate    history_kernel    theta_comparator
                                 (TSS-R1b)      (TSS-R1c/M1)        (TSS-M2)
```

- **M1** `relations/history_kernel.py`：H_τ 物理历史保持核，T-R1C-1~8 8/8 PASS。
  τ_h=600 步（复用 EXP-T1-01 slow，TSS-3a 裁定），可读窗 723 步，零自由参数。
- **M2** `relations/theta_comparator.py`：C_Θ 全物理 NMDA 型乘法符合检测器
  （C-02 用户裁定：比较完全由 MOSFET 承担），统一 Θ 九条资格 T-TH-1~9 9/9 PASS。
  真实链路三站点对 28≺15/21/24 正向产生、镜像全零；Δt={321,360,312} 为
  **representative observed run**（default seed，参考机），非冻结常数——
  精确步数对环境/浮点执行序敏感（外部评判独立复跑得 {315,355,308}，
  方向性质完全一致），资格依赖的是 forward-positive/reverse-zero，
  不是具体数字。运行出处见 `tss/QUALIFICATION_LEDGER.md`。
- **C0+C1** 关系结构第二层（2026-09-06，用户裁定直通）：
  - C0 契约+审计（`relations/coupling_contract.py` + EXP-C0-02）：候选站点
    扩至 12 个、10 种子两级判定 → **9 个 level-1 合格站点、25 个合格
    level-2 有序对**（排除对 11 个，(29,26) 5/10 翻转为天然阴性对照）
  - C1 适配器（`relations/relation_event_adapter.py`）：关系电流→脉冲，
    NMDA 树突棘波映射（Schiller 2000），HC-009 换能先例拓扑；电容由
    EXP-C1-01 单点响应反解（7.920427e-07，2× 裕量覆盖实测 r 下界）
  - **c_ro 关系次序耦合候选**：Θ 三件套在 level-2 原参数递归复用，
    **C1 工程递归链通过**（T-C1 全部工程性质 PASS：10 种子真实链路
    30/30 正确产生、阴性对照 fwd=5/10 rev=5/10 与审计精确吻合、
    §11 判据链单次跑通 T-C1-11）
  - **理论资格复审改判（EXT-2，2026-09-09/10）**：原 T-C1-6（现
    T-C1-6a）只证明对 memoryless/symmetric 弱基线的次序判别，
    **不构成理论 A8 父层同类不可重构资格**。外部同类 Θ 重构审计：
    c_ro 可由父 relation-event 时间历史经相同 H_τ+Theta 重构至浮点
    误差（残差 ≈5.12e-15），因此 **A8=NOT_MET**（机器守卫
    T-C1-6b）。A9 静态地址谱系 PASS（T-C1-9a）；A9 运行时
    relation-instance 谱系 **GAP**（adapter.step 不消费 instance
    身份，`_diag_c1_runtime_lineage_collision` 登记）。机器可读状态：
    `coupling_contract.C1_*` 常量。
  - c_ro 继续保持：**递归关系输出 / 组织候选前体，非新生成元**
    （K-05）；"方向"之名未冻结（§6.3：结构通过后由用户/评判冻结）；
    K-06 组织资格 BLOCKED、K-07 独立未来作用 NOT_QUALIFIED
- 已冻结资产：p_α 边界端口（`relations/boundary_process.py`）、ℰ↑ 物理门
  （`relations/entry_gate.py`）；`occurrence.py` 冻结为后验审计；Σ/Λ 降格保留
  （按路线图"保持缺失，不写占位电路"）
- **E0** 事件核/残差源类型审计（2026-09-07，§8 开启条件"耦合走通"
  已由 c_ro 满足）：`events/event_core_contract.py` + T-E0-1~4 4/4 PASS
  —— **类型审计资格，非事件核资格**（06 §6#12 措辞纪律）：
  - E-1 六分量审计：θ/Π/W/𝒞 可由既有结构承载；K 无持久存储
    （EXISTS_PARTIAL）、**ℒ 真实缺口**（GAP：tss 层元件不在 organism
    census，账本不可见，实测确认）
  - EXP-E0-01 复放算子地板：frozen c_ro 链从声明父输入端口复放
    **bit-exact**（残差精确 0.0；扰动录制则归零）⇒ C-06 的
    Replay[𝔈] 物理可执行
  - E-4 约束一单发生级证据已有、跨发生持续性未测；约束二与
    E-5(Xin) RULING_REQUIRED——待裁定登记 R-E0-2~5
  - **E0-fix（2026-09-07，用户裁定全修）**：R-E0-1 已裁定（契约+JSON
    快照）→ K=EXISTS、ℒ=EXISTS_PARTIAL（`events/kernel_ledger.py`
    只读账本，T-KL-1~4）；DEG-019/020/021 RESOLVED（021 含母体最小
    `_step_serial` 标记+双驱动互锁 T-DD-1~3）；DEG-018 审计裁定不合并
    （第二时钟非冗余，DESIGN_DECISION_QUANTIFIED）；编号分叉解决
- 理论路线图后续（未启动）：K-06"组织候选"资格实验（阻塞于 R-E0-3
  拓扑保护定义裁定 + 跨发生持续性实验）、S1/S2 空间来源裁定、G0 生长
- 理论文本（权威）：`cell-cell/理论文本_2026-08-14/`（原件另存于 J:/文本，两套独立保存）
  - 先读 `理论主线文档集_2026-08-14/06_当前冻结状态与未决问题.md`
  - 再读 `理论主线文档集_2026-08-14/08_下一阶段路线图.md`
  - 禁止扩张清单：`理念原典审计_2026-08-14/07_最小确认内核与禁止扩张.md`
- 相关登记：DEG-018（occurrence 双时钟）、DEG-019（MOSFET 阈下截零）、
  DEG-020（重复魔数阈值）、DEG-021（双驱动无互锁）
