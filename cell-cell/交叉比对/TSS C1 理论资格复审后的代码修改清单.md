# TSS C1 理论资格复审后的代码修改清单
## 基于 2026-08-14 理论文档 + 外部数值复审

## 0. 本轮原则

本轮**不重写 C1 物理链，不新增第三层生成元，不实现 Xin/Shadow，不给 c_ro 升格**。

目标只有三个：

1. 修正 C1 当前对“不可约性”的过度表述；
2. 把理论 A8 / A9 当前未通过的状态变成机器可见；
3. 保留 C1 已经真实取得的工程成果，不把负结论误写成代码失败。

当前工程事实继续保留：

```text
relation
→ RelationEventAdapter
→ binary physical pulse
→ level-2 EntryGate
→ H_tau
→ Theta
→ c_ro
```

C1 工程递归链仍然有效。

但当前不得再用现有证据宣称：

```text
c_ro 已满足新生成元不可约性
```

---

# P0-1：修改 `coupling_contract.py` 对 C1 的定位

文件：

```text
tss/relations/coupling_contract.py
```

### 1. 修改模块标题

当前：

```text
C0：首个不越级耦合生成元的类型契约
```

建议改成：

```text
C0：首个不越级耦合候选 / 递归关系候选的类型契约
```

原因：

模块后文本自己又明确：

```text
c_ro 是耦合输出/组织候选
不是新生成元
```

标题不应先行使用“耦合生成元已经成立”的措辞。

---

### 2. 重写 §6.2 第⑤项

当前大意：

```text
为什么不能由父输出的同类简单运算重构：
AND 无法区分顺序，而 c_ro 可以。
```

这只能证明：

```text
c_ro 不可由无记忆 AND / 序盲对称基线重构
```

不能证明理论 A8：

```text
父层同类合格算子不能重构 c_ro
```

外部实测已经证明：

对于父 relation event 间隔 Δt，

```text
c_ro_actual
```

可由父层同型：

```text
PhysicalHistoryKernel + PhysicalThetaComparator
```

重构。

测试范围内最大误差：

```text
≈ 5.12e-15
```

仅为浮点误差。

因此第⑤项应明确改成类似：

```text
⑤ A8 不可约资格当前 NOT_MET。

现有 C1 已证明其输出不能由无记忆 AND 或序盲对称基线重构；
但外部实测表明，relation event 经二值化后，
c_ro 可以由父层已合格的 H_tau + Theta 同类算子精确重构。

因此现有证据只支持：
“递归关系读出具有次序判别能力”

不支持：
“形成父层同类算子不可重构的新生成元作用”。
```

---

### 3. 增加机器可读资格状态

建议在 `coupling_contract.py` 增加纯常量，例如：

```python
C1_ENGINEERING_RECURSION_STATUS = "PASS"
C1_A8_PARENT_CLASS_IRREDUCIBILITY = "NOT_MET"
C1_A9_STATIC_ADDRESS_LINEAGE = "PASS"
C1_A9_RUNTIME_INSTANCE_LINEAGE = "GAP"
C1_GENERATOR_QUALIFICATION = "NOT_QUALIFIED"
```

名称可按项目惯例调整。

这些常量：

- 不进入物理路径；
- 不控制行为；
- 只是资格审计状态。

禁止因为这些状态增加 if/else 改变物理输出。

---

# P0-2：修正 T-C1-6“不可约性”测试含义

文件：

```text
tss/tests/test_c1_coupling.py
```

当前：

```python
test_c1_6_irreducibility()
```

不应该继续代表理论 A8。

## 修改方案

### T-C1-6a

将原测试重命名为类似：

```python
test_c1_6a_baseline_discrimination()
```

或者保留 pytest ID 但修改 docstring。

测试内容继续保留：

```text
memoryless min/AND baseline → 无法检测错时脉冲
symmetric forward+reverse baseline → 无法区分交换序
c_ro → 可以区分 A→B / B→A
```

新的资格名称必须明确：

```text
对弱基线的次序判别能力
```

不要再写：

```text
A8 不可约性已经通过
```

---

# P0-3：新增真正的 A8 反资格测试

增加：

```python
test_c1_6b_parent_theta_reconstructibility()
```

目标：

**证明当前 c_ro 可以由父层同类合格算子重构。**

这是一条 PASS 测试，但 PASS 的含义是：

```text
A8_NOT_MET 被稳定复现
```

不是：

```text
生成元资格 PASS
```

