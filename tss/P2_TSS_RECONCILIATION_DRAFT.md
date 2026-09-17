# P2_TSS_RECONCILIATION_DRAFT — 旧 P2 与 TSS 机制对应审计（草案）

日期：2026-09-18
依据：《TSS 收尾与主线重启》§20/§21。
级别：**draft** = 基于代码阅读的六维比对（input / state / equations /
physical support / output / future effect），不跑新实验；不凭名字判同。
修正：方案矩阵把 `r_ρ^τ` 与 TSS 关系实例并列一行——实际是两个不同对象
（`ratio_r_part.py` 占比关系 vs `relation_occurrence.py` r_prec 关系实例），
本矩阵拆为两行。

---

## 对照矩阵

### 1. ξ_i^occ ↔ TSS occurrence / entry — **SAME（occurrence）+ COEXIST（entry）**

- 六维：**同一实现**。`tss/generators/occurrence.py` 的 `Occurrence`/`OccurrenceClosure` 既是 G0 的 ξ_i^occ 输出（`BaseGenerator.tick()→Optional[Occurrence]`），也是 TSS 关系层的消费入口。input=collector 电压；state=三相状态机；output=χ 记录。
- `entry_gate.PhysicalEntryGate`（E^↑）是**另一个对象**：relation 层"首次进入边界"物理门，作用于 collector 边界过程（R1b），不替代生成元级 occurrence——角色不同，COEXIST。

### 2. χ_i^k ↔ occurrence identity — **SAME + SUPERSET**

- χ_i^k = `Occurrence(t_up, t_down, t_rearm)` 本体（occurrence.py:127 docstring 原话）；χ≠𝔫 由 `natural_unit.py` 承载。
- `occurrence_identity.OccurrenceIdentityRegistry`（P2-B1X1a）是 χ 的**实例身份扩展**（记录 occurrence_28_epoch_17 级身份而非站点身份）——SUPERSET，无冲突。

### 3. r_≺^τ（T1/T2/T3 电路）↔ H_τ+Θ — **COEXIST（不同机制层级）**

| 维 | r_prec（temporal_r_prec*.py） | H_τ+Θ（history_kernel+theta_comparator） |
|---|---|---|
| input | 两站点 occurrence 脉冲（双向历史痕迹） | entry 脉冲流（q_pulse 刷新保持核） |
| state | bundle pre/post trace 电路 | 专用保持电容 C_h（τ_h=600） |
| equations | STDP 型痕迹耦合 | 指数保持 + NMDA 乘法比较（C-02 全物理） |
| physical support | 站点对专属电路 | 统一时间算子（站点无关） |
| output | collector 电流（学习资格轨） | 关系事件（→adapter→c_ro） |
| future effect | LIM-RPREC-READOUT-001（效应上限 0.117%，读出压缩 297×，冻结） | C0 25 对 level-2 + C1 12/12 资格链 |

- 判定：**不同关系机制，允许并存**（§21）。证据强度与物理闭合：H_τ+Θ 更强（M1 8/8 + M2 9/9 + C0/C1 链 + 复放 bit-exact）；r_prec 保留为站点对级可塑关系载体的 findings（含阴性 LIM），不 archive（其学习资格维度 H_τ+Θ 不覆盖）。

### 4. r_ρ^τ（占比关系）↔ TSS 当前机制 — **NOT_COVERED**

- `ratio_r_part.py`（T3-B 原型）/`ratio_r_part_ternary.py`（T3-C2）：r_part 占比关系原型，**r_ρ 升格从未完成**（docstring 自述"留作 T3-C"）。TSS 无占比型关系机制。冻结为 findings，主线若需占比关系须走新资格。

### 5. ρ_{A≺B}^fast（关系实例）↔ TSS 关系实例机制 — **SAME**

- `relation_occurrence.py:70 RELATION_TYPE_A_PREC_B_FAST` + RelationOccurrence/Finalizer **就是** TSS 的在线 D2 关系实例闭合机制本身（P2-B1X1c→R1 时间投影重定型）；C0/C1 的直接消费对象。同一实现，无需 reconcile。

### 6. P2-C relation-relation ↔ C1 — **DIFFERENT（两种构造，允许并存）**

| 维 | P2-C1F（r2_fork.py） | C1（relation_event_adapter + c_ro） |
|---|---|---|
| input | 两条 R1 的共同源分叉 | 两 relation event 的时间次序 |
| state/equations | 分叉结构块（R1StructureBlock 族） | H_τ+Θ 同型栈 + adapter（C=7.92e-07） |
| physical support | fork 拓扑 | 统一时间算子递归 |
| output | R2 关系（关系-关系生成） | c_ro 耦合输出（组织候选，K-05 措辞） |
| future effect | T-R2F 4/4（longrun 追认） | 12/12 + A8_NOT_MET 稳定复现（T-C1-6b） |

- 判定：**DIFFERENT**——分叉生成与递归耦合是两种 relation-relation 构造，表示不同关系，并存；不为架构整洁强行统一（§21）。

### 7. relation qualification ↔ A8-v2 — **EXTENSION**

- 旧资格判据（TSS-3a 三条、§11 判据链、C1 资格语义）⊂ A8-v2 六门制（M1-M5 + M5-P，第四轮扩展）。A8-v2 是资格方法的上位扩展，采纳为按需调用的 qualification test（见 TSS_FREEZE §三）。旧判据继续作为其子集有效。

---

## 汇总

| 旧主线 | TSS | 判定 |
|---|---|---|
| ξ_i^occ | occurrence | SAME（entry=COEXIST） |
| χ_i^k | occurrence identity | SAME + SUPERSET |
| r_≺^τ | H_τ+Θ | COEXIST（保留双方；H_τ+Θ 证据更强） |
| r_ρ^τ | — | NOT_COVERED（升格未完成，冻结） |
| ρ_{A≺B}^fast | relation instance | SAME（同一实现） |
| P2-C relation-relation | C1 | DIFFERENT（并存） |
| relation qualification | A8-v2 | EXTENSION |

**重叠度回答（§27 问 5）**：occurrence/identity/关系实例层完全同一（无重复建设）；时间关系机制层两套并存（不同层级，一强一冻）；关系-关系层两种构造并存；占比关系无覆盖；资格方法统一到 A8-v2。**无一处需要"二选一删除"，无一处凭名字误判。**
