# MAINLINE V2 — D2-0 / P2-B
## 自然化接口与第一次真实关系生成
### G0 主线冻结后的首个 D2 实验方案

---

# 0. 阶段定位

当前冻结状态：

```text
W1 = WORLD_V2_RAW_QUALIFIED
T1-B = TRANSDUCTION_V2_QUALIFIED
G0-R0 = G0_MULTIRATE_TIMEBASE_QUALIFIED
G0-R1/OCC = G0_OCCURRENCE_V2_QUALIFIED
D1_SUFFICIENT_FOR_D2 = TRUE

FREEZE G0-CENTRIC MAINLINE
```

G0-R1/OCC 已明确：

> 下一轮为 D2-0 / P2-B，多个真实 \(\chi_i^{(0)}\) 经 \(\mathcal N\) 进入 \(\mathcal C_\rho\)，消费接口为 `OccurrencePortV2`。

本轮理论建筑地址：

\[
\boxed{
D_1
\rightarrow
D_2
}
\]

本轮目标不是构造：

- TOPRXin；
- Xin；
- Shadow；
- 完整内部时空；
- 高级自然单位；
- 行为规划；
- G1 最终资格。

只解决：

\[
\boxed{
\chi^{(0)}
\xrightarrow{\mathcal N}
\widehat y^{(0)}
\xrightarrow{\mathcal C_\rho}
x_\rho
}
\]

并判断：

\[
x_\rho
\]

是否已经形成一个**真实关系过程候选**。

旧理论的完整递归本来就是：

\[
\chi^{(d)}
\xrightarrow{\mathcal N}
\widehat y^{(d)}
\xrightarrow{\mathcal C}
x
\xrightarrow{\mathcal Q}
\chi^{(d+1)}.
\]

本轮只推进前三项，并尽量做到首次 \(\mathcal Q\) 原型；不提前宣称新生成元。

---

# 1. 核心研究问题

本轮只问一个问题：

> 多个已经资格化的基础发生，在不读取 G0 内部神经元状态、不使用语义标签、不预设关系类别的条件下，是否可以经过有限自然化，进入一个具有自身状态、耗散和历史的真实关系结构？

形式化：

给定：

\[
\chi_i^{(0)},\quad
\chi_j^{(0)}
\]

及其：

\[
OccurrencePortV2_i,
OccurrencePortV2_j,
\]

寻找：

\[
\mathcal N_i,\mathcal N_j
\]

使：

\[
\widehat y_i
=
\mathcal N_i(\chi_i^{(0)}),
\]

\[
\widehat y_j
=
\mathcal N_j(\chi_j^{(0)}),
\]

可以合法进入：

\[
\mathcal C_\rho
(
\widehat y_i,
\widehat y_j;
x_\rho
)
\]

并形成：

\[
\dot x_\rho
=
F_\rho(
x_\rho,
\widehat y_i,
\widehat y_j
).
\]

---

# 2. 本轮最重要的限制

禁止：

\[
\boxed{
\chi_i+\chi_j
\rightarrow
\text{Python label `"relation"`}
}
\]

关系不能是：

- tuple；
- database row；
- correlation coefficient；
- 两个 occurrence ID 拼接；
- 人工 `if A before B then relation=1`；
- 固定语义分类。

真正的关系候选必须有：

\[
\boxed{
\text{自己的动态状态 }x_\rho
}
\]

并表现：

- 蓄积；
- 有限响应；
- 衰减；
- 耗散；
- 历史依赖；
- 对输入顺序/相位/重叠产生真实动力学差异。

旧理论对此已经明确要求：关系耦合必须具有内部状态、耗散和历史，而不是瞬时比例计算。

---

# 3. 输入源只能是 OccurrencePortV2

D2 禁止：

```text
read neuron membrane voltage
read collector internal state
read pre_trace directly
read ensemble state
read hidden Z_full
```

D2 只能消费：

```text
OccurrencePortV2
```

允许字段：

```text
occurrence_id
generation_depth
physical lineage
t_up_s
t_down_s
t_rearm_s
raw physical track reference
typed input-port provenance
```

本轮可以从 raw track 中派生自然化候选，但必须通过显式：

\[
\mathcal N
\]

完成。