## 测试方式

不要只复制解析公式。

真正实例化一套独立父层同型：

```text
PhysicalEntryGate
PhysicalHistoryKernel
PhysicalThetaComparator
```

使用与 M2 相同的默认参数。

给 reconstruction stack 输入与 C1 adapter 输出完全相同的二值事件时刻。

扫描至少：

```text
Δt =
1
5
10
20
35
42
50
100
300
600
700
722
723
800
```

比较：

```python
actual_c_ro
reconstructed_theta_output
```

要求：

```python
math.isclose(
    actual,
    reconstructed,
    rel_tol=1e-12,
    abs_tol=1e-12,
)
```

并确认：

```text
Δt >= read window
```

时两边都归零。

如果未来这项测试开始出现系统性非零残差：

**不要自动修测试。**

那意味着可能出现了新的研究对象，应单独开启理论审查。

---

# P0-4：更新 C1 总资格表述

当前 C1 不应再总结成：

```text
T-C1-1~11 全部通过
→ 不可约耦合候选成立
```

应拆成两层：

### 工程资格

```text
relation re-eventization       PASS
单父零输出                      PASS
交换序拒绝                      PASS
窗口边界                        PASS
父结构阻断                      PASS
弱基线次序判别                  PASS
跨层共参                        PASS
阴性对照                        PASS
静态地址谱系                    PASS
无学习依赖                      PASS
真实端到端链                    PASS
```

### 理论生成元资格

```text
A8 父层同类不可重构             NOT_MET
A9 静态地址谱系                 PASS
A9 运行时 relation-instance 谱系 GAP
K-06 组织闭合                   NOT_STARTED / BLOCKED
K-07 独立未来可达作用           NOT_QUALIFIED
```

---

# P1-1：拆分 T-C1-9 的“谱系”含义

当前：

```python
test_c1_9_lineage_and_static_audit()
```

实际上证明的是：

```text
GeneratedAddress domain 正确
generation_depth == 2
有两个 parent_addresses
level-2 comparator 使用两个 adapter address
adapter 无软件 t_step/phase
```

这只能称：

```text
static structural-address lineage
```

不能代表：

```text
runtime relation-instance lineage
```

建议改名：

```python
test_c1_9a_static_address_lineage()
```

或者至少修改 docstring 和打印信息。

---

# P1-2：把 A9 运行时谱系缺口显式登记

当前：

```python
RelationEventAdapter.step(self, r_current, dt)
```

物理接口只消费：

```text
r_current
dt
```

不会消费：

```text
RelationOccurrence
parent occurrence instance IDs
relation window
ledger snapshot
runtime epoch identity
```

因此两个不同 relation instance：

```text
Relation A/Epoch1
Relation A/Epoch2
```

只要产生完全相同的 `r_current(t)`，

adapter 和 C1 后续物理路径无法区分。

本轮**不要为了修这个问题直接修改 adapter.step()**。

原因：

1. 当前 c_ro 尚未取得生成元资格；
2. 把 INFRA identity 强行塞进 BIO/SEMI 物理路径，容易反过来污染原有纪律；
3. 目前应先冻结缺口，再设计正式的谱系保持机制。

建议新增一个纯 diagnostic：

```text
tss/tests/_diag_c1_runtime_lineage_collision.py
```

实验：

```text
case A:
relation instance lineage = Epoch1/Epoch1
physical r traces = X

case B:
relation instance lineage = Epoch1/Epoch2
physical r traces = X
```

确认：

```text
adapter pulses identical
c_ro identical
```

并打印：

```text
A9_RUNTIME_INSTANCE_LINEAGE = GAP
```

这个脚本 exit 0。

exit 0 表示：

```text
已正确复现并登记缺口
```

不是：

```text
A9 PASS
```

---

# P1-3：暂时不要给 RelationEventAdapter 加身份判定

特别禁止 agent 直接做：

```python
adapter.step(r_current, dt, relation_occurrence)
```

然后：

```python
if epoch_mismatch:
    return 0
```

这种修改。

这会让 Python/INFRA 身份直接决定 BIO/SEMI 物理输出。

当前没有理论裁定允许这样做。

未来如果解决 A9，应优先考虑：

```text
物理信号路径保持原样

+
独立的 lineage audit/binding sidecar
```

由 sidecar 记录：

```text
emitted relation-event pulse
↔
online relation instance key
↔
parent occurrence instance IDs
↔
relation window
↔
ledger
```

但该 sidecar：