不得绕过 port 直接进入 G0。

---

# 4. 第一轮不要跨模态

为了避免：

```text
thermal vs pressure
thermal vs acceleration
different unit families
```

同时引入过多变量，

第一轮使用：

\[
\boxed{
\text{同类型、不同物理支撑的 2–3 个 }G_0
}
\]

例如：

\[
G_a,G_b,G_c.
\]

它们必须：

- 支撑地址不同；
- occurrence 独立；
- 不共享 instance identity；
- 可产生错开、重叠和独立发生。

这样自然化首先解决：

\[
\boxed{
\text{同类型发生之间的关系生成}
}
\]

跨模态留到 D2-1 或 D2-X。

---

# 5. 最小输入规模

首轮只用：

\[
\boxed{2\text{ 个 G0}}
\]

作为主实验。

第三个只作攻击实验。

不要一开始：

\[
10,\ 20,\ 64
\]

个生成元。

理由：

如果：

\[
2\rightarrow1
\]

的生成机制本身都不成立，

扩大规模没有意义。

---

# 6. 自然化 \(\mathcal N\) 不先追求“最终自然单位”

延续旧 P2-B 原则：

\[
P2\text{-B}
\]

只检验：

> 如何对真实发生施加无量纲测度，使不同生成元可以进入共同关系耦合。

不冻结“自然单位最终是什么”。

因此只允许候选：

## N0 — Occurrence count identity

一次有效发生：

\[
n_i=1.
\]

只能作为存在基准。

不能单独承担关系输入。

---

## N1 — Local phase

对 occurrence：

\[
\vartheta_i(t)
=
\frac{
t-t_i^\uparrow
}{
t_i^{rearm}-t_i^\uparrow
}
\in[0,1].
\]

同时必须保留：

\[
\tau_i^{phys}
=
t_i^{rearm}-t_i^\uparrow.
\]

禁止用 phase 删除物理时间差异。

---

## N2 — Relative timing

两个 occurrence：

\[
\Delta \tau_{ij}
=
t_j^\uparrow-t_i^\uparrow.
\]

自然化：

\[
\widehat{\Delta\tau}_{ij}
=
\frac{
\Delta\tau_{ij}
}{
f(\tau_i,\tau_j)+\epsilon
}.
\]

其中 \(f\) 只允许使用实际 occurrence duration/rearm 等可追踪尺度。

不允许 arbitrary global constant。

---

## N3 — Participation / integrated activity candidate

从 raw track 中定义：

\[
A_i
=
\int_{W_i}
a_i(t)\,dt.
\]

关系输入可用：

\[
\rho_i
=
\frac{A_i}
{\sum_k A_k+\epsilon}.
\]

但必须同时保留原始：

\[
A_i
\]

和 energy ledger。

---

# 7. 第一轮推荐自然化集合

不要一次全部混用。

建议冻结：

\[
\boxed{
\widehat y_i
=
(
\vartheta_i,
\tau_i^{phys},
A_i
)
}
\]

其中：

- \(\vartheta\) = 局部过程进度；
- \(\tau^{phys}\) = 真实持续时间；
- \(A\) = 活动剂量/参与度候选。

关系结构真正消费哪一项必须通过实验资格，而不是理论预选。

---

# 8. Relation Structure 必须是一个真实动态系统

本轮建立最小：

```text
RelationCell / RelationCircuit
```

名称可调整。

必须有状态：

\[
x_\rho(t).
\]

最简单可以是：

\[
\tau_\rho
\dot x_\rho
=
-x_\rho
+
\sum_i
w_i
\Phi(\widehat y_i).
\]

但：

\[
x_\rho
\]

必须由真实可实现结构承担。

优先复用项目已有：

- Capacitor；
- Neuron；
- SynapticBundle；
- collector；
- PowerRail / resource interface。

不得新造“纯数学 RelationState”直接作为最终实现。

research 层可以先有 reference equation，但最终 qualification 必须对应实体结构。

---

# 9. 不要直接复活旧 r≺ / rρ 名称

旧路线曾写：

```text
r≺^τ
r_ρ^τ
```

可以作为历史参考。

但本轮先使用中性名字：

\[
\mathcal C_{\rho,0}.
\]

原因：