```text
不得改变 spike 是否产生
不得控制 Θ
不得控制 gate
```

除非以后另有理论裁定。

本轮只登记 GAP，不实现正式 binder。

---

# P1-4：新增 relation amplitude 信息损失诊断

外部实测发现：

固定：

```text
Δt2 = 50
```

把两条父 relation current 从：

```text
0.002 ～ 0.36
```

大幅改变，

只要两边都超过 adapter 的实际发放阈值，

最终：

```text
c_ro
```

完全相同。

49 个有效组合实测均为：

```text
0.4340310902405273
```

说明当前：

```text
graded relation current
→ binary relation event
```

会主动删除父关系幅度信息。

建议增加：

```text
_diag_c1_parent_amplitude_information_loss.py
```

只作为诊断，不判 bug。

记录：

```text
adapter threshold
above-threshold amplitude equivalence
fixed Δt2 output equality
```

并在台账说明：

> level-2 当前消费的是“关系是否发生 + 发生时间”，而不是完整父关系幅度。

---

# P1-5：增加跨 occurrence 历史可重构诊断

外部重复 relation-pair 实验发现：

第二次相同 pair 的输出会因上一 occurrence 的 H_tau 残留而增强。

但是整个效应仍可由：

```text
已有 H_tau 指数历史叠加
```

重构到约：

```text
5e-15
```

因此增加：

```text
_diag_c1_cross_occurrence_history_reconstruction.py
```

测试多个 epoch gap：

```text
1204
1300
1500
2000
2500
3000
4000
5000
```

比较：

```text
actual second c_ro
known H_tau reconstruction
```

结论必须写：

```text
cross-occurrence history dependence EXISTS

but

independent organization state NOT ESTABLISHED
```

不要把历史增强写成“跨 occurrence 组织持续性”。

---

# P1-6：随机性实验语义拆分

外部实测还发现：

当前 `physical_seed` 只固定相关 bundle 的物理扰动。

母体仍存在独立全局随机源，例如 Langevin noise。

因此：

```text
physical_seed variation
```

和：

```text
world/global RNG variation
```

不是同一随机变量。

以后涉及多种子资格时，建议明确区分：

```text
physical_seed
world_rng_seed
```

可以增加新的研究/诊断驱动：

```text
physical_seed × world_rng_seed
```

但本轮不要改原冻结 C0/C1 合格列表。

只修改 manifest/说明：

> 当前历史 10-seed 资格是复合随机环境下的鲁棒性样本，不应解释成只扫描了 bundle physical variation。

如果 agent 要增加 deterministic reproduction helper，可以提供：

```python
random.seed(world_rng_seed)
```

但不能把固定 world RNG 变成所有正式资格测试的唯一模式。

最好同时保留：

```text
deterministic reproduction mode
stochastic robustness mode
```

---

# P2：修正 README

文件：

```text
tss/README.md
```

当前 C0+C1 段落中类似：

```text
T-C1-1~11 PASS
含不可约实验
```

应改成：

```text
C1 工程递归链通过；
原 T-C1-6 只证明对 memoryless/symmetric 弱基线的次序判别，
不构成理论 A8 父层同类不可重构资格。

外部同类 Θ 重构审计：
c_ro 可由父 relation-event 时间历史经相同 H_tau+Theta
重构至浮点误差，因此 A8=NOT_MET。

c_ro 继续保持：
递归关系输出 / 组织候选前体，
非新生成元。
```

项目当前 README 本来已经强调 `c_ro` 不是新生成元，这一点继续保持。

---

# P2：更新 `QUALIFICATION_LEDGER.md`

建议新增：

```text
EXT-2 — 2026-09-09/10 C1 理论资格复审
```

至少记录：

### A8

```text
parent-class reconstruction:
max residual ≈ 5.12e-15

RULING:
A8 NOT_MET
```

### Adapter 信息压缩

```text
above-threshold relation amplitudes:
0.002 ... 0.36

fixed Δt2:
same binary event
same c_ro
```

### Cross-occurrence

```text
history dependence observed
fully explained by existing H_tau
no independent persistent organization variable established
```

### A9

```text
static address lineage: PASS
runtime relation-instance lineage through adapter: GAP
```

### 总状态

```text
C1 engineering recursion: PASS
new-generator qualification: NOT_QUALIFIED
K-06 organization qualification: BLOCKED
```

资格台账当前已经明确要求区分历史资格与当前复现结果，这次继续沿用这个纪律。

---

# P2：更新 `EXPERIMENT_MANIFEST.md`

新增 diagnostic 项：

```text
_diag_c1_parent_theta_reconstruction
_diag_c1_runtime_lineage_collision
_diag_c1_parent_amplitude_information_loss
_diag_c1_cross_occurrence_history_reconstruction
```

或将第一个做成正式 pytest。

推荐：

```text
parent Theta reconstruction → required qualification/audit pytest
其他三个 → diagnostic
```

C1 状态不要再简单写：

```text
PASS
```

建议写：

```text
Engineering PASS;
A8 NOT_MET;
A9-runtime GAP;
not generator-qualified
```

---

# P2：`r2_fork` marker 顺手修正

这是上一轮已经连续两次外部实测确认的小型测试工程问题。

当前 manifest：

```text
test_r2_fork = integration (<60s)
```

但外部实际：

```text
第一次 ≈182s
第二次 ≈121.5s
```

已经连续超过 integration 定义。

建议：

```text
test_r2_fork
integration → longrun
```

这只是 marker 修复，不改代码行为。

当前 manifest 自己已经登记过这一冲突。

---

# 明确禁止本轮修改的内容

Agent 不要顺手做以下事情：

```text
1. 不新增第三层生成元。
2. 不把 c_ro 改名为“方向生成元”。
3. 不实现 Xin。
4. 不实现 Shadow。
5. 不开始 S1/S2 空间构造。
6. 不修改 H_tau=600 来制造不可约残差。
7. 不修改 Theta 参数。
8. 不修改 RelationEventAdapter 阈值来保留 amplitude。
9. 不引入 STDP/DA。
10. 不为了 A9 把 Python epoch 判断放进物理发放条件。
11. 不删除现有 C1 PASS 实验。
12. 不把两个 LIM XFAIL 调绿。
```

特别注意：

**现有 C1 不是“失败代码”。**

需要修改的是它的：

```text
qualification semantics
test naming
audit boundary
documentation
```

而不是把物理实现重写到产生“更复杂”的结果。

---

# 修改后的推荐状态树

最终项目应该明确呈现：

```text
真实基础发生
    ↓
Theta 一级时间关系                 PASS
    ↓
RelationEventAdapter 关系再事件化   PASS
    ↓
Theta 递归                         PASS
    ↓
c_ro                               EXISTS
                                      │
                                      ├─ 次序判别             PASS
                                      ├─ 父阻断               PASS
                                      ├─ 共参                 PASS
                                      ├─ 非学习依赖           PASS
                                      ├─ 静态地址谱系         PASS
                                      │
                                      ├─ A8 同类不可重构      NOT_MET
                                      ├─ A9 运行时实例谱系     GAP
                                      ├─ 自身闭合             NOT_ESTABLISHED
                                      └─ 独立未来作用         NOT_ESTABLISHED

因此：

c_ro =
递归关系输出 / 组织候选前体

NOT:
新生成元
```

---

# 修改完成后的验收

至少运行：

```bash
python -m pytest tss/tests/test_c1_coupling.py -q
```

要求：

```text
旧工程性质全部继续 PASS
新增 parent-Theta reconstructibility audit PASS
```

这里新增测试 PASS 的语义必须明确：

```text
A8 NOT_MET 被成功验证
```

而不是“A8 PASS”。

再运行：

```bash
python -m tss.tests._diag_c1_runtime_lineage_collision
python -m tss.tests._diag_c1_parent_amplitude_information_loss
python -m tss.tests._diag_c1_cross_occurrence_history_reconstruction
```

然后：

```bash
python -m pytest tss/tests --collect-only -q
```

确认：

```text
旧测试没有凭空消失
总数 = 223 + 本轮实际新增 pytest 数
```

最后跑：

```text
完整 TSS pytest
全部 exp/diag/probe
nexus_v1 母体 21 项回归
```

两个已有 LIM：

```text
replay_simple effect-size
replay R2 effect-size
```

仍应保持 XFAIL。

---

## 本轮最终裁定

不要让 agent 试图“修到 c_ro 通过 A8”。

这轮真正要达到的目标是：

> **让代码忠实表达实验事实：C1 的递归物理链成立，但当前 c_ro 可由父层同类 Θ 完全重构，因此尚未取得新生成元资格；同时运行时实例谱系在 relation re-eventization 处仍有明确缺口。**

完成这一步以后，再开始设计真正满足 A8/A9/K-06 的“时间方向组织候选”。