“先后”“占比”等身份必须由实际响应性质确认。

不能因为：

\[
\Delta t>0
\]

就直接命名：

```text
temporal-order generator
```

本轮允许外部报告说：

> candidate responds to relative timing.

内部不创建语义标签。

---

# 10. 第一关系结构最低要求

必须具有：

### R1. Statefulness

同样当前输入：

\[
u(t_0)
\]

不同历史：

\[
x_{\rho,A}\neq x_{\rho,B}
\]

可以产生不同未来响应。

---

### R2. Dissipation

输入停止后：

\[
x_\rho
\]

不能永久保持非物理常值。

必须有：

\[
\dot x_\rho\rightarrow0
\]

或物理耗散/恢复机制。

---

### R3. Finite response

禁止无限累加。

必须存在：

- saturation；
- leak；
- resource bound；
- reset/recovery；

至少一个真实物理限制。

---

### R4. Physical ledger

关系结构的：

\[
E_{in},E_{stored},E_{diss}
\]

或当前模型可实现代理必须可审计。

---

### R5. Lineage

输出必须能追溯：

\[
\chi_i^{(0)},
\chi_j^{(0)}
\rightarrow
x_\rho.
\]

---

# 11. 输入实验矩阵

不要暴力全排列。

首轮只做以下 6 类：

### C0 — Single A

\[
A
\]

单独 occurrence。

### C1 — Single B

\[
B
\]

单独 occurrence。

### C2 — Simultaneous

\[
A\parallel B.
\]

### C3 — A→B

固定物理延迟：

\[
+\Delta t.
\]

### C4 — B→A

反向：

\[
-\Delta t.
\]

### C5 — Partial overlap

两个 occurrence 只部分重叠。

这 6 个已经足以攻击：

- 纯共现；
- 时序；
- overlap；
- 单输入污染。

---

# 12. 第二轮才增加 history attack

只有 C0-C5 表明：

\[
\mathcal C_{\rho,0}
\]

确实不是瞬时函数，

才增加：

### C6 — Same current input, different past

构造：

\[
u_A(t_0)=u_B(t_0)
\]

但：

\[
history_A\neq history_B.
\]

如果：

\[
x_{\rho,A}(t_0)
\neq
x_{\rho,B}(t_0),
\]

且未来关系响应不同，

说明存在真正 relation memory。

---

# 13. Hidden Dynamics 方法正式复用

本轮禁止重新发明 hidden-state 方法。

直接复用：

\[
\boxed{
\text{same visible}
\rightarrow
\text{different future}
\rightarrow
\text{probe locate}
\rightarrow
\text{causal intervention}
\rightarrow
\text{stop/deepen}
}
\]

如果关系结构存在：

\[
Z_\rho
\]

导致未来差异，

先找最低维候选。

如果：

\[
(P,Z_\rho)
\]

已经关闭未来，

登记：

```text
RELATION_MINIMAL_SUFFICIENT_STATE_CANDIDATE
STOP_DEEPER_DECOMPOSITION
```

不继续拆电容、神经元、bundle 微态。

---

# 14. Probe / Ledger 策略

当前不要做 organism census integration。

直接复用：

```text
research recorder
kernel ledger
relation-local ledger
existing diagnostic probes where visible
```

本轮外部记录：

\[
O_\rho(t)
=
(
input,
x_\rho,
energy,
dissipation,
lineage,
candidate\ hidden\ state
).
\]

全部是：

```text
READ_ONLY
```

---

# 15. 纯共现负对照

必须存在：

\[
\boxed{\text{NC1：Pure Coincidence}}
\]

实现一个瞬时：

\[
r(t)=f(y_i(t),y_j(t)).
\]

没有：

\[
x_\rho.
\]

它可以计算 correlation / product / ratio。

预期：

```text
RELATION_SIGNAL = YES
RELATION_GENERATOR_CANDIDATE = NO
```

这样能证明：

> 计算出“关系值”本身不等于产生了关系过程。

---

# 16. 无历史负对照

构造：

\[
x_\rho(t)
=
f(y_i(t),y_j(t))
\]

但没有动态状态。

要求：

\[
same\ current\ input
\Rightarrow
same\ future.
\]

如果它仍被资格化：

```text
QUALIFICATION_LOGIC_FAIL
```

---

# 17. 自激负对照

关系结构接入电源后可能自己振荡。

必须测试：

\[
input=0
\]

但：

\[
x_\rho\neq0.
\]

允许内部余振。

但禁止：

\[
\text{internal oscillation}
\Rightarrow
\text{new physical confirmation}.
\]

没有新的父 occurrence：

\[
\Delta C_{phys}=0.
\]

---

# 18. Lineage block

分别阻断：

\[
\chi_i
\]

或：

\[
\chi_j.
\]

要求关系结构响应发生对应变化。

如果删除父输入仍完全无变化：

```text
PARENT_LINEAGE_INEFFECTIVE
```

该输入不能算真正 parent。

---

# 19. 自然化候选比较原则

不做“best score”。

每个 \(\mathcal N_k\) 独立回答：

1. 是否保持物理来源？
2. 是否避免单位/量程主导？
3. 是否进入同一关系结构？
4. 是否保留时序差异？
5. 是否保留 dose 差异？
6. 是否导致虚假 saturation？
7. 是否对 dt 稳健？

最终允许：

```text
N_PHASE = QUALIFIED
N_ACTIVITY = QUALIFIED
N_COUNT = INSUFFICIENT
```

而不是：

```text
N_PHASE wins
```

---

# 20. dt/timebase

本轮全部沿用：

\[
t_{phys}
\]

唯一物理时间。

Relation structure 可以有自己的：

\[
\Delta t_\rho,
\]

但它只是：

\[
\text{integration resolution}.
\]

必须满足：

\[
\Delta t_\rho
\]

改变时真实：

- leak time；
- delay；
- recovery；
- energy dose；

基本不漂移。

---

# 21. 第一次关系闭合 \(\mathcal Q_\rho\)

本轮允许做一个**最小 closure prototype**。

定义候选：

\[
\chi_\rho^{(1)}
=
(
t_\rho^\uparrow,
t_\rho^\downarrow,
t_\rho^{rearm}
).
\]

但它只登记：

```text
RELATION_OCCURRENCE_CANDIDATE
```

不得直接：

```text
G1_QUALIFIED
```

因为 G1 还需要下一轮递归与独立状态资格。

---

# 22. Relation closure 不能抄 G0 参数

禁止直接复用：

```text
theta_up = 0.01
rearm = 500
```

等 G0 数值。

Relation structure 必须重新测：

\[
u_{\rm silent},
u_{\rm work},
u_{\rm sat},
\tau_{\rm decay},
\tau_{\rm rearm}.
\]

原因：

它是新的物理结构，不是 G0 的另一实例。

---

# 23. Relation closure 只找失败沿

禁止：

\[
8\times8\times16
\]

这类暴力网格。

使用：

\[
\boxed{
\text{adaptive boundary search}
}
\]

流程：

1. 找一个 alive 点；
2. 向低端扩到 fail；
3. 向高端扩到 fail；
4. 二分或小步逼近边界；
5. 只在边界附近留 2–3 个验证点。

目标：

\[
O(\log N)
\]

而不是：

\[
O(N^2).
\]

---

# 24. 计算预算硬规则

每个实验必须预先登记：

```text
n_physical_trajectories
n_replays
n_parameter_points
estimated_state_updates
```

本轮建议上限：

```text
Physical G0 trajectories <= 24
Relation parameter candidates <= 16
Random seeds <= 3
Full hidden-state interventions <= 6
```

超出必须说明：

```text
WHY_NEW_INFORMATION_EXPECTED
```

否则禁止扩大。

---

# 25. 轨迹缓存

所有：

\[
OccurrencePortV2
\]

一旦生成：

```text
IMMUTABLE_CACHE
```

后续 \(\mathcal N\) 和 relation 参数扫描只读缓存。

禁止每换一个：

\[
\theta_\rho
\]

就重新跑 World→G0。

---

# 26. Replay first

关系实验默认：

\[
OccurrencePortV2
\rightarrow
Relation
\]

使用 replay。

只有最终通过后，才跑：

\[
World
\rightarrow
G0
\rightarrow
OccurrencePortV2
\rightarrow
Relation
\]

live end-to-end。

这样大幅降低算力。

---

# 27. Calibration / held-out

建议：

```text
cal = 12
hold = 8
```

而不是立刻扩大到几十上百。

cal 覆盖：

- simultaneous；
- A→B；
- B→A；
- weak overlap；
- strong overlap；
- single parent。

hold 必须加入：

- 未见过的 delay；
- 未见过的 duration；
- 未见过的 dose；
- hidden-dynamics variant。

hold manifest：

\[
SHA256
\]

先冻结再跑。

---

# 28. Held-out 不要求“关系一定发生”

如果某 held-out 输入在物理上不满足 relation structure 的工作域，

允许：

```text
STRUCTURALLY_NO_RELATION
```

不能为了 8/8 relation events 调参数。

真正要求的是：

\[
\boxed{
\text{同样物理条件下行为可解释、可重放、无隐藏语义作弊}
}
\]

---

# 29. Relation Dynamics 五门

## D2-M1 — Naturalization legality

\[
\mathcal N
\]

保留 lineage、物理轨和量纲来源。

---

## D2-M2 — Stateful relation

存在：

\[
x_\rho.
\]

同当前输入、不同合法历史可导致不同 relation future。

---

## D2-M3 — Physical realization

关系状态由真实 project component 承担：

- storage；
- leak；
- delay；
- resource；

不是 Python-only variable。

---

## D2-M4 — Causal parentage

阻断某 parent 会改变 relation process。

---

## D2-M5 — Replay / held-out

缓存 occurrence replay 可重现 relation trajectory，held-out 不结构性崩溃。

---

# 30. 第六门：避免伪生成深度

## D2-M6 — No label promotion

如果删除 RelationCircuit，仅保留：

```text
(A_id, B_id, timing label)
```

仍能得到完全相同输出，

则：

```text
PSEUDO_GENERATION_DEPTH
FAIL
```

必须证明：

\[
\mathcal C_\rho
\]

自身动力学真的贡献了不可替代状态。

---

# 31. G1 资格本轮禁止提前裁定

本轮最多：

```text
RELATION_PROCESS_V0_QUALIFIED
RELATION_OCCURRENCE_CANDIDATE
```

禁止：

```text
G1_QUALIFIED
```

因为下一轮还需要验证：

\[
\chi_\rho^{(1)}
\]

能否再次作为输入参与新的关系生成。

即旧 P2-C：

\[
R+R\rightarrow R'.
\]

并且旧总纲已经明确：

> 即使 `R+R→R'` 成立，也不能自动证明该历史关系已经取得改变未来过程的算子资格。

---

# 32. D2-0 终态只允许四种

### A

```text
D2_RELATION_PROCESS_V0_QUALIFIED
RELATION_OCCURRENCE_CANDIDATE = YES
READY_FOR_D2-1/P2-C
```

---

### B

```text
NATURALIZATION_CONTRACT_UNRESOLVED
```

发生已经够用，但 \(\mathcal N\) 无法合法连接多个 parent。

---

### C

```text
RELATION_STATE_NOT_ESTABLISHED
```

只能得到瞬时函数，没有自己的动态状态。

---

### D

```text
RELATION_PHYSICAL_REALIZATION_FAIL
```

数学 relation 可工作，但物理载体无法成立。

---

# 33. 本轮硬停止

一旦：

```text
D2_RELATION_PROCESS_V0_QUALIFIED
```

成立，

禁止：

```text
D2-0b
Naturalization-v2
RelationCell-v3
large-scale relation sweep
64-generator expansion
```

下一步直接：

\[
\boxed{
D2\text{-}1/P2\text{-C
}
\]

验证关系 occurrence 是否能再次进入关系生成。

---

# 34. D2-1 提前预登记

下一轮目标：

\[
\chi_\rho^{(1)}
\xrightarrow{\mathcal N_\rho}
\widehat y_\rho^{(1)}
\]

然后与：

\[
\chi_k^{(0)}
\]

或另一个：

\[
\chi_{\rho'}^{(1)}
\]

进入：

\[
\mathcal C_{\rho_2}.
\]

如果：

\[
\chi^{(1)}
\]

不能再次成为输入，

则说明 D2-0 形成的是：

```text
terminal relation readout
```

而不是递归生成接口。

---

# 35. 后验构建暂不执行，但预留观测

D2-0 每次 relation 形成后保存：

```text
relation state snapshot
parent lineage
window boundary
local timing candidate
energy ledger
```

这样未来 Posterior-0 可以输入：

\[
\Delta\Gamma^{phys}
\]

然后比较：

\[
\mathfrak B_{\Delta\Gamma}^{W}
\stackrel{?}{\neq}
id.
\]

本轮不实现回限制算子。

---

# 36. UTF-8 可移植性先修

开工前做一个不占研究轮的工程修复：

所有：

```text
JSON
CSV
JSONL
Markdown generated by experiment
```

统一：

```text
UTF-8
```

所有 Python IO 显式：

```python
encoding="utf-8"
```

这是：

```text
REPRODUCIBILITY_PORTABILITY_FIX
```

不算新的 G0 阶段。

---

# 37. 代码范围

建议新增：

```text
research/d2_relation_v0/
```

包含：

```text
dataset_builder.py
naturalization_candidates.py
relation_reference.py
relation_physical_impl.py
calibration.py
hidden_state_attack.py
heldout_eval.py
final_qualification.py
```

production/TSS 新增最小：

```text
tss/relations_v2/
```

或复用现有 `tss/relations/`，避免再造平行架构。

在真正编码前先核查现有 TSS relation primitive 是否可复用。

---

# 38. 优先复用旧 TSS

因为 TSS 已经证明过：

- relation construction；
- re-eventization；
- recursive engineering；

所以第一选择不是从零写 RelationCircuit。

先问：

\[
\boxed{
\text{现有 TSS relation primitive 能否直接消费 OccurrencePortV2？}
}
\]

如果可以：

只增加 adapter 和重标。

如果不可以：

明确记录接口缺口，再做最小新实现。

---

# 39. 禁止旧 TSS 资格反向污染

旧 TSS 中：

```text
c_ro
relation event
H_tau
```

等对象可以作为工程参考。

但不得直接宣称：

\[
\text{旧 TSS relation}
=
\text{当前 D2 relation generator}.
\]

必须重新经过：

\[
OccurrencePortV2
\rightarrow
\mathcal N
\rightarrow
\mathcal C_\rho
\]

主线资格。

---

# 40. 数据输出

至少：

```text
occurrence_parent_manifest.csv
naturalization_comparison.csv
relation_trials.csv
relation_hidden_twins.csv
relation_interventions.csv
relation_energy_ledger.csv
relation_heldout.csv
qualification_summary.json
```

---

# 41. 报告输出

只生成四份：

```text
D2_0_NATURALIZATION_CONTRACT.md
D2_0_RELATION_DYNAMICS_REPORT.md
D2_0_NEGATIVE_RESULTS.md
D2_0_FINAL_RULING.md
```

不再生成大量重复报告。

---

# 42. 首屏必须回答

最终报告必须直接回答：

1. 使用了几个基础 occurrence？
2. 自然化用了哪些字段？
3. 哪些自然化候选失败？
4. Relation 是否有自己的状态？
5. Relation 状态由什么物理结构承担？
6. 输入停止后如何耗散？
7. A→B 和 B→A 是否产生不同动力学？
8. simultaneous 是否与 sequential 不同？
9. same-current / different-history 是否出现不同未来？
10. hidden-state 最小充分候选是什么？
11. 是否停止进一步分解？
12. 阻断 parent 是否改变关系过程？
13. pure coincidence negative control 是否被正确拒绝？
14. held-out 是否通过？
15. 是否形成 relation occurrence candidate？
16. 是否得到：

```text
D2_RELATION_PROCESS_V0_QUALIFIED
```

17. 是否进入：

```text
D2-1/P2-C
```

---

# 43. 本轮真正的成功标准

不是：

> 算出了某种“关系值”。

而是：

\[
\boxed{
\text{多个真实 occurrence 进入一个新的物理结构后，
该结构产生了父 occurrence 单独不能替代的动态状态。}
}
\]

---

# 44. 一句话目标

\[
\boxed{
\text{第一次让“发生之间的关系”真正变成一个正在运行的物理过程，
而不是一个分析者计算出来的标签。}
}
\]